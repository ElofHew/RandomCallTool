"""
更新程序网络层 — 元数据获取、版本比对、下载 URL 构造
"""
import json
from urllib.request import urlopen, Request
from utils import config


def fetch_json(url, timeout=15):
    req = Request(url, headers={"User-Agent": "RandomCallTool-Update"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_remote_metadata(source="github", timeout=15):
    url = config.GITHUB_META if source == "github" else config.GITEE_META
    return fetch_json(url, timeout)


def check_remote_version(source="github", timeout=10):
    """检查远程是否有新版本，返回 dict"""
    result = {"success": False, "has_update": False,
              "local_version": config.VERSION, "local_vercode": config.VERCODE,
              "remote_version": "", "remote_vercode": 0,
              "remote_date": "", "source_name": config.SOURCE_NAMES.get(source, source),
              "error": None}
    try:
        meta = fetch_remote_metadata(source, timeout)
        ver = meta.get("version", {})
        result["remote_version"] = ver.get("version", "?")
        result["remote_vercode"] = ver.get("vercode", 0)
        result["remote_date"] = ver.get("date", "?")
        result["has_update"] = ver.get("vercode", 0) > config.VERCODE
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result


def get_download_url(metadata, source="github", version=""):
    """从 metadata 构造下载 URL"""
    ver = version or metadata.get("version", {}).get("version", "")
    filename = "RandomCallTool_Setup_V" + ver + ".exe"
    base = config.GITHUB_RELEASE if source == "github" else config.GITEE_RELEASE
    dl_url = base + "/download/V" + ver + "/" + filename
    return dl_url, filename
