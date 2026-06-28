"""
RemoveTool for RandomCallTool - 随机抽取工具配套卸载工具
卸载工具入口 - remove.py

流程:
  1. 本地构建 remove.bat 脚本
  2. 写入系统临时目录 (%TEMP%)
  3. 结束正在运行的套件程序 (rctool/encode/update)
  4. 非阻塞并行运行 bat
  5. 立即杀死卸载工具自身进程，bat 在后台完成后续工作
"""
import os
import sys
import time
import subprocess
import argparse
import tkinter as tk
from tkinter import messagebox

# 程序根目录
if getattr(sys, "frozen", False):
    PROGRAM_ROOT = os.path.dirname(sys.executable)
else:
    PROGRAM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_process_list():
    """需要杀死的进程名列表"""
    return ["rctool", "encode", "update"]


def kill_processes():
    """结束正在运行的套件程序"""
    print("[Uninstall] Killing running processes...")
    for name in get_process_list():
        try:
            subprocess.run(["taskkill", "/F", "/IM", f"{name}.exe"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
    time.sleep(0.5)


def get_files_to_delete(mode):
    """获取要删除的文件/目录列表"""
    if mode == "reset":
        return [os.path.join(PROGRAM_ROOT, "data")], PROGRAM_ROOT

    all_items = []
    for name in os.listdir(PROGRAM_ROOT):
        path = os.path.join(PROGRAM_ROOT, name)
        if name == os.path.basename(__file__):
            continue
        all_items.append(path)

    if mode == "keep-data":
        data_dir = os.path.join(PROGRAM_ROOT, "data")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        keep = {data_dir,
                os.path.join(desktop, "\u968f\u673a\u62bd\u53d6\u7ed3\u679c"),
                os.path.join(desktop, "\u7f16\u7801\u540d\u5355")}
        filtered = []
        for p in all_items:
            skip = False
            for kd in keep:
                try:
                    if not os.path.relpath(p, kd).startswith(".."):
                        skip = True
                        break
                except ValueError:
                    pass
            if not skip:
                filtered.append(p)
        all_items = filtered

    return all_items, PROGRAM_ROOT


def build_remove_script(mode, setup_path=None):
    """构建 remove.bat → 写入 %TEMP%，返回 bat 路径

    bat 流程:
      1. 结束所有套件进程
      2. 按模式删除文件
      3. 如果给了安装包，非阻塞运行安装
      4. 删除自身
    """
    items, root_dir = get_files_to_delete(mode)
    root_dir = os.path.normpath(root_dir)

    bat = "@echo off\r\nchcp 65001 >nul\r\n"
    bat += "title RandomCallTool Uninstall...\r\n"
    bat += "echo [Uninstall] Removing program files...\r\n"

    # 1. 杀进程
    for name in get_process_list():
        bat += f'taskkill /F /IM "{name}.exe" >nul 2>&1\r\n'

    bat += "timeout /t 1 /nobreak >nul\r\n"

    # 2. 删除文件
    for item in items:
        n = os.path.normpath(item)
        bat += f'if exist "{n}" (\r\n'
        if os.path.isdir(item):
            bat += f'    rmdir /s /q "{n}" >nul 2>&1\r\n'
        else:
            bat += f'    del /f /q "{n}" >nul 2>&1\r\n'
        bat += ")\r\n"
    if mode == "full":
        bat += f'rmdir /s /q "{root_dir}" >nul 2>&1\r\n'

    # 3. 运行安装包（如果给了）
    if setup_path and os.path.isfile(setup_path):
        sp = os.path.normpath(setup_path)
        bat += f'echo [Uninstall] Running setup...\r\n'
        bat += f'start /b "" "{sp}"\r\n'

    # 4. 删除 bat 自身并退出
    bat += 'del /f /q "%~f0" >nul 2>&1\r\n'
    bat += 'exit\r\n'

    # 写入临时目录
    tmp = os.environ.get("TEMP", os.path.expanduser("~"))
    os.makedirs(tmp, exist_ok=True)
    sp = os.path.join(tmp, "rct_remove.bat")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(bat)
    return sp


def run_uninstall(mode, setup_path=None):
    """执行卸载：构建 bat → 非阻塞运行 → 杀死自身"""
    MODE_LABELS = {"keep-data": "Keep Data", "reset": "Reset", "full": "Full Uninstall"}
    label = MODE_LABELS.get(mode, mode)
    print("=" * 50)
    print("  Random Call Tool - Uninstaller")
    print("  Mode: " + label)
    print("  Directory: " + PROGRAM_ROOT)
    if setup_path:
        print("  Setup: " + setup_path)
    print("=" * 50)

    kill_processes()
    script = build_remove_script(mode, setup_path)

    print("[Uninstall] Starting cleanup in background...")
    subprocess.Popen(["cmd.exe", "/c", "start", "", "/MIN", script])

    print("[Uninstall] Uninstaller exiting...")
    time.sleep(0.5)
    os._exit(0)


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
        icon_path = os.path.join(PROGRAM_ROOT, "res", "icon", "remove.ico")
        if os.path.isfile(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    mode_var = tk.StringVar(value="keep-data")

    # 标题
    tk.Label(
        root, text="随机抽取工具 - 卸载程序",
        font=("Helvetica", 14, "bold"), fg="blue"
    ).pack(pady=(15, 5))

    # 目录信息
    tk.Label(
        root, text="目录: " + PROGRAM_ROOT,
        font=("", 9), fg="gray", wraplength=420
    ).pack(pady=(0, 10))

    # 模式选择框
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

    # 警告
    warn_label = tk.Label(
        root,
        text="注意: 卸载前请确保已备份重要数据，此操作不可撤销！",
        fg="red", font=("", 9),
    )
    warn_label.pack(pady=(5, 10))

    # 按钮
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(0, 15))

    def on_confirm():
        mode = mode_var.get()
        labels = {"keep-data": "保留数据", "reset": "重置（仅删除数据）", "full": "完全卸载"}
        label = labels.get(mode, mode)
        ok = messagebox.askyesno(
            "确认",
            "即将执行: " + label + "\n\n"
            "目标目录: " + PROGRAM_ROOT + "\n\n"
            "确定要继续吗？\n(此操作不可撤销！)"
        )
        if ok:
            root.destroy()
            run_uninstall(mode)

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
        print("Target: " + PROGRAM_ROOT)
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

    run_uninstall(mode, setup_path=args.setup_path)


if __name__ == "__main__":
    main()

