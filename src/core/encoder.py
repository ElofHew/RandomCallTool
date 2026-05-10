"""
名单编码/解码器
"""
import logging
from base64 import b64encode, b64decode

logger = logging.getLogger(__name__)


class ListEncoder:
    @staticmethod
    def encode_list(text):
        """将文本编码为Base64格式"""
        try:
            if not text or not text.strip():
                return ""
            # 标准化换行符并添加结尾换行符
            text = text.replace('\r\n', '\n').replace('\r', '\n').strip() + "\n"
            encoded_bytes = b64encode(text.encode('utf-8'))
            encoded_text = encoded_bytes.decode('utf-8')
            logger.info(f"成功编码名单，原始长度: {len(text)}，编码后长度: {len(encoded_text)}")
            return encoded_text
        except Exception as e:
            logger.error(f"编码失败: {e}")
            raise

    @staticmethod
    def decode_list(encoded_text):
        """将Base64格式解码为文本"""
        try:
            if not encoded_text or not encoded_text.strip():
                return ""
            decoded_bytes = b64decode(encoded_text)
            decoded_text = decoded_bytes.decode('utf-8')
            return decoded_text.strip()
        except Exception as e:
            logger.error(f"解码失败: {e}")
            raise

    @staticmethod
    def process_text(text, remove_duplicates=True, trim_spaces=True):
        """处理文本：去除重复项和空格"""
        if not text:
            return ""
        lines = text.split('\n')
        processed_lines = []
        for line in lines:
            if trim_spaces:
                line = line.strip()
            if line:
                processed_lines.append(line)
        if remove_duplicates:
            # 保持顺序去重
            seen = set()
            unique_lines = []
            for line in processed_lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            processed_lines = unique_lines
        return '\n'.join(processed_lines)