@echo off
title AI KPI Copilot - Module 6 Backend
cd /d "%~dp0"
echo.
echo  ==========================================
echo   AI KPI Copilot - Module 6
echo   Server: http://localhost:8997
echo   Docs:   http://localhost:8997/docs
echo   Test:   test_ui.html
echo  ==========================================
echo.

:: Mo test UI tren trinh duyet
start "" "%~dp0test_ui.html"

:: Khoi dong server
uv run uvicorn main:app --port 8997 --reload
