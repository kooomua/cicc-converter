Purpose: final package quality gate.

Checks:
- `.tex` exists.
- `.pdf` exists after evaluation.
- `cicc.cls` and `cicc.bst` exist.
- referenced figure files exist.
- bibliography data exists when citations exist.
- output zip is created.

Output:
- PASS when the package is usable.
- WARNING when non-blocking quality issues remain.
- FAIL when an essential output artifact is missing.
