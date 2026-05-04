import json
with open('/Users/sachinbadgi/Documents/lal_kitab/astroq-v2/backend/tests/graphify_test/full_audit_report.json', 'r') as f:
    data = json.load(f)

total = data['stats']['total_attempts']
semantic_success = sum(1 for r in data['detailed_results'] if r['success'])
structural_success = sum(1 for r in data['detailed_results'] if r['node_hit'])

print(f"Total Rules: {total}")
print(f"Structural Hits (Node reached): {structural_success} ({structural_success/total*100:.1f}%)")
print(f"Semantic Success (Rule matched): {semantic_success} ({semantic_success/total*100:.1f}%)")

print("\nSemantic Failure by Domain:")
failures = [r for r in data['detailed_results'] if not r['success']]
domain_failures = {}
for f in failures:
    d = f['domain']
    domain_failures[d] = domain_failures.get(d, 0) + 1

for d, count in sorted(domain_failures.items(), key=lambda x: x[1], reverse=True):
    print(f"  {d}: {count}")
