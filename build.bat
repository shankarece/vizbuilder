@echo off
REM ============================================================
REM  PBIX Visual Builder - CMD launcher (no PowerShell needed)
REM ============================================================
REM
REM  Usage:
REM    build.bat input.pbix output.pbix
REM    build.bat input.pbix output.pbix --open
REM
REM  Examples:
REM    build.bat MyReport.pbix MyReport-Out.pbix
REM    build.bat MyReport.pbix MyReport-Out.pbix --open
REM
REM ============================================================

if "%~1"=="" (
    echo Usage: build.bat ^<input.pbix^> ^<output.pbix^> [--open]
    echo.
    echo   --open   Automatically open the output in Power BI Desktop
    exit /b 1
)

if "%~2"=="" (
    echo Error: Please provide both input and output PBIX paths.
    echo Usage: build.bat ^<input.pbix^> ^<output.pbix^> [--open]
    exit /b 1
)

python "%~dp0build.py" %*
