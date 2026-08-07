#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 技能包管家（openpackage）全新独立实现

本脚本依据功能规格独立编写，不参考任何既有代码。
提供技能包/命令的统一收纳、组织、分发辅助功能，
支持批量转换与格式校验。

用法示例：
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --convert input.json --format json
    python scripts/main.py --batch --inputs a.json b.yaml --format markdown
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码（E001-E010）
ERROR_INVALID_ARGS = "E001"          # 命令行参数非法
ERROR_FILE_NOT_FOUND = "E002"        # 输入文件不存在
ERROR_FILE_READ_FAILED = "E003"      # 文件读取失败
ERROR_PARSE_FAILED = "E004"          # 数据解析失败
ERROR_UNSUPPORTED_FORMAT = "E005"    # 不支持的输出格式
ERROR_MISSING_FIELD = "E006"         # 缺少必需字段
ERROR_BATCH_EMPTY = "E007"           # 批量输入为空
ERROR_INTERNAL = "E008"              # 内部逻辑错误
ERROR_CONFIDENCE = "E009"            # 置信度计算异常
ERROR_OUTPUT_WRITE = "E010"          # 输出写入失败

# 支持的文件扩展名与解析器映射
SUPPORTED_INPUT_FORMATS = {".json", ".yaml", ".yml", ".txt", ".md"}

# 支持的数据源类型
SOURCE_TYPE_TEXT = "text"
SOURCE_TYPE_FILE = "file"
SOURCE_TYPE_URL = "url"

# 输出格式
OUTPUT_FORMATS = {"json", "markdown", "yaml"}

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 输出模板常量
MARKDOWN_TEMPLATE = """## 技能包清单

| 序号 | 名称 | 版本 | 触发词 | 置信度 |
|------|------|------|--------|--------|
{rows}

> 生成时间：{timestamp}
> 生成方式：openpackage 技能包管家
"""

