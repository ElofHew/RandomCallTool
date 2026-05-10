"""
图形界面组件：基础选项卡、主页、随机抽组、随机抽人、配置窗口、通用功能
"""
import os
import logging
from time import strftime
from base64 import b64decode
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont

from .config import ConfigManager
from .file_utils import FileManager, SaveResult
from .sampler import SmartSampler
from .constants import (
    __version__, __author__, __date__,
    __github__, __gitee__, __description__,
    PROG_DATA_PATH, DOCUMENT_PATH, AVAILABLE_FILES_TYPES, LOG_PATH
)

logger = logging.getLogger(__name__)


class BaseTab:
    """选项卡基类"""
    def __init__(self, parent, title):
        self.frame = ttk.Frame(parent)
        self.create_title(title)

    def create_title(self, title, font_size=18):
        title_label = tk.Label(
            self.frame,
            text=title,
            font=("Arial", font_size, "bold"),
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)
        return title_label

    def create_button(self, parent, text, command, width=15, height=2, font_size=10, **kwargs):
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
        history_frame = tk.LabelFrame(self.frame, text="历史记录")
        history_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.history_listbox = tk.Listbox(history_frame, height=height, selectmode=tk.SINGLE)
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        self.history = []
        return history_frame

    def add_history(self, item):
        self.history.insert(0, item)
        self.history_listbox.insert(0, item)
        max_history = ConfigManager().get("max_history_items", 10)
        if len(self.history) > max_history:
            self.history = self.history[:max_history]
            self.history_listbox.delete(max_history, tk.END)

    def add_save_message(self):
        save_message_frame = tk.Frame(self.frame)
        save_message_frame.pack(pady=5)
        tk.Label(save_message_frame, text="保存提示：").pack(side="left")
        self.save_message_entry = tk.Entry(save_message_frame, width=30)
        self.save_message_entry.pack(side="left", padx=5)
        self.save_message_entry.insert(0, "")
        self.save_message_entry.config(state="normal")

    def create_result_label(self, wraplength=350):
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(
            self.frame,
            font=bold_font,
            text="",
            wraplength=wraplength,
            justify="center"
        )
        self.result_label.pack(pady=10, padx=10, fill="both", expand=True)
        return self.result_label

    def clear_result(self):
        if hasattr(self, 'result_label'):
            self.result_label.config(text="")
        logger.info(f"[{self.__class__.__name__}] 清空结果")


class HomeTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽取工具")
        self.create_widgets()

    def create_widgets(self):
        version_label = tk.Label(self.frame, text=f"当前版本：{__version__}", font=("Helvetica", 12), fg="purple")
        version_label.pack(pady=5)

        hint_label = tk.Label(self.frame, text="请点击上方选项卡进行操作", font=("Helvetica", 12), fg="green")
        hint_label.pack(pady=5, ipady=10)

        button_configs = [
            ("打开配置窗口", self.open_config_window),
            ("打开结果目录", self.open_result_directory),
            ("打开关于窗口", self.show_about),
            ("退出程序", self.quit_program)
        ]
        for text, command in button_configs:
            button = self.create_button(self.frame, text, command)
            button.pack(pady=5)

        start_time = strftime("%Y-%m-%d %H:%M:%S")
        start_label = tk.Label(self.frame, text=f"启动时间：{start_time}", font=("Helvetica", 12), fg="gray")
        start_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=5)

    def open_config_window(self):
        logger.info("打开配置窗口")
        ConfigWindow(self.frame)

    def open_result_directory(self):
        FileManager.open_directory(FileManager.get_result_path())

    def show_about(self):
        ApplicationFunctions.show_about(self.frame)

    def quit_program(self):
        logger.info("程序正常退出")
        self.frame.winfo_toplevel().quit()


class RandomGroupTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽组")
        config = ConfigManager()
        self.sampler = SmartSampler(
            use_weighted=config.get("use_weighted_sampling", False),
            shuffle_before=config.get("shuffle_before_sample", True)
        )
        self.create_widgets()

    def create_widgets(self):
        self.group_order_var = tk.StringVar(value="123")
        group_order_frame = tk.Frame(self.frame)
        group_order_frame.pack(pady=5)
        tk.Label(group_order_frame, text="分组方式：").pack(side="left")
        for text, value in [("123(数字)", "123"), ("ABC(字母)", "ABC")]:
            tk.Radiobutton(group_order_frame, text=text, variable=self.group_order_var, value=value).pack(side="left", padx=5)

        config = ConfigManager()
        rcg_total_default = config.get("rcg_total_default", 9)
        rcg_total_default = rcg_total_default if 0 < rcg_total_default <= 26 else 9
        rcg_choice_default = config.get("rcg_choice_default", 3)
        rcg_choice_default = rcg_choice_default if 0 < rcg_choice_default <= rcg_total_default else 3

        input_configs = [
            ("样本总数：", "total_entry", rcg_total_default),
            ("选取数量：", "choice_entry", rcg_choice_default)
        ]
        for label_text, attr_name, default_value in input_configs:
            sub_frame = tk.Frame(self.frame)
            sub_frame.pack(pady=5, fill='x')
            sub_frame.grid_columnconfigure(0, weight=1)
            sub_frame.grid_columnconfigure(1, weight=1)
            tk.Label(sub_frame, text=label_text, width=10).grid(row=0, column=0, padx=5, sticky='e')
            combo = ttk.Combobox(
                sub_frame,
                values=list(range(1, 27 if attr_name == "total_entry" else rcg_total_default + 1)),
                width=5,
                state="readonly"
            )
            combo.grid(row=0, column=1, padx=5, sticky='w')
            combo.set(str(default_value))
            setattr(self, attr_name, combo)

        self.total_entry.bind("<<ComboboxSelected>>", self._on_total_change)

        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        button_configs = [
            ("抽取", self.select_groups),
            ("清空", self.clear_result),
            ("保存", lambda: self.save_result("group")),
            ("重置历史", self.reset_sampler_history)
        ]
        for text, command in button_configs:
            btn = self.create_button(button_frame, text, command, width=8, height=1)
            btn.pack(side="left", padx=5)

        self.add_save_message()
        self.create_history_frame(height=10)
        self.create_result_label()

    def _on_total_change(self, event):
        try:
            total = int(self.total_entry.get())
            if total > 0:
                self.choice_entry['values'] = list(range(1, min(total + 1, 27)))
                self.choice_entry.set(str(min(3, total)))
        except ValueError:
            pass

    def validate_input(self, total_num, choice_num):
        try:
            total_num = int(total_num)
            choice_num = int(choice_num)
            if total_num < 1:
                logger.warning(f"[随机抽组] 样本总数 {total_num} 小于1")
                messagebox.showwarning("错误", "样本总数不能小于1")
                return False, 0, 0
            if choice_num < 1:
                logger.warning(f"[随机抽组] 抽取数量 {choice_num} 小于1")
                messagebox.showwarning("错误", "抽取数量不能小于1")
                return False, 0, 0
            if choice_num > total_num:
                logger.warning(f"[随机抽组] 抽取数量 {choice_num} 大于总数量 {total_num}")
                messagebox.showwarning("错误", "抽取数量不能大于总数量")
                return False, 0, 0
            if choice_num == total_num:
                logger.info(f"[随机抽组] 抽取数量 {choice_num} 等于总数量 {total_num}")
                if not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有组吗？"):
                    return False, 0, 0
            return True, total_num, choice_num
        except ValueError:
            logger.error(f"[随机抽组] 输入值 {total_num} 或 {choice_num} 不是数字")
            messagebox.showwarning("错误", "请输入有效的数字")
            return False, 0, 0

    def select_groups(self):
        self.clear_result()
        total_num = self.total_entry.get()
        choice_num = self.choice_entry.get()
        logger.info(f"[随机抽组] 开始抽取: 总数={total_num}, 抽取数={choice_num}")
        valid, total_num, choice_num = self.validate_input(total_num, choice_num)
        if not valid:
            return
        try:
            if self.group_order_var.get() == "ABC":
                all_groups = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:total_num]
            else:
                all_groups = list(range(1, total_num + 1))
            selected_groups = self.sampler.smart_sample(all_groups, choice_num)
            selected_groups.sort()
            result_text = "\n".join([f"{group}组" for group in selected_groups])
            self.result_label.config(text=result_text)
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}组: {', '.join(map(str, selected_groups))}"
            self.add_history(history_item)
            logger.info(f"[随机抽组] 抽取成功: {selected_groups}")
            messagebox.showinfo("抽取结果", f"抽取结果：\n{result_text}")
            if ConfigManager().get("save_result", True):
                result_list = [f"{group}组" for group in selected_groups]
                SaveResult().save_result("RandomGroup", "随机抽组", result_list)
        except Exception as e:
            logger.error(f"[随机抽组] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")

    def reset_sampler_history(self):
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            logger.info("[随机抽组] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")

    def save_result(self, result_type):
        result_text = self.result_label.cget("text")
        ready_to_save_message = self.save_message_entry.get().strip()
        if not result_text:
            logger.warning(f"[随机抽组] 结果为空，无法保存")
            messagebox.showwarning("错误", "结果为空，无法保存")
            return
        SaveResult().save_result("RandomGroup", "随机抽组", result_text.split("\n"), ready_to_save_message)


class RandomPersonTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽人")
        self.names = []
        self.current_file = None
        self.auto_file = ConfigManager().get("rcp_default_sample", os.path.join(PROG_DATA_PATH, "default.rcp"))
        config = ConfigManager()
        self.sampler = SmartSampler(
            use_weighted=config.get("use_weighted_sampling", False),
            shuffle_before=config.get("shuffle_before_sample", True)
        )
        self.create_widgets()
        self._auto_load_sample()

    def _auto_load_sample(self):
        config = ConfigManager()
        if config.get("auto_load_sample", True) and os.path.exists(self.auto_file):
            self.names, _ = self.load_names_from_file(self.auto_file)
            if self.names:
                logger.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")

    def create_widgets(self):
        file_frame = tk.LabelFrame(self.frame, text="样本列表")
        file_frame.pack(pady=10, padx=10, fill="x")

        self.file_path_label = tk.Label(file_frame, text="未选择文件", fg="gray", wraplength=300)
        self.file_path_label.pack(pady=5, padx=5)

        button_frame = tk.Frame(file_frame)
        button_frame.pack(pady=5)
        button_configs = [
            ("选择文件", self.load_names),
            ("重新加载", self.reload_current_file),
            ("自动加载", self.auto_load_file)
        ]
        for text, command in button_configs:
            btn = self.create_button(button_frame, text, command, width=9, height=1)
            btn.pack(side="left", padx=2)

        info_frame = tk.Frame(self.frame)
        info_frame.pack(pady=5)
        self.sample_count_label = tk.Label(info_frame, text="样本数量: 0", fg="green")
        self.sample_count_label.pack(side="left", padx=10)

        rcp_choice_default = ConfigManager().get("rcp_choice_default", 1)
        rcp_choice_default = rcp_choice_default if 0 < rcp_choice_default <= 10 else 1

        choice_frame = tk.Frame(self.frame)
        choice_frame.pack(pady=10)
        tk.Label(choice_frame, text="抽取数量：").grid(row=0, column=0, padx=5, pady=5)
        self.choice_entry = ttk.Combobox(choice_frame, values=list(range(1, 11)), width=5, state="readonly")
        self.choice_entry.grid(row=0, column=1, padx=5, pady=5)
        self.choice_entry.set(str(rcp_choice_default))
        choice_frame.grid_columnconfigure(0, weight=1)
        choice_frame.grid_columnconfigure(1, weight=1)

        action_frame = tk.Frame(self.frame)
        action_frame.pack(pady=10)
        button_configs = [
            ("抽取", self.select_persons),
            ("清空", self.clear_result),
            ("保存", lambda: self.save_result("person")),
            ("重置历史", self.reset_sampler_history)
        ]
        for text, command in button_configs:
            btn = self.create_button(action_frame, text, command, width=8, height=1)
            btn.pack(side="left", padx=5)

        self.add_save_message()
        self.create_history_frame(height=5)
        self.create_result_label()

    def load_names_from_file(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=AVAILABLE_FILES_TYPES,
                initialdir=DOCUMENT_PATH,
                title="选择样本文件"
            )
            logger.info(f"[随机抽人] 选择文件: {file_path if file_path else '(取消选择)'}")
        if not file_path:
            logger.warning("[随机抽人] 未选择文件")
            return [], []

        additional_messages = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            if file_path.endswith('.rcp'):
                content = self.decode_list(content)
            names = []
            for line in content.splitlines():
                line = line.strip()
                if line:
                    separators = [',', ';', '\t']
                    for sep in separators:
                        if sep in line:
                            names.extend([name.strip() for name in line.split(sep) if name.strip()])
                            break
                    else:
                        names.append(line)
            if ConfigManager().get("rcp_merge_names", True):
                if len(names) != len(set(names)):
                    names = list(set(names))
                    logger.warning(f"[随机抽人] 文件 {file_path} 中存在重复的名字")
                    additional_messages.append("注意，文件中存在重复的名字，已自动去除")
            else:
                if len(names) != len(set(names)):
                    logger.info(f"[随机抽人] 文件 {file_path} 中存在重复的名字，已保留")
                    additional_messages.append("注意，文件中存在重复的名字，已保留")
            if not names:
                logger.warning(f"[随机抽人] 文件 {file_path} 中没有有效数据")
                messagebox.showwarning("警告", "文件中没有有效的数据")
                return [], additional_messages
            update_name = os.path.basename(file_path)
            self.file_path_label.config(text=update_name if not file_path == self.auto_file else "默认样本", fg="purple")
            self.sample_count_label.config(text=f"样本数量: {len(names)}", fg="green")
            max_choice = len(names)
            self.choice_entry['values'] = list(range(1, max_choice + 1))
            self.current_file = file_path
            logger.info(f"[随机抽人] 成功加载 {len(names)} 个名字")
            return names, additional_messages
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    names = [line.strip() for line in file if line.strip()]
                if names:
                    self.file_path_label.config(text=os.path.basename(file_path))
                    self.sample_count_label.config(text=f"样本数量: {len(names)}")
                    self.current_file = file_path
                    return names, additional_messages
            except Exception as e:
                logger.error(f"[随机抽人] 读取文件失败: {e}")
                messagebox.showerror("错误", f"读取文件失败: {e}")
                return [], additional_messages
        except Exception as e:
            logger.error(f"[随机抽人] 读取文件失败: {e}")
            messagebox.showerror("错误", f"读取文件失败: {e}")
            return [], additional_messages

    def reload_current_file(self):
        current_display = self.file_path_label.cget("text")
        file_path = self.current_file
        if current_display != "未选择文件" and file_path:
            self.names, additional_messages = self.load_names_from_file(file_path)
            msg = "\n".join(additional_messages) if additional_messages else ""
            if self.names:
                messagebox.showinfo("成功", f"重新加载成功\n共加载 {len(self.names)} 个名字\n{msg}")

    def auto_load_file(self):
        if self.auto_file and os.path.exists(self.auto_file):
            self.names, additional_messages = self.load_names_from_file(self.auto_file)
            msg = "\n".join(additional_messages) if additional_messages else ""
            if self.names:
                logger.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")
                messagebox.showinfo("成功", f"自动加载成功\n共加载 {len(self.names)} 个名字\n{msg}")
        else:
            logger.warning(f"[随机抽人] 自动加载失败，文件 {self.auto_file} 不存在")
            messagebox.showwarning("警告", f"自动加载失败，文件 {self.auto_file} 不存在")

    def decode_list(self, data=None):
        if not data:
            return ""
        try:
            data = data.strip() + "\n"
            data = b64decode(data).decode('utf-8')
            logger.info("[随机抽人] 成功解码列表数据")
            return data
        except Exception as e:
            logger.error(f"[随机抽人] 解码失败: {e}")
            return ""

    def load_names(self):
        self.names, additional_messages = self.load_names_from_file()
        msg = "\n".join(additional_messages) if additional_messages else ""
        if self.names:
            messagebox.showinfo("成功", f"样本列表已加载\n共加载 {len(self.names)} 个名字\n{msg}")
            logger.info(f"[随机抽人] 手动加载样本列表，共 {len(self.names)} 个名字")

    def select_persons(self):
        if not self.names:
            logger.warning("[随机抽人] 样本列表为空")
            messagebox.showwarning("警告", "请先加载样本列表文件")
            return
        choice_num = self.choice_entry.get()
        if not choice_num:
            logger.warning("[随机抽人] 未选择抽取数量")
            messagebox.showwarning("警告", "请选择抽取数量")
            return
        try:
            choice_num = int(choice_num)
            total_names = len(self.names)
            if choice_num < 1:
                logger.warning(f"[随机抽人] 抽取数量 {choice_num} 小于1")
                messagebox.showwarning("错误", "抽取数量必须大于0")
                return
            if choice_num > total_names:
                logger.warning(f"[随机抽人] 抽取数量 {choice_num} 大于样本数量 {total_names}")
                messagebox.showwarning("错误", f"抽取数量({choice_num})大于样本数量({total_names})")
                return
            if choice_num == total_names:
                if not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有人吗？"):
                    return
            selected_persons = self.sampler.smart_sample(self.names, choice_num)
            self.result_label.config(text="\n".join(selected_persons))
            display_names = selected_persons[:10]
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}人: {', '.join(display_names)}{'...' if len(selected_persons) > 10 else ''}"
            self.add_history(history_item)
            logger.info(f"[随机抽人] 成功抽取 {choice_num} 人: {selected_persons}")
            messagebox.showinfo("抽取结果", f"抽取结果：\n" + "\n".join(selected_persons))
            if ConfigManager().get("save_result", True):
                SaveResult().save_result("RandomPerson", "随机抽人", selected_persons)
        except ValueError:
            logger.error("[随机抽人] 输入值不是有效数字")
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            logger.error(f"[随机抽人] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")

    def reset_sampler_history(self):
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            logger.info("[随机抽人] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")

    def save_result(self, result_type):
        result_text = self.result_label.cget("text")
        ready_to_save_message = self.save_message_entry.get().strip()
        if not result_text:
            logger.warning(f"[随机抽人] 结果为空，无法保存")
            messagebox.showwarning("错误", "结果为空，无法保存")
            return
        SaveResult().save_result("RandomPerson", "随机抽人", result_text.split("\n"), ready_to_save_message)


