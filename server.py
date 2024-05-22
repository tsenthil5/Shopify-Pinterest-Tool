from flask import Flask, request, jsonify, render_template
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import os
import mimetypes
import requests
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
    data = request.json
    
    var1 = data.get('n')
    print(var1)
    query = gql(''' {
  files(first: %s, reverse:true) {
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
'''%(var1))
    print(query)
    response = client.execute(query)
    print(response)
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
    
    response = requests.post(target['url'], data=form_data, files=files)
    response.raise_for_status()
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
    data = {'n': '1'}
    target_url = request.url_root + 'images'
    print(target_url)
    response = requests.post(target_url, json=data, headers={'Content-Type': 'application/json'})
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
