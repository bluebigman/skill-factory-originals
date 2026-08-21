#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cursor-handbook: Cursor规则 结构化转换 技能手册
=================================================
将Cursor IDE规则集转化为可查询、可校验、可执行的结构化技能文档。

功能模块:
  - parse_rule      规则解析（.mdc -> 结构化条目）
  - validate_rule   规则校验（语法/引用/命名）
  - convert_to_skill 规则转换（.mdc -> SKILL.md 文档）
  - query_rules     规则查询（关键词/场景/优先级）
  - build_steps     规则执行辅助（生成操作步骤清单）

命令行:
  python main.py <规则文件或目录> [--output 输出路径] [--format json|yaml|markdown]
  python main.py --selftest   # 离线自检（内置样例数据）

错误码:
  E001 输入路径不存在
  E002 文件读取失败
  E003 文件格式不支持（非 .mdc）
  E004 规则语法不完整（缺必需字段）
  E005 引用无效（引用了不存在的规则ID）
  E006 命名不规范（不符合命名约定）
  E007 输出目录不可写
  E008 输出格式不支持
  E009 查询条件为空
  E010 内部逻辑错误（未知状态）
"""

import sys
import os
import re
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class RuleEntry:
    """单条规则的结构化表示"""
    rule_id: str                    # 规则唯一标识，如 "R001"
    name: str                       # 规则名称
    description: str = ""           # 规则描述
    priority: str = "medium"        # 优先级: high / medium / low
    tags: List[str] = field(default_factory=list)       # 场景标签
    content: str = ""               # 规则原始内容
    applies_to: List[str] = field(default_factory=list) # 适用文件类型
    references: List[str] = field(default_factory=list) # 引用的其他规则ID
    file_path: str = ""             # 来源文件路径
    line_number: int = 0            # 起始行号

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON/YAML输出）"""
        return asdict(self)


@dataclass
class ValidationIssue:
    """校验发现的问题"""
    code: str                       # 错误码（E001-E010）
    message: str                    # 问题描述
    rule_id: str = ""               # 相关规则ID
    suggestion: str = ""            # 修正建议
    severity: str = "error"         # severity: error / warning


@dataclass
class ValidationReport:
    """校验报告"""
    total_rules: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rules": self.total_rules,
            "passed": self.passed,
            "issue_count": len(self.issues),
            "issues": [asdict(i) for i in self.issues]
        }


# ============================================================
# 解析模块
# ============================================================

def parse_rule_file(file_path: str) -> RuleEntry:
    """
    解析单个 .mdc 规则文件为结构化 RuleEntry。
    
    期望格式（简化示意）:
        ---
        name: 规则名称
        priority: high
        tags: [前端, 安全]
        applies_to: [*.ts, *.tsx]
        references: [R002]
        ---
        规则描述内容...
    
    参数:
        file_path: 规则文件路径
    
    返回:
        RuleEntry 结构化规则
    
    异常:
        E001 文件不存在
        E002 文件读取失败
        E003 非 .mdc 文件
        E004 语法不完整（缺少必需字段）
    """
    path = Path(file_path)
    
    # E001: 输入路径不存在
    if not path.exists():
        raise RuntimeError(f"E001: 文件不存在: {file_path}")
    
    # E003: 文件格式不支持
    if path.suffix.lower() != ".mdc":
        raise RuntimeError(f"E003: 不支持的文件格式: {path.suffix}，仅支持 .mdc")
    
    # E002: 文件读取失败
    try:
        raw_content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise RuntimeError(f"E002: 读取文件失败: {file_path} - {exc}")
    
    # 解析 frontmatter（--- 开头和结尾的 YAML 风格头信息）
    frontmatter: Dict[str, Any] = {}
    body_content: str = raw_content
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw_content, re.DOTALL)
    
    if fm_match:
        fm_text = fm_match.group(1)
        body_content = fm_match.group(2) if fm_match.group(2) else ""
        # 简单解析 key: value 或 key: [v1, v2]
        for line in fm_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                # 处理列表值 [a, b, c]
                if value.startswith("[") and value.endswith("]"):
                    items = [v.strip() for v in value[1:-1].split(",") if v.strip()]
                    frontmatter[key] = items
                else:
                    frontmatter[key] = value
    
    # 提取必需字段
    rule_id = frontmatter.get("id", "")
    name = frontmatter.get("name", "")
    
    # E004: 语法不完整
    if not rule_id or not name:
        raise RuntimeError(
            f"E004: 规则语法不完整: {file_path} - 缺少 'id' 或 'name' 字段"
        )
    
    # 构建规则条目
    entry = RuleEntry(
        rule_id=str(rule_id),
        name=str(name),
        description=str(frontmatter.get("description", "")),
        priority=str(frontmatter.get("priority", "medium")),
        tags=[str(t) for t in frontmatter.get("tags", [])] if isinstance(frontmatter.get("tags"), list) else [],
        content=body_content.strip(),
        applies_to=[str(a) for a in frontmatter.get("applies_to", [])] if isinstance(frontmatter.get("applies_to"), list) else [],
        references=[str(r) for r in frontmatter.get("references", [])] if isinstance(frontmatter.get("references"), list) else [],
        file_path=str(path),
        line_number=1
    )
    
    return entry


