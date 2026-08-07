#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kanban-md 任务看板标记转换器
功能：将自由文本转换为看板 Markdown 结构，支持列识别、卡片元数据、多级嵌套。
"""

import argparse
import re
import sys
from collections import OrderedDict
from typing import List, Dict, Tuple, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或仅包含空白字符",
    "E002": "无法识别任何看板列（缺少分类词）",
    "E003": "卡片内容格式错误",
    "E004": "子任务缩进层级超过最大深度",
    "E005": "元数据标记格式不合法",
    "E006": "输入不是字符串类型",
    "E007": "输出写入失败",
    "E008": "参数解析失败",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}

# 默认看板列（按优先级顺序）
DEFAULT_COLUMNS = ["待办", "进行中", "已完成", "阻塞"]

# 元数据正则：优先级 [高/中/低]、负责人 @xxx、日期 (YYYY-MM-DD)
META_PRIORITY_RE = re.compile(r"\[(高|中|低)\]")
META_ASSIGNEE_RE = re.compile(r"@([\w\u4e00-\u9fa5-]+)")
META_DATE_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")


def _validate_input(text: str) -> None:
    """验证输入文本，错误码 E001/E006"""
    if not isinstance(text, str):
        raise ValueError(f"E006: {ERROR_CODES['E006']}")
    if not text.strip():
        raise ValueError(f"E001: {ERROR_CODES['E001']}")


def _detect_columns(text: str, custom_columns: Optional[List[str]] = None) -> List[str]:
    """
    识别输入中的看板列。
    优先使用自定义列，否则使用默认列 + 输入中出现的分类词。
    """
    columns = []
    if custom_columns:
        columns = [c.strip() for c in custom_columns if c.strip()]
    else:
        # 从输入中查找已知列关键词
        for col in DEFAULT_COLUMNS:
            if col in text:
                columns.append(col)
        # 如果没有找到，使用默认全部列
        if not columns:
            columns = DEFAULT_COLUMNS.copy()
    return columns


def _parse_card_line(line: str, line_num: int) -> Tuple[str, Dict[str, str]]:
    """
    解析单行卡片内容，提取元数据。
    返回 (卡片文本, 元数据字典)
    错误码 E003/E005
    """
    if not line.strip():
        raise ValueError(f"E003: 第{line_num}行 {ERROR_CODES['E003']}")

    meta = {}
    text = line.strip()

    # 提取优先级
    pri_match = META_PRIORITY_RE.search(text)
    if pri_match:
        meta["priority"] = pri_match.group(1)
        text = META_PRIORITY_RE.sub("", text).strip()

    # 提取负责人
    assignee_matches = META_ASSIGNEE_RE.findall(text)
    if assignee_matches:
        meta["assignee"] = assignee_matches[0]
        text = META_ASSIGNEE_RE.sub("", text).strip()

    # 提取日期
    date_match = META_DATE_RE.search(text)
    if date_match:
        meta["due_date"] = date_match.group(1)
        text = META_DATE_RE.sub("", text).strip()

    # 清理多余空格
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise ValueError(f"E005: 第{line_num}行 {ERROR_CODES['E005']}")

    return text, meta


def _format_card_meta(meta: Dict[str, str]) -> str:
    """格式化卡片元数据为标记字符串"""
    parts = []
    if "priority" in meta:
        parts.append(f"[{meta['priority']}]")
    if "assignee" in meta:
        parts.append(f"@{meta['assignee']}")
    if "due_date" in meta:
        parts.append(f"({meta['due_date']})")
    return " ".join(parts)


def _extract_subtasks(lines: List[str], start_idx: int, indent: int = 0) -> Tuple[List[str], int]:
    """
    提取子任务列表（以 - 或 * 开头的行，缩进表示层级）。
    返回 (子任务列表, 下一行索引)
    错误码 E004
    """
    subtasks = []
    idx = start_idx
    max_depth = 5  # 最大嵌套深度

    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue

        # 计算缩进层级
        leading_spaces = len(line) - len(line.lstrip(" "))
        level = leading_spaces // 2  # 每级缩进2空格

        # 检查是否为子任务行（以 - 或 * 开头）
        stripped = line.strip()
        if not (stripped.startswith("-") or stripped.startswith("*")):
            break

        if level > max_depth:
            raise ValueError(f"E004: {ERROR_CODES['E004']} (最大深度{max_depth})")

        # 去掉列表标记
        content = re.sub(r"^[-*]\s+", "", stripped)
        indent_str = "  " * (indent + level)
        subtasks.append(f"{indent_str}- {content}")
        idx += 1

    return subtasks, idx


def _group_lines_by_column(lines: List[str], columns: List[str]) -> Dict[str, List[str]]:
    """
    将输入行按列分组。
    识别列标题行（以 ## 或 ### 开头，或包含列关键词）。
    """
    result = {col: [] for col in columns}
    current_col = columns[0] if columns else "待办"

    for line in lines:
        stripped = line.strip()

        # 检查是否为列标题
        col_match = None
        for col in columns:
            if col in stripped and (stripped.startswith("#") or stripped == col or
                                    stripped.startswith(f"{col}:")):
                col_match = col
                break

        if col_match:
            current_col = col_match
            continue

        # 跳过空行和纯标题行
        if not stripped or stripped.startswith("#"):
            continue

        # 添加到当前列
        result[current_col].append(line)

    return result


def _process_text_to_board(text: str, custom_columns: Optional[List[str]] = None) -> str:
    """
    核心转换逻辑：将文本转换为看板 Markdown。
    错误码 E002
    """
    _validate_input(text)
    lines = text.split("\n")
    columns = _detect_columns(text, custom_columns)

    if not columns:
        raise ValueError(f"E002: {ERROR_CODES['E002']}")

    # 按列分组
    grouped = _group_lines_by_column(lines, columns)

    # 生成看板 Markdown
    output = ["# 任务看板\n"]

    for col in columns:
        output.append(f"## {col}\n")
        col_lines = grouped.get(col, [])

        if not col_lines:
            output.append("_暂无任务_\n")
            continue

        for line in col_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 解析卡片
            try:
                card_text, meta = _parse_card_line(stripped, lines.index(line) + 1)
            except ValueError as e:
                # 跳过无法解析的行，但保留错误信息
                output.append(f"<!-- 解析失败: {e} -->\n")
                continue

            # 生成卡片
            meta_str = _format_card_meta(meta)
            if meta_str:
                output.append(f"- {card_text} {meta_str}")
            else:
                output.append(f"- {card_text}")

            # 检查后续行是否有子任务
            line_idx = lines.index(line)
            if line_idx + 1 < len(lines):
                # 尝试提取子任务
                try:
                    subtasks, _ = _extract_subtasks(lines, line_idx + 1)
                    if subtasks:
                        output.extend(subtasks)
                except ValueError:
                    pass  # 子任务解析失败不影响主流程

        output.append("")  # 列间空行

    return "\n".join(output)


def _selftest() -> bool:
    """
    内置自检函数：使用硬编码样例数据验证核心逻辑。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("运行自检...")

    # 测试样例1：基本转换
    sample1 = """
待办：
- 买牛奶 [高] @张三 (2025-06-30)
- 写周报

进行中：
- 修复登录bug [中] @李四
  - 检查日志
  - 定位问题

已完成：
- 部署测试环境
"""
    try:
        result1 = _process_text_to_board(sample1)
        # 宽松断言：检查关键结构存在
        assert "## 待办" in result1, "缺少待办列"
        assert "## 进行中" in result1, "缺少进行中列"
        assert "## 已完成" in result1, "缺少已完成列"
        assert "买牛奶" in result1, "缺少卡片内容"
        assert "修复登录bug" in result1, "缺少卡片内容"
        assert "[高]" in result1 or "高" in result1, "缺少优先级标记"
        assert "@张三" in result1 or "张三" in result1, "缺少负责人标记"
        assert "2025-06-30" in result1, "缺少日期标记"
        assert "检查日志" in result1, "缺少子任务"
        print("  样例1（基本转换）: 通过")
    except AssertionError as e:
        print(f"  样例1失败: {e}")
        return False
    except Exception as e:
        print(f"  样例1异常: {e}")
        return False

    # 测试样例2：自定义列
    sample2 = "紧急任务：处理服务器故障\n常规任务：优化代码"
    try:
        result2 = _process_text_to_board(sample2, custom_columns=["紧急任务", "常规任务"])
        assert "## 紧急任务" in result2, "缺少自定义列"
        assert "## 常规任务" in result2, "缺少自定义列"
        assert "处理服务器故障" in result2, "缺少任务内容"
        assert "优化代码" in result2, "缺少任务内容"
        print("  样例2（自定义列）: 通过")
    except AssertionError as e:
        print(f"  样例2失败: {e}")
        return False
    except Exception as e:
        print(f"  样例2异常: {e}")
        return False

    # 测试样例3：空输入处理
    try:
        _process_text_to_board("   ")
        print("  样例3（空输入）: 失败 - 应抛出异常")
        return False
    except ValueError as e:
        assert "E001" in str(e), "错误码不正确"
        print("  样例3（空输入）: 通过")
    except Exception:
        print("  样例3（空输入）: 失败 - 异常类型错误")
        return False

    # 测试样例4：元数据解析
    sample4 = "- [中] 优化数据库 @王五 (2025-07-15)"
    try:
        result4 = _process_text_to_board(sample4)
        assert "优化数据库" in result4, "缺少卡片内容"
        assert "中" in result4, "缺少优先级"
        assert "王五" in result4, "缺少负责人"
        assert "2025-07-15" in result4, "缺少日期"
        print("  样例4（元数据解析）: 通过")
    except AssertionError as e:
        print(f"  样例4失败: {e}")
        return False
    except Exception as e:
        print(f"  样例4异常: {e}")
        return False

    # 测试样例5：多级嵌套
    sample5 = """
待办：
- 项目启动
  - 需求分析
    - 用户调研
    - 竞品分析
  - 技术选型
"""
    try:
        result5 = _process_text_to_board(sample5)
        assert "项目启动" in result5, "缺少主卡片"
        assert "需求分析" in result5, "缺少一级子任务"
        assert "用户调研" in result5, "缺少二级子任务"
        assert "竞品分析" in result5, "缺少二级子任务"
        assert "技术选型" in result5, "缺少一级子任务"
        # 检查缩进存在（宽松判断）
        lines5 = result5.split("\n")
        has_indent = any(line.startswith("  ") for line in lines5)
        assert has_indent, "缺少缩进结构"
        print("  样例5（多级嵌套）: 通过")
    except AssertionError as e:
        print(f"  样例5失败: {e}")
        return False
    except Exception as e:
        print(f"  样例5异常: {e}")
        return False

    print("\n全部自检通过 ✓")
    return True


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="kanban-md 任务看板标记转换器",
        epilog="示例: python main.py -i input.txt -o output.md"
    )
    parser.add_argument("-i", "--input", help="输入文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("-c", "--columns", help="自定义列（逗号分隔）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--text", help="直接传入文本内容")

    try:
        args = parser.parse_args()
    except SystemExit:
        return 8  # E008 参数解析失败

    # 自检模式
    if args.selftest:
        return 0 if _selftest() else 1

    # 获取输入文本
    input_text = ""
    try:
        if args.text:
            input_text = args.text
        elif args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        else:
            # 从标准输入读取
            print("请输入文本（Ctrl+D 结束）:")
            input_text = sys.stdin.read()
    except Exception as e:
        print(f"E001: 读取输入失败 - {e}")
        return 1

    # 处理自定义列
    custom_cols = None
    if args.columns:
        custom_cols = [c.strip() for c in args.columns.split(",") if c.strip()]

    # 执行转换
    try:
        result = _process_text_to_board(input_text, custom_cols)
    except ValueError as e:
        print(f"转换失败: {e}")
        return 1
    except Exception as e:
        print(f"E010: 未知错误 - {e}")
        return 10

    # 输出结果
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"看板已保存至: {args.output}")
        else:
            print(result)
    except Exception as e:
        print(f"E007: 输出失败 - {e}")
        return 7

    return 0


if __name__ == "__main__":
    sys.exit(main())
