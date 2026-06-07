from base64 import b64encode, b64decode
from core.logman import enclog

class ListEncoder:
    """名单编码器"""
    
    @staticmethod
    def encode_list(text):
        """将文本编码为Base64格式"""
        try:
            # 如果文本为空，返回空字符串
            if not text or not text.strip():
                return ""
            
            # 标准化换行符并添加结尾换行符
            text = text.replace('\r\n', '\n').replace('\r', '\n').strip() + "\n"
            
            # Base64编码
            encoded_bytes = b64encode(text.encode('utf-8'))
            encoded_text = encoded_bytes.decode('utf-8')
            
            enclog.info(f"成功编码名单，原始长度: {len(text)}，编码后长度: {len(encoded_text)}")
            return encoded_text
            
        except Exception as e:
            enclog.error(f"编码失败: {e}")
            raise
    
    @staticmethod
    def decode_list(encoded_text):
        """将Base64格式解码为文本"""
        try:
            if not encoded_text or not encoded_text.strip():
                return ""
            
            # Base64解码
            decoded_bytes = b64decode(encoded_text)
            decoded_text = decoded_bytes.decode('utf-8')
            
            return decoded_text.strip()
            
        except Exception as e:
            enclog.error(f"解码失败: {e}")
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
            
            if line:  # 跳过空行
                processed_lines.append(line)
        
        # 去除重复项
        if remove_duplicates:
            processed_lines = list(dict.fromkeys(processed_lines))  # 保持顺序
        
        return '\n'.join(processed_lines)
