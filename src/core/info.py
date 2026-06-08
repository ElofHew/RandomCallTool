"""
项目全局路径与元数据常量
"""
import os

work_path = os.getcwd()
user_home_path = os.path.expanduser("~")
app_prog_data_path = os.path.join(work_path, "data")
app_local_data_path = os.path.join(user_home_path, ".randomcalltool")
desktop_path = os.path.join(user_home_path, "Desktop")
document_path = os.path.join(user_home_path, "Documents")
github = "https://github.com/ElofHew/RandomCallTool"
gitee = "https://gitee.com/ElofHew/RandomCallTool"

# ── 主程序 RandomCallTool ──
rct_appname = "RandomCallTool"
rct_version = "2.2"
rct_vercode = 2200
rct_author = "Dan_Evan"
rct_date = "2026-06-07"
rct_description = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"
rct_prog_data_path = app_prog_data_path
rct_log_path = os.path.join(rct_prog_data_path, "log")
rct_result_path = os.path.join(rct_prog_data_path, "result")
rct_config_path = os.path.join(rct_prog_data_path, "config.json")
rct_desktop_result_path = os.path.join(desktop_path, "随机抽取结果")
rct_rcplist_path = os.path.join(rct_prog_data_path, "rcplist")

# ── 编码工具 EncodeTool ──
enc_appname = "EncodeTool"
enc_version = "1.1"
enc_vercode = 1100
enc_author = "Dan_Evan"
enc_date = "2026-06-07"
enc_description = "一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。"
enc_prog_data_path = os.path.join(app_prog_data_path, "EncodeTool")
enc_log_path = os.path.join(enc_prog_data_path, "log")
enc_output_path = os.path.join(enc_prog_data_path, "encoded_files")
enc_config_path = os.path.join(enc_prog_data_path, "config.json")
enc_desktop_output_path = os.path.join(desktop_path, "编码名单")
