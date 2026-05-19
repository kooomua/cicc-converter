from __future__ import annotations

import difflib
import json
import re
from pathlib import Path
from typing import Any

from .config import (
    LAYOUT_REPAIR_TEXT_LIMIT,
    LLM_API_KEY,
    LLM_API_STYLE,
    LLM_BASE_URL,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    LLM_THINKING,
)
from .latex_repairer import compact_eval_report
from .llm_client import openai_client_kwargs
from .openai_converter import strip_code_fence


LINE_RE = re.compile(r"\bline\s+(\d+)\b", re.IGNORECASE)
BEGIN_ENV_RE = re.compile(r"\\begin\{([^{}]+)\}")
END_ENV_RE = re.compile(r"\\end\{([^{}]+)\}")
TARGET_ENVS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "widetext",
    "figure",
    "figure*",
    "scheme",
    "scheme*",
    "table",
    "table*",
}


def compact_layout_report(layout_report: dict) -> str:
    compact = {
        "overall_visual_quality": layout_report.get("overall_visual_quality"),
        "issues": layout_report.get("issues", [])[:40],
        "notes": layout_report.get("notes", ""),
        "source": layout_report.get("source", ""),
    }
    return json.dumps(compact, indent=2, ensure_ascii=False)


def extract_issue_line(issue: dict[str, Any]) -> int | None:
    line = issue.get("line")
    if isinstance(line, int) and line > 0:
        return line
    for key in ("description", "detail"):
        match = LINE_RE.search(str(issue.get(key, "")))
        if match:
            return int(match.group(1))
    return None


def find_enclosing_block(lines: list[str], line_no: int) -> tuple[int, int, str]:
    index = max(0, min(len(lines) - 1, line_no - 1))

    start = index
    env_name = ""
    while start >= 0:
        begin_match = BEGIN_ENV_RE.search(lines[start])
        if begin_match and begin_match.group(1) in TARGET_ENVS:
            env_name = begin_match.group(1)
            break
        start -= 1

    if not env_name:
        start = max(0, index - 8)
        end = min(len(lines) - 1, index + 8)
        return start + 1, end + 1, "context"

    depth = 0
    end = start
    for cursor in range(start, len(lines)):
        for begin_match in BEGIN_ENV_RE.finditer(lines[cursor]):
            if begin_match.group(1) == env_name:
                depth += 1
        for end_match in END_ENV_RE.finditer(lines[cursor]):
            if end_match.group(1) == env_name:
                depth -= 1
                if depth <= 0:
                    end = cursor
                    return start + 1, end + 1, env_name
    return start + 1, min(len(lines), start + 80), env_name


def build_repair_blocks(tex_text: str, layout_report: dict) -> list[dict[str, Any]]:
    lines = tex_text.splitlines()
    blocks_by_range: dict[tuple[int, int], dict[str, Any]] = {}

    for issue in layout_report.get("issues", []) or []:
        line_no = extract_issue_line(issue)
        if not line_no:
            continue
        start_line, end_line, env_name = find_enclosing_block(lines, line_no)
        key = (start_line, end_line)
        block = blocks_by_range.setdefault(
            key,
            {
                "block_id": f"B{len(blocks_by_range) + 1}",
                "start_line": start_line,
                "end_line": end_line,
                "environment": env_name,
                "issues": [],
                "text": "\n".join(lines[start_line - 1 : end_line]),
            },
        )
        block["issues"].append(issue)

    return list(blocks_by_range.values())


def numbered_block_text(block: dict[str, Any]) -> str:
    start_line = int(block["start_line"])
    lines = str(block["text"]).splitlines()
    return "\n".join(f"{start_line + offset:05d}: {line}" for offset, line in enumerate(lines))


