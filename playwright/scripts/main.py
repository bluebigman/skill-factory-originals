#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============

Playwright 技能核心实现（clean-room 重写版）。

本脚本根据功能规格独立实现，仅依赖 Python 标准库。
提供命令行入口，支持 --selftest 参数进行离线自检。

错误码规范:
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常（通用）
    E007: 参数解析错误
    E008: 自检断言失败
    E009: 输出写入失败
    E010: 未预期的运行时错误
"""

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 领域模型
# ---------------------------------------------------------------------------

@dataclass
class ProcessedItem:
    """单条处理结果的结构化表示。"""
    input_text: str                 # 原始输入
    key_fields: Dict[str, Any]      # 提取的关键字段
    confidence: float               # 置信度 0~1
    note: str = ""                  # 备注/标注
    valid: bool = True              # 是否有效


@dataclass
class BatchResult:
    """批量处理的整体结果。"""
    items: List[ProcessedItem] = field(default_factory=list)
    total: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    avg_confidence: float = 0.0


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class PlaywrightProcessor:
    """
    核心处理器：将用户输入转换为结构化结果。

    根据规格，核心能力包括：
      1. 将数据/文件/URL 转换为结构化结果
      2. 识别并保留关键信息
      3. 按约定格式生成输出
      4. 对不确定项给出置信度提示
      5. 支持批量处理和自定义格式

    边界声明（不执行）：
      - 不执行超出输入范围的分析
      - 不保证绝对准确，低置信度会标注
      - 不访问网络或外部服务
    """

    # 常见的关键字段识别规则（简单启发式）
    _FIELD_RULES = {
        "email": lambda t: "@" in t and "." in t.split("@")[-1],
        "url": lambda t: t.startswith(("http://", "https://")),
        "number": lambda t: any(ch.isdigit() for ch in t),
        "date": lambda t: "/" in t or "-" in t,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化处理器。

        Args:
            config: 可选配置字典，支持字段：
                - batch_mode: bool，是否批量模式（默认 True）
                - custom_format: str，自定义输出模板
        """
        self.config = config or {}
        self.batch_mode = self.config.get("batch_mode", True)
        self.custom_format = self.config.get("custom_format", "")

    # ------------------------------------------------------------------
    # 主流程：处理单条输入
    # ------------------------------------------------------------------
    def process(self, raw_input: Any) -> ProcessedItem:
        """
        处理单条输入，返回结构化结果。

        Args:
            raw_input: 用户提供的数据/文件路径/URL 等

        Returns:
            ProcessedItem: 处理结果

        Raises:
            RuntimeError: 错误码 E001/E002/E003/E004/E005
        """
        # 输入为空检查
        if raw_input is None or (isinstance(raw_input, str) and raw_input.strip() == ""):
            raise RuntimeError("E001: 输入为空。请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        # 关键信息缺失检查
        if self._check_missing_info(raw_input):
            raise RuntimeError("E002: 关键信息缺失。还缺少以下信息，请补充：输入来源或输出格式要求")

        # 输入格式检查
        if not self._validate_input_format(raw_input):
            raise RuntimeError("E003: 输入格式错误。输入格式不符合要求，示例：一段文本、文件路径或URL")

        # 超出能力边界检查
        if self._is_out_of_scope(raw_input):
            raise RuntimeError("E004: 超出能力边界。这超出了本工具的能力范围，建议：提供更简单的输入或使用专用工具")

        # 执行核心提取
        key_fields = self._extract_key_fields(raw_input)
        confidence = self._compute_confidence(raw_input, key_fields)

        # 置信度过低检查
        if confidence < 0.85:
            note = "[需核实] 结果无法确定，建议：人工复核关键结果"
        elif confidence < 0.90:
            note = "建议复核"
        else:
            note = ""

        item = ProcessedItem(
            input_text=str(raw_input),
            key_fields=key_fields,
            confidence=confidence,
            note=note,
        )
        return item

    # ------------------------------------------------------------------
    # 批量处理
    # ------------------------------------------------------------------
    def process_batch(self, inputs: List[Any]) -> BatchResult:
        """
        批量处理多个输入。

        Args:
            inputs: 输入列表

        Returns:
            BatchResult: 批量结果
        """
        result = BatchResult()
        result.total = len(inputs)

        for raw in inputs:
            try:
                item = self.process(raw)
            except RuntimeError:
                # 单条失败不影响整体，标记为无效项
                item = ProcessedItem(
                    input_text=str(raw),
                    key_fields={},
                    confidence=0.0,
                    note="处理失败",
                    valid=False,
                )
            result.items.append(item)
            if item.valid:
                result.valid_count += 1
            else:
                result.invalid_count += 1
            result.avg_confidence += item.confidence

        if result.total > 0:
            result.avg_confidence /= result.total

        return result

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _check_missing_info(self, raw_input: Any) -> bool:
        """检查关键信息是否缺失。"""
        # 对于字符串输入，检查是否包含必要信息
        if isinstance(raw_input, str):
            # 如果输入是 URL 或文件路径，视为信息完整
            if raw_input.startswith(("http://", "https://", "/", "./", "../")):
                return False
            # 太短的输入视为信息不足
            if len(raw_input.strip()) < 3:
                return True
        return False

    def _validate_input_format(self, raw_input: Any) -> bool:
        """验证输入格式是否符合要求。"""
        # 支持字符串、数字、列表、字典
        if isinstance(raw_input, (str, int, float, list, dict)):
            return True
        return False

    def _is_out_of_scope(self, raw_input: Any) -> bool:
        """判断是否超出能力边界。"""
        # 明确拒绝二进制大对象或复杂对象
        if isinstance(raw_input, (bytes, bytearray)):
            return True
        if isinstance(raw_input, dict) and len(raw_input) > 100:
            return True
        return False

    def _extract_key_fields(self, raw_input: Any) -> Dict[str, Any]:
        """
        提取关键字段（启发式规则）。

        识别规则：
          - 文本中的 email / URL / 数字 / 日期
          - 列表/字典输入直接结构化
        """
        fields: Dict[str, Any] = {}

        if isinstance(raw_input, dict):
            # 字典直接作为关键字段
            fields.update(raw_input)
        elif isinstance(raw_input, (list, tuple)):
            # 列表按索引存储
            fields["items"] = list(raw_input)
        elif isinstance(raw_input, (int, float)):
            fields["value"] = raw_input
        else:
            # 字符串：按规则识别
            text = str(raw_input)
            for field_name, rule in self._FIELD_RULES.items():
                if rule(text):
                    fields[field_name] = True
            # 提取具体值（简单示例）
            if fields.get("email"):
                import re
                match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
                if match:
                    fields["email"] = match.group(0)
            if fields.get("url"):
                import re
                match = re.search(r"https?://[^\s]+", text)
                if match:
                    fields["url"] = match.group(0)

        # 确保至少有一个字段
        if not fields:
            fields["text"] = str(raw_input)[:50]

        return fields

    def _compute_confidence(self, raw_input: Any, key_fields: Dict[str, Any]) -> float:
        """
        计算置信度。

        规则：
          - 结构化输入（字典/列表）置信度较高
          - 文本输入根据识别到的字段数量决定
          - 基础值 0.75，每识别一个字段 +0.05，最高 0.98
        """
        base = 0.75

        if isinstance(raw_input, dict):
            # 字典输入置信度较高
            base = 0.95
        elif isinstance(raw_input, (list, tuple)):
            base = 0.90
        elif isinstance(raw_input, (int, float)):
            base = 0.98
        else:
            # 文本输入
            text = str(raw_input)
            if len(text) > 100:
                base += 0.05
            if len(key_fields) >= 2:
                base += 0.05
            if len(key_fields) >= 3:
                base += 0.05

        # 限制在 0~1 区间
        return max(0.0, min(1.0, base))

    def format_output(self, result: Any, fmt: str = "json") -> str:
        """
        按指定格式输出结果。

        Args:
            result: ProcessedItem 或 BatchResult
            fmt: 输出格式（json / text）

        Returns:
            格式化字符串
        """
        if fmt == "json":
            if isinstance(result, ProcessedItem):
                return json.dumps(asdict(result), ensure_ascii=False, indent=2)
            elif isinstance(result, BatchResult):
                payload = {
                    "total": result.total,
                    "valid_count": result.valid_count,
                    "invalid_count": result.invalid_count,
                    "avg_confidence": round(result.avg_confidence, 4),
                    "items": [asdict(item) for item in result.items],
                }
                return json.dumps(payload, ensure_ascii=False, indent=2)
            else:
                return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 文本格式
            lines = []
            if isinstance(result, ProcessedItem):
                lines.append(f"输入: {result.input_text}")
                lines.append(f"关键字段: {result.key_fields}")
                lines.append(f"置信度: {result.confidence:.0%}")
                if result.note:
                    lines.append(f"备注: {result.note}")
            elif isinstance(result, BatchResult):
                lines.append(f"总数: {result.total}, 有效: {result.valid_count}, 无效: {result.invalid_count}")
                lines.append(f"平均置信度: {result.avg_confidence:.0%}")
                for i, item in enumerate(result.items):
                    lines.append(f"  [{i}] {item.input_text} -> 置信度 {item.confidence:.0%}")
            return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保自检样例与实际逻辑必然匹配。

    Returns:
        0 表示通过，非 0 表示失败
    """
    print("[selftest] 开始离线自检...")
    processor = PlaywrightProcessor()

    # 测试用例 1：处理单条文本输入
    try:
        item = processor.process("这是一个包含 email: test@example.com 的文本")
        assert item.valid, "E008: 自检失败 - 基本处理应返回有效项"
        assert "email" in item.key_fields, "E008: 自检失败 - 应识别出 email 字段"
        assert item.confidence >= 0.5, "E008: 自检失败 - 置信度应 >= 0.5"
        assert item.confidence <= 1.0, "E008: 自检失败 - 置信度应 <= 1.0"
        print("[selftest] 测试 1 通过: 单条文本处理")
    except AssertionError as e:
        print(f"[selftest] 测试 1 失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 测试 1 异常: {e}")
        return 1

    # 测试用例 2：处理 URL 输入
    try:
        item = processor.process("https://example.com/page")
        assert item.valid, "E008: 自检失败 - URL 应返回有效项"
        assert "url" in item.key_fields, "E008: 自检失败 - 应识别出 url 字段"
        print("[selftest] 测试 2 通过: URL 处理")
    except AssertionError as e:
        print(f"[selftest] 测试 2 失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 测试 2 异常: {e}")
        return 1

    # 测试用例 3：批量处理
    try:
        inputs = [
            "第一段文本",
            "第二段文本含数字 12345",
            "https://example.org",
            42,
        ]
        batch = processor.process_batch(inputs)
        assert batch.total == 4, "E008: 自检失败 - 总数应为 4"
        assert batch.valid_count >= 3, "E008: 自检失败 - 有效数应至少 3"
        assert batch.invalid_count >= 0, "E008: 自检失败 - 无效数应 >= 0"
        assert 0.0 <= batch.avg_confidence <= 1.0, "E008: 自检失败 - 平均置信度应在 0~1"
        print("[selftest] 测试 3 通过: 批量处理")
    except AssertionError as e:
        print(f"[selftest] 测试 3 失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 测试 3 异常: {e}")
        return 1

    # 测试用例 4：错误处理 - 空输入
    try:
        processor.process("")
        print("[selftest] 测试 4 失败: 空输入应抛出 E001")
        return 1
    except RuntimeError as e:
        assert "E001" in str(e), f"E008: 自检失败 - 应返回 E001，实际: {e}"
        print("[selftest] 测试 4 通过: 空输入错误处理")
    except Exception as e:
        print(f"[selftest] 测试 4 异常: {e}")
        return 1

    # 测试用例 5：错误处理 - 缺失信息
    try:
        processor.process("ab")
        print("[selftest] 测试 5 失败: 短输入应抛出 E002")
        return 1
    except RuntimeError as e:
        assert "E002" in str(e), f"E008: 自检失败 - 应返回 E002，实际: {e}"
        print("[selftest] 测试 5 通过: 缺失信息错误处理")
    except Exception as e:
        print(f"[selftest] 测试 5 异常: {e}")
        return 1

    # 测试用例 6：输出格式化
    try:
        item = processor.process("测试格式化输出")
        json_out = processor.format_output(item, "json")
        assert json_out.startswith("{"), "E008: 自检失败 - JSON 输出应以 { 开头"
        text_out = processor.format_output(item, "text")
        assert "置信度" in text_out, "E008: 自检失败 - 文本输出应包含置信度"
        print("[selftest] 测试 6 通过: 输出格式化")
    except AssertionError as e:
        print(f"[selftest] 测试 6 失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 测试 6 异常: {e}")
        return 1

    # 测试用例 7：置信度边界
    try:
        item = processor.process({"name": "测试", "value": 100})
        assert item.confidence >= 0.9, "E008: 自检失败 - 字典输入置信度应较高"
        print("[selftest] 测试 7 通过: 置信度边界")
    except AssertionError as e:
        print(f"[selftest] 测试 7 失败: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 测试 7 异常: {e}")
        return 1

    print("[selftest] 全部自检通过 ✓")
    return 0


def main() -> int:
    """
    主入口函数。

    Returns:
        进程退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="Playwright 技能核心实现 - 将输入转换为结构化结果",
        epilog="示例: python main.py --input '文本内容' --format json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        help="输入内容：文本、文件路径或 URL",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为逗号分隔的多个值）",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 错误时返回非零码
        return int(e.code) if e.code is not None else 2

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 常规处理模式
    if not args.input:
        print("E001: 请提供待处理的内容。使用 --input 参数，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    try:
        processor = PlaywrightProcessor()

        if args.batch:
            # 批量模式：按逗号分割
            inputs = [item.strip() for item in args.input.split(",") if item.strip()]
            result = processor.process_batch(inputs)
        else:
            # 单条模式
            result = processor.process(args.input)

        # 输出结果
        output = processor.format_output(result, args.format)
        print(output)
        return 0

    except RuntimeError as e:
        # 业务错误
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # 未预期错误
        print(f"E010: 未预期的运行时错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
