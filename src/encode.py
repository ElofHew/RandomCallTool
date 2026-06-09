"""
@Name: 随机抽人名单编码工具
@Author: Dan_Evan
@Date: 2026-06-09
@Version: 1.2
@Description: 一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。
"""

import os
import argparse
import tkinter as tk
from tkinter import messagebox
from core.logman import enclog
from core.info import (
    work_path, enc_version, enc_prog_data_path,
    enc_output_path, enc_log_path,
)
from enccore.config import ConfigManager
from enccore.appfunc import MainApplication


class Main:
    def __init__(self, file_to_load=None):
        self.config = ConfigManager()
        self.root = tk.Tk()
        self.root.title("随机抽人名单编码工具")
        self.root.minsize(500, 500)
        self.root.resizable(True, True)

        self.app = MainApplication(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 如果命令行指定了文件，自动加载
        if file_to_load and os.path.exists(file_to_load):
            self.app.open_input_file(file_to_load)

        self.root.mainloop()

    def on_closing(self):
        enclog.info("用户关闭窗口")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            enclog.info("程序正常退出")
            self.root.destroy()


def init_dir():
    """初始化目录结构"""
    for path in [enc_prog_data_path, enc_output_path, enc_log_path]:
        os.makedirs(path, exist_ok=True)


def parse_args():
    """命令行参数解析"""
    parser = argparse.ArgumentParser(
        description="随机抽人名单编码工具 - 为 RandomCallTool 生成 RCP 编码文件"
    )
    parser.add_argument(
        "file", nargs="?", default=None,
        help="要加载编码的名单文件（.txt）"
    )
    parser.add_argument(
        "-v", "--version", action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--batch", metavar="DIR",
        help="批量编码指定目录下所有 .txt 文件"
    )
    parser.add_argument(
        "--output", metavar="DIR",
        help="批量编码时的输出目录"
    )
    parser.add_argument(
        "--method", choices=["base64", "hex"], default="base64",
        help="编码方式 (默认: base64)"
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 版本信息
    if args.version:
        print(f"随机抽人名单编码工具 v{enc_version}")
        print(f"作者: Dan_Evan")
        print(f"日期: 2026-06-08")
        return

    init_dir()

    # 命令行批量模式
    if args.batch:
        from enccore.encoder import ListEncoder
        input_dir = os.path.abspath(args.batch)
        output_dir = os.path.abspath(args.output) if args.output else enc_output_path
        print(f"批量编码: {input_dir} -> {output_dir} (方式: {args.method})")
        results = ListEncoder.batch_encode_files(
            input_dir, output_dir,
            method=args.method,
            pattern="*.txt",
        )
        success = sum(1 for _, _, ok in results if ok)
        print(f"完成: {success}/{len(results)} 个文件")
        return

    # GUI 模式
    try:
        enclog.info("=" * 50)
        enclog.info(f"随机抽人名单编码工具 v{enc_version} 启动")
        enclog.info(f"工作目录: {work_path}")
        enclog.info("=" * 50)

        file_to_load = os.path.abspath(args.file) if args.file else None
        Main(file_to_load=file_to_load)

        enclog.info("程序正常退出")
        enclog.info("=" * 50)

    except Exception as e:
        enclog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")


if __name__ == '__main__':
    main()