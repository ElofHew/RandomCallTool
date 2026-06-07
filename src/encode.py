"""
@Name: 随机抽人名单编码工具
@Author: Dan_Evan
@Date: 2026-06-07
@Version: 1.1
@Description: 一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。
"""

# 导入系统库
import sys
import platform
# 导入Tkinter GUI库
import tkinter as tk
from tkinter import messagebox
# 导入日志库
from core.logman import enclog
# 导入信息类
from core.info import work_path, enc_version
# 导入初始化目录
from enccore.dirman import init_dir
# 导入配置管理器
from enccore.config import ConfigManager
# 导入主应用类
from enccore.appfunc import MainApplication

class Main:
    def __init__(self):
        """初始化主程序"""
        # 初始化配置
        self.config = ConfigManager()
        # 构建主窗口
        self.root = tk.Tk()
        self.root.title("随机抽人名单编码工具")
        self.root.geometry("600x600+50+50")
        self.root.minsize(500, 500)
        self.root.resizable(True, True)
        # 创建应用程序
        self.app = MainApplication(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 启动主循环
        self.root.mainloop()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        enclog.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            enclog.info("程序正常退出")
            self.root.destroy()
        
    
def check_os():
    pfs = platform.system()
    pfr = platform.release()
    pfv = platform.version()
    pfn = platform.node()
    pfall = f"{pfs} {pfr} ({pfv}) - {pfn}"
    if pfs == "Darwin":
        enclog.error(f"操作系统检测不通过：{pfall}")
        return False
    else:
        enclog.info(f"操作系统检测通过：{pfall}")
        return True

def main():
    """主函数"""
    init_dir() # 初始化目录结构

    try:
        enclog.info("=" * 50)
        enclog.info(f"随机抽人名单编码工具 {enc_version} 启动")
        enclog.info(f"工作目录: {work_path}")
        enclog.info("=" * 50)

        Main()

        enclog.info("程序正常退出")
        enclog.info("=" * 50)
        
    except Exception as e:
        enclog.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    if not check_os():
        sys.exit(1)
    else:
        main()