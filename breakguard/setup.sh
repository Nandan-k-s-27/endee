#!/bin/bash
# BreakGuard - Setup Script for Linux/macOS
# This script installs dependencies and sets up the environment.

set -e

echo ""
echo "============================================================"
echo "  BreakGuard - Setup Script"
echo "============================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3.8+ first."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[WARNING] Docker is not installed."
    echo "Endee server requires Docker. Install from https://docker.com"
fi

echo "[1/3] Installing Python dependencies..."
pip3 install -r requirements.txt
echo "[OK] Dependencies installed."

echo ""
echo "[2/3] Starting Endee server via Docker..."
docker compose up -d || {
    echo "[WARNING] Could not start Endee server."
    echo "Make sure Docker is running and try: docker compose up -d"
}
echo "Waiting for Endee to be ready..."
sleep 5

echo ""
echo "[3/3] Building API knowledge base..."
python3 build_knowledge_base.py
echo "[OK] Knowledge base built."

echo ""
echo "============================================================"
echo "  Setup complete! Run BreakGuard:"
echo ""
echo "  python3 breakguard.py ./test_project --from 17 --to 18"
echo "============================================================"
echo ""
