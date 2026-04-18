# Foundational Source: B.M. Goswami (1952)

The core logical foundation for the entire `astroq-v2` backend is derived from **Jyotish Lal Kitab (1952 Edition)** by B.M. Goswami.

To maintain the architectural integrity of this knowledge base, the original raw PDF has been securely archived in our sources directory:
`sources/Jyotish_Lal Kitab_B.M. Gosvami 1952.pdf`

*Note: We do not duplicate the hundreds of pages of textual astrological definitions from the PDF here. Doing so would violate the DRY (Don't Repeat Yourself) principle of our parsed architecture.*

Instead, the abstract knowledge from this book has been explicitly "compiled" into strictly deterministic, language-agnostic components mapping directly to our codebase:

### Where to find Goswami's concepts in the Wiki:
- **[[AstrologicalConstants]]**: Contains the hard-coded data tables for Dignities (Pakka Ghars), Aspect strengths, and 35-year/75-year matrices derived from the book.
- **[[RulesAndRemedies]]**: Contains the Goswami Priority ranking algorithms and how we evaluate the "If/Then" sentence structures dynamically.
- **[[DatabaseSchema]]**: Holds the SQL formatting and JSON AST representations for every individual Lal Kitab deterministic rule.

If you ever need to add new rules from the PDF:
1. Do not rewrite them as plain text here.
2. Read the PDF.
3. Formulate the JSON AST payloads as defined in `DatabaseSchema`.
4. Insert them directly into `rules.db`.

This ensures the book serves as **Ground Truth** and the code/Wiki serve as the **Deterministic Execution** of that truth.
