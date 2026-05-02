#!/usr/bin/env python3
"""
enhanced_public_figures_fuzzer.py
==================================
Full confusion-matrix analysis of run_lk_engine.py predictive accuracy.

Produces per-figure and aggregate metrics for:
  - True Positives (TP)  : event year predicted HIT
  - False Negatives (FN) : event year predicted MISS
  - True Negatives (TN)  : noise year correctly predicted MISS
  - False Positives (FP) : noise year incorrectly predicted HIT

Breakdowns per:
  1. Fate category: GRAHA_PHAL (Fixed Fate) vs RASHI_PHAL/HYBRID (Doubtful Fate) per natal
  2. Aspect Strength: mean aspect strength at TP vs FP events

Run from project root:
    cd /Users/sachinbadgi/Documents/lal_kitab/astroq-v2
    python backend/scripts/enhanced_public_figures_fuzzer.py
"""

import os
import sys
import json
from typing import Optional
import sqlite3
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.aspect_engine import AspectEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.natal_fate_view import NatalFateView

# ── Domain mapping (fuzzer key → engine key) ──────────────────────────────────
DOMAIN_MAP = {
    "Career":        "career_travel",
    "Career": "career_travel",
    "Legal":         "career_travel",
    "Business":      "career_travel",
    "Debut":         "career_travel",
    "Success":       "career_travel",
    "Finance":       "finance",
    "Health":        "health",
    "Death":         "health",
    "Marriage":      "marriage",
    "Progeny":       "progeny",
    "Sports":        "career_travel",
    "Award":         "career_travel",
    "Triumph":       "career_travel",
    "Setback":       "career_travel",
    "Relocation":    "career_travel"
}

NOISE_WINDOW = 5  # ±5 years around each event year


# ── Helpers ───────────────────────────────────────────────────────────────────

def _confidence_score(confidence: str) -> int:
    return {"None": 0, "Low": 1, "Medium": 2, "High": 3}.get(confidence, 0)


def _is_hit(score: int) -> bool:
    return score > 1  # Medium or High = hit


def _compute_aspect_strength(chart: dict) -> float:
    """
    Compute mean signed aspect strength across all planets in the chart.
    Uses AspectEngine to replicate the engine's own strength calculation.
    """
    aspect_engine = AspectEngine()
    all_planets = chart.get("planets_in_houses", {})
    total_strength = 0.0
    n = 0
    for planet, data in all_planets.items():
        house = data.get("house")
        if not house:
            continue
        aspects = aspect_engine.calculate_planet_aspects(planet, house, all_planets)
        total_strength += aspect_engine.calculate_total_aspect_strength(aspects)
        n += 1
    return total_strength / n if n else 0.0


def _fate_category(fate_type: str) -> str:
    """Collapse GRAHA_PHAL → 'fixed', everything else → 'doubtful'."""
    if fate_type == "GRAHA_PHAL":
        return "fixed"
    return "doubtful"


# ── Per-figure analysis ───────────────────────────────────────────────────────

