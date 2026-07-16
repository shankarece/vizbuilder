@echo off
REM ============================================================
REM  PBIX Analyzer Suite - CMD launcher (no PowerShell needed)
REM ============================================================
REM
REM  Usage:
REM    analyze.bat file.pbix                    Full analysis
REM    analyze.bat file.pbix --output reports/  Save outputs to directory
REM    analyze.bat file.pbix --metadata-only    Extract metadata only
REM    analyze.bat file.pbix --lineage-only     Analyze lineage only
REM
REM ============================================================

if "%~1"=="" (
    echo Usage: analyze.bat ^<file.pbix^> [--output dir] [--metadata-only] [--lineage-only]
    exit /b 1
)

python "%~dp0analyze.py" %*
