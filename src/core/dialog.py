"""
公共对话框模块 - 关于窗口、使用说明窗口（可翻页）
"""
import os
import webbrowser
import tkinter as tk
from tkinter import ttk
from core.logman import rctlog
from core.info import github, gitee


# ══════════════════════════════════════════════════════════
#  关于窗口（通用）
# ══════════════════════════════════════════════════════════

class AboutWindow:
    """美观的关于窗口（通用版，信息从参数字典传入）"""

    def __init__(self, parent, info):
        """
        info: dict 包含以下键
            - title: 应用名称
            - description: 描述
            - version: 版本号
            - date: 日期
            - author: 作者
            - extra_lines: 可选，额外信息列表
        """
        self.win = tk.Toplevel(parent)
        self.win.title(f"关于 {info['title']}")
        self.win.geometry("460x380")
        self.win.minsize(420, 340)
        self.win.resizable(False, False)
        self.win.transient(parent)

        main = tk.Frame(self.win, bg="#f0f4ff")
        main.pack(fill="both", expand=True)

        # ── 标题区 ──
        title_frame = tk.Frame(main, bg="#4a7db4", height=90)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame, text=info["title"],
            font=("Microsoft YaHei", 20, "bold"),
            fg="white", bg="#4a7db4",
        ).pack(pady=(12, 0))
        tk.Label(
            title_frame, text=info.get("description", ""),
            font=("Microsoft YaHei", 9),
            fg="#d0e0ff", bg="#4a7db4", wraplength=400,
        ).pack(pady=(4, 0))

        # ── 信息区 ──
        info_frame = tk.Frame(main, bg="#f0f4ff", padx=30, pady=15)
        info_frame.pack(fill="both", expand=True)

        info_items = [
            ("版本", f"v{info['version']}  ({info['date']})"),
            ("作者", info["author"]),
        ]
        for extra in info.get("extra_lines", []):
            info_items.append(("", extra))

        for label, value in info_items:
            row = tk.Frame(info_frame, bg="#f0f4ff")
            row.pack(fill="x", pady=4)
            if label:
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
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=_lighten(c)))
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

        # 等所有控件构建完后，再处理模态和居中（避免 update_idletasks 卡死）
        self.win.grab_set()
        self.win.after(10, self._center_window, parent)

        rctlog.info("打开关于窗口")

    def _center_window(self, parent):
        """将窗口居中于父窗口"""
        try:
            self.win.update_idletasks()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            px, py = parent.winfo_x(), parent.winfo_y()
        except Exception:
            pw, ph, px, py = 600, 400, 100, 100
        ww, wh = 460, 380
        x = px + (pw - ww) // 2
        y = py + (ph - wh) // 2
        self.win.geometry(f"{ww}x{wh}+{x}+{y}")


# ══════════════════════════════════════════════════════════
#  使用说明窗口（通用，支持翻页，内容从文本文件加载）
# ══════════════════════════════════════════════════════════

class HelpWindow:
    """可翻页的使用说明窗口（通用版，内容从文本文件加载）"""

    def __init__(self, parent, tips_file, title="使用说明"):
        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("450x610+60+60")
        self.win.minsize(450, 350)
        self.win.maxsize(800, 1000)
        self.win.resizable(True, True)
        self.win.transient(parent)
        self.win.grab_set()

        self.pages = self._parse_tips_file(tips_file)
        self.current_page = 0
        self.total_pages = len(self.pages)
        self._build_ui()
        self._show_page(0)

        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        rctlog.info(f"打开使用说明窗口: {tips_file}")

    @staticmethod
    def _parse_tips_file(filepath):
        """解析 tips 文本文件，返回 [(标题, [(文本, 是否加粗), ...]), ...]"""
        pages = []
        if not os.path.isfile(filepath):
            pages.append(("提示", [("提示文件未找到", False)]))
            return pages

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 按 === 标题 === 分割
        raw_pages = []
        current_title = ""
        current_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("===") and stripped.endswith("==="):
                if current_lines or current_title:
                    raw_pages.append((current_title, current_lines))
                current_title = stripped.strip("=").strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines or current_title:
            raw_pages.append((current_title, current_lines))

        for title, lines in raw_pages:
            parsed = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    # 如果只是 "#" 空行，显示空白行
                    text = stripped[1:].strip() if stripped != "#" else ""
                    parsed.append((text, True))
                else:
                    parsed.append((line, False))
            pages.append((title, parsed))

        return pages

    def _build_ui(self):
        """构建界面"""
        # ── 标题栏 ──
        title_frame = tk.Frame(self.win, bg="#4a7db4", height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame, text=self.win.title(),
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
        title, lines = self.pages[index]
        self.page_title_label.config(text=title)

        self.content_text.config(state="normal")
        self.content_text.delete(1.0, tk.END)
        for text, is_bold in lines:
            self.content_text.insert(tk.END, text + "\n", "bold" if is_bold else "")
        self.content_text.config(state="disabled")
        self.content_text.see(1.0)

        self.page_label.config(text=f"第 {index + 1} 页，共 {self.total_pages} 页")
        self.prev_btn.config(state="normal" if index > 0 else "disabled")
        self.next_btn.config(state="normal" if index < self.total_pages - 1 else "disabled")

    def _prev_page(self):
        if self.current_page > 0:
            self._show_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self._show_page(self.current_page + 1)


# ── 工具函数 ──────────────────────────────────────────────

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


def load_about_info(filepath):
    """从 about.restxt 文件加载关于信息，返回 dict"""
    info = {}
    if not os.path.isfile(filepath):
        return info
    extra_lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if key.startswith("extra_line"):
                    extra_lines.append(value)
                else:
                    info[key] = value
    if extra_lines:
        info["extra_lines"] = extra_lines
    return info
