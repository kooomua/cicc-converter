from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .config import (
    CONVERTER_TEXT_LIMIT,
    LLM_API_KEY,
    LLM_API_STYLE,
    LLM_BASE_URL,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    LLM_THINKING,
    PANDOC_BIN,
    PROJECT_ROOT,
)
from .llm_client import openai_client_kwargs


MAX_CHAT_CONTINUATIONS = 3

CICC_OPENING_FRAME = r"""
\documentclass{cicc}
\firstpage{1}
\articletype{Regular / Feature / Perspective / Review Article}

\doi{doi: 10.4208/cicc.2026.xxx.xx}
\publishedyear{2026}
\volume{1}
\issue{1}
%\pagenumbers{1-2}

\receiveddate{20 Oct. 2026}
\revisiondate{25 Oct. 2026}
\accepteddate{25 Dec. 2026}
\onlinedate{28 Dec. 2026}
\publisheddate{30 Dec. 2026}

\title[Here is the Title]
{Here is the Title}
\author[1,2]{John Doe}
\author[1,2,*]{Jane Smith}

\affil[1]{\textit{Department of Chemistry, Faculty of Arts and Sciences, Beijing Normal University, Zhuhai 519087, China} }
\affil[2]{\textit{College of Chemistry, Beijing Normal University, Beijing 100875, China}
\protect\vspace{1em}}

\affil[*]{Corresponding authors: xxxxx@xxx}


\let\leqslant=\leq

\newtheorem{theorem}{Theorem}[section]

\begin{document}

\twocolumn[{
  \vspace*{0.5em}
  \maketitle
  \thispagestyle{firstpage}
  \label{firstpage}

\begin{abstract}
The abstract should be a single paragraph that summarises the content of the article.

\keywords{keyword1, keyword2, keyword3, keyword4.}
\end{abstract}

}] % End of twocolumn header block
""".strip()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def docx_to_markdown(docx_path: Path, work_dir: Path) -> str:
    if not shutil.which(PANDOC_BIN):
        raise RuntimeError("Pandoc was not found. Install pandoc or set PANDOC_BIN.")
    media_dir = work_dir / "pandoc_media"
    cmd = [
        PANDOC_BIN,
        str(docx_path),
        "--to",
        "markdown",
        "--extract-media",
        str(media_dir),
    ]
    result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed: {result.stderr.strip()}")
    return result.stdout


def extracted_media_manifest(input_dir: Path) -> str:
    media_dir = input_dir / "pandoc_media" / "media"
    if not media_dir.exists():
        return "No extracted media files were found."

    lines = []
    for path in sorted(media_dir.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".pdf", ".eps"}:
            latex_path = f"figures/{path.name}"
        elif suffix in {".tif", ".tiff"}:
            latex_path = f"figures/{path.stem}.png"
        elif suffix in {".emf", ".wmf"}:
            latex_path = f"figures/{path.stem}.pdf"
        else:
            continue
        lines.append(f"- extracted: {path.name} -> use in LaTeX as `{latex_path}`")
    return "\n".join(lines) if lines else "No usable extracted media files were found."


def build_prompt(
    input_dir: Path,
    output_tex_name: str,
    recommended_path: str,
    manuscript_id: str,
    primary_tex_file: str | None = None,
    feedback_text: str | None = None,
    attempt: int = 1,
) -> str:
    rules = read_text(PROJECT_ROOT / "skills" / "cicc-rules.md")
    cls_text = read_text(PROJECT_ROOT / "templates" / "cicc" / "cicc.cls")
    skill_file = "cicc-latex_SKILL.md" if recommended_path == "cicc-latex" else "cicc-reformat_SKILL.md"
    skill = read_text(PROJECT_ROOT / "skills" / skill_file)

    if recommended_path == "cicc-latex":
        docx_files = sorted(input_dir.glob("*.docx"))
        if not docx_files:
            raise RuntimeError("No .docx file found for cicc-latex conversion.")
        source = docx_to_markdown(docx_files[0], input_dir)
        source_label = f"Pandoc Markdown extracted from {docx_files[0].name}"
        media_manifest = extracted_media_manifest(input_dir)
    else:
        selected_tex = input_dir / primary_tex_file if primary_tex_file else None
        if selected_tex and not selected_tex.exists():
            raise RuntimeError(f"Inspector selected primary_tex_file={primary_tex_file}, but it was not found.")
        tex_files = sorted(input_dir.glob("*.tex"))
        if selected_tex is None:
            selected_tex = next((path for path in tex_files if path.name.lower() == "main.tex"), None)
        if selected_tex is None and tex_files:
            selected_tex = tex_files[0]
        if selected_tex is None:
            raise RuntimeError("No .tex file found for cicc-reformat conversion.")
        source = read_text(selected_tex)
        source_label = f"Original TeX source from {selected_tex.name}"
        media_manifest = ""

    opening_contract = """
Non-negotiable CiCC opening frame contract:
- The returned file must start exactly with `\\documentclass{cicc}`. Do not put comments, markdown, or any text before it.
- From `\\documentclass{cicc}` through the end of the `\\twocolumn[{...}]` abstract block, follow the fixed opening frame supplied below as the authoritative frame.
- `\\title`, every `\\author`, and every `\\affil` command must appear before `\\begin{document}`.
- `\\maketitle`, `\\thispagestyle{firstpage}`, `\\label{firstpage}`, `\\begin{abstract}`, `\\keywords{...}`, and `\\end{abstract}` must be inside the `\\twocolumn[{...}]` block.
- Put the manuscript body after the opening abstract block, normally beginning with the first `\\section{...}`.
- The returned file must be complete and must end with `\\label{lastpage}` followed by `\\end{document}`.
- Do not copy the author's preamble wholesale. Keep only author packages that are actually required by the converted body.
- Do not reload packages already provided by `cicc.cls`, including geometry, fontenc, inputenc, newtxtext, newtxmath, microtype, graphicx, xcolor, etoolbox, amsmath, calc, xstring, authblk, cuted, abstract, fancyhdr, caption, and natbib.
- Do not load `amsthm`. If theorem-like environments are needed, define them with basic `\\newtheorem` only.
- If evaluator feedback contains compile errors caused by a package or command conflict, remove or replace the conflicting package/command in the next attempt.
- For Word/docx inputs, use the extracted media filenames exactly as supplied in the media manifest. Do not invent or substitute `example-image` placeholders.
""".strip()

    parts = [
        "You convert manuscripts into CiCC-compliant LaTeX.",
        "Return only the final .tex file content. Do not wrap it in markdown fences. Do not include explanations.",
        f"The output filename will be {output_tex_name}. The manuscript id is {manuscript_id}.",
        f"This is conversion attempt {attempt}.",
        "If evaluator feedback is supplied, fix every issue it reports while preserving correct content from the source.",
        "",
        opening_contract,
        "",
        "Authoritative fixed CiCC opening frame:",
        CICC_OPENING_FRAME,
        "",
        "Authoritative CiCC rules:",
        rules,
        "",
        f"Workflow skill ({skill_file}):",
        skill,
        "",
        "Authoritative cicc.cls:",
        cls_text,
        "",
        "Extracted media manifest:",
        media_manifest,
        "",
        source_label + ":",
        source,
    ]
    if feedback_text:
        parts.extend(
            [
                "",
                "Evaluator feedback from the previous attempt. Fix these issues in this attempt:",
                feedback_text,
            ]
        )
    prompt = "\n".join(parts)
    if len(prompt) > CONVERTER_TEXT_LIMIT:
        raise RuntimeError(
            f"The converter prompt is too large ({len(prompt)} chars > CICC_CONVERTER_TEXT_LIMIT={CONVERTER_TEXT_LIMIT}). "
            "Raise CICC_CONVERTER_TEXT_LIMIT or add section chunking for very long manuscripts."
        )
    return prompt


