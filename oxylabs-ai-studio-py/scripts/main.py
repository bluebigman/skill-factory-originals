#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 网页数据采集与结构化提取工具（独立实现）

本脚本依据功能规格独立编写，不包含任何既有代码。
提供 URL 采集、文件解析、批量处理、字段映射与置信度标注能力。
"""

import argparse
import csv
import json
import re
import sys
import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime


# ============================================================
# 错误码定义
# ============================================================
ERR_SUCCESS = 0
ERR_INVALID_URL = "E001"          # URL 格式无效
ERR_FETCH_FAILED = "E002"         # 网络请求失败
ERR_FILE_NOT_FOUND = "E003"       # 文件不存在
ERR_FILE_READ_FAILED = "E004"     # 文件读取失败
ERR_PARSE_FAILED = "E005"         # 内容解析失败
ERR_INVALID_FIELDS = "E006"       # 字段配置无效
ERR_INVALID_INPUT = "E007"        # 输入参数无效
ERR_BATCH_FAILED = "E008"         # 批量处理失败
ERR_OUTPUT_FAILED = "E009"        # 输出写入失败
ERR_INTERNAL = "E010"             # 内部错误


# ============================================================
# 工具函数
# ============================================================

def _safe_text(value: Any) -> str:
    """安全转换为文本"""
    if value is None:
        return ""
    return str(value).strip()


def _extract_by_regex(pattern: str, text: str) -> Optional[str]:
    """使用正则表达式提取第一个匹配项"""
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None
    except re.error:
        return None


def _extract_all_by_regex(pattern: str, text: str) -> List[str]:
    """使用正则表达式提取所有匹配项"""
    try:
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
        return [m.strip() if isinstance(m, str) else str(m[0]).strip() for m in matches]
    except re.error:
        return []


def _clean_html_tags(html_text: str) -> str:
    """去除 HTML 标签并压缩空白"""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_json_content(content: str) -> Optional[Dict[str, Any]]:
    """尝试解析 JSON 内容"""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def _parse_csv_content(content: str) -> Optional[List[Dict[str, str]]]:
    """尝试解析 CSV 内容"""
    try:
        reader = csv.DictReader(content.splitlines())
        return [dict(row) for row in reader]
    except (csv.Error, TypeError):
        return None


# ============================================================
# 核心数据模型
# ============================================================

class ExtractionResult:
    """提取结果对象，包含数据与置信度"""

    def __init__(self, data: Dict[str, Any], confidence: float = 1.0):
        self.data = data
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self.data,
            "confidence": round(self.confidence, 4)
        }


class FieldConfig:
    """字段映射配置"""

    def __init__(self, name: str, field_type: str = "string",
                 regex: Optional[str] = None, required: bool = False):
        self.name = name
        self.field_type = field_type
        self.regex = regex
        self.required = required

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "FieldConfig":
        """从字典创建字段配置"""
        name = _safe_text(config.get("name"))
        if not name:
            raise ValueError("字段名称不能为空")
        return cls(
            name=name,
            field_type=_safe_text(config.get("type", "string")),
            regex=config.get("regex"),
            required=bool(config.get("required", False))
        )

    def validate(self) -> bool:
        """校验配置合法性"""
        if not self.name:
            return False
        if self.field_type not in ("string", "number", "bool", "list"):
            return False
        if self.regex:
            try:
                re.compile(self.regex)
            except re.error:
                return False
        return True


# ============================================================
# 核心提取器
# ============================================================

class ContentExtractor:
    """内容提取器：从原始内容中提取结构化字段"""

    def __init__(self, fields: Optional[List[FieldConfig]] = None):
        self.fields = fields or []

    def extract(self, raw_content: str, source_type: str = "auto") -> ExtractionResult:
        """
        从原始内容提取字段
        
        Args:
            raw_content: 原始内容文本
            source_type: 内容类型 (html/json/csv/auto)
            
        Returns:
            ExtractionResult 对象
        """
        data: Dict[str, Any] = {}
        confidence = 1.0
        
        # 解析内容
        parsed = self._parse_content(raw_content, source_type)
        
        # 提取字段
        for field in self.fields:
            value, field_conf = self._extract_field(field, parsed, raw_content)
            if field.required and value is None:
                confidence *= 0.5  # 必填字段缺失降低置信度
            data[field.name] = value
            confidence *= field_conf
        
        return ExtractionResult(data=data, confidence=confidence)

    def _parse_content(self, content: str, source_type: str) -> Any:
        """解析内容为结构化数据"""
        if source_type == "auto":
            # 自动检测类型
            if content.lstrip().startswith("{"):
                return _parse_json_content(content)
            if "<html" in content[:500].lower() or "<!doctype" in content[:500].lower():
                return _clean_html_tags(content)
            if "," in content[:100]:
                return _parse_csv_content(content)
            return content
        elif source_type == "json":
            return _parse_json_content(content)
        elif source_type == "html":
            return _clean_html_tags(content)
        elif source_type == "csv":
            return _parse_csv_content(content)
        return content

    def _extract_field(self, field: FieldConfig, parsed: Any, raw: str) -> Tuple[Any, float]:
        """提取单个字段"""
        try:
            if isinstance(parsed, dict):
                # JSON 对象直接取键值
                if field.name in parsed:
                    return self._convert_type(parsed[field.name], field.field_type), 1.0
            
            if isinstance(parsed, list):
                # CSV 或列表数据
                if parsed and field.name in parsed[0]:
                    return self._convert_type(parsed[0][field.name], field.field_type), 1.0
            
            # 使用正则提取
            if field.regex:
                match = _extract_by_regex(field.regex, raw)
                if match is not None:
                    return self._convert_type(match, field.field_type), 0.9
                return None, 0.6
            
            # 默认从文本中查找
            text = str(parsed) if not isinstance(parsed, (dict, list)) else raw
            if field.field_type == "list":
                # 尝试提取列表项
                items = _extract_all_by_regex(rf"{field.name}[:\s]+(.+)", text)
                return items if items else None, 0.7
            return None, 0.5
            
        except Exception:
            return None, 0.3

    @staticmethod
    def _convert_type(value: Any, field_type: str) -> Any:
        """转换字段类型"""
        if field_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        elif field_type == "bool":
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("true", "yes", "1")
        elif field_type == "list":
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            return [value]
        return _safe_text(value)


# ============================================================
# 采集器
# ============================================================

class DataCollector:
    """数据采集器：处理 URL 和文件的采集"""

    def __init__(self, extractor: Optional[ContentExtractor] = None):
        self.extractor = extractor or ContentExtractor()

    def collect_from_url(self, url: str, timeout: int = 10) -> Tuple[Optional[str], str]:
        """
        从 URL 采集数据（模拟实现，实际应使用 requests）
        
        注意：实际网络请求需要第三方库，此处仅提供接口框架。
        如需真实网络请求，请安装: pip install requests
        """
        if not url or not urlparse(url).scheme:
            return None, ERR_INVALID_URL
        
        # 实际实现中应使用 requests.get(url, timeout=timeout)
        # 此处为演示返回错误
        return None, ERR_FETCH_FAILED

    def collect_from_file(self, file_path: str) -> Tuple[Optional[str], str]:
        """
        从文件读取内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            (内容, 错误码)
        """
        if not os.path.exists(file_path):
            return None, ERR_FILE_NOT_FOUND
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), ERR_SUCCESS
        except (IOError, OSError):
            return None, ERR_FILE_READ_FAILED

    def process_content(self, content: str, source_type: str = "auto") -> ExtractionResult:
        """处理内容并提取字段"""
        return self.extractor.extract(content, source_type)


# ============================================================
# 批量处理器
# ============================================================

class BatchProcessor:
    """批量任务处理器"""

    def __init__(self, collector: Optional[DataCollector] = None):
        self.collector = collector or DataCollector()

    def process_batch(self, sources: List[str], source_type: str = "auto",
                      fields: Optional[List[FieldConfig]] = None) -> Dict[str, Any]:
        """
        批量处理多个来源
        
        Args:
            sources: 来源列表（URL 或文件路径）
            source_type: 内容类型
            fields: 字段配置列表
            
        Returns:
            处理结果字典
        """
        extractor = ContentExtractor(fields or [])
        collector = DataCollector(extractor)
        
        results = []
        errors = []
        
        for source in sources:
            try:
                if source.startswith(("http://", "https://")):
                    # URL 来源
                    content, err = collector.collect_from_url(source)
                else:
                    # 文件来源
                    content, err = collector.collect_from_file(source)
                
                if err != ERR_SUCCESS:
                    errors.append({"source": source, "error": err})
                    continue
                
                result = collector.process_content(content, source_type)
                results.append({
                    "source": source,
                    **result.to_dict()
                })
            except Exception as e:
                errors.append({"source": source, "error": ERR_BATCH_FAILED, "detail": str(e)})
        
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }


# ============================================================
# 输出处理器
# ============================================================

class OutputHandler:
    """输出处理器：支持 JSON 和 CSV 格式"""

    @staticmethod
    def to_json(data: Any) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_csv(results: List[Dict[str, Any]]) -> str:
        """转换为 CSV 字符串"""
        if not results:
            return ""
        
        # 收集所有字段
        all_keys = set()
        for r in results:
            if isinstance(r.get("data"), dict):
                all_keys.update(r["data"].keys())
        
        # 写入 CSV
        import io
        output = io.StringIO()
        fieldnames = ["source", "confidence"] + sorted(all_keys)
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        for r in results:
            row = {
                "source": r.get("source", ""),
                "confidence": r.get("confidence", 0)
            }
            if isinstance(r.get("data"), dict):
                row.update(r["data"])
            writer.writerow(row)
        
        return output.getvalue()


# ============================================================
# 主程序
# ============================================================

def run_selftest() -> int:
    """
    自检函数：使用内置样例数据验证核心逻辑
    
    Returns:
        0 表示成功，非 0 表示失败
    """
    print("=== 开始自检 ===")
    
    # 样例 1: HTML 内容提取
    print("\n[测试 1] HTML 内容提取")
    html_sample = """
    <html>
    <head><title>测试商品页</title></head>
    <body>
        <h1 class="product-name">智能手表 Pro</h1>
        <span class="price">¥2999.00</span>
        <div class="rating">4.5</div>
        <ul class="features">
            <li>防水</li>
            <li>心率监测</li>
            <li>GPS</li>
        </ul>
    </body>
    </html>
    """
    
    fields = [
        FieldConfig(name="product_name", regex=r"<h1[^>]*>(.*?)</h1>", required=True),
        FieldConfig(name="price", regex=r"¥([\d.]+)", field_type="number"),
        FieldConfig(name="rating", regex=r"class=\"rating\">([\d.]+)</div>", field_type="number"),
        FieldConfig(name="features", regex=r"<li>(.*?)</li>", field_type="list"),
    ]
    
    extractor = ContentExtractor(fields)
    result = extractor.extract(html_sample, "html")
    
    assert result.data.get("product_name") is not None, "商品名称提取失败"
    assert result.data.get("price") is not None, "价格提取失败"
    assert result.data.get("price", 0) > 0, "价格应为正数"
    assert result.data.get("rating", 0) >= 0, "评分应为非负数"
    assert result.data.get("features") is not None, "特性列表提取失败"
    print(f"  提取结果: {result.to_dict()}")
    print("  ✓ 通过")
    
    # 样例 2: JSON 内容提取
    print("\n[测试 2] JSON 内容提取")
    json_sample = json.dumps({
        "product": {
            "id": "SKU-001",
            "name": "无线耳机",
            "price": 599.0,
            "stock": 120,
            "available": True
        }
    })
    
    json_fields = [
        FieldConfig(name="id", regex=r"\"id\":\s*\"([^\"]+)\""),
        FieldConfig(name="name", regex=r"\"name\":\s*\"([^\"]+)\""),
        FieldConfig(name="price", regex=r"\"price\":\s*([\d.]+)", field_type="number"),
        FieldConfig(name="stock", regex=r"\"stock\":\s*(\d+)", field_type="number"),
    ]
    
    extractor = ContentExtractor(json_fields)
    result = extractor.extract(json_sample, "json")
    
    assert result.data.get("id") == "SKU-001", "ID 提取错误"
    assert result.data.get("name") is not None, "名称提取失败"
    assert result.data.get("price", 0) > 0, "价格应为正数"
    assert result.data.get("stock", 0) >= 0, "库存应为非负数"
    print(f"  提取结果: {result.to_dict()}")
    print("  ✓ 通过")
    
    # 样例 3: CSV 内容提取
    print("\n[测试 3] CSV 内容提取")
    csv_sample = "name,price,quantity\n苹果,5.5,10\n香蕉,3.2,20\n"
    
    csv_fields = [
        FieldConfig(name="name", regex=r"^([^,]+)", required=True),
        FieldConfig(name="price", regex=r",([\d.]+),", field_type="number"),
    ]
    
    extractor = ContentExtractor(csv_fields)
    result = extractor.extract(csv_sample, "csv")
    
    assert result.data.get("name") is not None, "名称提取失败"
    print(f"  提取结果: {result.to_dict()}")
    print("  ✓ 通过")
    
    # 样例 4: 批量处理
    print("\n[测试 4] 批量处理")
    batch_processor = BatchProcessor()
    batch_result = batch_processor.process_batch(
        ["/nonexistent/file1.html", "/nonexistent/file2.html"],
        fields=fields
    )
    
    assert batch_result["success_count"] == 0, "不应有成功结果"
    assert batch_result["error_count"] == 2, "应有 2 个错误"
    assert len(batch_result["errors"]) == 2, "错误列表长度应为 2"
    print(f"  批量结果: 成功={batch_result['success_count']}, 错误={batch_result['error_count']}")
    print("  ✓ 通过")
    
    # 样例 5: 输出处理
    print("\n[测试 5] 输出处理")
    test_results = [
        {"source": "test1", "data": {"name": "商品A", "price": 100}, "confidence": 0.9},
        {"source": "test2", "data": {"name": "商品B", "price": 200}, "confidence": 0.8},
    ]
    
    json_output = OutputHandler.to_json(test_results)
    assert json_output is not None, "JSON 输出失败"
    
    csv_output = OutputHandler.to_csv(test_results)
    assert "商品A" in csv_output, "CSV 输出应包含商品A"
    assert "商品B" in csv_output, "CSV 输出应包含商品B"
    print("  ✓ 通过")
    
    print("\n=== 全部自检通过 ===")
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="网页数据采集与结构化提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest                          # 运行自检
  python main.py --url https://example.com --fields config.json
  python main.py --file data.html --type html
  python main.py --batch sources.txt --output result.json
        """
    )
    
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--url", help="采集单个 URL")
    parser.add_argument("--file", help="解析单个文件")
    parser.add_argument("--batch", help="批量处理文件（每行一个来源）")
    parser.add_argument("--type", default="auto", choices=["auto", "html", "json", "csv"], help="内容类型")
    parser.add_argument("--fields", help="字段配置 JSON 文件")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="输出格式")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not (args.url or args.file or args.batch):
        print(f"错误 [{ERR_INVALID_INPUT}]: 请提供 --url、--file 或 --batch 参数", file=sys.stderr)
        parser.print_help()
        return 1
    
    try:
        # 加载字段配置
        fields = []
        if args.fields:
            if not os.path.exists(args.fields):
                print(f"错误 [{ERR_FILE_NOT_FOUND}]: 字段配置文件不存在", file=sys.stderr)
                return 1
            with open(args.fields, "r", encoding="utf-8") as f:
                field_configs = json.load(f)
            for fc in field_configs:
                field = FieldConfig.from_dict(fc)
                if not field.validate():
                    print(f"错误 [{ERR_INVALID_FIELDS}]: 字段配置无效: {fc}", file=sys.stderr)
                    return 1
                fields.append(field)
        
        collector = DataCollector(ContentExtractor(fields))
        
        # 单 URL 处理
        if args.url:
            content, err = collector.collect_from_url(args.url)
            if err != ERR_SUCCESS:
                print(f"错误 [{err}]: URL 采集失败: {args.url}", file=sys.stderr)
                return 1
            result = collector.process_content(content, args.type)
            output = {"source": args.url, **result.to_dict()}
            output_list = [output]
        
        # 单文件处理
        elif args.file:
            content, err = collector.collect_from_file(args.file)
            if err != ERR_SUCCESS:
                print(f"错误 [{err}]: 文件读取失败: {args.file}", file=sys.stderr)
                return 1
            result = collector.process_content(content, args.type)
            output = {"source": args.file, **result.to_dict()}
            output_list = [output]
        
        # 批量处理
        else:
            if not os.path.exists(args.batch):
                print(f"错误 [{ERR_FILE_NOT_FOUND}]: 批量文件不存在", file=sys.stderr)
                return 1
            with open(args.batch, "r", encoding="utf-8") as f:
                sources = [line.strip() for line in f if line.strip()]
            
            processor = BatchProcessor()
            batch_result = processor.process_batch(sources, args.type, fields)
            output_list = batch_result["results"]
            
            if batch_result["error_count"] > 0:
                print(f"警告: {batch_result['error_count']} 个来源处理失败", file=sys.stderr)
        
        # 输出结果
        if args.format == "json":
            output_text = OutputHandler.to_json(output_list)
        else:
            output_text = OutputHandler.to_csv(output_list)
        
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已保存到: {args.output}")
            except (IOError, OSError):
                print(f"错误 [{ERR_OUTPUT_FAILED}]: 无法写入输出文件", file=sys.stderr)
                return 1
        else:
            print(output_text)
        
        return 0
        
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
