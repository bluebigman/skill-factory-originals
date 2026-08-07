#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
marketingskills - 营销技能工具（独立实现）

基于功能规格的 clean-room 实现，不依赖任何既有代码。
提供营销相关的数据解析、结构化和置信度评估能力。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "数据解析失败，请检查输入",
    "E007": "输出格式不支持",
    "E008": "批量处理中断",
    "E009": "内部状态异常",
    "E010": "参数校验失败",
}


class MarketingSkillError(Exception):
    """营销技能自定义异常"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class ParsedItem:
    """解析后的结构化数据项"""
    def __init__(self, item_id: str, content: str, fields: Dict[str, Any], confidence: float):
        self.item_id = item_id
        self.content = content
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.item_id,
            "content": self.content,
            "fields": self.fields,
            "confidence": self.confidence,
            "needs_review": self.confidence < 0.90,
            "uncertain": self.confidence < 0.85,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
class MarketingSkillProcessor:
    """营销技能核心处理器"""

    def __init__(self):
        """初始化处理器"""
        self.supported_formats = ["json", "text", "csv"]
        self.batch_limit = 100

    def process_input(self, raw_input: str, output_format: str = "json") -> Dict[str, Any]:
        """
        处理用户输入，转换为结构化结果

        Args:
            raw_input: 原始输入内容
            output_format: 输出格式（json/text/csv）

        Returns:
            处理结果字典

        Raises:
            MarketingSkillError: 处理失败时抛出
        """
        # 参数校验
        if not raw_input or not raw_input.strip():
            raise MarketingSkillError("E001")

        if output_format not in self.supported_formats:
            raise MarketingSkillError("E007", f"不支持的输出格式: {output_format}")

        # 解析输入
        try:
            items = self._parse_input(raw_input)
        except Exception as e:
            raise MarketingSkillError("E006", f"解析失败: {str(e)}")

        if not items:
            raise MarketingSkillError("E001")

        # 处理每个条目
        results = []
        for item in items:
            try:
                parsed = self._process_single_item(item)
                results.append(parsed)
            except MarketingSkillError:
                raise
            except Exception as e:
                raise MarketingSkillError("E009", f"处理条目失败: {str(e)}")

        # 生成输出
        output = self._generate_output(results, output_format)
        return {
            "success": True,
            "count": len(results),
            "format": output_format,
            "data": output,
            "summary": self._generate_summary(results),
        }

    def _parse_input(self, raw_input: str) -> List[str]:
        """解析输入为条目列表"""
        # 尝试 JSON 数组
        try:
            data = json.loads(raw_input)
            if isinstance(data, list):
                return [str(x) for x in data]
            elif isinstance(data, dict):
                return [json.dumps(data)]
        except json.JSONDecodeError:
            pass

        # 按行分割
        lines = [line.strip() for line in raw_input.split("\n") if line.strip()]
        if lines:
            return lines

        # 单条内容
        return [raw_input.strip()]

    def _process_single_item(self, content: str) -> ParsedItem:
        """处理单个条目"""
        # 提取关键信息
        fields = self._extract_fields(content)

        # 计算置信度
        confidence = self._calculate_confidence(content, fields)

        # 生成唯一 ID
        item_id = f"item_{len(content)}_{hash(content) % 10000:04d}"

        return ParsedItem(item_id, content, fields, confidence)

    def _extract_fields(self, content: str) -> Dict[str, Any]:
        """从内容中提取关键字段"""
        fields = {}

        # 提取名称（尝试匹配常见模式）
        name_patterns = [
            r"名称[:：]\s*(\S+)",
            r"name[:：]\s*(\S+)",
            r"标题[:：]\s*(\S+)",
            r"产品名称[:：]\s*(\S+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fields["name"] = match.group(1)
                break

        # 提取价格（多种格式）
        price_patterns = [
            r"价格[:：]\s*(\d+\.?\d*)",
            r"售价[:：]\s*(\d+\.?\d*)",
            r"price[:：]\s*(\d+\.?\d*)",
            r"金额[:：]\s*(\d+\.?\d*)",
            r"¥\s*(\d+\.?\d*)",
            r"￥\s*(\d+\.?\d*)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fields["价格"] = float(match.group(1))
                break

        # 提取数量
        quantity_patterns = [
            r"数量[:：]\s*(\d+)",
            r"quantity[:：]\s*(\d+)",
            r"库存[:：]\s*(\d+)",
        ]
        for pattern in quantity_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fields["数量"] = int(match.group(1))
                break

        # 提取 URL
        url_match = re.search(r"https?://\S+", content)
        if url_match:
            fields["url"] = url_match.group(0)

        # 提取邮箱
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", content)
        if email_match:
            fields["email"] = email_match.group(0)

        # 提取关键词
        keywords = re.findall(r"#(\w+)", content)
        if keywords:
            fields["keywords"] = keywords

        # 提取标签
        tags = re.findall(r"@(\w+)", content)
        if tags:
            fields["tags"] = tags

        # 提取日期
        date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", content)
        if date_match:
            fields["date"] = date_match.group(1)

        return fields

    def _calculate_confidence(self, content: str, fields: Dict[str, Any]) -> float:
        """计算处理置信度"""
        confidence = 0.90  # 基础置信度

        # 内容长度影响
        content_len = len(content.strip())
        if content_len < 10:
            confidence -= 0.10  # 内容过短，降低置信度
        elif content_len < 50:
            confidence -= 0.05

        # 字段丰富度影响
        field_count = len(fields)
        if field_count == 0:
            confidence -= 0.15  # 未提取到字段
        elif field_count < 2:
            confidence -= 0.05

        # 特殊标记影响
        if "[需核实]" in content:
            confidence -= 0.10
        if "不确定" in content or "可能" in content:
            confidence -= 0.05

        # 限制在 0.5-0.99 之间
        return max(0.50, min(0.99, confidence))

    def _generate_output(self, items: List[ParsedItem], output_format: str) -> Any:
        """生成输出"""
        if output_format == "json":
            return [item.to_dict() for item in items]
        elif output_format == "text":
            return self._format_text(items)
        elif output_format == "csv":
            return self._format_csv(items)
        return items

    def _format_text(self, items: List[ParsedItem]) -> str:
        """格式化文本输出"""
        lines = []
        for item in items:
            lines.append(f"ID: {item.item_id}")
            lines.append(f"内容: {item.content}")
            lines.append(f"置信度: {item.confidence:.0%}")
            if item.fields:
                lines.append("字段:")
                for key, value in item.fields.items():
                    lines.append(f"  - {key}: {value}")
            if item.confidence < 0.85:
                lines.append("[需核实]")
            elif item.confidence < 0.90:
                lines.append("建议复核")
            lines.append("---")
        return "\n".join(lines)

    def _format_csv(self, items: List[ParsedItem]) -> str:
        """格式化 CSV 输出"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "内容", "置信度", "字段", "标记"])

        for item in items:
            fields_str = "; ".join(f"{k}={v}" for k, v in item.fields.items())
            mark = ""
            if item.confidence < 0.85:
                mark = "[需核实]"
            elif item.confidence < 0.90:
                mark = "建议复核"
            writer.writerow([item.item_id, item.content, f"{item.confidence:.0%}", fields_str, mark])

        return output.getvalue()

    def _generate_summary(self, items: List[ParsedItem]) -> Dict[str, Any]:
        """生成摘要信息"""
        total = len(items)
        high_conf = sum(1 for i in items if i.confidence >= 0.90)
        medium_conf = sum(1 for i in items if 0.85 <= i.confidence < 0.90)
        low_conf = sum(1 for i in items if i.confidence < 0.85)

        return {
            "总条目数": total,
            "高置信度": high_conf,
            "中置信度": medium_conf,
            "低置信度": low_conf,
            "需复核": medium_conf + low_conf,
            "需核实": low_conf,
        }


