"""通用辅助功能：退出和外部进程启动。"""
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
