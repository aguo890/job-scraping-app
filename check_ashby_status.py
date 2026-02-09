import requests

def check():
    url = "https://jobs.ashbyhq.com/retool"
    try:
        response = requests.head(url, timeout=10)
        print(f"{url} returned {response.status_code}")
        
        # Also try GET to see if it redirects
        response_get = requests.get(url, timeout=10)
        print(f"GET {url} returned {response_get.status_code}")
        print(f"Final URL: {response_get.url}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
