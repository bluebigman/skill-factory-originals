#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公众号文章 - 本地优先的内容情报处理工具

本模块根据功能规格独立实现，提供：
- 输入内容的结构化解析
- 关键信息识别与置信度评估
- 批量处理与自定义输出格式
- 内置自检功能（--selftest）

错误码体系：
    E001 - 输入为空
    E002 - 关键信息缺失
    E003 - 输入格式错误
    E004 - 超出能力边界
    E005 - 置信度过低
    E006 - 输出格式不支持
    E007 - 批量处理中断
    E008 - 内部状态异常
    E009 - 参数解析错误
    E010 - 未知错误
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


# ============================================================
# 数据模型
# ============================================================

@dataclass
class Article:
    """文章数据模型"""
    title: str = ""
    author: str = ""
    content: str = ""
    url: str = ""
    publish_date: str = ""
    source: str = ""
    comments: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    raw_input: str = ""


@dataclass
class ProcessResult:
    """处理结果数据模型"""
    success: bool = False
    error_code: str = ""
    message: str = ""
    confidence: float = 0.0
    data: Optional[Article] = None
    warnings: List[str] = field(default_factory=list)


# ============================================================
# 核心处理逻辑
# ============================================================

class ArticleProcessor:
    """文章处理器 - 负责输入解析、结构化、置信度评估"""
    
    def __init__(self):
        self.supported_formats = ["json", "text", "markdown", "html"]
        self.required_fields = ["title", "content"]
        self.confidence_thresholds = {
            "high": 0.90,
            "medium": 0.85
        }
    
    def process(self, input_data: str, output_format: str = "json") -> ProcessResult:
        """主处理入口"""
        try:
            # 检查输入
            if not input_data or not input_data.strip():
                return ProcessResult(
                    success=False,
                    error_code="E001",
                    message="请提供待处理的内容，格式为：用户提供的数据/文件/URL"
                )
            
            # 检查输出格式
            if output_format not in self.supported_formats:
                return ProcessResult(
                    success=False,
                    error_code="E006",
                    message=f"输出格式 '{output_format}' 不支持，支持：{', '.join(self.supported_formats)}"
                )
            
            # 解析输入
            article, parse_warnings = self._parse_input(input_data)
            
            # 检查关键字段
            missing_fields = self._check_required_fields(article)
            if missing_fields:
                return ProcessResult(
                    success=False,
                    error_code="E002",
                    message=f"还缺少以下信息，请补充：{', '.join(missing_fields)}"
                )
            
            # 评估置信度
            confidence, confidence_warnings = self._evaluate_confidence(article)
            warnings = parse_warnings + confidence_warnings
            
            # 置信度检查
            if confidence < self.confidence_thresholds["medium"]:
                return ProcessResult(
                    success=False,
                    error_code="E005",
                    message=f"结果无法确定（置信度 {confidence:.0%}），建议：补充更多信息或人工核实",
                    confidence=confidence,
                    data=article,
                    warnings=warnings
                )
            
            # 格式化输出
            formatted_output = self._format_output(article, output_format)
            
            return ProcessResult(
                success=True,
                message="处理成功",
                confidence=confidence,
                data=article,
                warnings=warnings
            )
            
        except Exception as e:
            return ProcessResult(
                success=False,
                error_code="E010",
                message=f"处理过程中发生错误：{str(e)}"
            )
    
    def process_batch(self, inputs: List[str], output_format: str = "json") -> List[ProcessResult]:
        """批量处理多个输入"""
        results = []
        for idx, input_data in enumerate(inputs):
            try:
                result = self.process(input_data, output_format)
                results.append(result)
            except Exception as e:
                results.append(ProcessResult(
                    success=False,
                    error_code="E007",
                    message=f"批量处理第 {idx+1} 项失败：{str(e)}"
                ))
        return results
    
    def _parse_input(self, input_data: str) -> Tuple[Article, List[str]]:
        """解析输入数据为结构化文章对象"""
        warnings = []
        article = Article(raw_input=input_data[:500])  # 截断原始输入
        
        # 尝试多种解析方式
        input_data = input_data.strip()
        
        # 尝试 JSON 解析
        try:
            parsed = json.loads(input_data)
            if isinstance(parsed, dict):
                article.title = str(parsed.get("title", ""))
                article.author = str(parsed.get("author", ""))
                article.content = str(parsed.get("content", ""))
                article.url = str(parsed.get("url", ""))
                article.publish_date = str(parsed.get("publish_date", ""))
                article.source = str(parsed.get("source", ""))
                article.comments = parsed.get("comments", [])
                article.stats = parsed.get("stats", {})
                return article, warnings
        except json.JSONDecodeError:
            pass
        
        # 尝试 URL 格式
        if input_data.startswith(("http://", "https://")):
            article.url = input_data
            article.title = self._extract_url_title(input_data)
            warnings.append("URL 输入，仅提取基本信息，建议提供完整内容")
            return article, warnings
        
        # 尝试 Markdown 格式
        if input_data.startswith("#") or "##" in input_data:
            article = self._parse_markdown(input_data)
            return article, warnings
        
        # 尝试 HTML 格式
        if "<html" in input_data.lower() or "<article" in input_data.lower():
            article = self._parse_html(input_data)
            return article, warnings
        
        # 尝试纯文本格式
        article = self._parse_text(input_data)
        warnings.append("使用纯文本解析，可能遗漏部分结构化信息")
        return article, warnings
    
    def _parse_markdown(self, text: str) -> Article:
        """解析 Markdown 格式"""
        article = Article()
        lines = text.split("\n")
        
        # 提取标题（第一个 # 开头行）
        for line in lines:
            if line.startswith("#"):
                article.title = line.lstrip("#").strip()
                break
        
        # 提取作者（常见标记）
        for line in lines:
            if re.match(r"^\s*(作者|author)\s*[:：]", line, re.IGNORECASE):
                article.author = re.sub(r"^\s*(作者|author)\s*[:：]\s*", "", line, flags=re.IGNORECASE)
                break
        
        # 提取日期
        for line in lines:
            date_match = re.search(r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", line)
            if date_match:
                article.publish_date = date_match.group(1)
                break
        
        # 保留所有非空行作为内容
        content_lines = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
        article.content = "\n".join(content_lines)
        
        return article
    
    def _parse_html(self, html: str) -> Article:
        """解析 HTML 格式（简化版）"""
        article = Article()
        
        # 提取标题
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            article.title = title_match.group(1).strip()
        
        # 提取 meta 作者
        author_match = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if author_match:
            article.author = author_match.group(1)
        
        # 提取正文（简化处理，去除标签）
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
        if body_match:
            content = body_match.group(1)
            content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
            article.content = content
        
        return article
    
    def _parse_text(self, text: str) -> Article:
        """解析纯文本格式"""
        article = Article()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        if not lines:
            return article
        
        # 第一行作为标题（如果合理长度）
        if len(lines[0]) <= 100:
            article.title = lines[0]
            content_start = 1
        else:
            article.title = lines[0][:50] + "..." if len(lines[0]) > 50 else lines[0]
            content_start = 0
        
        # 查找作者行
        for i, line in enumerate(lines[:5]):
            if re.match(r"^(作者|author|by)\s*[:：]", line, re.IGNORECASE):
                article.author = re.sub(r"^(作者|author|by)\s*[:：]\s*", "", line, flags=re.IGNORECASE)
                break
        
        # 内容为剩余行
        article.content = "\n".join(lines[content_start:])
        
        return article
    
    def _extract_url_title(self, url: str) -> str:
        """从 URL 提取简单标题"""
        # 从 URL 路径提取文件名
        path = url.rstrip("/").split("/")[-1]
        if path and not path.startswith("?"):
            return path.replace("-", " ").replace("_", " ").title()
        return "未命名文章"
    
    def _check_required_fields(self, article: Article) -> List[str]:
        """检查必填字段"""
        missing = []
        for field_name in self.required_fields:
            value = getattr(article, field_name, "")
            if not value or not value.strip():
                missing.append(field_name)
        return missing
    
    def _evaluate_confidence(self, article: Article) -> Tuple[float, List[str]]:
        """评估数据置信度"""
        warnings = []
        score = 0.0
        checks = 0
        
        # 标题检查
        if article.title:
            score += 1
            if len(article.title) < 5:
                warnings.append("标题过短，可能不完整")
                score += 0.5
        else:
            warnings.append("缺少标题")
        checks += 1
        
        # 内容检查
        if article.content:
            score += 1
            content_len = len(article.content)
            if content_len < 50:
                warnings.append("内容过短，可能信息不完整")
                score += 0.3
            elif content_len < 200:
                score += 0.7
            else:
                score += 1.0
        else:
            warnings.append("缺少正文内容")
        checks += 1
        
        # 作者检查（非必填）
        if article.author:
            score += 1
        else:
            warnings.append("缺少作者信息")
        checks += 1
        
        # URL 检查（非必填）
        if article.url and article.url.startswith("http"):
            score += 1
        else:
            warnings.append("缺少来源 URL")
        checks += 1
        
        # 日期检查（非必填）
        if article.publish_date:
            score += 1
        else:
            warnings.append("缺少发布日期")
        checks += 1
        
        # 计算最终置信度
        confidence = score / checks if checks > 0 else 0.0
        
        # 附加警告
        if confidence < 0.85:
            warnings.append("整体置信度偏低，建议人工复核关键信息")
        elif confidence >= 0.90:
            pass  # 高质量数据
        
        return min(confidence, 1.0), warnings
    
    def _format_output(self, article: Article, output_format: str) -> str:
        """格式化输出"""
        if output_format == "json":
            return json.dumps(asdict(article), ensure_ascii=False, indent=2)
        elif output_format == "markdown":
            return self._to_markdown(article)
        elif output_format == "html":
            return self._to_html(article)
        else:
            return self._to_text(article)
    
    def _to_markdown(self, article: Article) -> str:
        """转换为 Markdown 格式"""
        md = []
        if article.title:
            md.append(f"# {article.title}")
        if article.author:
            md.append(f"\n> 作者：{article.author}")
        if article.publish_date:
            md.append(f"> 日期：{article.publish_date}")
        if article.url:
            md.append(f"> 来源：{article.url}")
        if article.content:
            md.append(f"\n{article.content}")
        return "\n".join(md)
    
    def _to_html(self, article: Article) -> str:
        """转换为 HTML 格式"""
        html = ["<!DOCTYPE html>", "<html>", "<head>"]
        if article.title:
            html.append(f"<title>{article.title}</title>")
        html.append("</head><body>")
        if article.title:
            html.append(f"<h1>{article.title}</h1>")
        if article.author:
            html.append(f"<p>作者：{article.author}</p>")
        if article.publish_date:
            html.append(f"<p>日期：{article.publish_date}</p>")
        if article.url:
            html.append(f"<p>来源：<a href='{article.url}'>{article.url}</a></p>")
        if article.content:
            html.append(f"<div>{article.content}</div>")
        html.append("</body></html>")
        return "\n".join(html)
    
    def _to_text(self, article: Article) -> str:
        """转换为纯文本格式"""
        text = []
        if article.title:
            text.append(f"标题：{article.title}")
        if article.author:
            text.append(f"作者：{article.author}")
        if article.publish_date:
            text.append(f"日期：{article.publish_date}")
        if article.url:
            text.append(f"来源：{article.url}")
        if article.content:
            text.append(f"\n{article.content}")
        return "\n".join(text)


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """内置自检逻辑，使用硬编码样例数据验证核心功能"""
    print("开始自检...")
    processor = ArticleProcessor()
    all_passed = True
    
    # 测试用例 1：JSON 格式输入
    print("\n测试 1: JSON 格式输入")
    json_input = json.dumps({
        "title": "测试文章标题",
        "author": "测试作者",
        "content": "这是一篇用于测试的文章内容。" * 10,
        "url": "https://example.com/article/1",
        "publish_date": "2026-01-01",
        "source": "测试来源"
    })
    result = processor.process(json_input, "json")
    assert result.success, f"JSON 处理失败: {result.message}"
    assert result.confidence >= 0.85, f"置信度过低: {result.confidence}"
    assert result.data is not None and result.data.title == "测试文章标题"
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    # 测试用例 2：Markdown 格式输入
    print("\n测试 2: Markdown 格式输入")
    md_input = """# Markdown测试文章
> 作者：张三
> 日期：2026-02-15

这是第一段内容。
这是第二段内容。
"""
    result = processor.process(md_input, "markdown")
    assert result.success, f"Markdown 处理失败: {result.message}"
    assert result.data is not None and result.data.title == "Markdown测试文章"
    assert result.data.author == "张三"
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    # 测试用例 3：纯文本格式输入
    print("\n测试 3: 纯文本格式输入")
    text_input = """这是一篇纯文本测试文章

作者：李四

正文内容开始，包含足够长度的文字来满足置信度评估要求。
这里继续补充更多内容，确保整体长度超过阈值。
"""
    result = processor.process(text_input, "text")
    assert result.success, f"文本处理失败: {result.message}"
    assert result.data is not None and len(result.data.content) > 50
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    # 测试用例 4：错误处理 - 空输入
    print("\n测试 4: 空输入错误处理")
    result = processor.process("", "json")
    assert not result.success, "空输入应该失败"
    assert result.error_code == "E001", f"错误码错误: {result.error_code}"
    print(f"  通过 (错误码: {result.error_code})")
    
    # 测试用例 5：错误处理 - 缺少关键字段
    print("\n测试 5: 缺少关键字段")
    incomplete_input = json.dumps({"author": "某人"})
    result = processor.process(incomplete_input, "json")
    assert not result.success, "缺少关键字段应该失败"
    assert result.error_code == "E002", f"错误码错误: {result.error_code}"
    print(f"  通过 (错误码: {result.error_code})")
    
    # 测试用例 6：批量处理
    print("\n测试 6: 批量处理")
    batch_inputs = [
        json.dumps({"title": "文章1", "content": "内容1" * 30}),
        json.dumps({"title": "文章2", "content": "内容2" * 30}),
        "无效输入"
    ]
    results = processor.process_batch(batch_inputs, "json")
    assert len(results) == 3, f"批量处理数量错误: {len(results)}"
    success_count = sum(1 for r in results if r.success)
    assert success_count >= 2, f"成功数量过少: {success_count}"
    print(f"  通过 (成功 {success_count}/3)")
    
    # 测试用例 7：置信度评估
    print("\n测试 7: 置信度评估")
    low_conf_input = json.dumps({"title": "短标题", "content": "短内容"})
    result = processor.process(low_conf_input, "json")
    # 内容太短可能置信度低，但不应该报错
    assert result.confidence < 0.90, f"置信度应该偏低: {result.confidence}"
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    # 测试用例 8：HTML 格式输入
    print("\n测试 8: HTML 格式输入")
    html_input = """<html>
<head><title>HTML测试文章</title></head>
<body>
<article>
<h1>HTML测试文章</h1>
<p>这是HTML格式的测试内容。</p>
</article>
</body>
</html>"""
    result = processor.process(html_input, "json")
    assert result.success, f"HTML 处理失败: {result.message}"
    assert result.data is not None and result.data.title == "HTML测试文章"
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    # 测试用例 9：输出格式验证
    print("\n测试 9: 输出格式验证")
    json_input = json.dumps({
        "title": "格式测试",
        "content": "内容内容内容内容内容内容内容内容内容内容内容内容内容内容内容"
    })
    for fmt in ["json", "markdown", "html", "text"]:
        result = processor.process(json_input, fmt)
        assert result.success, f"格式 {fmt} 处理失败"
        assert result.data is not None
    print("  通过 (4种格式均正常)")
    
    # 测试用例 10：URL 输入
    print("\n测试 10: URL 输入")
    url_input = "https://mp.weixin.qq.com/s/example123456"
    result = processor.process(url_input, "json")
    assert result.success, f"URL 处理失败: {result.message}"
    assert result.data is not None and result.data.url == url_input
    print(f"  通过 (置信度: {result.confidence:.2%})")
    
    print("\n全部自检通过！")
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="公众号文章 - 本地优先的内容情报处理工具",
        epilog="示例：python main.py --input '{\"title\":\"测试\",\"content\":\"内容\"}' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（JSON/Markdown/HTML/纯文本/URL）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default="json",
        choices=["json", "markdown", "html", "text"],
        help="输出格式（默认：json）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理文件路径（每行一个输入）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自检异常: {e}")
            sys.exit(1)
    
    # 批量处理模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                inputs = [line.strip() for line in f if line.strip()]
            processor = ArticleProcessor()
            results = processor.process_batch(inputs, args.format)
            for idx, result in enumerate(results, 1):
                status = "✓" if result.success else "✗"
                print(f"{idx}. [{status}] {result.message}")
                if result.data:
                    print(f"   标题: {result.data.title}")
                    print(f"   置信度: {result.confidence:.1%}")
            sys.exit(0 if all(r.success for r in results) else 1)
        except FileNotFoundError:
            print(f"错误：找不到文件 {args.batch}")
            sys.exit(1)
        except Exception as e:
            print(f"批量处理异常: {e}")
            sys.exit(1)
    
    # 单条处理模式
    if not args.input:
        parser.print_help()
        print("\n错误：请提供输入内容（--input）或使用 --selftest 自检")
        sys.exit(1)
    
    processor = ArticleProcessor()
    result = processor.process(args.input, args.format)
    
    if result.success:
        print(f"处理成功（置信度 {result.confidence:.1%}）")
        print("=" * 50)
        if result.data:
            print(processor._format_output(result.data, args.format))
        if result.warnings:
            print("\n警告：")
            for warning in result.warnings:
                print(f"  - {warning}")
    else:
        print(f"处理失败：{result.message}")
        print(f"错误码：{result.error_code}")
        sys.exit(1)


if __name__ == "__main__":
    main()
