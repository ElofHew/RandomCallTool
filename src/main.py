"""
@Name: 随机抽取工具
@Author: Dan_Evan
@Date: 2026-01-10
@Version: 2.1
@Description: 一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。
"""

# 导入tkinter(GUI)库
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
# 导入基本库
import os
import json
from random import sample, shuffle, choices
from time import strftime
from sys import exit as sys_exit
from base64 import b64decode
from collections import defaultdict

# 导入日志库
import logging
from logging.handlers import RotatingFileHandler

"""定义程序元数据"""
__version__ = "2.1"
__author__ = "Dan_Evan"
__date__ = "2026-01-10"
__github__ = "https://github.com/ElofHew/RandomCallTool"
__gitee__ = "https://gitee.com/ElofHew/RandomCallTool"
__description__ = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"

"""定义全局变量"""
work_path = os.getcwd()
prog_data_path = os.path.join(work_path, "data")
log_path = os.path.join(prog_data_path, "log")
result_path = os.path.join(prog_data_path, "result")

user_home_path = os.path.expanduser("~")
desktop_path = os.path.join(user_home_path, "Desktop")
desktop_result_path = os.path.join(desktop_path, "随机抽取结果")
document_path = os.path.join(user_home_path, "Documents")

config_path = os.path.join(prog_data_path, "config.json")

available_files_types = [
    ("可用文件", "*.rcp;*.txt;*.csv"),
    ("名单文件", "*.rcp"),
    ("文本文件", "*.txt"),
    ("CSV文件", "*.csv"),
    ("所有文件", "*.*")
]

# 创建程序数据目录
for path in [prog_data_path, result_path, log_path]:
    os.makedirs(path, exist_ok=True)

"""初始化日志功能"""
def setup_logging():
    """设置日志记录"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

class ConfigManager:
    """配置管理器"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        default_config = {
            "result_path": 0,  # 结果保存路径(0:数据目录, 1:桌面)
            "save_result": True,  # 是否自动保存结果
            "auto_load_sample": True,  # 自动加载默认名单文件
            "max_history_items": 10,  # 最大历史记录条目数
            "rcg_total_default": 9,  # 随机抽组默认总组数
            "rcg_choice_default": 3,  # 随机抽组默认选择数
            "rcp_choice_default": 1,  # 随机抽人默认选择数
            "rcp_merge_names": True,  # 是否合并重复名字
            "rcp_default_sample": ".\\data\\default.rcp",  # 默认名单文件路径
            "shuffle_before_sample": True,  # 抽取前是否打乱
            "use_weighted_sampling": False,  # 是否使用加权抽样
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                    for key, value in default_config.items():
                        if key not in self._config:
                            self._config[key] = value
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
            self._save_config()
        
        logger.info(f"配置已加载: {self._config}")
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value
        self._save_config()