def parse_rule_directory(dir_path: str) -> List[RuleEntry]:
    """
    解析目录下所有 .mdc 规则文件。
    
    参数:
        dir_path: 规则目录路径
    
    返回:
        RuleEntry 列表
    """
    path = Path(dir_path)
    
    # E001: 输入路径不存在
    if not path.exists():
        raise RuntimeError(f"E001: 目录不存在: {dir_path}")
    
    if not path.is_dir():
        raise RuntimeError(f"E001: 不是目录: {dir_path}")
    
    rules: List[RuleEntry] = []
    for mdc_file in sorted(path.glob("*.mdc")):
        try:
            rule = parse_rule_file(str(mdc_file))
            rules.append(rule)
        except RuntimeError as exc:
            # 单个文件出错不影响整体，但记录到 stderr
            print(f"[警告] 跳过 {mdc_file.name}: {exc}", file=sys.stderr)
    
    return rules


# ============================================================
# 校验模块
# ============================================================

def validate_rules(rules: List[RuleEntry]) -> ValidationReport:
    """
    校验规则集合的完整性、引用有效性和命名规范性。
    
    校验项:
      1. 必需字段完整性（name, description, priority）
      2. 引用有效性（references 指向的规则必须存在）
      3. 命名规范性（rule_id 格式: R + 3位数字）
      4. 优先级合法性（high/medium/low）
    
    参数:
        rules: 规则条目列表
    
    返回:
        ValidationReport 校验报告
    """
    report = ValidationReport(total_rules=len(rules))
    valid_ids = {r.rule_id for r in rules}
    
    for rule in rules:
        # 检查必需字段
        if not rule.name:
            report.issues.append(ValidationIssue(
                code="E004",
                message=f"规则 {rule.rule_id} 缺少 name 字段",
                rule_id=rule.rule_id,
                suggestion="请为规则添加 name 字段",
                severity="error"
            ))
            report.passed = False
        
        if not rule.description:
            report.issues.append(ValidationIssue(
                code="E004",
                message=f"规则 {rule.rule_id} 缺少 description 字段",
                rule_id=rule.rule_id,
                suggestion="请为规则添加 description 字段",
                severity="warning"
            ))
        
        # 检查优先级
        if rule.priority not in ("high", "medium", "low"):
            report.issues.append(ValidationIssue(
                code="E006",
                message=f"规则 {rule.rule_id} 优先级非法: {rule.priority}",
                rule_id=rule.rule_id,
                suggestion="优先级应为 high/medium/low",
                severity="warning"
            ))
        
        # 检查命名规范（R + 3位数字）
        if not re.match(r"^R\d{3}$", rule.rule_id):
            report.issues.append(ValidationIssue(
                code="E006",
                message=f"规则 {rule.rule_id} 命名不符合规范",
                rule_id=rule.rule_id,
                suggestion="rule_id 格式应为 R001, R002, ... R999",
                severity="error"
            ))
            report.passed = False
        
        # 检查引用有效性
        for ref in rule.references:
            if ref not in valid_ids:
                report.issues.append(ValidationIssue(
                    code="E005",
                    message=f"规则 {rule.rule_id} 引用了不存在的规则: {ref}",
                    rule_id=rule.rule_id,
                    suggestion=f"请检查引用 {ref} 是否存在",
                    severity="error"
                ))
                report.passed = False
    
    return report


# ============================================================
# 转换模块
# ============================================================

