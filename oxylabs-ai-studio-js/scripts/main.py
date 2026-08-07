#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫采集技能 - 独立实现脚本
基于功能规格的 clean-room 实现，仅依赖标准库。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理错误：{detail}",
    "E007": "参数解析错误：{detail}",
    "E008": "输出格式不支持：{format}",
    "E009": "批量处理中断：{detail}",
    "E010": "未知错误：{detail}",
}


class SkillError(Exception):
    """技能异常基类"""
    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, ERROR_CODES["E010"]).format(**kwargs)
        super().__init__(self.message)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class ProcessedItem:
    """处理结果项"""
    source: str
    content: str
    confidence: float
    fields: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source": self.source,
            "content": self.content,
            "confidence": self.confidence,
            "fields": self.fields,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
class DataProcessor:
    """数据处理器 - 核心逻辑"""

    # 关键信息识别模式
    PATTERNS = {
        "url": re.compile(r'https?://[^\s<>"\'()]+', re.IGNORECASE),
        "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        "phone": re.compile(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}'),
        "date": re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}'),
        "number": re.compile(r'\d+(?:[.,]\d+)?'),
    }

    # 关键字段识别关键词
    FIELD_KEYWORDS = {
        "title": ["标题", "题目", "title", "name"],
        "author": ["作者", "author", "creator"],
        "description": ["描述", "简介", "description", "summary"],
        "price": ["价格", "price", "金额"],
        "location": ["地址", "位置", "location", "place"],
        "contact": ["联系", "电话", "contact", "phone"],
        "category": ["分类", "类型", "category", "type"],
    }

    def __init__(self):
        self.results: List[ProcessedItem] = []

    def process(self, inputs: List[str], format_type: str = "json") -> Dict[str, Any]:
        """批量处理输入数据"""
        if not inputs:
            raise SkillError("E001")

        processed = []
        for item in inputs:
            try:
                result = self._process_single(item)
                processed.append(result)
            except SkillError as e:
                # 单个条目失败不中断整体
                processed.append(ProcessedItem(
                    source=item,
                    content="",
                    confidence=0.0,
                    fields={"error": e.code, "message": str(e)},
                    warnings=["处理失败"]
                ))

        self.results = processed
        return self._format_output(processed, format_type)

    def _process_single(self, input_str: str) -> ProcessedItem:
        """处理单个输入"""
        if not input_str or not input_str.strip():
            raise SkillError("E001")

        # 识别输入类型
        source_type = self._detect_source_type(input_str)

        # 提取关键信息
        fields = self._extract_fields(input_str)

        # 计算置信度
        confidence = self._calculate_confidence(fields, source_type)

        # 生成警告
        warnings = self._generate_warnings(confidence, fields)

        # 检查关键信息完整性
        if not fields:
            raise SkillError("E002", missing="关键信息（如标题、内容等）")

        return ProcessedItem(
            source=input_str,
            content=input_str.strip(),
            confidence=confidence,
            fields=fields,
            warnings=warnings
        )

    def _detect_source_type(self, text: str) -> str:
        """检测输入来源类型"""
        if re.match(r'https?://', text.strip(), re.IGNORECASE):
            return "URL"
        if '\n' in text and len(text.strip()) > 50:
            return "TEXT_BLOCK"
        return "TEXT"

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """提取关键字段"""
        fields: Dict[str, Any] = {}

        # 提取 URL
        urls = self.PATTERNS["url"].findall(text)
        if urls:
            fields["urls"] = urls

        # 提取邮箱
        emails = self.PATTERNS["email"].findall(text)
        if emails:
            fields["emails"] = emails

        # 提取电话号码
        phones = self.PATTERNS["phone"].findall(text)
        if phones:
            fields["phones"] = phones

        # 提取日期
        dates = self.PATTERNS["date"].findall(text)
        if dates:
            fields["dates"] = dates

        # 识别关键字段
        lines = text.split('\n')
        for line in lines[:10]:  # 只检查前10行
            line_lower = line.lower().strip()
            for field_name, keywords in self.FIELD_KEYWORDS.items():
                if field_name in fields:
                    continue
                for keyword in keywords:
                    if keyword in line_lower:
                        # 提取冒号后的内容
                        if ':' in line:
                            value = line.split(':', 1)[1].strip()
                        elif '：' in line:
                            value = line.split('：', 1)[1].strip()
                        else:
                            value = line.strip()
                        if value and len(value) < 100:
                            fields[field_name] = value
                            break

        # 如果没找到标题，尝试用第一行
        if "title" not in fields and lines:
            first_line = lines[0].strip()
            if first_line and len(first_line) < 50:
                fields["title"] = first_line

        return fields

    def _calculate_confidence(self, fields: Dict[str, Any], source_type: str) -> float:
        """计算置信度"""
        if not fields:
            return 0.0

        # 基础置信度
        confidence = 0.7

        # 根据字段数量增加置信度
        field_count = len(fields)
        confidence += min(field_count * 0.05, 0.2)

        # 根据来源类型调整
        if source_type == "URL":
            confidence += 0.05
        elif source_type == "TEXT_BLOCK":
            confidence += 0.02

        # 有明确标识符增加置信度
        if "urls" in fields:
            confidence += 0.03
        if "emails" in fields or "phones" in fields:
            confidence += 0.02

        # 限制在 0-1 之间
        return max(0.0, min(confidence, 1.0))

    def _generate_warnings(self, confidence: float, fields: Dict[str, Any]) -> List[str]:
        """生成警告信息"""
        warnings = []

        if confidence < 0.85:
            warnings.append("建议复核")

        if confidence < 0.7:
            warnings.append("[需核实]")

        if not fields.get("urls") and not fields.get("emails"):
            warnings.append("未检测到明确的网络地址或联系方式")

        return warnings

    def _format_output(self, results: List[ProcessedItem], format_type: str) -> Dict[str, Any]:
        """格式化输出"""
        if format_type == "json":
            return {
                "status": "success",
                "count": len(results),
                "results": [r.to_dict() for r in results]
            }
        elif format_type == "text":
            # 文本格式输出
            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"结果 {i}:")
                lines.append(f"  来源: {r.source[:50]}...")
                lines.append(f"  置信度: {r.confidence:.0%}")
                if r.fields:
                    lines.append("  字段:")
                    for k, v in r.fields.items():
                        lines.append(f"    {k}: {v}")
                if r.warnings:
                    lines.append(f"  警告: {', '.join(r.warnings)}")
                lines.append("")
            return {
                "status": "success",
                "count": len(results),
                "output": "\n".join(lines)
            }
        else:
            raise SkillError("E008", format=format_type)


