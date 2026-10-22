@echo off
REM Pulls fresh 2026-27 data, rebuilds docs/live_data.json, and pushes it to GitHub.
REM Must be run from a clone of hoffmanap/sixers (not inside any other git repo).
cd /d "%~dp0"
git remote get-url origin 2>nul | findstr /i "hoffmanap/sixers" >nul
if errorlevel 1 (
  echo STOP: this folder's git remote is not hoffmanap/sixers. Nothing was changed.
  echo Clone it fresh:  git clone https://github.com/hoffmanap/sixers
  exit /b 1
)
git pull --rebase
if errorlevel 1 (
  echo git pull failed - nothing pushed.
  exit /b 1
)
python update_live.py
if errorlevel 1 (
  echo Pull failed - nothing pushed.
  exit /b 1
)
git add docs/live_data.json
git diff --cached --quiet && (echo No changes. & exit /b 0)
git commit -m "Update live tracker data"
git push
