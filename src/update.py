"""
RandomCallTool 独立更新程序
从 GitHub/Gitee Release 下载更新包 → 保留数据卸载旧版 → 安装新版

更新包命名规则: RandomCallTool_Setup_Vx.x.x.exe
更新包是一个静默解压安装包（NSIS/SFX），无需用户交互。

工作流程:
  1. 从远程 metadata.json 获取更新信息（或由主程序传入）
  2. 从 Release 下载更新包到 data/cache/
  3. 启动 remove.exe --mode keep-data（保留数据卸载）
  4. 启动下载好的安装包完成安装
  5. 更新程序自行退出
"""

import os
import sys
import json
import time
import argparse
import subprocess
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── 路径 ──
if getattr(sys, "frozen", False):
    PROGRAM_ROOT = os.path.dirname(sys.executable)
else:
    PROGRAM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROGRAM_ROOT, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
REMOVE_EXE = os.path.join(PROGRAM_ROOT, "remove.exe")

# ── 远程地址 ──
GITHUB_API = "https://api.github.com/repos/ElofHew/RandomCallTool/releases/latest"
GITHUB_META = "https://raw.githubusercontent.com/ElofHew/RandomCallTool/refs/heads/main/metadata.json"
GITEE_META = "https://raw.giteeusercontent.com/ElofHew/RandomCallTool/raw/main/metadata.json"


# ══════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════

