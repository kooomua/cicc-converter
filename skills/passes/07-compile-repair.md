Purpose: repair only LaTeX compile errors after focused passes.

Scope:
- fatal LaTeX errors
- missing local packages caused by generated syntax
- command conflicts

Rules:
- Do not reconvert the manuscript.
- Make the smallest local TeX change that restores compilation.
- Preserve references, figures, tables, and frontmatter unless the compile error is inside that local block.

Output:
- PASS when compilation succeeds.
- FAIL when fatal errors remain.
