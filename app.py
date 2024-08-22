import os
import re
import json
from flask import Flask, jsonify, request
from datetime import datetime
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

# Update index settings
client.indices.put_settings(
    index="cmssw-ibs",
    body={"index.mapping.total_fields.limit": 10000},  # Increase this value as needed
)


# Function that parses the folder's name and saves each part in a variable
def parse_IB_folder_name(folder_name):
    match = re.match(
        r"^(CMSSW_\d+_\d+)(_?[^_]+)?(_X)?_(\d{4}-\d{2}-\d{2}-\d{4})$", folder_name
    )
    if not match:
        print(f"Folder name '{folder_name}' doesn't match the expected pattern")
        return None
    version = match.group(1)
    flavor_part = match.group(2) if match.group(2) else ""
    flavor = flavor_part.lstrip("_")
    if not flavor:
        flavor = "DEFAULT"
    elif flavor == "X":
        flavor = "DEFAULT"
    date = match.group(4)
    return version, flavor, date


# Recursive function to find the cmssw-ib.json file in deeply nested directories
def find_cmssw_ib_file(start_dir):
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.endswith("cmssw-ib.json"):
                return os.path.join(root, file)
    return None


def extract_parse_index_IBs_folders(directory):
    result = {}  # Dictionary to hold all results
    # output_file ="ibs_summary.json"
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            parsed_result = parse_IB_folder_name(item)
            if parsed_result:
                version, flavor, date = parsed_result
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        package_file = find_cmssw_ib_file(sub_item_path)
                        if package_file:
                            packages = extract_packages(package_file)
                            IB_id = f"{version}_{flavor}_{date}_{sub_item}"

                            current_timestamp = datetime.now().isoformat()

                            result[IB_id] = {
                                "version": version,
                                "flavor": flavor,
                                "date": date,
                                "architecture": sub_item,
                                "packages": packages,
                                "@timestamp": current_timestamp,
                            }
                            doc = result
                            resp = client.index(
                                index="cmssw-ibs", id=IB_id, document=doc[IB_id]
                            )
                            # print(resp["result"])

                            resp = client.get(index="cmssw-ibs", id=IB_id)
                            # print(resp["_source"])

                            client.indices.refresh(index="cmssw-ibs")

    return result


def extract_and_parse_IBs_folders(directory):
    result = {}  # Dictionary to hold all results

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            parsed_result = parse_IB_folder_name(item)
            if parsed_result:
                version, flavor, date = parsed_result
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)

                    if os.path.isdir(sub_item_path):
                        package_file = find_cmssw_ib_file(sub_item_path)

                        if package_file:
                            packages = extract_packages(package_file)
                            IB_id = f"{version}_{flavor}_{date}_{sub_item}"

                            current_timestamp = datetime.now()

                            result[IB_id] = {
                                "version": version,
                                "flavor": flavor,
                                "date": date,
                                "architecture": sub_item,
                                "packages": packages,
                                "@timestamp": current_timestamp,
                            }
    return result


# Function to search the IBs index on ElasticSearch - query obtained from frontend POST request
@app.route("/allIBs", methods=["POST"])
def all_ibs_index():

    # Perform the search query on Elasticsearch
    response = client.search(index="cmssw-ibs", size=10000, query={"match_all": {}})

    # Extract the hits from the responsel
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return jsonify(results)


def parse_releases_path(path):
    # Extract Architecture using regex
    architecture_pattern = r"/cms/([^/]+)/"

    # The Version pattern is after the last "/" and before ".json"
    version_pattern = r"/([^/]+)\.json$"

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
        version_match = re.search(r"(CMSSW_\d+_\d+(_\d+)*)(_(.*))?", full_version)
        if version_match:
            release_cycle = version_match.group(1)
            flavor = version_match.group(4) if version_match.group(4) else ""
            release_name = f"{release_cycle}_{flavor}" if flavor else release_cycle
        else:
            release_cycle = "Not found"
            flavor = ""
            release_name = "Not found"
    else:
        release_cycle = "Not found"
        flavor = ""
        release_name = "Not found"

    return architecture, release_name, release_cycle, flavor


