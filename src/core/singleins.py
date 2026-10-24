"""
单实例检测：防止软件被重复启动多个实例而相互冲突。

- Windows : 命名互斥锁（Named Mutex），进程退出或崩溃后由系统自动释放，无残留
- 其他平台: 锁文件 + PID 存活检测，可自动接管崩溃进程遗留的陈旧锁
"""
import atexit
import os
import platform
import tkinter as tk
from tkinter import messagebox

from core.logman import rctlog
from core.info import rct_icon_path, app_local_data_path
from core.platutils import set_window_icon

# Windows 命名互斥锁；Local 前缀表示当前用户会话内唯一，可覆盖重复双击启动
_MUTEX_NAME = "Local\\DanEvan_RandomCallTool_SingleInstance"
_lock_file_path = os.path.join(app_local_data_path, "singleinstance.lock")
_mutex_handle = None  # 保持互斥锁句柄引用，防止被垃圾回收


def _acquire_on_windows():
    """创建命名互斥锁。返回 True 表示获取成功（当前为首个实例）。"""
    global _mutex_handle
    import ctypes
    ERROR_ALREADY_EXISTS = 183
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        # 检测手段失效时不应阻止软件正常启动，仅记录日志
        rctlog.warning(
            f"创建单实例互斥锁失败（错误码 {ctypes.get_last_error()}），跳过重复启动检测"
        )
        return True
    _mutex_handle = handle
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return False
    return True


def _is_pid_alive(pid):
    """判断指定 PID 的进程是否仍在运行。"""
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 进程存在，但当前用户无权向其发信号
    except Exception:
        return False
    return True


def _remove_lock_file():
    try:
        if os.path.exists(_lock_file_path):
            os.remove(_lock_file_path)
    except Exception:
        pass


def _acquire_lock_file():
    """通过锁文件 + PID 实现单实例（非 Windows 平台的兜底方案）。"""
    try:
        os.makedirs(os.path.dirname(_lock_file_path), exist_ok=True)
        if os.path.exists(_lock_file_path):
            old_pid = None
            try:
                with open(_lock_file_path, "r", encoding="utf-8") as f:
                    old_pid = int(f.read().strip())
            except (ValueError, OSError):
                pass
            if (
                old_pid is not None
                and old_pid != os.getpid()
                and _is_pid_alive(old_pid)
            ):
                return False
            rctlog.info(f"发现陈旧的单实例锁文件（PID {old_pid} 已退出），已自动接管")
        with open(_lock_file_path, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        atexit.register(_remove_lock_file)
        return True
    except Exception as e:
        rctlog.warning(f"创建单实例锁文件失败: {e}，跳过重复启动检测")
        return True


def _show_already_running_dialog():
    """弹窗提示程序已在运行。"""
    dlg_root = None
    try:
        dlg_root = tk.Tk()
        dlg_root.withdraw()
        set_window_icon(dlg_root, rct_icon_path)
        messagebox.showwarning(
            "程序已在运行",
            "[随机抽取工具] 已经在运行中。\n\n"
            "请勿重复启动多个实例，以免程序相互冲突。\n\n"
            "如果主界面已隐藏，请在系统托盘中查找。",
            parent=dlg_root,
        )
    except Exception as e:
        rctlog.warning(f"弹出重复启动提示失败: {e}")
    finally:
        if dlg_root is not None:
            try:
                dlg_root.destroy()
            except Exception:
                pass


def ensure_single_instance():
    """确保只有一个软件实例在运行。

    返回 True 表示当前为首个实例、可以继续启动；
    返回 False 表示已有实例在运行（已弹窗提示），调用方应直接退出。
    """
    if platform.system() == "Windows":
        acquired = _acquire_on_windows()
    else:
        acquired = _acquire_lock_file()
    if not acquired:
        rctlog.warning("检测到程序已在运行，本次启动终止")
        _show_already_running_dialog()
        return False
    rctlog.info("单实例检测通过")
    return True
