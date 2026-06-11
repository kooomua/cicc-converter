# CiCC Converter Architecture

The project is a browser-based manuscript converter. It prioritizes producing a
usable CiCC LaTeX/PDF package first, then records focused quality checks for
iteration.

## Runtime Flow

```text
Browser upload
→ FastAPI job
→ Inspector
→ Main Converter AI
→ Conversion Pass Runner
→ postprocess
→ Evaluator
→ AI compile repair, only if needed
→ evaluator-based equation/figure/table repair, only if needed
→ package zip
```

## Main Components

- `app/main.py`: web routes, upload endpoint, job status, and download endpoint.
- `app/inspector.py`: reads uploaded files and decides whether the source route
  is Word-to-CiCC or TeX-to-CiCC.
- `app/openai_converter.py`: main AI conversion step. This still creates the
  first complete `.tex` draft.
- `app/conversion_passes.py`: pass-based audit and small local repairs after the
  first AI draft.
- `app/postprocess.py`: deterministic cleanup applied after conversion and
  repair steps.
- `app/evaluator.py`: static checks, PDF compilation, image conversion support,
  and reference sanity checks.
- `app/latex_repairer.py`: AI compile repair when evaluator reports fatal
  LaTeX problems.
- `app/layout_repairer.py`: targeted equation/figure/table repair when the
  evaluator reports layout warnings.

## Conversion Passes

The pass runner does not replace the main Converter. It makes the Converter
output auditable and applies narrow fixes that are safer than asking AI to
rewrite the whole article.

```text
00-preflight
01-frontmatter
02-heading-keyword
03-body-paragraph
04-equation
05-figure-table
06-reference
07-compile-repair
08-layout
09-final
```

For every job attempt, pass output is written under:

```text
jobs/<job_id>/run_log/attempt_<n>/passes/
  pass_report.json
  pass_report.md
  00-preflight-audit.md
  01-frontmatter-audit.md
  ...
  09-final-audit.md
```

Each audit file records:

- checked items;
- violations;
- fixes applied;
- human-review items;
- final pass result.

## Current Design Boundary

Current behavior:

- one main AI converter generates the full `.tex`;
- pass runner performs deterministic checks and small local fixes;
- compile repair AI is only called if LaTeX compilation fails;
- layout repair AI is only called for evaluator-reported equation/figure/table
  warnings.

Not current behavior:

- separate AI calls for every pass;
- PDF screenshot visual QA;
- database-backed job history;
- multi-user account system.

This design keeps the automatic web workflow stable while making future
reference, equation, figure, table, or layout rules easier to improve
independently.
