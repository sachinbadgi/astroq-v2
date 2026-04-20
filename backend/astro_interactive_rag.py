import json
import os
import sys
from typing import Dict, Any, List
from astroq.lk_prediction.pipeline import LKPredictionPipeline
from astroq.lk_prediction.config import ModelConfig
from litellm import completion

def find_payload_files(root_dir: str) -> List[str]:
    """Finds all potential payload files in the root and backend dirs."""
    patterns = ["*payload*.txt", "*payload*.json"]
    found = []
    
    # Search root
    for f in os.listdir(root_dir):
        if any(f.endswith(".json") or f.endswith(".txt") for p in patterns if "payload" in f.lower()):
            found.append(f)
            
    # Search backend
    backend_dir = os.path.join(root_dir, "backend")
    if os.path.exists(backend_dir):
        for f in os.listdir(backend_dir):
             if any(f.endswith(".json") or f.endswith(".txt") for p in patterns if "payload" in f.lower()):
                found.append(os.path.join("backend", f))
    
    return sorted(list(set(found)))

def interactive_loop():
    print("\n" + "="*50)
    print("   🌌 ASTRO-Q INTERACTIVE GRAPH-RAG (OLLAMA) 🌌")
    print("="*50)
    
    root_dir = os.getcwd()
    
    # 1. Pipeline Setup
    backend_dir = os.path.join(root_dir, "backend")
    db_path = os.path.join(backend_dir, "data", "rules.db")
    defaults_path = os.path.join(backend_dir, "data", "model_defaults.json")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Rules DB not found at {db_path}")
        return

    cfg = ModelConfig(db_path=db_path, defaults_path=defaults_path)
    pipeline = LKPredictionPipeline(cfg)
    
    # 2. Payload Selection
    payloads = find_payload_files(root_dir)
    if not payloads:
        print("❌ No payload files found in root or backend directory.")
        return
    
    print("\nSelect a person/chart to load:")
    for i, p in enumerate(payloads):
        print(f"[{i+1}] {p}")
    
    try:
        choice = int(input("\nEnter number (or 0 to exit): "))
        if choice == 0: return
        selected_file = payloads[choice-1]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        return

    # 3. Load Selected Payload
    print(f"📂 Loading {selected_file}...")
    try:
        with open(selected_file, 'r') as f:
            data = json.load(f)
            natal_chart = data["natal_promise_baseline"]
            annual_charts = {e["age"]: e for e in data["annual_fulfillment_timeline"]}
    except Exception as e:
        print(f"❌ Failed to load payload: {e}")
        return

    print("✅ System Ready. (Using Ollama gemma4:latest)")
    
    # 4. Interaction Loop
    while True:
        print("\n" + "-"*30)
        query = input("❓ Query (e.g. 'career at 50', 'health at 60') or 'exit': ").strip()
        
        if query.lower() in ['exit', 'quit', 'q']:
            print("👋 Goodbye!")
            break
            
        if not query:
            continue
            
        # Extract age if possible (very simple heuristic)
        # In a real app, the SemanticBridge handles this, but here we just pass the string
        
        print("\n🔍 Extracting and Synthesizing...")
        
        try:
            # Step A: Pre-resolve anchors to show UI progress
            # Access the graph_rag predictor directly
            anchors = pipeline.graph_rag.bridge.get_query_anchors(query)
            extracted_info = f"Ages: {anchors['ages']}, Years: {anchors['calendar_years']}"
            print(f"   Targets identified: {extracted_info}")

            # Step B: Get Graph Context
            context_cluster = pipeline.answer_graph_query(query, natal_chart, annual_charts)
            
            # Step C: Call LLM
            system_prompt = """
You are a Lal Kitab Astrological Expert. 
Your goal is to provide a predictive narrative based on the provided Knowledge Graph Context Cluster.

CRITICAL INSTRUCTIONS:
1. FOCUS: You must answer the specific question asked (e.g., about a specific age).
2. VOID DATA: If the context contains an error like 'Data for age X not found', you MUST state that data for that specific year is missing from the payload.
3. ADHERENCE: Use ONLY the 'Active Rule Hits' and 'Verdicts' provided in the context. Do not give generic advice unless the context specifically supports it for that age.
4. STRUCTURE: 
   - Start with a direct answer to the query.
   - Use the 'Active Rule Hits' to justify the prediction.
   - Use 'Planetary States' to explain the quality of the period.
            """
            
            response = completion(
                model="ollama/gemma4:latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context_cluster}"}
                ],
                api_base="http://localhost:11434"
            )
            
            print("\n✨ PREDICTION:")
            print(response.choices[0].message.content)
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    interactive_loop()
