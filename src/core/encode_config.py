"""
编码工具配置管理器
"""
from .common import BaseConfigManager
from .encode_constants import CONFIG_PATH

class EncodeConfigManager(BaseConfigManager):
    config_path = CONFIG_PATH
    default_config = {
        "output_path": 0,               # 0: 数据目录, 1: 桌面
        "auto_clear_input": False,
        "default_filename": "sample_list",
        "auto_open_folder": True,
        "remove_duplicates": True,
        "trim_spaces": True
    }