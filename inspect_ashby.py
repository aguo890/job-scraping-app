import requests
import json

url = "https://api.ashbyhq.com/posting-api/job-board/linear"
try:
    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = resp.json()
    print("Keys in response:", data.keys())
    if 'jobs' in data:
        print("First job sample:", list(data['jobs'][0].keys()))
    else:
        print("Response might be a list?", isinstance(data, list))
        if isinstance(data, list) and data:
            print("First item keys:", list(data[0].keys()))
except Exception as e:
    print(e)
