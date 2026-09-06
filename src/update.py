"""
RandomCallTool 独立更新程序 — 入口
实现在 core/ 模块

参数:
  无参数          → 打开主界面
  --check         → 直接检测更新（启动即检测）
  --source <src>  → 指定更新源 (github/gitee)
  --check-silent  → 静默检测
  --version       → 打印版本
"""
import sys
import argparse
import os
import tkinter as tk

from core import updconf
from core import network
from core import updgui


def parse_args():
    parser = argparse.ArgumentParser(description="RandomCallTool 独立更新程序")
    parser.add_argument("--check", action="store_true", help="启动后立即检测")
    parser.add_argument("--source", choices=["github", "gitee"],
                        default="github", help="更新源")
    parser.add_argument("--check-silent", action="store_true", help="静默检测")
    parser.add_argument("--accept-preview", action="store_true", help="接收测试版更新")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.version:
        print("RandomCallTool Update Tool v" + updconf.VERSION)
        return

    # 是否接收测试版更新
    accept_preview = args.accept_preview or updconf.get_config_accept_preview()

    # 静默检测（无 GUI）
    if args.check_silent:
        src = updconf.get_config_source() if args.source == "github" else args.source
        result = network.check_remote_version(src, timeout=8, accept_preview=accept_preview)
        if result["success"] and result["has_update"]:
            sys.exit(1)
        sys.exit(0)

    os.makedirs(updconf.CACHE_DIR, exist_ok=True)

    # 确定更新源
    src = updconf.get_config_source()
    if any(a.startswith("--source") or a.startswith("-s") for a in sys.argv[1:]):
        src = args.source

    # 单窗口，注入 auto_check 和 accept_preview 参数
    root = tk.Tk()
    updgui.UpdateApp(root, source=src, auto_check=args.check, accept_preview=accept_preview)
    root.mainloop()


if __name__ == "__main__":
    main()
