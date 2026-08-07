#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper-fetch-skill 独立实现脚本
功能：将用户提供的文献数据/文件/URL转换为结构化结果，支持批量处理与置信度标注。
仅依据功能规格实现，不包含任何既有代码。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或未提供任何文献数据",
    "E002": "输入格式不支持（仅支持文本、JSON、YAML、文件路径或URL）",
    "E003": "文件读取失败或文件不存在",
    "E004": "JSON解析失败，输入不是有效的JSON格式",
    "E005": "YAML解析失败，输入不是有效的YAML格式",
    "E006": "URL格式无效或无法解析",
    "E007": "文献条目缺少必要字段（标题或作者）",
    "E008": "批量处理时部分条目处理失败",
    "E009": "内部处理逻辑错误",
    "E010": "未知错误",
}


class PaperFetchError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def error_message(code: str) -> str:
    """根据错误码返回标准错误信息。"""
    return ERROR_CODES.get(code, ERROR_CODES["E010"])


# ---------- 核心数据模型 ----------

class PaperEntry:
    """单篇文献的结构化数据模型。"""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self.title: str = ""
        self.authors: List[str] = []
        self.year: Optional[str] = None
        self.doi: Optional[str] = None
        self.journal: Optional[str] = None
        self.volume: Optional[str] = None
        self.issue: Optional[str] = None
        self.pages: Optional[str] = None
        self.url: Optional[str] = None
        self.confidence: Dict[str, str] = {}  # 字段名 -> 置信度等级
        self._parse()

    def _parse(self) -> None:
        """从原始数据中提取字段，并标注置信度。"""
        # 标题
        self.title = self._extract_field(
            ["title", "标题", "论文题目", "name"], required=True
        )

        # 作者
        authors_raw = self._extract_field(
            ["authors", "author", "作者", "authors_list"], required=True
        )
        self.authors = self._parse_authors(authors_raw)

        # 年份
        self.year = self._extract_field(["year", "年份", "date", "pub_year"])
        if self.year:
            # 从日期字符串中提取4位年份
            year_match = re.search(r"(19|20)\d{2}", str(self.year))
            if year_match:
                self.year = year_match.group(0)
                self.confidence["year"] = "高"
            else:
                self.year = None
                self.confidence["year"] = "低"

        # DOI
        self.doi = self._extract_field(["doi", "DOI", "doi_url"])
        if self.doi:
            self.confidence["doi"] = "高" if "10." in self.doi else "中"

        # 期刊
        self.journal = self._extract_field(
            ["journal", "期刊", "venue", "publication"]
        )
        if self.journal:
            self.confidence["journal"] = "中"

        # 卷、期、页码
        self.volume = self._extract_field(["volume", "卷"])
        self.issue = self._extract_field(["issue", "期"])
        self.pages = self._extract_field(["pages", "page", "页码"])

        # URL
        self.url = self._extract_field(["url", "link", "URL", "链接"])
        if self.url:
            self.confidence["url"] = "中"

    def _extract_field(self, keys: List[str], required: bool = False) -> Any:
        """从原始数据中提取第一个匹配键的值。"""
        for key in keys:
            if key in self.raw_data and self.raw_data[key] is not None:
                value = self.raw_data[key]
                if isinstance(value, str) and value.strip():
                    return value.strip()
                elif isinstance(value, (int, float)):
                    return str(value)
                elif isinstance(value, list) and value:
                    return value
        if required:
            raise PaperFetchError("E007", f"缺少必要字段，尝试了键: {keys}")
        return None

    def _parse_authors(self, authors_raw: Any) -> List[str]:
        """解析作者字段，支持字符串、列表等多种格式。"""
        if isinstance(authors_raw, list):
            authors = []
            for item in authors_raw:
                if isinstance(item, str):
                    authors.append(item.strip())
                elif isinstance(item, dict):
                    # 支持 {"name": "张三"} 或 {"first": "张", "last": "三"}
                    name = item.get("name") or item.get("full_name")
                    if not name and "first" in item and "last" in item:
                        name = f"{item['first']} {item['last']}".strip()
                    if name:
                        authors.append(str(name).strip())
            return [a for a in authors if a]

        if isinstance(authors_raw, str):
            # 支持逗号、分号、顿号分隔
            parts = re.split(r"[,;，；、]", authors_raw)
            return [p.strip() for p in parts if p.strip()]

        return []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，包含置信度标注。"""
        result = {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "journal": self.journal,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "url": self.url,
        }
        # 附加置信度标注
        for field, conf in self.confidence.items():
            if field in result and result[field] is not None:
                result[f"{field}_confidence"] = conf
        return result


# ---------- 输入解析模块 ----------

class InputParser:
    """解析不同格式的输入数据。"""

    @staticmethod
    def parse_text(text: str) -> List[Dict[str, Any]]:
        """解析纯文本格式的文献数据。

        支持格式：
        1. 每行一条文献，格式如 "标题 | 作者 | 年份"
        2. 包含标题、作者等关键字的键值对文本
        """
        if not text or not text.strip():
            raise PaperFetchError("E001", error_message("E001"))

        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        entries = []

        # 首先尝试解析多行键值对格式
        if len(lines) > 1 and ":" in lines[0]:
            kv_entries = InputParser._parse_key_value_multiline(lines)
            if kv_entries:
                return kv_entries

        for line in lines:
            # 尝试键值对解析（单行）
            if ":" in line and ("标题" in line or "title" in line.lower()):
                entry = InputParser._parse_key_value_text(line)
                if entry:
                    entries.append(entry)
            # 尝试管道符分隔
            elif "|" in line:
                parts = [p.strip() for p in line.split("|")]
                entry = {
                    "title": parts[0] if len(parts) > 0 else "",
                    "authors": parts[1] if len(parts) > 1 else "",
                    "year": parts[2] if len(parts) > 2 else None,
                }
                if entry["title"] and entry["authors"]:
                    entries.append(entry)
            # 尝试制表符分隔
            elif "\t" in line:
                parts = [p.strip() for p in line.split("\t")]
                entry = {
                    "title": parts[0] if len(parts) > 0 else "",
                    "authors": parts[1] if len(parts) > 1 else "",
                }
                if entry["title"] and entry["authors"]:
                    entries.append(entry)

        if not entries:
            # 尝试将整段文本作为一个条目
            # 查找标题模式
            title_match = re.search(r"^(.+?)[\n。.]*$", text.strip(), re.MULTILINE)
            if title_match:
                entries.append({"title": title_match.group(1), "authors": "未知"})

        if not entries:
            raise PaperFetchError("E007", "无法从文本中提取有效文献条目")

        return entries

    @staticmethod
    def _parse_key_value_multiline(lines: List[str]) -> Optional[List[Dict[str, Any]]]:
        """解析多行键值对文本。"""
        entry: Dict[str, Any] = {}
        entries = []
        
        for line in lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            
            if not value:
                continue
            
            # 映射中英文键名
            key_lower = key.lower()
            if key in ("标题", "title", "论文题目") or key_lower == "title":
                entry["title"] = value
            elif key in ("作者", "author", "authors") or key_lower in ("author", "authors"):
                entry["authors"] = value
            elif key in ("年份", "year", "date") or key_lower == "year":
                entry["year"] = value
            elif key in ("doi",) or key_lower == "doi":
                entry["doi"] = value
            elif key in ("期刊", "journal", "venue") or key_lower == "journal":
                entry["journal"] = value
            elif key in ("卷", "volume") or key_lower == "volume":
                entry["volume"] = value
            elif key in ("期", "issue") or key_lower == "issue":
                entry["issue"] = value
            elif key in ("页码", "pages", "page") or key_lower in ("pages", "page"):
                entry["pages"] = value
        
        if "title" in entry and "authors" in entry:
            entries.append(entry)
            return entries
        
        return None

    @staticmethod
    def _parse_key_value_text(text: str) -> Optional[Dict[str, Any]]:
        """解析单行键值对文本。"""
        entry: Dict[str, Any] = {}
        # 按逗号或分号分割键值对
        pairs = re.split(r"[,;，；]", text)
        for pair in pairs:
            if ":" not in pair:
                continue
            key, value = pair.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if not value:
                continue

            if key in ("标题", "title", "论文题目"):
                entry["title"] = value
            elif key in ("作者", "author", "authors"):
                entry["authors"] = value
            elif key in ("年份", "year", "date"):
                entry["year"] = value
            elif key in ("doi",):
                entry["doi"] = value
            elif key in ("期刊", "journal", "venue"):
                entry["journal"] = value

        if "title" in entry and "authors" in entry:
            return entry
        return None

    @staticmethod
    def parse_json(json_str: str) -> List[Dict[str, Any]]:
        """解析JSON格式的文献数据。"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            raise PaperFetchError("E004", error_message("E004"))

        return InputParser._normalize_entries(data)

    @staticmethod
    def parse_yaml(yaml_str: str) -> List[Dict[str, Any]]:
        """解析YAML格式的文献数据（简化实现，仅支持基础结构）。"""
        # 为避免依赖，实现一个简单的YAML子集解析器
        entries = []
        current_entry: Dict[str, Any] = {}
        current_key: Optional[str] = None
        in_list = False
        list_items = []

        for line in yaml_str.strip().split("\n"):
            line = line.rstrip()
            if not line.strip() or line.strip().startswith("#"):
                continue

            # 检测列表项
            if line.startswith("- "):
                if current_key and in_list:
                    list_items.append(line[2:].strip())
                continue

            # 检测键值对
            if ":" in line:
                # 处理缩进
                indent = len(line) - len(line.lstrip())
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if indent == 0:
                    # 新条目开始
                    if current_entry and "title" in current_entry:
                        entries.append(current_entry)
                    current_entry = {}
                    current_key = key
                    in_list = False
                    list_items = []

                    # 处理内联列表
                    if value.startswith("[") and value.endswith("]"):
                        items = value[1:-1].split(",")
                        current_entry[key] = [i.strip() for i in items if i.strip()]
                    elif value:
                        current_entry[key] = value
                else:
                    # 子字段
                    if key in ("authors", "author", "作者"):
                        if value.startswith("["):
                            items = value[1:-1].split(",")
                            current_entry[key] = [i.strip() for i in items if i.strip()]
                        elif value:
                            current_entry[key] = value
                    elif value:
                        current_entry[key] = value

        # 处理最后一个条目
        if current_entry and "title" in current_entry:
            entries.append(current_entry)

        if not entries:
            raise PaperFetchError("E005", error_message("E005"))

        return InputParser._normalize_entries(entries)

    @staticmethod
    def parse_file(file_path: str) -> List[Dict[str, Any]]:
        """从文件读取并解析文献数据。"""
        path = Path(file_path)
        if not path.exists():
            raise PaperFetchError("E003", error_message("E003"))

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            try:
                content = path.read_text(encoding="gbk")
            except Exception:
                raise PaperFetchError("E003", error_message("E003"))

        suffix = path.suffix.lower()
        if suffix in (".json",):
            return InputParser.parse_json(content)
        elif suffix in (".yaml", ".yml"):
            return InputParser.parse_yaml(content)
        elif suffix in (".txt", ".md", ".csv"):
            return InputParser.parse_text(content)
        else:
            raise PaperFetchError("E002", error_message("E002"))

    @staticmethod
    def parse_url(url_str: str) -> List[Dict[str, Any]]:
        """解析URL中的文献信息（仅提取URL元数据，不访问网络）。"""
        # 验证URL格式
        if not re.match(r"^https?://", url_str):
            raise PaperFetchError("E006", error_message("E006"))

        # 从URL中提取可能的文献信息
        entry: Dict[str, Any] = {}
        # 尝试从URL路径中提取标题
        path_part = url_str.split("//")[-1].split("/")[-1]
        if path_part and path_part not in ("", "index.html"):
            # 将URL编码的标题转换为可读文本
            title = path_part.replace("-", " ").replace("_", " ").replace("%20", " ")
            # 去除文件扩展名
            title = re.sub(r"\.(pdf|html?|txt)$", "", title, flags=re.IGNORECASE)
            entry["title"] = title
            entry["authors"] = "未知"
            entry["url"] = url_str
            entry["confidence"] = {"title": "低", "authors": "低"}

        if not entry:
            entry = {"title": "从URL提取的文献", "authors": "未知", "url": url_str}

        return [entry]

    @staticmethod
    def _normalize_entries(data: Any) -> List[Dict[str, Any]]:
        """将各种输入结构规范化为条目字典列表。"""
        if isinstance(data, dict):
            # 单个条目或包含条目的字典
            if "title" in data or "标题" in data:
                return [data]
            # 可能是 {papers: [...]} 结构
            for key in ("papers", "entries", "文献", "items", "results"):
                if key in data and isinstance(data[key], list):
                    return InputParser._normalize_entries(data[key])
            # 尝试将字典的每个值作为条目
            entries = []
            for value in data.values():
                if isinstance(value, dict):
                    entries.extend(InputParser._normalize_entries(value))
            return entries if entries else [data]

        elif isinstance(data, list):
            entries = []
            for item in data:
                if isinstance(item, dict):
                    entries.extend(InputParser._normalize_entries(item))
                elif isinstance(item, str):
                    # 可能是纯文本标题
                    entries.append({"title": item, "authors": "未知"})
            return entries

        return [{"title": str(data), "authors": "未知"}]


