"""
配置管理器 - 编码工具的 JSON 配置读写与校验（单例模式）
"""
import os
import json
from core.logman import enclog
from core.info import enc_config_path


class ConfigManager:
    """配置管理器（单例模式）"""
    _instance = None
    _config = None

    DEFAULT_CONFIG = {
        # 输出设置
        "enc_output_path": 0,          # 0: 数据目录, 1: 桌面
        "default_filename": "sample_list",  # 默认文件名
        "auto_open_folder": True,      # 编码后自动打开文件夹

        # 编码设置
        "encoding_method": "base64",   # base64 / hex
        "file_encoding": "utf-8",      # 文件读写编码

        # 文本处理
        "remove_duplicates": True,     # 自动去除重复项
        "trim_spaces": True,           # 自动去除首尾空格
        "auto_clear_input": False,     # 编码后自动清空输入
        "sort_names": False,           # 编码前按字母排序
        "ignore_empty_lines": True,    # 忽略空行

        # 窗口设置
        "window_geometry": "",         # 窗口位置大小
        "window_maximized": False,     # 是否最大化

        # 最近文件
        "recent_files": [],            # 最近打开的文件列表
        "max_recent_files": 10,        # 最大保留数量

        # 高级选项
        "confirm_overwrite": True,     # 覆盖文件时确认
        "show_success_dialog": True,   # 编码成功后显示弹窗
        "batch_keep_subdirs": False,   # 批量处理时保留子目录结构
    }

    # 配置项类型与校验规则
    _VALIDATORS = {
        "enc_output_path": lambda v: v in (0, 1),
        "encoding_method": lambda v: v in ("base64", "hex"),
        "file_encoding": lambda v: v in ("utf-8", "gbk", "gb2312", "utf-16"),
        "max_recent_files": lambda v: isinstance(v, int) and 1 <= v <= 50,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(enc_config_path):
            try:
                with open(enc_config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # 补充缺失的配置项
                self._fill_missing_keys()
                # 校验并修正无效值
                self._validate_config()
            except Exception as e:
                enclog.error(f"加载配置文件失败: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self._save_config()

        enclog.info(f"配置已加载")

    def _fill_missing_keys(self):
        """补充缺失的默认配置项"""
        modified = False
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value
                modified = True
        if modified:
            self._save_config()

    def _validate_config(self):
        """校验配置值，修正无效值"""
        modified = False
        for key, validator in self._VALIDATORS.items():
            if key in self._config and not validator(self._config[key]):
                enclog.warning(f"配置项 {key} 值无效 ({self._config[key]})，使用默认值")
                self._config[key] = self.DEFAULT_CONFIG[key]
                modified = True
        if modified:
            self._save_config()

    def _save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(enc_config_path), exist_ok=True)
            with open(enc_config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
            enclog.info("配置已保存")
        except Exception as e:
            enclog.error(f"保存配置文件失败: {e}")

    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key, value):
        """设置单个配置项（自动校验）"""
        validator = self._VALIDATORS.get(key)
        if validator and not validator(value):
            enclog.warning(f"配置项 {key} 值无效，拒绝设置: {value}")
            return False
        self._config[key] = value
        self._save_config()
        enclog.info(f"配置已更新: {key} = {value}")
        return True

    def set_multi(self, items: dict):
        """批量设置配置项"""
        changed = False
        for key, value in items.items():
            validator = self._VALIDATORS.get(key)
            if validator and not validator(value):
                enclog.warning(f"配置项 {key} 值无效，跳过: {value}")
                continue
            self._config[key] = value
            changed = True
        if changed:
            self._save_config()
            enclog.info(f"批量配置已更新: {len(items)} 项")

    def add_recent_file(self, filepath: str):
        """添加最近打开的文件"""
        recent = self._config.get("recent_files", [])
        # 标准化路径
        filepath = os.path.normpath(filepath)
        # 如果已存在，移到最前面
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        # 限制数量
        max_count = self._config.get("max_recent_files", 10)
        self._config["recent_files"] = recent[:max_count]
        self._save_config()

    def get_recent_files(self):
        """获取最近文件列表（仅返回存在的文件）"""
        recent = self._config.get("recent_files", [])
        valid = [f for f in recent if os.path.exists(f)]
        if len(valid) != len(recent):
            self._config["recent_files"] = valid
            self._save_config()
        return valid

    def get_window_geometry(self):
        """获取保存的窗口几何信息"""
        geo = self._config.get("window_geometry", "")
        if geo and "x" in geo and "+" in geo:
            return geo
        return None
