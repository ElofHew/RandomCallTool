"""
RemoveTool for RandomCallTool - 随机抽取工具配套卸载工具
卸载工具入口 — 解析参数 + GUI 交互，核心逻辑委派到 utils/installer

流程:
  1. 本地构建 remove.bat 脚本（utils/installer）
  2. 写入系统临时目录 (%TEMP%)
  3. 结束正在运行的套件程序 (rctool/update)
  4. 非阻塞并行运行 bat
  5. 立即杀死卸载工具自身进程，bat 在后台完成后续工作
"""
import os
import sys
import argparse
import tkinter as tk
from tkinter import messagebox

from utils import installer
from utils import config


def parse_args():
    p = argparse.ArgumentParser(description="Random Call Tool - Uninstaller")
    p.add_argument("mode", nargs="?", default=None,
                   choices=["keep-data", "reset", "full"],
                   help="keep-data: keep data | reset: delete data only | full: remove everything")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    p.add_argument("--setup-path", default=None,
                   help="卸载完成后运行的安装包路径")
    return p.parse_args()


def gui_main():
    """tkinter GUI 模式 — 让用户选择卸载方式并确认"""
    root = tk.Tk()
    root.title("随机抽取工具 - 卸载")
    root.geometry("460x320+200+200")
    root.resizable(False, False)
    try:
        icon_path = os.path.join(config.PROGRAM_ROOT, "res", "icon", "remove.ico")
        if os.path.isfile(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    mode_var = tk.StringVar(value="keep-data")

    tk.Label(
        root, text="随机抽取工具 - 卸载程序",
        font=("Helvetica", 14, "bold"), fg="blue"
    ).pack(pady=(15, 5))

    tk.Label(
        root, text="目录: " + config.PROGRAM_ROOT,
        font=("", 9), fg="gray", wraplength=420
    ).pack(pady=(0, 10))

    mode_frame = tk.LabelFrame(root, text="请选择卸载模式")
    mode_frame.pack(padx=20, pady=5, fill="x")

    tk.Radiobutton(
        mode_frame,
        text="保留数据 - 仅删除程序文件，保留数据配置和桌面结果",
        variable=mode_var, value="keep-data",
        anchor="w", font=("", 10),
    ).pack(fill="x", padx=15, pady=(10, 2))

    tk.Radiobutton(
        mode_frame,
        text="重置配置 - 仅删除数据配置和日志，保留程序文件",
        variable=mode_var, value="reset",
        anchor="w", font=("", 10),
    ).pack(fill="x", padx=15, pady=(2, 2))

    tk.Radiobutton(
        mode_frame,
        text="完全卸载 - 删除所有文件（包括程序/数据/配置/日志）",
        variable=mode_var, value="full",
        anchor="w", font=("", 10),
    ).pack(fill="x", padx=15, pady=(2, 10))

    warn_label = tk.Label(
        root,
        text="注意: 卸载前请确保已备份重要数据，此操作不可撤销！",
        fg="red", font=("", 9),
    )
    warn_label.pack(pady=(5, 10))

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(0, 15))

    def on_confirm():
        mode = mode_var.get()
        labels = {"keep-data": "保留数据", "reset": "重置（仅删除数据）", "full": "完全卸载"}
        label = labels.get(mode, mode)
        ok = messagebox.askyesno(
            "确认",
            "即将执行: " + label + "\n\n"
            "目标目录: " + config.PROGRAM_ROOT + "\n\n"
            "确定要继续吗？\n(此操作不可撤销！)"
        )
        if ok:
            root.destroy()
            installer.run_uninstall(mode)

    def on_cancel():
        root.destroy()
        sys.exit(0)

    tk.Button(
        btn_frame, text="执行卸载", command=on_confirm,
        width=14, height=1,
        bg="#d9534f", fg="white",
        activebackground="#c9302c", activeforeground="white",
        relief="flat", bd=0, cursor="hand2",
    ).pack(side="left", padx=5)

    tk.Button(
        btn_frame, text="取消", command=on_cancel,
        width=10, height=1,
    ).pack(side="left", padx=5)

    root.mainloop()


def main():
    try:
        args = parse_args()
    except SystemExit:
        return

    if args is None or args.mode is None:
        gui_main()
        return

    mode = args.mode

    if not args.yes:
        labels = {"keep-data": "Keep Data", "reset": "Reset", "full": "Full Uninstall"}
        label = labels.get(mode, mode)
        print("\nAbout to: " + label)
        print("Target: " + config.PROGRAM_ROOT)
        if args.setup_path:
            print("Setup: " + args.setup_path)
        try:
            c = input("Confirm? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled")
            return
        if c != "y":
            print("Cancelled")
            return

    installer.run_uninstall(mode, setup_path=args.setup_path)


if __name__ == "__main__":
    main()

