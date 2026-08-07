#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lanshu-awesome-ai-video-kit - 企业视频制作智能工具包

独立实现脚本（clean-room implementation），仅依据功能规格编写。
提供数据解析、批量转换、置信度标注等核心能力。

用法:
    python scripts/main.py --selftest    # 离线自检核心逻辑
    python scripts/main.py --help        # 查看帮助
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "无效的命令行参数",
    "E002": "输入数据为空或格式错误",
    "E003": "输入条目数量超过最大限制(20)",
    "E004": "不支持的输入文件类型",
    "E005": "无法读取输入文件",
    "E006": "output_schema 格式无效",
    "E007": "JSON 序列化失败",
    "E008": "内部处理逻辑错误",
    "E009": "URL 格式无效",
    "E010": "自检断言失败",
}

# 核心常量
MAX_BATCH_SIZE = 20  # 最大批量处理条数
DEFAULT_CONFIDENCE = "高"  # 默认置信度等级
SUPPORTED_EXTENSIONS = {".txt", ".csv", ".json", ".md"}  # 支持的文本文件类型


@dataclass
class ProcessingResult:
    """单条数据处理结果"""

    original: str
    structured: Dict[str, Any]
    confidence: Dict[str, str]
    notes: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class BatchResult:
    """批量处理汇总结果"""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[ProcessingResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class VideoDataProcessor:
    """企业AI视频数据处理核心处理器"""

    # 需要完整保留的关键信息类型
    KEY_PATTERNS = {
        "url": re.compile(r"https?://[^\s]+", re.IGNORECASE),
        "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
        "phone": re.compile(r"(\+?\d{1,3}[- ]?)?\(?\d{2,4}\)?[- ]?\d{3,4}[- ]?\d{4}"),
        "date": re.compile(r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?"),
        "currency": re.compile(r"[¥￥$€]\s?\d+(\.\d{2})?"),
        "percentage": re.compile(r"\d+(\.\d+)?%"),
    }

    # 常见项目角色关键词
    ROLE_KEYWORDS = ["导演", "制片人", "剪辑", "摄影", "编剧", "美术", "音效", "特效", "灯光", "场记"]

    # 常见优先级关键词
    PRIORITY_KEYWORDS = {
        "高": ["紧急", "加急", "立即", "尽快", "urgent", "asap", "high"],
        "中": ["正常", "标准", "普通", "normal", "medium"],
        "低": ["低", "不着急", "可以等", "low", "later"],
    }

    def __init__(self) -> None:
        """初始化处理器"""
        self.reset()

    def reset(self) -> None:
        """重置处理器状态"""
        self._current_schema: Dict[str, Any] = {}
        self._batch_mode: bool = False

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def process_text(self, text: str, output_schema: Optional[Dict] = None) -> ProcessingResult:
        """处理单条文本数据

        Args:
            text: 原始文本输入
            output_schema: 自定义输出字段结构

        Returns:
            ProcessingResult: 处理结果
        """
        if not text or not text.strip():
            raise ValueError(f"E002: {ERROR_CODES['E002']}")

        self._current_schema = output_schema or {}
        structured = self._extract_entities(text)
        confidence = self._calculate_confidence(text, structured)
        notes = self._generate_notes(text, structured, confidence)

        return ProcessingResult(
            original=text,
            structured=structured,
            confidence=confidence,
            notes=notes,
            success=True,
        )

    def process_batch(self, items: List[str], output_schema: Optional[Dict] = None) -> BatchResult:
        """批量处理多条数据

        Args:
            items: 文本条目列表
            output_schema: 自定义输出字段结构

        Returns:
            BatchResult: 批量处理结果
        """
        if not items:
            raise ValueError(f"E002: {ERROR_CODES['E002']}")

        if len(items) > MAX_BATCH_SIZE:
            raise ValueError(f"E003: {ERROR_CODES['E003']} (最大{MAX_BATCH_SIZE}条)")

        self._batch_mode = True
        batch = BatchResult(total=len(items))

        for item in items:
            try:
                result = self.process_text(item, output_schema)
                batch.results.append(result)
                batch.succeeded += 1
            except Exception as exc:
                # 单条失败不影响整体批次
                batch.results.append(
                    ProcessingResult(
                        original=item,
                        structured={},
                        confidence={},
                        notes=[f"处理失败: {str(exc)}"],
                        success=False,
                    )
                )
                batch.failed += 1

        self._batch_mode = False
        return batch

    def process_file(self, file_path: str, output_schema: Optional[Dict] = None) -> BatchResult:
        """处理本地文件

        Args:
            file_path: 文件路径
            output_schema: 自定义输出字段结构

        Returns:
            BatchResult: 批量处理结果
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"E005: {ERROR_CODES['E005']}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"E004: {ERROR_CODES['E004']} (支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))})")

        try:
            items = self._read_file_content(file_path, ext)
        except Exception as exc:
            raise IOError(f"E005: {ERROR_CODES['E005']}: {str(exc)}") from exc

        return self.process_batch(items, output_schema)

    def process_url(self, url: str, output_schema: Optional[Dict] = None) -> ProcessingResult:
        """处理公开URL内容（仅做格式校验，不实际访问网络）

        Args:
            url: 公开可访问的URL
            output_schema: 自定义输出字段结构

        Returns:
            ProcessingResult: 处理结果
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"E009: {ERROR_CODES['E009']}")

        # 注意：根据规格说明，本工具包不访问需登录的网页
        # 这里仅将URL作为文本进行结构化处理
        return self.process_text(f"URL: {url}", output_schema)

    def to_markdown(self, result: ProcessingResult) -> str:
        """将处理结果转换为Markdown表格

        Args:
            result: 单条处理结果

        Returns:
            str: Markdown格式文本
        """
        lines = ["| 字段 | 值 | 置信度 |", "|------|-----|--------|"]

        for key, value in result.structured.items():
            conf = result.confidence.get(key, DEFAULT_CONFIDENCE)
            lines.append(f"| {key} | {value} | {conf} |")

        if result.notes:
            lines.append("")
            lines.append("**备注:**")
            for note in result.notes:
                lines.append(f"- {note}")

        return "\n".join(lines)

    def to_json(self, result: ProcessingResult) -> str:
        """将处理结果转换为JSON字符串

        Args:
            result: 单条处理结果

        Returns:
            str: JSON格式文本
        """
        try:
            return json.dumps(
                {
                    "success": result.success,
                    "structured": result.structured,
                    "confidence": result.confidence,
                    "notes": result.notes,
                },
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"E007: {ERROR_CODES['E007']}") from exc

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """从文本中提取结构化实体

        Args:
            text: 原始文本

        Returns:
            Dict: 结构化字段字典
        """
        entities: Dict[str, Any] = {}

        # 1. 提取项目名称（常见模式：项目/方案/计划等关键词前的内容）
        project_match = re.search(
            r"(.{2,20}?)(?:项目|方案|计划|企划|制作|拍摄)",
            text,
        )
        if project_match:
            entities["project_name"] = project_match.group(1).strip()

        # 2. 提取关键信息（URL、日期、金额等）
        for key, pattern in self.KEY_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                entities[key] = matches[0] if len(matches) == 1 else list(matches)

        # 3. 提取角色信息
        roles = []
        for role in self.ROLE_KEYWORDS:
            if role in text:
                roles.append(role)
        if roles:
            entities["roles"] = roles

        # 4. 提取预算信息
        budget_match = re.search(r"(?:预算|经费|投入)[：:\s]*([¥￥$€]?\s?\d[\d,]*(?:\.\d{2})?)", text)
        if budget_match:
            entities["budget"] = budget_match.group(1).strip()

        # 5. 提取时间节点
        timeline = []
        for date_match in self.KEY_PATTERNS["date"].finditer(text):
            timeline.append(date_match.group())
        if timeline:
            entities["timeline"] = timeline

        # 6. 提取素材路径（常见文件路径模式）
        path_match = re.search(r"(?:素材|文件|路径)[：:\s]*([/\\][\w./\\-]+)", text)
        if path_match:
            entities["asset_path"] = path_match.group(1).strip()

        # 7. 提取优先级
        priority = self._detect_priority(text)
        if priority:
            entities["priority"] = priority

        # 8. 如果没有提取到任何内容，保留原文摘要
        if not entities:
            entities["summary"] = text[:100] + ("..." if len(text) > 100 else "")

        # 9. 如果指定了output_schema，按schema组织输出
        if self._current_schema:
            entities = self._apply_schema(entities, text)

        return entities

    def _apply_schema(self, entities: Dict[str, Any], text: str) -> Dict[str, Any]:
        """按自定义schema组织输出字段

        Args:
            entities: 已提取的实体
            text: 原始文本

        Returns:
            Dict: 按schema组织的字段
        """
        schema_result: Dict[str, Any] = {}

        # 支持简单schema定义: {"field1": "描述", "field2": "描述"}
        for field_name, field_desc in self._current_schema.items():
            if isinstance(field_name, str):
                # 尝试从已提取实体中匹配
                matched = False
                for key, value in entities.items():
                    if key.lower() in field_name.lower() or field_name.lower() in key.lower():
                        schema_result[field_name] = value
                        matched = True
                        break

                # 尝试从原文中提取
                if not matched and isinstance(field_desc, str):
                    pattern = re.compile(f"{field_desc}[:：]\\s*(.+)")
                    match = pattern.search(text)
                    if match:
                        schema_result[field_name] = match.group(1).strip()
                    else:
                        schema_result[field_name] = f"[需核实:{field_name}]"

        return schema_result

    def _calculate_confidence(self, text: str, entities: Dict[str, Any]) -> Dict[str, str]:
        """计算各字段的置信度

        Args:
            text: 原始文本
            entities: 已提取的实体

        Returns:
            Dict: 字段对应的置信度等级
        """
        confidence: Dict[str, str] = {}
        text_length = len(text)

        for key in entities.keys():
            # 基于提取方式判断置信度
            if key in ("url", "email", "phone", "date", "currency", "percentage"):
                # 精确模式匹配，置信度高
                confidence[key] = "高"
            elif key in ("project_name", "roles"):
                # 关键词匹配，置信度中
                confidence[key] = "中"
            elif key in ("budget", "timeline", "asset_path"):
                # 上下文相关，置信度中
                confidence[key] = "中"
            elif key == "priority":
                # 优先级推断，置信度中
                confidence[key] = "中"
            elif key == "summary":
                # 摘要生成，置信度低
                confidence[key] = "低"
            else:
                # 其他情况基于文本长度判断
                if text_length > 200:
                    confidence[key] = "中"
                else:
                    confidence[key] = "低"

            # 对以[需核实]开头的字段标记为低置信度
            if isinstance(entities[key], str) and entities[key].startswith("[需核实"):
                confidence[key] = "低"

        return confidence

    def _generate_notes(self, text: str, entities: Dict[str, Any], confidence: Dict[str, str]) -> List[str]:
        """生成处理备注

        Args:
            text: 原始文本
            entities: 已提取的实体
            confidence: 置信度信息

        Returns:
            List[str]: 备注列表
        """
        notes = []

        # 低置信度字段提醒
        low_conf_fields = [k for k, v in confidence.items() if v == "低"]
        if low_conf_fields:
            notes.append(f"以下字段置信度较低，建议人工核实: {', '.join(low_conf_fields)}")

        # 缺失关键信息提醒
        if "project_name" not in entities:
            notes.append("未识别到明确的项目名称")
        if "timeline" not in entities:
            notes.append("未识别到明确的时间节点")

        # 数据质量问题
        if len(text) < 20:
            notes.append("输入文本过短，可能影响提取效果")
        elif len(text) > 500:
            notes.append("输入文本较长，已截取关键信息")

        # 标记需核实的字段
        for key, value in entities.items():
            if isinstance(value, str) and value.startswith("[需核实"):
                notes.append(f"字段 '{key}' 在原文中未找到明确信息，已标记为需核实")

        return notes

    def _detect_priority(self, text: str) -> Optional[str]:
        """检测优先级

        Args:
            text: 原始文本

        Returns:
            Optional[str]: 优先级等级或None
        """
        text_lower = text.lower()
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return priority
        return None

    def _read_file_content(self, file_path: str, ext: str) -> List[str]:
        """读取文件内容并转换为文本条目列表

        Args:
            file_path: 文件路径
            ext: 文件扩展名

        Returns:
            List[str]: 文本条目列表
        """
        items: List[str] = []

        if ext == ".txt" or ext == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 按空行或换行分段
            items = [line.strip() for line in content.splitlines() if line.strip()]

        elif ext == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        items.append(" | ".join(cell.strip() for cell in row if cell.strip()))

        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        items.append(item)
                    elif isinstance(item, dict):
                        items.append(json.dumps(item, ensure_ascii=False))
            elif isinstance(data, dict):
                items.append(json.dumps(data, ensure_ascii=False))

        return items

    def export_batch_report(self, batch: BatchResult, format_type: str = "markdown") -> str:
        """导出批量处理报告

        Args:
            batch: 批量处理结果
            format_type: 输出格式 (markdown/json)

        Returns:
            str: 格式化报告
        """
        if format_type == "json":
            report = {
                "timestamp": batch.timestamp,
                "total": batch.total,
                "succeeded": batch.succeeded,
                "failed": batch.failed,
                "results": [
                    {
                        "success": r.success,
                        "structured": r.structured,
                        "confidence": r.confidence,
                        "notes": r.notes,
                    }
                    for r in batch.results
                ],
            }
            return json.dumps(report, ensure_ascii=False, indent=2)

        # 默认Markdown格式
        lines = [
            f"# 批量处理报告",
            f"",
            f"- **处理时间**: {batch.timestamp}",
            f"- **总条目**: {batch.total}",
            f"- **成功**: {batch.succeeded}",
            f"- **失败**: {batch.failed}",
            f"",
            f"## 处理详情",
            f"",
        ]

        for i, result in enumerate(batch.results, 1):
            lines.append(f"### 条目 {i}")
            lines.append("")
            lines.append(self.to_markdown(result))
            lines.append("")

        return "\n".join(lines)


# ----------------------------------------------------------------------
# 命令行接口
# ----------------------------------------------------------------------
def run_selftest() -> int:
    """运行内置自检

    使用硬编码样例数据离线验证核心逻辑，
    不依赖外部文件、网络或特定工作目录。

    Returns:
        int: 0表示通过，非0表示失败
    """
    print("=" * 60)
    print("lanshu-awesome-ai-video-kit 自检程序")
    print("=" * 60)

    try:
        processor = VideoDataProcessor()

        # ---- 测试用例1: 单条文本处理 ----
        print("\n[测试1] 单条文本处理")
        sample_text = (
            "企业宣传片项目制作计划，预算¥50000，"
            "导演张伟，制片人李娜，预计2026年3月15日前完成。"
            "素材路径: /assets/videos/promo/raw"
        )
        try:
            result = processor.process_text(sample_text)
            assert result.success, "处理结果应为成功"
            assert result.structured, "应提取到结构化字段"
            assert result.confidence, "应生成置信度标注"
            print(f"  ✓ 成功提取 {len(result.structured)} 个字段")
            for key, value in result.structured.items():
                conf = result.confidence.get(key, "未知")
                print(f"    - {key}: {value} (置信度: {conf})")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 处理异常: {exc}")
            return 1

        # ---- 测试用例2: 批量处理 ----
        print("\n[测试2] 批量处理")
        sample_items = [
            "短视频项目A，预算¥10000，剪辑师王五",
            "纪录片项目B，紧急，导演赵六，2026年5月",
            "动画项目C，素材路径: /data/animation/raw",
        ]
        try:
            batch = processor.process_batch(sample_items)
            assert batch.total == 3, "总条数应为3"
            assert batch.succeeded == 3, "全部应成功"
            assert batch.failed == 0, "不应有失败"
            print(f"  ✓ 批量处理成功: {batch.succeeded}/{batch.total}")
        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 处理异常: {exc}")
            return 1

        # ---- 测试用例3: 边界处理 ----
        print("\n[测试3] 边界处理")
        try:
            # 空输入
            try:
                processor.process_text("")
                print("  ✗ 空输入应报错")
                return 1
            except ValueError:
                print("  ✓ 空输入正确报错")

            # 超过批次限制
            too_many = [f"项目{i}" for i in range(21)]
            try:
                processor.process_batch(too_many)
                print("  ✗ 超过20条应报错")
                return 1
            except ValueError:
                print("  ✓ 批次限制正确报错")

            # 无效URL
            try:
                processor.process_url("not-a-url")
                print("  ✗ 无效URL应报错")
                return 1
            except ValueError:
                print("  ✓ 无效URL正确报错")

        except Exception as exc:
            print(f"  ✗ 边界测试异常: {exc}")
            return 1

        # ---- 测试用例4: 输出格式 ----
        print("\n[测试4] 输出格式")
        try:
            sample = "测试项目，预算¥9999，2026年1月"
            result = processor.process_text(sample)

            md = processor.to_markdown(result)
            assert "|" in md, "Markdown应包含表格"
            assert "置信度" in md, "Markdown应包含置信度列"
            print("  ✓ Markdown格式正确")

            js = processor.to_json(result)
            json_data = json.loads(js)
            assert "structured" in json_data, "JSON应包含structured字段"
            assert "confidence" in json_data, "JSON应包含confidence字段"
            print("  ✓ JSON格式正确")

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 格式测试异常: {exc}")
            return 1

        # ---- 测试用例5: 自定义Schema ----
        print("\n[测试5] 自定义Schema")
        try:
            schema = {
                "项目名称": "项目",
                "预算金额": "预算",
                "截止日期": "日期",
            }
            sample = "新产品发布项目，预算¥20000，截止日期2026年12月30日"
            result = processor.process_text(sample, schema)

            assert "项目名称" in result.structured, "应包含自定义字段"
            assert "预算金额" in result.structured, "应包含自定义字段"
            assert "截止日期" in result.structured, "应包含自定义字段"
            print("  ✓ 自定义Schema生效")
            for key, value in result.structured.items():
                print(f"    - {key}: {value}")

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ Schema测试异常: {exc}")
            return 1

        # ---- 测试用例6: 错误处理 ----
        print("\n[测试6] 错误处理")
        try:
            # 不存在的文件
            try:
                processor.process_file("/nonexistent/file.txt")
                print("  ✗ 不存在的文件应报错")
                return 1
            except (FileNotFoundError, IOError):
                print("  ✓ 文件不存在正确报错")

            # 不支持的文件类型
            with tempfile.NamedTemporaryFile(suffix=".exe", delete=True) as tmp:
                try:
                    processor.process_file(tmp.name)
                    print("  ✗ 不支持的文件类型应报错")
                    return 1
                except ValueError:
                    print("  ✓ 不支持的文件类型正确报错")

        except Exception as exc:
            print(f"  ✗ 错误处理测试异常: {exc}")
            return 1

        # ---- 测试用例7: 关键信息保留 ----
        print("\n[测试7] 关键信息保留")
        try:
            sample = "项目联系邮箱: contact@example.com，电话: 138-1234-5678"
            result = processor.process_text(sample)

            # 验证邮箱和电话被保留
            structured_str = str(result.structured)
            assert "contact@example.com" in structured_str, "邮箱应被保留"
            assert "138-1234-5678" in structured_str, "电话应被保留"
            print("  ✓ 关键信息完整保留")

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 关键信息测试异常: {exc}")
            return 1

        # ---- 测试用例8: 置信度标注 ----
        print("\n[测试8] 置信度标注")
        try:
            sample = "简单项目"
            result = processor.process_text(sample)

            # 短文本应产生低置信度或备注
            has_low_conf = any(v == "低" for v in result.confidence.values())
            has_note = len(result.notes) > 0
            assert has_low_conf or has_note, "短文本应有低置信度或备注"
            print("  ✓ 置信度标注正常")

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 置信度测试异常: {exc}")
            return 1

        # ---- 测试用例9: 批量报告导出 ----
        print("\n[测试9] 批量报告导出")
        try:
            sample_items = ["项目A", "项目B，紧急"]
            batch = processor.process_batch(sample_items)

            report = processor.export_batch_report(batch, "markdown")
            assert "批量处理报告" in report, "报告应包含标题"
            assert "项目A" in report or "条目" in report, "报告应包含条目信息"
            print("  ✓ Markdown报告导出正常")

            report_json = processor.export_batch_report(batch, "json")
            json_data = json.loads(report_json)
            assert json_data["total"] == 2, "JSON报告应包含总数"
            print("  ✓ JSON报告导出正常")

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 报告测试异常: {exc}")
            return 1

        # ---- 测试用例10: 文件处理 ----
        print("\n[测试10] 文件处理")
        try:
            # 使用临时文件测试
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8", delete=False) as tmp:
                tmp.write("项目A\n项目B\n项目C，紧急")
                tmp_path = tmp.name

            try:
                batch = processor.process_file(tmp_path)
                assert batch.total == 3, "应处理3行"
                assert batch.succeeded == 3, "全部应成功"
                print("  ✓ 文件处理正常")
            finally:
                os.unlink(tmp_path)

        except AssertionError as exc:
            print(f"  ✗ 断言失败: {exc}")
            return 1
        except Exception as exc:
            print(f"  ✗ 文件测试异常: {exc}")
            return 1

        # ---- 全部通过 ----
        print("\n" + "=" * 60)
        print("✅ 所有自检测试通过!")
        print("=" * 60)
        return 0

    except Exception as exc:
        print(f"\n❌ 自检过程中发生未预期异常: {exc}")
        return 1


def main() -> int:
    """主入口函数

    Returns:
        int: 退出码
    """
    parser = argparse.ArgumentParser(
        description="企业视频制作智能工具包 - 数据解析、批量转换与置信度标注",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部依赖）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="处理本地文件（支持.txt/.csv/.json/.md）",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="处理单条文本",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文本（用分号;分隔多条）",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="处理URL（仅校验格式，不访问网络）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认: markdown）",
    )
    parser.add_argument(
        "--schema",
        type=str,
        help="自定义输出Schema（JSON格式字符串）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    try:
        processor = VideoDataProcessor()

        # 解析自定义Schema
        schema = None
        if args.schema:
            try:
                schema = json.loads(args.schema)
                if not isinstance(schema, dict):
                    print(f"错误 E006: {ERROR_CODES['E006']}")
                    return 1
            except json.JSONDecodeError:
                print(f"错误 E006: {ERROR_CODES['E006']}")
                return 1

        # 处理文件
        if args.file:
            try:
                batch = processor.process_file(args.file, schema)
                print(processor.export_batch_report(batch, args.format))
                return 0
            except (FileNotFoundError, IOError, ValueError) as exc:
                print(f"错误: {exc}")
                return 1

        # 处理URL
        if args.url:
            try:
                result = processor.process_url(args.url, schema)
                if args.format == "json":
                    print(processor.to_json(result))
                else:
                    print(processor.to_markdown(result))
                return 0
            except ValueError as exc:
                print(f"错误: {exc}")
                return 1

        # 处理批量文本
        if args.batch:
            try:
                items = [item.strip() for item in args.batch.split(";") if item.strip()]
                batch = processor.process_batch(items, schema)
                print(processor.export_batch_report(batch, args.format))
                return 0
            except ValueError as exc:
                print(f"错误: {exc}")
                return 1

        # 处理单条文本
        if args.text:
            try:
                result = processor.process_text(args.text, schema)
                if args.format == "json":
                    print(processor.to_json(result))
                else:
                    print(processor.to_markdown(result))
                return 0
            except ValueError as exc:
                print(f"错误: {exc}")
                return 1

        # 未指定操作
        print("请指定操作: --selftest / --file / --text / --batch / --url")
        print("使用 --help 查看帮助")
        return 1

    except Exception as exc:
        print(f"错误 E008: {ERROR_CODES['E008']}: {str(exc)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
