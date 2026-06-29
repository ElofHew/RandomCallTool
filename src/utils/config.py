"""
更新程序配置 — 路径、常量、config.json 读写
"""
import os
import sys
import json

if getattr(sys, "frozen", False):
    PROGRAM_ROOT = os.path.dirname(sys.executable)
else:
    PROGRAM_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(PROGRAM_ROOT, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
REMOVE_EXE = os.path.join(PROGRAM_ROOT, "remove.exe")
RES_PATH = os.path.join(PROGRAM_ROOT, "res", "icon") if getattr(sys, "frozen", False) else \
           os.path.join(PROGRAM_ROOT, "src", "res", "icon")

# 元数据
VERSION = ""
VERCODE = 0
try:
    from core.info import rct_version, rct_vercode, rct_date, rct_appname
    VERSION = rct_version
    VERCODE = rct_vercode
except Exception:
    pass

# 远程地址
GITHUB_META = "https://raw.githubusercontent.com/ElofHew/RandomCallTool/refs/heads/main/metadata.json"
GITEE_META = "https://raw.giteeusercontent.com/ElofHew/RandomCallTool/raw/main/metadata.json"
GITHUB_RELEASE = "https://github.com/ElofHew/RandomCallTool/releases"
GITEE_RELEASE = "https://gitee.com/ElofHew/RandomCallTool/releases"
OFFICIAL_URL = "https://rct.danevan.top/#download"

SOURCE_NAMES = {"github": "GitHub", "gitee": "Gitee"}


def get_config_source():
    """从 config.json 读取 update_source，默认 github"""
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            src = cfg.get("update_source", "github")
            return src if src in SOURCE_NAMES else "github"
    except Exception:
        pass
    return "github"


def save_config_source(source):
    """将 update_source 写回 config.json"""
    try:
        cfg = {}
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["update_source"] = source
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
    except Exception:
        pass
