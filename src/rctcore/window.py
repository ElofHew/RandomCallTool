"""
窗口界面模块
"""
# 导入Tkinter GUI库
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
# 导入应用库
from core.logman import rctlog
from rctcore.config import ConfigManager
from core.info import document_path

class ConfigWindow:
    """软件内配置窗口"""
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
                filetypes=[
                    ("可用文件", "*.rcp;*.txt;*.csv"),
                    ("名单文件", "*.rcp"),
                    ("文本文件", "*.txt"),
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*")
                ]
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

            rctlog.info("配置已保存")
            messagebox.showinfo("成功", "配置已保存")
            self.window.destroy()

        except Exception as e:
            rctlog.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败: {e}")
