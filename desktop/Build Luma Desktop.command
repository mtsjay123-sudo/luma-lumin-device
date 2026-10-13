#!/bin/zsh
# Double-click to build Luma.app for this Mac. The result opens in Finder:
# drag Luma into Applications.
set -eu
cd "$(dirname "$0")"
if ! command -v npm >/dev/null; then
  echo "Luma Desktop needs Node.js to build. Install it from https://nodejs.org (the LTS button), then double-click this again."
  exit 1
fi
npm ci
npm run dist:mac
open dist
