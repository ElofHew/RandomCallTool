"""
配置管理器 - 随机抽取工具的 JSON 配置读写（单例模式）
"""
import os
import json
from core.logman import rctlog
from core.info import rct_config_path

class ConfigManager:
    """配置管理器（单例模式）"""
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件，缺失项用默认值补充"""
        default_config = {
            "result_path": 0,
            "save_result": True,
            "auto_load_sample": True,
            "max_history_items": 10,
            "rcg_total_default": 9,
            "rcg_choice_default": 3,
            "rcp_choice_default": 1,
            "rcp_merge_names": True,
            "rcp_default_sample": "",
            "sampler_mode": 0,
            "smart_window": 3,
            # ── 更新设置 ──
            "update_source": "github",
            "auto_check_update": True,
        }

        if os.path.exists(rct_config_path):
            try:
                with open(rct_config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                for key, value in default_config.items():
                    if key not in self._config:
                        self._config[key] = value
            except Exception as e:
                rctlog.error(f"加载配置文件失败: {e}")
                self._config = default_config
        else:
            self._config = default_config
            self._save_config()

        rctlog.info(f"配置已加载: {self._config}")

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(rct_config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            rctlog.error(f"保存配置文件失败: {e}")

    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key, value):
        """设置配置项"""
        self._config[key] = value
        self._save_config()
