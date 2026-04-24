import os
import json
import urllib.request
import re
import time

def fetch_html(url):
    req = urllib.request.Request(
        url, 
        data=None, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def get_profile_urls(category_url, limit=100):
    html = fetch_html(category_url)
    # The links are typically inside <div class="mw-category-group">
    # e.g. <a href="/astro-databank/Diana,_Princess_of_Wales" title="Diana, Princess of Wales">Diana, Princess of Wales</a>
    urls = []
    pattern = r'<a href="/astro-databank/([^"]+)" title="[^"]+">'
    matches = re.findall(pattern, html)
    
    for match in matches:
        if ":" not in match and "Main_Page" not in match: # Skip meta pages
            full_url = f"https://www.astro.com/astro-databank/{match}"
            if full_url not in urls:
                urls.append(full_url)
        if len(urls) >= limit:
            break
            
    return urls

def extract_between(html, start_tag, end_tag):
    start_idx = html.find(start_tag)
    if start_idx == -1: return ""
    start_idx += len(start_tag)
    end_idx = html.find(end_tag, start_idx)
    if end_idx == -1: return ""
    return html[start_idx:end_idx].strip()

def parse_profile(url):
    html = fetch_html(url)
    if not html: return None
    
    # Extract Name (from Title)
    # <h1 id="firstHeading" class="firstHeading" lang="en">Diana, Princess of Wales</h1>
    name = extract_between(html, '<h1 id="firstHeading"', '</h1>')
    name = re.sub(r'<[^>]+>', '', name).replace('class="firstHeading" lang="en">', '').strip()
    
    # Extract Born details
    # <tr><th> Born </th><td> 1 July 1961, 19:45 <small>(= 19:45)</small><br/>
    born_row = extract_between(html, '<th> Born </th>', '</tr>')
    if not born_row:
        return None
        
    dob_match = re.search(r'<td>\s*(\d{1,2} [A-Za-z]+ \d{4})', born_row)
    dob = dob_match.group(1) if dob_match else ""
    
    tob_match = re.search(r',\s*(\d{2}:\d{2})', born_row)
    tob = tob_match.group(1) if tob_match else ""
    
    # Extract Place
    place_row = extract_between(html, '<th> Place </th>', '</tr>')
    place = re.sub(r'<[^>]+>', '', place_row).replace('<td>', '').strip()
    # clean up coordinates if present
    place = re.sub(r',\s*\d+n\d+.*$', '', place).strip()
    
    # Parse DOB year to calculate ages
    birth_year_match = re.search(r'\d{4}', dob)
    birth_year = int(birth_year_match.group(0)) if birth_year_match else None
    
    # Extract Events
    events_section = extract_between(html, '<span class="mw-headline" id="Events">Events</span>', '<h2>')
    if not events_section:
        events_section = extract_between(html, '<span class="mw-headline" id="Events">Events</span>', '</div>')
        
    events = []
    # <li> Relationship : Marriage 29 July 1981
    lis = re.findall(r'<li>(.*?)</li>', events_section)
    for li in lis:
        text = re.sub(r'<[^>]+>', '', li).strip()
        # Try to find a year
        year_match = re.search(r'\b(18|19|20)\d{2}\b', text)
        if year_match and birth_year:
            year = int(year_match.group(0))
            age = year - birth_year
            if age > 0 and age < 120:
                domain = "other"
                lower_text = text.lower()
                if "marriage" in lower_text or "wedding" in lower_text or "relationship" in lower_text:
                    domain = "marriage"
                elif "death" in lower_text or "health" in lower_text or "disease" in lower_text or "accident" in lower_text:
                    domain = "health"
                elif "job" in lower_text or "work" in lower_text or "elected" in lower_text or "award" in lower_text or "promotion" in lower_text:
                    domain = "career"
                elif "child" in lower_text or "birth" in lower_text or "son" in lower_text or "daughter" in lower_text:
                    domain = "progeny"
                elif "move" in lower_text or "travel" in lower_text or "home" in lower_text or "buy" in lower_text:
                    domain = "real_estate"
                    
                events.append({
                    "description": text,
                    "year": year,
                    "age": age,
                    "domain": domain
                })
                
    if not dob or not birth_year:
        return None
        
    return {
        "name": name,
        "dob": dob,
        "tob": tob,
        "birth_place": place,
        "events": events
    }

def run_scraper():
    print("=== Astro-Databank Wiki Scraper ===")
    cat_url = "https://www.astro.com/astro-databank/Category:Family_:_Relationship_:_Marriage"
    
    print(f"Fetching URLs from {cat_url}...")
    urls = get_profile_urls(cat_url, 100)
    print(f"Found {len(urls)} profile URLs.")
    
    figures = []
    for i, url in enumerate(urls):
        print(f"[{i+1}/{len(urls)}] Scraping {url.split('/')[-1]}...")
        data = parse_profile(url)
        if data:
            figures.append(data)
        time.sleep(0.5) # Be nice to the server
        
    out_path = os.path.join("backend", "data", "adb_100_figures.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, "w") as f:
        json.dump(figures, f, indent=4)
        
    print(f"\\nSuccessfully scraped {len(figures)} records with {sum(len(f['events']) for f in figures)} total life events.")
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    run_scraper()
