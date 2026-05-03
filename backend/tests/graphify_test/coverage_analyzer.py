import json
from typing import List, Dict, Any, Set

class CoverageAnalyzer:
    def __init__(self, coverage_map_path: str):
        with open(coverage_map_path, "r") as f:
            self.target_rules = json.load(f)
        self.results = []

    def log_result(self, rule_id: str, success: bool, trace_hits: Set[str], error: str = None):
        rule = next((r for r in self.target_rules if r["rule_id"] == rule_id), None)
        self.results.append({
            "rule_id": rule_id,
            "domain": rule["domain"] if rule else "unknown",
            "target_node": rule["node_id"] if rule else None,
            "success": success,
            "hits_captured": list(trace_hits),
            "node_hit": rule["node_id"] in trace_hits if rule and rule["node_id"] else False,
            "error": error
        })

    def generate_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        successful_hits = sum(1 for r in self.results if r["node_hit"])
        
        # Group by domain
        domain_stats = {}
        for r in self.results:
            d = r["domain"]
            if d not in domain_stats:
                domain_stats[d] = {"total": 0, "hits": 0}
            domain_stats[d]["total"] += 1
            if r["node_hit"]:
                domain_stats[d]["hits"] += 1

        return {
            "stats": {
                "total_attempts": total,
                "successful_node_hits": successful_hits,
                "coverage_percent": (successful_hits / total * 100) if total > 0 else 0
            },
            "domain_stats": domain_stats,
            "failed_rules": [r["rule_id"] for r in self.results if not r["node_hit"]]
        }

    def print_report(self):
        summary = self.generate_summary()
        print("\n" + "="*50)
        print("GRAPHIFY SEMANTIC COVERAGE REPORT")
        print("="*50)
        print(f"Total Rules Attempted: {summary['stats']['total_attempts']}")
        print(f"Successful Node Hits:  {summary['stats']['successful_node_hits']}")
        print(f"Coverage Score:        {summary['stats']['coverage_percent']:.2f}%")
        print("-" * 50)
        print("DOMAIN BREAKDOWN:")
        for domain, stats in summary["domain_stats"].items():
            pct = (stats["hits"] / stats["total"] * 100)
            print(f"  {domain:<15}: {stats['hits']}/{stats['total']} ({pct:.1f}%)")
        print("="*50 + "\n")