YAML_TEMPLATE = """# 技能包清单
# 生成时间: {timestamp}
# 生成方式: openpackage 技能包管家

skills:
{items}
"""


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class SkillPackage:
    """技能包数据模型"""

    REQUIRED_FIELDS = ["name", "version"]

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        trigger_words: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        source: str = "",
        source_type: str = SOURCE_TYPE_TEXT,
        confidence: str = CONFIDENCE_MEDIUM,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.version = version
        self.description = description
        self.trigger_words = trigger_words or []
        self.dependencies = dependencies or []
        self.source = source
        self.source_type = source_type
        self.confidence = confidence
        self.extra = extra or {}
        self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "trigger_words": self.trigger_words,
            "dependencies": self.dependencies,
            "source": self.source,
            "source_type": self.source_type,
            "confidence": self.confidence,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillPackage":
        """从字典创建实例"""
        # 检查必需字段
        for field in cls.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                raise ValueError(
                    f"{ERROR_MISSING_FIELD}: 缺少必需字段 '{field}'"
                )

        return cls(
            name=str(data["name"]),
            version=str(data["version"]),
            description=str(data.get("description", "")),
            trigger_words=data.get("trigger_words", []),
            dependencies=data.get("dependencies", []),
            source=str(data.get("source", "")),
            source_type=str(data.get("source_type", SOURCE_TYPE_TEXT)),
            confidence=str(data.get("confidence", CONFIDENCE_MEDIUM)),
            extra={k: v for k, v in data.items() if k not in
                   {"id", "name", "version", "description", "trigger_words",
                    "dependencies", "source", "source_type", "confidence"}},
        )


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class PackageProcessor:
    """技能包处理核心类"""

    def __init__(self):
        self.packages: List[SkillPackage] = []

    def parse_input(self, raw_data: str, source: str = "",
                    source_type: str = SOURCE_TYPE_TEXT) -> List[SkillPackage]:
        """
        解析原始输入为技能包列表。

        支持 JSON 数组/对象、简单的键值对文本。
        """
        raw_data = raw_data.strip()
        if not raw_data:
            raise ValueError(f"{ERROR_PARSE_FAILED}: 输入数据为空")

        # 尝试 JSON 解析
        try:
            data = json.loads(raw_data)
            return self._parse_json_data(data, source, source_type)
        except json.JSONDecodeError:
            pass

        # 尝试文本解析（每行一个技能包，格式: 名称|版本|描述）
        return self._parse_text_data(raw_data, source, source_type)

    def _parse_json_data(self, data: Any, source: str,
                         source_type: str) -> List[SkillPackage]:
        """解析 JSON 数据"""
        packages = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    packages.append(self._build_package(item, source, source_type))
                else:
                    # 简单字符串条目
                    packages.append(self._build_package(
                        {"name": str(item), "version": "1.0.0"},
                        source, source_type
                    ))
        elif isinstance(data, dict):
            # 可能是单个技能包或包含技能包列表的对象
            if "skills" in data and isinstance(data["skills"], list):
                for item in data["skills"]:
                    if isinstance(item, dict):
                        packages.append(self._build_package(item, source, source_type))
            elif "name" in data:
                packages.append(self._build_package(data, source, source_type))
            else:
                # 尝试将键值对作为技能包字段
                packages.append(self._build_package(data, source, source_type))
        else:
            raise ValueError(f"{ERROR_PARSE_FAILED}: 不支持的 JSON 数据类型")

        return packages

    def _parse_text_data(self, raw_data: str, source: str,
                         source_type: str) -> List[SkillPackage]:
        """解析文本数据（每行一个技能包）"""
        packages = []
        lines = [line.strip() for line in raw_data.splitlines() if line.strip()]

        for line in lines:
            # 支持分隔符: | 或 逗号
            parts = [p.strip() for p in line.replace(",", "|").split("|")]
            if len(parts) >= 2:
                package = self._build_package(
                    {"name": parts[0], "version": parts[1],
                     "description": parts[2] if len(parts) > 2 else ""},
                    source, source_type
                )
            else:
                package = self._build_package(
                    {"name": parts[0], "version": "1.0.0"},
                    source, source_type
                )
            packages.append(package)

        return packages

    def _build_package(self, data: Dict[str, Any], source: str,
                       source_type: str) -> SkillPackage:
        """构建技能包对象"""
        try:
            package = SkillPackage.from_dict(data)
        except ValueError as e:
            # 缺少必需字段时使用占位符
            name = data.get("name", "[需核实:名称]")
            version = data.get("version", "[需核实:版本]")
            package = SkillPackage(
                name=str(name),
                version=str(version),
                description=str(data.get("description", "")),
                trigger_words=data.get("trigger_words", []),
                dependencies=data.get("dependencies", []),
                source=source,
                source_type=source_type,
                confidence=CONFIDENCE_LOW,
            )
            # 保留原始错误信息
            package.extra["parse_warning"] = str(e)

        # 自动计算置信度
        package.confidence = self._calculate_confidence(package)
        return package

    def _calculate_confidence(self, package: SkillPackage) -> str:
        """计算置信度（基于字段完整度）"""
        try:
            score = 0
            total = 5

            if package.name and "[需核实" not in package.name:
                score += 1
            if package.version and "[需核实" not in package.version:
                score += 1
            if package.description:
                score += 1
            if package.trigger_words:
                score += 1
            if package.dependencies:
                score += 1

            ratio = score / total
            if ratio >= 0.8:
                return CONFIDENCE_HIGH
            elif ratio >= 0.4:
                return CONFIDENCE_MEDIUM
            else:
                return CONFIDENCE_LOW
        except Exception:
            return CONFIDENCE_LOW

    def add_packages(self, packages: List[SkillPackage]) -> int:
        """添加技能包到处理器"""
        self.packages.extend(packages)
        return len(packages)

    def clear(self) -> None:
        """清空所有技能包"""
        self.packages.clear()

    @property
    def count(self) -> int:
        """技能包数量"""
        return len(self.packages)


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_json(packages: List[SkillPackage]) -> str:
        """JSON 格式输出"""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_count": len(packages),
            "skills": [p.to_dict() for p in packages],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def format_markdown(packages: List[SkillPackage]) -> str:
        """Markdown 格式输出"""
        rows = []
        for i, pkg in enumerate(packages, 1):
            triggers = ", ".join(pkg.trigger_words) if pkg.trigger_words else "-"
            rows.append(
                f"| {i} | {pkg.name} | {pkg.version} | {triggers} | {pkg.confidence} |"
            )
        return MARKDOWN_TEMPLATE.format(
            rows="\n".join(rows),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @staticmethod
    def format_yaml(packages: List[SkillPackage]) -> str:
        """YAML 格式输出（简易实现）"""
        items = []
        for pkg in packages:
            item_lines = [
                f"  - id: {pkg.id}",
                f"    name: \"{pkg.name}\"",
                f"    version: \"{pkg.version}\"",
                f"    description: \"{pkg.description}\"",
                f"    confidence: \"{pkg.confidence}\"",
            ]
            if pkg.trigger_words:
                triggers = ", ".join(f"\"{t}\"" for t in pkg.trigger_words)
                item_lines.append(f"    trigger_words: [{triggers}]")
            if pkg.dependencies:
                deps = ", ".join(f"\"{d}\"" for d in pkg.dependencies)
                item_lines.append(f"    dependencies: [{deps}]")
            items.append("\n".join(item_lines))

        return YAML_TEMPLATE.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            items="\n".join(items),
        )

    @staticmethod
    def format(packages: List[SkillPackage], output_format: str) -> str:
        """统一格式化入口"""
        output_format = output_format.lower()
        if output_format == "json":
            return OutputFormatter.format_json(packages)
        elif output_format == "markdown":
            return OutputFormatter.format_markdown(packages)
        elif output_format == "yaml":
            return OutputFormatter.format_yaml(packages)
        else:
            raise ValueError(f"{ERROR_UNSUPPORTED_FORMAT}: 不支持的输出格式 '{output_format}'")


