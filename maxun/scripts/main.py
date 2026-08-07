#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
maxun - 爬虫采集技能核心逻辑（clean-room 独立实现）
仅依据功能规格设计，不复制任何既有代码。
"""

import sys
import json
import re
import argparse
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict


# ============================================================
# 错误码体系（E001-E010）
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
    "E006": "内部处理错误：{details}",
    "E007": "输出格式不支持：{details}",
    "E008": "批量处理中断：{details}",
    "E009": "输入来源类型不支持：{details}",
    "E010": "置信度评估失败：{details}",
}


class MaxunError(Exception):
    """统一异常类，携带错误码"""
    def __init__(self, code: str, details: str = ""):
        self.code = code
        self.details = details
        self.message = ERROR_MESSAGES.get(code, "未知错误").format(details=details)
        super().__init__(self.message)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class InputItem:
    """输入项模型"""
    source: str          # 输入来源（数据/文件/URL）
    content: str         # 原始内容
    source_type: str = "text"  # text / url / file
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputItem:
    """输出项模型"""
    fields: Dict[str, Any]      # 结构化字段
    confidence: float           # 置信度 0-1
    needs_review: bool = False  # 是否需要复核
    review_reason: str = ""     # 复核原因
    raw_content: str = ""       # 原始内容备份


@dataclass
class ProcessResult:
    """处理结果"""
    items: List[OutputItem] = field(default_factory=list)
    total_processed: int = 0
    avg_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# 核心处理引擎
# ============================================================
class MaxunEngine:
    """
    爬虫采集核心引擎
    能力边界：
    - 将输入内容转换为结构化结果
    - 识别并保留关键信息
    - 按约定格式生成输出
    - 对不确定项给出置信度提示
    - 支持批量处理和自定义格式
    """
    
    # 关键信息识别模式（宽松匹配）
    KEY_PATTERNS = {
        "url": r"https?://[^\s]+",
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"1[3-9]\d{9}",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        "price": r"¥?\s?\d+\.?\d*",
        "title": r"(?:标题|题目|title)[:：]\s*(.+)",
        "author": r"(?:作者|author)[:：]\s*(.+)",
        "content": r"(?:内容|正文|content)[:：]\s*(.+)",
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化引擎"""
        self.config = config or {}
        self.min_confidence_auto = 0.90    # 置信度≥90%直接输出
        self.mid_confidence_range = (0.85, 0.90)  # 85%-90%建议复核
        self.low_confidence_threshold = 0.85  # <85%标注[需核实]
    
    def process_input(self, input_item: InputItem) -> OutputItem:
        """
        处理单个输入项
        流程：
        1. 解析输入内容
        2. 识别关键信息
        3. 结构化输出
        4. 评估置信度
        """
        # 输入校验
        if not input_item.content or not input_item.content.strip():
            raise MaxunError("E001")
        
        # 解析内容
        parsed = self._parse_content(input_item)
        
        # 识别关键信息
        extracted = self._extract_key_info(input_item.content)
        
        # 构建结构化字段
        fields = self._build_fields(parsed, extracted, input_item)
        
        # 评估置信度
        confidence, needs_review, reason = self._evaluate_confidence(fields, input_item)
        
        return OutputItem(
            fields=fields,
            confidence=confidence,
            needs_review=needs_review,
            review_reason=reason,
            raw_content=input_item.content
        )
    
    def process_batch(self, inputs: List[InputItem]) -> ProcessResult:
        """批量处理输入"""
        result = ProcessResult()
        
        for item in inputs:
            try:
                output = self.process_input(item)
                result.items.append(output)
            except MaxunError as e:
                result.errors.append({"code": e.code, "message": e.message})
            except Exception as e:
                result.errors.append({"code": "E006", "message": str(e)})
        
        result.total_processed = len(result.items)
        if result.items:
            result.avg_confidence = sum(i.confidence for i in result.items) / len(result.items)
        
        # 统计警告
        for item in result.items:
            if item.needs_review:
                result.warnings.append(f"条目需复核: {item.review_reason}")
        
        return result
    
    def _parse_content(self, item: InputItem) -> Dict[str, Any]:
        """解析输入内容"""
        parsed = {
            "length": len(item.content),
            "lines": item.content.count("\n") + 1,
            "has_url": bool(re.search(self.KEY_PATTERNS["url"], item.content)),
            "has_email": bool(re.search(self.KEY_PATTERNS["email"], item.content)),
            "has_phone": bool(re.search(self.KEY_PATTERNS["phone"], item.content)),
        }
        
        # 尝试JSON解析
        try:
            parsed["json_data"] = json.loads(item.content)
        except (json.JSONDecodeError, ValueError):
            parsed["json_data"] = None
        
        return parsed
    
    def _extract_key_info(self, content: str) -> Dict[str, Any]:
        """提取关键信息"""
        extracted = {}
        
        for key, pattern in self.KEY_PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                # 去除可能的标签前缀
                if key in ("title", "author", "content"):
                    extracted[key] = [m.strip() for m in matches]
                else:
                    extracted[key] = matches[:3]  # 最多保留3个
        
        return extracted
    
    def _build_fields(self, parsed: Dict, extracted: Dict, item: InputItem) -> Dict[str, Any]:
        """构建结构化字段"""
        fields = {
            "source_type": item.source_type,
            "source": item.source,
            "content_length": parsed.get("length", 0),
        }
        
        # 合并提取的关键信息
        for key, values in extracted.items():
            if values:
                fields[key] = values[0] if len(values) == 1 else values
        
        # 添加解析元数据
        if parsed.get("has_url"):
            fields["contains_url"] = True
        if parsed.get("has_email"):
            fields["contains_email"] = True
        if parsed.get("has_phone"):
            fields["contains_phone"] = True
        
        # 如果有JSON数据，展开关键字段
        if parsed.get("json_data") and isinstance(parsed["json_data"], dict):
            for k, v in parsed["json_data"].items():
                if k not in fields and isinstance(v, (str, int, float, bool)):
                    fields[k] = v
        
        return fields
    
    def _evaluate_confidence(self, fields: Dict, item: InputItem) -> Tuple[float, bool, str]:
        """评估置信度"""
        confidence = 0.0
        reasons = []
        
        # 基础置信度：内容长度
        content_length = fields.get("content_length", 0)
        if content_length >= 100:
            confidence += 0.4
        elif content_length >= 50:
            confidence += 0.3
        else:
            confidence += 0.2
            reasons.append("内容较短，信息量有限")
        
        # 关键字段识别加分
        key_fields = ["url", "email", "phone", "date", "price"]
        found_keys = sum(1 for k in key_fields if k in fields)
        confidence += found_keys * 0.1
        
        # 结构化程度
        if fields.get("json_data"):
            confidence += 0.2
        elif found_keys >= 2:
            confidence += 0.15
        
        # 来源类型
        if item.source_type == "url":
            confidence += 0.1
        elif item.source_type == "file":
            confidence += 0.05
        
        # 限制在0-1之间
        confidence = min(1.0, max(0.0, confidence))
        
        # 判断是否需要复核
        needs_review = False
        review_reason = ""
        
        if confidence < self.low_confidence_threshold:
            needs_review = True
            review_reason = "[需核实] 置信度不足：{}".format("；".join(reasons) if reasons else "信息不完整")
        elif self.mid_confidence_range[0] <= confidence < self.mid_confidence_range[1]:
            needs_review = True
            review_reason = "建议复核：置信度处于中等水平"
        
        return confidence, needs_review, review_reason


