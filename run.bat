@echo off
REM ============================================================
REM  Deduction list  ->  Westpac Deskbank CSV payment file
REM  Double-click this file to run. No typing needed.
REM ============================================================
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"

python -m trans_processor.cli --input "%~dp0input" --output "%~dp0output"
if errorlevel 1 (
    echo.
    echo *** Something needs fixing. Read the ERROR line above, ***
    echo *** correct the spreadsheet in the 'input' folder,     ***
    echo *** then double-click run.bat again.                   ***
)

echo.
echo Done. This window can be closed.
pause
