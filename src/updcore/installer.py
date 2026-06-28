"""
更新程序卸载与安装 — remove.exe 保留数据卸载 + 运行安装包
"""
import os
import subprocess
from updcore.config import REMOVE_EXE, PROGRAM_ROOT


def get_remove_path():
    candidates = [REMOVE_EXE, os.path.join(PROGRAM_ROOT, "src", "remove.py")]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return REMOVE_EXE


def run_remove_keep_data():
    rp = get_remove_path()
    if not os.path.isfile(rp):
        return True
    try:
        proc = subprocess.Popen([rp, "keep-data", "-y"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        proc.wait(timeout=30)
        return proc.returncode == 0
    except Exception:
        return False


def run_installer(exe_path):
    if not os.path.isfile(exe_path):
        return False
    try:
        subprocess.Popen([exe_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False
