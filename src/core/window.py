"""UI 窗口模块：配置窗口、选项卡界面和高级抽取界面。"""
import os
from time import strftime
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, filedialog

# 抽取结果超过该数量时，提醒中省略多余项并强制保存完整结果
OVERSIZED_LIMIT = 10
from core.logman import rctlog
from core.config import ConfigManager
from core import islandmq
from core import tray
from core import autostart
from core.notify import notify_result
from core.info import work_path, rct_rcplist_path, rct_version, document_path, rct_history_path
from core.fileman import (SampleLibrary, SaveResult, base64decode,
                          read_text_file, parse_names, MAX_FILE_BYTES, MAX_NAMES)
from core.historyman import append as history_append, clear_files as history_clear_files
from core.sampler import SmartSampler
from core.platutils import open_file_or_dir
from core.dialog import AboutWindow, load_about_info, ask_string
from core.info import rct_icon_path
from core.platutils import set_window_icon


class ConfigWindow:
    """软件内配置窗口：统一管理程序各项设置。

    单例：重复打开（如托盘菜单连点）时改为前置已有窗口，避免出现多个模态窗口。
    """
    _instance = None

    def __new__(cls, parent):
        if cls._instance is not None:
            try:
                if cls._instance.window.winfo_exists():
                    cls._instance.window.deiconify()
                    cls._instance.window.lift()
                    cls._instance.window.focus_force()
                    try:
                        cls._instance.window.grab_set()
                    except tk.TclError:
                        pass
                    rctlog.info("配置窗口已打开，前置已有窗口")
                    # 阻止 __init__ 再次执行（否则会新建 Toplevel 覆盖旧窗口）
                    cls._instance._skip_init = True
                    return cls._instance
            except Exception:
                pass
            cls._instance = None
        return super().__new__(cls)

    def __init__(self, parent):
        # __new__ 复用了已存在的实例时，跳过全部初始化
        if getattr(self, "_skip_init", False):
            self._skip_init = False
            return

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
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        set_window_icon(self.window, rct_icon_path)
        self._applied = False
        self._create_widgets()
        self._init_config = self._collect_config()
        ConfigWindow._instance = self

    def _on_close(self):
        """关闭窗口时清除单例引用"""
        if ConfigWindow._instance is self:
            ConfigWindow._instance = None
        self.window.destroy()

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
        self._create_notify_tab(notebook)
        self._create_floatball_tab(notebook)
        self._create_update_tab(notebook)

        self.window.protocol("WM_DELETE_WINDOW", self._prompt_close)
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)
        for text, cmd in [
            ("确定", self._ok),
            ("应用", self._apply),
            ("关闭", self._prompt_close),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, width=12, height=1
                      ).pack(side="left", padx=5)

    # 基本设置

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

        # 自动加载随机抽人样本
        self.auto_load_var = tk.BooleanVar(
            value=self.config.get("auto_load_sample", True))
        tk.Checkbutton(tab, text="启动时自动加载样本（随机抽人）",
                       variable=self.auto_load_var).pack(anchor="w", **pad)

        # 自动加载点名名单（独立于抽样）
        self.rollcall_auto_load_var = tk.BooleanVar(
            value=self.config.get("rollcall_auto_load_sample", True))
        tk.Checkbutton(tab, text="启动时自动加载名单（随机点名）",
                       variable=self.rollcall_auto_load_var).pack(anchor="w", **pad)

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

        # 抽取历史实时写入本地文件
        self.history_file_var = tk.BooleanVar(
            value=bool(self.config.get("history_file_enabled", True)))
        tk.Checkbutton(tab, text="把抽取历史实时写入本地文件",
                       variable=self.history_file_var).pack(anchor="w", **pad)
        tk.Button(tab, text="打开记录目录",
                  command=lambda: open_file_or_dir(rct_history_path),
                  width=14).pack(anchor="w", **pad)

        # ── 默认样本 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        tk.Label(tab, text="默认加载样本",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", padx=15, pady=(2, 0))
        tk.Label(tab, text="启动时自动加载的样本库文件（用于随机抽人）",
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

    # 抽样设置

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

        tk.Label(tab, text="基本：纯随机 ｜ 智能：避免连续、可自定义权重 ｜ 高级：完整高级配置",
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
        tk.Label(tab, text="放回 / 不放回、抽取优化、加权等详细配置",
                 fg="gray", font=("", 8)).pack(anchor="w", **pad, pady=(0, 6))

        # ── 随机点名配置入口 ──
        roll_btn_frame = tk.Frame(tab)
        roll_btn_frame.pack(fill="x", **pad, pady=2)
        tk.Label(roll_btn_frame, text="随机点名配置：", width=15, anchor="w").pack(side="left")
        tk.Button(roll_btn_frame, text="打开随机点名配置",
                  command=self._open_rollcall_config,
                  bg="#8e44ad", fg="white",
                  activebackground="#7d3c98", activeforeground="white",
                  relief="flat", bd=0, padx=10, cursor="hand2",
                  width=18).pack(side="left", padx=5)
        tk.Label(tab, text="点名速率、打乱名单、放回 / 不放回、重置限度等",
                 fg="gray", font=("", 8)).pack(anchor="w", **pad, pady=(0, 6))

        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=6)

        # ── 默认值 ──
        tk.Label(tab, text="默认值设定",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", **pad, pady=(2, 0))
        tk.Label(tab, text="以下数值将作为对应输入框的默认值",
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
            ("默认抽取数量：", "rct_choice_default", 3, 1, 50),
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
        """从配置窗口打开高级抽取配置

        优先复用抽取页正在使用的 sampler 实例，让「应用」即时生效；
        只有在抽取页尚未就绪时才退化为临时 sampler（仅写配置文件）。
        """
        sampler = None
        try:
            from core.appfunc import get_app
            app = get_app()
            if app is not None and getattr(app, "call_tab", None) is not None:
                sampler = app.call_tab.sampler
        except Exception as e:
            rctlog.warning(f"获取抽取页 sampler 失败，改用临时实例: {e}")
            sampler = None

        if sampler is None:
            from core.sampler import SmartSampler
            sampler = SmartSampler(mode=self.config.get("sampler_mode", 1),
                                   smart_window=self.config.get(
                                       "adv_smart_memory_count",
                                       self.config.get("smart_window", 3)))

        # 加载当前配置到 sampler（复用实例时同样先同步一遍，保证界面与运行态一致）
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

    def _open_rollcall_config(self):
        """从配置窗口打开随机点名配置（与高级抽取配置入口类似）"""
        from core.rollcall import RollCallConfigWindow
        options = {
            "speed": self.config.get("rollcall_speed", 1.0),
            "shuffle": self.config.get("rollcall_shuffle", False),
            "with_replacement": self.config.get("rollcall_with_replacement", True),
            "reset_limit": self.config.get("rollcall_reset_limit", "full"),
            "reset_custom": self.config.get("rollcall_reset_custom", 1),
        }
        RollCallConfigWindow(self.window, options)
        rctlog.info("从配置窗口打开随机点名配置")

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

    # 样本管理

    def _create_sample_mgr_tab(self, notebook):
        tab = self._make_tab(notebook, "样本管理")
        pad = {"padx": 15}

        tk.Label(tab, text="已保存的样本（上限50个）",
                 font=("", 10, "bold")).pack(anchor="w", **pad, pady=(10, 2))
        tk.Label(tab, text="样本可导出为 RCP / TXT 格式",
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
                       ("CSV 文件", "*.csv"),
                       ("RCP 文件", "*.rcp"),
                       ("所有文件", "*.*")])
        if not fp:
            return

        samples = SampleLibrary.get_samples()
        if len(samples) >= 50:
            messagebox.showwarning("样本库已达上限",
                                   "样本库最多存放 50 个样本，请先删除部分样本后再导入。")
            return

        default_name = os.path.splitext(os.path.basename(fp))[0]
        name = ask_string(
            "导入样本",
            "请输入样本名称（将作为文件名，无需填写扩展名）：\n"
            "不能包含以下字符：\\ / : * ? \" < > |",
            initialvalue=default_name,
            parent=self.window)
        if not name:
            return
        name = name.strip()

        try:
            _dest, notes = SampleLibrary.import_sample(fp, name)
            rctlog.info(f"样本已导入: {name}")
            self._rebuild_mgr_list()
            self._refresh_sample_list()
            msg = f"样本「{name}」已导入样本库。"
            if notes:
                msg += "\n\n" + "\n".join(notes)
                messagebox.showwarning("导入成功（已调整）", msg)
            else:
                messagebox.showinfo("导入成功", msg)
        except Exception as e:
            messagebox.showerror("导入失败", f"导入样本时出错：\n{e}")

    def _export_rcp(self, name):
        """导出单个样本为 .rcp"""
        dest = filedialog.askdirectory(title=f"选择 RCP 文件的导出目录（{name}.rcp）")
        if not dest:
            return
        try:
            path = SampleLibrary.export_rcp(name, dest)
            messagebox.showinfo("导出成功", f"已导出到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出 RCP 文件时出错：\n{e}")

    def _export_txt(self, name):
        """导出单个样本为 .txt"""
        dest = filedialog.askdirectory(title=f"选择 TXT 文件的导出目录（{name}.txt）")
        if not dest:
            return
        try:
            path = SampleLibrary.export_txt(name, dest)
            messagebox.showinfo("导出成功", f"已导出到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出 TXT 文件时出错：\n{e}")

    def _rename_sample(self, old_name):
        """重命名样本"""
        new_name = ask_string(
            "重命名样本", f"请输入新的样本名称（原名称：{old_name}）：",
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
            messagebox.showinfo("重命名成功", f"样本已重命名为「{new_name}」。")
        except Exception as e:
            messagebox.showerror("重命名失败", f"重命名样本时出错：\n{e}")

    def _delete_sample(self, name):
        """删除样本"""
        if not messagebox.askyesno("删除样本",
                                   f"确定要删除样本「{name}」吗？\n\n删除后无法恢复。"):
            return
        SampleLibrary.delete_sample(name)
        self._rebuild_mgr_list()
        self._refresh_sample_list()
        messagebox.showinfo("删除成功", f"样本「{name}」已删除。")

    # 抽取后提醒

    @staticmethod
    def _parse_duration(value, default):
        """解析时长输入，非法值回退到默认值"""
        try:
            seconds = float(value)
        except (TypeError, ValueError):
            return default
        return round(seconds, 1) if seconds > 0 else default

    def _create_notify_tab(self, notebook):
        tab = self._make_tab(notebook, "提醒")
        pad = {"padx": 15}

        # ── 提醒方式 ──
        f1 = tk.Frame(tab)
        f1.pack(fill="x", **pad, pady=(15, 2))
        tk.Label(f1, text="提醒方式：", width=15, anchor="w").pack(side="left")
        self.notify_mode_var = tk.StringVar(
            value=str(self.config.get("notify_mode", "popup")))
        tk.Radiobutton(f1, text="弹窗提醒", variable=self.notify_mode_var,
                       value="popup",
                       command=self._on_notify_mode_change).pack(side="left", padx=2)
        self.island_radio = tk.Radiobutton(
            f1, text="ClassIsland 通知", variable=self.notify_mode_var,
            value="island", command=self._on_notify_mode_change)
        self.island_radio.pack(side="left", padx=2)

        tk.Label(tab, text="弹窗提醒：抽取完成后弹出结果窗口（默认）\n"
                           "ClassIsland 通知：通过 IslandMQ 插件把抽取结果推送到教室电脑",
                 fg="gray", font=("", 8), justify="left").pack(anchor="w", **pad)

        # ── ClassIsland 通知设置 ──
        self.island_box = tk.LabelFrame(tab, text="ClassIsland 通知设置")
        self.island_box.pack(fill="x", padx=15, pady=(8, 0))
        self._island_widgets = []

        row = tk.Frame(self.island_box)
        row.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(row, text="主机 IP：", width=9, anchor="w").pack(side="left")
        self.ci_ip_var = tk.StringVar(
            value=str(self.config.get("ci_ip", islandmq.DEFAULT_IP)))
        w = tk.Entry(row, textvariable=self.ci_ip_var, width=16)
        w.pack(side="left")
        self._island_widgets.append(w)
        tk.Label(row, text="端口：").pack(side="left", padx=(10, 0))
        self.ci_port_var = tk.StringVar(
            value=str(self.config.get("ci_port", islandmq.DEFAULT_PORT)))
        w = tk.Entry(row, textvariable=self.ci_port_var, width=8)
        w.pack(side="left", padx=2)
        self._island_widgets.append(w)

        row = tk.Frame(self.island_box)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="通知标题：", width=9, anchor="w").pack(side="left")
        self.ci_title_var = tk.StringVar(
            value=str(self.config.get("ci_title", "")))
        w = tk.Entry(row, textvariable=self.ci_title_var)
        w.pack(side="left", fill="x", expand=True)
        self._island_widgets.append(w)

        tk.Label(self.island_box,
                 text="标题留空时自动使用「随机抽取结果」",
                 fg="gray", font=("", 8)).pack(anchor="w", padx=8)

        row = tk.Frame(self.island_box)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="遮罩时长：", width=9, anchor="w").pack(side="left")
        self.ci_mask_var = tk.StringVar(
            value=str(self.config.get("ci_mask_duration",
                                      islandmq.DEFAULT_MASK_DURATION)))
        w = tk.Spinbox(row, textvariable=self.ci_mask_var, from_=0.5, to=60.0,
                       increment=0.5, width=6)
        w.pack(side="left")
        self._island_widgets.append(w)
        tk.Label(row, text="秒").pack(side="left", padx=(2, 14))
        tk.Label(row, text="正文时长：").pack(side="left")
        self.ci_overlay_var = tk.StringVar(
            value=str(self.config.get("ci_overlay_duration",
                                      islandmq.DEFAULT_OVERLAY_DURATION)))
        w = tk.Spinbox(row, textvariable=self.ci_overlay_var, from_=0.5, to=60.0,
                       increment=0.5, width=6)
        w.pack(side="left")
        self._island_widgets.append(w)
        tk.Label(row, text="秒").pack(side="left", padx=2)

        row = tk.Frame(self.island_box)
        row.pack(fill="x", padx=8, pady=(4, 8))
        self.ci_fallback_var = tk.BooleanVar(
            value=bool(self.config.get("ci_fallback_popup", True)))
        cb = tk.Checkbutton(row, text="发送失败时改用弹窗提醒",
                            variable=self.ci_fallback_var)
        cb.pack(side="left")
        self._island_widgets.append(cb)

        self.ci_test_btn = tk.Button(
            row, text="连接测试", command=self._test_island_connection,
            bg="#4a90d9", fg="white",
            activebackground="#357abd", activeforeground="white",
            relief="flat", bd=0, padx=10, cursor="hand2")
        self.ci_test_btn.pack(side="right")
        self._island_widgets.append(self.ci_test_btn)

        self.ci_notice_btn = tk.Button(
            row, text="发送测试通知", command=self._send_test_island_notice,
            relief="groove", bd=1, padx=10, cursor="hand2")
        self.ci_notice_btn.pack(side="right", padx=6)
        self._island_widgets.append(self.ci_notice_btn)

        tk.Label(self.island_box,
                 text="需要教室电脑运行 ClassIsland 并安装 IslandMQ 插件；\n"
                      "抽取结果会以「标题（遮罩）+ 名单（正文）」的形式推送。",
                 fg="gray", font=("", 8), justify="left"
                 ).pack(anchor="w", padx=8, pady=(0, 6))

        # pyzmq 不可用时禁用该选项
        if not islandmq.is_available():
            self.island_radio.config(state="disabled")
            self.notify_mode_var.set("popup")
            tk.Label(self.island_box,
                     text="⚠ 未检测到 pyzmq，ClassIsland 通知不可用。\n"
                          "请先执行：pip install pyzmq",
                     fg="#c0392b", font=("", 8), justify="left"
                     ).pack(anchor="w", padx=8, pady=(0, 6))

        self._on_notify_mode_change()

    def _on_notify_mode_change(self):
        """选择弹窗提醒时禁用 ClassIsland 相关控件"""
        state = ("normal" if self.notify_mode_var.get() == "island"
                 else "disabled")
        for w in self._island_widgets:
            try:
                w.config(state=state)
            except tk.TclError:
                pass

    def _island_endpoint_or_warn(self):
        """校验当前 IP/端口，返回端点字符串；无效时提示并返回 None"""
        try:
            return islandmq.build_endpoint(self.ci_ip_var.get(),
                                           self.ci_port_var.get())
        except ValueError as e:
            messagebox.showwarning("地址无效", str(e))
            return None

    def _test_island_connection(self):
        """向 ClassIsland 发送 ping 心跳"""
        if not islandmq.is_available():
            messagebox.showwarning(
                "ClassIsland 通知不可用",
                "未检测到 pyzmq，无法发送 ClassIsland 通知。\n"
                "请先执行：pip install pyzmq")
            return
        if self._island_endpoint_or_warn() is None:
            return
        ok, msg = islandmq.ping(self.ci_ip_var.get(), self.ci_port_var.get())
        if ok:
            messagebox.showinfo("连接测试", f"连接成功！\n\n服务器响应：{msg}")
        else:
            messagebox.showerror("连接失败", f"无法连接到 ClassIsland。\n\n{msg}")

    def _send_test_island_notice(self):
        """发送一条测试通知，用于确认遮罩 / 正文时长"""
        if not islandmq.is_available():
            messagebox.showwarning(
                "ClassIsland 通知不可用",
                "未检测到 pyzmq，无法发送 ClassIsland 通知。\n"
                "请先执行：pip install pyzmq")
            return
        if self._island_endpoint_or_warn() is None:
            return
        ok, msg = islandmq.send_notice(
            self.ci_title_var.get(), "这是一条测试通知",
            self.ci_ip_var.get(), self.ci_port_var.get(),
            self.ci_mask_var.get(), self.ci_overlay_var.get(),
            self.config.get("ci_timeout_ms", islandmq.DEFAULT_TIMEOUT_MS),
        )
        if ok:
            messagebox.showinfo("测试通知", "测试通知已发送，请在教室电脑上查看显示效果。")
        else:
            messagebox.showerror("测试通知发送失败", msg)

    # 桌面集成（悬浮球 + 系统托盘）

    def _create_floatball_tab(self, notebook):
        tab = self._make_tab(notebook, "桌面集成")
        pad = {"padx": 15, "pady": 4}

        tk.Label(tab, text="桌面悬浮球",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", **pad)

        self.floatball_var = tk.BooleanVar(
            value=self.config.get("floatball_enabled", True))
        tk.Checkbutton(tab, text="显示桌面悬浮球",
                       variable=self.floatball_var).pack(anchor="w", **pad)

        tk.Label(tab, text="启用后，桌面会出现一个可拖动的置顶圆形按钮。",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)
        tk.Label(tab, text="左键单击执行抽取；右键选择抽取类型与数量。",
                 fg="gray", font=("", 9)).pack(anchor="w", **pad)

        size_row = tk.Frame(tab)
        size_row.pack(fill="x", **pad)
        tk.Label(size_row, text="悬浮球大小：", width=15, anchor="w").pack(side="left")
        self.floatball_size_var = tk.StringVar(
            value=self.config.get("floatball_size", "medium"))
        for val, label in [("small", "小"), ("medium", "中"), ("large", "大")]:
            tk.Radiobutton(size_row, text=label, variable=self.floatball_size_var,
                           value=val).pack(side="left", padx=3)

        # ── 系统托盘 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        tk.Label(tab, text="系统托盘",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", **pad)

        self.tray_var = tk.BooleanVar(
            value=self.config.get("tray_enabled", True))
        tk.Checkbutton(tab, text="关闭窗口后保留系统托盘",
                       variable=self.tray_var).pack(anchor="w", **pad)

        self.tray_min_var = tk.BooleanVar(
            value=self.config.get("tray_start_minimized", False))
        tk.Checkbutton(tab, text="启动后直接后台驻留托盘（不显示主界面）",
                       variable=self.tray_min_var).pack(anchor="w", **pad)

        if not tray.is_available():
            tk.Label(tab, text=f"当前不可用：{tray.unavailable_reason()}",
                     fg="#c0392b", font=("", 9)).pack(anchor="w", **pad)
        else:
            tk.Label(tab, text="托盘右键菜单：显示主界面 / 软件配置 / 检测更新 / 悬浮球 / 退出",
                     fg="gray", font=("", 9)).pack(anchor="w", **pad)

        # ── 开机自启 ──
        ttk.Separator(tab, orient="horizontal").pack(fill="x", padx=15, pady=8)

        tk.Label(tab, text="开机自启",
                 font=("", 10, "bold"), fg="#2b5b84").pack(anchor="w", **pad)

        self.autostart_var = tk.BooleanVar(value=autostart.is_enabled())
        tk.Checkbutton(tab, text="开机时自动启动本程序",
                       variable=self.autostart_var).pack(anchor="w", **pad)

    # 更新设置

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
        
        tk.Label(tab, text="中国大陆建议使用 Gitee，其他地区建议使用 GitHub",
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

        # 测试版更新
        self.accept_preview_var = tk.BooleanVar(
            value=self.config.get("accept_preview_update", False))
        tk.Checkbutton(tab, text="接收测试版更新",
                       variable=self.accept_preview_var).pack(anchor="w", **pad)

        tk.Label(tab, text="启用后，版本检测将同时检查测试版更新",
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
                 text=f"版本号：{rct_version}\n"
                      f"版本代码：{rct_vercode}\n"
                      f"发布日期：{rct_date}",
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
        """立即检查更新 — 启动 update.py --check"""
        update_source = self.update_source_var.get()
        accept_preview = self.accept_preview_var.get()
        from core.update import run_auto_update
        success = run_auto_update(source=update_source, mode="--check", accept_preview=accept_preview)
        if not success:
            messagebox.showerror("启动失败", "无法启动更新程序，请手动前往官网下载最新版本。")

    # ── 保存（纯逻辑，不涉及 UI 弹窗）──────────────

    def _collect_config(self):
        """收集当前 UI 配置到字典（不写入文件）"""
        updates = {
            "save_result": self.save_result_var.get(),
            "result_path": 1 if self.result_path_var.get() == "桌面" else 0,
            "auto_load_sample": self.auto_load_var.get(),
            "rollcall_auto_load_sample": self.rollcall_auto_load_var.get(),
            "rct_merge_names": self.merge_names_var.get(),
            "max_history_items": int(self.history_var.get()),
            "history_file_enabled": self.history_file_var.get(),
            "sampler_mode": self.sampler_mode_var.get(),
            "smart_use_fixed_weights": self.smart_fixed_weights_var.get(),
            "rct_default_sample": self.sample_combo.get(),
            "update_source": self.update_source_var.get(),
            "auto_check_update": self.auto_check_var.get(),
            "accept_preview_update": self.accept_preview_var.get(),
            "notify_mode": self.notify_mode_var.get(),
            "ci_ip": self.ci_ip_var.get().strip(),
            "ci_port": self.ci_port_var.get().strip(),
            "ci_title": self.ci_title_var.get().strip(),
            "ci_mask_duration": self._parse_duration(
                self.ci_mask_var.get(), islandmq.DEFAULT_MASK_DURATION),
            "ci_overlay_duration": self._parse_duration(
                self.ci_overlay_var.get(), islandmq.DEFAULT_OVERLAY_DURATION),
            "ci_fallback_popup": self.ci_fallback_var.get(),
            "floatball_enabled": self.floatball_var.get(),
            "floatball_size": self.floatball_size_var.get(),
            "tray_enabled": self.tray_var.get(),
            "tray_start_minimized": self.tray_min_var.get(),
            "auto_start": self.autostart_var.get(),
        }
        if updates["rct_default_sample"] in ("（无）", "（样本库为空）"):
            updates["rct_default_sample"] = ""
        updates["rct_default_mode"] = self.default_mode_var.get()
        for key in ("rct_group_total", "rct_choice_default"):
            updates[key] = int(self._default_vars[key].get())
        return updates

    def _collect_and_save(self):
        """收集所有配置项并写入配置文件
        Returns: True 成功 / False 失败
        """
        try:
            updates = self._collect_config()
            # 开机自启：复制 / 删除启动文件夹快捷方式，失败则中止本次保存
            ok, msg = autostart.apply(updates["auto_start"])
            if not ok:
                messagebox.showerror("开机自启设置失败", msg)
                return False
            for key, value in updates.items():
                self.config.set(key, value)
            rctlog.info("配置已保存")
            # 按悬浮窗开关刷新其显示状态
            try:
                from core import floatball
                floatball.refresh()
            except Exception as e:
                rctlog.warning(f"刷新悬浮球可见性失败: {e}")
            # 按托盘开关启用 / 停用托盘
            try:
                tray.refresh()
            except Exception as e:
                rctlog.warning(f"刷新托盘状态失败: {e}")
            return True
        except Exception as e:
            rctlog.error(f"保存配置失败: {e}")
            messagebox.showerror("保存失败", f"保存配置时出错：\n{e}")
            return False

    # ── 按钮回调 ──────────────────────────────────────

    def _prompt_close(self):
        """关闭前检查是否有未应用的更改"""
        if self._collect_config() != self._init_config and not self._applied:
            if messagebox.askyesno("配置已更改", "配置已修改但尚未保存，是否立即应用？"):
                self._ok()
                return
        self.window.destroy()

    def _ok(self):
        """确定：应用更改并关闭窗口"""
        if self._collect_and_save():
            self._applied = True
            messagebox.showinfo("保存成功", "配置已保存。")
            self.window.destroy()

    def _apply(self):
        """应用：仅应用更改，不关闭窗口"""
        if self._collect_and_save():
            self._applied = True
            messagebox.showinfo("应用成功", "配置已应用。")

    # ── 旧的 _save 方法保留兼容引用 ──────────────────
    def _save(self):
        """兼容旧调用（等同于确定）"""
        self._ok()


# ══════════════════════════════════════════════════════════
# 便捷引用：将通用对话框暴露到 core.window 命名空间。
# 实现位于 core.dialog。
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
    """所有选项卡的公共基类。"""
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
    """主页选项卡：提供主功能入口。"""
    def __init__(self, parent):
        super().__init__(parent, "随机抽取工具")
        self.create_widgets()

    def create_widgets(self):
        version_label = tk.Label(
            self.frame,
            text=f"当前版本：{rct_version}",
            font=("Microsoft YaHei", 12),
            fg="purple",
        )
        version_label.pack(pady=(0, 12))

        # 主界面快捷入口
        btn_frame = tk.Frame(self.frame)
        btn_frame.pack(expand=True)

        buttons = [
            ("抽取", self.open_random_call, "#4a90d9"),
            ("点名", self.open_rollcall, "#8e44ad"),
            ("设置", self.open_config_window, "#16a085"),
            ("更新", self.open_update, "#e67e22"),
            ("关于", self.show_about, "#7f8c8d"),
            ("退出", self.quit_program, "#c0392b"),
        ]
        for i, (text, command, color) in enumerate(buttons):
            btn = self._make_home_button(btn_frame, text, command, color)
            btn.grid(row=i // 2, column=i % 2, padx=12, pady=8)

        start_time = strftime("%Y-%m-%d %H:%M:%S")
        start_label = tk.Label(
            self.frame,
            text=f"启动时间：{start_time}",
            font=("Microsoft YaHei", 12),
            fg="gray",
        )
        start_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=8)
    
    def _make_home_button(self, parent, text, command, color):
        """主页美化按钮：扁平色块 + 悬停变色 + 手型光标（无焦点高亮边框）"""
        return tk.Button(
            parent, text=text, command=command,
            font=("Microsoft YaHei", 12, "bold"),
            bg=color, fg="white",
            activebackground=self._darken(color),
            activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=0, takefocus=False,
            width=12, height=2,
        )

    @staticmethod
    def _darken(color, amount=32):
        """将颜色调暗，用于按钮悬停态"""
        try:
            c = color.lstrip("#")
            r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
            r = max(0, r - amount)
            g = max(0, g - amount)
            b = max(0, b - amount)
            return "#%02x%02x%02x" % (r, g, b)
        except Exception:
            return color

    def _select_tab(self, title):
        """按选项卡标题切换到对应页"""
        notebook = self.frame.master
        try:
            for i, tab_id in enumerate(notebook.tabs()):
                if notebook.tab(tab_id, "text") == title:
                    notebook.select(i)
                    return True
        except Exception as e:
            rctlog.warning(f"切换选项卡失败: {e}")
        return False

    def open_random_call(self):
        """打开随机抽取界面"""
        rctlog.info("打开随机抽取界面")
        self._select_tab("随机抽取")

    def open_rollcall(self):
        """打开随机点名界面"""
        rctlog.info("打开随机点名界面")
        self._select_tab("随机点名")

    def open_update(self):
        """打开更新程序"""
        rctlog.info("打开更新程序")
        try:
            config = ConfigManager()
            source = config.get("update_source", "github")
            accept_preview = config.get("accept_preview_update", False)
            from core.update import run_auto_update
            ok = run_auto_update(source=source, mode="--check",
                                 accept_preview=accept_preview)
            if not ok:
                messagebox.showerror("启动失败", "无法启动更新程序，请手动前往官网下载最新版本。")
        except Exception as e:
            rctlog.error(f"打开更新程序失败: {e}")
            messagebox.showerror("启动失败", f"无法启动更新程序：\n{e}")

    def open_config_window(self):
        """打开配置窗口"""
        rctlog.info("打开配置窗口")
        ConfigWindow(self.frame)

    def show_about(self):
        """显示关于信息（日志由 AboutWindow 统一记录）"""
        info = load_about_info()
        AboutWindow(self.frame.winfo_toplevel(), info, rct_icon_path)

    def quit_program(self):
        """退出程序：该按钮为整体关闭，需二次确认"""
        if not messagebox.askyesno("退出程序", "确定要退出随机抽取工具吗？"):
            return
        rctlog.info("程序正常退出")
        t = tray.get()
        if t is not None and t.active:
            t.quit_app()
        else:
            self.frame.winfo_toplevel().destroy()

class RandomCallTab(BaseTab):
    """随机抽取选项卡：支持抽人、抽组和历史记录管理。"""

    # 历史记录面板固定宽度（保证每条记录都与面板等宽）
    HISTORY_PANEL_WIDTH = 160
    HISTORY_CANVAS_WIDTH = 140
    HISTORY_ROW_PADX = 4
    # 条目文字换行宽度：画布宽减去条目内边距
    HISTORY_TEXT_WRAP = HISTORY_CANVAS_WIDTH - 2 * HISTORY_ROW_PADX - 12
    # 样本名显示：固定单行，超出该像素宽度用省略号截断
    SAMPLE_NAME_FONT = ("Microsoft YaHei", 12)
    SAMPLE_NAME_MAX_WIDTH = 220

    def __init__(self, parent, start_args=None):
        super().__init__(parent, "随机抽取")
        self._start_args = start_args
        config = ConfigManager()
        self.mode_var = tk.StringVar(value=config.get("rct_default_mode", "person"))
        self.mode_var.trace_add("write", self._on_mode_changed)

        sampler_mode = config.get("sampler_mode", 0)
        # 「记忆次数」以高级抽取配置（adv_smart_memory_count）为准，兼容旧的 smart_window
        smart_window = config.get("adv_smart_memory_count",
                                  config.get("smart_window", 3))
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
        # -file 指定外部文件：启动时自动加载并应用权重
        if self._start_args is not None and self._start_args.target_files:
            self._load_start_file()

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
        self.person_frame = tk.LabelFrame(self.control_frame, text="样本列表", height=120)
        self.person_frame.pack_propagate(False)

        # 样本信息行：名称（紫色）+ 数量（绿色），名称固定单行、超宽用省略号
        info_row = tk.Frame(self.person_frame)
        info_row.pack(pady=5, padx=5)
        self.file_path_label = tk.Label(
            info_row, text="未选择文件", fg="gray",
            font=self.SAMPLE_NAME_FONT,
        )
        self.file_path_label.pack(side="left")
        self.sample_count_label = tk.Label(info_row, text="", fg="green",
                                           font=self.SAMPLE_NAME_FONT)
        self.sample_count_label.pack(side="left")

        btn_row = tk.Frame(self.person_frame)
        btn_row.pack(pady=5)
        load_actions = [
            ("选择文件", self.load_names, "#6a1b9a", "#4a148c"),
            ("从样本库", self.load_from_library, "#2e7d32", "#1b5e20"),
            ("重新加载", self.reload_current_file, "#5d4037", "#3e2723"),
            ("自动加载", self.auto_load_file, "#c2185b", "#880e4f"),
        ]
        for text, cmd, color, active in load_actions:
            tk.Button(
                btn_row, text=text, command=cmd,
                font=("Microsoft YaHei", 10, "bold"),
                bg=color, fg="white",
                activebackground=active, activeforeground="white",
                relief="flat", bd=0, cursor="hand2",
                highlightthickness=0, takefocus=False,
                padx=10, pady=5,
            ).pack(side="left", padx=3)


        # ----- 抽组控件（LabelFrame，固定最小高度，与样本列表统一）-----
        self.group_frame = tk.LabelFrame(self.control_frame, text="抽组设置", height=120)
        self.group_frame.pack_propagate(False)

        order_row = tk.Frame(self.group_frame)
        order_row.pack(pady=5)
        tk.Label(order_row, text="分组方式：").pack(side="left")
        for text, val in [("123（数字）", "123"), ("ABC（字母）", "ABC")]:
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

        tk.Label(self.group_frame, text="最多支持 26 个组；触屏设备可在选择框上滑动选择",
                 fg="gray", font=("", 8)).pack(pady=(0, 4))

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

        # ── 抽取：醒目主按钮（居中，适当加高） ──
        self.draw_btn = tk.Button(
            inner_btns, text="抽  取", command=self.draw,
            font=("Microsoft YaHei", 16, "bold"),
            bg="#4a90d9", fg="white",
            activebackground="#357abd", activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=0, takefocus=False,
            width=10, height=1,
        )
        self.draw_btn.grid(row=0, column=0, columnspan=3, padx=4, pady=(2, 6))

        # ── 次要操作：一行三个彩色按钮 ──
        sub_actions = [
            ("保存当前结果", self.save_current_result, "#16a085", "#11806a"),
            ("清空历史记录", self.clear_all_history, "#7f8c8d", "#616a6b"),
            ("重置抽样历史", self.reset_sampler_history, "#e67e22", "#cf6d17"),
        ]
        for j, (text, cmd, color, active) in enumerate(sub_actions):
            btn = tk.Button(
                inner_btns, text=text, command=cmd,
                font=("Microsoft YaHei", 10, "bold"),
                bg=color, fg="white",
                activebackground=active, activeforeground="white",
                relief="flat", bd=0, cursor="hand2", height=1,
                highlightthickness=0, takefocus=False,
            )
            btn.grid(row=1, column=j, sticky="ew", padx=4, pady=2)
        for j in range(3):
            inner_btns.grid_columnconfigure(j, weight=1)

        # 初始模式
        self._switch_mode()

    def _create_history_area(self, parent):
        """创建右侧历史记录面板"""
        hist_frame = tk.LabelFrame(parent, text="历史记录",
                                   width=self.HISTORY_PANEL_WIDTH)
        hist_frame.pack(side="right", fill="y", padx=(10, 0))
        hist_frame.pack_propagate(False)

        canvas = tk.Canvas(hist_frame, highlightthickness=0,
                           width=self.HISTORY_CANVAS_WIDTH)
        vbar = tk.Scrollbar(hist_frame, orient="vertical", command=canvas.yview)
        self.history_inner = tk.Frame(canvas)

        self.history_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._history_win_id = canvas.create_window(
            (0, 0), window=self.history_inner, anchor="nw")
        # 让内部容器始终等于画布宽度，条目才能与面板等宽
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._history_win_id, width=e.width),
        )
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
            # 恢复抽取数量范围为组选取数量（与抽人一致：保留当前值，仅在超范围时收窄）
            try:
                total = int(self.total_entry.get())
                self.choice_entry["values"] = list(range(1, min(total + 1, 27)))
                cur = self.choice_entry.get()
                if not cur or int(cur) > total:
                    self.choice_entry.set(str(min(
                        ConfigManager().get("rct_choice_default", 3), total)))
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
                messagebox.showwarning("参数不足", "请先设置抽组的组数等参数。")
                return

        if not items:
            messagebox.showwarning("无可抽样本", "当前没有可用的样本。")
            return

        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title("权重设置")
        win.geometry("420x480+100+100")
        win.transient(self.frame.winfo_toplevel())
        set_window_icon(win, rct_icon_path)
        win.grab_set()
        win.minsize(300, 300)

        top_frame = tk.Frame(win)
        top_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(top_frame, text="为每个样本设置权重（≥0，默认 1.0）",
                 font=("", 10, "bold"), fg="blue").pack(anchor="w")
        tk.Label(top_frame, text="权重越高，被抽中的概率越大",
                 font=("", 9), fg="gray").pack(anchor="w")

        # "使用固定权重" 勾选项（use_fixed_var 变量先创建，控件在下方函数定义后创建）
        use_fixed_var = tk.BooleanVar(value=self.sampler.use_fixed_weights)

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
        # WM_DELETE_WINDOW 在下方 _prompt_and_close 中设置

        # 为每个项目创建权重输入框
        weight_vars = {}
        weight_entries = {}
        weight_labels = {}  # 存储权重状态 Label 引用
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
            weight_labels[item] = tk.Label(row, text="", fg="gray", font=("", 8))
            weight_labels[item].pack(side="left")

        def _update_weight_display():
            """根据固定权重勾选状态，切换显示智能权重或固定权重"""
            fixed_on = use_fixed_var.get()
            for item in items:
                if fixed_on:
                    weight_labels[item].config(
                        text=f"固定：{self.sampler.get_weight(item):.1f}")
                else:
                    smart_w = self.sampler.get_smart_effective_weight(item)
                    weight_labels[item].config(
                        text=f"智能：{smart_w:.1f}")
            # 同步切换输入框可编辑状态
            state = "normal" if fixed_on else "readonly"
            for entry in weight_entries.values():
                entry.config(state=state)

        # 创建复选框（必须在 _update_weight_display 定义之后）
        fixed_cb = tk.Checkbutton(
            top_frame, text="使用固定权重（勾选后可修改，不勾选仅查看智能权重）",
            variable=use_fixed_var,
            command=_update_weight_display,
            font=("", 9),
        )
        fixed_cb.pack(anchor="w", pady=(5, 5))

        # 初始显示
        _update_weight_display()

        # 记录初始状态，用于检测改动
        _init_use_fixed = use_fixed_var.get()
        _init_weights = {item: var.get() for item, var in weight_vars.items()}
        _applied = False

        def _has_weight_changes():
            if use_fixed_var.get() != _init_use_fixed:
                return True
            for item, var in weight_vars.items():
                if var.get() != _init_weights.get(item):
                    return True
            return False

        def save_weights():
            nonlocal _applied
            self.sampler.use_fixed_weights = use_fixed_var.get()
            for item, var in weight_vars.items():
                try:
                    w = float(var.get().strip())
                    self.sampler.set_weight(item, w)
                except ValueError:
                    messagebox.showwarning(
                        "权重无效", f"「{item}」的权重值不是有效数字，已跳过。")
                    continue
            # 同步高级模式的自定义权重开关
            self.sampler.advanced_config["custom_weights"] = self.sampler.use_fixed_weights
            _applied = True
            rctlog.info(f"权重已更新 ({len(weight_vars)} 项), 固定权重={self.sampler.use_fixed_weights}")
            messagebox.showinfo("保存成功", "权重已保存。")
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        def _prompt_and_close():
            if _has_weight_changes() and not _applied:
                if messagebox.askyesno("权重已更改", "权重已修改但尚未保存，是否立即应用？"):
                    save_weights()
                    return
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(btn_frame, text="应用", command=save_weights, width=12).pack(side="left", padx=3)
        tk.Button(btn_frame, text="重置",
                  command=lambda: [var.set("1.0") for var in weight_vars.values()],
                  width=15).pack(side="left", padx=3)
        tk.Button(btn_frame, text="取消", command=_prompt_and_close, width=8).pack(side="left", padx=3)
        # 窗口关闭也触发提醒
        win.protocol("WM_DELETE_WINDOW", _prompt_and_close)

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

    def _set_sample_info(self, name_text, count=None):
        """更新样本信息行：名称紫色、固定单行，数量用 (绿色) 紧随其后"""
        self.file_path_label.config(
            text=self._ellipsize(name_text, self.SAMPLE_NAME_MAX_WIDTH), fg="purple")
        if count is None:
            self.sample_count_label.config(text="")
        else:
            self.sample_count_label.config(text=f" ({count})", fg="green")

    def _ellipsize(self, text, max_width):
        """把文本按像素宽度截断为单行，超出部分用省略号

        Tkinter 的 Label 不支持自动省略号，因此用字体实测宽度后手动截断。
        """
        text = str(text)
        font = tkFont.Font(font=self.SAMPLE_NAME_FONT)
        if font.measure(text) <= max_width:
            return text
        for cut in range(len(text) - 1, 0, -1):
            if font.measure(text[:cut] + "…") <= max_width:
                return text[:cut] + "…"
        return "…"

    def _start_args_matches(self):
        """当前已加载样本是否符合启动参数限定的目标。"""
        sa = self._start_args
        if sa is None:
            return False
        # 未指定 -lib/-file：全局生效
        if not sa.target_libs and not sa.target_files:
            return True
        if not self.current_file:
            return False
        cur = os.path.normpath(self.current_file)
        # 样本库来源：样本名命中 -lib 列表
        if os.path.dirname(cur) == os.path.normpath(rct_rcplist_path):
            stem = os.path.splitext(os.path.basename(cur))[0]
            return stem in sa.target_libs
        # 外部文件命中 -file 列表：
        #   值为纯文件名（无目录）→ 任何路径下同名文件皆命中；
        #   值带目录（绝对/相对路径）→ 仅匹配该具体文件，
        #     相对路径基于工作目录解析。
        base = os.path.basename(cur)
        for target in sa.target_files:
            tnorm = os.path.normpath(target)
            if os.path.basename(tnorm) == tnorm:
                if base == tnorm:
                    return True
            else:
                if not os.path.isabs(tnorm):
                    tnorm = os.path.normpath(os.path.join(work_path, target))
                if cur == tnorm:
                    return True
        return False

    def _apply_start_args(self):
        """按启动参数对当前样本应用自定义权重（仅本次运行，不落盘）。"""
        sa = self._start_args
        if sa is None or not sa.has_rules() or not self.names:
            return
        if not self._start_args_matches():
            rctlog.info("[启动参数] 当前样本不是限定目标，跳过权重设置")
            return
        applied = []
        for name, w in sa.weight_sets:
            if name in self.names:
                self.sampler.set_weight(name, w)
                applied.append("%s=%s" % (name, w))
        if not applied:
            rctlog.info("[启动参数] 当前样本中没有指定名字，未设置权重")
            return
        # 让权重在当前模式下真正生效
        self.sampler.advanced_config["custom_weights"] = True
        self.sampler.use_fixed_weights = True
        if self.sampler.mode == SmartSampler.MODE_BASIC:
            self.sampler.set_mode(SmartSampler.MODE_ADVANCED)
            rctlog.info("[启动参数] 基本模式不支持权重，已切换为高级抽样模式")
        rctlog.info("[启动参数] 已应用自定义权重：" + "，".join(applied))

    def _load_start_file(self):
        """启动参数 -file：自动加载第一个存在的指定外部文件并应用权重。"""
        sa = self._start_args
        loaded = None
        for target in sa.target_files:
            path = target
            if not os.path.isabs(path):
                cand = os.path.join(work_path, path)
                if os.path.isfile(cand):
                    path = cand
            if os.path.isfile(path):
                loaded = path
                break
        if loaded is None:
            rctlog.warning("[启动参数] 指定文件均不存在，已跳过自动加载: %s"
                           % "，".join(sa.target_files))
            return
        names, extra = self._load_names_from_file(loaded)
        if not names:
            return
        self.names = names
        self.current_file = loaded
        self.sampler.reset_no_replace_pool()
        self.choice_entry["values"] = list(range(1, len(names) + 1))
        self._apply_start_args()

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
            self._set_sample_info(f"样本库：{default_name}", len(names))
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 自动加载样本库: {default_name}, 共 {len(names)} 个名字")
            self._apply_start_args()

    # ══════════════════════════════════════════════════════════
    #  文件加载（抽人）
    # ══════════════════════════════════════════════════════════

    def _load_names_from_file(self, file_path=None):
        """从文件加载名字，返回 (names, additional_messages)"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("可用文件", "*.rcp;*.txt;*.csv"),
                    ("RCP 名单文件", "*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV 文件", "*.csv"),
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
            if file_path.endswith(".rcp"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = self._decode_rcp(f.read())
                truncated = False
            else:
                content, truncated = read_text_file(file_path)

            names = parse_names(content)

            if truncated:
                mb = MAX_FILE_BYTES // (1024 * 1024)
                extra.append(f"文件超过 {mb}MB，只读取了前 {mb}MB 内容")
            # 用不截断的解析结果判断是否真的超过上限，避免恰好 1000 个时误报
            if len(parse_names(content, limit=10 ** 9)) > MAX_NAMES:
                extra.append(f"名单过长，只读取了前 {MAX_NAMES} 个名字")

            config = ConfigManager()
            if config.get("rct_merge_names", True):
                if len(names) != len(set(names)):
                    # 保序去重，避免 set 打乱原始名单顺序
                    names = list(dict.fromkeys(names))
                    extra.append("文件中存在重复的名字，已自动去除")
            else:
                if len(names) != len(set(names)):
                    extra.append("文件中存在重复的名字，已保留")

            if not names:
                messagebox.showwarning("文件为空", "文件中没有可用的名单数据。")
                return [], extra

            self._set_sample_info(
                ("默认样本：" if file_path == self.auto_file else "样本文件：")
                + os.path.basename(file_path),
                len(names),
            )

            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            self.current_file = file_path

            rctlog.info(f"[随机抽取] 成功加载 {len(names)} 个名字")
            return names, extra

        except Exception as e:
            rctlog.error(f"[随机抽取] 读取文件失败: {e}")
            messagebox.showerror("读取失败", f"读取文件时出错：\n{e}")
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
            self._apply_start_args()
            msg = f"已加载 {len(names)} 个名字。"
            if extra:
                msg += "\n" + "\n".join(extra)
            messagebox.showinfo("加载成功", msg)
            # 样本库为空时，询问是否将该文件导入到样本库
            if not SampleLibrary.get_samples():
                self._prompt_import_to_library(self.current_file)

    def _prompt_import_to_library(self, file_path):
        """样本库为空时，提示把刚打开的文件导入到样本库"""
        if not file_path or not os.path.isfile(file_path):
            return
        if not messagebox.askyesno(
                "导入到样本库",
                "样本库当前为空。\n是否将刚刚打开的文件导入到样本库？"):
            return
        try:
            from core.appfunc import ApplicationFunctions
            ApplicationFunctions.import_sample(
                parent=self.frame.winfo_toplevel(), source_path=file_path)
        except Exception as e:
            rctlog.error(f"[随机抽取] 导入到样本库失败: {e}")
            messagebox.showerror("导入失败", f"导入到样本库时出错：\n{e}")

    def reload_current_file(self):
        """重新加载当前文件"""
        if self.current_file and os.path.exists(self.current_file):
            names, extra = self._load_names_from_file(self.current_file)
            if names:
                self.names = names
                self.sampler.reset_no_replace_pool()
                self._apply_start_args()
                msg = f"已重新加载，共 {len(names)} 个名字。"
                if extra:
                    msg += "\n" + "\n".join(extra)
                messagebox.showinfo("加载成功", msg)

    def load_from_library(self):
        """从样本库选择样本加载"""
        samples = SampleLibrary.get_samples()
        if not samples:
            messagebox.showwarning("样本库为空", "样本库为空，请先导入样本。")
            return
        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title("选择样本")
        win.geometry("380x420+150+150")
        win.transient(self.frame.winfo_toplevel())
        set_window_icon(win, rct_icon_path)
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
            self._set_sample_info(f"样本库：{name}", len(names))
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 从样本库加载: {name}, 共 {len(names)} 个名字")
            self._apply_start_args()
            messagebox.showinfo("加载成功", f"已加载样本「{name}」，共 {len(names)} 个名字。")
            win.destroy()
        else:
            messagebox.showwarning("样本无效", f"样本「{name}」为空或内容无效。")

    def auto_load_file(self):
        """自动加载默认样本（从样本库）"""
        config = ConfigManager()
        default_name = config.get("rct_default_sample", "")
        if not default_name:
            messagebox.showwarning(
                "未设置默认样本",
                "尚未设置默认样本，请先到「配置 → 基本设置」中选择「默认加载样本」。")
            return
        names = SampleLibrary.load_names(default_name)
        if names:
            self.names = names
            self.sampler.reset_no_replace_pool()
            self.current_file = os.path.join(rct_rcplist_path, f"{default_name}.rcp")
            self._set_sample_info(f"样本库：{default_name}", len(names))
            mx = len(names)
            self.choice_entry["values"] = list(range(1, mx + 1))
            rctlog.info(f"[随机抽取] 自动加载样本库: {default_name}, 共 {len(names)} 个名字")
            self._apply_start_args()
            messagebox.showinfo("加载成功", f"已加载默认样本「{default_name}」，共 {len(names)} 个名字。")
        else:
            messagebox.showwarning("默认样本无效", f"默认样本「{default_name}」不存在或内容无效。")

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
            messagebox.showwarning("未加载样本", "请先加载样本文件。")
            return

        try:
            k = int(self.choice_entry.get())
        except (ValueError, TypeError):
            messagebox.showwarning("未选择数量", "请先选择抽取数量。")
            return

        if k < 1:
            return
        if k > len(self.names):
            messagebox.showwarning(
                "数量超出范围",
                f"抽取数量（{k}）超过了样本数量（{len(self.names)}），请重新选择。")
            return
        if k == len(self.names) and not messagebox.askyesno(
                "抽取数量与样本总数相同", "确定要抽取全部人员吗？"):
            return

        selected = self.sampler.smart_sample(self.names, k)

        preview = ", ".join(selected[:8]) + ("..." if len(selected) > 8 else "")
        oversized = self._is_oversized(selected)
        self._add_history("person", selected, f"抽{k}人：{preview}", force=oversized)

        rctlog.info(f"[随机抽取] 抽人成功: {selected}")
        if oversized:
            self._handle_oversized("RandomPerson", "随机抽人", selected)
        else:
            self._notify_result("抽取结果", selected)
            if ConfigManager().get("save_result", True):
                SaveResult().save_result("RandomPerson", "随机抽人", selected)

    def _draw_group(self):
        """随机抽组"""
        try:
            total = int(self.total_entry.get())
            k = int(self.choice_entry.get())
        except (ValueError, TypeError):
            messagebox.showwarning("参数无效", "请选择有效的数字。")
            return

        if total < 1:
            messagebox.showwarning("参数无效", "样本总数不能小于 1。")
            return
        if k < 1:
            messagebox.showwarning("参数无效", "抽取数量不能小于 1。")
            return
        if k > total:
            messagebox.showwarning("参数无效", "抽取数量不能大于样本总数。")
            return
        if k == total and not messagebox.askyesno(
                "抽取数量与组总数相同", "确定要抽取全部组吗？"):
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
        oversized = self._is_oversized(result_items)
        self._add_history("group", result_items, f"抽{k}组：{preview}", force=oversized)

        rctlog.info(f"[随机抽取] 抽组成功: {selected}")
        if oversized:
            self._handle_oversized("RandomGroup", "随机抽组", result_items)
        else:
            self._notify_result("抽取结果", result_items)
            if ConfigManager().get("save_result", True):
                SaveResult().save_result("RandomGroup", "随机抽组", result_items)

    # ══════════════════════════════════════════════════════════
    #  抽取后提醒
    # ══════════════════════════════════════════════════════════

    def _notify_result(self, title, items):
        """抽取后提醒：按配置选择「弹窗」或「ClassIsland 通知」"""
        notify_result(title, items, default_mask_title="随机抽取结果")

    @staticmethod
    def _is_oversized(items):
        """结果是否超过提醒数量上限（大于 10 个才省略）"""
        return len(items) > OVERSIZED_LIMIT

    def _handle_oversized(self, class_name, prefix, items):
        """结果超过 10 个：提醒中省略多余项，强制保存完整结果并引导查看

        - 弹窗 / ClassIsland 通知只带前 10 项
        - 不受「自动保存抽取结果」开关影响，强制落盘 HTML
        - 再次弹窗提醒，并用浏览器以 file:// 打开该 HTML
        """
        shown = list(items[:OVERSIZED_LIMIT])
        rest = len(items) - len(shown)
        self._notify_result("抽取结果", shown + [f"……（其余 {rest} 个已省略）"])

        path = SaveResult().save_result(class_name, prefix, items, silent=True)
        if not path:
            messagebox.showwarning(
                "完整结果保存失败",
                f"本次共抽取 {len(items)} 个，提醒中已省略超出 {OVERSIZED_LIMIT} 个的部分。"
                "\n\n完整结果保存失败，请到历史记录中手动保存后查看。")
            return

        rctlog.info(f"[{prefix}] 结果超过 {OVERSIZED_LIMIT} 个，"
                    f"已强制保存并打开完整结果: {path}")
        tip = "已自动打开" if self._open_result_html(path) else "打开失败，请手动打开"
        messagebox.showinfo(
            "结果较多，请查看完整结果",
            f"本次共抽取 {len(items)} 个，提醒中已省略超出 {OVERSIZED_LIMIT} 个的部分。"
            f"\n\n完整结果已保存为 HTML（{tip}）：\n{path}")

    @staticmethod
    def _open_result_html(path):
        """用系统默认程序打开结果 HTML

        不用 file:// URI：Windows 上会走 file: 协议处理器（旧 IE / Edge），可能被重定向到
        帮助页而打不开文件。直接传普通路径等同于双击，会交给用户默认浏览器。
        都失败时退回打开所在目录，保证用户能找到文件。
        """
        try:
            open_file_or_dir(path)
            return True
        except Exception as e:
            rctlog.warning(f"[随机抽取] 打开结果文件失败: {e}")
        folder = os.path.dirname(path)
        try:
            open_file_or_dir(folder)
            rctlog.info(f"[随机抽取] 已改为打开结果目录: {folder}")
        except Exception as e:
            rctlog.error(f"[随机抽取] 打开结果目录也失败: {e}")
        return False

    # ══════════════════════════════════════════════════════════
    #  历史记录
    # ══════════════════════════════════════════════════════════

    def _add_history(self, mode, items, preview, force=False):
        """添加一条历史记录并刷新UI（force=True 时强制写入记录文件）"""
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
        # 同步追加到 data/history/YYYY-MM-DD.txt，失败不影响抽取主流程
        try:
            history_append(mode, items, entry["ts_short"], force=force)
        except Exception as e:
            rctlog.warning(f"[随机抽取] 写入历史记录文件失败: {e}")

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
            row.pack(fill="x", padx=self.HISTORY_ROW_PADX, pady=2)

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
                wraplength=self.HISTORY_TEXT_WRAP,
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

        win = tk.Toplevel(self.frame.winfo_toplevel())
        win.title(f"历史记录 #{entry['id']}")
        # 固定窗口位置：距屏幕上方、左侧各 100 像素
        win.geometry("400x300+100+100")
        win.transient(self.frame.winfo_toplevel())
        set_window_icon(win, rct_icon_path)
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
            messagebox.showinfo("暂无历史记录", "暂无历史记录。")
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
        messagebox.showinfo("批量保存完成", f"已保存 {saved} / {len(self.history)} 条记录。")

    def _prompt_save_message(self):
        """弹窗输入保存提示信息

        Returns:
            str: 用户输入的提示信息（可能为空字符串）
            None: 用户点了取消或关闭窗口
        """
        return ask_string(
            "保存提示", "请输入保存提示信息（留空则不显示提示）：",
            parent=self.frame.winfo_toplevel(),
        )

    # ══════════════════════════════════════════════════════════
    #  保存当前结果
    # ══════════════════════════════════════════════════════════

    def save_current_result(self):
        """保存当前抽取结果（取自最新一条历史记录）"""
        if not self.history:
            messagebox.showwarning("暂无结果", "暂无抽取结果可保存。")
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
        """清空历史面板，同时删除本地记录文件"""
        if not messagebox.askyesno(
                "清除历史记录",
                "确定要清除全部历史记录吗？\n\n"
                "将同时删除 data/history 下的全部记录文件，清除后无法恢复。"):
            return
        self.history.clear()
        self._rebuild_history_ui()
        removed = history_clear_files()
        rctlog.info(f"历史记录已清除，删除记录文件 {removed} 个")
        messagebox.showinfo("清除成功", f"历史记录已清除，同时删除 {removed} 个记录文件。")

    # ══════════════════════════════════════════════════════════
    #  重置抽样历史
    # ══════════════════════════════════════════════════════════

    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("重置抽样历史", "确定要重置抽样历史与统计计数吗？"):
            self.sampler.reset_history()
            messagebox.showinfo("重置成功", "抽样历史记录已重置。")

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
        self._applied = False
        # 创建控件后再收集初始快照（控件在后续流程创建）
        self.win.geometry("470x610+80+80")
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
        def _prompt_close():
            if self._collect_config() != self._init_config and not self._applied:
                if messagebox.askyesno("配置已更改", "高级抽取配置已修改但尚未保存，是否立即应用？"):
                    self._apply()
                    return
            canvas.unbind_all("<MouseWheel>")
            self.win.destroy()
        self.win.protocol("WM_DELETE_WINDOW", _prompt_close)

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

        tk.Label(sec1,
                 text="连续循环样本：抽完剩余名字后接着下一轮补齐；\n"
                      "整除式重载：剩余不足一轮时直接重载整轮；\n"
                      "比率式调整：剩余低于阈值比率时提前重载。",
                 fg="gray", font=("", 8), justify="left"
                 ).pack(anchor="w", padx=20, pady=(0, 4))

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
        tk.Label(f_multi, text="（取被抽次数最多的前 k 个）", fg="gray", font=("", 8)).pack(side="left")

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
        tk.Label(f_smart, text="（统计最近 N 次抽取，自动降权）", fg="gray", font=("", 8)).pack(side="left")

        # --- 加权说明 ---
        tk.Label(
            self.sec3,
            text="说明：放回式下加权抽取为「有放回」，同一样本可能被重复抽中；\n"
                 "不放回式下始终按随机顺序抽取，不重复，也不叠加权重。",
            fg="gray", font=("", 8), justify="left", anchor="w",
        ).pack(fill="x", pady=(4, 2))

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
            f_custw, text="查看权重设置",
            command=self._open_weight_from_advanced,
            width=12,
            relief="groove", bd=1,
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
        tk.Button(btn_frame, text="取消", command=_prompt_close,
                  width=8).pack(side="left", padx=5)

        # 存储控件引用（用于冲突禁用）
        self._shuffle_widgets = [self.shuffle_spin]
        self._pre_draw_widgets = [self.pre_draw_spin]
        self._all_optimize_widgets = []  # 将在 _apply_conflicts 中动态处理

        # 初始状态
        self._on_replacement_change()
        # 记录初始配置快照
        self._init_config = self._collect_config()

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

        # 不放回时强制禁用权重相关控件
        if not is_replacement:
            self.custw_cb.config(state="disabled")
            self.custw_btn.config(state="disabled")

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
        self._applied = True
        rctlog.info("高级抽取配置已应用")
        messagebox.showinfo("应用成功", "高级抽取配置已应用。")
        if self.on_apply:
            self.on_apply()

    def _ok(self):
        """确定并关闭"""
        self._save_to_sampler()
        self._save_to_global_config()
        self._applied = True
        rctlog.info("高级抽取配置已保存")
        if self.on_apply:
            self.on_apply()
        self.win.destroy()

    def _reset_defaults(self):
        """恢复默认配置"""
        if not messagebox.askyesno("恢复默认配置", "确定要将高级抽取配置恢复为默认值吗？"):
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
        messagebox.showinfo("已恢复默认", "高级抽取配置已恢复为默认值。")

    def _open_weight_from_advanced(self):
        """从高级窗口打开权重设置"""
        if self.on_open_weights:
            # 继承"自定义权重"勾选状态到权重窗口
            self.sampler.use_fixed_weights = self.custw_var.get()
            self.on_open_weights()
        else:
            messagebox.showinfo(
                "无可设置的样本",
                "请先在「随机抽取」页加载样本，再点击此按钮设置权重。"
            )