def convert_to_skill(rules: List[RuleEntry], template: Optional[str] = None) -> str:
    """
    将规则集合转换为 Markdown 技能文档（SKILL.md 格式）。
    
    参数:
        rules: 规则条目列表
        template: 可选的自定义模板（含 {rules} 占位符）
    
    返回:
        生成的 SKILL.md 文档字符串
    """
    # 按优先级排序
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_rules = sorted(rules, key=lambda r: priority_order.get(r.priority, 99))
    
    # 生成规则列表部分
    rules_md = []
    for rule in sorted_rules:
        tags_str = ", ".join(rule.tags) if rule.tags else "无"
        applies_str = ", ".join(rule.applies_to) if rule.applies_to else "全部"
        refs_str = ", ".join(rule.references) if rule.references else "无"
        
        rule_md = "### " + rule.rule_id + ": " + rule.name + "\n\n"
        rule_md += "- **优先级**: " + rule.priority + "\n"
        rule_md += "- **标签**: " + tags_str + "\n"
        rule_md += "- **适用文件**: " + applies_str + "\n"
        rule_md += "- **引用规则**: " + refs_str + "\n\n"
        rule_md += "**描述**: " + rule.description + "\n"
        
        if rule.content:
            rule_md += "\n**内容**:\n" + rule.content + "\n"
        
        rules_md.append(rule_md)
    
    rules_section = "\n".join(rules_md)
    
    # 生成完整的 SKILL.md 文档
    if template:
        # 使用自定义模板
        return template.replace("{rules}", rules_section)
    
    # 默认模板
    skill_doc = "# Cursor 规则技能手册\n\n"
    skill_doc += "> 本手册由 cursor-handbook 工具自动生成\n\n"
    skill_doc += "## 规则总览\n\n"
    skill_doc += "共 " + str(len(rules)) + " 条规则\n\n"
    skill_doc += "## 规则详情\n\n"
    skill_doc += rules_section
    
    return skill_doc


# ============================================================
# 查询模块
# ============================================================

def query_rules(
    rules: List[RuleEntry],
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    priority: Optional[str] = None
) -> List[RuleEntry]:
    """
    根据条件查询规则。
    
    参数:
        rules: 规则列表
        keyword: 关键词（匹配名称或描述）
        tag: 场景标签
        priority: 优先级（high/medium/low）
    
    返回:
        匹配的规则列表
    """
    # E009: 查询条件为空
    if not keyword and not tag and not priority:
        raise RuntimeError("E009: 查询条件为空，至少提供一个查询条件")
    
    results = []
    for rule in rules:
        match = True
        
        if keyword:
            kw_lower = keyword.lower()
            if kw_lower not in rule.name.lower() and kw_lower not in rule.description.lower():
                match = False
        
        if match and tag:
            if tag not in rule.tags:
                match = False
        
        if match and priority:
            if rule.priority != priority:
                match = False
        
        if match:
            results.append(rule)
    
    return results


# ============================================================
# 执行辅助模块
# ============================================================

def build_steps(rules: List[RuleEntry]) -> List[Dict[str, Any]]:
    """
    根据规则生成操作步骤清单。
    
    参数:
        rules: 规则列表
    
    返回:
        步骤清单，每步包含 rule_id, action, details
    """
    steps = []
    
    for rule in rules:
        # 从规则描述中提取操作要点
        description = rule.description.lower()
        
        # 判断操作类型
        if "禁止" in description or "不要" in description:
            action = "避免"
        elif "必须" in description or "需要" in description:
            action = "执行"
        elif "建议" in description:
            action = "考虑"
        else:
            action = "检查"
        
        step = {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "action": action,
            "details": rule.description,
            "priority": rule.priority
        }
        steps.append(step)
    
    return steps


# ============================================================
# 输出模块
# ============================================================

