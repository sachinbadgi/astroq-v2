import pytest
import json
from datetime import datetime

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    Custom summary for Graphify Semantic Coverage.
    """
    stats = terminalreporter.stats
    passed = len(stats.get('passed', []))
    failed = len(stats.get('failed', []))
    total = passed + failed
    
    if total == 0:
        return

    coverage = (passed / total) * 100 if total > 0 else 0

    terminalreporter.write_sep("=", "GRAPHIFY REGRESSION SUMMARY", bold=True, cyan=True)
    terminalreporter.write_line(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    terminalreporter.write_line(f"Total Semantic Rules: {total}")
    terminalreporter.write_line(f"Successful Hits:     {passed}")
    terminalreporter.write_line(f"Failed/Unreachable:  {failed}")
    
    color = "green" if coverage > 90 else "yellow" if coverage > 50 else "red"
    terminalreporter.write_line(f"Semantic Coverage:   {coverage:.2f}%", **{color: True, "bold": True})
    
    if failed > 0:
        terminalreporter.write_line("\nTOP FAILURE DOMAINS:", bold=True, red=True)
        # Collect failure domains from reports
        failed_reports = stats.get('failed', [])
        domains = {}
        for rep in failed_reports:
            # We can't easily get the domain here without custom metadata
            # but we can show the rule IDs
            rule_id = rep.nodeid.split("[")[-1].replace("]", "")
            terminalreporter.write_line(f"  - {rule_id}")
            
    terminalreporter.write_sep("=", bold=True, cyan=True)

    # Save manifest of passed rules for graph filtering
    passed_reports = stats.get('passed', [])
    passed_rule_ids = []
    for rep in passed_reports:
        if "[" in rep.nodeid:
            rule_id = rep.nodeid.split("[")[-1].replace("]", "")
            passed_rule_ids.append(rule_id)
    
    with open("backend/tests/graphify_test/passed_rules.json", "w") as f:
        json.dump(passed_rule_ids, f, indent=2)

    _generate_markdown_report(total, passed, failed, coverage, passed_rule_ids)

def _generate_markdown_report(total, passed, failed, coverage, passed_rule_ids):
    report_path = "backend/tests/graphify_test/latest_regression_report.md"
    passed_rules_str = "\n".join([f"- {rid}" for rid in passed_rule_ids])
    content = f"""# Graphify Regression Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

| Metric | Value |
|--------|-------|
| Total Rules | {total} |
| Passed | {passed} |
| Failed | {failed} |
| **Coverage** | **{coverage:.2f}%** |

## Passed Rules (Mapped to Graphify Nodes)
{passed_rules_str}

## Summary
The suite verified the semantic reachability of {total} astrological rules against the Graphify-tagged codebase.
"""
    with open(report_path, "w") as f:
        f.write(content)
