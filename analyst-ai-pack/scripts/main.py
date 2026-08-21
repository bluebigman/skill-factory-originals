#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyst-ai-pack 技能实现脚本
功能：将用户提供的任意数据源解析为结构化结果，并标注置信度。
版本：1.0.2
"""

import json
import re
import sys
import os
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据为空或类型不正确",
    "E002": "数据源格式不支持",
    "E003": "JSON 解析失败",
    "E004": "CSV 解析失败",
    "E005": "字段映射失败",
    "E006": "置信度计算失败",
    "E007": "输出模板不合法",
    "E008": "批量处理失败",
    "E009": "参数错误",
    "E010": "内部逻辑错误",
}


class SkillError(Exception):
    """技能运行异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class StructuredRecord:
    """结构化单条记录"""

    def __init__(self, fields: Dict[str, Any], confidence: float = 1.0):
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": self.fields,
            "confidence": self.confidence,
        }


class ParseResult:
    """解析结果集合"""

    def __init__(self):
        self.records: List[StructuredRecord] = []
        self.source_type: str = "unknown"
        self.total_confidence: float = 0.0

    def add_record(self, record: StructuredRecord) -> None:
        self.records.append(record)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "record_count": len(self.records),
            "total_confidence": self.total_confidence,
            "records": [r.to_dict() for r in self.records],
        }


# ============================================================
# 数据解析器
# ============================================================

