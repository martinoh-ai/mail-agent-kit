#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Manque .env — lance d'abord ./setup.sh"; exit 1; }
[ -f preferences.md ] || { echo "Manque preferences.md — lance d'abord ./setup.sh"; exit 1; }

set -a; . ./.env; set +a

command -v claude >/dev/null 2>&1 || { echo "Claude Code requis → https://claude.com/claude-code"; exit 1; }

# Claude Code scanne tes 90 derniers jours et te pose une revue d'abonnements en brouillon.
claude -p "$(cat newsletters.md)" --allowed-tools "Bash" "Read"
