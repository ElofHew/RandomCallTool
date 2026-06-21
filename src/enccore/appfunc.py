import os
import webbrowser
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from enccore.config import ConfigManager
from core.logman import enclog
from enccore.encoder import ListEncoder
from enccore.window import ConfigWindow
from core.utils import open_file_or_dir
from core.info import enc_output_path, enc_desktop_output_path, res_path, official_website
from core.dialog import AboutWindow, load_about_info


class MainApplication:
    def __init__(self, root):
        self.root = root
        self.config = ConfigManager()

        self._restore_geometry()
        self._bind_shortcuts()
        self.create_menu()
        self.create_widgets()

    # ── 窗口几何 ────────────────────────────────────────────

    def _restore_geometry(self):
        """从配置恢复窗口位置"""
        geo = self.config.get_window_geometry()
        if geo:
            self.root.geometry(geo)
        if self.config.get("window_maximized", False):
            self.root.state("zoomed")

    def _save_geometry(self):
        """保存窗口位置到配置"""
        if self.root.state() == "zoomed":
            self.config.set("window_maximized", True)
        else:
            self.config.set("window_maximized", False)
            self.config.set("window_geometry", self.root.geometry())

    # ── 快捷键 ──────────────────────────────────────────────

    def _bind_shortcuts(self):
        self.root.bind("<Control-o>", lambda e: self.open_input_file())
        self.root.bind("<Control-s>", lambda e: self.encode_and_save())
        self.root.bind("<Control-Return>", lambda e: self.quick_encode())
        self.root.bind("<Control-d>", lambda e: self.test_decode())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_as_plaintext())
        self.root.bind("<F5>", lambda e: self.process_text())
        self.root.bind("<Control-w>", lambda e: self.clear_input())
        self.root.bind("<Control-Shift-W>", lambda e: self.clear_output())
        self.root.bind("<Control-i>", lambda e: self.show_statistics())
        self.root.bind("<Control-,>", lambda e: self.open_config_window())

    # ── 菜单栏 ──────────────────────────────────────────────

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # 文件
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开输入文件 (Ctrl+O)", command=self.open_input_file)
        file_menu.add_command(label="追加文件到输入", command=self.append_input_file)

        # 最近文件子菜单
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="最近打开的文件", menu=self.recent_menu)
        file_menu.add_separator()

        file_menu.add_command(label="批量编码", command=self.batch_encode)
        file_menu.add_command(label="批量解码", command=self.batch_decode)
        file_menu.add_separator()
        file_menu.add_command(label="保存为明文 (Ctrl+Shift+S)", command=self.save_as_plaintext)
        file_menu.add_separator()
        file_menu.add_command(label="打开输出目录", command=self.open_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)

        # 编辑
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="清空输入 (Ctrl+W)", command=self.clear_input)
        edit_menu.add_command(label="清空输出 (Ctrl+Shift+W)", command=self.clear_output)
        edit_menu.add_command(label="处理文本 (F5)", command=self.process_text)
        edit_menu.add_separator()
        edit_menu.add_command(label="配置 (Ctrl+,)", command=self.open_config_window)

        # 工具
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="快速编码 (Ctrl+Enter)", command=self.quick_encode)
        tools_menu.add_command(label="编码并保存 (Ctrl+S)", command=self.encode_and_save)
        tools_menu.add_separator()
        tools_menu.add_command(label="解码测试 (Ctrl+D)", command=self.test_decode)
        tools_menu.add_command(label="测试编码/解码循环", command=self.test_encode_decode)
        tools_menu.add_command(label="统计信息 (Ctrl+I)", command=self.show_statistics)

        # 帮助
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="访问官网", command=self.open_website)
        help_menu.add_command(label="关于", command=self.show_about)

        self._update_recent_menu()

    # ── 界面组件 ────────────────────────────────────────────

    def create_widgets(self):
        title_label = tk.Label(
            self.root,
            text="随机抽人名单编码工具",
            font=("Helvetica", 18, "bold"),
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # ── 输入区 ──
        input_frame = tk.LabelFrame(main_frame, text="输入明文名单")
        input_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.input_text = scrolledtext.ScrolledText(
            input_frame, height=8, wrap=tk.WORD, font=("Courier", 10)
        )
        self.input_text.pack(fill="both", expand=True, padx=5, pady=5)

        btn_row1 = tk.Frame(input_frame)
        btn_row1.pack(fill="x", pady=(0, 5))
        for text, cmd in [
            ("从文件加载", self.open_input_file),
            ("追加文件", self.append_input_file),
            ("清空输入", self.clear_input),
            ("处理文本", self.process_text),
        ]:
            ttk.Button(btn_row1, text=text, command=cmd).pack(side="left", padx=2)

        # ── 输出区 ──
        output_frame = tk.LabelFrame(main_frame, text="编码结果")
        output_frame.pack(fill="both", expand=True, pady=(0, 8))

        self.output_text = scrolledtext.ScrolledText(
            output_frame, height=6, wrap=tk.WORD,
            font=("Courier", 9), bg="#f0f0f0"
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        btn_row2 = tk.Frame(output_frame)
        btn_row2.pack(fill="x", pady=(0, 5))
        for text, cmd in [
            ("复制到剪贴板", self.copy_to_clipboard),
            ("清空输出", self.clear_output),
            ("解码测试", self.test_decode),
        ]:
            ttk.Button(btn_row2, text=text, command=cmd).pack(side="left", padx=2)

        # ── 底部操作栏 ──
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x", pady=(0, 10))

        # 编码方式选择
        tk.Label(bottom_frame, text="编码方式:").pack(side="left", padx=(0, 5))
        self.enc_method_var = tk.StringVar(
            value=self.config.get("encoding_method", "base64")
        )
        self.enc_method_combo = ttk.Combobox(
            bottom_frame,
            textvariable=self.enc_method_var,
            values=["base64", "hex"],
            state="readonly",
            width=10
        )
        self.enc_method_combo.pack(side="left", padx=(0, 10))

        # 文件名
        tk.Label(bottom_frame, text="文件名:").pack(side="left", padx=(0, 5))
        self.filename_var = tk.StringVar(
            value=self.config.get("default_filename", "sample_list")
        )
        self.filename_entry = ttk.Entry(
            bottom_frame, textvariable=self.filename_var, width=25
        )
        self.filename_entry.pack(side="left", fill="x", expand=True, padx=(0, 3))
        tk.Label(bottom_frame, text=".rcp").pack(side="left", padx=(0, 10))

        # 操作按钮
        ttk.Button(
            bottom_frame, text="快速编码",
            command=self.quick_encode, width=14
        ).pack(side="left", padx=2)
        ttk.Button(
            bottom_frame, text="编码并保存",
            command=self.encode_and_save, width=14
        ).pack(side="left", padx=2)

        # 状态栏
        self.status_bar = tk.Label(
            self.root, text="就绪",
            bd=1, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ══════════════════════════════════════════════════════════
    #  文件操作
    # ══════════════════════════════════════════════════════════

    def _read_file_with_fallback(self, file_path):
        """尝试多种编码读取文件"""
        encodings = [
            self.config.get("file_encoding", "utf-8"),
            "utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "utf-16"
        ]
        # 去重
        seen = set()
        unique_encodings = [e for e in encodings if not (e in seen or seen.add(e))]

        for enc in unique_encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                return content, enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise UnicodeDecodeError("所有尝试的编码均无法解码文件", file_path, 0, 0, "")

    def open_input_file(self, file_path=None):
        """打开输入文件"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("可用文件", "*.txt;*.csv;*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("编码文件", "*.rcp"),
                    ("所有文件", "*.*")
                ],
                title="选择要编码的名单文件"
            )
        if not file_path:
            return

        try:
            content, enc = self._read_file_with_fallback(file_path)
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(1.0, content)

            # 记录最近文件
            self.config.add_recent_file(file_path)
            self._update_recent_menu()

            label = os.path.basename(file_path)
            if enc != "utf-8":
                label += f" ({enc.upper()})"
            self.set_status(f"已加载: {label}")
            enclog.info(f"已加载文件 ({enc}): {file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件:\n{e}")
            enclog.error(f"读取文件失败: {file_path} -> {e}")

    def append_input_file(self):
        """追加文件到输入区"""
        file_path = filedialog.askopenfilename(
            filetypes=[("文本文件", "*.txt;*.csv"), ("所有文件", "*.*")],
            title="选择要追加的文件"
        )
        if not file_path:
            return
        try:
            content, enc = self._read_file_with_fallback(file_path)
            self.input_text.insert(tk.END, "\n" + content.strip())
            self.set_status(f"已追加: {os.path.basename(file_path)} ({enc.upper()})")
            enclog.info(f"已追加文件: {file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"追加失败:\n{e}")

    def save_as_plaintext(self):
        """保存为明文文件"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "输入为空，无需保存")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="保存为明文文件"
        )
        if not file_path:
            return

        try:
            file_enc = self.config.get("file_encoding", "utf-8")
            with open(file_path, 'w', encoding=file_enc) as f:
                f.write(text)
            self.set_status(f"明文已保存: {os.path.basename(file_path)}")
            enclog.info(f"明文文件已保存: {file_path}")
            messagebox.showinfo("成功", f"文件已保存:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            enclog.error(f"保存明文文件失败: {e}")

    def open_output_dir(self):
        """打开输出目录"""
        try:
            save_dir = (
                enc_desktop_output_path
                if self.config.get("enc_output_path", 0) == 1
                else enc_output_path
            )
            os.makedirs(save_dir, exist_ok=True)
            open_file_or_dir(save_dir)
            self.set_status("已打开输出目录")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {e}")
            enclog.error(f"打开输出目录失败: {e}")

    # ── 最近文件 ──────────────────────────────────────────

    def _update_recent_menu(self):
        """更新最近文件菜单"""
        self.recent_menu.delete(0, tk.END)
        recent = self.config.get_recent_files()
        if not recent:
            self.recent_menu.add_command(
                label="（无最近文件）",
                state="disabled"
            )
            return
        for fp in recent:
            label = os.path.basename(fp)
            self.recent_menu.add_command(
                label=label,
                command=lambda p=fp: self.open_input_file(p)
            )

    # ══════════════════════════════════════════════════════════
    #  编码 / 解码
    # ══════════════════════════════════════════════════════════

    def _get_encoding_method(self):
        """获取当前选中的编码方式（UI优先）"""
        return self.enc_method_var.get()

    def process_text(self):
        """处理输入文本"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            self.set_status("输入为空，无需处理")
            return

        processed_text = ListEncoder.process_text(
            text,
            remove_duplicates=self.config.get("remove_duplicates", True),
            trim_spaces=self.config.get("trim_spaces", True),
            sort_names=self.config.get("sort_names", False),
            ignore_empty_lines=self.config.get("ignore_empty_lines", True),
        )

        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(1.0, processed_text)

        original_count = len([l for l in text.split('\n') if l.strip()])
        processed_count = len([l for l in processed_text.split('\n') if l.strip()])
        diff = original_count - processed_count

        if diff > 0:
            self.set_status(f"文本已处理: 去除了 {diff} 个重复行")
            enclog.info(f"文本处理: {original_count} -> {processed_count} 行")
        else:
            self.set_status("文本已处理")
            enclog.info("文本处理完成（无变化）")

    def quick_encode(self):
        """快速编码（不保存）"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return

        try:
            method = self._get_encoding_method()
            processed = ListEncoder.process_text(
                text,
                remove_duplicates=self.config.get("remove_duplicates", True),
                trim_spaces=self.config.get("trim_spaces", True),
                sort_names=self.config.get("sort_names", False),
            )
            encoded = ListEncoder.encode_list(processed, method=method)

            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded)

            lines = len([l for l in processed.split('\n') if l.strip()])
            self.set_status(
                f"快速编码完成 [{method}]: {lines} 个名字，{len(encoded)} 字节"
            )
            enclog.info(f"快速编码完成 [{method}]: {lines} 个名字")

        except Exception as e:
            messagebox.showerror("错误", f"编码失败: {e}")
            enclog.error(f"快速编码失败: {e}")

    def encode_and_save(self):
        """编码并保存 .rcp 文件"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return

        try:
            method = self._get_encoding_method()
            processed = ListEncoder.process_text(
                text,
                remove_duplicates=self.config.get("remove_duplicates", True),
                trim_spaces=self.config.get("trim_spaces", True),
                sort_names=self.config.get("sort_names", False),
            )
            encoded = ListEncoder.encode_list(processed, method=method)

            # 输出路径
            save_dir = (
                enc_desktop_output_path
                if self.config.get("enc_output_path", 0) == 1
                else enc_output_path
            )
            os.makedirs(save_dir, exist_ok=True)

            # 文件名
            filename = self.filename_var.get().strip() or self.config.get("default_filename", "sample_list")
            if not filename.endswith('.rcp'):
                filename += '.rcp'
            file_path = os.path.join(save_dir, filename)

            # 覆盖确认
            if os.path.exists(file_path) and self.config.get("confirm_overwrite", True):
                if not messagebox.askyesno("确认", f"文件 {filename} 已存在，是否覆盖？"):
                    return

            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encoded)

            # 显示到输出区
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded)

            self.set_status(f"已保存: {file_path}")
            enclog.info(f"编码文件已保存 [{method}]: {file_path}")

            # 成功提示
            lines = len([l for l in processed.split('\n') if l.strip()])
            if self.config.get("show_success_dialog", True):
                messagebox.showinfo(
                    "成功",
                    f"名单编码完成！\n\n"
                    f"保存位置: {file_path}\n"
                    f"编码方式: {method}\n"
                    f"包含 {lines} 个名字\n"
                    f"文件大小: {len(encoded)} 字节"
                )

            # 自动清空
            if self.config.get("auto_clear_input", False):
                self.clear_input()

            # 自动打开文件夹
            if self.config.get("auto_open_folder", True):
                try:
                    open_file_or_dir(save_dir)
                except Exception:
                    pass

        except Exception as e:
            messagebox.showerror("错误", f"编码保存失败: {e}")
            enclog.error(f"编码保存失败: {e}")

    def copy_to_clipboard(self):
        """复制输出到剪贴板"""
        content = self.output_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("警告", "输出为空")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.set_status(f"已复制 {len(content)} 字符到剪贴板")

    def test_decode(self):
        """解码测试"""
        encoded = self.output_text.get(1.0, tk.END).strip()
        if not encoded:
            messagebox.showwarning("警告", "输出为空，无法解码")
            return

        try:
            method = ListEncoder.detect_encoding(encoded)
            decoded = ListEncoder.decode_list(encoded, method=method)

            win = tk.Toplevel(self.root)
            win.title(f"解码测试 [{method}]")
            win.geometry("500x400")
            win.transient(self.root)
            win.grab_set()

            tk.Label(win, text="解码结果",
                     font=("Helvetica", 14, "bold"),
                     fg="green").pack(pady=10)

            tw = scrolledtext.ScrolledText(
                win, wrap=tk.WORD, font=("Courier", 10)
            )
            tw.pack(fill="both", expand=True, padx=10, pady=10)
            tw.insert(1.0, decoded)
            tw.config(state="disabled")

            tk.Button(win, text="关闭", command=win.destroy,
                      width=15).pack(pady=10)

            self.set_status(f"解码测试完成 [{method}]")
        except Exception as e:
            messagebox.showerror("错误", f"解码失败: {e}")
            enclog.error(f"解码测试失败: {e}")

    def test_encode_decode(self):
        """测试编码/解码循环"""
        test_text = "测试名字1\n测试名字2\n测试名字3\n测试名字4"
        method = self._get_encoding_method()
        try:
            encoded = ListEncoder.encode_list(test_text, method=method)
            decoded = ListEncoder.decode_list(encoded, method=method)
            # 比较
            expected = test_text.strip()
            ok = decoded.strip() == expected
            if ok:
                messagebox.showinfo("测试结果", f"编码/解码测试成功！\n方式: {method}\n功能正常。")
            else:
                messagebox.showwarning("测试结果", f"编码/解码测试失败！\n方式: {method}")
            enclog.info(f"编码/解码测试 [{method}]: {'成功' if ok else '失败'}")
        except Exception as e:
            messagebox.showerror("错误", f"测试失败: {e}")

    # ══════════════════════════════════════════════════════════
    #  批量处理
    # ══════════════════════════════════════════════════════════

    def batch_encode(self):
        """批量编码"""
        input_dir = filedialog.askdirectory(title="选择包含名单文件的文件夹")
        if not input_dir:
            return

        output_dir = filedialog.askdirectory(title="选择编码文件输出文件夹")
        if not output_dir:
            return

        method = self._get_encoding_method()
        try:
            results = ListEncoder.batch_encode_files(
                input_dir, output_dir,
                method=method,
                pattern="*.txt",
                remove_duplicates=self.config.get("remove_duplicates", True),
                trim_spaces=self.config.get("trim_spaces", True),
                sort_names=self.config.get("sort_names", False),
            )
            success = sum(1 for _, _, ok in results if ok)
            total = len(results)
            msg = f"批量编码完成: {success}/{total} 个文件成功\n\n"
            for src, dst, ok in results:
                status = "✓" if ok else "✗"
                msg += f"  {status} {os.path.basename(src)} -> {os.path.basename(dst)}\n"
            messagebox.showinfo("批量编码结果", msg)
            enclog.info(f"批量编码: {success}/{total} 成功")

            if success > 0:
                open_file_or_dir(output_dir)
        except Exception as e:
            messagebox.showerror("错误", f"批量编码失败: {e}")
            enclog.error(f"批量编码失败: {e}")

    def batch_decode(self):
        """批量解码"""
        input_dir = filedialog.askdirectory(title="选择包含 .rcp 文件的文件夹")
        if not input_dir:
            return

        output_dir = filedialog.askdirectory(title="选择解码文件输出文件夹")
        if not output_dir:
            return

        try:
            results = ListEncoder.batch_decode_files(
                input_dir, output_dir,
                method=None,
                file_encoding=self.config.get("file_encoding", "utf-8"),
            )
            success = sum(1 for _, _, ok in results if ok)
            total = len(results)
            msg = f"批量解码完成: {success}/{total} 个文件成功\n\n"
            for src, dst, ok in results:
                status = "✓" if ok else "✗"
                msg += f"  {status} {os.path.basename(src)} -> {os.path.basename(dst)}\n"
            messagebox.showinfo("批量解码结果", msg)
            enclog.info(f"批量解码: {success}/{total} 成功")

            if success > 0:
                open_file_or_dir(output_dir)
        except Exception as e:
            messagebox.showerror("错误", f"批量解码失败: {e}")
            enclog.error(f"批量解码失败: {e}")

    # ══════════════════════════════════════════════════════════
    #  其它功能
    # ══════════════════════════════════════════════════════════

    def show_statistics(self):
        """显示统计信息（独立窗口）"""
        in_text = self.input_text.get(1.0, tk.END).strip()
        out_text = self.output_text.get(1.0, tk.END).strip()
        method = self._get_encoding_method()

        in_lines = len([l for l in in_text.split('\n') if l.strip()])
        in_chars = len(in_text)
        out_lines = len([l for l in out_text.split('\n') if l.strip()])
        out_chars = len(out_text)

        win = tk.Toplevel(self.root)
        win.title("统计信息")
        win.geometry("380x320")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        tk.Label(win, text="统计信息",
                 font=("Helvetica", 14, "bold")).pack(pady=(15, 10))

        info = (
            f"编码方式: {method}\n\n"
            f"─ 输入统计 ─\n"
            f"  行数:     {in_lines}\n"
            f"  字符数:   {in_chars}\n"
            f"  平均行长: {in_chars // max(1, in_lines)} 字符\n\n"
            f"─ 输出统计 ─\n"
            f"  行数:     {out_lines}\n"
            f"  字符数:   {out_chars}\n"
            f"  编码率:   {out_chars / max(1, in_chars):.2f}x\n"
        )
        tk.Label(win, text=info, font=("Courier", 10),
                 justify="left", anchor="w").pack(padx=20, fill="both", expand=True)

        tk.Button(win, text="关闭", command=win.destroy,
                  width=12).pack(pady=15)

        enclog.info(f"统计信息: 输入 {in_lines} 行 / 输出 {out_lines} 行")

    # ── 编辑 ──────────────────────────────────────────────

    def clear_input(self):
        """清空输入文本框"""
        self.input_text.delete(1.0, tk.END)
        self.set_status("输入已清空")

    def clear_output(self):
        """清空输出文本框"""
        self.output_text.delete(1.0, tk.END)
        self.set_status("输出已清空")

    # ── 配置 ──────────────────────────────────────────────

    def open_config_window(self):
        """打开配置窗口"""
        enclog.info("打开配置窗口")
        ConfigWindow(self.root, self.config, self)

    # ── 帮助 / 关于 ───────────────────────────────────────

    def open_website(self):
        """在浏览器中打开官网"""
        webbrowser.open(official_website)
        enclog.info(f"已打开官网: {official_website}")

    def show_help(self):
        """打开在线帮助文档"""
        webbrowser.open("https://rct.danevan.top/docs/")
        enclog.info("打开在线帮助文档")

    def show_about(self):
        """显示关于信息（从文件加载）"""
        about_file = os.path.join(res_path, "encode", "about.restxt")
        info = load_about_info(about_file)
        AboutWindow(self.root, info)

    # ── 状态栏 ────────────────────────────────────────────

    def set_status(self, message):
        """更新状态栏文本"""
        self.status_bar.config(text=message)

    def quit_app(self):
        """退出前保存窗口位置"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            self._save_geometry()
            enclog.info("用户确认退出程序")
            self.root.quit()
