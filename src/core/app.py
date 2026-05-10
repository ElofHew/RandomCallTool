"""
应用程序主框架和主窗口管理
"""
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from .config import ConfigManager
from .file_utils import FileManager
from .gui import HomeTab, RandomGroupTab, RandomPersonTab, ConfigWindow, ApplicationFunctions

logger = logging.getLogger(__name__)


class MainApplication:
    def __init__(self, root):
        self.root = root
        self.group_tab = None
        self.person_tab = None
        self.create_tabs()
        self.create_menu()

    def create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.home_tab = HomeTab(self.notebook)
        self.group_tab = RandomGroupTab(self.notebook)
        self.person_tab = RandomPersonTab(self.notebook)

        self.notebook.add(self.home_tab.frame, text="主页")
        self.notebook.add(self.group_tab.frame, text="随机抽组")
        self.notebook.add(self.person_tab.frame, text="随机抽人")

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

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
        logger.info("打开配置窗口")
        ConfigWindow(self.root)

    def open_result_dir(self):
        FileManager.open_directory(FileManager.get_result_path())

    def quit_app(self):
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("用户确认退出程序")
            self.root.quit()