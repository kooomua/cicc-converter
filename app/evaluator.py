from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .bib_normalizer import normalize_bib_files
from .config import BIBTEX_BIN, PDFLATEX_BIN, PROJECT_ROOT


FIGURE_SUFFIXES = {".pdf", ".eps", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".emf", ".wmf"}


def libreoffice_bin() -> str | None:
    for candidate in (
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def convert_figure_for_pdflatex(source: Path, target: Path) -> None:
    suffix = source.suffix.lower()
    if suffix in {".tif", ".tiff"}:
        png_target = target.with_suffix(".png")
        png_target.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["sips", "-s", "format", "png", str(source), "--out", str(png_target)],
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            return
    elif suffix in {".emf", ".wmf"}:
        soffice = libreoffice_bin()
        if not soffice:
            return
        pdf_target = target.with_suffix(".pdf")
        pdf_target.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf_target.parent), str(source)],
                capture_output=True,
                text=True,
                timeout=180,
                check=True,
            )
        except subprocess.SubprocessError:
            return


def run_static_checks(tex_file: Path, figures_dir: Path, run_log_dir: Path) -> dict[str, Any]:
    run_log_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python3",
        str(PROJECT_ROOT / "scripts" / "check_format_rules.py"),
        str(tex_file),
        "--figures-dir",
        str(figures_dir),
        "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    (run_log_dir / "static_check_output.json").write_text(result.stdout or result.stderr, encoding="utf-8")
    if result.returncode != 0:
        return {"issue_count": 1, "issues": [{"severity": "critical", "detail": result.stderr.strip()}]}
    return json.loads(result.stdout)


def compile_latex(output_dir: Path, manuscript_id: str, run_log_dir: Path) -> dict[str, Any]:
    run_log_dir.mkdir(parents=True, exist_ok=True)
    tex_name = f"{manuscript_id}.tex"
    has_bib = any(output_dir.glob("*.bib"))
    commands = [
        [PDFLATEX_BIN, "-interaction=nonstopmode", "-no-shell-escape", tex_name],
    ]
    if has_bib:
        commands.append([BIBTEX_BIN, manuscript_id])
    commands.extend(
        [
            [PDFLATEX_BIN, "-interaction=nonstopmode", "-no-shell-escape", tex_name],
            [PDFLATEX_BIN, "-interaction=nonstopmode", "-no-shell-escape", tex_name],
        ]
    )

    combined = []
    for cmd in commands:
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        combined.append("$ " + " ".join(cmd))
        combined.append(result.stdout)
        combined.append(result.stderr)

    compile_output = "\n".join(combined)
    (run_log_dir / "compile_output.txt").write_text(compile_output, encoding="utf-8")

    pdf_path = output_dir / f"{manuscript_id}.pdf"
    errors = [line for line in compile_output.splitlines() if line.startswith("!")]
    warnings = [
        line
        for line in compile_output.splitlines()
        if "Warning" in line or "Overfull \\hbox" in line or "Underfull \\hbox" in line
    ]
    return {
        "success": pdf_path.exists(),
        "pdf_path": str(pdf_path) if pdf_path.exists() else None,
        "errors": errors[:50],
        "warnings": warnings[:100],
    }


def evaluate_output(output_dir: Path, manuscript_id: str, run_log_dir: Path) -> dict[str, Any]:
    tex_file = output_dir / f"{manuscript_id}.tex"
    figures_dir = output_dir / "figures"
    static_report = run_static_checks(tex_file, figures_dir, run_log_dir)
    compile_report = compile_latex(output_dir, manuscript_id, run_log_dir)

    blocking = [issue for issue in static_report.get("issues", []) if issue.get("severity") == "critical"]
    passed = not blocking and compile_report["success"]
    report = {
        "overall_result": "pass" if passed else "fail",
        "static_report": static_report,
        "compile_report": compile_report,
        "recommended_action": "approve" if passed else "rerun_converter",
    }
    (run_log_dir / "eval_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    handoff = [
        "# Evaluator Handoff",
        "",
        f"Overall result: {report['overall_result']}",
        f"Static issues: {static_report.get('issue_count', 0)}",
        f"Compile success: {'yes' if compile_report['success'] else 'no'}",
        "",
        "## Compile Errors",
    ]
    handoff.extend(f"- {err}" for err in compile_report["errors"][:20])
    if not compile_report["errors"]:
        handoff.append("- none")
    (run_log_dir / "evaluator_handoff.md").write_text("\n".join(handoff), encoding="utf-8")
    return report


def copy_supporting_files(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    for template in ("cicc.cls", "cicc.bst"):
        shutil.copy2(PROJECT_ROOT / "templates" / "cicc" / template, output_dir / template)

    for bib in input_dir.glob("*.bib"):
        shutil.copy2(bib, output_dir / bib.name)
    normalize_bib_files(output_dir)

    for path in input_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in FIGURE_SUFFIXES:
            continue
        if any(part.startswith(".") or part == "__MACOSX" for part in path.relative_to(input_dir).parts):
            continue

        relative_path = path.relative_to(input_dir)
        if relative_path.parts and relative_path.parts[0] == "figures":
            relative_path = Path(*relative_path.parts[1:]) if len(relative_path.parts) > 1 else Path(path.name)
        elif len(relative_path.parts) >= 3 and relative_path.parts[:2] == ("pandoc_media", "media"):
            relative_path = Path(path.name)

        target = figures_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        if path.suffix.lower() in {".emf", ".wmf", ".tif", ".tiff"}:
            convert_figure_for_pdflatex(path, target)
