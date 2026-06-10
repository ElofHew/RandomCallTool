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
rct_version = "2.3"
rct_vercode = 2300
rct_author = "Dan_Evan"
rct_date = "2026-06-09"
rct_description = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"
rct_prog_data_path = app_prog_data_path
rct_log_path = os.path.join(rct_prog_data_path, "log")
rct_result_path = os.path.join(rct_prog_data_path, "result")
rct_config_path = os.path.join(rct_prog_data_path, "config.json")
rct_desktop_result_path = os.path.join(desktop_path, "随机抽取结果")
rct_rcplist_path = os.path.join(rct_prog_data_path, "rcplist")

# ── 编码工具 EncodeTool ──
enc_appname = "EncodeTool"
enc_version = "1.2"
enc_vercode = 1200
enc_author = "Dan_Evan"
enc_date = "2026-06-09"
enc_description = "一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。"
enc_prog_data_path = os.path.join(app_prog_data_path, "EncodeTool")
enc_log_path = os.path.join(enc_prog_data_path, "log")
enc_output_path = os.path.join(enc_prog_data_path, "encoded_files")
enc_config_path = os.path.join(enc_prog_data_path, "config.json")
enc_desktop_output_path = os.path.join(desktop_path, "编码名单")

# ── 程序图标路径 ──
rct_icon_path = os.path.join(res_path, "icon", "rctool.ico")
enc_icon_path = os.path.join(res_path, "icon", "encode.ico")
rem_icon_path = os.path.join(res_path, "icon", "remove.ico")
