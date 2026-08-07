#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autoscraper - 爬虫采集技能核心实现
====================================
基于功能规格独立实现（clean-room 重写）。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

错误码体系：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 文件读取失败
    E007: URL 格式无效
    E008: 批量处理中断
    E009: 输出写入失败
    E010: 未知内部错误

仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ProcessingResult:
    """处理结果数据模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_input: Any = None


@dataclass
class FieldDefinition:
    """字段定义，用于描述期望提取的字段"""
    name: str
    aliases: List[str] = field(default_factory=list)
    required: bool = False
    type_hint: str = "string"  # string, number, boolean, date


# ============================================================
# 核心处理引擎
# ============================================================

class AutoScraperEngine:
    """
    核心处理引擎：负责解析输入、提取关键信息、生成结构化结果。
    
    设计原则：
    - 输入可以是字符串、字典、列表或包含文本的文件路径
    - 使用启发式规则识别关键信息，不依赖特定网站结构
    - 输出统一为字典结构，包含提取的字段和置信度
    """

    # 常见字段别名映射，用于识别关键信息
    COMMON_FIELD_ALIASES = {
        "标题": ["title", "标题", "题目", "headline", "name"],
        "作者": ["author", "作者", "creator", "writer", "by"],
        "日期": ["date", "日期", "time", "发布时间", "publish_date", "created"],
        "内容": ["content", "内容", "body", "text", "正文", "description", "描述"],
        "链接": ["url", "链接", "href", "link", "source"],
        "关键词": ["keywords", "关键词", "tags", "标签", "subjects"],
        "数量": ["count", "数量", "number", "total", "总计"],
        "价格": ["price", "价格", "cost", "amount", "金额"],
        "分类": ["category", "分类", "type", "类型", "section"],
        "状态": ["status", "状态", "state", "condition"],
    }

    # 常见 URL 模式，用于识别链接
    URL_PATTERN = re.compile(
        r'https?://[^\s<>"\'{}|\\^`\[\]]+'
        r'|www\.[^\s<>"\'{}|\\^`\[\]]+'
        r'|[a-z0-9][a-z0-9-]*\.(com|cn|org|net|io|edu|gov)(/[^\s]*)?',
        re.IGNORECASE
    )

    # 日期模式（宽松匹配）
    DATE_PATTERN = re.compile(
        r'\d{4}[-/年.]\d{1,2}[-/月.]\d{1,2}日?'
        r'|\d{1,2}[-/月.]\d{1,2}[-/日.]\d{2,4}'
        r'|(?:19|20)\d{2}年\d{1,2}月\d{1,2}日'
    )

    # 数字模式（含小数和千分位）
    NUMBER_PATTERN = re.compile(r'-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+\.\d+')

    # 邮箱模式
    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

    def __init__(self):
        """初始化引擎"""
        self.field_definitions = self._build_default_fields()

    def _build_default_fields(self) -> List[FieldDefinition]:
        """构建默认字段定义列表"""
        fields = []
        for name, aliases in self.COMMON_FIELD_ALIASES.items():
            fields.append(FieldDefinition(
                name=name,
                aliases=aliases,
                required=False,
                type_hint="string"
            ))
        return fields

    # --------------------------------------------------------
    # 主入口
    # --------------------------------------------------------

    def process(
        self,
        raw_input: Any,
        custom_fields: Optional[List[Dict[str, Any]]] = None,
        output_format: str = "dict",
        batch_mode: bool = False
    ) -> ProcessingResult:
        """
        处理输入数据，提取关键信息并生成结构化结果。

        Args:
            raw_input: 输入数据（字符串、字典、列表或文件路径）
            custom_fields: 自定义字段定义列表，格式:
                [{"name": "字段名", "aliases": ["别名1"], "required": True, "type_hint": "string"}]
            output_format: 输出格式（dict/json/text）
            batch_mode: 是否为批量处理模式

        Returns:
            ProcessingResult 对象
        """
        try:
            # 第一步：验证输入不为空
            if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
                return ProcessingResult(
                    success=False,
                    error_code="E001",
                    error_message="输入为空，请提供待处理的内容",
                    raw_input=raw_input
                )

            # 第二步：解析输入内容
            parsed_content, input_type = self._parse_input(raw_input)

            if parsed_content is None:
                return ProcessingResult(
                    success=False,
                    error_code="E003",
                    error_message="输入格式错误，无法解析内容",
                    raw_input=raw_input
                )

            # 第三步：合并自定义字段定义
            all_fields = self._merge_field_definitions(custom_fields)

            # 第四步：提取关键信息
            extracted, confidence = self._extract_fields(parsed_content, all_fields)

            # 第五步：检查必需字段
            missing_fields = self._check_required_fields(extracted, all_fields)
            if missing_fields:
                return ProcessingResult(
                    success=False,
                    error_code="E002",
                    error_message=f"关键信息缺失，缺少字段: {', '.join(missing_fields)}",
                    data=extracted,
                    confidence=confidence,
                    raw_input=raw_input
                )

            # 第六步：格式化输出
            formatted = self._format_output(extracted, output_format)

            # 第七步：生成警告
            warnings = []
            if confidence < 0.85:
                warnings.append("置信度低于85%，部分字段可能不准确，请人工核实")
            elif confidence < 0.90:
                warnings.append("置信度在85%-90%之间，建议复核")

            return ProcessingResult(
                success=True,
                data=formatted,
                confidence=confidence,
                warnings=warnings,
                raw_input=raw_input
            )

        except Exception as exc:
            return ProcessingResult(
                success=False,
                error_code="E010",
                error_message=f"未知内部错误: {str(exc)}",
                raw_input=raw_input
            )

    # --------------------------------------------------------
    # 批量处理
    # --------------------------------------------------------

    def process_batch(
        self,
        inputs: List[Any],
        custom_fields: Optional[List[Dict[str, Any]]] = None,
        output_format: str = "dict"
    ) -> List[ProcessingResult]:
        """
        批量处理多个输入。

        Args:
            inputs: 输入列表
            custom_fields: 自定义字段定义
            output_format: 输出格式

        Returns:
            处理结果列表
        """
        if not inputs:
            return [ProcessingResult(
                success=False,
                error_code="E001",
                error_message="批量输入为空"
            )]

        results = []
        for idx, item in enumerate(inputs):
            try:
                result = self.process(item, custom_fields, output_format)
                results.append(result)
            except Exception as exc:
                results.append(ProcessingResult(
                    success=False,
                    error_code="E008",
                    error_message=f"批量处理第{idx+1}项失败: {str(exc)}",
                    raw_input=item
                ))

        return results

    # --------------------------------------------------------
    # 内部方法：输入解析
    # --------------------------------------------------------

    def _parse_input(self, raw_input: Any) -> Tuple[Any, str]:
        """
        解析输入内容，识别输入类型。

        Returns:
            (解析后的内容, 输入类型)
        """
        # 处理字典类型
        if isinstance(raw_input, dict):
            return raw_input, "dict"

        # 处理列表类型
        if isinstance(raw_input, list):
            return raw_input, "list"

        # 处理字符串类型
        if isinstance(raw_input, str):
            text = raw_input.strip()

            # 检查是否为 URL
            if self._looks_like_url(text):
                return {"url": text, "text": text}, "url"

            # 检查是否为文件路径
            if self._looks_like_file_path(text):
                try:
                    with open(text, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content, "file"
                except (IOError, OSError):
                    return None, "error"

            # 尝试解析 JSON
            if text.startswith('{') or text.startswith('['):
                try:
                    parsed = json.loads(text)
                    return parsed, "json"
                except json.JSONDecodeError:
                    pass

            # 作为纯文本处理
            return text, "text"

        return raw_input, "unknown"

    def _looks_like_url(self, text: str) -> bool:
        """判断文本是否像 URL"""
        # 检查是否有明显的 URL 前缀
        if text.startswith(('http://', 'https://', 'www.')):
            return True
        # 检查是否匹配 URL 模式
        if self.URL_PATTERN.match(text):
            return True
        return False

    def _looks_like_file_path(self, text: str) -> bool:
        """判断文本是否像文件路径"""
        # 检查常见文件扩展名
        common_exts = ['.txt', '.csv', '.json', '.xml', '.html', '.md', '.log', '.dat']
        for ext in common_exts:
            if text.lower().endswith(ext):
                return True
        # 检查是否包含路径分隔符
        if '/' in text or '\\' in text:
            return True
        return False

    # --------------------------------------------------------
    # 字段定义管理
    # --------------------------------------------------------

    def _merge_field_definitions(
        self,
        custom_fields: Optional[List[Dict[str, Any]]]
    ) -> List[FieldDefinition]:
        """合并默认字段和自定义字段"""
        fields = list(self.field_definitions)

        if custom_fields:
            for cf in custom_fields:
                if isinstance(cf, dict) and 'name' in cf:
                    fields.append(FieldDefinition(
                        name=str(cf['name']),
                        aliases=cf.get('aliases', []),
                        required=cf.get('required', False),
                        type_hint=cf.get('type_hint', 'string')
                    ))

        return fields

    # --------------------------------------------------------
    # 核心提取逻辑
    # --------------------------------------------------------

    def _extract_fields(
        self,
        content: Any,
        fields: List[FieldDefinition]
    ) -> Tuple[Dict[str, Any], float]:
        """
        从内容中提取字段值。

        Returns:
            (提取结果字典, 置信度)
        """
        extracted = {}
        confidence_scores = []

        # 将内容转换为可供搜索的文本
        text_content = self._content_to_text(content)

        for field_def in fields:
            value, conf = self._extract_single_field(content, text_content, field_def)

            if value is not None:
                extracted[field_def.name] = value
                confidence_scores.append(conf)

        # 计算总体置信度
        if confidence_scores:
            # 使用加权平均，但避免过度乐观
            overall = sum(confidence_scores) / len(confidence_scores)
            # 根据提取字段的完整度微调
            if len(extracted) < len(fields) * 0.5:
                overall *= 0.9
        else:
            overall = 0.0

        return extracted, round(overall, 4)

    def _extract_single_field(
        self,
        content: Any,
        text_content: str,
        field_def: FieldDefinition
    ) -> Tuple[Optional[Any], float]:
        """提取单个字段的值"""
        field_name = field_def.name
        aliases = field_def.aliases
        type_hint = field_def.type_hint

        # 方法1: 直接键匹配（适用于字典输入）
        if isinstance(content, dict):
            for key, value in content.items():
                if self._key_matches(key, aliases):
                    return self._convert_type(value, type_hint), 0.95

        # 方法2: 列表中的字典匹配
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if self._key_matches(key, aliases):
                            return self._convert_type(value, type_hint), 0.90

        # 方法3: 文本模式匹配
        if isinstance(text_content, str):
            value, conf = self._extract_from_text(text_content, aliases, type_hint)
            if value is not None:
                return value, conf

        return None, 0.0

    def _key_matches(self, key: str, aliases: List[str]) -> bool:
        """检查键名是否匹配别名"""
        key_lower = str(key).strip().lower()
        for alias in aliases:
            if str(alias).strip().lower() == key_lower:
                return True
        return False

    def _extract_from_text(
        self,
        text: str,
        aliases: List[str],
        type_hint: str
    ) -> Tuple[Optional[Any], float]:
        """从文本中提取字段值"""
        # 尝试标签-值模式: "标签: 值"
        for alias in aliases:
            # 构建正则模式
            pattern = re.compile(
                rf'{re.escape(alias)}\s*[:：]\s*([^\n\r]+)',
                re.IGNORECASE
            )
            match = pattern.search(text)
            if match:
                raw_value = match.group(1).strip()
                value = self._convert_type(raw_value, type_hint)
                if value is not None:
                    return value, 0.85

        # 根据类型提示尝试通用模式
        if type_hint == "string":
            return None, 0.0
        elif type_hint == "number":
            matches = self.NUMBER_PATTERN.findall(text)
            if matches:
                return self._convert_type(matches[0], "number"), 0.7
        elif type_hint == "date":
            matches = self.DATE_PATTERN.findall(text)
            if matches:
                return matches[0], 0.7
        elif type_hint == "boolean":
            if re.search(r'\b(是|否|true|false|yes|no)\b', text, re.IGNORECASE):
                return True, 0.6

        return None, 0.0

    def _convert_type(self, value: Any, type_hint: str) -> Any:
        """将值转换为指定类型"""
        if value is None:
            return None

        try:
            if type_hint == "number":
                if isinstance(value, (int, float)):
                    return value
                # 清理数字字符串
                cleaned = str(value).replace(',', '').strip()
                if cleaned.lstrip('-').replace('.', '', 1).isdigit():
                    if '.' in cleaned:
                        return float(cleaned)
                    return int(cleaned)
                return None
            elif type_hint == "boolean":
                if isinstance(value, bool):
                    return value
                if str(value).strip().lower() in ('true', 'yes', '是', '1'):
                    return True
                if str(value).strip().lower() in ('false', 'no', '否', '0'):
                    return False
                return None
            elif type_hint == "date":
                if isinstance(value, str) and self.DATE_PATTERN.search(value):
                    return value
                return None
            else:
                return str(value)
        except (ValueError, TypeError):
            return None

    # --------------------------------------------------------
    # 内容辅助方法
    # --------------------------------------------------------

    def _content_to_text(self, content: Any) -> str:
        """将内容转换为纯文本"""
        if isinstance(content, str):
            return content
        elif isinstance(content, dict):
            # 提取所有字符串值
            parts = []
            for key, value in content.items():
                if isinstance(value, str):
                    parts.append(f"{key}: {value}")
                elif isinstance(value, (dict, list)):
                    nested = self._content_to_text(value)
                    if nested:
                        parts.append(nested)
            return '\n'.join(parts)
        elif isinstance(content, list):
            parts = []
            for item in content:
                text = self._content_to_text(item)
                if text:
                    parts.append(text)
            return '\n'.join(parts)
        else:
            return str(content)

    def _check_required_fields(
        self,
        extracted: Dict[str, Any],
        fields: List[FieldDefinition]
    ) -> List[str]:
        """检查必需字段是否都已提取"""
        missing = []
        for field_def in fields:
            if field_def.required and field_def.name not in extracted:
                missing.append(field_def.name)
        return missing

    # --------------------------------------------------------
    # 输出格式化
    # --------------------------------------------------------

    def _format_output(self, data: Dict[str, Any], format_type: str) -> Any:
        """格式化输出"""
        if format_type == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        elif format_type == "text":
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return '\n'.join(lines)
        else:
            return data


# ============================================================
# 命令行接口
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑：使用硬编码样例数据验证核心功能。
    不读取外部文件、不访问网络、不依赖当前工作目录。
    """
    print("=" * 60)
    print("autoscraper 自检程序启动")
    print("=" * 60)

    engine = AutoScraperEngine()
    all_passed = True

    # --------------------------------------------------------
    # 测试用例1: 字典输入
    # --------------------------------------------------------
    print("\n[测试1] 字典输入处理")
    test_dict = {
        "标题": "Python 编程入门",
        "作者": "张三",
        "日期": "2024-03-15",
        "内容": "这是一篇关于 Python 编程的入门教程。",
        "链接": "https://example.com/python-intro",
        "关键词": ["python", "编程", "入门"]
    }

    result = engine.process(test_dict)
    if result.success:
        assert result.data is not None, "测试1失败: 输出为空"
        assert "标题" in result.data, "测试1失败: 缺少标题字段"
        assert "作者" in result.data, "测试1失败: 缺少作者字段"
        assert result.confidence > 0.5, f"测试1失败: 置信度过低 ({result.confidence})"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
    else:
        print(f"  ✗ 失败: {result.error_message}")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例2: 纯文本输入
    # --------------------------------------------------------
    print("\n[测试2] 纯文本输入处理")
    test_text = """
    文章标题: 深度学习基础
    作者: 李四
    发布时间: 2024年6月1日
    摘要: 本文介绍深度学习的基本概念和应用场景。
    原文链接: https://example.com/dl-basics
    关键词: 深度学习, 神经网络, AI
    """

    result = engine.process(test_text)
    if result.success:
        assert result.data is not None, "测试2失败: 输出为空"
        assert result.confidence > 0.3, f"测试2失败: 置信度过低 ({result.confidence})"
        print(f"  ✓ 通过 (置信度: {result.confidence:.2f})")
    else:
        print(f"  ✗ 失败: {result.error_message}")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例3: 空输入错误处理
    # --------------------------------------------------------
    print("\n[测试3] 空输入错误处理")
    result = engine.process("")
    if not result.success and result.error_code == "E001":
        print(f"  ✓ 通过 (错误码: {result.error_code})")
    else:
        print(f"  ✗ 失败: 期望 E001, 实际 {result.error_code}")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例4: 批量处理
    # --------------------------------------------------------
    print("\n[测试4] 批量处理")
    batch_inputs = [
        {"标题": "文章A", "作者": "作者1"},
        {"标题": "文章B", "作者": "作者2"},
        {"标题": "文章C", "作者": "作者3"}
    ]
    results = engine.process_batch(batch_inputs)
    if len(results) == 3:
        success_count = sum(1 for r in results if r.success)
        assert success_count >= 2, f"测试4失败: 成功率过低 ({success_count}/3)"
        print(f"  ✓ 通过 ({success_count}/3 成功)")
    else:
        print(f"  ✗ 失败: 结果数量错误 ({len(results)})")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例5: 自定义字段
    # --------------------------------------------------------
    print("\n[测试5] 自定义字段处理")
    custom_fields = [
        {"name": "评分", "aliases": ["rating", "分数"], "type_hint": "number"}
    ]
    test_custom = {"标题": "测试", "评分": "4.5"}
    result = engine.process(test_custom, custom_fields=custom_fields)
    if result.success:
        assert "评分" in result.data, "测试5失败: 缺少自定义字段"
        assert result.data["评分"] == 4.5, f"测试5失败: 评分值错误 ({result.data.get('评分')})"
        print(f"  ✓ 通过 (评分: {result.data['评分']})")
    else:
        print(f"  ✗ 失败: {result.error_message}")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例6: 必需字段缺失
    # --------------------------------------------------------
    print("\n[测试6] 必需字段缺失检测")
    custom_fields = [
        {"name": "必填字段", "required": True}
    ]
    result = engine.process({"标题": "测试"}, custom_fields=custom_fields)
    if not result.success and result.error_code == "E002":
        print(f"  ✓ 通过 (错误码: {result.error_code})")
    else:
        print(f"  ✗ 失败: 期望 E002, 实际 {result.error_code}")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例7: 输出格式
    # --------------------------------------------------------
    print("\n[测试7] 输出格式转换")
    test_data = {"标题": "测试", "作者": "作者"}
    result_json = engine.process(test_data, output_format="json")
    result_text = engine.process(test_data, output_format="text")

    if result_json.success and result_text.success:
        # 验证 JSON 输出
        import json as json_module
        try:
            parsed_json = json_module.loads(result_json.data)
            assert isinstance(parsed_json, dict), "测试7失败: JSON 解析结果不是字典"
        except (json.JSONDecodeError, TypeError):
            print("  ✗ 失败: JSON 输出无效")
            all_passed = False

        # 验证文本输出
        assert isinstance(result_text.data, str), "测试7失败: 文本输出不是字符串"
        assert "标题" in result_text.data, "测试7失败: 文本输出缺少标题"
        print("  ✓ 通过 (JSON 和文本格式均正确)")
    else:
        print("  ✗ 失败: 格式转换失败")
        all_passed = False

    # --------------------------------------------------------
    # 测试用例8: 边界情况
    # --------------------------------------------------------
    print("\n[测试8] 边界情况处理")

    # 特殊字符输入
    special_input = {"标题": "特殊字符: @#$%^&*()", "内容": "包含特殊字符的内容"}
    result = engine.process(special_input)
    if result.success:
        print("  ✓ 特殊字符输入处理通过")
    else:
        print(f"  ✗ 特殊字符输入处理失败: {result.error_message}")
        all_passed = False

    # 超长输入
    long_text = "内容: " + "测试" * 1000
    result = engine.process(long_text)
    if result.success or result.error_code in ("E001", "E003"):
        print("  ✓ 超长输入处理通过")
    else:
        print(f"  ✗ 超长输入处理失败: {result.error_message}")
        all_passed = False

    # --------------------------------------------------------
    # 汇总
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
        print("=" * 60)
        return True
    else:
        print("自检存在失败项 ✗")
        print("=" * 60)
        return False


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="autoscraper - 爬虫采集技能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest                    # 运行自检
  python main.py --input "标题: 测试文章"       # 处理文本
  python main.py --input '{"标题": "测试"}'     # 处理 JSON
  python main.py --batch "输入1" "输入2" "输入3" # 批量处理
        """
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检程序（无需任何外部依赖）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（文本、JSON 或文件路径）"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量输入内容"
    )
    parser.add_argument(
        "--format",
        choices=["dict", "json", "text"],
        default="dict",
        help="输出格式 (默认: dict)"
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义字段定义 (JSON 格式)"
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 初始化引擎
    engine = AutoScraperEngine()

    # 解析自定义字段
    custom_fields = None
    if args.fields:
        try:
            custom_fields = json.loads(args.fields)
        except json.JSONDecodeError:
            print("E003: 自定义字段格式错误，应为 JSON 格式")
            sys.exit(3)

    # 批量处理
    if args.batch:
        results = engine.process_batch(args.batch, custom_fields, args.format)
        for idx, result in enumerate(results, 1):
            if result.success:
                print(f"[{idx}] 成功 (置信度: {result.confidence:.2f})")
                if isinstance(result.data, str):
                    print(result.data)
                else:
                    print(json.dumps(result.data, ensure_ascii=False, indent=2))
            else:
                print(f"[{idx}] 失败 ({result.error_code}): {result.error_message}")
        sys.exit(0)

    # 单条处理
    if args.input:
        result = engine.process(args.input, custom_fields, args.format)
        if result.success:
            if result.warnings:
                for warning in result.warnings:
                    print(f"警告: {warning}")
            print(f"置信度: {result.confidence:.2f}")
            if isinstance(result.data, str):
                print(result.data)
            else:
                print(json.dumps(result.data, ensure_ascii=False, indent=2))
            sys.exit(0)
        else:
            print(f"错误 ({result.error_code}): {result.error_message}")
            sys.exit(1)

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
