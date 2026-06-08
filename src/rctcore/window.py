"""
配置窗口模块 - 多选项卡配置界面
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from core.logman import rctlog
from rctcore.config import ConfigManager
from core.info import document_path, rct_rcplist_path
from rctcore.fileman import SampleLibrary
from core.utils import open_file_or_dir


class ConfigWindow:
    """软件内配置窗口（多选项卡）"""
    def __init__(self, parent):
        self.parent = parent
        self.config = ConfigManager()

        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("460x420+100+100")
        self.window.resizable(False, False)
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
            ("保存配置", self._save),
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
            value=self.config.get("rcp_merge_names", True))
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
        tk.Button(f3, text="确定", command=self._apply_default_sample,
                  width=5).pack(side="left", padx=2)

    def _apply_default_sample(self):
        """立即将下拉框选中的样本设为默认并刷新列表"""
        val = self.sample_combo.get()
        if val and val not in ("（无）", "（样本库为空）"):
            self.config.set("rcp_default_sample", val)
            rctlog.info(f"默认样本已立即应用: {val}")
        self._refresh_sample_list()

    def _refresh_sample_list(self):
        """刷新样本库下拉列表"""
        samples = SampleLibrary.get_samples()
        if samples:
            names = [s[0] for s in samples]
            self.sample_combo["values"] = names
            current = self.config.get("rcp_default_sample", "")
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
        canvas.create_window((0, 0), window=self._mgr_inner, anchor="nw")
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
            # 截断过长的文件名，留足按钮空间
            max_name_len = 22
            display_name = name if len(name) <= max_name_len else name[:max_name_len] + "..."

            label = tk.Label(row, text=f"{display_name}  ({size_str})",
                             anchor="w", font=("", 9), width=30)
            label.pack(side="left", padx=4)

            tk.Button(row, text="导出RCP", width=8,
                      command=lambda n=name: self._export_rcp(n)).pack(side="right", padx=1)
            tk.Button(row, text="导出TXT", width=8,
                      command=lambda n=name: self._export_txt(n)).pack(side="right", padx=1)
            tk.Button(row, text="重命名", width=6,
                      command=lambda n=name: self._rename_sample(n)).pack(side="right", padx=1)
            tk.Button(row, text="删除", width=5,
                      command=lambda n=name: self._delete_sample(n)).pack(side="right", padx=1)

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
                 text=f"版本: {rct_version} (vercode: {rct_vercode})\n"
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
        """立即检查更新（按钮回调）"""
        source = self.update_source_var.get()
        from rctcore.update import check_update, open_download_page

        # 显示等待提示
        self.window.config(cursor="watch")
        self.window.update()

        try:
            result = check_update(source=source)

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

        finally:
            self.window.config(cursor="")

    # ── 标签页 4：默认值 ────────────────────────────────

    def _create_defaults_tab(self, notebook):
        tab = self._make_tab(notebook, "默认值")
        pad = {"padx": 15}

        tk.Label(tab, text="这些值作为各输入框的默认显示值",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad, pady=(15, 4))

        defaults = [
            ("抽组默认总数：", "rcg_total_default", 9, 1, 26),
            ("抽组默认选数：", "rcg_choice_default", 3, 1, 26),
            ("抽人默认选数：", "rcp_choice_default", 1, 1, 50),
        ]

        self._default_vars = {}
        for label, key, default, mn, mx in defaults:
            row = tk.Frame(tab)
            row.pack(fill="x", **pad, pady=4)
            tk.Label(row, text=label, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.config.get(key, default)))
            self._default_vars[key] = var
            tk.Spinbox(row, textvariable=var, from_=mn, to=mx,
                       state="readonly", width=8).pack(side="left")

    # ── 保存 ──────────────────────────────────────────────

    def _save(self):
        try:
            updates = {
                "save_result": self.save_result_var.get(),
                "result_path": 1 if self.result_path_var.get() == "桌面" else 0,
                "auto_load_sample": self.auto_load_var.get(),
                "rcp_merge_names": self.merge_names_var.get(),
                "max_history_items": int(self.history_var.get()),
                "sampler_mode": self.sampler_mode_var.get(),
                "smart_window": int(self.smart_window_var.get()),
                "rcp_default_sample": self.sample_combo.get(),
                "update_source": self.update_source_var.get(),
                "auto_check_update": self.auto_check_var.get(),
            }
            # 防止保存占位文本
            if updates["rcp_default_sample"] in ("（无）", "（样本库为空）"):
                updates["rcp_default_sample"] = ""
            for key in ("rcg_total_default", "rcg_choice_default", "rcp_choice_default"):
                updates[key] = int(self._default_vars[key].get())

            for key, value in updates.items():
                self.config.set(key, value)

            rctlog.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()

        except Exception as e:
            rctlog.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