def output_rules(rules: List[RuleEntry], output_format: str = "json") -> str:
    """
    将规则列表序列化为指定格式。
    
    参数:
        rules: 规则列表
        output_format: json / yaml / markdown
    
    返回:
        序列化后的字符串
    """
    if output_format == "json":
        return json.dumps([r.to_dict() for r in rules], ensure_ascii=False, indent=2)
    
    elif output_format == "yaml":
        # 简单的 YAML 生成（不依赖外部库）
        yaml_lines = []
        for rule in rules:
            yaml_lines.append(f"- rule_id: {rule.rule_id}")
            yaml_lines.append(f"  name: {rule.name}")
            yaml_lines.append(f"  description: {rule.description}")
            yaml_lines.append(f"  priority: {rule.priority}")
            yaml_lines.append(f"  tags: [{', '.join(rule.tags)}]")
            yaml_lines.append(f"  applies_to: [{', '.join(rule.applies_to)}]")
            yaml_lines.append(f"  references: [{', '.join(rule.references)}]")
            yaml_lines.append("")
        return "\n".join(yaml_lines)
    
    elif output_format == "markdown":
        return convert_to_skill(rules)
    
    else:
        raise RuntimeError(f"E008: 不支持的输出格式: {output_format}")


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行离线自检，验证各模块功能正常。
    
    返回:
        True 如果所有测试通过，否则 False
    """
    print("="*60)
    print("cursor-handbook 自检开始")
    print("="*60)
    
    all_passed = True
    
    # 1. 测试解析模块
    print("\n[1/6] 测试解析模块...")
    try:
        # 创建临时测试文件
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_rule.mdc"
            test_content = """---
