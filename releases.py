from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch

app = Flask(__name__)

client = Elasticsearch(
    cloud_id="c4934b0fc9bc4932b9e66aaf7a514d19:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJDkxZmY3NjM0N2ZjYTRjZjY5N2IwYmMxOWUyYTZlM2I3JGE1MTA5YjUyM2RkNzQ1NWNiNjg5YzU0MmI4MDZlNmI5",
    api_key="UXVfUExKRUJ6ZWFqX0oxRXpYRmc6VnVFbl9pX2JSTnFoOFlzNHg5R1c5dw==",
)

# Function to search the Releases index on ElasticSearch - query obtained from frontend POST request
@app.route('/search', methods=['POST'])
def search_releases_index():
    data = request.get_json()
    query = data.get('query', '')

    # Perform the search query on Elasticsearch
    response = client.search(index="cmssw-releases", q=query)
    
    # Extract the hits from the response
    hits = response['hits']['hits']
    results = [hit['_source'] for hit in hits]

    return jsonify(results)   


if __name__ == "__main__":
    app.run(debug=True)
