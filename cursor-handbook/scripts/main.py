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
        
        rules_md.append(f"""
### {rule.rule_id}: {rule.name}

- **优先级**: {rule.priority}
- **标签**: {tags_str}
- **适用文件**: {applies_str}
- **引用规则**: {refs_str}

**描述**: {rule.description}
