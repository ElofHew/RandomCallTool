"""
选项卡界面模块 — 主页、随机抽组、随机抽人
"""
import os
import sys
from time import strftime
import tkinter as tk
import tkinter.font as tkFont
from tkinter import ttk, messagebox, filedialog
from core.info import rct_prog_data_path, rct_version, document_path
from core.logman import rctlog
from rctcore.config import ConfigManager
from rctcore.more import More
from rctcore.window import ConfigWindow
from rctcore.sampler import SmartSampler
from rctcore.fileman import FileManager, SaveResult, base64decode

class BaseTab:
    """选项卡基类"""
    def __init__(self, parent, title):
        self.frame = ttk.Frame(parent)
        self.create_title(title)
        
    def create_title(self, title, font_size=18):
        """创建标题"""
        title_label = tk.Label(
            self.frame, 
            text=title, 
            font=("Arial", font_size, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)
        return title_label
    
    def create_button(self, parent, text, command, width=15, height=2, font_size=10, **kwargs):
        """创建标准按钮"""
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
        """创建历史记录框架"""
        history_frame = tk.LabelFrame(self.frame, text="历史记录")
        history_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.history_listbox = tk.Listbox(
            history_frame,
            height=height,
            selectmode=tk.SINGLE
        )
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        
        self.history = []
        return history_frame
    
    def add_history(self, item):
        """添加历史记录"""
        self.history.insert(0, item)
        self.history_listbox.insert(0, item)
        
        max_history = ConfigManager().get("max_history_items", 10)
        if len(self.history) > max_history:
            self.history = self.history[:max_history]
            self.history_listbox.delete(max_history, tk.END)
    
    def add_save_message(self):
        """添加保存提示信息"""
        save_message_frame = tk.Frame(self.frame)
        save_message_frame.pack(pady=5)
        tk.Label(save_message_frame, text="保存提示：").pack(side="left")
        self.save_message_entry = tk.Entry(save_message_frame, width=30)
        self.save_message_entry.pack(side="left", padx=5)
        self.save_message_entry.insert(0, "")
        self.save_message_entry.config(state="normal")

    def create_result_label(self, wraplength=350):
        """创建结果标签"""
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
        """清空结果"""
        if hasattr(self, 'result_label'):
            self.result_label.config(text="")
        rctlog.info(f"[{self.__class__.__name__}] 清空结果")

class HomeTab(BaseTab):
    """首页选项卡"""
    def __init__(self, parent):
        super().__init__(parent, "随机抽取工具")
        self.create_widgets()

    def create_widgets(self):
        version_label = tk.Label(
            self.frame,
            text=f"当前版本：{rct_version}",
            font=("Helvetica", 12),
            fg="purple"
        )
        version_label.pack(pady=5)

        hint_label = tk.Label(
            self.frame,
            text="请点击上方选项卡进行操作",
            font=("Helvetica", 12),
            fg="green"
        )
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
        start_label = tk.Label(
            self.frame,
            text=f"启动时间：{start_time}",
            font=("Helvetica", 12),
            fg="gray"
        )
        start_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=5)

    def open_config_window(self):
        """打开配置窗口"""
        rctlog.info("打开配置窗口")
        ConfigWindow(self.frame)

    def open_result_directory(self):
        """打开结果目录"""
        FileManager.open_directory(FileManager.get_result_path())

    def show_about(self):
        """显示关于信息"""
        rctlog.info("打开关于窗口")
        More(self.frame).about()

    def quit_program(self):
        """退出程序"""
        rctlog.info("程序正常退出")
        sys.exit(0)

class RandomGroupTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽组")
        # 初始化抽样器（在构造函数中创建，而不是每次抽取都创建）
        config = ConfigManager()
        self.sampler = SmartSampler(
            use_weighted=config.get("use_weighted_sampling", False),
            shuffle_before=config.get("shuffle_before_sample", True)
        )
        self.create_widgets()
        
    def create_widgets(self):
        """创建随机抽组界面组件"""
        self.group_order_var = tk.StringVar(value="123")
        group_order_frame = tk.Frame(self.frame)
        group_order_frame.pack(pady=5)
        tk.Label(group_order_frame, text="分组方式：").pack(side="left")

        for text, value in [("123(数字)", "123"), ("ABC(字母)", "ABC")]:
            tk.Radiobutton(
                group_order_frame,
                text=text,
                variable=self.group_order_var,
                value=value
            ).pack(side="left", padx=5)

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
            button = self.create_button(button_frame, text, command, width=8, height=1)
            button.pack(side="left", padx=5)

        self.add_save_message()
        self.create_history_frame(height=10)
        self.create_result_label()
    
    def _on_total_change(self, event):
        """当总数变化时更新可选的抽取数量"""
        try:
            total = int(self.total_entry.get())
            if total > 0:
                self.choice_entry['values'] = list(range(1, min(total + 1, 27)))
                self.choice_entry.set(str(min(3, total)))
        except ValueError:
            pass
    
    def validate_input(self, total_num, choice_num):
        """校验输入值"""
        try:
            total_num = int(total_num)
            choice_num = int(choice_num)
            
            if total_num < 1:
                rctlog.warning(f"[随机抽组] 样本总数 {total_num} 小于1")
                messagebox.showwarning("错误", "样本总数不能小于1")
                return False, 0, 0
            
            if choice_num < 1:
                rctlog.warning(f"[随机抽组] 抽取数量 {choice_num} 小于1")
                messagebox.showwarning("错误", "抽取数量不能小于1")
                return False, 0, 0
            
            if choice_num > total_num:
                rctlog.warning(f"[随机抽组] 抽取数量 {choice_num} 大于总数量 {total_num}")
                messagebox.showwarning("错误", "抽取数量不能大于总数量")
                return False, 0, 0
            
            if choice_num == total_num:
                rctlog.info(f"[随机抽组] 抽取数量 {choice_num} 等于总数量 {total_num}")
                if not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有组吗？"):
                    return False, 0, 0
            
            return True, total_num, choice_num
            
        except ValueError:
            rctlog.error(f"[随机抽组] 输入值 {total_num} 或 {choice_num} 不是数字")
            messagebox.showwarning("错误", "请输入有效的数字")
            return False, 0, 0
    
    def select_groups(self):
        """随机抽取组"""
        self.clear_result()
        
        total_num = self.total_entry.get()
        choice_num = self.choice_entry.get()
        
        rctlog.info(f"[随机抽组] 开始抽取: 总数={total_num}, 抽取数={choice_num}")
        
        valid, total_num, choice_num = self.validate_input(total_num, choice_num)
        if not valid:
            rctlog.warning("[随机抽组] 输入验证失败")
            return
        
        try:
            # 生成所有组号
            if self.group_order_var.get() == "ABC":
                all_groups = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")[:total_num]
            else:
                all_groups = list(range(1, total_num + 1))
            
            # 使用智能抽样器抽取
            selected_groups = self.sampler.smart_sample(all_groups, choice_num)
            selected_groups.sort()
            
            # 显示结果
            result_text = "\n".join([f"{group}组" for group in selected_groups])
            self.result_label.config(text=result_text)
            
            # 添加到历史记录
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}组: {', '.join(map(str, selected_groups))}"
            self.add_history(history_item)
            
            rctlog.info(f"[随机抽组] 抽取成功: {selected_groups}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n{result_text}")
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                result_list = [f"{group}组" for group in selected_groups]
                file_path = SaveResult().save_result("RandomGroup", "随机抽组", result_list)
                if file_path:
                    rctlog.info(f"[随机抽组] 结果已保存到: {file_path}")
            
        except Exception as e:
            rctlog.error(f"[随机抽组] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")
    
    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            rctlog.info("[随机抽组] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")
    
    def save_result(self, result_type):
        """保存结果"""
        result_text = self.result_label.cget("text")
        ready_to_save_message = self.save_message_entry.get().strip()
        if not result_text:
            rctlog.warning(f"[随机抽组] 结果为空，无法保存")
            messagebox.showwarning("错误", "结果为空，无法保存")
            return
        
        SaveResult().save_result("RandomGroup", "随机抽组", result_text.split("\n"), ready_to_save_message)

class RandomPersonTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽人")
        self.names = []
        self.current_file = None
        self.auto_file = ConfigManager().get("rcp_default_sample", os.path.join(rct_prog_data_path, "default.rcp"))
        # 初始化抽样器
        config = ConfigManager()
        self.sampler = SmartSampler(
            use_weighted=config.get("use_weighted_sampling", False),
            shuffle_before=config.get("shuffle_before_sample", True)
        )
        self.create_widgets()
        self._auto_load_sample()
        
    def _auto_load_sample(self):
        """自动加载样本文件"""
        config = ConfigManager()
        if config.get("auto_load_sample", True) and os.path.exists(self.auto_file):
            self.names, additional_messages = self.load_names_from_file(self.auto_file)
            if self.names:
                rctlog.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")
        
    def create_widgets(self):
        """创建随机抽人界面组件"""
        file_frame = tk.LabelFrame(self.frame, text="样本列表")
        file_frame.pack(pady=10, padx=10, fill="x")

        self.file_path_label = tk.Label(
            file_frame,
            text="未选择文件",
            fg="gray",
            wraplength=300
        )
        self.file_path_label.pack(pady=5, padx=5)

        button_frame = tk.Frame(file_frame)
        button_frame.pack(pady=5)

        button_configs = [
            ("选择文件", self.load_names),
            ("重新加载", self.reload_current_file),
            ("自动加载", self.auto_load_file)
        ]

        for text, command in button_configs:
            button = self.create_button(button_frame, text, command, width=9, height=1)
            button.pack(side="left", padx=2)

        info_frame = tk.Frame(self.frame)
        info_frame.pack(pady=5)

        self.sample_count_label = tk.Label(
            info_frame,
            text="样本数量: 0",
            fg="green"
        )
        self.sample_count_label.pack(side="left", padx=10)

        rcp_choice_default = ConfigManager().get("rcp_choice_default", 1)
        rcp_choice_default = rcp_choice_default if 0 < rcp_choice_default <= 10 else 1

        choice_frame = tk.Frame(self.frame)
        choice_frame.pack(pady=10)

        tk.Label(choice_frame, text="抽取数量：").grid(row=0, column=0, padx=5, pady=5)

        self.choice_entry = ttk.Combobox(
            choice_frame,
            values=list(range(1, 11)),
            width=5,
            state="readonly"
        )
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
            button = self.create_button(action_frame, text, command, width=8, height=1)
            button.pack(side="left", padx=5)

        self.add_save_message()
        self.create_history_frame(height=5)
        self.create_result_label()
    
    def load_names_from_file(self, file_path=None):
        """从文件加载名字"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("可用文件", "*.rcp;*.txt;*.csv"),
                    ("名单文件", "*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*")
                ],
                initialdir=document_path,
                title="选择样本文件"
            )
            rctlog.info(f"[随机抽人] 选择文件: {file_path if file_path else '(取消选择)'}")
        
        if not file_path:
            rctlog.warning("[随机抽人] 未选择文件")
            return [], []
        
        additional_messages = []

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Base64解码
            if file_path.endswith('.rcp'):
                content = self.decode_list(content)
            
            # 支持多种分隔符
            names = []
            for line in content.splitlines():
                line = line.strip()
                if line:
                    # 尝试按逗号、分号、制表符、空格分割
                    separators = [',', ';', '\t']
                    for sep in separators:
                        if sep in line:
                            names.extend([name.strip() for name in line.split(sep) if name.strip()])
                            break
                    else:
                        names.append(line)
            
            if ConfigManager().get("rcp_merge_names", True):
                # 判断并去除重复的名字
                if len(names) != len(set(names)):
                    names = list(set(names))
                    rctlog.warning(f"[随机抽人] 文件 {file_path} 中存在重复的名字")
                    additional_messages.append("注意，文件中存在重复的名字，已自动去除")
            else:
                # 保留重复的名字
                if len(names) != len(set(names)):
                    rctlog.info(f"[随机抽人] 文件 {file_path} 中存在重复的名字，已保留")
                    additional_messages.append("注意，文件中存在重复的名字，已保留")

            # 无效数据过滤
            if not names:
                rctlog.warning(f"[随机抽人] 文件 {file_path} 中没有有效数据")
                messagebox.showwarning("警告", "文件中没有有效的数据")
                return [], additional_messages
            
            # 更新显示
            update_name = os.path.basename(file_path)
            self.file_path_label.config(
                text=update_name if not file_path == self.auto_file else "默认样本",
                fg="purple"
            )
            self.sample_count_label.config(
                text=f"样本数量: {len(names)}",
                fg="green"
            )
            
            # 更新可选的抽取数量
            max_choice = len(names)
            self.choice_entry['values'] = list(range(1, max_choice + 1))
            
            self.current_file = file_path

            rctlog.info(f"[随机抽人] 成功加载 {len(names)} 个名字")
            return names, additional_messages
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    names = [line.strip() for line in file if line.strip()]
                if names:
                    self.file_path_label.config(text=os.path.basename(file_path))
                    self.sample_count_label.config(text=f"样本数量: {len(names)}")
                    return names, additional_messages
            except Exception as e:
                rctlog.error(f"[随机抽人] 读取文件失败: {e}")
                messagebox.showerror("错误", f"读取文件失败: {e}")
                return [], additional_messages
        except Exception as e:
            rctlog.error(f"[随机抽人] 读取文件失败: {e}")
            messagebox.showerror("错误", f"读取文件失败: {e}")
            return [], additional_messages
    
    def reload_current_file(self):
        """重新加载当前文件"""
        current_display = self.file_path_label.cget("text")
        file_path = self.current_file
        if current_display != "未选择文件" and file_path:
            self.names, additional_messages = self.load_names_from_file(file_path)
            additional_messages = "\n".join(additional_messages) if additional_messages else ""
            if self.names:
                messagebox.showinfo("成功", f"重新加载成功\n共加载 {len(self.names)} 个名字\n{additional_messages}")
    
    def auto_load_file(self):
        """自动加载样本文件"""
        if self.auto_file and os.path.exists(self.auto_file):
            self.names, additional_messages = self.load_names_from_file(self.auto_file)
            additional_messages = "\n".join(additional_messages) if additional_messages else ""
            if self.names:
                rctlog.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")
                messagebox.showinfo("成功", f"自动加载成功\n共加载 {len(self.names)} 个名字\n{additional_messages}")
        else:
            rctlog.warning(f"[随机抽人] 自动加载失败，文件 {self.auto_file} 不存在")
            messagebox.showwarning("警告", f"自动加载失败，文件 {self.auto_file} 不存在")

    def decode_list(self, data=None):
        """解码列表"""
        if not data:
            return ""
        
        data = data.strip() + "\n"
        return base64decode(data)

    def load_names(self):
        """加载名字并更新显示"""
        self.names, additional_messages = self.load_names_from_file()
        additional_messages = "\n".join(additional_messages) if additional_messages else ""
        if self.names:
            messagebox.showinfo("成功", f"样本列表已加载\n共加载 {len(self.names)} 个名字\n{additional_messages}")
            rctlog.info(f"[随机抽人] 手动加载样本列表，共 {len(self.names)} 个名字")
    
    def select_persons(self):
        """随机抽取人员"""
        if not self.names:
            rctlog.warning("[随机抽人] 样本列表为空")
            messagebox.showwarning("警告", "请先加载样本列表文件")
            return
        
        choice_num = self.choice_entry.get()
        if not choice_num:
            rctlog.warning("[随机抽人] 未选择抽取数量")
            messagebox.showwarning("警告", "请选择抽取数量")
            return
        
        try:
            choice_num = int(choice_num)
            total_names = len(self.names)
            
            if choice_num < 1:
                rctlog.warning(f"[随机抽人] 抽取数量 {choice_num} 小于1")
                messagebox.showwarning("错误", "抽取数量必须大于0")
                return
            
            if choice_num > total_names:
                rctlog.warning(f"[随机抽人] 抽取数量 {choice_num} 大于样本数量 {total_names}")
                messagebox.showwarning("错误", f"抽取数量({choice_num})大于样本数量({total_names})")
                return
            
            if choice_num == total_names:
                if not messagebox.askyesno("提示", "抽取数量与总数量相同，确定要抽取所有人吗？"):
                    return
            
            # 使用智能抽样器抽取
            selected_persons = self.sampler.smart_sample(self.names, choice_num)
            
            # 显示结果
            self.result_label.config(text="\n".join(selected_persons))
            
            # 添加到历史记录
            display_names = selected_persons[:10]
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}人: {', '.join(display_names)}{'...' if len(selected_persons) > 10 else ''}"
            self.add_history(history_item)
            
            rctlog.info(f"[随机抽人] 成功抽取 {choice_num} 人: {selected_persons}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n" + "\n".join(selected_persons))
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                file_path = SaveResult().save_result("RandomPerson", "随机抽人", selected_persons)
                if file_path:
                    rctlog.info(f"[随机抽人] 结果已保存到: {file_path}")
                    
        except ValueError:
            rctlog.error("[随机抽人] 输入值不是有效数字")
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            rctlog.error(f"[随机抽人] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")
    
    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            rctlog.info("[随机抽人] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")
    
    def save_result(self, result_type):
        """保存结果"""
        result_text = self.result_label.cget("text")
        ready_to_save_message = self.save_message_entry.get().strip()
        if not result_text:
            rctlog.warning(f"[随机抽人] 结果为空，无法保存")
            messagebox.showwarning("错误", "结果为空，无法保存")
            return
        
        SaveResult().save_result("RandomPerson", "随机抽人", result_text.split("\n"), ready_to_save_message)
