@echo off
REM ============================================================
REM  PBIX Layout Linter - CMD launcher (no PowerShell needed)
REM ============================================================
REM
REM  Usage:
REM    lint.bat file.pbix                     Audit and print issues
REM    lint.bat file.pbix --fix               Auto-fix and save -fixed.pbix
REM    lint.bat file.pbix --report out.md     Save audit report as markdown
REM    lint.bat file.pbix --fix --open        Fix and auto-open in Desktop
REM
REM ============================================================

if "%~1"=="" (
    echo Usage: lint.bat ^<file.pbix^> [--fix] [--report out.md] [--open]
    exit /b 1
)

python "%~dp0lint.py" %*
