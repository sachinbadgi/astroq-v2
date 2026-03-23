---
name: astroq-react-ui
description: Build the AstroQ v2 production React UI from scratch using TDD (Vitest + React Testing Library). Covers Auth, Chart generation, 7 tabs (General Chat, Oracle Chat, 2D Chart, Prediction Dashboard, Remedies, Benchmark), a dark cosmic design system, and clean component architecture. Uses autoresearch on old UI and superpowers turbo annotations for all test runs.
---

# AstroQ React UI — Build Skill

## Goal

Build the complete React frontend at `frontend/` (under `d:\astroq-v2\frontend\`) for the new AstroQ v2 backend engine using strict TDD. The UI must be production-quality, visually stunning (dark cosmic theme), and fully wired to the backend APIs documented in `resources/ui_design_model.md`.

> **REFERENCE CODEBASE (READ-ONLY)**
> Study the old frontend at `D:\astroq-mar26\frontend\src\` for UI patterns, API shapes, and component logic. Never modify it.

> **STRICT BAN ON STUBS / HALF-BAKED FEATURES**: Every component must be fully implemented with real API calls and real data rendering. No placeholder text or hardcoded fake data in final components.

---

## Reference Locations

```
REFERENCE_OLD_FRONTEND  = D:\astroq-mar26\frontend\src
REFERENCE_OLD_BACKEND   = D:\astroq-mar26\backend\astroq\api.py
NEW_FRONTEND_ROOT       = D:\astroq-v2\frontend
NEW_BACKEND_ROUTES      = D:\astroq-v2\backend\astroq\lk_prediction\pipeline.py
UX_MODEL                = .antigravity/skills/astroq-react-ui/resources/ui_design_model.md
```

---

## ⚡ Memory System (MANDATORY)

### On Session Start — ALWAYS do this FIRST

```bash
view_file .antigravity/skills/astroq-react-ui/memory/progress.md
view_file .antigravity/skills/astroq-react-ui/memory/learnings.md
view_file .antigravity/skills/astroq-react-ui/memory/decisions.md
```

> **CRITICAL**: Do NOT skip this step. Memory files tell you which phases are done, which design decisions are settled, and what patterns work.

### On Session End — ALWAYS do this LAST

1. **Update `memory/progress.md`** — Mark completed phases, test counts, components built
2. **Append to `memory/learnings.md`** — Dated entry with what you discovered
3. **Append to `memory/decisions.md`** — Any new architectural decisions made

---

## Autoresearch Superpowers

Before coding each component, autoresearch the **reference codebase** for patterns:

| Component | Study These Files (old frontend) |
|-----------|----------------------------------|
| AuthPage | `App.tsx` lines 434–519 (auth form + Google SSO) |
| ProfileSidebar + ChartForm | `App.tsx` lines 521–653 (sidebar form + location search) |
| NatalChart2D | `Chart2D.tsx` (entire file — house rendering logic) |
| OracleChat | `AstroChat.tsx` + `App.tsx` processFlow() |
| RemedyPanel | `RemedySimulator.tsx` (entire file — matrix, charts) |
| PredictionDashboard | `NEW` — no reference; use `lk_prediction/pipeline.py` output shape |
| BenchmarkDashboard | `BenchmarkDashboard.tsx` (entire file — table structure) |

> Also read `D:\astroq-mar26\backend\astroq\api.py` for all API endpoint contracts.

---

## Superpowers TDD Build Sequence

Build in strict phase order. For EACH phase:
1. **Write tests FIRST** (Red) — component renders, props, API calls mocked
2. **Implement just enough to pass** (Green)
3. **Run tests** to confirm all green
4. **Refactor** for design quality

---

### Phase 0: Scaffold

```bash
# Initialize Vite + React + TypeScript
cd D:\astroq-v2
npx -y create-vite@latest frontend -- --template react-ts

# Install dependencies
cd frontend
npm install axios lucide-react recharts
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom

# Verify scaffold
npm run dev
```

Configure `vite.config.ts` for Vitest:
```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.ts',
  },
})
```

After scaffold: Replace `index.css` with the full design system from `resources/ui_design_model.md` Section 4.

---

### Phase 1: AuthPage Component

```bash
# 1. Write test first
# File: src/__tests__/AuthPage.test.tsx
# Tests: 5 (renders login form, submit with valid data, shows error, toggles to register, Google button present)

