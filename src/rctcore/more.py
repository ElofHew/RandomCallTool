"""
功能模块 - 退出及外部进程调用
"""
import subprocess
from core.logman import rctlog

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        rctlog.info("程序正常退出")
        self.root.quit()

def run_process(*command):
    """启动外部进程（非阻塞，允许并行运行）"""
    if not command:
        rctlog.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.Popen(command, shell=True)
        rctlog.info(f"程序已启动，PID: {proc.pid}")
        return True
    except FileNotFoundError as e:
        rctlog.error(f"程序不存在：{e}")
        return False
    except Exception as e:
        rctlog.error(f"运行程序时发生错误: {e}")
        return False
