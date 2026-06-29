@echo off
chcp 65001 >nul

rmdir /S /Q "dist"

echo Starting compilation of rctool...
pyinstaller --icon=./src/res/icon/rctool.ico -w .\src\rctool.py

echo Starting compilation of remove...
pyinstaller --icon=./src/res/icon/remove.ico -w .\src\remove.py

echo Starting compilation of update...
pyinstaller --icon=./src/res/icon/update.ico -w .\src\update.py

echo Compilation completed, organizing files...

:: 移动 dist/rctool/ 下的所有内容到 dist/
if exist "dist\rctool" (
    echo Moving files from dist/rctool/ to dist/...
    xcopy "dist\rctool\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\rctool"
)

:: 移动 dist/remove/ 下的所有内容到 dist/
if exist "dist\remove" (
    echo Moving files from dist/remove/ to dist/...
    xcopy "dist\remove\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\remove"
)

:: 移动 dist/update/ 下的所有内容到 dist/
if exist "dist\update" (
    echo Moving files from dist/update/ to dist/...
    xcopy "dist\update\*" "dist\" /E /H /C /I /Y
    rmdir /S /Q "dist\update"
)

:: 复制 res 资源文件到 dist 目录
echo Copying res files to dist...
xcopy /E /I /Y "src\res" "dist\res"

:: 删除 spec 文件
echo Deleting spec files...
if exist "rctool.spec" del /Q "rctool.spec"
if exist "remove.spec" del /Q "remove.spec"
if exist "update.spec" del /Q "update.spec"

:: 删除 build 文件夹
echo Deleting build folder...
if exist "build" rmdir /S /Q "build"

echo Cleanup completed!
pause