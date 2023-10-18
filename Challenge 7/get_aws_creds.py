import requests

# URL to fetch data from
url = "https://13.213.29.24/"
# url = "https://54.255.155.134/"

# Paths to the client certificate (.crt) and private key (.pem) files
cert_file = "client.crt"
key_file = "private_key.pem"

try:
    # Make an HTTP GET request with client certificate and private key
    # response = requests.get(url, cert=(cert_file, key_file), verify=False)
    response = requests.get(url, cert=(cert_file, key_file), verify=False)

    if response.status_code == 200:
        # Assuming the response contains JSON data
        json_data = response.json()
        print("AWS Creds fetched successfully")
        print(f"Access Key: {json_data['Access_Key']}")
        print(f"Secret Key: {json_data['Secret_Key']}")
    else:
        print(response.text)
        print(f"Failed to fetch data, Status Code: {response.status_code}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
