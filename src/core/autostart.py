"""开机自启管理：通过向系统启动文件夹复制 / 删除开始菜单快捷方式实现。

原理（Windows）：
  - 「shell:common startup」对应公共启动文件夹：
      %ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp
  - 启用：把开始菜单中的「随机抽取工具.lnk」复制到该文件夹
  - 关闭：删除启动文件夹中的对应快捷方式

权限：
  - 程序以管理员身份运行时直接复制 / 删除；
  - 普通用户身份运行时，首次操作会弹出一次 UAC，经用户同意后由
    提权的系统命令完成同一个复制 / 删除动作。
"""
import os
import shutil
import platform
import ctypes
from ctypes import wintypes

# 主程序快捷方式文件名（与 SFX 安装器创建的开始菜单快捷方式一致）
SHORTCUT_NAME = "随机抽取工具.lnk"

_PROGRAMS_REL = os.path.join("Microsoft", "Windows", "Start Menu", "Programs")
_STARTUP_REL = os.path.join(_PROGRAMS_REL, "StartUp")

# ShellExecuteEx 标志 / 窗口状态
_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SW_HIDE = 0
_WAIT_TIMEOUT = 0x00000102
_ERROR_CANCELLED = 1223


class _SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def _env(name, fallback):
    return os.environ.get(name) or fallback


def common_startup_dir():
    """「shell:common startup」对应的公共启动文件夹路径。"""
    programdata = _env("ProgramData", r"C:\ProgramData")
    return os.path.join(programdata, _STARTUP_REL)


def startup_shortcut_path():
    """公共启动文件夹中的自启快捷方式完整路径。"""
    return os.path.join(common_startup_dir(), SHORTCUT_NAME)


def find_start_menu_shortcut():
    """在开始菜单中查找主程序快捷方式，返回路径；找不到返回 None。

    依次检查公共 / 当前用户开始菜单，并兼容快捷方式位于
    「随机抽取工具」子文件夹或 Programs 根目录两种布局。
    """
    programdata = _env("ProgramData", r"C:\ProgramData")
    appdata = _env("APPDATA",
                   os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
    bases = [
        os.path.join(programdata, _PROGRAMS_REL),
        os.path.join(appdata, _PROGRAMS_REL),
    ]
    candidates = []
    for base in bases:
        candidates.append(os.path.join(base, "随机抽取工具", SHORTCUT_NAME))
        candidates.append(os.path.join(base, SHORTCUT_NAME))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _run_elevated(cmd_parameters, timeout_ms=120000):
    """以管理员身份运行隐藏的 cmd.exe 并等待结束。

    Returns:
        (True, exit_code)  提权命令执行完毕
        (False, error_code) 启动提权进程失败（1223 = 用户在 UAC 中点了取消）
    """
    sei = _SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = _SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas"
    sei.lpFile = "cmd.exe"
    sei.lpParameters = cmd_parameters
    sei.nShow = _SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        return False, ctypes.windll.kernel32.GetLastError()
    try:
        wait_rc = ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess,
                                                             timeout_ms)
        if wait_rc == _WAIT_TIMEOUT:
            ctypes.windll.kernel32.TerminateProcess(sei.hProcess, 1)
            return False, _WAIT_TIMEOUT
        exit_code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(sei.hProcess,
                                                  ctypes.byref(exit_code))
        return True, exit_code.value
    finally:
        ctypes.windll.kernel32.CloseHandle(sei.hProcess)


def _elevated_copy(source, target):
    """经 UAC 提权复制快捷方式，返回 (ok, message)。"""
    params = f'/c chcp 65001 >nul && copy /y "{source}" "{target}"'
    started, info = _run_elevated(params)
    if not started:
        if info == _ERROR_CANCELLED:
            return False, "已取消管理员授权，开机自启未启用。"
        return False, f"提权操作启动失败（错误码 {info}）。"
    if info != 0 or not os.path.isfile(target):
        return False, "管理员复制快捷方式失败，请检查权限或杀毒软件拦截。"
    return True, ""


def _elevated_remove(target):
    """经 UAC 提权删除快捷方式，返回 (ok, message)。"""
    params = f'/c chcp 65001 >nul && del /f /q "{target}"'
    started, info = _run_elevated(params)
    if not started:
        if info == _ERROR_CANCELLED:
            return False, "已取消管理员授权，开机自启未关闭。"
        return False, f"提权操作启动失败（错误码 {info}）。"
    if info != 0 or os.path.isfile(target):
        return False, "管理员删除快捷方式失败，请检查权限或杀毒软件拦截。"
    return True, ""


def is_enabled():
    """启动文件夹中是否已存在自启快捷方式（以文件实际状态为准）。"""
    return os.path.isfile(startup_shortcut_path())


def enable():
    """将开始菜单快捷方式复制到公共启动文件夹。

    Returns: (True, "") 成功；(False, 错误说明) 失败
    """
    if platform.system() != "Windows":
        return False, "开机自启仅支持 Windows 系统。"

    target = startup_shortcut_path()
    if os.path.isfile(target):
        return True, ""

    source = find_start_menu_shortcut()
    if source is None:
        return False, (
            "未在开始菜单中找到「随机抽取工具」快捷方式。\n\n"
            "请使用安装版程序，或先运行安装程序创建开始菜单快捷方式。"
        )
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source, target)
        return True, ""
    except PermissionError:
        # 普通用户无写权限：经 UAC 提权完成同一次复制
        return _elevated_copy(source, target)
    except OSError as e:
        return False, f"复制快捷方式失败：{e}"


def disable():
    """删除公共启动文件夹中的自启快捷方式。

    Returns: (True, "") 成功；(False, 错误说明) 失败
    """
    if platform.system() != "Windows":
        return False, "开机自启仅支持 Windows 系统。"

    target = startup_shortcut_path()
    if not os.path.isfile(target):
        return True, ""
    try:
        os.remove(target)
        return True, ""
    except PermissionError:
        # 普通用户无删权限：经 UAC 提权完成同一次删除
        return _elevated_remove(target)
    except OSError as e:
        return False, f"删除快捷方式失败：{e}"


def apply(enabled):
    """按目标状态启用 / 关闭开机自启。

    Returns: (True, "") 成功；(False, 错误说明) 失败
    """
    return enable() if enabled else disable()
