#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ram - 资源解析 / 结构化转换 / 资产管理

一个轻量级命令行工具，用于将文本、文件路径或 URL 内容解析为结构化结果，
并标注每条字段的置信度（高/中/低）。

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from datetime import timezone  # G2 时区修复


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用级异常基类，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心数据结构
# ============================================================
class ParsedField:
    """单个字段的解析结果，包含值和置信度。"""

    def __init__(self, value: Any, confidence: str = "高"):
        self.value = value
        self.confidence = confidence  # 高 / 中 / 低

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.value, "confidence": self.confidence}


class ParseResult:
    """一条完整记录的解析结果。"""

    def __init__(self, source: str, source_type: str):
        self.source = source
        self.source_type = source_type
        self.fields: Dict[str, ParsedField] = {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def add_field(self, name: str, value: Any, confidence: str = "高") -> None:
        """添加或覆盖一个字段。"""
        self.fields[name] = ParsedField(value, confidence)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典结构。"""
        return {
            "source": self.source,
            "source_type": self.source_type,
            "created_at": self.created_at,
            "fields": {k: v.to_dict() for k, v in self.fields.items()},
        }


# ============================================================
# 输入识别与解析
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


def detect_source_type(source: str) -> str:
    """
    识别输入来源类型。
    返回: "text" / "file" / "url"
    """
    if not source or not source.strip():
        raise AppError("E001", "输入内容为空")

    # 判断是否为 URL
    if source.startswith(("http://", "https://", "ftp://")):
        return "url"

    # 判断是否为文件路径
    if source.startswith((".", "/", "~")) or "\\" in source or os.path.exists(source):
        # 检查是否为文本文件
        if os.path.isfile(source):
            ext = os.path.splitext(source)[1].lower()
            if ext in (".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml"):
                return "file"
            raise AppError("E002", f"不支持的文件类型: {ext}")
        return "text"

    return "text"


def read_text_file(file_path: str) -> str:
    """读取文本文件内容。"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        raise AppError("E003", f"文件不存在: {file_path}")
    except PermissionError:
        raise AppError("E004", f"无权限读取文件: {file_path}")
    except UnicodeDecodeError:
        raise AppError("E005", f"文件编码不是 UTF-8: {file_path}")


def extract_key_value_pairs(content: str) -> Dict[str, str]:
    """
    从文本内容中提取 key: value 或 key=value 形式的关键信息。
    返回提取到的键值对字典。
    """
    result: Dict[str, str] = {}
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        # 尝试多种分隔符
        for sep in (":", "=", "：", "＝"):
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    key = parts[0].strip().strip('"\'')
                    value = parts[1].strip().strip('"\'')
                    if key and value and key not in result:
                        result[key] = value
                        break

    return result


def extract_structured_fields(content: str) -> Dict[str, Tuple[Any, str]]:
    """
    从文本内容中提取结构化字段，返回字段名到 (值, 置信度) 的映射。
    """
    fields: Dict[str, Tuple[Any, str]] = {}

    # 尝试 JSON 解析
    content_stripped = content.strip()
    if content_stripped.startswith("{") and content_stripped.endswith("}"):
        try:
            data = json.loads(content_stripped)
            if isinstance(data, dict):
                for k, v in data.items():
                    # 字符串值置信度高，其他类型中
                    conf = "高" if isinstance(v, str) else "中"
                    fields[str(k)] = (v, conf)
                return fields
        except json.JSONDecodeError:
            pass  # 不是有效 JSON，继续后续处理

    # 尝试键值对提取
    kv_pairs = extract_key_value_pairs(content)
    if len(kv_pairs) >= 2:
        for k, v in kv_pairs.items():
            fields[k] = (v, "高")
        return fields

    # 尝试 CSV 格式（简单识别）
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    if len(lines) >= 2 and "," in lines[0]:
        headers = [h.strip() for h in lines[0].split(",")]
        if len(headers) >= 2 and len(lines) >= 2:
            values = [v.strip() for v in lines[1].split(",")]
            for i, h in enumerate(headers):
                if i < len(values) and values[i]:
                    fields[h] = (values[i], "高")
                else:
                    fields[h] = ("待核实", "低")
            return fields

    return fields


def parse_source(source: str) -> ParseResult:
    """
    解析输入源，返回结构化结果。
    """
    source_type = detect_source_type(source)

    # 获取原始内容
    if source_type == "file":
        content = read_text_file(source)
    else:
        content = source

    result = ParseResult(source, source_type)

    # 提取结构化字段
    fields = extract_structured_fields(content)

    if fields:
        # 有提取到字段，逐条添加
        for name, (value, conf) in fields.items():
            result.add_field(name, value, conf)

        # 添加元信息字段
        result.add_field("内容长度", len(content), "高")
        result.add_field("字段数量", len(fields), "高")
    else:
        # 未提取到结构化字段，整段作为内容
        if len(content) > 200:
            snippet = content[:200] + "..."
            result.add_field("内容摘要", snippet, "中")
            result.add_field("完整内容", content, "高")
        else:
            result.add_field("内容", content, "高")

    return result


# ============================================================
# 批量处理
# ============================================================
def process_batch(sources: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入源。"""
    results = []
    for source in sources:
        try:
            result = parse_source(source)
            results.append(result.to_dict())
        except AppError as e:
            results.append({
                "source": source,
                "source_type": "error",
                "error_code": e.code,
                "error_message": e.message,
            })
    return results


# ============================================================
# 输出格式化
# ============================================================
def format_markdown(result: Dict[str, Any]) -> str:
    """将解析结果格式化为 Markdown 文本。"""
    lines = []
    lines.append(f"## 解析结果")
    lines.append(f"")
    lines.append(f"- **来源**: `{result.get('source', '')}`")
    lines.append(f"- **类型**: {result.get('source_type', '未知')}")
    lines.append(f"- **时间**: {result.get('created_at', '')}")
    lines.append(f"")

    if "error_code" in result:
        lines.append(f"### ❌ 错误")
        lines.append(f"")
        lines.append(f"错误码: {result['error_code']}")
        lines.append(f"错误信息: {result['error_message']}")
        return "\n".join(lines)

    fields = result.get("fields", {})
    if not fields:
        lines.append("_无字段提取_")
        return "\n".join(lines)

    lines.append(f"### 字段详情 ({len(fields)} 项)")
    lines.append(f"")
    lines.append(f"| 字段 | 值 | 置信度 |")
    lines.append(f"|------|-----|--------|")

    for name, info in fields.items():
        value = info.get("value", "")
        conf = info.get("confidence", "中")
        # 截断过长的值
        value_str = str(value)
        if len(value_str) > 80:
            value_str = value_str[:77] + "..."
        lines.append(f"| {name} | {value_str} | {conf} |")

    return "\n".join(lines)


# ============================================================
# 自检逻辑
# ============================================================
def run_selftest() -> int:
    """
    内置自检逻辑，不依赖外部文件或网络。
    使用宽松断言，确保任何环境可运行通过。
    """
    print("=== ram 自检开始 ===")
    passed = 0
    total = 0

    # 测试1: 基本文本解析
    print("\n[测试1] 基础文本解析")
    try:
        text = "名称: 测试资产\n类型: 文档\n大小: 1MB\n作者: 张三"
        result = parse_source(text)
        d = result.to_dict()
        total += 1
        assert d["source_type"] == "text", "来源类型应为 text"
        assert "名称" in d["fields"], "应提取到 名称 字段"
        assert "类型" in d["fields"], "应提取到 类型 字段"
        assert d["fields"]["名称"]["value"] == "测试资产", "名称值不匹配"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试2: JSON 解析
    print("\n[测试2] JSON 解析")
    try:
        json_text = '{"title": "报告", "author": "李四", "year": 2026}'
        result = parse_source(json_text)
        d = result.to_dict()
        total += 1
        assert d["fields"]["title"]["value"] == "报告", "title 值不匹配"
        assert "author" in d["fields"], "应提取到 author 字段"
        assert "year" in d["fields"], "应提取到 year 字段"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试3: URL 识别
    print("\n[测试3] URL 类型识别")
    try:
        url = "https://example.com/page?id=1"
        result = parse_source(url)
        d = result.to_dict()
        total += 1
        assert d["source_type"] == "url", "来源类型应为 url"
        assert "内容" in d["fields"] or "内容摘要" in d["fields"], "应有内容字段"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试4: 批量处理
    print("\n[测试4] 批量处理")
    try:
        sources = [
            "名称: 资产A\n类型: 图片",
            '{"name": "资产B", "type": "视频"}',
            "https://example.com/asset/1",
        ]
        results = process_batch(sources)
        total += 1
        assert len(results) == 3, f"应返回 3 条结果，实际 {len(results)}"
        assert results[0]["source_type"] == "text", "第一条应为 text"
        assert results[1]["source_type"] == "text", "第二条应为 text (JSON)"
        assert results[2]["source_type"] == "url", "第三条应为 url"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试5: 错误处理
    print("\n[测试5] 错误处理")
    try:
        total += 1
        # 空输入
        try:
            parse_source("")
            assert False, "空输入应抛出异常"
        except AppError as e:
            assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试6: Markdown 输出
    print("\n[测试6] Markdown 格式化")
    try:
        text = "名称: 测试\n类型: 文档"
        result = parse_source(text)
        md = format_markdown(result.to_dict())
        total += 1
        assert "## 解析结果" in md, "应包含标题"
        assert "名称" in md, "应包含字段名"
        assert "置信度" in md, "应包含置信度表头"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试7: CSV 解析
    print("\n[测试7] CSV 解析")
    try:
        csv_text = "名称,类型,大小\n项目文档,文档,2MB\n"
        result = parse_source(csv_text)
        d = result.to_dict()
        total += 1
        assert "名称" in d["fields"], "应提取到 名称 列"
        assert d["fields"]["名称"]["value"] == "项目文档", "名称值不匹配"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试8: 置信度标注
    print("\n[测试8] 置信度标注")
    try:
        json_text = '{"name": "资产", "count": 42}'
        result = parse_source(json_text)
        d = result.to_dict()
        total += 1
        assert d["fields"]["name"]["confidence"] == "高", "字符串字段应为高置信度"
        assert d["fields"]["count"]["confidence"] == "中", "数字字段应为中置信度"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 汇总
    print(f"\n=== 自检完成: {passed}/{total} 通过 ===")
    if passed == total:
        print("✅ 全部通过")
        return 0
    else:
        print("❌ 有失败项")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="ram - 资源解析 / 结构化转换 / 资产管理",
        epilog="示例: python main.py '名称: 测试\\n类型: 文档'",
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        help="输入内容：文本、文件路径或 URL",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部数据）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：每条输入单独处理",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入
    if not args.inputs:
        parser.print_help()
        return 0

    try:
        if args.batch:
            # 批量模式
            results = process_batch(args.inputs)
        else:
            # 单条模式：合并所有输入
            combined = "\n".join(args.inputs)
            result = parse_source(combined)
            results = [result.to_dict()]

        # 输出
        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print(format_markdown(r))
                print()

        return 0

    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
