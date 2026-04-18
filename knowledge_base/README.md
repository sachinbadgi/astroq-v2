# LLM Knowledge Base

This directory uses the **LLM Wiki** pattern (popularized by Andrej Karpathy) for managing domain knowledge, rules, and documentation.

## Structure

- `/sources/`: Raw, immutable files (e.g., transcripts, old notes, PDFs, or code dumps). You drop files here and we never modify them.
- `/wiki/`: The cleanly compiled, formatted, and cross-referenced Markdown files. I (your agent) am responsible for creating and maintaining these whenever new sources are added.

## Workflow

1. **Add Sources**: Drop any new raw Lal Kitab rules, charts, or documentation into `sources/`.
2. **Compile**: Tell me to "compile the knowledge base", and I will read the new sources and synthesize the information into the `wiki/` directory, updating existing pages or creating new ones.
3. **Reference**: As we code the `astroq-v2` prediction engine, we rely on the structured `wiki/` for our source of truth.
