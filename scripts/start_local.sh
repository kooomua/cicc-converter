#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run: bash scripts/setup_local.sh"
  exit 1
fi

source .venv/bin/activate

echo "Starting CiCC Pipeline local browser app..."
echo "Open this address in your browser:"
echo "http://localhost:8000"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

