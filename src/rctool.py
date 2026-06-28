"""
RandomCallTool - 随机抽取工具
主程序入口 - rctool.py
"""

import os
import tkinter as tk
from tkinter import messagebox
from core.logman import rctlog
from core.info import work_path, rct_version, rct_prog_data_path, rct_result_path, rct_log_path, rct_cache_path, rct_icon_path
from core.utils import set_window_icon
from rctcore.config import ConfigManager
from rctcore.appfunc import MainApplication

class Main:
    def __init__(self):
        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.title("随机抽取工具")
        self.root.geometry("600x480+50+50")
        self.root.minsize(560, 460)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        set_window_icon(self.root, rct_icon_path)
        self.app = MainApplication(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动后延迟执行自动检测更新
        self.root.after(1500, self._auto_check_update)
        self.root.mainloop()

    def _auto_check_update(self):
        """启动时静默检测更新 — 调用 update.py --check-silent"""
        try:
            if not self.config.get("auto_check_update", True):
                return
            source = self.config.get("update_source", "github")
            from rctcore.update import run_auto_update

            def _check():
                has_update = run_auto_update(source=source, mode="--check-silent", timeout=8)
                if has_update:
                    self.root.after(0, self._show_update_prompt, source)

            import threading
            t = threading.Thread(target=_check, daemon=True)
            t.start()
        except Exception as e:
            rctlog.warning(f"自动检测更新失败（静默）: {e}")

    def _show_update_prompt(self, source):
        """检测到新版本时弹窗"""
        try:
            reply = messagebox.askyesno(
                "发现新版本",
                "检测到新版本可用！\n\n"
                "是否立即打开更新程序进行升级？\n\n"
                "「是」打开更新程序  |  「否」稍后手动更新"
            )
            if reply:
                from rctcore.update import run_auto_update
                run_auto_update(source=source, mode="--check")
        except Exception:
            pass

    def on_closing(self):
        """窗口关闭时询问确认"""
        rctlog.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            rctlog.info("程序正常退出")
            self.root.destroy()

def init_dir():
    for path in [rct_prog_data_path, rct_result_path, rct_log_path, rct_cache_path]:
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
        rctlog.info("=" * 50)
    except Exception as e:
        rctlog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    main()