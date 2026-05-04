# Timeline Fidelity Fixes — Implementation Plan

> **For Antigravity:** REQUIRED SUB-SKILL: Load executing-plans to implement this plan task-by-task.

**Goal:** Fix functional issues in Amitabh timeline: ledger bypass, frozen fate, hardcoded event anchors, domain score max instead of sum, timing-gate invisibility, stub click handlers.

**Architecture:** Two-stage pipeline — generate_amitabh_full_timeline_data.py produces JSON, generate_amitabh_visualizer.py renders HTML. Issues #7/#8 deferred (confirmed non-bugs after deeper check).

**Tech Stack:** Python 3.11, Chart.js + chartjs-plugin-annotation, StrengthEngine, VarshphalTimingEngine, StateLedger

---

## Files

- Data generator: `backend/scripts/generate_amitabh_full_timeline_data.py`
- HTML generator: `backend/scripts/generate_amitabh_visualizer.py`
- Test file: `backend/tests/test_timeline_fidelity.py` (CREATE)

**Run tests:** `cd backend && python -m pytest tests/test_timeline_fidelity.py -v`

