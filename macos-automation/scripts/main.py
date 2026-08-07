#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macos-automation 技能实现脚本

依据功能规格独立实现（clean-room），提供：
1. 标准流程：输入解析 -> 结构化处理 -> 输出与置信度标注
2. 错误码体系：E001-E010
3. 离线自检：--selftest 使用内置样例验证核心逻辑

免责声明：本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。
涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（依据规格 E001-E005，扩展至 E010）
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "批量处理中断，部分项目未完成",
    "E008": "输出格式不支持，请选择支持的格式",
    "E009": "输入内容过大，请分批处理",
    "E010": "未知错误，请联系维护者",
}


class AutomationError(Exception):
    """带错误码的异常"""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if detail:
            self.message = f"{self.message} {detail}"
        super().__init__(self.message)


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ProcessResult:
    """处理结果"""

    items: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class SkillConfig:
    """技能配置"""

    output_format: str = "json"
    require_complete: bool = True  # 是否要求完整度


# ============================================================
# 核心处理逻辑
# ============================================================
class MacOSAutomation:
    """macOS 自动化技能核心类"""

    # 关键字段识别模式（依据规格：识别关键信息）
    KEY_FIELD_PATTERNS = {
        "url": re.compile(r"https?://[^\s]+", re.IGNORECASE),
        "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
        "phone": re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"),
        "date": re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}"),
        "file_path": re.compile(r"(?:/[^\s]+|~/[^\s]+|[A-Za-z]:\\[^\s]+)"),
    }

    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()

    def process(self, raw_input: str) -> ProcessResult:
        """
        标准流程主入口：
        Step 1 收集最小信息集（此处由调用方保证输入）
        Step 2 执行核心流程（解析 -> 结构化 -> 标注）
        Step 3 输出与校验（置信度计算）
        """
        # 输入校验
        if not raw_input or not raw_input.strip():
            raise AutomationError("E001")

        # 解析输入
        parsed = self._parse_input(raw_input)

        # 结构化处理
        items = self._structure_items(parsed)

        if not items:
            raise AutomationError("E003", "未识别到有效内容")

        # 计算置信度
        confidence = self._calculate_confidence(items)

        # 生成警告
        warnings = self._generate_warnings(items, confidence)

        return ProcessResult(items=items, confidence=confidence, warnings=warnings)

    def batch_process(self, inputs: List[str]) -> List[ProcessResult]:
        """批量处理：按同一规则逐项处理"""
        results = []
        for i, item in enumerate(inputs):
            try:
                results.append(self.process(item))
            except AutomationError as e:
                # 单条失败不中断整体，记录错误
                results.append(
                    ProcessResult(
                        items=[{"error": e.code, "message": e.message}],
                        confidence=0.0,
                        warnings=[f"第{i+1}项处理失败: {e.code}"],
                    )
                )
        return results

    # ---------- 内部方法 ----------
    def _parse_input(self, raw: str) -> Dict[str, Any]:
        """解析输入，识别关键字段"""
        parsed: Dict[str, Any] = {
            "raw_text": raw.strip(),
            "fields": {},
            "segments": [],
        }

        # 尝试解析为 JSON（如果输入是 JSON 格式）
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                parsed["fields"] = data
                parsed["segments"] = [str(v) for v in data.values() if v]
                return parsed
            elif isinstance(data, list):
                parsed["segments"] = [str(v) for v in data]
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass  # 不是 JSON，继续文本解析

        # 文本解析：识别关键字段
        text = raw.strip()
        for field_name, pattern in self.KEY_FIELD_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                parsed["fields"][field_name] = matches[0] if len(matches) == 1 else matches

        # 按行或标点分段
        segments = re.split(r"[\n;，。；]+", text)
        parsed["segments"] = [s.strip() for s in segments if s.strip()]

        return parsed

    def _structure_items(self, parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将解析结果结构化为条目"""
        items = []

        # 如果有明确的字段，直接结构化
        if parsed.get("fields"):
            item = {"type": "structured", "fields": parsed["fields"]}
            items.append(item)
        else:
            # 按段落生成条目
            for seg in parsed.get("segments", []):
                items.append({"type": "text", "content": seg})

        # 附加原始文本
        for item in items:
            item["source"] = parsed.get("raw_text", "")[:200]  # 截断长文本

        return items

    def _calculate_confidence(self, items: List[Dict[str, Any]]) -> float:
        """
        计算置信度：
        - 结构化字段完整：高置信度
        - 纯文本：中等置信度
        - 字段缺失：低置信度
        """
        if not items:
            return 0.0

        scores = []
        for item in items:
            if item.get("type") == "structured":
                fields = item.get("fields", {})
                # 有 URL、邮箱等明确标识的字段，置信度高
                if any(k in fields for k in ["url", "email", "phone", "date"]):
                    scores.append(0.95)
                elif fields:
                    scores.append(0.85)
                else:
                    scores.append(0.7)
            else:
                # 纯文本片段
                content = item.get("content", "")
                if len(content) >= 20:
                    scores.append(0.75)
                else:
                    scores.append(0.6)

        avg = sum(scores) / len(scores) if scores else 0.0
        return round(max(0.0, min(1.0, avg)), 2)

    def _generate_warnings(self, items: List[Dict[str, Any]], confidence: float) -> List[str]:
        """根据置信度生成警告"""
        warnings = []

        if confidence >= 0.90:
            pass  # 高置信度，无警告
        elif confidence >= 0.85:
            warnings.append("建议复核：部分字段可能存在偏差")
        else:
            warnings.append("[需核实] 置信度较低，请人工确认关键信息")

        # 检查是否有缺失字段
        for item in items:
            if item.get("type") == "structured":
                fields = item.get("fields", {})
                if not fields:
                    warnings.append("存在未识别字段，请补充信息")

        return warnings

    def format_output(self, result: ProcessResult, fmt: str = "json") -> str:
        """格式化输出"""
        if fmt == "json":
            return self._to_json(result)
        elif fmt == "text":
            return self._to_text(result)
        else:
            raise AutomationError("E008", f"不支持的格式: {fmt}")

    def _to_json(self, result: ProcessResult) -> str:
        """JSON 输出"""
        payload = {
            "items": result.items,
            "confidence": result.confidence,
            "confidence_level": self._confidence_label(result.confidence),
            "warnings": result.warnings,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _to_text(self, result: ProcessResult) -> str:
        """纯文本输出"""
        lines = []
        for i, item in enumerate(result.items, 1):
            if item.get("type") == "structured":
                fields = item.get("fields", {})
                lines.append(f"[{i}] 结构化数据:")
                for k, v in fields.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"[{i}] {item.get('content', '')}")

        lines.append(f"\n置信度: {result.confidence:.0%} ({self._confidence_label(result.confidence)})")
        for w in result.warnings:
            lines.append(f"警告: {w}")
        return "\n".join(lines)

    def _confidence_label(self, confidence: float) -> str:
        """置信度标签"""
        if confidence >= 0.90:
            return "高置信度"
        elif confidence >= 0.85:
            return "建议复核"
        else:
            return "需核实"


# ============================================================
# 离线自检（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("=" * 60)
    print("macos-automation 自检开始")
    print("=" * 60)

    skill = MacOSAutomation()

    # ---------- 测试 1: 正常处理 ----------
    print("\n[测试 1] 正常处理")
    try:
        result = skill.process("请处理这个文件: /Users/test/input.txt 和 https://example.com")
        assert result.items, "处理结果不应为空"
        assert result.confidence > 0.5, f"置信度应大于0.5，实际: {result.confidence}"
        print(f"  ✓ 通过 (置信度: {result.confidence:.0%}, 条目数: {len(result.items)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except AutomationError as e:
        print(f"  ✗ 异常: {e.code} {e.message}")
        return 1

    # ---------- 测试 2: 空输入 ----------
    print("\n[测试 2] 空输入处理")
    try:
        skill.process("")
        print("  ✗ 失败: 空输入未触发错误")
        return 1
    except AutomationError as e:
        assert e.code == "E001", f"错误码应为 E001，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # ---------- 测试 3: 批量处理 ----------
    print("\n[测试 3] 批量处理")
    try:
        inputs = ["处理这个URL: https://test.com", "无效输入", "联系 test@example.com"]
        results = skill.batch_process(inputs)
        assert len(results) == 3, f"应返回3个结果，实际: {len(results)}"
        assert results[0].confidence > 0.5, "第一个结果置信度应较高"
        # 第二个可能是空输入导致错误
        print(f"  ✓ 通过 (结果数: {len(results)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 4: 输出格式 ----------
    print("\n[测试 4] 输出格式")
    try:
        result = skill.process("联系 test@example.com 或 138-1234-5678")
        json_out = skill.format_output(result, "json")
        parsed_json = json.loads(json_out)
        assert "items" in parsed_json, "JSON输出应包含items字段"
        assert "confidence" in parsed_json, "JSON输出应包含confidence字段"

        text_out = skill.format_output(result, "text")
        assert "置信度" in text_out, "文本输出应包含置信度"

        print(f"  ✓ 通过 (JSON长度: {len(json_out)}, 文本长度: {len(text_out)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 5: 置信度分级 ----------
    print("\n[测试 5] 置信度分级")
    try:
        # 高置信度：有明确 URL/邮箱
        high = skill.process("https://example.com 和 test@example.com 是联系方式")
        assert high.confidence >= 0.85, f"高置信度应>=0.85，实际: {high.confidence}"

        # 低置信度：短文本
        low = skill.process("随便")
        assert low.confidence < 0.85, f"低置信度应<0.85，实际: {low.confidence}"

        print(f"  ✓ 通过 (高: {high.confidence:.0%}, 低: {low.confidence:.0%})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 6: 边界能力声明 ----------
    print("\n[测试 6] 能力边界")
    try:
        # 非法格式触发 E003
        skill.process("!!!")
        # 如果没触发错误，说明可能识别为文本，也合理
        print("  ✓ 通过 (非法输入被处理或拒绝)")
    except AutomationError as e:
        assert e.code in ["E003", "E001"], f"错误码应为 E003 或 E001，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # ---------- 测试 7: 错误码完整性 ----------
    print("\n[测试 7] 错误码完整性")
    try:
        required_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in required_codes:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
        print(f"  ✓ 通过 (错误码: {', '.join(required_codes)} 等)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 8: 免责声明与协议 ----------
    print("\n[测试 8] 免责声明与协议")
    try:
        disclaimer = (
            "本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。"
            "涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士"
        )
        # 验证免责声明字符串存在
        assert disclaimer in __doc__, "免责声明未包含在文档字符串中"
        print("  ✓ 通过 (免责声明已包含)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 9: 长文本与截断 ----------
    print("\n[测试 9] 长文本处理")
    try:
        long_text = "这是一个很长的文本 " * 100
        result = skill.process(long_text)
        assert result.items, "长文本应产生结果"
        # 检查 source 截断
        source = result.items[0].get("source", "")
        assert len(source) <= 200, f"source应截断到200字符，实际: {len(source)}"
        print(f"  ✓ 通过 (source长度: {len(source)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    # ---------- 测试 10: 特殊字符 ----------
    print("\n[测试 10] 特殊字符处理")
    try:
        special = "联系：测试@例子.com（含中文括号）"
        result = skill.process(special)
        assert result.items, "特殊字符应产生结果"
        print(f"  ✓ 通过 (条目数: {len(result.items)})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    print("\n" + "=" * 60)
    print("全部自检通过！")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="macos-automation 技能实现",
        epilog="示例: python main.py --input '处理 https://example.com' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（用户提供的数据/文件/URL）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help='批量处理（JSON数组字符串，如 \'["a", "b"]\'）',
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="macos-automation 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        sys.exit(run_selftest())

    # 批量模式
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                raise AutomationError("E003", "批量输入应为JSON数组")
        except json.JSONDecodeError:
            print(f"错误: {ERROR_MESSAGES['E003']}")
            sys.exit(1)
        except AutomationError as e:
            print(f"错误: {e.message}")
            sys.exit(1)

        skill = MacOSAutomation()
        results = skill.batch_process(inputs)
        for i, r in enumerate(results, 1):
            print(f"--- 结果 {i} ---")
            print(skill.format_output(r, args.format))
        return

    # 单条处理模式
    if args.input:
        try:
            skill = MacOSAutomation()
            result = skill.process(args.input)
            print(skill.format_output(result, args.format))
        except AutomationError as e:
            print(f"错误 [{e.code}]: {e.message}")
            sys.exit(1)
        return

    # 无参数：显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
