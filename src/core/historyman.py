"""抽取历史记录：把每次抽取实时追加写入本地日期文件。"""
import os
from time import strftime

from core.logman import rctlog
from core.config import ConfigManager
from core.info import rct_history_path

# 抽取类型 → 记录中的名称
MODE_LABELS = {"person": "随机抽人", "group": "随机抽组"}


def is_enabled():
    """是否启用历史文件写入（配置项 history_file_enabled）"""
    return bool(ConfigManager().get("history_file_enabled", True))


def history_file_path(day=None):
    """当天记录文件路径：data/history/YYYY-MM-DD.txt"""
    return os.path.join(rct_history_path, (day or strftime("%Y-%m-%d")) + ".txt")


def format_line(time_text, mode, count, items):
    """生成一行记录：[HH:MM:SS]：随机抽人：抽取数量3：张三、李四"""
    label = MODE_LABELS.get(mode, "随机抽取")
    names = "、".join(str(i) for i in items)
    return f"[{time_text}]：{label}：抽取数量{count}：{names}"


def append(mode, items, time_text=None, force=False):
    """把一次抽取追加写入当天的记录文件

    force: 忽略配置开关强制写入（用于结果过多、必须落盘的场景）

    Returns: 写入的文件路径；未启用或失败时返回 None
    """
    if not force and not is_enabled():
        return None
    items = list(items or [])
    if not items:
        return None
    line = format_line(time_text or strftime("%H:%M:%S"), mode, len(items), items)
    path = history_file_path()
    try:
        os.makedirs(rct_history_path, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        rctlog.info(f"[历史记录] 已写入 {path}: {line}")
        return path
    except Exception as e:
        rctlog.error(f"[历史记录] 写入失败: {e}")
        return None


def clear_files():
    """删除全部记录文件

    Returns: 成功删除的文件数量
    """
    if not os.path.isdir(rct_history_path):
        return 0
    removed = 0
    for name in os.listdir(rct_history_path):
        if not name.endswith(".txt"):
            continue
        try:
            os.remove(os.path.join(rct_history_path, name))
            removed += 1
        except Exception as e:
            rctlog.error(f"[历史记录] 删除 {name} 失败: {e}")
    return removed