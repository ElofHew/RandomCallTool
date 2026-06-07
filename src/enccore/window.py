import tkinter as tk
from tkinter import messagebox
from core.logman import enclog

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
        self.path_var = tk.StringVar(value="桌面" if self.config.get("enc_output_path", 0) == 1 else "数据目录")
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
            self.config.set("enc_output_path", 1 if self.path_var.get() == "桌面" else 0)
            self.config.set("default_filename", self.name_var.get())
            self.config.set("auto_clear_input", self.auto_clear_var.get())
            self.config.set("auto_open_folder", self.auto_open_var.get())
            self.config.set("remove_duplicates", self.remove_dup_var.get())
            self.config.set("trim_spaces", self.trim_space_var.get())
            
            # 更新主界面的文件名
            self.app.filename_var.set(self.name_var.get())
            
            enclog.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            
        except Exception as e:
            enclog.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def apply_and_update(self):
        """应用配置并更新界面"""
        self.save_config()
        self.app.set_status("配置已应用")
        self.window.destroy()
