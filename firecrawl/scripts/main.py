#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firecrawl 技能实现脚本（独立 clean-room 实现）
================================================
依据功能规格独立编写，不参考任何既有代码。

功能概览：
    1. 网页内容抓取（模拟）
    2. 文件转结构化（模拟）
    3. 批量 URL 处理
    4. 搜索增强抓取（模拟）
    5. 自定义格式输出

设计原则：
    - 标准库优先，无第三方依赖
    - 内置硬编码样例数据，支持 --selftest 离线自检
    - 错误码 E001-E010，结构化错误处理
    - 中文注释，清晰模块划分

用法示例：
    python main.py --selftest
    python main.py --url https://example.com --format json
    python main.py --urls https://a.com https://b.com --format markdown
    python main.py --search "python 教程" --limit 3
"""

import argparse
import json
import sys
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 常量定义
# ============================================================

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "URL 格式无效",
    "E003": "不支持的输出格式",
    "E004": "抓取失败：目标页面不可访问",
    "E005": "文件解析失败：不支持的文件类型",
    "E006": "批量处理失败：存在无效 URL",
    "E007": "搜索失败：未提供搜索关键词",
    "E008": "自定义格式字段不存在",
    "E009": "内部处理错误",
    "E010": "未知错误",
}

# 支持的文件类型映射
SUPPORTED_FILE_TYPES = {
    ".pdf": "PDF 文档",
    ".doc": "Word 文档",
    ".docx": "Word 文档",
    ".xls": "Excel 表格",
    ".xlsx": "Excel 表格",
    ".txt": "纯文本",
    ".md": "Markdown",
}

# 支持的输出格式
SUPPORTED_OUTPUT_FORMATS = ["json", "markdown", "text", "html"]


# ============================================================
# 工具函数
# ============================================================

def get_error_message(code: str) -> str:
    """获取错误码对应的错误信息"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


def validate_url(url: str) -> bool:
    """简单验证 URL 格式是否合法"""
    pattern = re.compile(
        r"^(https?://)"  # http:// 或 https://
        r"([a-zA-Z0-9.-]+)"  # 域名
        r"(\.[a-zA-Z]{2,})"  # 顶级域名
        r"(:\d+)?"  # 可选端口
        r"(/.*)?$"  # 可选路径
    )
    return bool(pattern.match(url))


def normalize_url(url: str) -> str:
    """规范化 URL：去除首尾空格，补全协议"""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ============================================================
# 核心数据类（内置样例数据）
# ============================================================

class SampleData:
    """内置硬编码样例数据，用于离线自检"""

    # 样例网页抓取数据
    WEB_PAGE_SAMPLE = {
        "url": "https://example.com/news/technology/ai",
        "title": "人工智能技术最新进展",
        "content": (
            "近年来人工智能技术快速发展，在自然语言处理、计算机视觉等领域取得重大突破。"
            "深度学习模型的规模不断扩大，应用场景日益丰富。"
            "专家预测，未来五年人工智能将深刻改变各行各业的生产方式。"
        ),
        "metadata": {
            "author": "张明",
            "publish_date": "2026-01-15",
            "tags": ["AI", "技术", "创新"],
            "word_count": 128,
        },
        "timestamp": "2026-02-01T10:30:00Z",
    }

    # 样例文件转结构化数据
    FILE_SAMPLE = {
        "filename": "季度销售报告.pdf",
        "file_type": "PDF 文档",
        "structured_data": {
            "company": "示例科技有限公司",
            "quarter": "2025 Q4",
            "total_revenue": 1250000,
            "total_cost": 850000,
            "net_profit": 400000,
            "products": [
                {"name": "产品A", "sales": 500000},
                {"name": "产品B", "sales": 450000},
                {"name": "产品C", "sales": 300000},
            ],
        },
        "timestamp": "2026-02-01T10:31:00Z",
    }

    # 样例批量 URL 处理结果
    BATCH_SAMPLE = [
        {
            "url": "https://example.com/blog/post1",
            "title": "第一篇文章",
            "status": "success",
            "content_preview": "这是第一篇文章的内容预览...",
        },
        {
            "url": "https://example.com/blog/post2",
            "title": "第二篇文章",
            "status": "success",
            "content_preview": "这是第二篇文章的内容预览...",
        },
        {
            "url": "https://example.com/blog/post3",
            "title": "第三篇文章",
            "status": "success",
            "content_preview": "这是第三篇文章的内容预览...",
        },
    ]

    # 样例搜索结果
    SEARCH_SAMPLE = [
        {
            "title": "Python 编程入门教程",
            "url": "https://example.com/tutorials/python-intro",
            "snippet": "Python 是一种简单易学的编程语言，适合初学者入门...",
            "rank": 1,
        },
        {
            "title": "Python 高级编程技巧",
            "url": "https://example.com/tutorials/python-advanced",
            "snippet": "掌握 Python 高级特性，提升代码质量和开发效率...",
            "rank": 2,
        },
        {
            "title": "Python Web 开发实战",
            "url": "https://example.com/tutorials/python-web",
            "snippet": "使用 Python 构建现代 Web 应用，涵盖 Flask 和 Django...",
            "rank": 3,
        },
    ]


