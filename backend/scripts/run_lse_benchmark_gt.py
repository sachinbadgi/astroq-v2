import sqlite3
import json
import os
import argparse
import logging
import re
import sys
from typing import List, Dict, Any

# Ensure backend is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from astroq.lk_prediction.chart_generator import ChartGenerator
from astroq.lk_prediction.lse_orchestrator import LSEOrchestrator
from astroq.lk_prediction.lse_chart_dna import ChartDNARepository
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.data_contracts import LifeEventLog, ChartData

# Configuration
DB_PATH = "backend/data/astroq_gt.db"
DEFAULTS_PATH = "backend/data/model_defaults.json"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("lse_benchmark_gt")

import astroq
logger.info(f"Using astroq from: {astroq.__file__}")

def normalize_name(name: str) -> str:
    """Normalize name for linking tables (remove dots, extra spaces, lowercase)."""
    return re.sub(r'[^a-zA-Z0-0]', '', name.lower())

def fetch_figures_and_events(db_path: str):
    """Fetch figures from lk_birth_charts and events from benchmark_ground_truth."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all birth charts
    cursor.execute("SELECT id, client_name, birth_date, birth_time, birth_place, latitude, longitude, timezone_name FROM lk_birth_charts")
    birth_charts_raw = cursor.fetchall()

    # Get all events
    cursor.execute("SELECT figure_name, event_name, age, domain, event_date FROM benchmark_ground_truth")
    events_raw = cursor.fetchall()
    
    conn.close()

    # Organize events by normalized name
    events_by_figure = {}
    for fig_name, event_name, age, domain, event_date in events_raw:
        norm_name = normalize_name(fig_name)
        if norm_name not in events_by_figure:
            events_by_figure[norm_name] = []
        
        events_by_figure[norm_name].append({
            "age": age,
            "domain": domain.lower() if domain else "career",
            "description": event_name,
            "is_verified": True # Ground truth is considered verified
        })

    # Link birth charts with events
    figures_to_process = []
    for bc in birth_charts_raw:
        bc_id, name, dob, tob, place, lat, lon, tz = bc
        norm_name = normalize_name(name)
        
        if norm_name in events_by_figure:
            figures_to_process.append({
                "id": bc_id,
                "name": name,
                "dob": dob,
                "tob": tob,
                "place": place,
                "lat": lat,
                "lon": lon,
                "tz": tz,
                "events": events_by_figure[norm_name]
            })
        else:
            logger.debug(f"No events found for {name} ({norm_name})")

    return figures_to_process

def run_benchmark(batch_size: int = 10, limit: int = None, start_index: int = 0):
    """Run the LSE benchmark in batches."""
    logger.info(f"Starting LSE Benchmark using {DB_PATH}")
    
    figures = fetch_figures_and_events(DB_PATH)
    if limit:
        figures = figures[start_index : start_index + limit]
    else:
        figures = figures[start_index:]

    logger.info(f"Found {len(figures)} figures to process with associated events.")

    generator = ChartGenerator()
    config = ModelConfig(db_path=DB_PATH, defaults_path=DEFAULTS_PATH)
    orchestrator = LSEOrchestrator(config)
    repo = ChartDNARepository(DB_PATH) # Save back to the same DB

    total_processed = 0
    for i in range(0, len(figures), batch_size):
        batch = figures[i : i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} figures)...")
        
        for fig in batch:
            try:
                logger.info(f"  Solving chart for: {fig['name']} (ID: {fig['id']})")
                
                # 1. Generate charts
                full_payload = generator.build_full_chart_payload(
                    dob_str=fig['dob'],
                    tob_str=fig['tob'],
                    place_name=fig['place'],
                    latitude=fig['lat'],
                    longitude=fig['lon'],
                    utc_string=fig['tz']
                )
                
                natal_chart = full_payload["chart_0"]
                annual_charts = {int(k.split("_")[1]): v for k, v in full_payload.items() if k.startswith("chart_") and k != "chart_0"}
                
                # 2. Run LSE Orchestrator
                result = orchestrator.solve_chart(
                    birth_chart=natal_chart,
                    annual_charts=annual_charts,
                    life_event_log=fig['events'],
                    figure_id=fig['name']
                )

                # 3. Persist result
                if result.chart_dna:
                    repo.save(result.chart_dna)
                    logger.info(f"    - Converged: {result.converged}, Hit Rate: {result.chart_dna.back_test_hit_rate:.2f}")
                else:
                    logger.warning(f"    - No DNA generated for {fig['name']}")
                
                total_processed += 1

            except Exception as e:
                logger.error(f"  Error processing {fig['name']}: {str(e)}")
                continue

    logger.info(f"Benchmark complete. Processed {total_processed} figures.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LSE Autoresearch Benchmark on astroq_gt.db")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of figures to process in one batch")
    parser.add_argument("--limit", type=int, default=None, help="Total number of figures to process")
    parser.add_argument("--start-index", type=int, default=0, help="Index to start from")
    
    args = parser.parse_args()
    run_benchmark(batch_size=args.batch_size, limit=args.limit, start_index=args.start_index)
