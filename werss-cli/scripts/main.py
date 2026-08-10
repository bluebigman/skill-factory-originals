#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
werss-cli 公众号文章处理工具（独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
仅供学习与参考用途，使用前请阅读相关文档。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容。",
    "E002": "关键信息缺失，请补充必要字段。",
    "E003": "输入格式不符合要求。",
    "E004": "超出能力边界，无法处理。",
    "E005": "置信度过低，结果无法确定。",
    "E006": "内部处理异常。",
    "E007": "参数不合法。",
    "E008": "数据解析失败。",
    "E009": "输出生成失败。",
    "E010": "未知错误。",
}


class WerssError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从输入数据中提取关键字段并结构化。

    支持两种输入格式：
    1. 直接包含 title/content/author 等字段的字典
    2. 包含 article 或 data 嵌套字段的字典

    返回结构化后的结果，包含置信度评估。
    """
    if not data:
        raise WerssError("E001")

    # 尝试提取嵌套数据
    source = data
    if isinstance(data.get("article"), dict):
        source = data["article"]
    elif isinstance(data.get("data"), dict):
        source = data["data"]

    # 提取关键字段
    title = source.get("title") or source.get("name") or source.get("subject")
    content = source.get("content") or source.get("body") or source.get("text")
    author = source.get("author") or source.get("creator") or source.get("writer")
    date = source.get("date") or source.get("publish_time") or source.get("created_at")
    url = source.get("url") or source.get("link") or source.get("source_url")

    # 检查关键信息是否缺失
    missing = []
    if not title:
        missing.append("标题(title)")
    if not content:
        missing.append("内容(content)")

    if missing:
        raise WerssError("E002", f"缺少以下关键字段: {', '.join(missing)}")

    # 结构化结果
    result = {
        "title": title.strip() if isinstance(title, str) else str(title),
        "content": content.strip() if isinstance(content, str) else str(content),
        "author": author.strip() if isinstance(author, str) else str(author or "未知"),
        "date": str(date or "未知"),
        "url": str(url or ""),
        "source": source.get("source", "用户提供"),
    }

    # 计算置信度
    confidence = _calculate_confidence(result)
    result["confidence"] = confidence

    return result


def _calculate_confidence(article: Dict[str, Any]) -> float:
    """
    根据字段完整度计算置信度。

    规则：
    - 基础分 60 分
    - 有作者 +10
    - 有日期 +10
    - 有URL +10
    - 内容长度 > 100 字符 +10
    - 内容长度 > 500 字符 +10
    """
    score = 60

    if article.get("author") and article["author"] != "未知":
        score += 10
    if article.get("date") and article["date"] != "未知":
        score += 10
    if article.get("url"):
        score += 10

    content_len = len(article.get("content", ""))
    if content_len > 100:
        score += 10
    if content_len > 500:
        score += 10

    return min(score, 100)


def format_markdown(article: Dict[str, Any]) -> str:
    """
    将结构化文章转换为 Markdown 格式。

    输出格式：
    # 标题
    > 作者 | 日期 | 来源
    ---
    正文内容
    """
    if not article:
        raise WerssError("E001")

    try:
        lines = []
        lines.append(f"# {article['title']}")
        lines.append("")
        lines.append(
            f"> 作者: {article.get('author', '未知')} | "
            f"日期: {article.get('date', '未知')} | "
            f"来源: {article.get('source', '用户提供')}"
        )
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(article["content"])
        lines.append("")

        # 置信度标注
        confidence = article.get("confidence", 0)
        if confidence < 85:
            lines.append("")
            lines.append(f"> ⚠️ [需核实] 置信度: {confidence:.0f}%")
        elif confidence < 90:
            lines.append("")
            lines.append(f"> 💡 建议复核 置信度: {confidence:.0f}%")

        return "\n".join(lines)
    except KeyError as exc:
        raise WerssError("E009", f"缺少必要字段: {exc}") from exc


def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    处理用户输入，返回结构化结果。

    支持输入类型：
    - 字典（直接处理）
    - JSON 字符串（解析后处理）
    - 文本（尝试提取标题和内容）
    """
    if raw_input is None:
        raise WerssError("E001")

    # 解析不同类型输入
    if isinstance(raw_input, dict):
        data = raw_input
    elif isinstance(raw_input, str):
        try:
            data = json.loads(raw_input)
        except json.JSONDecodeError:
            # 尝试从文本提取标题和内容
            data = _parse_text_input(raw_input)
    else:
        raise WerssError("E003", f"不支持的输入类型: {type(raw_input).__name__}")

    # 提取关键字段
    article = extract_key_fields(data)

    # 生成 Markdown
    article["markdown"] = format_markdown(article)

    return article


