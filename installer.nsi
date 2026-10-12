; ============================================================================
;  RandomCallTool（随机抽取工具） NSIS 安装脚本
; ----------------------------------------------------------------------------
;  说明：
;    本脚本把 build.bat 生成的 dist\ 目录打包成「货真价实」的 Windows
;    安装程序（向导界面 + 可选安装目录 / 开始菜单组 / 桌面快捷方式 +
;    「应用和功能」卸载注册），取代原先的 7z 纯 SFX 自解压包。
;
;  卸载方案（过渡形态）：
;    1. NSIS 生成的 uninst.exe 是一个【完整、常规的卸载器】：结束进程 →
;       删除程序文件 / 快捷方式 / 注册表卸载项 / 自身；
;    2. 项目原有 remove.exe（保留数据 / 重置 / 完全卸载 三模式）暂时原样
;       保留，开始菜单中的「卸载工具」仍指向它；
;    3. 后续再把 remove.exe 的细分模式合并进 NSIS 卸载器。
;
;  编译方法（项目根目录下）：
;    1. 先运行 build.bat，确保 dist\ 目录为最新产物；
;    2. 执行：  makensis RandomCallTool.nsi
;    3. 产物：  RandomCallTool_Setup_V<版本>.exe
;       （命名与更新程序 network.get_download_url 的约定一致，
;         可直接作为 GitHub / Gitee Release 上传）
;
;    支持静默安装 / 静默卸载： 在 exe 后加 /S
; ============================================================================

; ----------------------------- 版本 / 常量 ----------------------------------
; 升级版本时，主要改这里（版本号同时写进安装包资源、注册表、输出文件名）
!define VER            "2.7.1.1"
!define PRODUCT_NAME   "随机抽取工具"
!define PUBLISHER      "Dan_Evan"
!define SETUP_BASENAME "RandomCallTool_Setup"
!define WEB_SITE       "https://rct.danevan.top"
; 「应用和功能」里显示的程序体积（KB），约等于 dist 总大小，版本变化时顺手更新
!define EST_SIZE_KB    28800
; 注册表卸载项路径
!define UNINST_KEY     "Software\Microsoft\Windows\CurrentVersion\Uninstall\RandomCallTool"
; 开始菜单程序组文件夹名（与原 SFX、remove.exe 的清理目标一致）
!define SM_FOLDER      "随机抽取工具"

; ------------------------------- 全局设置 -----------------------------------
Unicode True
SetCompressor /SOLID lzma
SetOverwrite on
RequestExecutionLevel admin         ; 默认装到 C:\Apps 并写 HKLM，需要管理员

Name "${PRODUCT_NAME}"
; 默认安装目录与原 SFX 保持一致（程序把数据写在自身目录的 data\ 下，
; 不适合装进 Program Files）
InstallDir "C:\Apps\RandomCallTool"
; 覆盖安装 / 升级时读取上一次安装目录的逻辑写在 .onInit 里（需 64 位视图）
OutFile "${SETUP_BASENAME}_V${VER}.exe"
BrandingText "${PUBLISHER} · ${WEB_SITE}"

; --------------------------- 安装包版本资源信息 ------------------------------
VIProductVersion "${VER}"
VIAddVersionKey "ProductName"      "${PRODUCT_NAME}"
VIAddVersionKey "FileDescription"  "一个基于Python3和Tkinter的随机抽取工具"
VIAddVersionKey "CompanyName"      "${PUBLISHER}"
VIAddVersionKey "LegalCopyright"   "MIT License"
VIAddVersionKey "FileVersion"      "${VER}"
VIAddVersionKey "ProductVersion"   "${VER}"
VIAddVersionKey "OriginalFilename" "${SETUP_BASENAME}_V${VER}.exe"

; -------------------------------- MUI2 --------------------------------------
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "StrFunc.nsh"
${Using:StrFunc} StrLoc

; -------------------------------- 变量 --------------------------------------
Var StartMenuFolder     ; 开始菜单程序组文件夹名
Var DesktopChecked      ; 是否创建桌面快捷方式（BST_CHECKED=1）
Var IsQuiet             ; 本次启动是否为 /S 静默
Var ChkDesktopCtl       ; 附加任务页复选框控件句柄

!define MUI_ICON        "src\res\icon\rctool.ico"
!define MUI_UNICON      "src\res\icon\remove.ico"
!define MUI_ABORTWARNING
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "${SM_FOLDER}"
!define MUI_FINISHPAGE_RUN       "$INSTDIR\rctool.exe"
!define MUI_FINISHPAGE_RUN_TEXT  "立即运行随机抽取工具(&R)"

; 安装向导页面
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE  "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU Application $StartMenuFolder
Page Custom TasksPageCreate TasksPageLeave        ; 附加任务（桌面快捷方式）
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 卸载向导页面（完整 NSIS 卸载器）
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

