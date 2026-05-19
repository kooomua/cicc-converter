from __future__ import annotations

import re
from pathlib import Path


PLACEHOLDER_BIB_RE = re.compile(
    r"\n\\begin\{thebibliography\}\{99\}.*?\\end\{thebibliography\}\n",
    re.DOTALL,
)
THEBIBLIOGRAPHY_RE = re.compile(
    r"\\begin\{thebibliography\}\{[^{}]*\}.*?\\end\{thebibliography\}",
    re.DOTALL,
)


def ensure_graphics_path(text: str) -> str:
    if "\\graphicspath" in text:
        return text

    documentclass_match = re.search(r"^(\\documentclass(?:\[[^\]]*\])?\{[^{}]+\})\s*", text, re.MULTILINE)
    if documentclass_match:
        insert_at = documentclass_match.end()
        return text[:insert_at] + "\\graphicspath{{figures/}}\n" + text[insert_at:]

    begin_document = text.find("\\begin{document}")
    if begin_document != -1:
        return text[:begin_document] + "\\graphicspath{{figures/}}\n" + text[begin_document:]

    return text


def strip_visible_reference_identifiers(text: str) -> str:
    def clean_block(match: re.Match[str]) -> str:
        block = match.group(0)
        block = re.sub(r"(?im)^\s*\\newblock\s+URL\s+\\url\{[^{}]*\}\.?\s*\n?", "", block)
        block = re.sub(r"(?im)^\s*\\newblock\s+ISSN\s+[^\n.]+\.?\s*\n?", "", block)
        block = re.sub(r"(?im)^\s*\\newblock\s+DOI:\s+[^\n.]+\.?\s*\n?", "", block)
        block = re.sub(r"(?i),?\s+DOI:\s*(?:\\url\{[^{}]*\}|10\.[^\s,.;}]+)[,.]?", "", block)
        block = re.sub(r"(?i),?\s+URL\s+\\url\{[^{}]*\}[,.]?", "", block)
        block = re.sub(r"(?i),?\s+ISSN\s+[0-9Xx-]+[,.]?", "", block)
        return block

    return THEBIBLIOGRAPHY_RE.sub(clean_block, text)


def postprocess_tex(tex_file: Path, output_dir: Path) -> bool:
    text = tex_file.read_text(encoding="utf-8")
    original = text

    text = text.replace("\\PassOptionsToPackage{draft}{graphicx}\n", "")

    if (output_dir / "figures").exists() and "\\graphicspath" not in text:
        text = ensure_graphics_path(text)

    if (output_dir / "ref.bib").exists():
        replacement = "\n\\bibliographystyle{cicc}\n\\bibliography{ref}\n"
        text = PLACEHOLDER_BIB_RE.sub(replacement, text)

    text = strip_visible_reference_identifiers(text)

    if text != original:
        tex_file.write_text(text, encoding="utf-8")
        return True
    return False
