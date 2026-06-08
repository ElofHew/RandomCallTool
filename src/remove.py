"""
随机抽取工具 - 卸载工具
提供保留数据/完全卸载两种模式，支持 Windows / Linux / macOS
"""
import os
import sys
import time
import platform
import subprocess
import argparse
import tkinter as tk
from tkinter import messagebox

# 获取程序根目录（支持 PyInstaller 打包和源码两种模式）
if getattr(sys, "frozen", False):
    PROGRAM_ROOT = os.path.dirname(sys.executable)
else:
    PROGRAM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYSTEM = platform.system()
EXE_NAMES = ["rctool", "encode"]


def get_process_kill_cmd():
    """生成杀死指定进程的系统命令"""
    cmds = []
    for name in EXE_NAMES:
        if SYSTEM == "Windows":
            cmds.append(["taskkill", "/F", "/IM", f"{name}.exe"])
        elif SYSTEM == "Darwin":
            cmds.append(["pkill", "-9", name])
            cmds.append(["pkill", "-9", f"{name}.app"])
        else:
            cmds.append(["pkill", "-9", name])
    return cmds


def kill_processes():
    """杀死正在运行的 rctool / encode 进程"""
    print("[Uninstall] Killing running processes...")
    for cmd in get_process_kill_cmd():
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except Exception:
            pass
    time.sleep(0.5)


def get_files_to_delete(mode):
    """获取要删除的文件/目录列表"""
    all_items = []
    for name in os.listdir(PROGRAM_ROOT):
        path = os.path.join(PROGRAM_ROOT, name)
        if name == os.path.basename(__file__):
            continue
        all_items.append(path)

    if mode == "keep-data":
        data_dir = os.path.join(PROGRAM_ROOT, "data")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        keep = {
            data_dir,
            os.path.join(desktop, u"\u968f\u673a\u62bd\u53d6\u7ed3\u679c"),
            os.path.join(desktop, u"\u7f16\u7801\u540d\u5355"),
        }
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


def build_remove_script(mode):
    """构建系统级删除脚本"""
    items, root_dir = get_files_to_delete(mode)
    root_dir = os.path.normpath(root_dir)

    if SYSTEM == "Windows":
        # Windows: 生成临时 .bat 脚本
        bat = "@echo off\nchcp 65001 >nul\n"
        bat += "echo [Uninstall] Removing program files...\n"
        bat += "timeout /t 1 /nobreak >nul\n"
        for item in items:
            n = os.path.normpath(item)
            bat += 'if exist "' + n + '" (\n'
            if os.path.isdir(item):
                bat += '    rmdir /s /q "' + n + '" >nul 2>&1\n'
            else:
                bat += '    del /f /q "' + n + '" >nul 2>&1\n'
            bat += ")\n"
        # 完全卸载模式才删除根目录，保留数据模式不能删
        if mode == "full":
            bat += 'rmdir /s /q "' + root_dir + '" >nul 2>&1\n'
        bat += 'del /f /q "%~f0" >nul 2>&1\n'
        tmp = os.path.join(os.environ.get("TEMP", "."), "rct_uninstall")
        os.makedirs(tmp, exist_ok=True)
        sp = os.path.join(tmp, "uninstall.bat")
        with open(sp, "w", encoding="utf-8") as f:
            f.write(bat)
        return sp, True

    else:
        # Linux/macOS: 返回 Shell 命令字符串
        cmds = ["echo '[Uninstall] Removing program files...'", "sleep 1"]
        for item in items:
            e = item.replace("'", "'\\''")
            if os.path.isfile(item):
                cmds.append("rm -f '" + e + "' 2>/dev/null")
            else:
                cmds.append("rm -rf '" + e + "' 2>/dev/null")
        # 完全卸载模式才删除根目录，保留数据模式不能删
        if mode == "full":
            e = root_dir.replace("'", "'\\''")
            cmds.append("rm -rf '" + e + "' 2>/dev/null")
        cmds.append("echo '[Uninstall] Done'")
        return "; ".join(cmds), False


def run_uninstall(mode):
    """执行卸载流程"""
    label = "Keep Data" if mode == "keep-data" else "Full Uninstall"
    print("=" * 50)
    print("  Random Call Tool - Uninstaller")
    print("  Mode: " + label)
    print("  Directory: " + PROGRAM_ROOT)
    print("=" * 50)
    print()

    kill_processes()
    script, is_file = build_remove_script(mode)

    print("[Uninstall] Starting cleanup...")
    if SYSTEM == "Windows":
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", "/MIN", script], shell=True
        )
    else:
        subprocess.Popen(
            ["nohup", "sh", "-c", script, "&"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    print("[Uninstall] Uninstaller exiting, cleanup continues in background...")
    time.sleep(0.5)
    os._exit(0)


def parse_args():
    p = argparse.ArgumentParser(
        description="Random Call Tool - Uninstaller"
    )
    p.add_argument(
        "mode", nargs="?", default=None,
        choices=["keep-data", "full"],
        help="keep-data: keep data & config | full: remove everything"
    )
    p.add_argument(
        "-y", "--yes", action="store_true",
        help="skip confirmation prompt"
    )
    return p.parse_args()


def gui_main():
    """tkinter GUI 模式 — 让用户选择卸载方式并确认"""
    root = tk.Tk()
    root.title("Random Call Tool - 卸载")
    root.geometry("460x280+200+200")
    root.resizable(False, False)

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
        text="完全卸载 - 删除所有文件（包括数据/配置/日志）",
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
        label = "保留数据" if mode == "keep-data" else "完全卸载"
        ok = messagebox.askyesno(
            "确认卸载",
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
    args = parse_args()

    if args.mode is None:
        # 无参数 → 启动 tkinter GUI
        gui_main()
        return
    else:
        mode = args.mode

    if not args.yes:
        label = "Keep Data" if mode == "keep-data" else "Full Uninstall"
        print("\nAbout to: " + label)
        print("Target: " + PROGRAM_ROOT)
        try:
            c = input("Confirm? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled")
            return
        if c != "y":
            print("Cancelled")
            return

    run_uninstall(mode)


if __name__ == "__main__":
    main()
