"""
编码工具 - 配置模块
"""
import os
import json
from core.logman import enclog
from core.info import enc_config_path

class ConfigManager:
    """配置管理器"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """加载配置文件"""
        default_config = {
            "enc_output_path": 0,  # 0: 数据目录, 1: 桌面
            "auto_clear_input": False,  # 编码后自动清空输入
            "default_filename": "sample_list",  # 默认文件名
            "auto_open_folder": True,  # 编码后自动打开文件夹
            "remove_duplicates": True,  # 自动去除重复项
            "trim_spaces": True  # 自动去除首尾空格
        }
        
        if os.path.exists(enc_config_path):
            try:
                with open(enc_config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                    # 确保所有配置项都存在
                    for key, value in default_config.items():
                        if key not in self._config:
                            self._config[key] = value
            except Exception as e:
                enclog.error(f"加载配置文件失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
            self._save_config()
        
        enclog.info(f"配置已加载: {self._config}")
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(enc_config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
            enclog.info("配置已保存")
        except Exception as e:
            enclog.error(f"保存配置文件失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value
        self._save_config()
        enclog.info(f"配置已更新: {key} = {value}")
