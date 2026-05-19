#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env. Open it and replace OPENAI_API_KEY=replace_me with your API key."
else
  echo ".env already exists. I did not overwrite it."
fi

echo "Setup complete."

