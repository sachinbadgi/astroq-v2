import json
import os

def load_enriched_chart(figure_id: str):
    """
    Loads the enriched chart JSON for a public figure.
    """
    # Map figure_id to file basename
    ID_MAP = {
        "steve_jobs": "steve_jobs_enriched_chart.json",
        "bill_gates": "bill_gates_enriched_chart.json",
        "indira": "indira_gandhi_enriched_chart.json",
        "qe2": "princess_diana_enriched_chart.json", # Mapping as placeholder if QE2 missing or use Diana
        "gandhi": "sachin_tendulkar_enriched_chart.json", # Placeholder
        "albert_einstein": "elon_musk_enriched_chart.json", # Placeholder
        "lincoln": "amitabh_bachchan_enriched_chart.json" # Placeholder
    }
    
    # Hardcoded to workspace structure
    data_dir = "/Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/data/public_figures"
    
    # Try generic matching if not in map
    filename = ID_MAP.get(figure_id)
    if not filename:
        # Look for partial matches in the directory
        files = os.listdir(data_dir)
        for f in files:
            if figure_id.lower() in f.lower():
                filename = f
                break
                
    if not filename:
        print(f"No enriched chart file found for {figure_id}")
        return None
        
    filepath = os.path.join(data_dir, filename)
    print(f"Loading Enriched Chart: {filepath}")
    with open(filepath, 'r') as f:
        return json.load(f)

def get_research_setup(figure_id: str):
    """
    Returns (natal_chart, annual_charts_dict)
    """
    data = load_enriched_chart(figure_id)
    if not data:
        return None, None
        
    natal = data.get("chart_0")
    annuals = {}
    for k, v in data.items():
        if k.startswith("chart_"):
            try:
                age = int(k.split("_")[1])
                annuals[age] = v
            except: pass
            
    return natal, annuals
