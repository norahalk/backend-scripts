import os
import re
import json
from datetime import datetime
from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch

app = Flask(__name__)

client = Elasticsearch(
    cloud_id="c4934b0fc9bc4932b9e66aaf7a514d19:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJDkxZmY3NjM0N2ZjYTRjZjY5N2IwYmMxOWUyYTZlM2I3JGE1MTA5YjUyM2RkNzQ1NWNiNjg5YzU0MmI4MDZlNmI5",
    api_key="UXVfUExKRUJ6ZWFqX0oxRXpYRmc6VnVFbl9pX2JSTnFoOFlzNHg5R1c5dw==",
)

# Update index settings
client.indices.put_settings(
    index="cmssw-releases",
    body={"index.mapping.total_fields.limit": 10000},  # Increase this value as needed
)

def parse_path(path):
    # Extract Architecture using regex
    architecture_pattern = r'/cms/([^/]+)/'
    
    # The Version pattern is after the last "/" and before ".json"
    # We want to capture the full version including suffixes like HeavyIon
    version_pattern = r'/([^/]+)\.json$'
    
    # Find Architecture
    architecture_match = re.search(architecture_pattern, path)
    if architecture_match:
        architecture = architecture_match.group(1)
    else:
        architecture = "Not found"
    
    # Find and refine Version
    version_match = re.search(version_pattern, path)
    if version_match:
        full_version = version_match.group(1)
        # Extract the CMSSW version part and any suffix
        version_match = re.search(r'(CMSSW_\d+_\d+(_\d+)*)(_(.*))?', full_version)
        if version_match:
            release_cycle = version_match.group(1)
            flavor = version_match.group(4) if version_match.group(4) else ''
            release_name = f"{release_cycle}_{flavor}" if flavor else release_cycle
        else:
            release_cycle = "Not found"
            flavor = ''
            release_name = "Not found"
    else:
        release_cycle = "Not found"
        flavor = ''
        release_name = "Not found"
    
    return architecture, release_name, release_cycle, flavor

def extract_packages(package_file):
    with open(package_file, "r") as f:
        package_data = json.load(f)

    # Dictionary to store package name and version pairs
    package_dict = {}

    for package_key in package_data:
        package_info = package_data[package_key]
        package_name = package_info["name"]
        full_version = package_info["version"]

        # Split the version to remove the checksum
        version_without_checksum = full_version.split("+")[0]

        package_dict[package_name] = version_without_checksum

    return package_dict

def process_directory(directory):
    releases_info = {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                
                # Extract architecture, release_name, release_cycle, and flavor from path
                architecture, release_name, release_cycle, flavor = parse_path(file_path)
                
                if architecture != "Not found" and release_name != "Not found":
                    # Extract packages from JSON file
                    packages = extract_packages(file_path)
                    
                    release_id = f"{release_name}_{architecture}"

                    current_timestamp = datetime.now().isoformat()

                    # Store the data in the dictionary
                    releases_info[release_id] = {
                        "release_name": release_name,
                        "flavor": flavor,
                        "release_cycle": release_cycle,
                        "architecture": architecture,
                        "timestamp": current_timestamp,
                        "packages": packages
                    }

    # Save the releases_info to a JSON file
    # save_to_json(releases_info,"releases-info.json")

    return releases_info

def process_and_index_directory(directory):
    releases_info = {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                
                # Extract architecture, release_name, release_cycle, and flavor from path
                architecture, release_name, release_cycle, flavor = parse_path(file_path)
                
                if architecture != "Not found" and release_name != "Not found":
                    # Extract packages from JSON file
                    packages = extract_packages(file_path)
                    
                    release_id = f"{release_name}_{architecture}"

                    current_timestamp = datetime.now().isoformat()

                    # Store the data in the dictionary
                    releases_info[release_id] = {
                        "release_name": release_name,
                        "flavor": flavor,
                        "release_cycle": release_cycle,
                        "architecture": architecture,
                        "timestamp": current_timestamp,
                        "packages": packages
                    }
                    doc = releases_info
                    resp = client.index(
                        index="cmssw-releases", id=release_id, document=doc[release_id]
                    )
                    print(resp["result"])

                    resp = client.get(index="cmssw-releases", id=release_id)
                    print(resp["_source"])

                    client.indices.refresh(index="cmssw-releases")

    return releases_info

# Function to search the IBs index on ElasticSearch - query obtained from frontend POST request
@app.route("/search", methods=["POST"])
def search_releases_index():
    data = request.get_json()
    query = data.get("query", "")

    # Perform the search query on Elasticsearch
    response = client.search(index="cmssw-releases", q=query)

    # Extract the hits from the response
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return jsonify(results)


def save_to_json(data, output_file):
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    # Directory to search
    directory = "../Desktop/releases-pkg-info"

    # Process the directory
    # releases_info = process_directory(directory)
    # process_directory(directory)
    process_and_index_directory(directory)

    app.run(debug=True)

    # Save the results to a new JSON file
    # output_file = "releases_summary.json"
    # save_to_json(releases_info, output_file)