class DataParser:
    """数据解析器：将不同格式的输入转换成结构化记录"""

    def __init__(self):
        self.supported_formats = ["json", "csv", "text"]

    def parse(self, data: Union[str, bytes, Dict, List], source_type: Optional[str] = None) -> ParseResult:
        """主解析入口"""
        if data is None or (isinstance(data, (str, bytes)) and not data):
            raise SkillError("E001")

        # 判断数据源类型
        fmt = source_type or self._detect_format(data)
        if fmt not in self.supported_formats:
            raise SkillError("E002", f"不支持的数据格式: {fmt}")

        result = ParseResult()
        result.source_type = fmt

        if fmt == "json":
            self._parse_json(data, result)
        elif fmt == "csv":
            self._parse_csv(data, result)
        elif fmt == "text":
            self._parse_text(data, result)

        # 计算整体置信度
        self._calculate_total_confidence(result)
        return result

    def _detect_format(self, data: Any) -> str:
        """自动检测数据格式"""
        if isinstance(data, (dict, list)):
            return "json"
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")

        if isinstance(data, str):
            stripped = data.strip()
            if stripped.startswith(("{", "[")):
                return "json"
            if "," in stripped and "\n" in stripped:
                return "csv"
        return "text"

    def _parse_json(self, data: Any, result: ParseResult) -> None:
        """解析 JSON 格式数据"""
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            if isinstance(data, str):
                parsed = json.loads(data)
            else:
                parsed = data

            # 处理列表
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        conf = self._estimate_confidence(item)
                        result.add_record(StructuredRecord(item, conf))
            # 处理单个字典
            elif isinstance(parsed, dict):
                # 可能是单条记录，也可能是嵌套结构
                if any(isinstance(v, dict) for v in parsed.values()):
                    # 嵌套结构，尝试提取记录列表
                    for key, value in parsed.items():
                        if isinstance(value, list) and value and isinstance(value[0], dict):
                            for item in value:
                                conf = self._estimate_confidence(item)
                                result.add_record(StructuredRecord(item, conf))
                        elif isinstance(value, dict):
                            conf = self._estimate_confidence(value)
                            result.add_record(StructuredRecord(value, conf))
                else:
                    conf = self._estimate_confidence(parsed)
                    result.add_record(StructuredRecord(parsed, conf))
            else:
                raise SkillError("E003", "JSON 顶层必须是对象或数组")
        except json.JSONDecodeError as e:
            raise SkillError("E003", f"JSON 解析错误: {e}")

    def _parse_csv(self, data: Any, result: ParseResult) -> None:
        """解析 CSV 格式数据"""
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            if not isinstance(data, str):
                raise SkillError("E004")

            lines = [line.strip() for line in data.split("\n") if line.strip()]
            if not lines:
                raise SkillError("E004", "CSV 内容为空")

            headers = self._parse_csv_line(lines[0])
            for line in lines[1:]:
                values = self._parse_csv_line(line)
                if len(values) != len(headers):
                    # 长度不匹配，补齐或截断
                    values = self._align_values(values, len(headers))
                record = dict(zip(headers, values))
                conf = self._estimate_confidence(record)
                result.add_record(StructuredRecord(record, conf))
        except Exception as e:
            raise SkillError("E004", f"CSV 解析错误: {e}")

    def _parse_csv_line(self, line: str) -> List[str]:
        """解析单行 CSV（处理引号包裹的逗号）"""
        # 简化实现：处理带引号的字段
        fields = []
        current = []
        in_quotes = False
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                fields.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        fields.append("".join(current).strip())
        return fields

    def _align_values(self, values: List[str], target_len: int) -> List[str]:
        """对齐字段数量"""
        if len(values) < target_len:
            return values + [""] * (target_len - len(values))
        return values[:target_len]

    def _parse_text(self, data: Any, result: ParseResult) -> None:
        """解析纯文本格式（尝试提取键值对）"""
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")
        if not isinstance(data, str):
            raise SkillError("E001")

        lines = [line.strip() for line in data.split("\n") if line.strip()]
        current_record: Dict[str, Any] = {}
        records: List[Dict[str, Any]] = []

        for line in lines:
            # 尝试匹配 key: value 或 key = value 格式
            match = re.match(r'^([^:=]+)[:=]\s*(.+)$', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                current_record[key] = value
            elif line.startswith("---") or line.startswith("==="):
                # 记录分隔符
                if current_record:
                    records.append(current_record)
                    current_record = {}
            else:
                # 非键值对行，如果当前有记录则保存，否则忽略
                if current_record:
                    records.append(current_record)
                    current_record = {}

        if current_record:
            records.append(current_record)

        if not records:
            # 无法提取结构化数据，将整段作为一条记录
            records = [{"content": data.strip()}]

        for record in records:
            conf = self._estimate_confidence(record)
            result.add_record(StructuredRecord(record, conf))

    def _estimate_confidence(self, record: Dict[str, Any]) -> float:
        """估算单条记录的置信度"""
        try:
            if not record:
                return 0.0

            # 基于字段完整性和类型丰富度估算
            total_fields = len(record)
            if total_fields == 0:
                return 0.0

            # 检查字段是否有值
            filled_fields = sum(1 for v in record.values() if v is not None and str(v).strip() != "")
            fill_ratio = filled_fields / total_fields

            # 检查是否有常见关键字段
            key_fields = ["id", "name", "date", "amount", "type", "title", "content"]
            key_hits = sum(1 for k in record.keys() if any(key in str(k).lower() for key in key_fields))
            key_ratio = min(key_hits / max(len(key_fields), 1), 1.0)

            # 综合置信度
            confidence = 0.4 * fill_ratio + 0.3 * key_ratio + 0.3 * min(total_fields / 5, 1.0)
            return round(min(max(confidence, 0.0), 1.0), 4)
        except Exception:
            raise SkillError("E006")

    def _calculate_total_confidence(self, result: ParseResult) -> None:
        """计算整体置信度"""
        if not result.records:
            result.total_confidence = 0.0
            return
        avg_conf = sum(r.confidence for r in result.records) / len(result.records)
        result.total_confidence = round(avg_conf, 4)


# ============================================================
# 结构化转换器
# ============================================================

class StructureTransformer:
    """将解析结果转换为用户定义的输出模板"""

    def __init__(self):
        self.default_template = {
            "record_count": "record_count",
            "confidence": "total_confidence",
            "data": "records"
        }

    def transform(self, parse_result: ParseResult, template: Optional[Dict] = None) -> Dict[str, Any]:
        """根据模板转换输出结构"""
        if template is None:
            template = self.default_template

        if not isinstance(template, dict):
            raise SkillError("E007", "模板必须是字典类型")

        output = {}
        try:
            for out_key, source_path in template.items():
                if isinstance(source_path, str):
                    # 简单路径映射
                    value = self._get_by_path(parse_result, source_path)
                    output[out_key] = value
                elif isinstance(source_path, dict):
                    # 嵌套模板
                    output[out_key] = self.transform(parse_result, source_path)
                else:
                    raise SkillError("E007", f"模板值类型不支持: {type(source_path)}")
            return output
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E007", f"模板转换失败: {e}")

    def _get_by_path(self, obj: Any, path: str) -> Any:
        """按路径获取值（支持点号访问）"""
        current = obj
        for part in path.split("."):
            if isinstance(current, ParseResult):
                # 处理 ParseResult 对象
                if part == "record_count":
                    current = len(current.records)
                elif part == "total_confidence":
                    current = current.total_confidence
                elif part == "source_type":
                    current = current.source_type
                elif part == "records":
                    # 转换为字典列表以便后续访问
                    current = [r.to_dict() for r in current.records]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part, None)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current


