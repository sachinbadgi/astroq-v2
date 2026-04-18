
import os
import sys
import sqlite3
import json
from dataclasses import replace

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.agent.research_graph import run_research
from astroq.lk_prediction.lse_validator import ValidatorAgent, normalize_domain
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.agent.chart_loader import get_research_setup

def get_top_3_for_event(predictions, event):
    domain = normalize_domain(event.get("domain", ""))
    actual_age = event.get("age", 0)
    
    # Matching logic from ValidatorAgent
    p_list = []
    for p in predictions:
        p_domain = normalize_domain(p.domain)
        if domain in p_domain or p_domain in domain:
            p_list.append(p)
    
    DOMAIN_KARAKAS = {
        "marriage": ["Venus", "Jupiter", "Moon"],
        "career": ["Sun", "Saturn", "Mars", "Mercury"],
        "profession": ["Sun", "Saturn", "Mars", "Mercury"],
        "wealth": ["Jupiter", "Venus", "Moon"],
        "health": ["Sun", "Mars", "Saturn"]
    }

    def get_rank_tuple(p):
        purity_bonus = 1.0
        domain_lower = domain.lower()
        p_domain_lower = p.domain.lower()
        if domain_lower in p_domain_lower:
            if p_domain_lower.startswith(domain_lower):
                purity_bonus *= 1.0
            else:
                purity_bonus *= 0.5
        else:
            purity_bonus *= 0.1
        
        karakas = DOMAIN_KARAKAS.get(domain_lower, [])
        planet_name = p.source_planets[0] if p.source_planets else ""
        if karakas and planet_name.capitalize() in karakas:
            purity_bonus *= 1.2
        
        return (round(p.probability * purity_bonus, 4), round(p.magnitude * purity_bonus, 4))

    ranked = sorted(p_list, key=get_rank_tuple, reverse=True)
    
    top_ages = []
    for r in ranked:
        if r.peak_age not in top_ages:
            top_ages.append(r.peak_age)
        if len(top_ages) >= 3:
            break
            
    is_top3_hit = False
    for tage in top_ages:
        if abs(tage - actual_age) <= 1:
            is_top3_hit = True
            break
            
    return top_ages, is_top3_hit

def generate_report(figure_ids):
    print("# FORENSIC REPORT: PHYSICS ENGINE VS GROUND TRUTH")
    print("Aggregate metrics show high convergence. Localized domain analysis follows.\n")
    
    for fig_id in figure_ids:
        print(f"## Subject: {fig_id.replace('_', ' ').title()}")
        
        # 1. Run Research to get the converged DNA
        res = run_research(fig_id)
        if not res:
            print(f"Skipping {fig_id}: No data.")
            continue
            
        dna = res.chart_dna
        
        # 2. Re-run Pipeline with final DNA to get the exact predictions
        natal_chart, annual_charts = get_research_setup(fig_id)
        base_path = os.getcwd()
        db_path = os.path.join(base_path, "backend", f"mock_{fig_id}.db")
        defaults_path = os.path.join(base_path, "backend", "astroq", "lk_prediction", "data", "model_defaults.json")
        
        cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
        orchestrator = LSEOrchestrator(cfg)
        
        # Apply DNA overrides
        if dna.config_overrides:
            for k, v in dna.config_overrides.items():
                cfg.set_override(k, v, source="report_gen")
                
        predictions = orchestrator._run_pipeline(natal_chart, annual_charts, fig_id)
        
        # Apply DNA Delays
        adjusted_predictions = []
        for p in predictions:
            p_adj = replace(p)
            for planet in p_adj.source_planets:
                for k, v in dna.delay_constants.items():
                    if planet.lower() in k.lower():
                        p_adj.peak_age += float(v)
                        break
            adjusted_predictions.append(p_adj)

        # 3. Print the Table
        print("| Domain/Sub-domain | Event Description | Actual Age | Top 3 Age Matches | Hit? |")
        print("| :--- | :--- | :--- | :--- | :--- |")
        
        for event in res.gap_report['entries']:
            le = event['life_event']
            top_ages, is_top3_hit = get_top_3_for_event(adjusted_predictions, le)
            
            top_ages_str = ", ".join([f"{a:.1f}" for a in top_ages])
            hit_str = "✅" if is_top3_hit else "❌"
            
            print(f"| {le['domain']} | {le['description']} | {le['age']} | {top_ages_str} | {hit_str} |")
        
        print(f"\n**Summary for {fig_id}:** Top-3 Hit Rate: {res.gap_report.get('top_3_hit_rate', 0.0)*100:.1f}%\n")

if __name__ == "__main__":
    generate_report(['narendra_modi', 'elon_musk', 'amitabh_bachchan'])
