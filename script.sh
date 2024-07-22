#!/bin/bash

# Define the JSON file locations
json_file="cmssw-ib.json"
output_file="yum_info_results.json"
no_details_file="no_details.json"
pypi_details_file="pypi_info_results.json"
pip_details_file="pip_details_file.json"

# Initialize empty JSON objects for output files
echo "{}" > "$output_file"                                                                  
echo "{}" > "$no_details_file"
echo "{}" > "$pypi_details_file"
echo "{}" > "$pip_details_file"

# Function to update JSON file with package information
update_json() {
  local json_file=$1
  local package_name=$2
  local info=$3

  jq --arg name "$package_name" --argjson info "$info" '.[$name] = $info' "$json_file" > tmp.$$.json && mv tmp.$$.json "$json_file"
}

# Function to get yum package info
get_yum_info() {
  local package_name=$1
  local yum_output

  yum_output=$(yum info "$package_name" 2>&1)
  
  if echo "$yum_output" | grep -i "error"; then
    echo "No information found for package: $package_name"
    update_json "$no_details_file" "$package_name" '"No matching packages to list"'
  else
    local description summary license url
    # description=$(echo "$yum_output" | grep  -m 1 "^Description" | cut -d: -f2- | xargs)
    description=$(echo "$yum_output" | awk '/^Description/ {flag=1} /^Summary|License/ {flag=0} flag {print}' | cut -d: -f2- |  sed ':a;N;$!ba;s/\n/ /g')                                                                                                                                                                                                                                                         
    summary=$(echo "$yum_output" | grep -m 1 -E "^Summary" | cut -d: -f2- | xargs)
    license=$(echo "$yum_output" | grep -m 1 -E "^License" | cut -d: -f2- | xargs)
    url=$(echo "$yum_output" | grep -m 1 -E "^URL" | cut -d: -f2- | xargs)

    info=$(jq -n \
      --arg description "$description" \
      --arg summary "$summary" \
      --arg license "$license" \
      --arg url "$url" \
      '{description: $description, summary: $summary, license: $license, URL: $url}')

    update_json "$output_file" "$package_name" "$info"
  fi
} 


# Function to get pip package info
get_pip_info() {
  local package_name=$1
  local actual_package_name=$2
  local pip_output

  pip_output=$(pip show "$actual_package_name" 2>&1)

  if echo "$pip_output" | grep -i "WARNING: Package(s) not found:"; then
    get_pypi_info "$package_name" "$actual_package_name"
  else
    local description summary license url
    description=$(echo "$pip_output" | grep -E "^Description" | xargs)
    summary=$(echo "$pip_output" | grep -E "^Summary" | xargs)
    license=$(echo "$pip_output" | grep -E "^License" | cut -d: -f2- | xargs)
    url=$(echo "$pip_output" | grep -E "^Home-page" | cut -d: -f2- | xargs)

    info=$(jq -n \
      --arg description "$description" \
      --arg summary "$summary" \
      --arg license "$license" \
      --arg url "$url" \
      '{description: $description, summary: $summary, license: $license, URL: $url}')

    update_json "$pip_details_file" "$actual_package_name" "$info"
  fi
}
# Function to get PyPi package info using curl
get_pypi_info() {
  local package_name=$1
  local actual_package_name=$2
  local pypi_output

  pypi_output=$(curl -s "https://pypi.org/pypi/$actual_package_name/json")

  if echo "$pypi_output" | grep -i '"message": "Not Found"'; then
    echo "No information found for package: $package_name"
    update_json "$no_details_file" "$package_name" '"No matching packages to list"'
  else
    local description summary license url
    description=$(echo "$pypi_output" | jq -r '.info.description' | sed ':a;N;$!ba;s/\n/ /g')
    summary=$(echo "$pypi_output" | jq -r '.info.summary')
    license=$(echo "$pypi_output" | jq -r '.info.license')
    url=$(echo "$pypi_output" | jq -r '.info.home_page')

    info=$(jq -n \
      --arg description "$description" \
      --arg summary "$summary" \
      --arg license "$license" \
      --arg url "$url" \
      '{description: $description, summary: $summary, license: $license, URL: $url}')
    update_json "$pypi_details_file" "$package_name" "$info"
  fi
}


# Loop through the package names and run 'yum info' or 'pip show' for each package
jq -r 'keys[]' "$json_file" | while read -r package_name; do
  echo "Fetching info for package: $package_name"

# Check for Python packages and make pip commands or PyPi calls
 if [[ "$package_name" == py3-* ]]; then
    actual_package_name=${package_name#py3-}
    get_pip_info "$package_name" "$actual_package_name"
 elif [[ "$package_name" == py* ]]; then
    actual_package_name=${actual_package_name#py}   
    get_pip_info "$package_name" "$actual_package_name"
  else
    get_yum_info "$package_name"
  fi
done
