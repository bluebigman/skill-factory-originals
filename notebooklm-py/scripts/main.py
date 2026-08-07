#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notebooklm-py 独立实现脚本（clean-room 重写）

功能：
- 将用户提供的文本、文件路径或 URL 转换为结构化结果
- 支持批量处理与置信度标注
- 内置离线自检（--selftest），不依赖外部环境

仅使用 Python 标准库，无任何第三方依赖。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或无效",
    "E002": "文件不存在或无法读取",
    "E003": "URL 格式无效",
    "E004": "文件扩展名不支持",
    "E005": "JSON 解析失败",
    "E006": "CSV 解析失败",
    "E007": "批量处理中存在失败项",
    "E008": "输出模板格式错误",
    "E009": "内部逻辑错误",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


@dataclass
class FieldInfo:
    """单个字段的结构化信息"""
    key: str
    value: Any
    confidence: str = "高"  # 高/中/低
    source: str = "input"   # input/derived/unknown


@dataclass
class StructuredResult:
    """结构化输出结果"""
    title: str = ""
    author: str = ""
    date: str = ""
    key_points: List[str] = field(default_factory=list)
    raw_text: str = ""
    fields: List[FieldInfo] = field(default_factory=list)
    confidence_overall: str = "高"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "author": self.author,
            "date": self.date,
            "key_points": self.key_points,
            "raw_text_preview": self.raw_text[:200] if self.raw_text else "",
            "fields": [asdict(f) for f in self.fields],
            "confidence_overall": self.confidence_overall,
        }


class TextParser:
    """纯文本解析器：从文本中提取关键字段"""

    # 常见标题模式
    TITLE_PATTERNS = [
        r"^#\s+(.+)$",                    # Markdown 一级标题
        r"^标题[:：]\s*(.+)$",             # 中文标题
        r"^Title[:：]\s*(.+)$",            # 英文标题
        r"^《(.+)》",                      # 书名号
    ]

    # 常见作者模式
    AUTHOR_PATTERNS = [
        r"^作者[:：]\s*(.+)$",
        r"^Author[:：]\s*(.+)$",
        r"^[（(]?\s*作者\s*[)）]?[:：]\s*(.+)$",
    ]

    # 常见日期模式
    DATE_PATTERNS = [
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
    ]

    # 要点提取模式
    POINT_PATTERNS = [
        r"^[-\*]\s+(.+)$",                # 列表项
        r"^\d+[.、]\s*(.+)$",             # 数字列表
        r"^要点[:：]\s*(.+)$",             # 显式要点
    ]

    def __init__(self, text: str):
        if not text or not text.strip():
            raise SkillError("E001")
        self.text = text.strip()
        self.lines = self.text.splitlines()

    def extract_title(self) -> str:
        """提取标题"""
        for pattern in self.TITLE_PATTERNS:
            for line in self.lines:
                m = re.match(pattern, line.strip())
                if m:
                    return m.group(1).strip()
        # 默认取第一行非空内容
        for line in self.lines:
            if line.strip():
                return line.strip()[:50]
        return ""

    def extract_author(self) -> str:
        """提取作者"""
        for pattern in self.AUTHOR_PATTERNS:
            for line in self.lines:
                m = re.match(pattern, line.strip())
                if m:
                    return m.group(1).strip()
        return ""

    def extract_date(self) -> str:
        """提取日期"""
        for pattern in self.DATE_PATTERNS:
            m = re.search(pattern, self.text)
            if m:
                return m.group(1)
        return ""

    def extract_key_points(self) -> List[str]:
        """提取关键要点"""
        points = []
        for pattern in self.POINT_PATTERNS:
            for line in self.lines:
                m = re.match(pattern, line.strip())
                if m:
                    point = m.group(1).strip()
                    if point and point not in points:
                        points.append(point)
        # 限制最多 10 条
        return points[:10]

    def parse(self) -> StructuredResult:
        """执行解析，返回结构化结果"""
        result = StructuredResult()
        result.raw_text = self.text
        result.title = self.extract_title()
        result.author = self.extract_author()
        result.date = self.extract_date()
        result.key_points = self.extract_key_points()

        # 构建字段列表
        result.fields.append(FieldInfo("title", result.title, "高" if result.title else "低"))
        result.fields.append(FieldInfo("author", result.author, "高" if result.author else "低"))
        result.fields.append(FieldInfo("date", result.date, "高" if result.date else "低"))
        result.fields.append(FieldInfo("key_points", result.key_points, "中" if result.key_points else "低"))

        # 计算整体置信度
        filled = sum(1 for f in result.fields if f.value)
        total = len(result.fields)
        ratio = filled / total if total > 0 else 0
        if ratio >= 0.75:
            result.confidence_overall = "高"
        elif ratio >= 0.4:
            result.confidence_overall = "中"
        else:
            result.confidence_overall = "低"

        return result


