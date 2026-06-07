; WARNING ע�⣬������ʹ��NSIS���䱾�ű������װ���򣬿��ܴ����޷���ж�ص�BUG
; WARNING ע�⣬������ʹ��NSIS���䱾�ű������װ���򣬿��ܴ����޷���ж�ص�BUG
; WARNING ע�⣬������ʹ��NSIS���䱾�ű������װ���򣬿��ܴ����޷���ж�ص�BUG

; �����ȡ���� ��װ����
; ʹ�� NSIS 2.46 ����߰汾����

; ���尲װ��������
Name "�����ȡ����"
OutFile "RandomCallTool_Setup_2.2.exe"
InstallDir "C:\Apps\RandomCallTool"
InstallDirRegKey HKLM "Software\RandomCallTool" "Install_Dir"
RequestExecutionLevel admin

; ��������
BrandingText "�����ȡ����"
ShowInstDetails show
ShowUninstDetails show

; �����ִ� UI
!include "MUI2.nsh"
!include "LogicLib.nsh"

; ���峣��
!define PRODUCT_NAME "�����ȡ����"
!define PRODUCT_VERSION "2.2"
!define PRODUCT_PUBLISHER "Dan_Evan"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\RandomCallTool"

; ��װҳ��
!define MUI_ABORTWARNING
!define MUI_HEADERIMAGE

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ��������
!insertmacro MUI_LANGUAGE "SimpChinese"

; ��װ����
Section "������" SecMain
    SetOutPath $INSTDIR
    
    ; �����������ļ�
    File "rctool.exe"

    ; �����������빤��
    File "encode.exe"
    
    ; ���� _internal �ļ��м����������ݣ�����Ŀ¼�ṹ��
    File /r "_internal"
    
    ; ������ʼ�˵���ݷ�ʽ
    CreateDirectory "$SMPROGRAMS\�����ȡ�����׼�"
    CreateShortCut "$SMPROGRAMS\�����ȡ�����׼�\�����ȡ����.lnk" "$INSTDIR\rctool.exe"
    CreateShortCut "$SMPROGRAMS\�����ȡ�����׼�\�������빤��.lnk" "$INSTDIR\encode.exe"
    CreateShortCut "$SMPROGRAMS\�����ȡ�����׼�\ж��.lnk" "$INSTDIR\uninstall.exe"
    
    ; д��ע���
    WriteRegStr HKLM "Software\RandomCallTool" "Install_Dir" "$INSTDIR"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\rctool.exe"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${UNINSTALL_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD HKLM "${UNINSTALL_KEY}" "NoRepair" 1
    
    ; ����ж�س���
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; ж�ز���
Section "Uninstall"
    ; ɾ���������ļ�
    Delete "$INSTDIR\rctool.exe"
    Delete "$INSTDIR\encode.exe"
    Delete "$INSTDIR\uninstall.exe"
    
    ; �ݹ�ɾ�� _internal �ļ��м�����������
    RMDir /r "$INSTDIR\_internal"

    ; �ݹ�ɾ�� data �ļ��м�����������
    RMDir /r "$INSTDIR\data"
    
    ; ɾ��Ŀ¼
    RMDir "$INSTDIR"
    
    ; ɾ����ݷ�ʽ
    Delete "$SMPROGRAMS\�����ȡ�����׼�\�����ȡ����.lnk"
    Delete "$SMPROGRAMS\�����ȡ�����׼�\�������빤��.lnk"
    Delete "$SMPROGRAMS\�����ȡ�����׼�\ж��.lnk"
    RMDir "$SMPROGRAMS\�����ȡ�����׼�"
    
    ; ɾ��ע���
    DeleteRegKey HKLM "Software\RandomCallTool"
    DeleteRegKey HKLM "${UNINSTALL_KEY}"
SectionEnd