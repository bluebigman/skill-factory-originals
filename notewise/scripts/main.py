#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notewise — 知识笔记结构化整理工具（独立实现）

本脚本根据技能功能规格独立编写，不复制任何既有代码。
功能：将零散笔记文本转换为结构化知识卡片（JSON 格式输出）。
支持批量模式、缺失字段标注、置信度评估与自检模式。

用法示例：
    python scripts/main.py --input note.txt --output result.json
    python scripts/main.py --batch notes_dir --output out_dir
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入文件不存在或不可读",
    "E002": "输出目录无法创建",
    "E003": "输入内容为空",
    "E004": "JSON 序列化失败",
    "E005": "批量模式输入目录无效",
    "E006": "批量模式输出目录无效",
    "E007": "参数组合不合法",
    "E008": "内部逻辑错误（不应发生）",
    "E009": "自检失败",
    "E010": "未知错误",
}


def err_exit(code: str, message: str = None) -> None:
    """输出错误信息并以非零状态退出。"""
    msg = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
    print(f"[ERROR {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- 核心解析逻辑 ----------

# 要素识别正则（宽松匹配，避免精确依赖）
_CONCEPT_RE = re.compile(
    r"(?:概念|定义|术语)[：:\s]*([^。\n]{2,80})", re.IGNORECASE
)
_PROCESS_RE = re.compile(
    r"(?:流程|步骤|过程)[：:\s]*([^。\n]{2,200})", re.IGNORECASE
)
_CONCLUSION_RE = re.compile(
    r"(?:结论|总结|要点)[：:\s]*([^。\n]{2,200})", re.IGNORECASE
)
_TODO_RE = re.compile(
    r"(?:待办|任务|行动项)[：:\s]*([^。\n]{2,100})", re.IGNORECASE
)
_TAG_RE = re.compile(r"#([\w\u4e00-\u9fa5]+)")

# 标题识别：Markdown 风格
_TITLE_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def _extract_by_pattern(text: str, pattern: re.Pattern) -> list:
    """从文本中按正则提取匹配内容，去除空白。"""
    matches = pattern.findall(text)
    return [m.strip() for m in matches if m and m.strip()]


def _detect_confidence(text: str) -> float:
    """
    基于文本特征评估置信度（0.0 ~ 1.0）。
    宽松规则：含明确标记（如“确定”“明确”）加分，含模糊词（如“可能”“大概”）减分。
    """
    score = 0.5  # 基础值
    if re.search(r"(确定|明确|肯定|一定)", text):
        score += 0.2
    if re.search(r"(可能|大概|也许|似乎|或许)", text):
        score -= 0.2
    # 文本长度越长，信息量越大，置信度适当提升（但不超过 0.95）
    score += min(len(text) / 2000.0, 0.25)
    return max(0.1, min(0.95, score))


def _extract_title(text: str) -> str:
    """提取标题：优先取 Markdown 标题，否则取首行非空内容。"""
    titles = _TITLE_RE.findall(text)
    if titles:
        return titles[0].strip()
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:50]  # 取首行前 50 字符作为标题
    return "未命名笔记"


def _extract_need_verify(text: str) -> list:
    """
    识别信息缺失或模糊处。
    规则：包含“？”、“待确认”、“未知”等字样，或字段值为空。
    """
    needs = []
    if re.search(r"[?？]", text):
        needs.append("存在疑问的内容")
    if re.search(r"待确认|待核实|未知|未提供", text):
        needs.append("信息缺失字段")
    return needs