# Function that reads package names and versions from a JSON file
# For both IBs and Releases
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
        version_without_checksum = full_version.split("-")[0]

        package_dict[package_name] = version_without_checksum

    return package_dict


def process_releases_directory(directory):
    releases_info = {}

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)

                # Extract architecture, release_name, release_cycle, and flavor from path
                architecture, release_name, release_cycle, flavor = parse_releases_path(
                    file_path
                )

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
                        "packages": packages,
                    }
    return releases_info


def process_and_index_releases_directory(directory):
    releases_info = {}

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)

                # Extract architecture, release_name, release_cycle, and flavor from path
                architecture, release_name, release_cycle, flavor = parse_releases_path(
                    file_path
                )

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
                        "packages": packages,
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


# Function to search the releases index on ElasticSearch - query obtained from frontend POST request
@app.route("/allReleases", methods=["POST"])
def all_releases_index():

    # Perform the search query on Elasticsearch
    response = client.search(
        index="cmssw-releases", size=10000, query={"match_all": {}}
    )

    # Extract the hits from the responsel
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return jsonify(results)


@app.route("/searchIBs", methods=["POST"])
def search_ibs_index():
    search_data = request.json
    packages = search_data.get("packages", [])

    # Build Elasticsearch query
    must_clauses = []
    for package in packages:
        package_name = package.get("packageName")
        version = package.get("version")

        if package_name and version:
            must_clauses.append({"term": {f"packages.{package_name}.keyword": version}})

    query = {"query": {"bool": {"must": must_clauses}}}

    # Perform the search query on Elasticsearch
    response = client.search(index="cmssw-ibs", size=10000, body=query)

    # Extract the hits from the response
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return jsonify(results)


@app.route("/searchReleases", methods=["POST"])
def search_releases_index():
    search_data = request.json
    packages = search_data.get("packages", [])

    # Build Elasticsearch query
    must_clauses = []
    for package in packages:
        package_name = package.get("packageName")
        version = package.get("version")

        if package_name and version:
            must_clauses.append({"term": {f"packages.{package_name}.keyword": version}})

    query = {"query": {"bool": {"must": must_clauses}}}

    # Perform the search query on Elasticsearch
    response = client.search(index="cmssw-releases", size=10000, body=query)

    # Extract the hits from the response
    hits = response["hits"]["hits"]
    results = [hit["_source"] for hit in hits]

    return jsonify(results)


@app.route("/searchIBsPackages", methods=["POST"])
def get_ibs_packages():
    search_data = request.json
    version = search_data.get("version")
    date = search_data.get("date")
    flavor = search_data.get("flavor")
    architecture = search_data.get("architecture")

    # Perform the search query on Elasticsearch
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"version": f"{version}"}},
                    {"match": {"date": f"{date}"}},
                    {"match": {"flavor": f"{flavor}"}},
                    {"match": {"architecture": f"{architecture}"}},
                ]
            }
        }
    }
    response = client.search(index="cmssw-ibs", size=10000, body=query)

    # Extract the hits from the response
    hits = response["hits"]["hits"]
    if hits:
        # Assuming the first hit is the correct one
        packages = hits[0]["_source"].get("packages", {})
        return jsonify(packages)
    else:
        return jsonify({})  # Return an empty dictionary if no results found


@app.route("/searchReleasesPackages", methods=["POST"])
def get_releases_packages():
    search_data = request.json
    release_name = search_data.get("release_name")

    # Perform the search query on Elasticsearch
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"release_name": f"{release_name}"}}
                ]
            }
        }
    }
    response = client.search(index="cmssw-releases", size=10000, body=query)

    # Extract the hits from the response
    hits = response["hits"]["hits"]
    if hits:
        # Assuming the first hit is the correct one
        packages = hits[0]["_source"].get("packages", {})
        return jsonify(packages)
    else:
        return jsonify({})  # Return an empty dictionary if no results found

if __name__ == "__main__":
    app.run(debug=True)


def save_to_json(data, output_file):
    with open(output_file, "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    app.run(debug=True)
