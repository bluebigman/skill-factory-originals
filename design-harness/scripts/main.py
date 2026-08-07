#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design-harness 技能实现脚本
版本: 1.1.0
说明: 将用户提供的半成品想法/数据/URL 整理为结构化 Markdown 设计方案。
      标准库实现，无第三方依赖。
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出写入失败，请检查文件路径",
    "E008": "输入读取失败，请检查数据来源",
    "E009": "参数解析失败，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class InputItem:
    """单个输入条目"""
    raw: str
    content_type: str = "text"  # text / url / file
    key_points: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class OutputResult:
    """结构化输出结果"""
    title: str = ""
    sections: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    markdown: str = ""
    items: List[InputItem] = field(default_factory=list)  # 保存输入项


# ============================================================
# 核心处理逻辑
# ============================================================
class DesignHarness:
    """设计工具主处理器"""

    # 能力边界声明
    CAPABILITIES = [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ]
    LIMITATIONS = [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ]

    def __init__(self) -> None:
        self.items: List[InputItem] = []
        self.output: OutputResult = OutputResult()

    # ---------- 输入解析 ----------
    def parse_input(self, raw_input: str) -> List[InputItem]:
        """解析输入内容，识别关键信息"""
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # 按行拆分，识别不同条目
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        items = []

        for line in lines:
            item = InputItem(raw=line)
            # 识别输入类型
            if re.match(r"^https?://", line, re.IGNORECASE):
                item.content_type = "url"
            elif re.match(r"^[\w\-. /\\]+\.\w+$", line):
                item.content_type = "file"
            else:
                item.content_type = "text"

            # 提取关键信息（简单分词）
            words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", line)
            item.key_points = words[:10]  # 最多保留 10 个关键词
            item.confidence = self._estimate_confidence(item)
            items.append(item)

        return items

    def _estimate_confidence(self, item: InputItem) -> float:
        """估算置信度"""
        score = 0.0
        # 基于关键信息数量
        if len(item.key_points) >= 3:
            score += 0.5
        elif len(item.key_points) >= 1:
            score += 0.3

        # 基于输入类型
        if item.content_type == "url":
            score += 0.3  # URL 格式明确
        elif item.content_type == "file":
            score += 0.2
        else:
            score += 0.1

        # 基于文本长度
        if len(item.raw) >= 50:
            score += 0.2
        elif len(item.raw) >= 10:
            score += 0.1

        return min(score, 1.0)

    # ---------- 核心处理 ----------
    def process(self, raw_input: str, title: str = "") -> OutputResult:
        """执行完整处理流程"""
        try:
            # Step 1: 解析输入
            self.items = self.parse_input(raw_input)
            if not self.items:
                raise ValueError("E002")

            # Step 2: 生成结构化输出
            self.output = OutputResult(title=title or "设计方案")
            self.output.items = self.items.copy()  # 保存输入项到输出结果
            self._build_sections()
            self._calculate_confidence()
            self._generate_markdown()

            # Step 3: 校验输出
            self._validate_output()

            return self.output

        except ValueError as e:
            code = str(e)
            raise RuntimeError(f"{code}: {ERROR_CODES.get(code, ERROR_CODES['E010'])}")
        except Exception:
            raise RuntimeError(f"E006: {ERROR_CODES['E006']}")

    def _build_sections(self) -> None:
        """构建输出章节"""
        # 概述
        overview = []
        for item in self.items:
            if item.content_type == "url":
                overview.append(f"- 参考链接: {item.raw}")
            elif item.content_type == "file":
                overview.append(f"- 数据文件: {item.raw}")
            else:
                overview.append(f"- 输入内容: {item.raw[:50]}{'...' if len(item.raw) > 50 else ''}")
        self.output.sections["概述"] = overview

        # 关键信息
        key_info = []
        for item in self.items:
            if item.key_points:
                key_info.append(f"- 关键词: {', '.join(item.key_points[:5])}")
        self.output.sections["关键信息"] = key_info

        # 置信度评估
        confidence_note = []
        for item in self.items:
            if item.confidence >= 0.9:
                confidence_note.append(f"- {item.raw[:30]}... 置信度: {item.confidence:.0%} (直接输出)")
            elif item.confidence >= 0.85:
                confidence_note.append(f"- {item.raw[:30]}... 置信度: {item.confidence:.0%} (建议复核)")
            else:
                confidence_note.append(f"- {item.raw[:30]}... 置信度: {item.confidence:.0%} [需核实]")
        self.output.sections["置信度评估"] = confidence_note

    def _calculate_confidence(self) -> None:
        """计算整体置信度"""
        if not self.items:
            self.output.confidence = 0.0
            return
        self.output.confidence = sum(i.confidence for i in self.items) / len(self.items)

    def _generate_markdown(self) -> None:
        """生成 Markdown 格式输出"""
        md_lines = [f"# {self.output.title}", ""]

        # 元信息
        md_lines.append("> 由 design-harness 自动生成")
        md_lines.append("")

        # 章节内容
        for section_name, lines in self.output.sections.items():
            md_lines.append(f"## {section_name}")
            md_lines.extend(lines)
            md_lines.append("")

        # 整体置信度
        md_lines.append("## 整体置信度")
        md_lines.append(f"- 综合置信度: {self.output.confidence:.0%}")
        if self.output.confidence < 0.85:
            md_lines.append("- 警告: 置信度偏低，请人工复核关键结果")
        md_lines.append("")

        # 能力边界声明
        md_lines.append("## 能力边界")
        md_lines.append("**支持:**")
        for cap in self.CAPABILITIES:
            md_lines.append(f"- {cap}")
        md_lines.append("**不支持:**")
        for limit in self.LIMITATIONS:
            md_lines.append(f"- {limit}")

        self.output.markdown = "\n".join(md_lines)

    def _validate_output(self) -> None:
        """输出自查"""
        # 检查字段完整性
        if not self.output.sections:
            self.output.warnings.append("输出章节为空")
        if not self.output.markdown:
            self.output.warnings.append("Markdown 内容为空")
        # 检查置信度标注
        if self.output.confidence < 0.85:
            self.output.warnings.append("置信度低于 85%，已标注 [需核实]")

    # ---------- 批量处理 ----------
    def batch_process(self, inputs: List[str], title: str = "") -> List[OutputResult]:
        """批量处理多个输入"""
        results = []
        for idx, raw in enumerate(inputs):
            try:
                result = self.process(raw, title=f"{title} - 批次{idx + 1}" if title else f"方案{idx + 1}")
                results.append(result)
            except RuntimeError as e:
                # 单条失败不影响其他
                error_result = OutputResult(title=f"方案{idx + 1} (失败)")
                error_result.warnings.append(str(e))
                results.append(error_result)
        return results


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置自检，不依赖外部文件/网络"""
    print("=" * 60)
    print("design-harness 自检开始")
    print("=" * 60)

    harness = DesignHarness()

    # 测试用例 1: 基本文本处理
    print("\n[测试 1] 基本文本处理")
    sample1 = "设计一个用户登录系统，支持 OAuth2.0 和短信验证码，需要高可用部署"
    try:
        result1 = harness.process(sample1, title="登录系统设计")
        assert result1.markdown, "输出为空"
        assert "登录系统设计" in result1.markdown, "标题未包含"
        assert "关键信息" in result1.markdown, "缺少关键信息章节"
        assert result1.confidence > 0.5, "置信度过低"
        print(f"  ✓ 通过 (置信度: {result1.confidence:.0%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 2: URL 处理
    print("\n[测试 2] URL 处理")
    sample2 = "https://example.com/api/docs"
    try:
        result2 = harness.process(sample2, title="API 文档分析")
        assert result2.markdown, "输出为空"
        assert "参考链接" in result2.markdown, "未识别 URL"
        print(f"  ✓ 通过 (置信度: {result2.confidence:.0%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 3: 批量处理
    print("\n[测试 3] 批量处理")
    samples = [
        "第一个批量输入，包含关键词A和关键词B，用于测试",
        "第二个批量输入，包含关键词C和关键词D，用于测试",
        "https://example.org/data",
    ]
    try:
        results = harness.batch_process(samples, title="批量方案")
        assert len(results) == 3, "批量数量错误"
        for idx, r in enumerate(results):
            assert r.markdown, f"第{idx + 1}个结果为空"
        print(f"  ✓ 通过 (共 {len(results)} 条)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 4: 错误处理
    print("\n[测试 4] 错误处理")
    try:
        harness.process("")
        print("  ✗ 失败: 空输入未报错")
        return False
    except RuntimeError as e:
        assert "E001" in str(e), "错误码不正确"
        print(f"  ✓ 通过 (错误码正确: {str(e)[:20]}...)")

    # 测试用例 5: 置信度评估
    print("\n[测试 5] 置信度评估")
    sample5 = "短文本"
    try:
        result5 = harness.process(sample5, title="短文本测试")
        assert result5.confidence < 0.9, "短文本置信度应较低"
        print(f"  ✓ 通过 (置信度: {result5.confidence:.0%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 6: Markdown 格式完整性
    print("\n[测试 6] Markdown 格式")
    sample6 = "这是一个更长的输入文本，用于验证 Markdown 格式输出的完整性，确保所有章节都能正确生成。"
    try:
        result6 = harness.process(sample6, title="格式测试")
        assert result6.markdown.startswith("# "), "缺少一级标题"
        assert "## " in result6.markdown, "缺少二级标题"
        assert result6.markdown.count("## ") >= 3, "章节数量不足"
        print(f"  ✓ 通过 (共 {result6.markdown.count('## ')} 个章节)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 7: 中文内容处理
    print("\n[测试 7] 中文内容")
    sample7 = "设计一个电商平台，需要支持商品管理、订单处理、支付集成，以及用户评价功能"
    try:
        result7 = harness.process(sample7, title="电商平台设计")
        assert "电商平台设计" in result7.markdown, "中文标题未正确显示"
        assert len(result7.sections) > 0, "章节为空"
        assert len(result7.items) > 0, "输入项为空"
        assert result7.items[0].key_points, "关键词为空"
        print(f"  ✓ 通过 (关键词提取: {result7.items[0].key_points[:3]})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="design-harness: 将输入转换为结构化设计方案",
        epilog="示例: python main.py --input '设计一个登录系统' --title '登录系统设计'"
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（文本/URL/文件路径）")
    parser.add_argument("--title", "-t", type=str, default="设计方案", help="输出标题")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径（.md）")
    parser.add_argument("--batch", "-b", type=str, help="批量输入，用 | 分隔多个输入")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    try:
        args = parser.parse_args()
    except SystemExit:
        return 1

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    harness = DesignHarness()

    try:
        # 批量模式
        if args.batch:
            inputs = [s.strip() for s in args.batch.split("|") if s.strip()]
            results = harness.batch_process(inputs, title=args.title)
            for idx, result in enumerate(results):
                print(f"\n--- 方案 {idx + 1} ---")
                print(result.markdown)
            return 0

        # 单条模式
        if not args.input:
            print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
            return 1

        result = harness.process(args.input, title=args.title)

        # 输出到文件
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result.markdown)
                print(f"已输出到: {args.output}")
            except OSError:
                print(f"E007: {ERROR_CODES['E007']}", file=sys.stderr)
                return 1
        else:
            print(result.markdown)

        # 显示警告
        for warning in result.warnings:
            print(f"[警告] {warning}", file=sys.stderr)

        return 0

    except RuntimeError as e:
        code = str(e).split(":")[0]
        print(f"{code}: {ERROR_CODES.get(code, ERROR_CODES['E010'])}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']} ({str(e)})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
