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
    if not command:
        rctlog.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.run(command, capture_output=True, text=True, shell=True)
        if proc.returncode != 0:
            rctlog.warning(f"程序已运行，但产生错误，返回码为：{proc.returncode}")
            return proc.returncode
        rctlog.info("程序运行成功")
        return True
    except FileNotFoundError as e:
        rctlog.error(f"程序不存在：{e}")
        return False
    except Exception as e:
        rctlog.error(f"运行程序时发生错误: {e}")
        return False