class FileParser:
    """文件解析器：根据扩展名分派到对应解析器"""

    SUPPORTED_EXT = {".txt", ".md", ".csv", ".json"}

    def __init__(self, filepath: str):
        self.filepath = filepath
        ext = self._get_ext()
        if ext not in self.SUPPORTED_EXT:
            raise SkillError("E004", f"不支持的文件类型: {ext}")

    def _get_ext(self) -> str:
        """获取文件扩展名（小写）"""
        parts = self.filepath.rsplit(".", 1)
        if len(parts) == 2:
            return f".{parts[1].lower()}"
        return ""

    def _read_file(self) -> str:
        """读取文件内容"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise SkillError("E002", f"文件不存在: {self.filepath}")
        except PermissionError:
            raise SkillError("E002", f"无读取权限: {self.filepath}")
        except Exception as e:
            raise SkillError("E010", f"读取文件失败: {str(e)}")

    def _parse_json(self, content: str) -> StructuredResult:
        """解析 JSON 内容"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise SkillError("E005")

        result = StructuredResult()
        result.raw_text = content
        # 从 JSON 中提取常见字段
        if isinstance(data, dict):
            result.title = str(data.get("title", data.get("标题", "")))
            result.author = str(data.get("author", data.get("作者", "")))
            result.date = str(data.get("date", data.get("日期", "")))
            points = data.get("key_points", data.get("要点", []))
            if isinstance(points, list):
                result.key_points = [str(p) for p in points[:10]]
            elif isinstance(points, str):
                result.key_points = [points]

            # 构建字段列表
            for key, value in data.items():
                if key in ("title", "author", "date", "key_points", "要点", "标题", "作者", "日期"):
                    continue
                result.fields.append(
                    FieldInfo(str(key), value, "高" if value is not None else "低")
                )

        result.confidence_overall = "高" if result.title else "中"
        return result

    def _parse_csv(self, content: str) -> StructuredResult:
        """解析 CSV 内容（简化处理，按行拆分）"""
        result = StructuredResult()
        result.raw_text = content
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            raise SkillError("E006")

        # 第一行作为标题，后续行作为要点
        result.title = lines[0]
        if len(lines) > 1:
            result.key_points = lines[1:11]
        result.confidence_overall = "中"
        return result

    def parse(self) -> StructuredResult:
        """根据扩展名分派解析"""
        content = self._read_file()
        ext = self._get_ext()
        if ext == ".json":
            return self._parse_json(content)
        elif ext == ".csv":
            return self._parse_csv(content)
        else:  # .txt / .md
            parser = TextParser(content)
            return parser.parse()


class URLParser:
    """URL 解析器：验证 URL 并提取信息（不实际访问网络）"""

    def __init__(self, url: str):
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise SkillError("E003", f"无效 URL: {url}")
        self.url = url
        self.parsed = parsed

    def parse(self) -> StructuredResult:
        """解析 URL 信息（仅提取 URL 本身的结构信息）"""
        result = StructuredResult()
        result.raw_text = self.url
        # 从 URL 路径提取可能的标题
        path = self.parsed.path.strip("/")
        if path:
            segments = [s for s in path.split("/") if s]
            if segments:
                result.title = segments[-1].replace("-", " ").replace("_", " ").title()
        if not result.title:
            result.title = self.parsed.netloc

        result.fields.append(FieldInfo("url", self.url, "高", "input"))
        result.fields.append(FieldInfo("domain", self.parsed.netloc, "高", "derived"))
        result.fields.append(FieldInfo("path", path, "中", "derived"))
        result.confidence_overall = "中"
        return result


