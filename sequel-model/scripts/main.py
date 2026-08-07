#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

sequel-model 技能的全新独立实现（clean-room）。
仅依据功能规格设计，不参考任何既有代码。

功能：
- 将用户提供的数据源（列表/文件路径/URL文本）转换为结构化结果
- 支持字段映射、批量处理、置信度标注
- 支持 JSON / YAML / CSV 三种输出格式
- 内置 --selftest 离线自检

错误码：
E001 - 输入参数错误
E002 - 数据源为空或无法识别
E003 - 文件读取失败
E004 - URL内容获取失败
E005 - 字段映射配置无效
E006 - 单条记录转换失败
E007 - 批量处理超过1000条限制
E008 - 输出格式不支持
E009 - 序列化输出失败
E010 - 内部未知错误
"""

import argparse
import csv
import io
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量与配置
# ---------------------------------------------------------------------------

SUPPORTED_FORMATS = ("json", "yaml", "csv")
MAX_BATCH_SIZE = 1000

# 默认字段映射：原始字段名 -> 标准字段名
DEFAULT_FIELD_MAP = {
    "name": "姓名",
    "age": "年龄",
    "email": "邮箱",
    "phone": "电话",
    "address": "地址",
    "company": "公司",
    "title": "职位",
}


# ---------------------------------------------------------------------------
# 核心数据模型类
# ---------------------------------------------------------------------------

class Record:
    """单条结构化记录，包含数据和置信度。"""

    def __init__(self, data: Dict[str, Any], confidence: float = 1.0):
        self.data = data
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（含置信度元数据）。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Record":
        """从字典构造 Record。"""
        return cls(data=raw.get("data", {}), confidence=float(raw.get("confidence", 1.0)))


class BatchResult:
    """批量处理结果，包含多条记录和整体统计。"""

    def __init__(self, records: List[Record]):
        self.records = records

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典结构。"""
        return {
            "total": len(self.records),
            "records": [r.to_dict() for r in self.records],
            "avg_confidence": self._avg_confidence(),
        }

    def _avg_confidence(self) -> float:
        """计算平均置信度。"""
        if not self.records:
            return 0.0
        return round(sum(r.confidence for r in self.records) / len(self.records), 4)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "BatchResult":
        """从字典构造 BatchResult。"""
        records = [Record.from_dict(item) for item in raw.get("records", [])]
        return cls(records=records)


# ---------------------------------------------------------------------------
# 数据解析与转换核心逻辑
# ---------------------------------------------------------------------------

class DataParser:
    """解析不同来源的数据。"""

    @staticmethod
    def parse_text(text: str) -> List[Dict[str, Any]]:
        """将纯文本解析为字典列表（简单启发式：按行拆分，识别键值对）。"""
        records = []
        current = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                if current:
                    records.append(current)
                    current = {}
                continue
            # 尝试解析 "key: value" 格式
            if ":" in line:
                key, _, value = line.partition(":")
                current[key.strip()] = value.strip()
            elif "=" in line:
                key, _, value = line.partition("=")
                current[key.strip()] = value.strip()
            else:
                # 无分隔符：作为独立字段
                current[f"field_{len(current)+1}"] = line
        if current:
            records.append(current)
        return records

    @staticmethod
    def parse_json(data: Any) -> List[Dict[str, Any]]:
        """将 JSON 数据转换为字典列表。"""
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @staticmethod
    def parse_csv(text: str) -> List[Dict[str, Any]]:
        """将 CSV 文本转换为字典列表。"""
        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    @staticmethod
    def parse_file(path: str) -> List[Dict[str, Any]]:
        """读取文件并解析。"""
        try:
            p = Path(path)
            suffix = p.suffix.lower()
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            raise RuntimeError(f"E003: 文件读取失败 {path}: {e}")

        if suffix == ".json":
            try:
                data = json.loads(content)
                return DataParser.parse_json(data)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"E003: JSON 解析失败: {e}")
        elif suffix == ".csv":
            return DataParser.parse_csv(content)
        else:
            return DataParser.parse_text(content)

    @staticmethod
    def parse_url(url: str) -> List[Dict[str, Any]]:
        """从 URL 获取内容并解析。"""
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                content = resp.read().decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"E004: URL 获取失败 {url}: {e}")
        return DataParser.parse_text(content)


