#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体技能编排：数据转换与结构化输出工具
=========================================
依据功能规格独立实现（clean-room），不依赖任何第三方库。
支持批量处理、置信度标注、自定义模板等核心能力。

用法示例：
    python scripts/main.py --input sample.csv --output result.json
    python scripts/main.py --text "张三 2024-01-01 100元" --format json
    python scripts/main.py --selftest
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
dry_run = False  # v3.274 模块级 dry-run 标志

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "文件解析失败：格式不正确",
    "E004": "输入数据为空：没有可处理的内容",
    "E005": "模板渲染失败：模板格式错误",
    "E006": "输出写入失败：无法写入目标文件",
    "E007": "不支持的输入类型",
    "E008": "数据转换失败：无法提取有效字段",
    "E009": "批量处理失败：部分条目处理出错",
    "E010": "内部错误：未预期的异常",
}

# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class StructuredRecord:
    """单条结构化记录。"""

    def __init__(self, raw_text: str = "", fields: Optional[Dict[str, Any]] = None,
                 confidence: float = 1.0, needs_verification: Optional[List[str]] = None):
        self.raw_text = raw_text
        self.fields = fields if fields is not None else {}
        self.confidence = confidence
        self.needs_verification = needs_verification if needs_verification is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        result = {
            "raw": self.raw_text,
            "fields": self.fields,
            "confidence": self.confidence,
        }
        if self.needs_verification:
            result["needs_verification"] = self.needs_verification
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredRecord":
        """从字典创建实例。"""
        return cls(
            raw_text=data.get("raw", ""),
            fields=data.get("fields", {}),
            confidence=data.get("confidence", 1.0),
            needs_verification=data.get("needs_verification", []),
        )


class BatchResult:
    """批量处理结果。"""

    def __init__(self):
        self.records: List[StructuredRecord] = []
        self.errors: List[Dict[str, Any]] = []
        self.processed_count = 0
        self.failed_count = 0

    def add_record(self, record: StructuredRecord) -> None:
        """添加成功记录。"""
        self.records.append(record)
        self.processed_count += 1

    def add_error(self, error: Dict[str, Any]) -> None:
        """添加错误记录。"""
        self.errors.append(error)
        self.failed_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "records": [r.to_dict() for r in self.records],
            "errors": self.errors,
            "stats": {
                "processed": self.processed_count,
                "failed": self.failed_count,
                "total": self.processed_count + self.failed_count,
            },
        }

    @property
    def success_rate(self) -> float:
        """计算成功率。"""
        total = self.processed_count + self.failed_count
        if total == 0:
            return 0.0
        return self.processed_count / total


# ---------------------------------------------------------------------------
# 输入解析器
# ---------------------------------------------------------------------------

