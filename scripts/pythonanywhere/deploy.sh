#!/bin/bash
# Set up or update Royal Shetkari POS on PythonAnywhere.
#
# Expects in the home directory:
#   royal_shetkari_release.zip   the code (git archive) plus db.sqlite3 and media/ if wanted
#   royal_shetkari.env           settings (becomes .env; never committed)
# Run it from a Bash console, or as a one-off scheduled task:
#   bash ~/royal_shetkari_deploy.sh > ~/deploy.log 2>&1
set -euo pipefail

APP="$HOME/royal-shetkari"
VENV="$HOME/.virtualenvs/royal-shetkari"
ZIP="$HOME/royal_shetkari_release.zip"
PY=python3.13

echo "== $(date -u) start"
mkdir -p "$APP"
if [ -f "$ZIP" ]; then
    # Keep the live database and uploads unless the release brings its own.
    unzip -oq "$ZIP" -d "$APP"
    rm -f "$ZIP"
fi
[ -f "$HOME/royal_shetkari.env" ] && mv -f "$HOME/royal_shetkari.env" "$APP/.env"

if [ ! -x "$VENV/bin/python" ]; then
    echo "== creating virtualenv"
    $PY -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP/requirements-pythonanywhere.txt"

cd "$APP"
if [ -f db.sqlite3 ]; then
    mkdir -p backups
    cp db.sqlite3 "backups/db_before_deploy_$(date -u +%Y%m%d_%H%M%S).sqlite3"
fi
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput -v 0
"$VENV/bin/python" manage.py check
echo "== $(date -u) done"