class FieldMapper:
    """字段映射与转换。"""

    def __init__(self, field_map: Optional[Dict[str, str]] = None):
        self.field_map = field_map or DEFAULT_FIELD_MAP

    def map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """将原始记录映射为标准字段。"""
        mapped = {}
        missing = []
        for src_field, dst_field in self.field_map.items():
            if src_field in record and record[src_field] not in (None, ""):
                mapped[dst_field] = record[src_field]
            else:
                missing.append(dst_field)
        # 保留未映射的额外字段
        for key, value in record.items():
            if key not in self.field_map and value not in (None, ""):
                mapped[key] = value
        return mapped

    def calculate_confidence(self, record: Dict[str, Any]) -> float:
        """根据字段填充率计算置信度。"""
        if not record:
            return 0.0
        filled = sum(1 for v in record.values() if v not in (None, ""))
        return round(filled / len(record), 4) if record else 0.0


class ModelConverter:
    """主转换器：组合解析与映射。"""

    def __init__(self, field_map: Optional[Dict[str, str]] = None):
        self.mapper = FieldMapper(field_map)

    def convert(self, records: List[Dict[str, Any]]) -> BatchResult:
        """批量转换记录。"""
        if len(records) > MAX_BATCH_SIZE:
            raise RuntimeError(f"E007: 批量处理超过 {MAX_BATCH_SIZE} 条限制")
        result_records = []
        for raw in records:
            try:
                mapped = self.mapper.map_record(raw)
                confidence = self.mapper.calculate_confidence(mapped)
                result_records.append(Record(data=mapped, confidence=confidence))
            except Exception as e:
                raise RuntimeError(f"E006: 单条记录转换失败: {e}")
        return BatchResult(result_records)

    def convert_text(self, text: str) -> BatchResult:
        """从文本直接转换。"""
        records = DataParser.parse_text(text)
        return self.convert(records)

    def convert_file(self, path: str) -> BatchResult:
        """从文件转换。"""
        records = DataParser.parse_file(path)
        return self.convert(records)

    def convert_url(self, url: str) -> BatchResult:
        """从 URL 转换。"""
        records = DataParser.parse_url(url)
        return self.convert(records)


# ---------------------------------------------------------------------------
# 输出序列化
# ---------------------------------------------------------------------------

