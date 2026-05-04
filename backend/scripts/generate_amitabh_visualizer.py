import json
import os
import sys

def generate_html(timeline, events_list):
    # Sort timeline by age
    timeline.sort(key=lambda x: x['age'])
    
    # Prepare Data
    ages = [t['age'] for t in timeline]
    planets = ["Jupiter", "Sun", "Moon", "Venus", "Mars", "Mercury", "Saturn", "Rahu", "Ketu"]
    
    # FIX #2: Majority-vote fate per planet instead of frozen age-0 snapshot.
    # Old: planet_fates = timeline[0].get('planet_fates', ...) — always age-0 values.
    # New: vote across all 76 ages; most common fate wins.
    from collections import Counter
    planet_fates_by_age = {
        t['age']: t.get('planet_fates', {p: 'RASHI_PHAL' for p in planets})
        for t in timeline
    }
    planet_fates = {}
    for p in planets:
        fates_for_planet = [planet_fates_by_age[t['age']].get(p, 'RASHI_PHAL') for t in timeline]
        planet_fates[p] = Counter(fates_for_planet).most_common(1)[0][0]
    
    # Annual Planet Strengths
    planet_annual = {p: [t['planet_strengths'].get(p, 0.0) for t in timeline] for p in planets}
    
    # Timing-gated strengths (suppressed where LK timing engine blocks the planet)
    planet_timing_gated = {
        p: [t.get('timing_gated_strengths', t['planet_strengths']).get(p, 0.0) for t in timeline]
        for p in planets
    }
    
    # Cumulative Planet Strengths
    planet_cumulative = {p: [t['planet_cumulative_strengths'].get(p, 0.0) for t in timeline] for p in planets}
            
    # Total Strength
    total_annual = [t['total_strength'] for t in timeline]
    total_cumulative = [t['total_strength_cumulative'] for t in timeline]
    
    # FIX #3: Build age->total_strength lookup for event annotation y-anchoring.
    age_to_total_strength = {t['age']: t['total_strength'] for t in timeline}

    # Prepare Events Data for Chart.js Annotations
    event_annotations = {}
    for i, ev in enumerate(events_list):
        age = ev['age']
        event_annotations[f'event_{i}'] = {
            "type": 'line',
            "xMin": age,
            "xMax": age,
            "borderColor": 'rgba(56, 189, 248, 0.4)',
            "borderWidth": 2,
            "borderDash": [6, 4],
            "label": {
                "display": True,
                "content": ev['description'],
                "backgroundColor": 'rgba(15, 23, 42, 0.9)',
                "color": '#38bdf8',
                "font": {"size": 11, "family": 'Outfit', "weight": '600'},
                "position": 'start',
                "yAdjust": -20,
                "padding": 6,
                "borderRadius": 4,
                "borderWidth": 1,
                "borderColor": 'rgba(56, 189, 248, 0.2)'
            }
        }
        # FIX #3: Anchor point yValue to actual total_strength at that age.
        # Old: hardcoded yValue: 60 (cosmetic-only, not data-anchored).
        event_annotations[f'event_point_{i}'] = {
            "type": 'point',
            "xValue": age,
            "yValue": age_to_total_strength.get(age, 0),
            "backgroundColor": '#38bdf8',
            "radius": 4,
            "borderWidth": 2,
            "borderColor": '#fff'
        }

    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AstroQ-v2: Forensic Aukaat Explorer</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0b0f19;
            --card: #161b2a;
            --text: #f8fafc;
            --accent: #38bdf8;
            --fixed: #10b981;
            --doubtful: #f43f5e;
            --sidebar: #1e293b;
            --border: rgba(255,255,255,0.08);
        }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        .sidebar {
            width: 340px;
            background: var(--sidebar);
            padding: 24px;
            overflow-y: auto;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        .main-content {
            flex: 1;
            padding: 32px;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            gap: 24px;
        }
        .card {
            background: var(--card);
            border-radius: 20px;
            padding: 28px;
            box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
            border: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        h1 { font-size: 1.6rem; margin: 0; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        h2 { font-size: 0.85rem; margin: 0; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
        
        .control-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .fate-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.65rem;
            text-transform: uppercase;
        }
        .badge-fixed { background: rgba(16, 185, 129, 0.1); color: var(--fixed); border: 1px solid rgba(16, 185, 129, 0.2); }
        .badge-doubtful { background: rgba(244, 63, 94, 0.1); color: var(--doubtful); border: 1px solid rgba(244, 63, 94, 0.2); }

        .checkbox-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
            border: 1px solid transparent;
        }
        .checkbox-item:hover { background: rgba(255,255,255,0.06); border-color: var(--accent); }
        .checkbox-item input { margin-right: 12px; cursor: pointer; }
        .item-left { display: flex; align-items: center; }
        
        .color-box {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 10px;
        }
        
        .btn-group {
            display: flex;
            gap: 8px;
        }
        button {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            color: #94a3b8;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
            flex: 1;
        }
        button:hover { background: var(--accent); color: #0b0f19; font-weight: 600; }
        
        .chart-container { height: 500px; position: relative; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.02);
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            border: 1px solid var(--border);
        }
        .stat-val { font-size: 1.4rem; font-weight: 600; color: #fff; }
        .stat-label { font-size: 0.75rem; color: #64748b; margin-top: 6px; text-transform: uppercase; }

        .event-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .event-item {
            padding: 10px;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
            font-size: 0.8rem;
            border-left: 2px solid var(--accent);
            cursor: pointer;
            transition: 0.2s;
        }
        .event-item:hover { background: rgba(56, 189, 248, 0.1); }
        .event-age { color: var(--accent); font-weight: 600; margin-right: 8px; }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div>
            <h1>Aukaat Explorer</h1>
            <p style="color: #64748b; font-size: 0.8rem; margin-top: 4px;">Forensic Resilience Engine v2.1</p>
        </div>
        
        <div class="control-section">
            <h2>Global Metrics</h2>
            <label class="checkbox-item">
                <div class="item-left">
                    <input type="checkbox" id="toggle-total-annual" checked onchange="updateChart()">
                    <div class="color-box" style="background: #fff"></div> Total Annual
                </div>
            </label>
            <label class="checkbox-item">
                <div class="item-left">
                    <input type="checkbox" id="toggle-total-cum" onchange="updateChart()">
                    <div class="color-box" style="background: #fbbf24"></div> Total Cumulative
                </div>
            </label>
        </div>

        <div class="control-section">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2>Annual Planets</h2>
                <div class="btn-group">
                    <button onclick="toggleSet('annual', true)">All</button>
                    <button onclick="toggleSet('annual', false)">None</button>
                </div>
            </div>
            
            <div class="fate-header"><div class="badge badge-fixed">Fixed</div> GRAHA PHAL</div>
            <div id="fixed-list-annual"></div>
            
            <div class="fate-header"><div class="badge badge-doubtful">Doubtful</div> RASHI PHAL</div>
            <div id="doubtful-list-annual"></div>
        </div>

        <div class="control-section">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2>Cumulative</h2>
                <div class="btn-group">
                    <button onclick="toggleSet('cum', true)">All</button>
                    <button onclick="toggleSet('cum', false)">None</button>
                </div>
            </div>
            <div id="cum-list"></div>
        </div>

        <div class="control-section">
            <h2>Biographical Events</h2>
            <div class="event-list" id="event-list"></div>
        </div>
    </div>

    <div class="main-content">
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h2 style="margin:0; color: #fff; font-size: 1.2rem;">Biographical Resilience Overlay</h2>
                    <p style="color: #64748b; font-size: 0.9rem; margin-top: 4px;">Subject: Amitabh Bachchan | Lifecycle Evaluation</p>
                </div>
                <div style="text-align: right;">
                    <div class="stat-val" id="hover-age" style="color: var(--accent)">Age: 0</div>
                    <div class="stat-label">Time Cursor</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="mainChart"></canvas>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-val" id="max-strength">0.0</div>
                    <div class="stat-label">Peak Annual Vitality</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val" id="final-cum">0.0</div>
                    <div class="stat-label">Structural Net Worth</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val" id="avg-strength">0.0</div>
                    <div class="stat-label">Avg. Forensic Stability</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ages = """ + json.dumps(ages) + """;
        const planets = """ + json.dumps(planets) + """;
        const planetFates = """ + json.dumps(planet_fates) + """;
        const planetAnnual = """ + json.dumps(planet_annual) + """;
        const planetTimingGated = """ + json.dumps(planet_timing_gated) + """;
        const planetCum = """ + json.dumps(planet_cumulative) + """;
        const totalAnnual = """ + json.dumps(total_annual) + """;
        const totalCum = """ + json.dumps(total_cumulative) + """;
        const annotations = """ + json.dumps(event_annotations) + """;
        const events = """ + json.dumps(events_list) + """;
        
        const colors = [
            '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', 
            '#3b82f6', '#6366f1', '#a855f7', '#ec4899'
        ];

        // Init UI
        const fixedListAnnual = document.getElementById('fixed-list-annual');
        const doubtfulListAnnual = document.getElementById('doubtful-list-annual');
        const cumList = document.getElementById('cum-list');
        const eventListDiv = document.getElementById('event-list');
        
        planets.forEach((p, i) => {
            const color = colors[i % colors.length];
            const fate = planetFates[p];
            
            const aItem = document.createElement('label');
            aItem.className = 'checkbox-item';
            aItem.innerHTML = `<div class="item-left">
                               <input type="checkbox" class="planet-annual-check" data-planet="${p}" onchange="updateChart()">
                               <div class="color-box" style="background: ${color}"></div> ${p}
                               </div>`;
            
            if (fate === 'GRAHA_PHAL') {
                fixedListAnnual.appendChild(aItem);
            } else {
                doubtfulListAnnual.appendChild(aItem);
            }
            
            const cItem = document.createElement('label');
            cItem.className = 'checkbox-item';
            cItem.innerHTML = `<div class="item-left">
                               <input type="checkbox" class="planet-cum-check" data-planet="${p}" onchange="updateChart()">
                               <div class="color-box" style="background: ${color}; border: 1px solid rgba(255,255,255,0.3)"></div> ${p}
                               </div>
                               <div class="badge ${fate === 'GRAHA_PHAL' ? 'badge-fixed' : 'badge-doubtful'}">${fate === 'GRAHA_PHAL' ? 'GP' : 'RP'}</div>`;
            cumList.appendChild(cItem);
        });

        // FIX #6: Real click handler + HIT badge + active_promises display.
        events.forEach(ev => {
            const div = document.createElement('div');
            div.className = 'event-item';
            const hitBadge = ev.baseline_hit
                ? '<span style="color:#10b981;font-size:0.7rem;margin-left:6px;font-weight:700;">✓ HIT</span>'
                : '';
            const promises = (ev.active_promises || []).length > 0
                ? `<div style="color:#64748b;font-size:0.72rem;margin-top:4px;">${ev.active_promises.join(' · ')}</div>`
                : '';
            div.innerHTML = `<span class="event-age">${ev.age}y</span> ${ev.description}${hitBadge}${promises}`;
            div.onclick = () => focusAge(ev.age);
            eventListDiv.appendChild(div);
        });

        const ctx = document.getElementById('mainChart').getContext('2d');
        let chart;

        function updateChart() {
            const datasets = [];
            
            if (document.getElementById('toggle-total-annual').checked) {
                datasets.push({
                    label: 'Total Strength',
                    data: totalAnnual,
                    borderColor: '#fff',
                    borderWidth: 3,
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y'
                });
            }
            if (document.getElementById('toggle-total-cum').checked) {
                datasets.push({
                    label: 'Total Cumulative',
                    data: totalCum,
                    borderColor: '#fbbf24',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0.1,
                    yAxisID: 'y1'
                });
            }
            
            document.querySelectorAll('.planet-annual-check').forEach((cb, i) => {
                if (cb.checked) {
                    const p = cb.dataset.planet;
                    const pIdx = planets.indexOf(p);
                    datasets.push({
                        label: `${p}`,
                        data: planetAnnual[p],
                        borderColor: colors[pIdx % colors.length],
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.4,
                        yAxisID: 'y'
                    });
                }
            });
            
            document.querySelectorAll('.planet-cum-check').forEach((cb, i) => {
                if (cb.checked) {
                    const p = cb.dataset.planet;
                    const pIdx = planets.indexOf(p);
                    datasets.push({
                        label: `${p} (Cum)`,
                        data: planetCum[p],
                        borderColor: colors[pIdx % colors.length],
                        borderWidth: 2,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        tension: 0.1,
                        yAxisID: 'y1'
                    });
                }
            });

            if (chart) chart.destroy();
            
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: ages, datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 0 },
                    interaction: { intersect: false, mode: 'index' },
                    onHover: (e, items) => {
                        if (items.length > 0) {
                            document.getElementById('hover-age').innerText = `Age: ${ages[items[0].index]}`;
                        }
                    },
                    scales: {
                        x: { 
                            grid: { color: 'rgba(255,255,255,0.03)' }, 
                            ticks: { color: '#64748b', font: { family: 'Outfit' } } 
                        },
                        y: { 
                            title: { display: true, text: 'ANNUAL AUKAAT', color: '#64748b' },
                            grid: { color: 'rgba(255,255,255,0.05)' }, 
                            ticks: { color: '#94a3b8' },
                            suggestedMax: 65,
                            suggestedMin: -25
                        },
                        y1: {
                            position: 'right',
                            title: { display: true, text: 'CUMULATIVE LEDGER', color: '#fbbf24' },
                            grid: { display: false },
                            ticks: { color: '#fbbf24' }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        annotation: { 
                            annotations: annotations,
                            clip: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(15, 23, 42, 0.9)',
                            titleFont: { family: 'Outfit', size: 14 },
                            bodyFont: { family: 'Outfit', size: 12 },
                            padding: 12,
                            borderColor: 'rgba(255,255,255,0.1)',
                            borderWidth: 1
                        }
                    }
                }
            });
            
            updateStats();
        }

        function toggleSet(type, state) {
            const selector = type === 'annual' ? '.planet-annual-check' : '.planet-cum-check';
            document.querySelectorAll(selector).forEach(cb => cb.checked = state);
            updateChart();
        }
        
        function updateStats() {
            document.getElementById('max-strength').innerText = Math.max(...totalAnnual).toFixed(1);
            document.getElementById('final-cum').innerText = totalCum[totalCum.length - 1].toFixed(1);
            const avg = totalAnnual.reduce((a, b) => a + b, 0) / totalAnnual.length;
            document.getElementById('avg-strength').innerText = avg.toFixed(1);
        }

        // FIX #6: Navigate chart to age on sidebar event click.
        function focusAge(age) {
            const idx = ages.indexOf(age);
            if (idx === -1 || !chart) return;
            document.getElementById('hover-age').innerText = `Age: ${age}`;
            try {
                chart.tooltip.setActiveElements([{datasetIndex: 0, index: idx}], {x: 0, y: 0});
                chart.update();
            } catch(e) { /* chart may not have dataset 0 visible */ }
        }

        updateChart();
    </script>
</body>
</html>
    """
    return html_template

def main():
    base_path = "/Users/sachinbadgi/Documents/lal_kitab/astroq-v2"
    timeline_path = os.path.join(base_path, "backend/output/amitabh_full_timeline_data.json")
    benchmark_report_path = os.path.join(base_path, "artifacts/reports/doubtful_timing_benchmark_report.json")
    
    if not os.path.exists(timeline_path):
        print(f"Error: {timeline_path} not found")
        return
    
    with open(timeline_path, 'r') as f:
        timeline = json.load(f)
        
    amitabh_events = []
    if os.path.exists(benchmark_report_path):
        with open(benchmark_report_path, 'r') as f:
            benchmark_report = json.load(f)
        amitabh_events = next((f['events'] for f in benchmark_report.get('figures', []) if "Amitabh" in f['name']), [])
        
    html = generate_html(timeline, amitabh_events)
    
    output_path = os.path.join(base_path, "backend/output/amitabh_domain_timeline.html")
    with open(output_path, 'w') as f:
        f.write(html)
        
    print(f"Visualizer generated at: {output_path}")

if __name__ == "__main__":
    main()
