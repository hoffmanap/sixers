@echo off
REM Pulls fresh 2026-27 data, rebuilds docs/live_data.json, and pushes it to GitHub.
cd /d "%~dp0"
git pull --rebase --autostash
python update_live.py
if errorlevel 1 (
  echo Pull failed - nothing pushed.
  exit /b 1
)
git add docs/live_data.json
git diff --cached --quiet && (echo No changes. & exit /b 0)
git commit -m "Update live tracker data"
git push
