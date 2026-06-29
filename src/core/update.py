"""
检测更新模块（精简版）— 保留网络层供主程序自动检测使用
UI 界面已移至 src/update.py（独立更新程序）
"""
import json
import os
import sys
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from core.info import rct_vercode, rct_version, rct_appname
from core.logman import rctlog

# -- 远程元数据地址 --
GITHUB_META_URL = "https://raw.githubusercontent.com/ElofHew/RandomCallTool/refs/heads/main/metadata.json"
GITEE_META_URL = "https://raw.giteeusercontent.com/ElofHew/RandomCallTool/raw/main/metadata.json"

# -- 更新源映射 --
SOURCE_NAMES = {"github": "GitHub", "gitee": "Gitee"}
SOURCE_META_URLS = {"github": GITHUB_META_URL, "gitee": GITEE_META_URL}


def fetch_remote_metadata(source="github", timeout=10):
    url = SOURCE_META_URLS.get(source)
    if not url:
        raise ValueError("未知的更新源: " + str(source))
    source_name = SOURCE_NAMES.get(source, source)
    rctlog.info("[检测更新] 正在从 " + source_name + " 获取版本信息...")
    req = Request(url, headers={"User-Agent": rct_appname + "/" + rct_version})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    metadata = json.loads(raw)
    rctlog.info("[检测更新] 远程元数据获取成功: " + str(metadata.get("version", {})))
    return metadata, source_name


def compare_version(remote_metadata):
    ver_info = remote_metadata.get("version", {})
    remote_vercode = ver_info.get("vercode", 0)
    remote_version = ver_info.get("version", "?")
    remote_date = ver_info.get("date", "?")
    return {
        "has_update": remote_vercode > rct_vercode,
        "local_vercode": rct_vercode,
        "remote_vercode": remote_vercode,
        "local_version": rct_version,
        "remote_version": remote_version,
        "remote_date": remote_date,
    }


def check_update(source="github", timeout=10):
    result = {"success": False, "error": None, "has_update": False,
              "source_name": "", "lanzou_download_url": "", "lanzou_password": ""}
    try:
        metadata, source_name = fetch_remote_metadata(source, timeout)
        result["source_name"] = source_name
        cmp = compare_version(metadata)
        result.update(cmp)
        lz = metadata.get("lanzou", {})
        result["lanzou_download_url"] = lz.get("download", "")
        result["lanzou_password"] = lz.get("password", "")
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
        rctlog.error("[检测更新] 错误: " + str(e))
    return result


def run_auto_update(source="github", timeout=120, mode="--check"):
    """启动独立更新程序（update.py / update.exe）
    mode: "--check" 打开检测界面 | "--check-silent" 静默检测
    """
    try:
        upd_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "update.py")
        if getattr(sys, "frozen", False):
            upd_path = os.path.join(os.path.dirname(sys.executable), "update.exe")
        else:
            upd_path = upd_py

        if not os.path.isfile(upd_path):
            rctlog.error("[自动更新] 更新程序不存在: " + str(upd_path))
            return False

        args = [upd_path, "--source", source, mode]
        if upd_path.endswith(".py"):
            python = sys.executable or "python"
            args = [python] + args

        if mode == "--check-silent":
            # 静默模式：需要获取返回码，隐藏窗口
            proc = subprocess.run(args, capture_output=True, timeout=timeout,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            return proc.returncode == 1  # 1=有更新
        else:
            # 非静默模式：GUI 需正常显示，不用 CREATE_NO_WINDOW
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rctlog.info("[自动更新] 更新程序已启动 (PID: " + str(proc.pid) + ")")
            return True
    except Exception as e:
        rctlog.error("[自动更新] 启动失败: " + str(e))
        return False
