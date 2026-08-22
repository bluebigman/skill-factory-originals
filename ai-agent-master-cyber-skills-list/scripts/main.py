#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能体技能编排：数据转换与结构化输出工具
=========================================
依据功能规格独立实现（clean-room），不依赖任何第三方库。
支持批量处理、置信度标注、自定义模板等核心能力。

用法示例：
    python scripts/main.py --input sample.csv --output result.json
    python scripts/main.py --text "张三 2024-01-01 100元" --format json
    python scripts/main.py --selftest
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "文件解析失败：格式不正确",
    "E004": "输入数据为空：没有可处理的内容",
    "E005": "模板渲染失败：模板格式错误",
    "E006": "输出写入失败：无法写入目标文件",
    "E007": "不支持的输入类型",
    "E008": "数据转换失败：无法提取有效字段",
    "E009": "批量处理失败：部分条目处理出错",
    "E010": "内部错误：未预期的异常",
}

# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class StructuredRecord:
    """单条结构化记录。"""

    def __init__(self, raw_text: str = "", fields: Optional[Dict[str, Any]] = None,
                 confidence: float = 1.0, needs_verification: Optional[List[str]] = None):
        self.raw_text = raw_text
        self.fields = fields if fields is not None else {}
        self.confidence = confidence
        self.needs_verification = needs_verification if needs_verification is not None else []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        result = {
            "raw": self.raw_text,
            "fields": self.fields,
            "confidence": self.confidence,
        }
        if self.needs_verification:
            result["needs_verification"] = self.needs_verification
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredRecord":
        """从字典创建实例。"""
        return cls(
            raw_text=data.get("raw", ""),
            fields=data.get("fields", {}),
            confidence=data.get("confidence", 1.0),
            needs_verification=data.get("needs_verification", []),
        )


class BatchResult:
    """批量处理结果。"""

    def __init__(self):
        self.records: List[StructuredRecord] = []
        self.errors: List[Dict[str, Any]] = []
        self.processed_count = 0
        self.failed_count = 0

    def add_record(self, record: StructuredRecord) -> None:
        """添加成功记录。"""
        self.records.append(record)
        self.processed_count += 1

    def add_error(self, error: Dict[str, Any]) -> None:
        """添加错误记录。"""
        self.errors.append(error)
        self.failed_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "records": [r.to_dict() for r in self.records],
            "errors": self.errors,
            "stats": {
                "processed": self.processed_count,
                "failed": self.failed_count,
                "total": self.processed_count + self.failed_count,
            },
        }

    @property
    def success_rate(self) -> float:
        """计算成功率。"""
        total = self.processed_count + self.failed_count
        if total == 0:
            return 0.0
        return self.processed_count / total


# ---------------------------------------------------------------------------
# 输入解析器
# ---------------------------------------------------------------------------

