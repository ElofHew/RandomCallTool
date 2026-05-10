"""
编码工具 - 元数据和路径常量
"""
import os

__version__ = "1.0"
__author__ = "Dan_Evan"
__date__ = "2026-01-10"
__description__ = "一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。"

WORK_PATH = os.getcwd()
PROG_DATA_PATH = os.path.join(WORK_PATH, "data", "EncodeTool")
LOG_PATH = os.path.join(PROG_DATA_PATH, "log")
OUTPUT_PATH = os.path.join(PROG_DATA_PATH, "encoded_files")
DESKTOP_OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "编码名单")
CONFIG_PATH = os.path.join(PROG_DATA_PATH, "config_encode.json")

# 确保目录存在
for path in [PROG_DATA_PATH, OUTPUT_PATH, LOG_PATH]:
    os.makedirs(path, exist_ok=True)