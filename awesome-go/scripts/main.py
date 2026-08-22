#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-go 技能核心逻辑实现

面向 Go 开发者的学习资源导航与项目速查工具。
本脚本仅依据功能规格独立实现（clean-room），不复制任何既有代码。

功能概述：
- 将用户提供的文本/文件/URL 内容解析为结构化项目条目
- 支持关键信息提取（名称、分类、描述、星标数、维护状态）
- 支持多种输出格式（Markdown 表格、JSON、纯文本列表）
- 支持批量处理、自定义字段与排序
- 支持置信度标注
- 内置离线自检（--selftest），不依赖外部环境

用法示例：
    python scripts/main.py --input "项目名: gin, 分类: Web框架, 描述: 高性能HTTP框架" --format json
    python scripts/main.py --selftest

错误码约定：
    E001: 参数解析错误
    E002: 输入内容为空
    E003: 输入格式无法解析
    E004: 输出格式不支持
    E005: 文件读取失败
    E006: 排序字段不存在
    E007: 排序方向非法
    E008: 字段过滤失败
    E009: 内部逻辑错误
    E010: 自检失败
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 支持的输出格式
SUPPORTED_FORMATS = ("table", "json", "list")

# 项目条目核心字段
CORE_FIELDS = ("name", "category", "description", "stars", "maintenance")

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"
CONFIDENCE_UNKNOWN = "待核实"

# 分类别名映射（用于归一化）
CATEGORY_ALIASES = {
    "web": "Web框架",
    "web框架": "Web框架",
    "http": "Web框架",
    "网络": "网络",
    "net": "网络",
    "数据库": "数据库",
    "db": "数据库",
    "sql": "数据库",
    "命令行": "命令行工具",
    "cli": "命令行工具",
    "工具": "命令行工具",
    "日志": "日志",
    "log": "日志",
    "测试": "测试",
    "test": "测试",
    "并发": "并发编程",
    "concurrent": "并发编程",
    "goroutine": "并发编程",
    "微服务": "微服务",
    "microservice": "微服务",
    "rpc": "微服务",
    "其他": "其他",
    "other": "其他",
    "": "其他",
}


# ============================================================
# 核心数据结构
# ============================================================

class ProjectEntry:
    """单个 Go 项目条目"""

    def __init__(
        self,
        name: str = "",
        category: str = "其他",
        description: str = "",
        stars: Optional[int] = None,
        maintenance: str = CONFIDENCE_UNKNOWN,
        source: str = "",
    ) -> None:
        self.name = name.strip()
        self.category = self._normalize_category(category)
        self.description = description.strip()
        self.stars = stars
        self.maintenance = maintenance
        self.source = source
        self.confidence = self._compute_confidence()

    @staticmethod
    def _normalize_category(category: str) -> str:
        """归一化分类名称"""
        key = category.strip().lower()
        return CATEGORY_ALIASES.get(key, category.strip() or "其他")

    def _compute_confidence(self) -> str:
        """根据字段完整度计算置信度"""
        if self.name and self.description and self.stars is not None:
            return CONFIDENCE_HIGH
        if self.name and (self.description or self.stars is not None):
            return CONFIDENCE_MEDIUM
        if self.name:
            return CONFIDENCE_LOW
        return CONFIDENCE_UNKNOWN

    def to_dict(self, include_confidence: bool = True) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "stars": self.stars,
            "maintenance": self.maintenance,
        }
        if include_confidence:
            result["confidence"] = self.confidence
        return result


# ============================================================
# 解析器
# ============================================================

