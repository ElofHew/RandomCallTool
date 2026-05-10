"""
随机抽取工具 - 文件和结果管理
"""
import os
import logging
from time import strftime
from tkinter import messagebox

from .common import BaseFileManager
from .config import ConfigManager
from .constants import (
    RESULT_PATH, DESKTOP_RESULT_PATH, LOG_PATH,
    __github__, __gitee__
)

logger = logging.getLogger(__name__)


class FileManager:
    @staticmethod
    def get_result_path():
        config = ConfigManager()
        if config.get("result_path", 0) == 1:
            save_dir = DESKTOP_RESULT_PATH
        else:
            save_dir = RESULT_PATH
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    @staticmethod
    def open_directory(path):
        return BaseFileManager.open_directory(path)

    @staticmethod
    def open_log_file():
        log_file = os.path.join(LOG_PATH, f"{strftime('%Y-%m-%d')}.log")
        return BaseFileManager.open_file(log_file)


class SaveResult:
    def __init__(self):
        self.config = ConfigManager()

    def make_html(self, class_name, result, save_message=None):
        if class_name == "RandomGroup":
            cname = "随机抽组"
        elif class_name == "RandomPerson":
            cname = "随机抽人"
        else:
            cname = "抽取结果"

        result_text = "<br>".join(result)
        current_time = strftime('%Y-%m-%d %H:%M:%S')

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
            <p><strong>抽取时间：</strong>{current_time}</p>
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
            生成于 随机抽取工具 v2.1 | <a href="{__github__}" target="_blank">GitHub</a> | <a href="{__gitee__}" target="_blank">Gitee</a> | UTC+8 {current_time}
        </div>
    </div>
</body>
</html>"""
        return template

    def save_result(self, class_name, prefix, result, save_message=""):
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