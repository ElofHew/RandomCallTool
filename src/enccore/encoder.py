import os
import glob
import binascii
from base64 import b64encode, b64decode
from core.logman import enclog


class ListEncoder:
    """名单编码器 — 支持 Base64 / Hex 编码方式"""

    @staticmethod
    def encode_list(text, method="base64"):
        """将文本编码为指定格式
        Args:
            text: 要编码的文本
            method: 编码方式 - "base64" 或 "hex"
        Returns:
            编码后的字符串
        """
        try:
            if not text or not text.strip():
                return ""

            # 标准化换行符并添加结尾换行符
            text = text.replace('\r\n', '\n').replace('\r', '\n').strip() + "\n"
            raw_bytes = text.encode('utf-8')

            if method == "hex":
                encoded_text = binascii.hexlify(raw_bytes).decode('ascii')
            else:  # base64
                encoded_text = b64encode(raw_bytes).decode('utf-8')

            enclog.info(
                f"编码成功 (方式={method}, "
                f"原始长度={len(text)}, "
                f"编码后长度={len(encoded_text)})"
            )
            return encoded_text

        except Exception as e:
            enclog.error(f"编码失败: {e}")
            raise

    @staticmethod
    def decode_list(encoded_text, method="base64"):
        """将编码后的文本解码
        Args:
            encoded_text: 编码后的字符串
            method: 解码方式 - "base64" 或 "hex"
        Returns:
            解码后的明文
        """
        try:
            if not encoded_text or not encoded_text.strip():
                return ""

            encoded_str = encoded_text.strip()

            if method == "hex":
                decoded_bytes = binascii.unhexlify(encoded_str)
            else:  # base64
                decoded_bytes = b64decode(encoded_str)

            decoded_text = decoded_bytes.decode('utf-8')
            return decoded_text.strip()

        except Exception as e:
            enclog.error(f"解码失败: {e}")
            raise

    @staticmethod
    def process_text(text, remove_duplicates=True, trim_spaces=True,
                     sort_names=False, ignore_empty_lines=True):
        """处理文本：去除重复项、空格、排序等
        Args:
            text: 原始文本
            remove_duplicates: 是否去除重复项
            trim_spaces: 是否去除首尾空格
            sort_names: 是否按字母排序
            ignore_empty_lines: 是否忽略空行
        Returns:
            处理后的文本
        """
        if not text:
            return ""

        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            if trim_spaces:
                line = line.strip()

            if ignore_empty_lines and not line:
                continue

            if line:
                processed_lines.append(line)

        # 去除重复项（保持顺序）
        if remove_duplicates:
            processed_lines = list(dict.fromkeys(processed_lines))

        # 排序
        if sort_names:
            processed_lines.sort(key=lambda x: x.lower())

        return '\n'.join(processed_lines)

    @staticmethod
    def detect_encoding(encoded_text):
        """智能检测编码方式
        Args:
            encoded_text: 编码后的文本
        Returns:
            检测到的编码方式 ("base64" / "hex")
        """
        text = encoded_text.strip()
        if not text:
            return "base64"

        # Hex 编码仅含 0-9 a-f
        hex_chars = set("0123456789abcdefABCDEF")
        if all(c in hex_chars for c in text):
            return "hex"
        return "base64"

    # ── 批量处理 ──────────────────────────────────────────────

    @staticmethod
    def encode_file(input_path, output_path, method="base64",
                    remove_duplicates=True, trim_spaces=True,
                    file_encoding="utf-8", sort_names=False):
        """编码单个文件并保存"""
        try:
            # 读取
            with open(input_path, 'r', encoding=file_encoding) as f:
                text = f.read()

            # 处理
            processed = ListEncoder.process_text(
                text,
                remove_duplicates=remove_duplicates,
                trim_spaces=trim_spaces,
                sort_names=sort_names
            )
            if not processed:
                enclog.warning(f"文件为空: {input_path}")
                return False

            # 编码
            encoded = ListEncoder.encode_list(processed, method=method)

            # 保存
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(encoded)

            enclog.info(f"文件编码完成: {input_path} -> {output_path}")
            return True

        except Exception as e:
            enclog.error(f"文件编码失败 [{input_path}]: {e}")
            return False

    @staticmethod
    def decode_file(input_path, output_path, method=None,
                    file_encoding="utf-8"):
        """解码单个文件并保存
        Args:
            method: None 表示自动检测
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                encoded = f.read()

            if method is None:
                method = ListEncoder.detect_encoding(encoded)

            decoded = ListEncoder.decode_list(encoded, method=method)

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, 'w', encoding=file_encoding) as f:
                f.write(decoded)

            enclog.info(f"文件解码完成: {input_path} -> {output_path}")
            return True

        except Exception as e:
            enclog.error(f"文件解码失败 [{input_path}]: {e}")
            return False

    @staticmethod
    def batch_encode_files(input_dir, output_dir, method="base64",
                           pattern="*.txt", **kwargs):
        """批量编码目录下所有匹配的文件"""
        matched = glob.glob(os.path.join(input_dir, pattern))
        if not matched:
            enclog.warning(f"未找到匹配文件: {input_dir}/{pattern}")
            return []

        results = []
        for src in matched:
            rel = os.path.relpath(src, input_dir)
            name_no_ext = os.path.splitext(rel)[0]
            dst = os.path.join(output_dir, name_no_ext + ".rcp")
            ok = ListEncoder.encode_file(src, dst, method=method, **kwargs)
            results.append((src, dst, ok))

        enclog.info(f"批量编码完成: {sum(1 for _, _, ok in results if ok)}/{len(results)}")
        return results

    @staticmethod
    def batch_decode_files(input_dir, output_dir, pattern="*.rcp",
                           method=None, file_encoding="utf-8"):
        """批量解码目录下所有匹配的文件"""
        matched = glob.glob(os.path.join(input_dir, pattern))
        if not matched:
            enclog.warning(f"未找到匹配文件: {input_dir}/{pattern}")
            return []

        results = []
        for src in matched:
            rel = os.path.relpath(src, input_dir)
            name_no_ext = os.path.splitext(rel)[0]
            dst = os.path.join(output_dir, name_no_ext + ".txt")
            ok = ListEncoder.decode_file(src, dst, method=method,
                                         file_encoding=file_encoding)
            results.append((src, dst, ok))

        enclog.info(f"批量解码完成: {sum(1 for _, _, ok in results if ok)}/{len(results)}")
        return results