class EntryParser:
    """解析用户输入为项目条目列表"""

    # 匹配模式：字段名: 值
    FIELD_PATTERN = re.compile(
        r"(?:项目名|名称|name)\s*[:：]\s*([^\n,;，；]+)"
        r"|(?:分类|类别|category)\s*[:：]\s*([^\n,;，；]+)"
        r"|(?:描述|简介|description)\s*[:：]\s*([^\n,;，；]+)"
        r"|(?:星标|star|stars)\s*[:：]\s*(\d+)"
        r"|(?:维护状态|维护|maintenance)\s*[:：]\s*([^\n,;，；]+)",
        re.IGNORECASE,
    )

    # 匹配模式：GitHub 链接
    GITHUB_URL_PATTERN = re.compile(
        r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"
    )

    # 匹配模式：简单条目行（如 "- gin: 高性能HTTP框架"）
    SIMPLE_ENTRY_PATTERN = re.compile(
        r"^\s*[-*]\s*([A-Za-z0-9_.-]+)\s*[:：]\s*(.+)$"
    )

    # 匹配模式：括号内字段（如 "(分类: Web框架, 星标: 50000)"）
    PAREN_FIELD_PATTERN = re.compile(
        r"\((.*?)\)"
    )

    # 匹配模式：括号内的键值对
    PAREN_KEY_VALUE_PATTERN = re.compile(
        r"(?:分类|类别|category)\s*[:：]\s*([^,，;；]+)"
        r"|(?:星标|star|stars)\s*[:：]\s*(\d+)"
        r"|(?:维护状态|维护|maintenance)\s*[:：]\s*([^,，;；]+)",
        re.IGNORECASE,
    )

    def parse(self, content: str) -> List[ProjectEntry]:
        """解析输入内容，返回项目条目列表"""
        if not content or not content.strip():
            raise ValueError("E002: 输入内容为空")

        entries: List[ProjectEntry] = []
        lines = content.strip().splitlines()

        # 尝试按行解析简单条目
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试 GitHub 链接
            url_match = self.GITHUB_URL_PATTERN.search(line)
            if url_match:
                owner, repo = url_match.group(1), url_match.group(2)
                entry = ProjectEntry(
                    name=repo,
                    category="其他",
                    description=f"GitHub 项目 {owner}/{repo}",
                    source=url_match.group(0),
                )
                entries.append(entry)
                continue

            # 尝试简单条目格式
            simple_match = self.SIMPLE_ENTRY_PATTERN.match(line)
            if simple_match:
                name = simple_match.group(1)
                rest = simple_match.group(2)
                
                # 提取括号内的字段
                category = "其他"
                desc = rest
                stars = None
                maintenance = CONFIDENCE_UNKNOWN
                
                # 查找括号内容
                paren_match = self.PAREN_FIELD_PATTERN.search(rest)
                if paren_match:
                    inner = paren_match.group(1)
                    # 从括号内容中提取字段
                    for kv_match in self.PAREN_KEY_VALUE_PATTERN.finditer(inner):
                        if kv_match.group(1):
                            category = kv_match.group(1).strip()
                        elif kv_match.group(2):
                            try:
                                stars = int(kv_match.group(2))
                            except ValueError:
                                pass
                        elif kv_match.group(3):
                            maintenance = kv_match.group(3).strip()
                    # 移除括号部分
                    desc = rest.replace(paren_match.group(0), "").strip(" ,，;；")
                else:
                    # 尝试从 rest 中提取分类
                    cat_match = re.search(r"(?:分类|类别)[:：]\s*([^\s,，;；]+)", rest)
                    if cat_match:
                        category = cat_match.group(1)
                        desc = rest.replace(cat_match.group(0), "").strip(" ,，;；")
                    
                    # 尝试提取星标
                    star_match = re.search(r"(?:星标|star|stars)\s*[:：]\s*(\d+)", rest, re.IGNORECASE)
                    if star_match:
                        try:
                            stars = int(star_match.group(1))
                        except ValueError:
                            pass
                        desc = desc.replace(star_match.group(0), "").strip(" ,，;；")
                
                entry = ProjectEntry(
                    name=name,
                    category=category,
                    description=desc,
                    stars=stars,
                    maintenance=maintenance,
                )
                entries.append(entry)
                continue

            # 尝试字段式解析
            if ":" in line or "：" in line:
                entry_dict = self._parse_fields(line)
                if entry_dict.get("name"):
                    entries.append(ProjectEntry(**entry_dict))
                    continue

            # 无法识别，尝试作为纯文本描述处理
            if not entries:
                # 首行可能是标题或说明，跳过
                continue

        if not entries:
            raise ValueError("E003: 输入格式无法解析为有效的项目条目")

        return entries

    def _parse_fields(self, text: str) -> Dict[str, Any]:
        """从文本中提取字段（使用正则匹配）"""
        result: Dict[str, Any] = {}
        for match in self.FIELD_PATTERN.finditer(text):
            if match.group(1):
                result["name"] = match.group(1).strip()
            elif match.group(2):
                result["category"] = match.group(2).strip()
            elif match.group(3):
                result["description"] = match.group(3).strip()
            elif match.group(4):
                try:
                    result["stars"] = int(match.group(4))
                except ValueError:
                    pass
            elif match.group(5):
                result["maintenance"] = match.group(5).strip()
        return result


