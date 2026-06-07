"""
应用配置模块
"""
# 导入基本库
import os
import json
# 导入应用库
from rctool_core.logman import logger
from rctool_core.meta import config_path

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
            "result_path": 0,  # 结果保存路径(0:数据目录, 1:桌面)
            "save_result": True,  # 是否自动保存结果
            "auto_load_sample": True,  # 自动加载默认名单文件
            "max_history_items": 10,  # 最大历史记录条目数
            "rcg_total_default": 9,  # 随机抽组默认总组数
            "rcg_choice_default": 3,  # 随机抽组默认选择数
            "rcp_choice_default": 1,  # 随机抽人默认选择数
            "rcp_merge_names": True,  # 是否合并重复名字
            "rcp_default_sample": ".\\data\\default.rcp",  # 默认名单文件路径
            "shuffle_before_sample": True,  # 抽取前是否打乱
            "use_weighted_sampling": False,  # 是否使用加权抽样
        }
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                    for key, value in default_config.items():
                        if key not in self._config:
                            self._config[key] = value
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
            self._save_config()
        
        logger.info(f"配置已加载: {self._config}")
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value
        self._save_config()
