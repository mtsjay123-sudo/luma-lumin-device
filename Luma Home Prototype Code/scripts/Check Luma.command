#!/bin/zsh
# Double-click: does Luma sound like a person and get things done? (uses your local model; nothing is sent)
cd "$(dirname "$0")/.."
.venv/bin/python scripts/luma_check.py --save "luma-check-$(date +%Y%m%d-%H%M).json"
echo
echo "Done. Copy everything above (or the saved .json file) and send it to Claude."
read -k1 "?Press any key to close…"
