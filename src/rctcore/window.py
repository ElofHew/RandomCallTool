"""
UI 窗口布局模块 — 配置窗口、选项卡界面、高级抽取窗口
"""
import os
from time import strftime
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, filedialog, simpledialog
from core.logman import rctlog
from rctcore.config import ConfigManager
from core.info import rct_rcplist_path, rct_version, document_path
from rctcore.fileman import SampleLibrary, SaveResult, base64decode
from rctcore.sampler import SmartSampler
from core.utils import open_file_or_dir
from core.dialog import AboutWindow, load_about_info
from core.info import rct_icon_path
from core.utils import set_window_icon


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
        set_window_icon(self.window, rct_icon_path)
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

        # ── 默认样本 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        tk.Label(tab, text="默认加载样本",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", padx=15, pady=(2, 0))
        tk.Label(tab, text="启动时自动加载的样本库文件",
                 fg="gray", font=("", 8)).pack(anchor="w", padx=15, pady=(0, 2))

        f3 = tk.Frame(tab)
        f3.pack(fill="x", padx=15, pady=4)
        tk.Label(f3, text="默认样本：", width=15, anchor="w").pack(side="left")
        self.sample_combo = ttk.Combobox(f3, state="readonly", width=25)
        self.sample_combo.pack(side="left", padx=3)
        self._refresh_sample_list()
        if self.sample_combo.get():
            pass
        else:
            self.sample_combo.set("（无）")

    # ── 标签页 2：抽样设置 ────────────────────────────────

    def _create_sampling_tab(self, notebook):
        tab = self._make_tab(notebook, "抽样设置")
        pad = {"padx": 15}

        # ── 抽样模式 ──
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 4))
        tk.Label(f1, text="抽样模式：", width=15, anchor="w").pack(side="left")
        self.sampler_mode_var = tk.IntVar(
            value=self.config.get("sampler_mode", 1))
        for i, name in enumerate(["基本抽样", "智能抽样", "高级抽样"]):
            tk.Radiobutton(f1, text=name, variable=self.sampler_mode_var,
                           value=i).pack(side="left", padx=1)

        tk.Label(tab, text="基本: 纯随机 | 智能: 避免连续抽中+可自定义权重 | 高级: 完整高级配置",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)

        # 智能模式：使用固定权重
        self.smart_fixed_weights_var = tk.BooleanVar(
            value=self.config.get("smart_use_fixed_weights", False))
        tk.Checkbutton(tab, text="智能模式使用固定权重（勾选后可自定义权重）",
                       variable=self.smart_fixed_weights_var).pack(anchor="w", **pad)

        # ── 高级抽取入口 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        adv_btn_frame = tk.Frame(tab)
        adv_btn_frame.pack(fill="x", **pad, pady=2)
        tk.Label(adv_btn_frame, text="高级抽取配置：", width=15, anchor="w").pack(side="left")
        tk.Button(adv_btn_frame, text="打开高级抽取配置",
                  command=self._open_advanced_config,
                  bg="#4a90d9", fg="white",
                  activebackground="#357abd", activeforeground="white",
                  relief="flat", bd=0, padx=10, cursor="hand2",
                  width=18).pack(side="left", padx=5)
        tk.Label(tab, text="放回/不放回、抽取优化、加权等详细配置",
                 fg="gray", font=("", 8)).pack(anchor="w", **pad, pady=(0, 6))

        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=6)

        # ── 默认值 ──
        tk.Label(tab, text="默认值设定",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", **pad, pady=(2, 0))
        tk.Label(tab, text="以下值作为各输入框的默认显示值",
                 fg="gray", font=("", 8)).pack(anchor="w", **pad, pady=(0, 4))

        mode_row = tk.Frame(tab)
        mode_row.pack(fill="x", **pad, pady=4)
        tk.Label(mode_row, text="默认抽取方式：", width=15, anchor="w").pack(side="left")
        self.default_mode_var = tk.StringVar(
            value=self.config.get("rct_default_mode", "person"))
        for val, label in [("person", "抽人"), ("group", "抽组")]:
            tk.Radiobutton(mode_row, text=label, variable=self.default_mode_var,
                           value=val).pack(side="left", padx=3)

        self._default_vars = {}
        default_items = [
            ("抽组默认总数：", "rct_group_total", 9, 1, 26),
            ("默认选取数量：", "rct_choice_default", 3, 1, 50),
        ]
        for label, key, default, mn, mx in default_items:
            row = tk.Frame(tab)
            row.pack(fill="x", **pad, pady=4)
            tk.Label(row, text=label, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.config.get(key, default)))
            self._default_vars[key] = var
            tk.Spinbox(row, textvariable=var, from_=mn, to=mx,
                       state="readonly", width=8).pack(side="left")

    def _open_advanced_config(self):
        """从配置窗口打开高级抽取配置"""
        from rctcore.sampler import SmartSampler
        sampler = SmartSampler(mode=self.config.get("sampler_mode", 1),
                               smart_window=self.config.get("smart_window", 3))
        # 加载当前配置到临时 sampler
        adv_keys = [
            ("adv_with_replacement", "with_replacement"),
            ("adv_no_replace_method", "no_replace_method"),
            ("adv_no_replace_ratio", "no_replace_ratio"),
            ("adv_shuffle_before", "shuffle_before"),
            ("adv_shuffle_count", "shuffle_count"),
            ("adv_shuffle_frequency", "shuffle_frequency"),
            ("adv_pre_draw_balance", "pre_draw_balance"),
            ("adv_pre_draw_count", "pre_draw_count"),
            ("adv_pre_draw_frequency", "pre_draw_frequency"),
            ("adv_multi_draw_best", "multi_draw_best"),
            ("adv_multi_draw_count", "multi_draw_count"),
            ("adv_random_weights", "random_weights"),
            ("adv_random_weight_min", "random_weight_min"),
            ("adv_random_weight_max", "random_weight_max"),
            ("adv_progressive_draw", "progressive_draw"),
            ("adv_smart_reduce_weight", "smart_reduce_weight"),
            ("adv_smart_memory_count", "smart_memory_count"),
            ("adv_custom_weights", "custom_weights"),
        ]
        for cfg_key, adv_key in adv_keys:
            sampler.advanced_config[adv_key] = self.config.get(
                cfg_key, sampler.advanced_config[adv_key]
            )
        AdvancedConfigWindow(self.window, sampler)
        rctlog.info("从配置窗口打开高级抽取配置")

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

    # ── 标签页 4：更新设置 ──────────────────────────────

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

        # ── 下载源选择 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        f_dl = tk.Frame(tab)
        f_dl.pack(fill="x", **pad, pady=4)
        tk.Label(f_dl, text="下载源：", width=15, anchor="w").pack(side="left")
        self.download_source_var = tk.StringVar(
            value=self.config.get("download_source", "github"))
        for val, label in [
            ("github", "GitHub"),
            ("gitee", "Gitee"),
            ("lanzou", "蓝奏云"),
            ("official", "官网"),
        ]:
            tk.Radiobutton(f_dl, text=label, variable=self.download_source_var,
                           value=val).pack(side="left", padx=3)

        tk.Label(tab, text="检测到新版本时，点击下载将打开此平台页面",
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
        update_source = self.update_source_var.get()
        download_source = self.download_source_var.get()
        from rctcore.update import check_update_async, run_auto_update, open_download_page

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
                reply = messagebox.askyesnocancel(
                    "发现新版本",
                    f"发现新版本！\n\n"
                    f"当前版本: v{result['local_version']}\n"
                    f"最新版本: v{result['remote_version']} ({result['remote_date']})\n"
                    f"更新源: {result['source_name']}\n\n"
                    f"是否自动更新？\n"
                    f"「是」自动下载安装  |  「否」前往下载页面  |  「取消」稍后"
                )
                if reply is None:
                    return
                if reply:
                    success = run_auto_update(source=download_source)
                    if not success:
                        messagebox.showwarning("启动失败", "自动更新程序启动失败，将打开下载页面。")
                        open_download_page(download_source,
                                           lanzou_url=result.get("lanzou_download_url", ""),
                                           lanzou_password=result.get("lanzou_password", ""))
                else:
                    open_download_page(download_source,
                                       lanzou_url=result.get("lanzou_download_url", ""),
                                       lanzou_password=result.get("lanzou_password", ""))
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
            self.window, source=update_source, timeout=10,
            on_success=_safe_callback(_on_success),
            on_error=_safe_callback(_on_error),
        )

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
                "smart_use_fixed_weights": self.smart_fixed_weights_var.get(),
                "rct_default_sample": self.sample_combo.get(),
                "update_source": self.update_source_var.get(),
                "download_source": self.download_source_var.get(),
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
#  便捷引用 — 将公共对话框暴露在 rctcore.window 命名空间
#  实际实现在 core.dialog
# ══════════════════════════════════════════════════════════