class FileManager:
    """文件管理器"""
    
    @staticmethod
    def get_result_path():
        """获取结果保存路径"""
        config = ConfigManager()
        if config.get("result_path", 0) == 1:
            save_dir = desktop_result_path
        else:
            save_dir = result_path
        
        if not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
        
        return save_dir
    
    @staticmethod
    def open_directory(path):
        """打开目录"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            os.startfile(path)
            logger.info(f"打开目录: {path}")
            return True
        except Exception as e:
            logger.error(f"打开目录失败: {e}")
            messagebox.showerror("错误", f"无法打开目录: {e}")
            return False
    
    @staticmethod
    def open_log_file():
        """打开日志文件"""
        try:
            log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
            if os.path.exists(log_file):
                os.startfile(log_file)
                logger.info("打开日志文件")
                return True
            else:
                messagebox.showinfo("提示", "今天的日志文件不存在")
                return False
        except Exception as e:
            logger.error(f"打开日志文件失败: {e}")
            messagebox.showerror("错误", f"无法打开日志文件: {e}")
            return False

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        logger.info("程序正常退出")
        self.root.quit()

    def about(self):
        """关于"""
        about_text = f"""随机抽取工具
{__description__}
版本：{__version__}
作者：{__author__}
日期：{__date__}
Github：{__github__}
Gitee：{__gitee__}"""

        messagebox.showinfo("关于", about_text)
        logger.info("打开关于窗口")

class SmartSampler:
    """智能抽样器"""
    
    def __init__(self, use_weighted=False, shuffle_before=True):
        """
        初始化抽样器
        
        Args:
            use_weighted: 是否使用加权抽样
            shuffle_before: 是否在抽样前打乱
        """
        self.use_weighted = use_weighted
        self.shuffle_before = shuffle_before
        self.selection_history = defaultdict(int)  # 记录选中次数
        self.total_selections = 0  # 总抽取次数
        
    def smart_sample(self, population, k):
        """
        智能抽样
        
        Args:
            population: 总体列表
            k: 抽取数量
            
        Returns:
            抽取结果列表
        """
        if not population:
            return []
        
        # 如果k大于或等于总体数量，直接返回整个总体（打乱后）
        if k >= len(population):
            result = population.copy()
            shuffle(result)
            return result[:k] if k > len(population) else result
        
        if self.use_weighted:
            return self._weighted_sample(population, k)
        else:
            return self._simple_sample(population, k)
    
    def _simple_sample(self, population, k):
        """简单随机抽样（可先打乱）"""
        working_population = population.copy()
        
        if self.shuffle_before:
            shuffle(working_population)
        
        # 使用sample进行无放回抽样
        result = sample(working_population, k)
        
        # 更新历史记录
        self._update_history(result)
        
        return result
    
    def _weighted_sample(self, population, k):
        """加权随机抽样"""
        # 计算每个元素的权重：选中次数越少，权重越高
        weights = []
        for item in population:
            # 基础权重为1，每被选中一次减少0.1权重
            weight = 1.0 - (self.selection_history.get(item, 0) * 0.1)
            weight = max(0.1, weight)  # 最小权重为0.1
            weights.append(weight)
        
        # 使用加权抽样（无放回）
        result = []
        temp_population = population.copy()
        temp_weights = weights.copy()
        
        for _ in range(k):
            if not temp_population:
                break
                
            # 根据权重随机选择一个
            selected = choices(temp_population, weights=temp_weights, k=1)[0]
            result.append(selected)
            
            # 从临时列表中移除已选中的
            idx = temp_population.index(selected)
            temp_population.pop(idx)
            temp_weights.pop(idx)
        
        # 更新历史记录
        self._update_history(result)
        
        return result
    
    def _update_history(self, selected_items):
        """更新选中历史"""
        for item in selected_items:
            self.selection_history[item] += 1
        self.total_selections += 1
    
    def get_selection_stats(self):
        """获取选中统计"""
        return {
            'total_selections': self.total_selections,
            'selection_counts': dict(self.selection_history),
            'most_selected': max(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None,
            'least_selected': min(self.selection_history.items(), key=lambda x: x[1]) if self.selection_history else None,
        }
    
    def reset_history(self):
        """重置历史记录"""
        self.selection_history.clear()
        self.total_selections = 0

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
        logger.info(f"[{self.__class__.__name__}] 清空结果")

class HomeTab(BaseTab):
    def __init__(self, parent):
        super().__init__(parent, "随机抽取工具")
        self.create_widgets()

    def create_widgets(self):
        """创建主界面组件"""
        # 显示当前版本
        version_label = tk.Label(
            self.frame,
            text=f"当前版本：{__version__}",
            font=("Helvetica", 12),
            fg="purple"
        )
        version_label.pack(pady=5)

        # 提示点击上方选项卡
        hint_label = tk.Label(
            self.frame,
            text="请点击上方选项卡进行操作",
            font=("Helvetica", 12),
            fg="green"
        )
        hint_label.pack(pady=5, ipady=10)

        # 创建功能按钮
        button_configs = [
            ("打开配置窗口", self.open_config_window),
            ("打开结果目录", self.open_result_directory),
            ("打开关于窗口", self.show_about),
            ("退出程序", self.quit_program)
        ]
        
        for text, command in button_configs:
            button = self.create_button(self.frame, text, command)
            button.pack(pady=5)

        # 显示启动时间
        start_time = strftime("%Y-%m-d %H:%M:%S")
        start_label = tk.Label(
            self.frame,
            text=f"启动时间：{start_time}",
            font=("Helvetica", 12),
            fg="gray"
        )
        start_label.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=5)

    def open_config_window(self):
        """打开配置窗口"""
        logger.info("打开配置窗口")
        ConfigWindow(self.frame)

    def open_result_directory(self):
        """打开结果目录"""
        FileManager.open_directory(FileManager.get_result_path())

    def show_about(self):
        """显示关于信息"""
        logger.info("打开关于窗口")
        More(self.frame).about()

    def quit_program(self):
        """退出程序"""
        logger.info("程序正常退出")
        sys_exit()

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
        # 选择分组方式
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

        # 加载默认配置
        config = ConfigManager()
        rcg_total_default = config.get("rcg_total_default", 9)
        rcg_total_default = rcg_total_default if 0 < rcg_total_default <= 26 else 9
        rcg_choice_default = config.get("rcg_choice_default", 3)
        rcg_choice_default = rcg_choice_default if 0 < rcg_choice_default <= rcg_total_default else 3

        # 创建标签和选择框
        input_configs = [
            ("样本总数：", "total_entry", rcg_total_default),
            ("选取数量：", "choice_entry", rcg_choice_default)
        ]
        
        for label_text, attr_name, default_value in input_configs:
            # 创建子容器
            sub_frame = tk.Frame(self.frame)
            sub_frame.pack(pady=5, fill='x')
            
            # 使用 grid 布局来居中显示标签和选择框
            sub_frame.grid_columnconfigure(0, weight=1)
            sub_frame.grid_columnconfigure(1, weight=1)

            # 创建标签并放入子容器，使用 grid 布局并居中显示
            tk.Label(sub_frame, text=label_text, width=10).grid(row=0, column=0, padx=5, sticky='e')

            # 创建下拉选择框并放入子容器，使用 grid 布局并居中显示
            combo = ttk.Combobox(
                sub_frame, 
                values=list(range(1, 27 if attr_name == "total_entry" else rcg_total_default + 1)),
                width=5,
                state="readonly"
            )
            combo.grid(row=0, column=1, padx=5, sticky='w')
            combo.set(str(default_value))

            # 设置属性
            setattr(self, attr_name, combo)

        self.total_entry.bind("<<ComboboxSelected>>", self._on_total_change)
        
        # 创建按钮框架
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        button_configs = [
            ("抽取", self.select_groups),
            ("清空", self.clear_result),
            ("保存", lambda: self.save_result("group")),
            ("重置历史", self.reset_sampler_history)  # 新增按钮
        ]
        
        for text, command in button_configs:
            button = self.create_button(button_frame, text, command, width=8, height=1)
            button.pack(side="left", padx=5)
        
        # 创建保存提示信息
        self.add_save_message()

        # 创建历史记录框架
        self.create_history_frame(height=10)
        
        # 创建结果标签
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
        """随机抽取组"""
        self.clear_result()
        
        total_num = self.total_entry.get()
        choice_num = self.choice_entry.get()
        
        logger.info(f"[随机抽组] 开始抽取: 总数={total_num}, 抽取数={choice_num}")
        
        valid, total_num, choice_num = self.validate_input(total_num, choice_num)
        if not valid:
            logger.warning("[随机抽组] 输入验证失败")
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
            
            logger.info(f"[随机抽组] 抽取成功: {selected_groups}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n{result_text}")
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                result_list = [f"{group}组" for group in selected_groups]
                file_path = SaveResult().save_result("RandomGroup", "随机抽组", result_list)
                if file_path:
                    logger.info(f"[随机抽组] 结果已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"[随机抽组] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")
    
    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            logger.info("[随机抽组] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")
    
    def save_result(self, result_type):
        """保存结果"""
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
        self.auto_file = ConfigManager().get("rcp_default_sample", os.path.join(prog_data_path, "default.rcp"))
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
                logger.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")
        
    def create_widgets(self):
        """创建随机抽人界面组件"""
        # 文件选择区域
        file_frame = tk.LabelFrame(self.frame, text="样本列表")
        file_frame.pack(pady=10, padx=10, fill="x")
        
        # 文件路径显示
        self.file_path_label = tk.Label(
            file_frame, 
            text="未选择文件", 
            fg="gray",
            wraplength=300
        )
        self.file_path_label.pack(pady=5, padx=5)
        
        # 按钮框架
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
        
        # 样本信息
        info_frame = tk.Frame(self.frame)
        info_frame.pack(pady=5)
        
        self.sample_count_label = tk.Label(
            info_frame, 
            text="样本数量: 0", 
            fg="green"
        )
        self.sample_count_label.pack(side="left", padx=10)
        
        # 加载默认配置
        rcp_choice_default = ConfigManager().get("rcp_choice_default", 1)
        rcp_choice_default = rcp_choice_default if 0 < rcp_choice_default <= 10 else 1

        # 抽取数量选择
        choice_frame = tk.Frame(self.frame)
        choice_frame.pack(pady=10)

        # 使用grid布局将标签和组合框放置在一行
        tk.Label(choice_frame, text="抽取数量：").grid(row=0, column=0, padx=5, pady=5)

        self.choice_entry = ttk.Combobox(
            choice_frame,
            values=list(range(1, 11)),
            width=5,
            state="readonly"
        )
        self.choice_entry.grid(row=0, column=1, padx=5, pady=5)
        self.choice_entry.set(str(rcp_choice_default))

        # 设置choice_frame居中
        choice_frame.grid_columnconfigure(0, weight=1)
        choice_frame.grid_columnconfigure(1, weight=1)

        # 抽取按钮框架
        action_frame = tk.Frame(self.frame)
        action_frame.pack(pady=10)
        
        button_configs = [
            ("抽取", self.select_persons),
            ("清空", self.clear_result),
            ("保存", lambda: self.save_result("person")),
            ("重置历史", self.reset_sampler_history)  # 新增按钮
        ]
        
        for text, command in button_configs:
            button = self.create_button(action_frame, text, command, width=8, height=1)
            button.pack(side="left", padx=5)
        
        # 创建保存提示信息
        self.add_save_message()

        # 创建历史记录框架
        self.create_history_frame(height=5)
        
        # 创建结果标签
        self.create_result_label()
    
    def load_names_from_file(self, file_path=None):
        """从文件加载名字"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=available_files_types,
                initialdir=document_path,
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
                    logger.warning(f"[随机抽人] 文件 {file_path} 中存在重复的名字")
                    additional_messages.append("注意，文件中存在重复的名字，已自动去除")
            else:
                # 保留重复的名字
                if len(names) != len(set(names)):
                    logger.info(f"[随机抽人] 文件 {file_path} 中存在重复的名字，已保留")
                    additional_messages.append("注意，文件中存在重复的名字，已保留")

            # 无效数据过滤
            if not names:
                logger.warning(f"[随机抽人] 文件 {file_path} 中没有有效数据")
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

            logger.info(f"[随机抽人] 成功加载 {len(names)} 个名字")
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
                logger.error(f"[随机抽人] 读取文件失败: {e}")
                messagebox.showerror("错误", f"读取文件失败: {e}")
                return [], additional_messages
        except Exception as e:
            logger.error(f"[随机抽人] 读取文件失败: {e}")
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
                logger.info(f"[随机抽人] 自动加载 {self.auto_file}, 共 {len(self.names)} 个名字")
                messagebox.showinfo("成功", f"自动加载成功\n共加载 {len(self.names)} 个名字\n{additional_messages}")
        else:
            logger.warning(f"[随机抽人] 自动加载失败，文件 {self.auto_file} 不存在")
            messagebox.showwarning("警告", f"自动加载失败，文件 {self.auto_file} 不存在")

    def decode_list(self, data=None):
        """解码列表"""
        if not data:
            return ""
        
        try:
            data = data.strip() + "\n"
            data = b64decode(data).decode('utf-8')
            logger.info(f"[随机抽人] 成功解码列表数据")
            return data
        except Exception as e:
            logger.error(f"[随机抽人] 解码失败: {e}")
            return ""

    def load_names(self):
        """加载名字并更新显示"""
        self.names, additional_messages = self.load_names_from_file()
        additional_messages = "\n".join(additional_messages) if additional_messages else ""
        if self.names:
            messagebox.showinfo("成功", f"样本列表已加载\n共加载 {len(self.names)} 个名字\n{additional_messages}")
            logger.info(f"[随机抽人] 手动加载样本列表，共 {len(self.names)} 个名字")
    
    def select_persons(self):
        """随机抽取人员"""
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
            
            # 使用智能抽样器抽取
            selected_persons = self.sampler.smart_sample(self.names, choice_num)
            
            # 显示结果
            self.result_label.config(text="\n".join(selected_persons))
            
            # 添加到历史记录
            display_names = selected_persons[:10]
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}人: {', '.join(display_names)}{'...' if len(selected_persons) > 10 else ''}"
            self.add_history(history_item)
            
            logger.info(f"[随机抽人] 成功抽取 {choice_num} 人: {selected_persons}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n" + "\n".join(selected_persons))
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                file_path = SaveResult().save_result("RandomPerson", "随机抽人", selected_persons)
                if file_path:
                    logger.info(f"[随机抽人] 结果已保存到: {file_path}")
                    
        except ValueError:
            logger.error("[随机抽人] 输入值不是有效数字")
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            logger.error(f"[随机抽人] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")
    
    def reset_sampler_history(self):
        """重置抽样器历史记录"""
        if messagebox.askyesno("确认", "确定要重置抽样历史记录吗？这将影响加权抽样的公平性计算。"):
            self.sampler.reset_history()
            logger.info("[随机抽人] 抽样历史记录已重置")
            messagebox.showinfo("成功", "抽样历史记录已重置")
    
    def save_result(self, result_type):
        """保存结果"""
        result_text = self.result_label.cget("text")
        ready_to_save_message = self.save_message_entry.get().strip()
        if not result_text:
            logger.warning(f"[随机抽人] 结果为空，无法保存")
            messagebox.showwarning("错误", "结果为空，无法保存")
            return
        
        SaveResult().save_result("RandomPerson", "随机抽人", result_text.split("\n"), ready_to_save_message)

