import requests
import json

# {"a":[0,0,8,0,8,0,8,0,8,0,8,0,0,56,0,0,4,0,4,240,0,0,0,0,0,0,0,0,128,0,128,0],"b":"14304965105721980115","c":"11223910293330938400","d":2074871048}

url = "http://rubg.chals.tisc23.ctf.sg:34567/solve"
headers = {
    "Host": "rubg.chals.tisc23.ctf.sg:34567",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-GB",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) rubg/1.0.0 Chrome/112.0.5615.204 Electron/24.4.0 Safari/537.36"
}

req = requests.post(url, headers=headers, data=json.dumps({
    "a": "08181e287375767b7ca8afbfc0c2e8ef",
    "b": 2074871048
}))



