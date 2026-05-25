from __future__ import annotations

import base64
import binascii
import secrets
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles

from .config import (
    AUTH_ENABLED,
    AUTH_PASSWORD,
    AUTH_USERNAME,
    BIBTEX_BIN,
    EVAL_LAYOUT_REPAIR_ENABLED,
    JOBS_ROOT,
    LLM_API_KEY,
    LLM_API_STYLE,
    LLM_BASE_URL,
    LLM_MODEL,
    MAX_LAYOUT_REPAIR_ATTEMPTS,
    MAX_UPLOAD_MB,
    MAX_CONVERSION_ATTEMPTS,
    MAX_REPAIR_ATTEMPTS,
    PANDOC_BIN,
    PDFLATEX_BIN,
    PROJECT_ROOT,
)
from .pipeline import run_job
from .storage import (
    extract_zip_safely,
    flatten_single_top_level_dir,
    init_job,
    job_dir,
    new_job_id,
    read_status,
    safe_name,
    update_status,
)


app = FastAPI(title="CiCC converter API", version="0.1.0")
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "app" / "static"), name="static")


def valid_basic_auth(authorization: str | None) -> bool:
    if not authorization or not authorization.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False
    return secrets.compare_digest(username, AUTH_USERNAME) and secrets.compare_digest(password, AUTH_PASSWORD)


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    if AUTH_ENABLED and not valid_basic_auth(request.headers.get("Authorization")):
        return PlainTextResponse(
            "Authentication required.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="CiCC Converter", charset="UTF-8"'},
        )
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    if bool(AUTH_USERNAME) != bool(AUTH_PASSWORD):
        raise RuntimeError("Set both CICC_AUTH_USERNAME and CICC_AUTH_PASSWORD, or leave both unset.")
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (PROJECT_ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "llm_api_key_configured": bool(LLM_API_KEY) and LLM_API_KEY != "replace_me",
        "openai_api_key_configured": bool(LLM_API_KEY) and LLM_API_KEY != "replace_me",
        "base_url": LLM_BASE_URL or "default OpenAI API",
        "api_style": LLM_API_STYLE,
        "model": LLM_MODEL,
        "max_attempts": MAX_CONVERSION_ATTEMPTS,
        "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        "max_layout_repair_attempts": MAX_LAYOUT_REPAIR_ATTEMPTS,
        "eval_layout_repair_enabled": EVAL_LAYOUT_REPAIR_ENABLED,
        "auth_enabled": AUTH_ENABLED,
        "tools": {
            "pdflatex": shutil.which(PDFLATEX_BIN),
            "bibtex": shutil.which(BIBTEX_BIN),
            "pandoc": shutil.which(PANDOC_BIN),
        },
        "optional_tools": {
            "soffice": shutil.which("soffice"),
        },
    }


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="Upload manuscript files or one zip file.")],
    manuscript_id: Annotated[str | None, Form()] = None,
    primary_source: Annotated[str | None, Form()] = None,
) -> dict[str, str]:
    primary_source = primary_source or None
    if primary_source not in {None, "docx", "tex"}:
        raise HTTPException(status_code=400, detail="primary_source must be docx or tex.")

    job_id = new_job_id()
    clean_manuscript_id = safe_name(manuscript_id or job_id)
    root = init_job(job_id, clean_manuscript_id)
    input_dir = root / "input"

    total = 0
    for upload in files:
        filename = safe_name(upload.filename or "uploaded_file")
        target = input_dir / filename
        with target.open("wb") as f:
            while chunk := await upload.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_MB * 1024 * 1024:
                    shutil.rmtree(root, ignore_errors=True)
                    raise HTTPException(status_code=413, detail=f"Uploads exceed {MAX_UPLOAD_MB} MB.")
                f.write(chunk)
        if target.suffix.lower() == ".zip":
            extract_zip_safely(target, input_dir)
            target.unlink()

    flatten_single_top_level_dir(input_dir)
    update_status(root, status="queued", stage="queued")
    background_tasks.add_task(run_job, root, primary_source)
    return {"job_id": job_id, "status_url": f"/api/jobs/{job_id}"}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    root = job_dir(safe_name(job_id))
    if not root.exists():
        raise HTTPException(status_code=404, detail="Job not found.")
    status = read_status(root)
    if status.get("result_zip"):
        status["download_url"] = f"/api/jobs/{job_id}/download"
    return status


@app.get("/api/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    root = job_dir(safe_name(job_id))
    if not root.exists():
        raise HTTPException(status_code=404, detail="Job not found.")
    status = read_status(root)
    result_zip = status.get("result_zip")
    if not result_zip or not Path(result_zip).exists():
        raise HTTPException(status_code=404, detail="Output zip is not ready.")
    return FileResponse(result_zip, filename=Path(result_zip).name, media_type="application/zip")