class BatchProcessor:
    """批量处理器：支持多个输入源"""

    def __init__(self, inputs: List[str], input_type: str = "auto"):
        self.inputs = inputs
        self.input_type = input_type
        self.results: List[StructuredResult] = []
        self.errors: List[Dict[str, str]] = []

    def _detect_type(self, item: str) -> str:
        """自动检测输入类型"""
        if self.input_type != "auto":
            return self.input_type
        # 判断是否为 URL
        parsed = urlparse(item)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return "url"
        # 判断是否为文件路径
        if "." in item and not item.startswith((" ", "\t")):
            # 排除常见文本内容
            if not re.match(r"^[\s\S]{50,}$", item):
                return "file"
        return "text"

    def _process_one(self, item: str) -> Optional[StructuredResult]:
        """处理单个输入"""
        item_type = self._detect_type(item)
        try:
            if item_type == "url":
                parser = URLParser(item)
            elif item_type == "file":
                parser = FileParser(item)
            else:
                parser = TextParser(item)
            return parser.parse()
        except SkillError as e:
            self.errors.append({"input": item[:50], "code": e.code, "message": e.message})
            return None
        except Exception as e:
            self.errors.append({"input": item[:50], "code": "E010", "message": str(e)})
            return None

    def process(self) -> Dict[str, Any]:
        """执行批量处理"""
        for item in self.inputs:
            result = self._process_one(item)
            if result:
                self.results.append(result)

        output = {
            "total": len(self.inputs),
            "success": len(self.results),
            "failed": len(self.errors),
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
        }

        if self.errors and not self.results:
            raise SkillError("E007", "所有输入均处理失败")
        return output


