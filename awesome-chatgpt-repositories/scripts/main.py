#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — ChatGPT 开源仓库检索与整理工具（独立实现）

功能概述：
    1. 解析用户输入的仓库描述文本（可包含仓库名、简介、链接等）。
    2. 从文本中提取与 ChatGPT / OpenAI / Codex 相关的开源项目信息。
    3. 输出结构化清单（仓库名、描述、链接、置信度）。
    4. 支持 --selftest 离线自检，不依赖外部文件与网络。

设计原则：
    - 仅依据功能规格独立实现，不参考任何既有代码。
    - 标准库优先，无第三方依赖。
    - 错误码：E001-E010，见 ERROR_MESSAGES。

用法示例：
    python scripts/main.py --input "仓库：chatgpt-web，简介：ChatGPT 网页版，链接：https://github.com/xxx/chatgpt-web"
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "输入为空或未提供有效文本。",
    "E002": "输入格式错误：无法解析仓库条目。",
    "E003": "缺少必要字段（仓库名或链接）。",
    "E004": "链接格式无效（必须以 http:// 或 https:// 开头）。",
    "E005": "置信度计算失败（内部错误）。",
    "E006": "输出序列化失败（JSON 编码错误）。",
    "E007": "命令行参数冲突（--selftest 与 --input 不能同时使用）。",
    "E008": "文件读取失败（文件不存在或不可读）。",
    "E009": "文件写入失败（路径不可写或权限不足）。",
    "E010": "未知错误（未捕获的异常）。",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Repository:
    """表示一个开源仓库条目。"""

    name: str                  # 仓库名称
    description: str = ""      # 仓库简介
    url: str = ""              # 仓库链接
    confidence: float = 0.0    # 置信度（0.0 ~ 1.0）
    tags: List[str] = field(default_factory=list)  # 关联标签

    def to_dict(self) -> Dict:
        """转换为字典，便于 JSON 序列化。"""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "confidence": round(self.confidence, 3),
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# 核心解析与筛选逻辑
# ---------------------------------------------------------------------------
class RepositoryParser:
    """
    从文本中解析仓库条目。

    支持的输入格式（宽松匹配）：
        - "仓库：xxx，简介：yyy，链接：https://..."
        - "name: xxx | desc: yyy | url: https://..."
        - 自由文本中包含 "xxx (https://...)" 或 "xxx - https://..."
    """

    # 关键词表：用于计算置信度与打标签
    KEYWORDS_HIGH = [
        "chatgpt", "openai", "gpt-4", "gpt4", "codex",
        "chat-gpt", "chat gpt", "gpt-3.5", "gpt-3",
    ]
    KEYWORDS_MEDIUM = [
        "llm", "large language model", "ai chat", "chatbot",
        "api wrapper", "gpt", "prompt", "openai api",
    ]
    KEYWORDS_LOW = [
        "python", "javascript", "typescript", "web", "cli",
        "library", "framework", "tool", "demo", "example",
    ]

    # 标签映射
    TAG_MAP = {
        "chatgpt": "chatgpt",
        "openai": "openai",
        "codex": "codex",
        "gpt": "gpt",
        "llm": "llm",
        "api": "api",
        "web": "web",
        "cli": "cli",
    }

    # 字段提取正则（宽松匹配）
    _FIELD_PATTERNS = {
        "name": re.compile(r"(?:仓库|名称|name|repo)\s*[:：]\s*([^\s,，;；|]+)", re.I),
        "description": re.compile(r"(?:简介|描述|desc|description)\s*[:：]\s*([^,，;；|]+)", re.I),
        "url": re.compile(r"(?:链接|网址|url|link)\s*[:：]\s*(https?://[^\s,，;；|]+)", re.I),
    }

    # 通用 URL 提取（用于无标签自由文本）
    _URL_PATTERN = re.compile(r"https?://[^\s,，;；|]+", re.I)

    def parse(self, text: str) -> List[Repository]:
        """
        解析输入文本，返回仓库列表。

        参数:
            text: 用户提供的原始文本

        返回:
            List[Repository] 仓库对象列表

        异常:
            SkillError: E001 输入为空; E002 无法解析任何条目
        """
        if not text or not text.strip():
            raise SkillError("E001")

        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

        # 按空行或明显分隔符切分为块（每条目一个块）
        blocks: List[str] = []
        current_block: List[str] = []
        for line in lines:
            # 检测条目分隔符：行首出现 "---" 或 "===" 或 "###" 或 "1." 等
            if re.match(r"^[-=#]{3,}|^\d+[.、)]", line):
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                # 分隔符本身不作为内容
                if re.match(r"^[-=#]{3,}", line):
                    continue
            current_block.append(line)
        if current_block:
            blocks.append("\n".join(current_block))

        # 如果无法自动分块，则将整个文本作为一块
        if not blocks:
            blocks = [text.strip()]

        repos: List[Repository] = []
        for block in blocks:
            repo = self._parse_block(block)
            if repo:
                repos.append(repo)

        if not repos:
            raise SkillError("E002")

        return repos

    def _parse_block(self, block: str) -> Optional[Repository]:
        """解析单个文本块为一个仓库对象。"""
        # 提取字段
        name = self._extract_field(block, "name")
        desc = self._extract_field(block, "description")
        url = self._extract_field(block, "url")

        # 如果缺少 name 或 url，尝试从自由文本中推断
        if not name:
            name = self._infer_name(block)
        if not url:
            url_match = self._URL_PATTERN.search(block)
            if url_match:
                url = url_match.group(0)

        # 校验必要字段
        if not name:
            return None
        if not url:
            # 允许无链接条目，但置信度降低
            pass
        elif not url.startswith(("http://", "https://")):
            # 链接格式无效
            return None

        # 计算置信度
        confidence = self._calculate_confidence(block, name, desc, url)

        # 提取标签
        tags = self._extract_tags(block, name, desc)

        return Repository(
            name=name,
            description=desc,
            url=url,
            confidence=confidence,
            tags=tags,
        )

    def _extract_field(self, block: str, field: str) -> str:
        """按正则提取指定字段。"""
        pattern = self._FIELD_PATTERNS.get(field)
        if not pattern:
            return ""
        match = pattern.search(block)
        if match:
            return match.group(1).strip()
        return ""

    def _infer_name(self, block: str) -> str:
        """
        从自由文本中推断仓库名。

        规则：
            1. 优先取 URL 路径最后一段（去掉 .git 后缀）
            2. 其次取第一个以字母开头的连续单词
        """
        # 从 URL 推断
        url_match = self._URL_PATTERN.search(block)
        if url_match:
            url_path = url_match.group(0).rstrip("/")
            last_segment = url_path.split("/")[-1]
            if last_segment and last_segment != "github.com":
                return last_segment.replace(".git", "")

        # 从文本开头推断（第一个单词或短语）
        word_match = re.search(r"([A-Za-z][A-Za-z0-9_-]{1,30})", block)
        if word_match:
            return word_match.group(1)

        return ""

    def _calculate_confidence(self, block: str, name: str, desc: str, url: str) -> float:
        """
        计算置信度（0.0 ~ 1.0）。

        规则：
            - 基础分 0.3（存在有效条目）
            - 高相关关键词（chatgpt/openai/codex 等）每个 +0.2，上限 +0.4
            - 中相关关键词（llm/chatbot 等）每个 +0.1，上限 +0.2
            - 低相关关键词（python/web 等）每个 +0.05，上限 +0.1
            - 同时包含名称、描述、链接 +0.2
            - 最终结果裁剪到 [0.0, 1.0]

        异常:
            SkillError: E005 计算失败（理论上不会发生）
        """
        try:
            text_for_score = f"{block} {name} {desc} {url}".lower()
            score = 0.3

            # 高相关关键词
            high_hits = sum(1 for kw in self.KEYWORDS_HIGH if kw in text_for_score)
            score += min(high_hits * 0.2, 0.4)

            # 中相关关键词
            medium_hits = sum(1 for kw in self.KEYWORDS_MEDIUM if kw in text_for_score)
            score += min(medium_hits * 0.1, 0.2)

            # 低相关关键词
            low_hits = sum(1 for kw in self.KEYWORDS_LOW if kw in text_for_score)
            score += min(low_hits * 0.05, 0.1)

            # 字段完整性加分
            if name and desc and url:
                score += 0.2
            elif name and url:
                score += 0.1

            return max(0.0, min(score, 1.0))

        except Exception as exc:
            # 理论上不会进入此分支，但保留防御性代码
            raise SkillError("E005", f"置信度计算异常: {exc}")

    def _extract_tags(self, block: str, name: str, desc: str) -> List[str]:
        """提取标签，返回去重后的标签列表。"""
        text_for_tags = f"{block} {name} {desc}".lower()
        tags: List[str] = []
        for keyword, tag in self.TAG_MAP.items():
            if keyword in text_for_tags and tag not in tags:
                tags.append(tag)
        return tags


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """将仓库列表格式化为结构化输出。"""

    @staticmethod
    def to_json(repos: List[Repository], pretty: bool = True) -> str:
        """序列化为 JSON 字符串。"""
        try:
            data = [repo.to_dict() for repo in repos]
            if pretty:
                return json.dumps(data, ensure_ascii=False, indent=2)
            return json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise SkillError("E006", f"JSON 序列化失败: {exc}")

    @staticmethod
    def to_text(repos: List[Repository]) -> str:
        """格式化为可读文本表格。"""
        lines = []
        lines.append("=" * 60)
        lines.append("ChatGPT 相关开源仓库清单")
        lines.append("=" * 60)

        for idx, repo in enumerate(repos, start=1):
            lines.append(f"{idx}. {repo.name}")
            if repo.description:
                lines.append(f"   简介: {repo.description}")
            if repo.url:
                lines.append(f"   链接: {repo.url}")
            lines.append(f"   置信度: {repo.confidence:.1%}")
            if repo.tags:
                lines.append(f"   标签: {', '.join(repo.tags)}")
            lines.append("-" * 60)

        lines.append(f"共 {len(repos)} 个仓库")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主处理流程
