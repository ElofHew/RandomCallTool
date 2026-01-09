"""
@Name: 随机抽取工具
@Author: Dan_Evan
@Date: 2026-01-09
@Version: 2.0_beta
@Website: www.danevan.top
@Description: 随机抽取工具
"""

# 导入tkinter(GUI)库
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
# 导入基本库
import os
import json
from random import randint, sample, shuffle
from time import strftime, localtime
from sys import exit as sys_exit
from platform import system as pfs
from base64 import b64encode, b64decode
# 导入日志库
import logging
from logging.handlers import RotatingFileHandler

"""定义程序元数据"""
__version__ = "2.0_beta"
__author__ = "Dan_Evan"
__date__ = "2026-01-09"
__website__ = "www.danevan.top"
__description__ = "随机抽取工具"

"""定义全局变量"""
user_path = os.getcwd()  # 获取用户目录路径
work_path = os.path.dirname(__file__)  # 获取程序目录路径
prog_data_path = os.path.join(user_path, "data")  # 程序数据目录路径
log_path = os.path.join(prog_data_path, "log")  # 日志文件路径
result_path = os.path.join(prog_data_path, "result")  # 结果文件路径
desktop_result_path = os.path.join(os.path.expanduser("~"), "Desktop", "随机抽取结果")

config_path = os.path.join(prog_data_path, "config.json")  # 配置文件路径

# 创建程序数据目录
os.makedirs(prog_data_path, exist_ok=True)
os.makedirs(result_path, exist_ok=True)
os.makedirs(log_path, exist_ok=True)
os.makedirs(desktop_result_path, exist_ok=True)

