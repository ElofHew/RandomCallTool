"""
跨平台工具函数
"""
import os
import platform
import subprocess


def open_file_or_dir(path):
    """跨平台打开文件或目录（自动检测系统选择合适方法）

    - Windows : os.startfile
    - macOS   : open
    - Linux   : xdg-open
    """
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path], check=True)
        else:  # Linux
            subprocess.run(["xdg-open", path], check=True)
    except Exception as e:
        raise RuntimeError(f"无法打开 [{path}]: {e}") from e


def set_window_icon(window, icon_path):
    """为 tkinter 窗口设置任务栏图标
    用于解决 PyInstaller 打包后 tkinter 默认羽毛笔图标问题。
    支持 Tk 根窗口和 Toplevel 子窗口。
    """
    try:
        if icon_path and os.path.isfile(icon_path):
            window.iconbitmap(icon_path)
    except Exception:
        pass  # 图标设置失败不应影响程序运行
