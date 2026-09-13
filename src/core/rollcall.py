"""
随机点名模块 — 跑马灯式点名

功能说明：
  与「随机抽取/随机抽人」不同，点名采用类似跑马灯的形式：
  点「开始点名」后名单里的名字快速跳动，点「停止」则定格显示当前名字。
  另有「自动点名」：在 1.0x~3.0x 速率与 2~3 秒时长范围内各随机取一个值，
  到时自动停止并定格结果。

名单来源：
  与随机抽人一致，使用样本库中的 RCP 名单（data/rcplist/）。

点名优化（见 RollCallConfigWindow）：
  名字轮换速率、点名前打乱名单、放回式/不放回式、重置限度。
"""
import random
import tkinter as tk
from tkinter import ttk, messagebox

from core.logman import rctlog
from core.config import ConfigManager
from core.fileman import SampleLibrary
from core.window import BaseTab
from core.platutils import set_window_icon
from core.info import rct_icon_path


class RollCallTab(BaseTab):
    """随机点名选项卡 — 手动点名 + 自动点名"""

    ROLL_INTERVAL_MS = 70   # 滚动时名字切换间隔（毫秒）
    NAME_FONT_SIZE = 40    # 名字显示字号（固定，避免点名时 UI 跳变）
    MAX_NAME_LEN = 10      # 名字最大字符数，超出部分自动截断
    ROLL_TIMEOUT_MS = 10000  # 手动点名超时（毫秒），超时未停止则强制停止
    AUTO_SPEED_MIN = 1.0     # 自动点名速率范围下限（倍）
    AUTO_SPEED_MAX = 3.0     # 自动点名速率范围上限（倍）
    AUTO_SEC_MIN = 2.0       # 自动点名时长范围下限（秒）
    AUTO_SEC_MAX = 3.0       # 自动点名时长范围上限（秒）
    SPEED_MIN = 0.5          # 手动点名速率下限（设置窗口滑杆用）
    SPEED_MAX = 5.0          # 手动点名速率上限（设置窗口滑杆用）

    def __init__(self, parent):
        super().__init__(parent, "随机点名")
        self.parent = parent

        self.names = []            # 当前名单（名字列表）
        self.sample_name = ""      # 当前样本名
        self._after_id = None      # 滚动定时器句柄
        self._timeout_id = None    # 超时自动停止定时器句柄
        self._roll_timeout_ms = self.ROLL_TIMEOUT_MS  # 本次滚动设定时长
        self.rolling = False       # 是否正在滚动
        self._current = ""         # 当前显示的名字

        # 点名选项（速率、打乱、放回方式、重置限度）
        self.speed = 1.0
        self._active_speed = 1.0
        self.shuffle = False
        self.with_replacement = True
        self.reset_limit = "full"
        self.reset_custom = 1
        self._pool = []            # 不放回模式的剩余名单池
        self._load_options()

        self._build_ui()
        self._auto_load_default()

    def _load_options(self):
        """从配置读取点名相关选项（若影响池的选项变化则重装池）"""
        old = (self.with_replacement, self.shuffle,
               self.reset_limit, self.reset_custom)
        try:
            cfg = ConfigManager()
            self.speed = float(cfg.get("rollcall_speed", 1.0) or 1.0)
            self.shuffle = bool(cfg.get("rollcall_shuffle", False))
            self.with_replacement = bool(cfg.get("rollcall_with_replacement", True))
            self.reset_limit = cfg.get("rollcall_reset_limit", "full")
            self.reset_custom = int(cfg.get("rollcall_reset_custom", 1) or 1)
        except Exception as e:
            rctlog.warning(f"[随机点名] 读取点名选项失败，使用默认值: {e}")
            self.speed = 1.0
            self.shuffle = False
            self.with_replacement = True
            self.reset_limit = "full"
            self.reset_custom = 1
        self._active_speed = self.speed
        new = (self.with_replacement, self.shuffle,
               self.reset_limit, self.reset_custom)
        if old != new:
            self._refill_pool()

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
        tk.Button(src, text="刷新", command=self.refresh_state,
                  bg="#16a085", fg="white", relief="flat", padx=10,
                  cursor="hand2").pack(side="left", padx=2)
        tk.Button(src, text="点名设置", command=self._open_config,
                  relief="groove", padx=8,
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
        self.auto_btn = tk.Button(btns, text="自动点名", command=self.auto_start,
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg="#8e44ad", fg="white",
                                  activebackground="#7d3c98",
                                  activeforeground="white",
                                  relief="flat", padx=18, pady=5, width=10,
                                  cursor="hand2")
        self.auto_btn.pack(side="left", padx=10)
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

    def refresh_state(self):
        """刷新样本库列表与当前名单状态

        适用场景：样本库增删样本、或名单相关配置发生变化后，
        重新扫描样本库；若当前名单仍在库中则重新读取以同步文件内容。
        """
        prev = self.sample_combo.get()
        self._refresh_samples()
        values = list(self.sample_combo["values"])
        # 尽量保持原选择
        if prev in values:
            self.sample_var.set(prev)

        reloaded = False
        if self.sample_name and self.sample_name in values:
            names = SampleLibrary.load_names(self.sample_name)
            if names:
                names, _ = self._truncate_names(names)
                names, _ = self._merge_duplicates(names)
                self._set_names(self.sample_name, names)
                reloaded = True

        if not values:
            self.info_var.set("样本库为空")
        elif self.sample_name and self.sample_name not in values:
            self.info_var.set(f"当前名单: {self.sample_name}（已不在样本库中）")
        elif not self.sample_name:
            self.info_var.set("尚未加载名单")

        rctlog.info(f"[随机点名] 刷新状态: 样本库 {len(values)} 个样本, "
                    f"重新加载名单={reloaded}")

    def _auto_load_default(self):
        """自动加载点名名单（由「自启动加载点名名单」独立控制）"""
        try:
            config = ConfigManager()
            if not config.get("rollcall_auto_load_sample", True):
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
        # 1) 先截断超长名字
        names, truncated = self._truncate_names(names)
        # 2) 再强制合并重复名字（点名场景恒定去重，忽略软件配置开关）
        names, merged_count = self._merge_duplicates(names)
        self._set_names(name, names)
        msg = f"已加载名单「{name}」\n共 {len(names)} 人"
        notes = []
        if truncated:
            notes.append(f"有 {len(truncated)} 个名字超过 "
                         f"{self.MAX_NAME_LEN} 个字符，已自动截断")
        if merged_count:
            notes.append(f"有 {merged_count} 个重复名字，已自动合并")
        if notes:
            msg += "\n\n" + "\n".join(notes)
        if not silent:
            if notes:
                messagebox.showwarning("提示", msg)
            else:
                messagebox.showinfo("成功", msg)
        rctlog.info(f"[随机点名] 加载名单: {name}, 共 {len(names)} 人 "
                    f"(截断 {len(truncated)} 个, 合并 {merged_count} 个)")
        if truncated:
            rctlog.warning(f"[随机点名] {len(truncated)} 个超长名字已截断: {truncated}")
        if merged_count:
            rctlog.info(f"[随机点名] 已强制合并 {merged_count} 个重复名字")

    def _truncate_names(self, names):
        """截断超过 MAX_NAME_LEN 的名字，返回 (处理后列表, 被截断的原名列表)"""
        truncated = []
        result = []
        for n in names:
            if len(n) > self.MAX_NAME_LEN:
                truncated.append(n)
                result.append(n[:self.MAX_NAME_LEN])
            else:
                result.append(n)
        return result, truncated

    def _merge_duplicates(self, names):
        """强制合并重复名字（保序去重），返回 (去重列表, 被合并的数量)"""
        seen = set()
        result = []
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            result.append(n)
        return result, len(names) - len(result)

    def _set_names(self, name, names):
        """设置名单并复位状态"""
        self._stop_rolling()
        self.names = list(names)
        self.sample_name = name
        self._refill_pool()
        self.info_var.set(f"当前名单: {name} ｜ 共 {len(self.names)} 人")
        self._show("准备就绪", highlight=False, idle=True)
        self.start_btn.config(text="开始点名", state="normal")
        self.stop_btn.config(state="disabled")

    # ══════════════════════════════════════════════════════════
    #  点名逻辑（手动 / 自动）
    # ══════════════════════════════════════════════════════════

    def start(self, timeout_ms=None, speed=None):
        """开始滚动点名
        timeout_ms: 自动停止时长（毫秒），None 用默认手动超时
        speed: 本次使用的速率倍数，None 用用户配置速率
        """
        if not self.names:
            messagebox.showwarning("警告", "请先加载名单")
            return
        if self.rolling:
            return
        self._load_options()   # 每次开始前重新读取配置，使外部修改即时生效
        self._active_speed = self.speed if speed is None else float(speed)
        self.rolling = True
        self.start_btn.config(text="点名中…", state="disabled")
        self.stop_btn.config(state="normal")
        self._tick()
        # 超时保护：到时仍未停止则强制停止
        duration = self.ROLL_TIMEOUT_MS if timeout_ms is None else timeout_ms
        self._roll_timeout_ms = duration
        self._timeout_id = self.frame.after(duration, self._on_timeout)

    def auto_start(self):
        """自动点名：在速率与时长范围内各随机取一个值，到时自动停止"""
        if not self.names:
            messagebox.showwarning("警告", "请先加载名单")
            return
        if self.rolling:
            return
        # 随机选取本次速率与时长（仅本次生效，不改动用户配置）
        speed = round(random.uniform(self.AUTO_SPEED_MIN, self.AUTO_SPEED_MAX), 1)
        duration = round(random.uniform(self.AUTO_SEC_MIN, self.AUTO_SEC_MAX), 1)
        rctlog.info(f"[随机点名] 自动点名开始，本次速率 {speed:.1f}x，"
                    f"{duration:g} 秒后自动停止")
        self.start(timeout_ms=int(duration * 1000), speed=speed)

    def _tick(self):
        """滚动一步 — 随机切换显示一个名字"""
        if not self.rolling or not self.names:
            return
        self._show(self._pick_name(), highlight=False, idle=False)
        self._after_id = self.frame.after(self._interval_ms(), self._tick)

    def _pick_name(self):
        """按放回/不放回模式选出一个名字"""
        if self.with_replacement:
            return random.choice(self.names)
        # 不放回式：从剩余池中取，取走后按重置限度决定是否重置
        if not self._pool:
            self._refill_pool()
        name = self._pool.pop(random.randrange(len(self._pool)))
        if len(self._pool) <= self._reset_threshold():
            self._refill_pool()
        return name

    def _refill_pool(self):
        """重新装填不放回池（按需打乱顺序）"""
        self._pool = list(self.names)
        if self.shuffle:
            random.shuffle(self._pool)

    def _reset_threshold(self):
        """重置阈值：剩余人数 ≤ 阈值时重置名单"""
        total = len(self.names)
        if self.reset_limit == "half":
            return total // 2
        if self.reset_limit == "custom":
            try:
                n = int(self.reset_custom)
            except Exception:
                n = 0
            return max(0, min(n, max(0, total - 1)))
        return 0   # full：抽完（剩余 0）才重置

    def _interval_ms(self):
        """按本次速率倍数换算实际轮换间隔（毫秒），1.0x = 基准间隔"""
        try:
            speed = max(0.1, float(self._active_speed))
        except Exception:
            speed = 1.0
        return max(5, int(self.ROLL_INTERVAL_MS / speed))

    # ══════════════════════════════════════════════════════════
    #  设置
    # ══════════════════════════════════════════════════════════

    def _open_config(self):
        """打开随机点名设置子窗口"""
        RollCallConfigWindow(self.frame, self._current_options(),
                             self._apply_settings)

    def _current_options(self):
        """返回当前点名选项（供设置窗口初始化）"""
        return {
            "speed": self.speed,
            "shuffle": self.shuffle,
            "with_replacement": self.with_replacement,
            "reset_limit": self.reset_limit,
            "reset_custom": self.reset_custom,
        }

    def _apply_settings(self, settings):
        """应用设置窗口返回的选项（由设置窗口回调）"""
        try:
            self.speed = max(0.1, float(settings.get("speed", self.speed)))
        except Exception:
            self.speed = 1.0
        self._active_speed = self.speed
        self.shuffle = bool(settings.get("shuffle", self.shuffle))
        self.with_replacement = bool(settings.get("with_replacement", True))
        self.reset_limit = settings.get("reset_limit", "full")
        try:
            self.reset_custom = int(settings.get("reset_custom", self.reset_custom))
        except Exception:
            self.reset_custom = 1
        # 应用后按新设置重装池
        self._refill_pool()
        rctlog.info(f"[随机点名] 设置已应用: 速率 {self.speed:.1f}x, "
                    f"打乱={self.shuffle}, 放回式={self.with_replacement}, "
                    f"重置限度={self.reset_limit}({self.reset_custom})")

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
        self._cancel_timeout()
        if self._after_id:
            try:
                self.frame.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _cancel_timeout(self):
        """取消超时自动停止定时器"""
        if self._timeout_id:
            try:
                self.frame.after_cancel(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None

    def _on_timeout(self):
        """到达设定时长仍未停止 — 强制停止"""
        self._timeout_id = None
        if self.rolling:
            rctlog.info(f"[随机点名] 到达设定时长（{self._roll_timeout_ms / 1000:g}s），自动停止")
            self.stop()

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


# ══════════════════════════════════════════════════════════
#  随机点名设置窗口
# ══════════════════════════════════════════════════════════

class RollCallConfigWindow:
    """随机点名设置 — 独立子窗口"""

    MIN_SPEED = RollCallTab.SPEED_MIN
    MAX_SPEED = RollCallTab.SPEED_MAX

    def __init__(self, parent, options=None, on_apply=None):
        self.on_apply = on_apply
        self.config = ConfigManager()
        self.options = options or {}

        self.window = tk.Toplevel(parent)
        self.window.title("随机点名设置")
        self.window.geometry("400x440+100+100")
        self.window.resizable(False, False)
        self.window.transient(parent.winfo_toplevel())
        self.window.grab_set()
        try:
            set_window_icon(self.window, rct_icon_path)
        except Exception:
            pass

        self._build()

    def _build(self):
        opt = self.options
        tk.Label(self.window, text="随机点名设置",
                 font=("Microsoft YaHei", 14, "bold"),
                 fg="#2b5b84").pack(pady=(12, 2))

        # ── 名字轮换速率 ──
        speed_box = tk.LabelFrame(self.window, text="名字轮换速率")
        speed_box.pack(fill="x", padx=16, pady=6)
        self.speed_var = tk.DoubleVar(value=float(opt.get("speed", 1.0)))
        self.value_label = tk.Label(speed_box,
                                    text=f"x{float(opt.get('speed', 1.0)):.1f}",
                                    font=("Microsoft YaHei", 12, "bold"),
                                    fg="#4a90d9")
        self.value_label.pack(pady=(6, 0))
        tk.Scale(speed_box, from_=self.MIN_SPEED, to=self.MAX_SPEED,
                 resolution=0.1, orient="horizontal",
                 variable=self.speed_var, showvalue=False,
                 length=320, command=self._on_scale).pack(padx=12, pady=(2, 0))
        tk.Label(speed_box, text="1.0x 为基准速率，数值越大名字切换越快",
                 font=("", 8), fg="gray").pack(pady=(0, 6))

        # ── 点名优化 ──
        opt_box = tk.LabelFrame(self.window, text="点名优化")
        opt_box.pack(fill="x", padx=16, pady=6)

        self.shuffle_var = tk.BooleanVar(value=bool(opt.get("shuffle", False)))
        tk.Checkbutton(opt_box, text="点名前打乱名单顺序",
                       variable=self.shuffle_var).pack(anchor="w", padx=8, pady=(6, 2))

        tk.Label(opt_box, text="点名方式：", font=("", 10, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.replace_var = tk.StringVar(
            value="with" if opt.get("with_replacement", True) else "without")
        rf = tk.Frame(opt_box)
        rf.pack(anchor="w", padx=16)
        tk.Radiobutton(rf, text="放回式（点名后保留）", value="with",
                       variable=self.replace_var,
                       command=self._on_mode_change).pack(anchor="w")
        tk.Radiobutton(rf, text="不放回式（点到后移除）", value="without",
                       variable=self.replace_var,
                       command=self._on_mode_change).pack(anchor="w")

        tk.Label(opt_box, text="重置限度：", font=("", 10, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.limit_var = tk.StringVar(value=opt.get("reset_limit", "full"))
        lf = tk.Frame(opt_box)
        lf.pack(anchor="w", padx=16)
        self.rb_full = tk.Radiobutton(lf, text="完全", value="full",
                                      variable=self.limit_var,
                                      command=self._on_limit_change)
        self.rb_full.pack(side="left", padx=(0, 8))
        self.rb_half = tk.Radiobutton(lf, text="过半", value="half",
                                      variable=self.limit_var,
                                      command=self._on_limit_change)
        self.rb_half.pack(side="left", padx=(0, 8))
        self.rb_custom = tk.Radiobutton(lf, text="自定义", value="custom",
                                        variable=self.limit_var,
                                        command=self._on_limit_change)
        self.rb_custom.pack(side="left")
        self.custom_var = tk.IntVar(value=int(opt.get("reset_custom", 1) or 1))
        self.custom_spin = tk.Spinbox(lf, from_=0, to=9999, width=5,
                                      textvariable=self.custom_var)
        self.custom_spin.pack(side="left", padx=2)
        tk.Label(lf, text="人", font=("", 10)).pack(side="left")
        self._limit_widgets = [self.rb_full, self.rb_half, self.rb_custom]

        tk.Label(opt_box, text="注：重置限度仅在「不放回式」下生效，剩余人数 ≤ 限度时重置名单",
                 font=("", 8), fg="gray").pack(anchor="w", padx=8, pady=(2, 6))

        btns = tk.Frame(self.window)
        btns.pack(pady=12)
        tk.Button(btns, text="确定", width=10, command=self._ok,
                  bg="#4a90d9", fg="white", relief="flat",
                  cursor="hand2").pack(side="left", padx=8)
        tk.Button(btns, text="取消", width=10, command=self.window.destroy,
                  relief="groove").pack(side="left", padx=8)

        self._on_mode_change()

    def _on_scale(self, _=None):
        self.value_label.config(text=f"x{float(self.speed_var.get()):.1f}")

    def _on_mode_change(self):
        """放回式时重置限度无意义，禁用相关控件"""
        state = "normal" if self.replace_var.get() == "without" else "disabled"
        for w in self._limit_widgets:
            w.config(state=state)
        self._on_limit_change()

    def _on_limit_change(self):
        """仅不放回式 + 自定义时启用阈值输入"""
        active = (self.replace_var.get() == "without"
                  and self.limit_var.get() == "custom")
        self.custom_spin.config(state="normal" if active else "disabled")

    def _ok(self):
        speed = round(float(self.speed_var.get()), 1)
        speed = min(self.MAX_SPEED, max(self.MIN_SPEED, speed))
        try:
            custom = int(self.custom_var.get())
        except Exception:
            custom = 1
        custom = max(0, custom)
        settings = {
            "speed": speed,
            "shuffle": bool(self.shuffle_var.get()),
            "with_replacement": self.replace_var.get() == "with",
            "reset_limit": self.limit_var.get(),
            "reset_custom": custom,
        }
        for key, value in (
            ("rollcall_speed", settings["speed"]),
            ("rollcall_shuffle", settings["shuffle"]),
            ("rollcall_with_replacement", settings["with_replacement"]),
            ("rollcall_reset_limit", settings["reset_limit"]),
            ("rollcall_reset_custom", settings["reset_custom"]),
        ):
            try:
                self.config.set(key, value)
            except Exception as e:
                rctlog.error(f"[随机点名] 保存设置失败 {key}: {e}")
        if self.on_apply:
            self.on_apply(settings)
        rctlog.info(f"[随机点名] 设置已保存: {settings}")
        self.window.destroy()