id: R001
name: 测试规则
description: 这是一条用于测试的规则
priority: high
tags: [测试, 示例]
applies_to: [*.py, *.md]
references: [R002]
---
这是规则的具体内容描述。
"""
            if not dry_run or getattr(args, "force", False):
                test_file.write_text(test_content, encoding="utf-8")
            
            rule = parse_rule_file(str(test_file))
            assert rule.rule_id == "R001", "rule_id 解析失败"
            assert rule.name == "测试规则", "name 解析失败"
            assert rule.priority == "high", "priority 解析失败"
            assert "测试" in rule.tags, "tags 解析失败"
            assert "*.py" in rule.applies_to, "applies_to 解析失败"
            assert "R002" in rule.references, "references 解析失败"
            print("  ✓ 解析模块测试通过")
    except Exception as exc:
        print(f"  ✗ 解析模块测试失败: {exc}")
        all_passed = False
    
    # 2. 测试校验模块
    print("\n[2/6] 测试校验模块...")
    try:
        # 创建测试规则
        test_rules = [
            RuleEntry(
                rule_id="R001",
                name="测试规则1",
                description="描述1",
                priority="high",
                tags=["测试"],
                references=["R002"]
            ),
            RuleEntry(
                rule_id="R002",
                name="测试规则2",
                description="描述2",
                priority="medium",
                tags=["测试"],
                references=[]
            )
        ]
        
        report = validate_rules(test_rules)
        assert report.passed, "有效规则校验不应失败"
        assert report.total_rules == 2, "规则数量统计错误"
        print("  ✓ 校验模块测试通过")
    except Exception as exc:
        print(f"  ✗ 校验模块测试失败: {exc}")
        all_passed = False
    
    # 3. 测试转换模块
    print("\n[3/6] 测试转换模块...")
    try:
        test_rules = [
            RuleEntry(
                rule_id="R001",
                name="测试规则1",
                description="描述1",
                priority="high",
                tags=["测试"],
                content="内容1"
            )
        ]
        skill_md = convert_to_skill(test_rules)
        assert "R001" in skill_md, "转换结果缺少规则ID"
        assert "测试规则1" in skill_md, "转换结果缺少规则名称"
        assert "描述1" in skill_md, "转换结果缺少规则描述"
        print("  ✓ 转换模块测试通过")
    except Exception as exc:
        print(f"  ✗ 转换模块测试失败: {exc}")
        all_passed = False
    
    # 4. 测试查询模块
    print("\n[4/6] 测试查询模块...")
    try:
        test_rules = [
            RuleEntry(
                rule_id="R001",
                name="前端安全规则",
                description="确保前端代码安全",
                priority="high",
                tags=["前端", "安全"]
            ),
            RuleEntry(
                rule_id="R002",
                name="数据库优化规则",
                description="优化数据库查询性能",
                priority="medium",
                tags=["数据库", "性能"]
            )
        ]
        
        # 按关键词查询
        results = query_rules(test_rules, keyword="安全")
        assert len(results) == 1, "关键词查询失败"
        assert results[0].rule_id == "R001", "关键词查询结果错误"
        
        # 按标签查询
        results = query_rules(test_rules, tag="数据库")
        assert len(results) == 1, "标签查询失败"
        assert results[0].rule_id == "R002", "标签查询结果错误"
        
        # 按优先级查询
        results = query_rules(test_rules, priority="high")
        assert len(results) == 1, "优先级查询失败"
        
        print("  ✓ 查询模块测试通过")
    except Exception as exc:
        print(f"  ✗ 查询模块测试失败: {exc}")
        all_passed = False
    
    # 5. 测试执行辅助模块
    print("\n[5/6] 测试执行辅助模块...")
    try:
        test_rules = [
            RuleEntry(
                rule_id="R001",
                name="禁止使用eval",
                description="禁止在生产代码中使用eval函数",
                priority="high"
            ),
            RuleEntry(
                rule_id="R002",
                name="必须使用类型注解",
                description="所有函数必须添加类型注解",
                priority="medium"
            )
        ]
        
        steps = build_steps(test_rules)
        assert len(steps) == 2, "步骤数量错误"
        assert steps[0]["action"] == "避免", "禁止类规则动作判断错误"
        assert steps[1]["action"] == "执行", "必须类规则动作判断错误"
        print("  ✓ 执行辅助模块测试通过")
    except Exception as exc:
        print(f"  ✗ 执行辅助模块测试失败: {exc}")
        all_passed = False
    
    # 6. 测试输出模块
    print("\n[6/6] 测试输出模块...")
    try:
        test_rules = [
            RuleEntry(
                rule_id="R001",
                name="测试规则",
                description="测试描述",
                priority="high",
                tags=["测试"]
            )
        ]
        
        # JSON 输出
        json_output = output_rules(test_rules, "json")
        assert "R001" in json_output, "JSON输出失败"
        
        # Markdown 输出
        md_output = output_rules(test_rules, "markdown")
        assert "R001" in md_output, "Markdown输出失败"
        
        # YAML 输出
        yaml_output = output_rules(test_rules, "yaml")
        assert "R001" in yaml_output, "YAML输出失败"
        
        print("  ✓ 输出模块测试通过")
    except Exception as exc:
        print(f"  ✗ 输出模块测试失败: {exc}")
        all_passed = False
    
    # 汇总结果
    print("\n" + "="*60)
    if all_passed:
        print("自检通过：所有模块功能正常 ✓")
    else:
        print("自检失败：存在未通过的功能模块 ✗")
    print("="*60)
    
    return all_passed


# ============================================================
# 主程序
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="cursor-handbook: Cursor规则 结构化转换 技能手册",
        epilog="示例: python main.py rules/ --output output.md --format markdown"
    )
    
    parser.add_argument(
        "--input",
        nargs="?",
        help="规则文件或目录路径"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        help="输出文件路径"
    )
    
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "yaml", "markdown"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    
    parser.add_argument(
        "--query",
        "-q",
        help="查询关键词"
    )
    
    parser.add_argument(
        "--tag",
        help="按标签查询"
    )
    
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="按优先级查询"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="仅校验规则，不生成输出"
    )
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查是否提供了输入
    if not args.input:
        parser.print_help()
        sys.exit(1)
    
    try:
        # 解析规则
        input_path = Path(args.input)
        if input_path.is_dir():
            rules = parse_rule_directory(args.input)
        else:
            rules = [parse_rule_file(args.input)]
        
        if not rules:
            print("未找到有效的规则文件", file=sys.stderr)
            sys.exit(1)
        
        # 校验规则
        report = validate_rules(rules)
        
        if args.validate:
            # 仅输出校验报告
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
            sys.exit(0 if report.passed else 1)
        
        # 查询过滤
        if args.query or args.tag or args.priority:
            try:
                rules = query_rules(
                    rules,
                    keyword=args.query,
                    tag=args.tag,
                    priority=args.priority
                )
            except RuntimeError as exc:
                print(f"查询失败: {exc}", file=sys.stderr)
                sys.exit(1)
        
        # 生成输出
        output_content = output_rules(rules, args.format)
        
        # 输出到文件或标准输出
        if args.output:
            output_path = Path(args.output)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if not dry_run or getattr(args, "force", False):
                    output_path.write_text(output_content, encoding="utf-8")
                print(f"输出已写入: {output_path}")
            except Exception as exc:
                print(f"E007: 输出目录不可写: {output_path.parent} - {exc}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output_content)
        
        # 如果有警告，打印到 stderr
        if not report.passed:
            print("\n[警告] 存在规则校验问题:", file=sys.stderr)
            for issue in report.issues:
                if issue.severity == "warning":
                    print(f"  - {issue.message}", file=sys.stderr)
        
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"E010: 内部错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
