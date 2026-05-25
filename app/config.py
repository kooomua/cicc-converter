from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_ROOT = Path(os.getenv("CICC_JOBS_DIR", PROJECT_ROOT / "jobs")).resolve()
MAX_UPLOAD_MB = int(os.getenv("CICC_MAX_UPLOAD_MB", "100"))
CONVERSION_MODE = os.getenv("CICC_CONVERSION_MODE", "auto").strip().lower()
LLM_API_KEY = os.getenv("CICC_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
LLM_BASE_URL = os.getenv("CICC_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
LLM_MODEL = os.getenv("CICC_LLM_MODEL") or os.getenv("CICC_OPENAI_MODEL", "gpt-4.1")
LLM_API_STYLE = os.getenv("CICC_LLM_API_STYLE", "responses").strip().lower()
LLM_REASONING_EFFORT = os.getenv("CICC_LLM_REASONING_EFFORT", "high").strip().lower()
LLM_THINKING = os.getenv("CICC_LLM_THINKING", "").strip().lower()
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("CICC_MAX_OUTPUT_TOKENS", "32768"))
LLM_TIMEOUT_SECONDS = float(os.getenv("CICC_LLM_TIMEOUT_SECONDS", "1200"))
LLM_MAX_RETRIES = int(os.getenv("CICC_LLM_MAX_RETRIES", "4"))
LLM_TRUST_ENV = os.getenv("CICC_LLM_TRUST_ENV", "false").strip().lower() in {"1", "true", "yes", "on"}
CONVERTER_TEXT_LIMIT = int(os.getenv("CICC_CONVERTER_TEXT_LIMIT", "360000"))
REPAIR_TEXT_LIMIT = int(os.getenv("CICC_REPAIR_TEXT_LIMIT", "360000"))
LAYOUT_REPAIR_TEXT_LIMIT = int(os.getenv("CICC_LAYOUT_REPAIR_TEXT_LIMIT", "160000"))
MAX_CONVERSION_ATTEMPTS = int(os.getenv("CICC_MAX_CONVERSION_ATTEMPTS", "3"))
MAX_REPAIR_ATTEMPTS = int(os.getenv("CICC_MAX_REPAIR_ATTEMPTS", "3"))
MAX_LAYOUT_REPAIR_ATTEMPTS = int(os.getenv("CICC_MAX_LAYOUT_REPAIR_ATTEMPTS", "1"))
EVAL_LAYOUT_REPAIR_ENABLED = os.getenv("CICC_EVAL_LAYOUT_REPAIR_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
PUBLIC_BASE_URL = os.getenv("CICC_PUBLIC_BASE_URL", "")
AUTH_USERNAME = os.getenv("CICC_AUTH_USERNAME", "").strip()
AUTH_PASSWORD = os.getenv("CICC_AUTH_PASSWORD", "")
AUTH_ENABLED = bool(AUTH_USERNAME and AUTH_PASSWORD)

PDFLATEX_BIN = os.getenv("PDFLATEX_BIN", "pdflatex")
BIBTEX_BIN = os.getenv("BIBTEX_BIN", "bibtex")
PANDOC_BIN = os.getenv("PANDOC_BIN", "pandoc")
