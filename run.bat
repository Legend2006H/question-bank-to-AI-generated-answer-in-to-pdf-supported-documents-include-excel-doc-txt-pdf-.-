@echo off
echo.
echo  QB Solver - Question Bank Answer Generator
echo  ==========================================
echo.

if "%~1"=="" (
    echo  Drag and drop your question bank file onto this window,
    echo  OR type the file path below:
    echo.
    set /p FILEPATH=" File path: "
    python qb_solver.py "%FILEPATH%"
) else (
    python qb_solver.py "%~1"
)

echo.
pause
