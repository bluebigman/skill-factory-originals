#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-to-skill 技能包生成器 - 独立实现脚本

依据功能规格书 clean-room 重写，仅使用 Python 标准库。
功能：将书籍、文档或链接转化为结构化技能包。

用法示例：
    python scripts/main.py --selftest          # 运行内置自检
    python scripts/main.py --input book.txt    # 处理本地文本文件
    python scripts/main.py --url https://...   # 处理网页链接（需网络）
"""

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少输入或输入格式不正确",
    "E002": "文件读取失败：文件不存在或无法访问",
    "E003": "URL 访问失败：网络错误或返回非 200 状态",
    "E004": "内容解析失败：无法从输入中提取有效文本",
    "E005": "技能包生成失败：内部处理逻辑错误",
    "E006": "输出写入失败：无法写入目标文件",
    "E007": "自检失败：核心逻辑验证未通过",
    "E008": "输入为空：未提供任何可处理的内容",
    "E009": "内容过长：输入超过单次处理上限",
    "E010": "未知错误：未预期的异常情况",
}


@dataclass
class SkillModule:
    """技能模块数据类"""
    title: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    difficulty: str = "入门"
    estimated_time: str = "30分钟"


@dataclass
class SkillPackage:
    """技能包数据类"""
    title: str
    source_type: str  # book / document / url / notes
    source_name: str
    description: str
    modules: List[SkillModule] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典结构"""
        return {
            "title": self.title,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "description": self.description,
            "modules": [
                {
                    "title": m.title,
                    "summary": m.summary,
                    "key_points": m.key_points,
                    "actions": m.actions,
                    "difficulty": m.difficulty,
                    "estimated_time": m.estimated_time,
                }
                for m in self.modules
            ],
            "tags": self.tags,
            "generated_at": self.generated_at,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式输出"""
        lines = [
            f"# {self.title}",
            "",
            f"> 来源类型：{self.source_type}",
            f"> 来源名称：{self.source_name}",
            f"> 生成时间：{self.generated_at}",
            "",
            "## 技能包描述",
            "",
            self.description,
            "",
            "## 技能模块",
            "",
        ]

        for idx, module in enumerate(self.modules, 1):
            lines.extend(
                [
                    f"### 模块 {idx}: {module.title}",
                    "",
                    f"**概述**：{module.summary}",
                    "",
                    f"**难度**：{module.difficulty} | **预计耗时**：{module.estimated_time}",
                    "",
                    "**关键要点**：",
                ]
            )
            for point in module.key_points:
                lines.append(f"- {point}")
            lines.append("")
            lines.append("**实践动作**：")
            for action in module.actions:
                lines.append(f"- [ ] {action}")
            lines.append("")

        if self.tags:
            lines.extend(["## 标签", "", ", ".join(self.tags), ""])

        return "\n".join(lines)


class TextExtractor:
    """文本提取器：从不同来源提取结构化文本"""

    @staticmethod
    def from_file(file_path: str) -> str:
        """从本地文件读取文本"""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            return path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError as exc:
            raise RuntimeError("E002") from exc
        except Exception as exc:
            raise RuntimeError("E002") from exc

    @staticmethod
    def from_url(url: str) -> str:
        """从 URL 获取文本内容"""
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (skill-factory)"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    raise RuntimeError("E003")
                # 尝试多种编码
                content = resp.read()
                for encoding in ["utf-8", "gbk", "latin-1"]:
                    try:
                        return content.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return content.decode("utf-8", errors="replace")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("E003") from exc

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """清理原始文本：去除多余空白、特殊字符等"""
        if not raw_text or not raw_text.strip():
            raise RuntimeError("E008")
        # 统一换行符
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        # 合并连续空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除特殊控制字符
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text.strip()


class SkillParser:
    """技能解析器：将文本内容解析为技能模块"""

    # 常见章节标题模式
    CHAPTER_PATTERNS = [
        r"^第[一二三四五六七八九十百千0-9]+[章节篇部分].*$",
        r"^Chapter\s+\d+.*$",
        r"^\d+\.\s+\S+.*$",
        r"^#{1,3}\s+\S+.*$",
    ]

    # 关键要点标记
    KEY_POINT_MARKERS = [
        "要点", "关键", "重点", "核心", "注意", "重要",
        "key point", "important", "note", "tip",
    ]

    # 动作/实践标记
    ACTION_MARKERS = [
        "实践", "操作", "步骤", "练习", "行动", "实施",
        "practice", "step", "action", "exercise",
    ]

    @classmethod
    def split_sections(cls, text: str) -> List[Dict[str, str]]:
        """将文本按章节切分为独立部分"""
        lines = text.split("\n")
        sections: List[Dict[str, str]] = []
        current_title = "前言"
        current_content: List[str] = []

        for line in lines:
            stripped = line.strip()
            # 判断是否为章节标题
            is_heading = False
            for pattern in cls.CHAPTER_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    is_heading = True
                    break

            if is_heading:
                # 保存上一个章节
                if current_content:
                    sections.append(
                        {"title": current_title, "content": "\n".join(current_content)}
                    )
                current_title = stripped
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_content:
            sections.append(
                {"title": current_title, "content": "\n".join(current_content)}
            )

        # 过滤过短的章节
        return [s for s in sections if len(s["content"].strip()) > 20]

    @classmethod
    def extract_key_points(cls, content: str) -> List[str]:
        """从内容中提取关键要点"""
        points: List[str] = []
        sentences = re.split(r"[。！？!?\.]+", content)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
            # 检查是否包含关键标记
            contains_marker = any(
                marker.lower() in sentence.lower() for marker in cls.KEY_POINT_MARKERS
            )
            # 或者句子以"是/应该/需要/必须"等开头
            starts_with_verb = bool(
                re.match(r"^(是|应该|需要|必须|应当|可以|建议)", sentence)
            )
            if contains_marker or starts_with_verb:
                points.append(sentence[:80])  # 截断过长句子

        # 去重并限制数量
        unique_points: List[str] = []
        for p in points:
            if p not in unique_points:
                unique_points.append(p)
        return unique_points[:5]

    @classmethod
    def extract_actions(cls, content: str) -> List[str]:
        """从内容中提取实践动作"""
        actions: List[str] = []
        lines = content.split("\n")

        for line in lines:
            stripped = line.strip()
            # 去除列表标记
            cleaned = re.sub(r"^[-*•]\s+", "", stripped)
            cleaned = re.sub(r"^\d+[.、)]\s+", "", cleaned)

            if len(cleaned) < 5 or len(cleaned) > 100:
                continue

            contains_marker = any(
                marker.lower() in cleaned.lower() for marker in cls.ACTION_MARKERS
            )
            # 以动词开头的句子
            starts_with_action = bool(
                re.match(r"^(使用|创建|编写|设计|实现|分析|测试|部署|学习|掌握)", cleaned)
            )

            if contains_marker or starts_with_action:
                actions.append(cleaned)

        # 去重并限制数量
        unique_actions: List[str] = []
        for a in actions:
            if a not in unique_actions:
                unique_actions.append(a)
        return unique_actions[:5]

    @classmethod
    def create_module(cls, title: str, content: str) -> SkillModule:
        """从章节内容创建技能模块"""
        # 生成摘要：取前几句
        sentences = re.split(r"[。！？!?\.]+", content)
        summary = " ".join(s.strip() for s in sentences[:2] if s.strip())[:100]

        key_points = cls.extract_key_points(content)
        actions = cls.extract_actions(content)

        # 如果没有提取到要点，使用默认内容
        if not key_points:
            key_points = [f"理解 {title} 的核心概念"]
        if not actions:
            actions = [f"阅读并总结 {title} 相关内容"]

        return SkillModule(
            title=title[:50],
            summary=summary,
            key_points=key_points,
            actions=actions,
            difficulty="入门" if len(key_points) <= 3 else "进阶",
            estimated_time=f"{max(15, len(key_points) * 10)}分钟",
        )

    @classmethod
    def parse(cls, raw_text: str, source_name: str = "") -> SkillPackage:
        """解析文本为技能包"""
        try:
            text = TextExtractor.clean_text(raw_text)
            if len(text) > 100000:
                raise RuntimeError("E009")

            sections = cls.split_sections(text)
            if not sections:
                raise RuntimeError("E004")

            modules = []
            for section in sections:
                module = cls.create_module(section["title"], section["content"])
                modules.append(module)

            # 限制模块数量
            modules = modules[:8]

            # 生成技能包
            package = SkillPackage(
                title=f"《{source_name or '输入内容'}》技能包",
                source_type="text",
                source_name=source_name or "用户输入",
                description=f"从输入内容中提取了 {len(modules)} 个核心技能模块，"
                           f"覆盖关键要点 {sum(len(m.key_points) for m in modules)} 条，"
                           f"实践动作 {sum(len(m.actions) for m in modules)} 项。",
                modules=modules,
                tags=["知识萃取", "技能包", "结构化学习"],
                generated_at="2026-01-01T00:00:00+08:00",
            )
            return package

        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("E005") from exc


class SkillPackageGenerator:
    """技能包生成器主类"""

    def __init__(self) -> None:
        self.parser = SkillParser()

    def generate_from_text(self, text: str, name: str = "") -> SkillPackage:
        """从文本生成技能包"""
        return self.parser.parse(text, name)

    def generate_from_file(self, file_path: str) -> SkillPackage:
        """从文件生成技能包"""
        text = TextExtractor.from_file(file_path)
        return self.parser.parse(text, Path(file_path).stem)

    def generate_from_url(self, url: str) -> SkillPackage:
        """从 URL 生成技能包"""
        text = TextExtractor.from_url(url)
        return self.parser.parse(text, url)

    def save_output(self, package: SkillPackage, output_path: str, fmt: str = "md") -> None:
        """保存输出文件"""
        try:
            if fmt == "json":
                content = json.dumps(package.to_dict(), ensure_ascii=False, indent=2)
            else:
                content = package.to_markdown()

            Path(output_path).write_text(content, encoding="utf-8")
        except Exception as exc:
            raise RuntimeError("E006") from exc


class SelfTester:
    """内置自检器：使用硬编码样例数据验证核心逻辑"""

    # 硬编码测试样例数据（不依赖外部文件）
    SAMPLE_TEXT = """
    第一章 引言：深度工作的价值
    在当今信息过载的时代，深度工作能力变得越来越重要。
    关键要点：深度工作是指在无干扰状态下专注于认知要求高的任务。
    需要建立固定的工作流程和习惯来支持深度工作。
    实践步骤：每天安排固定的深度工作时间块。
    应该减少社交媒体使用时间，增加专注时间。

    第二章 深度工作的准则
    准则一：工作要深入。培养深度工作的习惯需要刻意练习。
    重点：选择适合自己节奏的深度工作模式。
    准则二：拥抱无聊。不要害怕无聊时刻，它们是大脑休息的机会。
    注意：定期让自己远离电子设备。
    实践：制定每周的数字排毒计划。
    操作：创建深度工作的评分系统来追踪进步。

    第三章 深度工作的策略
    策略包括：节奏哲学、双峰哲学、禁欲哲学和新闻记者哲学。
    核心：根据个人情况选择最合适的深度工作策略。
    关键：将深度工作纳入日程安排，而非等待灵感。
    应该建立仪式感来启动深度工作状态。
    实施：在每周计划中预留固定的深度工作时间。
    步骤：记录每日深度工作的时长和质量。
    """

    @classmethod
    def run_all(cls) -> bool:
        """运行全部自检，返回是否通过"""
        checks = [
            ("文本清理", cls._test_text_cleaning),
            ("章节切分", cls._test_section_splitting),
            ("要点提取", cls._test_key_point_extraction),
            ("动作提取", cls._test_action_extraction),
            ("模块创建", cls._test_module_creation),
            ("技能包生成", cls._test_package_generation),
            ("序列化", cls._test_serialization),
        ]

        all_passed = True
        for name, test_fn in checks:
            try:
                test_fn()
                print(f"  ✓ {name}")
            except AssertionError as exc:
                print(f"  ✗ {name}: {exc}")
                all_passed = False
            except Exception as exc:
                print(f"  ✗ {name}: 异常 - {exc}")
                all_passed = False

        return all_passed

    @classmethod
    def _test_text_cleaning(cls) -> None:
        """测试文本清理功能"""
        raw = "  测试文本\r\n\r\n\r\n  多行内容  \n"
        cleaned = TextExtractor.clean_text(raw)
        # 宽松断言：清理后应包含核心内容
        assert "测试文本" in cleaned, "清理后应保留核心内容"
        assert "多行内容" in cleaned, "清理后应保留多行内容"
        # 不应有连续三个以上换行
        assert "\n\n\n" not in cleaned, "不应有连续三个换行"

    @classmethod
    def _test_section_splitting(cls) -> None:
        """测试章节切分功能"""
        sections = SkillParser.split_sections(cls.SAMPLE_TEXT)
        # 宽松断言：应能切分出至少 2 个章节
        assert len(sections) >= 2, f"应切分出至少2个章节，实际 {len(sections)}"
        # 每个章节应有标题和内容
        for section in sections:
            assert "title" in section, "章节应包含标题"
            assert "content" in section, "章节应包含内容"
            assert len(section["content"]) > 0, "章节内容不应为空"

    @classmethod
    def _test_key_point_extraction(cls) -> None:
        """测试关键要点提取"""
        content = "关键要点：这是第一个要点。重点：这是第二个要点。普通句子。"
        points = SkillParser.extract_key_points(content)
        # 宽松断言：应提取到至少 1 个要点
        assert len(points) >= 1, f"应提取到至少1个要点，实际 {len(points)}"
        # 提取的要点不应为空
        for p in points:
            assert len(p) > 0, "要点不应为空"

    @classmethod
    def _test_action_extraction(cls) -> None:
        """测试实践动作提取"""
        content = "实践：完成这个练习。操作：按照步骤执行。普通描述。"
        actions = SkillParser.extract_actions(content)
        # 宽松断言：应提取到至少 1 个动作
        assert len(actions) >= 1, f"应提取到至少1个动作，实际 {len(actions)}"
        # 提取的动作不应为空
        for a in actions:
            assert len(a) > 0, "动作不应为空"

    @classmethod
    def _test_module_creation(cls) -> None:
        """测试技能模块创建"""
        module = SkillParser.create_module("测试章节", cls.SAMPLE_TEXT)
        # 宽松断言：模块应有基本属性
        assert module.title, "模块应有标题"
        assert module.summary, "模块应有摘要"
        assert len(module.key_points) > 0, "模块应有关键要点"
        assert len(module.actions) > 0, "模块应有实践动作"
        assert module.difficulty in ["入门", "进阶"], "难度等级应合法"
        assert "分钟" in module.estimated_time, "预计时间应包含单位"

    @classmethod
    def _test_package_generation(cls) -> None:
        """测试完整技能包生成"""
        generator = SkillPackageGenerator()
        package = generator.generate_from_text(cls.SAMPLE_TEXT, "测试书籍")
        # 宽松断言：技能包应有完整结构
        assert package.title, "技能包应有标题"
        assert package.source_type, "技能包应有来源类型"
        assert len(package.modules) > 0, f"技能包应有至少1个模块，实际 {len(package.modules)}"
        assert package.description, "技能包应有描述"
        assert len(package.tags) > 0, "技能包应有标签"

    @classmethod
    def _test_serialization(cls) -> None:
        """测试序列化功能"""
        generator = SkillPackageGenerator()
        package = generator.generate_from_text(cls.SAMPLE_TEXT, "测试书籍")
        # 测试 dict 转换
        data = package.to_dict()
        assert "title" in data, "dict 应包含标题"
        assert "modules" in data, "dict 应包含模块列表"
        assert len(data["modules"]) > 0, "dict 模块列表不应为空"
        # 测试 markdown 转换
        md = package.to_markdown()
        assert "# " in md, "Markdown 应包含一级标题"
        assert "## " in md, "Markdown 应包含二级标题"


def run_selftest() -> int:
    """运行自检程序"""
    print("=" * 60)
    print("book-to-skill 技能包生成器 - 自检模式")
    print("=" * 60)
    print("\n开始执行核心逻辑自检...\n")

    passed = SelfTester.run_all()

    print("\n" + "=" * 60)
    if passed:
        print("✅ 自检通过：所有核心逻辑验证成功")
        return 0
    else:
        print("❌ 自检失败：存在未通过的检查项")
        return 1


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="book-to-skill 技能包生成器 - 将书籍/文档/链接转化为结构化技能包",
        epilog="示例: python scripts/main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件，离线可执行）",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文件路径（支持 .txt 等文本文件）",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="输入网页 URL",
    )
    parser.add_argument(
        "--text",
        type=str,
        help="直接输入文本内容",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output",
        help="输出文件路径（不含扩展名），默认: output",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["md", "json"],
        default="md",
        help="输出格式: md (Markdown) 或 json，默认: md",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input and not args.url and not args.text:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请提供 --input、--url 或 --text 之一", file=sys.stderr)
        return 1

    try:
        generator = SkillPackageGenerator()

        # 根据输入类型生成技能包
        if args.input:
            print(f"正在处理文件: {args.input}")
            package = generator.generate_from_file(args.input)
        elif args.url:
            print(f"正在处理 URL: {args.url}")
            package = generator.generate_from_url(args.url)
        else:
            print("正在处理文本输入...")
            package = generator.generate_from_text(args.text, "用户输入")

        # 输出结果
        output_path = f"{args.output}.{args.format}"
        generator.save_output(package, output_path, args.format)

        print(f"\n✅ 技能包生成成功！")
        print(f"   标题: {package.title}")
        print(f"   模块数: {len(package.modules)}")
        print(f"   输出文件: {output_path}")

        # 打印模块概览
        print("\n📋 模块概览:")
        for i, module in enumerate(package.modules, 1):
            print(f"   {i}. {module.title} ({module.difficulty}, {module.estimated_time})")

        return 0

    except RuntimeError as exc:
        code = str(exc)
        msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
        print(f"错误 [{code}]: {msg}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 [E010]: {ERROR_CODES['E010']} - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
