#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pdfmd - PDF转文档（Clean-room 独立实现）

依据功能规格独立编写的 PDF 转 Markdown 转换器。
核心能力：
  1. 智能标题检测（基于字号/加粗/位置启发式）
  2. 自动页眉页脚去除（基于重复文本模式）
  3. 孤立片段合并（基于段落连续性启发式）
  4. 置信度评估与标注
  5. 批量处理支持

仅使用 Python 标准库，无第三方依赖。
用法：
  python scripts/main.py --selftest    # 离线自检
  python scripts/main.py <input.txt>   # 处理文本文件（模拟 PDF 提取后的文本）
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERR_INPUT_EMPTY = "E001"           # 输入为空
ERR_KEY_INFO_MISSING = "E002"      # 关键信息缺失
ERR_INPUT_FORMAT = "E003"          # 输入格式错误
ERR_OUT_OF_SCOPE = "E004"          # 超出能力边界
ERR_LOW_CONFIDENCE = "E005"        # 置信度过低
ERR_INTERNAL = "E006"              # 内部处理错误
ERR_IO_READ = "E007"               # 读取失败
ERR_IO_WRITE = "E008"              # 写入失败
ERR_INVALID_PARAM = "E009"         # 参数无效
ERR_UNSUPPORTED = "E010"           # 不支持的操作

# ============================================================
# 数据结构
# ============================================================

@dataclass
class LineInfo:
    """单行文本及其启发式特征"""
    text: str
    font_size: float = 12.0          # 相对字号（默认正文）
    is_bold: bool = False
    indent: int = 0                  # 缩进级别（0=无缩进）
    page_num: int = 0
    y_position: float = 0.5          # 页面纵向位置（0=顶部，1=底部）

    @property
    def is_heading_candidate(self) -> bool:
        """是否为标题候选（字号大/加粗/短行）"""
        if not self.text.strip():
            return False
        # 启发式：字号 > 14 或加粗，且长度 < 80
        if self.font_size >= 14.0 or self.is_bold:
            if len(self.text.strip()) < 80:
                return True
        return False

    @property
    def is_header_footer_candidate(self) -> bool:
        """是否为页眉/页脚候选（短文本、位于页面边缘）"""
        text = self.text.strip()
        if not text:
            return False
        # 页眉页脚通常：长度短、位于页面顶部或底部
        if len(text) > 50:
            return False
        # 顶部 10% 或底部 10% 区域
        if self.y_position < 0.1 or self.y_position > 0.9:
            return True
        return False

    @property
    def is_orphan_fragment(self) -> bool:
        """是否为孤立片段（以连字符结尾/极短行）"""
        text = self.text.strip()
        if not text:
            return False
        # 以连字符结尾，或长度 < 20 且不以句号结尾
        if text.endswith('-'):
            return True
        if len(text) < 20 and not text.endswith(('.', '。', '！', '？', '!', '?')):
            return True
        return False


@dataclass
class Document:
    """解析后的文档模型"""
    lines: List[LineInfo] = field(default_factory=list)
    headings: List[int] = field(default_factory=list)      # 标题行索引
    removed_lines: List[int] = field(default_factory=list) # 被移除的页眉页脚索引

    def add_line(self, line: LineInfo) -> None:
        self.lines.append(line)

    def remove_line(self, idx: int) -> None:
        if idx not in self.removed_lines:
            self.removed_lines.append(idx)

    def get_content_lines(self) -> List[LineInfo]:
        """获取未被移除的行（按原顺序）"""
        removed_set = set(self.removed_lines)
        return [line for i, line in enumerate(self.lines) if i not in removed_set]


# ============================================================
# 核心处理逻辑
# ============================================================

