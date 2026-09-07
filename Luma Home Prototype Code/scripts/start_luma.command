#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
if curl -fsS --max-time 2 http://127.0.0.1:8095/api/session >/dev/null; then
  open http://127.0.0.1:8095/
  exit 0
fi
(open http://127.0.0.1:8095/ >/dev/null 2>&1) &
exec .venv/bin/python -m luma.cli serve
