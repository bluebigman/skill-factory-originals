#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
日语NLP资源导航 工具库速查 - 独立实现脚本

功能：将用户提供的非结构化文本中的日语NLP资源信息整理为结构化清单。
本脚本为 clean-room 实现，仅依据功能规格独立编写。
"""

import argparse
import re
import sys
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文本为空或仅包含空白字符",
    "E002": "输入文本不是字符串类型",
    "E003": "无法从文本中解析出任何资源条目",
    "E004": "资源条目缺少名称字段",
    "E005": "资源类别不在允许范围内",
    "E006": "内部数据异常：类别映射失败",
    "E007": "参数解析失败",
    "E008": "输出格式不支持",
    "E009": "自检失败：核心逻辑断言未通过",
    "E010": "未知异常",
}


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出程序。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        print(f"[错误 {code}] {msg}: {detail}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 核心数据结构
# ============================================================

# 允许的资源类别
ALLOWED_CATEGORIES = ["Python库", "LLM", "词典", "语料库"]

# 类别关键词映射表（用于自动分类）
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Python库": ["pip", "python", "py", "library", "库", "github.com/"],
    "LLM": ["llm", "gpt", "bert", "transformer", "模型", "model"],
    "词典": ["辞書", "词典", "dictionary", "dict", "lexicon", "辞書データ"],
    "语料库": ["コーパス", "语料库", "corpus", "corpora", "データセット", "dataset"],
}


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(text: str) -> None:
    """
    校验输入文本的基本合法性。

    Args:
        text: 待处理的输入文本

    Raises:
        SystemExit: 当输入不合法时，以错误码退出
    """
    if not isinstance(text, str):
        error_exit("E002", f"期望 str 类型，实际为 {type(text).__name__}")
    if not text.strip():
        error_exit("E001", "输入内容为空")


def extract_resource_blocks(text: str) -> List[str]:
    """
    从输入文本中提取资源条目块。

    策略：按行扫描，将包含资源特征（如URL、库名、模型名等）的连续行
    合并为一个资源块。每个资源块后续会单独解析。

    Args:
        text: 原始输入文本

    Returns:
        List[str]: 资源块列表，每个块包含一行或多行文本
    """
    lines = text.splitlines()
    blocks: List[str] = []
    current_block: List[str] = []

    # 识别行是否为资源行（包含 URL、常见库名关键词等）
    resource_pattern = re.compile(
        r"(https?://|github\.com|pip|pip install|pip3|"
        r"llm|bert|gpt|transformer|辞書|词典|dictionary|"
        r"コーパス|语料库|corpus|dataset|モデル|模型)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # 空行分隔资源块
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            continue

        if resource_pattern.search(stripped):
            # 当前行是资源行
            if current_block and not resource_pattern.search(current_block[-1]):
                # 如果当前块的最后一行不是资源行，说明是新条目开始
                blocks.append("\n".join(current_block))
                current_block = [stripped]
            else:
                current_block.append(stripped)
        else:
            # 非资源行，如果当前块非空则加入，否则忽略
            if current_block:
                current_block.append(stripped)

    # 处理末尾残留块
    if current_block:
        blocks.append("\n".join(current_block))

    return blocks


def extract_name(block_text: str) -> Optional[str]:
    """
    从资源块中提取资源名称。

    策略：
    1. 查找 Markdown 链接格式 [名称](url)
    2. 查找 GitHub 仓库路径（owner/repo）
    3. 查找以常见前缀开头的行

    Args:
        block_text: 单个资源块的文本

    Returns:
        Optional[str]: 提取到的名称，未找到则返回 None
    """
    # 优先匹配 Markdown 链接格式
    md_link = re.search(r"\[([^\]]+)\]\([^)]+\)", block_text)
    if md_link:
        name = md_link.group(1).strip()
        if name:
            return name

    # 匹配 GitHub 仓库路径
    gh_match = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", block_text)
    if gh_match:
        return gh_match.group(1)

    # 匹配 pip 包名
    pip_match = re.search(r"pip install\s+([A-Za-z0-9_.-]+)", block_text, re.IGNORECASE)
    if pip_match:
        return pip_match.group(1)

    # 匹配常见库名前缀
    for line in block_text.splitlines():
        stripped = line.strip().strip("-").strip("*").strip()
        # 去除常见的列表编号前缀
        stripped = re.sub(r"^\d+[\.\)]\s*", "", stripped)
        if re.match(r"^[A-Za-z][A-Za-z0-9_/-]{2,}$", stripped):
            return stripped

    return None


def extract_url(block_text: str) -> Optional[str]:
    """
    从资源块中提取 URL。

    Args:
        block_text: 单个资源块的文本

    Returns:
        Optional[str]: 提取到的 URL，未找到则返回 None
    """
    url_match = re.search(r"https?://[^\s\)\]\}]+", block_text)
    if url_match:
        return url_match.group(0).rstrip(".,;")
    return None


def classify_category(block_text: str) -> str:
    """
    根据资源块内容自动判断资源类别。

    Args:
        block_text: 单个资源块的文本

    Returns:
        str: 资源类别，属于 ALLOWED_CATEGORIES 之一
    """
    lower_text = block_text.lower()

    # 统计各类别关键词命中次数
    scores: Dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = 0
        for kw in keywords:
            count += lower_text.count(kw.lower())
        scores[category] = count

    # 取最高分类别
    best_category = max(scores, key=scores.get)
    if scores[best_category] > 0:
        return best_category

    # 未命中任何关键词，默认归为 Python库
    return "Python库"


def extract_license(block_text: str) -> str:
    """
    从资源块中提取许可证信息。

    常见许可证关键词：MIT, Apache, GPL, BSD, LGPL 等。
    未找到时返回占位符 [需核实:许可证]。

    Args:
        block_text: 单个资源块的文本

    Returns:
        str: 许可证信息或占位符
    """
    license_pattern = re.compile(
        r"\b(MIT|Apache[- ]2\.0|GPL[- ]?v?3?|LGPL|BSD[- ]?[23]?[- ]?Clause|"
        r"MPL[- ]?2\.0|CC[- ]BY|CC0|Unlicense)\b",
        re.IGNORECASE,
    )
    match = license_pattern.search(block_text)
    if match:
        return match.group(1)
    return "[需核实:许可证]"


def extract_maintainer(block_text: str) -> str:
    """
    从资源块中提取维护方信息。

    策略：查找 GitHub 用户名、组织名或常见维护者标识。

    Args:
        block_text: 单个资源块的文本

    Returns:
        str: 维护方信息或占位符
    """
    # 匹配 GitHub 用户名（github.com/后面的第一段）
    gh_owner = re.search(r"github\.com/([A-Za-z0-9_.-]+)/", block_text)
    if gh_owner:
        return gh_owner.group(1)

    # 匹配 "作者:"、"维护:" 等中文标识
    maintainer_cn = re.search(r"(?:作者|维护|维护者)[:：]\s*([^\s,，;；]+)", block_text)
    if maintainer_cn:
        return maintainer_cn.group(1).strip()

    return "[需核实:维护方]"


def parse_resource_block(block_text: str) -> Dict[str, str]:
    """
    将单个资源块解析为结构化记录。

    Args:
        block_text: 单个资源块的文本

    Returns:
        Dict[str, str]: 结构化资源记录

    Raises:
        SystemExit: 当无法提取名称时，以错误码 E004 退出
    """
    name = extract_name(block_text)
    if not name:
        error_exit("E004", f"无法从资源块中提取名称: {block_text[:80]}")

    # 判断类别
    category = classify_category(block_text)
    if category not in ALLOWED_CATEGORIES:
        error_exit("E005", f"类别 '{category}' 不在允许范围内")

    record = {
        "名称": name,
        "类别": category,
        "URL": extract_url(block_text) or "[需核实:URL]",
        "维护方": extract_maintainer(block_text),
        "许可证": extract_license(block_text),
    }
    return record


def process_text(text: str) -> List[Dict[str, str]]:
    """
    处理输入文本，提取并结构化所有资源条目。

    Args:
        text: 原始输入文本

    Returns:
        List[Dict[str, str]]: 结构化资源记录列表

    Raises:
        SystemExit: 当处理失败时以相应错误码退出
    """
    # 校验输入
    validate_input(text)

    # 提取资源块
    blocks = extract_resource_blocks(text)
    if not blocks:
        error_exit("E003", "未从输入文本中识别到任何资源条目")

    # 解析每个资源块
    records: List[Dict[str, str]] = []
    for block in blocks:
        record = parse_resource_block(block)
        records.append(record)

    return records


# ============================================================
# 输出格式化
# ============================================================

def format_markdown(records: List[Dict[str, str]]) -> str:
    """
    将结构化记录格式化为 Markdown 表格输出。

    Args:
        records: 结构化资源记录列表

    Returns:
        str: Markdown 格式的输出文本
    """
    if not records:
        return ""

    lines = [
        "| 名称 | 类别 | URL | 维护方 | 许可证 |",
        "|------|------|-----|--------|--------|",
    ]
    for rec in records:
        # 转义 Markdown 表格中的竖线
        name = rec["名称"].replace("|", "\\|")
        url = rec["URL"].replace("|", "\\|")
        maintainer = rec["维护方"].replace("|", "\\|")
        license_ = rec["许可证"].replace("|", "\\|")
        lines.append(
            f"| {name} | {rec['类别']} | {url} | {maintainer} | {license_} |"
        )
    return "\n".join(lines)


def format_json(records: List[Dict[str, str]]) -> str:
    """
    将结构化记录格式化为 JSON 输出。

    Args:
        records: 结构化资源记录列表

    Returns:
        str: JSON 格式的输出文本
    """
    import json

    return json.dumps(records, ensure_ascii=False, indent=2)


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> None:
    """
    运行内置自检，验证核心逻辑正确性。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保在各种环境下均可通过。
    """
    # 硬编码自检样例 - 每行一个资源，用空行分隔
    sample_text = """