def log(msg):
    """控制台输出"""
    print(f"[Update] {msg}")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def fetch_json(url, timeout=15):
    """获取远程 JSON"""
    req = Request(url, headers={"User-Agent": "RandomCallTool-Update"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_remove_exe_path():
    """获取 remove.exe 路径（支持打包和源码模式）"""
    candidates = [
        REMOVE_EXE,
        os.path.join(PROGRAM_ROOT, "src", "remove.py"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return REMOVE_EXE


# ══════════════════════════════════════════════════════════
#  获取版本信息
# ══════════════════════════════════════════════════════════

def fetch_remote_metadata(source="github", timeout=15):
    """获取远程 metadata.json"""
    url = GITHUB_META if source == "github" else GITEE_META
    return fetch_json(url, timeout)


def get_download_url_from_metadata(metadata, source="github"):
    """从 metadata 中提取下载 URL

    返回 (download_url, filename)
    """
    ver = metadata.get("version", {}).get("version", "")
    filename = f"RandomCallTool_Setup_V{ver}.exe"

    # 优先蓝奏云（在 metadata 中）
    lanzou = metadata.get("lanzou", {})
    if source == "lanzou" and lanzou.get("download"):
        return lanzou["download"], filename

    # GitHub / Gitee Release 直接下载 URL
    if source == "github":
        # GitHub Release Asset 直链
        # 格式: https://github.com/{owner}/{repo}/releases/download/v{ver}/{filename}
        dl_url = f"https://github.com/ElofHew/RandomCallTool/releases/download/v{ver}/{filename}"
    else:
        dl_url = f"https://gitee.com/ElofHew/RandomCallTool/releases/download/v{ver}/{filename}"

    return dl_url, filename


# ══════════════════════════════════════════════════════════
#  下载逻辑
# ══════════════════════════════════════════════════════════

def download_file(url, dest_path, timeout=120):
    """下载文件，显示进度"""
    log(f"开始下载: {url}")
    log(f"保存到: {dest_path}")

    req = Request(url, headers={"User-Agent": "RandomCallTool-Update"})
    with urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 8192

        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 // total
                    log(f"下载进度: {pct}% ({downloaded // 1024}KB / {total // 1024}KB)")
                else:
                    log(f"已下载: {downloaded // 1024}KB")

    log("下载完成")
    return os.path.getsize(dest_path)


# ══════════════════════════════════════════════════════════
#  卸载与安装流程
# ══════════════════════════════════════════════════════════

def run_remove_keep_data():
    """运行 remove.exe 保留数据卸载"""
    remove_exe = get_remove_exe_path()
    log(f"运行保留数据卸载: {remove_exe}")

    if not os.path.isfile(remove_exe):
        log(f"警告: remove.exe 不存在 ({remove_exe})，跳过卸载步骤")
        return True

    try:
        # remove.exe 支持命令行: remove.exe keep-data -y
        proc = subprocess.Popen(
            [remove_exe, "keep-data", "-y"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        # 等待完成（最多 30 秒）
        try:
            proc.wait(timeout=30)
            log(f"卸载完成，退出码: {proc.returncode}")
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            log("卸载超时，强制终止")
            proc.kill()
            return False
    except Exception as e:
        log(f"卸载失败: {e}")
        return False


def run_installer(exe_path):
    """运行下载好的安装包"""
    log(f"运行安装包: {exe_path}")
    if not os.path.isfile(exe_path):
        log(f"错误: 安装包不存在 ({exe_path})")
        return False

    try:
        # Windows: 直接运行，静默安装
        subprocess.Popen(
            [exe_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        log("安装包已启动，更新程序退出")
        return True
    except Exception as e:
        log(f"运行安装包失败: {e}")
        return False


# ══════════════════════════════════════════════════════════
#  主流程
# ══════════════════════════════════════════════════════════

def run_update(source="github", timeout=120):
    """完整更新流程"""
    log(f"更新源: {source}")

    # 1. 获取远程版本信息
    try:
        metadata = fetch_remote_metadata(source, timeout=15)
        log(f"远程版本: {metadata.get('version', {}).get('version', '?')}")
        ver_info = metadata.get("version", {})
        remote_version = ver_info.get("version", "")
        remote_vercode = ver_info.get("vercode", 0)
    except Exception as e:
        log(f"获取版本信息失败: {e}")
        return False

    # 2. 获取下载 URL
    dl_url, filename = get_download_url_from_metadata(metadata, source)
    log(f"文件名: {filename}")

    # 3. 准备缓存目录
    ensure_dir(CACHE_DIR)
    dest_path = os.path.join(CACHE_DIR, filename)

    # 4. 下载
    try:
        size = download_file(dl_url, dest_path, timeout)
        log(f"下载成功: {size} 字节")
    except Exception as e:
        log(f"下载失败: {e}")
        # 如果是蓝奏云链接，提示用户可能需要手动下载
        if source == "lanzou":
            log("蓝奏云链接可能需要浏览器访问，请手动下载:")
            log(f"  {dl_url}")
        return False

    # 5. 保留数据卸载
    log("步骤 1/2: 保留数据卸载旧版...")
    if not run_remove_keep_data():
        log("卸载失败或超时，继续尝试安装...")

    # 等待卸载进程完全退出
    time.sleep(1)

    # 6. 运行安装包
    log("步骤 2/2: 运行安装包...")
    if run_installer(dest_path):
        log("安装包已启动，更新程序退出")
        return True
    else:
        log("安装包启动失败")
        return False


# ══════════════════════════════════════════════════════════
#  命令行入口
# ══════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="RandomCallTool 独立更新程序"
    )
    parser.add_argument(
        "--source", choices=["github", "gitee", "lanzou"],
        default="github",
        help="更新源 (默认: github)"
    )
    parser.add_argument(
        "--timeout", type=int, default=120,
        help="下载超时秒数 (默认: 120)"
    )
    parser.add_argument(
        "--version", action="store_true",
        help="显示版本信息"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.version:
        from core.info import rct_version
        print(f"RandomCallTool Update Tool v{rct_version}")
        return

    ensure_dir(CACHE_DIR)

    log("=" * 50)
    log("RandomCallTool 更新程序启动")
    log(f"程序目录: {PROGRAM_ROOT}")
    log(f"缓存目录: {CACHE_DIR}")
    log("=" * 50)

    success = run_update(source=args.source, timeout=args.timeout)

    if success:
        log("更新流程完成")
    else:
        log("更新失败，请稍后重试或手动下载")
        sys.exit(1)


if __name__ == "__main__":
    main()
