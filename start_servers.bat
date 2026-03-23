@echo off
echo Starting AstroQ v2 Servers...

:: Start Backend in a new terminal
start "AstroQ Backend" cmd /k "cd /d %~dp0backend && set PYTHONPATH=. && python -m uvicorn astroq.lk_prediction.api.server:app --host 0.0.0.0 --port 8000 --reload"

:: Start Frontend in a new terminal
start "AstroQ Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Servers are starting in separate windows.
