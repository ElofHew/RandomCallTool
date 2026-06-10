@echo off
chcp 65001 >nul

del /Q "dist"

echo Starting compilation of rctool (single file)...
pyinstaller --icon=./src/res/icon/rctool.ico -F -w .\src\rctool.py

echo Starting compilation of encode (single file)...
pyinstaller --icon=./src/res/icon/encode.ico -F -w .\src\encode.py

echo Starting compilation of remove (single file)...
pyinstaller --icon=./src/res/icon/remove.ico -F -w .\src\remove.py

echo Compilation completed, single file mode requires no folder content moving...

:: 复制 res 资源文件到 dist 目录
echo Copying res files to dist...
xcopy /E /I /Y "src\res" "dist\res"

:: 单文件模式下，.exe 直接生成在 dist/ 目录
:: 但可能还是会生成临时文件夹，如果有则删除
if exist "dist\rctool" rmdir /S /Q "dist\rctool"
if exist "dist\encode" rmdir /S /Q "dist\encode"
if exist "dist\remove" rmdir /S /Q "dist\remove"

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