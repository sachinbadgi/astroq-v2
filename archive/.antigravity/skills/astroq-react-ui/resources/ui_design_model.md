# AstroQ v2 — UI Design Model & User Journey

**Version**: 2.0  
**Date**: 2026-03-22  
**Backend**: `d:/astroq-v2/backend/astroq/lk_prediction/`  
**Old Reference**: `D:\astroq-mar26\frontend\src\`

---

## 1. User Journey Map

```
[UNAUTHENTICATED]
      │
      ▼
┌──────────────────────────────────┐
│  STEP 1: AUTH PAGE               │
│  - Username/Password login        │
│  - Google SSO (one-click)         │
│  - Register mode toggle           │
└──────────────┬───────────────────┘
               │ JWT stored in localStorage
               ▼
┌──────────────────────────────────┐
│  STEP 2: APP SHELL               │
│  Left: ProfileSidebar            │
│   ├─ [+] New Chart Form          │
│   └─ Saved Profiles list         │
│  Right: Tab Panel (empty state)  │
└──────────────┬───────────────────┘
               │ Fill name/DOB/TOB/place
               ▼
┌──────────────────────────────────┐
│  STEP 3: CHART GENERATION        │
│  - Place search with geocoding    │
│  - System: KP / Vedic            │
│  - POST /lal-kitab/generate-birth-chart │
│  - ~10s processing               │
│  - Chart saved automatically     │
└──────────────┬───────────────────┘
               │ chartData loaded
               ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 4: MAIN DASHBOARD (tabs enabled)                        │
│                                                               │
│  [💬 GENERAL] [🔮 ORACLE] [🪐 CHART] [📊 PREDICT] [⚡ REMEDY] [📈 BENCH] │
│                                                               │
│  Each tab is lazy-loaded. State preserved via React state.    │
└──────────────┬───────────────────────────────────────────────┘
               │
       ┌───────┴──────────────────────────┐
       │           STEP 5: TABS           │
       │                                  │
       ▼                                  ▼
[GENERAL CHAT]                    [ORACLE CHAT]
 POST /ask-chart                   POST /ask-chart-premium/stream
 Instant Q&A                       SSE step-by-step reasoning
                                   Shows: ANALYZE→REASON→CONCLUDE
       │                                  │
       └──────────────────────────────────┘
       
[2D CHART]              [PREDICTION]             [REMEDIES]
 North Indian grid        lk_prediction output     Shifting matrix
 12 house cells           - Planet strengths        Lifetime projection
 Planet placements        - Grammar scores          /simulate-remedies
 Ascendant shown          - Probability bars        Sub-modes: matrix,
                          - Event predictions       summary, concierge
                                                    
[BENCHMARK]
  /metrics/test-runs
  Hit Rate, Offset, Natal Accuracy
  Public figure table

               │
               ▼
┌──────────────────────────────────┐
│  STEP 6: PERSIST & RETURN        │
│  - Charts auto-persist           │
│  - Active chart saved to memory  │
│  - Sidebar shows active (green)  │
│  - Return: sidebar restores last │
└──────────────────────────────────┘
```

---

## 2. Component Hierarchy

```
App.tsx (router + auth gate)
├── AuthPage.tsx
└── AppShell.tsx
    ├── ProfileSidebar.tsx
    │   └── ChartForm.tsx
    └── TabPanel.tsx
        ├── GeneralChat.tsx
        ├── OracleChat.tsx
        ├── NatalChart2D.tsx
        ├── PredictionDashboard.tsx
        ├── RemedyPanel.tsx
        └── BenchmarkDashboard.tsx
```

---

## 3. API Surface Map

| Tab / Component | Endpoint | Method | Auth? |
|-----------------|----------|--------|-------|
| AuthPage | `/login` | POST | ❌ |
| AuthPage | `/register` | POST | ❌ |
| AuthPage | `/auth/google` | POST | ❌ |
| ProfileSidebar | `/lal-kitab/birth-charts` | GET | ✅ |
| ChartForm | `/search-location` | POST | ❌ |
| ChartForm | `/lal-kitab/generate-birth-chart` | POST | ✅ |
| ChartForm (load) | `/lal-kitab/birth-charts/{id}` | GET | ✅ |
| GeneralChat | `/ask-chart` | POST | ✅ |
| OracleChat | `/ask-chart-premium/stream` | POST (SSE) | ✅ |
| RemedyPanel | `/simulate-remedies` | POST | ❌ |
| RemedyPanel (concierge) | `/concierge-diagnosis` | POST | ❌ |
| PredictionDashboard | `/lal-kitab/birth-charts/{id}` | GET | ✅ |
| BenchmarkDashboard | `/metrics/test-runs` | GET | ✅ |

> **TODO (future)**: `/lk-predict` endpoint to be added when new backend API is wired.

---

## 4. Design System Tokens

```css
/* index.css — Design System */