def parse_input(text: str) -> List[LineInfo]:
    """
    将输入文本解析为 LineInfo 列表。
    采用启发式规则推断字号/加粗/位置。
    输入格式（模拟 PDF 提取后的纯文本）：
      - 每行以 [S=字号, B=加粗, Y=纵向位置] 可选前缀开头
      - 或纯文本（使用默认值）
    """
    if not text or not text.strip():
        raise ValueError(ERR_INPUT_EMPTY)

    lines: List[LineInfo] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # 尝试解析元数据前缀
        font_size = 12.0
        is_bold = False
        y_position = 0.5
        indent = 0
        content = line

        meta_match = re.match(r'^\[S=([\d.]+),\s*B=(\d),\s*Y=([\d.]+)\]\s*(.*)$', line)
        if meta_match:
            font_size = float(meta_match.group(1))
            is_bold = meta_match.group(2) == '1'
            y_position = float(meta_match.group(3))
            content = meta_match.group(4)

        # 计算缩进（前导空格数）
        stripped = content.lstrip()
        indent = len(content) - len(stripped)

        lines.append(LineInfo(
            text=stripped,
            font_size=font_size,
            is_bold=is_bold,
            indent=indent,
            y_position=y_position
        ))

    if not lines:
        raise ValueError(ERR_INPUT_EMPTY)
    return lines


def detect_headings(doc: Document) -> None:
    """智能标题检测（基于字号/加粗/位置启发式）"""
    doc.headings.clear()
    for i, line in enumerate(doc.lines):
        if i in doc.removed_lines:
            continue
        if line.is_heading_candidate:
            doc.headings.append(i)


def remove_header_footer(doc: Document) -> None:
    """
    自动页眉页脚去除。
    策略：在页面顶部/底部区域中，出现 >=2 次的相同文本视为页眉/页脚。
    优化：只考虑非标题、非正文的长文本模式。
    """
    # 收集页面边缘的候选文本
    edge_texts: dict = {}
    for i, line in enumerate(doc.lines):
        if line.is_header_footer_candidate:
            text = line.text.strip()
            # 排除看起来像标题的行（字号大或加粗）
            if line.font_size < 14.0 and not line.is_bold:
                if text in edge_texts:
                    edge_texts[text].append(i)
                else:
                    edge_texts[text] = [i]

    # 出现 >=2 次的边缘文本视为页眉/页脚
    for text, indices in edge_texts.items():
        if len(indices) >= 2:
            for idx in indices:
                doc.remove_line(idx)


def merge_orphan_fragments(doc: Document) -> List[LineInfo]:
    """
    孤立片段合并。
    将孤立片段与下一行合并（若下一行存在且非标题）。
    返回合并后的行列表。
    """
    content_lines = doc.get_content_lines()
    merged: List[LineInfo] = []
    i = 0
    while i < len(content_lines):
        current = content_lines[i]
        if current.is_orphan_fragment and i + 1 < len(content_lines):
            next_line = content_lines[i + 1]
            # 不合并到标题行
            if not next_line.is_heading_candidate:
                # 合并：去掉连字符，拼接
                if current.text.endswith('-'):
                    merged_text = current.text.rstrip('-').strip() + next_line.text
                else:
                    merged_text = current.text + " " + next_line.text
                merged_line = LineInfo(
                    text=merged_text,
                    font_size=current.font_size,
                    is_bold=current.is_bold,
                    indent=current.indent,
                    y_position=current.y_position
                )
                merged.append(merged_line)
                i += 2
                continue
        merged.append(current)
        i += 1
    return merged


def evaluate_confidence(doc: Document, merged_lines: List[LineInfo]) -> Tuple[float, List[str]]:
    """
    置信度评估。
    返回 (置信度百分比, 不确定点列表)
    """
    total_lines = len(doc.lines)
    if total_lines == 0:
        return 0.0, ["输入为空"]

    removed_count = len(doc.removed_lines)
    headings_count = len(doc.headings)
    merged_count = len(doc.lines) - len(merged_lines)  # 合并后减少的行数

    # 基础置信度：100
    confidence = 100.0
    uncertainties: List[str] = []

    # 页眉页脚移除比例过高 => 可能误删
    if total_lines > 0:
        removal_ratio = removed_count / total_lines
        if removal_ratio > 0.3:
            confidence -= 15
            uncertainties.append("页眉页脚移除比例偏高，可能存在误删")

    # 大量合并 => 可能错误合并
    if total_lines > 0:
        merge_ratio = merged_count / total_lines
        if merge_ratio > 0.2:
            confidence -= 10
            uncertainties.append("孤立片段合并比例偏高，可能存在误合并")

    # 标题占比异常
    if total_lines > 0:
        heading_ratio = headings_count / total_lines
        if heading_ratio > 0.3:
            confidence -= 10
            uncertainties.append("标题占比偏高，可能存在误判")

    # 无标题 => 可能未识别
    if headings_count == 0:
        confidence -= 5
        uncertainties.append("未检测到标题，结果可能不完整")

    confidence = max(0.0, min(100.0, confidence))
    return confidence, uncertainties