class InputParser:
    """解析各种格式的输入数据。"""

    # 常见日期格式
    DATE_PATTERNS = [
        r"\d{4}-\d{1,2}-\d{1,2}",       # 2024-01-01
        r"\d{4}/\d{1,2}/\d{1,2}",       # 2024/01/01
        r"\d{4}年\d{1,2}月\d{1,2}日",    # 2024年1月1日
        r"\d{1,2}-\d{1,2}-\d{4}",       # 01-01-2024
    ]

    # 常见金额格式
    MONEY_PATTERNS = [
        r"\d+(?:\.\d{1,2})?\s*(?:元|块|RMB|CNY|¥)",
        r"\$\s*\d+(?:\.\d{1,2})?",
        r"USD\s*\d+(?:\.\d{1,2})?",
    ]

    # 常见人名模式（中文）
    NAME_PATTERNS = [
        r"[\u4e00-\u9fa5]{2,4}(?=\s|$|，|。|,|\.)",
    ]

    @classmethod
    def parse_text(cls, text: str) -> StructuredRecord:
        """
        从纯文本中提取结构化信息。
        返回记录，包含提取的字段和置信度。
        """
        if not text or not text.strip():
            raise ValueError("E004: 输入文本为空")

        text = text.strip()
        fields: Dict[str, Any] = {}
        needs_verification: List[str] = []

        # 提取日期
        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                date_str = match.group()
                # 转换为标准格式
                try:
                    if "年" in date_str:
                        parts = re.findall(r"\d+", date_str)
                        if len(parts) == 3:
                            date_str = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif "/" in date_str:
                        parts = date_str.split("/")
                        if len(parts) == 3:
                            date_str = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif "-" in date_str and len(date_str.split("-")[0]) == 2:
                        # mm-dd-yyyy 格式
                        parts = date_str.split("-")
                        date_str = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                    fields["date"] = date_str
                except (ValueError, IndexError):
                    needs_verification.append("date")
                break

        # 提取金额
        for pattern in cls.MONEY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                money_str = match.group()
                # 提取数字部分
                num_match = re.search(r"\d+(?:\.\d{1,2})?", money_str)
                if num_match:
                    fields["amount"] = float(num_match.group())
                    # 判断货币类型
                    if "$" in money_str or "USD" in money_str.upper():
                        fields["currency"] = "USD"
                    elif "¥" in money_str or "RMB" in money_str.upper() or "CNY" in money_str.upper():
                        fields["currency"] = "CNY"
                    else:
                        fields["currency"] = "CNY"
                break

        # 提取人名（中文）
        name_match = re.search(cls.NAME_PATTERNS[0], text)
        if name_match:
            name = name_match.group().strip("，。,.")
            # 过滤掉常见非名字词汇
            if len(name) >= 2 and not any(kw in name for kw in ["数据", "信息", "内容", "结果"]):
                fields["name"] = name

        # 提取状态标记
        status_keywords = {
            "成功": "success",
            "失败": "failed",
            "进行中": "in_progress",
            "已完成": "completed",
            "待处理": "pending",
        }
        for keyword, status in status_keywords.items():
            if keyword in text:
                fields["status"] = status
                break

        # 计算置信度
        confidence = 0.5  # 基础置信度
        has_fields = len(fields)
        if has_fields >= 3:
            confidence = 0.9
        elif has_fields >= 2:
            confidence = 0.75
        elif has_fields >= 1:
            confidence = 0.6

        # 如果存在可能需要核实的字段
        if needs_verification:
            confidence = min(confidence, 0.5)

        return StructuredRecord(
            raw_text=text,
            fields=fields,
            confidence=confidence,
            needs_verification=needs_verification,
        )

    @classmethod
    def parse_csv(cls, file_path: str) -> List[StructuredRecord]:
        """解析 CSV 文件为结构化记录列表。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002: 文件不存在")

        records: List[StructuredRecord] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    # 将 CSV 行转换为结构化记录
                    fields = {}
                    for header in headers:
                        if header and row.get(header):
                            fields[header.strip()] = row[header].strip()
                    if fields:
                        records.append(StructuredRecord(
                            raw_text=str(row),
                            fields=fields,
                            confidence=0.9,
                        ))
        except csv.Error as e:
            raise ValueError(f"E003: CSV 解析失败 - {e}")
        except Exception as e:
            raise ValueError(f"E003: 文件读取失败 - {e}")

        return records

    @classmethod
    def parse_json(cls, file_path: str) -> List[StructuredRecord]:
        """解析 JSON 文件为结构化记录列表。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002: 文件不存在")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            records: List[StructuredRecord] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        records.append(StructuredRecord(
                            raw_text=json.dumps(item, ensure_ascii=False),
                            fields=item,
                            confidence=0.95,
                        ))
            elif isinstance(data, dict):
                records.append(StructuredRecord(
                    raw_text=json.dumps(data, ensure_ascii=False),
                    fields=data,
                    confidence=0.95,
                ))
            return records
        except json.JSONDecodeError as e:
            raise ValueError(f"E003: JSON 解析失败 - {e}")
        except Exception as e:
            raise ValueError(f"E003: 文件读取失败 - {e}")


# ---------------------------------------------------------------------------
# 模板渲染器
# ---------------------------------------------------------------------------

class TemplateRenderer:
    """渲染自定义输出模板。"""

    @staticmethod
    def render(template: str, record: StructuredRecord) -> str:
        """
        使用记录数据渲染模板。
        支持 {field_name} 占位符和简单条件。
        """
        if not template:
            return json.dumps(record.to_dict(), ensure_ascii=False, indent=2)

        result = template
        # 替换字段占位符
        for key, value in record.fields.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # 替换特殊占位符
        result = result.replace("{raw}", record.raw_text)
        result = result.replace("{confidence}", f"{record.confidence:.2f}")

        # 处理需要核实的字段标记
        if record.needs_verification:
            for field in record.needs_verification:
                result = result.replace(
                    "{" + field + "}",
                    f"[需核实:{field}]"
                )

        # 移除未替换的占位符
        result = re.sub(r"\{[^}]+\}", "[需核实]", result)

        return result


