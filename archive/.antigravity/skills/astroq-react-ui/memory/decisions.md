# Architectural Decisions — astroq-react-ui

Settled decisions. Do NOT re-debate these.

---

## DEC-001: Stack Choice
**Decision**: Vite + React + TypeScript + Vanilla CSS (CSS custom properties)
**Rationale**: Old UI used Tailwind which caused 867-line App.tsx with utility sprawl. CSS custom properties give us a clean design system that's more readable. Vite provides fast HMR. TypeScript ensures type safety for API contracts.
**Date**: 2026-03-22

---

## DEC-002: Test Framework
**Decision**: Vitest + @testing-library/react + jsdom
**Rationale**: Vitest is Vite-native (same config), faster than Jest for this monorepo structure. React Testing Library promotes testing behavior over implementation.
**Date**: 2026-03-22

---

## DEC-003: Backend Target
**Decision**: New frontend initially targets OLD backend at `localhost:8000`
**Rationale**: New `d:/astroq-v2/backend` does not yet expose a REST API. All API routes defined in `src/api/client.ts` with `// TODO: migrate to new backend` comments.
**Date**: 2026-03-22

---

## DEC-004: Charts Library
**Decision**: Recharts for all charts/graphs
**Rationale**: Old UI already used Recharts in RemedySimulator. Familiarity, good TypeScript support, composable API. Chart3D (Three.js) to be re-evaluated as optional lazy-loaded tab.
**Date**: 2026-03-22

---

## DEC-005: Component Granularity
**Decision**: One file per component, no giant monolith
**Rationale**: Old App.tsx was 867 lines. New architecture: each component its own file, own test file. App.tsx only wires them together.
**Date**: 2026-03-22

---

## DEC-006: New Tab — Prediction Dashboard
**Decision**: Add a `prediction` tab that exposes `lk_prediction` pipeline output
**Rationale**: The new backend's core value is the `lk_prediction` engine. The old UI had no way to visualize its output. This tab is the primary new feature of V2.
**Date**: 2026-03-22

---

## DEC-007: Drop MASF Tab (for now)
**Decision**: MASF Graph tab is omitted from V2 initial build
**Rationale**: `/masf/analyze` endpoint exists only in old backend and uses heavy multi-agent infrastructure not yet ported. The Prediction Dashboard covers the same use case more cleanly.
**Can re-add if**: MASF is ported to new backend.
**Date**: 2026-03-22

---

## DEC-008: Color Theme
**Decision**: Dark cosmic theme (deep indigo/purple-black) with violet/pink accents, gold highlights
**Rationale**: Matches AstroQ brand identity from old UI. Colors mapped to CSS custom properties: `--bg-deep`, `--bg-card`, `--bg-elevated`, `--border`, `--accent-violet`, `--accent-pink`, `--accent-gold`, `--text-primary`, `--text-muted`.
**Date**: 2026-03-22