class ConfigWindow:
    def __init__(self, parent):
        self.parent = parent
        self.config = ConfigManager()
        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("350x480+50+50")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        self.create_widgets()

    def create_widgets(self):
        title_label = tk.Label(self.window, text="配置设置", font=("Helvetica", 16, "bold"), fg="blue")
        title_label.pack(pady=15)

        config_frame = tk.Frame(self.window)
        config_frame.pack(pady=10, padx=20, fill="both", expand=True)

        config_items = [
            ("自动保存结果：", "save_result", ["开", "关"], "开" if self.config.get("save_result", True) else "关"),
            ("结果保存位置：", "result_path", ["数据目录", "桌面"], "桌面" if self.config.get("result_path", 0) == 1 else "数据目录"),
            ("自动加载样本：", "auto_load_sample", ["开", "关"], "开" if self.config.get("auto_load_sample", True) else "关"),
            ("合并重复名字：", "rcp_merge_names", ["开", "关"], "开" if self.config.get("rcp_merge_names", True) else "关"),
            ("抽取前打乱：", "shuffle_before_sample", ["开", "关"], "开" if self.config.get("shuffle_before_sample", True) else "关"),
            ("使用加权抽样：", "use_weighted_sampling", ["开", "关"], "开" if self.config.get("use_weighted_sampling", False) else "关")
        ]

        self.vars = {}
        for label_text, key, values, default_value in config_items:
            frame = tk.Frame(config_frame)
            frame.pack(fill="x", pady=5)
            tk.Label(frame, text=label_text, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=default_value)
            self.vars[key] = var
            for value in values:
                tk.Radiobutton(frame, text=value, variable=var, value=value).pack(side="left", padx=2)

        history_frame = tk.Frame(config_frame)
        history_frame.pack(fill="x", pady=5)
        tk.Label(history_frame, text="历史记录数量：", width=15, anchor="w").pack(side="left")
        self.history_var = tk.StringVar(value=str(self.config.get("max_history_items", 10)))
        tk.Spinbox(history_frame, textvariable=self.history_var, from_=5, to=30, increment=5, state="readonly", width=10).pack(side="left")

        sample_frame = tk.Frame(config_frame)
        sample_frame.pack(fill="x", pady=5)
        tk.Label(sample_frame, text="默认样本位置：", width=15, anchor="w").pack(side="left")
        self.sample_var = tk.Entry(sample_frame, width=20)
        self.sample_var.pack(side="left")
        self.sample_var.config(state="normal")
        self.sample_var.insert(0, self.config.get("rcp_default_sample", ""))
        self.sample_var.config(state="readonly")

        def select_file():
            file_path = filedialog.askopenfilename(
                title="选择文件",
                initialdir=DOCUMENT_PATH,
                filetypes=AVAILABLE_FILES_TYPES
            )
            if file_path:
                self.sample_var.config(state="normal")
                self.sample_var.delete(0, tk.END)
                self.sample_var.insert(0, file_path)
                self.sample_var.config(state="readonly")

        tk.Button(sample_frame, text="选择", command=select_file).pack(side="left", padx=5)

        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        tk.Button(button_frame, text="保存", command=self.save_config, width=10, height=2).pack(side="left", padx=10)
        tk.Button(button_frame, text="关闭", command=self.window.destroy, width=10, height=2).pack(side="left", padx=10)

    def save_config(self):
        try:
            config_updates = {
                "save_result": self.vars["save_result"].get() == "开",
                "result_path": 1 if self.vars["result_path"].get() == "桌面" else 0,
                "auto_load_sample": self.vars["auto_load_sample"].get() == "开",
                "max_history_items": int(self.history_var.get()),
                "rcp_merge_names": self.vars["rcp_merge_names"].get() == "开",
                "rcp_default_sample": self.sample_var.get(),
                "shuffle_before_sample": self.vars["shuffle_before_sample"].get() == "开",
                "use_weighted_sampling": self.vars["use_weighted_sampling"].get() == "开"
            }
            for key, value in config_updates.items():
                self.config.set(key, value)
            logger.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")


