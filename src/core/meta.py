"""
元数据存放模块
"""
# 导入OS模块以处理路径数据
from os import path as osp
from os import getcwd

"""定义程序元数据"""
version = "2.1"
author = "Dan_Evan"
date = "2026-01-10"
github = "https://github.com/ElofHew/RandomCallTool"
gitee = "https://gitee.com/ElofHew/RandomCallTool"
description = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"

"""定义全局变量"""
work_path = getcwd()
prog_data_path = osp.join(work_path, "data")
log_path = osp.join(prog_data_path, "log")
result_path = osp.join(prog_data_path, "result")

user_home_path = osp.expanduser("~")
desktop_path = osp.join(user_home_path, "Desktop")
desktop_result_path = osp.join(desktop_path, "随机抽取结果")
document_path = osp.join(user_home_path, "Documents")

config_path = osp.join(prog_data_path, "config.json")

available_files_types = [
    ("可用文件", "*.rcp;*.txt;*.csv"),
    ("名单文件", "*.rcp"),
    ("文本文件", "*.txt"),
    ("CSV文件", "*.csv"),
    ("所有文件", "*.*")
]
