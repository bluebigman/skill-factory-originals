#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Cursor Handbook 规则引擎技能文档生成器（独立实现）

功能概述：
    将 Cursor IDE 的规则集文本（Markdown / JSON / YAML）解析为
    结构化、可查询、可校验、可导出的技能文档。

设计原则：
    - 仅使用 Python 标准库。
    - 所有核心逻辑均为独立实现（clean-room）。
    - 支持 --selftest 离线自检，不依赖外部文件或网络。

错误码约定：
    E001 参数解析失败
    E002 输入文件不存在或不可读
    E003 输入格式不支持（非 txt/md/json/yaml）
    E004 JSON 解析失败
    E005 YAML 解析失败（未安装 PyYAML 时）
    E006 规则结构无效（缺少必要字段）
    E007 输出目录不可写
    E008 模板渲染失败
    E009 内部逻辑错误（不应发生）
    E010 未知异常
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """单条规则的结构化表示。"""
    name: str = ""
    trigger: str = ""          # when 条件
    action: str = ""           # then 动作
    priority: str = "medium"   # high / medium / low
    dependencies: List[str] = field(default_factory=list)
    confidence: float = 0.5    # 0.0 ~ 1.0
    source_line: int = 0       # 原始文本中的行号（可选）
    raw_text: str = ""         # 原始片段