def _get_rct_about_info():
    """读取 rctool 的关于信息"""
    return load_about_info("rct")


def _get_rct_about_window(parent):
    """打开 rctool 的关于窗口"""
    info = _get_rct_about_info()
    return AboutWindow(parent, info, rct_icon_path)

# ========================================
#  选项卡界面类 (原 tabs.py)
# ========================================

class BaseTab:
    """选项卡基类"""
    def __init__(self, parent, title):
        self.frame = ttk.Frame(parent)
        self.create_title(title)
        
    def create_title(self, title, font_size=18):
        """创建标题"""
        title_label = tk.Label(
            self.frame, 
            text=title, 
            font=("Arial", font_size, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)
        return title_label
    
    def create_button(self, parent, text, command, width=15, height=2, font_size=10, **kwargs):
        """创建标准按钮"""
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", font_size),
            width=width,
            height=height,
            **kwargs
        )
        return button
    
    def create_history_frame(self, height=5):
        """创建历史记录框架"""
        history_frame = tk.LabelFrame(self.frame, text="历史记录")
        history_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.history_listbox = tk.Listbox(
            history_frame,
            height=height,
            selectmode=tk.SINGLE
        )
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        
        self.history = []
        return history_frame
    
    def add_history(self, item):
        """添加历史记录"""
        self.history.insert(0, item)
        self.history_listbox.insert(0, item)
        
        max_history = ConfigManager().get("max_history_items", 10)
        if len(self.history) > max_history:
            self.history = self.history[:max_history]
            self.history_listbox.delete(max_history, tk.END)
    
    def add_save_message(self):
        """添加保存提示信息"""
        save_message_frame = tk.Frame(self.frame)
        save_message_frame.pack(pady=5)
        tk.Label(save_message_frame, text="保存提示：").pack(side="left")
        self.save_message_entry = tk.Entry(save_message_frame, width=30)
        self.save_message_entry.pack(side="left", padx=5)
        self.save_message_entry.insert(0, "")
        self.save_message_entry.config(state="normal")

    def create_result_label(self, wraplength=350):
        """创建结果标签"""
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(
            self.frame, 
            font=bold_font, 
            text="",
            wraplength=wraplength, 
            justify="center"
        )
        self.result_label.pack(pady=(5, 10), padx=10, fill="x")
        return self.result_label
    
    def clear_result(self):
        """清空结果"""
        if hasattr(self, 'result_label'):
            self.result_label.config(text="")
        rctlog.info(f"[{self.__class__.__name__}] 清空结果")

class HomeTab(BaseTab):
    """首页选项卡"""
    def __init__(self, parent):
        super().__init__(parent, "随机抽取工具")
        self.create_widgets()

    def create_widgets(self):
        version_label = tk.Label(
            self.frame,
            text=f"当前版本：{rct_version}",
            font=("Helvetica", 12),
            fg="purple"
        )
        version_label.pack(pady=5)

        button_configs = [
            ("随机抽取", self.open_random_call),
            ("软件配置", self.open_config_window),
            ("关于应用", self.show_about),
            ("退出程序", self.quit_program)
        ]

        for text, command in button_configs:
            button = self.create_button(self.frame, text, command)
            button.pack(pady=5)

        start_time = strftime("%Y-%m-%d %H:%M:%S")
        start_label = tk.Label(
            self.frame,
            text=f"启动时间：{start_time}",
            font=("Helvetica", 12),
            fg="gray"
        )
        start_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=5)
    
    def open_random_call(self):
        """打开随机抽取界面"""
        rctlog.info("打开随机抽取界面")
        notebook = self.frame.master
        if hasattr(notebook, "select"):
            notebook.select(1)

    def open_config_window(self):
        """打开配置窗口"""
        rctlog.info("打开配置窗口")
        ConfigWindow(self.frame)

    def show_about(self):
        """显示关于信息"""
        rctlog.info("打开关于窗口")
        info = load_about_info("rct")
        AboutWindow(self.frame.winfo_toplevel(), info, rct_icon_path)

    def quit_program(self):
        """退出程序"""
        rctlog.info("程序正常退出")
        self.frame.winfo_toplevel().destroy()

