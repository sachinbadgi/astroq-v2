---
name: to-prd
description: Structured requirement generation. Use when you have research notes, forensic output, or unstructured ideas that need to be turned into a Product Requirements Document (PRD).
---

# To PRD

## Overview
Turns messy research and "vibe-based" requirements into a rigorous, actionable Product Requirements Document.

## When to Use
- You've just finished a research session (e.g., `forensic_output.txt`).
- You have a bunch of ideas for a new feature but no clear structure.
- You want to ensure "feature parity" with a canonical standard (Goswami 1952).

## PRD Structure
Every PRD generated must include:
1. **Summary**: What are we building and why?
2. **Success Criteria**: How do we know it works? (e.g., "100% parity on test set X").
3. **User Stories**: Functional requirements from the perspective of the end user or agent.
4. **Technical Constraints**: Performance, memory, or logical boundaries.
5. **Out of Scope**: What are we NOT doing? (Crucial for preventing scope creep).

## The Process
1. **Digest**: Read all provided research notes.
2. **Glossary Check**: Cross-reference all findings with [ubiquitous_language.md](file:///Users/sachinbadgi/Documents/lal_kitab/astroq-v2/ubiquitous_language.md).
3. **Categorize**: Group requirements by domain (Predictive, Mathematical, UI).
4. **Synthesize**: Write the PRD in a clean, versioned Markdown file.

## HARD-GATE
**Do NOT start implementation until the PRD has been reviewed and approved.**
