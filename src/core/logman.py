"""
日志处理模块
"""
# 导入基本库
import os
import logging
from logging.handlers import RotatingFileHandler
# 导入应用库（元数据、时间戳）
from core.info import rct_log_path, enc_log_path, rct_appname, enc_appname
# 导入时间戳格式化
from time import strftime

default_log_path = "logs"  # 默认日志路径
default_appname = "Unknown"  # 默认应用名称

def setup_logging(appname=default_appname, logpath=default_log_path):
    """设置日志记录"""
    logger_name = f"{appname}-logger"  # 日志名称
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器（重要！）
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    base_file = f"{appname}-{strftime('%Y-%m-%d')}.log"
    log_file = os.path.join(logpath, base_file)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

rctlog = setup_logging(appname=rct_appname, logpath=rct_log_path)
enclog = setup_logging(appname=enc_appname, logpath=enc_log_path)