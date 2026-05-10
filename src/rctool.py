"""
随机抽取工具 - 入口
"""
import os
import sys
import logging
from tkinter import messagebox
import tkinter as tk

from core.common import setup_logging
from core.constants import LOG_PATH, PROG_DATA_PATH, RESULT_PATH
from core.app import MainApplication

# 创建必要的目录
for path in [PROG_DATA_PATH, RESULT_PATH, LOG_PATH]:
    os.makedirs(path, exist_ok=True)

def check_os():
    if os.name != 'nt':
        logging.error("不支持的操作系统：%s", os.name)
        messagebox.showerror("错误", "本程序仅支持Windows系统")
        sys.exit(1)

def main():
    try:
        logger = setup_logging(LOG_PATH)
        logger.info("=" * 50)
        logger.info("随机抽取工具 v2.1 启动")
        logger.info("=" * 50)

        check_os()

        root = tk.Tk()
        root.title("随机抽取工具")
        root.geometry("400x550+50+50")
        root.minsize(350, 500)
        root.maxsize(1280, 1280)
        root.resizable(True, True)

        app = MainApplication(root)

        def on_closing():
            logger.info("用户关闭窗口，准备退出程序")
            if messagebox.askyesno("确认", "确定要退出程序吗？"):
                logger.info("程序正常退出")
                root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

        logger.info("程序正常退出")
        logger.info("=" * 50)

    except Exception as e:
        logging.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    main()