# ---------------------------------------------------------------------------
# 文件处理
# ---------------------------------------------------------------------------

class FileHandler:
    """文件读写处理"""

    @staticmethod
    def read_file(filepath: str) -> str:
        """读取文件内容"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{ERROR_FILE_NOT_FOUND}: 文件不存在 '{filepath}'")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(filepath, "r", encoding="gbk") as f:
                    return f.read()
            except Exception as e:
                raise IOError(f"{ERROR_FILE_READ_FAILED}: 文件读取失败 {e}")
        except Exception as e:
            raise IOError(f"{ERROR_FILE_READ_FAILED}: 文件读取失败 {e}")

    @staticmethod
    def write_file(filepath: str, content: str) -> None:
        """写入文件"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise IOError(f"{ERROR_OUTPUT_WRITE}: 文件写入失败 {e}")


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="openpackage",
        description="技能包管家 — 统一收纳、组织、分发技能包与命令",
        epilog="示例: python scripts/main.py --convert data.json --format json",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部文件）",
    )

    # 转换模式
    parser.add_argument(
        "--convert",
        metavar="FILE",
        help="转换单个文件为结构化输出",
    )

    # 批量模式
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式",
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        metavar="FILE",
        help="批量输入文件列表",
    )

    # 文本输入模式
    parser.add_argument(
        "--text",
        metavar="TEXT",
        help="直接传入文本内容",
    )

    # 输出选项
    parser.add_argument(
        "--format",
        choices=sorted(OUTPUT_FORMATS),
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="输出文件路径（默认输出到标准输出）",
    )

    return parser


