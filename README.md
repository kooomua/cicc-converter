# CiCC converter

Local browser app for converting CiCC manuscript inputs into a LaTeX/PDF output package.

## Current Scope

Supported inputs:

- Word `.docx`
- Existing LaTeX `.tex`
- ZIP files containing manuscript sources, figures, and bibliography files

Active pipeline:

```text
Inspector
→ Converter
→ postprocess
→ Evaluator
→ AI compile repair when needed
→ evaluator-based equation/figure/table layout repair when needed
→ output zip
```

Not active:

- PDF screenshot / visual QA
- IR conversion route
- Multi-user account system
- Database-backed job history

## Runtime Dependencies

Required local tools:

- Python 3.10+
- `pdflatex`
- `bibtex`
- `pandoc`
- LibreOffice `soffice` for converting `.emf/.wmf` images to PDF
- ImageMagick `magick` or `convert` for converting `.tif/.tiff` images to PNG

Python dependencies are listed in `requirements.txt`.

## Local Start

```bash
cd /Users/komachen/Documents/Claude/VScode_AIediting/cicc-pipeline
bash scripts/start_local.sh
```

Then open:

```text
http://localhost:8000
```

## Configuration

Copy `.env.example` to `.env`, then fill in the API key and model settings.

Important settings:

```env
CICC_LLM_API_KEY=replace_me
CICC_LLM_BASE_URL=https://api.deepseek.com
CICC_LLM_MODEL=deepseek-v4-pro
CICC_LLM_API_STYLE=chat
CICC_MAX_CONVERSION_ATTEMPTS=2
CICC_MAX_REPAIR_ATTEMPTS=3
CICC_EVAL_LAYOUT_REPAIR_ENABLED=true
CICC_MAX_LAYOUT_REPAIR_ATTEMPTS=1
```

## Output

Each job creates:

```text
jobs/<job_id>/
  input/
  output/
  run_log/
  status.json
  <manuscript_id>_output.zip
```

The zip contains the generated `.tex`, compiled `.pdf`, `cicc.cls`, `cicc.bst`, logs, converted figures, and original source images kept as backup/reference.

Special image formats are handled as follows:

- `.tif/.tiff` files are converted to `.png` under `figures/`.
- `.emf/.wmf` files are converted to `.pdf` under `figures/`.
- Original `.tif/.tiff/.emf/.wmf` files are preserved under `original_figures/`.
- `IMAGE_CONVERSION_NOTES.txt` records the conversion mapping.

## Acceptance Standard

The current evaluator is intentionally practical:

- PDF must be generated.
- CiCC frame must be present.
- Required figures must exist in usable formats.
- Major visual-perfect checks are not blocking.
- Small overfull boxes, float placement, section-title case, and similar formatting issues are warnings.

This matches the current production goal: produce a usable CiCC package first, then improve layout quality iteratively.
