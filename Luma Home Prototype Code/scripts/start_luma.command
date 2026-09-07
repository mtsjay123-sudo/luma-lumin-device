#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
if curl -fsS --max-time 2 http://127.0.0.1:8095/api/session >/dev/null; then
  open http://127.0.0.1:8095/
  exit 0
fi
(
  for attempt in {1..40}; do
    if curl -fsS --max-time 1 http://127.0.0.1:8095/api/session >/dev/null 2>&1; then
      open http://127.0.0.1:8095/
      exit 0
    fi
    sleep 0.25
  done
) &
exec .venv/bin/python -m luma.cli serve
