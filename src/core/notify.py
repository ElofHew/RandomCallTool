"""抽取结果通知：支持弹窗和 ClassIsland 通知两种模式。"""
import threading
from tkinter import messagebox

from core.logman import rctlog
from core.config import ConfigManager
from core import islandmq


def notify_result(popup_title, items, default_mask_title=None):
    """按配置提醒抽取结果

    popup_title: 弹窗标题（弹窗正文为「标题：\n每行一项」）
    items:       结果列表
    default_mask_title: ClassIsland 遮罩文本的默认值（配置项 ci_title 留空时使用）
    """
    items = [str(i) for i in items]
    text = popup_title + "：\n" + "\n".join(items)

    config = ConfigManager()
    mode = str(config.get("notify_mode", "popup") or "popup").lower()

    if mode != "island":
        messagebox.showinfo(popup_title, text)
        return

    # ── ClassIsland 通知 ──
    if not islandmq.is_available():
        rctlog.warning("[提醒] 未安装 pyzmq，回退为弹窗提醒")
        messagebox.showwarning(
            popup_title, f"未检测到 pyzmq，无法发送 ClassIsland 通知。\n\n{text}")
        return

    mask_title = (str(config.get("ci_title", "") or "").strip()
                  or default_mask_title or popup_title)

    # 发送参数先取出：后续在后台线程里不再访问 ConfigManager
    payload = (
        mask_title,
        "、".join(items),
        config.get("ci_ip", islandmq.DEFAULT_IP),
        config.get("ci_port", islandmq.DEFAULT_PORT),
        config.get("ci_mask_duration", islandmq.DEFAULT_MASK_DURATION),
        config.get("ci_overlay_duration", islandmq.DEFAULT_OVERLAY_DURATION),
        config.get("ci_timeout_ms", islandmq.DEFAULT_TIMEOUT_MS),
    )
    fallback = config.get("ci_fallback_popup", True)

    def _send():
        """后台线程发送，避免网络不通时阻塞界面最多 1 秒"""
        ok, msg = islandmq.send_notice(*payload)
        if ok:
            rctlog.info(f"[提醒] ClassIsland 通知已发送（{mask_title}）: {items}")
            return
        rctlog.error(f"[提醒] ClassIsland 通知发送失败: {msg}")
        # 回退弹窗需要回到主线程执行
        if fallback:
            _show_in_main(lambda: messagebox.showwarning(
                popup_title, f"ClassIsland 通知发送失败：{msg}\n\n{text}"))
        else:
            _show_in_main(lambda: messagebox.showerror("通知发送失败", msg))

    threading.Thread(target=_send, daemon=True).start()


def _show_in_main(func):
    """在 Tk 主线程中执行 func（非主线程直接弹窗会出错）"""
    try:
        import tkinter as tk
        root = tk._default_root
        if root is not None:
            root.after(0, func)
            return
    except Exception:
        pass
    try:
        func()
    except Exception as e:
        rctlog.error(f"[提醒] 回退弹窗失败: {e}")
