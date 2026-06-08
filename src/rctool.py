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
        self.root.geometry("580x480+50+50")
        self.root.minsize(560, 460)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        self.app = MainApplication(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动后延迟执行自动检测更新
        self.root.after(1500, self._auto_check_update)
        self.root.mainloop()

    def _auto_check_update(self):
        """启动时自动检测更新（静默模式）"""
        try:
            if not self.config.get("auto_check_update", True):
                return
            source = self.config.get("update_source", "github")
            from rctcore.update import check_update
            result = check_update(source=source, timeout=5)
            if result.get("success") and result.get("has_update"):
                rctlog.info(f"发现新版本: v{result['remote_version']} (当前 v{result['local_version']})")
                self._show_update_prompt(result, source)
        except Exception as e:
            rctlog.warning(f"自动检测更新失败（静默）: {e}")

    def _show_update_prompt(self, result, source):
        """显示更新提示弹窗"""
        try:
            reply = messagebox.askyesno(
                "发现新版本",
                f"检测到新版本可用！\n\n"
                f"当前版本: v{result['local_version']}\n"
                f"最新版本: v{result['remote_version']} ({result['remote_date']})\n\n"
                f"是否前往下载页面？"
            )
            if reply:
                from rctcore.update import open_download_page
                open_download_page(source)
        except Exception:
            pass

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