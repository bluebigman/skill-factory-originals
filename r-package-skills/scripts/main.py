#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — R包技能 数据处理 结构化输出

独立实现脚本，依据功能规格重建，不依赖任何既有代码。
提供命令行处理入口与离线自检功能。
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

# 错误码定义
ERR_OK = 0
ERR_INPUT = "E001"      # 输入数据为空或格式错误
ERR_FILE = "E002"       # 文件读取失败
ERR_FORMAT = "E003"     # 数据格式无法解析
ERR_URL = "E004"        # URL 格式不合法
ERR_FIELD = "E005"      # 字段定义缺失或冲突
ERR_OUTPUT = "E006"     # 输出写入失败
ERR_SELFTEST = "E007"   # 自检失败
ERR_INTERNAL = "E008"   # 内部逻辑错误
ERR_ARGS = "E009"       # 参数错误
ERR_UNKNOWN = "E010"    # 未知错误


# ------------------------------------------------------------
# 核心数据模型
# ------------------------------------------------------------

class RPackageRecord:
    """单个 R 包的结构化记录"""

    def __init__(self, package_name="", version="", category="",
                 function_list=None, dependencies=None, doc_url="",
                 timestamp="", confidence=0.0):
        self.package_name = package_name
        self.version = version
        self.category = category
        self.function_list = function_list or []
        self.dependencies = dependencies or []
        self.doc_url = doc_url
        self.timestamp = timestamp
        self.confidence = confidence

    def to_dict(self):
        """转换为字典（JSON 友好）"""
        return {
            "package_name": self.package_name,
            "version": self.version,
            "category": self.category,
            "function_list": list(self.function_list),
            "dependencies": list(self.dependencies),
            "doc_url": self.doc_url,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data):
        """从字典构建记录"""
        if not isinstance(data, dict):
            raise ValueError("记录必须是字典")
        return cls(
            package_name=str(data.get("package_name", "")),
            version=str(data.get("version", "")),
            category=str(data.get("category", "")),
            function_list=list(data.get("function_list", [])),
            dependencies=list(data.get("dependencies", [])),
            doc_url=str(data.get("doc_url", "")),
            timestamp=str(data.get("timestamp", "")),
            confidence=float(data.get("confidence", 0.0)),
        )


# ------------------------------------------------------------
# 解析与提取逻辑
# ------------------------------------------------------------

def extract_key_values(text):
    """
    从文本中提取键值对信息。
    支持格式: "key: value" 或 "key=value"
    """
    if not text or not isinstance(text, str):
        return {}

    result = {}
    # 匹配 key: value 或 key=value
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*([^\n,;]+)")
    for match in pattern.finditer(text):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        if key and value:
            result[key] = value
    return result


def extract_r_package_info(text):
    """
    从文本中提取 R 包相关信息。
    识别包名、版本、依赖、函数列表等。
    """
    if not text or not isinstance(text, str):
        return None

    record = RPackageRecord()
    lower_text = text.lower()

    # 提取包名（常见模式）
    pkg_match = re.search(r"(?:package|pkg)\s*[:=]\s*([A-Za-z][A-Za-z0-9.]*)", text, re.IGNORECASE)
    if pkg_match:
        record.package_name = pkg_match.group(1)
    else:
        # 尝试从 "R包 xxx" 或 "xxx 包" 中提取
        pkg_match2 = re.search(r"(?:R包|包)\s*[：:]?\s*([A-Za-z][A-Za-z0-9.]*)", text)
        if pkg_match2:
            record.package_name = pkg_match2.group(1)

    # 提取版本号
    ver_match = re.search(r"(?:version|版本)\s*[:=]\s*([0-9]+[0-9.]*)", text, re.IGNORECASE)
    if ver_match:
        record.version = ver_match.group(1)

    # 提取分类
    cat_match = re.search(r"(?:category|分类)\s*[:=]\s*([^\n,;]+)", text, re.IGNORECASE)
    if cat_match:
        record.category = cat_match.group(1).strip()

    # 提取依赖包
    dep_match = re.search(r"(?:depends|依赖)\s*[:=]\s*([^\n]+)", text, re.IGNORECASE)
    if dep_match:
        deps = re.findall(r"[A-Za-z][A-Za-z0-9.]*", dep_match.group(1))
        record.dependencies = [d for d in deps if d.lower() not in ("r", "depends", "依赖")]

    # 提取函数列表
    func_match = re.search(r"(?:functions?|函数)\s*[:=]\s*([^\n]+)", text, re.IGNORECASE)
    if func_match:
        funcs = re.findall(r"[A-Za-z][A-Za-z0-9._]*", func_match.group(1))
        record.function_list = funcs

    # 提取文档 URL
    url_match = re.search(r"(?:url|文档|doc)\s*[:=]\s*(https?://[^\s]+)", text, re.IGNORECASE)
    if url_match:
        record.doc_url = url_match.group(1)

    # 时间戳
    record.timestamp = datetime.now().isoformat()

    # 置信度评估：至少识别出包名才算基本有效
    if record.package_name:
        base_conf = 0.5
        if record.version:
            base_conf += 0.2
        if record.function_list:
            base_conf += 0.2
        if record.dependencies:
            base_conf += 0.1
        record.confidence = min(0.95, base_conf)
    else:
        record.confidence = 0.1

    return record


