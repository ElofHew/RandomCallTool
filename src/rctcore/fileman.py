"""
文件管理器模块
"""
# 导入本地库
import os
from base64 import b64decode
# 导入时间戳格式化
from time import strftime
# 导入Tkinter消息框方法
from tkinter import messagebox
# 导入应用库
from core.logman import rctlog
from rctcore.config import ConfigManager
from core.info import rct_prog_data_path, rct_result_path, rct_desktop_result_path, rct_log_path, rct_appname, github, gitee

class FileManager:
    """文件管理器"""
    
    @staticmethod
    def get_result_path():
        """获取结果保存路径"""
        config = ConfigManager()
        if config.get("result_path", 0) == 1:
            save_dir = rct_desktop_result_path
        else:
            save_dir = rct_result_path
        
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
            rctlog.info(f"打开目录: {path}")
            return True
        except Exception as e:
            rctlog.error(f"打开目录失败: {e}")
            messagebox.showerror("错误", f"无法打开目录: {e}")
            return False
    
    @staticmethod
    def open_log_file():
        """打开日志文件"""
        try:
            log_file = os.path.join(rct_log_path, f"{rct_appname}-{strftime('%Y-%m-%d')}.log")
            if os.path.exists(log_file):
                os.startfile(log_file)
                rctlog.info("打开日志文件")
                return True
            else:
                messagebox.showinfo("提示", "今天的日志文件不存在")
                return False
        except Exception as e:
            rctlog.error(f"打开日志文件失败: {e}")
            messagebox.showerror("错误", f"无法打开日志文件: {e}")
            return False


class SaveResult:
    """保存结果功能模块"""
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
            生成于 随机抽取工具 v2.2 | <a href="{github}" target="_blank">GitHub</a> | <a href="{gitee}" target="_blank">Gitee</a> | UTC+8 {curren_time}
        </div>
    </div>
</body>
</html>"""
        return template
    
    def save_result(self, class_name, prefix, result, save_message=""):
        """保存结果"""
        if not result:
            rctlog.warning(f"[{prefix}] 结果为空，跳过保存")
            return None
        
        try:
            save_dir = FileManager.get_result_path()
            timestamp = strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(save_dir, f"{prefix}_{timestamp}.html")
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.make_html(class_name, result, save_message))
            
            rctlog.info(f"[{prefix}] 结果已保存到: {file_path}")
            messagebox.showinfo("成功", f"抽取结果已保存到:\n{file_path}")
            return file_path
            
        except Exception as e:
            rctlog.error(f"[{prefix}] 保存结果失败: {e}")
            messagebox.showwarning("错误", f"保存结果失败: {e}")
            return None

def base64decode(data=None):
    """Base64解码"""
    try:
        decoded = b64decode(data).decode('utf-8')
        rctlog.info("Base64解码成功")
        return decoded
    except Exception as e:
        rctlog.error(f"Base64解码失败: {e}")
        return ""