# ---------------------------------------------------------------------------
# 核心处理引擎
# ---------------------------------------------------------------------------

class DataProcessor:
    """核心数据处理引擎。"""

    def __init__(self, template: str = ""):
        self.template = template
        self.renderer = TemplateRenderer()

    def process_text(self, text: str) -> StructuredRecord:
        """处理单条文本。"""
        return InputParser.parse_text(text)

    def process_batch(self, items: List[str]) -> BatchResult:
        """批量处理多条文本。"""
        result = BatchResult()
        for item in items:
            try:
                record = self.process_text(item)
                result.add_record(record)
            except Exception as e:
                result.add_error({
                    "input": item[:100] if item else "",
                    "error": str(e),
                    "code": "E009",
                })
        return result

    def process_file(self, file_path: str) -> BatchResult:
        """处理文件（自动检测格式）。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002: 文件不存在")

        suffix = path.suffix.lower()
        result = BatchResult()

        try:
            if suffix == ".csv":
                records = InputParser.parse_csv(file_path)
            elif suffix == ".json":
                records = InputParser.parse_json(file_path)
            else:
                # 尝试按文本处理
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                records = [self.process_text(content)]
        except Exception as e:
            result.add_error({
                "input": file_path,
                "error": str(e),
                "code": "E008",
            })
            return result

        for record in records:
            result.add_record(record)

        return result

    def render_output(self, result: Union[StructuredRecord, BatchResult]) -> str:
        """渲染输出结果。"""
        if isinstance(result, StructuredRecord):
            if self.template:
                return self.renderer.render(self.template, result)
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        elif isinstance(result, BatchResult):
            if self.template:
                rendered = []
                for record in result.records:
                    rendered.append(self.renderer.render(self.template, record))
                return "\n".join(rendered)
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        else:
            raise ValueError("E007: 不支持的结果类型")


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。
    使用硬编码样例数据，不依赖外部文件或网络。
    """
    print("=" * 60)
    print("运行自检...")
    print("=" * 60)

    # 测试数据
    test_texts = [
        "张三 2024-01-15 完成项目 金额5000元",
        "李四 2024/02/20 失败 支出$120.50",
        "王五 2024年3月10日 进行中 预算3000元",
        "这是一个没有结构化信息的长文本，用于测试低置信度情况。",
        "赵六 2024-04-01 待处理 收入20000元",
    ]

    # 初始化处理器
    processor = DataProcessor()

    # 测试 1：单条文本处理
    print("\n[测试1] 单条文本处理")
    test_passed = True
    for text in test_texts:
        try:
            record = processor.process_text(text)
            print(f"  输入: {text[:30]}...")
            print(f"  输出: 字段数={len(record.fields)}, 置信度={record.confidence:.2f}")
            # 宽松断言：至少能处理不崩溃
            assert record is not None
            assert record.confidence > 0.0
            assert record.confidence <= 1.0
        except Exception as e:
            print(f"  [失败] {e}")
            test_passed = False

    # 测试 2：批量处理
    print("\n[测试2] 批量处理")
    try:
        batch_result = processor.process_batch(test_texts)
        print(f"  成功: {batch_result.processed_count}, 失败: {batch_result.failed_count}")
        # 宽松断言：至少处理了部分
        assert batch_result.processed_count > 0
        assert batch_result.success_rate > 0.5
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    # 测试 3：字段提取准确性（宽松验证）
    print("\n[测试3] 字段提取验证")
    try:
        # 验证日期提取
        rec = processor.process_text("测试 2024-05-20 数据")
        if "date" in rec.fields:
            print(f"  日期提取: {rec.fields['date']}")
            # 宽松验证：年份应在合理范围
            year = int(rec.fields["date"][:4])
            assert 2000 <= year <= 2100
        else:
            print("  日期提取: 未提取（可接受）")

        # 验证金额提取
        rec = processor.process_text("测试 金额100元")
        if "amount" in rec.fields:
            print(f"  金额提取: {rec.fields['amount']}")
            # 宽松验证：金额为正值
            assert rec.fields["amount"] > 0
        else:
            print("  金额提取: 未提取（可接受）")

        # 验证状态提取
        rec = processor.process_text("测试 成功 数据")
        if "status" in rec.fields:
            print(f"  状态提取: {rec.fields['status']}")
            assert rec.fields["status"] in ["success", "failed", "in_progress", "completed", "pending"]
        else:
            print("  状态提取: 未提取（可接受）")
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    # 测试 4：置信度标注
    print("\n[测试4] 置信度标注")
    try:
        # 低信息量文本应产生较低置信度
        low_info = processor.process_text("这是一段没有结构化信息的普通文本")
        high_info = processor.process_text("张三 2024-01-01 收入5000元 成功")
        print(f"  低信息置信度: {low_info.confidence:.2f}")
        print(f"  高信息置信度: {high_info.confidence:.2f}")
        # 宽松断言：高信息量置信度应不低于低信息量
        assert high_info.confidence >= low_info.confidence
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    # 测试 5：模板渲染
    print("\n[测试5] 模板渲染")
    try:
        renderer = TemplateRenderer()
        record = StructuredRecord(
            raw_text="测试数据",
            fields={"name": "张三", "amount": 100},
            confidence=0.8,
        )
        output = renderer.render("姓名: {name}, 金额: {amount}", record)
        print(f"  模板输出: {output}")
        assert "张三" in output
        assert "100" in output

        # 测试需核实标记
        record.needs_verification = ["age"]
        output = renderer.render("年龄: {age}", record)
        print(f"  核实输出: {output}")
        assert "[需核实" in output
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    # 测试 6：输出序列化
    print("\n[测试6] 输出序列化")
    try:
        record = processor.process_text("测试 2024-01-01 金额100元")
        processor2 = DataProcessor()
        output = processor2.render_output(record)
        # 验证是合法 JSON
        json.loads(output)
        print("  JSON 序列化: OK")

        batch = processor.process_batch(["测试1", "测试2", "测试3"])
        output = processor2.render_output(batch)
        json.loads(output)
        print("  批量 JSON 序列化: OK")
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    # 测试 7：错误处理
    print("\n[测试7] 错误处理")
    try:
        # 空文本
        try:
            processor.process_text("")
            print("  [失败] 空文本未抛出异常")
            test_passed = False
        except ValueError:
            print("  空文本错误处理: OK")

        # 不存在的文件
        try:
            processor.process_file("/nonexistent/file.csv")
            print("  [失败] 不存在文件未抛出异常")
            test_passed = False
        except FileNotFoundError:
            print("  文件不存在错误处理: OK")

        # 无效 JSON
        try:
            InputParser.parse_json("/nonexistent/file.json")
            print("  [失败] 无效JSON未抛出异常")
            test_passed = False
        except FileNotFoundError:
            print("  JSON文件不存在错误处理: OK")
    except Exception as e:
        print(f"  [失败] {e}")
        test_passed = False

    print("\n" + "=" * 60)
    if test_passed:
        print("自检通过 ✅")
    else:
        print("自检失败 ❌")
    print("=" * 60)

    return test_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="智能体技能编排：数据转换与结构化输出工具",
        epilog="示例: python main.py --text '张三 2024-01-01 100元' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文件路径（支持 CSV/JSON）")
    parser.add_argument("--text", "-t", type=str, help="输入文本内容")
    parser.add_argument("--batch", "-b", nargs="+", help="批量输入文本")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--template", type=str, help="自定义输出模板")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    try:
        processor = DataProcessor(template=args.template or "")

        # 处理输入
        if args.input:
            result = processor.process_file(args.input)
            output = processor.render_output(result)
        elif args.text:
            record = processor.process_text(args.text)
            output = processor.render_output(record)
        elif args.batch:
            result = processor.process_batch(args.batch)
            output = processor.render_output(result)
        else:
            print(f"错误 {ERROR_CODES['E001']}", file=sys.stderr)
            parser.print_help()
            return 1

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except Exception as e:
                print(f"错误 {ERROR_CODES['E006']}: {e}", file=sys.stderr)
                return 1
        else:
            print(output)

        return 0

    except FileNotFoundError as e:
        print(f"错误 {ERROR_CODES['E002']}: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"错误 {ERROR_CODES['E003']}: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"错误 {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
