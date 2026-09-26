"""ClassIsland IslandMQ 通知客户端。"""
import json
from ipaddress import ip_address

from core.logman import rctlog

try:
    import zmq
    ZMQ_AVAILABLE = True
    ZMQ_IMPORT_ERROR = ""
except Exception as _import_error:      # ImportError 或 DLL 加载失败
    zmq = None
    ZMQ_AVAILABLE = False
    ZMQ_IMPORT_ERROR = str(_import_error)

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = "5555"
DEFAULT_TITLE = "随机抽取结果"
DEFAULT_MASK_DURATION = 1.0
DEFAULT_OVERLAY_DURATION = 3.0
MAX_TIMEOUT_MS = 1000           # 本地直连推送，正常应秒发，超时上限设为 1 秒
DEFAULT_TIMEOUT_MS = MAX_TIMEOUT_MS
PING_TIMEOUT_MS = MAX_TIMEOUT_MS

_context = None      # 全局 zmq.Context（懒创建）


# 可用性与生命周期

def is_available():
    """pyzmq 是否可用"""
    return ZMQ_AVAILABLE


def unavailable_reason():
    """pyzmq 不可用时的原因描述"""
    return ZMQ_IMPORT_ERROR or "未安装 pyzmq"


def _get_context():
    """获取（懒创建）全局 Context"""
    global _context
    if _context is None:
        _context = zmq.Context()
        rctlog.info("[IslandMQ] 已创建 ZeroMQ Context")
    return _context


def shutdown():
    """释放全局 Context（程序退出时调用）"""
    global _context
    if _context is None:
        return
    try:
        _context.term()
        rctlog.info("[IslandMQ] 已释放 ZeroMQ Context")
    except Exception as e:
        rctlog.warning(f"[IslandMQ] 释放 Context 失败: {e}")
    finally:
        _context = None


# 地址处理

def clean_ip(ip):
    """去掉用户可能输入的 IPv6 方括号"""
    ip = str(ip or "").strip()
    if ip.startswith("[") and ip.endswith("]"):
        ip = ip[1:-1]
    return ip


def build_endpoint(ip, port):
    """校验 IP / 端口并构造 tcp:// 端点，非法时抛出 ValueError"""
    ip = clean_ip(ip)
    port = str(port or "").strip()

    if not ip:
        raise ValueError("IP 地址不能为空")
    try:
        ip_address(ip)
    except ValueError:
        raise ValueError(f"IP 地址格式不正确：{ip}")

    if not port:
        raise ValueError("端口不能为空")
    if not port.isdigit():
        raise ValueError("端口必须是纯数字")
    if not (1 <= int(port) <= 65535):
        raise ValueError("端口号必须在 1~65535 之间")

    if ":" in ip:      # IPv6 需要方括号
        return f"tcp://[{ip}]:{port}"
    return f"tcp://{ip}:{port}"


def _safe_timeout(value, default=DEFAULT_TIMEOUT_MS):
    """把超时值规范为合法整数毫秒，并限制在 MAX_TIMEOUT_MS 以内"""
    try:
        ms = int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default
    if ms <= 0:
        return default
    return min(ms, MAX_TIMEOUT_MS)


def _safe_duration(value, default):
    """把时长规范为大于 0 的浮点数（秒）"""
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return round(seconds, 1) if seconds > 0 else default


# 请求发送

def _request(endpoint, payload, timeout_ms, tag=""):
    """在独立 REQ socket 上发送一次请求

    Returns:
        (bool, str): (是否成功, 提示信息)
    """
    if not ZMQ_AVAILABLE:
        return False, f"未安装 pyzmq（{ZMQ_IMPORT_ERROR}），ClassIsland 通知不可用"

    timeout_ms = _safe_timeout(timeout_ms)
    prefix = f"[{tag}] " if tag else ""
    sock = None
    try:
        sock = _get_context().socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
        sock.setsockopt(zmq.SNDTIMEO, timeout_ms)
        sock.setsockopt(zmq.LINGER, 0)
        sock.connect(endpoint)

        text = json.dumps(payload, ensure_ascii=False)
        rctlog.info(f"[IslandMQ] {prefix}发送 -> {endpoint}: {text}")
        sock.send_string(text)
        reply = sock.recv_string()
        rctlog.info(f"[IslandMQ] {prefix}收到 <- {endpoint}: {reply}")

        try:
            resp = json.loads(reply)
        except ValueError:
            # 插件返回了非 JSON 内容，视为成功但原样转发
            return True, reply

        if isinstance(resp, dict):
            return bool(resp.get("success", False)), str(resp.get("message", reply))
        return True, str(resp)

    except zmq.Again:
        rctlog.warning(f"[IslandMQ] {prefix}{endpoint} 请求超时（{timeout_ms}ms）")
        return False, ("请求超时：请确认教室电脑在线、IP 与端口正确，"
                       "且 ClassIsland 已启用 IslandMQ 插件并监听该端口")
    except zmq.ZMQError as e:
        rctlog.error(f"[IslandMQ] {prefix}{endpoint} ZeroMQ 错误: {e}")
        return False, f"网络错误：{e}"
    except Exception as e:
        rctlog.error(f"[IslandMQ] {prefix}{endpoint} 发送失败: {e}")
        return False, f"未知错误：{e}"
    finally:
        if sock is not None:
            try:
                sock.close(linger=0)
            except Exception:
                pass


# 对外功能

def ping(ip, port, timeout_ms=PING_TIMEOUT_MS):
    """连接测试（发送 ping 心跳）"""
    try:
        endpoint = build_endpoint(ip, port)
    except ValueError as e:
        return False, str(e)
    return _request(endpoint, {"version": 0, "command": "ping", "args": []},
                    timeout_ms, tag="连接测试")


def send_notice(title, body, ip, port,
                mask_duration=DEFAULT_MASK_DURATION,
                overlay_duration=DEFAULT_OVERLAY_DURATION,
                timeout_ms=DEFAULT_TIMEOUT_MS):
    """发送一条通知

    title: 遮罩（标题）文本
    body:  正文（通知内容）文本，为空则不发送正文
    mask_duration:    遮罩显示时长（秒）
    overlay_duration: 正文显示时长（秒）
    """
    try:
        endpoint = build_endpoint(ip, port)
    except ValueError as e:
        return False, str(e)

    title = str(title or "").strip() or DEFAULT_TITLE
    mask = _safe_duration(mask_duration, DEFAULT_MASK_DURATION)
    overlay = _safe_duration(overlay_duration, DEFAULT_OVERLAY_DURATION)

    args = [title]
    if body:
        args.append(f"--context={body}")
    args.append(f"--mask-duration={mask}")
    args.append(f"--overlay-duration={overlay}")

    return _request(endpoint, {"version": 0, "command": "notice", "args": args},
                    timeout_ms, tag="通知")
