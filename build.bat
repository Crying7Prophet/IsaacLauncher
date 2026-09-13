@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set PATH=C:\msys64\ucrt64\bin;%PATH%

if not exist build mkdir build
cmake -S . -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=C:/msys64/ucrt64 -DCMAKE_MAKE_PROGRAM=C:/msys64/ucrt64/bin/mingw32-make.exe
cmake --build build -j 8

echo.
echo Compilado: build\IsaacLauncherCpp.exe
pause