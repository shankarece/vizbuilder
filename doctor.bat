@echo off
REM ============================================================
REM  vizbuilder environment check - double-click or run in CMD
REM ============================================================
REM
REM  Usage:
REM    doctor.bat                        Check this computer
REM    doctor.bat "C:\work\Sales.pbix"   Also check a report file
REM
REM ============================================================

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo Python was not found on this computer.
        echo Install Python 3.8 or newer, then run this again.
        pause
        exit /b 1
    )
    py "%~dp0doctor.py" %*
) else (
    python "%~dp0doctor.py" %*
)
if "%~1"=="" pause
