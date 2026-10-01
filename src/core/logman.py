"""日志工具：按日期滚动写入日志文件。"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from time import strftime
from core.info import rct_log_path, rct_appname

default_log_path = "logs"
default_appname = "Unknown"

class DatedRotatingFileHandler(TimedRotatingFileHandler):
    """按日期滚动，归档名形如 <stem>.<date>.log，方便 *.log 统一清理。

    默认的 TimedRotatingFileHandler 归档名形如：
        RandomCallTool.log.2026-09-27
    本类将其改为：
        RandomCallTool.2026-09-27.log
    这样清理日志时用 *.log 通配即可一并匹配到归档文件。
    """

    def rotation_filename(self, default_name):
        # default_name 形如: <dir>/RandomCallTool.log.2026-09-27
        dir_name, base_name = os.path.split(default_name)
        stem, sep, date = base_name.rpartition(".log.")
        if not sep:
            return default_name
        # 目标形如: <dir>/RandomCallTool.2026-09-27.log
        return os.path.join(dir_name, f"{stem}.{date}.log")

    def getFilesToDelete(self):
        # 自定义归档命名后，父类基于 baseFilename + "." 的匹配方式会失效，
        # 这里改为匹配 <stem>.<date>.log
        dir_name, base_name = os.path.split(self.baseFilename)
        stem = base_name[:-4] if base_name.endswith(".log") else base_name
        prefix = stem + "."
        suffix = ".log"

        result = []
        try:
            file_names = os.listdir(dir_name)
        except OSError:
            return result

        for file_name in file_names:
            if not (file_name.startswith(prefix) and file_name.endswith(suffix)):
                continue
            date_part = file_name[len(prefix):-len(suffix)]
            if self.extMatch.match(date_part):
                result.append(os.path.join(dir_name, file_name))

        if len(result) < self.backupCount:
            return []
        result.sort()
        return result[:len(result) - self.backupCount]

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

    # 按日期滚动：当前文件固定为 <appname>.log，
    # 每天午夜滚动时旧日志归档为 <appname>.<date>.log
    os.makedirs(logpath, exist_ok=True)
    log_file = os.path.join(logpath, f"{appname}.log")
    file_handler = DatedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    # 滚动后文件名形如 RandomCallTool.2026-09-27.log
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
    )
    logger.addHandler(file_handler)

    return logger

rctlog = setup_logging(appname=rct_appname, logpath=rct_log_path)