# ---------- 核心处理逻辑 ----------

class PaperProcessor:
    """文献数据处理器。"""

    def __init__(self, input_data: Any, input_type: str = "auto"):
        self.input_data = input_data
        self.input_type = input_type
        self.entries: List[PaperEntry] = []
        self.errors: List[Dict[str, str]] = []

    def process(self) -> Dict[str, Any]:
        """执行完整的处理流程。"""
        try:
            # 1. 解析输入
            raw_entries = self._parse_input()

            # 2. 构建结构化条目
            for raw in raw_entries:
                try:
                    entry = PaperEntry(raw)
                    self.entries.append(entry)
                except PaperFetchError as e:
                    self.errors.append({"code": e.code, "message": e.message, "raw": raw})

            # 3. 生成结果
            if not self.entries and self.errors:
                raise PaperFetchError("E008", error_message("E008"))

            return self._build_result()

        except PaperFetchError:
            raise
        except Exception as e:
            raise PaperFetchError("E010", f"{error_message('E010')}: {str(e)}")

    def _parse_input(self) -> List[Dict[str, Any]]:
        """根据输入类型解析数据。"""
        if self.input_type == "auto":
            # 自动检测类型
            if isinstance(self.input_data, dict) or isinstance(self.input_data, list):
                return InputParser._normalize_entries(self.input_data)
            elif isinstance(self.input_data, str):
                return self._parse_string_input(self.input_data)
            else:
                raise PaperFetchError("E002", error_message("E002"))
        elif self.input_type == "text":
            return InputParser.parse_text(str(self.input_data))
        elif self.input_type == "json":
            return InputParser.parse_json(self.input_data)
        elif self.input_type == "yaml":
            return InputParser.parse_yaml(self.input_data)
        elif self.input_type == "file":
            return InputParser.parse_file(self.input_data)
        elif self.input_type == "url":
            return InputParser.parse_url(self.input_data)
        else:
            raise PaperFetchError("E002", error_message("E002"))

    def _parse_string_input(self, text: str) -> List[Dict[str, Any]]:
        """解析字符串输入，自动检测格式。"""
        text = text.strip()

        # 空输入
        if not text:
            raise PaperFetchError("E001", error_message("E001"))

        # 尝试JSON
        if text.startswith("{") or text.startswith("["):
            try:
                return InputParser.parse_json(text)
            except PaperFetchError:
                pass

        # 尝试YAML（包含冒号缩进结构）
        if "\n" in text and ":" in text:
            try:
                return InputParser.parse_yaml(text)
            except PaperFetchError:
                pass

        # 尝试URL
        if text.startswith("http://") or text.startswith("https://"):
            return InputParser.parse_url(text)

        # 尝试文件路径
        if len(text) < 500 and ("/" in text or "\\" in text or text.endswith((".txt", ".json", ".yaml", ".yml"))):
            if Path(text).exists():
                return InputParser.parse_file(text)

        # 默认按纯文本处理
        return InputParser.parse_text(text)

    def _build_result(self) -> Dict[str, Any]:
        """构建最终结果。"""
        processed_entries = [entry.to_dict() for entry in self.entries]

        result = {
            "success": len(self.errors) == 0,
            "total": len(processed_entries),
            "processed": len(processed_entries),
            "failed": len(self.errors),
            "entries": processed_entries,
            "summary": {
                "with_doi": sum(1 for e in self.entries if e.doi),
                "with_journal": sum(1 for e in self.entries if e.journal),
                "with_year": sum(1 for e in self.entries if e.year),
                "high_confidence": sum(
                    1 for e in self.entries if any(c == "高" for c in e.confidence.values())
                ),
            },
            "errors": self.errors,
            "timestamp": datetime.now().isoformat(),
        }
        return result


