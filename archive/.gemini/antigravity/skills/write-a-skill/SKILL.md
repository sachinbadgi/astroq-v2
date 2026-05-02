---
name: write-a-skill
description: Self-evolving skill generation. Use when you identify a recurring pattern or technique in your workflow that should be documented as a skill.
---

# Write a Skill

## Overview
Automates the creation of new Antigravity skills following the "Matt Pocock" best practices (Folder structure, Reference, Examples).

## When to Use
- You find yourself explaining the same thing to the agent repeatedly.
- You have a new domain-specific technique (e.g., "Analyzing Lal Kitab Masnui Entanglement").
- You want to standardize a project-specific workflow.

## The Folder Pattern
Every skill must be a directory:
- `SKILL.md`: The trigger-based capability doc.
- `REFERENCE.md`: Deep dives and technical specs.
- `EXAMPLES.md`: Good/Bad examples to guide the model.

## The Trigger Pattern
The description in `SKILL.md` MUST follow:
`[Capability Description]. Use when [Keywords and Triggers].`

## Process
1. Identify the recurring pattern.
2. Draft the `SKILL.md` with clear triggers.
3. Create the directory and files.
4. Test the skill by asking the agent to perform the task.