# 2. Implement
# File: src/components/auth/AuthPage.tsx

# 3. Run tests
// turbo
npx vitest run src/__tests__/AuthPage.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders login form with username/password fields`
- `shows auth error message on failed login`
- `toggles to register mode`
- `calls /login API with correct payload`
- `renders Google Sign-In button`

---

### Phase 2: AppShell + ProfileSidebar + ChartForm

```bash
# 1. Write tests
# File: src/__tests__/ChartForm.test.tsx
# Tests: 8

# 2. Implement
# Files: src/components/layout/AppShell.tsx
#        src/components/layout/ProfileSidebar.tsx
#        src/components/chart/ChartForm.tsx

# 3. Run tests
// turbo
npx vitest run src/__tests__/ChartForm.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders all form fields (name, dob, tob, place, system)`
- `disables submit when fields empty`
- `calls /search-location on place blur`
- `shows location dropdown when multiple results`
- `selects location and clears dropdown`
- `calls /lal-kitab/generate-birth-chart on submit`
- `shows loading spinner during submit`
- `shows error on API failure`

---

### Phase 3: NatalChart2D Component

```bash
# 1. Write tests
# File: src/__tests__/NatalChart2D.test.tsx
# Tests: 6

# 2. Implement
# File: src/components/chart/NatalChart2D.tsx
# Reference: D:\astroq-mar26\frontend\src\Chart2D.tsx

# 3. Run tests
// turbo
npx vitest run src/__tests__/NatalChart2D.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders 12 house cells`
- `places planets in correct houses`
- `shows ascendant marker`
- `renders house numbers 1–12`
- `handles empty chartData gracefully`
- `shows planet abbreviations (Su, Mo, Ma, etc.)`

---

### Phase 4: GeneralChat + OracleChat (SSE)

```bash
# 1. Write tests
# File: src/__tests__/GeneralChat.test.tsx  (6 tests)
#        src/__tests__/OracleChat.test.tsx   (8 tests)

# 2. Implement
# Files: src/components/chat/GeneralChat.tsx
#        src/components/chat/OracleChat.tsx
#        src/hooks/useSSE.ts

# 3. Run tests
// turbo
npx vitest run src/__tests__/GeneralChat.test.tsx src/__tests__/OracleChat.test.tsx --reporter=verbose
```

**GeneralChat tests:**
- `renders message list`
- `sends message on Enter key`
- `calls /ask-chart API`
- `shows loading indicator`
- `displays assistant response`
- `shows error on API failure`

**OracleChat tests:**
- `renders query input`
- `calls /ask-chart-premium/stream endpoint`
- `renders step-by-step SSE events`
- `shows final synthesized answer`
- `handles SSE errors gracefully`
- `shows spinner during streaming`
- `displays step type labels (ANALYZE, REASON, CONCLUDE)`
- `clears previous result on new query`

---

### Phase 5: RemedyPanel

```bash
# 1. Write tests
# File: src/__tests__/RemedyPanel.test.tsx
# Tests: 8

# 2. Implement
# File: src/components/remedy/RemedyPanel.tsx
# Reference: D:\astroq-mar26\frontend\src\RemedySimulator.tsx