def response_text(response: object) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text)
    output = getattr(response, "output", None)
    if output:
        chunks: list[str] = []
        for item in output:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if value:
                    chunks.append(str(value))
        if chunks:
            return "\n".join(chunks)
    return str(response)


def create_chat_completion(client: object, prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise scientific LaTeX conversion engine. "
                "Follow the supplied CiCC rules and class file exactly."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": LLM_MAX_OUTPUT_TOKENS,
    }
    if LLM_REASONING_EFFORT in {"high", "max"}:
        kwargs["reasoning_effort"] = LLM_REASONING_EFFORT
    if LLM_THINKING in {"enabled", "disabled"}:
        kwargs["extra_body"] = {"thinking": {"type": LLM_THINKING}}
    if not LLM_THINKING and "reasoner" not in LLM_MODEL and "v4-pro" not in LLM_MODEL:
        kwargs["temperature"] = 0.2

    chunks: list[str] = []
    for continuation in range(MAX_CHAT_CONTINUATIONS + 1):
        response = client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        chunk = choice.message.content or ""
        chunks.append(chunk)
        combined = "".join(chunks)
        finish_reason = getattr(choice, "finish_reason", None)

        if "\\end{document}" in combined or finish_reason not in {"length", "max_tokens"}:
            return combined

        messages.append({"role": "assistant", "content": chunk})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Continue the LaTeX document exactly from the last character of your previous response. "
                    "Do not repeat any earlier content. Return only the continuation, and continue until "
                    "`\\label{lastpage}` and `\\end{document}` are included."
                ),
            }
        )
        kwargs["messages"] = messages

    return "".join(chunks)


def create_responses_completion(client: object, prompt: str) -> str:
    response = client.responses.create(
        model=LLM_MODEL,
        instructions=(
            "You are a precise scientific LaTeX conversion engine. "
            "Follow the supplied CiCC rules and class file exactly."
        ),
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    )
    return response_text(response)


def convert_with_openai(
    input_dir: Path,
    output_tex: Path,
    recommended_path: str,
    manuscript_id: str,
    primary_tex_file: str | None = None,
    feedback_text: str | None = None,
    attempt: int = 1,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai Python package is not installed. Run pip install -r requirements.txt.") from exc

    if not LLM_API_KEY or LLM_API_KEY == "replace_me":
        raise RuntimeError("CICC_LLM_API_KEY is not set. Add your API key to .env before running a conversion.")

    prompt = build_prompt(
        input_dir,
        output_tex.name,
        recommended_path,
        manuscript_id,
        primary_tex_file=primary_tex_file,
        feedback_text=feedback_text,
        attempt=attempt,
    )
    client_kwargs = openai_client_kwargs(LLM_API_KEY, LLM_BASE_URL)
    client = OpenAI(**client_kwargs)
    if LLM_API_STYLE == "chat":
        raw_text = create_chat_completion(client, prompt)
    elif LLM_API_STYLE == "responses":
        raw_text = create_responses_completion(client, prompt)
    else:
        raise RuntimeError("CICC_LLM_API_STYLE must be either 'chat' or 'responses'.")

    tex = strip_code_fence(raw_text)
    if not tex.startswith("\\documentclass{cicc}") or "\\begin{document}" not in tex or "\\end{document}" not in tex:
        raise RuntimeError("The model response did not look like a complete LaTeX document.")
    output_tex.write_text(tex + "\n", encoding="utf-8")
    return tex
