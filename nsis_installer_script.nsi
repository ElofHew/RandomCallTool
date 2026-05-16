; WARNING 注意，不建议使用NSIS搭配本脚本打包安装程序，可能存在无法被卸载的BUG
; WARNING 注意，不建议使用NSIS搭配本脚本打包安装程序，可能存在无法被卸载的BUG
; WARNING 注意，不建议使用NSIS搭配本脚本打包安装程序，可能存在无法被卸载的BUG

; 随机抽取工具 安装程序
; 使用 NSIS 2.46 或更高版本编译

; 定义安装程序属性
Name "随机抽取工具"
OutFile "RandomCallTool_Setup_2.1.exe"
InstallDir "C:\Apps\RandomCallTool"
InstallDirRegKey HKLM "Software\RandomCallTool" "Install_Dir"
RequestExecutionLevel admin

; 界面设置
BrandingText "随机抽取工具"
ShowInstDetails show
ShowUninstDetails show

; 包含现代 UI
!include "MUI2.nsh"
!include "LogicLib.nsh"

; 定义常量
!define PRODUCT_NAME "随机抽取工具"
!define PRODUCT_VERSION "2.1"
!define PRODUCT_PUBLISHER "Dan_Evan"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\RandomCallTool"

; 安装页面
!define MUI_ABORTWARNING
!define MUI_HEADERIMAGE

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 简体中文
!insertmacro MUI_LANGUAGE "SimpChinese"

; 安装部分
Section "主程序" SecMain
    SetOutPath $INSTDIR
    
    ; 复制主程序文件
    File "rctool.exe"

    ; 复制名单编码工具
    File "encode.exe"
    
    ; 复制 _internal 文件夹及其所有内容（保持目录结构）
    File /r "_internal"
    
    ; 创建开始菜单快捷方式
    CreateDirectory "$SMPROGRAMS\随机抽取工具套件"
    CreateShortCut "$SMPROGRAMS\随机抽取工具套件\随机抽取工具.lnk" "$INSTDIR\rctool.exe"
    CreateShortCut "$SMPROGRAMS\随机抽取工具套件\名单编码工具.lnk" "$INSTDIR\encode.exe"
    CreateShortCut "$SMPROGRAMS\随机抽取工具套件\卸载.lnk" "$INSTDIR\uninstall.exe"
    
    ; 写入注册表
    WriteRegStr HKLM "Software\RandomCallTool" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\rctool.exe"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair" 1
    
    ; 创建卸载程序
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; 卸载部分
Section "Uninstall"
    ; 删除主程序文件
    Delete "$INSTDIR\rctool.exe"
    Delete "$INSTDIR\encode.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; 递归删除 _internal 文件夹及其所有内容
    RMDir /r "$INSTDIR\_internal"

    ; 递归删除 data 文件夹及其所有内容
    RMDir /r "$INSTDIR\data"
    
    ; 删除目录
    RMDir "$INSTDIR"
    
    ; 删除快捷方式
    Delete "$SMPROGRAMS\随机抽取工具套件\随机抽取工具.lnk"
    Delete "$SMPROGRAMS\随机抽取工具套件\名单编码工具.lnk"
    Delete "$SMPROGRAMS\随机抽取工具套件\卸载.lnk"
    RMDir "$SMPROGRAMS\随机抽取工具套件"
    
    ; 删除注册表
    DeleteRegKey HKLM "Software\RandomCallTool"
    DeleteRegKey HKLM "${UNINSTALL_KEY}"
SectionEnd