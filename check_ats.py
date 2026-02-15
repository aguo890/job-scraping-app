import urllib.request
import sys

candidates = [
    ("Astranis (GH)", "https://boards.greenhouse.io/astranis"),
    ("Varda Space (GH)", "https://boards.greenhouse.io/varda"),
    ("Hadrian Automation (Ashby)", "https://jobs.ashbyhq.com/hadrian-automation"),
    ("Hadrian (Ashby)", "https://jobs.ashbyhq.com/hadrian"),
    
    ("Skydio (GH)", "https://boards.greenhouse.io/skydio"),
    ("Skydio (Lever)", "https://jobs.lever.co/skydio"),
    ("Skydio (Ashby)", "https://jobs.ashbyhq.com/skydio"),
    
    ("Epirus (GH)", "https://boards.greenhouse.io/epirus"),
    ("Epirus (Lever)", "https://jobs.lever.co/epirus"),
    
    ("Helsing (GH)", "https://boards.greenhouse.io/helsing"),
    ("Helsing (Lever)", "https://jobs.lever.co/helsing"),
    
    ("Impulse Space (GH)", "https://boards.greenhouse.io/impulsespace"),
    ("Impulse Space (Lever)", "https://jobs.lever.co/impulsespace"),
    
    ("Radiant (GH)", "https://boards.greenhouse.io/radiant"),
    ("Radiant Industries (GH)", "https://boards.greenhouse.io/radiantindustries"),
    ("Radiant (Lever)", "https://jobs.lever.co/radiant"),
    
    ("Helion Energy (GH)", "https://boards.greenhouse.io/helionenergy"),
    ("Helion (GH)", "https://boards.greenhouse.io/helion"),
    
    ("Firefly Aerospace (GH)", "https://boards.greenhouse.io/fireflyaerospace"),
    ("Firefly (GH)", "https://boards.greenhouse.io/firefly"),
]

print(f"{'Company':<30} | {'Status':<6} | {'URL'}")
print("-" * 80)

for name, url in candidates:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            if status == 200:
                print(f"{name:<30} | {status}  | {url}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
             print(f"{name:<30} | {e.code}  | {url} (Error)")
    except Exception as e:
        pass
