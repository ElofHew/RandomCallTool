"""更新程序 GUI：单窗口多页面逻辑。"""
import os
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk
from core import updconf
from core import network
from core import downloader
from core import installer


# ── 统一字阶（微软雅黑，避免各处默认字体/字号混乱）──
F_TITLE = ("Microsoft YaHei", 16, "bold")    # 页面大标题
F_HEADING = ("Microsoft YaHei", 14, "bold")  # 检测中 / 失败标题
F_SUBHEAD = ("Microsoft YaHei", 12, "bold")  # 下载页标题
F_BODY = ("Microsoft YaHei", 10)             # 正文 / 单选 / 勾选
F_BODY_BOLD = ("Microsoft YaHei", 10, "bold")
F_SMALL = ("Microsoft YaHei", 9)             # 卡片内容
F_SMALL_BOLD = ("Microsoft YaHei", 9, "bold")
F_TINY = ("Microsoft YaHei", 8)              # 辅助 / 提示小字
F_BTN = ("Microsoft YaHei", 10, "bold")      # 按钮文字


class UpdateApp:
    """单窗口多页面更新程序"""

    def __init__(self, root, source=None, auto_check=False, accept_preview=False):
        self.root = root
        self.source = source or updconf.get_config_source()
        self.auto_check = auto_check
        self.accept_preview = accept_preview
        self.result = None
        self.worker = None
        self.root.title("随机抽取工具 更新程序")
        self.root.geometry("460x420+100+100")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f4ff")
        # 未显式指定字体的控件也默认使用雅黑
        self.root.option_add("*Font", F_BODY)
        self._setup_style()
        self._set_icon()
        self._build_home()
        if self.auto_check:
            self.root.after(100, self._start_check)

    def _set_icon(self):
        try:
            p = os.path.join(updconf.RES_PATH, "update.ico")
            if os.path.isfile(p):
                self.root.iconbitmap(p)
        except Exception:
            pass

    def _setup_style(self):
        """配置与蓝色主题匹配的 ttk 进度条样式（替代默认绿色）。

        Windows 的 vista 主题把进度条颜色硬编码为绿色，configure 改不动；
        这里借用 clam 主题可自由着色的进度条元素，仅替换进度条这一个控件。
        """
        try:
            style = ttk.Style()
            try:
                style.element_create("Blue.Progressbar.trough", "from", "clam")
                style.element_create("Blue.Progressbar.pbar", "from", "clam")
                style.layout("Blue.Horizontal.TProgressbar", [
                    ("Blue.Progressbar.trough", {
                        "sticky": "nswe",
                        "children": [
                            ("Blue.Progressbar.pbar",
                             {"side": "left", "sticky": "nswe"}),
                        ],
                    }),
                ])
            except tk.TclError:
                pass  # 元素 / 布局已存在（同进程重复初始化时）
            style.configure(
                "Blue.Horizontal.TProgressbar",
                troughcolor="#e2e9f4",
                background="#4a90d9",
                bordercolor="#d5deeb",
                lightcolor="#4a90d9",
                darkcolor="#4a90d9",
            )
        except Exception:
            pass

    def _primary_btn(self, parent, text, cmd, bg="#4a90d9"):
        # 主操作按钮：实心扁平（蓝 / 绿）
        return tk.Button(parent, text=text, command=cmd, font=F_BTN,
                         bg=bg, fg="white",
                         activebackground=self._darken(bg),
                         activeforeground="white",
                         relief="flat", bd=0, padx=22, pady=6,
                         cursor="hand2")

    def _secondary_btn(self, parent, text, cmd):
        # 次要按钮：浅灰蓝扁平（替代灰色 groove）
        return tk.Button(parent, text=text, command=cmd, font=F_BTN,
                         bg="#e9eef6", fg="#3c4a5e",
                         activebackground="#d6dff0",
                         activeforeground="#2b3b52",
                         relief="flat", bd=0, padx=22, pady=6,
                         cursor="hand2")

    def _tiny_btn(self, parent, text, cmd):
        # 网盘等小按钮：浅色扁平
        return tk.Button(parent, text=text, command=cmd, font=F_SMALL,
                         bg="#eef2f8", fg="#3c4a5e",
                         activebackground="#dde5f1",
                         activeforeground="#2b3b52",
                         relief="flat", bd=0, padx=10, pady=2,
                         cursor="hand2")

    def _make_card(self, parent, **pack_kw):
        """白色信息卡片（groove 浅边框，与主页卡片同一风格）。"""
        card = tk.Frame(parent, relief="groove", bd=1, bg="#ffffff",
                        padx=18, pady=12)
        card.pack(**pack_kw)
        return card

    @staticmethod
    def _card_row(card, label, value):
        """卡片内的「标签：值」一行。"""
        row = tk.Frame(card, bg="#ffffff")
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label + "：", font=F_SMALL_BOLD,
                 width=10, anchor="e", bg="#ffffff").pack(side="left")
        tk.Label(row, text=value, font=F_SMALL, anchor="w",
                 bg="#ffffff", fg="#333").pack(side="left", padx=5)

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ==============================
    #  主页
    # ==============================

    def _build_home(self):
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True)
        tk.Label(main, text="随机抽取工具 更新程序",
                 font=F_TITLE,
                 fg="#2b5b84", bg="#f0f4ff").pack(pady=(10, 6))
        card = tk.Frame(main, relief="groove", bd=1, bg="#ffffff", padx=20, pady=10)
        card.pack(padx=34, pady=(0, 8), fill="x")
        for label, value in [
            ("当前版本", "v" + updconf.VERSION if updconf.VERSION else "未知"),
            ("版本代码", updconf.VERCODE if updconf.VERCODE else "未知"),
            ("发布日期", updconf.VERDATE if updconf.VERDATE else "未知"),
        ]:
            r = tk.Frame(card, bg="#ffffff")
            r.pack(fill="x", pady=3)
            tk.Label(r, text=label + "：", font=F_SMALL_BOLD,
                     width=10, anchor="e", bg="#ffffff").pack(side="left")
            tk.Label(r, text=value, font=F_SMALL, anchor="w",
                     bg="#ffffff", fg="#333", wraplength=280).pack(side="left", padx=5)
        sf = tk.Frame(main, bg="#f0f4ff")
        sf.pack(pady=4)
        tk.Label(sf, text="更新源：", font=F_BODY_BOLD,
                 bg="#f0f4ff").pack(side="left", padx=(0, 5))
        self._src_var = tk.StringVar(value=self.source)
        for val, name in [("github", "GitHub"), ("gitee", "Gitee")]:
            tk.Radiobutton(sf, text=name, variable=self._src_var, value=val,
                           bg="#f0f4ff", font=F_BODY, selectcolor="#f0f4ff",
                           activebackground="#f0f4ff",
                           command=self._on_source_changed).pack(side="left", padx=8)

        # 测试版更新选项
        pf = tk.Frame(main, bg="#f0f4ff")
        pf.pack(pady=2)
        self._preview_var = tk.BooleanVar(value=self.accept_preview)
        tk.Checkbutton(pf, text="接收测试版更新",
                       variable=self._preview_var, bg="#f0f4ff", font=F_BODY,
                       selectcolor="#f0f4ff", activebackground="#f0f4ff",
                       command=self._on_preview_changed).pack()

        bf = tk.Frame(main, bg="#f0f4ff")
        bf.pack(pady=8)
        self._primary_btn(bf, "  检测更新  ", self._start_check,
                          "#4a90d9").pack(side="left", padx=6)
        self._secondary_btn(bf, "  退出  ", self.root.destroy
                            ).pack(side="left", padx=6)
        tk.Label(main, text="从配置的源检测新版本，下载安装包后自动完成更新。",
                 font=F_TINY, fg="gray", bg="#f0f4ff").pack(side="bottom", pady=8)

    def _on_source_changed(self):
        self.source = self._src_var.get()
        updconf.save_config_source(self.source)

    def _on_preview_changed(self):
        self.accept_preview = self._preview_var.get()
        updconf.save_config_accept_preview(self.accept_preview)

    # ==============================
    #  检测中
    # ==============================

    def _build_checking(self):
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True)

        # 内容区整体垂直居中，避免返回按钮沉底、中部空洞
        holder = tk.Frame(main, bg="#f0f4ff")
        holder.pack(expand=True)
        tk.Label(holder, text="正在检测更新…",
                 font=F_HEADING,
                 fg="#2b5b84", bg="#f0f4ff").pack(pady=(0, 10))
        tk.Label(holder, text="正在从 " + updconf.SOURCE_NAMES.get(self.source, self.source) + " 获取版本信息\u2026",
                 font=F_BODY, fg="#555", bg="#f0f4ff").pack(pady=5)
        self._progress = ttk.Progressbar(holder, mode="indeterminate",
                                         length=300,
                                         style="Blue.Horizontal.TProgressbar")
        self._progress.pack(pady=12)
        self._progress.start(10)
        self._status_label = tk.Label(holder, text="", font=F_SMALL,
                                      fg="gray", bg="#f0f4ff", wraplength=380)
        self._status_label.pack()

        self._back_or_close().pack(side="bottom", pady=16)

    def _start_check(self):
        self._build_checking()
        def worker():
            result = network.check_remote_version(self.source, timeout=10, accept_preview=self.accept_preview)
            self.root.after(0, self._show_result, result)
        threading.Thread(target=worker, daemon=True).start()

    # ==============================
    #  检测结果
    # ==============================

    def _show_result(self, result):
        self._progress.stop()
        self.result = result
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True)
        if not result["success"]:
            tk.Label(main, text="检测失败", font=F_HEADING,
                     fg="#c0392b", bg="#f0f4ff").pack(pady=(32, 12))
            card = self._make_card(main, padx=34, fill="x")
            tk.Label(card, text="无法获取更新信息。", font=F_BODY_BOLD,
                     bg="#ffffff", fg="#333").pack(anchor="w")
            tk.Label(card, text=result["error"] or "未知错误",
                     font=F_SMALL, fg="#666", bg="#ffffff",
                     justify="left", wraplength=350).pack(anchor="w",
                                                          pady=(6, 0))
            self._back_or_close().pack(pady=20)
            return
        if result["has_update"]:
            # 仅当所选新版本确实来自测试版时才提示测试版
            is_preview = bool(result.get("is_preview"))
            label_text = "发现新版本（测试版）" if is_preview else "发现新版本"
            tk.Label(main, text=label_text, font=F_TITLE,
                     fg="#28a745", bg="#f0f4ff").pack(pady=(20, 8))

            # 版本对比信息以白色卡片承载，与主页风格呼应
            card = self._make_card(main, padx=34, fill="x")
            self._card_row(card, "当前版本", "v" + result["local_version"])
            self._card_row(card, "最新版本",
                           "v" + result["remote_version"] + "（" + result["remote_date"] + "）")
            self._card_row(card, "更新源", result["source_name"])
            if is_preview:
                self._card_row(card, "类型", "测试版更新")

            bf = tk.Frame(main, bg="#f0f4ff")
            bf.pack(pady=(12, 6))
            for text, cmd, bg in [
                ("  直接下载（推荐）  ", self._start_download, "#4a90d9"),
                ("  前往官网下载  ", lambda: webbrowser.open(updconf.OFFICIAL_URL), "#28a745"),
            ]:
                self._primary_btn(bf, text, cmd, bg).pack(side="left", padx=5)

            # 备用网盘下载（metadata 提供时显示）
            netdisks = []
            if result.get("quark_url"):
                netdisks.append(("夸克网盘", result["quark_url"]))
            if result.get("lanzou_url"):
                netdisks.append(("蓝奏云", result["lanzou_url"]))
            if netdisks:
                nf = tk.Frame(main, bg="#f0f4ff")
                nf.pack(pady=(8, 0))
                tk.Label(nf, text="备用下载：", font=F_SMALL, fg="#777",
                         bg="#f0f4ff").pack(side="left")
                for name, url in netdisks:
                    self._tiny_btn(nf, name,
                                   lambda u=url: webbrowser.open(u)
                                   ).pack(side="left", padx=4)
                if result.get("lanzou_url") and result.get("lanzou_password"):
                    tk.Label(main, text="蓝奏云提取码：" + result["lanzou_password"],
                             font=F_TINY, fg="#999", bg="#f0f4ff").pack(pady=(0, 2))
            self._back_or_close().pack(pady=8)
        else:
            tk.Label(main, text="已是最新版本", font=F_TITLE,
                     fg="#2b5b84", bg="#f0f4ff").pack(pady=(32, 12))
            card = self._make_card(main, padx=34, fill="x")
            self._card_row(card, "当前版本", "v" + result["local_version"])
            self._card_row(card, "远程版本",
                           "v" + result["remote_version"] + "（" + result["remote_date"] + "）")
            tk.Label(main, text="暂无可用更新。",
                     font=F_BODY, fg="#555", bg="#f0f4ff").pack(pady=10)
            self._back_or_close().pack(pady=12)

    # ==============================
    #  下载页面
    # ==============================

    def _start_download(self):
        self._build_download()
        ver = self.result.get("remote_version", "")
        meta = {"version": {"version": ver}}
        dl_url, filename = network.get_download_url(meta, self.source, ver)
        dest_path = os.path.join(updconf.CACHE_DIR, filename)
        self._dl_info.config(text="正在下载：" + filename)
        # 通过 after(0) 将 tkinter 操作调度到主线程，避免后台线程竞争
        def on_progress(downloaded, total, pct):
            self.root.after(0, self._on_dl_progress, downloaded, total, pct)
        def on_done(success, size, error):
            self.root.after(0, self._on_dl_done, success, size, error, dest_path)
        self.worker = downloader.DownloadWorker(dl_url, dest_path, on_progress, on_done)
        self.worker.start(timeout=180)

    def _on_dl_progress(self, downloaded, total, pct):
        """主线程：更新下载进度"""
        # 页面已被切换 / 控件已销毁时直接忽略，避免操作失效控件抛 TclError
        if self.worker is None or not self._widget_alive(self._dl_bar):
            return
        if total > 0:
            self._dl_bar["value"] = pct
            self._dl_pct.config(text=str(pct) + "%")
            self._dl_size.config(text=str(downloaded // 1024) + "KB / " + str(total // 1024) + "KB")
        else:
            self._dl_pct.config(text=str(downloaded // 1024) + "KB")

    @staticmethod
    def _widget_alive(widget):
        """控件是否仍存在（页面切换后旧控件会被销毁）"""
        try:
            return bool(widget is not None and widget.winfo_exists())
        except tk.TclError:
            return False

    def _on_dl_done(self, success, size, error, dest_path):
        """主线程：下载完成回调"""
        # 用户取消后已切回主页，此时旧控件已不存在，直接返回即可
        if not self._widget_alive(self._dl_btn):
            return
        self._dl_btn.config(state="disabled")
        if success:
            self._dl_info.config(text="下载完成，正在安装…", fg="green")
            self._dl_bar["value"] = 100
            self._dl_pct.config(text="100%")
            self._do_install(dest_path)
        elif error == downloader.CANCELED:
            # 取消是用户主动行为，不应显示为「下载失败」
            self._dl_info.config(text="下载已取消", fg="#888")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")
        else:
            self._dl_info.config(text="下载失败：" + (error or ""), fg="red")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")

    def _build_download(self):
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        tk.Label(main, text="正在下载更新包…",
                 font=F_SUBHEAD,
                 fg="#2b5b84", bg="#f0f4ff").pack(anchor="w")
        tk.Label(main, text="受网络状况影响，下载期间界面可能短暂无响应，请耐心等待。",
                 font=F_TINY, fg="#888", bg="#f0f4ff").pack(anchor="w",
                                                             pady=(2, 10))

        # 下载信息聚合到白色卡片，与其它页面风格一致
        card = self._make_card(main, fill="x", padx=0, pady=0)
        self._dl_info = tk.Label(card, text="", font=F_SMALL, fg="#555",
                                 bg="#ffffff", anchor="w", justify="left")
        self._dl_info.pack(fill="x")
        self._dl_bar = ttk.Progressbar(card, mode="determinate",
                                       style="Blue.Horizontal.TProgressbar")
        self._dl_bar.pack(fill="x", pady=8)
        pr = tk.Frame(card, bg="#ffffff")
        pr.pack(fill="x")
        self._dl_size = tk.Label(pr, text="", font=F_TINY, fg="gray",
                                 bg="#ffffff")
        self._dl_size.pack(side="left")
        self._dl_pct = tk.Label(pr, text="0%", font=F_BODY_BOLD,
                                fg="#333", bg="#ffffff")
        self._dl_pct.pack(side="right")

        br = tk.Frame(main, bg="#f0f4ff")
        br.pack(fill="x", pady=(12, 0))
        self._dl_btn = self._secondary_btn(br, "  取消下载  ", self._cancel_download)
        self._dl_btn.pack(side="right")

    def _cancel_download(self):
        """取消下载：先中止后台线程并清除引用，再切回主页

        先置 self.worker = None，让后台线程随后的完成回调识别为「已失效」并跳过，
        避免回调操作已被销毁的控件抛 TclError。
        """
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.cancel()
        self._build_home()

    def _do_install(self, exe_path):
        """链式卸载+安装：启动 remove.exe --setup-path → 自毁"""
        try:
            self._dl_info.config(text="即将安装，正在准备…")
            self._dl_btn.config(state="disabled")
            # 用 after 异步等待，避免 time.sleep 冻结界面
            self.root.after(2000, lambda: self._start_uninstall(exe_path))
        except Exception as e:
            self._dl_info.config(text="安装过程出错：" + str(e), fg="red")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")

    def _start_uninstall(self, exe_path):
        """延时后真正启动卸载链"""
        try:
            # 启动 remove.exe；它会建 bat 链式完成：杀进程→删文件→运行安装包→自删
            ok = installer.run_remove_with_setup(exe_path)
            if not ok:
                self._dl_info.config(text="无法启动卸载程序，请手动运行安装包。", fg="red")
                self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                    command=self.root.destroy if self.auto_check else self._build_home,
                                    state="normal")
                return

            # 更新程序自身退出，remove.exe 和 bat 接管后续
            self.root.destroy()
            import os as _os
            _os._exit(0)
        except Exception as e:
            self._dl_info.config(text="安装过程出错：" + str(e), fg="red")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")

    # ==============================
    #  工具
    # ==============================

    def _btn(self, text, cmd):
        return self._secondary_btn(self.root, text, cmd)

    def _back_or_close(self):
        """返回主页 或 关闭程序（auto_check 模式）"""
        if self.auto_check:
            return self._btn("  关闭  ", self.root.destroy)
        return self._btn("  返回  ", self._build_home)

    @staticmethod
    def _darken(color):
        try:
            c = color.lstrip("#")
            return "#{:02x}{:02x}{:02x}".format(
                max(0, int(c[0:2], 16) - 30),
                max(0, int(c[2:4], 16) - 30),
                max(0, int(c[4:6], 16) - 30))
        except Exception:
            return color