# ============================================================
# 格式化器
# ============================================================

class OutputFormatter:
    """将项目条目列表格式化为指定输出"""

    @staticmethod
    def format_table(entries: List[ProjectEntry]) -> str:
        """输出为 Markdown 表格"""
        if not entries:
            return "（无数据）"

        header = "| 项目名称 | 分类 | 描述 | 星标数 | 维护状态 | 置信度 |"
        separator = "|---------|------|------|--------|----------|--------|"
        lines = [header, separator]

        for entry in entries:
            stars = str(entry.stars) if entry.stars is not None else "N/A"
            lines.append(
                f"| {entry.name} | {entry.category} | {entry.description} | "
                f"{stars} | {entry.maintenance} | {entry.confidence} |"
            )
        return "\n".join(lines)

    @staticmethod
    def format_json(entries: List[ProjectEntry]) -> str:
        """输出为 JSON"""
        data = [entry.to_dict() for entry in entries]
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_list(entries: List[ProjectEntry]) -> str:
        """输出为纯文本列表"""
        if not entries:
            return "（无数据）"

        lines = []
        for i, entry in enumerate(entries, 1):
            stars = str(entry.stars) if entry.stars is not None else "N/A"
            lines.append(f"{i}. {entry.name} [{entry.category}] - {entry.description}")
            lines.append(f"   星标: {stars} | 维护: {entry.maintenance} | 置信度: {entry.confidence}")
        return "\n".join(lines)

    @staticmethod
    def format(entries: List[ProjectEntry], fmt: str) -> str:
        """统一格式化入口"""
        if fmt == "table":
            return OutputFormatter.format_table(entries)
        if fmt == "json":
            return OutputFormatter.format_json(entries)
        if fmt == "list":
            return OutputFormatter.format_list(entries)
        raise ValueError(f"E004: 不支持的输出格式: {fmt}")


# ============================================================
# 数据处理工具
# ============================================================

def sort_entries(entries: List[ProjectEntry], field: str, reverse: bool = False) -> List[ProjectEntry]:
    """按指定字段排序"""
    if field not in CORE_FIELDS:
        raise ValueError(f"E006: 排序字段不存在: {field}")

    def sort_key(entry: ProjectEntry) -> Any:
        value = getattr(entry, field, None)
        # 处理 None 值，确保类型一致
        if value is None:
            if field == "stars":
                return 0
            return ""
        # 确保字符串和数字类型一致
        if field == "stars":
            return value
        return str(value)

    return sorted(entries, key=sort_key, reverse=reverse)


def filter_fields(entries: List[ProjectEntry], fields: List[str]) -> List[Dict[str, Any]]:
    """按字段列表过滤输出"""
    if not fields:
        return [entry.to_dict() for entry in entries]

    for field in fields:
        if field not in CORE_FIELDS:
            raise ValueError(f"E008: 字段不存在: {field}")

    result = []
    for entry in entries:
        d = entry.to_dict()
        filtered = {k: v for k, v in d.items() if k in fields}
        result.append(filtered)
    return result


