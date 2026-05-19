#!/usr/bin/env python3
"""Static CiCC checks focused on headings, equations, figures, schemes, and tables."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FLOAT_RE = re.compile(
    r"\\begin\{(figure\*?|scheme\*?|table\*?)\}(?:\[([^\]]*)\])?"
    r"(.*?)\\end\{\1\}",
    re.DOTALL,
)

INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics\*?(?:\[([^\]]*)\])?\{([^{}]+)\}")
WIDTH_OPTION_RE = re.compile(r"width\s*=\s*([0-9]*\.?[0-9]+)\s*\\(textwidth|linewidth)")

TABULAR_RE = re.compile(
    r"\\begin\{(tabular\*?|tabularx|array)\}"
    r"(?:\{[^{}]*\})?\{([^{}]*)\}",
    re.DOTALL,
)

EQUATION_RE = re.compile(
    r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}"
    r"(.*?)\\end\{\1\}",
    re.DOTALL,
)

SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^{}\n]+)\}")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9/-]*")
FUNCTION_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "via",
    "with",
}


def line_for(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


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


def add_issue(issues: list[dict], severity: str, rule: str, line: int, detail: str) -> None:
    issues.append(
        {
            "severity": severity,
            "rule": rule,
            "line": line,
            "detail": detail,
        }
    )


def check_document_frame(text: str, issues: list[dict]) -> None:
    stripped = text.lstrip()
    if not stripped.startswith(r"\documentclass{cicc}"):
        add_issue(
            issues,
            "critical",
            "frame-documentclass",
            1,
            r"output must start with \documentclass{cicc}",
        )
    for token, rule in (
        (r"\begin{document}", "frame-begin-document"),
        (r"\end{document}", "frame-end-document"),
        (r"\twocolumn[{", "frame-twocolumn-opening"),
        (r"\maketitle", "frame-maketitle"),
        (r"\begin{abstract}", "frame-abstract"),
        (r"\keywords{", "frame-keywords"),
    ):
        if token not in text:
            add_issue(issues, "critical", rule, 1, f"missing required CiCC frame token: {token}")


def strip_comments(text: str) -> str:
    cleaned = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        cleaned.append(line[: match.start()] if match else line)
    return "\n".join(cleaned)


def strip_latex_inline(text: str) -> str:
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = text.replace("\\&", " and ")
    text = text.replace("~", " ")
    return text


def width_option(opts: str) -> tuple[float, str] | None:
    match = WIDTH_OPTION_RE.search(opts)
    if not match:
        return None
    return float(match.group(1)), match.group(2)


def has_multipanel_markup(body: str, include_count: int) -> bool:
    return (
        include_count > 1
        or r"\subfloat" in body
        or r"\subfigure" in body
        or r"\begin{subfigure}" in body
        or r"\begin{subcaptionblock}" in body
    )


def multipanel_widths_ok(include_options: list[str], max_width: float) -> bool:
    if not include_options:
        return False
    for opts in include_options:
        parsed = width_option(opts)
        if not parsed:
            return False
        value, unit = parsed
        if unit not in {"textwidth", "linewidth"} or not (0.15 <= value <= max_width):
            return False
    return True


def is_acronym_or_code(token: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", token)
    if not letters:
        return True
    if any(ch.isdigit() for ch in token):
        return True
    return letters.isupper() and len(letters) >= 2


def is_titlecase_word(token: str) -> bool:
    parts = [part for part in re.split(r"[-/]", token) if part]
    ordinary_parts = [
        part
        for part in parts
        if part.isalpha() and part.lower() not in FUNCTION_WORDS and not is_acronym_or_code(part)
    ]
    if not ordinary_parts:
        return False
    return all(part[:1].isupper() and part[1:].islower() for part in ordinary_parts)


def section_heading_case_issue(title: str) -> str | None:
    cleaned = strip_latex_inline(title)
    words = WORD_RE.findall(cleaned)
    if len(words) < 2:
        return None

    letters = "".join(re.findall(r"[A-Za-z]", cleaned))
    if len(letters) >= 8 and letters.upper() == letters:
        return "heading appears to be all caps; use sentence case"

    checked = [
        word
        for word in words[1:]
        if word.lower() not in FUNCTION_WORDS and not is_acronym_or_code(word)
    ]
    titlecase_count = sum(1 for word in checked if is_titlecase_word(word))
    if checked and titlecase_count / len(checked) >= 0.8:
        return "heading appears to use Title Case; use sentence case"
    return None


def check_section_headings(text: str, issues: list[dict]) -> None:
    for match in SECTION_RE.finditer(text):
        title = match.group(2).strip()
        issue = section_heading_case_issue(title)
        if issue:
            command = match.group(1)
            add_issue(
                issues,
                "warning",
                "section-heading-case",
                line_for(text, match.start()),
                f"\\{command}{{{title}}}: {issue}. Capitalize only the first word and proper nouns/established abbreviations.",
            )


def check_float_blocks(text: str, issues: list[dict]) -> None:
    for match in FLOAT_RE.finditer(text):
        env, spec, body = match.group(1), match.group(2), match.group(3)
        line = line_for(text, match.start())
        spec = spec or ""
        is_wide = env.endswith("*")
        base = env.rstrip("*")

        expected_spec = "!t" if is_wide else "h!"
        if spec != expected_spec:
            add_issue(
                issues,
                "warning",
                "float-placement",
                line,
                f"{env} uses [{spec or 'missing'}]; expected [{expected_spec}]",
            )

        if r"\centering" not in body:
            add_issue(issues, "warning", "float-centering", line, f"{env} is missing \\centering")

        if base in {"figure", "scheme"}:
            body_without_comments = strip_tex_comments(body)
            include_pos = body_without_comments.find(r"\includegraphics")
            caption_pos = body_without_comments.find(r"\caption")
            has_tikz_picture = r"\begin{tikzpicture}" in body_without_comments
            if include_pos == -1 and not has_tikz_picture:
                add_issue(issues, "critical", "figure-includegraphics", line, f"{env} has no \\includegraphics")
            elif caption_pos == -1:
                add_issue(issues, "warning", "figure-caption", line, f"{env} has no \\caption")
            elif include_pos > caption_pos:
                add_issue(
                    issues,
                    "warning",
                    "figure-caption-order",
                    line,
                    f"{env} has \\caption before \\includegraphics; caption must be below the image",
                )

            if include_pos != -1:
                include_matches = list(INCLUDEGRAPHICS_RE.finditer(body))
                include_options = [m.group(1) or "" for m in include_matches]
                is_multipanel = has_multipanel_markup(body, len(include_matches))
                if is_wide and is_multipanel:
                    if not multipanel_widths_ok(include_options, max_width=0.55):
                        add_issue(
                            issues,
                            "warning",
                            "figure-width",
                            line,
                            f"{env} multipanel graphics should use relative subimage widths around 0.15--0.55\\textwidth/\\linewidth",
                        )
                elif is_wide and r"width=0.9\textwidth" not in include_options[0]:
                    add_issue(
                        issues,
                        "warning",
                        "figure-width",
                        line,
                        f"{env} should normally use width=0.9\\textwidth",
                    )
                elif not is_wide and is_multipanel:
                    if not multipanel_widths_ok(include_options, max_width=0.5):
                        add_issue(
                            issues,
                            "warning",
                            "figure-width",
                            line,
                            f"{env} multipanel graphics should use relative subimage widths no larger than 0.5\\linewidth",
                        )
                elif not is_wide and r"width=1.0\linewidth" not in include_options[0]:
                    add_issue(
                        issues,
                        "warning",
                        "figure-width",
                        line,
                        f"{env} should normally use width=1.0\\linewidth",
                    )

        if base == "table":
            caption_pos = body.find(r"\caption")
            tabular_pos = body.find(r"\begin{tabular")
            if caption_pos == -1:
                add_issue(issues, "warning", "table-caption", line, f"{env} has no \\caption")
            elif tabular_pos != -1 and caption_pos > tabular_pos:
                add_issue(
                    issues,
                    "warning",
                    "table-caption-order",
                    line,
                    f"{env} has \\caption after tabular; table captions must be above tables",
                )
            label_pos = body.find(r"\label")
            if caption_pos != -1 and label_pos != -1 and label_pos < caption_pos:
                add_issue(
                    issues,
                    "warning",
                    "table-label-order",
                    line,
                    f"{env} has \\label before \\caption; place label immediately after caption",
                )


def check_tables(text: str, issues: list[dict]) -> None:
    for match in TABULAR_RE.finditer(text):
        env, colspec = match.group(1), match.group(2)
        line = line_for(text, match.start())
        if "|" in colspec:
            add_issue(
                issues,
                "warning",
                "table-vertical-lines",
                line,
                f"{env} column spec contains vertical rule(s): {{{colspec}}}",
            )

    for match in re.finditer(r"\\hline\b", text):
        add_issue(
            issues,
            "warning",
            "table-hline",
            line_for(text, match.start()),
            r"\hline found; use \toprule, \midrule, \bottomrule, or \cmidrule",
        )

    for match in re.finditer(r"\\begin\{table\*?\}", text):
        end = text.find(r"\end{table", match.start())
        body = text[match.start() : end if end != -1 else match.end()]
        line = line_for(text, match.start())
        if r"\begin{tabular" in body:
            for cmd in (r"\toprule", r"\midrule", r"\bottomrule"):
                if cmd not in body:
                    add_issue(issues, "warning", "table-booktabs", line, f"table is missing {cmd}")

            env_match = re.match(r"\\begin\{(table\*?)\}", text[match.start() : match.start() + 20])
            is_wide_table = bool(env_match and env_match.group(1).endswith("*"))
            tabular_match = TABULAR_RE.search(body)
            colspec = tabular_match.group(2) if tabular_match else ""
            column_count = len(re.findall(r"[lcrX]|p\{", colspec))
            body_without_commands = strip_latex_inline(body)
            longest_row = max((len(row.strip()) for row in body_without_commands.split(r"\\")), default=0)
            if not is_wide_table and (column_count >= 4 or longest_row > 180):
                add_issue(
                    issues,
                    "warning",
                    "table-width-risk",
                    line,
                    (
                        "single-column table may be too wide for CiCC two-column layout; "
                        f"detected {column_count or 'unknown'} columns and longest row length {longest_row}"
                    ),
                )


def check_equations(text: str, issues: list[dict]) -> None:
    for match in re.finditer(r"\\begin\{eqnarray\*?\}", text):
        add_issue(
            issues,
            "warning",
            "equation-eqnarray",
            line_for(text, match.start()),
            "eqnarray is not allowed; use equation+split, align, or widetext",
        )

    for match in re.finditer(r"(?<!\\)\$\$", text):
        add_issue(
            issues,
            "warning",
            "equation-display-dollar",
            line_for(text, match.start()),
            "display math with $$...$$ is not allowed; use LaTeX equation environments",
        )

    widetext_spans = [(m.start(), m.end()) for m in re.finditer(r"\\begin\{widetext\}.*?\\end\{widetext\}", text, re.DOTALL)]

    def in_widetext(pos: int) -> bool:
        return any(start <= pos <= end for start, end in widetext_spans)

    for match in EQUATION_RE.finditer(text):
        env, body = match.group(1), match.group(2)
        line = line_for(text, match.start())
        compact_lines = [ln.strip() for ln in strip_comments(body).splitlines() if ln.strip()]
        longest = max((len(ln) for ln in compact_lines), default=0)
        has_breaks = r"\\" in body
        has_splitter = any(token in body for token in (r"\begin{split}", r"\begin{aligned}", r"\begin{alignedat}"))

        if env.startswith("equation") and has_breaks and not has_splitter:
            add_issue(
                issues,
                "warning",
                "equation-split",
                line,
                "multi-line equation should use split/aligned inside equation",
            )

        if longest > 110 and not has_splitter and not in_widetext(match.start()):
            add_issue(
                issues,
                "warning",
                "equation-line-length",
                line,
                f"equation has a long source line ({longest} chars); split early for two-column layout",
            )


def check_graphics_files(text: str, figures_dir: Path | None, issues: list[dict]) -> None:
    for match in re.finditer(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^{}]+)\}", strip_tex_comments(text)):
        raw_name = match.group(1)
        line = line_for(text, match.start())
        if raw_name.lower().endswith((".emf", ".wmf")):
            add_issue(issues, "critical", "graphics-emf", line, f"{raw_name} must be converted to PDF")
        if not figures_dir:
            continue
        path = Path(raw_name)
        candidates = []
        if path.suffix:
            candidates.append(figures_dir / path)
            candidates.append(figures_dir / path.name)
            candidates.append(path)
        else:
            for suffix in (".pdf", ".png", ".jpg", ".jpeg", ".eps"):
                candidates.append((figures_dir / path).with_suffix(suffix))
                candidates.append(figures_dir / f"{path.name}{suffix}")
                candidates.append(path.with_suffix(suffix))
        if not any(candidate.exists() for candidate in candidates):
            add_issue(issues, "critical", "graphics-missing", line, f"graphic not found: {raw_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex_file", type=Path)
    parser.add_argument("--figures-dir", type=Path)
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    text = args.tex_file.read_text(encoding="utf-8")
    issues: list[dict] = []
    check_document_frame(text, issues)
    check_section_headings(text, issues)
    check_float_blocks(text, issues)
    check_tables(text, issues)
    check_equations(text, issues)
    check_graphics_files(text, args.figures_dir, issues)

    result = {
        "tex_file": str(args.tex_file),
        "issue_count": len(issues),
        "issues": issues,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"CiCC format checks: {len(issues)} issue(s)")
        for issue in issues:
            print(
                f"[{issue['severity']}] line {issue['line']}: "
                f"{issue['rule']} - {issue['detail']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
