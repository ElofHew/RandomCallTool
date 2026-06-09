"""
选项卡界面模块 — 主页、随机抽取
"""
import os
from time import strftime
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, filedialog
from core.info import rct_rcplist_path, rct_version, document_path
from core.logman import rctlog
from rctcore.config import ConfigManager
from rctcore.window import ConfigWindow, AboutWindow
from rctcore.sampler import SmartSampler
from rctcore.fileman import SaveResult, base64decode, SampleLibrary

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
        AboutWindow(self.frame.winfo_toplevel())

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
        for text, val in [("随机抽人", "person"), ("随机抽组", "group")]:
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
        self.group_frame = tk.LabelFrame(self.control_frame, text="组设置", height=130)
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
            values=["基本抽样", "智能抽样", "加权抽样"],
            state="readonly", width=12,
        )
        self.sampler_mode_combo.pack(side="left", padx=5)
        self.sampler_mode_combo.set(SmartSampler.MODE_NAMES[self.sampler_mode_var.get()])
        self.sampler_mode_combo.bind("<<ComboboxSelected>>", self._on_sampler_mode_change)

        self.weight_btn = tk.Button(
            inner_top, text="权重", command=self._open_weight_config,
            state="disabled", width=5,
        )
        self.weight_btn.pack(side="left")

        inner_btns = tk.Frame(self.action_frame)
        inner_btns.pack(fill="x", padx=8, pady=(2, 6))
        actions = [
            ("抽取", self.draw),
            ("保存结果", self.save_current_result),
            ("清空历史", self.clear_all_history),
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
        hist_frame = tk.LabelFrame(parent, text="历史记录", width=280)
        hist_frame.pack(side="right", fill="y", padx=(10, 0))
        hist_frame.pack_propagate(False)

        canvas = tk.Canvas(hist_frame, highlightthickness=0, width=260)
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
        # 加权模式才显示"设置权重"按钮
        if idx == SmartSampler.MODE_WEIGHTED:
            self.weight_btn.config(state="normal")
        else:
            self.weight_btn.config(state="disabled")
        rctlog.info(f"抽样模式切换为: {SmartSampler.MODE_NAMES[idx]}")

    def _open_weight_config(self):
        """打开权重设置窗口"""
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
        win.geometry("420x450+100+100")
        win.transient(self.frame.winfo_toplevel())
        win.grab_set()
        win.minsize(300, 250)

        top_frame = tk.Frame(win)
        top_frame.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(top_frame, text="为每个样本设置权重（≥0，默认 1.0）",
                 font=("", 10, "bold"), fg="blue").pack(anchor="w")
        tk.Label(top_frame, text="权重越高，被抽中的概率越大",
                 font=("", 9), fg="gray").pack(anchor="w")

        # 可滚动区域（容器撑满）
        body_frame = tk.Frame(win)
        body_frame.pack(fill="both", expand=True, padx=10, pady=10)

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

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()))

        # 为每个项目创建权重输入框
        weight_vars = {}
        for item in items:
            row = tk.Frame(inner)
            row.pack(fill="x", pady=2, padx=5)
            label_text = str(item) + ("组" if self.mode_var.get() == "group" and isinstance(item, int) else "")
            tk.Label(row, text=label_text, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(self.sampler.get_weight(item)))
            entry = tk.Entry(row, textvariable=var, width=10)
            entry.pack(side="left", padx=5)
            weight_vars[item] = var
            tk.Label(row, text=f"(当前: {self.sampler.get_weight(item):.1f})",
                     fg="gray", font=("", 8)).pack(side="left")

        def save_weights():
            for item, var in weight_vars.items():
                try:
                    w = float(var.get().strip())
                    self.sampler.set_weight(item, w)
                except ValueError:
                    messagebox.showwarning("无效输入", f"'{item}' 的权重值无效，已跳过")
                    continue
            rctlog.info(f"权重已更新 ({len(weight_vars)} 项)")
            messagebox.showinfo("成功", "权重已保存")
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(btn_frame, text="保存权重", command=save_weights, width=12).pack(side="left", padx=3)
        tk.Button(btn_frame, text="全部重置为 1.0",
                  command=lambda: [var.set("1.0") for var in weight_vars.values()],
                  width=15).pack(side="left", padx=3)
        tk.Button(btn_frame, text="取消",
                  command=lambda: (canvas.unbind_all("<MouseWheel>"), win.destroy()),
                  width=8).pack(side="left", padx=3)

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
        """弹窗输入保存提示信息，留空则无提示"""
        from tkinter import simpledialog
        result = simpledialog.askstring(
            "保存提示", "输入保存提示信息（留空则无提示）:",
            parent=self.frame.winfo_toplevel(),
        )
        return result if result else ""

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
