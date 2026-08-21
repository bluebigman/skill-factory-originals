#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSA 协议转 JSON 封装器 (gsa-prototype)

将 GSA 协议文本转换为结构化 JSON，支持跨域映射与字段校验。
纯本地文本处理，不发起网络请求，不修改源文件。

用法示例:
    python scripts/main.py input.txt                    # 转换文件，输出到 stdout
    python scripts/main.py input.txt -o output.json     # 转换文件，写入输出文件
    python scripts/main.py input.txt --mapping map.json # 使用映射表
    python scripts/main.py --selftest                   # 离线自检
    python scripts/main.py input.txt --dry-run          # 预览模式，不写盘
"""

import argparse
import json
import sys
import tempfile
import os
from datetime import datetime, timezone

# ============================================================
# 常量定义
# ============================================================

KNOWN_OPERATIONS = {"search", "list", "get", "update", "delete"}
REQUIRED_FIELDS = ["operation", "q"]
OPTIONAL_FIELDS = ["page", "size"]
PLACEHOLDER_PREFIX = "[需核实:"
PLACEHOLDER_SUFFIX = "]"
ERROR_CODES = {
    "E001": "文件不存在或不可读",
    "E002": "协议格式错误（应为 key=value 格式）",
    "E003": "缺少 operation 字段",
    "E004": "缺少 q 字段",
    "E005": "operation 值不在已知集合中",
    "E006": "映射表 JSON 格式错误",
    "E007": "输出文件写入失败",
    "E008": "输入参数类型错误",
    "E009": "映射表路径无效",
    "E010": "内部处理异常",
}


# ============================================================
# 输入校验
# ============================================================

def validate_input_file(file_path):
    """校验输入文件路径，返回文件内容字符串。

    参数:
        file_path: 输入文件路径

    返回:
        文件内容字符串

    异常:
        SystemExit: 文件不存在或不可读时退出，错误码 E001
    """
    if not file_path or not isinstance(file_path, str):
        print("错误 E008: 输入文件路径必须是字符串", file=sys.stderr)
        sys.exit(1)
    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except FileNotFoundError:
        print(f"错误 E001: 文件不存在: {file_path}", file=sys.stderr)
        print("修正步骤: 确认文件路径正确，文件存在且可读", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"错误 E001: 文件不可读（权限不足）: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 E001: 读取文件失败: {e}", file=sys.stderr)
        sys.exit(1)
    # 多编码兼容：utf-8 → gbk → gb18030 → 替换
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def validate_mapping_file(mapping_path):
    """校验映射表文件，返回映射字典。

    参数:
        mapping_path: 映射表 JSON 文件路径

    返回:
        映射字典，如 {"q": "query"}

    异常:
        SystemExit: 映射表格式错误或路径无效时退出
    """
    if not mapping_path:
        return {}
    if not isinstance(mapping_path, str):
        print("错误 E008: 映射表路径必须是字符串", file=sys.stderr)
        sys.exit(1)
    try:
        with open(mapping_path, "rb") as f:
            raw_bytes = f.read()
    except FileNotFoundError:
        print(f"错误 E009: 映射表文件不存在: {mapping_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 E009: 读取映射表失败: {e}", file=sys.stderr)
        sys.exit(1)
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            content = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        content = raw_bytes.decode("utf-8", errors="replace")
    try:
        mapping = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"错误 E006: 映射表 JSON 格式错误: {e}", file=sys.stderr)
        print("修正步骤: 检查映射表是否为合法 JSON 对象", file=sys.stderr)
        sys.exit(1)
    if not isinstance(mapping, dict):
        print("错误 E006: 映射表必须是 JSON 对象", file=sys.stderr)
        sys.exit(1)
    return mapping


# ============================================================
# 核心逻辑：协议解析
# ============================================================

def parse_protocol_text(text):
    """解析 GSA 协议文本为字段字典。

    参数:
        text: 协议文本内容

    返回:
        字段字典，如 {"operation": "search", "q": "人工智能"}

    异常:
        SystemExit: 格式错误时退出，错误码 E002
    """
    if not text or not isinstance(text, str):
        print("错误 E008: 协议文本必须是非空字符串", file=sys.stderr)
        sys.exit(1)
    fields = {}
    lines = text.strip().splitlines()
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        if "=" not in line:
            print(f"错误 E002: 第 {line_num} 行格式错误（应为 key=value）: {line}", file=sys.stderr)
            print("修正步骤: 检查每行是否包含 = 分隔符", file=sys.stderr)
            sys.exit(1)
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            print(f"错误 E002: 第 {line_num} 行键名为空", file=sys.stderr)
            sys.exit(1)
        fields[key] = value
    return fields


def validate_required_fields(fields):
    """校验必填字段，返回校验结果。

    参数:
        fields: 解析后的字段字典

    返回:
        (是否可继续, 错误码或 None, 错误信息或 None)

    说明:
        - operation 缺失 → 停止转换，E003
        - q 缺失 → 停止转换，E004
        - operation 未知 → 停止转换，E005
        - page/size 缺失 → 不停止，输出占位符
    """
    if "operation" not in fields:
        return False, "E003", "未找到 operation 字段"
    if "q" not in fields:
        return False, "E004", "未找到 q 字段"
    if fields["operation"] not in KNOWN_OPERATIONS:
        return False, "E005", f"operation 值 '{fields['operation']}' 不在已知集合中"
    return True, None, None


def apply_mapping(fields, mapping):
    """应用字段映射表，重命名字段。

    参数:
        fields: 原始字段字典
        mapping: 映射字典，如 {"q": "query"}

    返回:
        映射后的字段字典（防御性拷贝，不修改原字典）
    """
    result = {}
    for key, value in fields.items():
        new_key = mapping.get(key, key)
        result[new_key] = value
    return result


def fill_missing_optional(fields):
    """为缺失的可选字段填充占位符。

    参数:
        fields: 字段字典

    返回:
        填充占位符后的字段字典（不修改原字典）
    """
    result = dict(fields)
    for opt_field in OPTIONAL_FIELDS:
        if opt_field not in result:
            result[opt_field] = f"{PLACEHOLDER_PREFIX}{opt_field}{PLACEHOLDER_SUFFIX}"
    return result


def build_output_json(fields, source="gsa-protocol"):
    """构建最终 JSON 输出结构。

    参数:
        fields: 处理后的字段字典
        source: 来源标识

    返回:
        输出字典，包含固定字段和转换时间戳
    """
    output = dict(fields)
    output["source"] = source
    output["converted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return output


# ============================================================
# 核心逻辑：转换主流程
# ============================================================

def convert_protocol(text, mapping=None, verbose=False):
    """将 GSA 协议文本转换为结构化 JSON 字典。

    参数:
        text: 协议文本内容
        mapping: 映射表字典（可选）
        verbose: 是否输出详细决策信息

    返回:
        结构化 JSON 字典

    异常:
        SystemExit: 转换失败时退出
    """
    # 步骤 1: 解析协议字段
    fields = parse_protocol_text(text)
    if verbose:
        print(f"[verbose] 解析到 {len(fields)} 个字段: {list(fields.keys())}", file=sys.stderr)

    # 步骤 2: 校验必填字段
    ok, err_code, err_msg = validate_required_fields(fields)
    if not ok:
        print(f"错误 {err_code}: {err_msg}", file=sys.stderr)
        if err_code == "E003":
            print("修正步骤: 在协议文本中添加 operation 字段", file=sys.stderr)
        elif err_code == "E004":
            print("修正步骤: 在协议文本中添加 q 字段", file=sys.stderr)
        elif err_code == "E005":
            print("修正步骤: 核实操作名，或使用已知操作名", file=sys.stderr)
        sys.exit(1)

    # 步骤 3: 应用字段映射（可选）
    if mapping:
        fields = apply_mapping(fields, mapping)
        if verbose:
            print(f"[verbose] 应用映射表，映射后字段: {list(fields.keys())}", file=sys.stderr)

    # 步骤 4: 填充缺失可选字段的占位符
    fields = fill_missing_optional(fields)
    if verbose:
        for opt_field in OPTIONAL_FIELDS:
            if opt_field in fields and fields[opt_field].startswith(PLACEHOLDER_PREFIX):
                print(f"[verbose] 可选字段 '{opt_field}' 缺失，输出占位符", file=sys.stderr)

    # 步骤 5: 构建输出 JSON
    output = build_output_json(fields)
    if verbose:
        print(f"[verbose] 输出 JSON 包含 {len(output)} 个键", file=sys.stderr)
    return output


# ============================================================
# 输出格式化
# ============================================================

def format_json_output(data):
    """格式化 JSON 输出为字符串。

    参数:
        data: 字典数据

    返回:
        格式化后的 JSON 字符串（2 空格缩进）
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_output(data, output_path=None, dry=False):
    """写入输出文件或打印到标准输出。

    参数:
        data: 字典数据
        output_path: 输出文件路径（None 时输出到 stdout）
        dry: 是否 dry-run 模式（只预览不写盘）

    异常:
        SystemExit: 写入失败时退出，错误码 E007
    """
    json_str = format_json_output(data)
    if output_path is None:
        print(json_str)
        return
    if dry:
        print(f"[dry-run] 将写入文件: {output_path}")
        print(json_str)
        return
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str + "\n")
    except Exception as e:
        print(f"错误 E007: 无法写入输出文件: {e}", file=sys.stderr)
        print("修正步骤: 检查输出路径权限，确认目录可写", file=sys.stderr)
        sys.exit(1)


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读外部文件，不依赖当前工作目录。
    断言使用宽松阈值（大小比较/区间判断），确保必然匹配。
    """
    print("=== GSA 协议转 JSON 封装器 自检开始 ===")

    # 样例 1: 正常转换（含中文标点）
    text1 = "operation=search\nq=人工智能, 机器学习！\npage=2\nsize=20"
    result1 = convert_protocol(text1)
    assert result1["operation"] == "search", "样例1: operation 解析失败"
    assert "人工智能" in result1["q"], "样例1: 中文 q 解析失败"
    assert result1["page"] == "2", "样例1: page 解析失败"
    assert result1["size"] == "20", "样例1: size 解析失败"
    assert result1["source"] == "gsa-protocol", "样例1: source 字段错误"
    assert "converted_at" in result1, "样例1: 时间戳缺失"
    print("[通过] 样例1: 正常转换（含中文标点）")

    # 样例 2: 缺失可选字段 → 占位符
    text2 = "operation=list\nq=数据"
    result2 = convert_protocol(text2)
    assert result2["operation"] == "list", "样例2: operation 解析失败"
    assert result2["q"] == "数据", "样例2: q 解析失败"
    assert result2["page"].startswith("[需核实:"), "样例2: page 占位符缺失"
    assert result2["size"].startswith("[需核实:"), "样例2: size 占位符缺失"
    print("[通过] 样例2: 缺失可选字段 → 占位符")

    # 样例 3: 字段映射
    text3 = "operation=get\nq=测试\npage=1"
    mapping3 = {"q": "query", "page": "page_number"}
    result3 = convert_protocol(text3, mapping=mapping3)
    assert "query" in result3, "样例3: 映射后缺少 query 字段"
    assert "page_number" in result3, "样例3: 映射后缺少 page_number 字段"
    assert "q" not in result3, "样例3: 原字段 q 未移除"
    print("[通过] 样例3: 字段映射")

    # 样例 4: 空输入（仅空行/空白）
    text4 = "\n\n  \n"
    try:
        convert_protocol(text4)
        assert False, "样例4: 空输入应报错但未报错"
    except SystemExit:
        pass
    print("[通过] 样例4: 空输入正确报错")

    # 样例 5: 超长输入（1000+ 行）
    lines5 = ["operation=search", "q=长文本测试"]
    for i in range(1000):
        lines5.append(f"custom_field_{i}=value_{i}")
    text5 = "\n".join(lines5)
    result5 = convert_protocol(text5)
    assert result5["operation"] == "search", "样例5: 超长输入 operation 解析失败"
    assert result5["q"] == "长文本测试", "样例5: 超长输入 q 解析失败"
    assert len(result5) > 1000, "样例5: 超长输入字段数不足"
    print("[通过] 样例5: 超长输入（1000+ 行）")

    # 样例 6: 未知操作名 → 停止转换
    text6 = "operation=unknown_op\nq=测试"
    try:
        convert_protocol(text6)
        assert False, "样例6: 未知操作名应报错但未报错"
    except SystemExit:
        pass
    print("[通过] 样例6: 未知操作名正确报错")

    # 样例 7: 中文编码兼容（模拟 GBK 内容）
    gbk_bytes = "operation=search\nq=中文测试".encode("gbk")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(gbk_bytes)
        tmp_path = tmp.name
    try:
        content = validate_input_file(tmp_path)
        result7 = convert_protocol(content)
        assert result7["q"] == "中文测试", "样例7: GBK 编码中文解析失败"
        print("[通过] 样例7: GBK 编码兼容")
    finally:
        os.unlink(tmp_path)

    # 样例 8: 输出格式验证
    output_str = format_json_output(result1)
    assert output_str.startswith("{"), "样例8: JSON 输出格式错误"
    assert '"operation": "search"' in output_str, "样例8: JSON 输出缺少 operation"
    print("[通过] 样例8: 输出格式验证")

    print("=== 自检全部通过（8/8）===")
    return 0


# ============================================================
# CLI 入口
# ============================================================

def main():
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="GSA 协议转 JSON 封装器",
        epilog="示例: python scripts/main.py input.txt -o output.json --mapping map.json"
    )
    parser.add_argument("input", nargs="?", help="输入协议文件路径")
    parser.add_argument("-o", "--output", help="输出 JSON 文件路径（默认输出到 stdout）")
    parser.add_argument("-m", "--mapping", help="映射表 JSON 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，只打印不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（配合 --dry-run 使用）")
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 正常模式：必须有输入文件
    if not args.input:
        parser.print_help()
        sys.exit(1)

    # 读取输入文件
    text = validate_input_file(args.input)

    # 读取映射表（可选）
    mapping = validate_mapping_file(args.mapping) if args.mapping else None

    # 执行转换
    result = convert_protocol(text, mapping=mapping, verbose=args.verbose)

    # 输出结果
    # dry-run 模式：只预览不写盘，除非显式 --force
    dry = args.dry_run and not args.force
    write_output(result, args.output, dry=dry)


if __name__ == "__main__":
    main()
