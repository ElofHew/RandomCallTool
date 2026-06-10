import tkinter as tk
from tkinter import ttk, messagebox
from core.logman import enclog
from core.info import enc_icon_path
from core.utils import set_window_icon


class ConfigWindow:
    def __init__(self, parent, config, app):
        self.parent = parent
        self.config = config
        self.app = app

        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("480x420+50+50")
        self.window.resizable(False, False)

        # 模态
        self.window.transient(parent)
        self.window.grab_set()
        set_window_icon(self.window, enc_icon_path)
        self._create_widgets()

    # ── 构建界面 ──────────────────────────────────────────────

    def _create_widgets(self):
        title_label = tk.Label(
            self.window,
            text="编码工具配置",
            font=("Helvetica", 16, "bold"),
            fg="blue"
        )
        title_label.pack(pady=(15, 5))

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self._create_general_tab()
        self._create_encode_tab()
        self._create_advanced_tab()

        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=15)

        for text, cmd in [
            ("保存配置", self._save),
            ("应用", self._apply),
            ("关闭", self.window.destroy),
        ]:
            tk.Button(btn_frame, text=text, command=cmd,
                      width=12, height=1).pack(side="left", padx=5)

    def _make_tab(self, title):
        """创建标签页容器"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=title)
        return frame

    # ── 标签页 1：基本设置 ────────────────────────────────────

    def _create_general_tab(self):
        tab = self._make_tab("基本设置")
        pad = {"padx": 15}

        # 输出路径
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="输出路径：", width=14, anchor="w").pack(side="left")
        self.path_var = tk.StringVar(
            value="桌面" if self.config.get("enc_output_path", 0) == 1
            else "数据目录"
        )
        tk.Radiobutton(f1, text="数据目录", variable=self.path_var,
                       value="数据目录").pack(side="left")
        tk.Radiobutton(f1, text="桌面", variable=self.path_var,
                       value="桌面").pack(side="left", padx=(15, 0))

        # 默认文件名
        f2 = tk.Frame(tab)
        f2.pack(fill="x", **pad, pady=4)
        tk.Label(f2, text="默认文件名：", width=14, anchor="w").pack(side="left")
        self.name_var = tk.StringVar(
            value=self.config.get("default_filename", "sample_list")
        )
        tk.Entry(f2, textvariable=self.name_var, width=22).pack(side="left")
        tk.Label(f2, text=".rcp").pack(side="left", padx=(3, 0))

        # 自动打开文件夹
        f3 = tk.Frame(tab)
        f3.pack(fill="x", **pad, pady=4)
        self.auto_open_var = tk.BooleanVar(
            value=self.config.get("auto_open_folder", True)
        )
        tk.Checkbutton(f3, text="编码保存后自动打开文件夹",
                       variable=self.auto_open_var).pack(anchor="w")

        self.show_dlg_var = tk.BooleanVar(
            value=self.config.get("show_success_dialog", True)
        )
        tk.Checkbutton(f3, text="编码保存后显示成功提示",
                       variable=self.show_dlg_var).pack(anchor="w")

        self.confirm_overwrite_var = tk.BooleanVar(
            value=self.config.get("confirm_overwrite", True)
        )
        tk.Checkbutton(f3, text="覆盖文件时询问确认",
                       variable=self.confirm_overwrite_var).pack(anchor="w")

    # ── 标签页 2：编码设置 ────────────────────────────────────

    def _create_encode_tab(self):
        tab = self._make_tab("编码设置")
        pad = {"padx": 15}

        # 编码方式
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="编码方式：", width=14, anchor="w").pack(side="left")
        self.enc_method_var = tk.StringVar(
            value=self.config.get("encoding_method", "base64")
        )
        for val, label in [("base64", "Base64"), ("hex", "Hex (十六进制)")]:
            tk.Radiobutton(f1, text=label, variable=self.enc_method_var,
                           value=val).pack(side="left", padx=(0, 15))

        # 文件编码
        f2 = tk.Frame(tab)
        f2.pack(fill="x", **pad, pady=4)
        tk.Label(f2, text="文件编码：", width=14, anchor="w").pack(side="left")
        self.file_enc_var = tk.StringVar(
            value=self.config.get("file_encoding", "utf-8")
        )
        enc_menu = ttk.Combobox(f2, textvariable=self.file_enc_var,
                                values=["utf-8", "gbk", "gb2312", "utf-16"],
                                state="readonly", width=12)
        enc_menu.pack(side="left")
        tk.Label(f2, text="读取/保存文本文件时使用",
                 fg="gray", font=("", 9)).pack(side="left", padx=(8, 0))

        # 分隔线
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=10)

        # 文本处理选项
        tk.Label(tab, text="文本处理选项", font=("", 10, "bold"),
                 anchor="w").pack(fill="x", padx=15, pady=(0, 2))

        self.remove_dup_var = tk.BooleanVar(
            value=self.config.get("remove_duplicates", True)
        )
        self.trim_space_var = tk.BooleanVar(
            value=self.config.get("trim_spaces", True)
        )
        self.sort_var = tk.BooleanVar(
            value=self.config.get("sort_names", False)
        )
        self.auto_clear_var = tk.BooleanVar(
            value=self.config.get("auto_clear_input", False)
        )

        opts = [
            ("自动去除重复项", self.remove_dup_var),
            ("自动去除首尾空格", self.trim_space_var),
            ("按字母排序（编码前）", self.sort_var),
            ("编码后自动清空输入", self.auto_clear_var),
        ]
        for text, var in opts:
            tk.Checkbutton(tab, text=text, variable=var).pack(anchor="w", **pad, pady=4)

    # ── 标签页 3：高级设置 ────────────────────────────────────

    def _create_advanced_tab(self):
        tab = self._make_tab("高级设置")
        pad = {"padx": 15}

        # 最近文件
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="最近文件数量：", width=14, anchor="w").pack(side="left")
        self.recent_var = tk.IntVar(
            value=self.config.get("max_recent_files", 10)
        )
        tk.Spinbox(f1, from_=1, to=50, width=6,
                   textvariable=self.recent_var).pack(side="left")
        tk.Label(f1, text="条", fg="gray").pack(side="left", padx=(3, 0))

        # 清空最近文件按钮
        tk.Button(
            tab, text="清空最近文件记录",
            command=self._clear_recent
        ).pack(anchor="w", **pad, pady=4)

        # 分隔线
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=10)

        # 关于配置
        info_frame = tk.Frame(tab, relief="groove", bd=1)
        info_frame.pack(fill="x", padx=15, pady=10)

        from core.info import enc_config_path as cfg_path_real
        tk.Label(info_frame, text="配置文件信息",
                 font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(info_frame,
                 text=f"配置文件路径:\n{cfg_path_real}",
                 fg="gray", font=("", 9), justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

    # ── 操作 ──────────────────────────────────────────────────

    def _collect_values(self):
        """收集所有配置值"""
        return {
            "enc_output_path": 1 if self.path_var.get() == "桌面" else 0,
            "default_filename": self.name_var.get().strip(),
            "auto_open_folder": self.auto_open_var.get(),
            "show_success_dialog": self.show_dlg_var.get(),
            "confirm_overwrite": self.confirm_overwrite_var.get(),
            "encoding_method": self.enc_method_var.get(),
            "file_encoding": self.file_enc_var.get(),
            "remove_duplicates": self.remove_dup_var.get(),
            "trim_spaces": self.trim_space_var.get(),
            "sort_names": self.sort_var.get(),
            "auto_clear_input": self.auto_clear_var.get(),
            "max_recent_files": self.recent_var.get(),
        }

    def _save(self):
        """保存配置"""
        try:
            items = self._collect_values()
            self.config.set_multi(items)

            # 单独更新主界面文件名
            self.app.filename_var.set(items["default_filename"])

            enclog.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")

        except Exception as e:
            enclog.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def _apply(self):
        """应用配置并关闭"""
        self._save()
        self.app.set_status("配置已应用")
        self.window.destroy()

    def _clear_recent(self):
        """清空最近文件记录"""
        self.config.set("recent_files", [])
        self.app._update_recent_menu()
        messagebox.showinfo("完成", "最近文件记录已清空")
