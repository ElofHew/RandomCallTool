"""
随机抽取工具 - 元数据和全局路径常量
"""
import os

# 元数据
__version__ = "2.1"
__author__ = "Dan_Evan"
__date__ = "2026-01-10"
__github__ = "https://github.com/ElofHew/RandomCallTool"
__gitee__ = "https://gitee.com/ElofHew/RandomCallTool"
__description__ = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"

# 路径常量
WORK_PATH = os.getcwd()
PROG_DATA_PATH = os.path.join(WORK_PATH, "data")
LOG_PATH = os.path.join(PROG_DATA_PATH, "log")
RESULT_PATH = os.path.join(PROG_DATA_PATH, "result")

USER_HOME_PATH = os.path.expanduser("~")
DESKTOP_PATH = os.path.join(USER_HOME_PATH, "Desktop")
DESKTOP_RESULT_PATH = os.path.join(DESKTOP_PATH, "随机抽取结果")
DOCUMENT_PATH = os.path.join(USER_HOME_PATH, "Documents")

# 配置文件路径（随机抽取工具）
CONFIG_PATH = os.path.join(PROG_DATA_PATH, "config.json")

# 支持的文件类型
AVAILABLE_FILES_TYPES = [
    ("可用文件", "*.rcp;*.txt;*.csv"),
    ("名单文件", "*.rcp"),
    ("文本文件", "*.txt"),
    ("CSV文件", "*.csv"),
    ("所有文件", "*.*")
]