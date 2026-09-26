"""桌面悬浮球：置顶的小按钮，右键快速抽取单人/单组。"""
import tkinter as tk
from tkinter import messagebox

from core.config import ConfigManager
from core.logman import rctlog
from core import notify


_ball_ref = {"instance": None}

# 三档尺寸（像素）；medium 为默认
SIZE_PRESETS = {"small": 55, "medium": 70, "large": 90}
DEFAULT_SIZE_KEY = "medium"


def size_from_config():
    """从配置读取悬浮球尺寸，非法值回退到默认"""
    key = str(ConfigManager().get("floatball_size", DEFAULT_SIZE_KEY) or "").lower()
    return SIZE_PRESETS.get(key, SIZE_PRESETS[DEFAULT_SIZE_KEY])


def create_ball(root, app):
    """创建悬浮球（带单例持有，供配置窗口刷新可见性）"""
    if _ball_ref["instance"] is None:
        _ball_ref["instance"] = FloatBall(root, app)
    else:
        _ball_ref["instance"].bind_app(root, app)
    return _ball_ref["instance"]


def refresh():
    """按配置刷新悬浮球的尺寸与显示状态（配置保存后调用）"""
    ball = _ball_ref["instance"]
    if ball is None:
        return
    ball.apply_size()
    if ConfigManager().get("floatball_enabled", True):
        ball.show()
    else:
        ball.hide()


def destroy():
    """销毁悬浮球（程序退出时调用）"""
    ball = _ball_ref["instance"]
    if ball is None:
        return
    try:
        ball.win.destroy()
    except Exception as e:
        rctlog.warning(f"[悬浮球] 销毁失败: {e}")
    finally:
        _ball_ref["instance"] = None


def sync_position(x, y):
    """记录悬浮球当前位置到配置"""
    cfg = ConfigManager()
    cfg.set("floatball_x", x)
    cfg.set("floatball_y", y)