# ---------------------------------------------------------------------------
def process_input(text: str) -> List[Repository]:
    """处理输入文本，返回仓库列表。"""
    parser = RepositoryParser()
    return parser.parse(text)


def run_selftest() -> int:
    """
    内置自检逻辑（离线、无外部依赖）。

    使用硬编码样例数据验证核心功能：
        1. 正常解析（字段齐全）
        2. 自由文本解析（无显式字段标签）
        3. 空输入处理（应报 E001）
    返回 0 表示通过，非 0 表示失败。
    """
    print("[selftest] 开始离线自检...")
    parser = RepositoryParser()

    # 样例 1：字段齐全的条目
    sample1 = (
        "仓库：chatgpt-web\n"
        "简介：ChatGPT 网页版，支持多用户部署\n"
        "链接：https://github.com/xxx/chatgpt-web"
    )
    repos1 = parser.parse(sample1)
    assert len(repos1) >= 1, "自检失败：样例1应解析出至少1个仓库"
    repo1 = repos1[0]
    assert repo1.name == "chatgpt-web", f"自检失败：仓库名不符，实际={repo1.name}"
    assert "chatgpt" in repo1.tags, "自检失败：应包含 chatgpt 标签"
    assert repo1.confidence > 0.5, f"自检失败：置信度应较高，实际={repo1.confidence}"
    print(f"  [通过] 样例1：结构化解析 (置信度={repo1.confidence:.2f})")

    # 样例 2：自由文本（无字段标签）
    sample2 = (
        "这是一个 OpenAI Codex 的 Python 客户端库，"
        "支持自动补全和代码生成。"
        "https://github.com/xxx/openai-codex-python"
    )
    repos2 = parser.parse(sample2)
    assert len(repos2) >= 1, "自检失败：样例2应解析出至少1个仓库"
    repo2 = repos2[0]
    assert "codex" in repo2.tags or "openai" in repo2.tags, "自检失败：应包含 codex/openai 标签"
    assert repo2.url.startswith("https://"), "自检失败：URL 应有效"
    print(f"  [通过] 样例2：自由文本解析 (名称={repo2.name})")

    # 样例 3：多条目输入
    sample3 = (
        "1. 仓库：gpt-cli，简介：命令行 GPT 工具，链接：https://github.com/xxx/gpt-cli\n"
        "2. 仓库：chatbot-ui，简介：基于 GPT 的聊天界面，链接：https://github.com/xxx/chatbot-ui"
    )
    repos3 = parser.parse(sample3)
    assert len(repos3) >= 2, f"自检失败：应解析出至少2个仓库，实际={len(repos3)}"
    print(f"  [通过] 样例3：多条目解析 (共{len(repos3)}个)")

    # 样例 4：空输入应报错
    try:
        parser.parse("")
        assert False, "自检失败：空输入应抛出 E001"
    except SkillError as exc:
        assert exc.code == "E001", f"自检失败：错误码应为 E001，实际={exc.code}"
    print("  [通过] 样例4：空输入错误处理")

    # 样例 5：无链接条目（置信度应较低但不报错）
    sample5 = "仓库：my-tool，简介：一个工具"
    repos5 = parser.parse(sample5)
    assert len(repos5) >= 1, "自检失败：样例5应解析出仓库"
    assert repos5[0].confidence < 0.6, "自检失败：无链接时置信度应较低"
    print(f"  [通过] 样例5：无链接条目 (置信度={repos5[0].confidence:.2f})")

    print("[selftest] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="ChatGPT 开源仓库检索与整理工具",
        epilog="示例: python scripts/main.py --input '仓库：xxx，链接：https://github.com/xxx'",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本：仓库描述、列表或链接",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入文本",
    )
    parser.add_argument(
        "--format", "-fmt",
        choices=["json", "text"],
        default="text",
        help="输出格式（默认 text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        if args.input or args.file:
            print("错误: --selftest 不能与 --input/--file 同时使用", file=sys.stderr)
            return 1
        try:
            return run_selftest()
        except AssertionError as exc:
            print(f"[selftest] 失败: {exc}", file=sys.stderr)
            return 1
        except SkillError as exc:
            print(f"[selftest] 错误: {exc}", file=sys.stderr)
            return 1

    # 获取输入文本
    text: Optional[str] = None
    try:
        if args.input:
            text = args.input
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except (IOError, OSError) as exc:
                print(f"错误: E008 文件读取失败: {exc}", file=sys.stderr)
                return 1
        else:
            # 无参数时提示用法
            parser.print_help()
            return 0

        # 处理输入
        repos = process_input(text)

        # 输出结果
        formatter = OutputFormatter()
        if args.format == "json":
            output = formatter.to_json(repos)
        else:
            output = formatter.to_text(repos)

        print(output)
        return 0

    except SkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常
        print(f"错误: E010 未知异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
