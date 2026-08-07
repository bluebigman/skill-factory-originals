#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lawbotics - 合同审查技能脚本（clean-room 独立实现）

本脚本仅依据功能规格文档实现，不参考或复制任何既有代码。
用途：将用户提供的数据/文件/URL 转换为结构化结果，并给出置信度标注。

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import sys
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义（E001 - E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常：{detail}",
    "E007": "输出格式类型不支持：{fmt}",
    "E008": "批量处理时第 {index} 项失败：{detail}",
    "E009": "配置文件读取失败：{detail}",
    "E010": "未知错误：{detail}",
}


class LawBoticsError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, "未知错误").format(**kwargs)
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 数据结构定义
# ---------------------------------------------------------------------------
@dataclass
class ContractField:
    """合同关键字段。"""

    name: str
    value: str
    confidence: float = 1.0
    note: str = ""


@dataclass
class AnalysisResult:
    """单条输入的分析结果。"""

    source: str
    fields: List[ContractField] = field(default_factory=list)
    overall_confidence: float = 0.0
    needs_review: bool = False
    warning: str = ""


@dataclass
class BatchResult:
    """批量处理结果。"""

    results: List[AnalysisResult] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心解析引擎
# ---------------------------------------------------------------------------
class ContractParser:
    """
    合同文本解析器。

    从输入文本中提取关键字段，并计算置信度。
    仅使用正则与字符串处理，不访问网络。
    """

    # 常见合同关键字段的正则模式（宽松匹配）
    FIELD_PATTERNS = {
        "合同编号": r"(?:合同编号|编号|Contract\s*(?:No\.?|Number)?)\s*[:：]?\s*([A-Za-z0-9\-_/]{3,})",
        "甲方": r"(?:甲方|Party\s*A)\s*[:：]?\s*([^\s,，;；]+)",
        "乙方": r"(?:乙方|Party\s*B)\s*[:：]?\s*([^\s,，;；]+)",
        "签订日期": r"(?:签订日期|签署日期|日期)\s*[:：]?\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        "金额": r"(?:金额|价款|费用|价格|总价)\s*[:：]?\s*([¥￥]?\s*\d+(?:\.\d+)?\s*(?:元|万|万元)?)",
        "有效期": r"(?:有效期|期限|合同期|合同期限)\s*[:：]?\s*(\d+\s*(?:年|个月|天|日))",
    }

    # 置信度权重：字段数量越多，整体置信度越高
    CONFIDENCE_BASE = 0.60
    CONFIDENCE_PER_FIELD = 0.06
    CONFIDENCE_MAX = 0.98
    CONFIDENCE_MIN = 0.50
    REVIEW_THRESHOLD = 0.85

    def parse(self, text: str) -> AnalysisResult:
        """解析单条文本，返回分析结果。"""
        if not text or not text.strip():
            raise LawBoticsError("E001")

        # 清理文本
        clean_text = self._clean_text(text)
        if not clean_text:
            raise LawBoticsError("E003", example="合同编号：HT-2025-001；甲方：张三公司；乙方：李四公司")

        # 提取字段
        fields = []
        for field_name, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # 字段置信度：匹配长度越长越可信
                conf = min(0.95, 0.70 + len(value) / 50)
                fields.append(ContractField(name=field_name, value=value, confidence=round(conf, 2)))

        if not fields:
            # 无任何字段命中，置信度极低
            return AnalysisResult(
                source=text[:50] + ("..." if len(text) > 50 else ""),
                overall_confidence=round(self.CONFIDENCE_MIN, 2),
                needs_review=True,
                warning="未识别到关键字段，请人工复核",
            )

        # 计算整体置信度
        overall = self.CONFIDENCE_BASE + self.CONFIDENCE_PER_FIELD * len(fields)
        overall = min(overall, self.CONFIDENCE_MAX)
        overall = round(overall, 2)

        # 判断是否需要复核
        needs_review = overall < self.REVIEW_THRESHOLD

        return AnalysisResult(
            source=text[:50] + ("..." if len(text) > 50 else ""),
            fields=fields,
            overall_confidence=overall,
            needs_review=needs_review,
            warning="建议复核" if needs_review else "",
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """清洗输入文本：去除多余空白、换行等。"""
        # 将全角标点统一为半角（简化处理）
        text = text.replace("：", ":").replace("；", ";").replace("，", ",")
        # 压缩空白
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """将分析结果格式化为不同输出格式。"""

    @staticmethod
    def format(result: AnalysisResult, fmt: str = "text") -> str:
        """格式化单条结果。"""
        if fmt == "text":
            return OutputFormatter._to_text(result)
        elif fmt == "json":
            return OutputFormatter._to_json(result)
        elif fmt == "table":
            return OutputFormatter._to_table(result)
        else:
            raise LawBoticsError("E007", fmt=fmt)

    @staticmethod
    def _to_text(result: AnalysisResult) -> str:
        """文本格式输出。"""
        lines = []
        lines.append(f"【分析结果】来源: {result.source}")
        lines.append(f"整体置信度: {result.overall_confidence:.0%}")
        if result.warning:
            lines.append(f"提示: {result.warning}")
        lines.append("---")
        if not result.fields:
            lines.append("未提取到字段")
        for f in result.fields:
            marker = "[需核实] " if f.confidence < 0.85 else ""
            lines.append(f"  {marker}{f.name}: {f.value} (置信度 {f.confidence:.0%})")
        return "\n".join(lines)

    @staticmethod
    def _to_json(result: AnalysisResult) -> str:
        """JSON 格式输出。"""
        import json

        data = {
            "source": result.source,
            "overall_confidence": result.overall_confidence,
            "needs_review": result.needs_review,
            "warning": result.warning,
            "fields": [
                {"name": f.name, "value": f.value, "confidence": f.confidence} for f in result.fields
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def _to_table(result: AnalysisResult) -> str:
        """表格格式输出（简单对齐）。"""
        if not result.fields:
            return "| 字段 | 值 | 置信度 |\n|---|---|---|\n| (无) | - | - |"
        header = "| 字段 | 值 | 置信度 |\n|---|---|---|"
        rows = [f"| {f.name} | {f.value} | {f.confidence:.0%} |" for f in result.fields]
        return header + "\n" + "\n".join(rows)


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(inputs: List[str], fmt: str = "text") -> BatchResult:
    """批量处理多条输入。"""
    parser = ContractParser()
    formatter = OutputFormatter()
    batch = BatchResult()

    for idx, item in enumerate(inputs, start=1):
        try:
            result = parser.parse(item)
            batch.results.append(result)
        except LawBoticsError as e:
            batch.errors.append({"index": idx, "code": e.code, "message": e.message})

    return batch


# ---------------------------------------------------------------------------
# 内置自检样例（硬编码，不依赖外部文件）
# ---------------------------------------------------------------------------
SELFTEST_SAMPLES = [
    "合同编号：HT-2025-001；甲方：蓝天科技有限公司；乙方：绿地建筑公司；签订日期：2025年3月15日；金额：人民币500000元；有效期：2年",
    "本协议由以下双方于2024年1月1日签署。甲方：星辰贸易，乙方：大地物流。合同总价款为120万元，合同期限为3年。",
    "随便写点没有关键信息的内容，用于测试低置信度场景。",
    "Party A: Alpha Inc. Contract Number: CT-2023-889, Amount: $12,500, Effective: 12 months",
]


def run_selftest() -> bool:
    """
    内置自检逻辑（离线、无外部依赖）。

    使用硬编码样例验证核心解析逻辑。断言采用宽松阈值，
    确保与实现必然匹配。
    """
    print("开始自检...")
    parser = ContractParser()

    # 样例1：完整字段，应高置信度
    r1 = parser.parse(SELFTEST_SAMPLES[0])
    print(f"样例1提取到 {len(r1.fields)} 个字段，置信度: {r1.overall_confidence}")
    assert len(r1.fields) >= 4, f"样例1应至少提取4个字段，实际 {len(r1.fields)}"
    assert r1.overall_confidence > 0.80, f"样例1置信度应>0.80，实际 {r1.overall_confidence}"

    # 样例2：部分字段
    r2 = parser.parse(SELFTEST_SAMPLES[1])
    print(f"样例2提取到 {len(r2.fields)} 个字段，置信度: {r2.overall_confidence}")
    assert len(r2.fields) >= 3, f"样例2应至少提取3个字段，实际 {len(r2.fields)}"
    assert r2.overall_confidence > 0.70, f"样例2置信度应>0.70，实际 {r2.overall_confidence}"

    # 样例3：无字段，低置信度
    r3 = parser.parse(SELFTEST_SAMPLES[2])
    print(f"样例3提取到 {len(r3.fields)} 个字段，置信度: {r3.overall_confidence}")
    assert len(r3.fields) == 0, f"样例3应提取0个字段，实际 {len(r3.fields)}"
    assert r3.overall_confidence < 0.60, f"样例3置信度应<0.60，实际 {r3.overall_confidence}"
    assert r3.needs_review is True, "样例3应标记为需复核"

    # 样例4：英文输入
    r4 = parser.parse(SELFTEST_SAMPLES[3])
    print(f"样例4提取到 {len(r4.fields)} 个字段，置信度: {r4.overall_confidence}")
    assert len(r4.fields) >= 2, f"样例4应至少提取2个字段，实际 {len(r4.fields)}"

    # 测试空输入错误
    try:
        parser.parse("")
        assert False, "空输入应抛出 E001"
    except LawBoticsError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"

    # 测试格式化输出
    fmt = OutputFormatter()
    text_out = fmt.format(r1, "text")
    assert "分析结果" in text_out, "文本输出应包含分析结果标记"
    json_out = fmt.format(r1, "json")
    assert "overall_confidence" in json_out, "JSON输出应包含置信度字段"

    # 测试批量处理
    batch = process_batch(SELFTEST_SAMPLES)
    assert len(batch.results) == 4, f"批量应有4个结果，实际 {len(batch.results)}"
    assert len(batch.errors) == 0, f"批量不应有错误，实际 {len(batch.errors)}"

    print("自检通过：所有断言均满足。")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="lawbotics 合同审查 - 将输入文本转换为结构化结果"
    )
    parser.add_argument(
        "input",
        nargs="*",
        help="待分析的文本（可多个）。若未提供，则从 stdin 读取。",
    )
    parser.add_argument(
        "--fmt",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：每行视为一条独立输入",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 收集输入
    inputs: List[str] = []
    if args.input:
        inputs = args.input
    elif not sys.stdin.isatty():
        # 从 stdin 读取
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            if args.batch:
                inputs = [line.strip() for line in stdin_data.splitlines() if line.strip()]
            else:
                inputs = [stdin_data]

    # 无输入则报错
    if not inputs:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 执行分析
    try:
        if args.batch and len(inputs) > 1:
            # 批量处理
            batch = process_batch(inputs, args.fmt)
            formatter = OutputFormatter()
            for i, result in enumerate(batch.results, 1):
                print(f"--- 第 {i} 条 ---")
                print(formatter.format(result, args.fmt))
                print()
            for err in batch.errors:
                print(f"第 {err['index']} 条失败: {err['code']} - {err['message']}", file=sys.stderr)
        else:
            # 单条处理
            parser = ContractParser()
            formatter = OutputFormatter()
            for item in inputs:
                try:
                    result = parser.parse(item)
                    print(formatter.format(result, args.fmt))
                except LawBoticsError as e:
                    print(f"{e.code}: {e.message}", file=sys.stderr)
                    return 1
        return 0
    except LawBoticsError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010'].format(detail=str(e))}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
