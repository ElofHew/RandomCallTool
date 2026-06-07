import os
from core.logman import enclog
from core.info import enc_prog_data_path, enc_output_path, enc_log_path

def init_dir():
    try:
        for path in [enc_prog_data_path, enc_output_path, enc_log_path]:
            os.makedirs(path, exist_ok=True)
    except Exception as e:
        enclog.error(f"创建目录失败: {e}")
