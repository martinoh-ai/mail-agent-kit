#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Manque .env — lance d'abord ./setup.sh"; exit 1; }
[ -f preferences.md ] || { echo "Manque preferences.md — lance d'abord ./setup.sh"; exit 1; }

# charge tes identifiants Gmail
set -a; . ./.env; set +a

command -v claude >/dev/null 2>&1 || { echo "Claude Code requis → https://claude.com/claude-code"; exit 1; }

# Claude Code lit triage.md, appelle gmail_helper.py (Bash), classe, sauve les brouillons.
claude -p "$(cat triage.md)" --allowed-tools "Bash" "Read"