# ============================================================
# 批量处理器
# ============================================================

class BatchProcessor:
    """批量处理多个数据源"""

    def __init__(self):
        self.parser = DataParser()
        self.transformer = StructureTransformer()

    def process_batch(self, data_items: List[Any], template: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """批量处理数据项"""
        if not isinstance(data_items, list):
            raise SkillError("E008", "批量处理需要列表输入")

        results = []
        for i, item in enumerate(data_items):
            try:
                parse_result = self.parser.parse(item)
                transformed = self.transformer.transform(parse_result, template)
                transformed["_batch_index"] = i
                results.append(transformed)
            except SkillError as e:
                results.append({
                    "_batch_index": i,
                    "_error": e.code,
                    "_error_message": e.message
                })
        return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置自检逻辑，不依赖外部文件"""
    print("=" * 60)
    print("开始自检 (analyst-ai-pack) ...")
    print("=" * 60)

    try:
        # 1. 测试 JSON 解析
        print("\n[1/4] 测试 JSON 解析...")
        json_data = json.dumps([
            {"id": 1, "name": "张三", "amount": 100.5},
            {"id": 2, "name": "李四", "amount": 200.0},
            {"id": 3, "name": "王五", "amount": 300.75}
        ])
        parser = DataParser()
        result = parser.parse(json_data, "json")
        assert result.source_type == "json", "JSON 类型检测失败"
        assert len(result.records) == 3, f"JSON 记录数错误: {len(result.records)}"
        assert result.total_confidence > 0.5, f"JSON 置信度异常: {result.total_confidence}"
        assert all("name" in r.fields for r in result.records), "JSON 字段丢失"
        print(f"  ✓ JSON 解析成功, 记录数={len(result.records)}, 置信度={result.total_confidence}")

        # 2. 测试 CSV 解析
        print("\n[2/4] 测试 CSV 解析...")
        csv_data = "name,age,city\n张三,28,北京\n李四,32,上海\n王五,25,广州"
        result = parser.parse(csv_data, "csv")
        assert result.source_type == "csv", "CSV 类型检测失败"
        assert len(result.records) == 3, f"CSV 记录数错误: {len(result.records)}"
        assert result.total_confidence > 0.5, f"CSV 置信度异常: {result.total_confidence}"
        assert all("name" in r.fields for r in result.records), "CSV 字段丢失"
        print(f"  ✓ CSV 解析成功, 记录数={len(result.records)}, 置信度={result.total_confidence}")

        # 3. 测试文本解析
        print("\n[3/4] 测试文本解析...")
        text_data = """
        name: 张三
        age: 28
        city: 北京
        ---
        name: 李四
        age: 32
        city: 上海
        """
        result = parser.parse(text_data, "text")
        assert result.source_type == "text", "文本类型检测失败"
        assert len(result.records) >= 2, f"文本记录数错误: {len(result.records)}"
        assert result.total_confidence > 0.3, f"文本置信度异常: {result.total_confidence}"
        print(f"  ✓ 文本解析成功, 记录数={len(result.records)}, 置信度={result.total_confidence}")

        # 4. 测试模板转换和批量处理
        print("\n[4/4] 测试模板转换和批量处理...")
        transformer = StructureTransformer()
        custom_template = {
            "total": "record_count",
            "avg_confidence": "total_confidence",
            "first_record": "records.0.fields"
        }
        transformed = transformer.transform(result, custom_template)
        assert "total" in transformed, "模板转换缺少 total 字段"
        assert "avg_confidence" in transformed, "模板转换缺少 avg_confidence 字段"
        assert transformed["total"] > 0, "模板转换 total 值异常"
        assert isinstance(transformed["first_record"], dict), "模板转换 first_record 类型错误"
        print(f"  ✓ 模板转换成功: {json.dumps(transformed, ensure_ascii=False)}")

        batch_processor = BatchProcessor()
        batch_data = [json_data, csv_data, "key: value\nanother: test"]
        batch_results = batch_processor.process_batch(batch_data)
        assert len(batch_results) == 3, f"批量处理数量错误: {len(batch_results)}"
        assert all("_batch_index" in r for r in batch_results), "批量处理缺少索引"
        print(f"  ✓ 批量处理成功, 处理数量={len(batch_results)}")

        # 5. 测试错误处理
        print("\n[5/4] 测试错误处理...")
        try:
            parser.parse("", "json")
            raise AssertionError("空输入应该抛出 E001")
        except SkillError as e:
            assert e.code == "E001", f"错误码错误: {e.code}"
        print("  ✓ 错误处理正常 (E001)")

        print("\n" + "=" * 60)
        print("✅ 所有自检通过！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        return False
    except SkillError as e:
        print(f"\n❌ 自检失败: [{e.code}] {e.message}")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        return False


# ============================================================
# 主入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="analyst-ai-pack 数据分析智能处理工具",
        epilog="示例: python main.py --input data.json --format json --template template.json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--input", type=str, help="输入文件路径或数据字符串")
    parser.add_argument("--format", type=str, choices=["json", "csv", "text", "auto"], default="auto",
                        help="输入数据格式")
    parser.add_argument("--template", type=str, help="输出模板 JSON 文件路径")
    parser.add_argument("--output", type=str, help="输出结果文件路径")
    parser.add_argument("--batch", action="store_true", help="批量处理模式（输入为 JSON 数组）")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    if not args.input:
        print("错误: 请提供 --input 参数或使用 --selftest 进行自检", file=sys.stderr)
        sys.exit(1)

    try:
        # 读取输入
        input_data = args.input
        if os.path.isfile(args.input):
            with open(args.input, "r", encoding="utf-8") as f:
                input_data = f.read()

        # 批量处理
        if args.batch:
            try:
                batch_items = json.loads(input_data) if isinstance(input_data, str) else input_data
                if not isinstance(batch_items, list):
                    raise SkillError("E009", "批量模式需要 JSON 数组输入")
            except json.JSONDecodeError:
                raise SkillError("E003", "批量模式输入必须是有效 JSON 数组")
            processor = BatchProcessor()
            results = processor.process_batch(batch_items)
            output = {"batch_results": results, "count": len(results)}
        else:
            # 单条处理
            source_type = None if args.format == "auto" else args.format
            parser = DataParser()
            parse_result = parser.parse(input_data, source_type)

            # 加载模板
            template = None
            if args.template:
                if os.path.isfile(args.template):
                    with open(args.template, "r", encoding="utf-8") as f:
                        template = json.load(f)
                else:
                    try:
                        template = json.loads(args.template)
                    except json.JSONDecodeError:
                        raise SkillError("E007", "模板必须是有效 JSON")

            transformer = StructureTransformer()
            output = transformer.transform(parse_result, template)
            output["_source_type"] = parse_result.source_type

        # 输出结果
        output_json = json.dumps(output, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            print(f"结果已写入: {args.output}")
        else:
            print(output_json)

    except SkillError as e:
        print(f"错误: [{e.code}] {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
