import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any

# Ensure we can import from backend
sys.path.append(os.path.abspath("backend"))

from astroq.lk_prediction.varshphal_timing_engine import VarshphalTimingEngine
from astroq.lk_prediction.astrological_context import UnifiedAstrologicalContext
from astroq.lk_prediction.data_contracts import EnrichedChart
from astroq.lk_prediction.natal_fate_view import NatalFateView
from astroq.lk_prediction.lifecycle_engine import LifecycleEngine
from astroq.lk_prediction.chart_enricher import ChartEnricher
from astroq.lk_prediction.grammar_analyser import GrammarAnalyser
from astroq.lk_prediction.strength_engine import StrengthEngine
from astroq.lk_prediction.config import ModelConfig
from tests.graphify_test.orchestrator import GraphifyTestOrchestrator
from tests.graphify_test.fuzzer import ConstraintAwareFuzzer
from tests.graphify_test.coverage_analyzer import CoverageAnalyzer

# Domain mapping for Public Figures
DOMAIN_MAP = {
    "Career": "career",
    "Legal": "litigation",
    "Business": "career",
    "Debut": "career",
    "Success": "career",
    "Finance": "finance",
    "Health": "health",
    "Death": "health",
    "Marriage": "marriage",
    "Progeny": "progeny",
    "Sports": "career",
    "Award": "career",
    "Triumph": "career",
    "Setback": "career",
    "Relocation": "career"
}

class SystemAuditOrchestrator:
    def __init__(self, graph_path: str, coverage_map_path: str, pf_db_path: str):
        self.graph_path = graph_path
        self.coverage_map_path = coverage_map_path
        self.pf_db_path = pf_db_path
        
        # Engines
        self.engine = VarshphalTimingEngine()
        self.fate_view = NatalFateView()
        self.lifecycle = LifecycleEngine()
        
        # Setup config and enricher
        db_path = "backend/data/config.db"
        defaults_path = "backend/data/model_defaults.json"
        self.config = ModelConfig(db_path, defaults_path)
        grammar_analyser = GrammarAnalyser(self.config)
        strengths = StrengthEngine(self.config)
        self.enricher = ChartEnricher(grammar_analyser.registry, strengths)
        
        # Tools
        self.orchestrator = GraphifyTestOrchestrator(graph_path)
        self.fuzzer = ConstraintAwareFuzzer(coverage_map_path)
        self.analyzer = CoverageAnalyzer(coverage_map_path)
        
        self.forensic_results = []

    def run_rule_audit(self):
        print(f"--- Running Rule-Based Audit ({len(self.fuzzer.rules)} rules) ---")
        for i, rule in enumerate(self.fuzzer.rules):
            rule_id = rule["rule_id"]
            chart_data = self.fuzzer.generate_chart_for_rule(rule)
            context = UnifiedAstrologicalContext(enriched=EnrichedChart(source=chart_data))
            context.age = 30
            
            with self.orchestrator.start_trace() as trace:
                try:
                    results = self.engine.evaluate_varshphal_triggers(context, rule["domain"])
                    is_hit = any(r.get("desc") == rule_id for r in results)
                    self.analyzer.log_result(rule_id, is_hit, trace.hits)
                except Exception as e:
                    self.analyzer.log_result(rule_id, False, trace.hits, error=str(e))

    def run_forensic_audit(self):
        print(f"--- Running Public Figures Forensic Audit ---")
        if not os.path.exists(self.pf_db_path):
            print(f"Warning: Public figures database not found at {self.pf_db_path}")
            return

        conn = sqlite3.connect(self.pf_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, natal_chart_json, annual_charts_json FROM public_figures WHERE natal_chart_json IS NOT NULL")
        figures = cursor.fetchall()
        
        for fid, name, natal_str, annual_str in figures:
            print(f"  Analysing {name}...")
            natal = json.loads(natal_str)
            annuals = json.loads(annual_str)
            
            # Natal Verification
            fate_entries = self.fate_view.evaluate(natal)
            fate_by_domain = {e["domain"]: e["fate_type"] for e in fate_entries}
            
            # Get Events
            cursor.execute("SELECT event, date, type FROM life_events WHERE figure_id = ?", (fid,))
            events = [{"event": e[0], "date": e[1], "type": e[2]} for e in cursor.fetchall()]
            
            # Find death age to cap noise
            death_age = None
            for ev in events:
                if ev["type"].lower() == "death" or "death" in ev["event"].lower():
                    try:
                        birth_year = int(natal.get("birth_time", "")[:4])
                        event_year = int(ev["date"][:4])
                        death_age = event_year - birth_year
                    except: pass

            figure_report = {
                "figure_id": fid,
                "name": name,
                "natal_fates": fate_entries,
                "event_results": []
            }
            
            birth_year = int(natal.get("birth_time", "")[:4]) if natal.get("birth_time") else 0

            for event in events:
                domain_raw = event["type"]
                engine_domain = DOMAIN_MAP.get(domain_raw, "career")
                
                try:
                    age = int(event["date"][:4]) - birth_year
                except: continue
                
                if age < 0 or (death_age and age > death_age): continue
                
                # Check Natal Promise
                fate_type = fate_by_domain.get(engine_domain, "RASHI_PHAL")
                
                # Timing check
                annual = annuals.get(f"chart_{age}")
                hit = False
                if annual:
                    enriched = self.enricher.enrich(annual, natal)
                    ctx = UnifiedAstrologicalContext(enriched=enriched, natal_chart=natal, config=self.config)
                    # We use get_timing_confidence for forensic accuracy
                    res = self.engine.get_timing_confidence(ctx, engine_domain, fate_type=fate_type, age=age)
                    hit = res["confidence"] in ["Medium", "High"]

                figure_report["event_results"].append({
                    "event": event["event"],
                    "domain": engine_domain,
                    "age": age,
                    "fate_type": fate_type,
                    "hit": hit,
                    "triggers": res.get("triggers", []) if annual else []
                })

            self.forensic_results.append(figure_report)
        
        conn.close()

    def save_reports(self, output_path: str):
        report = self.analyzer.generate_summary()
        report["detailed_results"] = self.analyzer.results
        report["forensic_results"] = self.forensic_results
        
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"System Audit Complete! Report saved to {output_path}")

if __name__ == "__main__":
    orchestrator = SystemAuditOrchestrator(
        graph_path="graphify-out/graph.json",
        coverage_map_path="backend/tests/graphify_test/coverage_map.json",
        pf_db_path="backend/data/public_figures.db"
    )
    orchestrator.run_rule_audit()
    orchestrator.run_forensic_audit()
    orchestrator.save_reports("backend/tests/graphify_test/full_system_report.json")
