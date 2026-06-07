"""
应用功能模块
"""
# 导入OS库
import os
# 导入时间戳格式化
from time import strftime
# 导入Tkinter GUI库
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import messagebox
# 导入应用库
from rctcore.more import More, run_process
from core.info import work_path, rct_log_path, rct_appname
from core.logman import rctlog
from rctcore.fileman import FileManager
from rctcore.tabs import HomeTab, RandomGroupTab, RandomPersonTab
from rctcore.window import ConfigWindow

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.group_tab = None
        self.person_tab = None
        self.create_tabs()
        self.create_menu()
        
    def create_tabs(self):
        """创建选项卡界面"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.home_tab = HomeTab(self.notebook)
        self.group_tab = RandomGroupTab(self.notebook)
        self.person_tab = RandomPersonTab(self.notebook)
        
        self.notebook.add(self.home_tab.frame, text="主页")
        self.notebook.add(self.group_tab.frame, text="随机抽组")
        self.notebook.add(self.person_tab.frame, text="随机抽人")
    
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # 菜单项配置
        menus = {
            "文件": [
                ("打开结果目录", self.open_result_dir),
                ("-", None),
                ("退出", self.quit_app)
            ],
            "编辑": [
                ("配置", self.open_config_window),
                ("清除所有历史", lambda: ApplicationFunctions.clear_all_history(self.group_tab, self.person_tab))
            ],
            "工具": [
                ("随机抽组", lambda: self.notebook.select(self.group_tab.frame)),
                ("随机抽人", lambda: self.notebook.select(self.person_tab.frame)),
                ("-", None),
                ("生成RCP文件", ApplicationFunctions.create_rcp_file)
            ],
            "帮助": [
                ("使用说明", ApplicationFunctions.show_help),
                ("关于", lambda: ApplicationFunctions.show_about(self.root))
            ],
            "日志": [
                ("查看日志", FileManager.open_log_file),
                ("清除日志", ApplicationFunctions.clear_log)
            ]
        }
        
        for menu_name, items in menus.items():
            menu = tk.Menu(menu_bar, tearoff=0)
            menu_bar.add_cascade(label=menu_name, menu=menu)
            for item_text, command in items:
                if item_text == "-":
                    menu.add_separator()
                else:
                    menu.add_command(label=item_text, command=command)
    
    def open_config_window(self):
        """打开配置窗口"""
        rctlog.info("打开配置窗口")
        ConfigWindow(self.root)
    
    def open_result_dir(self):
        """打开结果目录"""
        FileManager.open_directory(FileManager.get_result_path())
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            rctlog.info("用户确认退出程序")
            self.root.quit()

class ApplicationFunctions:
    """应用程序通用功能类"""
    
    @staticmethod
    def show_help():
        """显示帮助"""
        help_text = """随机抽取工具 v2.2 使用说明

一、主要功能：
1. 随机抽组：从指定数量的组中随机抽取一个或多个组
2. 随机抽人：从样本文件中随机抽取一个或多个人名

二、操作指南：

【随机抽组】
1. 选择分组方式：数字(123)或字母(ABC)
2. 输入总组数（1-26）
3. 输入要抽取的组数（不能超过总组数）
4. 点击"抽取"按钮进行随机抽取

【随机抽人】
1. 加载样本文件（支持 .rcp, .txt, .csv 格式）
   - 点击"选择文件"手动选择
   - 点击"自动加载"使用默认样本
   - 点击"重新加载"刷新当前文件
2. 输入要抽取的人数（不能超过样本数量）
3. 点击"抽取"按钮进行随机抽取

三、文件格式说明：
1. .rcp文件：经过Base64编码的名单文件（推荐使用）
2. .txt文件：纯文本文件，支持逗号、分号、制表符或换行分隔
3. .csv文件：逗号分隔值文件

四、智能抽样功能：
1. 抽取前打乱：提高随机性，减少顺序影响
2. 加权抽样：根据历史抽取次数调整权重，实现长期公平
3. 可重置抽样历史：重新开始公平性计算

五、其他功能：
1. 结果保存：抽取结果自动保存为HTML格式
2. 历史记录：记录最近的抽取历史
3. 配置管理：可设置保存路径、自动保存等选项
4. 日志查看：记录程序运行状态

六、注意事项：
1. 支持重复名字自动去重
2. 抽取人数不能超过样本总数
3. 默认样本存放在 data/default.rcp
4. 结果文件保存在 data/result 目录或桌面

如需更多帮助，请访问项目地址：
GitHub: https://github.com/ElofHew/RandomCallTool
Gitee: https://gitee.com/ElofHew/RandomCallTool"""
        
        messagebox.showinfo("使用说明", help_text)
        rctlog.info("显示使用说明")
    
    @staticmethod
    def create_rcp_file():
        """打开RCP生成工具"""
        rcp_tool_path = os.path.join(work_path, "encode.exe")
        process = run_process(rcp_tool_path, "-h")
        return process
    
    @staticmethod
    def show_about(root):
        """显示关于信息"""
        More(root).about()
    
    @staticmethod
    def clear_all_history(group_tab, person_tab):
        """清除所有历史记录"""
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            for tab in [group_tab, person_tab]:
                if hasattr(tab, 'history'):
                    tab.history.clear()
                    if hasattr(tab, 'history_listbox'):
                        tab.history_listbox.delete(0, tk.END)
            rctlog.info("所有历史记录已清除")
            messagebox.showinfo("成功", "历史记录已清除")
            return True
        return False
    
    @staticmethod
    def clear_log():
        """清除日志"""
        if messagebox.askyesno("确认", "确定要清除所有日志文件吗？"):
            try:
                for file in os.listdir(rct_log_path):
                    if file == (f"{rct_appname}-{strftime('%Y-%m-%d')}.log" or f"{strftime('%Y-%m-%d')}.log"):
                        continue
                    if file.endswith('.log'):
                        os.remove(os.path.join(rct_log_path, file))
                rctlog.info("日志文件已清除")
                messagebox.showinfo("成功", "日志文件已清除")
                return True
            except Exception as e:
                rctlog.error(f"清除日志失败: {e}")
                messagebox.showerror("错误", f"清除日志失败: {e}")
                return False