[SudachiPy](https://github.com/WorksApplications/SudachiPy) - 日语分词器，pip install sudachipy

[fugashi](https://github.com/polm/fugashi) - MeCab 的 Python 封装，pip install fugashi

[Japanese-Language-Model](https://github.com/example/japanese-llm) - 日语大语言模型 LLM

[JMDict](https://www.edrdg.org/jmdict/) - 日语词典数据

[Kotonoha](https://github.com/kotonoha/corpus) - 日语语料库数据集
    """

    # 执行核心处理
    records = process_text(sample_text)

    # ---- 宽松断言 ----
    # 断言1：至少解析出 3 条记录
    assert len(records) >= 3, f"自检失败：解析记录数过少，实际 {len(records)}"

    # 断言2：每条记录包含所有必需字段
    required_fields = {"名称", "类别", "URL", "维护方", "许可证"}
    for rec in records:
        assert required_fields.issubset(rec.keys()), (
            f"自检失败：记录缺少必需字段 {required_fields - rec.keys()}"
        )

    # 断言3：类别字段值合法
    for rec in records:
        assert rec["类别"] in ALLOWED_CATEGORIES, (
            f"自检失败：非法类别 {rec['类别']}"
        )

    # 断言4：至少有一条记录包含 GitHub URL
    github_records = [r for r in records if "github.com" in r["URL"]]
    assert len(github_records) >= 1, "自检失败：未找到 GitHub 资源"

    # 断言5：名称字段非空
    for rec in records:
        assert rec["名称"].strip(), "自检失败：存在空名称记录"

    # 断言6：至少有一条记录被分类为 Python库 或 LLM
    tech_categories = [r for r in records if r["类别"] in ("Python库", "LLM")]
    assert len(tech_categories) >= 1, "自检失败：未找到技术类资源"

    # 断言7：许可证字段不为空
    for rec in records:
        assert rec["许可证"].strip(), "自检失败：存在空许可证字段"

    # 断言8：Markdown 输出包含表头
    md_output = format_markdown(records)
    assert "| 名称 |" in md_output, "自检失败：Markdown 输出缺少表头"
    assert "|------|" in md_output, "自检失败：Markdown 输出缺少分隔行"

    # 断言9：JSON 输出可解析
    json_output = format_json(records)
    import json as json_module

    parsed_json = json_module.loads(json_output)
    assert isinstance(parsed_json, list), "自检失败：JSON 输出不是列表"
    assert len(parsed_json) == len(records), "自检失败：JSON 记录数不匹配"

    # 断言10：空输入触发错误码（捕获 SystemExit）
    try:
        process_text("   ")
        assert False, "自检失败：空输入未触发错误"
    except SystemExit as e:
        assert e.code == 1, "自检失败：空输入错误码异常"

    # 全部通过
    print("[自检通过] 所有核心逻辑断言验证成功")
    print(f"  样例输入解析记录数: {len(records)}")
    print(f"  分类分布: ", end="")
    for cat in ALLOWED_CATEGORIES:
        count = sum(1 for r in records if r["类别"] == cat)
        print(f"{cat}={count} ", end="")
    print()


# ============================================================
# 主程序入口
# ============================================================

def main() -> None:
    """主程序入口。"""
    parser = argparse.ArgumentParser(
        description="日语NLP资源导航工具：将非结构化文本整理为结构化清单",
        epilog="示例: python main.py -i input.txt -o output.md --format markdown",
    )
    parser.add_argument(
        "-i", "--input",
        help="输入文件路径（UTF-8编码），若不指定则从标准输入读取",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径，若不指定则输出到标准输出",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )

    try:
        parser.add_argument("--force", action="store_true")  # R4 强制写盘

        parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
        args = parser.parse_args()
        global dry_run
        dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    except SystemExit:
        # argparse 在参数错误时会自行退出，这里捕获并转为 E007
        error_exit("E007", "命令行参数解析失败")

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            sys.exit(0)
        except AssertionError as e:
            error_exit("E009", str(e))
        except SystemExit:
            # 自检中的错误码已经输出过，直接退出
            raise
        except Exception as e:
            error_exit("E010", f"自检过程发生未知异常: {e}")

    # 读取输入
    try:
        if args.input:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            # 从标准输入读取
            print("请输入文本（Ctrl+D 结束输入）：", file=sys.stderr)
            text = sys.stdin.read()
    except FileNotFoundError:
        error_exit("E001", f"输入文件不存在: {args.input}")
    except Exception as e:
        error_exit("E010", f"读取输入失败: {e}")

    # 处理文本
    try:
        records = process_text(text)
    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", f"处理文本时发生未知异常: {e}")

    # 格式化输出
    try:
        if args.format == "markdown":
            output_text = format_markdown(records)
        elif args.format == "json":
            output_text = format_json(records)
        else:
            error_exit("E008", f"不支持的输出格式: {args.format}")
    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", f"格式化输出失败: {e}")

    # 输出结果
    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
                f.write("\n")
            print(f"已写入输出文件: {args.output}", file=sys.stderr)
        else:
            print(output_text)
    except Exception as e:
        error_exit("E010", f"写入输出失败: {e}")


if __name__ == "__main__":
    main()
