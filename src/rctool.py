"""
@Name: 随机抽取工具
@Author: Dan_Evan
@Date: 2026-01-10
@Version: 2.1
@Description: 一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。
"""

# 导入系统库
import sys
# 导入Tkinter GUI库
import tkinter as tk
from tkinter import messagebox
# 导入文件管理器
from rctool_core.fileman import init_dir
# 导入更多功能类
from rctool_core.more import check_os
# 导入元数据
from rctool_core.meta import work_path, prog_data_path, log_path, result_path
# 导入日志库
from rctool_core.logman import logger
# 导入配置管理器
from rctool_core.config import ConfigManager
# 导入主应用类
from rctool_core.appfunc import MainApplication

class Main:
    def __init__(self):
        self.config = ConfigManager()
        
        self.root = tk.Tk()
        self.root.title("随机抽取工具")
        self.root.geometry("400x550+50+50")
        self.root.minsize(350, 500)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        
        self.app = MainApplication(self.root)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        logger.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("程序正常退出")
            self.root.destroy()

def main():
    """主函数"""
    init_dir()

    try:
        logger.info("=" * 50)
        logger.info("随机抽取工具 v2.1 启动")
        logger.info(f"工作目录: {work_path}")
        logger.info(f"数据目录: {prog_data_path}")
        logger.info(f"日志目录: {log_path}")
        logger.info(f"结果目录: {result_path}")
        logger.info("=" * 50)
        
        Main()
        
        logger.info("程序正常退出")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    if not check_os():
        sys.exit(1)
    else:
        main()