# Skill Memory: Learnings Log

> Accumulated knowledge from implementation sessions.
> The agent MUST read this at the start of each session and append new entries at the end.

## How to Use This File

**At session start**: Read this entire file to absorb prior learnings.
**At session end**: Append a new entry at the bottom with:
- Date
- Phase/module worked on
- What was discovered (bugs, patterns, design decisions)
- What worked well
- What didn't work (and the fix)
- Config values that were tuned and why

---

## 2026-03-23 — Chart Accuracy Fix
- **Sidereal vs Tropical**: Discovered that Lal Kitab "Software" look for many users expects **Sidereal (Lahiri)** signs mapped to fixed houses (Aries=1). Reverted `chart_generator.py` to Lahiri.
- **Ascendant Mapping**: Fixed missing "Asc" point in `planets_in_houses` and correctly positioned it in `NatalChart2D.tsx`.
- **Fixed House Logic**: Confirmed `int(lon // 30) + 1` correctly maps absolute longitude to signs 1-12.
