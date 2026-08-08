#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
angreal - 未命名工具（仅供学习与参考用途）

一个通用数据处理工具，用于将用户提供的数据/文件/URL 转换为结构化结果。
本实现为 clean-room 独立重写，仅依据功能规格开发。
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
}


class AngrealError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessedItem:
    """单条处理结果。"""

    original: str                # 原始输入
    extracted: Dict[str, str]    # 提取的关键字段
    confidence: float            # 置信度 0~1
    flags: List[str] = field(default_factory=list)  # 标注（如"建议复核"）


@dataclass
class ProcessResult:
    """整体处理结果。"""

    items: List[ProcessedItem]
    total: int
    success: int


# ============================================================
# 核心处理逻辑
# ============================================================
class AngrealProcessor:
    """核心处理器：解析输入、提取信息、计算置信度。"""

    # 常见字段模式（用于从文本中提取关键信息）
    FIELD_PATTERNS = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "url": r"https?://[^\s]+",
        "phone": r"1[3-9]\d{9}",  # 中国大陆手机号
        "date": r"\d{4}-\d{1,2}-\d{1,2}",
    }

    def process(self, inputs: List[str]) -> ProcessResult:
        """处理一批输入，返回结构化结果。"""
        if not inputs:
            raise AngrealError("E001")

        items = []
        success = 0
        for raw in inputs:
            item = self._process_single(raw)
            items.append(item)
            if item.confidence >= 0.85:
                success += 1
        return ProcessResult(items=items, total=len(items), success=success)

    def _process_single(self, raw: str) -> ProcessedItem:
        """处理单条输入。"""
        raw = raw.strip()
        if not raw:
            raise AngrealError("E001")

        # 提取关键字段
        extracted = self._extract_fields(raw)
        if not extracted:
            # 无法提取任何字段：输入格式不符合要求
            raise AngrealError("E003", example="包含邮箱、URL、手机号或日期的文本")

        # 计算置信度
        confidence = self._calc_confidence(raw, extracted)

        # 生成标注
        flags = []
        if confidence < 0.85:
            flags.append("[需核实]")
        elif confidence < 0.90:
            flags.append("建议复核")

        return ProcessedItem(
            original=raw,
            extracted=extracted,
            confidence=confidence,
            flags=flags,
        )

    def _extract_fields(self, text: str) -> Dict[str, str]:
        """从文本中提取关键字段。"""
        result = {}
        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                result[field_name] = match.group(0)
        return result

    def _calc_confidence(self, text: str, extracted: Dict[str, str]) -> float:
        """
        计算置信度（0~1）。
        规则（宽松）：
        - 提取到至少一个字段：0.80 基础分
        - 每多一个字段：+0.05
        - 文本长度 ≥ 10：+0.05
        - 文本长度 ≥ 30：额外 +0.05
        - 上限 0.98
        """
        base = 0.80
        bonus = min(0.10, 0.05 * (len(extracted) - 1))  # 多字段奖励
        length_bonus = 0.05 if len(text) >= 10 else 0.0
        length_bonus2 = 0.05 if len(text) >= 30 else 0.0
        return min(0.98, base + bonus + length_bonus + length_bonus2)

    def format_output(self, result: ProcessResult, fmt: str = "text") -> str:
        """按指定格式输出结果。"""
        if fmt == "json":
            return self._format_json(result)
        return self._format_text(result)

    def _format_text(self, result: ProcessResult) -> str:
        """文本格式输出。"""
        lines = []
        lines.append(f"处理完成：共 {result.total} 条，成功 {result.success} 条")
        lines.append("-" * 50)
        for i, item in enumerate(result.items, 1):
            lines.append(f"[{i}] 原始输入：{item.original}")
            for k, v in item.extracted.items():
                lines.append(f"    {k}: {v}")
            conf_pct = f"{item.confidence * 100:.1f}%"
            flag_str = " ".join(item.flags) if item.flags else ""
            lines.append(f"    置信度：{conf_pct} {flag_str}")
            lines.append("")
        return "\n".join(lines)

    def _format_json(self, result: ProcessResult) -> str:
        """JSON 格式输出（标准库实现）。"""
        import json

        payload = {
            "total": result.total,
            "success": result.success,
            "items": [
                {
                    "original": it.original,
                    "extracted": it.extracted,
                    "confidence": round(it.confidence, 4),
                    "flags": it.flags,
                }
                for it in result.items
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


# ============================================================
# 批量处理支持
# ============================================================
def batch_process(
    processor: AngrealProcessor,
    inputs: List[str],
    output_format: str = "text",
) -> str:
    """批量处理入口。"""
    result = processor.process(inputs)
    return processor.format_output(result, output_format)


# ============================================================
# 自检（selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例，离线自检核心逻辑。
    所有断言使用宽松阈值，不依赖精确值。
    """
    print("[selftest] 开始自检...")
    processor = AngrealProcessor()

    # --- 测试用例 1：正常输入 ---
    sample_1 = [
        "联系我：test@example.com，电话 13812345678",
        "访问 https://example.com 获取更多信息",
        "日期 2026-03-15 截止",
    ]
    try:
        result = processor.process(sample_1)
        assert result.total == 3, "应处理 3 条输入"
        assert result.success >= 2, "至少 2 条应达到成功阈值"
        # 验证字段提取
        assert any("email" in it.extracted for it in result.items), "应提取到 email"
        assert any("url" in it.extracted for it in result.items), "应提取到 url"
        assert any("date" in it.extracted for it in result.items), "应提取到 date"
        # 置信度应在合理区间
        for it in result.items:
            assert 0.0 <= it.confidence <= 1.0, "置信度应在 0~1 之间"
        print("  测试1（正常输入）通过")
    except AssertionError as e:
        print(f"  测试1失败：{e}")
        return 1

    # --- 测试用例 2：空输入应报 E001 ---
    try:
        processor.process([])
        print("  测试2（空输入）失败：未抛出异常")
        return 1
    except AngrealError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  测试2（空输入）通过")

    # --- 测试用例 3：无法提取字段应报 E003 ---
    try:
        processor.process(["这是一段没有关键信息的纯文本"])
        print("  测试3（无字段输入）失败：未抛出异常")
        return 1
    except AngrealError as e:
        assert e.code == "E003", f"错误码应为 E003，实际 {e.code}"
        print("  测试3（无字段输入）通过")

    # --- 测试用例 4：输出格式 ---
    sample_4 = ["测试邮箱 a@b.com"]
    result_4 = processor.process(sample_4)
    text_out = processor.format_output(result_4, "text")
    json_out = processor.format_output(result_4, "json")
    assert "置信度" in text_out, "文本输出应包含置信度"
    assert '"total"' in json_out, "JSON 输出应包含 total 字段"
    assert '"items"' in json_out, "JSON 输出应包含 items 字段"
    print("  测试4（输出格式）通过")

    # --- 测试用例 5：批量处理 ---
    sample_5 = ["电话 13912345678", "https://a.com", "混合内容 test@x.com 和 13800001111"]
    out_5 = batch_process(processor, sample_5, "json")
    assert '"total": 3' in out_5, "批量处理 JSON 应包含 total=3"
    print("  测试5（批量处理）通过")

    # --- 测试用例 6：置信度标注 ---
    sample_6 = ["简单邮箱 a@b.com"]  # 短文本，置信度应较低
    result_6 = processor.process(sample_6)
    it_6 = result_6.items[0]
    # 短文本置信度不应过高
    assert it_6.confidence < 0.90, "短文本置信度应低于 0.90"
    print("  测试6（置信度标注）通过")

    # --- 测试用例 7：空字符串输入应报 E001 ---
    try:
        processor.process([""])
        print("  测试7（空字符串输入）失败：未抛出异常")
        return 1
    except AngrealError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  测试7（空字符串输入）通过")

    # --- 测试用例 8：混合有效和无效输入 ---
    try:
        processor.process(["有效邮箱 a@b.com", "无效文本"])
        print("  测试8（混合输入）失败：未抛出异常")
        return 1
    except AngrealError as e:
        assert e.code == "E003", f"错误码应为 E003，实际 {e.code}"
        print("  测试8（混合输入）通过")

    # --- 测试用例 9：多字段提取 ---
    sample_9 = ["联系 test@example.com 或 13812345678，日期 2026-03-15"]
    result_9 = processor.process(sample_9)
    it_9 = result_9.items[0]
    assert len(it_9.extracted) >= 3, "应提取至少 3 个字段"
    assert it_9.confidence >= 0.90, "多字段置信度应较高"
    print("  测试9（多字段提取）通过")

    # --- 测试用例 10：URL 提取 ---
    sample_10 = ["访问 https://example.com/path?query=1 获取信息"]
    result_10 = processor.process(sample_10)
    it_10 = result_10.items[0]
    assert "url" in it_10.extracted, "应提取到 url"
    assert it_10.extracted["url"] == "https://example.com/path?query=1", "URL 提取不完整"
    print("  测试10（URL 提取）通过")

    # --- 测试用例 11：手机号提取 ---
    sample_11 = ["联系电话 13912345678"]
    result_11 = processor.process(sample_11)
    it_11 = result_11.items[0]
    assert "phone" in it_11.extracted, "应提取到 phone"
    assert it_11.extracted["phone"] == "13912345678", "手机号提取错误"
    print("  测试11（手机号提取）通过")

    # --- 测试用例 12：日期提取 ---
    sample_12 = ["截止日期 2026-12-31"]
    result_12 = processor.process(sample_12)
    it_12 = result_12.items[0]
    assert "date" in it_12.extracted, "应提取到 date"
    assert it_12.extracted["date"] == "2026-12-31", "日期提取错误"
    print("  测试12（日期提取）通过")

    # --- 测试用例 13：置信度上限 ---
    sample_13 = ["这是一个很长的文本，包含多个字段：test@example.com 和 13812345678，日期 2026-03-15，还有 https://example.com 这个链接，内容足够长以触发所有置信度加成"]
    result_13 = processor.process(sample_13)
    it_13 = result_13.items[0]
    assert it_13.confidence <= 0.98, "置信度不应超过 0.98"
    assert it_13.confidence >= 0.95, "长文本多字段置信度应较高"
    print("  测试13（置信度上限）通过")

    # --- 测试用例 14：flags 标注 ---
    sample_14 = ["简单邮箱 a@b.com"]  # 短文本，置信度应较低
    result_14 = processor.process(sample_14)
    it_14 = result_14.items[0]
    assert it_14.confidence < 0.85, "短文本置信度应低于 0.85"
    assert "[需核实]" in it_14.flags, "低置信度应标注 [需核实]"
    print("  测试14（flags 标注）通过")

    # --- 测试用例 15：建议复核标注 ---
    sample_15 = ["这是一个中等长度的文本，包含邮箱 test@example.com，长度超过 10 个字符"]
    result_15 = processor.process(sample_15)
    it_15 = result_15.items[0]
    assert 0.85 <= it_15.confidence < 0.90, "中等置信度应在 0.85~0.90 之间"
    assert "建议复核" in it_15.flags, "中等置信度应标注 建议复核"
    print("  测试15（建议复核标注）通过")

    print("[selftest] 全部通过")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="angreal - 未命名工具（仅供学习与参考用途）",
        epilog="示例：python main.py --input '邮箱 a@b.com' --format json",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="待处理输入，可多次指定（如 --input '文本1' --input '文本2'）",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--batch-file",
        help="从文件读取多行输入（每行一条）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    inputs = list(args.input)

    # 从文件读取（如果指定）
    if args.batch_file:
        try:
            with open(args.batch_file, "r", encoding="utf-8") as f:
                file_inputs = [line.strip() for line in f if line.strip()]
            inputs.extend(file_inputs)
        except OSError as e:
            print(f"错误：无法读取文件 {args.batch_file}：{e}", file=sys.stderr)
            return 1

    # 无输入则报错
    if not inputs:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    # 执行处理
    try:
        processor = AngrealProcessor()
        output = batch_process(processor, inputs, args.format)
        print(output)
        return 0
    except AngrealError as e:
        print(f"错误 {e.code}：{e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        # 兜底错误处理
        print(f"错误 E010：未知异常 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
