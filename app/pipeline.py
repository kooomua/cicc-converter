from __future__ import annotations

import json
import traceback
from pathlib import Path

from .config import (
    EVAL_LAYOUT_REPAIR_ENABLED,
    MAX_CONVERSION_ATTEMPTS,
    MAX_LAYOUT_REPAIR_ATTEMPTS,
    MAX_REPAIR_ATTEMPTS,
)
from .evaluator import copy_supporting_files, evaluate_output
from .inspector import inspect_input
from .layout_repairer import repair_layout_with_ai
from .latex_repairer import repair_tex_with_ai
from .openai_converter import convert_with_openai
from .postprocess import postprocess_tex
from .storage import make_zip, read_status, update_status


def feedback_from_eval(eval_report: dict) -> str:
    compact = {
        "overall_result": eval_report.get("overall_result"),
        "recommended_action": eval_report.get("recommended_action"),
        "static_issues": eval_report.get("static_report", {}).get("issues", [])[:80],
        "compile_errors": eval_report.get("compile_report", {}).get("errors", [])[:40],
        "compile_warnings": eval_report.get("compile_report", {}).get("warnings", [])[:40],
    }
    return json.dumps(compact, indent=2, ensure_ascii=False)


def package_and_finish(
    job_root: Path,
    output_dir: Path,
    manuscript_id: str,
    eval_report: dict,
    attempts_used: int,
    layout_report: dict | None = None,
) -> None:
    update_status(job_root, stage="packaging")
    zip_path = make_zip(output_dir, job_root / f"{manuscript_id}_output.zip")
    layout_quality = (layout_report or {}).get("overall_visual_quality")
    evaluator_passed = eval_report["overall_result"] == "pass"
    layout_passed = layout_quality in {None, "pass"}
    final_status = "completed" if evaluator_passed and layout_passed else "completed_with_warnings"
    if not evaluator_passed:
        error = "Output generated, but evaluator reported issues."
    elif not layout_passed:
        error = "Output generated, but evaluator reported remaining equation/figure/table layout warnings."
    else:
        error = None
    update_status(
        job_root,
        status=final_status,
        stage="done",
        error=error,
        result_zip=str(zip_path),
        attempts_used=attempts_used,
        max_attempts=MAX_CONVERSION_ATTEMPTS,
        max_repair_attempts=MAX_REPAIR_ATTEMPTS,
        max_layout_repair_attempts=MAX_LAYOUT_REPAIR_ATTEMPTS,
        conversion_route="direct_ai",
        layout_report=layout_report,
    )


LAYOUT_WARNING_RULE_TYPES = {
    "equation-line-length": "equation_layout_issue",
    "equation-split": "equation_layout_issue",
    "figure-width": "figure_layout_issue",
    "table-width-risk": "table_layout_issue",
}


def evaluator_layout_report(eval_report: dict) -> dict:
    issues = []
    for issue in eval_report.get("static_report", {}).get("issues", []):
        rule = issue.get("rule")
        if rule not in LAYOUT_WARNING_RULE_TYPES:
            continue
        issues.append(
            {
                "type": LAYOUT_WARNING_RULE_TYPES[rule],
                "severity": "major",
                "pages": [],
                "description": f"Evaluator reported {rule} at line {issue.get('line')}: {issue.get('detail')}",
                "suggested_fix": (
                    "Make a local LaTeX layout repair for this equation, figure, or table. "
                    "Do not change unrelated text, font color, or general style."
                ),
            }
        )

    return {
        "overall_visual_quality": "needs_layout_repair" if issues else "pass",
        "issues": issues,
        "notes": (
            "Evaluator found equation/figure/table layout warnings."
            if issues
            else "Evaluator found no equation/figure/table layout warnings targeted for repair."
        ),
        "source": "evaluator_static_warnings",
    }


