#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3.11 >/dev/null || { echo 'Install Python 3.11: brew install python@3.11'; exit 1; }
command -v node >/dev/null || { echo 'Install Node.js 22 LTS: brew install node@22'; exit 1; }
command -v npm >/dev/null || { echo 'npm is required with Node.js'; exit 1; }
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
if [ ! -f .env ]; then
  cp .env.example .env
  .venv/bin/python - <<'PY'
from pathlib import Path
import secrets
p=Path('.env');p.write_text(p.read_text().replace('REPLACE_WITH_32_RANDOM_BYTES',secrets.token_urlsafe(32)))
p.chmod(0o600)
PY
fi
(cd frontend && npm install)
(cd backend && ../.venv/bin/python -m app.ml)
HF_HOME="$PWD/.hf-cache" .venv/bin/python scripts/download_models.py
printf '\nSetup complete. Install/start Ollama, then: ollama pull qwen3:4b-instruct-2507-q4_K_M\nRun: ./scripts/start.sh\n'
