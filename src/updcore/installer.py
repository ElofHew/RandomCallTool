"""
更新程序卸载与安装 — 通过 remove.exe 完成保留数据卸载 + 安装
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
