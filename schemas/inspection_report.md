# Inspector Output Schema

The Inspector agent must write its output as valid JSON conforming to this schema.
File location: `run_log/TIMESTAMP/inspection_report.json`

## Schema

```json
{
  "run_id": "YYYYMMDD_HHMMSS",
  "input_type": "docx | tex | mixed | unknown",
  "files_found": [
    {
      "filename": "manuscript.docx",
      "type": "docx | tex | bib | figure_pdf | figure_emf | figure_raster | other",
      "status": "usable | needs_conversion | irrelevant"
    }
  ],
  "missing_files": [
    "figure2.pdf"
  ],
  "emf_files": [
    "scheme1.emf"
  ],
  "figures_referenced_but_missing": [
    "figure3.pdf"
  ],
  "recommended_path": "cicc-latex | cicc-reformat",
  "ready_to_convert": true,
  "notes": "Free text. List anything unusual, ambiguous, or requiring user attention before conversion begins."
}
```

## Field Definitions

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Timestamp of this run in `YYYYMMDD_HHMMSS` format. Shared across all agents in the same run. |
| `input_type` | enum | `"docx"` — only Word file present; `"tex"` — only .tex file present; `"mixed"` — both present; `"unknown"` — neither found |
| `files_found` | array | Every file found in `input/`, one entry each |
| `files_found[].filename` | string | Bare filename including extension |
| `files_found[].type` | enum | Semantic type of the file |
| `files_found[].status` | enum | `"usable"` — ready to use as-is; `"needs_conversion"` — e.g. EMF must become PDF; `"irrelevant"` — not needed for conversion |
| `missing_files` | array | Filenames that would normally be expected (e.g. a `.bib` file) but were not found. May be empty. |
| `emf_files` | array | Filenames of any `.emf` images found. These must be converted before LaTeX compilation. May be empty. |
| `figures_referenced_but_missing` | array | Figure filenames cited in the manuscript body (via `\includegraphics` or Word figure references) but absent from `input/`. Blocks conversion if non-empty unless user confirms. |
| `recommended_path` | enum | `"cicc-latex"` if source is `.docx`; `"cicc-reformat"` if source is `.tex` |
| `ready_to_convert` | boolean | `true` if conversion can proceed without user intervention; `false` if there are blockers (missing figures, EMF files not yet converted, ambiguous input type, etc.) |
| `notes` | string | Any additional observations. Required field; use `""` if nothing to report. |

## Notes

- If `input_type` is `"mixed"`, set `ready_to_convert` to `false` and explain in `notes` that the user must choose a path.
- If `figures_referenced_but_missing` is non-empty, set `ready_to_convert` to `false`.
- If `emf_files` is non-empty, note whether `extract_images.py` has already been run and whether PDF versions exist.
