Purpose: validate and repair only CiCC front matter.

Scope:
- `\title`
- `\author`
- `\affil`
- article metadata before `\begin{document}`
- `\maketitle` inside the opening `\twocolumn[{...}]` block

Rules:
- Do not edit body paragraphs, figures, equations, tables, or references.
- `\title`, all `\author`, and all `\affil` commands must remain before `\begin{document}`.
- Preserve the fixed CiCC opening frame unless a local frontmatter field is missing or misplaced.

Output:
- PASS when the frontmatter frame is valid.
- WARNING when fields are placeholders but not fatal.
- FAIL when required frontmatter structure is missing.
