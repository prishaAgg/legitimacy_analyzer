#!/bin/bash
# setup.sh — run once to install dependencies and create .env
# Usage: cd socratix/backend && bash setup.sh

set -e
cd "$(dirname "$0")"

echo "Creating virtual environment"
python3 -m venv venv
source venv/bin/activate

echo "Installing dependencies"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "Creating .env if not present"
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "⚠  .env created. Open it and fill in your API keys:"
  echo "   ANTHROPIC_API_KEY  — required for AI synthesis (console.anthropic.com)"
  echo "   SERPER_API_KEY     — required for web search: website, reviews, social (serper.dev)"
  echo "   NEWS_API_KEY       — optional: adverse media screening (newsapi.org)"
  echo "   GUARDIAN_API_KEY   — optional: Guardian news coverage (open-platform.theguardian.com)"
fi

echo ""
echo "✅ Setup complete."
echo ""
echo "Option 1 — Run with Docker (recommended):"
echo "   cd .. && docker compose up --build"
echo ""
echo "Option 2 — Run locally:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8000"
