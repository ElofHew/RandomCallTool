"""
配置窗口模块 - 多选项卡配置界面、关于窗口、使用说明窗口
"""
import os
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from core.logman import rctlog
from rctcore.config import ConfigManager
from core.info import rct_rcplist_path
from rctcore.fileman import SampleLibrary
from core.utils import open_file_or_dir


class ConfigWindow:
    """软件内配置窗口（多选项卡）"""
    def __init__(self, parent):
        self.parent = parent
        self.config = ConfigManager()

        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("460x520+100+100")
        self.window.resizable(True, True)
        self.window.minsize(460, 520)
        self.window.maxsize(800, 600)
        self.window.transient(parent)
        self.window.grab_set()

        self._create_widgets()

    def _make_tab(self, notebook, title):
        """创建标签页容器"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        return frame

    def _create_widgets(self):
        title_label = tk.Label(
            self.window,
            text="软件配置",
            font=("Helvetica", 16, "bold"),
            fg="blue",
        )
        title_label.pack(pady=(12, 5))

        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self._create_general_tab(notebook)
        self._create_sampling_tab(notebook)
        self._create_sample_mgr_tab(notebook)
        self._create_defaults_tab(notebook)
        self._create_update_tab(notebook)

        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)
        for text, cmd in [
            ("确定", self._ok),
            ("应用", self._apply),
            ("关闭", self.window.destroy),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, width=12, height=1
                      ).pack(side="left", padx=5)

    # ── 标签页 1：基本设置 ────────────────────────────────

    def _create_general_tab(self, notebook):
        tab = self._make_tab(notebook, "基本设置")
        pad = {"padx": 15, "pady": 4}

        # 自动保存结果
        self.save_result_var = tk.BooleanVar(
            value=self.config.get("save_result", True))
        tk.Checkbutton(tab, text="自动保存抽取结果",
                       variable=self.save_result_var).pack(anchor="w", **pad)

        # 结果保存位置
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad)
        tk.Label(f1, text="结果保存位置：", width=15, anchor="w").pack(side="left")
        self.result_path_var = tk.StringVar(
            value="桌面" if self.config.get("result_path", 0) == 1 else "数据目录")
        for v in ["数据目录", "桌面"]:
            tk.Radiobutton(f1, text=v, variable=self.result_path_var,
                           value=v).pack(side="left", padx=2)

        # 自动加载样本
        self.auto_load_var = tk.BooleanVar(
            value=self.config.get("auto_load_sample", True))
        tk.Checkbutton(tab, text="启动时自动加载默认样本",
                       variable=self.auto_load_var).pack(anchor="w", **pad)

        # 合并重复名字
        self.merge_names_var = tk.BooleanVar(
            value=self.config.get("rct_merge_names", True))
        tk.Checkbutton(tab, text="加载样本时自动合并重复名字",
                       variable=self.merge_names_var).pack(anchor="w", **pad)

        # 历史记录数量
        f2 = tk.Frame(tab)
        f2.pack(fill="x", **pad)
        tk.Label(f2, text="历史记录条数：", width=15, anchor="w").pack(side="left")
        self.history_var = tk.StringVar(
            value=str(self.config.get("max_history_items", 10)))
        tk.Spinbox(f2, textvariable=self.history_var, from_=5, to=30,
                   increment=5, state="readonly", width=8).pack(side="left")

    # ── 标签页 2：抽样设置 ────────────────────────────────

    def _create_sampling_tab(self, notebook):
        tab = self._make_tab(notebook, "抽样设置")
        pad = {"padx": 15}

        # 抽样模式
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="抽样模式：", width=15, anchor="w").pack(side="left")
        self.sampler_mode_var = tk.IntVar(
            value=self.config.get("sampler_mode", 0))
        for i, name in enumerate(["基本抽样", "智能抽样", "加权抽样"]):
            tk.Radiobutton(f1, text=name, variable=self.sampler_mode_var,
                           value=i).pack(side="left", padx=1)

        tk.Label(tab, text="基本: 纯随机 | 智能: 避免连续抽中 | 加权: 用户设置权重",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)

        # 智能窗口大小
        f2 = tk.Frame(tab)
        f2.pack(fill="x", **pad, pady=4)
        tk.Label(f2, text="智能记忆次数：", width=15, anchor="w").pack(side="left")
        self.smart_window_var = tk.StringVar(
            value=str(self.config.get("smart_window", 3)))
        tk.Spinbox(f2, textvariable=self.smart_window_var, from_=1, to=10,
                   increment=1, state="readonly", width=8).pack(side="left")
        tk.Label(f2, text="(智能模式下追踪的最近抽取次数)",
                 fg="gray", font=("", 9)).pack(side="left", padx=(5, 0))

        # 默认样本（从样本库选择）
        f3 = tk.Frame(tab)
        f3.pack(fill="x", **pad, pady=4)
        tk.Label(f3, text="默认样本：", width=15, anchor="w").pack(side="left")
        self.sample_combo = ttk.Combobox(f3, state="readonly", width=25)
        self.sample_combo.pack(side="left", padx=3)
        self._refresh_sample_list()
        if self.sample_combo.get():
            pass  # _refresh_sample_list 已设置值
        else:
            self.sample_combo.set("（无）")
    def _refresh_sample_list(self):
        """刷新样本库下拉列表"""
        samples = SampleLibrary.get_samples()
        if samples:
            names = [s[0] for s in samples]
            self.sample_combo["values"] = names
            current = self.config.get("rct_default_sample", "")
            if current in names:
                self.sample_combo.set(current)
            else:
                self.sample_combo.set(names[0])
        else:
            self.sample_combo["values"] = []
            self.sample_combo.set("（样本库为空）")

    # ── 标签页 3：样本管理 ────────────────────────────────

    def _create_sample_mgr_tab(self, notebook):
        tab = self._make_tab(notebook, "样本管理")
        pad = {"padx": 15}

        tk.Label(tab, text="已保存的样本（上限50个）",
                 font=("", 10, "bold")).pack(anchor="w", **pad, pady=(10, 2))
        tk.Label(tab, text="RCP / TXT 为导出样本的格式",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad, pady=(0, 2))

        btn_row = tk.Frame(tab)
        btn_row.pack(fill="x", **pad, pady=4)
        tk.Button(btn_row, text="导入样本", command=self._import_sample,
                  width=12).pack(side="left", padx=2)
        tk.Button(btn_row, text="打开样本目录",
                  command=lambda: open_file_or_dir(rct_rcplist_path),
                  width=12).pack(side="left", padx=2)

        # 可滚动列表
        list_frame = tk.Frame(tab)
        list_frame.pack(fill="both", expand=True, **pad, pady=4)

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        vbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self._mgr_inner = tk.Frame(canvas)

        self._mgr_inner.bind("<Configure>",
                             lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(self._mgr_win_id, width=e.width))
        self._mgr_win_id = canvas.create_window((0, 0), window=self._mgr_inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        self._mgr_canvas = canvas

        self._rebuild_mgr_list()

    def _rebuild_mgr_list(self):
        """重建样本管理列表"""
        for w in self._mgr_inner.winfo_children():
            w.destroy()

        samples = SampleLibrary.get_samples()
        if not samples:
            tk.Label(self._mgr_inner, text="样本库为空\n请点击「导入样本」添加",
                     fg="gray", font=("", 10)).pack(pady=20)
            return

        for name, fp in samples:
            row = tk.Frame(self._mgr_inner, relief="groove", bd=1)
            row.pack(fill="x", padx=3, pady=2)

            size_bytes = os.path.getsize(fp)
            size_str = f"{size_bytes}B"

            tk.Button(row, text="删除", width=5,
                      command=lambda n=name: self._delete_sample(n)).pack(side="right", padx=1)
            tk.Button(row, text="重命名", width=6,
                      command=lambda n=name: self._rename_sample(n)).pack(side="right", padx=1)
            tk.Button(row, text="TXT", width=5,
                      command=lambda n=name: self._export_txt(n)).pack(side="right", padx=1)
            tk.Button(row, text="RCP", width=5,
                      command=lambda n=name: self._export_rcp(n)).pack(side="right", padx=1)

            label = tk.Label(row, text=f"{name}  ({size_str})",
                             anchor="w", font=("", 9))
            label.pack(side="left", fill="x", expand=True, padx=4)

    def _import_sample(self):
        """导入样本"""
        fp = filedialog.askopenfilename(
            title="选择要导入的名单文件",
            filetypes=[("可用文件", "*.txt;*.csv;*.rcp"),
                       ("文本文件", "*.txt"),
                       ("CSV文件", "*.csv"),
                       ("编码文件", "*.rcp"),
                       ("所有文件", "*.*")])
        if not fp:
            return

        samples = SampleLibrary.get_samples()
        if len(samples) >= 50:
            messagebox.showwarning("警告", "样本库已达上限（50个），请删除一些后再导入")
            return

        name = simpledialog.askstring(
            "导入样本",
            "请输入样本名称（将作为文件名，不含扩展名）：\n"
            "不能包含字符: \\ / : * ? \" < > |",
            parent=self.window)
        if not name:
            return
        name = name.strip()

        try:
            SampleLibrary.import_sample(fp, name)
            rctlog.info(f"样本已导入: {name}")
            self._rebuild_mgr_list()
            self._refresh_sample_list()
            messagebox.showinfo("成功", f"样本「{name}」已导入")
        except Exception as e:
            messagebox.showerror("导入失败", str(e))

    def _export_rcp(self, name):
        """导出单个样本为 .rcp"""
        dest = filedialog.askdirectory(title=f"选择导出目录 - {name}.rcp")
        if not dest:
            return
        try:
            path = SampleLibrary.export_rcp(name, dest)
            messagebox.showinfo("成功", f"已导出:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _export_txt(self, name):
        """导出单个样本为 .txt"""
        dest = filedialog.askdirectory(title=f"选择导出目录 - {name}.txt")
        if not dest:
            return
        try:
            path = SampleLibrary.export_txt(name, dest)
            messagebox.showinfo("成功", f"已导出:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _rename_sample(self, old_name):
        """重命名样本"""
        new_name = simpledialog.askstring(
            "重命名样本", f"请输入新的名称（原名称: {old_name}）：",
            initialvalue=old_name, parent=self.window)
        if not new_name:
            return
        new_name = new_name.strip()
        if new_name == old_name:
            return
        try:
            SampleLibrary.rename_sample(old_name, new_name)
            self._rebuild_mgr_list()
            self._refresh_sample_list()
            messagebox.showinfo("成功", f"已重命名为: {new_name}")
        except Exception as e:
            messagebox.showerror("重命名失败", str(e))

    def _delete_sample(self, name):
        """删除样本"""
        if not messagebox.askyesno("确认删除", f"确定要删除样本「{name}」吗？"):
            return
        SampleLibrary.delete_sample(name)
        self._rebuild_mgr_list()
        self._refresh_sample_list()
        messagebox.showinfo("成功", f"样本「{name}」已删除")

    # ── 标签页 5：更新设置 ──────────────────────────────

    def _create_update_tab(self, notebook):
        tab = self._make_tab(notebook, "更新")
        pad = {"padx": 15}

        # 更新源选择
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="版本更新源：", width=15, anchor="w").pack(side="left")
        self.update_source_var = tk.StringVar(
            value=self.config.get("update_source", "github"))
        for val, label in [("github", "GitHub"), ("gitee", "Gitee")]:
            tk.Radiobutton(f1, text=label, variable=self.update_source_var,
                           value=val).pack(side="left", padx=3)

        tk.Label(tab, text="选择从哪个平台获取版本更新信息",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)
        
        tk.Label(tab, text="中国大陆建议使用Gitee，其他地区建议使用GitHub",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)

        # 自动检测更新
        f2 = tk.Frame(tab)
        f2.pack(fill="x", **pad, pady=4)
        self.auto_check_var = tk.BooleanVar(
            value=self.config.get("auto_check_update", True))
        tk.Checkbutton(tab, text="启动时自动检测更新",
                       variable=self.auto_check_var).pack(anchor="w", **pad)

        tk.Label(tab, text="启用后，每次启动程序会自动检查是否有新版本",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)

        # 分隔线
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=12)

        # 立即检查按钮 + 版本信息
        info_frame = tk.Frame(tab, relief="groove", bd=1)
        info_frame.pack(fill="x", padx=15, pady=5)

        from core.info import rct_version, rct_vercode, rct_date
        tk.Label(info_frame, text="当前版本信息",
                 font=("", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(info_frame,
                 text=f"版本: {rct_version} (版本码: {rct_vercode})\n"
                       f"日期: {rct_date}",
                 fg="gray", font=("", 9), justify="left"
                 ).pack(anchor="w", padx=10, pady=(0, 8))

        btn_frame = tk.Frame(tab)
        btn_frame.pack(fill="x", **pad, pady=10)
        tk.Button(btn_frame, text="立即检查更新",
                  command=self._check_update_now,
                  width=16, height=1,
                  bg="#4a90d9", fg="white",
                  activebackground="#357abd", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2",
                  ).pack()

    def _check_update_now(self):
        """立即检查更新（按钮回调，异步线程）"""
        source = self.update_source_var.get()
        from rctcore.update import check_update_async, open_download_page

        def _safe_callback(fn):
            """包装回调，先检查窗口是否仍存在"""
            def wrapper(*args, **kwargs):
                try:
                    if not self.window.winfo_exists():
                        return
                except tk.TclError:
                    return
                fn(*args, **kwargs)
            return wrapper

        def _on_success(result):
            self.window.config(cursor="")
            if not result["success"]:
                messagebox.showerror(
                    "检测失败",
                    f"无法获取版本信息\n\n原因: {result.get('error', '未知错误')}"
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
                    f"版本: v{result['local_version']}\n"
                    f"更新源: {result['source_name']}\n"
                    f"远程版本: v{result['remote_version']} ({result['remote_date']})"
                )

        def _on_error(err):
            self.window.config(cursor="")
            messagebox.showerror("检测失败", f"网络请求失败:\n{err}")

        # 显示等待光标，异步启动
        self.window.config(cursor="watch")
        check_update_async(
            self.window, source=source, timeout=10,
            on_success=_safe_callback(_on_success),
            on_error=_safe_callback(_on_error),
        )

    # ── 标签页 4：默认值 ────────────────────────────────

    def _create_defaults_tab(self, notebook):
        tab = self._make_tab(notebook, "默认值")
        pad = {"padx": 15}

        tk.Label(tab, text="这些值作为各输入框的默认显示值",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad, pady=(15, 4))

        defaults = [
            ("抽组默认总数：", "rct_group_total", 9, 1, 26),
            ("默认选取数量：", "rct_choice_default", 3, 1, 50),
        ]

        # 默认抽取方式
        mode_row = tk.Frame(tab)
        mode_row.pack(fill="x", **pad, pady=4)
        tk.Label(mode_row, text="默认抽取方式：", width=15, anchor="w").pack(side="left")
        self.default_mode_var = tk.StringVar(
            value=self.config.get("rct_default_mode", "person"))
        for val, label in [("person", "随机抽人"), ("group", "随机抽组")]:
            tk.Radiobutton(mode_row, text=label, variable=self.default_mode_var,
                           value=val).pack(side="left", padx=3)

        self._default_vars = {}
        for label, key, default, mn, mx in defaults:
            row = tk.Frame(tab)
            row.pack(fill="x", **pad, pady=4)
            tk.Label(row, text=label, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.config.get(key, default)))
            self._default_vars[key] = var
            tk.Spinbox(row, textvariable=var, from_=mn, to=mx,
                       state="readonly", width=8).pack(side="left")

    # ── 保存（纯逻辑，不涉及 UI 弹窗）──────────────

    def _collect_and_save(self):
        """收集所有配置项并写入配置文件
        Returns: True 成功 / False 失败
        """
        try:
            updates = {
                "save_result": self.save_result_var.get(),
                "result_path": 1 if self.result_path_var.get() == "桌面" else 0,
                "auto_load_sample": self.auto_load_var.get(),
                "rct_merge_names": self.merge_names_var.get(),
                "max_history_items": int(self.history_var.get()),
                "sampler_mode": self.sampler_mode_var.get(),
                "smart_window": int(self.smart_window_var.get()),
                "rct_default_sample": self.sample_combo.get(),
                "update_source": self.update_source_var.get(),
                "auto_check_update": self.auto_check_var.get(),
            }
            # 防止保存占位文本
            if updates["rct_default_sample"] in ("（无）", "（样本库为空）"):
                updates["rct_default_sample"] = ""
            updates["rct_default_mode"] = self.default_mode_var.get()
            for key in ("rct_group_total", "rct_choice_default"):
                updates[key] = int(self._default_vars[key].get())

            for key, value in updates.items():
                self.config.set(key, value)

            rctlog.info("配置已保存")
            return True

        except Exception as e:
            rctlog.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False

    # ── 按钮回调 ──────────────────────────────────────

    def _ok(self):
        """确定：应用更改并关闭窗口"""
        if self._collect_and_save():
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()

    def _apply(self):
        """应用：仅应用更改，不关闭窗口"""
        if self._collect_and_save():
            messagebox.showinfo("成功", "配置已应用")

    # ── 旧的 _save 方法保留兼容引用 ──────────────────
    def _save(self):
        """兼容旧调用（等同于确定）"""
        self._ok()


# ══════════════════════════════════════════════════════════
#  关于窗口
# ══════════════════════════════════════════════════════════

class AboutWindow:
    """美观的关于窗口"""

    def __init__(self, parent):
        from core.info import (
            rct_description, rct_version, rct_author, rct_date,
            enc_description, enc_version, enc_author, enc_date,
            github, gitee,
        )

        self.win = tk.Toplevel(parent)
        self.win.title("关于 随机抽取工具")
        self.win.geometry("460x380")
        self.win.minsize(420, 340)
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        # 窗口居中
        self.win.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_x(), parent.winfo_y()
        ww, wh = 460, 380
        x = px + (pw - ww) // 2
        y = py + (ph - wh) // 2
        self.win.geometry(f"{ww}x{wh}+{x}+{y}")

        main = tk.Frame(self.win, bg="#f0f4ff")
        main.pack(fill="both", expand=True)

        # ── 标题区 ──
        title_frame = tk.Frame(main, bg="#4a7db4", height=90)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame, text="随机抽取工具",
            font=("Microsoft YaHei", 20, "bold"),
            fg="white", bg="#4a7db4",
        ).pack(pady=(12, 0))
        tk.Label(
            title_frame, text=rct_description,
            font=("Microsoft YaHei", 9),
            fg="#d0e0ff", bg="#4a7db4", wraplength=400,
        ).pack(pady=(4, 0))

        # ── 信息区 ──
        info_frame = tk.Frame(main, bg="#f0f4ff", padx=30, pady=15)
        info_frame.pack(fill="both", expand=True)

        info_items = [
            ("主程序版本", f"v{rct_version}  ({rct_date})"),
            ("编码工具版本", f"v{enc_version}  ({enc_date})"),
            ("作者", rct_author),
        ]
        for i, (label, value) in enumerate(info_items):
            row = tk.Frame(info_frame, bg="#f0f4ff")
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label + "：", font=("", 9, "bold"),
                     width=14, anchor="e", bg="#f0f4ff").pack(side="left")
            tk.Label(row, text=value, font=("", 9),
                     anchor="w", bg="#f0f4ff", fg="#333").pack(side="left", padx=5)

        # ── 彩色按钮项目地址 ──
        link_frame = tk.Frame(info_frame, bg="#f0f4ff")
        link_frame.pack(fill="x", pady=(12, 0))

        tk.Label(link_frame, text="项目地址：", font=("", 9, "bold"),
                 bg="#f0f4ff").pack(anchor="w")

        btn_frame = tk.Frame(link_frame, bg="#f0f4ff")
        btn_frame.pack(fill="x", pady=(5, 0))

        for url, label, color in [
            (github, "  GitHub  ", "#2b5b84"),
            (gitee, "  Gitee  ", "#c71d23"),
        ]:
            btn = tk.Button(
                btn_frame, text=label,
                font=("", 9, "bold"),
                fg="white", bg=color,
                activebackground=color,
                activeforeground="white",
                relief="flat", bd=0, padx=12, pady=3,
                cursor="hand2",
                command=lambda u=url: webbrowser.open(u),
            )
            btn.pack(side="left", padx=(0, 10))
            # hover 效果
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=self._lighten(c)))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))

        # ── 底部关闭按钮 ──
        bottom_frame = tk.Frame(main, bg="#f0f4ff", height=40)
        bottom_frame.pack(fill="x")
        tk.Button(
            bottom_frame, text="关闭",
            font=("", 10), width=12,
            command=self.win.destroy,
            relief="groove", bd=1,
        ).pack(pady=5)

        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        rctlog.info("打开关于窗口")

    @staticmethod
    def _lighten(color):
        """简单颜色变浅"""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            r = min(255, r + 40)
            g = min(255, g + 40)
            b = min(255, b + 40)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color


# ══════════════════════════════════════════════════════════
#  使用说明窗口（支持翻页）
# ══════════════════════════════════════════════════════════

class HelpWindow:
    """可翻页的使用说明窗口"""

    # 每页内容（标题, [(文本, 是否加粗), ...]）
    PAGES = [
        # 第 1 页
        ("简介与主要功能", [
            ("一、主要功能", True), ("", False),
            ("1. 随机抽组", False),
            ("   从指定数量的组（数字或字母）中随机抽取一个或多个组。", False), ("", False),
            ("2. 随机抽人", False),
            ("   从样本文件（.rcp / .txt / .csv）或样本库中", False),
            ("   随机抽取指定数量的人名。", False), ("", False),
            ("3. 三档抽样模式", False),
            ("   · 基本抽样：random.sample 简单随机抽取", False),
            ("   · 智能抽样：追踪近期历史，自动降低刚被选中项的权重", False),
            ("   · 加权抽样：可单独设置权重，权重越高概率越大", False), ("", False),
            ("4. 样本库管理：常用名单导入样本库（上限 50 个）", False),
            ("5. 整合式操作界面：抽人与抽组一键切换", False),
            ("6. 历史记录面板：支持单条保存和批量保存", False),
            ("7. 配置管理：多选项卡配置窗口", False),
            ("8. 快捷键操作：Ctrl+Enter 抽取 / Ctrl+O 选择文件等", False),
        ]),
        # 第 2 页
        ("操作指南 — 随机抽组", [
            ("二、操作指南", True), ("", False),
            ("【随机抽组】", True), ("", False),
            ("1. 切换到「随机抽取」选项卡，选择「随机抽组」模式", False), ("", False),
            ("2. 选择分组方式：", False),
            ("   · 数字 (123)：组编号为 1, 2, 3 ...", False),
            ("   · 字母 (ABC)：组编号为 A, B, C ...", False), ("", False),
            ("3. 设置样本总数（1-26）", False), ("", False),
            ("4. 设置要抽取的组数（不能超过总组数）", False), ("", False),
            ("5. 点击「抽取」按钮或按 Ctrl+Enter 进行抽取", False), ("", False),
            ("6. 结果展示在程序窗口，可保存为 HTML 文件", False),
        ]),
        # 第 3 页
        ("操作指南 — 随机抽人", [
            ("【随机抽人】", True), ("", False),
            ("1. 切换到「随机抽取」选项卡，选择「随机抽人」模式", False), ("", False),
            ("2. 加载样本文件（支持 .rcp / .txt / .csv）：", False),
            ("   · Ctrl+O  → 手动选择文件", False),
            ("   · Ctrl+Shift+O → 从样本库加载", False),
            ("   · Ctrl+R  → 重新加载当前文件", False),
            ("   · Ctrl+D  → 自动加载默认样本", False), ("", False),
            ("3. 设置抽取数量", False), ("", False),
            ("4. 选择抽样模式（基本 / 智能 / 加权）", False), ("", False),
            ("5. 点击「抽取」按钮或按 Ctrl+Enter 进行抽取", False), ("", False),
            ("6. 结果展示在程序窗口，可保存为 HTML 文件", False),
        ]),
        # 第 4 页
        ("文件格式说明", [
            ("三、文件格式说明", True), ("", False),
            ("1. .rcp 文件（推荐）", False),
            ("   经过 Base64 编码的名单文件，", False),
            ("   使用配套的「名单编码工具」生成。", False), ("", False),
            ("2. .txt 文件", False),
            ("   纯文本文件，每行一个名字，", False),
            ("   也支持逗号、分号、制表符分隔。", False), ("", False),
            ("3. .csv 文件", False),
            ("   逗号分隔值文件。", False), ("", False),
            ("4. 重复名字处理：", False),
            ("   可在配置中开启「合并重复名字」功能，", False),
            ("   开启后自动去除重复项。", False),
        ]),
        # 第 5 页
        ("抽样模式与附加功能", [
            ("四、智能抽样功能", True), ("", False),
            ("1. 抽取前打乱：提高随机性，减少顺序影响", False),
            ("2. 加权抽样：根据历史抽取次数调整权重，实现长期公平", False),
            ("3. 可重置抽样历史：重新开始公平性计算", False), ("", False),
            ("五、其他功能", True), ("", False),
            ("1. 结果保存：抽取结果自动保存为 HTML 格式", False),
            ("2. 历史记录：记录最近的抽取历史，支持查看和保存", False),
            ("3. 配置管理：可设置保存路径、自动保存、默认值等", False),
            ("4. 日志查看：记录程序运行状态，支持查看和清理", False),
            ("5. 自动检测更新：启动时静默检测新版本", False),
            ("6. 快捷键操作：全程键盘可完成大部分操作", False),
        ]),
        # 第 6 页
        ("注意事项", [
            ("六、注意事项", True), ("", False),
            ("1. 支持重复名字自动去重（可在配置中关闭）", False),
            ("2. 抽取人数不能超过样本总数", False),
            ("3. 默认样本文件存放在 data/default.rcp", False),
            ("4. 结果文件默认保存在 data/result 或桌面", False),
            ("5. 支持跨平台运行（Windows / Linux / macOS）", False), ("", False), ("", False),
            ("如需更多帮助，请访问项目地址（关于界面）。", False),
        ]),
    ]

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("使用说明")
        self.win.geometry("450x610+60+60")
        self.win.minsize(450, 350)
        self.win.maxsize(800, 1000)
        self.win.resizable(True, True)
        self.win.transient(parent)
        self.win.grab_set()

        self.current_page = 0
        self.total_pages = len(self.PAGES)
        self._build_ui()
        self._show_page(0)

        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        rctlog.info("打开使用说明窗口")

    def _build_ui(self):
        """构建界面"""
        # ── 标题栏 ──
        title_frame = tk.Frame(self.win, bg="#4a7db4", height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame, text="使用说明",
            font=("Microsoft YaHei", 14, "bold"),
            fg="white", bg="#4a7db4",
        ).pack(expand=True)

        # ── 页面标题 ──
        self.page_title_label = tk.Label(
            self.win, text="",
            font=("Microsoft YaHei", 12, "bold"),
            fg="#2b5b84",
        )
        self.page_title_label.pack(pady=(10, 5))

        # ── 内容区（Text 组件 + 滚动条） ──
        content_frame = tk.Frame(self.win)
        content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        self.content_text = tk.Text(
            content_frame,
            font=("Microsoft YaHei", 10),
            wrap=tk.WORD,
            relief="flat",
            bg="#fafcff",
            padx=10, pady=10,
            state="disabled",
        )
        scrollbar = tk.Scrollbar(content_frame, command=self.content_text.yview)
        self.content_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.content_text.pack(side="left", fill="both", expand=True)

        # ── 底部导航栏 ──
        nav_frame = tk.Frame(self.win, bg="#e8ecf0", height=45)
        nav_frame.pack(fill="x", side="bottom")
        nav_frame.pack_propagate(False)

        self.prev_btn = tk.Button(
            nav_frame, text="◀ 上一页",
            font=("", 10), width=10,
            command=self._prev_page,
            relief="groove", bd=1,
        )
        self.prev_btn.pack(side="left", padx=(15, 5), pady=5)

        self.page_label = tk.Label(
            nav_frame, text="",
            font=("", 10), bg="#e8ecf0", fg="#555",
        )
        self.page_label.pack(side="left", expand=True)

        self.next_btn = tk.Button(
            nav_frame, text="下一页 ▶",
            font=("", 10), width=10,
            command=self._next_page,
            relief="groove", bd=1,
        )
        self.next_btn.pack(side="right", padx=(5, 15), pady=5)

        # ── 关闭按钮 ──
        tk.Button(
            nav_frame, text="关闭",
            font=("", 10), width=8,
            command=self.win.destroy,
            relief="groove", bd=1,
        ).pack(side="right", padx=(0, 5), pady=5)

    def _show_page(self, index):
        """显示指定页"""
        self.current_page = index
        title, lines = self.PAGES[index]
        self.page_title_label.config(text=title)

        # 更新内容
        self.content_text.config(state="normal")
        self.content_text.delete(1.0, tk.END)
        for text, is_bold in lines:
            self.content_text.insert(tk.END, text + "\n", "bold" if is_bold else "")
        self.content_text.config(state="disabled")
        self.content_text.see(1.0)

        # 更新页码 / 按钮状态
        self.page_label.config(text=f"第 {index + 1} 页，共 {self.total_pages} 页")
        self.prev_btn.config(state="normal" if index > 0 else "disabled")
        self.next_btn.config(state="normal" if index < self.total_pages - 1 else "disabled")

    def _prev_page(self):
        if self.current_page > 0:
            self._show_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self._show_page(self.current_page + 1)
