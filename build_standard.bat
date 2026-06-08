@echo off
chcp 65001 >nul

echo Starting compilation of rctool...
pyinstaller --icon=./icon/rctool.ico -w .\src\rctool.py

echo Starting compilation of encode...
pyinstaller --icon=./icon/encode.ico -w .\src\encode.py

echo Starting compilation of remove...
pyinstaller --icon=./icon/remove.ico -w .\src\remove.py

echo Compilation completed, organizing files...

:: 移动 dist/rctool/ 下的所有内容到 dist/
if exist "dist\rctool" (
    echo Moving files from dist/rctool/ to dist/...
    xcopy "dist\rctool\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\rctool"
)

:: 移动 dist/encode/ 下的所有内容到 dist/
if exist "dist\encode" (
    echo Moving files from dist/encode/ to dist/...
    xcopy "dist\encode\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\encode"
)

:: 移动 dist/remove/ 下的所有内容到 dist/
if exist "dist\remove" (
    echo Moving files from dist/remove/ to dist/...
    xcopy "dist\remove\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\remove"
)

:: 删除 spec 文件
echo Deleting spec files...
if exist "rctool.spec" del /Q "rctool.spec"
if exist "encode.spec" del /Q "encode.spec"
if exist "remove.spec" del /Q "remove.spec"

:: 删除 build 文件夹
echo Deleting build folder...
if exist "build" rmdir /S /Q "build"

echo Cleanup completed!
pause