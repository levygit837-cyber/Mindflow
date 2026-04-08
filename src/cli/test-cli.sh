#!/bin/bash
# Test script for MindFlow CLI

echo "=========================================="
echo "MindFlow CLI Integration Test"
echo "=========================================="
echo ""

cd /home/levybonito/Projetos/MindFlow/src/cli

# Type check
echo "Running type check..."
npm run typecheck 2>&1 | head -20

echo ""
echo "Starting MindFlow CLI..."
echo "Press Ctrl+C to exit"
echo ""

npx tsx demo.tsx