def analyse_figure(name: str, natal_chart: dict, annual_charts: dict, events: list, engine, fate_view, config) -> Optional[dict]:
    print(f"\n  → {name}", flush=True)

    if not natal_chart:
        print("     ✗ No natal chart found")
        return None

    # Pre-compute natal fate classification for all domains
    fate_entries = fate_view.evaluate(natal_chart)
    fate_by_domain: dict[str, str] = {e["domain"]: e["fate_type"] for e in fate_entries}

    if not events:
        return None

    rows: list[dict] = []

    # Filter events that have a valid date and calculate age roughly
    valid_events = []
    birth_date = natal_chart.get("birth_time", "")
    try:
        birth_year = int(birth_date[:4])
    except:
        birth_year = 0
        
    for event in events:
        date_str = event.get("date")
        if not date_str or not birth_year: continue
        try:
            event_year = int(date_str[:4])
            age = event_year - birth_year
            if age > 0 and age <= 100:
                event["age"] = age
                valid_events.append(event)
        except:
            continue
            
    if not valid_events:
        return None

    event_ages = {ev.get("age") for ev in valid_events}

    # Determine death age if known — cap all analysis at this year
    death_age = None
    for ev in valid_events:
        if ev.get("type", "").lower() == "death" or "death" in ev.get("event", "").lower():
            death_age = ev.get("age")
            break

    for event in valid_events:
        age  = event.get("age")
        desc = event.get("event", "?")
        domain_raw = event.get("type", "Career")
        engine_domain = DOMAIN_MAP.get(domain_raw, "career_travel")

        annual = annual_charts.get(f"chart_{age}")
        if not annual:
            print(f"     ✗ No annual chart for age {age}")
            continue

        fate_type  = fate_by_domain.get(engine_domain, "RASHI_PHAL")
        fate_cat   = _fate_category(fate_type)

        ctx    = UnifiedAstrologicalContext(chart=annual, natal_chart=natal_chart, config=config)
        result = engine.get_timing_confidence(ctx, engine_domain, fate_type=fate_type, age=age)
        score  = _confidence_score(result["confidence"])
        hit    = _is_hit(score)

        asp_str = _compute_aspect_strength(annual)

        row = {
            "person":        name,
            "age":           age,
            "domain":        engine_domain,
            "domain_raw":    domain_raw,
            "fate_type":     fate_type,
            "fate_cat":      fate_cat,
            "desc":          desc,
            "confidence":    result["confidence"],
            "score":         score,
            "hit":           hit,
            "asp_strength":  asp_str,
            "label":         "TP" if hit else "FN",
            "triggers":      result.get("triggers", []),
        }
        rows.append(row)

        marker = "✓ TP" if hit else "✗ FN"
        print(f"     [{marker}] Age {age:>3}  {engine_domain:<14}  "
              f"{fate_type:<12}  {result['confidence']:<6}  {desc[:50]}")

        # Noise years
        max_noise_age = death_age if death_age else (age + NOISE_WINDOW)
        for n_age in range(max(1, age - NOISE_WINDOW), min(max_noise_age, age + NOISE_WINDOW) + 1):
            if n_age == age or n_age in event_ages:
                continue
            n_chart = annual_charts.get(f"chart_{n_age}")
            if not n_chart:
                continue

            n_ctx    = UnifiedAstrologicalContext(chart=n_chart, natal_chart=natal_chart, config=config)
            n_result = engine.get_timing_confidence(n_ctx, engine_domain, fate_type=fate_type, age=n_age)
            n_score  = _confidence_score(n_result["confidence"])
            n_hit    = _is_hit(n_score)
            n_asp    = _compute_aspect_strength(n_chart)

            noise_row = {
                "person":       name,
                "age":          n_age,
                "domain":       engine_domain,
                "fate_type":    fate_type,
                "fate_cat":     fate_cat,
                "desc":         f"[NOISE near age {age}]",
                "confidence":   n_result["confidence"],
                "score":        n_score,
                "hit":          n_hit,
                "asp_strength": n_asp,
                "label":        "FP" if n_hit else "TN",
                "triggers":     n_result.get("triggers", []),
            }
            rows.append(noise_row)

    return {"name": name, "rows": rows}


# ── Confusion matrix helpers ──────────────────────────────────────────────────

def _confusion_matrix(rows: list[dict]) -> dict:
    tp = sum(1 for r in rows if r["label"] == "TP")
    fn = sum(1 for r in rows if r["label"] == "FN")
    fp = sum(1 for r in rows if r["label"] == "FP")
    tn = sum(1 for r in rows if r["label"] == "TN")
    total = tp + fn + fp + tn
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall    = tp / (tp + fn) if (tp + fn) else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
    return {
        "TP": tp, "FN": fn, "FP": fp, "TN": tn,
        "total": total,
        "precision": precision,
        "recall":    recall,
        "f1":        f1,
        "sensitivity": recall,  # = TPR
        "specificity": tn / (tn + fp) if (tn + fp) else 0,  # TNR
        "fpr":         fp / (fp + tn) if (fp + tn) else 0,
    }