def run_selftest() -> int:
    """内置自检功能（离线、不依赖外部文件）"""
    print("=" * 60)
    print("openpackage 自检模式")
    print("=" * 60)

    processor = PackageProcessor()
    formatter = OutputFormatter()

    # 1. 测试 JSON 解析
    print("\n[1] 测试 JSON 解析...")
    json_data = json.dumps([
        {
            "name": "测试技能包A",
            "version": "1.2.3",
            "description": "用于自检的测试技能包",
            "trigger_words": ["测试A", "testA"],
            "dependencies": ["python>=3.8"],
        },
        {
            "name": "测试技能包B",
            "version": "0.9.1",
            "description": "第二个测试包",
        },
    ])
    packages = processor.parse_input(json_data, source="内置样例", source_type=SOURCE_TYPE_TEXT)
    assert len(packages) == 2, f"JSON 解析失败: 期望 2 个包，实际 {len(packages)}"
    assert packages[0].name == "测试技能包A", f"名称解析错误: {packages[0].name}"
    assert packages[0].confidence == CONFIDENCE_HIGH, f"置信度计算错误: {packages[0].confidence}"
    print(f"  ✓ JSON 解析成功，共 {len(packages)} 个技能包")

    # 2. 测试文本解析
    print("[2] 测试文本解析...")
    text_data = "文本技能包|2.0.0|通过文本创建的包\n简单包|1.0.0"
    packages = processor.parse_input(text_data, source="内置文本", source_type=SOURCE_TYPE_TEXT)
    assert len(packages) == 2, f"文本解析失败: 期望 2 个包，实际 {len(packages)}"
    assert packages[0].name == "文本技能包", f"文本名称解析错误: {packages[0].name}"
    print(f"  ✓ 文本解析成功，共 {len(packages)} 个技能包")

    # 3. 测试缺失字段处理
    print("[3] 测试缺失字段处理...")
    incomplete_data = json.dumps({"description": "缺少名称和版本"})
    packages = processor.parse_input(incomplete_data, source="不完整数据")
    assert len(packages) == 1, f"缺失字段处理失败: 期望 1 个包，实际 {len(packages)}"
    assert "[需核实" in packages[0].name, f"占位符未生效: {packages[0].name}"
    assert packages[0].confidence == CONFIDENCE_LOW, f"低置信度判定失败: {packages[0].confidence}"
    print(f"  ✓ 缺失字段处理成功，使用占位符并标记低置信度")

    # 4. 测试输出格式
    print("[4] 测试输出格式...")
    processor.clear()
    processor.add_packages([
        SkillPackage(name="格式测试包", version="1.0.0",
                     description="用于格式测试", trigger_words=["格式"]),
    ])

    for fmt in OUTPUT_FORMATS:
        output = formatter.format(processor.packages, fmt)
        assert output and len(output) > 0, f"格式 {fmt} 输出为空"
        print(f"  ✓ {fmt} 格式输出成功（{len(output)} 字符）")

    # 5. 测试批量处理
    print("[5] 测试批量处理...")
    processor.clear()
    batch_data = [
        {"name": f"批量包{i}", "version": f"{i}.0.0"} for i in range(1, 6)
    ]
    packages = processor.parse_input(json.dumps(batch_data))
    assert len(packages) == 5, f"批量处理失败: 期望 5 个包，实际 {len(packages)}"
    print(f"  ✓ 批量处理成功，共 {len(packages)} 个技能包")

    # 6. 测试空数据处理
    print("[6] 测试空数据处理...")
    try:
        processor.parse_input("")
        assert False, "空数据应抛出异常"
    except ValueError as e:
        assert ERROR_PARSE_FAILED in str(e), f"错误码不正确: {e}"
        print("  ✓ 空数据处理正确（抛出 E004 错误）")

    # 7. 测试不支持格式
    print("[7] 测试不支持格式...")
    try:
        formatter.format(processor.packages, "xml")
        assert False, "不支持的格式应抛出异常"
    except ValueError as e:
        assert ERROR_UNSUPPORTED_FORMAT in str(e), f"错误码不正确: {e}"
        print("  ✓ 不支持格式处理正确（抛出 E005 错误）")

    print("\n" + "=" * 60)
    print("✅ 所有自检通过！")
    print("=" * 60)
    return 0


def run_convert(args: argparse.Namespace) -> int:
    """执行转换操作"""
    processor = PackageProcessor()
    formatter = OutputFormatter()
    file_handler = FileHandler()

    try:
        # 收集输入
        input_sources = []

        if args.convert:
            input_sources.append((args.convert, SOURCE_TYPE_FILE))
        if args.text:
            input_sources.append((args.text, SOURCE_TYPE_TEXT))
        if args.batch and args.inputs:
            for f in args.inputs:
                input_sources.append((f, SOURCE_TYPE_FILE))

        if not input_sources:
            print(f"{ERROR_INVALID_ARGS}: 请提供输入（--convert/--text/--batch）", file=sys.stderr)
            return 1

        # 处理每个输入
        all_packages = []
        for source, source_type in input_sources:
            if source_type == SOURCE_TYPE_FILE:
                content = file_handler.read_file(source)
                packages = processor.parse_input(content, source=source, source_type=source_type)
            else:
                packages = processor.parse_input(source, source=source, source_type=source_type)
            all_packages.extend(packages)

        if not all_packages:
            print(f"{ERROR_BATCH_EMPTY}: 未解析到任何技能包", file=sys.stderr)
            return 1

        # 格式化输出
        output_content = formatter.format(all_packages, args.format)

        # 输出
        if args.output:
            file_handler.write_file(args.output, output_content)
            print(f"✓ 已写入 {args.output}")
        else:
            print(output_content)

        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except (ValueError, IOError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERROR_INTERNAL}: 未预期错误: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """主入口函数"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无参数时显示帮助
    if not (args.convert or args.batch or args.text):
        parser.print_help()
        return 0

    # 转换模式
    return run_convert(args)


if __name__ == "__main__":
    sys.exit(main())
