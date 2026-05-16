"""
随机抽取工具配置管理器
"""
from .common import BaseConfigManager
from .constants import (ENCODE_CONFIG_PATH, CONFIG_PATH)

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

class EncodeConfigManager(BaseConfigManager):
    config_path = ENCODE_CONFIG_PATH
    default_config = {
        "output_path": 0, # 0: 数据目录, 1: 桌面
        "auto_clear_input": False,
        "default_filename": "sample_list",
        "auto_open_folder": True,
        "remove_duplicates": True,
        "trim_spaces": True
    }