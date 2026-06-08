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
