"""系统托盘：常驻任务栏通知区，右键可快速访问主要功能。"""
import queue
import threading

from core.config import ConfigManager
from core.info import rct_icon_path
from core.logman import rctlog

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
    TRAY_IMPORT_ERROR = ""
except Exception as _import_error:
    pystray = None
    Image = None
    TRAY_AVAILABLE = False
    TRAY_IMPORT_ERROR = str(_import_error)


def is_available():
    """托盘依赖是否可用"""
    return TRAY_AVAILABLE


def unavailable_reason():
    """托盘不可用时的原因描述"""
    return TRAY_IMPORT_ERROR or "未安装 pystray / Pillow"


class TrayIcon:
    """托盘图标：在独立线程运行，回调统一投递回主线程执行。"""

    def __init__(self, root, app):
        self.root = root
        self.app = app
        self.icon = None
        self._thread = None
        self._queue = queue.Queue()
        self.active = False

    # ── 生命周期 ──

    def start(self):
        """创建并启动托盘图标"""
        if self.active or not TRAY_AVAILABLE:
            return False
        try:
            image = self._load_image()
            self.icon = pystray.Icon(
                "RandomCallTool",
                image,
                "随机抽取工具",
                menu=self._build_menu(),
            )
            self._thread = threading.Thread(target=self.icon.run, daemon=True)
            self._thread.start()
            self.active = True
            # 主线程轮询回调队列
            self.root.after(200, self._poll_queue)
            rctlog.info("[托盘] 图标已启动")
            return True
        except Exception as e:
            rctlog.error(f"[托盘] 启动失败: {e}")
            self.icon = None
            self.active = False
            return False

    def stop(self):
        """停止托盘图标"""
        if not self.active or self.icon is None:
            return
        try:
            self.icon.stop()
            rctlog.info("[托盘] 图标已停止")
        except Exception as e:
            rctlog.warning(f"[托盘] 停止失败: {e}")
        finally:
            self.active = False
            self.icon = None

    def _load_image(self):
        """加载托盘图标，失败时退回一个简单的纯色图标"""
        try:
            return Image.open(rct_icon_path)
        except Exception as e:
            rctlog.warning(f"[托盘] 图标加载失败，使用默认图标: {e}")
            return Image.new("RGBA", (64, 64), (74, 144, 217, 255))

    # ── 菜单 ──

    def _build_menu(self):
        from core import floatball

        def checked_ball(item):
            return bool(ConfigManager().get("floatball_enabled", True))

        return pystray.Menu(
            pystray.MenuItem("显示主界面", self._post(self.show_main), default=True),
            pystray.MenuItem("软件配置", self._post(self.open_config)),
            pystray.MenuItem("检测更新", self._post(self.check_update)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("显示悬浮球", self._post(self.toggle_floatball),
                             checked=checked_ball),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._post(self.quit_app)),
        )

    def sync_menu(self):
        """刷新菜单的勾选状态"""
        if self.icon is not None:
            try:
                self.icon.update_menu()
            except Exception as e:
                rctlog.warning(f"[托盘] 刷新菜单失败: {e}")

    # ── 线程调度 ──

    def _post(self, func):
        """包装回调：投递到主线程队列执行（pystray 的回调在托盘线程中）"""
        def wrapper(*_args):
            self._queue.put(func)
        return wrapper

    def _poll_queue(self):
        """主线程：取出并执行托盘回调"""
        while True:
            try:
                func = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                func()
            except Exception as e:
                rctlog.error(f"[托盘] 回调执行失败: {e}")
        if self.active:
            self.root.after(200, self._poll_queue)

    # ── 菜单动作 ──

    def show_main(self):
        """显示并前置主窗口"""
        root = self.root
        root.deiconify()
        root.state("normal")
        root.lift()
        root.attributes("-topmost", True)
        root.after(300, lambda: root.attributes("-topmost", False))
        rctlog.info("[托盘] 显示主界面")

    def open_config(self):
        """打开配置窗口"""
        self.show_main()
        from core.window import ConfigWindow
        ConfigWindow(self.root)

    def check_update(self):
        """检测更新"""
        try:
            from core.update import run_auto_update
            config = ConfigManager()
            ok = run_auto_update(
                source=config.get("update_source", "github"),
                mode="--check",
                accept_preview=config.get("accept_preview_update", False),
            )
            if not ok:
                rctlog.warning("[托盘] 更新程序启动失败")
        except Exception as e:
            rctlog.error(f"[托盘] 检测更新失败: {e}")

    def toggle_floatball(self):
        """切换悬浮球显示状态"""
        from core import floatball
        config = ConfigManager()
        enabled = not bool(config.get("floatball_enabled", True))
        config.set("floatball_enabled", enabled)
        floatball.refresh()
        self.sync_menu()
        rctlog.info(f"[托盘] 悬浮球已{'显示' if enabled else '隐藏'}")

    def quit_app(self):
        """退出程序"""
        rctlog.info("[托盘] 用户选择退出程序")
        self.stop()
        try:
            from core import floatball
            floatball.destroy()
        except Exception as e:
            rctlog.warning(f"[托盘] 关闭悬浮球失败: {e}")
        try:
            self.root.destroy()
        except Exception:
            pass


_tray = {"instance": None}


def setup(root, app):
    """创建托盘实例，并按配置决定是否启动"""
    if _tray["instance"] is None:
        _tray["instance"] = TrayIcon(root, app)
    else:
        _tray["instance"].root = root
        _tray["instance"].app = app
    refresh()
    return _tray["instance"]


def get():
    """获取当前托盘实例（可能为 None）"""
    return _tray["instance"]


def is_active():
    """托盘图标是否正在运行"""
    return bool(_tray["instance"] and _tray["instance"].active)


def refresh():
    """按配置启用 / 停用托盘；被停用时确保主窗口可见"""
    tray = _tray["instance"]
    if tray is None:
        return
    if not TRAY_AVAILABLE:
        return
    enabled = bool(ConfigManager().get("tray_enabled", True))
    if enabled and not tray.active:
        tray.start()
    elif not enabled and tray.active:
        tray.stop()
        tray.show_main()