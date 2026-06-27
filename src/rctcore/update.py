"""
检测更新模块 — 从 GitHub/Gitee 获取远程 metadata.json 并与本地版本比对
"""
import json
import os
import sys
import subprocess
import threading
import webbrowser
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from core.info import rct_vercode, rct_version, rct_appname
from core.logman import rctlog

# ── 远程元数据地址 ──
GITHUB_META_URL = "https://raw.githubusercontent.com/ElofHew/RandomCallTool/refs/heads/main/metadata.json"
GITEE_META_URL = "https://raw.giteeusercontent.com/ElofHew/RandomCallTool/raw/main/metadata.json"
# GITEE_META_URL = "https://gitee.com/ElofHew/RandomCallTool/raw/main/metadata.json"
# 这个URL是Gitee的直连地址，但是不确定在本地程序能不能正常用，先留个URL在这里以后测试。

# ── 各平台下载页面 ──
GITHUB_RELEASE_URL = "https://github.com/ElofHew/RandomCallTool/releases/latest"
GITEE_RELEASE_URL = "https://gitee.com/ElofHew/RandomCallTool/releases/latest"
OFFICIAL_WEBSITE_URL = "https://rct.danevan.top/#download"

# ── 更新源名称映射 ──
SOURCE_NAMES = {
    "github": "GitHub",
    "gitee": "Gitee",
}

SOURCE_META_URLS = {
    "github": GITHUB_META_URL,
    "gitee": GITEE_META_URL,
}

# ── 下载源映射 ──
DOWNLOAD_SOURCE_NAMES = {
    "github": "GitHub",
    "gitee": "Gitee",
    "lanzou": "蓝奏云",
    "official": "官网",
}

SOURCE_DOWNLOAD_URLS = {
    "github": GITHUB_RELEASE_URL,
    "gitee": GITEE_RELEASE_URL,
    "lanzou": "",  # 从远程 metadata.json 动态获取
    "official": OFFICIAL_WEBSITE_URL,
}