# ============================================================
# URL 分析工具（可选扩展）
# ============================================================
class URLAnalyzer:
    """URL 分析工具"""

    @staticmethod
    def analyze(url: str) -> Dict[str, Any]:
        """分析 URL 结构"""
        try:
            parsed = urlparse(url)
            return {
                "scheme": parsed.scheme,
                "netloc": parsed.netloc,
                "path": parsed.path,
                "params": parsed.params,
                "query": parsed.query,
                "fragment": parsed.fragment,
                "is_valid": all([parsed.scheme, parsed.netloc])
            }
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e)
            }


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    自检函数 - 使用内置硬编码样例数据
    不读取外部文件，不依赖当前工作目录，不访问网络
    """
    print("开始自检...")
    processor = DataProcessor()

    # 测试样例 1: 文本数据
    test_input_1 = """标题：爬虫技术入门
作者：张三
描述：学习如何使用Python进行网页爬取
价格：99元
地址：北京市海淀区
联系：13812345678
"""

    # 测试样例 2: URL
    test_input_2 = "https://example.com/products/123?page=1&size=10"

    # 测试样例 3: 混合数据
    test_input_3 = """产品信息
分类：电子设备
型号：X100
价格：2999.00
邮箱：sales@example.com
电话：010-88886666
日期：2024-01-15
"""

    # 测试 1: 处理文本数据
    print("\n测试 1: 文本数据处理")
    try:
        result = processor.process([test_input_1], format_type="json")
        assert result["status"] == "success", "处理失败"
        assert result["count"] == 1, "结果数量错误"
        item = result["results"][0]
        # 宽松断言：置信度应较高
        assert item["confidence"] > 0.5, f"置信度异常: {item['confidence']}"
        # 应识别出关键字段
        assert len(item["fields"]) > 0, "未提取到任何字段"
        print(f"  ✓ 通过 (置信度: {item['confidence']:.0%}, 字段数: {len(item['fields'])})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 2: 处理 URL
    print("\n测试 2: URL 处理")
    try:
        result = processor.process([test_input_2], format_type="json")
        assert result["status"] == "success", "处理失败"
        item = result["results"][0]
        assert "urls" in item["fields"], "未识别URL"
        assert item["confidence"] > 0.5, f"置信度异常: {item['confidence']}"
        print(f"  ✓ 通过 (置信度: {item['confidence']:.0%})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 3: 批量处理
    print("\n测试 3: 批量处理")
    try:
        inputs = [test_input_1, test_input_2, test_input_3]
        result = processor.process(inputs, format_type="json")
        assert result["count"] == 3, "批量处理数量错误"
        assert all(r["confidence"] > 0.3 for r in result["results"]), "置信度过低"
        print(f"  ✓ 通过 (处理 {result['count']} 条)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 4: 空输入处理
    print("\n测试 4: 空输入处理")
    try:
        processor.process([])
        print("  ✗ 失败: 未触发错误")
        return False
    except SkillError as e:
        assert e.code == "E001", f"错误码错误: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 5: URL 分析
    print("\n测试 5: URL 分析")
    try:
        analyzer = URLAnalyzer()
        url_info = analyzer.analyze("https://example.com/path?query=1")
        assert url_info["is_valid"], "URL 验证失败"
        assert url_info["scheme"] == "https", "协议错误"
        assert url_info["netloc"] == "example.com", "域名错误"
        print(f"  ✓ 通过 (scheme: {url_info['scheme']}, domain: {url_info['netloc']})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 6: 文本格式输出
    print("\n测试 6: 文本格式输出")
    try:
        result = processor.process([test_input_1], format_type="text")
        assert result["status"] == "success", "处理失败"
        assert "output" in result, "缺少输出内容"
        assert len(result["output"]) > 0, "输出为空"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试 7: 错误处理
    print("\n测试 7: 错误处理")
    try:
        processor.process(["test"], format_type="xml")
        print("  ✗ 失败: 未触发错误")
        return False
    except SkillError as e:
        assert e.code == "E008", f"错误码错误: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n所有自检通过！")
    return True


# ============================================================
# 主程序入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="爬虫采集技能 - 结构化数据处理工具",
        epilog="示例: python main.py --input '标题：示例' 或 python main.py --selftest"
    )
    parser.add_argument(
        "--input", "-i",
        nargs="+",
        help="输入内容（文本或URL），支持多个"
    )
    parser.add_argument(
        "--file", "-f",
        help="从文件读取输入（每行一个条目）"
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )
    parser.add_argument(
        "--analyze-url",
        help="分析URL结构"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # URL 分析模式
    if args.analyze_url:
        analyzer = URLAnalyzer()
        result = analyzer.analyze(args.analyze_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 标准处理模式
    try:
        inputs = []

        # 从命令行参数获取输入
        if args.input:
            inputs.extend(args.input)

        # 从文件获取输入
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    file_inputs = [line.strip() for line in f if line.strip()]
                    inputs.extend(file_inputs)
            except FileNotFoundError:
                raise SkillError("E006", detail=f"文件不存在: {args.file}")
            except Exception as e:
                raise SkillError("E006", detail=f"文件读取失败: {e}")

        # 处理输入
        if not inputs:
            # 尝试从标准输入读取
            if not sys.stdin.isatty():
                inputs = [line.strip() for line in sys.stdin if line.strip()]
            else:
                raise SkillError("E001")

        processor = DataProcessor()
        result = processor.process(inputs, format_type=args.format)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["output"])

    except SkillError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 [E010]: 未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
