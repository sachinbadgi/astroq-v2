import json
import os
import sys

# Ensure we can import from backend
base_path = "/Users/sachinbadgi/Documents/lal_kitab/astroq-v2"
sys.path.append(os.path.join(base_path, "backend"))

from astroq.lk_prediction.engine_runner import LKEngineRunner
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.state_ledger import StateLedger
from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.lk_constants import KARAKA_DOMAIN_MAP

def generate_optimized_timeline(name, dob, tob, place):
    db_path = os.path.join(base_path, "backend/data/rules.db")
    cfg_file = os.path.join(base_path, "backend/data/model_defaults.json")
    runner = LKEngineRunner(db_path, cfg_file)
    
    # 1. Build Natal Chart
    natal, _ = runner.build_chart(dob, tob, place)
    
    # 2. Run Forensic Lifecycle ONCE
    print("Running Forensic Lifecycle (75 years)...")
    lifecycle = LifecycleEngine()
    history = lifecycle.run_75yr_analysis(natal)
    
    # 3. Setup Pipeline & Strength Engine
    from astroq.lk_prediction.config import ModelConfig
    cfg = ModelConfig(db_path, cfg_file)
    
    pipe = runner.build_pipeline()
    pipe.load_natal_baseline(natal)
    
    from astroq.lk_prediction.strength_engine import StrengthEngine
    strength_engine = StrengthEngine(cfg)
    timing_engine = VarshphalTimingEngine()
    
    domains_to_track = ["career_travel", "health", "marriage", "finance"]
    planets = ["Jupiter", "Sun", "Moon", "Venus", "Mars", "Mercury", "Saturn", "Rahu", "Ketu"]
    timeline = []
    
    cumulative_totals = {p: 0.0 for p in planets}
    total_strength_cum = 0.0

    for age in range(0, 76):
        if age % 10 == 0: print(f"  Evaluating Age {age}...")
        
        # Project chart for this age
        positions = lifecycle._get_annual_positions(lifecycle._extract_positions(natal), age)
        annual_chart = {
            "chart_type": "Yearly",
            "chart_period": age,
            "planets_in_houses": {p: {"house": h} for p, h in positions.items()}
        }
        
        # Get ledger for this age
        # FIX #1: Use lifecycle history at ALL ages (including age 0).
        # Lifecycle engine starts at age=1 (range(1,76)), so age 0 uses age=1 as
        # the natal proxy — closer to birth state than a blank StateLedger.
        ledger = history.get(age) or history.get(1, StateLedger())
        
        # Use the strength engine to get 'Aukaat' for each year
        # Pass the ledger to honor scapegoat exhaustion and negative debt
        strengths_payload = strength_engine.calculate_chart_strengths(annual_chart, natal, ledger=ledger)
        planet_strengths = {}
        planet_cum_strengths = {}
        planet_fates = {}
        total_strength = 0.0
        for p in planets:
            s_data = strengths_payload.get(p, {})
            val = s_data.get("strength_total", 0.0)
            planet_strengths[p] = round(val, 2)
            planet_fates[p] = s_data.get("fate_type", "RASHI_PHAL")
            
            cumulative_totals[p] += val
            planet_cum_strengths[p] = round(cumulative_totals[p], 2)
            total_strength += val
        
        total_strength_cum += total_strength
        
        # Generate predictions with this ledger
        preds, ctx = pipe.generate_predictions(annual_chart, focus_domains=domains_to_track)
        
        # Extract stats
        avg_efficiency = sum(ledger.get_leakage_multiplier(p) for p in ledger.planets) / len(ledger.planets) if ledger.planets else 1.0
        friction = 1.0 - avg_efficiency
        total_trauma = sum(s.trauma_points for s in ledger.planets.values())
        awakened_count = sum(1 for p_name, st in ledger.planets.items() if st.is_awake)
        momentum = awakened_count / len(ledger.planets) if ledger.planets else 0.0
        
        # FIX #4: Accumulate domain scores across ALL predictions (LK convergence).
        # Old code: if score > domain_scores[dom] → only kept max, lost multi-planet signals.
        domain_scores = {d: 0.0 for d in domains_to_track}
        domain_confidence = {d: "None" for d in domains_to_track}
        domain_hit_count = {d: 0 for d in domains_to_track}
        conf_rank = {"High": 3, "Medium": 2, "Low": 1, "None": 0}
        
        for p in preds:
            dom = p.domain.lower()
            if dom in domains_to_track:
                conf_map = {"High": 1.0, "Medium": 0.7, "Low": 0.3, "None": 0.0}
                conf_score = conf_map.get(p.timing_confidence, 0.0)
                score = p.magnitude * conf_score
                # Accumulate ALL signal contributions
                domain_scores[dom] += score
                domain_hit_count[dom] += 1
                # Promote confidence to highest seen
                if conf_rank.get(p.timing_confidence, 0) > conf_rank.get(domain_confidence[dom], 0):
                    domain_confidence[dom] = p.timing_confidence
        
        # FIX #5: Timing-gate overlay — visually suppress planets blocked by LK timing rules.
        # Raw strength_total is preserved; gated value is a separate forensic signal.
        timing_gated_strengths = {}
        for p in planets:
            raw_val = planet_strengths[p]
            primary_domains = KARAKA_DOMAIN_MAP.get(p, [])
            fate_type = planet_fates.get(p, "RASHI_PHAL")
            gated_val = raw_val
            for domain in primary_domains[:1]:  # check first primary domain only
                try:
                    result = timing_engine.get_timing_confidence(
                        context=ctx, domain=domain, fate_type=fate_type, age=age
                    )
                    if result.get("confidence") == "Low":
                        gated_val = raw_val * 0.3  # timing gate suppresses this planet
                except Exception:
                    pass
            timing_gated_strengths[p] = round(gated_val, 2)
        
        timeline.append({
            "age": age,
            "friction": round(friction, 3),
            "momentum": round(momentum, 3),
            "trauma": round(total_trauma, 2),
            "planet_strengths": planet_strengths,
            "planet_cumulative_strengths": planet_cum_strengths,
            "planet_fates": planet_fates,
            "timing_gated_strengths": timing_gated_strengths,
            "total_strength": round(total_strength, 2),
            "total_strength_cumulative": round(total_strength_cum, 2),
            "domain_scores": domain_scores,
            "domain_confidence": domain_confidence,
            "domain_hit_count": domain_hit_count,
        })
        
    return timeline

if __name__ == "__main__":
    name = "Amitabh Bachchan"
    dob = "1942-10-11"
    tob = "16:00"
    place = "Allahabad, India"
    
    timeline = generate_optimized_timeline(name, dob, tob, place)
    
    output_path = os.path.join(base_path, "backend/output/amitabh_full_timeline_data.json")
    with open(output_path, 'w') as f:
        json.dump(timeline, f, indent=2)
    
    print(f"Optimized timeline data saved to: {output_path}")
