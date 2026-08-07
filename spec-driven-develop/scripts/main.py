#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec-driven-develop 独立实现脚本
================================
将需求规格转化为结构化开发计划与任务清单的流程型技能。

仅依据功能规格文档独立实现（clean-room），不参考任何既有代码。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空或格式无效",
    "E002": "输入超过处理上限（5000字或100个需求点）",
    "E003": "无法读取文件",
    "E004": "无法访问URL",
    "E005": "URL返回非文本内容",
    "E006": "JSON解析失败",
    "E007": "Markdown/纯文本解析失败",
    "E008": "任务拆解失败",
    "E009": "GitHub产物生成失败",
    "E010": "内部未知错误",
}


# ============================================================
# 数据结构定义
# ============================================================
@dataclass
class RequirementItem:
    """需求点"""
    content: str
    category: str = "功能"          # 功能/约束/验收标准
    confidence: str = "中"          # 高/中/低
    ambiguous: bool = False         # 是否模糊表述


@dataclass
class ModuleSuggestion:
    """模块划分建议"""
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskItem:
    """开发任务"""
    id: str
    title: str
    description: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    estimated_hours_min: float = 0.0
    estimated_hours_max: float = 0.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ADRSummary:
    """架构决策记录摘要"""
    decisions: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class GitHubIssueTemplate:
    """GitHub Issue 模板"""
    title: str
    labels: List[str] = field(default_factory=list)
    body: str = ""


@dataclass
class PRDescriptionTemplate:
    """PR 描述模板"""
    title: str = ""
    body: str = ""


@dataclass
class DevelopmentPlan:
    """完整开发计划"""
    requirements: List[RequirementItem] = field(default_factory=list)
    modules: List[ModuleSuggestion] = field(default_factory=list)
    tasks: List[TaskItem] = field(default_factory=list)
    adr: ADRSummary = field(default_factory=ADRSummary)
    issue_template: GitHubIssueTemplate = field(default_factory=GitHubIssueTemplate)
    pr_template: PRDescriptionTemplate = field(default_factory=PRDescriptionTemplate)


# ============================================================
# 核心处理类
# ============================================================
class SpecDrivenDeveloper:
    """规格驱动开发处理器"""
    
    MAX_CHARS = 5000
    MAX_REQUIREMENTS = 100
    
    def __init__(self):
        self.plan = DevelopmentPlan()
    
    # ---------- 输入处理 ----------
    def process_input(self, text: Optional[str] = None, 
                      file_path: Optional[str] = None,
                      url: Optional[str] = None) -> DevelopmentPlan:
        """处理输入：文本/文件/URL"""
        try:
            if text:
                content = text
            elif file_path:
                content = self._read_file(file_path)
            elif url:
                content = self._fetch_url(url)
            else:
                raise ValueError(ERROR_CODES["E001"])
            
            if not content or not content.strip():
                raise ValueError(ERROR_CODES["E001"])
            
            # 检查处理上限
            if len(content) > self.MAX_CHARS:
                raise ValueError(ERROR_CODES["E002"])
            
            # 解析需求
            self.plan.requirements = self._parse_requirements(content)
            if len(self.plan.requirements) > self.MAX_REQUIREMENTS:
                raise ValueError(ERROR_CODES["E002"])
            
            # 生成开发计划
            self._generate_plan()
            return self.plan
            
        except ValueError as e:
            code = str(e) if str(e) in ERROR_CODES.values() else ERROR_CODES["E010"]
            raise RuntimeError(f"{code}: {e}")
        except Exception as e:
            raise RuntimeError(f"{ERROR_CODES['E010']}: {str(e)}")
    
    def _read_file(self, path: str) -> str:
        """读取文件内容"""
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            
            ext = os.path.splitext(path)[1].lower()
            if ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 尝试提取文本字段
                if isinstance(data, dict):
                    if "requirements" in data:
                        return json.dumps(data["requirements"], ensure_ascii=False)
                    elif "text" in data:
                        return str(data["text"])
                    elif "content" in data:
                        return str(data["content"])
                    return json.dumps(data, ensure_ascii=False)
                return json.dumps(data, ensure_ascii=False)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except FileNotFoundError:
            raise ValueError(ERROR_CODES["E003"])
        except json.JSONDecodeError:
            raise ValueError(ERROR_CODES["E006"])
        except Exception:
            raise ValueError(ERROR_CODES["E003"])
    
    def _fetch_url(self, url: str) -> str:
        """获取URL内容"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text" not in content_type and "json" not in content_type and "markdown" not in content_type:
                    raise ValueError(ERROR_CODES["E005"])
                return resp.read().decode("utf-8", errors="replace")
        except ValueError as e:
            raise e
        except Exception:
            raise ValueError(ERROR_CODES["E004"])
    
    # ---------- 需求解析 ----------
    def _parse_requirements(self, content: str) -> List[RequirementItem]:
        """解析需求文本，提取功能点、约束、验收标准"""
        items: List[RequirementItem] = []
        
        try:
            # 按行分割
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            
            current_category = "功能"
            for line in lines:
                # 识别分类标题
                if re.match(r"^#{1,6}\s*", line):
                    title = re.sub(r"^#{1,6}\s*", "", line).strip()
                    if "约束" in title or "限制" in title:
                        current_category = "约束"
                    elif "验收" in title or "标准" in title:
                        current_category = "验收标准"
                    else:
                        current_category = "功能"
                    continue
                
                # 跳过非需求行（表格、引用、列表标记等）
                if line.startswith('|') or line.startswith('>') or line.startswith('-') or line.startswith('*') or line.startswith('