:root {
  /* Backgrounds */
  --bg-deep:      #070510;     /* Page background */
  --bg-card:      #12101e;     /* Card/panel background */
  --bg-elevated:  #1a1830;     /* Elevated card (sidebar, headers) */
  --bg-overlay:   #231f38;     /* Hover / selected state */

  /* Borders */
  --border-subtle:  #1e1b30;
  --border-normal:  #2d2850;
  --border-visible: #3d3870;

  /* Accents */
  --accent-violet:  #7c5cf0;   /* Primary actions, active tabs */
  --accent-violet-glow: rgba(124, 92, 240, 0.25);
  --accent-pink:    #e040c8;   /* Highlights, alerts */
  --accent-pink-glow: rgba(224, 64, 200, 0.2);
  --accent-gold:    #f5c842;   /* NOW marker, warnings */
  --accent-teal:    #2dd4bf;   /* 2D chart tab */
  --accent-emerald: #10b981;   /* Success, active profiles */
  --accent-rose:    #f43f5e;   /* Danger, negative states */

  /* Text */
  --text-primary:  #e8e4fc;
  --text-secondary: #9490b8;
  --text-muted:    #5a5680;
  --text-disabled: #35325a;

  /* Typography */
  --font-sans: 'Inter', 'Segoe UI', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  --font-display: 'Inter', system-ui, sans-serif;

  /* Spacing */
  --radius-sm:  6px;
  --radius-md:  12px;
  --radius-lg:  18px;
  --radius-xl:  24px;

  /* Shadows */
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.5);
  --shadow-glow-violet: 0 0 20px rgba(124, 92, 240, 0.3);
  --shadow-glow-pink: 0 0 20px rgba(224, 64, 200, 0.2);
}

/* Base Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #root { height: 100%; }

body {
  font-family: var(--font-sans);
  background: var(--bg-deep);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-elevated); }
::-webkit-scrollbar-thumb { background: var(--border-visible); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-violet); }

/* Google Fonts Import */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
```

---

## 5. Prediction Dashboard — Data Shape

The `PredictionDashboard` component receives `chartData` and calls `GET /lal-kitab/birth-charts/{id}` which returns `lk_chart`. The `lk_prediction` pipeline output shape (from `data_contracts.py`):

```typescript
interface LKPrediction {
  domain: string;            // "career", "marriage", "health"
  event_type: string;        // "promotion", "marriage_timing"
  prediction_text: string;   // natural language
  confidence: string;        // "certain" | "highly_likely" | "possible"
  polarity: string;          // "benefic" | "malefic" | "mixed"
  peak_age: number;
  age_window: [number, number];
  probability: number;       // 0.0–1.0
  source_planets: string[];
  source_houses: number[];
  remedy_applicable: boolean;
  remedy_hints: string[];
}

interface EnrichedPlanet {
  house: number;
  strength_total: number;
  strength_breakdown: {
    aspects: number;
    dignity: number;
    scapegoat: number;
    disposition: number;
    mangal_badh: number;
    cycle_35yr: number;
    // ... 14 grammar factors
  };
  sleeping_status: string;
  dharmi_status: string;
  dhoka_graha: boolean;
  achanak_chot_active: boolean;
}
```

**PredictionDashboard UI Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│  🔮 PREDICTION ENGINE                                         │
│  [Planet Strengths ▼] [Grammar Scores ▼] [Predictions ▼]     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  PLANET STRENGTHS (Bar Chart)                                 │
│  Sun ████████░░  4.2 / 6.0  [Benefic]                        │
│  Moon ██████░░░  3.1 / 6.0  [Mixed]                          │
│  Mars ██░░░░░░░  1.4 / 6.0  [Malefic]                        │
│  ...                                                          │
│                                                               │
│  GRAMMAR FLAGS (Pill badges per planet)                       │
│  Sun: [Sleeping] [Dharmi]                                     │
│  Mars: [Dhoka Graha] [Achanak Chot Active]                    │
│                                                               │
│  LIFE PREDICTIONS (Cards)                                     │
│  ┌────────────────────────────────────────┐                  │
│  │ 🏢 Career · Promotion    [Peak: Age 52]│ [Highly Likely]  │
│  │ "Venus in H2 with Jupiter creates..."  │ Prob: 78%        │
│  │ Remedy: Feed crows on Saturday         │                  │
│  └────────────────────────────────────────┘                  │
│  ┌────────────────────────────────────────┐                  │
│  │ 💔 Health · Illness risk [Window: 48-51]│ [Possible]      │
│  │ "Saturn-Rahu conjunction in H6..."     │ Prob: 45%        │
│  └────────────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Accessibility Requirements

- All interactive elements have unique `id` attributes (for browser testing)
- All input fields have `aria-label` or associated `<label>`
- Color is not the only means of conveying information (use icons + text)
- Focus ring visible on all focusable elements (`outline` not removed)
- Loading states announced via `aria-live="polite"`
- ESC key closes modals/dropdowns

---

## 7. Responsive Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | < 640px | Sidebar hidden (hamburger), tabs scroll horizontally |
| Tablet | 640–1024px | Sidebar overlay, 2-column grids in panels |
| Desktop | > 1024px | Sidebar always visible, full layout |

```css
/* Breakpoints */
--bp-sm: 640px;
--bp-md: 768px;
--bp-lg: 1024px;
--bp-xl: 1280px;
```
