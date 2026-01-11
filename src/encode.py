"""
@Name: 随机抽人名单编码工具
@Author: Dan_Evan
@Date: 2026-01-10
@Version: 1.0
@Website: www.danevan.top
@Description: 将明文名单转换为编码后的rcp文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkinter.font as tkFont
import os
import json
import base64
from time import strftime
import logging
from logging.handlers import RotatingFileHandler

# 定义程序元数据
__version__ = "1.0"
__author__ = "Dan_Evan"
__date__ = "2026-01-10"
__website__ = "www.danevan.top"
__description__ = "随机抽人名单编码工具"

# 定义全局变量
user_path = os.getcwd()  # 获取用户目录路径
work_path = os.path.dirname(__file__)  # 获取程序目录路径
prog_data_path = os.path.join(user_path, "data", "EncodeTool")  # 程序数据目录路径
log_path = os.path.join(prog_data_path, "log")  # 日志文件路径
output_path = os.path.join(prog_data_path, "encoded_files")  # 编码文件输出路径
desktop_output_path = os.path.join(os.path.expanduser("~"), "Desktop", "编码名单")  # 桌面输出路径

config_path = os.path.join(prog_data_path, "config_encode.json")  # 配置文件路径

# 创建程序数据目录
os.makedirs(prog_data_path, exist_ok=True)
os.makedirs(output_path, exist_ok=True)
os.makedirs(log_path, exist_ok=True)
os.makedirs(desktop_output_path, exist_ok=True)

# 初始化日志功能
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
    log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}_encode.log")
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
            "output_path": 0,  # 0: 数据目录, 1: 桌面
            "auto_clear_input": False,  # 编码后自动清空输入
            "default_filename": "sample_list",  # 默认文件名
            "auto_open_folder": True,  # 编码后自动打开文件夹
            "remove_duplicates": True,  # 自动去除重复项
            "trim_spaces": True  # 自动去除首尾空格
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

class ListEncoder:
    """名单编码器"""
    
    @staticmethod
    def encode_list(text):
        """将文本编码为Base64格式"""
        try:
            # 如果文本为空，返回空字符串
            if not text or not text.strip():
                return ""
            
            # 标准化换行符并添加结尾换行符
            text = text.replace('\r\n', '\n').replace('\r', '\n').strip() + "\n"
            
            # Base64编码
            encoded_bytes = base64.b64encode(text.encode('utf-8'))
            encoded_text = encoded_bytes.decode('utf-8')
            
            logger.info(f"成功编码名单，原始长度: {len(text)}，编码后长度: {len(encoded_text)}")
            return encoded_text
            
        except Exception as e:
            logger.error(f"编码失败: {e}")
            raise
    
    @staticmethod
    def decode_list(encoded_text):
        """将Base64格式解码为文本"""
        try:
            if not encoded_text or not encoded_text.strip():
                return ""
            
            # Base64解码
            decoded_bytes = base64.b64decode(encoded_text)
            decoded_text = decoded_bytes.decode('utf-8')
            
            return decoded_text.strip()
            
        except Exception as e:
            logger.error(f"解码失败: {e}")
            raise
    
    @staticmethod
    def process_text(text, remove_duplicates=True, trim_spaces=True):
        """处理文本：去除重复项和空格"""
        if not text:
            return ""
        
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            if trim_spaces:
                line = line.strip()
            
            if line:  # 跳过空行
                processed_lines.append(line)
        
        # 去除重复项
        if remove_duplicates:
            processed_lines = list(dict.fromkeys(processed_lines))  # 保持顺序
        
        return '\n'.join(processed_lines)

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.config = ConfigManager()
        self.create_menu()
        self.create_widgets()
        
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        
        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开输入文件", command=self.open_input_file)
        file_menu.add_command(label="保存为明文", command=self.save_as_plaintext)
        file_menu.add_separator()
        file_menu.add_command(label="打开输出目录", command=self.open_output_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit_app)
        
        # 编辑菜单
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="清空输入", command=self.clear_input)
        edit_menu.add_command(label="清空输出", command=self.clear_output)
        edit_menu.add_command(label="处理文本", command=self.process_text)
        edit_menu.add_separator()
        edit_menu.add_command(label="配置", command=self.open_config_window)
        
        # 工具菜单
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="测试编码/解码", command=self.test_encode_decode)
        tools_menu.add_command(label="统计信息", command=self.show_statistics)
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建标题标签
        title_label = tk.Label(
            self.root, 
            text="随机抽人名单编码工具", 
            font=("Helvetica", 18, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=10, ipady=15)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 输入区域
        input_frame = tk.LabelFrame(main_frame, text="输入明文名单")
        input_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 输入文本框
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=8,
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        self.input_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 输入按钮框架
        input_button_frame = tk.Frame(input_frame)
        input_button_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            input_button_frame,
            text="从文件加载",
            command=self.open_input_file
        ).pack(side="left", padx=2)
        
        ttk.Button(
            input_button_frame,
            text="清空输入",
            command=self.clear_input
        ).pack(side="left", padx=2)
        
        ttk.Button(
            input_button_frame,
            text="处理文本",
            command=self.process_text
        ).pack(side="left", padx=2)
        
        # 输出区域
        output_frame = tk.LabelFrame(main_frame, text="编码结果")
        output_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # 输出文本框
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#f0f0f0"
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 输出按钮框架
        output_button_frame = tk.Frame(output_frame)
        output_button_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            output_button_frame,
            text="复制到剪贴板",
            command=self.copy_to_clipboard
        ).pack(side="left", padx=2)
        
        ttk.Button(
            output_button_frame,
            text="清空输出",
            command=self.clear_output
        ).pack(side="left", padx=2)
        
        ttk.Button(
            output_button_frame,
            text="解码测试",
            command=self.test_decode
        ).pack(side="left", padx=2)
        
        # 文件名输入区域
        filename_frame = tk.Frame(main_frame)
        filename_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            filename_frame,
            text="输出文件名:"
        ).pack(side="left", padx=(0, 5))
        
        self.filename_var = tk.StringVar(value=self.config.get("default_filename", "sample_list"))
        self.filename_entry = ttk.Entry(
            filename_frame,
            textvariable=self.filename_var,
            width=30
        )
        self.filename_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        tk.Label(
            filename_frame,
            text=".rcp"
        ).pack(side="left")
        
        # 操作按钮框架
        action_frame = tk.Frame(main_frame)
        action_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(
            action_frame,
            text="编码并保存",
            command=self.encode_and_save,
            width=20
        ).pack(side="left", padx=2)
        
        ttk.Button(
            action_frame,
            text="快速编码",
            command=self.quick_encode,
            width=20
        ).pack(side="left", padx=2)
        
        # 状态栏
        self.status_bar = tk.Label(
            self.root,
            text="就绪",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_input_file(self):
        """打开输入文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            title="选择要编码的名单文件"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.input_text.delete(1.0, tk.END)
                self.input_text.insert(1.0, content)
                
                # 更新状态
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
        """处理输入文本"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            self.set_status("输入为空，无需处理")
            return
        
        remove_duplicates = self.config.get("remove_duplicates", True)
        trim_spaces = self.config.get("trim_spaces", True)
        
        processed_text = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
        
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(1.0, processed_text)
        
        # 统计信息
        original_lines = len([line for line in text.split('\n') if line.strip()])
        processed_lines = len([line for line in processed_text.split('\n') if line.strip()])
        
        if remove_duplicates and original_lines != processed_lines:
            self.set_status(f"文本已处理: 去除了 {original_lines - processed_lines} 个重复项")
            logger.info(f"文本处理完成: 原始行数 {original_lines}, 处理后行数 {processed_lines}")
        else:
            self.set_status("文本已处理")
            logger.info("文本处理完成")
    
    def encode_and_save(self):
        """编码并保存为rcp文件"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return
        
        try:
            # 处理文本
            remove_duplicates = self.config.get("remove_duplicates", True)
            trim_spaces = self.config.get("trim_spaces", True)
            processed_text = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
            
            # 编码
            encoded_text = ListEncoder.encode_list(processed_text)
            
            # 获取输出路径
            if self.config.get("output_path", 0) == 1:
                save_dir = desktop_output_path
            else:
                save_dir = output_path
            
            os.makedirs(save_dir, exist_ok=True)
            
            # 获取文件名
            filename = self.filename_var.get().strip()
            if not filename:
                filename = self.config.get("default_filename", "sample_list")
            
            # 确保文件名以.rcp结尾
            if not filename.endswith('.rcp'):
                filename += '.rcp'
            
            file_path = os.path.join(save_dir, filename)
            
            # 如果文件已存在，询问是否覆盖
            if os.path.exists(file_path):
                if not messagebox.askyesno("确认", f"文件 {filename} 已存在，是否覆盖？"):
                    return
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(encoded_text)
            
            # 更新输出文本框
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded_text)
            
            # 设置状态
            self.set_status(f"文件已保存: {file_path}")
            logger.info(f"编码文件已保存: {file_path}")
            
            # 显示成功消息
            lines_count = len([line for line in processed_text.split('\n') if line.strip()])
            messagebox.showinfo(
                "成功", 
                f"名单编码完成！\n\n"
                f"保存位置: {file_path}\n"
                f"包含 {lines_count} 个名字\n"
                f"文件大小: {len(encoded_text)} 字节"
            )
            
            # 自动清空输入
            if self.config.get("auto_clear_input", False):
                self.clear_input()
            
            # 自动打开文件夹
            if self.config.get("auto_open_folder", True):
                try:
                    os.startfile(save_dir)
                except:
                    pass
                
        except Exception as e:
            messagebox.showerror("错误", f"编码保存失败: {e}")
            logger.error(f"编码保存失败: {e}")
    
    def quick_encode(self):
        """快速编码（不保存文件）"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "请输入要编码的文本")
            return
        
        try:
            # 处理文本
            remove_duplicates = self.config.get("remove_duplicates", True)
            trim_spaces = self.config.get("trim_spaces", True)
            processed_text = ListEncoder.process_text(text, remove_duplicates, trim_spaces)
            
            # 编码
            encoded_text = ListEncoder.encode_list(processed_text)
            
            # 更新输出文本框
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, encoded_text)
            
            # 统计信息
            lines_count = len([line for line in processed_text.split('\n') if line.strip()])
            self.set_status(f"快速编码完成: {lines_count} 个名字，{len(encoded_text)} 字节")
            logger.info(f"快速编码完成: {lines_count} 个名字")
            
        except Exception as e:
            messagebox.showerror("错误", f"编码失败: {e}")
            logger.error(f"快速编码失败: {e}")
    
    def copy_to_clipboard(self):
        """复制输出到剪贴板"""
        output_content = self.output_text.get(1.0, tk.END).strip()
        if not output_content:
            messagebox.showwarning("警告", "输出为空，无需复制")
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(output_content)
        
        self.set_status("已复制到剪贴板")
        logger.info("输出内容已复制到剪贴板")
    
    def test_decode(self):
        """测试解码功能"""
        encoded_text = self.output_text.get(1.0, tk.END).strip()
        if not encoded_text:
            messagebox.showwarning("警告", "输出为空，无法解码")
            return
        
        try:
            decoded_text = ListEncoder.decode_list(encoded_text)
            
            # 在新窗口中显示解码结果
            decode_window = tk.Toplevel(self.root)
            decode_window.title("解码测试")
            decode_window.geometry("500x400")
            decode_window.transient(self.root)
            decode_window.grab_set()
            
            tk.Label(
                decode_window,
                text="解码结果",
                font=("Helvetica", 14, "bold"),
                fg="green"
            ).pack(pady=10)
            
            text_widget = scrolledtext.ScrolledText(
                decode_window,
                wrap=tk.WORD,
                font=("Courier", 10)
            )
            text_widget.pack(fill="both", expand=True, padx=10, pady=10)
            text_widget.insert(1.0, decoded_text)
            text_widget.config(state="disabled")
            
            tk.Button(
                decode_window,
                text="关闭",
                command=decode_window.destroy,
                width=15
            ).pack(pady=10)
            
            self.set_status("解码测试完成")
            logger.info("解码测试完成")
            
        except Exception as e:
            messagebox.showerror("错误", f"解码失败: {e}")
            logger.error(f"解码测试失败: {e}")
    
    def save_as_plaintext(self):
        """保存为明文文件"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("警告", "输入为空，无需保存")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            title="保存为明文文件"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                self.set_status(f"明文文件已保存: {file_path}")
                logger.info(f"明文文件已保存: {file_path}")
                messagebox.showinfo("成功", f"文件已保存:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
                logger.error(f"保存明文文件失败: {e}")
    
    def clear_input(self):
        """清空输入"""
        self.input_text.delete(1.0, tk.END)
        self.set_status("输入已清空")
        logger.info("输入已清空")
    
    def clear_output(self):
        """清空输出"""
        self.output_text.delete(1.0, tk.END)
        self.set_status("输出已清空")
        logger.info("输出已清空")
    
    def open_output_dir(self):
        """打开输出目录"""
        try:
            if self.config.get("output_path", 0) == 1:
                open_dir = desktop_output_path
            else:
                open_dir = output_path
            
            if not os.path.exists(open_dir):
                os.makedirs(open_dir, exist_ok=True)
            
            os.startfile(open_dir)
            self.set_status("已打开输出目录")
            logger.info("已打开输出目录")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {e}")
            logger.error(f"打开输出目录失败: {e}")
    
    def test_encode_decode(self):
        """测试编码/解码循环"""
        test_text = "测试名字1\n测试名字2\n测试名字3\n测试名字4"
        
        try:
            # 编码
            encoded = ListEncoder.encode_list(test_text)
            # 解码
            decoded = ListEncoder.decode_list(encoded)
            
            # 验证
            if test_text + "\n" == decoded + "\n":
                messagebox.showinfo("测试结果", "编码/解码测试成功！\n\n功能正常。")
                logger.info("编码/解码测试成功")
            else:
                messagebox.showwarning("测试结果", "编码/解码测试失败！")
                logger.warning("编码/解码测试失败")
                
        except Exception as e:
            messagebox.showerror("测试错误", f"测试失败: {e}")
            logger.error(f"编码/解码测试失败: {e}")
    
    def show_statistics(self):
        """显示统计信息"""
        input_text = self.input_text.get(1.0, tk.END).strip()
        output_text = self.output_text.get(1.0, tk.END).strip()
        
        input_lines = len([line for line in input_text.split('\n') if line.strip()])
        input_chars = len(input_text)
        
        output_lines = len([line for line in output_text.split('\n') if line.strip()])
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
        logger.info(f"显示统计信息: 输入{input_lines}行，输出{output_lines}行")
    
    def open_config_window(self):
        """打开配置窗口"""
        logger.info("打开配置窗口")
        ConfigWindow(self.root, self.config, self)
    
    def show_help(self):
        """显示帮助"""
        help_text = """使用说明：

1. 输入明文名单
   - 在左侧文本框输入名单（每行一个名字）
   - 或点击"从文件加载"导入文本文件

2. 处理文本（可选）
   - 点击"处理文本"自动去除重复项和空格

3. 编码名单
   - 点击"快速编码"仅生成Base64编码
   - 点击"编码并保存"生成并保存.rcp文件

4. 输出文件
   - 编码结果会显示在下方文本框
   - 可以复制到剪贴板或直接保存

5. 文件格式
   - 输入: 普通文本文件 (.txt)
   - 输出: 编码后的.rcp文件
   - 每行一个名字，支持中文

6. 配置选项
   - 可以设置输出位置、文件名等
   - 配置会自动保存"""
        
        messagebox.showinfo("使用说明", help_text)
        logger.info("显示使用说明")
    
    def show_about(self):
        """显示关于信息"""
        about_text = f"""随机抽人名单编码工具
版本：{__version__}
作者：{__author__}
日期：{__date__}
网站：{__website__}

功能：将明文名单转换为编码后的rcp文件
用于随机抽取工具的样本列表"""
        
        messagebox.showinfo("关于", about_text)
        logger.info("显示关于信息")
    
    def set_status(self, message):
        """设置状态栏消息"""
        self.status_bar.config(text=message)
    
    def quit_app(self):
        """退出应用程序"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            logger.info("用户确认退出程序")
            self.root.quit()

class ConfigWindow:
    def __init__(self, parent, config, app):
        self.parent = parent
        self.config = config
        self.app = app
        
        self.window = tk.Toplevel(parent)
        self.window.title("配置")
        self.window.geometry("400x400+50+50")
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
            text="编码工具配置", 
            font=("Helvetica", 16, "bold"), 
            fg="blue"
        )
        title_label.pack(pady=15)
        
        # 配置项框架
        config_frame = tk.Frame(self.window)
        config_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # 1. 输出路径
        path_frame = tk.Frame(config_frame)
        path_frame.pack(fill="x", pady=8)
        tk.Label(path_frame, text="输出路径：", width=15, anchor="w").pack(side="left")
        self.path_var = tk.StringVar(value="桌面" if self.config.get("output_path", 0) == 1 else "数据目录")
        tk.Radiobutton(path_frame, text="数据目录", variable=self.path_var, value="数据目录").pack(side="left")
        tk.Radiobutton(path_frame, text="桌面", variable=self.path_var, value="桌面").pack(side="left", padx=(20, 0))
        
        # 2. 默认文件名
        name_frame = tk.Frame(config_frame)
        name_frame.pack(fill="x", pady=8)
        tk.Label(name_frame, text="默认文件名：", width=15, anchor="w").pack(side="left")
        self.name_var = tk.StringVar(value=self.config.get("default_filename", "sample_list"))
        tk.Entry(name_frame, textvariable=self.name_var, width=20).pack(side="left")
        
        # 3. 自动处理选项
        auto_frame = tk.Frame(config_frame)
        auto_frame.pack(fill="x", pady=8)
        
        self.auto_clear_var = tk.BooleanVar(value=self.config.get("auto_clear_input", False))
        self.auto_open_var = tk.BooleanVar(value=self.config.get("auto_open_folder", True))
        self.remove_dup_var = tk.BooleanVar(value=self.config.get("remove_duplicates", True))
        self.trim_space_var = tk.BooleanVar(value=self.config.get("trim_spaces", True))
        
        tk.Checkbutton(
            auto_frame, 
            text="编码后自动清空输入", 
            variable=self.auto_clear_var
        ).pack(anchor="w", pady=2)
        
        tk.Checkbutton(
            auto_frame, 
            text="保存后自动打开文件夹", 
            variable=self.auto_open_var
        ).pack(anchor="w", pady=2)
        
        tk.Checkbutton(
            auto_frame, 
            text="自动去除重复项", 
            variable=self.remove_dup_var
        ).pack(anchor="w", pady=2)
        
        tk.Checkbutton(
            auto_frame, 
            text="自动去除首尾空格", 
            variable=self.trim_space_var
        ).pack(anchor="w", pady=2)
        
        # 按钮框架
        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=20)
        
        # 保存按钮
        save_button = tk.Button(
            button_frame,
            text="保存配置",
            command=self.save_config,
            width=15,
            height=2
        )
        save_button.pack(side="left", padx=10)
        
        # 应用按钮
        apply_button = tk.Button(
            button_frame,
            text="应用并更新",
            command=self.apply_and_update,
            width=15,
            height=2
        )
        apply_button.pack(side="left", padx=10)
        
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
        """保存配置"""
        try:
            self.config.set("output_path", 1 if self.path_var.get() == "桌面" else 0)
            self.config.set("default_filename", self.name_var.get())
            self.config.set("auto_clear_input", self.auto_clear_var.get())
            self.config.set("auto_open_folder", self.auto_open_var.get())
            self.config.set("remove_duplicates", self.remove_dup_var.get())
            self.config.set("trim_spaces", self.trim_space_var.get())
            
            # 更新主界面的文件名
            self.app.filename_var.set(self.name_var.get())
            
            logger.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def apply_and_update(self):
        """应用配置并更新界面"""
        self.save_config()
        self.app.set_status("配置已应用")
        self.window.destroy()

def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("随机抽人名单编码工具 V1.0 启动")
        logger.info(f"工作目录: {user_path}")
        logger.info(f"数据目录: {prog_data_path}")
        logger.info(f"输出目录: {output_path}")
        logger.info("=" * 50)
        
        # 创建主窗口
        root = tk.Tk()
        root.title("随机抽人名单编码工具 V1.0")
        root.geometry("600x600+50+50")
        root.minsize(500, 500)
        
        # 创建应用程序
        app = MainApplication(root)
        
        # 绑定窗口关闭事件
        def on_closing():
            if messagebox.askyesno("确认", "确定要退出程序吗？"):
                logger.info("程序正常退出")
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 启动主循环
        root.mainloop()
        
        logger.info("程序正常退出")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}", exc_info=True)
        messagebox.showerror("错误", f"程序启动失败:\n{e}")

if __name__ == '__main__':
    main()