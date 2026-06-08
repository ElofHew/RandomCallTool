@echo off
chcp 65001 >nul
title Build and Clean

echo ========================================
echo 1. Standard build (folder mode)
echo 2. Single file build
echo ========================================
set /p choice="Please select (1 or 2): "

if "%choice%"=="1" (
    call :build_standard
) else if "%choice%"=="2" (
    call :build_onefile
) else (
    echo Invalid choice
    pause
    exit /b
)

goto :eof

del /Q "dist"

:build_standard
echo Starting standard build...
pyinstaller --icon=./icon/rctool.ico -w .\src\rctool.py
pyinstaller --icon=./icon/encode.ico -w .\src\encode.py
pyinstaller --icon=./icon/remove.ico -w .\src\remove.py
call :cleanup_standard
goto :eof

:build_onefile
echo Starting single file build...
pyinstaller --icon=./icon/rctool.ico -F -w .\src\rctool.py
pyinstaller --icon=./icon/encode.ico -F -w .\src\encode.py
pyinstaller --icon=./icon/remove.ico -F -w .\src\remove.py
call :cleanup_onefile
goto :eof

:cleanup_standard
echo Organizing files...
if exist "dist\rctool" (
    xcopy "dist\rctool\*" "dist\" /E /H /C /I /Y >nul
    rmdir /S /Q "dist\rctool"
)
if exist "dist\encode" (
    xcopy "dist\encode\*" "dist\" /E /H /C /I /Y >nul
    rmdir /S /Q "dist\encode"
)
if exist "dist\remove" (
    xcopy "dist\remove\*" "dist\" /E /H /C /I /Y >nul
    rmdir /S /Q "dist\remove"
)
call :delete_temp_files
goto :eof

:cleanup_onefile
if exist "dist\rctool" rmdir /S /Q "dist\rctool"
if exist "dist\encode" rmdir /S /Q "dist\encode"
if exist "dist\remove" rmdir /S /Q "dist\remove"
call :delete_temp_files
goto :eof

:delete_temp_files
echo Deleting temporary files...
if exist "rctool.spec" del /Q "rctool.spec"
if exist "encode.spec" del /Q "encode.spec"
if exist "remove.spec" del /Q "remove.spec"
if exist "build" rmdir /S /Q "build"
echo Cleanup completed!
pause
goto :eof