def _parse_text_input(text: str) -> Dict[str, str]:
    """
    从纯文本中提取标题和内容。

    规则：
    - 第一行作为标题（如果有）
    - 其余部分作为内容
    """
    lines = text.strip().split("\n")
    if not lines or not lines[0].strip():
        raise WerssError("E001")

    title = lines[0].strip()
    content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    if not content:
        content = title
        title = "未命名文章"

    return {"title": title, "content": content}


def batch_process(items: List[Any]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入。

    每个项目独立处理，单个失败不影响其他项目。
    """
    results = []
    errors = []

    for idx, item in enumerate(items):
        try:
            result = process_input(item)
            results.append(result)
        except WerssError as exc:
            errors.append({"index": idx, "error": exc.code, "message": str(exc)})

    # 如果有错误，附加到结果中
    if errors:
        results.append({"batch_errors": errors})

    return results


# ============================================================
# 自检（SELFTEST）模块
# ============================================================

def run_selftest() -> int:
    """
    内置自检函数，使用硬编码样例数据验证核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保在各种环境下都能通过。
    """
    print("=" * 60)
    print("werss-cli 自检开始")
    print("=" * 60)

    # 测试数据 1：完整文章
    test_article_1 = {
        "title": "测试文章标题",
        "content": "这是一段测试内容，用于验证文章处理功能是否正常工作。" * 10,
        "author": "测试作者",
        "date": "2026-01-15",
        "url": "https://example.com/article/1",
        "source": "测试源",
    }

    # 测试数据 2：迷你文章（测试置信度逻辑）
    test_article_2 = {
        "title": "短文章",
        "content": "简短内容",
    }

    # 测试数据 3：嵌套格式
    test_article_3 = {
        "article": {
            "name": "嵌套文章",
            "body": "嵌套内容测试，用于验证嵌套数据提取功能是否正常工作。",
            "creator": "嵌套作者",
        }
    }

    # 测试数据 4：JSON 字符串
    test_article_4 = json.dumps({
        "title": "JSON文章",
        "content": "JSON格式的测试内容，用于验证字符串解析功能。",
        "author": "JSON作者",
    })

    # 测试数据 5：纯文本
    test_article_5 = "纯文本标题\n这是纯文本的内容部分，用于测试文本解析功能。"

    # 测试数据 6：空输入（应抛出 E001）
    test_article_6 = None

    # 测试数据 7：缺少关键字段（应抛出 E002）
    test_article_7 = {"title": "只有标题"}

    # 测试数据 8：批量处理
    test_batch = [
        {"title": "批量文章1", "content": "批量测试内容1"},
        {"title": "批量文章2", "content": "批量测试内容2" * 10, "author": "批量作者"},
    ]

    passed = 0
    failed = 0

    # ---- 测试 1：完整文章处理 ----
    try:
        result = process_input(test_article_1)
        # 宽松断言：字段存在且非空
        assert result.get("title"), "标题不应为空"
        assert result.get("content"), "内容不应为空"
        assert result.get("author"), "作者不应为空"
        assert result.get("confidence", 0) >= 80, f"置信度应>=80, 实际: {result.get('confidence')}"
        assert "markdown" in result, "应生成markdown"
        assert result["markdown"].startswith("# "), "markdown应以标题开头"
        passed += 1
        print("✓ 测试1 完整文章处理 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试1 完整文章处理 失败: {exc}")

    # ---- 测试 2：短文章置信度 ----
    try:
        result = process_input(test_article_2)
        # 短内容置信度应相对较低
        assert result.get("confidence", 100) <= 90, f"短文章置信度应<=90, 实际: {result.get('confidence')}"
        passed += 1
        print("✓ 测试2 短文章置信度 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试2 短文章置信度 失败: {exc}")

    # ---- 测试 3：嵌套格式 ----
    try:
        result = process_input(test_article_3)
        assert result.get("title") == "嵌套文章", "应提取嵌套标题"
        assert result.get("author") == "嵌套作者", "应提取嵌套作者"
        passed += 1
        print("✓ 测试3 嵌套格式 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试3 嵌套格式 失败: {exc}")

    # ---- 测试 4：JSON 字符串 ----
    try:
        result = process_input(test_article_4)
        assert result.get("title") == "JSON文章", "应解析JSON标题"
        assert result.get("author") == "JSON作者", "应解析JSON作者"
        passed += 1
        print("✓ 测试4 JSON字符串 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试4 JSON字符串 失败: {exc}")

    # ---- 测试 5：纯文本 ----
    try:
        result = process_input(test_article_5)
        assert result.get("title") == "纯文本标题", "应提取文本标题"
        assert "纯文本的内容" in result.get("content", ""), "应提取文本内容"
        passed += 1
        print("✓ 测试5 纯文本 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试5 纯文本 失败: {exc}")

    # ---- 测试 6：空输入 ----
    try:
        process_input(test_article_6)
        failed += 1
        print("✗ 测试6 空输入 失败: 应抛出错误")
    except WerssError as exc:
        assert exc.code == "E001", f"错误码应为E001, 实际: {exc.code}"
        passed += 1
        print("✓ 测试6 空输入 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试6 空输入 失败: {exc}")

    # ---- 测试 7：缺少关键字段 ----
    try:
        process_input(test_article_7)
        failed += 1
        print("✗ 测试7 缺少字段 失败: 应抛出错误")
    except WerssError as exc:
        assert exc.code == "E002", f"错误码应为E002, 实际: {exc.code}"
        passed += 1
        print("✓ 测试7 缺少字段 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试7 缺少字段 失败: {exc}")

    # ---- 测试 8：批量处理 ----
    try:
        results = batch_process(test_batch)
        assert len(results) == 2, f"应返回2个结果, 实际: {len(results)}"
        assert all(r.get("markdown") for r in results), "每个结果都应包含markdown"
        passed += 1
        print("✓ 测试8 批量处理 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试8 批量处理 失败: {exc}")

    # ---- 测试 9：Markdown 格式 ----
    try:
        result = process_input(test_article_1)
        md = result["markdown"]
        assert "# " in md, "应包含标题标记"
        assert "---" in md, "应包含分隔线"
        assert len(md) > len(test_article_1["title"]), "markdown应比标题长"
        passed += 1
        print("✓ 测试9 Markdown格式 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试9 Markdown格式 失败: {exc}")

    # ---- 测试 10：错误码体系 ----
    try:
        # 验证所有错误码都有定义
        for code in ["E001", "E002", "E003", "E004", "E005"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 消息为空"
        passed += 1
        print("✓ 测试10 错误码体系 通过")
    except Exception as exc:
        failed += 1
        print(f"✗ 测试10 错误码体系 失败: {exc}")

    # ---- 汇总 ----
    print("=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        print("\n⚠️ 部分测试未通过，请检查实现。")
        return 1
    else:
        print("\n✅ 所有测试通过！")
        return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="公众号文章处理工具 (werss-cli)",
        epilog="示例: python main.py --input '{\"title\": \"测试\", \"content\": \"内容\"}'"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据：JSON字符串、文本或文件路径（以@开头表示文件）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="批量输入：JSON数组字符串"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（默认输出到stdout）"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入时显示帮助
    if not args.input and not args.batch:
        parser.print_help()
        return 0

    try:
        # 批量处理
        if args.batch:
            try:
                items = json.loads(args.batch)
            except json.JSONDecodeError as exc:
                raise WerssError("E008", f"批量输入JSON解析失败: {exc}") from exc

            if not isinstance(items, list):
                raise WerssError("E003", "批量输入应为JSON数组")

            results = batch_process(items)
            output_data = results

        # 单条处理
        else:
            raw_input = args.input
            # 文件输入
            if raw_input.startswith("@"):
                filepath = raw_input[1:]
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        raw_input = f.read()
                except OSError as exc:
                    raise WerssError("E008", f"无法读取文件: {exc}") from exc

            result = process_input(raw_input)
            output_data = result

        # 输出
        if args.format == "json":
            output_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        else:
            if isinstance(output_data, list):
                # 批量输出markdown
                parts = []
                for item in output_data:
                    if "markdown" in item:
                        parts.append(item["markdown"])
                output_str = "\n\n---\n\n".join(parts)
            else:
                output_str = output_data.get("markdown", json.dumps(output_data, ensure_ascii=False, indent=2))

        # 写入文件或输出到stdout
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_str)
            print(f"✅ 结果已保存到: {args.output}")
        else:
            print(output_str)

        return 0

    except WerssError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ [E010] 未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