class FloatBall:
    """置顶悬浮球：无边框 Toplevel，可拖动；右键弹出快速抽取菜单。"""

    # 让圆形之外区域透明的键色（Windows 上通过 -transparentcolor 生效）
    KEY_COLOR = "#ff00ff"
    # 右键菜单可选的最大抽取数量
    MAX_QUICK_COUNT = 9
    # 窗口整体不透明度；越高则白字越亮，同时球体越实
    ALPHA = 0.92
    # 判定为「单击」而非「拖动」的位移阈值（像素）
    CLICK_THRESHOLD = 4

    def __init__(self, root, app):
        self.app = app
        self.size = size_from_config()
        self._offset_x = 0
        self._offset_y = 0
        self._moved = False
        # 左键单击时执行的操作（右键菜单里选择）
        self._quick_kind = "person"
        self._quick_count = 1
        self._build_window()
        self._build_menu()

    def bind_app(self, root, app):
        """更新引用的主程序与根窗口（配置窗口后可复用）"""
        self.app = app
        self._menu.update_idletasks()

    # ── 窗口构建 ──

    def _build_window(self):
        cfg = ConfigManager()
        self.win = tk.Toplevel()
        self.win.title("快速抽取")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        # Windows：把键色设为透明，圆形外区域即透明
        try:
            self.win.attributes("-transparentcolor", self.KEY_COLOR)
            bg_color = self.KEY_COLOR
        except tk.TclError:
            bg_color = "#f0f4ff"
        self.win.configure(bg=bg_color)
        # 整体半透明，配合黑色球体呈现「透明黑」效果
        try:
            self.win.attributes("-alpha", self.ALPHA)
        except tk.TclError:
            pass
        # 默认位置：屏幕右上角
        x = cfg.get("floatball_x")
        y = cfg.get("floatball_y")
        if x is None or y is None:
            x = self.win.winfo_screenwidth() - self.size - 40
            y = 80
        self.win.geometry(f"{self.size}x{self.size}+{int(x)}+{int(y)}")

        self.canvas = tk.Canvas(self.win, width=self.size, height=self.size,
                                highlightthickness=0, bg=bg_color)
        self.canvas.pack()
        self._draw_ball()

        # 拖动 + 单击支持
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

    def _draw_ball(self):
        """绘制半透明黑色圆形悬浮球"""
        size = self.size
        pad = max(2, round(size * 0.04))
        self.canvas.delete("all")
        self.canvas.create_oval(pad, pad, size - pad, size - pad,
                                fill="#000000", outline="#444444", width=1)
        self.canvas.create_text(size // 2, size // 2,
                                text="抽", fill="#ffffff",
                                font=("Microsoft YaHei", max(10, round(size * 0.21)), "bold"))

    def apply_size(self):
        """按配置应用悬浮球尺寸（保持当前位置）"""
        new_size = size_from_config()
        if new_size == self.size:
            return
        self.size = new_size
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        self.canvas.configure(width=new_size, height=new_size)
        self.win.geometry(f"{new_size}x{new_size}+{x}+{y}")
        self._draw_ball()
        rctlog.info(f"[悬浮球] 尺寸已调整为 {new_size}px")

    # ── 菜单 ──

    def _build_menu(self):
        """右键菜单：选择下一次左键单击要执行的操作"""
        self._menu = tk.Menu(self.win, tearoff=0)
        for kind, label in [
            ("group_letter", "抽字母组"),
            ("group_number", "抽数字组"),
            ("person", "抽人"),
        ]:
            self._menu.add_command(
                label=label,
                command=lambda k=kind: self._set_kind(k))
        self._count_menu = tk.Menu(self._menu, tearoff=0)
        self._menu.add_cascade(label="抽取数量", menu=self._count_menu)
        self._sync_count_menu()
        # 尺寸快捷切换（单选，当前档位带勾选标记）
        self._size_var = tk.StringVar(value=self._size_key())
        size_menu = tk.Menu(self._menu, tearoff=0)
        for key, label in [("small", "小"), ("medium", "中"), ("large", "大")]:
            size_menu.add_radiobutton(
                label=label, variable=self._size_var, value=key,
                command=lambda k=key: self._set_size(k))
        self._menu.add_cascade(label="悬浮球大小", menu=size_menu)

    def _size_key(self):
        """当前尺寸档位键，用于菜单勾选状态"""
        key = str(ConfigManager().get("floatball_size", DEFAULT_SIZE_KEY) or "").lower()
        return key if key in SIZE_PRESETS else DEFAULT_SIZE_KEY

    def _available_count(self):
        """当前选定类型下可抽的最大数量"""
        if self._quick_kind == "person":
            tab = self.app.call_tab if self.app else None
            return len(tab.names) if tab else 0
        return self._group_total()

    def _max_quick_count(self):
        """菜单允许选择的数量上限：不超过实际可抽数量"""
        return max(1, min(self.MAX_QUICK_COUNT, self._available_count()))

    def _sync_count_menu(self):
        """按当前可抽数量重建「抽取数量」子菜单，避免选到不够的数量"""
        self._count_menu.delete(0, "end")
        for k in range(1, self._max_quick_count() + 1):
            self._count_menu.add_command(
                label=f"抽 {k} 个",
                command=lambda n=k: self._set_count(n))
        if self._quick_count > self._max_quick_count():
            self._quick_count = self._max_quick_count()

    def _set_kind(self, kind):
        self._quick_kind = kind
        # 切换类型后可抽数量可能变小，先把已选数量收窄
        self._quick_count = min(self._quick_count, self._max_quick_count())
        rctlog.info(f"[悬浮球] 下一次左键操作类型改为: {kind}（数量 {self._quick_count}）")

    def _set_count(self, n):
        self._quick_count = max(1, min(int(n), self._max_quick_count()))
        rctlog.info(f"[悬浮球] 下一次左键抽取数量改为: {self._quick_count}")

    def _set_size(self, key):
        """快捷切换悬浮球大小"""
        ConfigManager().set("floatball_size", key)
        self._size_var.set(key)
        self.apply_size()
        rctlog.info(f"[悬浮球] 大小已切换为: {key}")

    # ── 交互 ──

    def _on_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y
        self._moved = False

    def _on_drag(self, event):
        dx = event.x - self._offset_x
        dy = event.y - self._offset_y
        if abs(dx) > self.CLICK_THRESHOLD or abs(dy) > self.CLICK_THRESHOLD:
            self._moved = True
        x = self.win.winfo_x() + dx
        y = self.win.winfo_y() + dy
        self.win.geometry(f"+{x}+{y}")

    def _on_release(self, event):
        sync_position(self.win.winfo_x(), self.win.winfo_y())
        # 未发生拖动则视为单击：执行右键菜单选定的操作
        if not self._moved:
            self._do_quick(self._quick_kind, self._quick_count)

    def _on_right_click(self, event):
        # 同步勾选状态与可选数量（配置窗口、主界面加载名单后都可能变化）
        self._size_var.set(self._size_key())
        self._sync_count_menu()
        self._menu.tk_popup(event.x_root, event.y_root)

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)

    def hide(self):
        self.win.withdraw()

    # ── 数量与抽取 ──

    def _group_total(self):
        total = ConfigManager().get("rct_group_total", 9)
        return total if 0 < total <= 26 else 9

    def _do_quick(self, kind, k):
        """执行一次快速抽取"""
        app = self.app
        if not app or not app.call_tab:
            messagebox.showwarning("未初始化", "主程序尚未就绪，请稍后再试。")
            return
        tab = app.call_tab
        try:
            if kind == "person":
                if not tab.names:
                    messagebox.showwarning("未加载样本", "请先在主界面加载样本文件。")
                    return
                k = min(k, len(tab.names))
                selected = tab.sampler.smart_sample(tab.names, k)
                title, stamp = "抽取结果", "快速抽人"
                result_text = "\n".join(selected)
            else:
                total = self._group_total()
                k = min(k, total)
                pool = (list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:total]
                        if kind == "group_letter"
                        else list(range(1, total + 1)))
                selected = tab.sampler.smart_sample(pool, k)
                selected.sort()
                selected = [f"{g}组" for g in selected]
                title, stamp = "抽取结果", ("快速抽字母组" if kind == "group_letter" else "快速抽数字组")
                result_text = "\n".join(selected)

            tab._add_history("group" if kind.startswith("group") else "person",
                             selected, f"{stamp}：{', '.join(map(str, selected[:8]))}")
            rctlog.info(f"[悬浮球] {stamp} {k} 个: {selected}")
            notify.notify_result(title, selected, default_mask_title="随机抽取结果")

            if ConfigManager().get("save_result", True):
                from core.fileman import SaveResult
                cls = "RandomGroup" if kind.startswith("group") else "RandomPerson"
                SaveResult().save_result(cls, "随机抽" +
                                         ("组" if kind.startswith("group") else "人"),
                                         selected)
        except Exception as e:
            rctlog.error(f"[悬浮球] 快速抽取失败: {e}")
            messagebox.showerror("抽取失败", f"快速抽取时出错：\n{e}")