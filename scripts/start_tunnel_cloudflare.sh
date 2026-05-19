#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Missing cloudflared. Install it with: brew install cloudflared"
  exit 1
fi

echo "Starting Cloudflare Quick Tunnel for CiCC Converter..."
echo "Keep this terminal open while sharing the generated https://*.trycloudflare.com URL."
echo ""

cloudflared tunnel --url http://localhost:8000
