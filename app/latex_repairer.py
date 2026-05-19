from __future__ import annotations

import json
from pathlib import Path

from .config import (
    LLM_API_KEY,
    LLM_API_STYLE,
    LLM_BASE_URL,
    LLM_MAX_OUTPUT_TOKENS,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    LLM_THINKING,
    REPAIR_TEXT_LIMIT,
)
from .llm_client import openai_client_kwargs
from .openai_converter import MAX_CHAT_CONTINUATIONS, strip_code_fence


def compile_context(compile_log: Path, limit: int = 24_000) -> str:
    if not compile_log.exists():
        return "compile_output.txt was not found."
    text = compile_log.read_text(encoding="utf-8", errors="replace")
    error_positions = [idx for idx, line in enumerate(text.splitlines()) if line.startswith("!")]
    if not error_positions:
        return text[-limit:]

    lines = text.splitlines()
    snippets: list[str] = []
    for idx in error_positions[-5:]:
        start = max(0, idx - 8)
        end = min(len(lines), idx + 16)
        snippets.append("\n".join(lines[start:end]))
    snippets.append("## Tail of compile log\n" + text[-limit // 2 :])
    return "\n\n---\n\n".join(snippets)[-limit:]


def compact_eval_report(eval_report: dict) -> str:
    compact = {
        "overall_result": eval_report.get("overall_result"),
        "recommended_action": eval_report.get("recommended_action"),
        "static_issues": eval_report.get("static_report", {}).get("issues", [])[:60],
        "compile_errors": eval_report.get("compile_report", {}).get("errors", [])[:30],
        "compile_warnings": eval_report.get("compile_report", {}).get("warnings", [])[:40],
    }
    return json.dumps(compact, indent=2, ensure_ascii=False)


def build_repair_prompt(
    tex_text: str,
    eval_report: dict,
    compile_log_text: str,
    repair_attempt: int,
) -> str:
    prompt = f"""
You are the CiCC LaTeX Repair agent.

Repair the current converted LaTeX file so it compiles under cicc.cls and satisfies blocking evaluator issues.

Constraints:
- Return the full corrected .tex file only. Do not use markdown fences. Do not explain.
- Do not reconvert or rewrite the manuscript from scratch.
- Preserve the current manuscript content, section order, citations, labels, figures, bibliography command, and CiCC opening frame unless a reported error requires a local edit.
- Prefer the smallest local fix that resolves the reported compile/static failure.
- Do not replace real figure paths with `example-image` or other placeholder graphics. If a graphic path is wrong, preserve the intended figure number and choose the matching extracted file path instead.
- If the compile error is an undefined control sequence, either replace it with standard LaTeX or add a minimal non-conflicting definition in the preamble.
- Do not add `amsthm`. Do not reload packages already supplied by `cicc.cls` unless the current document already did so and it is not causing the error.
- Keep `\\documentclass{{cicc}}` as the first command.
- Ensure the file ends with `\\label{{lastpage}}` followed by `\\end{{document}}`.

Repair attempt: {repair_attempt}

Evaluator report:
{compact_eval_report(eval_report)}

Compile log context:
{compile_log_text}

Current .tex file:
{tex_text}
""".strip()
    if len(prompt) > REPAIR_TEXT_LIMIT:
        raise RuntimeError("The repair prompt is too large. The current MVP needs section-level repair for this file.")
    return prompt


def create_repair_chat_completion(client: object, prompt: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise LaTeX repair agent. You fix only the reported errors "
                "in an existing CiCC LaTeX file and return the full corrected .tex."
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
        kwargs["temperature"] = 0.1

    chunks: list[str] = []
    for _ in range(MAX_CHAT_CONTINUATIONS + 1):
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
                    "Continue the repaired LaTeX file exactly from the last character of your previous response. "
                    "Do not repeat any earlier content. Return only the continuation, ending with "
                    "`\\label{lastpage}` and `\\end{document}`."
                ),
            }
        )
        kwargs["messages"] = messages

    return "".join(chunks)


def create_repair_responses_completion(client: object, prompt: str) -> str:
    response = client.responses.create(
        model=LLM_MODEL,
        instructions=(
            "You are a precise LaTeX repair agent. You fix only the reported errors "
            "in an existing CiCC LaTeX file and return the full corrected .tex."
        ),
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
    )
    text = getattr(response, "output_text", None)
    return str(text) if text else str(response)


def repair_tex_with_ai(
    tex_file: Path,
    eval_report: dict,
    compile_log: Path,
    repair_log_dir: Path,
    repair_attempt: int,
) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai Python package is not installed. Run pip install -r requirements.txt.") from exc

    if not LLM_API_KEY or LLM_API_KEY == "replace_me":
        raise RuntimeError("CICC_LLM_API_KEY is not set. Add your API key to .env before running repair.")

    tex_text = tex_file.read_text(encoding="utf-8")
    prompt = build_repair_prompt(tex_text, eval_report, compile_context(compile_log), repair_attempt)
    repair_log_dir.mkdir(parents=True, exist_ok=True)
    (repair_log_dir / "repair_prompt.txt").write_text(prompt, encoding="utf-8")

    client_kwargs = openai_client_kwargs(LLM_API_KEY, LLM_BASE_URL)
    client = OpenAI(**client_kwargs)

    if LLM_API_STYLE == "chat":
        raw_text = create_repair_chat_completion(client, prompt)
    elif LLM_API_STYLE == "responses":
        raw_text = create_repair_responses_completion(client, prompt)
    else:
        raise RuntimeError("CICC_LLM_API_STYLE must be either 'chat' or 'responses'.")

    repaired = strip_code_fence(raw_text)
    (repair_log_dir / "repair_response.tex").write_text(repaired + "\n", encoding="utf-8")
    if (
        not repaired.startswith("\\documentclass{cicc}")
        or "\\begin{document}" not in repaired
        or "\\end{document}" not in repaired
    ):
        raise RuntimeError("The repair response did not look like a complete LaTeX document.")

    tex_file.write_text(repaired + "\n", encoding="utf-8")
    return repaired
