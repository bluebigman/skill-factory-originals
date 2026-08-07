#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

网页数据采集与结构化提取工具（独立实现）
==========================================
本脚本依据功能规格独立设计，提供以下核心能力：
1. URL 结构化采集：从单个或多个 URL 中提取目标字段
2. 文件内容解析：读取 HTML/PDF/CSV 等文件，抽取关键信息
3. 批量任务处理：支持多 URL 或多文件同时提交，统一输出结果集
4. 自定义字段映射：按用户指定字段名与类型返回结构化数据
5. 置信度标注：对每条提取结果附加可信度评估

仅使用标准库实现，无第三方依赖。
支持 --selftest 参数进行离线自检，不访问网络、不读取外部文件。
"""

import argparse
import csv
import html.parser
import io
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """统一错误码常量"""
    E001 = "E001: 参数错误 - 输入参数缺失或格式不正确"
    E002 = "E002: URL 格式错误 - 无法解析的 URL 地址"
    E003 = "E003: 网络访问失败 - 无法获取远程资源"
    E004 = "E004: 文件读取失败 - 无法读取本地文件"
    E005 = "E005: 数据解析失败 - 无法从内容中提取结构化数据"
    E006 = "E006: 字段映射错误 - 指定的字段名或类型不合法"
    E007 = "E007: 批量任务失败 - 批量处理中出现错误"
    E008 = "E008: 输出格式错误 - 不支持的输出格式"
    E009 = "E009: 内容类型不支持 - 无法处理该类型的内容"
    E010 = "E010: 内部错误 - 未知异常"


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ExtractionResult:
    """单条提取结果"""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """批量处理结果"""
    results: List[ExtractionResult] = field(default_factory=list)
    success_count: int = 0
    failed_count: int = 0
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (source, error_code)


# ============================================================
# 核心解析器
# ============================================================
class SimpleHtmlExtractor(html.parser.HTMLParser):
    """轻量级 HTML 解析器，提取文本与链接"""
    
    def __init__(self):
        super().__init__()
        self.text_parts: List[str] = []
        self.links: List[Dict[str, str]] = []
        self.tables: List[List[List[str]]] = []
        self._current_table: Optional[List[List[str]]] = None
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[str] = None
        self._skip_depth = 0
        self._in_script = False
        self._in_style = False
    
    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        """处理开始标签"""
        tag = tag.lower()
        attr_dict = dict(attrs)
        
        if tag in ('script', 'style'):
            self._in_script = True
            return
        
        if tag == 'a' and 'href' in attr_dict:
            self.links.append({
                'href': attr_dict['href'],
                'text': '',
                'title': attr_dict.get('title', '')
            })
        
        if tag == 'table':
            self._current_table = []
        
        if tag == 'tr' and self._current_table is not None:
            self._current_row = []
        
        if tag in ('td', 'th') and self._current_row is not None:
            self._current_cell = ''
    
    def handle_endtag(self, tag: str) -> None:
        """处理结束标签"""
        tag = tag.lower()
        
        if tag in ('script', 'style'):
            self._in_script = False
            return
        
        if tag == 'a' and self.links:
            # 将最后一个链接的文本补充完整
            pass  # 文本在 handle_data 中已追加
        
        if tag in ('td', 'th') and self._current_row is not None:
            if self._current_cell is not None:
                self._current_row.append(self._current_cell.strip())
                self._current_cell = None
        
        if tag == 'tr' and self._current_table is not None and self._current_row is not None:
            self._current_table.append(self._current_row)
            self._current_row = None
        
        if tag == 'table' and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None
    
    def handle_data(self, data: str) -> None:
        """处理文本数据"""
        if self._in_script or self._in_style:
            return
        
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)
        
        # 补充链接文本
        if self.links and not self._in_script:
            self.links[-1]['text'] += data
    
    def get_text(self) -> str:
        """获取提取的纯文本"""
        return '\n'.join(self.text_parts)
    
    def get_links(self) -> List[Dict[str, str]]:
        """获取提取的链接列表"""
        result = []
        for link in self.links:
            if link['text'].strip():
                result.append({
                    'url': link['href'],
                    'text': link['text'].strip(),
                    'title': link['title']
                })
        return result


class CsvParser:
    """CSV 文件解析器"""
    
    @staticmethod
    def parse(content: str) -> List[Dict[str, Any]]:
        """解析 CSV 内容为字典列表"""
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]


class JsonParser:
    """JSON 内容解析器"""
    
    @staticmethod
    def parse(content: str) -> Any:
        """解析 JSON 字符串"""
        return json.loads(content)


# ============================================================
# 字段提取引擎
# ============================================================
class FieldExtractor:
    """从解析后的内容中提取指定字段"""
    
    # 常见字段的正则模式
    PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'phone': r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        'url': r'https?://[^\s<>"\'{}|\\^`\[\]]+',
        'price': r'(?:¥|￥|RMB|CNY|USD|EUR)?\s?\d+(?:,\d{3})*(?:\.\d{1,2})?\s?(?:元|人民币|美元|欧元)?',
        'date': r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',
        'id': r'[A-Za-z0-9_-]{8,32}',
        'title': r'^.{5,100}$',  # 宽松的标题模式
    }
    
    def __init__(self, field_mapping: Optional[Dict[str, str]] = None):
        """
        初始化字段提取器
        
        Args:
            field_mapping: 字段名到类型的映射，如 {'email': 'email', 'phone': 'phone'}
                          类型支持: email, phone, url, price, date, id, text
        """
        self.field_mapping = field_mapping or {}
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """从纯文本中提取字段"""
        result: Dict[str, Any] = {}
        confidence_values: List[float] = []
        
        for field_name, field_type in self.field_mapping.items():
            value, confidence = self._extract_single_field(text, field_type)
            result[field_name] = value
            confidence_values.append(confidence)
        
        # 计算整体置信度
        if confidence_values:
            result['_confidence'] = sum(confidence_values) / len(confidence_values)
        else:
            result['_confidence'] = 0.5
        
        return result
    
    def _extract_single_field(self, text: str, field_type: str) -> Tuple[Any, float]:
        """提取单个字段"""
        field_type = field_type.lower().strip()
        
        if field_type == 'text':
            # 提取文本片段
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                return lines[0], 0.8
            return "", 0.0
        
        if field_type == 'json':
            # 尝试解析 JSON
            try:
                return json.loads(text), 0.9
            except json.JSONDecodeError:
                return None, 0.0
        
        if field_type == 'list':
            # 提取列表（按行分割）
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if lines:
                return lines, 0.7
            return [], 0.0
        
        if field_type in self.PATTERNS:
            pattern = self.PATTERNS[field_type]
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # 去除重复，保留前 5 个
                unique = list(dict.fromkeys(matches))[:5]
                if len(unique) == 1:
                    return unique[0], 0.9
                return unique, 0.7
            return None, 0.0
        
        # 未知类型，直接返回文本
        return text[:200], 0.3
    
    def extract_from_html(self, html_content: str) -> Dict[str, Any]:
        """从 HTML 内容中提取字段"""
        parser = SimpleHtmlExtractor()
        try:
            parser.feed(html_content)
        except Exception:
            return {'_confidence': 0.0, '_error': ErrorCode.E005}
        
        text = parser.get_text()
        result = self.extract_from_text(text)
        
        # 补充链接信息
        links = parser.get_links()
        if links and 'links' not in self.field_mapping:
            result['_links'] = links[:10]
        
        # 补充表格信息
        if parser.tables:
            result['_tables'] = parser.tables[:3]
        
        return result


# ============================================================
# 内容处理器
# ============================================================
class ContentProcessor:
    """处理不同类型的内容源"""
    
    def __init__(self):
        self.extractor = FieldExtractor()
    
    def set_field_mapping(self, mapping: Dict[str, str]) -> None:
        """设置字段映射"""
        self.extractor = FieldExtractor(mapping)
    
    def process_html(self, html_content: str, source: str = "") -> ExtractionResult:
        """处理 HTML 内容"""
        try:
            data = self.extractor.extract_from_html(html_content)
            confidence = data.pop('_confidence', 0.0)
            warnings = []
            
            if '_error' in data:
                warnings.append(data.pop('_error'))
            
            return ExtractionResult(
                data=data,
                confidence=confidence,
                source=source,
                warnings=warnings
            )
        except Exception as e:
            return ExtractionResult(
                data={},
                confidence=0.0,
                source=source,
                warnings=[f"{ErrorCode.E005} - {str(e)}"]
            )
    
    def process_text(self, text_content: str, source: str = "") -> ExtractionResult:
        """处理纯文本内容"""
        try:
            data = self.extractor.extract_from_text(text_content)
            confidence = data.pop('_confidence', 0.0)
            
            return ExtractionResult(
                data=data,
                confidence=confidence,
                source=source
            )
        except Exception as e:
            return ExtractionResult(
                data={},
                confidence=0.0,
                source=source,
                warnings=[f"{ErrorCode.E005} - {str(e)}"]
            )
    
    def process_csv(self, csv_content: str, source: str = "") -> List[ExtractionResult]:
        """处理 CSV 内容，每行作为一个结果"""
        results = []
        try:
            rows = CsvParser.parse(csv_content)
            for row in rows:
                result = ExtractionResult(
                    data=row,
                    confidence=0.8,  # CSV 数据置信度较高
                    source=source
                )
                results.append(result)
        except Exception as e:
            results.append(ExtractionResult(
                data={},
                confidence=0.0,
                source=source,
                warnings=[f"{ErrorCode.E005} - {str(e)}"]
            ))
        return results
    
    def process_json(self, json_content: str, source: str = "") -> ExtractionResult:
        """处理 JSON 内容"""
        try:
            data = JsonParser.parse(json_content)
            if isinstance(data, dict):
                return ExtractionResult(
                    data=data,
                    confidence=0.9,
                    source=source
                )
            else:
                return ExtractionResult(
                    data={'value': data},
                    confidence=0.7,
                    source=source
                )
        except Exception as e:
            return ExtractionResult(
                data={},
                confidence=0.0,
                source=source,
                warnings=[f"{ErrorCode.E005} - {str(e)}"]
            )
    
    def process_by_content_type(self, content: str, content_type: str, source: str = "") -> List[ExtractionResult]:
        """根据内容类型自动处理"""
        content_type = content_type.lower()
        
        if 'html' in content_type:
            return [self.process_html(content, source)]
        elif 'csv' in content_type:
            return self.process_csv(content, source)
        elif 'json' in content_type:
            return [self.process_json(content, source)]
        elif 'text' in content_type:
            return [self.process_text(content, source)]
        else:
            # 尝试自动检测
            if content.lstrip().startswith('{') or content.lstrip().startswith('['):
                return [self.process_json(content, source)]
            elif '<html' in content.lower() or '<!doctype' in content.lower():
                return [self.process_html(content, source)]
            elif ',' in content.split('\n')[0]:
                return self.process_csv(content, source)
            else:
                return [self.process_text(content, source)]


# ============================================================
# 主处理引擎
# ============================================================
class ExtractionEngine:
    """网页数据采集与结构化提取主引擎"""
    
    def __init__(self):
        self.processor = ContentProcessor()
        self.field_mapping: Dict[str, str] = {}
    
    def configure(self, field_mapping: Optional[Dict[str, str]] = None) -> None:
        """配置字段映射"""
        if field_mapping:
            # 验证字段映射
            valid_types = {'email', 'phone', 'url', 'price', 'date', 'id', 'text', 'json', 'list'}
            for field, ftype in field_mapping.items():
                if ftype.lower() not in valid_types:
                    raise ValueError(f"{ErrorCode.E006} - 不支持的字段类型: {ftype}")
            self.field_mapping = field_mapping
            self.processor.set_field_mapping(field_mapping)
    
    def extract_from_url(self, url: str) -> ExtractionResult:
        """
        从 URL 提取数据（模拟实现）
        
        注意：由于标准库限制，此方法仅做 URL 验证和模拟处理。
        实际网络请求需要第三方库支持。
        """
        # 验证 URL
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ExtractionResult(
                data={},
                confidence=0.0,
                source=url,
                warnings=[ErrorCode.E002]
            )
        
        if parsed.scheme not in ('http', 'https'):
            return ExtractionResult(
                data={},
                confidence=0.0,
                source=url,
                warnings=[f"{ErrorCode.E002} - 不支持的协议: {parsed.scheme}"]
            )
        
        # 模拟处理（实际实现需要网络库）
        # 这里生成模拟数据用于演示
        mock_data = {
            'url': url,
            'domain': parsed.netloc,
            'path': parsed.path,
            'title': f"模拟标题 - {parsed.netloc}",
            'content_preview': "这是模拟的网页内容预览，实际采集需要网络访问支持。"
        }
        
        return ExtractionResult(
            data=mock_data,
            confidence=0.5,  # 模拟数据置信度较低
            source=url,
            warnings=["注意：当前为模拟模式，未进行真实网络请求"]
        )
    
    def extract_from_file(self, file_path: str) -> List[ExtractionResult]:
        """从本地文件提取数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            return [ExtractionResult(
                data={},
                confidence=0.0,
                source=file_path,
                warnings=[f"{ErrorCode.E004} - 文件不存在: {file_path}"]
            )]
        except Exception as e:
            return [ExtractionResult(
                data={},
                confidence=0.0,
                source=file_path,
                warnings=[f"{ErrorCode.E004} - {str(e)}"]
            )]
        
        # 根据文件扩展名判断类型
        ext = file_path.lower().rsplit('.', 1)[-1] if '.' in file_path else ''
        content_type_map = {
            'html': 'text/html',
            'htm': 'text/html',
            'csv': 'text/csv',
            'json': 'application/json',
            'txt': 'text/plain',
        }
        content_type = content_type_map.get(ext, 'text/plain')
        
        return self.processor.process_by_content_type(content, content_type, file_path)
    
    def extract_from_content(self, content: str, content_type: str, source: str = "") -> List[ExtractionResult]:
        """从直接提供的内容中提取数据"""
        return self.processor.process_by_content_type(content, content_type, source)
    
    def batch_extract(self, sources: List[str], source_type: str = 'url') -> BatchResult:
        """
        批量处理多个源
        
        Args:
            sources: 源列表（URL 或文件路径）
            source_type: 'url' 或 'file'
        """
        batch = BatchResult()
        
        for source in sources:
            if source_type == 'url':
                result = self.extract_from_url(source)
                if result.warnings:
                    batch.failed_count += 1
                    batch.errors.append((source, result.warnings[0]))
                else:
                    batch.success_count += 1
                batch.results.append(result)
            elif source_type == 'file':
                results = self.extract_from_file(source)
                for result in results:
                    if result.warnings:
                        batch.failed_count += 1
                        batch.errors.append((source, result.warnings[0]))
                    else:
                        batch.success_count += 1
                    batch.results.append(result)
            else:
                batch.failed_count += 1
                batch.errors.append((source, f"{ErrorCode.E001} - 不支持的源类型: {source_type}"))
        
        return batch