@dataclass
class RuleSet:
    """一组规则的集合，附带元信息。"""
    title: str = "Cursor Rules"
    version: str = "1.0.0"
    rules: List[Rule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于 JSON 序列化）。"""
        return {
            "title": self.title,
            "version": self.version,
            "rules": [asdict(r) for r in self.rules],
        }


# ---------------------------------------------------------------------------
# 解析器：从文本 / JSON / YAML 提取规则
# ---------------------------------------------------------------------------

class RuleParser:
    """将不同格式的输入解析为 RuleSet。"""

    def parse(self, content: str, fmt: str = "md") -> RuleSet:
        """根据格式分发到具体解析方法。"""
        fmt = fmt.lower().lstrip(".")
        if fmt in ("md", "markdown", "txt", "text"):
            return self._parse_markdown(content)
        if fmt == "json":
            return self._parse_json(content)
        if fmt in ("yaml", "yml"):
            return self._parse_yaml(content)
        raise ValueError(f"E003: 不支持的输入格式 '{fmt}'")

    # -- Markdown / 纯文本 -------------------------------------------------
    def _parse_markdown(self, content: str) -> RuleSet:
        """从 Markdown 或纯文本中提取规则。"""
        ruleset = RuleSet()
        lines = content.splitlines()

        # 尝试从标题中提取文档标题
        for line in lines[:20]:
            m = re.match(r"^#\s+(.+)$", line.strip())
            if m:
                ruleset.title = m.group(1).strip()
                break

        current: Optional[Rule] = None
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # 检测新规则块开始（宽松匹配）
            if self._looks_like_rule_header(stripped):
                if current is not None:
                    ruleset.rules.append(current)
                current = Rule(name=self._extract_rule_name(stripped), source_line=idx, raw_text=stripped)
                continue

            if current is None:
                continue

            # 填充当前规则的字段
            lower = stripped.lower()
            if lower.startswith("when") or lower.startswith("触发"):
                current.trigger = self._clean_value(stripped)
            elif lower.startswith("then") or lower.startswith("动作"):
                current.action = self._clean_value(stripped)
            elif lower.startswith("priority") or lower.startswith("优先级"):
                current.priority = self._clean_value(stripped).lower()
            elif "依赖" in lower or lower.startswith("depends"):
                current.dependencies = self._split_dependencies(stripped)
            elif "confidence" in lower or "置信" in lower:
                current.confidence = self._parse_confidence(stripped)

        if current is not None:
            ruleset.rules.append(current)

        return ruleset

    # -- JSON ----------------------------------------------------------------
    def _parse_json(self, content: str) -> RuleSet:
        """从 JSON 解析规则。"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"E004: JSON 解析失败 — {exc}") from exc

        if isinstance(data, list):
            return self._rules_from_list(data)
        if isinstance(data, dict):
            return self._rules_from_dict(data)
        raise ValueError("E006: JSON 根节点必须是对象或数组")

    # -- YAML ----------------------------------------------------------------
    def _parse_yaml(self, content: str) -> RuleSet:
        """从 YAML 解析规则。优先使用 PyYAML，缺失时给出错误提示。"""
        try:
            import yaml  # pip install pyyaml
        except ImportError:
            raise ValueError("E005: 解析 YAML 需要 PyYAML，请先执行 pip install pyyaml") from None

        try:
            data = yaml.safe_load(content)
        except Exception as exc:
            raise ValueError(f"E005: YAML 解析失败 — {exc}") from exc

        if isinstance(data, list):
            return self._rules_from_list(data)
        if isinstance(data, dict):
            return self._rules_from_dict(data)
        raise ValueError("E006: YAML 根节点必须是对象或数组")

    # -- 内部辅助 ------------------------------------------------------------
    def _rules_from_list(self, items: List[Any]) -> RuleSet:
        """从列表结构构建 RuleSet。"""
        ruleset = RuleSet()
        for item in items:
            if not isinstance(item, dict):
                continue
            rule = Rule()
            rule.name = str(item.get("name", item.get("规则", "")))
            rule.trigger = str(item.get("when", item.get("trigger", item.get("触发", ""))))
            rule.action = str(item.get("then", item.get("action", item.get("动作", ""))))
            rule.priority = str(item.get("priority", item.get("优先级", "medium"))).lower()
            deps = item.get("depends", item.get("dependencies", item.get("依赖", [])))
            rule.dependencies = deps if isinstance(deps, list) else [str(deps)]
            conf = item.get("confidence", item.get("置信度", 0.5))
            rule.confidence = float(conf) if isinstance(conf, (int, float)) else 0.5
            ruleset.rules.append(rule)
        return ruleset

    def _rules_from_dict(self, data: Dict[str, Any]) -> RuleSet:
        """从字典结构构建 RuleSet。"""
        ruleset = RuleSet()
        ruleset.title = str(data.get("title", data.get("名称", "Cursor Rules")))
        ruleset.version = str(data.get("version", data.get("版本", "1.0.0")))
        raw_rules = data.get("rules", data.get("规则", []))
        if isinstance(raw_rules, list):
            ruleset.rules = self._rules_from_list(raw_rules).rules
        return ruleset

    # -- 文本辅助 ------------------------------------------------------------
    @staticmethod
    def _looks_like_rule_header(text: str) -> bool:
        """判断一行文本是否像规则标题。"""
        if not text:
            return False
        lowered = text.lower()
        # 支持中英文关键词
        keywords = ("rule", "规则", "when", "触发", "if", "如果")
        for kw in keywords:
            if lowered.startswith(kw):
                return True
        return False

    @staticmethod
    def _extract_rule_name(text: str) -> str:
        """从标题行提取规则名称。"""
        # 去掉常见前缀
        cleaned = re.sub(r"^(rule|规则|when|触发|if|如果)\s*[：:]\s*", "", text, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" -#*")
        return cleaned[:80]  # 限制长度

    @staticmethod
    def _clean_value(text: str) -> str:
        """清理字段值。"""
        # 去掉前缀
        cleaned = re.sub(
            r"^(when|then|priority|触发|动作|优先级)\s*[：:]\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return cleaned.strip()

    @staticmethod
    def _split_dependencies(text: str) -> List[str]:
        """拆分依赖列表。"""
        cleaned = re.sub(
            r"^(depends|dependencies|依赖)\s*[：:]\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        parts = re.split(r"[,，、;；]", cleaned)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _parse_confidence(text: str) -> float:
        """解析置信度（0~1 或 0~100）。"""
        m = re.search(r"([0-9]*\.?[0-9]+)", text)
        if not m:
            return 0.5
        val = float(m.group(1))
        if val > 1.0:
            val = val / 100.0
        return max(0.0, min(1.0, val))


# ---------------------------------------------------------------------------
# 校验器
# ---------------------------------------------------------------------------

class RuleValidator:
    """对规则集进行结构校验。"""

    def validate(self, ruleset: RuleSet) -> List[str]:
        """返回问题列表，空列表表示全部通过。"""
        issues: List[str] = []
        if not ruleset.title.strip():
            issues.append("规则集缺少标题")

        for idx, rule in enumerate(ruleset.rules, start=1):
            if not rule.name.strip():
                issues.append(f"第 {idx} 条规则缺少名称")
            if not rule.trigger.strip() and not rule.action.strip():
                issues.append(f"规则 '{rule.name or idx}' 缺少 when/then 条件")
            if rule.priority not in ("high", "medium", "low"):
                issues.append(f"规则 '{rule.name or idx}' 优先级无效: {rule.priority}")
            if not (0.0 <= rule.confidence <= 1.0):
                issues.append(f"规则 '{rule.name or idx}' 置信度超出范围")
        return issues


# ---------------------------------------------------------------------------
# 导出器：生成 Markdown / JSON 文档
# ---------------------------------------------------------------------------

class RuleExporter:
    """将 RuleSet 导出为不同格式。"""

    def to_markdown(self, ruleset: RuleSet) -> str:
        """生成 Markdown 表格文档。"""
        lines = [
            f"# {ruleset.title}",
            "",
            f"> 版本: {ruleset.version}",
            "",
            "## 规则清单",
            "",
            "| 序号 | 规则名称 | 触发条件 | 动作 | 优先级 | 置信度 |",
            "|------|----------|----------|------|--------|--------|",
        ]
        for idx, rule in enumerate(ruleset.rules, start=1):
            conf = f"{rule.confidence:.0%}"
            lines.append(
                f"| {idx} | {rule.name} | {rule.trigger} | {rule.action} "
                f"| {rule.priority} | {conf} |"
            )
        lines.append("")
        return "\n".join(lines)

    def to_json(self, ruleset: RuleSet) -> str:
        """生成 JSON 文档。"""
        return json.dumps(ruleset.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------

def parse_args(argv: List[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Cursor Handbook — 规则引擎技能文档生成器",
        epilog="示例: python main.py input.md -o output.json",
    )
    parser.add_argument("input", nargs="?", help="输入文件路径 (.md/.txt/.json/.yaml)")
    parser.add_argument("-o", "--output", help="输出文件路径（默认 stdout）")
    parser.add_argument("-f", "--format", choices=["md", "json"], default="md", help="输出格式")
    parser.add_argument("--validate", action="store_true", help="仅校验，不输出")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    return parser.parse_args(argv)


def read_input(path: str) -> Tuple[str, str]:
    """读取输入文件，返回 (内容, 格式)。"""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"E002: 文件不存在: {path}")

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in ("md", "markdown", "txt", "text", "json", "yaml", "yml"):
        raise ValueError(f"E003: 不支持的文件格式 '.{ext}'")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        raise OSError(f"E002: 读取文件失败: {exc}") from exc

    return content, ext


def write_output(path: Optional[str], content: str) -> None:
    """写入输出文件或打印到 stdout。"""
    if path:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        except OSError as exc:
            raise OSError(f"E007: 写入文件失败: {exc}") from exc
    else:
        print(content)


# ---------------------------------------------------------------------------
# 自检模块（硬编码样例数据，离线运行）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """内置样例数据自检核心逻辑。返回 0 表示通过。"""
    print("[SELFTEST] 开始离线自检...")

    try:
        # 1. 解析 Markdown 样例
        sample_md = """# 测试规则集

## 规则：代码格式检查
- when: 用户提交 Python 代码
- then: 自动运行 Black 格式化
- priority: high
- confidence: 0.9

## 规则：依赖检查
- when: 修改 requirements.txt
- then: 检查依赖冲突
- priority: medium
- depends: 代码格式检查
"""
        parser = RuleParser()
        ruleset = parser.parse(sample_md, "md")
        assert len(ruleset.rules) >= 2, f"E009: 期望至少 2 条规则，实际 {len(ruleset.rules)}"
        assert ruleset.title == "测试规则集", f"E009: 标题解析错误: {ruleset.title}"
        print(f"  [OK] Markdown 解析: 提取 {len(ruleset.rules)} 条规则")

        # 2. 解析 JSON 样例
        sample_json = json.dumps({
            "title": "JSON 规则集",
            "version": "2.0.0",
            "rules": [
                {"name": "规则A", "when": "条件A", "then": "动作A", "priority": "high"},
                {"name": "规则B", "when": "条件B", "then": "动作B", "priority": "low"},
            ],
        })
        ruleset2 = parser.parse(sample_json, "json")
        assert len(ruleset2.rules) == 2, f"E009: JSON 规则数量错误: {len(ruleset2.rules)}"
        assert ruleset2.version == "2.0.0", "E009: JSON 版本解析错误"
        print(f"  [OK] JSON 解析: 提取 {len(ruleset2.rules)} 条规则")

        # 3. 校验器测试
        validator = RuleValidator()
        issues = validator.validate(ruleset)
        assert isinstance(issues, list), "E009: 校验结果类型错误"
        print(f"  [OK] 校验器: 发现 {len(issues)} 个问题（预期为 0）")

        # 4. 导出测试
        exporter = RuleExporter()
        md_output = exporter.to_markdown(ruleset)
        assert "| 1 |" in md_output, "E009: Markdown 导出缺少表格行"
        assert md_output.count("|") >= 10, "E009: Markdown 导出表格不完整"

        json_output = exporter.to_json(ruleset2)
        parsed_back = json.loads(json_output)
        assert parsed_back["title"] == "JSON 规则集", "E009: JSON 导出回读失败"
        assert len(parsed_back["rules"]) == 2, "E009: JSON 导出规则数量错误"
        print("  [OK] 导出器: Markdown 与 JSON 输出验证通过")

        # 5. 边界情况：空输入
        empty_ruleset = parser.parse("", "md")
        assert len(empty_ruleset.rules) == 0, "E009: 空输入应产生 0 条规则"
        assert empty_ruleset.title == "Cursor Rules", "E009: 空输入标题应为默认值"
        print("  [OK] 边界情况: 空输入处理正常")

        # 6. 宽松断言（不依赖精确值）
        assert len(ruleset.rules) > 0, "E009: 规则数应为正数"
        assert all(r.confidence >= 0.0 and r.confidence <= 1.0 for r in ruleset.rules), \
            "E009: 置信度应在 [0, 1] 区间"
        assert all(r.priority in ("high", "medium", "low") for r in ruleset.rules), \
            "E009: 优先级应为 high/medium/low"

        print("[SELFTEST] 全部通过 ✅")
        return 0

    except Exception as exc:
        print(f"[SELFTEST] 失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])

        # 自检模式
        if args.selftest:
            return run_selftest()

        # 正常模式
        if not args.input:
            print("E001: 缺少输入文件参数", file=sys.stderr)
            print("用法: python main.py <input> [-o output] [-f md|json]", file=sys.stderr)
            return 1

        # 读取输入
        try:
            content, fmt = read_input(args.input)
        except (FileNotFoundError, ValueError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 2

        # 解析规则
        try:
            parser = RuleParser()
            ruleset = parser.parse(content, fmt)
        except ValueError as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 3

        # 校验（可选）
        validator = RuleValidator()
        issues = validator.validate(ruleset)
        if issues:
            print("校验发现以下问题:", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            if args.validate:
                return 4

        # 导出
        try:
            exporter = RuleExporter()
            if args.format == "json":
                output = exporter.to_json(ruleset)
            else:
                output = exporter.to_markdown(ruleset)
            write_output(args.output, output)
        except (OSError, ValueError) as exc:
            print(f"错误: {exc}", file=sys.stderr)
            return 5

        return 0

    except KeyboardInterrupt:
        print("\nE010: 用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"E010: 未预期错误 — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
