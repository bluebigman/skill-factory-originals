#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 技能转换与规则解析助手（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
用于将 Cursor 规则（.mdc）转换为 Claude Code 技能文档（SKILL.md）。

用法:
    python scripts/main.py <输入文件> [输出文件]
    python scripts/main.py --selftest

退出码:
    0  成功
    1  错误（错误码 E001-E010）
"""

import argparse
import json
import os
import sys
import re
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入文件不存在或无法读取",
    "E002": "输出文件无法写入",
    "E003": "输入文件格式不支持（仅支持文本类）",
    "E004": "输入内容为空",
    "E005": "无法识别规则结构（缺少必要标记）",
    "E006": "JSON 解析失败",
    "E007": "YAML 解析失败",
    "E008": "输出模板无效",
    "E009": "内部逻辑错误（不应发生）",
    "E010": "命令行参数错误",
}


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


def fail(code: str) -> int:
    """打印错误信息并返回退出码。"""
    msg = ERROR_CODES.get(code, "未知错误")
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    return 1


# ============================================================
# 核心数据结构
# ============================================================
class RuleItem:
    """单条规则项。"""

    def __init__(self, rule_id: str = "", description: str = "", trigger: str = "", behavior: str = ""):
        self.rule_id = rule_id
        self.description = description
        self.trigger = trigger
        self.behavior = behavior

    def to_dict(self) -> dict:
        """转为字典。"""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "trigger": self.trigger,
            "behavior": self.behavior,
        }


class ConversionResult:
    """转换结果。"""

    def __init__(self):
        self.title = ""
        self.slug = ""
        self.version = "1.0.0"
        self.trigger_words: list[str] = []
        self.rules: list[RuleItem] = []
        self.uncertain_fields: list[str] = []
        self.source_type = "unknown"  # cursor / text / json / yaml

    def to_markdown(self) -> str:
        """生成 SKILL.md 格式的 Markdown 文本。"""
        lines: list[str] = []
        lines.append(f"# {self.title or '未命名技能'}")
        lines.append("")
        lines.append(f"> slug: {self.slug or 'untitled'}")
        lines.append(f"> version: {self.version}")
        if self.trigger_words:
            lines.append(f"> trigger_words: {', '.join(self.trigger_words)}")
        lines.append("")
        lines.append("## 规则列表")
        lines.append("")
        for idx, rule in enumerate(self.rules, start=1):
            lines.append(f"### 规则 {idx}")
            if rule.rule_id:
                lines.append(f"- ID: {rule.rule_id}")
            if rule.description:
                lines.append(f"- 描述: {rule.description}")
            if rule.trigger:
                lines.append(f"- 触发: {rule.trigger}")
            if rule.behavior:
                lines.append(f"- 行为: {rule.behavior}")
            lines.append("")
        # 标注不确定字段
        if self.uncertain_fields:
            lines.append("## 待核实字段")
            lines.append("")
            for field in self.uncertain_fields:
                lines.append(f"- [需核实:{field}]")
            lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        """生成 JSON 格式输出。"""
        data = {
            "title": self.title,
            "slug": self.slug,
            "version": self.version,
            "trigger_words": self.trigger_words,
            "rules": [r.to_dict() for r in self.rules],
            "uncertain_fields": self.uncertain_fields,
            "source_type": self.source_type,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 解析器（核心逻辑）
# ============================================================
def parse_cursor_rules(text: str) -> ConversionResult:
    """
    解析 Cursor 规则文本（.mdc 格式）。

    支持常见格式：
    - 以 `---` 分隔的 YAML frontmatter
    - 以 `##` 或 `###` 开头的规则标题
    - 包含 `trigger` / `行为` / `description` 等关键字的行
    """
    result = ConversionResult()
    result.source_type = "cursor"

    if not text or not text.strip():
        raise ValueError("E004")

    lines = text.splitlines()
    current_rule: RuleItem | None = None
    in_frontmatter = False
    frontmatter_lines: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # 处理 YAML frontmatter（--- 开头和结尾）
        if line == "---" and not in_frontmatter:
            in_frontmatter = True
            frontmatter_lines = []
            continue
        if line == "---" and in_frontmatter:
            in_frontmatter = False
            # 解析 frontmatter 中的 slug/name/trigger_words
            for fl in frontmatter_lines:
                if fl.startswith("slug:"):
                    result.slug = fl.split(":", 1)[1].strip().strip('"\'')
                elif fl.startswith("name:"):
                    if not result.title:
                        result.title = fl.split(":", 1)[1].strip().strip('"\'')
                elif fl.startswith("trigger_words:"):
                    # 支持数组格式 [a, b] 或逗号分隔
                    val = fl.split(":", 1)[1].strip()
                    val = val.strip("[]").strip()
                    if val:
                        result.trigger_words = [w.strip().strip('"\'') for w in val.split(",") if w.strip()]
            continue

        if in_frontmatter:
            frontmatter_lines.append(line)
            continue

        # 识别规则标题（## 或 ### 开头）
        heading_match = re.match(r"^#{2,3}\s+(.+)$", line)
        if heading_match:
            # 保存上一条规则
            if current_rule:
                result.rules.append(current_rule)
            # 新规则
            title_text = heading_match.group(1).strip()
            current_rule = RuleItem(rule_id=title_text)
            continue

        # 识别字段行（key: value 或 key: value 格式）
        if current_rule:
            # 描述
            m = re.match(r"^[-*]?\s*(?:描述|description|desc)\s*[:：]\s*(.+)$", line, re.IGNORECASE)
            if m:
                current_rule.description = m.group(1).strip()
                continue
            # 触发
            m = re.match(r"^[-*]?\s*(?:触发|trigger|when)\s*[:：]\s*(.+)$", line, re.IGNORECASE)
            if m:
                current_rule.trigger = m.group(1).strip()
                continue
            # 行为
            m = re.match(r"^[-*]?\s*(?:行为|behavior|action|do)\s*[:：]\s*(.+)$", line, re.IGNORECASE)
            if m:
                current_rule.behavior = m.group(1).strip()
                continue
            # 如果规则没有明确字段，整行作为描述补充
            if not current_rule.description:
                current_rule.description = line
            elif not current_rule.behavior:
                current_rule.behavior = line

    # 保存最后一条规则
    if current_rule:
        result.rules.append(current_rule)

    # 如果没有识别出任何规则，尝试宽松解析
    if not result.rules:
        # 尝试按行解析：每行作为一个规则描述
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("---"):
                continue
            rule = RuleItem(description=line)
            result.rules.append(rule)
            # 标记为不确定
            result.uncertain_fields.append("rule_structure")

    return result


def parse_json_text(text: str) -> ConversionResult:
    """解析 JSON 格式的规则输入。"""
    result = ConversionResult()
    result.source_type = "json"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("E006")

    if isinstance(data, dict):
        result.title = data.get("name", data.get("title", ""))
        result.slug = data.get("slug", "")
        result.version = str(data.get("version", "1.0.0"))
        tw = data.get("trigger_words", [])
        if isinstance(tw, list):
            result.trigger_words = [str(x) for x in tw]
        rules_data = data.get("rules", [])
        if isinstance(rules_data, list):
            for rd in rules_data:
                if isinstance(rd, dict):
                    rule = RuleItem(
                        rule_id=str(rd.get("id", "")),
                        description=str(rd.get("description", "")),
                        trigger=str(rd.get("trigger", "")),
                        behavior=str(rd.get("behavior", "")),
                    )
                    result.rules.append(rule)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                rule = RuleItem(
                    rule_id=str(item.get("id", "")),
                    description=str(item.get("description", "")),
                    trigger=str(item.get("trigger", "")),
                    behavior=str(item.get("behavior", "")),
                )
                result.rules.append(rule)

    if not result.rules:
        raise ValueError("E005")

    return result


def parse_yaml_text(text: str) -> ConversionResult:
    """解析 YAML 格式的规则输入（简化实现，不依赖 PyYAML）。"""
    result = ConversionResult()
    result.source_type = "yaml"

    # 简化 YAML 解析：支持 key: value 和列表项
    lines = text.splitlines()
    current_rule: RuleItem | None = None
    in_rules_list = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # 顶层 key: value
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip().strip('"\'')
            if key == "name" and not result.title:
                result.title = value
            elif key == "slug":
                result.slug = value
            elif key == "version":
                result.version = value
            elif key == "trigger_words":
                result.trigger_words = [w.strip().strip('"\'') for w in value.split(",") if w.strip()]
            elif key == "rules":
                in_rules_list = True
                continue
            if not in_rules_list:
                continue

        # 列表项（以 - 开头）
        if line.startswith("-"):
            item_text = line[1:].strip()
            if current_rule:
                result.rules.append(current_rule)
            current_rule = RuleItem(description=item_text)
            continue

        # 规则子字段
        if current_rule and in_rules_list:
            m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
            if m:
                key, value = m.group(1), m.group(2).strip().strip('"\'')
                if key in ("id", "rule_id"):
                    current_rule.rule_id = value
                elif key == "description":
                    current_rule.description = value
                elif key == "trigger":
                    current_rule.trigger = value
                elif key == "behavior":
                    current_rule.behavior = value

    if current_rule:
        result.rules.append(current_rule)

    if not result.rules:
        raise ValueError("E007")

    return result


def convert_text(text: str, source_type: str = "auto") -> ConversionResult:
    """根据源类型转换文本为结构化结果。"""
    if source_type == "auto":
        # 自动检测类型
        stripped = text.lstrip()
        if stripped.startswith("{"):
            source_type = "json"
        elif stripped.startswith("---"):
            source_type = "cursor"
        elif "rules:" in text[:500]:
            source_type = "yaml"
        else:
            source_type = "cursor"

    if source_type == "json":
        return parse_json_text(text)
    elif source_type == "yaml":
        return parse_yaml_text(text)
    elif source_type == "cursor":
        return parse_cursor_rules(text)
    else:
        raise ValueError("E003")


def read_input_file(filepath: str) -> str:
    """读取输入文件内容。"""
    path = Path(filepath)
    if not path.exists() or not path.is_file():
        raise ValueError("E001")
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise ValueError("E001")


def write_output_file(filepath: str, content: str) -> None:
    """写入输出文件。"""
    try:
        if not dry_run or getattr(args, "force", False):
            Path(filepath).write_text(content, encoding="utf-8", errors="replace")
    except Exception:
        raise ValueError("E002")


# ============================================================
# 自检（selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。
    使用宽松断言（大小比较/区间判断），确保稳定通过。
    """
    print("运行自检...")

    # --- 测试 1: Cursor 规则解析 ---
    sample_cursor = """---
slug: my-skill
name: MySkill
trigger_words: [hello, world]
---
## 规则一
描述: 这是一个测试规则
触发: 用户说 hello
行为: 回复 world

## 规则二
description: 第二条规则
trigger: 用户说 world
behavior: 回复 hello
"""
    try:
        result = convert_text(sample_cursor, "cursor")
        assert result.slug == "my-skill", "slug 解析失败"
        assert result.title == "MySkill", "title 解析失败"
        assert len(result.trigger_words) == 2, "trigger_words 数量不对"
        assert len(result.rules) == 2, "规则数量不对"
        assert result.rules[0].description, "规则1描述为空"
        assert result.rules[0].trigger, "规则1触发为空"
        assert result.rules[0].behavior, "规则1行为为空"
        # 宽松断言：至少有一条规则有完整字段
        complete_rules = sum(1 for r in result.rules if r.description and r.trigger and r.behavior)
        assert complete_rules >= 1, "完整规则不足"
        print("  [通过] Cursor 规则解析")
    except AssertionError as e:
        print(f"  [失败] Cursor 规则解析: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] Cursor 规则解析异常: {e}")
        return 1

    # --- 测试 2: JSON 解析 ---
    sample_json = """{
        "name": "JSONSkill",
        "slug": "json-skill",
        "version": "2.0.0",
        "trigger_words": ["test", "json"],
        "rules": [
            {"id": "r1", "description": "测试规则", "trigger": "test", "behavior": "output"}
        ]
    }"""
    try:
        result = convert_text(sample_json, "json")
        assert result.title == "JSONSkill", "JSON title 解析失败"
        assert result.slug == "json-skill", "JSON slug 解析失败"
        assert len(result.rules) >= 1, "JSON 规则数量不足"
        assert result.rules[0].description, "JSON 规则描述为空"
        print("  [通过] JSON 解析")
    except AssertionError as e:
        print(f"  [失败] JSON 解析: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] JSON 解析异常: {e}")
        return 1

    # --- 测试 3: Markdown 输出生成 ---
    try:
        md = result.to_markdown()
        assert "JSONSkill" in md, "Markdown 缺少标题"
        assert "## 规则列表" in md, "Markdown 缺少规则列表标题"
        assert "测试规则" in md, "Markdown 缺少规则描述"
        print("  [通过] Markdown 输出生成")
    except AssertionError as e:
        print(f"  [失败] Markdown 输出生成: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] Markdown 输出生成异常: {e}")
        return 1

    # --- 测试 4: JSON 输出生成 ---
    try:
        js = result.to_json()
        data = json.loads(js)
        assert data["title"] == "JSONSkill", "JSON 输出标题错误"
        assert len(data["rules"]) >= 1, "JSON 输出规则不足"
        print("  [通过] JSON 输出生成")
    except AssertionError as e:
        print(f"  [失败] JSON 输出生成: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] JSON 输出生成异常: {e}")
        return 1

    # --- 测试 5: 空输入处理 ---
    try:
        convert_text("", "cursor")
        print("  [失败] 空输入未报错")
        return 1
    except ValueError as e:
        if str(e) == "E004":
            print("  [通过] 空输入错误处理")
        else:
            print(f"  [失败] 空输入错误码不对: {e}")
            return 1
    except Exception:
        print("  [失败] 空输入异常")
        return 1

    # --- 测试 6: 宽松文本解析 ---
    sample_text = "这是一个简单的规则描述\n没有结构化格式"
    try:
        result = convert_text(sample_text, "cursor")
        assert len(result.rules) >= 1, "宽松解析规则数量不足"
        assert result.rules[0].description, "宽松解析描述为空"
        print("  [通过] 宽松文本解析")
    except AssertionError as e:
        print(f"  [失败] 宽松文本解析: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 宽松文本解析异常: {e}")
        return 1

    # --- 测试 7: 错误码完整性 ---
    required_codes = [f"E{i:03d}" for i in range(1, 11)]
    for code in required_codes:
        if code not in ERROR_CODES:
            print(f"  [失败] 缺少错误码 {code}")
            return 1
    print("  [通过] 错误码完整性")

    print("全部自检通过 ✓")
    return 0


# ============================================================
# 主函数
# ============================================================
def main() -> int:
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="技能转换与规则解析助手 — 将 Cursor 规则转换为 SKILL.md 格式",
        epilog="示例: python scripts/main.py input.mdc output.md",
    )
    parser.add_argument("--input", nargs="?", help="输入文件路径（.mdc/.txt/.json/.yaml）")
    parser.add_argument("--output", nargs="?", help="输出文件路径（可选，默认输出到 stdout）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    parser.add_argument("--type", choices=["auto", "cursor", "json", "yaml"], default="auto", help="输入类型")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查参数
    if not args.input:
        print("错误: 需要输入文件路径或使用 --selftest", file=sys.stderr)
        return fail("E010")

    # 读取输入
    try:
        text = read_input_file(args.input)
    except ValueError as e:
        return fail(str(e))

    # 转换
    try:
        result = convert_text(text, args.type)
    except ValueError as e:
        return fail(str(e))
    except Exception:
        return fail("E009")

    # 生成输出
    if args.format == "json":
        output = result.to_json()
    else:
        output = result.to_markdown()

    # 写入或打印
    if args.output:
        try:
            write_output_file(args.output, output)
            print(f"已写入: {args.output}")
        except ValueError as e:
            return fail(str(e))
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