def build_layout_repair_prompt(
    tex_text: str,
    eval_report: dict,
    layout_report: dict,
    layout_repair_attempt: int,
) -> tuple[str, list[dict[str, Any]]]:
    blocks = build_repair_blocks(tex_text, layout_report)
    if not blocks:
        raise RuntimeError("No local equation/figure/table blocks could be extracted for layout repair.")

    block_sections = []
    for block in blocks:
        block_sections.append(
            "\n".join(
                [
                    f"## {block['block_id']}",
                    f"allowed_start_line: {block['start_line']}",
                    f"allowed_end_line: {block['end_line']}",
                    f"environment: {block['environment']}",
                    "issues:",
                    json.dumps(block["issues"], indent=2, ensure_ascii=False),
                    "current_latex_with_line_numbers:",
                    numbered_block_text(block),
                ]
            )
        )

    repair_blocks_text = "\n\n---\n\n".join(block_sections)
    prompt = f"""
You are the CiCC Layout Repair agent.

The full LaTeX document already compiles. You are doing LOCAL PATCH repair only for equation, figure, and table layout issues.

Return strict JSON only. Do not return a full .tex file. Do not use markdown fences.

JSON schema:
{{
  "replacements": [
    {{
      "block_id": "B1",
      "start_line": 10,
      "end_line": 20,
      "replacement": "Complete replacement LaTeX for exactly this line range."
    }}
  ],
  "notes": "Short explanation."
}}

Rules:
- Only replace lines inside the allowed_start_line/allowed_end_line of a supplied block.
- Prefer replacing the complete supplied environment block rather than tiny fragments if that is safer.
- Preserve scientific meaning, citations, labels, captions, and figure filenames.
- Do not change text outside the supplied blocks.
- Do not remove colored text or general visual anomalies unless they are inside a supplied equation/table/figure block and directly cause the reported issue.
- For over-wide tables, prefer `table*` with `[!t]`, wrapped `p{{...}}` columns, shorter column headers, or `\\small` before whole-table scaling.
- For over-wide equations, prefer `widetext`, `split`, `aligned`, and earlier line breaks.
- For figure issues, adjust figure vs. figure*, width, placement, centering, and caption order.
- Do not add `amsthm`.
- Keep replacements syntactically complete and compilable.

Layout repair attempt: {layout_repair_attempt}

Evaluator report:
{compact_eval_report(eval_report)}

Layout QA report:
{compact_layout_report(layout_report)}

Repair blocks:
{repair_blocks_text}
""".strip()
    if len(prompt) > LAYOUT_REPAIR_TEXT_LIMIT:
        raise RuntimeError("The local layout repair prompt is too large. Reduce the number of reported blocks.")
    return prompt, blocks


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def create_layout_repair_chat_completion(client: object, prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise LaTeX patch repair agent. You return strict JSON replacements "
                "for local equation, figure, and table blocks only."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_tokens": min(LLM_MAX_OUTPUT_TOKENS, 24000),
    }
    if LLM_REASONING_EFFORT in {"high", "max"}:
        kwargs["reasoning_effort"] = LLM_REASONING_EFFORT
    if LLM_THINKING in {"enabled", "disabled"}:
        kwargs["extra_body"] = {"thinking": {"type": LLM_THINKING}}
    if not LLM_THINKING and "reasoner" not in LLM_MODEL and "v4-pro" not in LLM_MODEL:
        kwargs["temperature"] = 0.1

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def create_layout_repair_responses_completion(client: object, prompt: str) -> str:
    response = client.responses.create(
        model=LLM_MODEL,
        instructions=(
            "You are a precise LaTeX patch repair agent. You return strict JSON replacements "
            "for local equation, figure, and table blocks only."
        ),
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        max_output_tokens=min(LLM_MAX_OUTPUT_TOKENS, 24000),
    )
    text = getattr(response, "output_text", None)
    return str(text) if text else str(response)


