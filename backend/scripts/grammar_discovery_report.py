"""
Python Grammar Discovery Report.

Audits the hardcoded Lal Kitab logic tags (Mangal Badh, Masnui, Kaayam, etc.)
to verify they are being triggered correctly in real-sky charts.
"""

import sys
import os
from collections import defaultdict

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.config import ModelConfig
from scripts.auto_research_fuzzer import get_random_dob, get_random_tob

DB_PATH = "backend/data/rules.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"

def run_grammar_audit(iterations=10):
    print(f"=== Auditing Python Grammar Logic ({iterations} natives) ===")
    
    cfg = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    generator = ChartGenerator()
    grammar = GrammarAnalyser(cfg)
    strength = StrengthEngine(cfg)
    
    stats = defaultdict(int)
    examples = {} # Tag -> Example condition text
    
    for i in range(1, iterations + 1):
        dob = get_random_dob()
        tob = get_random_tob()
        system = "kp" if i % 2 == 0 else "vedic"
        
        payload = generator.build_full_chart_payload(
            dob_str=dob, tob_str=tob, place_name="New Delhi",
            latitude=28.6139, longitude=77.2090, utc_string="+05:30",
            chart_system=system
        )
        
        for k, v in payload.items():
            if not k.startswith("chart_"): continue
            
            # 1. Enrichment
            enriched = strength.calculate_chart_strengths(v)
            grammar.apply_grammar_rules(v, enriched)
            
            # 2. Audit Tags in Chart
            if v.get("mangal_badh_status") == "Active":
                stats["Mangal Badh (Active)"] += 1
                if "Mangal Badh (Active)" not in examples:
                    examples["Mangal Badh (Active)"] = f"Sun+Saturn link found in H{v.get('planets_in_houses', {}).get('Sun', {}).get('house')}"
            
            if v.get("dharmi_kundli_status") == "Dharmi Teva":
                stats["Dharmi Kundli (Lucky)"] += 1
                if "Dharmi Kundli (Lucky)" not in examples:
                    examples["Dharmi Kundli (Lucky)"] = f"Jupiter in H4 or Saturn in H11 found."
            
            # Audit Tags in Enriched Planets
            for planet, ep in enriched.items():
                if ep.get("kaayam_status") == "Kaayam":
                    stats["Kaayam (Stable)"] += 1
                    if "Kaayam (Stable)" not in examples:
                        h = ep.get('house')
                        examples["Kaayam (Stable)"] = f"{planet} in H{h} (Pakka Ghar) without enemies."
                
                if ep.get("is_masnui"):
                    stats["Masnui (Artificial)"] += 1
                    if "Masnui (Artificial)" not in examples:
                        examples["Masnui (Artificial)"] = f"{planet} formed via conjunction."
                
                if ep.get("bilmukabil_hostile_to"):
                    stats["BilMukabil (Hostility)"] += 1
                    if "BilMukabil (Hostility)" not in examples:
                        hostile = ep["bilmukabil_hostile_to"]
                        examples["BilMukabil (Hostility)"] = f"{planet} finds {hostile} hostile via 3-step logic."
                
                if ep.get("sleeping_status") == "Sleeping Planet":
                    stats["Sleeping Planet"] += 1
                    if "Sleeping Planet" not in examples:
                        examples["Sleeping Planet"] = f"{planet} in H{ep.get('house')} has no aspect support."
                
                if ep.get("achanak_chot_active"):
                    stats["Achanak Chot (Triggered)"] += 1

    print("\n--- PYTHON GRAMMAR AUDIT RESULTS ---")
    print(f"Total Charts Analyzed: {iterations * 76}")
    
    for tag, count in stats.items():
        ex = examples.get(tag, "")
        print(f"  - {tag:25}: {count:5} occurrences. Example: {ex}")

if __name__ == "__main__":
    # Increased iterations for grammar discovery
    run_grammar_audit(20)
