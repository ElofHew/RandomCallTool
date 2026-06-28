"""
更新程序 GUI — 单窗口多页面
根据参数直接渲染对应页面，不新建子窗口
"""
import os
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk
from updcore.config import VERSION, PROGRAM_ROOT, CACHE_DIR, RES_PATH, SOURCE_NAMES
from updcore.config import get_config_source, save_config_source, OFFICIAL_URL
from updcore.network import check_remote_version, get_download_url
from updcore.downloader import DownloadWorker
from updcore.installer import run_remove_with_setup


class UpdateApp:
    """单窗口多页面更新程序"""

    def __init__(self, root, source=None, auto_check=False):
        self.root = root
        self.source = source or get_config_source()
        self.auto_check = auto_check
        self.result = None
        self.worker = None
        self.root.title("RandomCallTool 更新程序")
        self.root.geometry("460x400+100+100")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f4ff")
        self._set_icon()
        self._build_home()
        if self.auto_check:
            self.root.after(100, self._start_check)

    def _set_icon(self):
        try:
            p = os.path.join(RES_PATH, "update.ico")
            if os.path.isfile(p):
                self.root.iconbitmap(p)
        except Exception:
            pass

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
        tk.Label(main, text="RandomCallTool 更新程序",
                 font=("Microsoft YaHei", 16, "bold"),
                 fg="#2b5b84", bg="#f0f4ff").pack(pady=(15, 8))
        card = tk.Frame(main, relief="groove", bd=1, bg="#ffffff", padx=20, pady=12)
        card.pack(padx=40, pady=(0, 10), fill="x")
        for label, value in [
            ("当前版本", "v" + VERSION if VERSION else "未知"),
            ("程序目录", PROGRAM_ROOT),
            ("缓存目录", CACHE_DIR),
        ]:
            r = tk.Frame(card, bg="#ffffff")
            r.pack(fill="x", pady=2)
            tk.Label(r, text=label + "：", font=("", 9, "bold"),
                     width=10, anchor="e", bg="#ffffff").pack(side="left")
            tk.Label(r, text=value, font=("", 9), anchor="w",
                     bg="#ffffff", fg="#333", wraplength=280).pack(side="left", padx=5)
        sf = tk.Frame(main, bg="#f0f4ff")
        sf.pack(pady=5)
        tk.Label(sf, text="更新源：", font=("", 10, "bold"),
                 bg="#f0f4ff").pack(side="left", padx=(0, 5))
        self._src_var = tk.StringVar(value=self.source)
        for val, name in [("github", "GitHub"), ("gitee", "Gitee")]:
            tk.Radiobutton(sf, text=name, variable=self._src_var, value=val,
                           bg="#f0f4ff", command=self._on_source_changed).pack(side="left", padx=8)
        bf = tk.Frame(main, bg="#f0f4ff")
        bf.pack(pady=12)
        tk.Button(bf, text="  检测更新  ", command=self._start_check,
                  font=("", 11, "bold"), bg="#4a90d9", fg="white",
                  activebackground="#357abd", activeforeground="white",
                  relief="flat", bd=0, padx=24, pady=6, cursor="hand2").pack(side="left", padx=6)
        tk.Button(bf, text="  退出  ", command=self.root.destroy,
                  font=("", 11), relief="groove", bd=1, padx=24, pady=5).pack(side="left", padx=6)
        tk.Label(main, text="从配置的源检测新版本，下载安装包后自动完成更新。",
                 font=("", 8), fg="gray", bg="#f0f4ff").pack(side="bottom", pady=10)

    def _on_source_changed(self):
        self.source = self._src_var.get()
        save_config_source(self.source)

    # ==============================
    #  检测中
    # ==============================

    def _build_checking(self):
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True)
        tk.Label(main, text="正在检测更新...",
                 font=("Microsoft YaHei", 14, "bold"),
                 fg="#2b5b84", bg="#f0f4ff").pack(pady=(30, 10))
        tk.Label(main, text="正在从 " + SOURCE_NAMES.get(self.source, self.source) + " 获取版本信息\u2026",
                 font=("", 10), fg="#555", bg="#f0f4ff").pack(pady=5)
        self._progress = ttk.Progressbar(main, mode="indeterminate", length=300)
        self._progress.pack(pady=10)
        self._progress.start(10)
        self._status_label = tk.Label(main, text="", font=("", 9),
                                       fg="gray", bg="#f0f4ff", wraplength=380)
        self._status_label.pack()
        self._back_or_close().pack(pady=15)

    def _start_check(self):
        self._build_checking()
        def worker():
            result = check_remote_version(self.source, timeout=10)
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
            tk.Label(main, text="检测失败", font=("", 14, "bold"),
                     fg="red", bg="#f0f4ff").pack(pady=(30, 10))
            tk.Label(main, text="无法获取更新信息\n\n" + (result["error"] or ""),
                     font=("", 10), fg="#555", bg="#f0f4ff", justify="center").pack(pady=10)
            self._back_or_close().pack(pady=15)
            return
        if result["has_update"]:
            tk.Label(main, text="发现新版本", font=("", 16, "bold"),
                     fg="green", bg="#f0f4ff").pack(pady=(20, 5))
            tk.Label(main, text="当前版本: v" + result["local_version"] + "\n"
                                "最新版本: v" + result["remote_version"] + " (" + result["remote_date"] + ")\n"
                                "更新源: " + result["source_name"],
                     font=("", 10), fg="#333", bg="#f0f4ff", justify="center").pack(pady=10)
            bf = tk.Frame(main, bg="#f0f4ff")
            bf.pack(pady=10)
            for text, cmd, bg in [
                ("  直接下载(推荐)  ", self._start_download, "#4a90d9"),
                ("  前往官网下载  ", lambda: webbrowser.open(OFFICIAL_URL), "#28a745"),
            ]:
                tk.Button(bf, text=text, command=cmd, font=("", 10), bg=bg, fg="white",
                          activebackground=self._darken(bg), activeforeground="white",
                          relief="flat", bd=0, padx=14, pady=4, cursor="hand2").pack(side="left", padx=5)
            self._back_or_close().pack(pady=8)
        else:
            tk.Label(main, text="已是最新版本", font=("", 16, "bold"),
                     fg="blue", bg="#f0f4ff").pack(pady=(30, 10))
            tk.Label(main, text="当前版本: v" + result["local_version"] + "\n"
                                "远程版本: v" + result["remote_version"] + " (" + result["remote_date"] + ")\n\n"
                                "暂无可用更新。",
                     font=("", 10), fg="#555", bg="#f0f4ff", justify="center").pack(pady=10)
            self._back_or_close().pack(pady=15)

    # ==============================
    #  下载页面
    # ==============================

    def _start_download(self):
        self._build_download()
        ver = self.result.get("remote_version", "")
        meta = {"version": {"version": ver}}
        dl_url, filename = get_download_url(meta, self.source, ver)
        dest_path = os.path.join(CACHE_DIR, filename)
        self._dl_info.config(text="正在下载: " + filename)
        # 通过 after(0) 将 tkinter 操作调度到主线程，避免后台线程竞争
        def on_progress(downloaded, total, pct):
            self.root.after(0, self._on_dl_progress, downloaded, total, pct)
        def on_done(success, size, error):
            self.root.after(0, self._on_dl_done, success, size, error, dest_path)
        self.worker = DownloadWorker(dl_url, dest_path, on_progress, on_done)
        self.worker.start(timeout=180)

    def _on_dl_progress(self, downloaded, total, pct):
        """主线程：更新下载进度"""
        if total > 0:
            self._dl_bar["value"] = pct
            self._dl_pct.config(text=str(pct) + "%")
            self._dl_size.config(text=str(downloaded // 1024) + "KB / " + str(total // 1024) + "KB")
        else:
            self._dl_pct.config(text=str(downloaded // 1024) + "KB")

    def _on_dl_done(self, success, size, error, dest_path):
        """主线程：下载完成回调"""
        self._dl_btn.config(state="disabled")
        if success:
            self._dl_info.config(text="下载完成，正在安装...", fg="green")
            self._dl_bar["value"] = 100
            self._dl_pct.config(text="100%")
            self._do_install(dest_path)
        else:
            msg = "下载失败: " + (error or "") if error else "下载已取消"
            self._dl_info.config(text=msg, fg="red")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")

    def _build_download(self):
        self._clear()
        main = tk.Frame(self.root, bg="#f0f4ff")
        main.pack(fill="both", expand=True, padx=20, pady=15)
        tk.Label(main, text="正在下载更新包...",
                 font=("Microsoft YaHei", 12, "bold"),
                 fg="#2b5b84", bg="#f0f4ff").pack(anchor="w")
        tk.Label(main, text="网络库特性，下载可能会卡住一会，请耐心等待。",
                 font=("", 8), fg="#888", bg="#f0f4ff").pack(anchor="w", pady=(0, 5))
        self._dl_info = tk.Label(main, text="", font=("", 9), fg="#555",
                                  bg="#f0f4ff", anchor="w", justify="left")
        self._dl_info.pack(fill="x", pady=5)
        self._dl_bar = ttk.Progressbar(main, mode="determinate", length=400)
        self._dl_bar.pack(fill="x", pady=5)
        self._dl_pct = tk.Label(main, text="0%", font=("", 10, "bold"), fg="#333", bg="#f0f4ff")
        self._dl_pct.pack()
        self._dl_size = tk.Label(main, text="", font=("", 8), fg="gray", bg="#f0f4ff")
        self._dl_size.pack()
        br = tk.Frame(main, bg="#f0f4ff")
        br.pack(fill="x", pady=(10, 0))
        self._dl_btn = tk.Button(br, text="  取消下载  ", command=self._cancel_download,
                                  relief="groove", bd=1, padx=10)
        self._dl_btn.pack(side="right")

    def _cancel_download(self):
        if self.worker:
            self.worker.cancel()
        self._build_home()

    def _do_install(self, exe_path):
        """链式卸载+安装：启动 remove.exe --setup-path → 自毁"""
        try:
            self._dl_info.config(text="即将安装，正在准备...")
            self._dl_btn.config(state="disabled")
            self.root.update()
            time.sleep(2)

            # 启动 remove.exe；它会建 bat 链式完成：杀进程→删文件→运行安装包→自删
            ok = run_remove_with_setup(exe_path)
            if not ok:
                self._dl_info.config(text="启动卸载程序失败，请手动运行安装包。", fg="red")
                self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                    command=self.root.destroy if self.auto_check else self._build_home,
                                    state="normal")
                return

            # 更新程序自身退出，remove.exe 和 bat 接管后续
            self.root.destroy()
            import os as _os
            _os._exit(0)
        except Exception as e:
            self._dl_info.config(text="安装过程出错: " + str(e), fg="red")
            self._dl_btn.config(text="  退出  " if self.auto_check else "  返回  ",
                                command=self.root.destroy if self.auto_check else self._build_home,
                                state="normal")

    # ==============================
    #  工具
    # ==============================

    @staticmethod
    def _btn(text, cmd):
        return tk.Button(text=text, command=cmd, relief="groove", bd=1, padx=15, pady=3)

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
