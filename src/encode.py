"""
随机抽人名单编码工具 - 入口
"""
import os
import sys
import logging
from tkinter import messagebox
import tkinter as tk

from core.common import setup_logging
from core.constants import ENCODE_LOG_PATH, ENCODE_DATA_PATH, ENCODE_OUTPUT_PATH
from core.encode_gui import MainApplication

for path in [ENCODE_DATA_PATH, ENCODE_OUTPUT_PATH, ENCODE_LOG_PATH]:
    os.makedirs(path, exist_ok=True)

def check_os():
    if os.name != 'nt':
        logging.error("不支持的操作系统：%s", os.name)
        messagebox.showerror("错误", "本程序仅支持Windows系统")
        sys.exit(1)

def main():
    try:
        logger = setup_logging(ENCODE_LOG_PATH)
        logger.info("=" * 50)
        logger.info("随机抽人名单编码工具 V1.0 启动")
        logger.info("=" * 50)

        check_os()

        root = tk.Tk()
        root.title("随机抽人名单编码工具")
        root.geometry("600x600+50+50")
        root.minsize(500, 500)

        app = MainApplication(root)

        def on_closing():
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