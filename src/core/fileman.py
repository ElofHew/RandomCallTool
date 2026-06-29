"""
文件管理器模块 - 目录操作、结果保存、Base64 解码、样本库管理
"""
import os
import re
from base64 import b64decode, b64encode
from time import strftime
from tkinter import messagebox
from core.logman import rctlog
from core.platutils import open_file_or_dir
from core.config import ConfigManager
from core.info import rct_result_path, rct_desktop_result_path, rct_log_path, rct_appname, rct_rcplist_path, github, gitee, res_path, official_website, rct_version

class FileManager:
    """文件管理器"""
    
    @staticmethod
    def get_result_path():
        """获取结果保存路径"""
        config = ConfigManager()
        if config.get("result_path", 0) == 1:
            save_dir = rct_desktop_result_path
        else:
            save_dir = rct_result_path
        
        if not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
        
        return save_dir
    
    @staticmethod
    def open_directory(path):
        """打开目录"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            open_file_or_dir(path)
            rctlog.info(f"打开目录: {path}")
            return True
        except Exception as e:
            rctlog.error(f"打开目录失败: {e}")
            messagebox.showerror("错误", f"无法打开目录: {e}")
            return False
    
    @staticmethod
    def open_log_file():
        """打开日志文件"""
        try:
            log_file = os.path.join(rct_log_path, f"{rct_appname}-{strftime('%Y-%m-%d')}.log")
            if os.path.exists(log_file):
                open_file_or_dir(log_file)
                rctlog.info("打开日志文件")
                return True
            else:
                messagebox.showinfo("提示", "今天的日志文件不存在")
                return False
        except Exception as e:
            rctlog.error(f"打开日志文件失败: {e}")
            messagebox.showerror("错误", f"无法打开日志文件: {e}")
            return False


class SaveResult:
    """保存结果功能模块"""
    def __init__(self):
        self.config = ConfigManager()
    
    def make_html(self, class_name, result, save_message=None, timestamp=None):
        """生成HTML结果
        Args:
            timestamp: 可选，显示在HTML中的时间字符串
        """
        if class_name == "RandomGroup":
            cname = "随机抽组"
        elif class_name == "RandomPerson":
            cname = "随机抽人"
        else:
            cname = "抽取结果"

        result_text = "<br>".join(result)
        current_time = timestamp or strftime('%Y-%m-%d %H:%M:%S')

        # 处理 tips 区域
        if save_message:
            tips_section = (
                '<div class="tips">\n'
                '            <p><strong>提示/说明</strong></p>\n'
                f'            <p style="font-size: 20px;">{save_message}</p>\n'
                "        </div>"
            )
        else:
            tips_section = ""

        # 从外置模板文件加载
        template_path = os.path.join(res_path, "htmltp.tpt")
        if os.path.isfile(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                raw = f.read()
        else:
            raw = "<html><body><h1>抽取结果 - {cname}</h1><p>{result_text}</p></body></html>"

        template = raw.format(
            cname=cname,
            current_time=current_time,
            result_text=result_text,
            result_count=len(result),
            tips_section=tips_section,
            version=rct_version,
            official=official_website,
            github=github,
            gitee=gitee,
        )
        return template
    
    def save_result(self, class_name, prefix, result, save_message="",
                    custom_timestamp=None):
        """保存结果
        Args:
            custom_timestamp: 可选 "YYYY-MM-DD HH:MM:SS"，用于文件名和 HTML 内的抽取时间
        """
        if not result:
            rctlog.warning(f"[{prefix}] 结果为空，跳过保存")
            return None

        try:
            save_dir = FileManager.get_result_path()
            if custom_timestamp:
                ts_file = custom_timestamp.replace("-", "").replace(" ", "_").replace(":", "")
                ts_display = custom_timestamp
            else:
                ts_file = strftime("%Y%m%d_%H%M%S")
                ts_display = strftime("%Y-%m-%d %H:%M:%S")
            file_path = os.path.join(save_dir, f"{prefix}_{ts_file}.html")

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.make_html(class_name, result, save_message, ts_display))
            
            rctlog.info(f"[{prefix}] 结果已保存到: {file_path}")
            messagebox.showinfo("成功", f"抽取结果已保存到:\n{file_path}")
            return file_path
            
        except Exception as e:
            rctlog.error(f"[{prefix}] 保存结果失败: {e}")
            messagebox.showwarning("错误", f"保存结果失败: {e}")
            return None

def base64decode(data=None):
    """Base64解码"""
    try:
        decoded = b64decode(data).decode('utf-8')
        rctlog.info("Base64解码成功")
        return decoded
    except Exception as e:
        rctlog.error(f"Base64解码失败: {e}")
        return ""


class SampleLibrary:
    """样本库管理器 — 管理 data/rcplist/ 下的 .rcp 样本文件"""

    _NAME_REGEX = re.compile(r'^[^\\/:*?"<>|]+$')

    @classmethod
    def ensure_dir(cls):
        os.makedirs(rct_rcplist_path, exist_ok=True)

    @classmethod
    def get_samples(cls):
        """返回 [(name, filepath), ...]，按修改时间降序"""
        cls.ensure_dir()
        items = []
        for f in os.listdir(rct_rcplist_path):
            if f.endswith(".rcp"):
                name = f[:-4]
                fp = os.path.join(rct_rcplist_path, f)
                mtime = os.path.getmtime(fp)
                items.append((name, fp, mtime))
        items.sort(key=lambda x: x[2], reverse=True)
        return [(n, p) for n, p, _ in items]

    @classmethod
    def validate_name(cls, name):
        """校验样本名是否合法，返回 (ok, 错误信息)"""
        if not name or not name.strip():
            return False, "样本名不能为空"
        if not cls._NAME_REGEX.match(name):
            return False, "样本名包含非法字符 (\\ / : * ? \" < > |)"
        if len(name) > 100:
            return False, "样本名过长（最多100字符）"
        return True, ""

    @classmethod
    def import_sample(cls, source_path, sample_name):
        """读取源文件 → 编码为 Base64 → 保存到 rcplist/{name}.rcp"""
        cls.ensure_dir()
        ok, err = cls.validate_name(sample_name)
        if not ok:
            raise ValueError(err)

        # 读取源文件（尝试多种编码）
        content = None
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030"):
            try:
                with open(source_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if content is None:
            raise UnicodeDecodeError("无法解码源文件", source_path, 0, 0, "")

        # 如果已经是 .rcp 则不解码，直接复制
        dest = os.path.join(rct_rcplist_path, f"{sample_name}.rcp")
        if source_path.endswith(".rcp"):
            import shutil
            shutil.copy2(source_path, dest)
            rctlog.info(f"样本已复制导入: {source_path} -> {dest}")
            return dest

        # 编码为 Base64 保存
        raw = content.encode("utf-8")
        encoded = b64encode(raw).decode("utf-8")
        with open(dest, "w", encoding="utf-8") as f:
            f.write(encoded)
        rctlog.info(f"样本已导入: {source_path} -> {dest}")
        return dest

    @classmethod
    def export_rcp(cls, sample_name, dest_dir):
        """导出 .rcp 文件到指定目录，返回目标路径"""
        cls.ensure_dir()
        src = os.path.join(rct_rcplist_path, f"{sample_name}.rcp")
        if not os.path.exists(src):
            raise FileNotFoundError(f"样本 {sample_name} 不存在")
        import shutil
        dest = os.path.join(dest_dir, f"{sample_name}.rcp")
        shutil.copy2(src, dest)
        rctlog.info(f"样本已导出 (.rcp): {src} -> {dest}")
        return dest

    @classmethod
    def export_txt(cls, sample_name, dest_dir, encoding="utf-8"):
        """解码并导出为 .txt 文件到指定目录，返回目标路径"""
        cls.ensure_dir()
        src = os.path.join(rct_rcplist_path, f"{sample_name}.rcp")
        if not os.path.exists(src):
            raise FileNotFoundError(f"样本 {sample_name} 不存在")
        with open(src, "r", encoding="utf-8") as f:
            encoded = f.read()
        decoded = base64decode(encoded)
        dest = os.path.join(dest_dir, f"{sample_name}.txt")
        with open(dest, "w", encoding=encoding) as f:
            f.write(decoded)
        rctlog.info(f"样本已导出 (.txt): {src} -> {dest}")
        return dest

    @classmethod
    def delete_sample(cls, sample_name):
        """删除样本文件"""
        fp = os.path.join(rct_rcplist_path, f"{sample_name}.rcp")
        if os.path.exists(fp):
            os.remove(fp)
            rctlog.info(f"样本已删除: {fp}")
            return True
        return False

    @classmethod
    def rename_sample(cls, old_name, new_name):
        """重命名样本"""
        ok, err = cls.validate_name(new_name)
        if not ok:
            raise ValueError(err)
        old_fp = os.path.join(rct_rcplist_path, f"{old_name}.rcp")
        new_fp = os.path.join(rct_rcplist_path, f"{new_name}.rcp")
        if not os.path.exists(old_fp):
            raise FileNotFoundError(f"样本 {old_name} 不存在")
        if os.path.exists(new_fp):
            raise FileExistsError(f"样本名 {new_name} 已存在")
        os.rename(old_fp, new_fp)
        rctlog.info(f"样本已重命名: {old_name} -> {new_name}")

    @classmethod
    def load_names(cls, sample_name):
        """加载指定样本的名字列表"""
        fp = os.path.join(rct_rcplist_path, f"{sample_name}.rcp")
        if not os.path.exists(fp):
            return []
        with open(fp, "r", encoding="utf-8") as f:
            encoded = f.read()
        decoded = base64decode(encoded)
        names = []
        for line in decoded.splitlines():
            line = line.strip()
            if line:
                names.append(line)
        return names
