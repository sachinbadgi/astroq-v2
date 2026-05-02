---
name: to-issues
description: Breakdown of PRDs into actionable tasks. Use when you have an approved PRD and need a step-by-step implementation list or GitHub issues.
---

# To Issues

## Overview
Decomposes high-level requirements into small, atomic tasks that can be executed independently.

## When to Use
- You have an approved PRD.
- You are ready to start coding but need a "To-Do" list.

## Issue Quality Standards
Every "issue" or "task" must have:
- **Title**: Action-oriented (e.g., "Implement Sun/Venus Entanglement logic").
- **Description**: What needs to be done.
- **Acceptance Criteria**: How to verify the task is complete (e.g., "Run test_entanglement.py").
- **Dependencies**: Which other tasks must be finished first.

## Process
1. Analyze the PRD.
2. Identify independent components.
3. Order tasks logically (Data Layer -> Logic Layer -> UI).
4. Present as a Markdown task list or ready-to-paste GitHub issues.
