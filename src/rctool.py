"""
@Name: 随机抽取工具
@Author: Dan_Evan
@Date: 2026-06-07
@Version: 2.2
@Description: 一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。
"""

# 导入系统库
import sys
# 导入Tkinter GUI库
import tkinter as tk
from tkinter import messagebox
# 导入日志库
from core.logman import rctlog
# 导入信息类
from core.info import work_path, rct_version
# 导入文件管理器
from rctcore.fileman import init_dir
# 导入更多功能类
from rctcore.more import check_os
# 导入配置管理器
from rctcore.config import ConfigManager
# 导入主应用类
from rctcore.appfunc import MainApplication

class Main:
    def __init__(self):
        """初始化主程序"""
        # 初始化配置
        self.config = ConfigManager()
        # 构建主窗口
        self.root = tk.Tk()
        self.root.title("随机抽取工具")
        self.root.geometry("400x550+50+50")
        self.root.minsize(350, 500)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        # 创建应用程序
        self.app = MainApplication(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动主循环
        self.root.mainloop()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        rctlog.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            rctlog.info("程序正常退出")
            self.root.destroy()

def main():
    """主函数"""
    init_dir()

    try:
        rctlog.info("=" * 50)
        rctlog.info(f"随机抽取工具 {rct_version} 启动")
        rctlog.info(f"工作目录: {work_path}")
        rctlog.info("=" * 50)
        
        Main()
        
        rctlog.info("程序正常退出")
        rctlog.info("=" * 50)
        
    except Exception as e:
        rctlog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    if not check_os():
        sys.exit(1)
    else:
        main()