# 3. Run tests
// turbo
npx vitest run src/__tests__/RemedyPanel.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders planet selector tabs`
- `renders shifting matrix table`
- `toggles shift button state on click`
- `calls /simulate-remedies on shift toggle`
- `renders lifetime projection AreaChart`
- `shows current age reference line`
- `shows commitment sliders in summary mode`
- `switches sub-mode tabs (matrix/summary)`

---

### Phase 6: PredictionDashboard (NEW)

This is a **new** component with no reference in the old UI.
It visualizes the output of `lk_prediction` pipeline:
- Planet strength scores (bar chart per planet)
- Grammar factor scores (radar chart)
- Probability timeline (line chart: probability vs age)
- Life domain predictions (cards with event labels)

```bash
# 1. Write tests
# File: src/__tests__/PredictionDashboard.test.tsx
# Tests: 10

# 2. Implement
# File: src/components/prediction/PredictionDashboard.tsx
# Study: D:\astroq-v2\backend\astroq\lk_prediction\data_contracts.py

# 3. Run tests
// turbo
npx vitest run src/__tests__/PredictionDashboard.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders planet strength bar chart`
- `renders grammar factor labels`
- `renders probability timeline chart`
- `shows predictions list with domain and event`
- `shows confidence level badge`
- `handles empty predictions array`
- `calls /lal-kitab/predict on componentDidMount`
- `shows loading skeleton`
- `refreshes on chartData change`
- `renders correct planet abbreviations`

---

### Phase 7: BenchmarkDashboard

```bash
# 1. Write tests
# File: src/__tests__/BenchmarkDashboard.test.tsx
# Tests: 6

# 2. Implement
# File: src/components/benchmark/BenchmarkDashboard.tsx
# Reference: D:\astroq-mar26\frontend\src\BenchmarkDashboard.tsx

# 3. Run tests
// turbo
npx vitest run src/__tests__/BenchmarkDashboard.test.tsx --reporter=verbose
```

**Test coverage required:**
- `renders test run table`
- `shows hit rate metric`
- `shows offset metric`
- `shows natal accuracy metric`
- `handles empty test runs`
- `renders public figure names`

---

### Phase 8: Full Integration & App.tsx Wiring

```bash
# Wire all components into App.tsx with React Router tabs
# File: src/App.tsx
# File: src/api/client.ts  (axios client with token interceptor)

# Run ALL tests
// turbo
npx vitest run --reporter=verbose

# Run dev server
npm run dev
```

---

## File Structure (Final)

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css                          ← Design system tokens
│   ├── api/
│   │   └── client.ts                      ← Axios + auth interceptor
│   ├── hooks/
│   │   ├── useChart.ts                    ← Chart load/generate hook
│   │   └── useSSE.ts                      ← Server-Sent Events hook
│   ├── components/
│   │   ├── auth/
│   │   │   └── AuthPage.tsx
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   └── ProfileSidebar.tsx
│   │   ├── chart/
│   │   │   ├── ChartForm.tsx
│   │   │   ├── NatalChart2D.tsx
│   │   │   └── StrengthTimeline.tsx
│   │   ├── chat/
│   │   │   ├── GeneralChat.tsx
│   │   │   └── OracleChat.tsx
│   │   ├── prediction/
│   │   │   └── PredictionDashboard.tsx
│   │   ├── remedy/
│   │   │   └── RemedyPanel.tsx
│   │   └── benchmark/
│   │       └── BenchmarkDashboard.tsx
│   └── __tests__/
│       ├── setup.ts
│       ├── AuthPage.test.tsx
│       ├── ChartForm.test.tsx
│       ├── NatalChart2D.test.tsx
│       ├── GeneralChat.test.tsx
│       ├── OracleChat.test.tsx
│       ├── PredictionDashboard.test.tsx
│       ├── RemedyPanel.test.tsx
│       └── BenchmarkDashboard.test.tsx
```

---

## Metrics (Target)

| Metric | Target |
|--------|--------|
| **Test Count** | 57 total (all green before merge) |
| **Test Coverage** | 100% component public interface |
| **Loading State** | All API calls show skeleton/spinner |
| **Error State** | All API calls show user-friendly error |
| **Mobile** | Usable on 375px (iPhone SE) width |
| **Performance** | First contentful paint < 1.5s |
