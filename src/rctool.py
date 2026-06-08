"""
@Name: 随机抽取工具
@Author: Dan_Evan
@Date: 2026-06-07
@Version: 2.2
@Description: 一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。
"""

import os
import tkinter as tk
from tkinter import messagebox
from core.logman import rctlog
from core.info import work_path, rct_version, rct_prog_data_path, rct_result_path, rct_log_path
from rctcore.config import ConfigManager
from rctcore.appfunc import MainApplication

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
        """窗口关闭时询问确认"""
        rctlog.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            rctlog.info("程序正常退出")
            self.root.destroy()

def init_dir():
    for path in [rct_prog_data_path, rct_result_path, rct_log_path]:
        os.makedirs(path, exist_ok=True)

def main():
    """主入口"""
    init_dir()
    try:
        rctlog.info("=" * 50)
        rctlog.info(f"随机抽取工具 {rct_version} 启动")
        rctlog.info(f"工作目录: {work_path}")
        rctlog.info("=" * 50)
        Main()
        rctlog.info("程序正常退出")
        rctlog.info("=" * 50)
    except Exception as e:
        rctlog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    main()