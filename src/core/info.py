"""
项目全局路径与元数据常量
"""
import os
import sys

# ── 基础路径：区分源码运行和 PyInstaller 打包 ──
if getattr(sys, "frozen", False):
    # PyInstaller 打包后，exe 所在目录作为工作目录
    work_path = os.path.dirname(sys.executable)
    # res 文件夹复制到 exe 同目录
    res_path = os.path.join(work_path, "res")
else:
    # 源码运行
    work_path = os.getcwd()
    src_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    res_path = os.path.join(src_path, "res")
user_home_path = os.path.expanduser("~")
app_prog_data_path = os.path.join(work_path, "data")
app_local_data_path = os.path.join(user_home_path, ".randomcalltool")
desktop_path = os.path.join(user_home_path, "Desktop")
document_path = os.path.join(user_home_path, "Documents")
github = "https://github.com/ElofHew/RandomCallTool"
gitee = "https://gitee.com/ElofHew/RandomCallTool"
official_website = "https://rct.danevan.top"

# ── 主程序 RandomCallTool ──
rct_appname = "RandomCallTool"
rct_version = "2.5.2"
rct_vercode = 252000
rct_author = "Dan_Evan"
rct_date = "2026-06-30"
rct_description = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"
rct_prog_data_path = app_prog_data_path
rct_log_path = os.path.join(rct_prog_data_path, "log")
rct_result_path = os.path.join(rct_prog_data_path, "result")
rct_config_path = os.path.join(rct_prog_data_path, "config.json")
rct_desktop_result_path = os.path.join(desktop_path, "随机抽取结果")
rct_rcplist_path = os.path.join(rct_prog_data_path, "rcplist")
rct_cache_path = os.path.join(rct_prog_data_path, "cache")

# ── 程序图标路径 ──
rct_icon_path = os.path.join(res_path, "icon", "rctool.ico")
rem_icon_path = os.path.join(res_path, "icon", "remove.ico")