; ============================================================================
;  辅助函数：进程检测
;  用法： Push "进程名.exe" → Call IsProcessRunning → Pop 结果（1=运行中 0=未运行）
; ============================================================================
Function IsProcessRunning
  Exch $R0                   ; $R0 = 传入的进程名
  Push $R1
  Push $R2
  Push $R3

  ; CSV 格式输出便于解析；无匹配时输出的是“没有运行的任务...”提示，不含进程名
  nsExec::ExecToStack 'cmd /c tasklist /NH /FO CSV /FI "IMAGENAME eq $R0"'
  Pop $R1                    ; 退出码
  Pop $R2                    ; 输出文本
  ${StrLoc} $R3 "$R2" "$R0" "<"
  StrCpy $R0 "0"
  ${If} $R3 != ""
    StrCpy $R0 "1"
  ${EndIf}

  Pop $R3
  Pop $R2
  Pop $R1
  Exch $R0                   ; 结果放回栈顶，$R0 恢复原值
FunctionEnd

; ============================================================================
;  安装程序初始化
; ============================================================================
Function .onInit
  ; 注册表统一走 64 位视图（SetRegView 只能在函数/段内使用，之后一直有效）
  SetRegView 64

  ; 升级 / 覆盖安装：读取上一次的安装目录
  ReadRegStr $R0 HKLM "${UNINST_KEY}" "InstallLocation"
  ${If} $R0 != ""
    StrCpy $INSTDIR "$R0"
  ${EndIf}

  ; 记录是否静默
  StrCpy $IsQuiet "0"
  ${If} ${Silent}
    StrCpy $IsQuiet "1"
  ${EndIf}

  ; 机器级安装：快捷方式写到公共开始菜单 / 公共桌面（remove.exe 两种位置都会清）
  SetShellVarContext all

  ; 默认值（静默安装时页面不显示，直接用默认值）
  StrCpy $StartMenuFolder "${SM_FOLDER}"
  StrCpy $DesktopChecked "1"

  ; 安装目录合法性：不允许装到驱动器根目录（如 C:\）
  StrLen $R0 $INSTDIR
  ${If} $R0 <= 3
    MessageBox MB_OK|MB_ICONSTOP "安装目录无效：不能直接安装到驱动器根目录。$\r$\n请重新运行安装程序并选择一个合法的文件夹。"
    Abort
  ${EndIf}

  ; 卸载工具正在运行时拒绝安装（它正在删文件，不能打断）
  Push "remove.exe"
  Call IsProcessRunning
  Pop $R0
  ${If} $R0 == "1"
    MessageBox MB_OK|MB_ICONSTOP "检测到卸载工具 remove.exe 正在运行。$\r$\n请等待它执行完毕后再运行安装程序。"
    Abort
  ${EndIf}

  ; 检测主程序 / 更新程序是否在运行
  Push "rctool.exe"
  Call IsProcessRunning
  Pop $R1
  Push "update.exe"
  Call IsProcessRunning
  Pop $R2

  ${If} $R1 == "1"
  ${OrIf} $R2 == "1"
    ${If} $IsQuiet == "1"
      ; 静默安装：直接结束占用进程
      nsExec::Exec 'taskkill /F /T /IM rctool.exe'
      nsExec::Exec 'taskkill /F /T /IM update.exe'
      Sleep 800
    ${Else}
      MessageBox MB_YESNO|MB_ICONQUESTION \
        "检测到「随机抽取工具」套件正在运行。$\r$\n$\r$\n安装前必须关闭主程序 rctool.exe 和更新程序 update.exe，否则会因文件占用导致安装失败、文件损坏。$\r$\n$\r$\n是否由安装程序自动关闭它们？$\r$\n（点击“是”前请先保存好当前数据）" \
        IDNO KillDeny
        nsExec::Exec 'taskkill /F /T /IM rctool.exe'
        nsExec::Exec 'taskkill /F /T /IM update.exe'
        Sleep 800
        Goto KillDone
      KillDeny:
        Abort
      KillDone:
    ${EndIf}
  ${EndIf}
FunctionEnd

; ============================================================================
;  附加任务页：桌面快捷方式复选框
; ============================================================================
Function TasksPageCreate
  !insertmacro MUI_HEADER_TEXT "选择附加任务" "选择安装程序要执行的附加任务。"
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  ${NSD_CreateCheckbox} 12u 12u 90% 12u "在桌面上创建「随机抽取工具」快捷方式"
  Pop $ChkDesktopCtl
  ${If} $DesktopChecked == "1"
    ${NSD_Check} $ChkDesktopCtl
  ${EndIf}

  nsDialogs::Show
FunctionEnd

Function TasksPageLeave
  ${NSD_GetState} $ChkDesktopCtl $0
  StrCpy $DesktopChecked $0
FunctionEnd

