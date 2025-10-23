#!/bin/bash

# Local development startup script

echo "🚀 Starting Status Dashboard..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if Node is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi

# Start backend in background
echo "📡 Starting backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Install Playwright if needed
if ! playwright --version &> /dev/null; then
    echo "Installing Playwright browsers..."
    playwright install chromium
fi

cd ..
python3 -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend in background
echo "🎨 Starting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Dashboard is starting..."
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap Ctrl+C and cleanup
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT

# Wait for both processes
wait