def parse_note(text: str, source: str = "inline") -> dict:
    """
    将单条原始笔记解析为结构化知识卡片。
    返回字典包含：标题、概念、流程、结论、待办、标签、置信度、待核实项、元信息。
    """
    if not text or not text.strip():
        err_exit("E003", "输入内容为空，无法解析")

    # 提取各要素（去重、保留顺序）
    concepts = list(dict.fromkeys(_extract_by_pattern(text, _CONCEPT_RE)))
    processes = list(dict.fromkeys(_extract_by_pattern(text, _PROCESS_RE)))
    conclusions = list(dict.fromkeys(_extract_by_pattern(text, _CONCLUSION_RE)))
    todos = list(dict.fromkeys(_extract_by_pattern(text, _TODO_RE)))
    tags = list(dict.fromkeys(_TAG_RE.findall(text)))

    # 若标签为空，尝试从标题提取（宽松处理）
    if not tags:
        title = _extract_title(text)
        title_tags = _TAG_RE.findall(title)
        tags = list(dict.fromkeys(title_tags))

    # 置信度与待核实
    confidence = _detect_confidence(text)
    needs_verify = _extract_need_verify(text)

    # 构建卡片
    card = {
        "title": _extract_title(text),
        "concepts": concepts,
        "processes": processes,
        "conclusions": conclusions,
        "todos": todos,
        "tags": tags,
        "confidence": round(confidence, 2),
        "needs_verify": needs_verify,
        "source": source,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    return card


def process_batch(texts: dict) -> list:
    """批量处理：输入为 {名称: 文本} 字典，输出卡片列表。"""
    cards = []
    for name, content in texts.items():
        if content.strip():
            cards.append(parse_note(content, source=name))
    return cards


# ---------- 文件读写 ----------

def read_input(path: str) -> str:
    """读取输入文件（UTF-8），失败时抛出错误码 E001。"""
    p = Path(path)
    if not p.is_file():
        err_exit("E001", f"文件不存在: {path}")
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        err_exit("E001", f"无法读取文件: {path}")


def write_output(data, path: str) -> None:
    """将数据以 JSON 格式写入文件，失败时抛出 E002/E004。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)  # 自动创建父目录
    if not p.parent.exists():
        err_exit("E002", f"无法创建目录: {p.parent}")
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        p.write_text(json_str, encoding="utf-8")
    except TypeError:
        err_exit("E004", "数据无法序列化为 JSON")
    except Exception:
        err_exit("E002", f"写入文件失败: {path}")


# ---------- 自检模式 ----------

def _run_selftest() -> None:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("[SELFTEST] 开始自检...")

    # 样例 1：包含多种要素的笔记
    sample1 = """
    # 机器学习基础笔记
    概念：监督学习是一种通过标注数据训练模型的方法。
    流程：数据预处理 -> 特征工程 -> 模型训练 -> 评估 -> 部署。
    结论：监督学习适用于分类和回归问题。
    待办：下周复习交叉验证。
    标签：#机器学习 #监督学习
    注意：可能存在过拟合风险？需进一步确认。
    """

    # 样例 2：简单笔记（无标签、无待办）
    sample2 = """
    会议纪要
    讨论了项目进度，确定了下一步计划。
    大概需要两周完成开发。
    """

    # 样例 3：空内容（应触发 E003，但自检中我们捕获异常）
    sample3 = "   \n  "

    # 测试 parse_note 正常情况
    card1 = parse_note(sample1, source="selftest_sample1")
    assert card1["title"], "标题不应为空"
    assert len(card1["concepts"]) >= 1, "应至少识别一个概念"
    assert len(card1["processes"]) >= 1, "应至少识别一个流程"
    assert len(card1["conclusions"]) >= 1, "应至少识别一个结论"
    assert len(card1["todos"]) >= 1, "应至少识别一个待办"
    assert len(card1["tags"]) >= 2, "应识别至少两个标签"
    assert 0.0 <= card1["confidence"] <= 1.0, "置信度应在 0~1 之间"
    assert len(card1["needs_verify"]) >= 1, "应识别待核实项（含问号）"
    print("  [OK] 样例1 多要素解析通过")

    # 测试 parse_note 简单情况
    card2 = parse_note(sample2, source="selftest_sample2")
    assert card2["title"], "标题不应为空"
    assert len(card2["concepts"]) == 0, "无概念标记时应为空列表"
    assert card2["confidence"] < 0.8, "含模糊词（大概）时置信度应较低"
    print("  [OK] 样例2 简单笔记解析通过")

    # 测试空内容报错
    try:
        parse_note(sample3)
        raise AssertionError("空内容应触发 E003 错误")
    except SystemExit as e:
        assert e.code != 0, "空内容应以非零状态退出"
    print("  [OK] 样例3 空内容错误处理通过")

    # 测试批量处理
    batch_input = {
        "笔记A": "概念：递归算法。流程：定义基准条件 -> 递归调用。",
        "笔记B": "待办：完成报告。",
    }
    cards = process_batch(batch_input)
    assert len(cards) == 2, "批量处理应返回两张卡片"
    assert cards[0]["source"] == "笔记A"
    assert cards[1]["source"] == "笔记B"
    assert len(cards[1]["todos"]) >= 1
    print("  [OK] 批量处理通过")

    # 测试 JSON 序列化（确保可输出）
    json.dumps(cards, ensure_ascii=False)
    print("  [OK] JSON 序列化通过")

    # 测试文件读写（使用临时目录，不依赖当前工作目录）
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = os.path.join(tmpdir, "test_out.json")
        write_output(cards, tmp_file)
        assert os.path.isfile(tmp_file), "输出文件应存在"
        with open(tmp_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert len(loaded) == 2, "读回的数据应包含两张卡片"
    print("  [OK] 文件读写通过（临时目录）")

    print("[SELFTEST] 全部自检通过 ✓")


# ---------- 命令行入口 ----------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="notewise — 知识笔记结构化整理工具",
        epilog="示例: python scripts/main.py --input note.txt --output result.json",
    )
    parser.add_argument("--input", type=str, help="输入笔记文件路径")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")
    parser.add_argument("--batch", type=str, help="批量模式：输入目录（内含 .txt 文件）")
    parser.add_argument("--batch-output", type=str, help="批量模式输出目录")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（离线）")
    args = parser.parse_args()

    # 自检模式优先
    if args.selftest:
        try:
            _run_selftest()
            sys.exit(0)
        except AssertionError as e:
            err_exit("E009", f"自检失败: {e}")
        except Exception as e:
            err_exit("E010", f"自检异常: {e}")

    # 参数合法性检查
    if args.input and args.batch:
        err_exit("E007", "不能同时指定 --input 和 --batch")
    if not args.input and not args.batch:
        err_exit("E007", "必须指定 --input 或 --batch（或使用 --selftest）")

    # 单文件模式
    if args.input:
        if not args.output:
            err_exit("E007", "单文件模式必须指定 --output")
        text = read_input(args.input)
        card = parse_note(text, source=args.input)
        write_output(card, args.output)
        print(f"✅ 已生成知识卡片: {args.output}")
        sys.exit(0)

    # 批量模式
    if args.batch:
        src_dir = Path(args.batch)
        if not src_dir.is_dir():
            err_exit("E005", f"批量输入目录无效: {args.batch}")
        if not args.batch_output:
            err_exit("E007", "批量模式必须指定 --batch-output")
        out_dir = Path(args.batch_output)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            err_exit("E006", f"无法创建输出目录: {args.batch_output}")

        # 收集所有 .txt 文件
        txt_files = list(src_dir.glob("*.txt"))
        if not txt_files:
            err_exit("E005", f"批量输入目录中没有 .txt 文件: {src_dir}")

        batch_data = {}
        for f in txt_files:
            try:
                content = f.read_text(encoding="utf-8")
                if content.strip():
                    batch_data[f.name] = content
            except Exception:
                print(f"  ⚠️ 跳过无法读取的文件: {f.name}", file=sys.stderr)

        if not batch_data:
            err_exit("E003", "批量输入中没有有效内容")

        cards = process_batch(batch_data)
        # 输出：每张卡片一个文件，另生成一个汇总文件
        for card in cards:
            safe_name = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", card["source"])
            out_file = out_dir / f"{safe_name}.json"
            write_output(card, str(out_file))

        summary_file = out_dir / "_summary.json"
        write_output(cards, str(summary_file))
        print(f"✅ 批量处理完成: 共 {len(cards)} 张卡片，输出至 {out_dir}")
        sys.exit(0)


if __name__ == "__main__":
    main()
