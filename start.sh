#!/bin/bash
set -e

echo "============================================"
echo "  EcoLink AI — MyHack 2026"
echo "============================================"

# Backend
cd backend
if [ ! -f ".env" ]; then
  echo "⚠  backend/.env not found — copy from backend/.env.example and fill in keys"
  exit 1
fi

echo "Installing Python dependencies..."
pip install -r requirements.txt -q

echo "Starting FastAPI backend on :8000..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Give backend a moment to start
sleep 2

# Frontend
cd frontend
if [ ! -f ".env.local" ]; then
  echo "⚠  frontend/.env.local not found — copy from frontend/.env.local.example and fill in keys"
  kill $BACKEND_PID
  exit 1
fi

echo "Installing Node dependencies..."
npm install -q

echo "Starting Next.js frontend on :3000..."
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "============================================"
echo "  EcoLink AI is running!"
echo ""
echo "  Frontend  → http://localhost:3000"
echo "  Backend   → http://localhost:8000"
echo "  API docs  → http://localhost:8000/docs"
echo ""
echo "  First time? Run:"
echo "    cd backend && python seed.py"
echo "============================================"
echo ""

trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
wait
