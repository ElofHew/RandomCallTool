"""
随机点名模块 — 跑马灯式手动点名（第一版草稿）

功能说明：
  与「随机抽取/随机抽人」不同，点名采用类似跑马灯的形式：
  点「开始点名」后名单里的名字快速跳动，点「停止」则定格显示当前名字。

名单来源：
  与随机抽人一致，使用样本库中的 RCP 名单（data/rcplist/）。

当前版本仅提供手动点名；后续计划参照随机抽人扩展：
  自动点名、点名优化等高级功能。
"""
import random
import tkinter as tk
from tkinter import ttk, messagebox

from core.logman import rctlog
from core.config import ConfigManager
from core.fileman import SampleLibrary
from core.window import BaseTab


class RollCallTab(BaseTab):
    """随机点名选项卡 — 第一版仅手动点名"""

    ROLL_INTERVAL_MS = 70   # 滚动时名字切换间隔（毫秒）
    NAME_FONT_SIZE = 40    # 名字显示字号（固定，避免点名时 UI 跳变）

    def __init__(self, parent):
        super().__init__(parent, "随机点名")
        self.parent = parent

        self.names = []            # 当前名单（名字列表）
        self.sample_name = ""      # 当前样本名
        self._after_id = None      # 滚动定时器句柄
        self.rolling = False       # 是否正在滚动
        self._current = ""         # 当前显示的名字

        self._build_ui()
        self._auto_load_default()

    # ══════════════════════════════════════════════════════════
    #  界面构建
    # ══════════════════════════════════════════════════════════

    def _build_ui(self):
        # ── 名单来源（居中） ──
        src = tk.Frame(self.frame)
        src.pack(pady=8)
        tk.Label(src, text="名单：", font=("", 10)).pack(side="left")
        self.sample_var = tk.StringVar()
        self.sample_combo = ttk.Combobox(src, textvariable=self.sample_var,
                                         state="readonly", width=22)
        self.sample_combo.pack(side="left", padx=4)
        self._refresh_samples()
        tk.Button(src, text="加载", command=self._load_selected,
                  bg="#4a90d9", fg="white", relief="flat", padx=10,
                  cursor="hand2").pack(side="left", padx=2)

        self.info_var = tk.StringVar(value="尚未加载名单")
        tk.Label(self.frame, textvariable=self.info_var,
                 font=("", 9), fg="gray").pack(pady=(0, 2))

        # ── 中部：点名名字 + 控制按钮（整体垂直居中） ──
        mid = tk.Frame(self.frame)
        mid.pack(fill="both", expand=True)
        content = tk.Frame(mid)
        content.pack(expand=True)

        self.name_label = tk.Label(content, text="准备就绪",
                                   font=("Microsoft YaHei",
                                         self.NAME_FONT_SIZE, "bold"),
                                   fg="#bbbbbb", bg="#fdfdfd",
                                   relief="groove", bd=2, width=12, height=2)
        self.name_label.pack(pady=(6, 0))

        btns = tk.Frame(content)
        btns.pack(pady=24)
        self.start_btn = tk.Button(btns, text="开始点名", command=self.start,
                                   font=("Microsoft YaHei", 12, "bold"),
                                   bg="#e67e22", fg="white",
                                   activebackground="#cf6d17",
                                   activeforeground="white",
                                   relief="flat", padx=18, pady=5, width=10,
                                   cursor="hand2")
        self.start_btn.pack(side="left", padx=10)
        self.stop_btn = tk.Button(btns, text="停止", command=self.stop,
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg="#c0392b", fg="white",
                                  activebackground="#a93226",
                                  activeforeground="white",
                                  relief="flat", padx=18, pady=5, width=10,
                                  cursor="hand2", state="disabled")
        self.stop_btn.pack(side="left", padx=10)

    # ══════════════════════════════════════════════════════════
    #  名单加载
    # ══════════════════════════════════════════════════════════

    def _refresh_samples(self):
        """刷新样本库下拉选项"""
        samples = [name for name, _ in SampleLibrary.get_samples()]
        self.sample_combo["values"] = samples
        # 尽量保持当前选择；否则选最近一个
        cur = self.sample_var.get()
        if cur not in samples and samples:
            self.sample_var.set(samples[0])
        if not samples:
            self.sample_var.set("")

    def _auto_load_default(self):
        """自动加载配置中的默认样本（与随机抽人一致）"""
        try:
            config = ConfigManager()
            if not config.get("auto_load_sample", True):
                return
            default_name = config.get("rct_default_sample", "")
            if default_name and default_name in self.sample_combo["values"]:
                self.sample_var.set(default_name)
                self._load_selected(silent=True)
        except Exception as e:
            rctlog.warning(f"[随机点名] 自动加载默认样本失败: {e}")

    def _load_selected(self, silent=False):
        """加载下拉框当前选中的样本"""
        name = self.sample_var.get()
        if not name:
            if not silent:
                messagebox.showwarning("警告", "样本库为空，请先导入样本")
            return
        names = SampleLibrary.load_names(name)
        if not names:
            if not silent:
                messagebox.showwarning("警告", f"样本「{name}」为空或无效")
            return
        self._set_names(name, names)
        if not silent:
            messagebox.showinfo("成功", f"已加载名单「{name}」\n共 {len(names)} 人")
        rctlog.info(f"[随机点名] 加载名单: {name}, 共 {len(names)} 人")

    def _set_names(self, name, names):
        """设置名单并复位状态"""
        self._stop_rolling()
        self.names = list(names)
        self.sample_name = name
        self.info_var.set(f"当前名单: {name} ｜ 共 {len(self.names)} 人")
        self._show("准备就绪", highlight=False, idle=True)
        self.start_btn.config(text="开始点名", state="normal")
        self.stop_btn.config(state="disabled")

    # ══════════════════════════════════════════════════════════
    #  点名逻辑（手动）
    # ══════════════════════════════════════════════════════════

    def start(self):
        """开始滚动点名"""
        if not self.names:
            messagebox.showwarning("警告", "请先加载名单")
            return
        if self.rolling:
            return
        self.rolling = True
        self.start_btn.config(text="点名中…", state="disabled")
        self.stop_btn.config(state="normal")
        self._tick()

    def _tick(self):
        """滚动一步 — 随机切换显示一个名字"""
        if not self.rolling or not self.names:
            return
        self._show(random.choice(self.names), highlight=False, idle=False)
        self._after_id = self.frame.after(self.ROLL_INTERVAL_MS, self._tick)

    def stop(self):
        """停止滚动，定格当前名字作为点名结果"""
        if not self.rolling:
            return
        self._stop_rolling()
        result = self._current
        # 定格高亮显示
        self._show(result if result else "（未点名）", highlight=True, idle=False)
        self.start_btn.config(text="再点一次", state="normal")
        self.stop_btn.config(state="disabled")
        if result:
            rctlog.info(f"[随机点名] 点中: {result}")

    def _stop_rolling(self):
        """停止内部滚动定时器"""
        self.rolling = False
        if self._after_id:
            try:
                self.frame.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ══════════════════════════════════════════════════════════
    #  显示与记录
    # ══════════════════════════════════════════════════════════

    def _show(self, name, highlight=False, idle=False):
        """更新大名字显示；highlight 表示定格结果"""
        self._current = name
        # 字号固定：占位与点名完全一致，避免界面跳动
        if idle:
            self.name_label.config(text=name,
                                   font=("Microsoft YaHei",
                                         self.NAME_FONT_SIZE, "bold"),
                                   fg="#bbbbbb")
            return
        color = "#2ecc71" if highlight else "#333333"
        self.name_label.config(text=name,
                               font=("Microsoft YaHei",
                                     self.NAME_FONT_SIZE, "bold"),
                               fg=color)


