#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glowstick — 实时 OpenGL 绘图 Skill（纯逻辑实现）

本脚本仅实现功能规格中描述的"输入解析与结构化输出"能力，
不执行任何实际的 OpenGL 渲染。支持文件、URL、原始数据三种输入方式。

用法示例:
    python scripts/main.py --input "1,2,3,4,5"
    python scripts/main.py --file data.csv
    python scripts/main.py --url https://example.com/data.json
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INVALID_ARGS = "E001"      # 参数错误
ERR_FILE_NOT_FOUND = "E002"    # 文件不存在
ERR_FILE_READ = "E003"         # 文件读取失败
ERR_URL_FETCH = "E004"         # URL 获取失败
ERR_PARSE = "E005"             # 数据解析失败
ERR_EMPTY_DATA = "E006"        # 无有效数据
ERR_UNSUPPORTED = "E007"       # 不支持的格式
ERR_SELFTEST = "E008"          # 自检失败
ERR_OUTPUT = "E009"            # 输出失败
ERR_INTERNAL = "E010"          # 内部错误


# ============================================================
# 核心数据结构
# ============================================================

class ChartData:
    """图表数据容器，保存解析后的结构化数据。"""
    
    def __init__(self) -> None:
        self.values: List[float] = []          # 数值序列
        self.timestamps: List[str] = []        # 时间戳（可选）
        self.labels: List[str] = []            # 标签（可选）
        self.source_type: str = "raw"          # 数据来源类型: raw/file/url
        self.confidence: float = 1.0           # 整体置信度 0-1
        self.field_confidence: Dict[str, float] = {}  # 各字段置信度
        self.metadata: Dict[str, Any] = {}     # 额外元数据


# ============================================================
# 输入解析模块
# ============================================================

def parse_raw_data(text: str) -> ChartData:
    """
    解析原始文本数据。
    
    支持格式：
    - 逗号/空格/制表符分隔的数字序列: "1,2,3,4"
    - 每行一个数字: "1\n2\n3\n4"
    - 带时间戳的日志行: "2024-01-01 10:00:00 42.5"
    - JSON 数组: [1, 2, 3] 或 [{"value": 1}, {"value": 2}]
    - 键值对行: "key=value"
    
    返回: ChartData 对象
    """
    data = ChartData()
    text = text.strip()
    
    if not text:
        raise ValueError(ERR_EMPTY_DATA)
    
    # 尝试 JSON 解析
    if text.startswith('[') or text.startswith('{'):
        try:
            return _parse_json_data(text, data)
        except (json.JSONDecodeError, ValueError):
            # JSON 解析失败，回退到文本解析
            pass
    
    # 按行解析
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    if not lines:
        raise ValueError(ERR_EMPTY_DATA)
    
    # 单行情况：尝试分隔符分割
    if len(lines) == 1:
        _parse_single_line(lines[0], data)
    else:
        _parse_multi_line(lines, data)
    
    if not data.values:
        raise ValueError(ERR_PARSE)
    
    return data


def _parse_json_data(text: str, data: ChartData) -> ChartData:
    """解析 JSON 格式数据。"""
    parsed = json.loads(text)
    
    # 纯数字数组
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, (int, float)):
                data.values.append(float(item))
            elif isinstance(item, dict) and "value" in item:
                val = item["value"]
                if isinstance(val, (int, float)):
                    data.values.append(float(val))
                    if "timestamp" in item:
                        data.timestamps.append(str(item["timestamp"]))
                    if "label" in item:
                        data.labels.append(str(item["label"]))
    
    # 对象格式 {"values": [...], "timestamps": [...]}
    elif isinstance(parsed, dict):
        if "values" in parsed and isinstance(parsed["values"], list):
            data.values = [float(v) for v in parsed["values"] if isinstance(v, (int, float))]
        if "timestamps" in parsed and isinstance(parsed["timestamps"], list):
            data.timestamps = [str(t) for t in parsed["timestamps"]]
        if "labels" in parsed and isinstance(parsed["labels"], list):
            data.labels = [str(l) for l in parsed["labels"]]
    
    if not data.values:
        raise ValueError(ERR_PARSE)
    
    data.source_type = "raw"
    data.confidence = 0.95
    data.field_confidence = {
        "values": 1.0,
        "timestamps": 0.9 if data.timestamps else 0.0,
        "labels": 0.9 if data.labels else 0.0
    }
    return data