def run_selftest() -> Dict[str, Any]:
    """离线自检：使用内置硬编码样例，不依赖外部环境"""
    test_results = {
        "name": "notebooklm-py selftest",
        "passed": True,
        "checks": [],
    }

    def check(name: str, condition: bool, detail: str = ""):
        test_results["checks"].append({
            "name": name,
            "passed": bool(condition),
            "detail": detail,
        })
        if not condition:
            test_results["passed"] = False

    # 测试1: 文本解析
    sample_text = """# 项目总结报告
作者：张三
日期：2025-03-15

- 完成了核心模块开发
- 修复了三个关键缺陷
- 性能提升了约40%
- 文档覆盖率达到了85%
"""
    try:
        parser = TextParser(sample_text)
        result = parser.parse()
        check("文本解析-标题提取", result.title == "项目总结报告", f"标题: {result.title}")
        check("文本解析-作者提取", result.author == "张三", f"作者: {result.author}")
        check("文本解析-日期提取", result.date == "2025-03-15", f"日期: {result.date}")
        check("文本解析-要点数量", len(result.key_points) >= 3, f"要点数: {len(result.key_points)}")
        check("文本解析-置信度", result.confidence_overall in ("高", "中", "低"), f"置信度: {result.confidence_overall}")
    except Exception as e:
        check("文本解析", False, str(e))

    # 测试2: URL 解析
    try:
        url_parser = URLParser("https://example.com/blog/notebooklm-tutorial")
        url_result = url_parser.parse()
        check("URL解析-域名", "example.com" in url_result.raw_text, f"域名: {url_result.fields[1].value}")
        check("URL解析-标题", len(url_result.title) > 0, f"标题: {url_result.title}")
    except Exception as e:
        check("URL解析", False, str(e))

    # 测试3: JSON 解析（使用临时内存模拟）
    try:
        json_content = '{"title": "测试文档", "author": "李四", "date": "2025-01-01", "tags": ["a", "b"]}'
        # 用临时文件模拟
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            tmp_path = f.name
        try:
            file_parser = FileParser(tmp_path)
            json_result = file_parser.parse()
            check("JSON解析-标题", json_result.title == "测试文档", f"标题: {json_result.title}")
            check("JSON解析-作者", json_result.author == "李四", f"作者: {json_result.author}")
            check("JSON解析-字段数", len(json_result.fields) >= 1, f"字段数: {len(json_result.fields)}")
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        check("JSON解析", False, str(e))

    # 测试4: 错误处理
    try:
        TextParser("")
        check("错误处理-空输入", False, "应该抛出 E001")
    except SkillError as e:
        check("错误处理-空输入", e.code == "E001", f"错误码: {e.code}")

    try:
        URLParser("not-a-valid-url")
        check("错误处理-无效URL", False, "应该抛出 E003")
    except SkillError as e:
        check("错误处理-无效URL", e.code == "E003", f"错误码: {e.code}")

    # 测试5: 批量处理
    try:
        batch = BatchProcessor([
            "这是一段普通文本内容",
            "https://example.com/page1",
            "不存在的文件.txt",
        ])
        batch_result = batch.process()
        check("批量处理-总数", batch_result["total"] == 3, f"总数: {batch_result['total']}")
        check("批量处理-成功数", batch_result["success"] >= 2, f"成功: {batch_result['success']}")
        check("批量处理-失败数", batch_result["failed"] >= 1, f"失败: {batch_result['failed']}")
    except Exception as e:
        check("批量处理", False, str(e))

    # 测试6: 宽松阈值验证
    check("自检-字段完整性", len(test_results["checks"]) >= 10, f"检查项: {len(test_results['checks'])}")
    passed_count = sum(1 for c in test_results["checks"] if c["passed"])
    check("自检-通过率", passed_count >= len(test_results["checks"]) * 0.7,
          f"通过 {passed_count}/{len(test_results['checks'])}")

    return test_results


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="notebooklm-py: 知识库笔记结构化处理工具",
        epilog="示例: python main.py -t '这是一段文本' | python main.py -f notes.txt | python main.py --selftest"
    )
    parser.add_argument("-t", "--text", help="要处理的文本内容")
    parser.add_argument("-f", "--file", help="要处理的文件路径 (txt/md/csv/json)")
    parser.add_argument("-u", "--url", help="要处理的 URL")
    parser.add_argument("-i", "--input", action="append", help="批量输入（可重复指定）")
    parser.add_argument("--type", choices=["auto", "text", "file", "url"], default="auto",
                        help="输入类型（默认自动检测）")
    parser.add_argument("-o", "--output", choices=["json", "text"], default="json",
                        help="输出格式（默认 json）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="notebooklm-py 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        result = run_selftest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["passed"] else 1)

    # 收集输入
    inputs = []
    if args.text:
        inputs.append(args.text)
    if args.file:
        inputs.append(args.file)
    if args.url:
        inputs.append(args.url)
    if args.input:
        inputs.extend(args.input)

    if not inputs:
        print("错误: 请提供输入内容 (-t/-f/-u/-i) 或使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(2)

    try:
        # 单输入直接处理
        if len(inputs) == 1:
            item = inputs[0]
            if args.type == "url" or (args.type == "auto" and urlparse(item).scheme in ("http", "https")):
                result = URLParser(item).parse()
            elif args.type == "file" or (args.type == "auto" and "." in item and len(item) < 200):
                try:
                    result = FileParser(item).parse()
                except SkillError as e:
                    if e.code == "E002" or e.code == "E004":
                        # 不是文件，当作文本处理
                        result = TextParser(item).parse()
                    else:
                        raise
            else:
                result = TextParser(item).parse()

            if args.output == "json":
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                # 文本输出
                print(f"标题: {result.title}")
                print(f"作者: {result.author}")
                print(f"日期: {result.date}")
                print(f"置信度: {result.confidence_overall}")
                if result.key_points:
                    print("要点:")
                    for p in result.key_points:
                        print(f"  - {p}")

        # 批量处理
        else:
            batch = BatchProcessor(inputs, args.type)
            result = batch.process()
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[E010] 未知错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
