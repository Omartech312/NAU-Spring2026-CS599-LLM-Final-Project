#!/bin/bash
# CitationLLM Setup Script
# Run this from the project root: ./setup.sh

set -e

echo "=== CitationLLM Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required"
    exit 1
fi

echo "Python and Node.js found."

# Backend setup
echo ""
echo "Setting up backend..."
cd backend

if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "Please edit backend/.env with your API keys and database URL"
fi

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q -r requirements.txt

cd ..

# Frontend setup
echo ""
echo "Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

cd ..

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys and DATABASE_URL"
echo "2. Make sure PostgreSQL is running with pgvector enabled"
echo "3. Start backend: cd backend && source venv/bin/activate && python run.py"
echo "4. Start frontend: cd frontend && npm run dev"
echo "5. Open http://localhost:3000 in your browser"
echo ""
echo "Database setup:"
echo "  createdb citation_llm"
echo "  psql -d citation_llm -c \"CREATE EXTENSION IF NOT EXISTS vector;\""
