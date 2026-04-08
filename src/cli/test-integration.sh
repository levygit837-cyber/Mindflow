#!/bin/bash
# Test script for MindFlow CLI with backend integration

echo "=========================================="
echo "MindFlow CLI Integration Test"
echo "=========================================="
echo ""

# Check if backend is running
echo "Checking backend..."
if curl -s http://localhost:8000/v1/health > /dev/null 2>&1; then
    echo "✓ Backend is running on http://localhost:8000"
else
    echo "✗ Backend is not running"
    echo "Please start the backend first:"
    echo "  cd /home/levybonito/Projetos/MindFlow/python"
    echo "  source mindflow_backend/venv/bin/activate"
    echo "  python -m mindflow_backend.main"
    echo ""
    echo "Or use the demo mode without backend:"
    echo "  cd /home/levybonito/Projetos/MindFlow/src/cli"
    echo "  npx tsx demo.tsx"
    exit 1
fi

echo ""
echo "Starting MindFlow CLI..."
cd /home/levybonito/Projetos/MindFlow/src/cli
npx tsx entrypoints/cli.tsx
