import os
import re
import json
from collections import defaultdict
from flask import Flask, jsonify
from datetime import datetime
from elasticsearch import Elasticsearch

app = Flask(__name__)


client = Elasticsearch(
    cloud_id="c4934b0fc9bc4932b9e66aaf7a514d19:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJDkxZmY3NjM0N2ZjYTRjZjY5N2IwYmMxOWUyYTZlM2I3JGE1MTA5YjUyM2RkNzQ1NWNiNjg5YzU0MmI4MDZlNmI5",
    api_key="UXVfUExKRUJ6ZWFqX0oxRXpYRmc6VnVFbl9pX2JSTnFoOFlzNHg5R1c5dw==",
)

# Function that parses the folder's name and saves each part in a variable
def parse_folder_name(folder_name):
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


# Function that reads package names and versions from a JSON file
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


# Recursive function to find the cmssw-ib.json file in deeply nested directories
def find_cmssw_ib_file(start_dir):
    for root, dirs, files in os.walk("../Desktop/package-info-viewer"):
        for file in files:
            if file.endswith(".json"):
                return os.path.join(root, file)
    return None


def extract_and_parse_folders(directory):
    output_file = "results.txt"
    parsed_folders = {}

    result = {}  # Dictionary to hold all results

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            parsed_result = parse_folder_name(item)
            if parsed_result:
                version, flavor, date = parsed_result
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        package_file = find_cmssw_ib_file(sub_item_path)
                        if package_file:
                            print("--> " + item)
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
                            doc = result
                            resp = client.index(
                                index="cmssw-ibs", id=IB_id, document=doc[IB_id]
                            )
                            print(resp["result"])

                            resp = client.get(index="cmssw-ibs", id=IB_id)
                            print(resp["_source"])

                            client.indices.refresh(index="cmssw-ibs")

                            resp = client.search(
                                index="cmssw-ibs", query={"match_all": {}}
                            )
                            print("Got {} hits:".format(resp["hits"]["total"]["value"]))
                            # for hit in resp["hits"]["hits"]:
                                # print("{release_cycle}".format(**hit["_source"]))

    # with open(output_file, "w") as file:
    #     json.dump(result, file, indent=4)

    return result


# Function to create a new JSON file containing the release cycle, flavor, date, architecture, packages,
# timestamp of current time, and ID (releasecycle_flavor_date_architecture) for each release.
# Release name and version as key/value pairs, other fields are extra labeled fields.
# All stored in a Python dictionary
def parser():
    directory = "../Desktop/package-info-viewer"
    extract_and_parse_folders(directory)


if __name__ == "__main__":
    parser()
    app.run(debug=True)