def convert_to_markdown(doc: Document, merged_lines: List[LineInfo]) -> str:
    """
    将处理后的行转换为 Markdown 格式。
    标题行使用 # 前缀，其他行原样输出。
    """
    # 构建标题索引集合（基于原始行索引）
    heading_set = set(doc.headings)

    # 需要将 merged_lines 映射回原始索引
    # 简化处理：直接使用 merged_lines 中的 is_heading_candidate 属性
    md_lines: List[str] = []
    for line in merged_lines:
        if line.is_heading_candidate:
            # 根据字号决定标题级别
            if line.font_size >= 20:
                level = 1
            elif line.font_size >= 16:
                level = 2
            else:
                level = 3
            md_lines.append(f"{'#' * level} {line.text}")
        else:
            md_lines.append(line.text)

    return "\n\n".join(md_lines)


def process_text(text: str) -> dict:
    """
    核心处理流程。
    输入：原始文本
    输出：包含结果和置信度的字典
    """
    result = {
        "success": False,
        "markdown": "",
        "confidence": 0.0,
        "uncertainties": [],
        "error_code": None,
        "error_msg": ""
    }

    try:
        # Step 1: 解析输入
        lines = parse_input(text)
        doc = Document()
        for line in lines:
            doc.add_line(line)

        # Step 2: 页眉页脚去除
        remove_header_footer(doc)

        # Step 3: 标题检测
        detect_headings(doc)

        # Step 4: 孤立片段合并
        merged_lines = merge_orphan_fragments(doc)

        # Step 5: 置信度评估
        confidence, uncertainties = evaluate_confidence(doc, merged_lines)

        # Step 6: 生成 Markdown
        markdown = convert_to_markdown(doc, merged_lines)

        # Step 7: 根据置信度标注
        if confidence >= 90:
            pass  # 直接输出
        elif confidence >= 85:
            markdown = "<!-- 建议复核 -->\n" + markdown
        else:
            markdown = "<!-- [需核实] -->\n" + markdown

        result["success"] = True
        result["markdown"] = markdown
        result["confidence"] = confidence
        result["uncertainties"] = uncertainties

    except ValueError as e:
        result["error_code"] = str(e)
        result["error_msg"] = str(e)
    except Exception as e:
        result["error_code"] = ERR_INTERNAL
        result["error_msg"] = f"内部处理错误: {str(e)}"

    return result


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读取外部文件，不依赖工作目录，不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健。
    """
    print("[selftest] 开始离线自检...")
    failures = 0

    # ---------- 测试用例 1：基本转换 ----------
    sample1 = (
        "[S=24.0, B=1, Y=0.05] 产品需求文档\n"
        "[S=12.0, B=0, Y=0.15] 版本：1.0\n"
        "[S=12.0, B=0, Y=0.20] 日期：2026-01-01\n"
        "[S=16.0, B=1, Y=0.30] 简介\n"
        "[S=12.0, B=0, Y=0.40] 这是一个示例文档，用于测试转换功能。\n"
        "[S=12.0, B=0, Y=0.45] 它包含多个段落，用于验证处理逻辑。\n"
        "[S=16.0, B=1, Y=0.60] 功能列表\n"
        "[S=12.0, B=0, Y=0.70] 支持标题检测\n"
        "[S=12.0, B=0, Y=0.75] 支持页眉页脚去除\n"
        "[S=12.0, B=0, Y=0.80] 支持孤立片段合并\n"
    )
    res1 = process_text(sample1)
    assert res1["success"], f"测试1失败：{res1.get('error_msg')}"
    assert res1["confidence"] >= 60, f"测试1置信度过低：{res1['confidence']}"
    assert "产品需求文档" in res1["markdown"], "测试1：未找到标题"
    assert "简介" in res1["markdown"], "测试1：未找到二级标题"
    assert "支持标题检测" in res1["markdown"], "测试1：正文缺失"
    print("[selftest] 测试1（基本转换）通过")

    # ---------- 测试用例 2：页眉页脚去除 ----------
    sample2 = (
        "[S=10.0, B=0, Y=0.02] 公司内部文档\n"
        "[S=24.0, B=1, Y=0.05] 季度报告\n"
        "[S=12.0, B=0, Y=0.20] 本季度业绩表现良好。\n"
        "[S=12.0, B=0, Y=0.30] 营收增长显著。\n"
        "[S=10.0, B=0, Y=0.95] 公司内部文档\n"
        "[S=10.0, B=0, Y=0.98] 第 1 页\n"
    )
    res2 = process_text(sample2)
    assert res2["success"], f"测试2失败：{res2.get('error_msg')}"
    assert "季度报告" in res2["markdown"], "测试2：未找到标题"
    assert "公司内部文档" not in res2["markdown"], "测试2：页眉未去除"
    assert "第 1 页" not in res2["markdown"], "测试2：页脚未去除"
    print("[selftest] 测试2（页眉页脚去除）通过")

    # ---------- 测试用例 3：孤立片段合并 ----------
    sample3 = (
        "[S=24.0, B=1, Y=0.05] 技术规格\n"
        "[S=12.0, B=0, Y=0.20] 系统需要支持高并- 发处理\n"
        "[S=12.0, B=0, Y=0.30] 以及低延迟响应。\n"
        "[S=12.0, B=0, Y=0.40] 这是一个短句\n"
        "[S=12.0, B=0, Y=0.50] 后续内容。\n"
    )
    res3 = process_text(sample3)
    assert res3["success"], f"测试3失败：{res3.get('error_msg')}"
    assert "高并发处理" in res3["markdown"], "测试3：孤立片段未正确合并"
    print("[selftest] 测试3（孤立片段合并）通过")

    # ---------- 测试用例 4：空输入 ----------
    res4 = process_text("")
    assert not res4["success"], "测试4：空输入应失败"
    assert res4["error_code"] == ERR_INPUT_EMPTY, f"测试4：错误码应为 E001，实际 {res4['error_code']}"
    print("[selftest] 测试4（空输入处理）通过")

    # ---------- 测试用例 5：批量处理 ----------
    samples = [sample1, sample2, sample3]
    for i, s in enumerate(samples):
        r = process_text(s)
        assert r["success"], f"测试5：批量样例{i}失败"
        assert r["confidence"] >= 50, f"测试5：批量样例{i}置信度过低"
    print("[selftest] 测试5（批量处理）通过")

    # ---------- 测试用例 6：标题级别 ----------
    sample6 = (
        "[S=28.0, B=1, Y=0.05] 一级标题\n"
        "[S=18.0, B=1, Y=0.15] 二级标题\n"
        "[S=14.0, B=1, Y=0.25] 三级标题\n"
        "[S=12.0, B=0, Y=0.35] 正文内容\n"
    )
    res6 = process_text(sample6)
    assert res6["success"], f"测试6失败：{res6.get('error_msg')}"
    assert "# 一级标题" in res6["markdown"], "测试6：一级标题级别错误"
    assert "## 二级标题" in res6["markdown"], "测试6：二级标题级别错误"
    assert "### 三级标题" in res6["markdown"], "测试6：三级标题级别错误"
    print("[selftest] 测试6（标题级别）通过")

    # ---------- 测试用例 7：置信度标注 ----------
    sample7 = "[S=12.0, B=0, Y=0.50] 只有一段文字，没有标题。"
    res7 = process_text(sample7)
    assert res7["success"], f"测试7失败：{res7.get('error_msg')}"
    assert res7["confidence"] < 100, "测试7：低置信度场景应小于100"
    print("[selftest] 测试7（置信度评估）通过")

    # ---------- 测试用例 8：错误码体系 ----------
    # 输入格式错误（无法解析的元数据）
    bad_input = "[S=abc] 无法解析"
    try:
        parse_input(bad_input)
        print("[selftest] 测试8：应抛出异常但未抛出")
        failures += 1
    except ValueError:
        pass  # 预期行为
    except Exception:
        print("[selftest] 测试8：抛出了非预期异常")
        failures += 1

    # ---------- 测试用例 9：边界处理 ----------
    # 大量重复页眉
    sample9 = []
    for i in range(5):
        sample9.append(f"[S=10.0, B=0, Y=0.03] 页眉文本")
    sample9.append("[S=20.0, B=1, Y=0.10] 正式内容")
    sample9.append("[S=12.0, B=0, Y=0.50] 这是正文内容，用于测试。")
    for i in range(5):
        sample9.append(f"[S=10.0, B=0, Y=0.97] 页脚文本")
    res9 = process_text("\n".join(sample9))
    assert res9["success"], f"测试9失败：{res9.get('error_msg')}"
    assert "页眉文本" not in res9["markdown"], "测试9：页眉未去除"
    assert "页脚文本" not in res9["markdown"], "测试9：页脚未去除"
    assert "正式内容" in res9["markdown"], "测试9：正文内容缺失"
    print("[selftest] 测试9（边界处理）通过")

    # ---------- 测试用例 10：长文档处理 ----------
    long_lines = ["[S=24.0, B=1, Y=0.05] 长文档测试"]
    for i in range(100):
        long_lines.append(f"[S=12.0, B=0, Y={0.1 + i * 0.008:.2f}] 这是第 {i} 行正文内容。")
    res10 = process_text("\n".join(long_lines))
    assert res10["success"], f"测试10失败：{res10.get('error_msg')}"
    assert "长文档测试" in res10["markdown"], "测试10：标题缺失"
    assert "第 50 行" in res10["markdown"], "测试10：正文缺失"
    print("[selftest] 测试10（长文档处理）通过")

    # ---------- 汇总 ----------
    if failures == 0:
        print("[selftest] 全部测试通过 ✓")
        return 0
    else:
        print(f"[selftest] 测试失败：{failures} 项")
        return 1


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="pdfmd - PDF转文档转换器",
        epilog="示例：python scripts/main.py input.txt"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="输入文本文件路径（模拟 PDF 提取后的文本）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读取外部文件）"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="输出 Markdown 文件路径（默认输出到 stdout）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    if not args.input_file:
        print(f"错误 [{ERR_INPUT_EMPTY}]: 请提供输入文件路径，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # 读取输入文件
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"错误 [{ERR_IO_READ}]: 文件不存在：{args.input_file}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"错误 [{ERR_IO_READ}]: 无权限读取文件：{args.input_file}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERR_IO_READ}]: 读取失败：{str(e)}", file=sys.stderr)
        return 1

    # 处理
    result = process_text(content)

    if not result["success"]:
        error_msg = result.get("error_msg", "未知错误")
        error_code = result.get("error_code", ERR_INTERNAL)
        print(f"错误 [{error_code}]: {error_msg}", file=sys.stderr)
        return 1

    # 输出
    output_text = result["markdown"]
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"已写入：{args.output}")
        except Exception as e:
            print(f"错误 [{ERR_IO_WRITE}]: 写入失败：{str(e)}", file=sys.stderr)
            return 1
    else:
        print(output_text)

    # 置信度提示
    confidence = result["confidence"]
    if confidence < 85:
        print(f"\n提示：置信度 {confidence:.1f}%，结果可能不准确。", file=sys.stderr)
        for u in result["uncertainties"]:
            print(f"  - {u}", file=sys.stderr)
    elif confidence < 90:
        print(f"\n提示：置信度 {confidence:.1f}%，建议复核。", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