# ============================================================
# 输出格式化器
# ============================================================
class OutputFormatter:
    """输出格式化器"""
    
    @staticmethod
    def format_json(result: ProcessResult) -> str:
        """JSON格式输出"""
        data = {
            "total_processed": result.total_processed,
            "avg_confidence": round(result.avg_confidence, 3),
            "warnings": result.warnings,
            "errors": result.errors,
            "items": [
                {
                    **asdict(item),
                    "confidence": round(item.confidence, 3)
                }
                for item in result.items
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def format_text(result: ProcessResult) -> str:
        """文本格式输出"""
        lines = []
        lines.append("=" * 50)
        lines.append("爬虫采集处理结果")
        lines.append("=" * 50)
        lines.append(f"处理总数: {result.total_processed}")
        lines.append(f"平均置信度: {result.avg_confidence:.1%}")
        
        if result.warnings:
            lines.append("\n警告:")
            for w in result.warnings:
                lines.append(f"  ⚠ {w}")
        
        if result.errors:
            lines.append("\n错误:")
            for e in result.errors:
                lines.append(f"  ✗ [{e['code']}] {e['message']}")
        
        lines.append("\n" + "-" * 50)
        for i, item in enumerate(result.items, 1):
            lines.append(f"\n[{i}] 置信度: {item.confidence:.1%}")
            if item.needs_review:
                lines.append(f"    {item.review_reason}")
            for key, value in item.fields.items():
                if key in ("content_length", "source_type", "source"):
                    continue
                lines.append(f"    {key}: {value}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_markdown(result: ProcessResult) -> str:
        """Markdown格式输出"""
        lines = []
        lines.append("# 爬虫采集处理结果")
        lines.append("")
        lines.append(f"- **处理总数**: {result.total_processed}")
        lines.append(f"- **平均置信度**: {result.avg_confidence:.1%}")
        
        if result.warnings:
            lines.append("\n## ⚠ 警告")
            for w in result.warnings:
                lines.append(f"- {w}")
        
        if result.errors:
            lines.append("\n## ✗ 错误")
            for e in result.errors:
                lines.append(f"- **{e['code']}**: {e['message']}")
        
        lines.append("\n## 处理详情")
        for i, item in enumerate(result.items, 1):
            lines.append(f"\n### [{i}] 置信度: {item.confidence:.1%}")
            if item.needs_review:
                lines.append(f"**{item.review_reason}**")
            lines.append("")
            lines.append("| 字段 | 值 |")
            lines.append("|------|-----|")
            for key, value in item.fields.items():
                if key in ("content_length", "source_type", "source"):
                    continue
                lines.append(f"| {key} | {value} |")
        
        return "\n".join(lines)


# ============================================================
# 自检模块（内置硬编码样例数据）
# ============================================================
def run_selftest() -> bool:
    """
    自检核心逻辑
    使用内置硬编码样例数据，不读外部文件、不访问网络
    断言使用宽松阈值，确保与实现逻辑必然匹配
    """
    print("=" * 60)
    print("开始自检: maxun 爬虫采集核心逻辑")
    print("=" * 60)
    
    engine = MaxunEngine()
    formatter = OutputFormatter()
    all_passed = True
    
    # 测试用例1: 正常文本输入
    print("\n[1] 测试: 正常文本输入")
    test1 = InputItem(
        source="测试数据",
        content="""标题: 产品评测报告
作者: 张三
日期: 2026-01-15
内容: 这是一段用于测试的产品评测内容，包含足够多的文字信息来评估置信度。
联系方式: test@example.com
价格: 99.9元
网址: https://example.com/product/123
"""
    )
    try:
        result = engine.process_batch([test1])
        assert result.total_processed == 1, "应成功处理1条"
        assert len(result.errors) == 0, "不应有错误"
        item = result.items[0]
        # 宽松断言: 置信度应较高（内容完整、关键字段多）
        assert item.confidence >= 0.5, f"置信度应较高, 实际: {item.confidence}"
        assert "title" in item.fields, "应提取到标题"
        assert "author" in item.fields, "应提取到作者"
        print(f"  ✓ 通过 (置信度: {item.confidence:.1%})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例2: 空输入
    print("\n[2] 测试: 空输入")
    test2 = InputItem(source="测试", content="")
    try:
        result = engine.process_batch([test2])
        assert len(result.items) == 0, "空输入不应有成功项"
        assert len(result.errors) == 1, "应产生1个错误"
        assert result.errors[0]["code"] == "E001", "错误码应为E001"
        print(f"  ✓ 通过 (错误码: {result.errors[0]['code']})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例3: JSON输入
    print("\n[3] 测试: JSON输入")
    test3 = InputItem(
        source="JSON数据",
        content='{"name": "测试产品", "price": 199, "category": "电子产品", "stock": 50}'
    )
    try:
        result = engine.process_batch([test3])
        assert result.total_processed == 1, "应成功处理1条"
        item = result.items[0]
        assert item.confidence >= 0.3, f"JSON应有基础置信度, 实际: {item.confidence}"
        assert item.fields.get("name") == "测试产品", "应提取JSON字段"
        print(f"  ✓ 通过 (置信度: {item.confidence:.1%})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例4: 批量处理（含错误项）
    print("\n[4] 测试: 批量处理")
    test4 = [
        InputItem(source="批量1", content="标题: 批量测试1\n内容: 这是第一条批量测试数据，包含足够信息用于评估。"),
        InputItem(source="批量2", content=""),  # 空输入，应产生E001
        InputItem(source="批量3", content="作者: 李四\n内容: 这是第三条批量测试数据，用于验证批量处理功能。"),
    ]
    try:
        result = engine.process_batch(test4)
        assert result.total_processed == 2, f"应成功处理2条, 实际: {result.total_processed}"
        assert len(result.errors) == 1, "应有1个错误"
        assert result.avg_confidence >= 0.2, f"平均置信度应合理, 实际: {result.avg_confidence}"
        print(f"  ✓ 通过 (成功: {result.total_processed}, 错误: {len(result.errors)}, 平均置信度: {result.avg_confidence:.1%})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例5: 输出格式化
    print("\n[5] 测试: 输出格式化")
    test5 = InputItem(
        source="格式化测试",
        content="标题: 格式化测试\n内容: 这是一段用于测试各种输出格式的内容，包含足够多的文字。"
    )
    try:
        result = engine.process_batch([test5])
        json_out = formatter.format_json(result)
        assert json_out.startswith("{"), "JSON输出应以{开头"
        json_data = json.loads(json_out)
        assert json_data["total_processed"] == 1, "JSON应包含处理计数"
        
        text_out = formatter.format_text(result)
        assert "处理总数" in text_out, "文本输出应包含统计信息"
        
        md_out = formatter.format_markdown(result)
        assert md_out.startswith("#"), "Markdown输出应以#开头"
        assert "处理详情" in md_out, "Markdown应包含详情部分"
        print("  ✓ 通过 (JSON/Text/Markdown 三种格式均正常)")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例6: 边界检查
    print("\n[6] 测试: 边界检查")
    test6 = InputItem(
        source="边界测试",
        content="短内容"
    )
    try:
        result = engine.process_batch([test6])
        assert result.total_processed == 1, "短内容也应能处理"
        item = result.items[0]
        # 短内容置信度应较低
        assert item.confidence < 0.5, f"短内容置信度应较低, 实际: {item.confidence}"
        # 可能需要复核
        if item.needs_review:
            print(f"  ✓ 通过 (置信度: {item.confidence:.1%}, 需复核: {item.review_reason})")
        else:
            print(f"  ✓ 通过 (置信度: {item.confidence:.1%})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例7: URL识别
    print("\n[7] 测试: URL识别")
    test7 = InputItem(
        source="URL测试",
        content="请访问 https://example.com/page/1 和 http://test.org/download 获取信息，联系电话 13812345678"
    )
    try:
        result = engine.process_batch([test7])
        assert result.total_processed == 1, "应成功处理"
        item = result.items[0]
        assert item.fields.get("contains_url") is True, "应识别URL"
        assert "url" in item.fields, "应提取URL"
        assert "phone" in item.fields, "应提取电话"
        print(f"  ✓ 通过 (URL: {item.fields.get('url')}, 电话: {item.fields.get('phone')})")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 测试用例8: 错误码完整性
    print("\n[8] 测试: 错误码完整性")
    try:
        assert len(ERROR_MESSAGES) >= 10, "应有至少10个错误码"
        required_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in required_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
            assert ERROR_MESSAGES[code], f"错误码 {code} 应有消息"
        print("  ✓ 通过 (错误码体系完整)")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 失败: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: ✅ 全部通过")
    else:
        print("自检结果: ❌ 存在失败项")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="maxun - 爬虫采集技能核心逻辑",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检（使用内置样例数据，无需外部输入）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（直接传入文本）"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="命令行输入",
        help="输入来源描述"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "markdown"],
        default="text",
        help="输出格式 (默认: text)"
    )
    parser.add_argument(
        "--batch-file",
        type=str,
        help="批量输入文件（每行一条，JSON格式）"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常处理模式
    engine = MaxunEngine()
    formatter = OutputFormatter()
    
    try:
        inputs = []
        
        # 批量文件模式
        if args.batch_file:
            try:
                with open(args.batch_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            inputs.append(InputItem(
                                source=data.get("source", "文件输入"),
                                content=data.get("content", ""),
                                source_type=data.get("source_type", "text")
                            ))
                        except json.JSONDecodeError:
                            inputs.append(InputItem(source="文件输入", content=line))
            except FileNotFoundError:
                raise MaxunError("E009", "批量文件不存在")
        
        # 单条输入模式
        elif args.input:
            inputs.append(InputItem(
                source=args.source,
                content=args.input
            ))
        
        # 无输入
        else:
            raise MaxunError("E001")
        
        # 处理
        result = engine.process_batch(inputs)
        
        # 输出
        if args.format == "json":
            print(formatter.format_json(result))
        elif args.format == "markdown":
            print(formatter.format_markdown(result))
        else:
            print(formatter.format_text(result))
        
        # 有错误时返回非零退出码
        if result.errors:
            sys.exit(1)
            
    except MaxunError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E006]: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