; ============================================================================
;  安装主段
; ============================================================================
Section "${PRODUCT_NAME}" SecMain
  SetRegView 64
  SetOutPath "$INSTDIR"

  ; ---- 三个可执行文件（主程序 / 更新程序 / 卸载工具） ----
  File "dist\rctool.exe"
  File "dist\update.exe"
  File "dist\remove.exe"

  ; ---- PyInstaller 依赖目录与资源目录 ----
  File /r "dist\_internal"
  File /r "dist\res"

  ; ---- 数据目录（全新安装时先建好；升级安装时原有数据不受影响） ----
  CreateDirectory "$INSTDIR\data"

  ; ---- 生成完整 NSIS 卸载器 ----
  WriteUninstaller "$INSTDIR\uninst.exe"

  ; ---- 开始菜单程序组及快捷方式（与原 SFX 内容一致） ----
  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    CreateDirectory "$SMPROGRAMS\$StartMenuFolder"
    SetOutPath "$INSTDIR"   ; CreateShortCut 的工作目录取 $OUTDIR
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\随机抽取工具.lnk" \
      "$INSTDIR\rctool.exe" "" "$INSTDIR\rctool.exe" 0 "" "" \
      "一个基于Python3和Tkinter的随机抽取工具"
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\检测更新.lnk" \
      "$INSTDIR\update.exe" "" "$INSTDIR\update.exe" 0 "" "" \
      "检测随机抽取工具是否有新版本更新"
    ; 「卸载工具」暂时仍指向原 remove.exe（三模式），后续再合并进 uninst.exe
    CreateShortCut "$SMPROGRAMS\$StartMenuFolder\卸载工具.lnk" \
      "$INSTDIR\remove.exe" "" "$INSTDIR\res\icon\remove.ico" 0 "" "" \
      "卸载或重置随机抽取工具"
  !insertmacro MUI_STARTMENU_WRITE_END

  ; ---- 桌面快捷方式（可选） ----
  ${If} $DesktopChecked == "1"
    SetOutPath "$INSTDIR"
    CreateShortCut "$DESKTOP\随机抽取工具.lnk" \
      "$INSTDIR\rctool.exe" "" "$INSTDIR\rctool.exe" 0 "" "" \
      "一个基于Python3和Tkinter的随机抽取工具"
  ${EndIf}

  ; ---- 注册表：注册到「应用和功能 / 添加删除程序」 ----
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"          "${PRODUCT_NAME}"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"       "${VER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"            "${PUBLISHER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"          "$INSTDIR\rctool.exe"
  WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation"      "$INSTDIR"
  WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString"      '"$INSTDIR\uninst.exe"'
  WriteRegStr   HKLM "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\uninst.exe" /S'
  WriteRegStr   HKLM "${UNINST_KEY}" "URLInfoAbout"         "${WEB_SITE}"
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify"             1
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"             1
  WriteRegDWORD HKLM "${UNINST_KEY}" "EstimatedSize"        ${EST_SIZE_KB}
SectionEnd

; ============================================================================
;  完整 NSIS 卸载器（uninst.exe）
;  注意：当前为「完全卸载」实现，会连同 data\ 用户数据一起删除；
;  需要保留数据 / 仅重置配置时，可继续使用 remove.exe。
;  TODO（后续合并）：把 remove.exe 的 keep-data / reset 模式做成卸载选项。
; ============================================================================
Function un.onInit
  SetShellVarContext all
  SetRegView 64
FunctionEnd

Section "Uninstall"
  ; ---- 结束正在运行的套件进程（主程序 / 更新程序） ----
  nsExec::Exec 'taskkill /F /T /IM rctool.exe'
  nsExec::Exec 'taskkill /F /T /IM update.exe'
  Sleep 800

  ; ---- 删除程序文件 ----
  Delete "$INSTDIR\rctool.exe"
  Delete "$INSTDIR\update.exe"
  Delete "$INSTDIR\remove.exe"
  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\res"

  ; ---- 删除用户数据（完全卸载）；合并 keep-data 模式后改为按选项执行 ----
  RMDir /r "$INSTDIR\data"

  ; ---- 删除开始菜单程序组（兼容两种历史命名）与桌面快捷方式 ----
  RMDir /r "$SMPROGRAMS\随机抽取工具"
  RMDir /r "$SMPROGRAMS\随机抽取工具套件"
  Delete  "$DESKTOP\随机抽取工具.lnk"

  ; ---- 删除「应用和功能」注册表项（64 / 32 位视图及 HKCU 兜底） ----
  SetRegView 64
  DeleteRegKey HKLM "${UNINST_KEY}"
  SetRegView 32
  DeleteRegKey HKLM "${UNINST_KEY}"
  DeleteRegKey HKCU "${UNINST_KEY}"

  ; ---- 卸载器自身：NSIS 内置自删并不可靠（官方 bug #1226），显式补删 ----
  ; 运行中的副本位于 %TEMP%（$EXEPATH），安装目录里的原始副本可直接删除
  Delete "$INSTDIR\uninst.exe"
  Delete /REBOOTOK "$EXEPATH"

  ; ---- 删除安装目录（空目录才会成功，data 已在上面删除） ----
  RMDir "$INSTDIR"
SectionEnd
