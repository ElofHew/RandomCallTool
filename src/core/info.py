"""
元数据存放模块
"""
# 导入OS模块以处理路径数据
from os import path as osp
from os import getcwd

# 通用
work_path = getcwd()
user_home_path = osp.expanduser("~")
desktop_path = osp.join(user_home_path, "Desktop")
document_path = osp.join(user_home_path, "Documents")
github = "https://github.com/ElofHew/RandomCallTool"
gitee = "https://gitee.com/ElofHew/RandomCallTool"

# 主程序
# 元数据
rct_appname = "RandomCallTool"
rct_version = "2.2"
rct_vercode = 2200
rct_author = "Dan_Evan"
rct_date = "2026-06-07"
rct_description = "一个基于Python + tkinter的随机抽取工具，支持随机抽组和随机抽人。"
# 全局变量
rct_prog_data_path = osp.join(work_path, "data")
# 数据文件
rct_log_path = osp.join(rct_prog_data_path, "log")
rct_result_path = osp.join(rct_prog_data_path, "result")
rct_config_path = osp.join(rct_prog_data_path, "config.json")
# 桌面输出路径
rct_desktop_result_path = osp.join(desktop_path, "随机抽取结果")

# 编码工具
# 元数据
enc_appname = "EncodeTool"
enc_version = "1.1"
enc_vercode = 1100
enc_author = "Dan_Evan"
enc_date = "2026-06-07"
enc_description = "一个为随机抽取工具-随机抽人生成配套RCP编码名单文件的工具。"
# 全局变量
enc_prog_data_path = osp.join(work_path, "data", "EncodeTool")
# 数据文件路径
enc_log_path = osp.join(enc_prog_data_path, "log")
enc_output_path = osp.join(enc_prog_data_path, "encoded_files")
enc_config_path = osp.join(enc_prog_data_path, "config_encode.json")
# 桌面输出路径
enc_desktop_output_path = osp.join(desktop_path, "编码名单")
