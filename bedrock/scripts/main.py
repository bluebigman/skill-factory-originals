#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bedrock 技能独立实现
功能：将任意文本数据转换为结构化结果，支持关键信息抽取、置信度标注与批量处理。
仅依赖标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_INPUT = "E001"       # 输入为空或类型错误
ERR_UNSUPPORTED_FORMAT = "E002"  # 不支持的数据格式
ERR_FIELD_CONFIG = "E003"        # 字段配置错误
ERR_BATCH_EMPTY = "E004"         # 批量处理时输入列表为空
ERR_OUTPUT_FAIL = "E005"         # 输出序列化失败
ERR_SELFTEST_FAIL = "E006"       # 自检失败
ERR_INTERNAL = "E007"            # 内部未知错误
ERR_URL_INVALID = "E008"         # URL 格式无效（本实现不访问网络）
ERR_FILE_NOT_ALLOWED = "E009"    # 不允许读取本地文件
ERR_ARGUMENT = "E010"            # 命令行参数错误


# ============================================================
# 核心数据类
# ============================================================

class FieldExtractor:
    """字段提取器：从文本中提取指定类型的字段。"""

    # 常见字段类型的正则模式
    PATTERNS = {
        "name": r"[\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9\s·]{1,30}",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        "amount": r"(?:人民币|RMB|￥|¥)?\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:元)?",
        "id": r"[A-Za-z0-9]{6,20}",
        "phone": r"1[3-9]\d{9}",
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    }

    def __init__(self, field_type: str):
        """初始化提取器。

        Args:
            field_type: 字段类型，如 'name'、'date'、'amount' 等。

        Raises:
            ValueError: 不支持的字段类型。
        """
        if field_type not in self.PATTERNS:
            raise ValueError(f"不支持的字段类型: {field_type}")
        self.field_type = field_type
        self.pattern = re.compile(self.PATTERNS[field_type])

    def extract(self, text: str) -> List[str]:
        """从文本中提取所有匹配的字段值。

        Args:
            text: 输入文本。

        Returns:
            匹配到的字段值列表。
        """
        if not text:
            return []
        matches = self.pattern.findall(text)
        # 清理结果（去除多余空白和符号）
        cleaned = []
        for m in matches:
            m = m.strip()
            if m and m not in cleaned:
                cleaned.append(m)
        return cleaned

    def extract_first(self, text: str) -> Optional[str]:
        """提取第一个匹配的字段值。

        Args:
            text: 输入文本。

        Returns:
            第一个匹配值，无匹配时返回 None。
        """
        results = self.extract(text)
        return results[0] if results else None


class ConfidenceCalculator:
    """置信度计算器：根据提取结果的特征计算置信度。"""

    # 各字段类型的置信度权重
    WEIGHTS = {
        "name": 0.8,
        "date": 0.9,
        "amount": 0.85,
        "id": 0.75,
        "phone": 0.95,
        "email": 0.95,
    }

    @classmethod
    def calculate(cls, field_type: str, value: Optional[str], text_length: int) -> str:
        """计算置信度等级（高/中/低）。

        Args:
            field_type: 字段类型。
            value: 提取到的值，None 表示未提取到。
            text_length: 输入文本长度。

        Returns:
            'high'、'medium' 或 'low'。
        """
        if value is None:
            return "low"

        base_weight = cls.WEIGHTS.get(field_type, 0.7)

        # 文本太短时降级
        if text_length < 10:
            base_weight -= 0.2
        # 文本较长时升级
        elif text_length > 100:
            base_weight += 0.1

        # 值长度合理性检查
        value_len = len(value)
        if field_type == "name" and value_len > 20:
            base_weight -= 0.1
        if field_type == "id" and value_len < 6:
            base_weight -= 0.2
        if field_type == "amount":
            # 金额需要包含数字
            if not re.search(r"\d", value):
                base_weight -= 0.3

        # 转换为等级
        base_weight = max(0.0, min(1.0, base_weight))
        if base_weight >= 0.8:
            return "high"
        elif base_weight >= 0.5:
            return "medium"
        else:
            return "low"


