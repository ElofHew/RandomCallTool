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
            # ── 基本设置 ──
            "result_path": 0,             # 结果保存位置: 0=数据目录, 1=桌面
            "save_result": False,          # 是否自动保存抽取结果
            "auto_load_sample": True,      # 启动时自动加载默认样本
            "max_history_items": 10,       # 历史记录最大条数

            # ── 抽组默认值 ──
            "rct_group_total": 9,          # 抽取 - 默认总组数

            # ── 抽人默认值 ──
            "rct_merge_names": True,       # 加载名单时自动合并重复名字
            "rct_default_sample": "",     # 默认加载的样本名称

            # ── 抽取默认值 ──
            "rct_choice_default": 3,       # 抽取 - 默认选取数量（抽组/抽人公用）
            "rct_default_mode": "group",   # 默认抽取方式: person=抽人, group=抽组

            # ── 抽样设置 ──
            "sampler_mode": 1,             # 抽样模式: 0=基本, 1=智能, 2=加权
            "smart_window": 3,             # 智能模式的记忆次数

            # ── 更新设置 ──
            "update_source": "github",      # 版本更新源: github/gitee
            "auto_check_update": True,     # 启动时自动检测更新
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