def parse_csv_data(file_path):
    """解析 CSV 文件为记录列表"""
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 将 CSV 行转换为文本再解析
                text_parts = []
                for k, v in row.items():
                    if v and k:
                        text_parts.append(f"{k}: {v}")
                text = "\n".join(text_parts)
                rec = extract_r_package_info(text)
                if rec and rec.package_name:
                    records.append(rec)
    except FileNotFoundError:
        raise RuntimeError(f"{ERR_FILE}: 文件不存在: {file_path}")
    except Exception as e:
        raise RuntimeError(f"{ERR_FORMAT}: CSV 解析失败: {e}")
    return records


def parse_json_data(file_path):
    """解析 JSON 文件为记录列表"""
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    rec = RPackageRecord.from_dict(item)
                    records.append(rec)
        elif isinstance(data, dict):
            # 可能是单个记录或包含记录的对象
            if "records" in data and isinstance(data["records"], list):
                for item in data["records"]:
                    rec = RPackageRecord.from_dict(item)
                    records.append(rec)
            else:
                rec = RPackageRecord.from_dict(data)
                records.append(rec)
    except FileNotFoundError:
        raise RuntimeError(f"{ERR_FILE}: 文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{ERR_FORMAT}: JSON 解析失败: {e}")
    except Exception as e:
        raise RuntimeError(f"{ERR_FORMAT}: JSON 数据处理失败: {e}")
    return records


def parse_text_data(text):
    """解析直接粘贴的文本数据"""
    if not text or not text.strip():
        raise RuntimeError(f"{ERR_INPUT}: 输入文本为空")

    records = []
    # 按空行或换行分割为多个数据块
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        rec = extract_r_package_info(block)
        if rec and rec.package_name:
            records.append(rec)

    return records


def validate_url(url):
    """验证 URL 格式合法性"""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def process_input(source, input_type="text"):
    """
    统一入口：处理输入并返回记录列表

    参数:
        source: 输入内容（文本、文件路径或 URL）
        input_type: text / file / url
    """
    records = []

    if input_type == "text":
        records = parse_text_data(source)

    elif input_type == "file":
        if not os.path.isfile(source):
            raise RuntimeError(f"{ERR_FILE}: 文件不存在: {source}")
        ext = os.path.splitext(source)[1].lower()
        if ext == ".csv":
            records = parse_csv_data(source)
        elif ext == ".json":
            records = parse_json_data(source)
        elif ext == ".txt":
            with open(source, "r", encoding="utf-8") as f:
                text = f.read()
            records = parse_text_data(text)
        else:
            raise RuntimeError(f"{ERR_FORMAT}: 不支持的文件格式: {ext}")

    elif input_type == "url":
        # 注意：本技能不主动访问网络，仅做格式校验
        if not validate_url(source):
            raise RuntimeError(f"{ERR_URL}: URL 格式不合法: {source}")
        # URL 内容需由用户提供，这里仅返回占位记录
        rec = RPackageRecord(
            package_name="url_reference",
            doc_url=source,
            timestamp=datetime.now().isoformat(),
            confidence=0.3,
        )
        records.append(rec)

    else:
        raise RuntimeError(f"{ERR_ARGS}: 不支持的输入类型: {input_type}")

    return records


