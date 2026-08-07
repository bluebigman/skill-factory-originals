#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataprovider - SQL查询技能核心实现
功能：将输入数据解析为结构化结果，支持批量处理和自定义格式输出
版本：1.0.0
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出格式不支持，可选：json/text/csv",
    "E008": "批量处理失败，请检查输入列表",
    "E009": "字段提取失败，请检查输入格式",
    "E010": "参数校验失败，请检查命令行参数",
}


class DataProviderError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class ParsedRecord:
    """解析后的单条记录"""
    def __init__(self, data: Dict[str, Any], confidence: float = 1.0):
        self.data = data          # 结构化数据
        self.confidence = confidence  # 置信度 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": round(self.confidence, 2),
            "level": self._get_confidence_level(),
        }

    def _get_confidence_level(self) -> str:
        """根据置信度返回等级标注"""
        if self.confidence >= 0.90:
            return "直接输出"
        elif self.confidence >= 0.85:
            return "建议复核"
        else:
            return "需核实"

    def __repr__(self):
        return f"ParsedRecord(data={self.data}, confidence={self.confidence})"


# ============================================================
# 核心解析器
# ============================================================
class DataParser:
    """
    数据解析器：将输入文本解析为结构化记录
    支持格式：
    - JSON 格式输入
    - 键值对格式（key=value, 每行一条）
    - 简单表格格式（逗号/制表符分隔）
    """

    def __init__(self):
        self.supported_formats = ["json", "kv", "table"]

    def parse(self, input_text: str) -> List[ParsedRecord]:
        """
        解析输入文本，返回记录列表
        
        参数:
            input_text: 原始输入字符串
            
        返回:
            List[ParsedRecord]: 解析后的记录列表
            
        异常:
            DataProviderError: E001 输入为空, E003 格式错误
        """
        if not input_text or not input_text.strip():
            raise DataProviderError("E001")

        # 去除首尾空白
        text = input_text.strip()

        # 尝试 JSON 解析
        try:
            return self._parse_json(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # 尝试键值对解析
        try:
            records = self._parse_kv(text)
            if records:
                return records
        except Exception:
            pass

        # 尝试表格解析
        try:
            records = self._parse_table(text)
            if records:
                return records
        except Exception:
            pass

        # 所有解析都失败
        raise DataProviderError("E003", "输入格式不符合要求，支持 JSON、key=value 或表格格式")

    def _parse_json(self, text: str) -> List[ParsedRecord]:
        """解析 JSON 格式输入"""
        data = json.loads(text)

        # 如果是单个对象
        if isinstance(data, dict):
            return [ParsedRecord(data, confidence=1.0)]

        # 如果是对象列表
        if isinstance(data, list):
            records = []
            for item in data:
                if isinstance(item, dict):
                    records.append(ParsedRecord(item, confidence=1.0))
                else:
                    raise ValueError("JSON 列表元素必须是对象")
            if records:
                return records
            raise ValueError("JSON 列表为空")

        raise ValueError("JSON 必须是对象或对象数组")

    def _parse_kv(self, text: str) -> List[ParsedRecord]:
        """解析键值对格式（每行一个 key=value）"""
        lines = text.splitlines()
        record: Dict[str, Any] = {}
        records: List[ParsedRecord] = []

        for line in lines:
            line = line.strip()
            if not line:
                # 空行分隔记录
                if record:
                    records.append(ParsedRecord(record, confidence=0.9))
                    record = {}
                continue

            # 查找 key=value 或 key: value
            match = re.match(r'^([^=:]+)[=:](.+)$', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                record[key] = value
            else:
                # 无法解析的行，跳过或报错
                continue

        # 处理最后一条记录
        if record:
            records.append(ParsedRecord(record, confidence=0.9))

        return records

    def _parse_table(self, text: str) -> List[ParsedRecord]:
        """解析表格格式（逗号或制表符分隔）"""
        lines = text.splitlines()
        if len(lines) < 2:
            return []

        # 检测分隔符
        delimiter = None
        for sep in [',', '\t', ';']:
            if sep in lines[0]:
                delimiter = sep
                break

        if not delimiter:
            return []

        # 解析表头
        headers = [h.strip() for h in lines[0].split(delimiter)]
        if not headers:
            return []

        records = []
        for line in lines[1:]:
            if not line.strip():
                continue
            values = [v.strip() for v in line.split(delimiter)]
            # 补齐缺失列
            while len(values) < len(headers):
                values.append("")
            # 截断多余列
            values = values[:len(headers)]

            record = dict(zip(headers, values))
            records.append(ParsedRecord(record, confidence=0.9))

        return records


# ============================================================
# 数据处理器
# ============================================================
class DataProcessor:
    """
    数据处理管道：对解析后的记录进行过滤、转换、排序等操作
    """

    def __init__(self, records: List[ParsedRecord]):
        self.records = records

    def filter_by_field(self, field: str, value: Any) -> 'DataProcessor':
        """按字段值过滤记录"""
        filtered = []
        for rec in self.records:
            if field in rec.data and rec.data[field] == value:
                filtered.append(rec)
        self.records = filtered
        return self

    def filter_by_confidence(self, min_confidence: float) -> 'DataProcessor':
        """按置信度阈值过滤"""
        filtered = [
            rec for rec in self.records
            if rec.confidence >= min_confidence
        ]
        self.records = filtered
        return self

    def select_fields(self, fields: List[str]) -> 'DataProcessor':
        """选择指定字段，丢弃其他字段"""
        selected = []
        for rec in self.records:
            new_data = {}
            for field in fields:
                if field in rec.data:
                    new_data[field] = rec.data[field]
            selected.append(ParsedRecord(new_data, rec.confidence))
        self.records = selected
        return self

    def sort_by_field(self, field: str, reverse: bool = False) -> 'DataProcessor':
        """按指定字段排序"""
        self.records.sort(
            key=lambda r: str(r.data.get(field, "")),
            reverse=reverse
        )
        return self

    def limit(self, count: int) -> 'DataProcessor':
        """限制记录数量"""
        self.records = self.records[:count]
        return self

    def get_records(self) -> List[ParsedRecord]:
        """获取处理后的记录"""
        return self.records


# ============================================================
# 输出格式化器
# ============================================================
class OutputFormatter:
    """将处理结果格式化为指定输出"""

    @staticmethod
    def format(records: List[ParsedRecord], output_format: str = "json") -> str:
        """
        格式化输出
        
        参数:
            records: 记录列表
            output_format: json / text / csv
            
        返回:
            格式化后的字符串
        """
        if output_format == "json":
            return OutputFormatter._to_json(records)
        elif output_format == "text":
            return OutputFormatter._to_text(records)
        elif output_format == "csv":
            return OutputFormatter._to_csv(records)
        else:
            raise DataProviderError("E007")

    @staticmethod
    def _to_json(records: List[ParsedRecord]) -> str:
        """JSON 格式输出"""
        result = {
            "count": len(records),
            "records": [rec.to_dict() for rec in records]
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_text(records: List[ParsedRecord]) -> str:
        """纯文本格式输出"""
        if not records:
            return "（无记录）"

        lines = []
        for i, rec in enumerate(records, 1):
            lines.append(f"--- 记录 {i} ---")
            for key, value in rec.data.items():
                lines.append(f"{key}: {value}")
            lines.append(f"置信度: {rec.confidence:.0%} ({rec._get_confidence_level()})")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _to_csv(records: List[ParsedRecord]) -> str:
        """CSV 格式输出"""
        if not records:
            return ""

        # 收集所有字段名
        all_fields = []
        for rec in records:
            for field in rec.data.keys():
                if field not in all_fields:
                    all_fields.append(field)

        # 写入 CSV
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 表头
        writer.writerow(all_fields + ["confidence"])

        # 数据行
        for rec in records:
            row = [rec.data.get(field, "") for field in all_fields]
            row.append(f"{rec.confidence:.2f}")
            writer.writerow(row)

        return output.getvalue()


# ============================================================
# 主处理函数
# ============================================================
def process_input(
    input_text: str,
    output_format: str = "json",
    filter_field: Optional[str] = None,
    filter_value: Optional[str] = None,
    select: Optional[List[str]] = None,
    sort_field: Optional[str] = None,
    sort_desc: bool = False,
    max_records: Optional[int] = None,
    min_confidence: Optional[float] = None,
) -> str:
    """
    处理输入数据的完整流程
    
    参数:
        input_text: 原始输入文本
        output_format: 输出格式 (json/text/csv)
        filter_field: 过滤字段名
        filter_value: 过滤字段值
        select: 选择的字段列表
        sort_field: 排序字段
        sort_desc: 是否降序
        max_records: 最大记录数
        min_confidence: 最低置信度
        
    返回:
        格式化后的输出字符串
        
    异常:
        DataProviderError: 各种错误码
    """
    # Step 1: 解析输入
    parser = DataParser()
    records = parser.parse(input_text)

    # Step 2: 处理数据
    processor = DataProcessor(records)

    # 按置信度过滤
    if min_confidence is not None:
        processor.filter_by_confidence(min_confidence)

    # 按字段过滤
    if filter_field and filter_value is not None:
        processor.filter_by_field(filter_field, filter_value)

    # 选择字段
    if select:
        processor.select_fields(select)

    # 排序
    if sort_field:
        processor.sort_by_field(sort_field, reverse=sort_desc)

    # 限制数量
    if max_records is not None:
        processor.limit(max_records)

    # Step 3: 格式化输出
    return OutputFormatter.format(processor.get_records(), output_format)


# ============================================================
# 内置自检（selftest）
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑
    
    使用硬编码样例数据，不依赖外部文件或网络
    
    返回:
        True 表示自检通过，False 表示失败
    """
    print("=== dataprovider 自检开始 ===")

    # 测试数据 1: JSON 格式
    test_json = '''
    [
        {"name": "张三", "age": 28, "city": "北京", "score": 85},
        {"name": "李四", "age": 32, "city": "上海", "score": 92},
        {"name": "王五", "age": 25, "city": "北京", "score": 78},
        {"name": "赵六", "age": 35, "city": "深圳", "score": 88}
    ]
    '''

    # 测试数据 2: 键值对格式
    test_kv = """
name=苹果
price=5.5
category=水果

name=香蕉
price=3.2
category=水果

name=牛奶
price=12.8
category=饮品
"""

    # 测试数据 3: 表格格式
    test_table = """id,name,department
001,张三,技术部
002,李四,市场部
003,王五,技术部
"""

    try:
        # ---- 测试 1: JSON 解析 ----
        print("\n[测试1] JSON 解析")
        parser = DataParser()
        records = parser.parse(test_json)
        assert len(records) == 4, f"JSON解析应得到4条记录，实际{len(records)}条"
        assert "name" in records[0].data, "记录应包含name字段"
        assert records[0].data["name"] == "张三", "第一条记录应为张三"
        assert records[0].confidence >= 1.0, "JSON解析置信度应为1.0"
        print(f"  ✓ 通过 (解析到 {len(records)} 条记录)")

        # ---- 测试 2: 键值对解析 ----
        print("\n[测试2] 键值对解析")
        records_kv = parser.parse(test_kv)
        assert len(records_kv) == 3, f"键值对解析应得到3条记录，实际{len(records_kv)}条"
        assert records_kv[0].data.get("name") == "苹果", "第一条应为苹果"
        assert records_kv[0].confidence >= 0.8, "键值对解析置信度应≥0.8"
        print(f"  ✓ 通过 (解析到 {len(records_kv)} 条记录)")

        # ---- 测试 3: 表格解析 ----
        print("\n[测试3] 表格解析")
        records_table = parser.parse(test_table)
        assert len(records_table) == 3, f"表格解析应得到3条记录，实际{len(records_table)}条"
        assert records_table[0].data.get("department") == "技术部", "第一条记录部门应为技术部"
        print(f"  ✓ 通过 (解析到 {len(records_table)} 条记录)")

        # ---- 测试 4: 过滤功能 ----
        print("\n[测试4] 字段过滤")
        processor = DataProcessor(parser.parse(test_json))
        processor.filter_by_field("city", "北京")
        filtered = processor.get_records()
        assert len(filtered) == 2, f"过滤北京应得到2条记录，实际{len(filtered)}条"
        for rec in filtered:
            assert rec.data["city"] == "北京", "过滤后城市都应为北京"
        print(f"  ✓ 通过 (过滤后剩余 {len(filtered)} 条记录)")

        # ---- 测试 5: 字段选择 ----
        print("\n[测试5] 字段选择")
        processor = DataProcessor(parser.parse(test_json))
        processor.select_fields(["name", "score"])
        selected = processor.get_records()
        assert len(selected) == 4, "字段选择后记录数不变"
        for rec in selected:
            assert "name" in rec.data, "应保留name字段"
            assert "score" in rec.data, "应保留score字段"
            assert "city" not in rec.data, "不应包含city字段"
        print(f"  ✓ 通过 (字段选择成功)")

        # ---- 测试 6: 排序功能 ----
        print("\n[测试6] 排序")
        processor = DataProcessor(parser.parse(test_json))
        processor.sort_by_field("score", reverse=True)
        sorted_records = processor.get_records()
        assert len(sorted_records) == 4, "排序后记录数不变"
        scores = [rec.data["score"] for rec in sorted_records]
        assert scores[0] >= scores[-1], "降序排序后第一个分数应大于等于最后一个"
        print(f"  ✓ 通过 (排序成功，最高分: {scores[0]})")

        # ---- 测试 7: 完整处理流程 ----
        print("\n[测试7] 完整处理流程")
        result = process_input(
            test_json,
            output_format="json",
            filter_field="city",
            filter_value="北京",
            sort_field="score",
            sort_desc=True,
        )
        result_data = json.loads(result)
        assert result_data["count"] == 2, f"处理结果应为2条记录，实际{result_data['count']}条"
        assert result_data["records"][0]["data"]["name"] == "张三", "北京最高分应为张三(85)"
        print(f"  ✓ 通过 (处理流程正常，返回 {result_data['count']} 条记录)")

        # ---- 测试 8: 输出格式 ----
        print("\n[测试8] 输出格式")
        text_result = process_input(test_kv, output_format="text")
        assert "苹果" in text_result, "文本输出应包含苹果"
        assert "置信度" in text_result, "文本输出应包含置信度信息"

        csv_result = process_input(test_table, output_format="csv")
        assert "name" in csv_result, "CSV输出应包含表头"
        assert "张三" in csv_result, "CSV输出应包含数据"
        print(f"  ✓ 通过 (text和csv格式输出正常)")

        # ---- 测试 9: 错误处理 ----
        print("\n[测试9] 错误处理")
        try:
            parser.parse("")
            raise AssertionError("空输入应抛出E001错误")
        except DataProviderError as e:
            assert e.error_code == "E001", f"空输入错误码应为E001，实际{e.error_code}"
            print(f"  ✓ 通过 (空输入正确返回E001: {e.message})")

        try:
            parser.parse("::: 无法解析的内容 :::")
            raise AssertionError("无法解析的内容应抛出E003错误")
        except DataProviderError as e:
            assert e.error_code == "E003", f"格式错误错误码应为E003，实际{e.error_code}"
            print(f"  ✓ 通过 (格式错误正确返回E003: {e.message})")

        # ---- 测试 10: 批量处理 ----
        print("\n[测试10] 批量处理")
        batch_inputs = [test_json, test_kv, test_table]
        batch_results = []
        for inp in batch_inputs:
            result = process_input(inp, output_format="json")
            batch_results.append(result)

        assert len(batch_results) == 3, "批量处理应返回3个结果"
        for result in batch_results:
            data = json.loads(result)
            assert data["count"] > 0, "每个结果都应有记录"
        print(f"  ✓ 通过 (批量处理 {len(batch_results)} 个输入成功)")

        print("\n=== 全部自检通过 ===")
        return True

    except AssertionError as e:
        print(f"\n✗ 自检失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 自检异常: {e}")
        return False


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="dataprovider - SQL查询技能核心实现",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从标准输入读取JSON并输出
  echo '[{"name":"张三","age":28}]' | python main.py

  # 从文件读取并输出为文本格式
  python main.py -f input.txt -o text

  # 过滤和排序
  python main.py -f input.json --filter-field city --filter-value 北京 --sort-field score

  # 运行自检
  python main.py --selftest
        """
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="输入文件路径（省略则从标准输入读取）"
    )
    parser.add_argument(
        "-o", "--output",
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--filter-field",
        help="按指定字段过滤"
    )
    parser.add_argument(
        "--filter-value",
        help="过滤字段的值"
    )
    parser.add_argument(
        "--select",
        help="选择字段，用逗号分隔"
    )
    parser.add_argument(
        "--sort-field",
        help="按指定字段排序"
    )
    parser.add_argument(
        "--sort-desc",
        action="store_true",
        help="降序排序"
    )
    parser.add_argument(
        "--max-records",
        type=int,
        help="最大记录数"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        help="最低置信度 (0.0-1.0)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    try:
        # 读取输入
        if args.input_file:
            try:
                with open(args.input_file, "r", encoding="utf-8") as f:
                    input_text = f.read()
            except FileNotFoundError:
                raise DataProviderError("E001", f"文件不存在: {args.input_file}")
            except IOError as e:
                raise DataProviderError("E006", f"读取文件失败: {e}")
        else:
            # 从标准输入读取
            input_text = sys.stdin.read()

        # 处理字段选择
        select_fields = None
        if args.select:
            select_fields = [f.strip() for f in args.select.split(",")]

        # 处理输入
        output = process_input(
            input_text=input_text,
            output_format=args.output,
            filter_field=args.filter_field,
            filter_value=args.filter_value,
            select=select_fields,
            sort_field=args.sort_field,
            sort_desc=args.sort_desc,
            max_records=args.max_records,
            min_confidence=args.min_confidence,
        )

        # 输出结果
        print(output)

    except DataProviderError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作已被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 [E006]: 未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
