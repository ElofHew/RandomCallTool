"""
公共对话框模块 - 关于窗口、使用说明窗口（可翻页）
"""
import os
import webbrowser
import tkinter as tk
from core.logman import rctlog
from core.info import github, gitee, official_website, res_path


# ══════════════════════════════════════════════════════════
#  关于窗口（通用）
# ══════════════════════════════════════════════════════════

class AboutWindow:
    """美观的关于窗口（通用版，信息从参数字典传入）"""

    def __init__(self, parent, info, icon_path=None):
        from core.platutils import set_window_icon
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
        set_window_icon(self.win, icon_path)

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
            (official_website, "  官方网站  ", "#2d8a4e"),
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


def load_about_info(app_key):
    """从 about.resd（JSON）+ info.py 加载关于信息

    Args:
        app_key: "rct" 或 "enc"，对应约应用标识

    Returns:
        dict: {
            "title", "description", "version", "date", "author",
            "extra_lines": []
        }
    """
    import json
    from core.info import (
        rct_version, rct_date, rct_author, rct_appname,
    )

    # 从 JSON 获取标题和描述
    info = {"title": "", "description": "", "extra_lines": []}
    about_file = os.path.join(res_path, "about.resd")
    if os.path.isfile(about_file):
        with open(about_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        entry = data.get(app_key, {})
        info.update(entry)

    # 版本信息从 info.py 获取
    if app_key == "rct":
        info.setdefault("version", rct_version)
        info.setdefault("date", rct_date)
        info.setdefault("author", rct_author)
        info.setdefault("title", rct_appname)

    return info