def _mean_asp(rows: list[dict], label: str) -> float:
    vals = [r["asp_strength"] for r in rows if r["label"] == label]
    return sum(vals) / len(vals) if vals else 0.0


def _print_matrix(title: str, m: dict):
    print(f"\n  ┌─ {title}")
    print(f"  │  TP={m['TP']:>4}  FN={m['FN']:>4}  │  Precision : {m['precision']*100:>6.1f}%")
    print(f"  │  FP={m['FP']:>4}  TN={m['TN']:>4}  │  Recall    : {m['recall']*100:>6.1f}%")
    print(f"  │                       │  F1 Score  : {m['f1']*100:>6.1f}%")
    print(f"  │                       │  Specificity: {m['specificity']*100:>6.1f}%")
    print(f"  └───────────────────────┘  FPR        : {m['fpr']*100:>6.1f}%")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 80)
    print("  ENHANCED PUBLIC FIGURES FUZZER — Full Confusion Matrix Analysis")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 80)

    db_path      = os.path.join("backend", "data", "config.db")
    defaults_path= os.path.join("backend", "data", "model_defaults.json")
    pf_db_path   = os.path.join("backend", "data", "public_figures.db")

    config    = ModelConfig(db_path, defaults_path)
    engine    = VarshphalTimingEngine()
    fate_view = NatalFateView()

    conn = sqlite3.connect(pf_db_path)
    cursor = conn.cursor()
    
    # Load figures that have charts generated
    cursor.execute("SELECT id, name, natal_chart_json, annual_charts_json FROM public_figures WHERE natal_chart_json IS NOT NULL")
    figure_rows = cursor.fetchall()
    
    print(f"\n  Loaded {len(figure_rows)} public figures from database.\n")

    all_rows: list[dict] = []
    per_figure: list[dict] = []

    for fid, name, natal_str, annual_str in figure_rows:
        try:
            natal = json.loads(natal_str)
            annuals = json.loads(annual_str)
        except Exception:
            continue
            
        # Get events
        cursor.execute("SELECT event, date, type FROM life_events WHERE figure_id = ?", (fid,))
        event_rows = cursor.fetchall()
        events = [{"event": e[0], "date": e[1], "type": e[2]} for e in event_rows]
        
        result = analyse_figure(name, natal, annuals, events, engine, fate_view, config)
        if result:
            all_rows.extend(result["rows"])
            per_figure.append(result)

    # ── Aggregate confusion matrices ──────────────────────────────────────────
    
    # Save Engine Metrics to Database for HTML Report
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS engine_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT,
        fate_type TEXT,
        tp INTEGER,
        fn INTEGER,
        fp INTEGER,
        tn INTEGER,
        precision REAL,
        recall REAL,
        specificity REAL
    )
    ''')
    cursor.execute("DELETE FROM engine_metrics")
    
    domains = set(r["domain"] for r in all_rows)
    fate_types = set(r["fate_type"] for r in all_rows)
    
    metric_rows = []
    for d in domains:
        for ft in fate_types:
            sub_rows = [r for r in all_rows if r["domain"] == d and r["fate_type"] == ft]
            if not sub_rows: continue
            cm = _confusion_matrix(sub_rows)
            metric_rows.append((d, ft, cm['TP'], cm['FN'], cm['FP'], cm['TN'], cm['precision'], cm['recall'], cm['specificity']))
            
    cursor.executemany("INSERT INTO engine_metrics (domain, fate_type, tp, fn, fp, tn, precision, recall, specificity) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", metric_rows)
    conn.commit()
    conn.close()

    W = 80
    print("\n\n" + "═" * W)
    print("  AGGREGATE CONFUSION MATRIX  (all figures, all domains)")
    print("═" * W)

    all_cm   = _confusion_matrix(all_rows)
    _print_matrix("ALL EVENTS + NOISE", all_cm)

    # Aspect-strength analysis at TP vs FP
    asp_tp = _mean_asp(all_rows, "TP")
    asp_fp = _mean_asp(all_rows, "FP")
    asp_fn = _mean_asp(all_rows, "FN")
    asp_tn = _mean_asp(all_rows, "TN")

    print(f"\n  ASPECT STRENGTH ANALYSIS  (mean signed strength per chart)")
    print(f"  TP mean aspect strength : {asp_tp:>+8.3f}")
    print(f"  FN mean aspect strength : {asp_fn:>+8.3f}")
    print(f"  FP mean aspect strength : {asp_fp:>+8.3f}")
    print(f"  TN mean aspect strength : {asp_tn:>+8.3f}")
    asp_signal = asp_tp - asp_fp
    print(f"  TP vs FP signal delta   : {asp_signal:>+8.3f}  "
          f"({'positive = aspect distinguishes events' if asp_signal > 0 else 'negative = FP have stronger aspects'})")

    # ── Split by fate category ────────────────────────────────────────────────
    print("\n\n" + "═" * W)
    print("  FATE CATEGORY SPLIT")
    print("═" * W)

    for cat in ("fixed", "doubtful"):
        cat_rows = [r for r in all_rows if r["fate_cat"] == cat]
        if not cat_rows:
            continue
        label = "FIXED FATE  (GRAHA_PHAL)" if cat == "fixed" else "DOUBTFUL FATE  (RASHI_PHAL / HYBRID)"
        cm = _confusion_matrix(cat_rows)
        _print_matrix(label, cm)

        asp_tp_c = _mean_asp(cat_rows, "TP")
        asp_fp_c = _mean_asp(cat_rows, "FP")
        delta    = asp_tp_c - asp_fp_c
        print(f"     Aspect strength — TP: {asp_tp_c:>+7.3f}  FP: {asp_fp_c:>+7.3f}  Δ: {delta:>+7.3f}")

    # ── Per-fate-type (fine-grained) ──────────────────────────────────────────
    print("\n\n" + "═" * W)
    print("  PER FATE TYPE  (fine-grained)")
    print("═" * W)

    for ft in ("GRAHA_PHAL", "RASHI_PHAL", "HYBRID"):
        ft_rows = [r for r in all_rows if r["fate_type"] == ft]
        if not ft_rows:
            continue
        cm = _confusion_matrix(ft_rows)
        _print_matrix(ft, cm)
        asp_tp_f = _mean_asp(ft_rows, "TP")
        asp_fp_f = _mean_asp(ft_rows, "FP")
        print(f"     Aspect strength — TP: {asp_tp_f:>+7.3f}  FP: {asp_fp_f:>+7.3f}  Δ: {asp_tp_f - asp_fp_f:>+7.3f}")

    # ── Per-domain breakdown ──────────────────────────────────────────────────
    print("\n\n" + "═" * W)
    print("  PER DOMAIN BREAKDOWN")
    print("═" * W)

    domains = sorted(set(r["domain"] for r in all_rows))
    header_row = f"  {'Domain':<16}  {'TP':>4}  {'FN':>4}  {'FP':>4}  {'TN':>4}  {'Prec':>7}  {'Recall':>7}  {'F1':>7}"
    print(header_row)
    print("  " + "─" * (len(header_row) - 2))

    for dom in domains:
        dom_rows = [r for r in all_rows if r["domain"] == dom]
        cm = _confusion_matrix(dom_rows)
        print(f"  {dom:<16}  {cm['TP']:>4}  {cm['FN']:>4}  {cm['FP']:>4}  {cm['TN']:>4}  "
              f"{cm['precision']*100:>6.1f}%  {cm['recall']*100:>6.1f}%  {cm['f1']*100:>6.1f}%")

    print("\n" + "═" * W)
    print("  ANALYSIS COMPLETE")
    print("═" * W + "\n")

if __name__ == "__main__":
    main()
