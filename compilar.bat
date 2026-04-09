@echo off
title Compilando DevThinker
color 0B

echo [+] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1 || pip install pyinstaller

echo [+] Limpiando cache antigua...
rmdir /s /q build 2>nul
rmdir /s /q temp_build 2>nul
rmdir /s /q temp_dist 2>nul
del /q DevThinker.spec 2>nul

echo [+] Preparando carpeta dist...
if not exist dist mkdir dist
if exist dist\DevThinker.exe del /q dist\DevThinker.exe

echo [+] Compilando de forma aislada...
pyinstaller --onefile --windowed --name "DevThinker" --distpath "temp_dist" --workpath "temp_build" main.py

echo [+] Moviendo nuevo ejecutable a dist...
move /y temp_dist\DevThinker.exe dist\ >nul

echo [+] Limpiando archivos temporales...
rmdir /s /q temp_dist 2>nul
rmdir /s /q temp_build 2>nul
del /q DevThinker.spec 2>nul

echo [+] Exito! DevThinker.exe actualizado sin borrar otros archivos.
pause