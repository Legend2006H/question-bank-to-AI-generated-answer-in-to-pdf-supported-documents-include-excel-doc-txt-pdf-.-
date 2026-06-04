#!/bin/bash
echo ""
echo " QB Solver - Question Bank Answer Generator"
echo " =========================================="
echo ""

if [ -z "$1" ]; then
    read -p " Enter file path: " FILEPATH
    python3 qb_solver.py "$FILEPATH"
else
    python3 qb_solver.py "$1"
fi
