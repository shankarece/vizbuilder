@echo off
REM Formatting audit / bulk restyle (no PowerShell needed)
REM   format.bat file.pbix --theme bank_theme.json            audit
REM   format.bat file.pbix --theme bank_theme.json --restyle  write file-restyled.pbix
python "%~dp0format_tools.py" %*
