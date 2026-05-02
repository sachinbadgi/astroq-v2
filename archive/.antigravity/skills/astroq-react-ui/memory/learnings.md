# Learnings — astroq-react-ui

Accumulated knowledge from sessions. Append; do NOT delete.

---

## 2026-03-22 — Initial Research Session

### Old Frontend Architecture
- `App.tsx` is 867 lines and handles ALL state — auth, chart, tabs, messages. This is the main anti-pattern to fix.
- Tabs are: `chat`, `oracle`, `2d`, `3d`, `remedy`, `masf`, `benchmark`
- `RemedySimulator.tsx` has 5 sub-modes: `matrix`, `summary`, `concierge`, `health`, `timeline`
- `MASFPanel.tsx` calls `/masf/analyze` — this endpoint exists in old backend only
- `BenchmarkDashboard.tsx` calls `/test-metrics/*` routes (authenticated)
- `AstroChat.tsx` — Oracle streaming component, calls `/ask-chart-premium/stream` via SSE

### API Patterns (Old Backend)
- Auth: `POST /login` (form), `POST /register`, `POST /auth/google`, `GET /users/me`
- Charts: `GET /lal-kitab/birth-charts`, `POST /lal-kitab/generate-birth-chart`, `GET /lal-kitab/birth-charts/{id}`
- Q&A: `POST /ask-chart`, `POST /ask-chart-premium`, `POST /ask-chart-premium/stream` (SSE)
- Remedies: `POST /simulate-remedies`, `POST /concierge-diagnosis`
- MASF: `POST /masf/analyze`
- Location: `POST /search-location`
- Benchmarks: `GET /metrics/test-runs` etc. (guessed from BenchmarkDashboard.tsx)

### New Backend (lk_prediction)
- New backend at `d:/astroq-v2/backend` only has `lk_prediction/` module — no REST API yet
- `pipeline.py` is the entry point — takes `ChartData`, outputs `LKPrediction`
- Data contracts in `data_contracts.py` — `LKPrediction`, `EnrichedPlanet`, `PredictionPoint`
- Frontend should point to OLD backend (localhost:8000) for now; TODO markers for migration

### Design Observations
- Old UI color palette: `#0a0710` (bg), `#1f1d2e` (card), `#26233a` (border), `#e0def4` (text)
- Font: `font-mono` everywhere in old UI — new UI should use Inter/modern sans + mono for code/data
- Tailwind was used but caused utility sprawl — new design uses CSS custom properties
- Old 3D chart uses Three.js — expensive to load; consider optional lazy import

### Patterns That Worked
- `localStorage` for auth token + active chart persistence (good pattern, keep it)
- Auto-location search on `onBlur` of the place field (good UX)
- Emerald dot on active profile in sidebar (good visual feedback)

### Things To Avoid
- 867-line monolithic App.tsx — split into proper component hierarchy
- Inline `const API_BASE_URL = 'http://localhost:8000'` duplicated in 5 files — use `api/client.ts`
- Rendering all tabs always but hiding via CSS `hidden` class — use lazy/conditional rendering