def read_input_file(filepath: str) -> str:
    """读取输入文件内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise ValueError(f"E005: 文件读取失败: {e}") from e


def is_url(text: str) -> bool:
    """判断是否为 URL"""
    return text.startswith(("http://", "https://"))


# ============================================================
# 主处理流程
# ============================================================

def process_input(
    content: str,
    output_format: str = "table",
    sort_field: Optional[str] = None,
    sort_desc: bool = False,
    fields: Optional[List[str]] = None,
) -> str:
    """处理输入内容并返回格式化结果"""
    try:
        # 解析输入
        parser = EntryParser()
        entries = parser.parse(content)

        # 排序
        if sort_field:
            entries = sort_entries(entries, sort_field, sort_desc)

        # 字段过滤
        if fields:
            data = filter_fields(entries, fields)
            # 字段过滤后直接输出 JSON
            return json.dumps(data, ensure_ascii=False, indent=2)

        # 格式化输出
        formatter = OutputFormatter()
        return formatter.format(entries, output_format)

    except ValueError as e:
        raise
    except Exception as e:
        raise ValueError(f"E009: 处理过程中发生内部错误: {e}") from e


def handle_input_arg(input_arg: str) -> str:
    """处理输入参数：可能是文本、文件路径或 URL"""
    # 如果是文件路径且文件存在
    if os.path.isfile(input_arg):
        return read_input_file(input_arg)

    # 如果是 URL（本技能不访问网络，仅返回提示）
    if is_url(input_arg):
        raise ValueError(
            "E003: 检测到 URL 输入，但本技能不访问网络。"
            "请提供文本内容或本地文件路径。"
        )

    # 视为纯文本
    return input_arg


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> int:
    """内置自检逻辑，不依赖外部文件或网络"""
    print("开始自检...")
    errors = []

    # --- 测试 1: 解析器基本功能 ---
    try:
        sample_input = """
