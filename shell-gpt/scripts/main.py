#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell-gpt 命令行智能助手 - 独立实现脚本

功能概述：
    1. 自然语言转命令：将中文/英文描述转换为可执行的 shell 命令
    2. 数据文件结构化：从 CSV、JSON、日志等文件中提取关键字段并重组
    3. URL 内容摘要：抓取网页正文并提炼要点
    4. 批量任务编排：对多文件/多输入执行同一套处理逻辑
    5. 输出格式定制：按指定格式（表格、JSON、Markdown）输出结果

设计原则：
    - 仅依据功能规格独立实现（clean-room）
    - 标准库优先，无第三方依赖
    - 错误处理统一使用错误码 E001-E010
    - 提供 --selftest 参数进行离线自检

作者：终端工坊
版本：1.0.1
许可证：MIT
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件不存在：指定的文件路径无法找到",
    "E003": "文件读取失败：文件存在但无法读取内容",
    "E004": "文件解析失败：文件格式不符合预期",
    "E005": "URL 访问失败：无法获取 URL 内容",
    "E006": "输出格式错误：指定的输出格式不受支持",
    "E007": "批量处理失败：批量任务中某个环节出错",
    "E008": "命令生成失败：无法从自然语言生成有效命令",
    "E009": "数据提取失败：无法从数据源提取所需字段",
    "E010": "内部错误：发生未预期的异常",
}


def raise_error(code: str, detail: str = "") -> None:
    """抛出带错误码的异常"""
    message = ERROR_CODES.get(code, "未知错误")
    if detail:
        message = f"{message} - {detail}"
    raise RuntimeError(f"[{code}] {message}")


# ============================================================
# 核心功能模块
# ============================================================

class CommandGenerator:
    """自然语言转 shell 命令生成器"""
    
    # 常见命令模板库
    COMMAND_TEMPLATES = {
        "find_large_files": {
            "pattern": r"(最大|最大文件|biggest|largest).*(文件|file)",
            "command": "find . -type f -exec du -h {{}} + | sort -rh | head -n {count}",
            "default_count": 5,
        },
        "count_lines": {
            "pattern": r"(行数|多少行|count.*line)",
            "command": "wc -l {file}",
        },
        "extract_ip": {
            "pattern": r"(提取|提取IP|IP地址|ip address)",
            "command": "grep -oE '([0-9]{{1,3}}\\.){{3}}[0-9]{{1,3}}' {file} | sort -u",
        },
        "list_files": {
            "pattern": r"(列出|查看|list).*(文件|file)",
            "command": "ls -la {path}",
            "default_path": ".",
        },
        "find_text": {
            "pattern": r"(搜索|查找|查找文本|grep).*(内容|text|string)",
            "command": "grep -rn '{text}' {path}",
            "default_path": ".",
        },
        "backup_file": {
            "pattern": r"(备份|backup)",
            "command": "cp {source} {source}.bak",
        },
    }
    
    def __init__(self) -> None:
        """初始化命令生成器"""
        self.templates = self.COMMAND_TEMPLATES
    
    def generate(self, natural_language: str) -> str:
        """
        将自然语言转换为 shell 命令
        
        Args:
            natural_language: 自然语言描述
            
        Returns:
            生成的 shell 命令字符串
            
        Raises:
            E008: 无法生成有效命令
        """
        # 去除首尾空白并转小写（用于匹配）
        text = natural_language.strip()
        text_lower = text.lower()
        
        # 提取可能的参数
        count = self._extract_count(text)
        file_path = self._extract_file_path(text)
        
        # 匹配模板
        for template_name, template_info in self.templates.items():
            if re.search(template_info["pattern"], text_lower):
                command = template_info["command"]
                
                # 替换参数
                command = command.replace("{count}", str(count))
                command = command.replace("{file}", file_path or "file.txt")
                command = command.replace("{path}", file_path or template_info.get("default_path", "."))
                command = command.replace("{source}", file_path or "source.txt")
                
                # 提取文本搜索内容
                if "{text}" in command:
                    text_match = re.search(r"(?:搜索|查找|grep).*?['\"]([^'\"]+)['\"]", text)
                    search_text = text_match.group(1) if text_match else "pattern"
                    command = command.replace("{text}", search_text)
                
                return command
        
        # 未匹配到模板，尝试简单处理
        if "删除" in text or "remove" in text_lower:
            target = file_path or "file.txt"
            return f"rm -i {target}"
        
        if "重命名" in text or "rename" in text_lower:
            return f"mv {file_path or 'oldname'} newname"
        
        # 无法生成命令
        raise_error("E008", f"无法理解指令: {natural_language}")
        return ""  # 不可达，仅为类型检查
    
    def _extract_count(self, text: str) -> int:
        """从文本中提取数量参数"""
        # 查找数字
        match = re.search(r"(\d+)\s*(个|条|行)?", text)
        if match:
            return int(match.group(1))
        return 5  # 默认值
    
    def _extract_file_path(self, text: str) -> Optional[str]:
        """从文本中提取文件路径"""
        # 查找引号中的路径
        match = re.search(r"['\"]([^'\"]+\.\w+)['\"]", text)
        if match:
            return match.group(1)
        
        # 查找常见的文件路径模式
        match = re.search(r"([\w./-]+\.\w+)", text)
        if match:
            return match.group(1)
        
        return None