class ApplicationFunctions:
    """通用功能集合"""
    @staticmethod
    def show_help():
        help_text = f"""随机抽取工具 v2.1 使用说明

一、主要功能：
1. 随机抽组：从指定数量的组中随机抽取一个或多个组
2. 随机抽人：从样本文件中随机抽取一个或多个人名

二、操作指南：

【随机抽组】
1. 选择分组方式：数字(123)或字母(ABC)
2. 输入总组数（1-26）
3. 输入要抽取的组数（不能超过总组数）
4. 点击"抽取"按钮进行随机抽取

【随机抽人】
1. 加载样本文件（支持 .rcp, .txt, .csv 格式）
   - 点击"选择文件"手动选择
   - 点击"自动加载"使用默认样本
   - 点击"重新加载"刷新当前文件
2. 输入要抽取的人数（不能超过样本数量）
3. 点击"抽取"按钮进行随机抽取

三、文件格式说明：
1. .rcp文件：经过Base64编码的名单文件（推荐使用）
2. .txt文件：纯文本文件，支持逗号、分号、制表符或换行分隔
3. .csv文件：逗号分隔值文件

四、智能抽样功能：
1. 抽取前打乱：提高随机性，减少顺序影响
2. 加权抽样：根据历史抽取次数调整权重，实现长期公平
3. 可重置抽样历史：重新开始公平性计算

五、其他功能：
1. 结果保存：抽取结果自动保存为HTML格式
2. 历史记录：记录最近的抽取历史
3. 配置管理：可设置保存路径、自动保存等选项
4. 日志查看：记录程序运行状态

六、注意事项：
1. 支持重复名字自动去重
2. 抽取人数不能超过样本总数
3. 默认样本存放在 data/default.rcp
4. 结果文件保存在 data/result 目录或桌面

如需更多帮助，请访问项目地址：
GitHub: {__github__}
Gitee: {__gitee__}"""
        messagebox.showinfo("使用说明", help_text)
        logger.info("显示使用说明")

    @staticmethod
    def create_rcp_file():
        rcp_tool_path = os.path.join(PROG_DATA_PATH, "..", "encode.exe")
        if os.path.exists(rcp_tool_path):
            os.system(f"start {rcp_tool_path}")
            logger.info("打开RCP生成工具")
            return True
        else:
            messagebox.showerror("错误", "RCP生成工具不存在")
            logger.error("RCP生成工具不存在")
            return False

    @staticmethod
    def show_about(root):
        about_text = f"""随机抽取工具
{__description__}
版本：{__version__}
作者：{__author__}
日期：{__date__}
Github：{__github__}
Gitee：{__gitee__}"""
        messagebox.showinfo("关于", about_text)
        logger.info("打开关于窗口")

    @staticmethod
    def clear_all_history(group_tab, person_tab):
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            for tab in [group_tab, person_tab]:
                if hasattr(tab, 'history'):
                    tab.history.clear()
                    if hasattr(tab, 'history_listbox'):
                        tab.history_listbox.delete(0, tk.END)
            logger.info("所有历史记录已清除")
            messagebox.showinfo("成功", "历史记录已清除")
            return True
        return False

    @staticmethod
    def clear_log():
        if messagebox.askyesno("确认", "确定要清除所有日志文件吗？"):
            try:
                today_log = f"{strftime('%Y-%m-%d')}.log"
                for file in os.listdir(LOG_PATH):
                    if file == today_log:
                        continue
                    if file.endswith('.log'):
                        os.remove(os.path.join(LOG_PATH, file))
                logger.info("日志文件已清除")
                messagebox.showinfo("成功", "日志文件已清除")
                return True
            except Exception as e:
                logger.error(f"清除日志失败: {e}")
                messagebox.showerror("错误", f"清除日志失败: {e}")
                return False