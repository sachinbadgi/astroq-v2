"""
Parallel Auto-Research Loop
===========================
Dispatches multiple research sessions in parallel using ThreadPoolExecutor.
"""

import os
import sqlite3
import concurrent.futures
from typing import List

from astroq.lk_prediction.agent.research_graph import run_research
from astroq.lk_prediction.data_contracts import LSESolveResult

def run_all_figures():
    print("--- Starting Parallel Auto-Research Loop ---")
    
    # 1. Fetch all unique figures from the database
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    db_path = os.path.join(base_path, "astroq", "lk_prediction", "research_ground_truth.db")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT figure_id FROM public_figure_events")
    figure_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    
    print(f"Found {len(figure_ids)} figures: {figure_ids}")
    
    # 2. Dispatch parallel sessions
    results: List[LSESolveResult] = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(figure_ids)) as executor:
        # Create a future for each figure
        future_to_fig = {executor.submit(run_research, fig_id): fig_id for fig_id in figure_ids}
        
        for future in concurrent.futures.as_completed(future_to_fig):
            fig_id = future_to_fig[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                    hit_rate = res.gap_report['hit_rate'] if res.gap_report else 0
                    fp_count = len(res.gap_report.get('false_positives', [])) if res.gap_report else 0
                    print(f"Result for {fig_id}: Accuracy={hit_rate}, FP Count={fp_count}")
            except Exception as exc:
                print(f"{fig_id} generated an exception: {exc}")
                
    # 3. Summary Report
    print("\n--- Parallel Research Summary (FULL THROTTLE) ---")
    print(f"Total Figures Processed: {len(results)}")
    avg_hit_rate = sum(r.gap_report['hit_rate'] for r in results if r.gap_report) / len(results) if results else 0
    total_fps = sum(len(r.gap_report.get('false_positives', [])) for r in results if r.gap_report)
    avg_fps_per_figure = total_fps / len(results) if results else 0

    for r in results:
        hr = r.gap_report['hit_rate'] if r.gap_report else 0
        fps = len(r.gap_report.get('false_positives', [])) if r.gap_report else 0
        print(f"- {r.chart_dna.figure_id}: HR={hr*100:.1f}%, FP={fps}, Converged={r.converged}")
    
    print("\nAGGREGATE METRICS:")
    print(f"Overall Engine Hit Rate: {avg_hit_rate*100:.1f}%")
    print(f"Average False Positives per Figure: {avg_fps_per_figure:.1f}")

if __name__ == "__main__":
    run_all_figures()
