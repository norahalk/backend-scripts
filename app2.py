import os
import re
import json
import datetime
from collections import defaultdict
from flask import Flask, jsonify

app = Flask(__name__)

# Function that parses the folder's name and saves each part in a variable
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

# Function that reads package names from cmssw-ib.json
def extract_packages(package_file):
    with open(package_file, 'r') as f:
        package_data = json.load(f)
    # Assuming package_data is a dictionary with package names as keys
    package_names = list(package_data.keys())
    return package_names

# Function that creates the subfolders of each parsed variable received
def extract_and_parse_folders(directory):
    parsed_folders = {}
    all_packages_info = []
    current_timestamp = datetime.datetime.now().isoformat()

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            parsed_result = parse_folder_name(item)
            if parsed_result:
                version, flavor, date = parsed_result
                architectures = []
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        architectures.append(sub_item)
                        package_file = os.path.join(sub_item_path, 'cmssw-ib.json')
                        if os.path.exists(package_file):
                            packages = extract_packages(package_file)
                            release_id = f"{version}_{flavor}_{date}_{sub_item}"
                            all_packages_info.append({
                                "release_cycle": version,
                                "flavor": flavor,
                                "date": date,
                                "architecture": sub_item,
                                "packages": packages,
                                "timestamp": current_timestamp,
                                "ID": release_id
                            })
                if version not in parsed_folders:
                    parsed_folders[version] = []
                parsed_folders[version].append((flavor, date, architectures))

    # Save all packages information to a JSON file
    with open('all_packages_info.json', 'w') as f:
        json.dump(all_packages_info, f, indent=4)

    return parsed_folders

# Function that takes the folders, sends them to be parsed then send them to the react frontend
@app.route('/folders', methods=['GET'])
def get_folders():
    directory = '../Desktop/IBs'
    parsed_folders = extract_and_parse_folders(directory)
    
    # Organize data for easier consumption by the frontend
    data = {}
    for version, flavor_date_arch_list in parsed_folders.items():
        dates = defaultdict(lambda: defaultdict(list))
        for flavor, date, architectures in flavor_date_arch_list:
            dates[date][flavor] = architectures
        data[version] = dates
    
    return jsonify(data)

# Function to get the packages from the cmssw-ib JSON file for each IB 
@app.route('/packages/<ib>/<date>/<flavor>/<architecture>', methods=['GET'])
def get_packages(ib, date, flavor, architecture):
    directory = f'../Desktop/package-info-viewer/{ib}_{flavor}_{date}/{architecture}'
    package_file = os.path.join(directory, 'cmssw-ib.json')
    if os.path.exists(package_file):
        with open(package_file) as f:
            packages = json.load(f)
        return jsonify(packages)
    return jsonify([]), 404

# Function to create a new JSON file containing the release cycle, flavor, date, architecture, packages,
# timestamp of current time, and ID (releasecycle_flavor_date_architecture) for each release. 
# Release name and version as key/value pairs, other fields are extra labeled fields.
# All stored in a Python dictionary 
def parser():
    directory = '../Desktop/IBs'
    extract_and_parse_folders(directory)

if __name__ == "__main__":
    parser()
    app.run(debug=True)
