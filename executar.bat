@echo off
title Dashboard Graham & Lynch
cd /d "%~dp0"

echo ========================================
echo   Dashboard Graham ^& Lynch
echo ========================================
echo.

:: Instalar dependencias (so na primeira vez, depois eh rapido)
echo [1/2] Verificando dependencias...
pip install -q -r requirements.txt

echo.
echo [2/2] Gerando dashboard...
echo.
python dashboard_completo.py

echo.
echo ========================================
echo   Abrindo no navegador...
echo ========================================
start "" "graham_dashboard.html"

echo.
pause
