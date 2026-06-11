Purpose: validate and repair headings, abstract, and keywords.

Scope:
- abstract text
- `\keywords{...}`
- `\section`, `\subsection`, and `\subsubsection` headings

Rules:
- Do not edit references, figures, tables, equations, or author metadata.
- Section headings should use sentence case: capitalize the first word and proper nouns/acronyms only.
- `\keywords{PLACEHOLDER.}` is not acceptable when source keywords are available.
- If source keywords are unavailable, leave a warning instead of inventing keywords.

Output:
- PASS when abstract/keywords/headings are usable.
- WARNING when keywords are missing from the source.
- FAIL when required heading or abstract structure is broken.
