import urllib.request
import json
repo = "astroq-facereading"
user = "sachinbadgi"
try:
    req = urllib.request.Request(f"https://api.github.com/repos/{user}/{repo}/branches")
    req.add_header('User-Agent', 'Mozilla/5.0')
    resp = urllib.request.urlopen(req)
    branches = json.loads(resp.read().decode('utf-8'))
    for branch in branches:
        print(f"Branch: {branch['name']}")
except Exception as e:
    print(f"Error: {e}")