class DataProcessor:
    """数据文件结构化处理"""
    
    def __init__(self) -> None:
        """初始化数据处理模块"""
        self.supported_formats = ["csv", "json", "log"]
    
    def process(self, file_path: str, fields: List[str], output_format: str = "json") -> str:
        """
        从数据文件中提取指定字段并重组
        
        Args:
            file_path: 数据文件路径
            fields: 需要提取的字段列表
            output_format: 输出格式 (json/csv/markdown)
            
        Returns:
            结构化处理后的数据字符串
            
        Raises:
            E002: 文件不存在
            E003: 文件读取失败
            E004: 文件解析失败
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise_error("E002", f"文件不存在: {file_path}")
        
        # 读取文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise_error("E003", f"无法读取文件: {str(e)}")
        
        # 根据文件类型解析
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        
        if file_ext == "csv":
            data = self._parse_csv(content)
        elif file_ext == "json":
            data = self._parse_json(content)
        elif file_ext in ["log", "txt"]:
            data = self._parse_log(content)
        else:
            # 尝试自动识别
            data = self._auto_parse(content, file_ext)
        
        # 提取字段
        extracted = self._extract_fields(data, fields)
        
        # 格式化输出
        return self._format_output(extracted, output_format)
    
    def _parse_csv(self, content: str) -> List[Dict[str, str]]:
        """解析 CSV 内容"""
        try:
            reader = csv.DictReader(content.splitlines())
            return [row for row in reader]
        except Exception as e:
            raise_error("E004", f"CSV 解析失败: {str(e)}")
        return []
    
    def _parse_json(self, content: str) -> Union[List, Dict]:
        """解析 JSON 内容"""
        try:
            return json.loads(content)
        except Exception as e:
            raise_error("E004", f"JSON 解析失败: {str(e)}")
        return {}
    
    def _parse_log(self, content: str) -> List[Dict[str, str]]:
        """解析日志内容（简单日志格式）"""
        lines = content.strip().splitlines()
        result = []
        
        for line in lines:
            # 尝试提取常见字段
            entry = {
                "line": line,
                "timestamp": self._extract_timestamp(line),
                "level": self._extract_level(line),
                "message": line,
            }
            result.append(entry)
        
        return result
    
    def _auto_parse(self, content: str, file_ext: str) -> List[Dict[str, str]]:
        """自动识别并解析文件内容"""
        # 尝试 JSON
        if content.strip().startswith("{"):
            return self._parse_json(content)
        
        # 尝试 CSV
        if "," in content.splitlines()[0]:
            return self._parse_csv(content)
        
        # 默认按日志处理
        return self._parse_log(content)
    
    def _extract_timestamp(self, line: str) -> str:
        """提取时间戳"""
        # 匹配常见时间格式
        patterns = [
            r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}",
            r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}",
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(0)
        return ""
    
    def _extract_level(self, line: str) -> str:
        """提取日志级别"""
        match = re.search(r"\b(DEBUG|INFO|WARN|ERROR|FATAL)\b", line, re.IGNORECASE)
        return match.group(1).upper() if match else "INFO"
    
    def _extract_fields(self, data: Any, fields: List[str]) -> List[Dict[str, Any]]:
        """从数据中提取指定字段"""
        result = []
        
        # 处理列表数据
        if isinstance(data, list):
            for item in data:
                result.append(self._extract_from_item(item, fields))
        # 处理字典数据
        elif isinstance(data, dict):
            result.append(self._extract_from_item(data, fields))
        
        return result
    
    def _extract_from_item(self, item: Any, fields: List[str]) -> Dict[str, Any]:
        """从单个数据项中提取字段"""
        extracted = {}
        
        if isinstance(item, dict):
            for field in fields:
                extracted[field] = item.get(field, "")
        else:
            # 非字典类型，尝试按字段名匹配
            for field in fields:
                extracted[field] = item
        
        return extracted
    
    def _format_output(self, data: List[Dict[str, Any]], output_format: str) -> str:
        """格式化输出"""
        if output_format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif output_format == "csv":
            if not data:
                return ""
            fieldnames = list(data[0].keys())
            output = ",".join(fieldnames) + "\n"
            for row in data:
                output += ",".join(str(row.get(field, "")) for field in fieldnames) + "\n"
            return output
        
        elif output_format == "markdown":
            if not data:
                return ""
            fieldnames = list(data[0].keys())
            output = "| " + " | ".join(fieldnames) + " |\n"
            output += "|" + "|".join(["---"] * len(fieldnames)) + "|\n"
            for row in data:
                output += "| " + " | ".join(str(row.get(field, "")) for field in fieldnames) + " |\n"
            return output
        
        elif output_format == "table":
            return self._format_output(data, "markdown")
        
        else:
            raise_error("E006", f"不支持的输出格式: {output_format}")
            return ""
    
    def process_batch(self, file_paths: List[str], fields: List[str], output_format: str = "json") -> List[str]:
        """
        批量处理多个文件
        
        Args:
            file_paths: 文件路径列表
            fields: 需要提取的字段
            output_format: 输出格式
            
        Returns:
            每个文件的处理结果列表
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.process(file_path, fields, output_format)
                results.append(result)
            except Exception as e:
                raise_error("E007", f"批量处理失败: {file_path} - {str(e)}")
        return results


