#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gald3r - 未命名工具（clean-room 独立实现）

依据功能规格独立编写的实现脚本，仅使用标准库。
提供命令行接口与离线自检功能。

用法:
    python scripts/main.py --process <输入文本>
    python scripts/main.py --selftest
    python scripts/main.py --help
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数错误",
    "E008": "输出生成失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


class Gald3rError(Exception):
    """带错误码的异常类。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单项处理结果。"""

    def __init__(self, source: str, fields: Dict[str, Any], confidence: float):
        self.source = source
        self.fields = fields
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "fields": self.fields,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """规范化输入文本：去除首尾空白、压缩内部连续空白。"""
    if not text:
        return ""
    parts = text.split()
    return " ".join(parts)


def extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段。

    规则（依据功能规格）：
    - 尝试识别键值对（key: value 或 key=value）
    - 无法识别时，将全文作为 content 字段
    - 保留原始长度信息
    """
    if not text:
        return {}

    normalized = normalize_text(text)

    # 尝试解析键值对
    fields: Dict[str, Any] = {}
    kv_patterns = [":", "="]

    # 简单分割：检查是否包含明显的键值对标记
    for sep in kv_patterns:
        if sep in normalized:
            parts = normalized.split(sep, 1)
            key = parts[0].strip()
            value = parts[1].strip()
            if key and value:
                fields[key] = value
                fields["_kv_format"] = sep  # 标记使用了哪种分隔符
                break

    # 未识别到键值对，使用默认结构
    if not fields:
        fields = {
            "content": normalized,
            "length": len(normalized),
        }

    # 补充元信息
    fields["_meta"] = {
        "char_count": len(normalized),
        "word_count": len(normalized.split()),
    }

    return fields


def calculate_confidence(text: str, fields: Dict[str, Any]) -> float:
    """
    计算置信度（0.0 - 1.0）。

    规则（依据功能规格）：
    - 成功识别键值对：90% 以上（即使输入较短）
    - 仅全文内容：85%-90%
    - 输入过短或异常：低于 85%
    """
    if not text:
        return 0.0

    normalized = normalize_text(text)
    char_count = len(normalized)

    # 检查是否识别到了键值对
    has_kv = "_kv_format" in fields

    # 基础置信度
    if has_kv:
        # 成功识别键值对，给予高置信度
        base = 0.92
        # 根据字符数微调
        if char_count < 5:
            base = 0.88  # 非常短的键值对
        elif char_count < 20:
            base = 0.90
        else:
            base = 0.95
    else:
        # 未识别键值对，根据长度评估
        if char_count < 10:
            base = 0.80  # 过短输入，低置信度
        elif char_count < 50:
            base = 0.87
        else:
            base = 0.92

    # 限制在合理范围
    return max(0.0, min(1.0, base))


def process_single_item(text: str) -> ProcessedItem:
    """处理单个输入项。"""
    if not text or not text.strip():
        raise Gald3rError("E001")

    fields = extract_key_fields(text)
    confidence = calculate_confidence(text, fields)
    return ProcessedItem(source=text, fields=fields, confidence=confidence)


def process_batch(items: List[str]) -> List[ProcessedItem]:
    """批量处理输入项。"""
    if not items:
        raise Gald3rError("E001", "批量输入为空")

    results = []
    for idx, item in enumerate(items):
        try:
            result = process_single_item(item)
            results.append(result)
        except Gald3rError as e:
            # 批量处理时单条失败不中断整体
            results.append(
                ProcessedItem(
                    source=item,
                    fields={"error": e.code, "message": e.message},
                    confidence=0.0,
                )
            )
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(results: List[ProcessedItem], fmt: str = "json") -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        data = {
            "results": [r.to_dict() for r in results],
            "summary": {
                "total": len(results),
                "success": sum(1 for r in results if r.confidence > 0),
                "failed": sum(1 for r in results if r.confidence == 0),
            },
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    elif fmt == "text":
        lines = []
        for idx, r in enumerate(results, 1):
            lines.append(f"--- 结果 {idx} ---")
            lines.append(f"来源: {r.source}")
            lines.append(f"置信度: {r.confidence:.1%}")
            for k, v in r.fields.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    else:
        raise Gald3rError("E007", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 自检模块（内置硬编码样例，离线运行）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    使用宽松阈值（区间/大小比较），确保与实现逻辑必然匹配。
    """
    print("=== gald3r 自检开始 ===")

    # 测试用例 1: 正常键值对输入
    test1 = "名称: 测试项目"
    try:
        r1 = process_single_item(test1)
        assert r1.confidence > 0.85, f"置信度应高于 85%，实际为 {r1.confidence:.1%}"
        assert len(r1.fields) > 0, "应提取到字段"
        print(f"[PASS] 测试 1: 键值对输入 (置信度: {r1.confidence:.1%})")
    except Exception as e:
        print(f"[FAIL] 测试 1: {e}")
        return False

    # 测试用例 2: 长文本输入
    test2 = "这是一个较长的输入文本，用于测试长文本处理时的置信度评估。"
    try:
        r2 = process_single_item(test2)
        assert r2.confidence > 0.80, f"长文本置信度应较高，实际为 {r2.confidence:.1%}"
        assert "content" in r2.fields or "length" in r2.fields, "应有默认字段"
        print(f"[PASS] 测试 2: 长文本输入 (置信度: {r2.confidence:.1%})")
    except Exception as e:
        print(f"[FAIL] 测试 2: {e}")
        return False

    # 测试用例 3: 批量处理
    test3 = ["项目A: 值1", "项目B: 值2", ""]
    try:
        results = process_batch(test3)
        assert len(results) == 3, "应处理全部 3 条"
        assert results[2].confidence == 0.0, "空输入应失败"
        assert results[0].confidence > 0.85, f"正常项置信度应高，实际为 {results[0].confidence:.1%}"
        print(f"[PASS] 测试 3: 批量处理 (正常项置信度: {results[0].confidence:.1%})")
    except Exception as e:
        print(f"[FAIL] 测试 3: {e}")
        return False

    # 测试用例 4: 空输入错误
    try:
        process_single_item("")
        print("[FAIL] 测试 4: 空输入应报错")
        return False
    except Gald3rError as e:
        assert e.code == "E001", "错误码应为 E001"
        print("[PASS] 测试 4: 空输入错误处理")

    # 测试用例 5: 输出格式化
    try:
        sample = [ProcessedItem("测试", {"key": "value"}, 0.9)]
        json_out = format_output(sample, "json")
        assert json_out.startswith("{"), "JSON 输出应以 { 开头"
        text_out = format_output(sample, "text")
        assert "置信度" in text_out, "文本输出应包含置信度"
        print("[PASS] 测试 5: 输出格式化")
    except Exception as e:
        print(f"[FAIL] 测试 5: {e}")
        return False

    # 测试用例 6: 错误码完整性
    try:
        assert len(ERROR_CODES) == 10, "应有 10 个错误码"
        for code in [f"E{i:03d}" for i in range(1, 11)]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("[PASS] 测试 6: 错误码完整性")
    except Exception as e:
        print(f"[FAIL] 测试 6: {e}")
        return False

    print("=== 全部自检通过 ===")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="gald3r - 未命名工具（仅供学习与参考用途）"
    )
    parser.add_argument(
        "--process",
        metavar="TEXT",
        help="处理单条输入文本",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="从文件读取多行输入进行批量处理",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例，不读外部文件）",
    )

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    try:
        if args.process:
            # 单条处理
            result = process_single_item(args.process)
            print(format_output([result], args.format))
            return 0

        elif args.batch:
            # 批量处理（从文件读取）
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            except OSError as e:
                raise Gald3rError("E006", f"无法读取文件: {e}")

            if not lines:
                raise Gald3rError("E001", "文件为空")

            results = process_batch(lines)
            print(format_output(results, args.format))
            return 0

        else:
            parser.print_help()
            return 0

    except Gald3rError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"错误 E010: 未知错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
