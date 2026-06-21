#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "📬 Agent Mail — setup"
echo

[ -f .env ] || { cp .env.example .env; echo "→ .env créé (à remplir)"; }
[ -f preferences.md ] || { cp preferences.example.md preferences.md; echo "→ preferences.md créé (à remplir)"; }

echo
echo "Étapes :"
echo "  1) Édite .env          → ton Gmail + mot de passe d'application (https://myaccount.google.com/apppasswords)"
echo "  2) Édite preferences.md → tes VIP, tes expéditeurs à museler, ta voix"
echo "  3) Lance ./run.sh"
echo

if command -v claude >/dev/null 2>&1; then echo "Claude Code : ✓"; else echo "Claude Code : ✗ → https://claude.com/claude-code"; fi
if python3 -c "import imaplib" 2>/dev/null; then echo "Python 3    : ✓"; else echo "Python 3    : ✗ (requis)"; fi