class SaveResult:
    def __init__(self):
        self.config = ConfigManager()
    
    def make_html(self, class_name, result, save_message=None):
        """生成HTML结果"""
        if class_name == "RandomGroup":
            cname = "随机抽组"
        elif class_name == "RandomPerson":
            cname = "随机抽人"
        else:
            cname = "抽取结果"
        
        result_text = "<br>".join(result)
        curren_time = strftime('%Y-%m-%d %H:%M:%S')

        template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>抽取结果 - {cname}</title>
    <style>
        body {{
            font-family: "Helvetica", "Microsoft YaHei", sans-serif;
            background-color: #f5f5f5;
            margin: 40px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 15px;
        }}
        a, a:hover, a:active, a:visited {{
            color: #6495ed;
            text-decoration: none;
        }}
        .info {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .tips {{
            background-color: #e9ffe9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            text-align: center;
        }}
        .result {{
            font-size: 20px;
            padding: 20px;
            background-color: #e8f4f8;
            border-radius: 5px;
            margin: 20px 0;
            text-align: center;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #7f8c8d;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>抽取结果 - {cname}</h1>
        <div class="info">
            <p><strong>抽取时间：</strong>{curren_time}</p>
            <p><strong>抽取数量：</strong>{len(result)}</p>
        </div>
{"<!--" if not save_message else ""}
        <div class="tips">
            <p><strong>提示/说明</strong></p>
            <p style="font-size: 20px;">{save_message}</p>
        </div>
{"-->" if not save_message else ""}
        <div class="result">
            {result_text}
        </div>
        <div class="footer">
            生成于 随机抽取工具 v2.1 | <a href="{__github__}" target="_blank">GitHub</a> | <a href="{__gitee__}" target="_blank">Gitee</a> | UTC+8 {curren_time}
        </div>
    </div>
</body>
</html>"""
        return template
    
    def save_result(self, class_name, prefix, result, save_message=""):
        """保存结果"""
        if not result:
            logger.warning(f"[{prefix}] 结果为空，跳过保存")
            return None
        
        try:
            save_dir = FileManager.get_result_path()
            timestamp = strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(save_dir, f"{prefix}_{timestamp}.html")
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.make_html(class_name, result, save_message))
            
            logger.info(f"[{prefix}] 结果已保存到: {file_path}")
            messagebox.showinfo("成功", f"抽取结果已保存到:\n{file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"[{prefix}] 保存结果失败: {e}")
            messagebox.showwarning("错误", f"保存结果失败: {e}")
            return None

class ConfigWindow:
    def __init__(self, parent):
        self.parent = parent
        self.config = ConfigManager()
        
        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("350x480+50+50")  # 增加高度以适应新配置项
        self.window.resizable(False, False)
        
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建配置界面组件"""
        # 创建标题标签
        title_label = tk.Label(
            self.window, 
            text="配置设置", 
            font=("Helvetica", 16, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=15)
        
        # 配置项框架
        config_frame = tk.Frame(self.window)
        config_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # 配置项列表
        config_items = [
            ("自动保存结果：", "save_result", ["开", "关"], 
             "开" if self.config.get("save_result", True) else "关"),
            ("结果保存位置：", "result_path", ["数据目录", "桌面"],
             "桌面" if self.config.get("result_path", 0) == 1 else "数据目录"),
            ("自动加载样本：", "auto_load_sample", ["开", "关"],
             "开" if self.config.get("auto_load_sample", True) else "关"),
            ("合并重复名字：", "rcp_merge_names", ["开", "关"],
             "开" if self.config.get("rcp_merge_names", True) else "关"),
            ("抽取前打乱：", "shuffle_before_sample", ["开", "关"],
             "开" if self.config.get("shuffle_before_sample", True) else "关"),
            ("使用加权抽样：", "use_weighted_sampling", ["开", "关"],
             "开" if self.config.get("use_weighted_sampling", False) else "关")
        ]
        
        self.vars = {}
        for label_text, key, values, default_value in config_items:
            frame = tk.Frame(config_frame)
            frame.pack(fill="x", pady=5)  # 减少间距以容纳更多配置项
            tk.Label(frame, text=label_text, width=15, anchor="w").pack(side="left")
            var = tk.StringVar(value=default_value)
            self.vars[key] = var
            for value in values:
                tk.Radiobutton(frame, text=value, variable=var, value=value).pack(side="left", padx=2)
        
        # 历史记录数量
        history_frame = tk.Frame(config_frame)
        history_frame.pack(fill="x", pady=5)
        tk.Label(history_frame, text="历史记录数量：", width=15, anchor="w").pack(side="left")
        self.history_var = tk.StringVar(value=str(self.config.get("max_history_items", 10)))
        tk.Spinbox(
            history_frame,
            textvariable=self.history_var,
            from_=5,
            to=30,
            increment=5,
            state="readonly",
            width=10
        ).pack(side="left")
        
        # 默认样本位置
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
                initialdir=document_path,
                filetypes=available_files_types
            )
            if file_path:
                self.sample_var.config(state="normal")
                self.sample_var.delete(0, tk.END)
                self.sample_var.insert(0, file_path)
                self.sample_var.config(state="readonly")
        
        tk.Button(sample_frame, text="选择", command=select_file).pack(side="left", padx=5)

        # 按钮框架
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        # 保存按钮
        save_button = tk.Button(
            button_frame,
            text="保存",
            command=self.save_config,
            width=10,
            height=2
        )
        save_button.pack(side="left", padx=10)
        
        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=self.window.destroy,
            width=10,
            height=2
        )
        close_button.pack(side="left", padx=10)
    
    def save_config(self):
        """保存配置"""
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
    """应用程序通用功能类"""
    
    @staticmethod
    def show_help():
        """显示帮助"""
        help_text = """随机抽取工具 v2.1 使用说明

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
GitHub: https://github.com/ElofHew/RandomCallTool
Gitee: https://gitee.com/ElofHew/RandomCallTool"""
        
        messagebox.showinfo("使用说明", help_text)
        logger.info("显示使用说明")
    
    @staticmethod
    def create_rcp_file():
        """打开RCP生成工具"""
        rcp_tool_path = os.path.join(work_path, "encode.exe")
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
        """显示关于信息"""
        More(root).about()
    
    @staticmethod
    def clear_all_history(group_tab, person_tab):
        """清除所有历史记录"""
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
        """清除日志"""
        if messagebox.askyesno("确认", "确定要清除所有日志文件吗？"):
            try:
                for file in os.listdir(log_path):
                    if file == f"{strftime('%Y-%m-%d')}.log":
                        continue
                    if file.endswith('.log'):
                        os.remove(os.path.join(log_path, file))
                logger.info("日志文件已清除")
                messagebox.showinfo("成功", "日志文件已清除")
                return True
            except Exception as e:
                logger.error(f"清除日志失败: {e}")
                messagebox.showerror("错误", f"清除日志失败: {e}")
                return False

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.group_tab = None
        self.person_tab = None
        self.create_tabs()
        self.create_menu()
        
    def create_tabs(self):
        """创建选项卡界面"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.home_tab = HomeTab(self.notebook)
        self.group_tab = RandomGroupTab(self.notebook)
        self.person_tab = RandomPersonTab(self.notebook)
        
        self.notebook.add(self.home_tab.frame, text="主页")
        self.notebook.add(self.group_tab.frame, text="随机抽组")
        self.notebook.add(self.person_tab.frame, text="随机抽人")
    
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # 菜单项配置
        menus = {
            "文件": [
                ("打开结果目录", self.open_result_dir),
                ("-", None),
                ("退出", self.quit_app)
            ],
            "编辑": [
                ("配置", self.open_config_window),
                ("清除所有历史", lambda: ApplicationFunctions.clear_all_history(self.group_tab, self.person_tab))
            ],
            "工具": [
                ("随机抽组", lambda: self.notebook.select(self.group_tab.frame)),
                ("随机抽人", lambda: self.notebook.select(self.person_tab.frame)),
                ("-", None),
                ("生成RCP文件", ApplicationFunctions.create_rcp_file)
            ],
            "帮助": [
                ("使用说明", ApplicationFunctions.show_help),
                ("关于", lambda: ApplicationFunctions.show_about(self.root))
            ],
            "日志": [
                ("查看日志", FileManager.open_log_file),
                ("清除日志", ApplicationFunctions.clear_log)
            ]
        }
        
        for menu_name, items in menus.items():
            menu = tk.Menu(menu_bar, tearoff=0)
            menu_bar.add_cascade(label=menu_name, menu=menu)
            for item_text, command in items:
                if item_text == "-":
                    menu.add_separator()
                else:
                    menu.add_command(label=item_text, command=command)
    
    def open_config_window(self):
        """打开配置窗口"""
        logger.info("打开配置窗口")
        ConfigWindow(self.root)
    
    def open_result_dir(self):
        """打开结果目录"""
        FileManager.open_directory(FileManager.get_result_path())
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("用户确认退出程序")
            self.root.quit()

class Main:
    def __init__(self):
        self.config = ConfigManager()
        
        self.root = tk.Tk()
        self.root.title("随机抽取工具")
        self.root.geometry("400x550+50+50")  # 增加宽度以容纳重置历史按钮
        self.root.minsize(350, 500)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        
        self.app = MainApplication(self.root)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        logger.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("程序正常退出")
            self.root.destroy()

def check_os():
    """检查操作系统"""
    if os.name != 'nt':
        logger.error("不支持的操作系统：%s" % os.name)
        messagebox.showerror("错误", "本程序仅支持Windows系统")
        sys_exit(1)

def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("随机抽取工具 v2.1 启动")
        logger.info(f"工作目录: {work_path}")
        logger.info(f"数据目录: {prog_data_path}")
        logger.info(f"日志目录: {log_path}")
        logger.info(f"结果目录: {result_path}")
        logger.info("=" * 50)
        
        Main()
        
        logger.info("程序正常退出")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    check_os()
    main()