# ------------------------------------------------------------
# 输出格式化
# ------------------------------------------------------------

def format_output(records, output_format="json", fields=None):
    """
    按指定格式输出结果

    参数:
        records: 记录列表
        output_format: json / table / kv
        fields: 自定义字段列表（用于过滤输出）
    """
    if not records:
        return "[]" if output_format == "json" else ""

    # 字段过滤
    if fields:
        filtered = []
        for rec in records:
            d = rec.to_dict()
            fd = {k: d.get(k, "") for k in fields if k in d}
            filtered.append(fd)
        data_to_output = filtered
    else:
        data_to_output = [r.to_dict() for r in records]

    if output_format == "json":
        return json.dumps(data_to_output, ensure_ascii=False, indent=2)

    elif output_format == "table":
        # 生成简单表格
        if not data_to_output:
            return ""
        headers = list(data_to_output[0].keys())
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        for row in data_to_output:
            values = [str(row.get(h, "")) for h in headers]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    elif output_format == "kv":
        # 键值对格式
        lines = []
        for i, row in enumerate(data_to_output, 1):
            lines.append(f"--- Record {i} ---")
            for k, v in row.items():
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    else:
        raise RuntimeError(f"{ERR_OUTPUT}: 不支持的输出格式: {output_format}")


# ------------------------------------------------------------
# 批量处理
# ------------------------------------------------------------

def batch_process(inputs, input_type="text", output_format="json"):
    """批量处理多个输入"""
    all_records = []
    for inp in inputs:
        try:
            recs = process_input(inp, input_type)
            all_records.extend(recs)
        except RuntimeError as e:
            print(f"警告: 处理 '{inp}' 时出错: {e}", file=sys.stderr)
    return format_output(all_records, output_format)


# ------------------------------------------------------------
# 自检功能
# ------------------------------------------------------------