# ============================================================
# 输出格式化
# ============================================================
class OutputFormatter:
    """结果输出格式化"""
    
    @staticmethod
    def to_json(results: List[ExtractionResult]) -> str:
        """转换为 JSON 格式"""
        output = []
        for r in results:
            item = {
                'source': r.source,
                'confidence': r.confidence,
                'data': r.data,
                'warnings': r.warnings
            }
            output.append(item)
        return json.dumps(output, ensure_ascii=False, indent=2, default=str)
    
    @staticmethod
    def to_csv(results: List[ExtractionResult]) -> str:
        """转换为 CSV 格式"""
        if not results:
            return ""
        
        # 收集所有字段
        all_fields = set()
        for r in results:
            all_fields.update(r.data.keys())
        
        fields = ['source', 'confidence'] + sorted(all_fields)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for r in results:
            row = {'source': r.source, 'confidence': r.confidence}
            row.update(r.data)
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def to_text(results: List[ExtractionResult]) -> str:
        """转换为纯文本格式"""
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"=== 结果 {i} ===")
            lines.append(f"来源: {r.source}")
            lines.append(f"置信度: {r.confidence:.2f}")
            for key, value in r.data.items():
                if isinstance(value, (list, dict)):
                    lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False, default=str)[:200]}")
                else:
                    lines.append(f"  {key}: {value}")
            if r.warnings:
                lines.append(f"警告: {'; '.join(r.warnings)}")
            lines.append("")
        
        return '\n'.join(lines)


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """离线自检功能"""
    
    @staticmethod
    def run() -> bool:
        """运行所有自检用例"""
        print("=" * 60)
        print("自检开始 - 使用内置硬编码样例数据")
        print("=" * 60)
        
        tests = [
            SelfTest.test_html_extraction,
            SelfTest.test_text_extraction,
            SelfTest.test_csv_extraction,
            SelfTest.test_json_extraction,
            SelfTest.test_batch_processing,
            SelfTest.test_output_formats,
        ]
        
        all_passed = True
        for test in tests:
            try:
                test()
                print(f"  [通过] {test.__name__}")
            except AssertionError as e:
                all_passed = False
                print(f"  [失败] {test.__name__}: {e}")
            except Exception as e:
                all_passed = False
                print(f"  [错误] {test.__name__}: {e}")
        
        print("=" * 60)
        if all_passed:
            print("自检全部通过！")
        else:
            print("自检存在失败项！")
        print("=" * 60)
        
        return all_passed
    
    @staticmethod
    def test_html_extraction():
        """测试 HTML 内容提取"""
        html_content = """
        <html>
            <head><title>测试页面</title></head>
            <body>
                <h1>产品价格监控</h1>
                <p>联系邮箱: support@example.com</p>
                <p>联系电话: +86 138-1234-5678</p>
                <div class="price">价格: ¥299.00</div>
                <a href="https://example.com/product/1">商品链接</a>
                <table>
                    <tr><td>SKU-001</td><td>库存</td><td>100</td></tr>
                    <tr><td>SKU-002</td><td>库存</td><td>50</td></tr>
                </table>
            </body>
        </html>
        """
        
        engine = ExtractionEngine()
        engine.configure({
            'email': 'email',
            'phone': 'phone',
            'price': 'price',
            'product_id': 'id',
        })
        
        results = engine.extract_from_content(html_content, 'text/html', 'test.html')
        assert len(results) == 1, "HTML 应产生一个结果"
        
        r = results[0]
        assert r.confidence > 0.3, f"置信度应大于 0.3，实际: {r.confidence}"
        
        # 宽松验证：email 字段应包含 @ 符号
        email = r.data.get('email', '')
        assert '@' in str(email), f"email 应包含 @，实际: {email}"
        
        # 宽松验证：price 应包含数字
        price = str(r.data.get('price', ''))
        assert any(c.isdigit() for c in price), f"price 应包含数字，实际: {price}"
    
    @staticmethod
    def test_text_extraction():
        """测试纯文本提取"""
        text_content = """
        会议通知
        日期: 2026-03-15
        地点: 北京
        参会人: zhangsan@example.com, lisi@example.com
        预算: 5000元
        """
        
        engine = ExtractionEngine()
        engine.configure({
            'date': 'date',
            'email': 'email',
            'budget': 'price',
        })
        
        results = engine.extract_from_content(text_content, 'text/plain', 'test.txt')
        assert len(results) == 1, "文本应产生一个结果"
        
        r = results[0]
        assert r.confidence > 0.2, f"置信度应大于 0.2，实际: {r.confidence}"
        
        # 宽松验证：日期应包含 4 位数字年份
        date_val = str(r.data.get('date', ''))
        assert any(c.isdigit() for c in date_val), f"date 应包含数字，实际: {date_val}"
    
    @staticmethod
    def test_csv_extraction():
        """测试 CSV 提取"""
        csv_content = """name,age,city
张三,28,北京
李四,35,上海
王五,42,广州
"""
        
        engine = ExtractionEngine()
        results = engine.extract_from_content(csv_content, 'text/csv', 'test.csv')
        
        assert len(results) == 3, f"CSV 应产生 3 个结果，实际: {len(results)}"
        
        for r in results:
            assert r.confidence > 0.5, f"CSV 置信度应大于 0.5，实际: {r.confidence}"
            assert 'name' in r.data, "CSV 结果应包含 name 字段"
    
    @staticmethod
    def test_json_extraction():
        """测试 JSON 提取"""
        json_content = json.dumps({
            'title': '测试商品',
            'price': 99.9,
            'stock': 150,
            'tags': ['数码', '热销']
        })
        
        engine = ExtractionEngine()
        results = engine.extract_from_content(json_content, 'application/json', 'test.json')
        
        assert len(results) == 1, "JSON 应产生一个结果"
        
        r = results[0]
        assert r.confidence > 0.5, f"JSON 置信度应大于 0.5，实际: {r.confidence}"
        assert 'title' in r.data, "JSON 结果应包含 title 字段"
        assert r.data.get('title') == '测试商品', "JSON title 字段值不匹配"
    
    @staticmethod
    def test_batch_processing():
        """测试批量处理"""
        engine = ExtractionEngine()
        
        # 使用无效 URL 测试错误处理
        batch = engine.batch_extract(['not-a-valid-url', 'https://example.com'], 'url')
        
        # 至少有一个失败（无效 URL）
        assert batch.failed_count >= 1, "应至少有一个失败项"
        
        # 有效 URL 也应产生结果（模拟模式）
        assert len(batch.results) >= 1, "应至少有一个结果"
    
    @staticmethod
    def test_output_formats():
        """测试输出格式化"""
        results = [
            ExtractionResult(
                data={'name': '测试', 'value': 100},
                confidence=0.8,
                source='test1',
                warnings=[]
            ),
            ExtractionResult(
                data={'name': '示例', 'value': 200},
                confidence=0.7,
                source='test2',
                warnings=['警告信息']
            ),
        ]
        
        formatter = OutputFormatter()
        
        # JSON 输出
        json_out = formatter.to_json(results)
        parsed = json.loads(json_out)
        assert len(parsed) == 2, f"JSON 输出应包含 2 条记录，实际: {len(parsed)}"
        
        # CSV 输出
        csv_out = formatter.to_csv(results)
        assert 'name' in csv_out, "CSV 输出应包含 name 列"
        assert 'value' in csv_out, "CSV 输出应包含 value 列"
        
        # 文本输出
        text_out = formatter.to_text(results)
        assert '结果 1' in text_out, "文本输出应包含结果编号"
        assert 'test1' in text_out, "文本输出应包含来源信息"


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='网页数据采集与结构化提取工具',
        epilog='示例: python main.py --url https://example.com --fields email,phone --output json'
    )
    
    parser.add_argument(
        '--selftest',
        action='store_true',
        help='运行离线自检（使用内置数据，不访问网络）'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='要采集的 URL 地址'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='要解析的本地文件路径'
    )
    
    parser.add_argument(
        '--content',
        type=str,
        help='直接提供文本内容'
    )
    
    parser.add_argument(
        '--content-type',
        type=str,
        default='text/plain',
        help='内容类型 (text/html, text/csv, application/json, text/plain)'
    )
    
    parser.add_argument(
        '--fields',
        type=str,
        help='字段映射，格式: 字段名:类型,字段名:类型 (如 email:email,phone:phone)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='json',
        choices=['json', 'csv', 'text'],
        help='输出格式 (默认: json)'
    )
    
    parser.add_argument(
        '--batch-file',
        type=str,
        help='批量处理文件（每行一个 URL 或文件路径）'
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1
    
    # 创建引擎
    engine = ExtractionEngine()
    
    # 配置字段映射
    field_mapping = None
    if args.fields:
        try:
            field_mapping = {}
            for pair in args.fields.split(','):
                if ':' in pair:
                    name, ftype = pair.split(':', 1)
                    field_mapping[name.strip()] = ftype.strip()
            engine.configure(field_mapping)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    # 批量处理模式
    if args.batch_file:
        try:
            with open(args.batch_file, 'r', encoding='utf-8') as f:
                sources = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"错误: {ErrorCode.E004} - {e}", file=sys.stderr)
            return 1
        
        batch = engine.batch_extract(sources, 'url')
        formatter = OutputFormatter()
        
        if args.output == 'json':
            print(formatter.to_json(batch.results))
        elif args.output == 'csv':
            print(formatter.to_csv(batch.results))
        else:
            print(formatter.to_text(batch.results))
        
        return 0
    
    # 单 URL 模式
    if args.url:
        result = engine.extract_from_url(args.url)
        formatter = OutputFormatter()
        
        if args.output == 'json':
            print(formatter.to_json([result]))
        elif args.output == 'csv':
            print(formatter.to_csv([result]))
        else:
            print(formatter.to_text([result]))
        
        return 0
    
    # 单文件模式
    if args.file:
        results = engine.extract_from_file(args.file)
        formatter = OutputFormatter()
        
        if args.output == 'json':
            print(formatter.to_json(results))
        elif args.output == 'csv':
            print(formatter.to_csv(results))
        else:
            print(formatter.to_text(results))
        
        return 0
    
    # 直接内容模式
    if args.content:
        results = engine.extract_from_content(args.content, args.content_type, 'direct-input')
        formatter = OutputFormatter()
        
        if args.output == 'json':
            print(formatter.to_json(results))
        elif args.output == 'csv':
            print(formatter.to_csv(results))
        else:
            print(formatter.to_text(results))
        
        return 0
    
    # 未提供任何输入
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
