@echo off
REM BreakGuard - Setup Script for Windows
REM This script installs dependencies and sets up the environment.

echo.
echo ============================================================
echo   BreakGuard - Setup Script
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    exit /b 1
)

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker is not installed.
    echo Endee server requires Docker. Install from https://docker.com
    echo You can still install Python dependencies.
)

echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)
echo [OK] Dependencies installed.

echo.
echo [2/3] Starting Endee server via Docker...
docker compose up -d
if errorlevel 1 (
    echo [WARNING] Could not start Endee server.
    echo Make sure Docker is running and try: docker compose up -d
) else (
    echo [OK] Endee server started on http://localhost:8080
    REM Wait for server to be ready
    echo Waiting for Endee to be ready...
    timeout /t 5 /nobreak >nul
)

echo.
echo [3/3] Building API knowledge base...
python build_knowledge_base.py
if errorlevel 1 (
    echo [ERROR] Failed to build knowledge base.
    echo Make sure Endee server is running on http://localhost:8080
    exit /b 1
)
echo [OK] Knowledge base built.

echo.
echo ============================================================
echo   Setup complete! Run BreakGuard:
echo.
echo   python breakguard.py ./test_project --from 17 --to 18
echo ============================================================
echo.