def _parse_single_line(line: str, data: ChartData) -> None:
    """解析单行数据（尝试多种分隔符）。"""
    # 尝试逗号分割
    for sep in [",", "\t", ";", "|", " "]:
        parts = [p.strip() for p in line.split(sep) if p.strip()]
        if len(parts) >= 1 and all(_is_number(p) for p in parts):
            data.values = [float(p) for p in parts]
            data.source_type = "raw"
            data.confidence = 0.9
            data.field_confidence = {"values": 1.0}
            return
    
    # 尝试键值对格式: key=value
    if "=" in line:
        pairs = [p for p in line.split(",") if "=" in p]
        if pairs:
            for pair in pairs:
                key, _, val = pair.partition("=")
                if _is_number(val.strip()):
                    data.values.append(float(val.strip()))
                    data.labels.append(key.strip())
            if data.values:
                data.source_type = "raw"
                data.confidence = 0.85
                data.field_confidence = {"values": 0.9, "labels": 0.9}
                return
    
    # 尝试时间戳+数值格式
    parts = line.split()
    if len(parts) >= 2:
        # 检查是否前部分是时间戳
        timestamp = " ".join(parts[:-1])
        last = parts[-1]
        if _is_number(last):
            try:
                # 尝试解析时间戳
                datetime.fromisoformat(timestamp.replace("T", " "))
                data.values.append(float(last))
                data.timestamps.append(timestamp)
                data.source_type = "raw"
                data.confidence = 0.8
                data.field_confidence = {
                    "values": 1.0,
                    "timestamps": 0.9
                }
                return
            except ValueError:
                pass
    
    raise ValueError(ERR_PARSE)


def _parse_multi_line(lines: List[str], data: ChartData) -> None:
    """解析多行数据。"""
    # 检查是否所有行都是纯数字
    if all(_is_number(line) for line in lines):
        data.values = [float(line) for line in lines]
        data.source_type = "raw"
        data.confidence = 0.95
        data.field_confidence = {"values": 1.0}
        return
    
    # 检查是否是 CSV 格式（有表头）
    if len(lines) > 1 and "," in lines[0]:
        header = [h.strip().lower() for h in lines[0].split(",")]
        # 检查是否有值列（value, val, y 等）
        val_idx = -1
        for i, h in enumerate(header):
            if h in ["value", "val", "y", "values", "data"]:
                val_idx = i
                break
        
        if val_idx >= 0:
            # 解析数据行
            for line in lines[1:]:
                cols = [c.strip() for c in line.split(",")]
                if len(cols) > val_idx and _is_number(cols[val_idx]):
                    data.values.append(float(cols[val_idx]))
                    # 尝试解析其他列
                    if len(cols) > 0:
                        first_col = cols[0]
                        if first_col != cols[val_idx]:  # 第一列不是值列
                            try:
                                datetime.fromisoformat(first_col.replace("T", " "))
                                data.timestamps.append(first_col)
                            except ValueError:
                                data.labels.append(first_col)
            
            if data.values:
                data.source_type = "raw"
                data.confidence = 0.9
                data.field_confidence = {
                    "values": 1.0,
                    "timestamps": 0.8 if data.timestamps else 0.0,
                    "labels": 0.8 if data.labels else 0.0
                }
                return
    
    # 尝试逐行解析（时间戳+数值格式）
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            # 尝试最后部分是数字
            if _is_number(parts[-1]):
                # 检查时间戳
                timestamp = " ".join(parts[:-1])
                try:
                    datetime.fromisoformat(timestamp.replace("T", " "))
                    data.values.append(float(parts[-1]))
                    data.timestamps.append(timestamp)
                except ValueError:
                    # 如果不是时间戳，尝试键值对格式
                    if "=" in line:
                        key, _, val = line.partition("=")
                        if _is_number(val.strip()):
                            data.values.append(float(val.strip()))
                            data.labels.append(key.strip())
    
    if not data.values:
        raise ValueError(ERR_PARSE)


def _is_number(s: str) -> bool:
    """判断字符串是否为数字。"""
    try:
        float(s)
        return True
    except ValueError:
        return False


def read_file(filepath: str) -> ChartData:
    """从文件读取数据。"""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(ERR_FILE_NOT_FOUND)
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        raise IOError(f"{ERR_FILE_READ}: {str(e)}")
    
    data = parse_raw_data(content)
    data.source_type = "file"
    data.metadata["filepath"] = filepath
    return data


