"""
功能模块 - 退出、关于及外部进程调用
"""
from tkinter import messagebox
import os
import subprocess
from core.logman import rctlog

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        rctlog.info("程序正常退出")
        self.root.quit()

    def about(self):
        """关于"""
        from core.info import rct_description, rct_version, rct_author, rct_date, github, gitee
        about_text = f"""随机抽取工具
{rct_description}
版本：{rct_version}
作者：{rct_author}
日期：{rct_date}
Github：{github}
Gitee：{gitee}"""

        messagebox.showinfo("关于", about_text)
        rctlog.info("打开关于窗口")

def run_process(*command):
    if command == []:
        rctlog.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.run(command, check=True, capture_output=True, text=True, shell=True)
        proccode = proc.returncode
        if proc.returncode != 0:
            rctlog.warning(f"程序已运行，但产生错误，返回码为：{proccode}")
            return proccode
        rctlog.info("程序运行成功")
        return True
    except FileNotFoundError as e:
        rctlog.error(f"程序不存在：{e}")
        return False
    except subprocess.CalledProcessError as e:
        rctlog.error(f"运行程序失败: {e}")
        return False
    except Exception as e:
        rctlog.error(f"运行程序时发生错误: {e}")
        return False
