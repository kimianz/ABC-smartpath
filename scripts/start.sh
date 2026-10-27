#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && [ -d .venv ] || { echo 'Run bash scripts/setup.sh first.'; exit 1; }
# Pick up the verified Homebrew Node 22 in new Terminal windows too.
if [ -x /opt/homebrew/opt/node@22/bin/node ]; then
  export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
fi
command -v npm >/dev/null || { echo 'npm is unavailable. Install Node.js 22 and reopen Terminal.'; exit 1; }
set -a; source .env; set +a
export HF_HOME="$PWD/.hf-cache"
export LANGCHAIN_TRACING_V2=false
export TOKENIZERS_PARALLELISM=false
exec .venv/bin/python scripts/run_services.py
