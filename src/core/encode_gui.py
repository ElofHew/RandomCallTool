"""
编码工具 GUI 组件
"""
import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from .config import EncodeConfigManager
from .encoder import ListEncoder
from .common import BaseFileManager
from .constants import (
    ENCODE_OUTPUT_PATH, ENCODE_DESKTOP_OUTPUT_PATH, __encode_version__, __author__, __encode_description__
)

logger = logging.getLogger(__name__)


class MainApplication:
    def __init__(self, root):
        self.root = root
        self.config = EncodeConfigManager()
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开输入文件", command=self.open_input_file)
        file_menu.add_command(label="保存为明文", command=self.save_as_plaintext)
        file_menu.add_separator()
        file_menu.add_command(label="打开输出目录", command=self.open_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="清空输入", command=self.clear_input)
        edit_menu.add_command(label="清空输出", command=self.clear_output)
        edit_menu.add_command(label="处理文本", command=self.process_text)
        edit_menu.add_separator()
        edit_menu.add_command(label="配置", command=self.open_config_window)

        tools_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="测试编码/解码", command=self.test_encode_decode)
        tools_menu.add_command(label="统计信息", command=self.show_statistics)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_widgets(self):
        title_label = tk.Label(self.root, text="随机抽人名单编码工具", font=("Helvetica", 18, "bold"), fg="blue")
        title_label.pack(pady=10, ipady=15)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 输入区域
        input_frame = tk.LabelFrame(main_frame, text="输入明文名单")
        input_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.input_text = scrolledtext.ScrolledText(input_frame, height=8, wrap=tk.WORD, font=("Courier", 10))
        self.input_text.pack(fill="both", expand=True, padx=5, pady=5)
        input_button_frame = tk.Frame(input_frame)
        input_button_frame.pack(fill="x", pady=5)
        ttk.Button(input_button_frame, text="从文件加载", command=self.open_input_file).pack(side="left", padx=2)
        ttk.Button(input_button_frame, text="清空输入", command=self.clear_input).pack(side="left", padx=2)
        ttk.Button(input_button_frame, text="处理文本", command=self.process_text).pack(side="left", padx=2)

        # 输出区域
        output_frame = tk.LabelFrame(main_frame, text="编码结果")
        output_frame.pack(fill="both", expand=True, pady=(0, 10))
        self.output_text = scrolledtext.ScrolledText(output_frame, height=6, wrap=tk.WORD, font=("Courier", 9), bg="#f0f0f0")
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        output_button_frame = tk.Frame(output_frame)
        output_button_frame.pack(fill="x", pady=5)
        ttk.Button(output_button_frame, text="复制到剪贴板", command=self.copy_to_clipboard).pack(side="left", padx=2)
        ttk.Button(output_button_frame, text="清空输出", command=self.clear_output).pack(side="left", padx=2)
        ttk.Button(output_button_frame, text="解码测试", command=self.test_decode).pack(side="left", padx=2)

        # 文件名输入区域
        filename_frame = tk.Frame(main_frame)
        filename_frame.pack(fill="x", pady=(0, 10))
        tk.Label(filename_frame, text="输出文件名:").pack(side="left", padx=(0, 5))
        self.filename_var = tk.StringVar(value=self.config.get("default_filename", "sample_list"))
        self.filename_entry = ttk.Entry(filename_frame, textvariable=self.filename_var, width=30)
        self.filename_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Label(filename_frame, text=".rcp").pack(side="left")

        # 操作按钮
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(action_frame, text="编码并保存", command=self.encode_and_save, width=20).pack(side="left", padx=2)
        ttk.Button(action_frame, text="快速编码", command=self.quick_encode, width=20).pack(side="left", padx=2)

        self.status_bar = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def open_input_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("可用文件", "*.txt;*.csv"), ("CSV文件", "*.csv"), ("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="选择要编码的名单文件"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.input_text.delete(1.0, tk.END)
                self.input_text.insert(1.0, content)
                self.set_status(f"已加载文件: {os.path.basename(file_path)}")
                logger.info(f"已加载输入文件: {file_path}")
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                    self.input_text.delete(1.0, tk.END)
                    self.input_text.insert(1.0, content)
                    self.set_status(f"已加载文件(GBK编码): {os.path.basename(file_path)}")
                    logger.info(f"已加载输入文件(GBK编码): {file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"无法读取文件: {e}")
                    logger.error(f"读取文件失败: {e}")
            except Exception as e:
                messagebox.showerror("错误", f"无法读取文件: {e}")
                logger.error(f"读取文件失败: {e}")

    def process_text(self):
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            self.set_status("输入为空，无需处理")
            return
        remove_duplicates = self.config.get("remove_duplicates", True)
        trim_spaces = self.config.get("trim_spaces", True)
        processed = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(1.0, processed)
        orig_count = len([l for l in text.split('\n') if l.strip()])
        proc_count = len([l for l in processed.split('\n') if l.strip()])
        if remove_duplicates and orig_count != proc_count:
            self.set_status(f"文本已处理: 去除了 {orig_count - proc_count} 个重复项")
        else:
            self.set_status("文本已处理")

    def encode_and_save(self):
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return
        try:
            remove_duplicates = self.config.get("remove_duplicates", True)
            trim_spaces = self.config.get("trim_spaces", True)
            processed = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
            encoded = ListEncoder.encode_list(processed)

            if self.config.get("output_path", 0) == 1:
                save_dir = ENCODE_DESKTOP_OUTPUT_PATH
            else:
                save_dir = ENCODE_OUTPUT_PATH
            os.makedirs(save_dir, exist_ok=True)

            filename = self.filename_var.get().strip()
            if not filename:
                filename = self.config.get("default_filename", "sample_list")
            if not filename.endswith('.rcp'):
                filename += '.rcp'
            file_path = os.path.join(save_dir, filename)
            if os.path.exists(file_path):
                if not messagebox.askyesno("确认", f"文件 {filename} 已存在，是否覆盖？"):
                    return
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encoded)
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded)
            self.set_status(f"文件已保存: {file_path}")
            logger.info(f"编码文件已保存: {file_path}")
            lines_count = len([l for l in processed.split('\n') if l.strip()])
            messagebox.showinfo("成功", f"名单编码完成！\n\n保存位置: {file_path}\n包含 {lines_count} 个名字\n文件大小: {len(encoded)} 字节")
            if self.config.get("auto_clear_input", False):
                self.clear_input()
            if self.config.get("auto_open_folder", True):
                BaseFileManager.open_directory(save_dir)
        except Exception as e:
            messagebox.showerror("错误", f"编码保存失败: {e}")
            logger.error(f"编码保存失败: {e}")

    def quick_encode(self):
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return
        try:
            remove_duplicates = self.config.get("remove_duplicates", True)
            trim_spaces = self.config.get("trim_spaces", True)
            processed = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
            encoded = ListEncoder.encode_list(processed)
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded)
            lines_count = len([l for l in processed.split('\n') if l.strip()])
            self.set_status(f"快速编码完成: {lines_count} 个名字，{len(encoded)} 字节")
            logger.info(f"快速编码完成: {lines_count} 个名字")
        except Exception as e:
            messagebox.showerror("错误", f"编码失败: {e}")
            logger.error(f"快速编码失败: {e}")

    def copy_to_clipboard(self):
        output_content = self.output_text.get(1.0, tk.END).strip()
        if not output_content:
            messagebox.showwarning("警告", "输出为空，无需复制")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(output_content)
        self.set_status("已复制到剪贴板")

    def test_decode(self):
        encoded_text = self.output_text.get(1.0, tk.END).strip()
        if not encoded_text:
            messagebox.showwarning("警告", "输出为空，无法解码")
            return
        try:
            decoded = ListEncoder.decode_list(encoded_text)
            decode_window = tk.Toplevel(self.root)
            decode_window.title("解码测试")
            decode_window.geometry("500x400")
            decode_window.transient(self.root)
            decode_window.grab_set()
            tk.Label(decode_window, text="解码结果", font=("Helvetica", 14, "bold"), fg="green").pack(pady=10)
            text_widget = scrolledtext.ScrolledText(decode_window, wrap=tk.WORD, font=("Courier", 10))
            text_widget.pack(fill="both", expand=True, padx=10, pady=10)
            text_widget.insert(1.0, decoded)
            text_widget.config(state="disabled")
            tk.Button(decode_window, text="关闭", command=decode_window.destroy, width=15).pack(pady=10)
            self.set_status("解码测试完成")
        except Exception as e:
            messagebox.showerror("错误", f"解码失败: {e}")
            logger.error(f"解码测试失败: {e}")

    def save_as_plaintext(self):
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "输入为空，无需保存")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")], title="保存为明文文件")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.set_status(f"明文文件已保存: {file_path}")
                logger.info(f"明文文件已保存: {file_path}")
                messagebox.showinfo("成功", f"文件已保存:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    def clear_input(self):
        self.input_text.delete(1.0, tk.END)
        self.set_status("输入已清空")

    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.set_status("输出已清空")

    def open_output_dir(self):
        if self.config.get("output_path", 0) == 1:
            open_dir = ENCODE_DESKTOP_OUTPUT_PATH
        else:
            open_dir = ENCODE_OUTPUT_PATH
        BaseFileManager.open_directory(open_dir)

    def test_encode_decode(self):
        test_text = "测试名字1\n测试名字2\n测试名字3\n测试名字4"
        try:
            encoded = ListEncoder.encode_list(test_text)
            decoded = ListEncoder.decode_list(encoded)
            if test_text + "\n" == decoded + "\n":
                messagebox.showinfo("测试结果", "编码/解码测试成功！\n\n功能正常。")
            else:
                messagebox.showwarning("测试结果", "编码/解码测试失败！")
        except Exception as e:
            messagebox.showerror("测试错误", f"测试失败: {e}")

    def show_statistics(self):
        input_text = self.input_text.get(1.0, tk.END).strip()
        output_text = self.output_text.get(1.0, tk.END).strip()
        input_lines = len([l for l in input_text.split('\n') if l.strip()])
        input_chars = len(input_text)
        output_lines = len([l for l in output_text.split('\n') if l.strip()])
        output_chars = len(output_text)
        stats = f"""
输入统计:
├─ 行数: {input_lines}
├─ 字符数: {input_chars}
└─ 平均每行字符: {input_chars // max(1, input_lines)}

输出统计:
├─ 行数: {output_lines}
├─ 字符数: {output_chars}
└─ 编码率: {output_chars / max(1, input_chars):.2f}x
"""
        messagebox.showinfo("统计信息", stats)

    def open_config_window(self):
        logger.info("打开配置窗口")
        EncodeConfigWindow(self.root, self.config, self)

    def show_help(self):
        help_text = """使用说明：
1. 输入明文名单：在文本框输入名单（每行一个名字），或点击"从文件加载"导入文件。
2. 处理文本：点击"处理文本"自动去除重复项和空格。
3. 编码：点击"快速编码"生成编码文本，或"编码并保存"保存为.rcp文件。
4. 输出文件：编码结果显示在下方，可复制或保存。
5. 文件格式：输入为.txt或.csv，输出为.rcp编码文件。
6. 配置选项：可设置输出位置、文件名等，点击菜单"编辑-配置"。"""
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        about_text = f"""随机抽人名单编码工具
{__encode_description__}
版本：{__encode_version__}
作者：{__author__}"""
        messagebox.showinfo("关于", about_text)

    def set_status(self, message):
        self.status_bar.config(text=message)

    def quit_app(self):
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("用户确认退出程序")
            self.root.quit()


class EncodeConfigWindow:
    def __init__(self, parent, config, app):
        self.parent = parent
        self.config = config
        self.app = app
        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("400x400+50+50")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.window, text="编码工具配置", font=("Helvetica", 16, "bold"), fg="blue").pack(pady=15)
        config_frame = tk.Frame(self.window)
        config_frame.pack(pady=10, padx=20, fill="both", expand=True)

        path_frame = tk.Frame(config_frame)
        path_frame.pack(fill="x", pady=8)
        tk.Label(path_frame, text="输出路径：", width=15, anchor="w").pack(side="left")
        self.path_var = tk.StringVar(value="桌面" if self.config.get("output_path", 0) == 1 else "数据目录")
        tk.Radiobutton(path_frame, text="数据目录", variable=self.path_var, value="数据目录").pack(side="left")
        tk.Radiobutton(path_frame, text="桌面", variable=self.path_var, value="桌面").pack(side="left", padx=(20, 0))

        name_frame = tk.Frame(config_frame)
        name_frame.pack(fill="x", pady=8)
        tk.Label(name_frame, text="默认文件名：", width=15, anchor="w").pack(side="left")
        self.name_var = tk.StringVar(value=self.config.get("default_filename", "sample_list"))
        tk.Entry(name_frame, textvariable=self.name_var, width=20).pack(side="left")

        auto_frame = tk.Frame(config_frame)
        auto_frame.pack(fill="x", pady=8)
        self.auto_clear_var = tk.BooleanVar(value=self.config.get("auto_clear_input", False))
        self.auto_open_var = tk.BooleanVar(value=self.config.get("auto_open_folder", True))
        self.remove_dup_var = tk.BooleanVar(value=self.config.get("remove_duplicates", True))
        self.trim_space_var = tk.BooleanVar(value=self.config.get("trim_spaces", True))
        tk.Checkbutton(auto_frame, text="编码后自动清空输入", variable=self.auto_clear_var).pack(anchor="w", pady=2)
        tk.Checkbutton(auto_frame, text="保存后自动打开文件夹", variable=self.auto_open_var).pack(anchor="w", pady=2)
        tk.Checkbutton(auto_frame, text="自动去除重复项", variable=self.remove_dup_var).pack(anchor="w", pady=2)
        tk.Checkbutton(auto_frame, text="自动去除首尾空格", variable=self.trim_space_var).pack(anchor="w", pady=2)

        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="保存配置", command=self.save_config, width=15, height=2).pack(side="left", padx=10)
        tk.Button(button_frame, text="应用并更新", command=self.apply_and_update, width=15, height=2).pack(side="left", padx=10)
        tk.Button(button_frame, text="关闭", command=self.window.destroy, width=15, height=2).pack(side="left", padx=10)

    def save_config(self):
        try:
            self.config.set("output_path", 1 if self.path_var.get() == "桌面" else 0)
            self.config.set("default_filename", self.name_var.get())
            self.config.set("auto_clear_input", self.auto_clear_var.get())
            self.config.set("auto_open_folder", self.auto_open_var.get())
            self.config.set("remove_duplicates", self.remove_dup_var.get())
            self.config.set("trim_spaces", self.trim_space_var.get())
            self.app.filename_var.set(self.name_var.get())
            logger.info("编码工具配置已保存")
            messagebox.showinfo("成功", "配置已保存")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def apply_and_update(self):
        self.save_config()
        self.app.set_status("配置已应用")
        self.window.destroy()