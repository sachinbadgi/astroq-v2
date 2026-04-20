import json
import os
import argparse
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from astroq.lk_prediction.graph_exporter import NotebookLMExporter

def main():
    parser = argparse.ArgumentParser(description="Export a full 75-year astrological lifeline to Markdown.")
    parser.add_argument("--payload", required=True, help="Path to the person's payload (json or txt)")
    parser.add_argument("--output", required=True, help="Path to save the master markdown file")
    parser.add_argument("--max-age", type=int, help="Optional: Maximum age to export (e.g. 50)")
    
    args = parser.parse_args()
    
    print(f"🌌 Exporting Lifeline for: {args.payload}")
    
    # 1. Setup Backend
    backend_dir = os.path.join(os.getcwd(), "backend")
    db_path = os.path.join(backend_dir, "data", "rules.db")
    defaults_path = os.path.join(backend_dir, "data", "model_defaults.json")
    
    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    pipeline = LKPredictionPipeline(cfg)
    
    # 2. Load Payload
    try:
        with open(args.payload, 'r') as f:
            data = json.load(f)
            natal_chart = data["natal_promise_baseline"]
            annual_charts = {e["age"]: e for e in data["annual_fulfillment_timeline"]}
    except Exception as e:
        print(f"❌ Failed to load payload: {e}")
        return

    # 3. Prepare Graph (All 75 years)
    print("📈 Building Knowledge Graph and indexing rules...")
    pipeline.graph_rag.prepare_graph(natal_chart, annual_charts)
    
    # 4. Export to Markdown
    print(f"📝 Serializing timeline to Markdown (Max Age: {args.max_age if args.max_age else 'All'})...")
    exporter = NotebookLMExporter(pipeline.graph_rag.graph)
    master_md = exporter.export_master_lifeline(max_age=args.max_age)
    
    # 5. Save
    try:
        with open(args.output, 'w') as f:
            f.write(master_md)
        print(f"✅ SUCCESSFULLY EXPORTED to: {args.output}")
        print(f"📊 Stats: ~{len(master_md.split())} words generated.")
        print("\nNEXT STEP: Upload this file to NotebookLM (https://notebooklm.google.com/) for holistic analysis.")
    except Exception as e:
        print(f"❌ Failed to save output: {e}")

if __name__ == "__main__":
    main()
