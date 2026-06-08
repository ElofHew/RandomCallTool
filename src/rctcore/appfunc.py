"""
应用功能模块 - 主界面选项卡、菜单栏及通用功能
"""
import os
from time import strftime
import tkinter as tk
from tkinter import ttk, messagebox
from rctcore.more import More, run_process
from core.info import work_path, rct_log_path, rct_appname, rct_version
from core.logman import rctlog
from rctcore.fileman import FileManager, SampleLibrary
from rctcore.tabs import HomeTab, RandomCallTab
from rctcore.window import ConfigWindow

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.call_tab = None
        self.create_tabs()
        self.create_menu()

    def create_tabs(self):
        """创建选项卡界面"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.home_tab = HomeTab(self.notebook)
        self.call_tab = RandomCallTab(self.notebook)

        self.notebook.add(self.home_tab.frame, text="主页")
        self.notebook.add(self.call_tab.frame, text="随机抽取")

    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        menus = {
            "文件": [
                ("导入样本", ApplicationFunctions.import_sample),
                ("打开结果目录", self.open_result_dir),
                ("-", None),
                ("退出", self.quit_app),
            ],
            "编辑": [
                ("配置", self.open_config_window),
                ("清除所有历史", lambda: ApplicationFunctions.clear_all_history(self.call_tab)),
            ],
            "工具": [
                ("随机抽取", lambda: self.notebook.select(self.call_tab.frame)),
                ("-", None),
                ("生成RCP文件", ApplicationFunctions.create_rcp_file),
                ("-", None),
                ("检测更新", ApplicationFunctions.check_update),
            ],
            "帮助": [
                ("使用说明", ApplicationFunctions.show_help),
                ("关于", lambda: ApplicationFunctions.show_about(self.root)),
            ],
            "日志": [
                ("查看日志", FileManager.open_log_file),
                ("清除日志", ApplicationFunctions.clear_log),
            ],
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
    def import_sample():
        """导入样本到样本库"""
        from tkinter import simpledialog, filedialog as fd
        fp = fd.askopenfilename(
            title="选择要导入的名单文件",
            filetypes=[("可用文件", "*.txt;*.csv;*.rcp"),
                       ("文本文件", "*.txt"),
                       ("CSV文件", "*.csv"),
                       ("编码文件", "*.rcp"),
                       ("所有文件", "*.*")])
        if not fp:
            return
        if len(SampleLibrary.get_samples()) >= 50:
            messagebox.showwarning("警告", "样本库已达上限（50个）")
            return
        name = simpledialog.askstring("导入样本", "请输入样本名称：")
        if not name:
            return
        name = name.strip()
        try:
            SampleLibrary.import_sample(fp, name)
            rctlog.info(f"样本已导入: {name}")
            messagebox.showinfo("成功", f"样本「{name}」已导入")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

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
        """打开RCP编码工具GUI"""
        rcp_tool_path = os.path.join(work_path, "encode.exe")
        run_process(rcp_tool_path)

    @staticmethod
    def check_update():
        """检测更新（菜单调用，异步线程）"""
        from rctcore.update import check_update_async, open_download_page
        from rctcore.config import ConfigManager
        import tkinter as tk

        config = ConfigManager()
        source = config.get("update_source", "github")

        # 弹窗让用户选择更新源
        choice = messagebox.askquestion(
            "检测更新",
            f"将从 {source.upper()} 获取版本信息\n"
            f"当前版本: v{rct_version}\n\n"
            f"是否继续？",
            icon="info",
        )
        if choice != "yes":
            return

        # 获取顶层窗口用于异步回调
        root = tk._default_root

        def _on_success(result):
            if not result["success"]:
                messagebox.showerror(
                    "检测失败",
                    f"无法获取版本信息\n\n原因: {result.get('error', '未知错误')}\n"
                    f"请检查网络连接或尝试切换更新源。"
                )
                return
            if result["has_update"]:
                reply = messagebox.askyesno(
                    "发现新版本",
                    f"发现新版本！\n\n"
                    f"当前版本: v{result['local_version']}\n"
                    f"最新版本: v{result['remote_version']} ({result['remote_date']})\n"
                    f"更新源: {result['source_name']}\n\n"
                    f"是否前往下载页面？"
                )
                if reply:
                    open_download_page(source)
            else:
                messagebox.showinfo(
                    "已是最新版本",
                    f"当前已是最新版本\n\n"
                    f"版本: v{result['local_version']} (vercode: {result['local_vercode']})\n"
                    f"远程版本: v{result['remote_version']} (vercode: {result['remote_vercode']})\n"
                    f"更新源: {result['source_name']}\n"
                    f"远程发布日期: {result['remote_date']}"
                )

        def _on_error(err):
            messagebox.showerror("检测失败", f"网络请求失败:\n{err}")

        if root:
            check_update_async(
                root, source=source, timeout=10,
                on_success=_on_success, on_error=_on_error,
            )

    @staticmethod
    def show_about(root):
        """显示关于信息"""
        More(root).about()
    
    @staticmethod
    def clear_all_history(call_tab):
        """清除所有历史记录"""
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            if hasattr(call_tab, "history") and hasattr(call_tab, "_rebuild_history_ui"):
                call_tab.history.clear()
                call_tab._rebuild_history_ui()
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
                    if file == f"{rct_appname}-{strftime('%Y-%m-%d')}.log" or file == f"{strftime('%Y-%m-%d')}.log":
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