def fetch_remote_metadata(source="github", timeout=10):
    """从远程获取 metadata.json 并解析为字典

    Args:
        source: "github" 或 "gitee"
        timeout: 请求超时秒数

    Returns:
        (metadata_dict, source_name) 成功时返回
        失败时抛出异常
    """
    url = SOURCE_META_URLS.get(source)
    if not url:
        raise ValueError(f"未知的更新源: {source}")

    source_name = SOURCE_NAMES.get(source, source)
    rctlog.info(f"[检测更新] 正在从 {source_name} 获取版本信息...")

    req = Request(url, headers={"User-Agent": f"{rct_appname}/{rct_version}"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")

    metadata = json.loads(raw)
    rctlog.info(f"[检测更新] 远程元数据获取成功: {metadata.get('version', {})}")
    return metadata, source_name


def compare_version(remote_metadata):
    """比对本地与远程版本号

    Args:
        remote_metadata: 远程 metadata.json 解析后的字典

    Returns:
        dict: {
            "has_update": bool,       # 是否有可用更新
            "local_vercode": int,     # 本地版本码
            "remote_vercode": int,    # 远程版本码
            "local_version": str,     # 本地版本号
            "remote_version": str,    # 远程版本号
            "remote_date": str,       # 远程发布日期
        }
    """
    ver_info = remote_metadata.get("version", {})
    remote_vercode = ver_info.get("vercode", 0)
    remote_version = ver_info.get("version", "未知")
    remote_date = ver_info.get("date", "未知")

    has_update = remote_vercode > rct_vercode

    return {
        "has_update": has_update,
        "local_vercode": rct_vercode,
        "remote_vercode": remote_vercode,
        "local_version": rct_version,
        "remote_version": remote_version,
        "remote_date": remote_date,
    }


def check_update(source="github", timeout=10):
    """一键检测更新：获取远程信息 → 比对 → 返回结果

    Args:
        source: "github" 或 "gitee"
        timeout: 请求超时秒数

    Returns:
        dict: {
            "success": bool,           # 检测是否成功
            "error": str or None,      # 错误信息
            "has_update": bool,        # 是否有更新
            "source_name": str,        # 更新源名称
            "download_url": str,       # 下载页面 URL
            ...  compare_version 的其他字段
        }
    """
    result = {
        "success": False,
        "error": None,
        "has_update": False,
        "source_name": "",
        "download_url": "",
    }

    try:
        metadata, source_name = fetch_remote_metadata(source, timeout)
        result["source_name"] = source_name
        result["download_url"] = SOURCE_DOWNLOAD_URLS.get(source, GITHUB_RELEASE_URL)

        cmp = compare_version(metadata)
        result.update(cmp)
        # 从 metadata 中提取蓝奏云链接（动态，不硬编码）
        lanzou_info = metadata.get("lanzou", {})
        result["lanzou_download_url"] = lanzou_info.get("download", "")
        result["lanzou_password"] = lanzou_info.get("password", "")
        result["success"] = True

    except (URLError, HTTPError) as e:
        result["error"] = f"网络请求失败: {e.reason if hasattr(e, 'reason') else e}"
        rctlog.error(f"[检测更新] 网络错误: {e}")
    except json.JSONDecodeError as e:
        result["error"] = f"解析远程数据失败: {e}"
        rctlog.error(f"[检测更新] JSON 解析错误: {e}")
    except ValueError as e:
        result["error"] = str(e)
        rctlog.error(f"[检测更新] 参数错误: {e}")
    except Exception as e:
        result["error"] = f"检测更新时发生未知错误: {e}"
        rctlog.error(f"[检测更新] 未知错误: {e}", exc_info=True)

    return result


def open_download_page(source="github", lanzou_url=None, lanzou_password=None):
    """在浏览器中打开对应平台的下载页面

    Args:
        source: "github" / "gitee" / "lanzou" / "official"
        lanzou_url: 从远程 metadata 获取的蓝奏云链接（动态，不硬编码）
        lanzou_password: 蓝奏云提取码（有值时弹窗提示）
    """
    try:
        if source == "lanzou" and lanzou_url:
            url = lanzou_url
            if lanzou_password:
                from tkinter import messagebox
                messagebox.showinfo(
                    "蓝奏云提取码",
                    f"蓝奏云下载页面需要提取码\n\n"
                    f"提取码: {lanzou_password}\n\n"
                    f"将在浏览器中打开下载页面，请输入该提取码。\n"
                    "提示：打开浏览器后URL最后的“?pwd=”后面四位文字即为提取码。"
                )
        else:
            url = SOURCE_DOWNLOAD_URLS.get(source, GITHUB_RELEASE_URL)
        webbrowser.open(url)
        rctlog.info(f"[检测更新] 已打开下载页面: {url}")
    except Exception as e:
        rctlog.error(f"[检测更新] 打开下载页面失败: {e}")


def run_auto_update(source="github", timeout=120):
    """启动独立更新程序（update.py）进行自动下载安装

    Args:
        source: "github" / "gitee" / "lanzou"
        timeout: 下载超时秒数

    Returns:
        bool: 是否成功启动更新程序
    """
    try:
        import subprocess
        from core.info import work_path

        # 查找 update.py / update.exe
        upd_py = os.path.join(work_path, "update.py")
        upd_exe = os.path.join(work_path, "update.exe")
        upd_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "update.py")

        upd_path = upd_exe if os.path.isfile(upd_exe) else (
            upd_py if os.path.isfile(upd_py) else upd_src
        )

        if not os.path.isfile(upd_path):
            rctlog.error(f"[自动更新] 更新程序不存在 ({upd_path})")
            return False

        args = [upd_path, "--source", source, "--timeout", str(timeout)]

        if upd_path.endswith(".py"):
            # 通过 Python 解释器运行
            python = sys.executable or "python"
            args = [python] + args

        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        rctlog.info(f"[自动更新] 更新程序已启动 (PID: {proc.pid}): {upd_path}")
        return True

    except Exception as e:
        rctlog.error(f"[自动更新] 启动更新程序失败: {e}")
        return False


def check_update_async(root, source="github", timeout=10,
                       on_success=None, on_error=None):
    """在后台线程中检测更新，避免阻塞 UI

    Args:
        root: tkinter root 窗口，用于调度主线程回调
        source: 更新源
        timeout: 超时秒数
        on_success: 成功时的回调函数 (result_dict) -> None
        on_error: 失败时的回调函数 (error_message) -> None
    """
    def _worker():
        try:
            result = check_update(source=source, timeout=timeout)
        except Exception as e:
            rctlog.error(f"[检测更新] 后台线程出错: {e}")
            _safe_call(lambda: on_error(str(e)) if on_error else None)
            return

        def _dispatch():
            if on_success:
                try:
                    on_success(result)
                except Exception as e:
                    rctlog.error(f"[检测更新] 回调执行失败: {e}")

        _safe_call(_dispatch)

    def _safe_call(fn):
        """安全地将回调调度到主线程，避免 root.after 本身抛异常"""
        try:
            root.after(0, fn)
        except Exception as e:
            rctlog.error(f"[检测更新] 调度回调到主线程失败: {e}")

    t = threading.Thread(target=_worker, daemon=True, name="UpdateCheck")
    t.start()
