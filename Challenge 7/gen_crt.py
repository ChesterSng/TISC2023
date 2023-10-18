import requests
import json
import time

# Function to fetch JSON from a URL
def fetch_json(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch JSON from {url}, Status Code: {response.status_code}")

# Function to upload a local file to a URL
def upload_file(local_file_path, upload_url):
    with open(local_file_path, 'rb') as file:
        response = requests.put(upload_url, data=file)
        if response.status_code != 200:
            raise Exception(f"Failed to upload file to {upload_url}, Status Code: {response.status_code}")

# Function to download a file from a URL
def download_file(url, local_file_path):
    response = requests.get(url)
    if response.status_code == 200:
        with open(local_file_path, 'wb') as file:
            file.write(response.content)
    else:
        raise Exception(f"Failed to download file from {url}, Status Code: {response.status_code}")

if __name__ == "__main__":
    # URL to fetch the initial JSON
    json_url = "https://61lxjmt991.execute-api.ap-southeast-1.amazonaws.com/development/generate"

    # Fetch the JSON
    initial_json = fetch_json(json_url)

    # Extract URLs for csr and crt
    csr_url = initial_json.get("csr")
    crt_url = initial_json.get("crt")

    # Local file path for the client.csr
    local_csr_file = "client.csr"
    
    try:
        # Upload the local CSR file to the csr URL
        upload_file(local_csr_file, csr_url)

        time.sleep(5)
        # Download the CRT file using the crt URL
        download_file(crt_url, 'client.crt')

        print("CSR file uploaded and CRT file downloaded successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
