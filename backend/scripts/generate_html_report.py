#!/usr/bin/env python3
"""
generate_html_report.py
=======================
Generates a highly-detailed, beautiful HTML report summarizing the 
Lal Kitab pattern analysis stored in public_figures.db.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("backend", "data", "public_figures.db")
OUTPUT_PATH = os.path.join("backend", "data", "pattern_analysis_report.html")

def fetch_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get definitions
    cursor.execute("SELECT id, name, description, category FROM pattern_definitions")
    defs = {row[0]: {"name": row[1], "desc": row[2], "category": row[3]} for row in cursor.fetchall()}
    
    # Analyze Natal Charts
    import json
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), "backend"))
    from astroq.lk_prediction.natal_fate_view import NatalFateView
    
    cursor.execute("SELECT natal_chart_json FROM public_figures WHERE natal_chart_json IS NOT NULL")
    natal_rows = cursor.fetchall()
    
    fate_view = NatalFateView()
    fate_distribution = {}
    
    for row in natal_rows:
        try:
            chart = json.loads(row[0])
            entries = fate_view.evaluate(chart)
            for e in entries:
                domain = e["domain"]
                # Remap NatalFateView domains to engine metrics domains
                if domain == "career": domain = "career_travel"
                if domain == "wealth": domain = "finance"
                
                fate = e["fate_type"]
                # Only track major core domains
                if domain not in ["career_travel", "finance", "health", "marriage", "progeny"]:
                    continue
                if domain not in fate_distribution:
                    fate_distribution[domain] = {"GRAHA_PHAL": 0, "RASHI_PHAL": 0, "HYBRID": 0, "NEITHER": 0}
                fate_distribution[domain][fate] += 1
        except Exception:
            pass
    
    # Get aggregate metrics by domain, fate_type and pattern
    cursor.execute("""
        SELECT domain, fate_type, pattern_id, 
               COUNT(*) as total_occurrences,
               SUM(CASE WHEN is_event = 1 THEN 1 ELSE 0 END) as tp_events,
               SUM(CASE WHEN is_event = 0 THEN 1 ELSE 0 END) as fp_noise
        FROM raw_pattern_occurrences
        GROUP BY domain, fate_type, pattern_id
    """)
    domain_metrics = {}
    for row in cursor.fetchall():
        d, ft, pid, tot, tp, fp = row
        if d not in domain_metrics:
            domain_metrics[d] = {}
        if ft not in domain_metrics[d]:
            domain_metrics[d][ft] = {}
        domain_metrics[d][ft][pid] = {"total": tot, "tp": tp, "fp": fp}
    
    # Get top 3 examples for each pattern
    examples = {}
    for pid in defs.keys():
        cursor.execute("""
            SELECT p.name, r.age, r.domain, r.source_planet, r.target_planet
            FROM raw_pattern_occurrences r
            JOIN public_figures p ON r.figure_id = p.id
            WHERE r.pattern_id = ? AND r.is_event = 1
            LIMIT 5
        """, (pid,))
        examples[pid] = cursor.fetchall()
        
    cursor.execute("SELECT domain, fate_type, tp, fn, fp, tn, precision, recall, specificity FROM engine_metrics")
    engine_metrics_db = {}
    for row in cursor.fetchall():
        d, ft, tp, fn, fp, tn, prec, rec, spec = row
        if d not in engine_metrics_db:
            engine_metrics_db[d] = {}
        engine_metrics_db[d][ft] = {
            "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "prec": prec, "rec": rec, "spec": spec
        }
    
    conn.close()
    
    return defs, domain_metrics, examples, fate_distribution, engine_metrics_db

def generate_html():
    defs, domain_metrics, examples, fate_distribution, engine_metrics_db = fetch_data()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lal Kitab Pattern Analysis</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Outfit:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.4);
            --success: #10b981;
        }}
        
        .metric-excellent {{ color: #10b981; font-weight: 800; text-shadow: 0 0 8px rgba(16,185,129,0.3); }}
        .metric-good {{ color: #34d399; font-weight: 600; }}
        .metric-avg {{ color: #fbbf24; font-weight: 600; }}
        .metric-bad {{ color: #f87171; font-weight: 600; }}
        .metric-neutral {{ color: #cbd5e1; font-weight: 600; }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background: radial-gradient(circle at top left, #1e293b, var(--bg-color));
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 3.5rem;
            text-align: center;
            margin-bottom: 10px;
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px var(--accent-glow);
        }}
        
        .subtitle {{
            text-align: center;
            color: var(--text-muted);
            margin-bottom: 50px;
            font-size: 1.2rem;
            font-weight: 300;
        }}
        
        .category-header {{
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            padding-bottom: 10px;
            margin-top: 60px;
            margin-bottom: 30px;
            color: #e2e8f0;
        }}
        
        .fate-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 50px;
        }}
        
        .fate-card {{
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }}
        
        .fate-domain {{
        .fate-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-size: 0.85rem;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        .fate-table th, .fate-table td {{
            padding: 10px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        .fate-table th {{
            background: rgba(0, 0, 0, 0.2);
            font-weight: 600;
            color: var(--accent);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 1px;
        }}
        
        .fate-table tr:hover td {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .domain-rowgroup td {{
            border-top: 2px solid rgba(56, 189, 248, 0.3);
        }}
        
        .domain-cell {{
            font-weight: 600;
            color: #fff;
            text-transform: capitalize;
            background: rgba(255, 255, 255, 0.02);
            vertical-align: top;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }}
        
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px var(--accent-glow);
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        
        .pattern-name {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.4rem;
            color: var(--accent);
            margin-top: 0;
            margin-bottom: 10px;
        }}
        
        .pattern-desc {{
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 20px;
            min-height: 65px;
        }}
        
        .stats {{
            display: flex;
            justify-content: space-between;
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        .stat-box {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 800;
            color: #fff;
        }}
        
        .stat-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }}
        
        .precision {{
            color: var(--success);
        }}
        
        .examples-title {{
            font-size: 0.85rem;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            border-bottom: 1px solid rgba(56, 189, 248, 0.2);
            padding-bottom: 5px;
        }}
        
        .example-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 0.85rem;
        }}
        
        .example-item {{
            padding: 6px 0;
            border-bottom: 1px dashed rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
        }}
        
        .example-item:last-child {{
            border-bottom: none;
        }}
        
        .ex-name {{ font-weight: 600; }}
        .ex-detail {{ color: var(--text-muted); font-size: 0.8rem; }}

    </style>
</head>
<body>
    <div class="container">
        <h1>AstroQ Lal Kitab Analytics</h1>
        <div class="subtitle">Empirical validation of 100,000+ geometric patterns over 488 historical lifecycles.<br>Generated {datetime.now().strftime('%Y-%m-%d')}</div>
"""
    
    html += '<h2 class="category-header">Natal Fate Distribution & Timing Accuracy</h2>\n'
    html += '<div style="overflow-x: auto;">\n<table class="fate-table">\n'
    html += '<thead><tr><th>Domain</th><th>Fate Type</th><th>Natal Chart Count</th><th>Event Hits</th><th>Missed Events</th><th>Noise Triggers</th><th>Silence on Noise</th><th>Recall (Sensitivity)</th><th>Specificity</th></tr></thead>\n<tbody>\n'
    
    for domain, counts in fate_distribution.items():
        total = sum(counts.values())
        if total == 0: continue
        
        # Calculate how many fate types we have for rowspan
        fate_types_present = [ft for ft in ["GRAHA_PHAL", "RASHI_PHAL", "HYBRID"] if counts.get(ft, 0) > 0]
        rowspan = len(fate_types_present)
        
        if rowspan == 0: continue
        
        first_row = True
        
        for fate_type in fate_types_present:
            count = counts.get(fate_type, 0)
            percent = (count / total * 100)
            fate_label = "Fixed (Graha)" if fate_type == "GRAHA_PHAL" else "Doubtful (Rashi)" if fate_type == "RASHI_PHAL" else "Hybrid"
            
            # Fetch Engine Metrics
            em = engine_metrics_db.get(domain, {}).get(fate_type, {})
            
            if em:
                tp, fn, fp, tn = em.get('tp',0), em.get('fn',0), em.get('fp',0), em.get('tn',0)
                rec_val = em.get('rec', 0) * 100
                spec_val = em.get('spec', 0) * 100
                
                rec_cls = "metric-excellent" if rec_val >= 50 else "metric-good" if rec_val >= 25 else "metric-avg" if rec_val >= 10 else "metric-bad"
                spec_cls = "metric-excellent" if spec_val >= 95 else "metric-good" if spec_val >= 85 else "metric-avg" if spec_val >= 70 else "metric-bad"
                
                rec = f"{rec_val:.1f}%"
                spec = f"{spec_val:.1f}%"
            else:
                tp, fn, fp, tn = "-", "-", "-", "-"
                rec, spec = "-", "-"
                rec_cls = "metric-neutral"
                spec_cls = "metric-neutral"
                
            row_class = "domain-rowgroup" if first_row else ""
            html += f'<tr class="{row_class}">'
            if first_row:
                html += f'<td rowspan="{rowspan}" class="domain-cell">{domain.replace("_", " ")}</td>'
                first_row = False
                
            html += f"""
                <td>{fate_label}</td>
                <td>{count} ({percent:.1f}%)</td>
                <td style="color: var(--success);">{tp}</td>
                <td style="color: #cbd5e1;">{fn}</td>
                <td style="color: #cbd5e1;">{fp}</td>
                <td style="color: var(--success);">{tn}</td>
                <td class="{rec_cls}">{rec}</td>
                <td class="{spec_cls}">{spec}</td>
            </tr>
            """
    html += '</tbody>\n</table>\n</div>\n'

    # Calculate exact total events and noise evaluated per domain from engine_metrics_db
    domain_event_totals = {}
    domain_noise_totals = {}
    for dom in ["career_travel", "finance", "health", "marriage", "progeny"]:
        tot_ev = sum(em.get('tp',0) + em.get('fn',0) for em in engine_metrics_db.get(dom, {}).values())
        tot_noise = sum(em.get('fp',0) + em.get('tn',0) for em in engine_metrics_db.get(dom, {}).values())
        domain_event_totals[dom] = tot_ev
        domain_noise_totals[dom] = tot_noise

    html += '<h2 class="category-header">Pattern Signatures by Domain & Fate</h2>\n'
    html += '<div style="overflow-x: auto;">\n<table class="fate-table">\n'
    html += '<thead><tr><th>Domain</th><th>Fate Type</th><th>Pattern Signature</th><th>Rule Description</th><th>Event Hits</th><th>Noise Triggers</th><th>Precision</th><th>Specificity</th></tr></thead>\n<tbody>\n'

    for domain in sorted(domain_metrics.keys()):
        # Calculate total rows for this domain across all fate types
        domain_rowspan = sum(len(pids) for pids in domain_metrics[domain].values())
        if domain_rowspan == 0: continue
        
        domain_first_row = True
        
        for fate_type in sorted(domain_metrics[domain].keys()):
            pids = list(domain_metrics[domain][fate_type].keys())
            if not pids: continue
            fate_rowspan = len(pids)
            
            fate_label = "Fixed (Graha)" if fate_type == "GRAHA_PHAL" else "Doubtful (Rashi)" if fate_type == "RASHI_PHAL" else "Hybrid"
            
            # Fetch domain and fate specific totals from engine metrics
            em = engine_metrics_db.get(domain, {}).get(fate_type, {})
            tot_ev = em.get('tp',0) + em.get('fn',0)
            if tot_ev == 0: tot_ev = 1
            tot_noise = em.get('fp',0) + em.get('tn',0)
            if tot_noise == 0: tot_noise = 1
            
            fate_first_row = True
            
            for pid in pids:
                d = defs.get(pid, {"name": pid, "desc": ""})
                m = domain_metrics[domain][fate_type][pid]
                tp = m["tp"]
                fp = m["fp"]
                tn = max(0, tot_noise - fp)
                
                # Precision: when this pattern fires, what % are real events? (bounded 0-100%)
                pattern_total = tp + fp
                prec_val = (tp / pattern_total * 100) if pattern_total > 0 else 0.0
                tnr_val = (tn / tot_noise * 100)
                prec_cls = "metric-excellent" if prec_val >= 50 else "metric-good" if prec_val >= 25 else "metric-avg" if prec_val >= 10 else "metric-bad"
                spec_cls = "metric-excellent" if tnr_val >= 95 else "metric-good" if tnr_val >= 85 else "metric-avg" if tnr_val >= 70 else "metric-bad"
                
                row_class = "domain-rowgroup" if domain_first_row else ""
                html += f'<tr class="{row_class}">'
                
                if domain_first_row:
                    html += f'<td rowspan="{domain_rowspan}" class="domain-cell">{domain.replace("_", " ")}</td>'
                    domain_first_row = False
                    
                if fate_first_row:
                    html += f'<td rowspan="{fate_rowspan}" style="vertical-align: top; color: var(--text-main); font-weight: 500; border-right: 1px solid rgba(255,255,255,0.05);">{fate_label}</td>'
                    fate_first_row = False
                    
                html += f"""
                    <td>{d.get('name', pid)}</td>
                    <td style="color: var(--text-muted); font-size: 0.75rem; max-width: 300px;">{d.get('desc', '')}</td>
                    <td style="color: var(--success);">{tp:,}</td>
                    <td style="color: var(--warning);">{fp:,}</td>
                    <td class="{prec_cls}">{prec_val:.1f}%</td>
                    <td class="{spec_cls}">{tnr_val:.1f}%</td>
                </tr>
                """
            
    html += '</tbody>\n</table>\n</div>\n'

    html += """
    </div>
</body>
</html>
"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"HTML Report generated at {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_html()
