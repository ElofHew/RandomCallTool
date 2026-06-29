"""
日志处理模块 - 为各应用提供 RotatingFileHandler 日志记录
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
from core.info import rct_log_path, rct_appname

default_log_path = "logs"
default_appname = "Unknown"

def setup_logging(appname=default_appname, logpath=default_log_path):
    """配置并返回以 appname 命名的日志记录器（含控制台与文件处理器）"""
    logger_name = f"{appname}-logger"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器（重要！）
    if logger.handlers:
        return logger

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)

    # 按日期滚动的文件输出
    os.makedirs(logpath, exist_ok=True)
    log_file = os.path.join(logpath, f"{appname}-{strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
    )
    logger.addHandler(file_handler)

    return logger

rctlog = setup_logging(appname=rct_appname, logpath=rct_log_path)
updlog = setup_logging(appname="UpdateTool", logpath=rct_log_path)