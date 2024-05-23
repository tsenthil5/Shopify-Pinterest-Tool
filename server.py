import json
from flask import Flask, request, jsonify, render_template
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import os
import mimetypes
import requests
import time
from flask import Flask, redirect, url_for

app = Flask(__name__)

shopify_url = ""
shopify_token = ""

transport = RequestsHTTPTransport(
    url=shopify_url,
    headers={'X-Shopify-Access-Token': shopify_token},
    use_json=True,
)
client = Client(transport=transport, fetch_schema_from_transport=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/images', methods=['POST'])
def get_images():
    query = gql(''' {
        files(first:10, reverse:true) {
            edges {
                node {
                    createdAt
                    updatedAt
                    alt
                    ... on MediaImage {
                        id
                        originalSource{
                            fileSize
                            source: url
                        }
                        image {
                            id
                            originalSrc: url
                            width
                            height
                        }
                    }
                }
            }
        }
    }
    ''')
    
    response = client.execute(query)
    return jsonify(response)

@app.route('/addImages', methods=['POST'])
def add_images():
    filePath = "frog.jpeg"
    with open(filePath, 'rb') as f:
        image = f.read()
    fileSize = os.path.getsize(filePath)
    
    query = gql('''
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
        stagedUploadsCreate(input: $input) {
            stagedTargets {
                resourceUrl
                url
                parameters {
                    name
                    value
                }
            }
            userErrors {
                field
                message
            }
        }
    }
    ''')

    variables = {
        "input": {
            "filename": filePath,
            "httpMethod": "POST",
            "mimeType": mimetypes.guess_type(filePath)[0],
            "resource": "IMAGE",
        }
    }
    response = client.execute(query, variable_values=variables)
    
    if 'userErrors' in response['stagedUploadsCreate'] and response['stagedUploadsCreate']['userErrors']:
        raise Exception(response['stagedUploadsCreate']['userErrors'])
    
    target = response['stagedUploadsCreate']['stagedTargets'][0]
    form_data = {param['name']: param['value'] for param in target['parameters']}
    files = {'file': (target['parameters'][0]['value'], image)}
    
    upload_response = requests.post(target['url'], data=form_data, files=files)
    upload_response.raise_for_status()
    
    query = gql('''
    mutation fileCreate($files: [FileCreateInput!]!) {
        fileCreate(files: $files) {
            files {
                alt
                createdAt
            }
            userErrors {
                field
                message
            }
        }
    }
    ''')

    variables = {
        "files": [{
            "alt": "Alt text for the Image",
            "contentType": "IMAGE",
            "originalSource": target["resourceUrl"],
        }]
    }
    response = client.execute(query, variable_values=variables)
    
    if 'userErrors' in response['fileCreate'] and response['fileCreate']['userErrors']:
        raise Exception(response['fileCreate']['userErrors'])
    
    query = gql(''' {
        files(first:2, reverse:true) {
            edges {
                node {
                    createdAt
                    updatedAt
                    alt
                    ... on MediaImage {
                        id
                        originalSource{
                            fileSize
                            source: url
                        }
                        image {
                            id
                            originalSrc: url
                            width
                            height
                        }
                    }
                }
            }
        }
    }
    ''')
    time.sleep(1.5)
    response = client.execute(query)
    new_urls = []
    for node in response['files']['edges']:

        url = node["node"]['image']['originalSrc']
        new_urls.append(url)



    print(new_urls)
    return response




if __name__ == '__main__':
    app.run(debug=True)
