"""
更新程序卸载与安装 — 卸载核心逻辑 + remove.exe 链式卸载安装
"""
import os
import sys
import time
import subprocess
from utils import config


# ==============================
#  函数：进程列表
# ==============================

def get_process_list():
    """需要杀死的进程名列表"""
    return ["rctool", "update"]


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
        return [os.path.join(config.PROGRAM_ROOT, "data")], config.PROGRAM_ROOT

    all_items = []
    for name in os.listdir(config.PROGRAM_ROOT):
        path = os.path.join(config.PROGRAM_ROOT, name)
        if name in ("remove.exe", "remove.py"):
            continue
        all_items.append(path)

    if mode == "keep-data":
        data_dir = os.path.join(config.PROGRAM_ROOT, "data")
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

    return all_items, config.PROGRAM_ROOT


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

    for name in get_process_list():
        bat += f'taskkill /F /IM "{name}.exe" >nul 2>&1\r\n'

    bat += "timeout /t 1 /nobreak >nul\r\n"

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

    if setup_path and os.path.isfile(setup_path):
        sp = os.path.normpath(setup_path)
        bat += f'echo [Uninstall] Running setup...\r\n'
        bat += f'start /b "" "{sp}"\r\n'

    bat += 'del /f /q "%~f0" >nul 2>&1\r\n'
    bat += 'exit\r\n'

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
    print("  Directory: " + config.PROGRAM_ROOT)
    if setup_path:
        print("  Setup: " + setup_path)
    print("=" * 50)

    kill_processes()
    script = build_remove_script(mode, setup_path)

    print("[Uninstall] Starting cleanup in background...")
    subprocess.Popen([script], creationflags=subprocess.CREATE_NO_WINDOW)

    print("[Uninstall] Uninstaller exiting...")
    time.sleep(0.5)
    os._exit(0)


# ==============================
#  函数：remove.exe 路径 & 链式调用
# ==============================

def get_remove_path():
    candidates = [config.REMOVE_EXE, os.path.join(config.PROGRAM_ROOT, "src", "remove.py")]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return config.REMOVE_EXE


def run_remove_with_setup(setup_path):
    """启动 remove.exe，传安装包路径，使 bat 链式完成卸载→安装→自毁

    remove.exe 会：
      1. 构建 remove.bat 写入 %TEMP%
      2. bat 杀进程 → 删文件 → start 安装包 → 自删
      3. remove.exe 自毁
    """
    if not setup_path or not os.path.isfile(setup_path):
        return False
    rp = get_remove_path()
    if not os.path.isfile(rp):
        return False
    try:
        subprocess.Popen([rp, "keep-data", "-y",
                          "--setup-path", setup_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False