def run_evaluator_layout_repair_gate(
    job_root: Path,
    output_dir: Path,
    manuscript_id: str,
    output_tex: Path,
    eval_report: dict,
    attempts_used: int,
) -> tuple[dict, dict]:
    run_log_dir = job_root / "run_log"
    layout_report = evaluator_layout_report(eval_report)
    (run_log_dir / "latest_evaluator_layout_report.json").write_text(
        json.dumps(layout_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if (
        not EVAL_LAYOUT_REPAIR_ENABLED
        or eval_report["overall_result"] != "pass"
        or layout_report.get("overall_visual_quality") != "needs_layout_repair"
    ):
        return eval_report, layout_report

    for layout_attempt in range(1, MAX_LAYOUT_REPAIR_ATTEMPTS + 1):
        layout_log_dir = run_log_dir / f"evaluator_layout_repair_{layout_attempt}"
        update_status(
            job_root,
            status="running",
            stage=f"evaluator_layout_repair_{layout_attempt}",
            attempts_used=attempts_used,
            max_layout_repair_attempts=MAX_LAYOUT_REPAIR_ATTEMPTS,
        )
        try:
            repair_layout_with_ai(
                tex_file=output_tex,
                eval_report=eval_report,
                visual_report=layout_report,
                repair_log_dir=layout_log_dir,
                layout_repair_attempt=layout_attempt,
            )
        except Exception:
            layout_log_dir.mkdir(parents=True, exist_ok=True)
            (layout_log_dir / "layout_repair_error.txt").write_text(
                traceback.format_exc(),
                encoding="utf-8",
            )
            return eval_report, {
                "overall_visual_quality": "needs_user_review",
                "issues": [
                    {
                        "type": "general_layout_anomaly",
                        "severity": "major",
                        "pages": [],
                        "description": "Evaluator-based Layout Repairer failed before producing a valid complete .tex file.",
                        "suggested_fix": "Review evaluator_layout_repair_* logs and rerun.",
                    }
                ],
                "notes": "Evaluator-based layout repair failed.",
                "source": "evaluator_static_warnings",
            }

        postprocess_tex(output_tex, output_dir)
        (output_dir / f"{manuscript_id}.evaluator_layout_repair_{layout_attempt}.tex").write_text(
            output_tex.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        update_status(
            job_root,
            status="running",
            stage=f"evaluator_layout_check_{layout_attempt}",
            attempts_used=attempts_used,
        )
        eval_report = evaluate_output(output_dir, manuscript_id, layout_log_dir)
        (run_log_dir / "latest_eval_report.json").write_text(
            json.dumps(eval_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if eval_report["overall_result"] != "pass":
            return eval_report, {
                "overall_visual_quality": "needs_user_review",
                "issues": [
                    {
                        "type": "general_layout_anomaly",
                        "severity": "critical",
                        "pages": [],
                        "description": "Evaluator-based layout repair introduced evaluator or compile issues.",
                        "suggested_fix": "Inspect latest_eval_report.json before another layout repair.",
                    }
                ],
                "notes": "Layout repair did not preserve evaluator pass status.",
                "source": "evaluator_static_warnings",
            }

        layout_report = evaluator_layout_report(eval_report)
        (run_log_dir / "latest_evaluator_layout_report.json").write_text(
            json.dumps(layout_report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if layout_report.get("overall_visual_quality") != "needs_layout_repair":
            return eval_report, layout_report

    return eval_report, layout_report


def run_job(job_root: Path, primary_source: str | None = None) -> None:
    status = read_status(job_root)
    manuscript_id = status["manuscript_id"]
    input_dir = job_root / "input"
    output_dir = job_root / "output"
    run_log_dir = job_root / "run_log"
    output_tex = output_dir / f"{manuscript_id}.tex"

    try:
        update_status(job_root, status="running", stage="inspector")
        inspection = inspect_input(job_root, manuscript_id, primary_source=primary_source)
        if not inspection["ready_to_convert"]:
            update_status(job_root, status="failed", stage="inspector", error=inspection["notes"])
            return

        copy_supporting_files(input_dir, output_dir)
        feedback_text = None
        eval_report = None
        attempts_used = 0

        for attempt in range(1, MAX_CONVERSION_ATTEMPTS + 1):
            attempts_used = attempt
            attempt_log_dir = run_log_dir / f"attempt_{attempt}"
            attempt_log_dir.mkdir(parents=True, exist_ok=True)

            update_status(
                job_root,
                status="running",
                stage=f"converter_attempt_{attempt}",
                error=None,
                attempts_used=attempts_used,
                max_attempts=MAX_CONVERSION_ATTEMPTS,
                max_repair_attempts=MAX_REPAIR_ATTEMPTS,
                conversion_route="direct_ai",
            )
            convert_with_openai(
                input_dir=input_dir,
                output_tex=output_tex,
                recommended_path=inspection["recommended_path"],
                manuscript_id=manuscript_id,
                primary_tex_file=inspection.get("primary_tex_file"),
                feedback_text=feedback_text,
                attempt=attempt,
            )
            copy_supporting_files(input_dir, output_dir)
            postprocess_tex(output_tex, output_dir)
            (output_dir / f"{manuscript_id}.attempt_{attempt}.tex").write_text(
                output_tex.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            update_status(
                job_root,
                stage=f"evaluator_attempt_{attempt}",
                attempts_used=attempts_used,
                conversion_route="direct_ai",
            )
            eval_report = evaluate_output(output_dir, manuscript_id, attempt_log_dir)
            (run_log_dir / "latest_eval_report.json").write_text(
                json.dumps(eval_report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            if eval_report["overall_result"] == "pass":
                break

            repair_error_feedback = None
            for repair_attempt in range(1, MAX_REPAIR_ATTEMPTS + 1):
                repair_log_dir = attempt_log_dir / f"repair_{repair_attempt}"
                previous_compile_log = (
                    attempt_log_dir / "compile_output.txt"
                    if repair_attempt == 1
                    else attempt_log_dir / f"repair_{repair_attempt - 1}" / "compile_output.txt"
                )
                update_status(
                    job_root,
                    status="running",
                    stage=f"repair_attempt_{attempt}_{repair_attempt}",
                    attempts_used=attempts_used,
                    max_attempts=MAX_CONVERSION_ATTEMPTS,
                    max_repair_attempts=MAX_REPAIR_ATTEMPTS,
                    conversion_route="direct_ai",
                )
                try:
                    repair_tex_with_ai(
                        tex_file=output_tex,
                        eval_report=eval_report,
                        compile_log=previous_compile_log,
                        repair_log_dir=repair_log_dir,
                        repair_attempt=repair_attempt,
                    )
                except Exception as repair_exc:
                    repair_log_dir.mkdir(parents=True, exist_ok=True)
                    (repair_log_dir / "repair_error.txt").write_text(
                        traceback.format_exc(),
                        encoding="utf-8",
                    )
                    repair_error_feedback = feedback_from_eval(eval_report) + f"\n\nAI repair failed: {repair_exc}"
                    break
                postprocess_tex(output_tex, output_dir)
                (output_dir / f"{manuscript_id}.attempt_{attempt}.repair_{repair_attempt}.tex").write_text(
                    output_tex.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
                eval_report = evaluate_output(output_dir, manuscript_id, repair_log_dir)
                (run_log_dir / "latest_eval_report.json").write_text(
                    json.dumps(eval_report, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                if eval_report["overall_result"] == "pass":
                    break

            if eval_report["overall_result"] == "pass":
                break
            feedback_text = repair_error_feedback or feedback_from_eval(eval_report)

        assert eval_report is not None
        layout_report = None
        if eval_report["overall_result"] == "pass":
            eval_report, layout_report = run_evaluator_layout_repair_gate(
                job_root,
                output_dir,
                manuscript_id,
                output_tex,
                eval_report,
                attempts_used,
            )
        package_and_finish(job_root, output_dir, manuscript_id, eval_report, attempts_used, layout_report)
    except Exception as exc:
        (run_log_dir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        update_status(job_root, status="failed", stage="error", error=str(exc))
