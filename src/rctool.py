"""
RandomCallTool - 随机抽取工具
主程序入口 - rctool.py
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
from core.logman import rctlog
from core.info import work_path, rct_version, rct_prog_data_path, rct_result_path, rct_log_path, rct_cache_path, rct_history_path, rct_icon_path
from core.platutils import set_window_icon
from core.config import ConfigManager
from core.appfunc import MainApplication

class Main:
    def __init__(self, start_args=None):
        self.config = ConfigManager()
        self._force_quit = False
        self.root = tk.Tk()
        # 先隐藏，等界面全部构建完成后再决定是否显示，避免启动时闪一下
        self.root.withdraw()
        self.root.title("随机抽取工具")
        self.root.geometry("600x460+50+50")
        self.root.minsize(560, 460)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        set_window_icon(self.root, rct_icon_path)
        self.app = MainApplication(self.root, start_args)
        # 创建桌面悬浮球（默认显示，可在配置中关闭）
        try:
            from core import floatball
            floatball.create_ball(self.root, self.app)
            floatball.refresh()
        except Exception as e:
            rctlog.warning(f"创建桌面悬浮球失败: {e}")
        # 创建系统托盘（默认启用，可配置关闭）
        self.tray = None
        self._tray_ok = False
        try:
            from core import tray as tray_mod
            self.tray = tray_mod.setup(self.root, self.app)
            self._tray_ok = tray_mod.is_available() and self.tray.active
            if not tray_mod.is_available():
                rctlog.warning(f"系统托盘不可用: {tray_mod.unavailable_reason()}")
        except Exception as e:
            rctlog.warning(f"创建系统托盘失败: {e}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动后延迟执行自动检测更新
        self.root.after(1500, self._auto_check_update)
        # 决定是否显示主界面：只有托盘已就绪且配置为后台启动才保持隐藏
        want_hidden = bool(self.config.get("tray_start_minimized", False))
        if want_hidden and self._tray_ok:
            rctlog.info("已按配置在启动后驻留系统托盘，主界面保持隐藏")
        else:
            self.root.deiconify()
            if want_hidden:
                rctlog.warning("托盘未就绪，已改为显示主界面")
        self.root.mainloop()

    def _tray_available(self):
        """托盘当前是否可用于驻留：需图标在运行且配置未关闭"""
        return (self.tray is not None
                and self.tray.active
                and self.config.get("tray_enabled", True))

    def _quit_app(self):
        """真正退出程序"""
        self._force_quit = True
        try:
            from core import floatball
            floatball.destroy()
        except Exception as e:
            rctlog.warning(f"关闭悬浮球失败: {e}")
        if self.tray is not None:
            try:
                self.tray.stop()
            except Exception as e:
                rctlog.warning(f"停止托盘失败: {e}")
        self.root.destroy()

    def _auto_check_update(self):
        """启动时静默检测更新 — 调用 update.py --check-silent"""
        try:
            if not self.config.get("auto_check_update", True):
                return
            source = self.config.get("update_source", "github")
            accept_preview = self.config.get("accept_preview_update", False)
            from core.update import run_auto_update

            def _check():
                has_update = run_auto_update(source=source, mode="--check-silent",
                                              timeout=8, accept_preview=accept_preview)
                if has_update:
                    self.root.after(0, self._show_update_prompt, source, accept_preview)

            import threading
            t = threading.Thread(target=_check, daemon=True)
            t.start()
        except Exception as e:
            rctlog.warning(f"自动检测更新失败（静默）: {e}")

    def _show_update_prompt(self, source, accept_preview=False):
        """检测到新版本时弹窗"""
        try:
            reply = messagebox.askyesno(
                "发现新版本",
                "检测到新版本可用。\n\n"
                "是否立即打开更新程序进行升级？\n\n"
                "选择「是」打开更新程序，选择「否」稍后手动更新。"
            )
            if reply:
                from core.update import run_auto_update
                run_auto_update(source=source, mode="--check", accept_preview=accept_preview)
        except Exception:
            pass

    def on_closing(self):
        """窗口关闭时：托盘可驻留则隐藏，否则一律按完全退出处理"""
        if self._force_quit:
            self._quit_app()
            return
        rctlog.info("用户关闭窗口")
        if self._tray_available():
            self.root.withdraw()
            rctlog.info("已隐藏到系统托盘，程序继续在后台运行")
            return
        # 托盘已关闭时若只隐藏窗口，用户将无法再唤出界面，因此直接走完全退出
        if messagebox.askyesno("退出程序", "确定要退出随机抽取工具吗？"):
            rctlog.info("程序正常退出")
            self._quit_app()

def init_dir():
    for path in [rct_prog_data_path, rct_result_path, rct_log_path, rct_cache_path, rct_history_path]:
        os.makedirs(path, exist_ok=True)

def main():
    """主入口"""
    init_dir()
    from core.startargs import parse as parse_start_args
    start_args = parse_start_args(sys.argv[1:])
    if start_args.errors:
        rctlog.warning("启动参数存在问题（异常部分已忽略）: "
                       + "; ".join(start_args.errors))
    try:
        rctlog.info("=" * 50)
        rctlog.info(f"随机抽取工具 {rct_version} 启动")
        rctlog.info(f"工作目录: {work_path}")
        if start_args.has_rules():
            parts = []
            if start_args.target_libs:
                parts.append("样本库=" + "、".join(start_args.target_libs))
            if start_args.target_files:
                parts.append("外部文件=" + "、".join(start_args.target_files))
            scope = "；".join(parts) if parts else "全部样本"
            rctlog.info("启动参数：自定义权重已开启，目标=" + scope)
        rctlog.info("=" * 50)
        Main(start_args)
        # 主循环结束，释放 IslandMQ 通知使用的 ZeroMQ Context
        try:
            from core import islandmq
            islandmq.shutdown()
        except Exception as e:
            rctlog.warning(f"释放 IslandMQ Context 失败: {e}")
        rctlog.info("=" * 50)
    except Exception as e:
        rctlog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("启动失败", f"程序启动失败：\n{e}")

if __name__ == '__main__':
    main()