def validate_replacements(payload: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed_ranges = {
        str(block["block_id"]): (int(block["start_line"]), int(block["end_line"]))
        for block in blocks
    }
    replacements = payload.get("replacements", [])
    if not isinstance(replacements, list) or not replacements:
        raise RuntimeError("Layout repair returned no replacements.")

    validated: list[dict[str, Any]] = []
    for item in replacements:
        if not isinstance(item, dict):
            continue
        block_id = str(item.get("block_id", "")).strip()
        if block_id not in allowed_ranges:
            raise RuntimeError(f"Layout repair returned replacement for unknown block_id={block_id}.")
        start_line = int(item.get("start_line", 0))
        end_line = int(item.get("end_line", 0))
        allowed_start, allowed_end = allowed_ranges[block_id]
        if start_line < allowed_start or end_line > allowed_end or end_line < start_line:
            raise RuntimeError(
                f"Layout repair replacement for {block_id} is outside allowed range "
                f"{allowed_start}-{allowed_end}: {start_line}-{end_line}."
            )
        replacement = str(item.get("replacement", "")).strip("\n")
        if not replacement.strip():
            raise RuntimeError(f"Layout repair replacement for {block_id} is empty.")
        validated.append(
            {
                "block_id": block_id,
                "start_line": start_line,
                "end_line": end_line,
                "replacement": replacement,
            }
        )

    validated.sort(key=lambda item: item["start_line"])
    for previous, current in zip(validated, validated[1:]):
        if current["start_line"] <= previous["end_line"]:
            raise RuntimeError("Layout repair returned overlapping replacements.")
    return validated


def apply_replacements(tex_text: str, replacements: list[dict[str, Any]]) -> str:
    lines = tex_text.splitlines()
    for item in sorted(replacements, key=lambda entry: entry["start_line"], reverse=True):
        start = int(item["start_line"]) - 1
        end = int(item["end_line"])
        replacement_lines = str(item["replacement"]).splitlines()
        lines[start:end] = replacement_lines
    return "\n".join(lines) + "\n"


def repair_layout_with_ai(
    tex_file: Path,
    eval_report: dict,
    visual_report: dict,
    repair_log_dir: Path,
    layout_repair_attempt: int,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai Python package is not installed. Run pip install -r requirements.txt.") from exc

    if not LLM_API_KEY or LLM_API_KEY == "replace_me":
        raise RuntimeError("CICC_LLM_API_KEY is not set. Add your API key to .env before running layout repair.")

    tex_text = tex_file.read_text(encoding="utf-8")
    prompt, blocks = build_layout_repair_prompt(tex_text, eval_report, visual_report, layout_repair_attempt)
    repair_log_dir.mkdir(parents=True, exist_ok=True)
    (repair_log_dir / "layout_repair_prompt.txt").write_text(prompt, encoding="utf-8")
    (repair_log_dir / "layout_repair_blocks.json").write_text(
        json.dumps(blocks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    client_kwargs = openai_client_kwargs(LLM_API_KEY, LLM_BASE_URL)
    client = OpenAI(**client_kwargs)

    if LLM_API_STYLE == "chat":
        raw_text = create_layout_repair_chat_completion(client, prompt)
    elif LLM_API_STYLE == "responses":
        raw_text = create_layout_repair_responses_completion(client, prompt)
    else:
        raise RuntimeError("CICC_LLM_API_STYLE must be either 'chat' or 'responses'.")

    (repair_log_dir / "layout_repair_response.json").write_text(raw_text + "\n", encoding="utf-8")
    payload = extract_json_object(raw_text)
    replacements = validate_replacements(payload, blocks)
    repaired = apply_replacements(tex_text, replacements)

    if (
        not repaired.startswith("\\documentclass{cicc}")
        or "\\begin{document}" not in repaired
        or "\\end{document}" not in repaired
    ):
        raise RuntimeError("Applying layout repair patches produced an incomplete LaTeX document.")

    (repair_log_dir / "layout_repair_applied_replacements.json").write_text(
        json.dumps(replacements, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (repair_log_dir / "layout_repair_diff.patch").write_text(
        "\n".join(
            difflib.unified_diff(
                tex_text.splitlines(),
                repaired.splitlines(),
                fromfile=f"{tex_file.name}.before",
                tofile=f"{tex_file.name}.after",
                lineterm="",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    tex_file.write_text(repaired, encoding="utf-8")
    return repaired
