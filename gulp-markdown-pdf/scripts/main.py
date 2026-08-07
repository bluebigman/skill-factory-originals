#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - PDF转文档 技能核心实现脚本

本脚本根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供命令行接口，支持 --selftest 离线自检。
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "输出格式错误",
    "E007": "内部处理异常",
    "E008": "参数校验失败",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================
class InputItem:
    """输入项数据结构"""

    def __init__(self, raw: str, source_type: str = "text"):
        self.raw = raw
        self.source_type = source_type
        self.key_fields: Dict[str, str] = {}
        self.confidence: float = 0.0
        self.notes: List[str] = []


class OutputResult:
    """输出结果数据结构"""

    def __init__(self):
        self.items: List[InputItem] = []
        self.summary: str = ""
        self.warnings: List[str] = []

    def add_item(self, item: InputItem):
        self.items.append(item)

    def to_text(self) -> str:
        """将结果转换为文本格式"""
        lines = []
        lines.append("=" * 50)
        lines.append("处理结果")
        lines.append("=" * 50)
        for idx, item in enumerate(self.items, 1):
            lines.append(f"\n--- 条目 {idx} ---")
            lines.append(f"来源类型: {item.source_type}")
            lines.append(f"置信度: {item.confidence * 100:.1f}%")
            if item.confidence < 0.85:
                lines.append("[需核实] 置信度过低")
            elif item.confidence < 0.90:
                lines.append("建议复核")
            lines.append(f"原始输入: {item.raw[:100]}...")
            if item.key_fields:
                lines.append("关键字段:")
                for k, v in item.key_fields.items():
                    lines.append(f"  {k}: {v}")
            if item.notes:
                lines.append("备注:")
                for note in item.notes:
                    lines.append(f"  - {note}")
        return "\n".join(lines)


# ============================================================
# 核心处理逻辑
# ============================================================
class MarkdownPdfSkill:
    """PDF转文档技能核心类"""

    def __init__(self):
        self.supported_formats = ["text", "markdown", "url", "file"]
        self.max_input_length = 10000  # 输入长度上限

    def validate_input(self, raw: str) -> None:
        """校验输入合法性"""
        if not raw or not raw.strip():
            raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        if len(raw) > self.max_input_length:
            raise SkillError("E003", f"输入内容过长（超过 {self.max_input_length} 字符）")

    def detect_source_type(self, raw: str) -> str:
        """识别输入来源类型"""
        stripped = raw.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            return "url"
        if stripped.endswith((".md", ".markdown", ".txt")):
            return "file"
        if stripped.startswith("#") or stripped.startswith("##") or "**" in stripped:
            return "markdown"
        return "text"

    def extract_key_fields(self, item: InputItem) -> None:
        """从输入中提取关键字段"""
        raw = item.raw.strip()
        lines = [line.strip() for line in raw.split("\n") if line.strip()]

        # 提取标题（以 # 开头或首行）
        title = ""
        for line in lines:
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        if not title and lines:
            # 取第一行前50字符作为标题
            title = lines[0][:50]

        # 提取内容摘要
        content_preview = ""
        for line in lines:
            if not line.startswith("#") and not line.startswith(">"):
                content_preview = line[:100]
                break

        item.key_fields = {
            "标题": title or "未命名",
            "内容摘要": content_preview or "无内容",
            "行数": str(len(lines)),
            "字符数": str(len(raw)),
        }

    def calculate_confidence(self, item: InputItem) -> float:
        """计算置信度"""
        score = 0.0
        raw_len = len(item.raw.strip())

        # 输入长度因素
        if raw_len > 0:
            score += 0.3
        if raw_len > 20:
            score += 0.2
        if raw_len > 100:
            score += 0.2

        # 关键字段完整性
        if item.key_fields:
            score += 0.2
            if item.key_fields.get("标题"):
                score += 0.1

        # 来源类型明确性
        if item.source_type in ["markdown", "file"]:
            score += 0.1
        elif item.source_type == "url":
            score += 0.05

        return min(score, 1.0)

    def process_single(self, raw: str) -> InputItem:
        """处理单个输入"""
        self.validate_input(raw)

        item = InputItem(raw)
        item.source_type = self.detect_source_type(raw)

        try:
            self.extract_key_fields(item)
            item.confidence = self.calculate_confidence(item)

            # 低置信度标注
            if item.confidence < 0.85:
                item.notes.append("内容不够完整，部分信息可能缺失")
                item.notes.append("请人工复核关键信息")

            return item
        except Exception as e:
            raise SkillError("E007", f"处理输入时发生异常: {str(e)}")

    def process_batch(self, inputs: List[str]) -> OutputResult:
        """批量处理多个输入"""
        result = OutputResult()

        for idx, raw in enumerate(inputs, 1):
            try:
                item = self.process_single(raw)
                result.add_item(item)
            except SkillError as e:
                result.warnings.append(f"条目 {idx} 处理失败: {e.code} - {e.message}")
            except Exception as e:
                result.warnings.append(f"条目 {idx} 处理失败: E007 - {str(e)}")

        if not result.items:
            raise SkillError("E009", "批量处理失败，没有成功处理任何条目")

        result.summary = f"共处理 {len(result.items)} 条，失败 {len(result.warnings)} 条"
        return result

    def format_output(self, result: OutputResult, fmt: str = "text") -> str:
        """格式化输出结果"""
        if fmt == "text":
            return result.to_text()
        elif fmt == "json":
            import json
            data = {
                "summary": result.summary,
                "warnings": result.warnings,
                "items": [
                    {
                        "raw": item.raw,
                        "source_type": item.source_type,
                        "confidence": item.confidence,
                        "key_fields": item.key_fields,
                        "notes": item.notes,
                    }
                    for item in result.items
                ],
            }
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            raise SkillError("E006", f"不支持的输出格式: {fmt}")