class InputParser:
    """解析各种格式的输入数据。"""

    # 常见日期格式
    DATE_PATTERNS = [
        r"\d{4}-\d{1,2}-\d{1,2}",       # 2024-01-01
        r"\d{4}/\d{1,2}/\d{1,2}",       # 2024/01/01
        r"\d{4}年\d{1,2}月\d{1,2}日",    # 2024年1月1日
        r"\d{1,2}-\d{1,2}-\d{4}",       # 01-01-2024
    ]

    # 常见金额格式
    MONEY_PATTERNS = [
        r"\d+(?:\.\d{1,2})?\s*(?:元|块|RMB|CNY|¥)",
        r"\$\s*\d+(?:\.\d{1,2})?",
        r"USD\s*\d+(?:\.\d{1,2})?",
    ]

    # 常见人名模式（中文）
    NAME_PATTERNS = [
        r"[\u4e00-\u9fa5]{2,4}(?=\s|$|，|。|,|\.)",
    ]

    @classmethod
    def parse_text(cls, text: str) -> StructuredRecord:
        """
        从纯文本中提取结构化信息。
        返回记录，包含提取的字段和置信度。
        """
        if not text or not text.strip():
            raise ValueError("E004: 输入文本为空")

        text = text.strip()
        fields: Dict[str, Any] = {}
        needs_verification: List[str] = []

        # 提取日期
        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                date_str = match.group()
                # 转换为标准格式
                try:
                    if "年" in date_str:
                        parts = re.findall(r"\d+", date_str)
                        if len(parts) == 3:
                            date_str = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif "/" in date_str:
                        parts = date_str.split("/")
                        if len(parts) == 3:
                            date_str = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif "-" in date_str and len(date_str.split("-")[0]) == 2:
                        # mm-dd-yyyy 格式
                        parts = date_str.split("-")
                        date_str = f"{parts[2]}-{int(parts[0]):02d}-{int(parts[1]):02d}"
                    fields["date"] = date_str
                except (ValueError, IndexError):
                    needs_verification.append("date")
                break

        # 提取金额
        for pattern in cls.MONEY_PATTERNS:
            match = re.search(pattern, text)
            if match:
                money_str = match.group()
                # 提取数字部分
                num_match = re.search(r"\d+(?:\.\d{1,2})?", money_str)
                if num_match:
                    fields["amount"] = float(num_match.group())
                    # 判断货币类型
                    if "$" in money_str or "USD" in money_str.upper():
                        fields["currency"] = "USD"
                    elif "¥" in money_str or "RMB" in money_str.upper() or "CNY" in money_str.upper():
                        fields["currency"] = "CNY"
                    else:
                        fields["currency"] = "CNY"
                break

        # 提取人名（中文）
        name_match = re.search(cls.NAME_PATTERNS[0], text)
        if name_match:
            name = name_match.group().strip("，。,.")
            # 过滤掉常见非名字词汇
            if len(name) >= 2 and not any(kw in name for kw in ["数据", "信息", "内容", "结果"]):
                fields["name"] = name

        # 提取状态标记
        status_keywords = {
            "成功": "success",
            "失败": "failed",
            "进行中": "in_progress",
            "已完成": "completed",
            "待处理": "pending",
        }
        for keyword, status in status_keywords.items():
            if keyword in text:
                fields["status"] = status
                break

        # 计算置信度
        confidence = 0.5  # 基础置信度
        has_fields = len(fields)
        if has_fields >= 3:
            confidence = 0.9
        elif has_fields >= 2:
            confidence = 0.75
        elif has_fields >= 1:
            confidence = 0.6

        # 如果存在可能需要核实的字段
        if needs_verification:
            confidence = min(confidence, 0.5)

        return StructuredRecord(
            raw_text=text,
            fields=fields,
            confidence=confidence,
            needs_verification=needs_verification,
        )

    @classmethod
    def parse_csv(cls, file_path: str) -> List[StructuredRecord]:
        """解析 CSV 文件为结构化记录列表。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002: 文件不存在")

        records: List[StructuredRecord] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                for row in reader:
                    # 将 CSV 行转换为结构化记录
                    fields = {}
                    for header in headers:
                        if header and row.get(header):
                            fields[header.strip()] = row[header].strip()
                    if fields:
                        records.append(StructuredRecord(
                            raw_text=str(row),
                            fields=fields,
                            confidence=0.9,
                        ))
        except csv.Error as e:
            raise ValueError(f"E003: CSV 解析失败 - {e}")
        except Exception as e:
            raise ValueError(f"E003: 文件读取失败 - {e}")

        return records

    @classmethod
    def parse_json(cls, file_path: str) -> List[StructuredRecord]:
        """解析 JSON 文件为结构化记录列表。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError("E002: 文件不存在")

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            records: List[StructuredRecord] = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        records.append(StructuredRecord(
                            raw_text=json.dumps(item, ensure_ascii=False),
                            fields=item,
                            confidence=0.95,
                        ))
            elif isinstance(data, dict):
                records.append(StructuredRecord(
                    raw_text=json.dumps(data, ensure_ascii=False),
                    fields=data,
                    confidence=0.95,
                ))
            return records
        except json.JSONDecodeError as e:
            raise ValueError(f"E003: JSON 解析失败 - {e}")
        except Exception as e:
            raise ValueError(f"E003: 文件读取失败 - {e}")


# ---------------------------------------------------------------------------
# 模板渲染器
# ---------------------------------------------------------------------------

class TemplateRenderer:
    """渲染自定义输出模板。"""

    @staticmethod
    def render(template: str, record: StructuredRecord) -> str:
        """
        使用记录数据渲染模板。
        支持 {field_name} 占位符和简单条件。
        """
        if not template:
            return json.dumps(record.to_dict(), ensure_ascii=False, indent=2)

        result = template
        # 替换字段占位符
        for key, value in record.fields.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # 替换特殊占位符
        result = result.replace("{raw}", record.raw_text)
        result = result.replace("{confidence}", f"{record.confidence:.2f}")

        # 处理需要核实的字段标记
        if record.needs_verification:
            for field in record.needs_verification:
                result = result.replace(
                    "{" + field + "}",
                    f"[需核实:{field}]"
                )

        # 移除未替换的占位符
        result = re.sub(r"\{[^}]+\}", "[需核实]", result)

        return result


