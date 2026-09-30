"""启动参数解析：--weight-set / -lib / -file。

用法示例：
  rctool.exe --weight-set "测试样本12" 20.00
  rctool.exe --weight-set "测试样本12" 20.00 -lib "测试样本文件"
  rctool.exe --weight-set "测试样本12" 20.00 -file "demo.txt"

名称均支持列表（JSON 风格，整体用单引号包裹）：
  rctool.exe --weight-set '["测试样本12","测试样本13"]' 20.00
  rctool.exe --weight-set "测试样本12" 20.00 -lib '["样本文件1","样本文件2"]'

语义：
  - --weight-set <名字> <权重>：设置一条权重，可重复出现；出现即开启自定义权重；
    名字支持列表，列表内各项设为同一权重；
  - 不指定目标：任何已加载样本中只要存在该名字即设置权重；
  - -lib <样本库名>：仅加载指定样本库样本时生效，可重复/列表；
  - -file <外部文件名或路径>：仅指定外部文件生效（可多个），
    启动时自动加载第一个存在的文件。

参数本身的任何错误（值非法、缺值、未知参数、列表格式错等）只记录到日志，
不弹前端界面；异常部分忽略，程序正常启动。
"""
import json
import math
from dataclasses import dataclass, field


@dataclass
class StartArgs:
    weight_sets: list = field(default_factory=list)   # [(name, weight), ...]
    target_libs: list = field(default_factory=list)
    target_files: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def has_rules(self):
        """是否具备可应用的权重规则"""
        return bool(self.weight_sets)


def parse_name_list(value, errors=None):
    """把参数值解析为名字列表：支持 ["a","b"] 列表形式，否则按单个名字。"""
    v = value.strip()
    if v.startswith("["):
        if not v.endswith("]"):
            # 列表未闭合：不按列表强行解析，原样作为单个名字并记录
            if errors is not None:
                errors.append("列表格式不正确（缺少右括号）：%s" % value)
            return [value] if value else []
        try:
            data = json.loads(v)
            if isinstance(data, list):
                return [str(x) for x in data if str(x)]
        except ValueError:
            pass
        # 容错：去掉方括号后按逗号分割，去除各项周围引号
        inner = v[1:-1].strip()
        if not inner:
            return []
        out = []
        for part in inner.split(","):
            p = part.strip()
            if len(p) >= 2 and p[0] in "\"'" and p[-1] == p[0]:
                p = p[1:-1]
            if p:
                out.append(p)
        return out
    return [value] if v else []


def parse_weight(wstr):
    """权重值 -> float；非法（非数字/负数/nan/inf）时返回 (None, 原因)。"""
    try:
        w = float(wstr)
    except (ValueError, TypeError):
        return None, "权重值无效：%s（需为数字）" % wstr
    if not math.isfinite(w):
        return None, "权重值无效：%s（不能为 nan/inf 等特殊值）" % wstr
    if w < 0:
        return None, "权重值无效：%s（不能为负数）" % wstr
    return w, None


def parse(argv):
    """把 argv（不含程序名）解析为 StartArgs。"""
    args = StartArgs()
    i = 0
    n = len(argv)

    def need(idx):
        if idx >= n:
            args.errors.append("参数不完整：缺少必要的值")
            return None
        return argv[idx]

    while i < n:
        token = argv[i]

        if token == "--weight-set":
            name_val = need(i + 1)
            wstr = need(i + 2)
            if name_val is None or wstr is None:
                break
            w, why = parse_weight(wstr)
            if w is None:
                args.errors.append(why)
                i += 3
                continue
            names = parse_name_list(name_val, args.errors)
            if not names:
                args.errors.append("权重名字为空，已跳过：%s" % name_val)
            for nm in names:
                args.weight_sets.append((nm, w))
            i += 3

        elif token in ("-lib", "--lib"):
            value = need(i + 1)
            if value is not None:
                vals = [x for x in parse_name_list(value, args.errors) if x]
                if not vals:
                    args.errors.append("-lib 未指定样本名，已跳过")
                args.target_libs.extend(vals)
            i += 2

        elif token in ("-file", "--file"):
            value = need(i + 1)
            if value is not None:
                vals = [x for x in parse_name_list(value, args.errors) if x]
                if not vals:
                    args.errors.append("-file 未指定文件名，已跳过")
                args.target_files.extend(vals)
            i += 2

        elif token in ("--custom-weight", "--point-sample"):
            # 旧参数已废弃：静默忽略；--custom-weight 后若带 enable/disable 一并消费
            j = i + 1
            if token == "--custom-weight" and j < n and argv[j] in ("enable", "disable"):
                i = j
            i += 1

        else:
            # 未知参数：记录到日志后忽略，避免影响正常启动
            args.errors.append("未知参数已忽略：%s" % token)
            i += 1

    return args
