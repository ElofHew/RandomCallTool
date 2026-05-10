"""
随机抽取工具配置管理器
"""
import os
from .common import BaseConfigManager
from .constants import CONFIG_PATH

class ConfigManager(BaseConfigManager):
    config_path = CONFIG_PATH
    default_config = {
        "result_path": 0,
        "save_result": True,
        "auto_load_sample": True,
        "max_history_items": 10,
        "rcg_total_default": 9,
        "rcg_choice_default": 3,
        "rcp_choice_default": 1,
        "rcp_merge_names": True,
        "rcp_default_sample": ".\\data\\default.rcp",
        "shuffle_before_sample": True,
        "use_weighted_sampling": False,
    }