# ============================================================
# 核心处理器
# ============================================================

class BedrockProcessor:
    """核心处理器：将文本转换为结构化结果。"""

    # 默认字段配置
    DEFAULT_FIELDS = ["name", "date", "amount", "id", "phone", "email"]

    def __init__(self, fields: Optional[List[str]] = None):
        """初始化处理器。

        Args:
            fields: 需要提取的字段类型列表，默认使用全部字段。

        Raises:
            ValueError: 字段配置不合法。
        """
        self.fields = fields or self.DEFAULT_FIELDS.copy()
        self._validate_fields()

    def _validate_fields(self) -> None:
        """验证字段配置是否合法。

        Raises:
            ValueError: 字段配置不合法。
        """
        if not self.fields:
            raise ValueError("字段列表不能为空")
        for f in self.fields:
            if f not in FieldExtractor.PATTERNS:
                raise ValueError(f"不支持的字段类型: {f}")

    def _extract_field(self, field_type: str, text: str) -> Tuple[Optional[str], str]:
        """提取单个字段并计算置信度。

        Args:
            field_type: 字段类型。
            text: 输入文本。

        Returns:
            (字段值, 置信度等级) 元组。
        """
        extractor = FieldExtractor(field_type)
        value = extractor.extract_first(text)
        confidence = ConfidenceCalculator.calculate(field_type, value, len(text))
        return value, confidence

    def process_text(self, text: str) -> Dict[str, Any]:
        """处理单条文本，返回结构化结果。

        Args:
            text: 输入文本。

        Returns:
            结构化结果字典，包含字段值、置信度、元信息。

        Raises:
            ValueError: 输入为空或类型错误。
        """
        if not text or not isinstance(text, str):
            raise ValueError(ERR_INVALID_INPUT)

        result: Dict[str, Any] = {
            "fields": {},
            "meta": {
                "text_length": len(text),
                "processed_at": datetime.now().isoformat(),
                "field_count": len(self.fields),
            }
        }

        for field in self.fields:
            value, confidence = self._extract_field(field, text)
            result["fields"][field] = {
                "value": value,
                "confidence": confidence,
            }

        return result

    def process_batch(self, texts: List[str]) -> Dict[str, Any]:
        """批量处理多条文本。

        Args:
            texts: 文本列表。

        Returns:
            批量处理结果，包含结果列表和统计信息。

        Raises:
            ValueError: 输入列表为空或包含无效元素。
        """
        if not texts or not isinstance(texts, list):
            raise ValueError(ERR_BATCH_EMPTY)

        results = []
        success_count = 0
        error_count = 0

        for idx, text in enumerate(texts):
            try:
                item = self.process_text(text)
                item["index"] = idx
                results.append(item)
                success_count += 1
            except ValueError:
                error_count += 1
                results.append({
                    "index": idx,
                    "error": "处理失败",
                    "fields": {},
                })

        return {
            "total": len(texts),
            "success": success_count,
            "errors": error_count,
            "results": results,
        }

    def format_output(self, data: Dict[str, Any], output_format: str = "json") -> str:
        """将结构化结果格式化为指定格式。

        Args:
            data: 结构化结果。
            output_format: 输出格式，支持 'json' 和 'text'。

        Returns:
            格式化后的字符串。

        Raises:
            ValueError: 输出格式不支持或序列化失败。
        """
        if output_format == "json":
            try:
                return json.dumps(data, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                raise ValueError(ERR_OUTPUT_FAIL)
        elif output_format == "text":
            lines = []
            if "fields" in data:
                for field, info in data["fields"].items():
                    value = info.get("value", "未提取")
                    conf = info.get("confidence", "unknown")
                    lines.append(f"{field}: {value} (置信度: {conf})")
            elif "results" in data:
                # 批量结果
                for item in data["results"]:
                    lines.append(f"--- 记录 {item.get('index', '?')} ---")
                    if "fields" in item:
                        for field, info in item["fields"].items():
                            value = info.get("value", "未提取")
                            conf = info.get("confidence", "unknown")
                            lines.append(f"  {field}: {value} (置信度: {conf})")
            return "\n".join(lines)
        else:
            raise ValueError(ERR_UNSUPPORTED_FORMAT)


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。

    Returns:
        True 表示自检通过，False 表示失败。

    使用硬编码样例数据，不依赖外部文件或网络。
    """
    print("运行自检...")
    processor = BedrockProcessor()

    # 测试样例 1：包含多种字段的文本
    sample1 = "张三于2024年3月15日购买商品，金额为人民币1,234.56元，订单编号ORD2024001，联系电话13812345678"
    result1 = processor.process_text(sample1)

    # 宽松断言：name 字段应包含"张三"
    name_val = result1["fields"]["name"]["value"]
    assert name_val is not None and "张" in name_val, f"姓名提取失败: {name_val}"

    # 宽松断言：date 字段应包含 2024
    date_val = result1["fields"]["date"]["value"]
    assert date_val is not None and "2024" in date_val, f"日期提取失败: {date_val}"

    # 宽松断言：amount 字段应包含 1234
    amount_val = result1["fields"]["amount"]["value"]
    assert amount_val is not None and "1234" in amount_val, f"金额提取失败: {amount_val}"

    # 宽松断言：置信度至少为 medium
    assert result1["fields"]["name"]["confidence"] in ("high", "medium"), "置信度等级异常"

    # 测试样例 2：批量处理
    sample2 = ["项目A预算5000元，负责人李四", "项目B预算8000元，负责人王五", "无有效信息"]
    batch_result = processor.process_batch(sample2)

    # 宽松断言：批量处理总数正确
    assert batch_result["total"] == 3, f"批量总数异常: {batch_result['total']}"
    assert batch_result["success"] >= 2, f"成功数异常: {batch_result['success']}"

    # 宽松断言：第一个结果包含"项目A"
    first_item = batch_result["results"][0]
    assert "项目" in str(first_item["fields"]), "批量处理结果异常"

    # 测试样例 3：格式输出
    formatted = processor.format_output(result1, "json")
    assert formatted.startswith("{"), "JSON 输出格式异常"
    formatted_text = processor.format_output(result1, "text")
    assert "name:" in formatted_text, "文本输出格式异常"

    # 测试样例 4：空输入错误处理
    try:
        processor.process_text("")
        assert False, "空输入应抛出异常"
    except ValueError as e:
        assert str(e) == ERR_INVALID_INPUT, f"错误码异常: {e}"

    print("自检通过 ✓")
    return True


def main() -> int:
    """主入口函数。

    Returns:
        退出码，0 表示成功，非 0 表示失败。
    """
    parser = argparse.ArgumentParser(
        description="bedrock 技能：数据解析、信息抽取、结构化输出",
        epilog="示例: python main.py --text '张三 2024年3月15日 金额1000元' --fields name,date,amount"
    )
    parser.add_argument("--text", type=str, help="要处理的文本内容")
    parser.add_argument("--fields", type=str, default=None,
                        help="要提取的字段，逗号分隔，如: name,date,amount")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "text"], help="输出格式")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--batch", type=str, default=None,
                        help="批量处理，用 | 分隔多条文本")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 参数验证
    if not args.text and not args.batch:
        parser.print_help()
        return 0

    try:
        # 解析字段配置
        fields = None
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]
            if not fields:
                print(f"错误 [{ERR_FIELD_CONFIG}]: 字段配置无效")
                return 1

        processor = BedrockProcessor(fields)

        # 批量处理模式
        if args.batch:
            texts = [t.strip() for t in args.batch.split("|") if t.strip()]
            if not texts:
                print(f"错误 [{ERR_BATCH_EMPTY}]: 批量输入为空")
                return 1
            result = processor.process_batch(texts)
        else:
            result = processor.process_text(args.text)

        # 格式化输出
        output = processor.format_output(result, args.format)
        print(output)
        return 0

    except ValueError as e:
        # 错误码已在异常消息中
        print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: 内部错误 - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