class RandomCallTab(BaseTab):
    """整合的随机抽取选项卡 — 支持随机抽人/随机抽组切换"""

    def __init__(self, parent):
        super().__init__(parent, "随机抽取")
        config = ConfigManager()
        self.mode_var = tk.StringVar(value=config.get("rct_default_mode", "person"))
        self.mode_var.trace_add("write", self._on_mode_changed)

        sampler_mode = config.get("sampler_mode", 0)
        smart_window = config.get("smart_window", 3)
        self.sampler = SmartSampler(mode=sampler_mode, smart_window=smart_window)

        # 加载智能模式固定权重设置
        self.sampler.use_fixed_weights = config.get("smart_use_fixed_weights", False)

        # 加载高级抽取配置
        adv_keys = [
            ("adv_with_replacement", "with_replacement"),
            ("adv_no_replace_method", "no_replace_method"),
            ("adv_no_replace_ratio", "no_replace_ratio"),
            ("adv_shuffle_before", "shuffle_before"),
            ("adv_shuffle_count", "shuffle_count"),
            ("adv_shuffle_frequency", "shuffle_frequency"),
            ("adv_pre_draw_balance", "pre_draw_balance"),
            ("adv_pre_draw_count", "pre_draw_count"),
            ("adv_pre_draw_frequency", "pre_draw_frequency"),
            ("adv_multi_draw_best", "multi_draw_best"),
            ("adv_multi_draw_count", "multi_draw_count"),
            ("adv_random_weights", "random_weights"),
            ("adv_random_weight_min", "random_weight_min"),
            ("adv_random_weight_max", "random_weight_max"),
            ("adv_progressive_draw", "progressive_draw"),
            ("adv_smart_reduce_weight", "smart_reduce_weight"),
            ("adv_smart_memory_count", "smart_memory_count"),
            ("adv_custom_weights", "custom_weights"),
        ]
        for cfg_key, adv_key in adv_keys:
            self.sampler.advanced_config[adv_key] = config.get(
                cfg_key, self.sampler.advanced_config[adv_key]
            )

        # 抽人状态
        self.names = []
        self.current_file = None
        self.auto_file = ""

        # 抽组状态
        self.group_order_var = tk.StringVar(value="123")

        # 历史记录
        self.history = []
        self._history_id_counter = 0

        self._create_widgets()
        self._auto_load_sample()

    # ══════════════════════════════════════════════════════════
    #  界面构建
    # ══════════════════════════════════════════════════════════

    def _create_widgets(self):
        """构建整合界面"""
        # ── 模式切换 ──
        mode_frame = tk.Frame(self.frame)
        mode_frame.pack(pady=(5, 0))
        tk.Label(mode_frame, text="抽取模式：", font=("", 10)).pack(side="left", padx=5)
        for text, val in [("抽人", "person"), ("抽组", "group")]:
            tk.Radiobutton(
                mode_frame, text=text, variable=self.mode_var, value=val,
                command=self._switch_mode,
            ).pack(side="left", padx=5)

        # ── 主体（左控制区 + 右历史区） ──
        main_frame = tk.Frame(self.frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.control_frame = tk.Frame(main_frame)
        self.control_frame.pack(side="left", fill="both", expand=True)

        # ----- 抽人控件（LabelFrame，固定最小高度）-----
        self.person_frame = tk.LabelFrame(self.control_frame, text="样本列表", height=130)
        self.person_frame.pack_propagate(False)
        self.file_path_label = tk.Label(
            self.person_frame, text="未选择文件", fg="gray", wraplength=250,
        )
        self.file_path_label.pack(pady=5, padx=5)

        btn_row = tk.Frame(self.person_frame)
        btn_row.pack(pady=5)
        for text, cmd in [
            ("选择文件", self.load_names),
            ("从样本库", self.load_from_library),
            ("重新加载", self.reload_current_file),
            ("自动加载", self.auto_load_file),
        ]:
            self.create_button(btn_row, text, cmd, width=9, height=1).pack(side="left", padx=2)

        self.sample_count_label = tk.Label(
            self.person_frame, text="样本数量: 0", fg="green",
        )
        self.sample_count_label.pack(pady=(0, 5))

        # ----- 抽组控件（LabelFrame，固定最小高度）-----
        self.group_frame = tk.LabelFrame(self.control_frame, text="抽组设置", height=130)
        self.group_frame.pack_propagate(False)

        order_row = tk.Frame(self.group_frame)
        order_row.pack(pady=5)
        tk.Label(order_row, text="分组方式：").pack(side="left")
        for text, val in [("123(数字)", "123"), ("ABC(字母)", "ABC")]:
            tk.Radiobutton(
                order_row, text=text, variable=self.group_order_var, value=val,
            ).pack(side="left", padx=5)

        config = ConfigManager()
        rcg_total = config.get("rct_group_total", 9)
        rcg_total = rcg_total if 0 < rcg_total <= 26 else 9

        row = tk.Frame(self.group_frame)
        row.pack(pady=5)
        tk.Label(row, text="样本总数：", width=10).pack(side="left")
        self.total_entry = ttk.Combobox(row, values=list(range(1, 27)), width=5, state="readonly")
        self.total_entry.pack(side="left")
        self.total_entry.set(str(rcg_total))

        self.total_entry.bind("<<ComboboxSelected>>", self._on_total_change)

        # ----- 右侧历史记录 -----
        self._create_history_area(main_frame)

        # ----- 操作（紧挨控制区下方）-----
        self.action_frame = tk.LabelFrame(self.control_frame, text="操作")

        inner_top = tk.Frame(self.action_frame)
        inner_top.pack(fill="x", padx=8, pady=(6, 2))

        tk.Label(inner_top, text="抽取数量：").pack(side="left")
        self.choice_entry = ttk.Combobox(
            inner_top, values=list(range(1, 11)), width=5, state="readonly",
        )
        self.choice_entry.pack(side="left", padx=5)
        self.choice_entry.set(str(config.get("rct_choice_default", 1)))

        tk.Label(inner_top, text="抽样模式：").pack(side="left", padx=(10, 0))
        self.sampler_mode_var = tk.IntVar(value=config.get("sampler_mode", 0))
        self.sampler_mode_combo = ttk.Combobox(
            inner_top,
            values=["基本抽样", "智能抽样", "高级抽样"],
            state="readonly", width=12,
        )
        self.sampler_mode_combo.pack(side="left", padx=5)
        self.sampler_mode_combo.set(SmartSampler.MODE_NAMES[self.sampler_mode_var.get()])
        self.sampler_mode_combo.bind("<<ComboboxSelected>>", self._on_sampler_mode_change)

        # 根据当前模式初始化按钮文字/状态
        init_mode = self.sampler_mode_var.get()
        if init_mode == SmartSampler.MODE_BASIC:
            btn_text, btn_state = "权重", "disabled"
        elif init_mode == SmartSampler.MODE_SMART:
            btn_text, btn_state = "权重", "normal"
        else:
            btn_text, btn_state = "高级", "normal"

        self.weight_btn = tk.Button(
            inner_top, text=btn_text, command=self._open_weight_config,
            state=btn_state, width=5,
        )
        self.weight_btn.pack(side="left")

        inner_btns = tk.Frame(self.action_frame)
        inner_btns.pack(fill="x", padx=8, pady=(2, 6))
        actions = [
            ("抽取", self.draw),
            ("保存当前结果", self.save_current_result),
            ("清空历史记录", self.clear_all_history),
            ("重置抽样历史", self.reset_sampler_history),
        ]
        for i, (text, cmd) in enumerate(actions):
            btn = self.create_button(inner_btns, text, cmd, width=11, height=1)
            btn.grid(row=i // 2, column=i % 2, padx=4, pady=2)
        inner_btns.grid_columnconfigure(0, weight=1)
        inner_btns.grid_columnconfigure(1, weight=1)

        # 初始模式
        self._switch_mode()

    def _create_history_area(self, parent):
        """创建右侧历史记录面板"""
        hist_frame = tk.LabelFrame(parent, text="历史记录", width=160)
        hist_frame.pack(side="right", fill="y", padx=(10, 0))
        hist_frame.pack_propagate(False)

        canvas = tk.Canvas(hist_frame, highlightthickness=0, width=140)
        vbar = tk.Scrollbar(hist_frame, orient="vertical", command=canvas.yview)
        self.history_inner = tk.Frame(canvas)

        self.history_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.history_inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        self._history_canvas = canvas

        tk.Button(hist_frame, text="批量保存所有", command=self.batch_save_all, width=20).pack(pady=5)

    # ══════════════════════════════════════════════════════════
    #  模式切换
    # ══════════════════════════════════════════════════════════

    def _on_mode_changed(self, *_):
        """mode_var 变化时触发"""
        self._switch_mode()

    def _switch_mode(self):
        """切换抽人/抽组控件显示"""
        # 先隐藏所有模式相关控件
        for f in (self.person_frame, self.group_frame, self.action_frame):
            f.pack_forget()

        # 切换模式时重置不放回抽取池
        self.sampler.reset_no_replace_pool()

        mode = self.mode_var.get()
        if mode == "person":
            self.person_frame.pack(fill="x", pady=5)
            self.action_frame.pack(fill="x", pady=5)
            # 恢复抽取数量范围为样本数量
            if self.names:
                self.choice_entry["values"] = list(range(1, len(self.names) + 1))
                cur = self.choice_entry.get()
                if cur and int(cur) > len(self.names):
                    self.choice_entry.set("1")
            else:
                self.choice_entry["values"] = list(range(1, 11))
        else:
            self.group_frame.pack(fill="x", pady=5)
            self.action_frame.pack(fill="x", pady=5)
            # 恢复抽取数量范围为组选取数量
            try:
                total = int(self.total_entry.get())
                self.choice_entry["values"] = list(range(1, min(total + 1, 27)))
                default_k = ConfigManager().get("rct_choice_default", 3)
                self.choice_entry.set(str(min(default_k, total)))
            except ValueError:
                pass

    def _on_total_change(self, event):
        """组总数变化时更新操作框的选取数量"""
        try:
            total = int(self.total_entry.get())
            if total > 0:
                mx = min(total, 26)
                if self.mode_var.get() == "group":
                    self.choice_entry["values"] = list(range(1, mx + 1))
                    cur = self.choice_entry.get()
                    if cur and int(cur) > mx:
                        self.choice_entry.set(str(min(3, mx)))
        except ValueError:
            pass

    # ══════════════════════════════════════════════════════════
    #  抽样模式
    # ══════════════════════════════════════════════════════════

    def _on_sampler_mode_change(self, event):
        """抽样模式切换"""
        idx = self.sampler_mode_combo.current()
        self.sampler_mode_var.set(idx)
        self.sampler.set_mode(idx)
        # 更新按钮状态和文字
        if idx == SmartSampler.MODE_BASIC:
            self.weight_btn.config(state="disabled", text="权重")
        elif idx == SmartSampler.MODE_SMART:
            self.weight_btn.config(state="normal", text="权重")
        else:  # MODE_ADVANCED
            self.weight_btn.config(state="normal", text="高级")
        rctlog.info(f"抽样模式切换为: {SmartSampler.MODE_NAMES[idx]}")

    def _open_weight_config(self):
        """打开权重设置窗口 或 高级抽取配置窗口"""
        mode = self.sampler_mode_var.get()

        if mode == SmartSampler.MODE_ADVANCED:
            # 高级模式：打开高级抽取配置窗口
            self._open_advanced_config()
            return

        # 智能模式：权重设置窗口
        self._open_weight_config_dialog()

    def _open_weight_config_dialog(self):
        """纯权重编辑窗口（不自检模式，供高级窗口回调使用）"""
        if self.mode_var.get() == "person":
            items = self.names if self.names else []
        else:
            try:
                total = int(self.total_entry.get())
                items = (
                    list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:total]
                    if self.group_order_var.get() == "ABC"
                    else list(range(1, total + 1))
                )
            except (ValueError, AttributeError):
                messagebox.showwarning("警告", "请先设置组参数")
                return

        if not items:
            messagebox.showwarning("警告", "当前无可用样本")
            return

        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title("权重设置")
        win.geometry("420x480+100+100")
        win.transient(self.frame.winfo_toplevel())
        win.grab_set()
        win.minsize(300, 300)

        top_frame = tk.Frame(win)
        top_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(top_frame, text="为每个样本设置权重（≥0，默认 1.0）",
                 font=("", 10, "bold"), fg="blue").pack(anchor="w")
        tk.Label(top_frame, text="权重越高，被抽中的概率越大",
                 font=("", 9), fg="gray").pack(anchor="w")

        # "使用固定权重" 勾选项
        use_fixed_var = tk.BooleanVar(value=self.sampler.use_fixed_weights)
        fixed_cb = tk.Checkbutton(
            top_frame, text="使用固定权重（勾选后可修改，不勾选仅查看智能权重）",
            variable=use_fixed_var,
            command=lambda: self._toggle_weight_entries(weight_entries, use_fixed_var),
            font=("", 9),
        )
        fixed_cb.pack(anchor="w", pady=(5, 5))

        # 可滚动区域
        body_frame = tk.Frame(win)
        body_frame.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = tk.Canvas(body_frame, highlightthickness=0, bg="#fafafa")
        vbar = tk.Scrollbar(body_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)

        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _configure_inner(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _configure_canvas(event):
            canvas.itemconfig(inner_id, width=event.width)

        inner.bind("<Configure>", _configure_inner)
        canvas.bind("<Configure>", _configure_canvas)
        canvas.configure(yscrollcommand=vbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()))

        # 为每个项目创建权重输入框
        weight_vars = {}
        weight_entries = {}  # 存储 Entry widget 引用
        for item in items:
            row = tk.Frame(inner)
            row.pack(fill="x", pady=2, padx=5)
            label_text = str(item) + ("组" if self.mode_var.get() == "group" and isinstance(item, int) else "")
            tk.Label(row, text=label_text, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.sampler.get_weight(item)))
            entry = tk.Entry(row, textvariable=var, width=10)
            entry.pack(side="left", padx=5)
            weight_vars[item] = var
            weight_entries[item] = entry
            # 显示智能有效权重
            smart_w = self.sampler.get_smart_effective_weight(item)
            tk.Label(row, text=f"(智能: {smart_w:.1f}  |  固定: {self.sampler.get_weight(item):.1f})",
                     fg="gray", font=("", 8)).pack(side="left")

        # 根据 use_fixed_weights 设置输入框初始状态
        self._toggle_weight_entries(weight_entries, use_fixed_var)

        def save_weights():
            self.sampler.use_fixed_weights = use_fixed_var.get()
            for item, var in weight_vars.items():
                try:
                    w = float(var.get().strip())
                    self.sampler.set_weight(item, w)
                except ValueError:
                    messagebox.showwarning("无效输入", f"'{item}' 的权重值无效，已跳过")
                    continue
            rctlog.info(f"权重已更新 ({len(weight_vars)} 项), 固定权重={self.sampler.use_fixed_weights}")
            messagebox.showinfo("成功", "权重已保存")
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(btn_frame, text="应用", command=save_weights, width=12).pack(side="left", padx=3)
        tk.Button(btn_frame, text="重置",
                  command=lambda: [var.set("1.0") for var in weight_vars.values()],
                  width=15).pack(side="left", padx=3)
        tk.Button(btn_frame, text="取消",
                  command=lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()),
                  width=8).pack(side="left", padx=3)

    @staticmethod
    def _toggle_weight_entries(weight_entries, use_fixed_var):
        """切换权重输入框的可编辑状态"""
        state = "normal" if use_fixed_var.get() else "readonly"
        for entry in weight_entries.values():
            entry.config(state=state)

    def _open_advanced_config(self):
        """打开高级抽取配置窗口"""
        AdvancedConfigWindow(
            self.frame.winfo_toplevel(),
            self.sampler,
            on_apply=self._on_advanced_config_applied,
            on_open_weights=self._open_weight_config_dialog,
        )

    def _on_advanced_config_applied(self):
        """高级配置应用后的回调"""
        rctlog.info("高级抽取配置已应用")

    # ══════════════════════════════════════════════════════════
    #  自动加载样本（抽人）
    # ══════════════════════════════════════════════════════════

    def _auto_load_sample(self):
        """自动加载默认样本（从样本库）"""
        config = ConfigManager()
        if not config.get("auto_load_sample", True):
            return
        default_name = config.get("rct_default_sample", "")
        if not default_name:
            return
        names = SampleLibrary.load_names(default_name)
        if names:
            self.names = names
            self.sampler.reset_no_replace_pool()
            self.current_file = os.path.join(rct_rcplist_path, f"{default_name}.rcp")
            self.file_path_label.config(text=f"样本库: {default_name}", fg="purple")
            self.sample_count_label.config(text=f"样本数量: {len(names)}", fg="green")
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 自动加载样本库: {default_name}, 共 {len(names)} 个名字")

    # ══════════════════════════════════════════════════════════
    #  文件加载（抽人）
    # ══════════════════════════════════════════════════════════

    def _load_names_from_file(self, file_path=None):
        """从文件加载名字，返回 (names, additional_messages)"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("可用文件", "*.rcp;*.txt;*.csv"),
                    ("名单文件", "*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*"),
                ],
                initialdir=document_path,
                title="选择样本文件",
            )
            rctlog.info(f"[随机抽取] 选择文件: {file_path or '(取消选择)'}")

        if not file_path:
            return [], []

        extra = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if file_path.endswith(".rcp"):
                content = self._decode_rcp(content)

            names = []
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                for sep in [",", ";", "\t"]:
                    if sep in line:
                        names.extend(n.strip() for n in line.split(sep) if n.strip())
                        break
                else:
                    names.append(line)

            config = ConfigManager()
            if config.get("rct_merge_names", True):
                if len(names) != len(set(names)):
                    names = list(set(names))
                    extra.append("文件中存在重复的名字，已自动去除")
            else:
                if len(names) != len(set(names)):
                    extra.append("文件中存在重复的名字，已保留")

            if not names:
                messagebox.showwarning("警告", "文件中没有有效的数据")
                return [], extra

            self.file_path_label.config(
                text="默认样本" if file_path == self.auto_file else os.path.basename(file_path),
                fg="purple",
            )
            self.sample_count_label.config(text=f"样本数量: {len(names)}", fg="green")

            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            self.current_file = file_path

            rctlog.info(f"[随机抽取] 成功加载 {len(names)} 个名字")
            return names, extra

        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    lines = [line.strip() for line in f if line.strip()]
                if lines:
                    self.file_path_label.config(text=os.path.basename(file_path), fg="purple")
                    self.sample_count_label.config(text=f"样本数量: {len(lines)}", fg="green")
                    mx = len(lines)
                    self.choice_entry["values"] = list(range(1, mx + 1))
                    self.current_file = file_path
                    return lines, extra
            except Exception as e:
                rctlog.error(f"[随机抽取] 读取文件失败: {e}")
                messagebox.showerror("错误", f"读取文件失败: {e}")
                return [], extra
        except Exception as e:
            rctlog.error(f"[随机抽取] 读取文件失败: {e}")
            messagebox.showerror("错误", f"读取文件失败: {e}")
            return [], extra

    def _decode_rcp(self, data):
        """解码 RCP 编码内容"""
        data = data.strip()
        return base64decode(data + "\n") if data else ""

    def load_names(self):
        """手动选择文件加载"""
        names, extra = self._load_names_from_file()
        if names:
            self.names = names
            self.sampler.reset_no_replace_pool()
            msg = f"共加载 {len(names)} 个名字"
            if extra:
                msg += "\n" + "\n".join(extra)
            messagebox.showinfo("成功", msg)

    def reload_current_file(self):
        """重新加载当前文件"""
        if self.current_file and os.path.exists(self.current_file):
            names, extra = self._load_names_from_file(self.current_file)
            if names:
                self.names = names
                self.sampler.reset_no_replace_pool()
                msg = f"重新加载成功\n共 {len(names)} 个名字"
                if extra:
                    msg += "\n" + "\n".join(extra)
                messagebox.showinfo("成功", msg)

    def load_from_library(self):
        """从样本库选择样本加载"""
        samples = SampleLibrary.get_samples()
        if not samples:
            messagebox.showwarning("警告", "样本库为空，请先导入样本")
            return
        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title("选择样本")
        win.geometry("380x420+150+150")
        win.transient(self.frame.winfo_toplevel())
        win.grab_set()
        win.minsize(300, 250)

        tk.Label(win, text="请选择要加载的样本：",
                 font=("", 11, "bold")).pack(pady=(10, 5))

        body = tk.Frame(win)
        body.pack(fill="both", expand=True, padx=10, pady=5)
        canvas = tk.Canvas(body, highlightthickness=0)
        vbar = tk.Scrollbar(body, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        for name, fp in samples:
            size = os.path.getsize(fp)
            card = tk.Frame(inner, relief="raised", bd=2, bg="#f5f5f5")
            card.pack(fill="x", padx=5, pady=3)

            name_label = tk.Label(card, text=name, font=("", 10, "bold"),
                                  bg="#f5f5f5", anchor="w")
            name_label.pack(fill="x", padx=6, pady=(4, 0))

            count = len(SampleLibrary.load_names(name))
            info_label = tk.Label(card, text=f"{count} 个名字 | {size}B",
                                  font=("", 8), fg="gray", bg="#f5f5f5", anchor="w")
            info_label.pack(fill="x", padx=6, pady=(0, 4))

            btn = tk.Button(card, text="加载此样本",
                           command=lambda n=name: self._confirm_load_sample(n, win),
                           bg="#4a90d9", fg="white",
                           activebackground="#357abd", activeforeground="white",
                           relief="flat", bd=0, padx=10, cursor="hand2")
            btn.pack(fill="x", padx=6, pady=(0, 4))

    def _confirm_load_sample(self, name, win):
        """确认加载样本并关闭窗口"""
        names = SampleLibrary.load_names(name)
        if names:
            self.names = names
            self.sampler.reset_no_replace_pool()
            self.current_file = os.path.join(rct_rcplist_path, f"{name}.rcp")
            self.file_path_label.config(text=f"样本库: {name}", fg="purple")
            self.sample_count_label.config(text=f"样本数量: {len(names)}", fg="green")
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 从样本库加载: {name}, 共 {len(names)} 个名字")
            messagebox.showinfo("成功", f"已加载样本「{name}」\n共 {len(names)} 个名字")
            win.destroy()
        else:
            messagebox.showwarning("警告", f"样本「{name}」为空或无效")

    def auto_load_file(self):
        """自动加载默认样本（从样本库）"""
        config = ConfigManager()
        default_name = config.get("rct_default_sample", "")
        if not default_name:
            messagebox.showwarning("警告", "未设置默认样本，请先在配置中设置")
            return
        names = SampleLibrary.load_names(default_name)
        if names:
            self.names = names
            self.sampler.reset_no_replace_pool()
            self.current_file = os.path.join(rct_rcplist_path, f"{default_name}.rcp")
            self.file_path_label.config(text=f"样本库: {default_name}", fg="purple")
            self.sample_count_label.config(text=f"样本数量: {len(names)}", fg="green")
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 自动加载样本库: {default_name}, 共 {len(names)} 个名字")
            messagebox.showinfo("成功", f"已加载默认样本「{default_name}」\n共 {len(names)} 个名字")
        else:
            messagebox.showwarning("警告", f"默认样本「{default_name}」不存在或无效")

    # ══════════════════════════════════════════════════════════
    #  抽取逻辑
    # ══════════════════════════════════════════════════════════

    def draw(self):
        """执行抽取（根据当前模式）"""
        self.clear_result()
        if self.mode_var.get() == "person":
            self._draw_person()
        else:
            self._draw_group()

    def _draw_person(self):
        """随机抽人"""
        if not self.names:
            messagebox.showwarning("警告", "请先加载样本列表文件")
            return

        try:
            k = int(self.choice_entry.get())
        except (ValueError, TypeError):
            messagebox.showwarning("警告", "请选择抽取数量")
            return

        if k < 1:
            return
        if k > len(self.names):
            messagebox.showwarning("错误", f"抽取数量({k})大于样本数量({len(self.names)})")
            return
        if k == len(self.names) and not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有人吗？"):
            return

        selected = self.sampler.smart_sample(self.names, k)

        preview = ", ".join(selected[:8]) + ("..." if len(selected) > 8 else "")
        self._add_history("person", selected, f"抽{k}人: {preview}")

        rctlog.info(f"[随机抽取] 抽人成功: {selected}")
        messagebox.showinfo("抽取结果", "抽取结果：\n" + "\n".join(selected))

        if ConfigManager().get("save_result", True):
            SaveResult().save_result("RandomPerson", "随机抽人", selected)

    def _draw_group(self):
        """随机抽组"""
        try:
            total = int(self.total_entry.get())
            k = int(self.choice_entry.get())
        except (ValueError, TypeError):
            messagebox.showwarning("错误", "请选择有效的数字")
            return

        if total < 1:
            messagebox.showwarning("错误", "样本总数不能小于1")
            return
        if k < 1:
            messagebox.showwarning("错误", "抽取数量不能小于1")
            return
        if k > total:
            messagebox.showwarning("错误", "抽取数量不能大于总数量")
            return
        if k == total and not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有组吗？"):
            return

        all_groups = (
            list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:total]
            if self.group_order_var.get() == "ABC"
            else list(range(1, total + 1))
        )

        selected = self.sampler.smart_sample(all_groups, k)
        selected.sort()
        result_items = [f"{g}组" for g in selected]

        preview = ", ".join(str(g) for g in selected[:8]) + ("..." if len(selected) > 8 else "")
        self._add_history("group", result_items, f"抽{k}组: {preview}")

        rctlog.info(f"[随机抽取] 抽组成功: {selected}")
        messagebox.showinfo("抽取结果", "抽取结果：\n" + "\n".join(result_items))

        if ConfigManager().get("save_result", True):
            SaveResult().save_result("RandomGroup", "随机抽组", result_items)

    # ══════════════════════════════════════════════════════════
    #  历史记录
    # ══════════════════════════════════════════════════════════

    def _add_history(self, mode, items, preview):
        """添加一条历史记录并刷新UI"""
        self._history_id_counter += 1
        now = strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": self._history_id_counter,
            "timestamp": now,
            "ts_short": strftime("%H:%M:%S"),
            "mode": mode,
            "items": items,
            "preview": preview,
        }
        self.history.insert(0, entry)

        max_items = ConfigManager().get("max_history_items", 10)
        if len(self.history) > max_items:
            self.history = self.history[:max_items]

        self._rebuild_history_ui()

    def _rebuild_history_ui(self):
        """重建历史记录条目UI"""
        for child in self.history_inner.winfo_children():
            child.destroy()

        for entry in self.history:
            eid = entry["id"]
            row = tk.Frame(self.history_inner, relief="groove", bd=1)
            row.pack(fill="x", padx=3, pady=2)

            # 时间戳
            ts_label = tk.Label(
                row, text=entry["ts_short"],
                fg="gray", font=("", 8),
                anchor="w",
            )
            ts_label.pack(fill="x", padx=3, pady=(2, 0))

            label = tk.Label(
                row, text=entry["preview"],
                anchor="w", justify="left", font=("", 9),
                wraplength=180,
            )
            label.pack(fill="x", padx=3, pady=(0, 1))

            btn_row2 = tk.Frame(row)
            btn_row2.pack(fill="x", pady=(0, 2))
            tk.Button(btn_row2, text="查看", width=6,
                      command=lambda eid=eid: self._view_history(eid)).pack(side="left", padx=2)
            tk.Button(btn_row2, text="保存", width=6,
                      command=lambda eid=eid: self._save_history(eid)).pack(side="left", padx=2)

        # 滚动到顶部
        self._history_canvas.yview_moveto(0)

    def _get_entry(self, eid):
        """按ID查找历史条目"""
        for e in self.history:
            if e["id"] == eid:
                return e
        return None

    def _view_history(self, eid):
        """查看单条历史记录"""
        entry = self._get_entry(eid)
        if not entry:
            return
        title = "抽人记录" if entry["mode"] == "person" else "抽组记录"
        text = f"[{entry['timestamp']}] {title}\n\n" + "\n".join(entry["items"])

        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title(f"历史记录 #{entry['id']}")
        win.geometry("400x300")
        win.transient(self.frame.winfo_toplevel())
        win.grab_set()

        tk.Label(win, text=f"历史记录 #{entry['id']}  -  {entry['timestamp']}",
                 font=("", 10, "bold")).pack(pady=5)
        tw = tk.Text(win, wrap="word", font=("Courier", 10))
        tw.pack(fill="both", expand=True, padx=10, pady=5)
        tw.insert("1.0", "\n".join(entry["items"]))
        tw.config(state="disabled")
        tk.Button(win, text="关闭", command=win.destroy, width=12).pack(pady=5)

    def _save_history(self, eid):
        """保存单条历史记录（使用条目自身的时间戳）"""
        entry = self._get_entry(eid)
        if not entry:
            return
        msg = self._prompt_save_message()
        if msg is None:
            return  # 用户取消
        class_name = "RandomPerson" if entry["mode"] == "person" else "RandomGroup"
        prefix = "随机抽人" if entry["mode"] == "person" else "随机抽组"
        SaveResult().save_result(
            class_name, prefix, entry["items"], msg,
            custom_timestamp=entry["timestamp"],
        )

    def batch_save_all(self):
        """批量保存所有历史记录（使用各条目自身的时间戳）"""
        if not self.history:
            messagebox.showinfo("提示", "暂无历史记录")
            return
        msg = self._prompt_save_message()
        if msg is None:
            return  # 用户取消
        saved = 0
        for entry in self.history:
            class_name = "RandomPerson" if entry["mode"] == "person" else "RandomGroup"
            prefix = "随机抽人" if entry["mode"] == "person" else "随机抽组"
            path = SaveResult().save_result(
                class_name, prefix, entry["items"], msg,
                custom_timestamp=entry["timestamp"],
            )
            if path:
                saved += 1
        messagebox.showinfo("批量保存", f"已保存 {saved}/{len(self.history)} 条记录")

    def _prompt_save_message(self):
        """弹窗输入保存提示信息

        Returns:
            str: 用户输入的提示信息（可能为空字符串）
            None: 用户点了取消或关闭窗口
        """
        from tkinter import simpledialog
        return simpledialog.askstring(
            "保存提示", "输入保存提示信息（留空则无提示）:",
            parent=self.frame.winfo_toplevel(),
        )

    # ══════════════════════════════════════════════════════════
    #  保存当前结果
    # ══════════════════════════════════════════════════════════

    def save_current_result(self):
        """保存当前抽取结果（取自最新一条历史记录）"""
        if not self.history:
            messagebox.showwarning("警告", "暂无抽取结果可保存")
            return
        entry = self.history[0]
        msg = self._prompt_save_message()
        if msg is None:
            return  # 用户取消
        class_name = "RandomPerson" if self.mode_var.get() == "person" else "RandomGroup"
        prefix = "随机抽人" if self.mode_var.get() == "person" else "随机抽组"
        SaveResult().save_result(
            class_name, prefix, entry["items"], msg,
            custom_timestamp=entry["timestamp"],
        )

    def clear_all_history(self):
        """清空所有历史记录"""
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            self.history.clear()
            self._rebuild_history_ui()
            rctlog.info("所有历史记录已清除")
            messagebox.showinfo("成功", "历史记录已清除")

    # ══════════════════════════════════════════════════════════
    #  重置抽样历史
    # ══════════════════════════════════════════════════════════

    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("确认", "确定要重置抽样历史记录和统计计数吗？"):
            self.sampler.reset_history()
            messagebox.showinfo("成功", "抽样历史记录已重置")

# ========================================
#  高级抽取配置窗口
# ========================================

class AdvancedConfigWindow:
    """高级抽取配置窗口"""

    def __init__(self, parent, sampler, on_apply=None, on_open_weights=None):
        self.parent = parent
        self.sampler = sampler
        self.on_apply = on_apply
        self.on_open_weights = on_open_weights
        self.config = ConfigManager()
        self.cfg = self.sampler.advanced_config

        self.win = tk.Toplevel(parent)
        self.win.title("高级抽取配置")
        self.win.geometry("450x550+80+80")
        self.win.minsize(450, 550)
        self.win.maxsize(550, 650)
        self.win.resizable(True, True)
        self.win.transient(parent)
        self.win.grab_set()
        set_window_icon(self.win, rct_icon_path)

        self._create_widgets()
        self._apply_conflicts()

        rctlog.info("打开高级抽取配置窗口")

    def _make_section(self, parent, title):
        """创建带标题的分组框"""
        frame = tk.LabelFrame(parent, text=title, font=("", 10, "bold"),
                              fg="#2b5b84", padx=8, pady=6)
        frame.pack(fill="x", padx=10, pady=4)
        return frame

    def _create_widgets(self):
        """构建界面"""
        cfg = self.cfg

        # ── 标题 ──
        title_label = tk.Label(
            self.win, text="高级抽取配置",
            font=("Microsoft YaHei", 14, "bold"), fg="blue",
        )
        title_label.pack(pady=(10, 5))

        # ── 可滚动主区域 ──
        main_frame = tk.Frame(self.win)
        main_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(main_frame, highlightthickness=0)
        vbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_inner = tk.Frame(canvas)

        scroll_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=vbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.win.protocol("WM_DELETE_WINDOW",
                          lambda: (canvas.unbind_all("<MouseWheel>"), self.win.destroy()))

        # ═══ 1. 抽取方式 ═══
        sec1 = self._make_section(scroll_inner, "抽取方式")

        # 放回式 / 不放回式
        self.replacement_var = tk.BooleanVar(value=cfg.get("with_replacement", True))
        rep_frame = tk.Frame(sec1)
        rep_frame.pack(fill="x", pady=2)
        tk.Radiobutton(rep_frame, text="放回式抽取",
                       variable=self.replacement_var, value=True,
                       command=self._on_replacement_change).pack(side="left", padx=5)
        tk.Radiobutton(rep_frame, text="不放回式抽取",
                       variable=self.replacement_var, value=False,
                       command=self._on_replacement_change).pack(side="left", padx=5)

        # 不放回调整方法（仅不放回时可用）
        self.no_replace_frame = tk.Frame(sec1)
        self.no_replace_frame.pack(fill="x", pady=(5, 2), padx=10)
        tk.Label(self.no_replace_frame, text="调整方法：", font=("", 9)).pack(side="left")

        self.no_replace_method_var = tk.IntVar(
            value=cfg.get("no_replace_method", SmartSampler.NO_REPLACE_METHOD_CONTINUOUS))
        for val, name in SmartSampler.NO_REPLACE_METHOD_NAMES.items():
            tk.Radiobutton(
                self.no_replace_frame, text=name,
                variable=self.no_replace_method_var, value=val,
                command=self._on_no_replace_method_change,
            ).pack(side="left", padx=3)

        # 比率式阈值
        self.ratio_frame = tk.Frame(sec1)
        self.ratio_frame.pack(fill="x", pady=2, padx=10)
        tk.Label(self.ratio_frame, text="剩余比率阈值：").pack(side="left")
        self.ratio_var = tk.StringVar(value=str(int(cfg.get("no_replace_ratio", 0.5) * 100)))
        self.ratio_spin = tk.Spinbox(
            self.ratio_frame, textvariable=self.ratio_var,
            from_=10, to=50, increment=5, state="readonly", width=5,
        )
        self.ratio_spin.pack(side="left", padx=5)
        tk.Label(self.ratio_frame, text="%（剩余样本低于此比率时自动重载）",
                 fg="gray", font=("", 8)).pack(side="left")

        # ═══ 2. 抽取优化 ═══
        self.sec2 = self._make_section(scroll_inner, "抽取优化（仅放回式有效）")

        # --- 抽取前打乱 ---
        f_shuffle = tk.Frame(self.sec2)
        f_shuffle.pack(fill="x", pady=3)
        self.shuffle_var = tk.BooleanVar(value=cfg.get("shuffle_before", False))
        self.shuffle_cb = tk.Checkbutton(
            f_shuffle, text="抽取前打乱", variable=self.shuffle_var,
            command=self._apply_conflicts,
        )
        self.shuffle_cb.pack(side="left")
        tk.Label(f_shuffle, text="打乱次数：").pack(side="left", padx=(15, 0))
        self.shuffle_count_var = tk.StringVar(value=str(cfg.get("shuffle_count", 1)))
        self.shuffle_spin = tk.Spinbox(
            f_shuffle, textvariable=self.shuffle_count_var,
            from_=1, to=10, increment=1, state="readonly", width=4,
        )
        self.shuffle_spin.pack(side="left", padx=3)
        self.shuffle_freq_var = tk.StringVar(value=cfg.get("shuffle_frequency", "each"))
        tk.Radiobutton(f_shuffle, text="每次", variable=self.shuffle_freq_var,
                       value="each").pack(side="left", padx=2)
        tk.Radiobutton(f_shuffle, text="仅启动时", variable=self.shuffle_freq_var,
                       value="once").pack(side="left", padx=2)

        # --- 预抽取平衡 ---
        f_pre = tk.Frame(self.sec2)
        f_pre.pack(fill="x", pady=3)
        self.pre_draw_var = tk.BooleanVar(value=cfg.get("pre_draw_balance", False))
        self.pre_draw_cb = tk.Checkbutton(
            f_pre, text="预抽取平衡", variable=self.pre_draw_var,
            command=self._apply_conflicts,
        )
        self.pre_draw_cb.pack(side="left")
        tk.Label(f_pre, text="预抽取次数：").pack(side="left", padx=(15, 0))
        self.pre_draw_count_var = tk.StringVar(value=str(cfg.get("pre_draw_count", 1)))
        self.pre_draw_spin = tk.Spinbox(
            f_pre, textvariable=self.pre_draw_count_var,
            from_=1, to=10, increment=1, state="readonly", width=4,
        )
        self.pre_draw_spin.pack(side="left", padx=3)
        self.pre_draw_freq_var = tk.StringVar(value=cfg.get("pre_draw_frequency", "each"))
        tk.Radiobutton(f_pre, text="每次", variable=self.pre_draw_freq_var,
                       value="each").pack(side="left", padx=2)
        tk.Radiobutton(f_pre, text="仅启动时", variable=self.pre_draw_freq_var,
                       value="once").pack(side="left", padx=2)

        # --- 多次取最值 ---
        f_multi = tk.Frame(self.sec2)
        f_multi.pack(fill="x", pady=3)
        self.multi_var = tk.BooleanVar(value=cfg.get("multi_draw_best", False))
        self.multi_cb = tk.Checkbutton(
            f_multi, text="多次取最值", variable=self.multi_var,
            command=self._apply_conflicts,
        )
        self.multi_cb.pack(side="left")
        tk.Label(f_multi, text="后台抽取次数：").pack(side="left", padx=(15, 0))
        self.multi_count_var = tk.StringVar(value=str(cfg.get("multi_draw_count", 3)))
        self.multi_spin = tk.Spinbox(
            f_multi, textvariable=self.multi_count_var,
            from_=2, to=100, increment=1, state="readonly", width=4,
        )
        self.multi_spin.pack(side="left", padx=3)
        tk.Label(f_multi, text="(取被抽次数最多的前k个)", fg="gray", font=("", 8)).pack(side="left")

        # --- 随机定权重 ---
        f_randw = tk.Frame(self.sec2)
        f_randw.pack(fill="x", pady=3)
        self.randw_var = tk.BooleanVar(value=cfg.get("random_weights", False))
        self.randw_cb = tk.Checkbutton(
            f_randw, text="随机定权重", variable=self.randw_var,
            command=self._apply_conflicts,
        )
        self.randw_cb.pack(side="left")
        tk.Label(f_randw, text="范围：").pack(side="left", padx=(15, 0))
        self.randw_min_var = tk.StringVar(value=str(cfg.get("random_weight_min", 0.10)))
        tk.Spinbox(f_randw, textvariable=self.randw_min_var,
                   from_=0.05, to=1.00, increment=0.05, state="readonly",
                   width=5, format="%.2f").pack(side="left", padx=2)
        tk.Label(f_randw, text="~").pack(side="left")
        self.randw_max_var = tk.StringVar(value=str(cfg.get("random_weight_max", 2.00)))
        tk.Spinbox(f_randw, textvariable=self.randw_max_var,
                   from_=1.05, to=5.00, increment=0.05, state="readonly",
                   width=5, format="%.2f").pack(side="left", padx=2)

        # --- 递进式抽取 ---
        f_prog = tk.Frame(self.sec2)
        f_prog.pack(fill="x", pady=3)
        self.prog_var = tk.BooleanVar(value=cfg.get("progressive_draw", False))
        self.prog_cb = tk.Checkbutton(
            f_prog, text="递进式抽取（层层缩小样本池）", variable=self.prog_var,
            command=self._apply_conflicts,
        )
        self.prog_cb.pack(side="left")

        # ═══ 3. 加权抽取部分 ═══
        self.sec3 = self._make_section(scroll_inner, "加权抽取（仅放回式有效）")

        # --- 智能降权/配权 ---
        f_smart = tk.Frame(self.sec3)
        f_smart.pack(fill="x", pady=3)
        self.smart_reduce_var = tk.BooleanVar(value=cfg.get("smart_reduce_weight", True))
        self.smart_reduce_cb = tk.Checkbutton(
            f_smart, text="智能降权/配权", variable=self.smart_reduce_var,
            command=self._apply_conflicts,
        )
        self.smart_reduce_cb.pack(side="left")
        tk.Label(f_smart, text="记忆次数：").pack(side="left", padx=(15, 0))
        self.smart_memory_var = tk.StringVar(value=str(cfg.get("smart_memory_count", 3)))
        tk.Spinbox(f_smart, textvariable=self.smart_memory_var,
                   from_=1, to=20, increment=1, state="readonly", width=4).pack(side="left", padx=3)
        tk.Label(f_smart, text="(统计最近N次抽取，自动降权)", fg="gray", font=("", 8)).pack(side="left")

        # --- 自定义权重 ---
        f_custw = tk.Frame(self.sec3)
        f_custw.pack(fill="x", pady=3)
        self.custw_var = tk.BooleanVar(value=cfg.get("custom_weights", False))
        self.custw_cb = tk.Checkbutton(
            f_custw, text="自定义权重", variable=self.custw_var,
            command=self._apply_conflicts,
        )
        self.custw_cb.pack(side="left")
        self.custw_btn = tk.Button(
            f_custw, text="打开权重设置",
            command=self._open_weight_from_advanced,
            state="disabled", width=12,
            relief="flat", bd=0, bg="#e8e8e8",
            activebackground="#d0d0d0",
        )
        self.custw_btn.pack(side="left", padx=5)

        # ── 底部按钮 ──
        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="确定", command=self._ok,
                  width=12, bg="#4a90d9", fg="white",
                  activebackground="#357abd", activeforeground="white",
                  relief="flat", bd=0, cursor="hand2",
                  ).pack(side="left", padx=5)
        tk.Button(btn_frame, text="应用", command=self._apply,
                  width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="恢复默认", command=self._reset_defaults,
                  width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="取消",
                  command=lambda: (canvas.unbind_all("<MouseWheel>"), self.win.destroy()),
                  width=8).pack(side="left", padx=5)

        # 存储控件引用（用于冲突禁用）
        self._shuffle_widgets = [self.shuffle_spin]
        self._pre_draw_widgets = [self.pre_draw_spin]
        self._all_optimize_widgets = []  # 将在 _apply_conflicts 中动态处理

        # 初始状态
        self._on_replacement_change()

    # ── 冲突处理 ──────────────────────────────────────────

    def _on_replacement_change(self):
        """放回/不放回切换"""
        is_replacement = self.replacement_var.get()
        # 不放回时禁用所有优化和加权选项
        state = "normal" if is_replacement else "disabled"

        # 不放回调整方法区域
        for child in self.no_replace_frame.winfo_children():
            try:
                child.config(state="normal" if not is_replacement else "disabled")
            except tk.TclError:
                pass
        for child in self.ratio_frame.winfo_children():
            try:
                # 比率式才启用ratio spin
                if child == self.ratio_spin:
                    child.config(state="readonly" if (
                        not is_replacement and
                        self.no_replace_method_var.get() == SmartSampler.NO_REPLACE_METHOD_RATIO
                    ) else "disabled")
                else:
                    child.config(state="normal" if not is_replacement else "disabled")
            except tk.TclError:
                pass

        # 抽取优化和加权区域整体启用/禁用
        self._set_section_state(self.sec2, state)
        self._set_section_state(self.sec3, state)

        self._apply_conflicts()

    def _on_no_replace_method_change(self):
        """不放回调整方法切换"""
        is_ratio = (self.no_replace_method_var.get() == SmartSampler.NO_REPLACE_METHOD_RATIO)
        self.ratio_spin.config(state="readonly" if is_ratio else "disabled")

    def _set_section_state(self, section, state):
        """递归设置区域内所有子控件的状态"""
        for child in section.winfo_children():
            try:
                if isinstance(child, (tk.Frame, tk.LabelFrame)):
                    self._set_section_state(child, state)
                elif isinstance(child, tk.Checkbutton):
                    child.config(state=state)
                elif isinstance(child, tk.Radiobutton):
                    child.config(state=state)
                elif isinstance(child, tk.Spinbox):
                    child.config(state=state)
                elif isinstance(child, tk.Label):
                    pass  # Label 无所谓
                else:
                    try:
                        child.config(state=state)
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

    def _apply_conflicts(self):
        """处理功能冲突，灰化互斥选项"""
        is_replacement = self.replacement_var.get()
        if not is_replacement:
            return  # 不放回时全部禁用，无需进一步处理

        # 获取当前选中状态
        shuffle_on = self.shuffle_var.get()
        pre_draw_on = self.pre_draw_var.get()
        multi_on = self.multi_var.get()
        randw_on = self.randw_var.get()
        prog_on = self.prog_var.get()
        smart_reduce_on = self.smart_reduce_var.get()
        custw_on = self.custw_var.get()

        # 冲突规则：
        # 1. 随机定权重 与 自定义权重 互斥
        # 2. 随机定权重 与 智能降权 互斥
        # 3. 多次取最值 与 递进式抽取 互斥
        # 4. 随机定权重 与 递进式抽取 互斥
        # 5. 递进式抽取 与 智能降权 互斥（递进不需要降权）
        # 6. 随机定权重 与 抽取前打乱/预抽取平衡 不冲突（可以叠加）
        # 7. 多次取最值 与 随机定权重 不冲突（可以叠加）

        # 随机定权重 → 禁用 智能降权、自定义权重、递进式
        if randw_on:
            self.smart_reduce_cb.config(state="disabled")
            self.custw_cb.config(state="disabled")
            self.prog_cb.config(state="disabled")
        else:
            # 恢复基本状态
            self.smart_reduce_cb.config(state="normal")
            self.custw_cb.config(state="normal")
            self.prog_cb.config(state="normal")

        # 自定义权重 → 禁用 随机定权重
        if custw_on:
            self.randw_cb.config(state="disabled")
        elif not randw_on:
            self.randw_cb.config(state="normal")

        # 智能降权 → 禁用 随机定权重
        # （已在上面处理过）

        # 多次取最值 → 禁用 递进式抽取
        if multi_on:
            self.prog_cb.config(state="disabled")
        elif not randw_on:
            self.prog_cb.config(state="normal")

        # 递进式抽取 → 禁用 多次取最值、智能降权、随机定权重
        if prog_on:
            self.multi_cb.config(state="disabled")
            self.smart_reduce_cb.config(state="disabled")
            self.randw_cb.config(state="disabled")
        elif not multi_on and not randw_on:
            self.multi_cb.config(state="normal")
            self.smart_reduce_cb.config(state="normal")

        # 如果智能降权和自定义权重都被禁用且不是随机定权重也不是递进式，恢复它们
        if not randw_on and not prog_on:
            self.smart_reduce_cb.config(state="normal")
            self.custw_cb.config(state="normal")

        # 自定义权重按钮：勾选时启用，否则禁用
        self.custw_btn.config(
            state="normal" if (custw_on and is_replacement) else "disabled",
        )

    # ── 收集与保存 ────────────────────────────────────────

    def _collect_config(self):
        """收集UI配置到字典"""
        cfg = {}
        cfg["with_replacement"] = self.replacement_var.get()
        cfg["no_replace_method"] = self.no_replace_method_var.get()
        try:
            cfg["no_replace_ratio"] = float(self.ratio_var.get()) / 100.0
        except ValueError:
            cfg["no_replace_ratio"] = 0.5

        cfg["shuffle_before"] = self.shuffle_var.get()
        try:
            cfg["shuffle_count"] = int(self.shuffle_count_var.get())
        except ValueError:
            cfg["shuffle_count"] = 1
        cfg["shuffle_frequency"] = self.shuffle_freq_var.get()

        cfg["pre_draw_balance"] = self.pre_draw_var.get()
        try:
            cfg["pre_draw_count"] = int(self.pre_draw_count_var.get())
        except ValueError:
            cfg["pre_draw_count"] = 1
        cfg["pre_draw_frequency"] = self.pre_draw_freq_var.get()

        cfg["multi_draw_best"] = self.multi_var.get()
        try:
            cfg["multi_draw_count"] = int(self.multi_count_var.get())
        except ValueError:
            cfg["multi_draw_count"] = 3

        cfg["random_weights"] = self.randw_var.get()
        try:
            cfg["random_weight_min"] = float(self.randw_min_var.get())
            cfg["random_weight_max"] = float(self.randw_max_var.get())
        except ValueError:
            cfg["random_weight_min"] = 0.10
            cfg["random_weight_max"] = 2.00

        cfg["progressive_draw"] = self.prog_var.get()

        cfg["smart_reduce_weight"] = self.smart_reduce_var.get()
        try:
            cfg["smart_memory_count"] = int(self.smart_memory_var.get())
        except ValueError:
            cfg["smart_memory_count"] = 3

        cfg["custom_weights"] = self.custw_var.get()

        return cfg

    def _save_to_sampler(self):
        """将配置写入 sampler"""
        cfg = self._collect_config()
        self.sampler.advanced_config.update(cfg)
        # 同步智能模式的记忆窗口
        if cfg.get("smart_reduce_weight", True):
            self.sampler.smart_window = cfg.get("smart_memory_count", 3)
        # 如果自定义权重启用，确保使用固定权重
        if cfg.get("custom_weights"):
            self.sampler.use_fixed_weights = True

    def _save_to_global_config(self):
        """将高级配置保存到全局 config.json"""
        cfg = self._collect_config()
        config = ConfigManager()
        mapping = {
            "with_replacement": "adv_with_replacement",
            "no_replace_method": "adv_no_replace_method",
            "no_replace_ratio": "adv_no_replace_ratio",
            "shuffle_before": "adv_shuffle_before",
            "shuffle_count": "adv_shuffle_count",
            "shuffle_frequency": "adv_shuffle_frequency",
            "pre_draw_balance": "adv_pre_draw_balance",
            "pre_draw_count": "adv_pre_draw_count",
            "pre_draw_frequency": "adv_pre_draw_frequency",
            "multi_draw_best": "adv_multi_draw_best",
            "multi_draw_count": "adv_multi_draw_count",
            "random_weights": "adv_random_weights",
            "random_weight_min": "adv_random_weight_min",
            "random_weight_max": "adv_random_weight_max",
            "progressive_draw": "adv_progressive_draw",
            "smart_reduce_weight": "adv_smart_reduce_weight",
            "smart_memory_count": "adv_smart_memory_count",
            "custom_weights": "adv_custom_weights",
        }
        for src_key, dst_key in mapping.items():
            if src_key in cfg:
                config.set(dst_key, cfg[src_key])

    def _apply(self):
        """应用配置"""
        self._save_to_sampler()
        self._save_to_global_config()
        rctlog.info("高级抽取配置已应用")
        messagebox.showinfo("成功", "高级抽取配置已应用")
        if self.on_apply:
            self.on_apply()

    def _ok(self):
        """确定并关闭"""
        self._save_to_sampler()
        self._save_to_global_config()
        rctlog.info("高级抽取配置已保存")
        if self.on_apply:
            self.on_apply()
        self.win.destroy()

    def _reset_defaults(self):
        """恢复默认配置"""
        if not messagebox.askyesno("确认", "确定要恢复高级抽取的默认配置吗？"):
            return
        defaults = {
            "with_replacement": True,
            "no_replace_method": SmartSampler.NO_REPLACE_METHOD_CONTINUOUS,
            "no_replace_ratio": 0.5,
            "shuffle_before": False,
            "shuffle_count": 1,
            "shuffle_frequency": "each",
            "pre_draw_balance": False,
            "pre_draw_count": 1,
            "pre_draw_frequency": "each",
            "multi_draw_best": False,
            "multi_draw_count": 3,
            "random_weights": False,
            "random_weight_min": 0.10,
            "random_weight_max": 2.00,
            "progressive_draw": False,
            "smart_reduce_weight": True,
            "smart_memory_count": 3,
            "custom_weights": False,
        }
        self.sampler.advanced_config.update(defaults)
        self.cfg = self.sampler.advanced_config
        # 重建UI变量
        self.replacement_var.set(defaults["with_replacement"])
        self.no_replace_method_var.set(defaults["no_replace_method"])
        self.ratio_var.set(str(int(defaults["no_replace_ratio"] * 100)))
        self.shuffle_var.set(defaults["shuffle_before"])
        self.shuffle_count_var.set(str(defaults["shuffle_count"]))
        self.shuffle_freq_var.set(defaults["shuffle_frequency"])
        self.pre_draw_var.set(defaults["pre_draw_balance"])
        self.pre_draw_count_var.set(str(defaults["pre_draw_count"]))
        self.pre_draw_freq_var.set(defaults["pre_draw_frequency"])
        self.multi_var.set(defaults["multi_draw_best"])
        self.multi_count_var.set(str(defaults["multi_draw_count"]))
        self.randw_var.set(defaults["random_weights"])
        self.randw_min_var.set(str(defaults["random_weight_min"]))
        self.randw_max_var.set(str(defaults["random_weight_max"]))
        self.prog_var.set(defaults["progressive_draw"])
        self.smart_reduce_var.set(defaults["smart_reduce_weight"])
        self.smart_memory_var.set(str(defaults["smart_memory_count"]))
        self.custw_var.set(defaults["custom_weights"])
        self._on_replacement_change()
        self._apply_conflicts()
        rctlog.info("高级抽取配置已恢复默认")
        messagebox.showinfo("成功", "已恢复默认配置")

    def _open_weight_from_advanced(self):
        """从高级窗口打开权重设置（先看是否有回调）"""
        if self.on_open_weights:
            self.on_open_weights()
        else:
            messagebox.showinfo(
                "提示",
                "请先在主界面中加载样本，\n"
                "然后在高级窗口中勾选「自定义权重」\n"
                "再点击此按钮设置。\n\n"
                "或者关闭高级窗口后，\n"
                "将抽样模式切换到「智能」或「高级」，\n"
                "点击主界面的「权重」按钮设置。"
            )
