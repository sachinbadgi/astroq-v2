# AstroQ NFR Architectural Optimizations (v1.0)

This document serves as a reference for the non-functional requirements (NFR) and architectural improvements implemented in AstroQ v2 to ensure production-grade scalability and data health.

## 1. Persistent State Management
*   **Implementation**: [SQLiteChartStore](file:///d:/astroq-v2/backend/astroq/lk_prediction/api/chart_store.py)
*   **Rationale**: Migrated from in-memory dictionary to disk-persistent SQLite to prevent data loss on server restart and ensure memory stability.
*   **Database**: `backend/data/charts.db`

## 2. Async Background Processing
*   **Implementation**: [TaskIQ](file:///d:/astroq-v2/backend/astroq/lk_prediction/api/tasks.py)
*   **Rationale**: Offloaded CPU-intensive actions (Public Figure Benchmarking) to background tasks using the **TaskIQ** framework.
*   **Outcome**: The `/metrics/test-runs` API route is now non-blocking and return a handle for results.

## 3. LLM Cost & Performance Optimization
*   **Implementation**: Integrated **LiteLLM** and implemented `_summarize_chart_for_llm` in `server.py`.
*   **Rationale**: 
    *   **LiteLLM**: Provides a unified, provider-agnostic interface for future-proofing.
    *   **Summarization**: Reduces token consumption by ~50% by sending house-maturation summaries (Fact-Strings) instead of large, raw JSON objects.

## 4. Data Health & Traceability
*   **Schema Versioning**: Every chart now carries a `schema_version`.
*   **Lazy Migration**: The store automatically updates older JSON structures (e.g., adding missing `grammar_tags`) upon retrieval, ensuring code-data compatibility.
*   **TTL Cleanup**: Benchmarks are tagged as `BENCHMARK` and assigned an `expires_at` timestamp. 
*   **Auto-Maintenance**: An automated purge job runs on server startup to delete expired test data.
*   **Traceability**: Stored charts log the `app_version` (currently `2.1.0-NFR`) used for the original prediction.

---
*Created on 2026-03-27 for AstroQ v2.1.0-NFR*
