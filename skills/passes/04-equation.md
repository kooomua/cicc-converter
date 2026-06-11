Purpose: validate and repair equations.

Scope:
- inline formulas
- display equations
- multiline equations
- equation labels and references

Rules:
- Do not edit prose, references, tables, figures, or frontmatter except for required math packages.
- Avoid `$$...$$` and `eqnarray`.
- Split long equations for two-column layout when needed.

Output:
- PASS when equations compile and are structurally acceptable.
- WARNING for possible layout concerns.
- FAIL for broken math environments or missing required packages.