# ---------------------------------------------------------------------------
# 技能编排引擎
# ---------------------------------------------------------------------------

class SkillRegistry:
    """技能注册表：管理可用技能的注册、发现和调用。"""
    
    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, description: str, handler: Callable, 
                 tags: Optional[List[str]] = None) -> None:
        """注册一个技能。"""
        with self._lock:
            self._skills[name] = {
                "name": name,
                "description": description,
                "handler": handler,
                "tags": tags or [],
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息。"""
        with self._lock:
            return self._skills.get(name)
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有已注册技能。"""
        with self._lock:
            return [
                {k: v for k, v in skill.items() if k != "handler"}
                for skill in self._skills.values()
            ]
    
    def invoke(self, name: str, *args, **kwargs) -> Any:
        """调用技能。"""
        skill = self.get(name)
        if not skill:
            raise KeyError(f"技能未注册: {name}")
        return skill["handler"](*args, **kwargs)


class SkillChain:
    """技能调用链：支持技能串联执行。"""
    
    def __init__(self):
        self._chain: List[Dict[str, Any]] = []
    
    def add_step(self, skill_name: str, params: Optional[Dict[str, Any]] = None) -> None:
        """添加一个执行步骤。"""
        self._chain.append({
            "skill": skill_name,
            "params": params or {},
        })
    
    def execute(self, registry: SkillRegistry, initial_input: Any = None) -> List[Any]:
        """执行整个调用链。"""
        results = []
        current_input = initial_input
        
        for step in self._chain:
            skill = registry.get(step["skill"])
            if not skill:
                raise KeyError(f"技能未注册: {step['skill']}")
            
            # 合并参数
            params = dict(step["params"])
            if current_input is not None:
                params["input"] = current_input
            
            # 执行技能
            current_input = skill["handler"](**params)
            results.append(current_input)
        
        return results


class ContextRouter:
    """上下文路由器：根据输入内容路由到合适的技能。"""
    
    def __init__(self):
        self._routes: List[Dict[str, Any]] = []
    
    def add_route(self, pattern: str, skill_name: str, priority: int = 0) -> None:
        """添加路由规则。"""
        self._routes.append({
            "pattern": re.compile(pattern),
            "skill": skill_name,
            "priority": priority,
        })
        # 按优先级排序
        self._routes.sort(key=lambda x: x["priority"], reverse=True)
    
    def route(self, text: str) -> Optional[str]:
        """根据输入文本路由到技能。"""
        for route in self._routes:
            if route["pattern"].search(text):
                return route["skill"]
        return None


# ---------------------------------------------------------------------------
# 核心处理引擎
# ---------------------------------------------------------------------------

class DataProcessor:
    """核心数据处理引擎。"""

    def __init__(self, template: str = "", max_workers: Optional[int] = None):
        self.template = template
        self.renderer = TemplateRenderer()
        # 设置最大并发数，默认使用 CPU 核心数，但限制最大为 8
        self.max_workers = max(1, min(max_workers if max_workers is not None else (os.cpu_count() or 4), 8))
        self._cache: Dict[str, StructuredRecord] = {}
        self._cache_lock = threading.Lock()  # 线程安全缓存
        self._output_lock = threading.Lock()  # 输出写入锁
        
        # 初始化技能编排组件
        self.registry = SkillRegistry()
        self.router = ContextRouter()
        self._init_skills()
    
    def _init_skills(self) -> None:
        """初始化内置技能。"""
        # 注册文本解析技能
        self.registry.register(
            name="text_parser",
            description="解析纯文本为结构化数据",
            handler=self._skill_text_parse,
            tags=["text", "parse", "extract"],
        )
        
        # 注册CSV解析技能
        self.registry.register(
            name="csv_parser",
            description="解析CSV文件为结构化数据",
            handler=self._skill_csv_parse,
            tags=["csv", "parse", "file"],
        )
        
        # 注册JSON解析技能
        self.registry.register(
            name="json_parser",
            description="解析JSON文件为结构化数据",
            handler=self._skill_json_parse,
            tags=["json", "parse", "file"],
        )
        
        # 注册模板渲染技能
        self.registry.register(
            name="template_renderer",
            description="使用模板渲染输出",
            handler=self._skill_template_render,
            tags=["template", "render", "output"],
        )
        
        # 注册数据验证技能
        self.registry.register(
            name="data_validator",
            description="验证数据完整性",
            handler=self._skill_data_validate,
            tags=["validate", "check", "quality"],
        )
        
        # 设置路由规则
        self
