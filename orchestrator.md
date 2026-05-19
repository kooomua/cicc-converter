# CiCC Pipeline Orchestrator Guide

## Pipeline Flow

```
[input/]
   │
   ▼
STEP 1 — Inspector
   │  Produces: run_log/TIMESTAMP/inspection_report.json
   │
   ▼ ── USER CONFIRMATION GATE ──────────────────────────────────────
   │  Review inspection report. Confirm file list, EMF flags, path.
   │  Type "proceed" to continue, or "abort" to stop.
   ▼
STEP 2 — Converter
   │  Produces: run_log/TIMESTAMP/converted/ (full .tex package)
   │
   ▼ ── USER CONFIRMATION GATE ──────────────────────────────────────
   │  Review the converted .tex file. Confirm it looks correct.
   │  Type "proceed" to continue, or "retry" to rerun Converter.
   ▼
STEP 3 — Evaluator
   │  Produces: run_log/TIMESTAMP/eval_report.json + compile log
   │
   ▼ ── USER DECISION ───────────────────────────────────────────────
      "approve"          → zip converted/ into output/, done
      "rerun_converter"  → return to Step 2
      "rerun_inspector"  → return to Step 1
```

---

## Starting a Run

1. Place all source files in `input/`:
   - Manuscript: `.docx` and/or `.tex`
   - Figures: `.pdf`, `.eps`, `.png`, `.jpg`, or `.emf`
   - Bibliography: `.bib` (if available)
2. Note the run timestamp you will use: `YYYYMMDD_HHMMSS`
3. Invoke the Inspector: **"run agents/inspector.md on the input/ folder"**

---

## Input Path Decision Logic

The Inspector determines which conversion path to use:

| Situation | Decision |
|---|---|
| Only `.docx` present | Use `cicc-latex` skill |
| Only `.tex` present (no `.docx`) | Use `cicc-reformat` skill |
| Both `.docx` and `.tex` present | **Ask the user** which to use before continuing |
| Neither present | Abort and report error |

---

## Agent Invocation

Each agent is invoked by referring the Claude Code agent to the agent prompt file and the current run's working folder:

- **Inspector:** "run agents/inspector.md on the input/ folder, write report to run_log/TIMESTAMP/"
- **Converter:** "run agents/converter.md using run_log/TIMESTAMP/inspection_report.json, write output to run_log/TIMESTAMP/converted/"
- **Evaluator:** "run agents/evaluator.md on run_log/TIMESTAMP/converted/, write report to run_log/TIMESTAMP/eval_report.json"

---

## Handoff Between Agents

Each agent reads from and writes to a timestamped subfolder under `run_log/`:

```
run_log/
└── 20260508_143022/
    ├── inspection_report.json    ← written by Inspector, read by Converter
    ├── converted/                ← written by Converter, read by Evaluator
    │   ├── manuscript.tex
    │   ├── figures/
    │   └── refs.bib
    ├── eval_report.json          ← written by Evaluator
    └── compile.log               ← written by compile_check.sh
```

All agents use the same `run_id` (the timestamp string) throughout a run.

---

## Retry Logic

If the Evaluator reports `"overall_result": "fail"`:

- **`recommended_action: "rerun_converter"`** — Return to Step 2. The Converter re-reads the same `inspection_report.json` and produces a new `converted/` folder. Use a new timestamp or a suffix (e.g., `_r2`) to avoid overwriting.
- **`recommended_action: "rerun_inspector"`** — Return to Step 1. Something fundamental is wrong with the input; the Inspector needs to re-examine it.
- **`recommended_action: "approve"`** — Only warnings, no blocking issues; user may choose to approve anyway.

The user always makes the final call. The Evaluator's `recommended_action` is a suggestion, not a command.
