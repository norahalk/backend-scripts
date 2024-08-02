import os
import re
from collections import defaultdict
from flask import Flask, jsonify

app = Flask(__name__)

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
                architectures = []
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        architectures.append(sub_item)
                if version not in parsed_folders:
                    parsed_folders[version] = []
                parsed_folders[version].append((flavor, date, architectures))
    return parsed_folders

@app.route('/folders', methods=['GET'])
def get_folders():
    directory = '../Desktop/package-info-viewer'
    parsed_folders = extract_and_parse_folders(directory)
    
    # Organize data for easier consumption by the frontend
    data = {}
    for version, flavor_date_arch_list in parsed_folders.items():
        dates = defaultdict(lambda: defaultdict(list))
        for flavor, date, architectures in flavor_date_arch_list:
            dates[date][flavor] = architectures
        data[version] = dates
    
    return jsonify(data)

@app.route('/packages/<ib>/<date>/<flavor>/<architecture>', methods=['GET'])
def get_packages(ib, date, flavor, architecture):
    directory = f'../Desktop/package-info-viewer/{ib}_{flavor}_{date}/{architecture}'
    package_file = os.path.join(directory, 'cmssw-ib.json')
    if os.path.exists(package_file):
        with open(package_file) as f:
            packages = f.read()
        return packages
    return jsonify([]), 404

if __name__ == "__main__":
    app.run(debug=True)
