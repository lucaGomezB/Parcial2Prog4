@echo off
echo ============================================
echo  Ejecutando todos los tests del backend...
echo ============================================
echo.

cd /d "%~dp0.."

python -m pytest tests/ -v --tb=short

echo.
echo ============================================
echo  Resultado: %errorlevel%
echo ============================================
pause