"""初始化日志功能"""
def setup_logging():
    """设置日志记录"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 - 按日期命名
    log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=1024*1024,  # 1MB
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
            "result_path": 0,  # 0: 数据目录, 1: 桌面
            "save_result": True,  # 是否保存结果
            "auto_load_sample": True,  # 是否自动加载样本
            "max_history_items": 10,  # 历史记录最大数量
            "rcg_total_default": 9,  # 随机抽组默认总数
            "rcg_choice_default": 3,  # 随机抽组默认选择数
            "rcp_choice_default": 1  # 随机抽人默认选择数
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                    # 确保所有配置项都存在
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
            logger.info("配置已保存")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value
        self._save_config()
        logger.info(f"配置已更新: {key} = {value}")

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        logger.info("程序正常退出")
        self.root.quit()

    def about(self):
        """关于"""
        logger.info("打开关于窗口")
        messagebox.showinfo(
            "关于", 
            f"随机抽取工具\n版本：{__version__}\n作者：{__author__}\n日期：{__date__}\n网站：{__website__}"
        )

class RandomGroupTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.history = []  # 历史记录
        self.create_widgets()
        
    def create_widgets(self):
        """创建随机抽组界面组件"""
        # 创建标题标签
        title_label = tk.Label(
            self.frame, 
            text="随机抽组", 
            font=("Helvetica", 18, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)

        # 加载默认配置
        rcg_total_default = ConfigManager().get("rcg_total_default", 9)
        rcg_total_default = rcg_total_default if rcg_total_default > 0 and rcg_total_default <= 10 else 9
        rcg_choice_default = ConfigManager().get("rcg_choice_default", 3)
        rcg_choice_default = rcg_choice_default if rcg_choice_default > 0 and rcg_choice_default <= rcg_total_default else 3

        # 创建标签和选择框
        label_total = tk.Label(self.frame, text="一共有几个组（样本总数）")
        label_total.pack(pady=5)
        self.total_entry = ttk.Combobox(
            self.frame, 
            values=list(range(1, 11)),  # 可选择1-10组
            width=5,
            state="readonly"
        )
        self.total_entry.pack(pady=5)
        self.total_entry.set(str(rcg_total_default))
        self.total_entry.bind("<<ComboboxSelected>>", self._on_total_change)
        
        label_choice = tk.Label(self.frame, text="你要抽取几个组？")
        label_choice.pack(pady=5)
        self.choice_entry = ttk.Combobox(
            self.frame,
            values=list(range(1, rcg_total_default + 1)),
            width=5,
            state="readonly"
        )
        self.choice_entry.pack(pady=5)
        self.choice_entry.set(str(rcg_choice_default))
        
        # 创建按钮框架
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        button_extract = tk.Button(
            button_frame, 
            text="抽取", 
            command=self.select_groups,
            width=10
        )
        button_extract.pack(side="left", padx=5)
        
        button_clear = tk.Button(
            button_frame,
            text="清空",
            command=self.clear_result,
            width=10
        )
        button_clear.pack(side="left", padx=5)
        
        # 创建历史记录框架
        history_frame = tk.LabelFrame(self.frame, text="历史记录")
        history_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 历史记录列表框
        self.history_listbox = tk.Listbox(
            history_frame,
            height=5,
            selectmode=tk.SINGLE
        )
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        
        # 创建结果标签
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(
            self.frame, 
            font=bold_font, 
            text="",
            wraplength=350, 
            justify="center"
        )
        self.result_label.pack(pady=10, padx=10, fill="both", expand=True)
    
    def _on_total_change(self, event):
        """当总数变化时更新可选的抽取数量"""
        try:
            total = int(self.total_entry.get())
            if total > 0:
                self.choice_entry['values'] = list(range(1, min(total + 1, 11)))
                self.choice_entry.set(str(min(3, total)))
        except ValueError:
            pass
    
    def clear_result(self):
        """清空结果"""
        self.result_label.config(text="")
        logger.info("[随机抽组] 清空结果")
    
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
            # 生成所有组号并随机选择
            all_groups = list(range(1, total_num + 1))
            selected_groups = sample(all_groups, choice_num)
            selected_groups.sort()
            
            # 显示结果
            result_text = "\n".join([f"第{group}组" for group in selected_groups])
            self.result_label.config(text=result_text)
            
            # 添加到历史记录
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}组: {', '.join(map(str, selected_groups))}"
            self.history.insert(0, history_item)
            self.history_listbox.insert(0, history_item)
            
            # 限制历史记录数量
            max_history = ConfigManager().get("max_history_items", 10)
            if len(self.history) > max_history:
                self.history = self.history[:max_history]
                self.history_listbox.delete(max_history, tk.END)
            
            logger.info(f"[随机抽组] 抽取成功: {selected_groups}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n{result_text}")
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                result_list = [f"第{group}组" for group in selected_groups]
                file_path = SaveResult().rg_save_result(result_list)
                if file_path:
                    logger.info(f"[随机抽组] 结果已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"[随机抽组] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")

class RandomPersonTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.names = []
        self.history = []  # 历史记录
        self.create_widgets()
        self._auto_load_sample()
        
    def _auto_load_sample(self):
        """自动加载样本文件"""
        config = ConfigManager()
        auto_file = "sample.rcp"
        if config.get("auto_load_sample", True) and os.path.exists(auto_file):
            self.names = self.load_names_from_file(auto_file)
            if self.names:
                logger.info(f"[随机抽人] 自动加载 {auto_file}, 共 {len(self.names)} 个名字")
        
    def create_widgets(self):
        """创建随机抽人界面组件"""
        # 创建标题标签
        title_label = tk.Label(
            self.frame, 
            text="随机抽人", 
            font=("Helvetica", 18, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)
        
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
        
        button_load = tk.Button(
            button_frame, 
            text="选择文件", 
            command=self.load_names,
            width=12
        )
        button_load.pack(side="left", padx=2)
        
        button_reload = tk.Button(
            button_frame,
            text="重新加载",
            command=self.reload_current_file,
            width=12
        )
        button_reload.pack(side="left", padx=2)
        
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
        rcp_choice_default = rcp_choice_default if rcp_choice_default > 0 and rcp_choice_default <= 10 else 1

        # 抽取数量选择
        choice_frame = tk.Frame(self.frame)
        choice_frame.pack(pady=10)
        
        label_choice = tk.Label(choice_frame, text="你要抽取几个人？")
        label_choice.pack(pady=5)
        
        self.choice_entry = ttk.Combobox(
            choice_frame,
            values=list(range(1, 11)),
            width=5,
            state="readonly"
        )
        self.choice_entry.pack(pady=5)
        self.choice_entry.set(str(rcp_choice_default))
        
        # 抽取按钮框架
        action_frame = tk.Frame(self.frame)
        action_frame.pack(pady=10)
        
        button_extract = tk.Button(
            action_frame,
            text="抽取",
            command=self.select_persons,
            width=10
        )
        button_extract.pack(side="left", padx=5)
        
        button_clear = tk.Button(
            action_frame,
            text="清空",
            command=self.clear_result,
            width=10
        )
        button_clear.pack(side="left", padx=5)
        
        # 历史记录框架
        history_frame = tk.LabelFrame(self.frame, text="历史记录")
        history_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 历史记录列表框
        self.history_listbox = tk.Listbox(
            history_frame,
            height=5,
            selectmode=tk.SINGLE
        )
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")
        self.history_listbox.pack(side="left", fill="both", expand=True)
        self.history_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.history_listbox.yview)
        
        # 创建结果标签
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(
            self.frame, 
            font=bold_font, 
            text="",
            wraplength=350, 
            justify="center"
        )
        self.result_label.pack(pady=10, padx=10, fill="both", expand=True)
    
    def load_names_from_file(self, file_path=None):
        """从文件加载名字"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("名单文件", "*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*")
                ],
                title="选择样本文件"
            )
            logger.info(f"[随机抽人] 选择文件: {file_path if file_path else '(取消选择)'}")
        
        if not file_path:
            logger.warning("[随机抽人] 未选择文件")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Base64解码
            content = self.decode_list(content)
            
            # 支持多种分隔符
            names = []
            for line in content.splitlines():
                line = line.strip()
                if line:
                    # 尝试按逗号、分号、制表符、空格分割
                    if ',' in line:
                        names.extend([name.strip() for name in line.split(',') if name.strip()])
                    elif ';' in line:
                        names.extend([name.strip() for name in line.split(';') if name.strip()])
                    elif '\t' in line:
                        names.extend([name.strip() for name in line.split('\t') if name.strip()])
                    else:
                        names.append(line)
            
            # 判断并去除重复的名字
            if len(names) != len(set(names)):
                logger.warning(f"[随机抽人] 文件 {file_path} 中存在重复的名字")
                messagebox.showwarning("警告", "文件中存在重复的名字，已自动去除")
                # 去除重复的名字
                names = list(set(names))
            
            # 去除空白行
            if '' in names:
                logger.warning(f"[随机抽人] 文件 {file_path} 中存在空白行")
                messagebox.showwarning("警告", "文件中存在空白行，已自动去除")
                names.remove('')

            # 无效数据过滤
            if not names:
                logger.warning(f"[随机抽人] 文件 {file_path} 中没有有效数据")
                messagebox.showwarning("警告", "文件中没有有效的数据")
                return []
            
            # 更新显示
            self.file_path_label.config(
                text=os.path.basename(file_path),
                fg="black"
            )
            self.sample_count_label.config(
                text=f"样本数量: {len(names)}",
                fg="green"
            )
            
            # 更新可选的抽取数量
            max_choice = len(names)
            self.choice_entry['values'] = list(range(1, max_choice + 1))
            
            logger.info(f"[随机抽人] 成功加载 {len(names)} 个名字")
            return names
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    names = [line.strip() for line in file if line.strip()]
                if names:
                    self.file_path_label.config(text=os.path.basename(file_path))
                    self.sample_count_label.config(text=f"样本数量: {len(names)}")
                    return names
            except Exception as e:
                logger.error(f"[随机抽人] 读取文件失败: {e}")
                messagebox.showerror("错误", f"读取文件失败: {e}")
                return []
        except Exception as e:
            logger.error(f"[随机抽人] 读取文件失败: {e}")
            messagebox.showerror("错误", f"读取文件失败: {e}")
            return []
    
    def reload_current_file(self):
        """重新加载当前文件"""
        current_file = self.file_path_label.cget("text")
        if current_file != "未选择文件":
            file_path = filedialog.askopenfilename(
                initialfile=current_file,
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if file_path:
                self.names = self.load_names_from_file(file_path)
                if self.names:
                    messagebox.showinfo("成功", f"重新加载成功\n共加载 {len(self.names)} 个名字")
    
    def decode_list(self, data=None):
        """解码列表"""
        if not data:
            return ""
        
        try:
            # 加一个换行符，防止解码失败
            data = data.strip() + "\n"
            # Base64解码
            data = b64decode(data).decode('utf-8')
            logger.info(f"[随机抽人] 成功解码列表数据")
            return data
        except Exception as e:
            logger.error(f"[随机抽人] 解码失败: {e}")
            return ""

    def load_names(self):
        """加载名字并更新显示"""
        self.names = self.load_names_from_file()
        if self.names:
            messagebox.showinfo("成功", f"样本列表已加载\n共加载 {len(self.names)} 个名字")
            logger.info(f"[随机抽人] 手动加载样本列表，共 {len(self.names)} 个名字")
    
    def clear_result(self):
        """清空结果"""
        self.result_label.config(text="")
        logger.info("[随机抽人] 清空结果")
    
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
            
            # 随机抽取
            selected_persons = sample(self.names, choice_num)
            
            # 显示结果
            self.result_label.config(text="\n".join(selected_persons))
            
            # 添加到历史记录
            history_item = f"{strftime('%H:%M:%S')} - 抽取{choice_num}人: {', '.join(selected_persons[:10])}{'...' if len(selected_persons) > 10 else ''}"
            self.history.insert(0, history_item)
            self.history_listbox.insert(0, history_item)
            
            # 限制历史记录数量
            max_history = ConfigManager().get("max_history_items", 10)
            if len(self.history) > max_history:
                self.history = self.history[:max_history]
                self.history_listbox.delete(max_history, tk.END)
            
            logger.info(f"[随机抽人] 成功抽取 {choice_num} 人: {selected_persons}")
            
            # 显示结果对话框
            messagebox.showinfo("抽取结果", f"抽取结果：\n" + "\n".join(selected_persons))
            
            # 保存结果
            if ConfigManager().get("save_result", True):
                file_path = SaveResult().rp_save_result(selected_persons)
                if file_path:
                    logger.info(f"[随机抽人] 结果已保存到: {file_path}")
                    
        except ValueError:
            logger.error("[随机抽人] 输入值不是有效数字")
            messagebox.showerror("错误", "请输入有效的数字")
        except Exception as e:
            logger.error(f"[随机抽人] 抽取过程中发生错误: {e}")
            messagebox.showerror("错误", f"抽取过程中发生错误: {e}")

class SaveResult:
    def __init__(self):
        self.config = ConfigManager()
    
    def get_save_path(self, result_type):
        """获取保存路径"""
        save_dir = result_path
        
        # 如果配置为保存到桌面
        if self.config.get("result_path", 0) == 1:
            desktop_save_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            save_dir = os.path.join(desktop_save_dir, "随机抽取结果")
            os.makedirs(save_dir, exist_ok=True)
        
        return save_dir
    
    def make_html(self, class_name, result):
        """生成HTML结果"""
        if class_name == "RandomGroup":
            cname = "随机抽组"
            result_text = "<br>".join(result)
        elif class_name == "RandomPerson":
            cname = "随机抽人"
            result_text = "<br>".join(result)
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
        <div class="result">
            {result_text}
        </div>
        <div class="footer">
            生成于 随机抽取工具 v2.0 | <a href="https://home.danevan.top" target="_blank">home.danevan.top</a> | UTC+8 {curren_time}
        </div>
    </div>
</body>
</html>"""
        return template
    
    def rg_save_result(self, result):
        """保存随机抽组结果"""
        if not result:
            logger.warning("[随机抽组] 结果为空，跳过保存")
            return None
        
        try:
            save_dir = self.get_save_path("group")
            timestamp = strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(save_dir, f"随机抽组_{timestamp}.html")
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.make_html("RandomGroup", result))
            
            logger.info(f"[随机抽组] 结果已保存到: {file_path}")
            messagebox.showinfo("成功", f"抽取结果已保存到:\n{file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"[随机抽组] 保存结果失败: {e}")
            messagebox.showwarning("错误", f"保存结果失败: {e}")
            return None
    
    def rp_save_result(self, result):
        """保存随机抽人结果"""
        if not result:
            logger.warning("[随机抽人] 结果为空，跳过保存")
            return None
        
        try:
            save_dir = self.get_save_path("person")
            timestamp = strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(save_dir, f"随机抽人_{timestamp}.html")
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.make_html("RandomPerson", result))
            
            logger.info(f"[随机抽人] 结果已保存到: {file_path}")
            messagebox.showinfo("成功", f"抽取结果已保存到:\n{file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"[随机抽人] 保存结果失败: {e}")
            messagebox.showwarning("错误", f"保存结果失败: {e}")
            return None

class ConfigWindow:
    def __init__(self, parent):
        self.parent = parent
        self.config = ConfigManager()
        
        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("350x350+50+50")
        self.window.resizable(False, False)
        
        # 设置窗口图标和模态
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
        
        # 1. 是否保存结果
        save_frame = tk.Frame(config_frame)
        save_frame.pack(fill="x", pady=8)
        tk.Label(save_frame, text="是否保存结果：", width=15, anchor="w").pack(side="left")
        self.save_var = tk.StringVar(value="开" if self.config.get("save_result", True) else "关")
        tk.Radiobutton(save_frame, text="开", variable=self.save_var, value="开").pack(side="left")
        tk.Radiobutton(save_frame, text="关", variable=self.save_var, value="关").pack(side="left")

        # 2. 结果保存路径
        path_frame = tk.Frame(config_frame)
        path_frame.pack(fill="x", pady=8)
        tk.Label(path_frame, text="结果保存位置：", width=15, anchor="w").pack(side="left")
        self.path_var = tk.StringVar(value="桌面" if self.config.get("result_path", 0) == 1 else "数据目录")
        tk.Radiobutton(path_frame, text="数据目录", variable=self.path_var, value="数据目录").pack(side="left")
        tk.Radiobutton(path_frame, text="桌面", variable=self.path_var, value="桌面").pack(side="left")

        # 3. 自动加载样本
        auto_frame = tk.Frame(config_frame)
        auto_frame.pack(fill="x", pady=8)
        tk.Label(auto_frame, text="自动加载样本：", width=15, anchor="w").pack(side="left")
        self.auto_var = tk.StringVar(value="开" if self.config.get("auto_load_sample", True) else "关")
        tk.Radiobutton(auto_frame, text="开", variable=self.auto_var, value="开").pack(side="left")
        tk.Radiobutton(auto_frame, text="关", variable=self.auto_var, value="关").pack(side="left")

        # 4. 历史记录数量
        history_frame = tk.Frame(config_frame)
        history_frame.pack(fill="x", pady=8)
        tk.Label(history_frame, text="历史记录数量：", width=15, anchor="w").pack(side="left")
        self.history_var = tk.StringVar(value=str(self.config.get("max_history_items", 10)))
        history_spinbox = tk.Spinbox(
            history_frame,
            textvariable=self.history_var,
            from_=5,
            to=30,
            increment=5,
            state="readonly",
            width=10
        )
        history_spinbox.pack(side="left")
        
        # 按钮框架
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        # 保存按钮
        save_button = tk.Button(
            button_frame,
            text="保存",
            command=self.save_config,
            width=15,
            height=2
        )
        save_button.pack(side="left", padx=10)
        
        # 关闭按钮
        close_button = tk.Button(
            button_frame,
            text="关闭",
            command=self.window.destroy,
            width=15,
            height=2
        )
        close_button.pack(side="left", padx=10)
    
    def save_config(self):
        """保存"""
        try:
            self.config.set("save_result", self.save_var.get() == "开")
            self.config.set("result_path", 1 if self.path_var.get() == "桌面" else 0)
            self.config.set("auto_load_sample", self.auto_var.get() == "开")
            self.config.set("max_history_items", int(self.history_var.get()))
            
            logger.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.create_menu()
        self.create_tabs()
        
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开结果目录", command=self.open_result_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        
        # 编辑菜单
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="配置", command=self.open_config_window)
        edit_menu.add_command(label="清除所有历史", command=self.clear_all_history)
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        
        # 日志菜单
        log_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="日志", menu=log_menu)
        log_menu.add_command(label="查看日志", command=self.view_log)
        log_menu.add_command(label="清除日志", command=self.clear_log)
    
    def create_tabs(self):
        """创建选项卡界面"""
        # 创建Notebook（选项卡控件）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建选项卡
        self.group_tab = RandomGroupTab(self.notebook)
        self.person_tab = RandomPersonTab(self.notebook)
        
        # 添加选项卡到Notebook
        self.notebook.add(self.group_tab.frame, text="随机抽组")
        self.notebook.add(self.person_tab.frame, text="随机抽人")
    
    def open_config_window(self):
        """打开配置窗口"""
        logger.info("打开配置窗口")
        ConfigWindow(self.root)
    
    def open_result_dir(self):
        """打开结果目录"""
        try:
            open_dir = result_path
            if not os.path.exists(open_dir):
                messagebox.showwarning("提示", "结果目录不存在")
                return
            os.startfile(open_dir)
            logger.info("打开结果目录")
        except Exception as e:
            logger.error(f"打开结果目录失败: {e}")
            messagebox.showerror("错误", f"无法打开结果目录: {e}")
    
    def view_log(self):
        """查看日志"""
        try:
            latest_log = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
            if os.path.exists(latest_log):
                os.startfile(latest_log)
            else:
                messagebox.showinfo("提示", "今天的日志文件不存在")
        except Exception as e:
            logger.error(f"查看日志失败: {e}")
            messagebox.showerror("错误", f"无法查看日志: {e}")
    
    def clear_log(self):
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
            except Exception as e:
                logger.error(f"清除日志失败: {e}")
                messagebox.showerror("错误", f"清除日志失败: {e}")
    
    def clear_all_history(self):
        """清除所有历史记录"""
        if messagebox.askyesno("确认", "确定要清除所有历史记录吗？"):
            if hasattr(self.group_tab, 'history'):
                self.group_tab.history.clear()
                self.group_tab.history_listbox.delete(0, tk.END)
            if hasattr(self.person_tab, 'history'):
                self.person_tab.history.clear()
                self.person_tab.history_listbox.delete(0, tk.END)
            logger.info("所有历史记录已清除")
            messagebox.showinfo("成功", "历史记录已清除")
    
    def show_help(self):
        """显示帮助"""
        help_text = """使用说明：

随机抽组：
1. 输入总组数
2. 输入要抽取的组数
3. 点击"抽取"按钮

随机抽人：
1. 点击"选择文件"加载样本列表（txt文件）
2. 输入要抽取的人数
3. 点击"抽取"按钮

功能：
- 自动保存抽取结果
- 记录抽取历史
- 可配置保存路径
- 查看日志记录

支持的文件格式：
- 纯文本文件 (.txt)
- 每行一个名字
- 支持中文编码"""
        
        messagebox.showinfo("使用说明", help_text)
        logger.info("显示使用说明")
    
    def show_about(self):
        """显示关于信息"""
        More(self.root).about()
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("用户确认退出程序")
            self.root.quit()

class Main:
    def __init__(self):
        # 初始化配置管理器
        self.config = ConfigManager()
        
        self.root = tk.Tk()
        self.root.title("随机抽取工具 v2.0")
        self.root.geometry("350x550+50+50")
        self.root.minsize(300, 500)
        self.root.maxsize(1280, 1280)
        self.root.resizable(True, True)
        
        # 设置应用程序图标
        self.set_app_icon()
        
        # 创建主应用程序
        self.app = MainApplication(self.root)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动主循环
        self.root.mainloop()
    
    def set_app_icon(self):
        """设置应用程序图标"""
        icon_path = os.path.join(work_path, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(default=icon_path)
            except:
                pass
    
    def on_closing(self):
        """窗口关闭事件处理"""
        logger.info("用户关闭窗口，准备退出程序")
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("程序正常退出")
            self.root.destroy()

def check_os():
    """检查操作系统"""
    if pfs() != 'Windows':
        logger.error("不支持的操作系统：%s" % pfs())
        messagebox.showerror("错误", "本程序仅支持Windows系统")
        sys_exit(1)

def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("随机抽取工具 v2.0 启动")
        logger.info(f"工作目录: {user_path}")
        logger.info(f"数据目录: {prog_data_path}")
        logger.info(f"日志目录: {log_path}")
        logger.info(f"结果目录: {result_path}")
        logger.info("=" * 50)
        
        # 启动主程序
        Main()
        
        logger.info("程序正常退出")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    # 检查操作系统
    check_os()
    
    # 启动程序
    main()