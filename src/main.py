import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkFont
from random import randint, sample
import os

class More:
    def __init__(self, root):
        self.root = root

    def quit(self):
        """退出"""
        self.root.quit()

    def about(self):
        """关于"""
        messagebox.showinfo("关于", "随机抽取工具\n版本：1.0\n作者：Dan_Evan\n日期：2025-12-26\n网站：www.danevan.top")

class RandomGroupTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.create_widgets()
        
    def create_widgets(self):
        """创建随机抽组界面组件"""
        # 创建标题标签
        title_label = tk.Label(self.frame, text="随机抽组", font=("Helvetica", 18, "bold"), fg="blue")
        title_label.pack(pady=10, ipady=15)
        
        # 创建标签和选择框
        label_total = tk.Label(self.frame, text="一共有几个组（样本总数）")
        label_total.pack(pady=5)
        self.total_entry = ttk.Combobox(self.frame, values=list(range(1, 11)), state="readonly")
        self.total_entry.pack(pady=5)
        self.total_entry.set("9")  # 设置默认显示文本为9
        
        label_choice = tk.Label(self.frame, text="你要抽取几个组？")
        label_choice.pack(pady=5)
        self.choice_entry = ttk.Combobox(self.frame, values=list(range(1, 11)), state="readonly")
        self.choice_entry.pack(pady=5)
        self.choice_entry.set("3")  # 设置默认显示文本为3
        
        # 创建按钮
        button = tk.Button(self.frame, text="抽取", command=self.select_groups)
        button.pack(pady=10)
        
        # 创建结果标签
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(self.frame, font=bold_font, text="", wraplength=350, justify="left")
        self.result_label.pack(pady=10, padx=10, fill="both", expand=True)
    
    def comparison(self, total_num, choice_num):
        """校验输入值"""
        try:
            total_num = int(total_num)
            choice_num = int(choice_num)
            if choice_num > total_num:
                messagebox.showwarning("错误", "抽取数量不能大于总数量")
                return False, 0, 0
            elif choice_num == total_num:
                messagebox.showinfo("提示", "抽取数量与总数量相同，无需抽取")
                return False, 0, 0
            elif choice_num < 1:
                messagebox.showwarning("错误", "抽取数量不能小于1")
                return False, 0, 0
            elif total_num < 1:
                messagebox.showwarning("错误", "样本总数不能小于1")
                return False, 0, 0
            else:
                return True, total_num, choice_num
        except ValueError:
            messagebox.showwarning("错误", "请输入有效的数字")
            return False, 0, 0
    
    def select_groups(self):
        """随机抽取组"""
        # 清空之前的抽取结果
        self.result_label.config(text="")
        comparison_result, total_num, choice_num = self.comparison(
            self.total_entry.get(), self.choice_entry.get()
        )
        
        if not comparison_result:
            return
        
        try:
            group_list = []
            info_list = []
            for _ in range(choice_num):
                while True:
                    result_num = randint(1, total_num)
                    if result_num not in group_list:
                        group_list.append(result_num)
                        break
                self.result_label.config(text=self.result_label.cget("text") + f"\n{result_num}组")
                info_list.append(f"{result_num}组")
            
            # 对结果进行排序
            group_list.sort()
            sorted_text = "\n".join([f"{num}组" for num in group_list])
            self.result_label.config(text=sorted_text)
            
            info_text = "\n".join(info_list)
            messagebox.showinfo("抽取结果", f"抽取结果：\n{info_text}")
        except ValueError:
            messagebox.showwarning("错误", "未知数据类型")

class RandomPersonTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.names = []
        self.create_widgets()
        
    def create_widgets(self):
        """创建随机抽人界面组件"""
        # 创建标题标签
        title_label = tk.Label(self.frame, text="随机抽人", font=("Helvetica", 18, "bold"), fg="blue")
        title_label.pack(pady=10, ipady=15)
        
        # 创建标签和按钮来选择文件
        label_total = tk.Label(self.frame, text="加载样本列表（txt文件）")
        label_total.pack(pady=5)
        
        # 文件路径显示框
        self.file_path_label = tk.Label(self.frame, text="未选择文件", fg="gray", wraplength=350)
        self.file_path_label.pack(pady=5)
        
        # 按钮框架
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=5)
        
        button_load = tk.Button(button_frame, text="选择文件", command=self.load_names, width=10)
        button_load.pack(side="left", padx=5)
        
        button_auto = tk.Button(button_frame, text="自动加载", command=self.auto_load_sample_file, width=10)
        button_auto.pack(side="left", padx=5)
        
        # 样本数量显示
        self.sample_count_label = tk.Label(self.frame, text="样本数量: 0", fg="green")
        self.sample_count_label.pack(pady=5)
        
        label_choice = tk.Label(self.frame, text="你要抽取几个人？")
        label_choice.pack(pady=5)
        self.choice_entry = ttk.Combobox(self.frame, values=list(range(1, 101)), state="readonly")
        self.choice_entry.pack(pady=5)
        self.choice_entry.set("1")  # 设置默认显示文本为1
        
        # 创建抽取按钮
        button = tk.Button(self.frame, text="抽取", command=self.select_persons)
        button.pack(pady=10)
        
        # 创建结果标签
        bold_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
        self.result_label = tk.Label(self.frame, font=bold_font, text="", 
                                     wraplength=350, justify="left")
        self.result_label.pack(pady=10, padx=10, fill="both", expand=True)
    
    def load_names_from_file(self, file_path=None):
        """从文件加载名字"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
        if not file_path:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                names = file.readlines()
                result = [name.strip() for name in names if name.strip()]
            
            # 更新文件路径显示
            self.file_path_label.config(text=os.path.basename(file_path))
            # 更新样本数量显示
            self.sample_count_label.config(text=f"样本数量: {len(result)}")
            
            return result
        except Exception as e:
            messagebox.showwarning("错误", f"读取文件时发生错误: {e}")
            return []
    
    def auto_load_sample_file(self):
        """自动尝试加载当前目录下的sample.txt文件"""
        if os.path.exists('sample.txt'):
            self.names = self.load_names_from_file('sample.txt')
            if self.names:
                messagebox.showinfo("成功", f"自动加载样本列表 sample.txt\n共加载 {len(self.names)} 个名字")
        else:
            messagebox.showinfo("提示", "未找到 sample.txt 文件")
    
    def load_names(self):
        """加载名字并更新显示"""
        self.names = self.load_names_from_file()
        if self.names:
            messagebox.showinfo("成功", f"样本列表已加载\n共加载 {len(self.names)} 个名字")
    
    def select_persons(self):
        """选择人员并显示"""
        if not self.names:
            messagebox.showwarning("警告", "请先加载列表文件")
            return
        
        choice_num = self.choice_entry.get()
        if not choice_num:
            return
        
        try:
            choice_num = int(choice_num)
            if choice_num > len(self.names):
                messagebox.showwarning("警告", f"抽取数量({choice_num})大于总数量({len(self.names)})，无法抽取")
                return
            elif choice_num == len(self.names):
                messagebox.showinfo("提示", "抽取数量与总数量相同，无需抽取")
                return
            elif choice_num < 1:
                messagebox.showwarning("警告", "抽取数量必须大于0")
                return
            
            selected_persons = sample(self.names, choice_num)
            self.result_label.config(text="\n".join(selected_persons))
            messagebox.showinfo("抽取结果", f"抽取结果：\n" + "\n".join(selected_persons))
        except ValueError:
            messagebox.showwarning("错误", "请输入有效的数字")

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
        
        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        more_instance = More(self.root)
        file_menu.add_command(label="退出", command=more_instance.quit)
        help_menu.add_command(label="关于", command=more_instance.about)
    
    def create_tabs(self):
        """创建选项卡界面"""
        # 创建Notebook（选项卡控件）
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建两个选项卡
        self.group_tab = RandomGroupTab(self.notebook)
        self.person_tab = RandomPersonTab(self.notebook)
        
        # 添加选项卡到Notebook
        self.notebook.add(self.group_tab.frame, text="随机抽组")
        self.notebook.add(self.person_tab.frame, text="随机抽人")

# 创建主窗口
root = tk.Tk()
root.title("随机抽取工具")
root.geometry("350x550+50+50")
root.minsize(300, 500)
root.maxsize(1000, 1000)
root.resizable(True, True)

# 设置窗口图标（可选）
try:
    root.iconbitmap(default='icon.ico')
except:
    pass

# 创建应用程序
app = MainApplication(root)

# 运行主循环
root.mainloop()