# ============================================================
# 批量处理
# ============================================================
def batch_process(items: List[str], output_format: str = "json") -> Dict[str, Any]:
    """
    批量处理多个条目

    Args:
        items: 条目列表
        output_format: 输出格式

    Returns:
        处理结果
    """
    processor = MarketingSkillProcessor()
    results = []

    for idx, item in enumerate(items):
        if idx >= processor.batch_limit:
            raise MarketingSkillError("E008", f"超出批量限制（{processor.batch_limit}条）")

        try:
            result = processor.process_input(item, output_format)
            results.append({
                "index": idx + 1,
                "input": item,
                "success": True,
                "data": result["data"],
            })
        except MarketingSkillError as e:
            results.append({
                "index": idx + 1,
                "input": item,
                "success": False,
                "error": str(e),
            })

    return {
        "success": all(r["success"] for r in results),
        "total": len(results),
        "succeeded": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据离线验证核心功能。

    Returns:
        True 表示自检通过
    """
    print("开始自检...")

    # 测试样例（硬编码，不依赖外部文件）
    test_cases = [
        {
            "name": "基础文本处理",
            "input": "产品名称: 智能手表\n价格: 299\n#科技 #穿戴",
            "expected_fields": ["name", "价格", "keywords"],
        },
        {
            "name": "URL处理",
            "input": "查看详情 https://example.com/product/123 联系 support@example.com",
            "expected_fields": ["url", "email"],
        },
        {
            "name": "空输入处理",
            "input": "",
            "expect_error": "E001",
        },
        {
            "name": "JSON数组输入",
            "input": '["第一条内容", "第二条内容 #测试"]',
            "expect_count": 2,
        },
    ]

    processor = MarketingSkillProcessor()
    all_passed = True

    for idx, case in enumerate(test_cases, 1):
        print(f"  测试用例 {idx}: {case['name']}", end=" ")

        try:
            # 处理输入
            if "expect_error" in case:
                # 预期错误场景
                try:
                    processor.process_input(case["input"])
                    print("失败 - 未抛出预期错误")
                    all_passed = False
                except MarketingSkillError as e:
                    if e.code == case["expect_error"]:
                        print("通过")
                    else:
                        print(f"失败 - 错误码不匹配: {e.code}")
                        all_passed = False
            else:
                # 正常处理场景
                result = processor.process_input(case["input"])

                # 宽松断言：只检查关键特征
                assert result["success"] is True, "处理失败"

                # 检查条目数量
                if "expect_count" in case:
                    assert result["count"] == case["expect_count"], \
                        f"条目数量不符: {result['count']} != {case['expect_count']}"

                # 检查字段提取（宽松检查）
                if "expected_fields" in case:
                    data = result["data"]
                    assert isinstance(data, list) and len(data) > 0, "数据为空"
                    first_item = data[0]
                    fields = first_item.get("fields", {})

                    for field in case["expected_fields"]:
                        # 宽松检查：字段存在即可，不检查具体值
                        assert field in fields or any(field in k for k in fields.keys()), \
                            f"缺少字段: {field}"

                # 检查置信度范围（宽松检查）
                for item in result["data"]:
                    conf = item.get("confidence", 0)
                    assert 0.0 <= conf <= 1.0, f"置信度超出范围: {conf}"
                    # 检查标记逻辑
                    if conf < 0.85:
                        assert item.get("uncertain") is True, "低置信度未标记"
                    elif conf < 0.90:
                        assert item.get("needs_review") is True, "中置信度未标记复核"

                print("通过")

        except AssertionError as e:
            print(f"失败 - 断言错误: {str(e)}")
            all_passed = False
        except Exception as e:
            print(f"失败 - 异常: {str(e)}")
            all_passed = False

    # 批量处理测试
    print("  测试批量处理...", end=" ")
    try:
        batch_items = ["第一条 #A", "第二条 #B", "第三条 #C"]
        batch_result = batch_process(batch_items)
        assert batch_result["success"] is True, "批量处理失败"
        assert batch_result["total"] == 3, "批量处理数量不符"
        assert batch_result["succeeded"] == 3, "批量处理成功数不符"
        print("通过")
    except AssertionError as e:
        print(f"失败 - {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"失败 - 异常: {str(e)}")
        all_passed = False

    # 输出格式测试
    print("  测试输出格式...", end=" ")
    try:
        result = processor.process_input("测试内容 #格式", "text")
        assert isinstance(result["data"], str), "文本格式输出类型错误"
        assert "测试内容" in result["data"], "文本输出内容缺失"

        result = processor.process_input("测试内容 #格式", "csv")
        assert isinstance(result["data"], str), "CSV格式输出类型错误"
        assert "ID" in result["data"], "CSV输出缺少表头"
        print("通过")
    except AssertionError as e:
        print(f"失败 - {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"失败 - 异常: {str(e)}")
        all_passed = False

    # 错误处理测试
    print("  测试错误处理...", end=" ")
    try:
        # 空输入
        try:
            processor.process_input("")
            print("失败 - 空输入未报错")
            all_passed = False
        except MarketingSkillError as e:
            assert e.code == "E001", f"错误码不符: {e.code}"

        # 不支持的格式
        try:
            processor.process_input("测试", "xml")
            print("失败 - 不支持的格式未报错")
            all_passed = False
        except MarketingSkillError as e:
            assert e.code == "E007", f"错误码不符: {e.code}"

        print("通过")
    except AssertionError as e:
        print(f"失败 - {str(e)}")
        all_passed = False
    except Exception as e:
        print(f"失败 - 异常: {str(e)}")
        all_passed = False

    # 错误码完整性测试
    print("  测试错误码完整性...", end=" ")
    try:
        assert len(ERROR_CODES) == 10, f"错误码数量不符: {len(ERROR_CODES)}"
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码: {code}"
        print("通过")
    except AssertionError as e:
        print(f"失败 - {str(e)}")
        all_passed = False

    print(f"\n自检完成: {'全部通过' if all_passed else '存在失败项'}")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="marketingskills - 营销技能工具",
        epilog="示例: python main.py --input '产品名称: 手机' --format json"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（文本或JSON）"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入"
    )

    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式（默认: json）"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（按行分割输入）"
    )

    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="列出支持的输出格式"
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

    # 列出格式
    if args.list_formats:
        print("支持的输出格式:")
        for fmt in ["json", "text", "csv"]:
            print(f"  - {fmt}")
        sys.exit(0)

    # 获取输入
    input_content = args.input
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                input_content = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            sys.exit(1)

    if not input_content:
        parser.print_help()
        sys.exit(1)

    # 处理输入
    try:
        processor = MarketingSkillProcessor()

        if args.batch:
            # 批量处理
            items = [line.strip() for line in input_content.split("\n") if line.strip()]
            result = batch_process(items, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 单条处理
            result = processor.process_input(input_content, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except MarketingSkillError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 未预期异常 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
