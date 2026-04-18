import urllib.request
import json

repos = ["astroq-facereading", "astroq-v2", "AstroQChat", "jules", "lal_kitab_ui", "minimax-rag"]
user = "sachinbadgi"

for repo in repos:
    # Get branches
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{user}/{repo}/branches")
        req.add_header('User-Agent', 'Mozilla/5.0')
        resp = urllib.request.urlopen(req)
        branches = json.loads(resp.read().decode('utf-8'))
        
        for branch in branches:
            branch_name = branch['name']
            
            # Get tree
            tree_url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{branch_name}?recursive=1"
            req2 = urllib.request.Request(tree_url)
            req2.add_header('User-Agent', 'Mozilla/5.0')
            resp2 = urllib.request.urlopen(req2)
            tree_data = json.loads(resp2.read().decode('utf-8'))
            
            for item in tree_data.get('tree', []):
                path = item.get('path', '')
                if path.endswith('.db') or path.endswith('.sqlite'):
                    print(f"FOUND: repo={repo}, branch={branch_name}, path={path}")
                    
    except Exception as e:
        print(f"Error fetching {repo}: {e}")