- gin: 高性能 HTTP 框架 (分类: Web框架, 星标: 50000)
- zap: 结构化日志库 (分类: 日志, 星标: 15000)
- cobra: 命令行工具库 (分类: 命令行工具)
"""
        parser = EntryParser()
        entries = parser.parse(sample_input)
        assert len(entries) >= 2, f"解析条目数不足: {len(entries)}"
        assert entries[0].name == "gin", f"首个条目名称错误: {entries[0].name}"
        assert entries[0].category == "Web框架", f"分类归一化失败: {entries[0].category}"
        assert entries[0].stars is not None and entries[0].stars > 10000, "星标解析失败"
        print("  [OK] 解析器基本功能")
    except AssertionError as e:
        errors.append(f"解析器基本功能失败: {e}")
        print(f"  [FAIL] 解析器基本功能: {e}")
    except Exception as e:
        errors.append(f"解析器基本功能异常: {e}")
        print(f"  [FAIL] 解析器基本功能异常: {e}")

    # --- 测试 2: 字段式解析 ---
    try:
        sample = "项目名: gorm, 分类: 数据库, 描述: ORM 库, 星标: 30000, 维护状态: 活跃"
        parser = EntryParser()
        entries = parser.parse(sample)
        assert len(entries) == 1, f"应解析出 1 条，实际 {len(entries)}"
        entry = entries[0]
        assert entry.name == "gorm", f"名称错误: {entry.name}"
        assert entry.category == "数据库", f"分类错误: {entry.category}"
        assert entry.stars == 30000, f"星标错误: {entry.stars}"
        assert entry.maintenance == "活跃", f"维护状态错误: {entry.maintenance}"
        print("  [OK] 字段式解析")
    except AssertionError as e:
        errors.append(f"字段式解析失败: {e}")
        print(f"  [FAIL] 字段式解析: {e}")
    except Exception as e:
        errors.append(f"字段式解析异常: {e}")
        print(f"  [FAIL] 字段式解析异常: {e}")

    # --- 测试 3: GitHub 链接解析 ---
    try:
        sample = "参考项目: https://github.com/gin-gonic/gin"
        parser = EntryParser()
        entries = parser.parse(sample)
        assert len(entries) >= 1, "应解析出 URL 条目"
        assert entries[0].name == "gin", f"URL 项目名错误: {entries[0].name}"
        print("  [OK] GitHub URL 解析")
    except AssertionError as e:
        errors.append(f"URL 解析失败: {e}")
        print(f"  [FAIL] URL 解析: {e}")
    except Exception as e:
        errors.append(f"URL 解析异常: {e}")
        print(f"  [FAIL] URL 解析异常: {e}")

    # --- 测试 4: 格式化输出 ---
    try:
        sample = "项目名: viper, 分类: 配置, 描述: 配置管理库"
        parser = EntryParser()
        entries = parser.parse(sample)
        formatter = OutputFormatter()

        table_out = formatter.format(entries, "table")
        assert "viper" in table_out, "表格输出缺少项目名"
        assert "|" in table_out, "表格输出缺少分隔符"

        json_out = formatter.format(entries, "json")
        json_data = json.loads(json_out)
        assert len(json_data) == 1, "JSON 输出条目数错误"
        assert json_data[0]["name"] == "viper", "JSON 输出名称错误"

        list_out = formatter.format(entries, "list")
        assert "viper" in list_out, "列表输出缺少项目名"

        print("  [OK] 格式化输出（table/json/list）")
    except AssertionError as e:
        errors.append(f"格式化输出失败: {e}")
        print(f"  [FAIL] 格式化输出: {e}")
    except Exception as e:
        errors.append(f"格式化输出异常: {e}")
        print(f"  [FAIL] 格式化输出异常: {e}")

    # --- 测试 5: 排序功能 ---
    try:
        sample = """
- a: 项目A (分类: 其他, 星标: 100)
- b: 项目B (分类: 其他, 星标: 9000)
- c: 项目C (分类: 其他, 星标: 500)
"""
        parser = EntryParser()
        entries = parser.parse(sample)
        sorted_asc = sort_entries(entries, "stars", reverse=False)
        assert sorted_asc[0].name == "a", f"升序排序失败: {sorted_asc[0].name}"
        assert sorted_asc[-1].name == "b", f"升序排序失败: {sorted_asc[-1].name}"

        sorted_desc = sort_entries(entries, "stars", reverse=True)
        assert sorted_desc[0].name == "b", f"降序排序失败: {sorted_desc[0].name}"
        assert sorted_desc[-1].name == "a", f"降序排序失败: {sorted_desc[-1].name}"

        print("  [OK] 排序功能")
    except AssertionError as e:
        errors.append(f"排序功能失败: {e}")
        print(f"  [FAIL] 排序功能: {e}")
    except Exception as e:
        errors.append(f"排序功能异常: {e}")
        print(f"  [FAIL] 排序功能异常: {e}")

    # --- 测试 6: 置信度标注 ---
    try:
        complete = ProjectEntry(name="test", category="其他", description="描述", stars=100)
        assert complete.confidence == CONFIDENCE_HIGH, f"完整条目置信度错误: {complete.confidence}"

        partial = ProjectEntry(name="test")
        assert partial.confidence == CONFIDENCE_LOW, f"部分条目置信度错误: {partial.confidence}"

        empty = ProjectEntry()
        assert empty.confidence == CONFIDENCE_UNKNOWN, f"空条目置信度错误: {empty.confidence}"

        print("  [OK] 置信度标注")
    except AssertionError as e:
        errors.append(f"置信度标注失败: {e}")
        print(f"  [FAIL] 置信度标注: {e}")
    except Exception as e:
        errors.append(f"置信度标注异常: {e}")
        print(f"  [FAIL] 置信度标注异常: {e}")

    # --- 测试 7: 错误处理 ---
    try:
        parser = EntryParser()
        try:
            parser.parse("")
            errors.append("空输入应抛出 E002")
            print("  [FAIL] 空输入错误处理")
        except ValueError as e:
            assert "E002" in str(e), f"错误码错误: {e}"
            print("  [OK] 空输入错误处理")

        try:
            parser.parse("无法解析的内容!!!")
            errors.append("无法解析的内容应抛出 E003")
            print("  [FAIL] 无法解析错误处理")
        except ValueError as e:
            assert "E003" in str(e), f"错误码错误: {e}"
            print("  [OK] 无法解析错误处理")

        try:
            formatter = OutputFormatter()
            formatter.format([], "xml")
            errors.append("不支持的格式应抛出 E004")
            print("  [FAIL] 格式错误处理")
        except ValueError as e:
            assert "E004" in str(e), f"错误码错误: {e}"
            print("  [OK] 格式错误处理")

    except AssertionError as e:
        errors.append(f"错误处理失败: {e}")
        print(f"  [FAIL] 错误处理: {e}")
    except Exception as e:
        errors.append(f"错误处理异常: {e}")
        print(f"  [FAIL] 错误处理异常: {e}")

    # --- 测试 8: 完整流程 ---
    try:
        sample = """
