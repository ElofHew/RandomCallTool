"""卸载与安装辅助逻辑，包括清理脚本生成和链式安装流程。"""
import os
import time
import subprocess
from core import updconf

# 跨平台兜底：CREATE_NO_WINDOW 仅 Windows 存在，其它平台取 0
NO_WINDOW_FLAG = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# 进程列表

def get_process_list():
    """需要杀死的进程名列表"""
    return ["rctool", "update"]


def kill_processes():
    """结束正在运行的套件程序"""
    print("[Uninstall] Killing running processes...")
    for name in get_process_list():
        try:
            subprocess.run(["taskkill", "/F", "/IM", f"{name}.exe"],
                           capture_output=True, timeout=5)
        except Exception:
            pass
    time.sleep(0.5)


def get_extra_uninstall_targets():
    """卸载额外清理项：开始菜单文件夹 + 桌面快捷方式

    为避免遗漏，开始菜单与桌面的「公用」与「当前用户」两个位置都尝试删除：
      - 开始菜单文件夹: 「随机抽取工具」或「随机抽取工具套件」
        * 当前用户: %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
        * 公用:     %ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs
      - 桌面快捷方式: 「随机抽取工具.lnk」
        * 当前用户: %USERPROFILE%\\Desktop
        * 公用:     %PUBLIC%\\Desktop
    返回路径列表（不管是否存在，由 remove.bat 用 if exist 判断）
    """
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    programdata = os.environ.get("ProgramData") or r"C:\ProgramData"
    public = os.environ.get("PUBLIC") or r"C:\Users\Public"

    targets = []
    start_menu_bases = [
        os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    for base in start_menu_bases:
        for name in ("随机抽取工具", "随机抽取工具套件"):
            targets.append(os.path.join(base, name))

    desktop_dirs = [
        os.path.join(home, "Desktop"),
        os.path.join(public, "Desktop"),
    ]
    for desktop in desktop_dirs:
        targets.append(os.path.join(desktop, "随机抽取工具.lnk"))

    # 启动文件夹中的开机自启快捷方式：
    #   公共 shell:common startup + 当前用户 shell:startup（兜底）
    startup_dirs = [
        os.path.join(programdata, "Microsoft", "Windows", "Start Menu",
                     "Programs", "StartUp"),
        os.path.join(appdata, "Microsoft", "Windows", "Start Menu",
                     "Programs", "Startup"),
    ]
    for startup in startup_dirs:
        targets.append(os.path.join(startup, "随机抽取工具.lnk"))

    return targets

def get_cache_dir():
    """返回 data/cache 目录路径"""
    return os.path.join(updconf.PROGRAM_ROOT, "data", "cache")

def get_files_to_delete(mode):
    """获取要删除的文件/目录列表"""
    if mode == "reset":
        return [os.path.join(updconf.PROGRAM_ROOT, "data")], updconf.PROGRAM_ROOT

    all_items = []
    for name in os.listdir(updconf.PROGRAM_ROOT):
        path = os.path.join(updconf.PROGRAM_ROOT, name)
        if name in ("remove.exe", "remove.py"):
            continue
        all_items.append(path)

    if mode == "keep-data":
        data_dir = os.path.join(updconf.PROGRAM_ROOT, "data")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        keep = {data_dir,
                os.path.join(desktop, "\u968f\u673a\u62bd\u53d6\u7ed3\u679c"),
                os.path.join(desktop, "\u7f16\u7801\u540d\u5355")}
        filtered = []
        for p in all_items:
            skip = False
            for kd in keep:
                try:
                    if not os.path.relpath(p, kd).startswith(".."):
                        skip = True
                        break
                except ValueError:
                    pass
            if not skip:
                filtered.append(p)
        all_items = filtered

    # 保留数据卸载 / 完全卸载：额外清理开始菜单与桌面快捷方式
    if mode in ("keep-data", "full"):
        all_items.extend(get_extra_uninstall_targets())

    return all_items, updconf.PROGRAM_ROOT

def _build_cache_cleanup_bat(cache_dir, exclude_path=None):
    """生成清空 data/cache 目录内容的 bat 片段

    - 保留 cache 目录本身（避免程序下次启动因目录缺失报错）
    - 保留 exclude_path 指向的文件（通常是从 cache 里正在运行的安装包）
    """
    cache_dir = os.path.normpath(os.path.abspath(cache_dir))
    exclude = os.path.normpath(os.path.abspath(exclude_path)) if exclude_path else None

    bat = 'echo [Uninstall] Cleaning cache...\r\n'
    bat += f'if exist "{cache_dir}" (\r\n'
    if exclude:
        # 逐个比对完整路径，跳过正在运行的安装包
        bat += f'    for %%f in ("{cache_dir}\\*") do (\r\n'
        bat += f'        if exist "%%~ff" (\r\n'
        bat += f'            if /i not "%%~ff"=="{exclude}" del /f /q "%%~ff" >nul 2>&1\r\n'
        bat += '        )\r\n'
        bat += '    )\r\n'
        bat += f'    for /d %%d in ("{cache_dir}\\*") do (\r\n'
        bat += f'        if /i not "%%~fd"=="{exclude}" rmdir /s /q "%%~fd" >nul 2>&1\r\n'
        bat += '    )\r\n'
    else:
        bat += f'    del /f /q "{cache_dir}\\*" >nul 2>&1\r\n'
        bat += f'    for /d %%d in ("{cache_dir}\\*") do rmdir /s /q "%%d" >nul 2>&1\r\n'
    bat += ')\r\n'
    return bat

def build_remove_script(mode, setup_path=None):
    """构建 remove.bat → 写入 %TEMP%，返回 bat 路径

    bat 流程:
      1. 结束所有套件进程
      2. 按模式删除文件
      3. 如果给了安装包：等待安装完成 → 清空 data/cache（保留安装包自身）
      4. 删除自身
    """
    items, root_dir = get_files_to_delete(mode)
    root_dir = os.path.normpath(root_dir)

    bat = "@echo off\r\nchcp 65001 >nul\r\n"
    bat += "title RandomCallTool Uninstall...\r\n"
    bat += "echo [Uninstall] Removing program files...\r\n"

    for name in get_process_list():
        bat += f'taskkill /F /IM "{name}.exe" >nul 2>&1\r\n'

    bat += "timeout /t 1 /nobreak >nul\r\n"

    for item in items:
        n = os.path.normpath(item)
        bat += f'if exist "{n}" (\r\n'
        if os.path.isdir(item):
            bat += f'    rmdir /s /q "{n}" >nul 2>&1\r\n'
        else:
            bat += f'    del /f /q "{n}" >nul 2>&1\r\n'
        bat += ")\r\n"
    if mode == "full":
        bat += f'rmdir /s /q "{root_dir}" >nul 2>&1\r\n'

    if setup_path and os.path.isfile(setup_path):
        sp = os.path.normpath(setup_path)
        bat += 'echo [Uninstall] Running setup...\r\n'
        # 用 start /wait 等安装程序返回，随后再清理缓存。
        # 注意：若安装包是「自解压后 fork 出真正安装进程」的实现，
        # start /wait 只会等自解压外壳退出，不会等到真正安装完成。
        bat += f'start /wait "" "{sp}"\r\n'
        bat += _build_cache_cleanup_bat(get_cache_dir(), exclude_path=sp)

    bat += 'del /f /q "%~f0" >nul 2>&1\r\n'
    bat += 'exit\r\n'

    tmp = os.environ.get("TEMP", os.path.expanduser("~"))
    os.makedirs(tmp, exist_ok=True)
    sp = os.path.join(tmp, "rct_remove.bat")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(bat)
    return sp


def run_uninstall(mode, setup_path=None):
    """执行卸载：构建 bat → 非阻塞运行 → 杀死自身"""
    MODE_LABELS = {"keep-data": "Keep Data", "reset": "Reset", "full": "Full Uninstall"}
    label = MODE_LABELS.get(mode, mode)
    print("=" * 50)
    print("  Random Call Tool - Uninstaller")
    print("  Mode: " + label)
    print("  Directory: " + updconf.PROGRAM_ROOT)
    if setup_path:
        print("  Setup: " + setup_path)
    print("=" * 50)

    kill_processes()
    script = build_remove_script(mode, setup_path)

    print("[Uninstall] Starting cleanup in background...")
    subprocess.Popen([script], creationflags=NO_WINDOW_FLAG)

    print("[Uninstall] Uninstaller exiting...")
    time.sleep(0.5)
    os._exit(0)


# remove.exe 路径与链式调用

def get_remove_path():
    candidates = [updconf.REMOVE_EXE, os.path.join(updconf.PROGRAM_ROOT, "src", "remove.py")]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return updconf.REMOVE_EXE


def run_remove_with_setup(setup_path):
    """启动 remove.exe，传安装包路径，使 bat 链式完成卸载→安装→清理缓存→自毁

    remove.exe 会：
      1. 构建 remove.bat 写入 %TEMP%
      2. bat 杀进程 → 删文件 → 等待安装包运行完 → 清空 data/cache（保留安装包自身）→ 自删
      3. remove.exe 自毁
    """
    if not setup_path or not os.path.isfile(setup_path):
        return False
    rp = get_remove_path()
    if not os.path.isfile(rp):
        return False
    try:
        subprocess.Popen([rp, "keep-data", "-y",
                          "--setup-path", setup_path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=NO_WINDOW_FLAG)
        return True
    except Exception:
        return False
