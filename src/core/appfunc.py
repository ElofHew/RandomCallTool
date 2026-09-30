"""主应用功能：菜单、快捷键和通用操作入口。"""
import os
import webbrowser
from time import strftime
import tkinter as tk
from tkinter import ttk, messagebox
from core.platutils import run_process
from core.dialog import load_about_info, ask_string
from core.info import work_path, rct_log_path, rct_appname, rct_version, official_website, rct_icon_path
from core.logman import rctlog
from core.fileman import FileManager, SampleLibrary
from core.window import HomeTab, RandomCallTab, ConfigWindow, AboutWindow
from core.rollcall import RollCallTab

# 当前运行中的主应用实例（供配置窗口等跨模块访问实时状态）
_current_app = {"instance": None}


def get_app():
    """获取当前运行中的 MainApplication 实例（可能为 None）"""
    return _current_app["instance"]


class MainApplication:
    def __init__(self, root, start_args=None):
        self.root = root
        self._start_args = start_args
        self.call_tab = None
        _current_app["instance"] = self
        self.create_tabs()
        self.create_menu()
        self._bind_shortcuts()

    def create_tabs(self):
        """创建选项卡界面"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.home_tab = HomeTab(self.notebook)
        self.call_tab = RandomCallTab(self.notebook, self._start_args)
        self.roll_tab = RollCallTab(self.notebook)

        self.notebook.add(self.home_tab.frame, text="主页")
        self.notebook.add(self.call_tab.frame, text="随机抽取")
        self.notebook.add(self.roll_tab.frame, text="随机点名")

    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=menu_bar)

        menus = {
            "文件": [
                ("选择样本文件 (Ctrl+O)", lambda: self.call_tab.load_names() if self.call_tab else None),
                ("从样本库加载 (Ctrl+Shift+O)", lambda: self.call_tab.load_from_library() if self.call_tab else None),
                ("重新加载当前文件 (Ctrl+R)", lambda: self.call_tab.reload_current_file() if self.call_tab else None),
                ("自动加载默认样本 (Ctrl+D)", lambda: self.call_tab.auto_load_file() if self.call_tab else None),
                ("-", None),
                ("导入样本到库 (Ctrl+I)", lambda: ApplicationFunctions.import_sample(self.root)),
                ("打开结果目录", self.open_result_dir),
                ("-", None),
                ("退出", self.quit_app),
            ],
            "编辑": [
                ("配置 (Ctrl+,)", self.open_config_window),
                ("-", None),
                ("抽取 (Ctrl+Enter)", lambda: self.call_tab.draw() if self.call_tab else None),
                ("保存结果 (Ctrl+S)", lambda: self.call_tab.save_current_result() if self.call_tab else None),
                ("批量保存所有 (Ctrl+Shift+S)", lambda: self.call_tab.batch_save_all() if self.call_tab else None),
                ("-", None),
                ("重置抽样历史 (Ctrl+Shift+R)", lambda: self.call_tab.reset_sampler_history() if self.call_tab else None),
            ],
            "工具": [
                ("随机抽取 (Ctrl+T)", lambda: self.notebook.select(self.call_tab.frame)),
                ("随机点名 (Ctrl+P)", lambda: self.notebook.select(self.roll_tab.frame)),
                ("-", None),
                ("检测更新", ApplicationFunctions.check_update),
                ("-", None),
                ("卸载", ApplicationFunctions.run_uninstall),
            ],
            "日志": [
                ("打开今日历史记录", FileManager.open_history_file),
                ("清除全部历史记录 (Ctrl+W)", lambda: self.call_tab.clear_all_history() if self.call_tab else None),
                ("-", None),
                ("查看日志 (Ctrl+L)", FileManager.open_log_file),
                ("清除日志", ApplicationFunctions.clear_log),
            ],
            "帮助": [
                ("使用说明", ApplicationFunctions.show_help),
                ("访问官网", ApplicationFunctions.open_website),
                ("关于", lambda: ApplicationFunctions.show_about(self.root)),
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

    def _bind_shortcuts(self):
        """绑定全局快捷键。"""
        ct = self.call_tab  # 简写引用

        self.root.bind("<Control-o>", lambda e: ct.load_names() if ct else None)
        self.root.bind("<Control-Shift-O>", lambda e: ct.load_from_library() if ct else None)
        self.root.bind("<Control-r>", lambda e: ct.reload_current_file() if ct else None)
        self.root.bind("<Control-d>", lambda e: ct.auto_load_file() if ct else None)
        self.root.bind("<Control-Return>", lambda e: ct.draw() if ct else None)
        self.root.bind("<Control-s>", lambda e: ct.save_current_result() if ct else None)
        self.root.bind("<Control-Shift-S>", lambda e: ct.batch_save_all() if ct else None)
        self.root.bind("<Control-w>", lambda e: ct.clear_all_history() if ct else None)
        self.root.bind("<Control-Shift-R>", lambda e: ct.reset_sampler_history() if ct else None)
        self.root.bind("<Control-comma>", lambda e: self.open_config_window())
        self.root.bind("<Control-i>", lambda e: ApplicationFunctions.import_sample(self.root))
        self.root.bind("<Control-t>", lambda e: self.notebook.select(ct.frame) if ct else None)
        self.root.bind("<Control-p>", lambda e: self.notebook.select(self.roll_tab.frame) if self.roll_tab else None)
        self.root.bind("<Control-l>", lambda e: FileManager.open_log_file())

    def open_config_window(self):
        """打开配置窗口"""
        rctlog.info("打开配置窗口")
        ConfigWindow(self.root)
    
    def open_result_dir(self):
        """打开结果目录"""
        FileManager.open_directory(FileManager.get_result_path())
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("退出程序", "确定要退出随机抽取工具吗？"):
            rctlog.info("用户确认退出程序")
            from core import tray
            t = tray.get()
            if t is not None and t.active:
                t.quit_app()
            else:
                self.root.destroy()

class ApplicationFunctions:
    """应用程序通用功能类"""

    @staticmethod
    def import_sample(parent=None, source_path=None):
        """导入样本到样本库

        source_path: 已选好的源文件路径；为空则弹出文件选择对话框
        """
        from tkinter import filedialog as fd
        if source_path:
            fp = source_path
        else:
            fp = fd.askopenfilename(
                title="选择要导入的名单文件",
                filetypes=[("样本文件", "*.txt;*.csv;*.rcp"),
                           ("文本文件", "*.txt"),
                           ("CSV 文件", "*.csv"),
                           ("RCP 文件", "*.rcp"),
                           ("所有文件", "*.*")])
            if not fp:
                return
        if len(SampleLibrary.get_samples()) >= 50:
            messagebox.showwarning("样本库已达上限",
                                   "样本库最多存放 50 个样本，请先删除部分样本后再导入。")
            return
        default_name = os.path.splitext(os.path.basename(fp))[0]
        name = ask_string(
            "导入样本",
            "请输入样本名称（将作为文件名，不含扩展名）：\n"
            "不能包含字符：\\ / : * ? \" < > |",
            initialvalue=default_name,
            parent=parent)
        if not name:
            return
        name = name.strip()
        try:
            _dest, notes = SampleLibrary.import_sample(fp, name)
            rctlog.info(f"样本已导入: {name}")
            msg = f"样本「{name}」已导入样本库。"
            if notes:
                msg += "\n\n" + "\n".join(notes)
                messagebox.showwarning("导入成功（已调整）", msg)
            else:
                messagebox.showinfo("导入成功", msg)
        except Exception as e:
            messagebox.showerror("导入失败", f"导入样本时出错：\n{e}")

    @staticmethod
    def open_website():
        """在浏览器中打开官网"""
        webbrowser.open(official_website)
        rctlog.info(f"已打开官网: {official_website}")

    @staticmethod
    def show_help():
        """打开在线帮助文档"""
        webbrowser.open("https://rct.danevan.top/docs/")
        rctlog.info("打开在线帮助文档")

    @staticmethod
    def run_uninstall():
        """卸载工具（菜单调用）"""
        rem_tool_path = os.path.join(work_path, "remove.exe")
        run_process(rem_tool_path)

    @staticmethod
    def check_update():
        """检测更新（菜单调用）— 启动 update.py --check"""
        from core.config import ConfigManager
        config = ConfigManager()
        source = config.get("update_source", "github")

        if not messagebox.askyesno(
            "检测更新",
            f"将从 {source.upper()} 检测新版本。\n\n"
            f"当前版本：v{rct_version}\n\n"
            f"是否打开更新程序？",
        ):
            return

        from core.update import run_auto_update
        success = run_auto_update(source=source, mode="--check")
        if not success:
            messagebox.showerror("启动失败", "无法启动更新程序，请手动前往官网下载最新版本。")

    @staticmethod
    def show_about(root):
        """显示关于信息"""
        info = load_about_info()
        AboutWindow(root, info, rct_icon_path)
    
    @staticmethod
    def clear_log():
        """清除日志（保留当天日志）"""
        if messagebox.askyesno("清除日志",
                               "确定要清除历史日志文件吗？\n\n今天的日志会保留。"):
            try:
                for file in os.listdir(rct_log_path):
                    if file == f"{rct_appname}-{strftime('%Y-%m-%d')}.log" or file == f"{strftime('%Y-%m-%d')}.log":
                        continue
                    if file.endswith('.log'):
                        os.remove(os.path.join(rct_log_path, file))
                rctlog.info("日志文件已清除")
                messagebox.showinfo("清除成功", "历史日志文件已清除。")
                return True
            except Exception as e:
                rctlog.error(f"清除日志失败: {e}")
                messagebox.showerror("清除失败", f"清除日志时出错：\n{e}")
                return False
