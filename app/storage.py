from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import JOBS_ROOT


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_name(name: str) -> str:
    name = Path(name).name.strip()
    cleaned = SAFE_NAME_RE.sub("_", name)
    return cleaned or "uploaded_file"


def new_job_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def job_dir(job_id: str) -> Path:
    return JOBS_ROOT / job_id


def init_job(job_id: str, manuscript_id: str | None = None) -> Path:
    root = job_dir(job_id)
    (root / "input").mkdir(parents=True, exist_ok=False)
    (root / "output").mkdir(parents=True, exist_ok=True)
    (root / "run_log").mkdir(parents=True, exist_ok=True)
    status = {
        "job_id": job_id,
        "manuscript_id": manuscript_id or job_id,
        "status": "created",
        "stage": "upload",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "error": None,
        "result_zip": None,
    }
    write_status(root, status)
    return root


def read_status(root: Path) -> dict[str, Any]:
    with (root / "status.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def write_status(root: Path, status: dict[str, Any]) -> None:
    status["updated_at"] = utc_now()
    with (root / "status.json").open("w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def update_status(root: Path, **changes: Any) -> dict[str, Any]:
    status = read_status(root)
    status.update(changes)
    write_status(root, status)
    return status


def extract_zip_safely(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe zip member: {member.filename}")
            target = dest / member_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def make_zip(source_dir: Path, zip_path: Path) -> Path:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir))
    return zip_path


def flatten_single_top_level_dir(input_dir: Path) -> None:
    while True:
        visible_entries = [
            p
            for p in input_dir.iterdir()
            if p.name != "__MACOSX" and not p.name.startswith(".")
        ]
        files = [p for p in visible_entries if p.is_file()]
        dirs = [p for p in visible_entries if p.is_dir()]
        if files or len(dirs) != 1:
            return

        nested = dirs[0]
        for child in nested.iterdir():
            target = input_dir / child.name
            if target.exists():
                raise ValueError(f"Cannot flatten upload because {target.name} already exists.")
            shutil.move(str(child), str(target))
        shutil.rmtree(nested, ignore_errors=True)
