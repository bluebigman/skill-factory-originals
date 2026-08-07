#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

Spec-driven development workflow 的独立实现（clean-room 重写）。

仅依据功能规格实现，不参考任何既有代码。
提供命令行入口，支持 --selftest 离线自检。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义（E001 - E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式不受支持，当前支持：json/text",
    "E008": "批量处理中断：某个输入项处理失败",
    "E009": "置信度计算失败，请检查输入数据",
    "E010": "未知错误，请联系维护者",
}


class SpecDrivenError(Exception):
    """业务异常，携带错误码。"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        message = ERROR_CODES.get(code, ERROR_CODES["E010"])
        if detail:
            message = f"{message}（{detail}）"
        super().__init__(f"[{code}] {message}")


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ProcessingResult:
    """单条输入的处理结果。"""

    input_raw: str
    structured: Dict[str, Any]
    confidence: float  # 0.0 - 1.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """批量处理的结果汇总。"""

    results: List[ProcessingResult] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# 核心处理引擎
# ============================================================
class SpecDrivenEngine:
    """
    核心引擎：负责将输入内容转换为结构化结果。

    能力边界：
      - 能：解析文本/JSON 输入，提取关键字段，生成结构化输出
      - 不做：网络访问、外部服务调用、超出输入范围的分析
    """

    # 默认输出字段模板
    DEFAULT_FIELDS = ["id", "type", "content", "metadata"]

    # 可识别的常见关键字段（用于从自由文本中提取）
    KEY_FIELD_PATTERNS = {
        "id": ["id", "编号", "序号"],
        "type": ["type", "类型", "类别"],
        "content": ["content", "内容", "正文"],
        "metadata": ["metadata", "元数据", "备注"],
    }

    def __init__(self, output_format: str = "json"):
        if output_format not in ("json", "text"):
            raise SpecDrivenError("E007", f"format={output_format}")
        self.output_format = output_format

    # ---------- 主入口 ----------
    def process(self, raw_input: str, required_fields: Optional[List[str]] = None) -> ProcessingResult:
        """
        处理单条输入。

        :param raw_input: 用户提供的原始输入（文本或 JSON 字符串）
        :param required_fields: 期望输出的字段列表，缺省使用 DEFAULT_FIELDS
        :return: ProcessingResult
        """
        if not raw_input or not raw_input.strip():
            raise SpecDrivenError("E001")

        # 1. 解析输入
        parsed = self._parse_input(raw_input)

        # 2. 提取关键信息
        extracted = self._extract_fields(parsed)

        # 3. 校验关键信息是否完整
        fields_needed = required_fields or self.DEFAULT_FIELDS
        missing = [f for f in fields_needed if f not in extracted or extracted[f] is None]
        if missing:
            raise SpecDrivenError("E002", f"缺少字段: {', '.join(missing)}")

        # 4. 计算置信度
        confidence = self._calculate_confidence(extracted, parsed)

        # 5. 组装结果
        warnings = []
        if confidence < 0.85:
            warnings.append("[需核实] 置信度过低，请人工复核")
        elif confidence < 0.90:
            warnings.append("建议复核")

        return ProcessingResult(
            input_raw=raw_input,
            structured=extracted,
            confidence=confidence,
            warnings=warnings,
        )

    def process_batch(self, inputs: List[str], required_fields: Optional[List[str]] = None) -> BatchResult:
        """
        批量处理多个输入。

        :param inputs: 输入字符串列表
        :param required_fields: 期望字段
        :return: BatchResult
        """
        if not inputs:
            raise SpecDrivenError("E001")

        batch = BatchResult()
        for idx, item in enumerate(inputs):
            try:
                result = self.process(item, required_fields)
                batch.results.append(result)
            except SpecDrivenError as e:
                batch.failed.append({"index": idx, "error_code": e.code, "message": str(e)})
            except Exception as e:  # 兜底异常
                batch.failed.append({"index": idx, "error_code": "E010", "message": str(e)})

        if batch.failed and len(batch.failed) == len(inputs):
            raise SpecDrivenError("E008", "所有输入项均处理失败")

        return batch

    # ---------- 内部方法 ----------
    def _parse_input(self, raw: str) -> Dict[str, Any]:
        """解析输入：尝试 JSON，失败则按纯文本处理。"""
        raw = raw.strip()
        # 尝试 JSON 解析
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return {"items": data}
            else:
                return {"value": data}
        except json.JSONDecodeError:
            # 不是 JSON，按纯文本处理
            return {"text": raw}

    def _extract_fields(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取关键字段。

        规则：
          - 如果输入是 JSON 对象，直接取对应 key
          - 如果输入是纯文本，尝试匹配常见字段名
        """
        extracted: Dict[str, Any] = {}

        # 情况1：输入本身就是结构化对象
        if "text" not in parsed:
            for key in self.DEFAULT_FIELDS:
                if key in parsed:
                    extracted[key] = parsed[key]
            # 保留其他额外字段到 metadata
            extra = {k: v for k, v in parsed.items() if k not in self.DEFAULT_FIELDS}
            if extra:
                extracted["metadata"] = extra
            return extracted

        # 情况2：纯文本输入，尝试按行识别 key: value 模式
        text = parsed["text"]
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试匹配 "key: value" 或 "key=value"
            for sep in (":", "=", "："):
                if sep in line:
                    key, _, value = line.partition(sep)
                    key = key.strip().lower()
                    value = value.strip()
                    # 匹配已知字段
                    for field, aliases in self.KEY_FIELD_PATTERNS.items():
                        if key in aliases:
                            extracted[field] = value
                            break
                    else:
                        # 未知字段，归入 metadata
                        extracted.setdefault("metadata", {})[key] = value
                    break

        # 如果什么都没提取到，把整段文本作为 content
        if not extracted:
            extracted["content"] = text

        return extracted

    def _calculate_confidence(self, extracted: Dict[str, Any], parsed: Dict[str, Any]) -> float:
        """
        计算置信度（0.0 - 1.0）。

        规则：
          - 结构化输入（JSON）且字段完整：>= 0.90
          - 纯文本提取：根据字段完整度计算
          - 存在未知字段或缺失字段：降低置信度
        """
        try:
            base_confidence = 1.0

            # 输入类型影响
            if "text" in parsed:
                base_confidence -= 0.15  # 纯文本解析有不确定性

            # 字段完整度
            present_count = sum(1 for f in self.DEFAULT_FIELDS if f in extracted)
            field_ratio = present_count / len(self.DEFAULT_FIELDS)
            base_confidence *= (0.5 + 0.5 * field_ratio)

            # metadata 中有未知字段，轻微降低
            meta = extracted.get("metadata")
            if isinstance(meta, dict) and len(meta) > 0:
                base_confidence -= 0.05

            # 限制在 0 到 1 之间
            return max(0.0, min(1.0, base_confidence))
        except Exception:
            raise SpecDrivenError("E009")

    # ---------- 输出格式化 ----------
    def format_output(self, result: ProcessingResult) -> str:
        """按指定格式输出结果。"""
        if self.output_format == "json":
            payload = {
                "input": result.input_raw,
                "structured": result.structured,
                "confidence": round(result.confidence, 4),
                "warnings": result.warnings,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            # text 格式
            lines = []
            lines.append(f"输入: {result.input_raw}")
            lines.append(f"置信度: {result.confidence:.1%}")
            for k, v in result.structured.items():
                lines.append(f"  {k}: {v}")
            if result.warnings:
                lines.append("警告: " + "; ".join(result.warnings))
            return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置样例数据，不依赖外部文件/网络。
    返回 0 表示全部通过，非 0 表示失败。
    """
    print("开始自检...")
    engine = SpecDrivenEngine(output_format="json")

    # --- 测试用例 1：合法 JSON 输入 ---
    test1 = json.dumps({
        "id": "A001",
        "type": "文档",
        "content": "这是测试内容",
        "metadata": {"author": "tester"},
    })
    try:
        r1 = engine.process(test1)
        assert r1.confidence >= 0.90, f"Test1 置信度应 >= 0.90，实际 {r1.confidence}"
        assert r1.structured["id"] == "A001"
        print("  [PASS] Test1: JSON 结构化输入")
    except Exception as e:
        print(f"  [FAIL] Test1: {e}")
        return 1

    # --- 测试用例 2：纯文本输入 ---
    test2 = "id: B002\n类型: 报告\n内容: 季度总结"
    try:
        r2 = engine.process(test2)
        assert "id" in r2.structured, "Test2 应提取出 id"
        assert r2.confidence < 1.0, "Test2 置信度应小于 1.0（文本解析）"
        print("  [PASS] Test2: 纯文本字段提取")
    except Exception as e:
        print(f"  [FAIL] Test2: {e}")
        return 1

    # --- 测试用例 3：空输入 → E001 ---
    try:
        engine.process("   ")
        print("  [FAIL] Test3: 空输入应抛 E001")
        return 1
    except SpecDrivenError as e:
        assert e.code == "E001", f"Test3 错误码应为 E001，实际 {e.code}"
        print("  [PASS] Test3: 空输入错误处理")

    # --- 测试用例 4：缺失关键字段 → E002 ---
    try:
        engine.process(json.dumps({"id": "X"}), required_fields=["id", "content"])
        print("  [FAIL] Test4: 缺字段应抛 E002")
        return 1
    except SpecDrivenError as e:
        assert e.code == "E002", f"Test4 错误码应为 E002，实际 {e.code}"
        print("  [PASS] Test4: 缺失字段错误处理")

    # --- 测试用例 5：批量处理 ---
    batch_inputs = [
        json.dumps({"id": "1", "type": "a", "content": "x"}),
        "无效输入",
        json.dumps({"id": "3", "type": "c", "content": "z"}),
    ]
    try:
        batch = engine.process_batch(batch_inputs)
        assert len(batch.results) == 2, f"Test5 应成功处理 2 条，实际 {len(batch.results)}"
        assert len(batch.failed) == 1, f"Test5 应有 1 条失败，实际 {len(batch.failed)}"
        assert batch.failed[0]["index"] == 1
        print("  [PASS] Test5: 批量处理（含部分失败）")
    except Exception as e:
        print(f"  [FAIL] Test5: {e}")
        return 1

    # --- 测试用例 6：置信度标注 ---
    low_conf_input = "随便写点什么没有结构"
    try:
        r6 = engine.process(low_conf_input)
        # 无结构文本置信度应该较低
        assert r6.confidence < 0.85, f"Test6 置信度应 < 0.85，实际 {r6.confidence}"
        assert any("[需核实]" in w for w in r6.warnings), "Test6 应有 [需核实] 警告"
        print("  [PASS] Test6: 低置信度标注")
    except Exception as e:
        print(f"  [FAIL] Test6: {e}")
        return 1

    # --- 测试用例 7：输出格式 ---
    try:
        out = engine.format_output(r1)
        json.loads(out)  # 应为合法 JSON
        print("  [PASS] Test7: JSON 输出格式")
    except Exception as e:
        print(f"  [FAIL] Test7: {e}")
        return 1

    # --- 测试用例 8：错误码覆盖 ---
    try:
        SpecDrivenEngine(output_format="xml")
        print("  [FAIL] Test8: 非法格式应抛 E007")
        return 1
    except SpecDrivenError as e:
        assert e.code == "E007", f"Test8 错误码应为 E007，实际 {e.code}"
        print("  [PASS] Test8: 错误码 E007")

    print("\n全部自检通过 ✅")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Spec-driven development workflow 工具",
        epilog="示例: python main.py --input 'id: 1\\ntype: 测试\\ncontent: 内容' --format json",
    )
    parser.add_argument("--input", "-i", help="输入内容（文本或 JSON 字符串）")
    parser.add_argument("--batch", "-b", help="批量输入，多个输入用 ||| 分隔")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--fields", nargs="*", help="期望输出的字段列表（默认: id type content metadata）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        engine = SpecDrivenEngine(output_format=args.format)

        # 批量模式
        if args.batch:
            inputs = [x.strip() for x in args.batch.split("|||") if x.strip()]
            batch = engine.process_batch(inputs, required_fields=args.fields)
            if batch.failed:
                print(f"警告: {len(batch.failed)} 条输入处理失败", file=sys.stderr)
                for f in batch.failed:
                    print(f"  [索引 {f['index']}] {f['message']}", file=sys.stderr)
            for r in batch.results:
                print(engine.format_output(r))
                print("---")
            return 0

        # 单条模式
        if not args.input:
            raise SpecDrivenError("E001")
        result = engine.process(args.input, required_fields=args.fields)
        print(engine.format_output(result))
        return 0

    except SpecDrivenError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
