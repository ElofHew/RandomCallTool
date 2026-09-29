"""JSON 配置读写管理器，负责加载和保存应用设置。"""
import os
import json
import threading
from core.logman import rctlog
from core.info import rct_config_path

class ConfigManager:
    """单例配置管理器。"""
    _instance = None
    _config = None
    # 写盘锁：后台更新线程与主线程可能并发写入
    _write_lock = threading.RLock()

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
            "save_result": True,           # 是否自动保存抽取结果
            "auto_load_sample": True,      # 启动时自动加载默认样本
            "max_history_items": 10,       # 历史记录最大条数
            "history_file_enabled": True,   # 是否把抽取历史实时写入本地文件

            # ── 抽组默认值 ──
            "rct_group_total": 9,          # 抽取 - 默认总组数

            # ── 抽人默认值 ──
            "rct_merge_names": True,       # 加载名单时自动合并重复名字
            "rct_default_sample": "",     # 默认加载的样本名称

            # ── 抽取默认值 ──
            "rct_choice_default": 3,       # 抽取 - 默认选取数量（抽组/抽人公用）
            "rct_default_mode": "person",  # 默认抽取方式: person=抽人, group=抽组

            # ── 抽样设置 ──
            "sampler_mode": 1,             # 抽样模式: 0=基本, 1=智能, 2=高级
            "smart_window": 3,             # 智能模式的记忆次数
            "smart_use_fixed_weights": False,  # 智能模式是否使用固定权重

            # ── 高级抽取设置 ──
            "adv_with_replacement": True,        # 放回式抽取
            "adv_no_replace_method": 0,          # 不放回调整方法: 0=连续循环, 1=整除式, 2=比率式
            "adv_no_replace_ratio": 0.5,         # 比率式调整阈值 (0.10~0.50)
            "adv_shuffle_before": False,         # 抽取前打乱
            "adv_shuffle_count": 1,              # 打乱次数 (1~10)
            "adv_shuffle_frequency": "each",     # 打乱频率: each=每次, once=仅启动时
            "adv_pre_draw_balance": False,       # 预抽取平衡
            "adv_pre_draw_count": 1,             # 预抽取次数 (1~10)
            "adv_pre_draw_frequency": "each",    # 预抽取频率: each=每次, once=仅启动时
            "adv_multi_draw_best": False,        # 多次取最值
            "adv_multi_draw_count": 3,           # 多次抽取次数 (2+)
            "adv_random_weights": False,         # 随机定权重
            "adv_random_weight_min": 0.10,       # 随机权重最小值
            "adv_random_weight_max": 2.00,       # 随机权重最大值
            "adv_progressive_draw": False,       # 递进式抽取
            "adv_smart_reduce_weight": True,     # 智能降权/配权
            "adv_smart_memory_count": 3,         # 高级模式记忆次数
            "adv_custom_weights": False,         # 高级模式自定义权重

            # ── 更新设置 ──
            "update_source": "github",          # 版本更新源: github/gitee
            "auto_check_update": True,          # 启动时自动检测更新
            "accept_preview_update": False,     # 是否接收测试版更新

            # ── 随机点名设置 ──
            "rollcall_speed": 1.0,              # 名字轮换速率倍数 (0.5~5.0, 1.0 为基准)
            "rollcall_shuffle": False,          # 点名前打乱名单顺序
            "rollcall_with_replacement": True,  # 放回式(True)/不放回式(False)
            "rollcall_reset_limit": "full",     # 重置限度: full/half/custom
            "rollcall_reset_custom": 1,         # 自定义重置阈值(剩多少人时重置)
            "rollcall_auto_load_sample": True,  # 启动时自动加载点名名单(独立于抽样)

            # ── 抽取后提醒 ──
            "notify_mode": "popup",             # 提醒方式: popup=弹窗, island=ClassIsland 通知
            "ci_ip": "127.0.0.1",               # ClassIsland 主机 IP
            "ci_port": "5555",                  # ClassIsland 端口
            "ci_title": "",                     # 通知标题（遮罩文本），留空按场景自动取默认
            "ci_mask_duration": 1.0,            # 遮罩显示时长（秒）
            "ci_overlay_duration": 3.0,         # 正文显示时长（秒）
            "ci_timeout_ms": 1000,              # 通知请求超时（毫秒，上限 1 秒）
            "ci_fallback_popup": True,          # ClassIsland 通知失败时回退为弹窗

            # ── 桌面悬浮球 ──
            "floatball_enabled": True,          # 是否显示桌面悬浮球
            "floatball_size": "medium",        # 悬浮球尺寸: small/medium/large
            "floatball_x": None,                # 悬浮球 X 坐标（None 时用默认位置）
            "floatball_y": None,                # 悬浮球 Y 坐标（None 时用默认位置）
            "floatball_kind": "person",         # 悬浮球快捷抽取类型: person/group_letter/group_number
            "floatball_count": 1,               # 悬浮球快捷抽取数量

            # ── 系统托盘 ──
            "tray_enabled": True,               # 关闭窗口后保留系统托盘
            "tray_start_minimized": False,      # 启动后直接后台驻留托盘

            # ── 开机自启 ──
            "auto_start": False,                # 开机时自动启动（启动文件夹快捷方式）
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
        """保存配置文件（原子写入：先写临时文件再 os.replace，避免写一半损坏）"""
        with self._write_lock:
            tmp_path = rct_config_path + ".tmp"
            try:
                os.makedirs(os.path.dirname(rct_config_path), exist_ok=True)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, rct_config_path)
            except Exception as e:
                rctlog.error(f"保存配置文件失败: {e}")
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass

    def get(self, key, default=None):
        """获取配置项"""
        return self._config.get(key, default)

    def set(self, key, value):
        """设置配置项并立即落盘"""
        with self._write_lock:
            self._config[key] = value
            self._save_config()