def run_selftest():
    """内置硬编码样例数据的离线自检"""
    print("=== 自检开始 ===")

    # 测试 1: 文本解析
    test_text = """
    package: dplyr
    version: 1.1.0
    分类: 数据处理
    依赖: rlang, tibble, tidyselect
    函数: filter, select, mutate, summarise
    url: https://dplyr.tidyverse.org/
    """
    try:
        records = parse_text_data(test_text)
        assert len(records) > 0, "文本解析应至少产生一条记录"
        rec = records[0]
        assert rec.package_name == "dplyr", f"包名应为 dplyr, 实际: {rec.package_name}"
        assert rec.version == "1.1.0", f"版本应为 1.1.0, 实际: {rec.version}"
        assert len(rec.function_list) >= 3, f"函数列表应至少3个, 实际: {len(rec.function_list)}"
        assert rec.confidence > 0.5, f"置信度应大于0.5, 实际: {rec.confidence}"
        print("✔ 测试1 (文本解析) 通过")
    except AssertionError as e:
        print(f"✘ 测试1 失败: {e}")
        return False
    except Exception as e:
        print(f"✘ 测试1 异常: {e}")
        return False

    # 测试 2: JSON 序列化/反序列化
    try:
        rec = RPackageRecord(
            package_name="ggplot2",
            version="3.4.0",
            category="可视化",
            function_list=["ggplot", "aes", "geom_point"],
            dependencies=["scales", "tibble"],
            doc_url="https://ggplot2.tidyverse.org/",
            confidence=0.85,
        )
        d = rec.to_dict()
        rec2 = RPackageRecord.from_dict(d)
        assert rec2.package_name == "ggplot2", "JSON 往返后包名应一致"
        assert len(rec2.function_list) == 3, "函数列表长度应一致"
        assert rec2.confidence > 0.8, "置信度应大于0.8"
        print("✔ 测试2 (JSON序列化) 通过")
    except AssertionError as e:
        print(f"✘ 测试2 失败: {e}")
        return False
    except Exception as e:
        print(f"✘ 测试2 异常: {e}")
        return False

    # 测试 3: 输出格式
    try:
        records = [rec]
        json_out = format_output(records, "json")
        parsed = json.loads(json_out)
        assert len(parsed) == 1, "JSON 输出应有1条记录"

        table_out = format_output(records, "table")
        assert "|" in table_out, "表格输出应包含竖线分隔符"

        kv_out = format_output(records, "kv")
        assert "package_name: ggplot2" in kv_out, "键值输出应包含包名"
        print("✔ 测试3 (输出格式) 通过")
    except AssertionError as e:
        print(f"✘ 测试3 失败: {e}")
        return False
    except Exception as e:
        print(f"✘ 测试3 异常: {e}")
        return False

    # 测试 4: URL 验证
    try:
        assert validate_url("https://cran.r-project.org/") == True, "合法URL应返回True"
        assert validate_url("not-a-url") == False, "非法URL应返回False"
        print("✔ 测试4 (URL验证) 通过")
    except AssertionError as e:
        print(f"✘ 测试4 失败: {e}")
        return False

    # 测试 5: 批量处理
    try:
        inputs = [
            "package: tidyr\nversion: 1.3.0\n函数: pivot_longer, pivot_wider",
            "package: purrr\nversion: 1.0.0\n函数: map, reduce",
        ]
        result = batch_process(inputs, "text", "json")
        parsed = json.loads(result)
        assert len(parsed) == 2, f"批量处理应有2条记录, 实际: {len(parsed)}"
        names = [r["package_name"] for r in parsed]
        assert "tidyr" in names and "purrr" in names, "应包含 tidyr 和 purrr"
        print("✔ 测试5 (批量处理) 通过")
    except AssertionError as e:
        print(f"✘ 测试5 失败: {e}")
        return False
    except Exception as e:
        print(f"✘ 测试5 异常: {e}")
        return False

    # 测试 6: 错误处理
    try:
        try:
            parse_text_data("")
            assert False, "空文本应抛出异常"
        except RuntimeError:
            pass  # 预期行为

        try:
            process_input("/nonexistent/file.csv", "file")
            assert False, "不存在的文件应抛出异常"
        except RuntimeError:
            pass  # 预期行为

        print("✔ 测试6 (错误处理) 通过")
    except AssertionError as e:
        print(f"✘ 测试6 失败: {e}")
        return False
    except Exception as e:
        print(f"✘ 测试6 异常: {e}")
        return False

    print("=== 全部自检通过 ===")
    return True


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="R包技能 数据处理 结构化输出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --text "package: dplyr, version: 1.1.0" --format json
  python main.py --file data.csv --format table
  python main.py --batch a.txt b.txt --input-type text
  python main.py --selftest
        """,
    )

    # 输入方式（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", help="直接输入的文本数据")
    input_group.add_argument("--file", help="输入文件路径 (CSV/JSON/TXT)")
    input_group.add_argument("--url", help="URL 链接（仅校验格式）")
    input_group.add_argument("--batch", nargs="+", help="批量处理多个输入")
    input_group.add_argument("--selftest", action="store_true", help="运行离线自检")

    # 其他参数
    parser.add_argument("--input-type", choices=["text", "file", "url"],
                        default="text", help="输入类型（默认: text）")
    parser.add_argument("--format", choices=["json", "table", "kv"],
                        default="json", help="输出格式（默认: json）")
    parser.add_argument("--fields", nargs="+",
                        help="自定义输出字段（如 --fields package_name version）")
    parser.add_argument("--output", "-o", help="输出文件路径（默认输出到 stdout）")

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            success = run_selftest()
            sys.exit(0 if success else 1)

        # 检查是否提供了输入
        if not (args.text or args.file or args.url or args.batch):
            parser.print_help()
            print(f"\n{ERR_ARGS}: 请提供输入数据（--text/--file/--url/--batch）或使用 --selftest", file=sys.stderr)
            sys.exit(1)

        # 处理输入
        result = ""

        if args.batch:
            # 批量模式
            result = batch_process(args.batch, args.input_type, args.format)
        else:
            # 单输入模式
            if args.text:
                records = process_input(args.text, "text")
            elif args.file:
                records = process_input(args.file, "file")
            elif args.url:
                records = process_input(args.url, "url")
            else:
                raise RuntimeError(f"{ERR_ARGS}: 未识别的输入参数")

            result = format_output(records, args.format, args.fields)

        # 输出结果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"结果已写入: {args.output}")
        else:
            print(result)

        return 0

    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"{ERR_UNKNOWN}: 未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
