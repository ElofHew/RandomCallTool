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

__encode_version__ = "1.0"
__encode_description__ = "一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。"

ENCODE_DATA_PATH = os.path.join(PROG_DATA_PATH, "EncodeTool")
ENCODE_LOG_PATH = os.path.join(ENCODE_DATA_PATH, "log")
ENCODE_OUTPUT_PATH = os.path.join(ENCODE_DATA_PATH, "encoded_files")
ENCODE_DESKTOP_OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "编码名单")
ENCODE_CONFIG_PATH = os.path.join(ENCODE_DATA_PATH, "config_encode.json")

# 确保目录存在
for path in [ENCODE_DATA_PATH, ENCODE_OUTPUT_PATH, ENCODE_LOG_PATH]:
    os.makedirs(path, exist_ok=True)