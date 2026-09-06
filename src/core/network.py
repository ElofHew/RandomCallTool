"""
更新程序网络层 — 元数据获取、版本比对、下载 URL 构造
"""
import json
from urllib.request import urlopen, Request
from core import updconf


def fetch_json(url, timeout=15):
    req = Request(url, headers={"User-Agent": "RandomCallTool-Update"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_remote_metadata(source="github", timeout=15):
    url = updconf.GITHUB_META if source == "github" else updconf.GITEE_META
    return fetch_json(url, timeout)


def check_remote_version(source="github", timeout=10, accept_preview=False):
    """检查远程是否有新版本，返回 dict
    accept_preview: 是否接收测试版更新（优先使用 preview 段版本号）
    """
    result = {"success": False, "has_update": False,
              "local_version": updconf.VERSION, "local_vercode": updconf.VERCODE,
              "remote_version": "", "remote_vercode": 0,
              "remote_date": "", "source_name": updconf.SOURCE_NAMES.get(source, source),
              "quark_url": "", "lanzou_url": "", "lanzou_password": "",
              "error": None}
    try:
        meta = fetch_remote_metadata(source, timeout)
        ver = meta.get("version", {})
        remote_vercode = ver.get("vercode", 0)
        remote_version = ver.get("version", "?")
        remote_date = ver.get("date", "?")

        # 如果允许测试版更新，检查 preview 段的版本号
        if accept_preview:
            prev = meta.get("preview", {})
            prev_vercode = prev.get("vercode", 0)
            if prev_vercode > remote_vercode:
                remote_vercode = prev_vercode
                remote_version = prev.get("version", remote_version)
                remote_date = prev.get("date", remote_date)

        result["remote_version"] = remote_version
        result["remote_vercode"] = remote_vercode
        result["remote_date"] = remote_date
        result["has_update"] = remote_vercode > updconf.VERCODE
        # 网盘备用下载渠道（供更新界面展示）
        qk = meta.get("quark") or {}
        lz = meta.get("lanzou") or {}
        result["quark_url"] = qk.get("download", "")
        result["lanzou_url"] = lz.get("download", "")
        result["lanzou_password"] = lz.get("password", "")
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


def get_download_url(metadata, source="github", version=""):
    """从 metadata 构造下载 URL"""
    ver = version or metadata.get("version", {}).get("version", "")
    filename = "RandomCallTool_Setup_V" + ver + ".exe"
    base = updconf.GITHUB_RELEASE if source == "github" else updconf.GITEE_RELEASE
    dl_url = base + "/download/V" + ver + "/" + filename
    return dl_url, filename