class URLSummarizer:
    """URL 内容摘要"""
    
    def __init__(self) -> None:
        """初始化 URL 摘要模块"""
        self.max_content_size = 10 * 1024 * 1024  # 10MB 限制
    
    def summarize(self, url: str, max_points: int = 5) -> Dict[str, Any]:
        """
        获取 URL 内容并生成摘要
        
        Args:
            url: 网页地址或本地文件路径
            max_points: 最大要点数量
            
        Returns:
            包含摘要信息的字典
            
        Raises:
            E005: URL 访问失败
        """
        try:
            # 检查是否为本地文件
            if url.startswith("file://"):
                # 处理 file:// 协议
                file_path = url[7:]  # 去掉 "file://" 前缀
                # 处理 Windows 路径
                if file_path.startswith("/") and ":" in file_path[1:3]:
                    file_path = file_path[1:]  # 去掉开头的 "/"
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif os.path.exists(url):
                # 直接作为文件路径处理
                with open(url, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                # 尝试作为 HTTP/HTTPS URL 处理
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read(self.max_content_size).decode("utf-8", errors="ignore")
        except Exception as e:
            raise_error("E005", f"无法访问 URL: {str(e)}")
        
        # 提取正文（简单实现：去除 HTML 标签）
        text = self._extract_text(content)
        
        # 生成摘要
        summary = self._generate_summary(text, max_points)
        
        # 提取标题
        title = self._extract_title(content)
        
        return {
            "url": url,
            "title": title,
            "summary": summary,
            "word_count": len(text.split()),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _extract_title(self, html: str) -> str:
        """提取网页标题"""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _extract_text(self, html: str) -> str:
        """从 HTML 中提取纯文本"""
        # 去除脚本和样式
        html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        
        # 去除 HTML 标签
        text = re.sub(r"<[^>]+>", " ", html)
        
        # 去除多余空白
        text = re.sub(r"\s+", " ", text)
        
        return text.strip()
    
    def _generate_summary(self, text: str, max_points: int) -> List[str]:
        """生成文本摘要（基于词频统计的简单实现）"""
        # 分词
        words = re.findall(r"\b\w+\b", text.lower())
        
        # 停用词
        stopwords = set([
            "the", "a", "an", "and", "or", "but", "if", "then", "else",
            "for", "to", "of", "in", "on", "at", "by", "with", "from",
            "is", "are", "was", "were", "be", "been", "being",
            "this", "that", "these", "those", "it", "its",
        ])
        
        # 统计词频
        word_freq = Counter(word for word in words if word not in stopwords and len(word) > 2)
        
        # 获取关键句子
        sentences = re.split(r"[.!?。！？]+", text)
        
        # 按关键词出现次数排序句子
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.strip()) < 20:
                continue
            score = sum(1 for word in sentence.lower().split() if word in word_freq)
            scored_sentences.append((score, sentence.strip()))
        
        scored_sentences.sort(reverse=True)
        
        # 返回得分最高的句子作为摘要
        summary = [sentence for _, sentence in scored_sentences[:max_points]]
        
        return summary if summary else ["无法生成摘要：内容过少"]


class OutputFormatter:
    """输出格式定制"""
    
    @staticmethod
    def format(data: Any, format_type: str) -> str:
        """
        按指定格式输出
        
        Args:
            data: 要格式化的数据
            format_type: 格式类型 (json/yaml/markdown/table/csv)
            
        Returns:
            格式化后的字符串
            
        Raises:
            E006: 不支持的格式
        """
        if format_type == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif format_type == "markdown":
            return OutputFormatter._to_markdown(data)
        
        elif format_type == "table":
            return OutputFormatter._to_table(data)
        
        elif format_type == "csv":
            return OutputFormatter._to_csv(data)
        
        else:
            raise_error("E006", f"不支持的输出格式: {format_type}")
            return ""
    
    @staticmethod
    def _to_markdown(data: Any) -> str:
        """转换为 Markdown 格式"""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # 表格形式
            headers = list(data[0].keys())
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            for row in data:
                lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
            return "\n".join(lines)
        
        elif isinstance(data, dict):
            # 键值对形式
            lines = []
            for key, value in data.items():
                lines.append(f"**{key}**: {value}")
            return "\n\n".join(lines)
        
        else:
            return str(data)
    
    @staticmethod
    def _to_table(data: Any) -> str:
        """转换为表格格式"""
        return OutputFormatter._to_markdown(data)
    
    @staticmethod
    def _to_csv(data: Any) -> str:
        """转换为 CSV 格式"""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            headers = list(data[0].keys())
            lines = [",".join(headers)]
            for row in data:
                lines.append(",".join(str(row.get(h, "")) for h in headers))
            return "\n".join(lines)
        
        return str(data)


# ============================================================
# 主程序
# ============================================================

class ShellGPT:
    """shell-gpt 主程序"""
    
    def __init__(self) -> None:
        """初始化各功能模块"""
        self.command_gen = CommandGenerator()
        self.data_processor = DataProcessor()
        self.url_summarizer = URLSummarizer()
        self.formatter = OutputFormatter()
    
    def run_command(self, natural_language: str) -> str:
        """执行自然语言转命令"""
        return self.command_gen.generate(natural_language)
    
    def process_data(self, file_path: str, fields: List[str], output_format: str) -> str:
        """执行数据处理"""
        return self.data_processor.process(file_path, fields, output_format)
    
    def summarize_url(self, url: str, max_points: int) -> Dict[str, Any]:
        """执行 URL 摘要"""
        return self.url_summarizer.summarize(url, max_points)
    
    def format_output(self, data: Any, format_type: str) -> str:
        """执行输出格式化"""
        return self.formatter.format(data, format_type)
    
    def process_batch(self, file_paths: List[str], fields: List[str], output_format: str) -> List[str]:
        """执行批量处理"""
        return self.data_processor.process_batch(file_paths, fields, output_format)


def selftest() -> bool:
    """
    离线自检核心逻辑
    
    Returns:
        True 表示所有测试通过
    """
    print("=" * 60)
    print("shell-gpt 自检程序")
    print("=" * 60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # ---------- 测试 1: 命令生成 ----------
        print("\n[测试 1] 自然语言转命令")
        gen = CommandGenerator()
        
        test_cases = [
            ("找出当前目录下最大的5个文件", "find"),
            ("统计 access.log 的行数", "wc"),
            ("提取 error.log 中的 IP 地址", "grep"),
        ]
        
        for desc, expected in test_cases:
            try:
                cmd = gen.generate(desc)
                assert expected in cmd, f"命令未包含 {expected}"
                print(f"  ✓ '{desc}' -> {cmd}")
            except Exception as e:
                print(f"  ✗ '{desc}' 失败: {e}")
                return False
        
        # ---------- 测试 2: 数据处理 ----------
        print("\n[测试 2] 数据处理")
        
        # 创建测试 CSV 文件
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("name,age,city\n")
            f.write("Alice,30,Beijing\n")
            f.write("Bob,25,Shanghai\n")
            f.write("Charlie,35,Shenzhen\n")
        
        processor = DataProcessor()
        
        # 测试 JSON 输出
        try:
            result = processor.process(csv_path, ["name", "age"], "json")
            data = json.loads(result)
            assert len(data) == 3, "应提取 3 条记录"
            assert data[0]["name"] == "Alice", "第一条记录姓名应为 Alice"
            print(f"  ✓ CSV 转 JSON 成功: {result}")
        except Exception as e:
            print(f"  ✗ CSV 转 JSON 失败: {e}")
            return False
        
        # 测试 Markdown 输出
        try:
            result = processor.process(csv_path, ["name", "city"], "markdown")
            assert "| name | city |" in result, "Markdown 表格头缺失"
            print(f"  ✓ CSV 转 Markdown 成功")
        except Exception as e:
            print(f"  ✗ CSV 转 Markdown 失败: {e}")
            return False
        
        # 测试错误处理
        try:
            processor.process(os.path.join(tmpdir, "nonexistent.csv"), ["name"], "json")
            print("  ✗ 应抛出 E002 错误")
            return False
        except RuntimeError as e:
            assert "E002" in str(e), "错误码应为 E002"
            print(f"  ✓ 错误处理正确: {e}")
        
        # ---------- 测试 3: URL 摘要 ----------
        print("\n[测试 3] URL 摘要")
        
        # 创建本地测试 HTML 文件
        html_path = os.path.join(tmpdir, "test.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("""
            <html>
            <head><title>测试页面</title></head>
            <body>
                <h1>Python 编程语言介绍</h1>
                <p>Python 是一种高级编程语言，广泛应用于 web 开发、数据分析、人工智能等领域。</p>
                <p>Python 的语法简洁清晰，易于学习，拥有丰富的第三方库支持。</p>
                <p>Python 社区活跃，文档完善，是初学者入门的理想选择。</p>
            </body>
            </html>
            """)
        
        # 使用 file:// 协议测试
        url = f"file://{html_path}"
        summarizer = URLSummarizer()
        
        try:
            result = summarizer.summarize(url, max_points=3)
            assert result["title"] == "测试页面", "标题提取失败"
            assert len(result["summary"]) > 0, "摘要为空"
            print(f"  ✓ URL 摘要成功: 标题='{result['title']}', 摘要点数={len(result['summary'])}")
        except Exception as e:
            print(f"  ✗ URL 摘要失败: {e}")
            return False
        
        # ---------- 测试 4: 批量处理 ----------
        print("\n[测试 4] 批量处理")
        
        # 创建第二个 CSV 文件
        csv_path2 = os.path.join(tmpdir, "test2.csv")
        with open(csv_path2, "w", encoding="utf-8") as f:
            f.write("name,age,city\n")
            f.write("David,40,Guangzhou\n")
        
        try:
            results = processor.process_batch([csv_path, csv_path2], ["name"], "json")
            assert len(results) == 2, "应返回 2 个结果"
            print(f"  ✓ 批量处理成功: 处理了 {len(results)} 个文件")
        except Exception as e:
            print(f"  ✗ 批量处理失败: {e}")
            return False
        
        # ---------- 测试 5: 输出格式化 ----------
        print("\n[测试 5] 输出格式化")
        formatter = OutputFormatter()
        
        test_data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        
        # JSON 格式
        json_out = formatter.format(test_data, "json")
        assert json.loads(json_out), "JSON 格式输出无效"
        print(f"  ✓ JSON 格式输出成功")
        
        # Markdown 格式
        md_out = formatter.format(test_data, "markdown")
        assert "| name | age |" in md_out, "Markdown 表格格式错误"
        print(f"  ✓ Markdown 格式输出成功")
        
        # CSV 格式
        csv_out = formatter.format(test_data, "csv")
        assert "name,age" in csv_out, "CSV 表头缺失"
        print(f"  ✓ CSV 格式输出成功")
        
        # 错误格式
        try:
            formatter.format(test_data, "yaml")
            print("  ✗ 应抛出 E006 错误")
            return False
        except RuntimeError as e:
            assert "E006" in str(e), "错误码应为 E006"
            print(f"  ✓ 错误格式处理正确: {e}")
    
    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return True


def main() -> int:
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="shell-gpt 命令行智能助手 - 将自然语言指令转化为可执行的命令行操作",
        epilog="示例: python main.py --command '找出当前目录下最大的5个文件'"
    )
    
    # 功能参数
    parser.add_argument(
        "--command", "-c",
        type=str,
        help="自然语言指令，转换为 shell 命令"
    )
    
    parser.add_argument(
        "--process", "-p",
        type=str,
        metavar="FILE",
        help="处理数据文件 (CSV/JSON/LOG)"
    )
    
    parser.add_argument(
        "--fields", "-f",
        type=str,
        nargs="+",
        help="需要提取的字段名列表"
    )
    
    parser.add_argument(
        "--url", "-u",
        type=str,
        help="获取 URL 内容并生成摘要"
    )
    
    parser.add_argument(
        "--max-points",
        type=int,
        default=5,
        help="URL 摘要的最大要点数量 (默认: 5)"
    )
    
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        metavar="FILE",
        help="批量处理多个文件"
    )
    
    # 输出参数
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "csv", "markdown", "table"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    # 其他参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检程序"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="shell-gpt 1.0.1"
    )
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = selftest()
        return 0 if success else 1
    
    # 创建主程序实例
    app = ShellGPT()
    
    try:
        # 处理自然语言转命令
        if args.command:
            cmd = app.run_command(args.command)
            print(cmd)
        
        # 处理数据文件
        elif args.process:
            if not args.fields:
                raise_error("E001", "处理数据文件时需要指定 --fields")
            result = app.process_data(args.process, args.fields, args.output)
            print(result)
        
        # 批量处理
        elif args.batch:
            if not args.fields:
                raise_error("E001", "批量处理时需要指定 --fields")
            results = app.process_batch(args.batch, args.fields, args.output)
            for i, result in enumerate(results):
                print(f"--- 文件 {i+1} ---")
                print(result)
        
        # URL 摘要
        elif args.url:
            result = app.summarize_url(args.url, args.max_points)
            print(app.format_output(result, args.output))
        
        else:
            parser.print_help()
            return 0
    
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 内部错误: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