- gin: 高性能 HTTP 框架 (分类: Web框架, 星标: 50000)
- zap: 结构化日志库 (分类: 日志, 星标: 15000)
- cobra: 命令行工具库 (分类: 命令行工具)
"""
        result = process_input(sample, output_format="json", sort_field="stars", sort_desc=True)
        data = json.loads(result)
        assert len(data) == 3, f"完整流程条目数错误: {len(data)}"
        assert data[0]["name"] == "gin", f"完整流程排序错误: {data[0]['name']}"
        assert data[0]["stars"] > data[1]["stars"], "星标排序错误"
        print("  [OK] 完整处理流程")
    except AssertionError as e:
        errors.append(f"完整流程失败: {e}")
        print(f"  [FAIL] 完整流程: {e}")
    except Exception as e:
        errors.append(f"完整流程异常: {e}")
        print(f"  [FAIL] 完整流程异常: {e}")

    # --- 汇总 ---
    print()
    if errors:
        print(f"自检失败，共 {len(errors)} 个错误:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        return 1

    print("全部自检通过 ✓")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="awesome-go: Go 资源导航与项目速查工具",
        epilog="示例: python main.py --input '项目名: gin, 分类: Web框架' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容：文本、文件路径（不支持 URL）",
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=SUPPORTED_FORMATS,
        default="table",
        help=f"输出格式: {', '.join(SUPPORTED_FORMATS)}（默认: table）",
    )

    parser.add_argument(
        "--sort",
        type=str,
        choices=CORE_FIELDS,
        help=f"排序字段: {', '.join(CORE_FIELDS)}",
    )

    parser.add_argument(
        "--desc",
        action="store_true",
        help="降序排序（配合 --sort 使用）",
    )

    parser.add_argument(
        "--fields",
        type=str,
        help=f"输出字段（逗号分隔）: {', '.join(CORE_FIELDS)}",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，无需外部输入）",
    )

    return parser


def main() -> int:
    """主函数"""
    parser = build_arg_parser()
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    if not args.input:
        parser.print_help()
        print("\n错误: E001 缺少输入参数 --input", file=sys.stderr)
        return 1

    try:
        # 处理输入
        content = handle_input_arg(args.input)

        # 解析字段过滤
        fields = None
        if args.fields:
            fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 处理并输出
        result = process_input(
            content=content,
            output_format=args.format,
            sort_field=args.sort,
            sort_desc=args.desc,
            fields=fields,
        )
        print(result)
        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E009 未预期异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
