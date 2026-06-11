from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import PANDOC_BIN


CITE_RE = re.compile(r"\\(?:cite|citet|citep|citealp|citeauthor|citeyear)\*?(?:\[[^\]]*\]){0,2}\{([^{}]+)\}")
KEYWORDS_RE = re.compile(r"\\keywords\{([^{}]*)\}")
THEBIB_RE = re.compile(r"\\begin\{thebibliography\}\{[^{}]*\}.*?\\end\{thebibliography\}", re.DOTALL)
BIB_COMMANDS_RE = re.compile(
    r"\n?\s*\\bibliographystyle\{[^{}]+\}\s*\n\s*\\bibliography\{[^{}]+\}\s*\n?",
    re.DOTALL,
)
NUMBERED_REF_RE = re.compile(r"^\s*(?:\\\((\d+)\\\)|\[(\d+)\]|(\d+)[.)])\s+(.*)")
DOI_URL_RE = re.compile(r"\s*(?:https?://(?:dx\.)?doi\.org/[^\s]+|doi:\s*10\.[^\s]+|DOI:\s*10\.[^\s]+)\.?", re.I)
URL_RE = re.compile(r"\s*https?://[^\s]+\.?", re.I)
ISSN_RE = re.compile(r"\s*,?\s*ISSN\s+[0-9Xx-]+\.?", re.I)
DAGGER_MARKERS = {r"\dag", r"\dagger", r"\textdagger"}
DOUBLE_DAGGER_MARKERS = {r"\ddag", r"\ddagger", r"\textdaggerdbl"}


@dataclass
class PassResult:
    name: str
    status: str
    checked: list[str] = field(default_factory=list)
    violations: list[dict[str, str]] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)
    human_review: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text_if_changed(path: Path, text: str) -> bool:
    original = read_text(path) if path.exists() else ""
    if original == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def citation_keys(tex_text: str) -> list[str]:
    keys: list[str] = []
    for match in CITE_RE.finditer(tex_text):
        for key in match.group(1).split(","):
            key = key.strip()
            if key and key not in keys:
                keys.append(key)
    return keys


def existing_bibliography_keys(tex_text: str, output_dir: Path) -> set[str]:
    keys: set[str] = set(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^{}]+)\}", tex_text))
    for bib in output_dir.glob("*.bib"):
        try:
            keys.update(re.findall(r"@\w+\s*\{\s*([^,\s]+)", read_text(bib)))
        except OSError:
            continue
    return keys


