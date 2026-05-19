from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


GRAPHICS_RE = re.compile(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^{}]+)\}")
DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{([^{}]+)\}")
DOCUMENTCLASS_FULL_RE = re.compile(r"\\documentclass(?:\[([^\]]*)\])?\{([^{}]+)\}")


def strip_tex_comments(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        escaped = False
        cut_at: int | None = None
        for index, char in enumerate(line):
            if char == "\\":
                escaped = not escaped
                continue
            if char == "%" and not escaped:
                cut_at = index
                break
            escaped = False
        if cut_at is None:
            cleaned_lines.append(line)
        else:
            newline = "\n" if line.endswith("\n") else ""
            cleaned_lines.append(line[:cut_at] + newline)
    return "".join(cleaned_lines)


def classify_file(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return "docx", "usable"
    if suffix == ".tex":
        return "tex", "usable"
    if suffix == ".bib":
        return "bib", "usable"
    if suffix in {".cls", ".bst"}:
        return "class_style", "usable"
    if suffix in {".pdf", ".eps"}:
        return "figure_pdf", "usable"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "figure_raster", "usable"
    if suffix in {".emf", ".wmf"}:
        return "figure_emf", "needs_conversion"
    if suffix in {".xlsx", ".csv"}:
        return "data", "irrelevant"
    return "other", "irrelevant"


def find_missing_graphics(tex_file: Path, input_dir: Path) -> list[str]:
    try:
        text = tex_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = tex_file.read_text(encoding="latin-1")

    missing: list[str] = []
    for match in GRAPHICS_RE.finditer(strip_tex_comments(text)):
        raw = match.group(1).strip()
        graphic = Path(raw)
        candidates: list[Path] = []
        if graphic.suffix:
            candidates.append(input_dir / graphic.name)
            candidates.append(input_dir / raw)
            candidates.append(input_dir / "figures" / graphic.name)
        else:
            for suffix in (".pdf", ".eps", ".png", ".jpg", ".jpeg"):
                candidates.append(input_dir / f"{graphic.name}{suffix}")
                candidates.append((input_dir / raw).with_suffix(suffix))
                candidates.append(input_dir / "figures" / f"{graphic.name}{suffix}")
        if not any(candidate.exists() for candidate in candidates):
            missing.append(raw)
    return sorted(set(missing))


def read_tex_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def tex_candidate_score(path: Path) -> dict[str, Any]:
    text = read_tex_text(path)
    name = path.name.lower()
    stem = path.stem.lower()
    score = 0
    reasons: list[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(f"{points:+d} {reason}")

    if name in {"main.tex", "manuscript.tex", "article.tex", "paper.tex"}:
        add(90, f"primary-looking filename ({path.name})")
    elif stem.startswith(("main", "manuscript", "article", "paper")):
        add(35, f"main-article-like filename ({path.name})")

    if re.search(r"\b(si|supp|support|supplement|supplementary)\b", stem):
        add(-110, "supplementary/SI-looking filename")
    if re.search(r"\b(cover|reply|response|rebuttal|letter)\b", stem):
        add(-120, "cover/reply/response-looking filename")
    if re.search(r"\b(marked|track|redline|changes?)\b", stem):
        add(-50, "marked/change-tracked-looking filename")
    if stem.endswith("_last") or stem.endswith("-last") or stem.endswith("last"):
        add(-15, "backup/final-copy-looking filename; prefer canonical main file when present")

    class_match = DOCUMENTCLASS_FULL_RE.search(text)
    class_options = class_match.group(1).lower() if class_match and class_match.group(1) else ""
    class_name = class_match.group(2).strip() if class_match else ""
    if class_match:
        add(35, f"has documentclass ({class_name})")
    if "suppinfo" in class_options or "supplement" in class_options:
        add(-120, "documentclass options indicate supporting information")

    signals = {
        "has_begin_document": r"\begin{document}" in text,
        "has_title": r"\title" in text,
        "has_author": r"\author" in text,
        "has_abstract": r"\begin{abstract}" in text,
        "has_keywords": r"\keywords" in text or "keywords" in text.lower(),
        "has_sections": bool(re.search(r"\\section\*?\{", text)),
        "has_figures": r"\includegraphics" in text,
        "has_tables": r"\begin{table" in text or r"\begin{tabular" in text,
        "has_bibliography": r"\bibliography" in text or r"\begin{thebibliography}" in text,
    }
    signal_points = {
        "has_begin_document": 30,
        "has_title": 35,
        "has_author": 35,
        "has_abstract": 35,
        "has_keywords": 20,
        "has_sections": 30,
        "has_figures": 10,
        "has_tables": 10,
        "has_bibliography": 25,
    }
    for key, present in signals.items():
        if present:
            add(signal_points[key], key.replace("_", " "))

    char_count = len(text)
    if char_count >= 100_000:
        add(30, "long manuscript-sized TeX source")
    elif char_count >= 50_000:
        add(20, "medium manuscript-sized TeX source")
    elif char_count >= 10_000:
        add(10, "substantial TeX source")
    else:
        add(-20, "short TeX source")

    if not signals["has_begin_document"]:
        add(-50, "missing begin document")
    if not signals["has_sections"]:
        add(-30, "missing section commands")

    return {
        "filename": path.name,
        "score": score,
        "class_name": class_name,
        "char_count": char_count,
        "signals": signals,
        "reasons": reasons,
    }


def rank_tex_candidates(tex_files: list[Path]) -> list[dict[str, Any]]:
    candidates = [tex_candidate_score(path) for path in tex_files]
    return sorted(candidates, key=lambda item: (-item["score"], item["filename"].lower()))


def classify_tex_quality(tex_file: Path) -> dict[str, Any]:
    text = read_tex_text(tex_file)
    class_match = DOCUMENTCLASS_RE.search(text)
    class_name = class_match.group(1).strip() if class_match else ""

    signals = {
        "has_documentclass": bool(class_match),
        "class_name": class_name,
        "has_title": r"\title" in text,
        "has_author": r"\author" in text,
        "has_affiliation": r"\affil" in text or r"\institute" in text or r"\address" in text,
        "has_abstract": r"\begin{abstract}" in text,
        "has_keywords": r"\keywords" in text or "keywords" in text.lower(),
        "has_sections": bool(re.search(r"\\section\*?\{", text)),
        "has_figures": r"\includegraphics" in text,
        "has_tables": r"\begin{table" in text or r"\begin{tabular" in text,
        "has_bibliography": r"\bibliography" in text or r"\begin{thebibliography}" in text,
        "custom_macro_count": len(re.findall(r"\\(?:newcommand|renewcommand|def)\b", text)),
    }

    reasons: list[str] = []
    structural_score = sum(
        1
        for key in (
            "has_title",
            "has_author",
            "has_abstract",
            "has_sections",
            "has_bibliography",
        )
        if signals[key]
    )

    if class_name.lower() in {"cicc", "cicc0509"} and structural_score >= 4:
        quality = "cicc_like"
        reasons.append(f"Uses CiCC document class ({class_name}) and has standard article structure.")
    elif signals["has_documentclass"] and signals["has_sections"] and structural_score >= 3:
        quality = "structured_non_cicc"
        reasons.append(f"Uses non-CiCC document class ({class_name}) but has recognizable article structure.")
    else:
        quality = "messy"
        reasons.append("Missing enough standard LaTeX article markers for deterministic baseline conversion.")

    if signals["custom_macro_count"] >= 20:
        reasons.append(f"Many custom macros detected ({signals['custom_macro_count']}); IR extraction may be safer.")
        if quality == "cicc_like":
            quality = "structured_non_cicc"

    return {
        "quality": quality,
        "signals": signals,
        "reasons": reasons,
    }


def inspect_input(
    job_root: Path,
    manuscript_id: str,
    primary_source: str | None = None,
) -> dict[str, Any]:
    input_dir = job_root / "input"
    run_log_dir = job_root / "run_log"
    run_log_dir.mkdir(parents=True, exist_ok=True)

    files = [p for p in input_dir.iterdir() if p.is_file()]
    files_found = []
    for path in sorted(files):
        file_type, status = classify_file(path)
        files_found.append({"filename": path.name, "type": file_type, "status": status})

    docx_files = [p for p in files if p.suffix.lower() == ".docx"]
    tex_files = [p for p in files if p.suffix.lower() == ".tex"]
    emf_files = [p.name for p in files if p.suffix.lower() in {".emf", ".wmf"}]

    notes: list[str] = []
    missing_files: list[str] = []
    figures_missing: list[str] = []
    tex_quality_report: dict[str, Any] | None = None
    tex_file_candidates: list[dict[str, Any]] = []
    ready = True

    if not files:
        input_type = "unknown"
        recommended_path = "unknown"
        ready = False
        notes.append("Input folder is empty.")
    elif docx_files and tex_files:
        if primary_source == "docx":
            input_type = "docx"
            recommended_path = "cicc-latex"
            notes.append("Both docx and tex were uploaded; primary_source=docx was selected.")
        elif primary_source == "tex":
            input_type = "tex"
            recommended_path = "cicc-reformat"
            notes.append("Both docx and tex were uploaded; primary_source=tex was selected.")
        else:
            input_type = "tex"
            recommended_path = "cicc-reformat"
            notes.append("Both .docx and .tex files were found; defaulting to the tex route.")
    elif docx_files:
        input_type = "docx"
        recommended_path = "cicc-latex"
    elif tex_files:
        input_type = "tex"
        recommended_path = "cicc-reformat"
    else:
        input_type = "unknown"
        recommended_path = "unknown"
        ready = False
        notes.append("No manuscript file (.docx or .tex) found.")

    if tex_files:
        tex_file_candidates = rank_tex_candidates(tex_files)
        primary_name = tex_file_candidates[0]["filename"]
        primary_tex = next(p for p in tex_files if p.name == primary_name)
        tex_quality_report = classify_tex_quality(primary_tex)
        figures_missing = find_missing_graphics(primary_tex, input_dir)
        if figures_missing:
            notes.append(
                "Some graphics referenced by the TeX file are missing; continuing so converter/repairer can handle them."
            )

    unconverted_emf = []
    for name in emf_files:
        if not (input_dir / Path(name).with_suffix(".pdf").name).exists():
            unconverted_emf.append(name)
    if unconverted_emf:
        notes.append("EMF/WMF files were found without matching PDFs; continuing and reporting them downstream.")

    report = {
        "run_id": job_root.name,
        "manuscript_id": manuscript_id,
        "input_type": input_type,
        "files_found": files_found,
        "missing_files": missing_files,
        "emf_files": emf_files,
        "figures_referenced_but_missing": figures_missing,
        "recommended_path": recommended_path,
        "primary_tex_file": tex_quality_report and primary_tex.name if tex_files else None,
        "tex_file_candidates": tex_file_candidates,
        "tex_quality": tex_quality_report["quality"] if tex_quality_report else None,
        "tex_quality_signals": tex_quality_report["signals"] if tex_quality_report else {},
        "tex_quality_reasons": tex_quality_report["reasons"] if tex_quality_report else [],
        "ready_to_convert": ready,
        "notes": " ".join(notes) if notes else "Ready to convert.",
    }

    (run_log_dir / "inspection_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    handoff = [
        "# Inspector Handoff",
        "",
        f"Manuscript: {manuscript_id}",
        f"Input type: {input_type}",
        f"Recommended path: {recommended_path}",
        f"TeX quality: {report['tex_quality'] or 'n/a'}",
        f"Ready to convert: {'yes' if ready else 'no'}",
        "",
        "## Files",
    ]
    for item in files_found:
        handoff.append(f"- {item['filename']} | {item['type']} | {item['status']}")
    handoff.extend(["", "## Notes", report["notes"]])
    if report["tex_quality_reasons"]:
        handoff.extend(["", "## TeX quality reasons"])
        handoff.extend(f"- {reason}" for reason in report["tex_quality_reasons"])
    if report["tex_file_candidates"]:
        handoff.extend(["", "## TeX file candidates"])
        for candidate in report["tex_file_candidates"]:
            handoff.append(
                f"- {candidate['filename']} | score {candidate['score']} | class {candidate.get('class_name') or 'n/a'}"
            )
    (run_log_dir / "inspector_handoff.md").write_text("\n".join(handoff), encoding="utf-8")
    return report
