"""
(更多)功能模块
"""
# 导入应用库
from rctool_core.logman import logger
from rctool_core.meta import description, version, author, date, github, gitee
# 导入Tkinter消息框方法
from tkinter import messagebox
# 导入平台检测库
import platform
# 导入格式化时间戳函数
from time import strftime
# 导入SubProcess库
import subprocess

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        logger.info("程序正常退出")
        self.root.quit()

    def about(self):
        """关于"""
        about_text = f"""随机抽取工具
{description}
版本：{version}
作者：{author}
日期：{date}
Github：{github}
Gitee：{gitee}"""

        messagebox.showinfo("关于", about_text)
        logger.info("打开关于窗口")

def check_os():
    pfs = platform.system()
    pfr = platform.release()
    pfv = platform.version()
    pfn = platform.node()
    pfall = f"{pfs} {pfr} ({pfv}) - {pfn}"
    if pfs == "Darwin":
        logger.error(f"操作系统检测不通过：{pfall}")
        return False
    else:
        logger.info(f"操作系统检测通过：{pfall}")
        return True

def run_process(*command):
    if command == []:
        logger.error("运行程序失败：命令为空")
        return False
    try:
        proc = subprocess.Popen(command)
        if not proc.returncode:
            logger.warning("程序已运行，但未返回任何值")
            return None
        logger.info("程序运行成功，返回码为: {proc.returncode}")
        return proc.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"运行程序失败: {e}")
        return False
    except Exception as e:
        logger.error(f"运行程序时发生错误: {e}")
        return False
