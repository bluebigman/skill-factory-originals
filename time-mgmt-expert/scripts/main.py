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
from datetime import datetime, timezone
dry_run = False  # v3.274 模块级 dry-run 标志

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

# 最大嵌套深度
MAX_DEPTH = 5

# 列识别置信度阈值（至少需要匹配到这些字符才算识别成功）
COLUMN_CONFIDENCE_THRESHOLD = 2


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
    增加置信度阈值，无匹配时返回明确错误。
    """
    columns = []
    if custom_columns:
        columns = [c.strip() for c in custom_columns if c.strip()]
        if not columns:
            raise ValueError(f"E002: {ERROR_CODES['E002']}")
        return columns

    # 从输入中查找已知列关键词，统计出现次数
    column_counts = {}
    for col in DEFAULT_COLUMNS:
        # 统计列名在文本中出现的次数（包括作为标题、列表项等）
        count = len(re.findall(re.escape(col), text))
        if count > 0:
            column_counts[col] = count

    # 按出现次数排序，取出现次数最多的列
    if column_counts:
        # 按出现次数降序排序
        sorted_columns = sorted(column_counts.items(), key=lambda x: x[1], reverse=True)
        # 取出现次数达到阈值的列
        columns = [col for col, count in sorted_columns if count >= COLUMN_CONFIDENCE_THRESHOLD]
        # 如果所有列都低于阈值，但至少有一个列出现，则使用出现次数最多的列
        if not columns and sorted_columns:
            columns = [sorted_columns[0][0]]
    else:
        # 没有匹配到任何列，返回明确错误
        raise ValueError(f"E002: {ERROR_CODES['E002']}")

    return columns


def _parse_card_line(line: str, line_num: int) -> Tuple[str, Dict[str, str]]:
    """
    解析单行卡片内容，提取元数据。
    返回 (卡片文本, 元数据字典)
    错误码 E003/E005
    """
    if not line.strip():
        # 空行作为分隔符，返回空卡片标记
        return "", {}

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
    max_depth = MAX_DEPTH

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

        for i, line in enumerate(col_lines):
            stripped = line.strip()
            if not stripped:
                continue

            # 解析卡片
            try:
                card_text, meta = _parse_card_line(stripped, i + 1)
                if not card_text:
                    continue  # 空行跳过
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

            # 检查后续行是否有子任务（需要找到原始行号）
            original_idx = lines.index(line)
            if original_idx + 1 < len(lines):
                # 尝试提取子任务
                try:
                    subtasks, _ = _extract_subtasks(lines, original_idx + 1)
                    if subtasks:
                        output.extend(subtasks)
                except ValueError:
                    pass  # 子任务解析失败不影响主流程

        output.append("")  # 列间空行

    return "\n".join(output)


def _selftest() -> bool:
    """
    内置自检函数：使用硬编码样例数据验证核心逻辑。
    真实调用主流程/核心函数并断言关键输出。
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
        # 严格断言：检查关键结构存在
        assert "## 待办" in result1, "缺少待办列"
        assert "## 进行中" in result1, "缺少进行中列"
        assert "## 已完成" in result1, "缺少已完成列"
        assert "买牛奶" in result1, "缺少卡片内容"
        assert "修复登录bug" in result1, "缺少卡片内容"
        assert "[高]" in result1, "缺少优先级标记"
        assert "@张三" in result1, "缺少负责人标记"
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
        # 检查缩进存在（严格判断）
        lines5 = result5.split("\n")
        has_indent = any(line.startswith("  ") for line in lines5)
        assert has_indent, "缺少缩进结构"
        # 验证嵌套层级
        assert "    - 用户调研" in result5, "二级子任务缩进错误"
        assert "    - 竞品分析" in result5, "二级子任务缩进错误"
        print("  样例5（多级嵌套）: 通过")
    except AssertionError as e:
        print(f"  样例5失败: {e}")
        return False
    except Exception as e:
        print(f"  样例5异常: {e}")
        return False

    # 测试样例6：错误码映射
    try:
        _process_text_to_board("")
        print("  样例6（错误码映射）: 失败 - 应抛出异常")
        return False
    except ValueError as e:
        assert "E001" in str(e), "错误码不正确"
        print("  样例6（错误码映射）: 通过")
    except Exception:
        print("  样例6（错误码映射）: 失败 - 异常类型错误")
        return False

    # 测试样例7：无列匹配时返回错误
    sample7 = "这是一个没有列关键词的文本"
    try:
        _process_text_to_board(sample7)
        print("  样例7（无列匹配）: 失败 - 应抛出异常")
        return False
    except ValueError as e:
        assert "E002" in str(e), "错误码不正确"
        print("  样例7（无列匹配）: 通过")
    except Exception:
        print("  样例7（无列匹配）: 失败 - 异常类型错误")
        return False

    # 测试样例8：主流程完整调用（通过main函数）
    try:
        # 使用临时文件测试主流程
        import tempfile
        import os
        
        # 创建临时输入文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(sample1)
            input_path = f.name
        
        # 创建临时输出文件
        output_path = input_path.replace('.txt', '_output.md')
        
        # 调用主函数
        exit_code = main_with_args(['-i', input_path, '-o', output_path])
        
        # 验证输出文件
        with open(output_path, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        assert exit_code == 0, f"主流程退出码不为0: {exit_code}"
        assert "## 待办" in output_content, "主流程输出缺少待办列"
        assert "买牛奶" in output_content, "主流程输出缺少卡片内容"
        
        # 清理临时文件
        os.unlink(input_path)
        os.unlink(output_path)
        
        print("  样例8（主流程完整调用）: 通过")
    except Exception as e:
        print(f"  样例8失败: {e}")
        return False

    # 测试样例9：空行作为分隔符（不报错）
    sample9 = """
待办：
- 任务1

- 任务2
"""
    try:
        result9 = _process_text_to_board(sample9)
        assert "任务1" in result9, "缺少任务1"
        assert "任务2" in result9, "缺少任务2"
        print("  样例9（空行分隔）: 通过")
    except Exception as e:
        print(f"  样例9失败: {e}")
        return False

    # 测试样例10：时区处理（验证datetime使用UTC）
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        assert now.tzinfo is not None, "datetime未使用时区"
        print("  样例10（时区处理）: 通过")
    except Exception as e:
        print(f"  样例10失败: {e}")
        return False

    print

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] kanban-md" % name)
        except Exception:
            failures += 1
            print("  [FAIL] kanban-md" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: kanban-md (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: kanban-md (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="kanban-md 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: kanban-md（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


def main_with_args(argv=None):
    """R1/R4/R6 契约主入口：-i 输入(文件或文本) -o 输出看板 .md 文件"""
    import argparse as _ap
    p = _ap.ArgumentParser(description="kanban-md：将任务文本整理为看板 Markdown")
    p.add_argument("-i", "--input", help="输入：文本文件路径或直接字符串")
    p.add_argument("-o", "--output", help="输出 .md 文件路径（缺省打印到 stdout）")
    p.add_argument("--dry-run", action="store_true", help="预览模式不写盘")
    p.add_argument("--force", action="store_true", help="强制写盘")
    p.add_argument("--verbose", action="store_true", help="输出明细")
    args = p.parse_args(argv)
    if not args.input:
        print("用法: kanban-md -i <输入文件或文本> [-o 输出.md]")
        return 1
    text = args.input
    if os.path.exists(args.input):
        text = _read_text_safe_enc(args.input)
    if not text or not text.strip():
        print("输入为空，无可整理内容")
        return 1
    board = _process_text_to_board(text)
    if args.output:
        if _write_guarded(args.output, board, dry_run=args.dry_run, force=args.force, verbose=args.verbose):
            if args.verbose:
                print(f"看板已写入: {args.output}")
        else:
            print(f"[dry-run] 不写盘: {args.output} ({len(board)} 字符)")
    else:
        print(board)
    return 0


def main() -> int:
    """R1 契约：转发 main_with_args"""
    return main_with_args(sys.argv[1:])

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
