"""跨平台工具函数：打开文件、设置窗口图标、退出辅助与外部进程启动。"""
import os
import platform
import subprocess

from core.logman import rctlog


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


class More:
    """程序退出辅助。"""

    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        rctlog.info("程序正常退出")
        self.root.quit()


def run_process(*command):
    """启动外部进程（非阻塞，允许并行运行）

    直接以参数列表方式启动（shell=False），避免安装路径含空格时被 cmd 截断。
    """
    if not command:
        rctlog.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.Popen(list(command), shell=False)
        rctlog.info(f"程序已启动，PID: {proc.pid}")
        return True
    except FileNotFoundError as e:
        rctlog.error(f"程序不存在：{e}")
        return False
    except Exception as e:
        rctlog.error(f"运行程序时发生错误: {e}")
        return False
