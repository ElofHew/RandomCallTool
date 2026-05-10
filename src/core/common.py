"""
通用组件：日志设置、基础配置管理器、基础文件管理器
"""
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from time import strftime
from tkinter import messagebox


def setup_logging(log_path, logger_name=None):
    """
    设置日志记录

    Args:
        log_path: 日志文件所在目录
        logger_name: 可选，指定日志记录器名称，为 None 则使用根日志记录器
    Returns:
        logger 实例
    """
    os.makedirs(log_path, exist_ok=True)

    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件处理器 - 按日期命名
    log_file = os.path.join(log_path, f"{strftime('%Y-%m-%d')}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


class BaseConfigManager:
    """配置管理器基类，子类需提供 config_path 属性和 default_config"""

    _instance = None
    _config = None
    config_path = None
    default_config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # 确保所有默认配置项都存在
                for key, value in self.default_config.items():
                    if key not in self._config:
                        self._config[key] = value
            except Exception as e:
                logging.getLogger(__name__).error(f"加载配置文件失败: {e}")
                self._config = self.default_config
        else:
            self._config = self.default_config
            self._save_config()
        logging.getLogger(__name__).info(f"配置已加载: {self._config}")

    def _save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.getLogger(__name__).error(f"保存配置文件失败: {e}")

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value
        self._save_config()


class BaseFileManager:
    """基础文件管理器，提供打开目录、打开文件等静态方法"""

    @staticmethod
    def open_directory(path):
        try:
            os.makedirs(path, exist_ok=True)
            os.startfile(path)
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"打开目录失败: {e}")
            messagebox.showerror("错误", f"无法打开目录: {e}")
            return False

    @staticmethod
    def open_file(file_path):
        try:
            if os.path.exists(file_path):
                os.startfile(file_path)
                return True
            else:
                messagebox.showinfo("提示", "文件不存在")
                return False
        except Exception as e:
            logging.getLogger(__name__).error(f"打开文件失败: {e}")
            messagebox.showerror("错误", f"无法打开文件: {e}")
            return False