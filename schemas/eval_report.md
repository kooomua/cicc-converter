# Evaluator Output Schema

The Evaluator agent must write its output as valid JSON conforming to this schema.
File location: `run_log/TIMESTAMP/eval_report.json`

## Schema

```json
{
  "run_id": "YYYYMMDD_HHMMSS",
  "overall_result": "pass | fail",
  "static_checks": [
    {
      "rule": "Title case for paper title",
      "status": "pass | fail | warning",
      "detail": "Optional explanation, required when status is fail or warning."
    }
  ],
  "compile_result": "success | errors | warnings_only | not_attempted",
  "compile_errors": [
    {
      "line": 42,
      "message": "Undefined control sequence \\foo"
    }
  ],
  "compile_warnings": [
    {
      "line": 87,
      "message": "Overfull \\hbox (12.3pt too wide)"
    }
  ],
  "issues_to_fix": [
    {
      "severity": "critical | major | minor",
      "description": "Citation appears after period on line 103",
      "location": "line 103 / Section 2.1"
    }
  ],
  "recommended_action": "approve | rerun_converter | rerun_inspector",
  "notes": "Free text summary for the user."
}
```

## Field Definitions

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Must match the `run_id` from the corresponding `inspection_report.json` |
| `overall_result` | enum | `"pass"` — no critical or major issues, compilation succeeded; `"fail"` — one or more critical/major issues or compilation errors |
| `static_checks` | array | One entry per CiCC formatting rule checked. See `skills/cicc-rules.md` for the full rule list. |
| `static_checks[].rule` | string | Short name of the rule being checked |
| `static_checks[].status` | enum | `"pass"`, `"fail"`, or `"warning"` (possible issue but not definitively wrong) |
| `static_checks[].detail` | string | Explanation of failure or warning. Use `""` when status is `"pass"`. |
| `compile_result` | enum | `"success"` — pdflatex exited cleanly; `"errors"` — compile errors present; `"warnings_only"` — compiled but with warnings; `"not_attempted"` — compile was skipped (e.g. missing figures) |
| `compile_errors` | array | Errors extracted from the pdflatex log. May be empty. |
| `compile_errors[].line` | integer | Line number in the `.tex` file, or `0` if not determinable |
| `compile_errors[].message` | string | Error message text |
| `compile_warnings` | array | Warnings extracted from the pdflatex log. May be empty. |
| `compile_warnings[].line` | integer | Line number, or `0` if not determinable |
| `compile_warnings[].message` | string | Warning message text |
| `issues_to_fix` | array | Consolidated list of all actionable problems, across both static checks and compilation. May be empty if `overall_result` is `"pass"`. |
| `issues_to_fix[].severity` | enum | `"critical"` — blocks approval; `"major"` — should be fixed; `"minor"` — cosmetic or low-priority |
| `issues_to_fix[].description` | string | Clear description of what is wrong |
| `issues_to_fix[].location` | string | Where in the document the issue occurs (line number, section, figure label, etc.) |
| `recommended_action` | enum | `"approve"` — output is acceptable; `"rerun_converter"` — conversion errors fixable by re-running Converter; `"rerun_inspector"` — fundamental input problem requires re-inspection |
| `notes` | string | Human-readable summary. Required; use `""` if nothing to add. |

## Decision Logic for `overall_result`

- `"fail"` if any `static_checks[].status` is `"fail"` with severity `critical` or `major`, OR if `compile_result` is `"errors"`
- `"pass"` if `compile_result` is `"success"` or `"warnings_only"` AND no `critical`/`major` static check failures
- When in doubt, prefer `"fail"` and document the issue in `notes`
