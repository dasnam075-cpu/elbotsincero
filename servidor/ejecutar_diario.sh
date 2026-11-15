#!/usr/bin/env bash
# Lo ejecuta cron una vez al día. Corre el bot y publica el registro en GitHub.
DIR="$HOME/elbotsincero"
LOG="$HOME/elbot.log"
cd "$DIR" || exit 1
{
  echo "===== $(date -u '+%Y-%m-%d %H:%M UTC') ====="
  git pull -q --rebase || echo "Aviso: no se pudo actualizar desde GitHub"
  set -a; . "$HOME/.elbot.env"; set +a
  if .venv/bin/python bot.py; then
    git add registro
    git diff --cached --quiet || { git commit -qm "Registro $(date -u +%F)" && git push -q; }
  else
    echo "ERROR: el bot terminó con error"
  fi
} >> "$LOG" 2>&1