def docx_to_markdown(input_dir: Path, pass_dir: Path) -> tuple[str, Path | None]:
    docx_files = sorted(input_dir.glob("*.docx"))
    if not docx_files:
        return "", None
    pass_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = pass_dir / "source_from_docx.md"
    media_dir = pass_dir / "pandoc_media"
    result = subprocess.run(
        [
            PANDOC_BIN,
            str(docx_files[0]),
            "--to",
            "markdown",
            "--extract-media",
            str(media_dir),
        ],
        cwd=input_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        (pass_dir / "pandoc_error.txt").write_text(result.stderr, encoding="utf-8")
        return "", docx_files[0]
    markdown_path.write_text(result.stdout, encoding="utf-8")
    return result.stdout, docx_files[0]


def extract_source_keywords(markdown: str) -> str | None:
    patterns = [
        r"(?im)^\s*(?:keywords?|key words)\s*[:：]\s*(.+?)\s*$",
        r"(?ims)^\s*(?:\*\*)?(?:keywords?|key words)(?:\*\*)?\s*$\s*(.+?)(?:\n\s*\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, markdown)
        if not match:
            continue
        keywords = " ".join(match.group(1).strip().split())
        keywords = re.sub(r"^[：:]\s*", "", keywords)
        if keywords and "placeholder" not in keywords.lower():
            return keywords.rstrip(".") + "."
    return None


def pass_preflight(input_dir: Path, output_dir: Path, tex_file: Path, markdown: str, docx_path: Path | None) -> PassResult:
    tex_text = read_text(tex_file)
    refs = extract_numbered_references(markdown) if markdown else []
    keys = citation_keys(tex_text)
    bib_keys = existing_bibliography_keys(tex_text, output_dir)
    notes = []
    if docx_path:
        notes.append(f"docx source: {docx_path.name}")
    if keys and not bib_keys and not refs and not any(output_dir.glob("*.bib")):
        notes.append("citations exist but no bibliography data was found yet")
    return PassResult(
        name="00-preflight",
        status="PASS",
        checked=[
            "converted TeX draft is readable",
            "source type and docx markdown availability",
            "citation count",
            "source reference count",
            "existing bibliography data",
        ],
        notes=notes,
        metrics={
            "docx_source": docx_path.name if docx_path else None,
            "citation_key_count": len(keys),
            "source_reference_count": len(refs),
            "existing_bibliography_key_count": len(bib_keys),
            "bib_files": [path.name for path in sorted(output_dir.glob("*.bib"))],
        },
    )


def pass_frontmatter(tex_file: Path) -> PassResult:
    tex_text = read_text(tex_file)
    original = tex_text
    tex_text = normalize_frontmatter_marks(tex_text)
    begin_document = tex_text.find(r"\begin{document}")
    notes = []
    violations = []
    status = "PASS"
    for token in (r"\title", r"\author", r"\affil"):
        pos = tex_text.find(token)
        if pos == -1:
            status = "WARNING"
            notes.append(f"{token} not found")
            violations.append(
                {
                    "location": "frontmatter",
                    "rule": f"{token} should be present",
                    "current": "not found",
                    "expected": f"{token} before \\begin{document}",
                    "status": "human-review",
                }
            )
        elif begin_document != -1 and pos > begin_document:
            status = "FAIL"
            notes.append(f"{token} appears after \\begin{{document}}")
            violations.append(
                {
                    "location": "frontmatter",
                    "rule": f"{token} placement",
                    "current": f"{token} after \\begin{{document}}",
                    "expected": f"{token} before \\begin{{document}}",
                    "status": "unfixed",
                }
            )
    changed = write_text_if_changed(tex_file, tex_text) if tex_text != original else False
    fixes = []
    if changed:
        notes.append(r"normalized author/affiliation dagger markers")
        fixes.append(r"normalized author/affiliation dagger markers to numeric affiliation markers")
    return PassResult(
        name="01-frontmatter",
        status=status,
        checked=[
            r"\title placement",
            r"\author placement",
            r"\affil placement",
            r"symbolic contribution markers in author/affiliation optional arguments",
        ],
        violations=violations,
        fixes_applied=fixes,
        notes=notes,
        changed_files=[tex_file.name] if changed else [],
    )


def normalize_frontmatter_marks(tex_text: str) -> str:
    begin_document = tex_text.find(r"\begin{document}")
    if begin_document == -1:
        return tex_text
    preamble = tex_text[:begin_document]
    numeric_markers = [int(value) for value in re.findall(r"\\(?:author|affil)\[([^\]]+)\]", preamble) for value in re.findall(r"\b\d+\b", value)]
    next_marker = max(numeric_markers, default=0) + 1
    marker_map = {
        **{marker: str(next_marker) for marker in DAGGER_MARKERS},
        **{marker: str(next_marker + 1) for marker in DOUBLE_DAGGER_MARKERS},
    }

    def replace_marks(match: re.Match[str]) -> str:
        command = match.group(1)
        marker = ",".join(marker_map.get(part.strip(), part.strip()) for part in match.group(2).split(","))
        return rf"\{command}[{marker}]"

    preamble = re.sub(r"\\(author|affil)\[([^\]]+)\]", replace_marks, preamble)
    return preamble + tex_text[begin_document:]


def pass_heading_keyword(tex_file: Path, markdown: str) -> PassResult:
    tex_text = read_text(tex_file)
    source_keywords = extract_source_keywords(markdown) if markdown else None
    changed = False
    notes = []
    violations = []
    human_review = []
    match = KEYWORDS_RE.search(tex_text)
    current = match.group(1).strip() if match else ""
    if match and source_keywords and ("placeholder" in current.lower() or not current):
        tex_text = tex_text[: match.start(1)] + source_keywords + tex_text[match.end(1) :]
        changed = write_text_if_changed(tex_file, tex_text)
        notes.append("replaced placeholder keywords from docx source")
    elif match and ("placeholder" in current.lower() or not current):
        notes.append("keywords are placeholder/empty and source keywords were not detected")
        human_review.append("keywords are placeholder/empty; source keywords were not detected")
    elif not match:
        notes.append(r"\keywords{...} not found")
        violations.append(
            {
                "location": "opening abstract block",
                "rule": r"\keywords{...} must be present",
                "current": "not found",
                "expected": r"\keywords{...} inside abstract",
                "status": "human-review",
            }
        )
    status = "PASS" if not notes or changed else "WARNING"
    return PassResult(
        name="02-heading-keyword",
        status=status,
        checked=[
            r"\keywords{...}",
            "source keyword extraction",
            "placeholder keyword detection",
        ],
        violations=violations,
        fixes_applied=["replaced placeholder keywords from source"] if changed else [],
        human_review=human_review,
        notes=notes,
        changed_files=[tex_file.name] if changed else [],
        metrics={"source_keywords": source_keywords},
    )


def pass_body_paragraph(tex_file: Path) -> PassResult:
    tex_text = read_text(tex_file)
    begin_document = tex_text.find(r"\begin{document}")
    end_document = tex_text.find(r"\end{document}")
    section_count = len(re.findall(r"\\section\*?\{", tex_text))
    wordish_count = len(re.findall(r"\b[A-Za-z][A-Za-z-]{2,}\b", tex_text[begin_document:end_document if end_document != -1 else None]))
    violations = []
    notes = []
    human_review = []
    status = "PASS"
    if begin_document == -1 or end_document == -1:
        status = "FAIL"
        violations.append(
            {
                "location": "document body",
                "rule": r"body must be enclosed by \begin{document} and \end{document}",
                "current": "missing document boundary",
                "expected": "complete LaTeX document",
                "status": "unfixed",
            }
        )
    if section_count == 0:
        status = "WARNING" if status == "PASS" else status
        human_review.append("no numbered section heading was detected")
        notes.append("no section heading detected")
    if wordish_count < 200:
        status = "WARNING" if status == "PASS" else status
        human_review.append("body text looks short; verify source content was not dropped")
        notes.append("body text looks short")
    return PassResult(
        name="03-body-paragraph",
        status=status,
        checked=[
            "document body boundaries",
            "section heading presence",
            "rough body text volume",
        ],
        violations=violations,
        human_review=human_review,
        notes=notes,
        metrics={"section_count": section_count, "rough_word_count": wordish_count},
    )


def pass_equation(tex_file: Path) -> PassResult:
    tex_text = read_text(tex_file)
    violations = []
    human_review = []
    notes = []
    display_math_count = len(re.findall(r"\\begin\{(?:equation|align|gather|multline|split)\*?\}", tex_text))
    if "$$" in tex_text:
        violations.append(
            {
                "location": "equations",
                "rule": "avoid TeX display math delimiters",
                "current": "$$ delimiter found",
                "expected": "LaTeX equation/align/multline environment",
                "status": "human-review",
            }
        )
        notes.append("raw $$ display math delimiter found")
    if r"\begin{eqnarray" in tex_text:
        violations.append(
            {
                "location": "equations",
                "rule": "avoid eqnarray",
                "current": "eqnarray found",
                "expected": "align or equation/split",
                "status": "human-review",
            }
        )
        notes.append("eqnarray environment found")
    if display_math_count:
        human_review.append("equation width is checked later by evaluator/layout repair when warnings are available")
    status = "WARNING" if violations else "PASS"
    return PassResult(
        name="04-equation",
        status=status,
        checked=[
            "raw $$ display math",
            "eqnarray usage",
            "display equation environment count",
        ],
        violations=violations,
        human_review=human_review,
        notes=notes,
        metrics={"display_math_environment_count": display_math_count},
    )


def has_usepackage(tex_text: str, package: str) -> bool:
    return bool(re.search(rf"\\usepackage(?:\[[^\]]*\])?\{{[^}}]*\b{re.escape(package)}\b[^}}]*\}}", tex_text))


def insert_before_begin_document(tex_text: str, insertion: str) -> str:
    begin_document = tex_text.find(r"\begin{document}")
    if begin_document == -1:
        return tex_text
    return tex_text[:begin_document].rstrip() + "\n" + insertion.rstrip() + "\n\n" + tex_text[begin_document:]


def graphics_candidates(output_dir: Path, graphics_path: str) -> list[Path]:
    raw = Path(graphics_path)
    roots = [output_dir, output_dir / "figures"]
    suffixes = [""] if raw.suffix else [".pdf", ".eps", ".png", ".jpg", ".jpeg"]
    candidates: list[Path] = []
    for root in roots:
        for suffix in suffixes:
            candidates.append(root / (graphics_path + suffix))
    return candidates


def pass_figure_table_packages(output_dir: Path, tex_file: Path) -> PassResult:
    tex_text = read_text(tex_file)
    original = tex_text
    tex_text = re.sub(r"\\usepackage\{mhchem\}", r"\\usepackage[version=4]{mhchem}", tex_text)
    additions = []
    violations = []
    human_review = []
    notes = []
    if any(cmd in tex_text for cmd in (r"\toprule", r"\midrule", r"\bottomrule", r"\cmidrule", r"\addlinespace")):
        if not has_usepackage(tex_text, "booktabs"):
            additions.append(r"\usepackage{booktabs}")
    if r"\multirow" in tex_text and not has_usepackage(tex_text, "multirow"):
        additions.append(r"\usepackage{multirow}")
    if r"\ce{" in tex_text and not has_usepackage(tex_text, "mhchem"):
        additions.append(r"\usepackage[version=4]{mhchem}")

    changed = tex_text != original
    if additions:
        tex_text = insert_before_begin_document(tex_text, "\n".join(additions))
        changed = write_text_if_changed(tex_file, tex_text)
    elif changed:
        changed = write_text_if_changed(tex_file, tex_text)
    for match in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^{}]+)\}", tex_text):
        graphics_path = match.group(1)
        if not any(path.exists() for path in graphics_candidates(output_dir, graphics_path)):
            violations.append(
                {
                    "location": f"line {tex_text[:match.start()].count(chr(10)) + 1}",
                    "rule": "referenced graphics file must exist in output package",
                    "current": graphics_path,
                    "expected": "existing file under output/ or output/figures/",
                    "status": "unfixed",
                }
            )
    if violations:
        notes.append(f"{len(violations)} referenced graphics file(s) were not found")
    if "tabular" in tex_text:
        human_review.append("table width is checked later by evaluator/layout repair when warnings are available")
    return PassResult(
        name="05-figure-table",
        status="FAIL" if violations else "PASS",
        checked=[
            "booktabs package requirement",
            "multirow package requirement",
            "mhchem package option",
            r"\includegraphics file existence",
        ],
        violations=violations,
        fixes_applied=[f"added required package: {pkg}" for pkg in additions]
        + ([r"normalized mhchem package option to version=4"] if r"\usepackage{mhchem}" in original else []),
        human_review=human_review,
        notes=notes
        + [f"added required package: {pkg}" for pkg in additions]
        + ([r"normalized mhchem package option to version=4"] if r"\usepackage{mhchem}" in original else []),
        changed_files=[tex_file.name] if changed else [],
        metrics={"added_packages": additions},
    )