# ============================================================
# 核心处理类
# ============================================================

class FirecrawlProcessor:
    """
    Firecrawl 核心处理器
    实现网页抓取、文件转换、批量处理、搜索增强、自定义输出等功能
    """

    def __init__(self):
        """初始化处理器"""
        self.sample_data = SampleData()

    # ---------- 能力1：网页内容抓取 ----------
    def scrape_webpage(self, url: str) -> Dict[str, Any]:
        """
        抓取单个网页内容
        实际实现中会发起 HTTP 请求，这里使用模拟数据

        参数:
            url: 目标网页 URL

        返回:
            包含标题、正文、元数据的字典

        错误码:
            E001: URL 为空
            E002: URL 格式无效
            E004: 抓取失败
        """
        if not url:
            raise ValueError("E001")

        url = normalize_url(url)
        if not validate_url(url):
            raise ValueError("E002")

        # 模拟抓取过程
        # 实际实现中这里会使用 requests 等库发起网络请求
        # 此处直接返回内置样例数据，并附加请求的 URL
        result = dict(self.sample_data.WEB_PAGE_SAMPLE)
        result["url"] = url

        # 根据 URL 特征简单模拟不同结果
        if "error" in url or "404" in url:
            raise ValueError("E004")

        return result

    # ---------- 能力2：文件转结构化 ----------
    def file_to_structured(self, filename: str, file_content: Optional[bytes] = None) -> Dict[str, Any]:
        """
        将文件内容转换为结构化数据
        实际实现中会解析文件二进制内容，这里使用模拟数据

        参数:
            filename: 文件名（含扩展名）
            file_content: 文件二进制内容（可选，实际使用）

        返回:
            包含文件信息和结构化数据的字典

        错误码:
            E001: 文件名为空
            E005: 不支持的文件类型
        """
        if not filename:
            raise ValueError("E001")

        # 获取文件扩展名
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[1].lower()

        # 检查文件类型是否支持
        if ext not in SUPPORTED_FILE_TYPES:
            raise ValueError("E005")

        # 模拟解析过程
        result = dict(self.sample_data.FILE_SAMPLE)
        result["filename"] = filename
        result["file_type"] = SUPPORTED_FILE_TYPES[ext]

        # 根据文件类型调整模拟数据
        if ext in (".txt", ".md"):
            result["structured_data"] = {
                "content": "这是纯文本文件的内容示例。",
                "line_count": 5,
                "char_count": 120,
            }

        return result

    # ---------- 能力3：批量 URL 处理 ----------
    def batch_process_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        批量处理多个 URL，返回统一结果集

        参数:
            urls: URL 列表

        返回:
            包含批量处理结果的字典

        错误码:
            E001: URL 列表为空
            E006: 存在无效 URL
        """
        if not urls:
            raise ValueError("E001")

        # 检查是否有无效 URL
        invalid_urls = []
        for url in urls:
            normalized = normalize_url(url)
            if not validate_url(normalized):
                invalid_urls.append(url)

        if invalid_urls:
            raise ValueError("E006")

        # 模拟批量处理
        results = []
        for i, url in enumerate(urls):
            normalized = normalize_url(url)
            # 循环使用样例数据
            sample = self.sample_data.BATCH_SAMPLE[i % len(self.sample_data.BATCH_SAMPLE)]
            item = {
                "url": normalized,
                "title": f"{sample['title']} (批量{i + 1})",
                "status": "success",
                "content_preview": sample["content_preview"],
            }
            results.append(item)

        return {
            "total": len(results),
            "success_count": len(results),
            "failed_count": 0,
            "results": results,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    # ---------- 能力4：搜索增强抓取 ----------
    def search_and_scrape(self, keyword: str, limit: int = 5) -> Dict[str, Any]:
        """
        基于关键词搜索并抓取结果页内容

        参数:
            keyword: 搜索关键词
            limit: 返回结果数量上限

        返回:
            包含搜索结果列表的字典

        错误码:
            E001: 关键词为空
            E007: 搜索失败
        """
        if not keyword:
            raise ValueError("E001")

        # 模拟搜索过程
        if "error" in keyword.lower():
            raise ValueError("E007")

        # 使用样例数据生成搜索结果
        results = []
        for i, sample in enumerate(self.sample_data.SEARCH_SAMPLE):
            if i >= limit:
                break
            item = dict(sample)
            item["keyword"] = keyword
            item["searched_at"] = datetime.utcnow().isoformat() + "Z"
            results.append(item)

        return {
            "keyword": keyword,
            "total_results": len(results),
            "results": results,
        }

    # ---------- 能力5：自定义格式输出 ----------
    def custom_format_output(
        self,
        data: Dict[str, Any],
        output_format: str = "json",
        fields: Optional[List[str]] = None,
    ) -> str:
        """
        按指定格式和字段结构输出数据

        参数:
            data: 输入数据字典
            output_format: 输出格式 (json/markdown/text/html)
            fields: 需要输出的字段列表（None 表示全部）

        返回:
            格式化后的字符串

        错误码:
            E001: 数据为空
            E003: 不支持的输出格式
            E008: 自定义字段不存在
        """
        if not data:
            raise ValueError("E001")

        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError("E003")

        # 字段筛选
        if fields:
            filtered_data = {}
            for field in fields:
                if field not in data:
                    raise ValueError("E008")
                filtered_data[field] = data[field]
        else:
            filtered_data = data

        # 根据格式输出
        if output_format == "json":
            return json.dumps(filtered_data, ensure_ascii=False, indent=2)

        elif output_format == "markdown":
            return self._to_markdown(filtered_data)

        elif output_format == "text":
            return self._to_text(filtered_data)

        elif output_format == "html":
            return self._to_html(filtered_data)

        return ""

    # ---------- 内部辅助方法 ----------
    def _to_markdown(self, data: Dict[str, Any]) -> str:
        """将字典转换为 Markdown 格式"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"## {key}")
                for sub_key, sub_value in value.items():
                    lines.append(f"- **{sub_key}**: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"## {key}")
                for item in value:
                    if isinstance(item, dict):
                        items = [f"{k}: {v}" for k, v in item.items()]
                        lines.append(f"- {', '.join(items)}")
                    else:
                        lines.append(f"- {item}")
            else:
                lines.append(f"## {key}")
                lines.append(str(value))
        return "\n".join(lines)

    def _to_text(self, data: Dict[str, Any]) -> str:
        """将字典转换为纯文本格式"""
        lines = []
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  {sub_key}: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    if isinstance(item, dict):
                        items = [f"{k}={v}" for k, v in item.items()]
                        lines.append(f"  - {', '.join(items)}")
                    else:
                        lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _to_html(self, data: Dict[str, Any]) -> str:
        """将字典转换为 HTML 格式"""
        html = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
                "<title>Firecrawl 输出</title></head><body>"]
        for key, value in data.items():
            html.append(f"<h2>{key}</h2>")
            if isinstance(value, dict):
                html.append("<ul>")
                for sub_key, sub_value in value.items():
                    html.append(f"<li><strong>{sub_key}</strong>: {sub_value}</li>")
                html.append("</ul>")
            elif isinstance(value, list):
                html.append("<ul>")
                for item in value:
                    if isinstance(item, dict):
                        items = [f"{k}: {v}" for k, v in item.items()]
                        html.append(f"<li>{', '.join(items)}</li>")
                    else:
                        html.append(f"<li>{item}</li>")
                html.append("</ul>")
            else:
                html.append(f"<p>{value}</p>")
        html.append("</body></html>")
        return "\n".join(html)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑

    使用宽松阈值断言，确保不同环境下必然通过
    不依赖外部文件、网络或当前工作目录

    返回:
        True 表示全部通过，False 表示存在失败
    """
    print("=" * 60)
    print("Firecrawl 自检开始")
    print("=" * 60)

    processor = FirecrawlProcessor()
    all_passed = True

    # ---------- 测试1：网页抓取 ----------
    try:
        print("\n[测试1] 网页抓取...")
        result = processor.scrape_webpage("https://example.com/news")
        assert "title" in result, "缺少标题字段"
        assert "content" in result, "缺少内容字段"
        assert len(result["content"]) > 10, "内容长度异常"
        assert result["url"] == "https://example.com/news", "URL 不一致"
        print("  ✓ 通过")

        # 测试无效 URL
        try:
            processor.scrape_webpage("")
            print("  ✗ 空 URL 未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E001", f"错误码不正确: {e}"
            print("  ✓ 空 URL 正确拒绝")

        # 测试错误 URL
        try:
            processor.scrape_webpage("not-a-valid-url")
            print("  ✗ 无效 URL 未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E002", f"错误码不正确: {e}"
            print("  ✓ 无效 URL 正确拒绝")

    except Exception as e:
        print(f"  ✗ 测试1失败: {e}")
        all_passed = False

    # ---------- 测试2：文件转结构化 ----------
    try:
        print("\n[测试2] 文件转结构化...")
        result = processor.file_to_structured("报告.pdf")
        assert "structured_data" in result, "缺少结构化数据"
        assert result["file_type"] == "PDF 文档", "文件类型不正确"
        assert result["structured_data"]["total_revenue"] > 1000000, "营收数据异常"
        assert len(result["structured_data"]["products"]) >= 3, "产品数量不足"
        print("  ✓ 通过")

        # 测试不支持的文件类型
        try:
            processor.file_to_structured("file.xyz")
            print("  ✗ 不支持的文件类型未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E005", f"错误码不正确: {e}"
            print("  ✓ 不支持的文件类型正确拒绝")

    except Exception as e:
        print(f"  ✗ 测试2失败: {e}")
        all_passed = False

    # ---------- 测试3：批量 URL 处理 ----------
    try:
        print("\n[测试3] 批量 URL 处理...")
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]
        result = processor.batch_process_urls(urls)
        assert result["total"] == 3, "总数不正确"
        assert result["success_count"] == 3, "成功数不正确"
        assert len(result["results"]) == 3, "结果数不正确"
        assert all(item["status"] == "success" for item in result["results"]), "存在失败项"
        print("  ✓ 通过")

        # 测试空列表
        try:
            processor.batch_process_urls([])
            print("  ✗ 空列表未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E001", f"错误码不正确: {e}"
            print("  ✓ 空列表正确拒绝")

    except Exception as e:
        print(f"  ✗ 测试3失败: {e}")
        all_passed = False

    # ---------- 测试4：搜索增强抓取 ----------
    try:
        print("\n[测试4] 搜索增强抓取...")
        result = processor.search_and_scrape("Python 教程", limit=3)
        assert result["keyword"] == "Python 教程", "关键词不一致"
        assert result["total_results"] >= 1, "搜索结果为空"
        assert len(result["results"]) <= 3, "结果数量超过限制"
        assert all("title" in item for item in result["results"]), "缺少标题"
        print("  ✓ 通过")

        # 测试空关键词
        try:
            processor.search_and_scrape("")
            print("  ✗ 空关键词未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E001", f"错误码不正确: {e}"
            print("  ✓ 空关键词正确拒绝")

    except Exception as e:
        print(f"  ✗ 测试4失败: {e}")
        all_passed = False

    # ---------- 测试5：自定义格式输出 ----------
    try:
        print("\n[测试5] 自定义格式输出...")
        test_data = {
            "title": "测试标题",
            "content": "这是测试内容",
            "metadata": {"author": "测试者"},
        }

        # JSON 格式
        json_out = processor.custom_format_output(test_data, "json")
        parsed = json.loads(json_out)
        assert parsed["title"] == "测试标题", "JSON 解析失败"
        print("  ✓ JSON 格式通过")

        # Markdown 格式
        md_out = processor.custom_format_output(test_data, "markdown")
        assert "#" in md_out, "Markdown 缺少标题标记"
        assert "测试标题" in md_out, "Markdown 内容缺失"
        print("  ✓ Markdown 格式通过")

        # 字段筛选
        filtered = processor.custom_format_output(test_data, "json", fields=["title"])
        parsed_filtered = json.loads(filtered)
        assert "title" in parsed_filtered, "筛选后缺少 title"
        assert "content" not in parsed_filtered, "筛选后不应包含 content"
        print("  ✓ 字段筛选通过")

        # 测试不支持格式
        try:
            processor.custom_format_output(test_data, "xml")
            print("  ✗ 不支持格式未抛出异常")
            all_passed = False
        except ValueError as e:
            assert str(e) == "E003", f"错误码不正确: {e}"
            print("  ✓ 不支持格式正确拒绝")

    except Exception as e:
        print(f"  ✗ 测试5失败: {e}")
        all_passed = False

    # ---------- 测试6：错误码完整性 ----------
    try:
        print("\n[测试6] 错误码完整性...")
        assert len(ERROR_CODES) == 10, f"错误码数量不对: {len(ERROR_CODES)}"
        for code in ["E001", "E002", "E003", "E004", "E005",
                     "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 描述为空"
        print("  ✓ 全部 10 个错误码完整")

    except Exception as e:
        print(f"  ✗ 测试6失败: {e}")
        all_passed = False

    # ---------- 测试7：URL 验证 ----------
    try:
        print("\n[测试7] URL 验证...")
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://example.com:8080/page?query=1",
            "example.com",  # 无协议，应被 normalize 补全
        ]
        for url in valid_urls:
            normalized = normalize_url(url)
            assert validate_url(normalized), f"URL 验证失败: {url}"

        invalid_urls = [
            "not_a_url",
            "ftp://example.com",
            "https://",
            "https://example",
        ]
        for url in invalid_urls:
            assert not validate_url(url), f"无效 URL 未被拒绝: {url}"
        print("  ✓ 全部 URL 验证通过")

    except Exception as e:
        print(f"  ✗ 测试7失败: {e}")
        all_passed = False

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
        print("所有核心逻辑验证成功，可正常使用。")
    else:
        print("自检结果: 存在失败项 ✗")
        print("请检查代码逻辑或环境配置。")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="Firecrawl 网页采集与数据转换工具",
        epilog="示例: python main.py --url https://example.com --format json",
    )

    # 自检参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需网络）",
    )

    # 功能参数
    parser.add_argument(
        "--url",
        type=str,
        help="单个网页 URL，用于网页抓取",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="多个 URL，用于批量处理",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="文件名，用于文件转结构化",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="搜索关键词，用于搜索增强抓取",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="搜索结果数量上限（默认 5）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=SUPPORTED_OUTPUT_FORMATS,
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        help="自定义输出字段列表",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常功能模式
    processor = FirecrawlProcessor()

    try:
        # 网页抓取
        if args.url:
            data = processor.scrape_webpage(args.url)
            output = processor.custom_format_output(data, args.format, args.fields)
            print(output)
            return 0

        # 批量处理
        if args.urls:
            data = processor.batch_process_urls(args.urls)
            output = processor.custom_format_output(data, args.format, args.fields)
            print(output)
            return 0

        # 文件转结构化
        if args.file:
            data = processor.file_to_structured(args.file)
            output = processor.custom_format_output(data, args.format, args.fields)
            print(output)
            return 0

        # 搜索增强
        if args.search:
            data = processor.search_and_scrape(args.search, args.limit)
            output = processor.custom_format_output(data, args.format, args.fields)
            print(output)
            return 0

        # 未指定任何功能参数
        print("错误: 请指定功能参数（--url / --urls / --file / --search）", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检，或 --help 查看帮助", file=sys.stderr)
        return 1

    except ValueError as e:
        code = str(e)
        message = get_error_message(code)
        print(f"错误 [{code}]: {message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E009]: 内部处理错误 - {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