class OutputSerializer:
    """将 BatchResult 序列化为不同格式。"""

    @staticmethod
    def to_json(result: BatchResult) -> str:
        """序列化为 JSON 字符串。"""
        try:
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"E009: JSON 序列化失败: {e}")

    @staticmethod
    def to_csv(result: BatchResult) -> str:
        """序列化为 CSV 字符串。"""
        try:
            if not result.records:
                return ""
            # 收集所有字段
            all_fields = set()
            for r in result.records:
                all_fields.update(r.data.keys())
            all_fields = sorted(all_fields)

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["confidence"] + list(all_fields))
            writer.writeheader()
            for r in result.records:
                row = {"confidence": r.confidence}
                row.update(r.data)
                writer.writerow(row)
            return output.getvalue()
        except Exception as e:
            raise RuntimeError(f"E009: CSV 序列化失败: {e}")

    @staticmethod
    def to_yaml(result: BatchResult) -> str:
        """序列化为 YAML 字符串（使用 JSON 兼容子集）。"""
        try:
            # 使用 json 转 dict，然后手动格式化 YAML
            data = result.to_dict()
            return OutputSerializer._dict_to_yaml(data)
        except Exception as e:
            raise RuntimeError(f"E009: YAML 序列化失败: {e}")

    @staticmethod
    def _dict_to_yaml(data: Any, indent: int = 0) -> str:
        """将字典/列表转为 YAML 格式字符串。"""
        lines = []
        prefix = " " * indent
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(OutputSerializer._dict_to_yaml(value, indent + 2))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(OutputSerializer._dict_to_yaml(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")
        return "\n".join(lines)

    @staticmethod
    def serialize(result: BatchResult, fmt: str) -> str:
        """根据格式序列化。"""
        fmt = fmt.lower()
        if fmt == "json":
            return OutputSerializer.to_json(result)
        elif fmt == "csv":
            return OutputSerializer.to_csv(result)
        elif fmt == "yaml":
            return OutputSerializer.to_yaml(result)
        else:
            raise RuntimeError(f"E008: 不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检测试
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """运行内置自检样例，验证核心逻辑。"""
    print("=== sequel-model 自检开始 ===")

    # 测试样例数据
    sample_text = """
name: 张三
age: 28
email: zhangsan@example.com
phone: 13800000000

name: 李四
age: 35
email: lisi@example.com
company: 测试公司
"""

    sample_csv = "name,age,email\n王五,30,wangwu@example.com\n赵六,25,zhaoliu@example.com"

    sample_json = json.dumps([
        {"name": "孙七", "age": 40, "email": "sunqi@example.com"},
        {"name": "周八", "age": 22, "phone": "13900000000"},
    ])

    # 1. 测试文本解析
    print("[1/6] 测试文本解析...")
    parser = DataParser()
    text_records = parser.parse_text(sample_text)
    assert len(text_records) == 2, "文本解析应得到2条记录"
    assert "name" in text_records[0], "第一条记录应有name字段"
    print("      通过")

    # 2. 测试 CSV 解析
    print("[2/6] 测试 CSV 解析...")
    csv_records = parser.parse_csv(sample_csv)
    assert len(csv_records) == 2, "CSV解析应得到2条记录"
    assert csv_records[0]["name"] == "王五", "第一条记录姓名应为王五"
    print("      通过")

    # 3. 测试 JSON 解析
    print("[3/6] 测试 JSON 解析...")
    json_records = parser.parse_json(json.loads(sample_json))
    assert len(json_records) == 2, "JSON解析应得到2条记录"
    assert json_records[1]["phone"] == "13900000000", "第二条记录应有电话"
    print("      通过")

    # 4. 测试字段映射与置信度
    print("[4/6] 测试字段映射与置信度...")
    converter = ModelConverter()
    result = converter.convert(text_records)
    assert len(result.records) == 2, "应得到2条转换记录"
    assert "姓名" in result.records[0].data, "映射后应包含标准字段'姓名'"
    assert 0.0 <= result.records[0].confidence <= 1.0, "置信度应在0~1之间"
    print("      通过")

    # 5. 测试批量转换与输出
    print("[5/6] 测试批量转换与输出...")
    all_records = text_records + csv_records + json_records
    batch_result = converter.convert(all_records)
    assert len(batch_result.records) == 6, "批量转换应得到6条记录"
    assert batch_result.to_dict()["total"] == 6, "总数应为6"

    # 测试 JSON 输出
    json_out = OutputSerializer.to_json(batch_result)
    assert json.loads(json_out)["total"] == 6, "JSON输出应包含总数"
    print("      通过")

    # 6. 测试 CSV 和 YAML 输出
    print("[6/6] 测试 CSV/YAML 输出...")
    csv_out = OutputSerializer.to_csv(batch_result)
    assert "confidence" in csv_out, "CSV应包含置信度列"

    yaml_out = OutputSerializer.to_yaml(batch_result)
    assert "total:" in yaml_out, "YAML应包含总数"
    print("      通过")

    print("=== 自检全部通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="sequel-model: 数据建模、结构转换、字段映射工具"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入数据：文件路径、URL 或直接文本（可用 --type 指定类型）"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["text", "file", "url"],
        default="text",
        help="输入类型 (默认: text)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=list(SUPPORTED_FORMATS),
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--field-map",
        help="字段映射 JSON 字符串，如 '{\"name\":\"姓名\",\"age\":\"年龄\"}'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"E010: 自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"E010: 自检异常: {e}", file=sys.stderr)
            return 1

    # 需要输入数据
    if not args.input:
        print("E001: 缺少输入数据。请提供 --input 或使用 --selftest", file=sys.stderr)
        return 1

    try:
        # 构建字段映射
        field_map = None
        if args.field_map:
            try:
                field_map = json.loads(args.field_map)
                if not isinstance(field_map, dict):
                    raise ValueError("字段映射必须是 JSON 对象")
            except json.JSONDecodeError:
                print("E005: 字段映射 JSON 解析失败", file=sys.stderr)
                return 1
            except ValueError as e:
                print(f"E005: 字段映射配置无效: {e}", file=sys.stderr)
                return 1

        # 创建转换器
        converter = ModelConverter(field_map)

        # 根据类型处理输入
        if args.type == "file":
            result = converter.convert_file(args.input)
        elif args.type == "url":
            result = converter.convert_url(args.input)
        else:
            result = converter.convert_text(args.input)

        # 序列化输出
        output = OutputSerializer.serialize(result, args.format)
        print(output)
        return 0

    except RuntimeError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
