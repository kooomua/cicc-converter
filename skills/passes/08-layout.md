Purpose: repair local layout problems only after compilation succeeds.

Scope:
- equation over-width
- figure width/caption placement
- table width/caption placement
- two-column float issues

Rules:
- Do not edit scientific content.
- Do not rewrite the whole TeX document.
- Only patch the local equation, figure, or table block that triggered the issue.

Output:
- PASS when targeted layout warnings are resolved.
- WARNING when residual review is acceptable.
- FAIL when layout repair breaks compilation.
