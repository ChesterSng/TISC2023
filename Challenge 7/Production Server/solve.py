import requests

# URL to fetch data from
# url = "https://13.213.29.24/"
url = "https://54.255.155.134/"

# Paths to the client certificate (.crt) and private key (.pem) files
cert_file = "ca.crt"
key_file = "ca.key"

response = requests.get(url, cert=(cert_file, key_file), verify=False)

if response.status_code == 200:
    json_data = response.text
    print(json_data)
else:
    print(response.text)
    print(f"Failed to fetch data, Status Code: {response.status_code}")

