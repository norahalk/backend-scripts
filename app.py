import os
import re
from collections import defaultdict
from flask import Flask, jsonify
import json
import subprocess
import requests
import os
import tempfile

app = Flask(__name__)

# Define the JSON file locations
json_file = "cmssw-ib.json"
output_file = "yum_info_results.json"
no_details_file = "no_details.json"
pypi_details_file = "pypi_info_results.json"
pip_details_file = "pip_details_file.json"

# Initialize empty JSON objects for output files
with open(output_file, 'w') as f:
    json.dump({}, f)
with open(no_details_file, 'w') as f:
    json.dump({}, f)
with open(pypi_details_file, 'w') as f:
    json.dump({}, f)
with open(pip_details_file, 'w') as f:
    json.dump({}, f)

def update_json(json_file, package_name, info):
    with open(json_file, 'r+') as f:
        data = json.load(f)
        data[package_name] = info
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()

def get_yum_info(package_name):
    try:
        yum_output = subprocess.check_output(['yum', 'info', package_name], stderr=subprocess.STDOUT, text=True)
        description = summary = license = url = ""

        description_flag = False
        for line in yum_output.split('\n'):
            if line.startswith('Description'):
                description_flag = True
                continue
            if description_flag and (line.startswith('Summary') or line.startswith('License')):
                description_flag = False
            if description_flag:
                description += line.strip()
            if line.startswith('Summary'):
                summary = line.split(':', 1)[1].strip()
            if line.startswith('License'):
                license = line.split(':', 1)[1].strip()
            if line.startswith('URL'):
                url = line.split(':', 1)[1].strip()

        info = {
            "description": description,
            "summary": summary,
            "license": license,
            "URL": url
        }
        update_json(output_file, package_name, info)
    except subprocess.CalledProcessError as e:
        if "Error" in e.output:
            print(f"No information found for package: {package_name}")
            update_json(no_details_file, package_name, "No matching packages to list")

def get_pip_info(package_name, actual_package_name):
    try:
        pip_output = subprocess.check_output(['pip', 'show', actual_package_name], stderr=subprocess.STDOUT, text=True)
        summary = license = url = ""

        for line in pip_output.split('\n'):
            if line.startswith('Summary'):
                summary = line.split(':', 1)[1].strip()
            if line.startswith('License'):
                license = line.split(':', 1)[1].strip()
            if line.startswith('Home-page'):
                url = line.split(':', 1)[1].strip()

        info = {
            "summary": summary,
            "license": license,
            "URL": url
        }
        update_json(pip_details_file, actual_package_name, info)
    except subprocess.CalledProcessError as e:
        if "WARNING: Package(s) not found:" in e.output:
            get_pypi_info(package_name, actual_package_name)

def get_pypi_info(package_name, actual_package_name):
    response = requests.get(f"https://pypi.org/pypi/{actual_package_name}/json")
    if response.status_code == 404:
        print(f"No information found for package: {package_name}")
        update_json(no_details_file, package_name, "No matching packages to list")
    else:
        pypi_output = response.json()
        description = pypi_output['info']['description'].replace('\n', ' ')
        summary = pypi_output['info']['summary']
        license = pypi_output['info']['license']
        url = pypi_output['info']['home_page']

        info = {
            "description": description,
            "summary": summary,
            "license": license,
            "URL": url
        }
        update_json(pypi_details_file, package_name, info)

@app.route('/api/flavors',methods=['GET'])
def lets_goooo():
    # Loop through the package names and run 'yum info' or 'pip show' for each package
    with open(json_file, 'r') as f:
        package_names = json.load(f).keys()
    for package_name in package_names:
        print(f"Fetching info for package: {package_name}")

        if package_name.startswith('py3-'):
            actual_package_name = package_name[4:]
            get_pip_info(package_name, actual_package_name)
        elif package_name.startswith('py'):
            actual_package_name = package_name[2:]
            get_pip_info(package_name, actual_package_name)
        else:
            get_yum_info(package_name)

def parse_folder_name(folder_name):
    match = re.match(r'^(CMSSW_\d+_\d+)(_?[^_]+)?(_X)?_(\d{4}-\d{2}-\d{2}-\d{4})$', folder_name)
    if not match:
        print(f"Folder name '{folder_name}' doesn't match the expected pattern")
        return None
    version = match.group(1)
    flavor_part = match.group(2) if match.group(2) else ""
    flavor = flavor_part.lstrip('_')
    if not flavor:
        flavor = "DEFAULT"
    elif flavor == "X":
        flavor = "DEFAULT"
    date = match.group(4)
    return version, flavor, date

def extract_and_parse_folders(directory):
    parsed_folders = {}
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            parsed_result = parse_folder_name(item)
            if parsed_result:
                version, flavor, date = parsed_result
                if version not in parsed_folders:
                    parsed_folders[version] = []
                parsed_folders[version].append((flavor, date))
    return parsed_folders

@app.route('/api/folders', methods=['GET'])
def get_folders():
    directory = '../Desktop/IBs'
    parsed_folders = extract_and_parse_folders(directory)
    
    # Organize data for easier consumption by the frontend
    data = {}
    for version, flavor_date_list in parsed_folders.items():
        dates = defaultdict(list)
        for flavor, date in flavor_date_list:
            dates[date].append(flavor)
        data[version] = dates
    
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)