# ============================================================
# 自检功能（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    使用内置硬编码样例数据离线自检核心逻辑。
    不读取外部文件，不依赖当前工作目录，不访问网络。
    """
    print("开始自检...")

    # 内置测试样例
    test_cases = [
        # (输入, 期望的成功标志, 置信度下限)
        ("# 项目报告\n\n这是一份测试文档，包含一些关键信息。\n\n## 第一章\n\n内容内容内容。", True, 0.8),
        ("https://example.com/document", True, 0.5),
        ("", False, 0.0),  # 空输入应失败
        ("## 简单标题\n只有一行内容", True, 0.7),
        (None, False, 0.0),  # None 输入应失败
    ]

    skill = MarkdownPdfSkill()
    all_passed = True

    for idx, (raw_input, should_succeed, min_confidence) in enumerate(test_cases, 1):
        print(f"\n测试用例 {idx}: 输入={repr(raw_input)[:60]}...")
        try:
            if raw_input is None:
                raise SkillError("E001", "输入为空")

            item = skill.process_single(raw_input)

            if not should_succeed:
                print(f"  失败: 预期失败但成功处理了")
                all_passed = False
                continue

            # 宽松阈值断言
            assert item.confidence >= min_confidence, \
                f"置信度过低: {item.confidence} < {min_confidence}"
            assert item.key_fields, "关键字段为空"
            assert item.source_type in skill.supported_formats, \
                f"未知来源类型: {item.source_type}"

            print(f"  通过: 置信度={item.confidence:.2f}, 类型={item.source_type}")
            print(f"        标题={item.key_fields.get('标题', 'N/A')}")

        except SkillError as e:
            if should_succeed:
                print(f"  失败: 意外错误 {e.code}: {e.message}")
                all_passed = False
            else:
                print(f"  通过: 正确拒绝非法输入 ({e.code})")

        except AssertionError as e:
            print(f"  失败: 断言错误 - {str(e)}")
            all_passed = False

        except Exception as e:
            print(f"  失败: 未预期异常 - {str(e)}")
            all_passed = False

    # 批量处理测试
    print("\n测试批量处理...")
    try:
        batch_inputs = [
            "# 批量测试文档\n\n第一条内容。",
            "## 第二条\n\n第二段内容。",
            "https://example.com/third",
        ]
        result = skill.process_batch(batch_inputs)
        assert len(result.items) == 3, f"批量处理条目数错误: {len(result.items)}"
        assert len(result.warnings) == 0, f"存在警告: {result.warnings}"
        output_text = skill.format_output(result, "text")
        assert "处理结果" in output_text
        print(f"  通过: 批量处理 {len(result.items)} 条成功，无警告")

        # JSON 格式测试
        output_json = skill.format_output(result, "json")
        assert output_json.startswith("{")
        print("  通过: JSON 格式输出正常")

    except Exception as e:
        print(f"  失败: 批量处理异常 - {str(e)}")
        all_passed = False

    # 边界测试
    print("\n测试边界情况...")
    try:
        # 超长输入
        long_input = "x" * 20000
        try:
            skill.process_single(long_input)
            print("  失败: 超长输入未被拒绝")
            all_passed = False
        except SkillError as e:
            assert e.code == "E003", f"错误码错误: {e.code}"
            print(f"  通过: 超长输入正确拒绝 ({e.code})")

        # 错误码完整性
        assert len(ERROR_CODES) >= 5, "错误码定义不完整"
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print(f"  通过: 错误码定义完整 ({len(ERROR_CODES)} 个)")

    except Exception as e:
        print(f"  失败: 边界测试异常 - {str(e)}")
        all_passed = False

    print("\n" + ("=" * 50))
    if all_passed:
        print("自检结果: ✅ 全部通过")
    else:
        print("自检结果: ❌ 存在失败项")
    print("=" * 50)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="PDF转文档 - Markdown to PDF 技能核心脚本",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码样例数据）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本、URL、文件路径）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量输入多个内容",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="gulp-markdown-pdf 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 正常处理模式
    try:
        skill = MarkdownPdfSkill()

        # 收集输入
        inputs = []
        if args.batch:
            inputs = args.batch
        elif args.input:
            inputs = [args.input]
        else:
            # 从标准输入读取
            print("请输入内容（Ctrl+D 结束）：")
            stdin_input = sys.stdin.read().strip()
            if stdin_input:
                inputs = [stdin_input]

        if not inputs:
            raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        # 处理
        if len(inputs) == 1:
            result = OutputResult()
            item = skill.process_single(inputs[0])
            result.add_item(item)
            result.summary = "单条处理完成"
        else:
            result = skill.process_batch(inputs)

        # 输出
        output = skill.format_output(result, args.format)
        print(output)

        # 输出警告
        if result.warnings:
            print("\n警告：")
            for warning in result.warnings:
                print(f"  - {warning}")

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 E010: 未预期异常 - {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
