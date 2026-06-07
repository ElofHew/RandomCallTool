"""
(更多)功能模块
"""
# 导入应用库
from core.logman import rctlog
# 导入Tkinter消息框方法
from tkinter import messagebox
# 导入平台检测库
import platform
# 导入SubProcess库
import subprocess

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

def check_os():
    pfs = platform.system()
    pfr = platform.release()
    pfv = platform.version()
    pfn = platform.node()
    pfall = f"{pfs} {pfr} ({pfv}) - {pfn}"
    if pfs == "Darwin":
        rctlog.error(f"操作系统检测不通过：{pfall}")
        return False
    else:
        rctlog.info(f"操作系统检测通过：{pfall}")
        return True

def run_process(*command):
    if command == []:
        rctlog.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.Popen(command)
        if not proc.returncode:
            rctlog.warning("程序已运行，但未返回任何值")
            return None
        rctlog.info("程序运行成功，返回码为: {proc.returncode}")
        return proc.returncode
    except subprocess.CalledProcessError as e:
        rctlog.error(f"运行程序失败: {e}")
        return False
    except Exception as e:
        rctlog.error(f"运行程序时发生错误: {e}")
        return False