def read_url(url: str) -> ChartData:
    """从 URL 读取数据。"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8")
    except Exception as e:
        raise ConnectionError(f"{ERR_URL_FETCH}: {str(e)}")
    
    data = parse_raw_data(content)
    data.source_type = "url"
    data.metadata["url"] = url
    return data


# ============================================================
# 结构化输出模块
# ============================================================

def to_json(data: ChartData) -> str:
    """将 ChartData 转为 JSON 字符串。"""
    output = {
        "source_type": data.source_type,
        "confidence": data.confidence,
        "field_confidence": data.field_confidence,
        "data": {
            "values": data.values,
            "timestamps": data.timestamps if data.timestamps else None,
            "labels": data.labels if data.labels else None
        },
        "metadata": data.metadata
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def to_yaml(data: ChartData) -> str:
    """将 ChartData 转为 YAML 格式字符串（简化实现）。"""
    lines = []
    lines.append(f"source_type: {data.source_type}")
    lines.append(f"confidence: {data.confidence}")
    lines.append("field_confidence:")
    for k, v in data.field_confidence.items():
        lines.append(f"  {k}: {v}")
    lines.append("data:")
    lines.append("  values:")
    for v in data.values:
        lines.append(f"    - {v}")
    if data.timestamps:
        lines.append("  timestamps:")
        for t in data.timestamps:
            lines.append(f"    - \"{t}\"")
    if data.labels:
        lines.append("  labels:")
        for l in data.labels:
            lines.append(f"    - \"{l}\"")
    if data.metadata:
        lines.append("metadata:")
        for k, v in data.metadata.items():
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


# ============================================================
# 批量处理模块
# ============================================================

def batch_process(inputs: List[Dict[str, str]], format: str = "json") -> List[str]:
    """
    批量处理多个输入。
    
    参数:
        inputs: 输入列表，每个元素为 {"type": "raw"/"file"/"url", "data": "..."}
        format: 输出格式 "json" 或 "yaml"
    
    返回: 处理结果字符串列表
    """
    results = []
    for item in inputs:
        input_type = item.get("type", "raw")
        input_data = item.get("data", "")
        
        try:
            if input_type == "file":
                data = read_file(input_data)
            elif input_type == "url":
                data = read_url(input_data)
            else:
                data = parse_raw_data(input_data)
            
            if format == "yaml":
                results.append(to_yaml(data))
            else:
                results.append(to_json(data))
        except Exception as e:
            results.append(json.dumps({
                "error": str(e),
                "input": input_data
            }, ensure_ascii=False))
    
    return results


# ============================================================
# 自检模块
# ============================================================

def selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据验证核心功能。
    不依赖外部文件、网络或当前工作目录。
    
    返回: True 表示全部通过，False 表示存在失败
    """
    print("=" * 60)
    print("glowstick 自检开始")
    print("=" * 60)
    
    all_passed = True
    
    # 测试1: 解析逗号分隔数字
    print("\n[测试1] 逗号分隔数字解析")
    try:
        data = parse_raw_data("1,2,3,4,5")
        assert len(data.values) == 5, "数值数量应为5"
        assert all(isinstance(v, float) for v in data.values), "应为浮点数"
        assert abs(sum(data.values) - 15.0) < 0.001, "总和应约为15"
        assert data.confidence > 0.5, "置信度应较高"
        print(f"  通过: 解析到 {len(data.values)} 个数值, 总和={sum(data.values):.1f}")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试2: 解析多行数字
    print("\n[测试2] 多行数字解析")
    try:
        data = parse_raw_data("10\n20\n30\n40")
        assert len(data.values) == 4, "数值数量应为4"
        assert max(data.values) == 40.0, "最大值应为40"
        assert min(data.values) == 10.0, "最小值应为10"
        print(f"  通过: 范围 [{min(data.values)}, {max(data.values)}]")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试3: JSON 数组解析
    print("\n[测试3] JSON 数组解析")
    try:
        data = parse_raw_data('[{"value": 1, "label": "A"}, {"value": 2, "label": "B"}]')
        assert len(data.values) == 2, "应有2个数值"
        assert len(data.labels) == 2, "应有2个标签"
        assert data.labels[0] == "A", "第一个标签应为A"
        print(f"  通过: 2个数据点, 标签={data.labels}")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试4: 时间戳数据解析
    print("\n[测试4] 时间戳数据解析")
    try:
        data = parse_raw_data("2024-01-01 10:00:00 42.5")
        assert len(data.values) == 1, "应有1个数值"
        assert len(data.timestamps) == 1, "应有1个时间戳"
        assert abs(data.values[0] - 42.5) < 0.001, "数值应为42.5"
        print(f"  通过: 时间戳={data.timestamps[0]}, 值={data.values[0]}")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试5: 空数据错误处理
    print("\n[测试5] 空数据错误处理")
    try:
        parse_raw_data("")
        all_passed = False
        print("  失败: 空数据应抛出异常")
    except ValueError as e:
        assert str(e) == ERR_EMPTY_DATA, f"错误码应为 {ERR_EMPTY_DATA}"
        print(f"  通过: 正确抛出 {ERR_EMPTY_DATA}")
    
    # 测试6: JSON 输出格式
    print("\n[测试6] JSON 输出格式")
    try:
        data = parse_raw_data("1,2,3")
        output = to_json(data)
        parsed = json.loads(output)
        assert "data" in parsed, "输出应包含data字段"
        assert "values" in parsed["data"], "data应包含values"
        assert len(parsed["data"]["values"]) == 3, "应有3个值"
        print(f"  通过: 输出JSON有效, 包含 {len(parsed['data']['values'])} 个值")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试7: YAML 输出格式
    print("\n[测试7] YAML 输出格式")
    try:
        data = parse_raw_data("5,6,7")
        output = to_yaml(data)
        assert "values:" in output, "应包含values字段"
        assert "source_type: raw" in output, "应包含source_type"
        print(f"  通过: YAML输出包含 {len(data.values)} 个值")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试8: 批量处理
    print("\n[测试8] 批量处理")
    try:
        inputs = [
            {"type": "raw", "data": "1,2,3"},
            {"type": "raw", "data": "4,5,6"}
        ]
        results = batch_process(inputs)
        assert len(results) == 2, "应有2个结果"
        for r in results:
            parsed = json.loads(r)
            assert "data" in parsed, "每个结果应包含data"
        print(f"  通过: 批量处理 {len(results)} 个输入")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试9: 文件处理（使用临时文件）
    print("\n[测试9] 文件处理（临时文件）")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("value\n1\n2\n3\n")
            temp_path = f.name
        try:
            data = read_file(temp_path)
            assert len(data.values) == 3, f"应有3个值, 实际{len(data.values)}"
            assert data.source_type == "file", "来源应为file"
            print(f"  通过: 从文件读取 {len(data.values)} 个值")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试10: 键值对解析
    print("\n[测试10] 键值对解析")
    try:
        data = parse_raw_data("A=10, B=20, C=30")
        assert len(data.values) == 3, "应有3个值"
        assert len(data.labels) == 3, "应有3个标签"
        assert data.labels[0] == "A", "第一个标签应为A"
        print(f"  通过: 标签={data.labels}, 值={data.values}")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 测试11: 错误码验证
    print("\n[测试11] 错误码验证")
    try:
        # 文件不存在
        try:
            read_file("/nonexistent/path/file.csv")
            all_passed = False
            print("  失败: 文件不存在应抛出异常")
        except FileNotFoundError as e:
            assert str(e) == ERR_FILE_NOT_FOUND, f"错误码应为 {ERR_FILE_NOT_FOUND}"
        
        # 无法解析的数据
        try:
            parse_raw_data("abc def ghi")
            all_passed = False
            print("  失败: 无法解析的数据应抛出异常")
        except ValueError as e:
            assert str(e) == ERR_PARSE, f"错误码应为 {ERR_PARSE}"
        
        print("  通过: 错误码验证成功")
    except Exception as e:
        all_passed = False
        print(f"  失败: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✅")
    else:
        print("自检存在失败 ❌")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数。"""
    parser = argparse.ArgumentParser(
        description="glowstick — 实时 OpenGL 绘图数据解析工具",
        epilog="示例: python main.py --input '1,2,3,4' | python main.py --file data.csv"
    )
    
    # 输入方式（三选一）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", "-i", type=str, help="原始数据字符串")
    input_group.add_argument("--file", "-f", type=str, help="输入文件路径")
    input_group.add_argument("--url", "-u", type=str, help="输入 URL")
    
    # 输出选项
    parser.add_argument("--format", "-fmt", choices=["json", "yaml"], default="json",
                        help="输出格式 (默认: json)")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（可选）")
    
    # 批量处理
    parser.add_argument("--batch", type=str, help="批量处理 JSON 文件路径")
    
    # 自检
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return 0 if selftest() else 1
    
    try:
        # 批量处理模式
        if args.batch:
            with open(args.batch, "r", encoding="utf-8") as f:
                batch_inputs = json.load(f)
            results = batch_process(batch_inputs, args.format)
            output = "\n---\n".join(results)
        else:
            # 单次处理
            if args.input:
                data = parse_raw_data(args.input)
            elif args.file:
                data = read_file(args.file)
            elif args.url:
                data = read_url(args.url)
            else:
                parser.error("必须指定 --input, --file, --url, --batch 或 --selftest 之一")
                return 1
            
            # 生成输出
            if args.format == "yaml":
                output = to_yaml(data)
            else:
                output = to_json(data)
        
        # 输出结果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"结果已写入: {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误 [{ERR_FILE_NOT_FOUND}]: 文件不存在", file=sys.stderr)
        return 1
    except (IOError, OSError) as e:
        print(f"错误 [{ERR_FILE_READ}]: {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(f"错误 [{ERR_URL_FETCH}]: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        code = str(e) if str(e).startswith("E") else ERR_PARSE
        print(f"错误 [{code}]: 数据解析失败", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