def clean_reference_markdown(markdown: str) -> str:
    text = DOI_URL_RE.sub("", markdown)
    text = URL_RE.sub("", text)
    text = ISSN_RE.sub("", text)
    text = re.sub(r"\s+\.", ".", text)
    return text.strip()


def extract_numbered_references(markdown: str) -> list[tuple[int, str]]:
    lines = markdown.splitlines()
    scan_start = len(lines) // 2
    refs: list[tuple[int, list[str]]] = []
    current: tuple[int, list[str]] | None = None

    for line in lines[scan_start:]:
        match = NUMBERED_REF_RE.match(line)
        if match:
            if current:
                refs.append(current)
            number = int(next(group for group in match.groups()[:3] if group))
            current = (number, [match.group(4).strip()])
            continue
        if current:
            current[1].append(line)
    if current:
        refs.append(current)

    return [(number, "\n".join(block).strip()) for number, block in refs if "\n".join(block).strip()]


def markdown_reference_to_latex(markdown: str) -> str:
    cleaned = clean_reference_markdown(markdown)
    if not cleaned:
        return ""
    try:
        result = subprocess.run(
            [PANDOC_BIN, "--from", "markdown", "--to", "latex"],
            input=cleaned,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            latex = result.stdout.strip()
        else:
            latex = cleaned
    except (OSError, subprocess.SubprocessError):
        latex = cleaned
    latex = re.sub(r"\\href\{[^{}]*\}\{([^{}]*)\}", r"\1", latex)
    latex = re.sub(r"\\url\{[^{}]*\}", "", latex)
    latex = DOI_URL_RE.sub("", latex)
    latex = URL_RE.sub("", latex)
    latex = ISSN_RE.sub("", latex)
    return " ".join(latex.split())


def build_thebibliography(refs: list[tuple[int, str]]) -> str:
    width = max(9, max((number for number, _ in refs), default=9))
    lines = [rf"\begin{{thebibliography}}{{{width}}}"]
    for number, markdown in refs:
        latex = markdown_reference_to_latex(markdown)
        if latex:
            lines.append(rf"\bibitem{{ref{number}}} {latex}")
    lines.append(r"\end{thebibliography}")
    return "\n".join(lines)


def replace_or_insert_bibliography(tex_text: str, bibliography_block: str) -> str:
    if THEBIB_RE.search(tex_text):
        return THEBIB_RE.sub(lambda _match: bibliography_block, tex_text, count=1)
    if BIB_COMMANDS_RE.search(tex_text):
        return BIB_COMMANDS_RE.sub(lambda _match: "\n" + bibliography_block + "\n", tex_text, count=1)
    label_lastpage = tex_text.find(r"\label{lastpage}")
    if label_lastpage != -1:
        return tex_text[:label_lastpage].rstrip() + "\n\n" + bibliography_block + "\n" + tex_text[label_lastpage:]
    end_document = tex_text.find(r"\end{document}")
    if end_document != -1:
        return tex_text[:end_document].rstrip() + "\n\n" + bibliography_block + "\n" + tex_text[end_document:]
    return tex_text.rstrip() + "\n\n" + bibliography_block + "\n"


def pass_reference(input_dir: Path, output_dir: Path, tex_file: Path, markdown: str, recommended_path: str) -> PassResult:
    tex_text = read_text(tex_file)
    keys = citation_keys(tex_text)
    existing_keys = existing_bibliography_keys(tex_text, output_dir)
    refs = extract_numbered_references(markdown) if markdown else []
    notes = []
    changed = False

    if keys and recommended_path == "cicc-latex" and not any(output_dir.glob("*.bib")) and refs:
        bibliography_block = build_thebibliography(refs)
        updated = replace_or_insert_bibliography(tex_text, bibliography_block)
        changed = write_text_if_changed(tex_file, updated)
        tex_text = updated
        existing_keys = existing_bibliography_keys(tex_text, output_dir)
        notes.append(f"generated thebibliography from {len(refs)} docx references")

    missing = [key for key in keys if key not in existing_keys]
    if keys and not existing_keys:
        status = "FAIL"
        notes.append("citations exist but no bibliography entries exist")
    elif missing:
        status = "WARNING"
        notes.append(f"{len(missing)} citation key(s) still have no bibliography entry")
    else:
        status = "PASS"

    return PassResult(
        name="06-reference",
        status=status,
        checked=[
            "citation commands",
            "existing .bib files",
            "existing thebibliography entries",
            "docx numbered References section",
            "missing citation keys",
        ],
        fixes_applied=[f"generated thebibliography from {len(refs)} docx references"] if changed else [],
        human_review=[f"{len(missing)} citation key(s) still need review"] if missing else [],
        notes=notes,
        changed_files=[tex_file.name] if changed else [],
        metrics={
            "citation_key_count": len(keys),
            "source_reference_count": len(refs),
            "bibliography_key_count": len(existing_keys),
            "missing_citation_keys": missing[:80],
        },
    )


def pass_compile_repair_deferred() -> PassResult:
    return PassResult(
        name="07-compile-repair",
        status="PASS",
        checked=["compile repair gate is owned by evaluator after these conversion passes"],
        notes=["deferred until evaluator has compile logs"],
        human_review=[],
        metrics={"deferred": True},
    )


def pass_layout_deferred() -> PassResult:
    return PassResult(
        name="08-layout",
        status="PASS",
        checked=["equation/figure/table layout repair gate is owned by evaluator after compilation"],
        notes=["deferred until evaluator has layout warnings"],
        human_review=[],
        metrics={"deferred": True},
    )


def pass_final(output_dir: Path, tex_file: Path) -> PassResult:
    tex_text = read_text(tex_file)
    keys = citation_keys(tex_text)
    bibliography_keys = existing_bibliography_keys(tex_text, output_dir)
    notes = []
    status = "PASS"
    for required in ("cicc.cls", "cicc.bst"):
        if not (output_dir / required).exists():
            status = "FAIL"
            notes.append(f"missing {required}")
    if keys and not bibliography_keys:
        status = "FAIL"
        notes.append("citations exist but no bibliography data exists")
    return PassResult(
        name="09-final",
        status=status,
        checked=[
            ".tex exists",
            "cicc.cls exists",
            "cicc.bst exists",
            "bibliography data exists when citations exist",
        ],
        notes=notes,
        violations=[
            {
                "location": "output package",
                "rule": note,
                "current": "missing",
                "expected": "present",
                "status": "unfixed",
            }
            for note in notes
        ],
        metrics={
            "tex_exists": tex_file.exists(),
            "citation_key_count": len(keys),
            "bibliography_key_count": len(bibliography_keys),
        },
    )


def write_pass_report(pass_dir: Path, results: list[PassResult]) -> dict[str, Any]:
    report = {
        "overall_result": "FAIL" if any(r.status == "FAIL" for r in results) else "PASS",
        "warning_count": sum(1 for r in results if r.status == "WARNING"),
        "passes": [asdict(result) for result in results],
    }
    pass_dir.mkdir(parents=True, exist_ok=True)
    (pass_dir / "pass_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for result in results:
        write_pass_audit(pass_dir, result)
    lines = ["# Conversion Pass Report", ""]
    for result in results:
        lines.append(f"{result.name}: {result.status}")
        for note in result.notes:
            lines.append(f"- {note}")
        if result.changed_files:
            lines.append(f"- changed: {', '.join(result.changed_files)}")
        lines.append("")
    (pass_dir / "pass_report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def write_pass_audit(pass_dir: Path, result: PassResult) -> None:
    file_name = f"{result.name}-audit.md"
    lines = [
        f"# {result.name} Audit",
        "",
        "## Checked",
    ]
    if result.checked:
        lines.extend(f"- [x] {item}" for item in result.checked)
    else:
        lines.append("- [ ] no explicit checks recorded")
    lines.extend(["", "## Violations", "| Location | Rule | Current | Expected | Status |", "|---|---|---|---|---|"])
    if result.violations:
        for item in result.violations:
            lines.append(
                "| {location} | {rule} | {current} | {expected} | {status} |".format(
                    location=item.get("location", ""),
                    rule=item.get("rule", ""),
                    current=item.get("current", ""),
                    expected=item.get("expected", ""),
                    status=item.get("status", ""),
                )
            )
    else:
        lines.append("| none | none | none | none | pass |")
    lines.extend(["", "## Fixes Applied"])
    lines.extend(f"- {item}" for item in result.fixes_applied) if result.fixes_applied else lines.append("- none")
    lines.extend(["", "## Human Review"])
    lines.extend(f"- {item}" for item in result.human_review) if result.human_review else lines.append("- none")
    lines.extend(["", "## Notes"])
    lines.extend(f"- {item}" for item in result.notes) if result.notes else lines.append("- none")
    lines.extend(["", "## Result", result.status])
    (pass_dir / file_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_conversion_passes(
    input_dir: Path,
    output_dir: Path,
    tex_file: Path,
    recommended_path: str,
    pass_log_dir: Path,
) -> dict[str, Any]:
    pass_log_dir.mkdir(parents=True, exist_ok=True)
    markdown = ""
    docx_path: Path | None = None
    if recommended_path == "cicc-latex":
        markdown, docx_path = docx_to_markdown(input_dir, pass_log_dir)

    results = [
        pass_preflight(input_dir, output_dir, tex_file, markdown, docx_path),
        pass_frontmatter(tex_file),
        pass_heading_keyword(tex_file, markdown),
        pass_body_paragraph(tex_file),
        pass_equation(tex_file),
        pass_figure_table_packages(output_dir, tex_file),
        pass_reference(input_dir, output_dir, tex_file, markdown, recommended_path),
        pass_compile_repair_deferred(),
        pass_layout_deferred(),
        pass_final(output_dir, tex_file),
    ]
    return write_pass_report(pass_log_dir, results)