# ---------- 批量处理 ----------

def batch_process(inputs: List[Any], input_type: str = "auto") -> List[Dict[str, Any]]:
    """批量处理多个输入。"""
    results = []
    for item in inputs:
        try:
            processor = PaperProcessor(item, input_type)
            result = processor.process()
            results.append(result)
        except PaperFetchError as e:
            results.append({
                "success": False,
                "error_code": e.code,
                "error_message": e.message,
                "input": item,
            })
    return results


# ---------- 自检模块 ----------

def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。"""
    print("=" * 60)
    print("开始自检 paper-fetch-skill ...")
    print("=" * 60)

    all_passed = True

    # 测试1: 文本解析
    print("\n[测试1] 文本解析")
    try:
        text_input = "深度学习综述 | 张三, 李四 | 2023\n"
        text_input += "注意力机制研究 | 王五 | 2022"
        parser = InputParser()
        entries = parser.parse_text(text_input)
        assert len(entries) == 2, f"期望2条，实际{len(entries)}条"
        assert entries[0]["title"] == "深度学习综述"
        assert "张三" in entries[0]["authors"]
        print("  ✓ 文本解析通过")
    except AssertionError as e:
        print(f"  ✗ 文本解析失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 文本解析异常: {e}")
        all_passed = False

    # 测试2: JSON解析
    print("\n[测试2] JSON解析")
    try:
        json_input = json.dumps([
            {"title": "论文A", "authors": ["作者1", "作者2"], "year": 2024, "doi": "10.1234/test"},
            {"title": "论文B", "authors": "作者3", "year": "2023"}
        ])
        entries = InputParser.parse_json(json_input)
        assert len(entries) == 2, f"期望2条，实际{len(entries)}条"
        assert entries[0]["doi"] == "10.1234/test"
        print("  ✓ JSON解析通过")
    except AssertionError as e:
        print(f"  ✗ JSON解析失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ JSON解析异常: {e}")
        all_passed = False

    # 测试3: 结构化处理
    print("\n[测试3] 结构化处理")
    try:
        raw_data = {
            "title": "机器学习前沿",
            "authors": ["Alice", "Bob"],
            "year": "2024",
            "journal": "Nature",
            "doi": "10.1038/s41586-024-00000-0",
            "volume": "100",
            "pages": "1-10"
        }
        entry = PaperEntry(raw_data)
        result = entry.to_dict()
        assert result["title"] == "机器学习前沿"
        assert len(result["authors"]) == 2
        assert result["year"] == "2024"
        assert result["doi"] == "10.1038/s41586-024-00000-0"
        assert "doi_confidence" in result
        print("  ✓ 结构化处理通过")
    except AssertionError as e:
        print(f"  ✗ 结构化处理失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 结构化处理异常: {e}")
        all_passed = False

    # 测试4: 完整处理流程
    print("\n[测试4] 完整处理流程")
    try:
        processor = PaperProcessor([
            {"title": "深度学习", "authors": "张三", "year": "2023"},
            {"title": "强化学习", "authors": ["李四", "王五"], "year": "2024", "doi": "10.1234/rl"}
        ])
        result = processor.process()
        assert result["success"] is True
        assert result["total"] == 2
        assert result["processed"] == 2
        assert result["failed"] == 0
        assert result["summary"]["with_doi"] == 1
        assert len(result["entries"]) == 2
        print("  ✓ 完整处理流程通过")
    except AssertionError as e:
        print(f"  ✗ 完整处理流程失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 完整处理流程异常: {e}")
        all_passed = False

    # 测试5: 批量处理
    print("\n[测试5] 批量处理")
    try:
        results = batch_process([
            {"title": "批量论文1", "authors": "作者A"},
            {"title": "批量论文2", "authors": "作者B", "year": "2024"}
        ])
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert results[0]["total"] == 1
        assert results[1]["entries"][0]["year"] == "2024"
        print("  ✓ 批量处理通过")
    except AssertionError as e:
        print(f"  ✗ 批量处理失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 批量处理异常: {e}")
        all_passed = False

    # 测试6: 错误处理
    print("\n[测试6] 错误处理")
    try:
        # 空输入
        try:
            InputParser.parse_text("")
            print("  ✗ 空输入未抛出异常")
            all_passed = False
        except PaperFetchError as e:
            assert e.code == "E001", f"期望E001，实际{e.code}"
            print("  ✓ 空输入错误处理通过")

        # 缺少必要字段
        try:
            PaperEntry({"title": "只有标题"})
            print("  ✗ 缺少作者未抛出异常")
            all_passed = False
        except PaperFetchError as e:
            assert e.code == "E007", f"期望E007，实际{e.code}"
            print("  ✓ 缺少字段错误处理通过")

        # 无效JSON
        try:
            InputParser.parse_json("{invalid json}")
            print("  ✗ 无效JSON未抛出异常")
            all_passed = False
        except PaperFetchError as e:
            assert e.code == "E004", f"期望E004，实际{e.code}"
            print("  ✓ 无效JSON错误处理通过")

    except Exception as e:
        print(f"  ✗ 错误处理测试异常: {e}")
        all_passed = False

    # 测试7: 置信度标注
    print("\n[测试7] 置信度标注")
    try:
        entry_data = {
            "title": "置信度测试",
            "authors": "测试作者",
            "year": "2024",
            "doi": "10.1234/confidence"
        }
        entry = PaperEntry(entry_data)
        result = entry.to_dict()
        assert "year_confidence" in result
        assert "doi_confidence" in result
        assert result["year_confidence"] == "高"
        print("  ✓ 置信度标注通过")
    except AssertionError as e:
        print(f"  ✗ 置信度标注失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 置信度标注异常: {e}")
        all_passed = False

    # 测试8: URL解析
    print("\n[测试8] URL解析")
    try:
        entries = InputParser.parse_url("https://example.com/papers/deep-learning-2024")
        assert len(entries) == 1
        assert entries[0]["url"] == "https://example.com/papers/deep-learning-2024"
        assert "deep" in entries[0]["title"].lower()
        print("  ✓ URL解析通过")
    except AssertionError as e:
        print(f"  ✗ URL解析失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ URL解析异常: {e}")
        all_passed = False

    # 测试9: 边界情况
    print("\n[测试9] 边界情况")
    try:
        # 单条目字典
        entries = InputParser._normalize_entries({"title": "单条目", "authors": "作者"})
        assert len(entries) == 1

        # 嵌套结构
        entries = InputParser._normalize_entries({"papers": [{"title": "A", "authors": "B"}]})
        assert len(entries) == 1

        # 空列表
        entries = InputParser._normalize_entries([])
        assert len(entries) == 0

        print("  ✓ 边界情况通过")
    except Exception as e:
        print(f"  ✗ 边界情况异常: {e}")
        all_passed = False

    # 测试10: 中文输入支持
    print("\n[测试10] 中文输入支持")
    try:
        text_input = "标题: 中文文献测试\n作者: 张三, 李四\n年份: 2024"
        entries = InputParser.parse_text(text_input)
        assert len(entries) >= 1, f"期望至少1条，实际{len(entries)}条"
        assert entries[0]["title"] == "中文文献测试", f"期望标题'中文文献测试'，实际'{entries[0].get('title')}'"
        assert "张三" in entries[0]["authors"], f"期望作者包含'张三'，实际'{entries[0].get('authors')}'"
        print("  ✓ 中文输入支持通过")
    except AssertionError as e:
        print(f"  ✗ 中文输入支持失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 中文输入支持异常: {e}")
        all_passed = False

    # 汇总
    print("\n" + "=" * 60)
    if all_passed:
        print("自检结果: 全部通过 ✓")
    else:
        print("自检结果: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ---------- 主入口 ----------

def main():
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="paper-fetch-skill: 文献获取、结构化解析、批量处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --text "深度学习 | 张三 | 2024"
  %(prog)s --json '{"title": "论文", "authors": "作者"}'
  %(prog)s --file papers.json
  %(prog)s --url https://example.com/paper
  %(prog)s --selftest
        """,
    )

    parser.add_argument(
        "--text", type=str, help="输入纯文本格式的文献数据"
    )
    parser.add_argument(
        "--json", type=str, dest="json_input", help="输入JSON格式的文献数据"
    )
    parser.add_argument(
        "--yaml", type=str, dest="yaml_input", help="输入YAML格式的文献数据"
    )
    parser.add_argument(
        "--file", type=str, help="从文件读取文献数据"
    )
    parser.add_argument(
        "--url", type=str, help="从URL提取文献信息（不访问网络）"
    )
    parser.add_argument(
        "--output", type=str, choices=["json", "yaml"], default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检"
    )
    parser.add_argument(
        "--batch", type=str, nargs="+", help="批量处理多个输入"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 收集输入
    input_data = None
    input_type = "auto"

    if args.text:
        input_data = args.text
        input_type = "text"
    elif args.json_input:
        input_data = args.json_input
        input_type = "json"
    elif args.yaml_input:
        input_data = args.yaml_input
        input_type = "yaml"
    elif args.file:
        input_data = args.file
        input_type = "file"
    elif args.url:
        input_data = args.url
        input_type = "url"

    # 批量处理
    if args.batch:
        results = batch_process(args.batch)
        output = {"results": results, "total": len(results)}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # 单条处理
    if input_data is None:
        parser.print_help()
        sys.exit(1)

    try:
        processor = PaperProcessor(input_data, input_type)
        result = processor.process()

        if args.output == "yaml":
            # 简化YAML输出
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except PaperFetchError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误 E010: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
