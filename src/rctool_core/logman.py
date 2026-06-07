"""
日志处理模块
"""
# 导入基本库
import os
import logging
from logging.handlers import RotatingFileHandler
# 导入应用库（元数据、时间戳）
from rctool_core.meta import log_path
# 导入时间戳格式化
from time import strftime

def setup_logging():
    """设置日志记录"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
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

logger = setup_logging()
