#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

会话经验提炼与技能生成工具（clean-room 独立实现）
仅依据功能规格编写，不参考任何既有代码。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入文件不存在或不可读",
    "E003": "输出目录不可写",
    "E004": "对话数据格式非法",
    "E005": "技能文档生成失败",
    "E006": "经验提取失败",
    "E007": "内部状态异常",
    "E008": "版本迭代失败",
    "E009": "脱敏处理失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能处理异常基类"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 数据模型 ----------

class ConversationEntry:
    """对话条目"""

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEntry":
        if "role" not in data or "content" not in data:
            raise SkillError("E004", "对话条目缺少 role 或 content 字段")
        return cls(
            role=str(data["role"]),
            content=str(data["content"]),
            timestamp=str(data.get("timestamp", "")),
        )


class SkillDocument:
    """技能文档"""

    def __init__(
        self,
        slug: str,
        name: str,
        display_name: str,
        description: str,
        version: str = "1.0.0",
        trigger_words: Optional[List[str]] = None,
        steps: Optional[List[str]] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.slug = slug
        self.name = name
        self.display_name = display_name
        self.description = description
        self.version = version
        self.trigger_words = trigger_words or []
        self.steps = steps or []
        self.examples = examples or []
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "name": self.name,
            "displayName": self.display_name,
            "description": self.description,
            "version": self.version,
            "triggerWords": self.trigger_words,
            "steps": self.steps,
            "examples": self.examples,
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ---------- 核心逻辑 ----------

class ExperienceExtractor:
    """经验提取器：从对话中提炼可复用模式"""

    # 常见问题模式关键词
    PATTERN_KEYWORDS = {
        "故障排查": ["报错", "错误", "失败", "异常", "bug", "崩溃"],
        "流程指导": ["怎么做", "如何", "步骤", "流程", "方法"],
        "知识问答": ["是什么", "什么是", "定义", "解释", "区别"],
        "最佳实践": ["最佳", "建议", "推荐", "优化", "改进"],
    }

    # 操作步骤连接词
    STEP_CONNECTORS = ["然后", "接着", "之后", "最后", "首先", "第一步", "第二步"]

    def __init__(self, min_content_length: int = 10):
        self.min_content_length = min_content_length

    def extract(self, entries: List[ConversationEntry]) -> Dict[str, Any]:
        """从对话条目中提取经验"""
        if not entries:
            raise SkillError("E006", "对话为空，无法提取经验")

        # 提取主题（取首个用户消息的关键内容）
        user_messages = [e for e in entries if e.role == "user"]
        assistant_messages = [e for e in entries if e.role == "assistant"]
        if not user_messages:
            raise SkillError("E006", "对话中没有用户消息")

        topic = self._extract_topic(user_messages[0].content)

        # 识别模式类型
        pattern_type = self._identify_pattern(entries)

        # 提取步骤
        steps = self._extract_steps(assistant_messages)

        # 提取示例
        examples = self._extract_examples(entries)

        # 提取触发词
        trigger_words = self._extract_trigger_words(topic, pattern_type)

        return {
            "topic": topic,
            "pattern_type": pattern_type,
            "steps": steps,
            "examples": examples,
            "trigger_words": trigger_words,
            "confidence": self._calculate_confidence(entries),
        }

    def _extract_topic(self, content: str) -> str:
        """从首条用户消息提取主题"""
        # 去除常见问句前缀
        cleaned = re.sub(r"^(请问|你好|我想问|麻烦问一下|帮我)[，,、\s]*", "", content)
        # 截断过长内容
        if len(cleaned) > 50:
            cleaned = cleaned[:50] + "..."
        return cleaned.strip() or "未命名主题"

    def _identify_pattern(self, entries: List[ConversationEntry]) -> str:
        """识别对话模式类型"""
        all_text = " ".join(e.content for e in entries)
        scores = {}
        for pattern, keywords in self.PATTERN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in all_text)
            scores[pattern] = score
        # 返回得分最高的模式，若无匹配则返回通用
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else "通用问答"

    def _extract_steps(self, assistant_messages: List[ConversationEntry]) -> List[str]:
        """从助手回复中提取操作步骤"""
        steps = []
        for msg in assistant_messages:
            content = msg.content
            # 按连接词拆分
            parts = re.split(r"[。；;\n]", content)
            for part in parts:
                part = part.strip()
                if not part or len(part) < self.min_content_length:
                    continue
                # 检查是否包含操作描述
                if any(word in part for word in ["请", "需要", "建议", "可以", "应该", "务必"]):
                    # 清理步骤前缀
                    cleaned = re.sub(r"^(首先|然后|接着|最后|第一步|第二步|第三步)[，,、\s]*", "", part)
                    if cleaned and cleaned not in steps:
                        steps.append(cleaned)
            if len(steps) >= 5:  # 最多提取5个步骤
                break
        return steps[:5]

    def _extract_examples(self, entries: List[ConversationEntry]) -> List[Dict[str, str]]:
        """提取典型问答对作为示例"""
        examples = []
        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]
            if current.role == "user" and next_entry.role == "assistant":
                if len(current.content) >= self.min_content_length and len(next_entry.content) >= self.min_content_length:
                    examples.append({
                        "question": current.content[:200],
                        "answer": next_entry.content[:300],
                    })
            if len(examples) >= 3:
                break
        return examples[:3]

    def _extract_trigger_words(self, topic: str, pattern_type: str) -> List[str]:
        """生成触发词列表"""
        words = []
        # 从主题提取关键词
        segments = re.split(r"[\s,，。、；;:：]+", topic)
        for seg in segments:
            if 2 <= len(seg) <= 10 and seg not in words:
                words.append(seg)
        # 添加模式相关触发词
        pattern_triggers = {
            "故障排查": ["排查", "解决", "修复"],
            "流程指导": ["流程", "步骤", "指南"],
            "知识问答": ["定义", "概念", "原理"],
            "最佳实践": ["最佳实践", "经验", "建议"],
        }
        for trigger in pattern_triggers.get(pattern_type, []):
            if trigger not in words:
                words.append(trigger)
        return words[:8]

    def _calculate_confidence(self, entries: List[ConversationEntry]) -> float:
        """计算提取置信度（0-1）"""
        if len(entries) < 2:
            return 0.3
        # 基于对话长度和完整性
        user_count = sum(1 for e in entries if e.role == "user")
        assistant_count = sum(1 for e in entries if e.role == "assistant")
        total = len(entries)
        ratio = min(user_count / max(total, 1), 1.0) * 0.5 + min(assistant_count / max(total, 1), 1.0) * 0.5
        return min(0.95, 0.4 + ratio * 0.5)


class SkillGenerator:
    """技能文档生成器"""

    def __init__(self, author: str = "认知工坊"):
        self.author = author

    def generate(self, experience: Dict[str, Any], existing: Optional[SkillDocument] = None) -> SkillDocument:
        """根据经验生成技能文档"""
        slug = self._make_slug(experience["topic"])
        name = f"skill-{slug}"
        display_name = experience["topic"]
        description = self._make_description(experience)
        version = self._next_version(existing.version if existing else None)

        doc = SkillDocument(
            slug=slug,
            name=name,
            display_name=display_name,
            description=description,
            version=version,
            trigger_words=experience["trigger_words"],
            steps=experience["steps"],
            examples=experience["examples"],
            metadata={
                "author": self.author,
                "pattern_type": experience["pattern_type"],
                "confidence": experience["confidence"],
                "ai_generated": True,
            },
        )
        return doc

    def _make_slug(self, topic: str) -> str:
        """从主题生成唯一slug"""
        # 转小写、去特殊字符
        cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", topic.lower())
        cleaned = cleaned.strip("-")
        # 添加短哈希确保唯一
        hash_part = hashlib.md5(topic.encode("utf-8")).hexdigest()[:6]
        return f"{cleaned[:30]}-{hash_part}"

    def _make_description(self, experience: Dict[str, Any]) -> str:
        """生成技能描述"""
        return (
            f"从对话中提炼的{experience['pattern_type']}技能，"
            f"主题：{experience['topic']}。"
            f"包含{len(experience['steps'])}个操作步骤，"
            f"{len(experience['examples'])}个典型示例。"
        )

    def _next_version(self, current: Optional[str]) -> str:
        """计算下一个版本号"""
        if not current:
            return "1.0.0"
        parts = current.split(".")
        if len(parts) != 3:
            return "1.0.0"
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            patch += 1
            if patch >= 10:
                patch = 0
                minor += 1
                if minor >= 10:
                    minor = 0
                    major += 1
            return f"{major}.{minor}.{patch}"
        except (ValueError, IndexError):
            return "1.0.0"


class DataSanitizer:
    """数据脱敏器"""

    SENSITIVE_PATTERNS = [
        (r"\b\d{11}\b", "[手机号]"),  # 手机号
        (r"\b\d{17}[\dXx]\b", "[身份证]"),  # 身份证
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[邮箱]"),  # 邮箱
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP地址]"),  # IP地址
        (r"\b\d{16,19}\b", "[银行卡]"),  # 银行卡
    ]

    def sanitize(self, text: str) -> str:
        """对文本进行脱敏处理"""
        result = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result)
        return result

    def sanitize_entries(self, entries: List[ConversationEntry]) -> List[ConversationEntry]:
        """对对话条目列表进行脱敏"""
        sanitized = []
        for entry in entries:
            sanitized.append(
                ConversationEntry(
                    role=entry.role,
                    content=self.sanitize(entry.content),
                    timestamp=entry.timestamp,
                )
            )
        return sanitized


class SkillManager:
    """技能管理器：负责完整流程"""

    def __init__(self, output_dir: str = "skills"):
        self.output_dir = output_dir
        self.extractor = ExperienceExtractor()
        self.generator = SkillGenerator()
        self.sanitizer = DataSanitizer()

    def process_conversation(
        self,
        entries: List[ConversationEntry],
        sanitize: bool = True,
        existing: Optional[SkillDocument] = None,
    ) -> SkillDocument:
        """处理对话并生成/更新技能文档"""
        # 1. 脱敏处理
        if sanitize:
            try:
                entries = self.sanitizer.sanitize_entries(entries)
            except Exception as exc:
                raise SkillError("E009", f"脱敏失败: {exc}")

        # 2. 提取经验
        try:
            experience = self.extractor.extract(entries)
        except SkillError:
            raise
        except Exception as exc:
            raise SkillError("E006", f"经验提取失败: {exc}")

        # 3. 生成技能文档
        try:
            doc = self.generator.generate(experience, existing)
        except Exception as exc:
            raise SkillError("E005", f"技能生成失败: {exc}")

        # 4. 保存文档
        self._save_document(doc)

        return doc

    def _save_document(self, doc: SkillDocument) -> None:
        """保存技能文档到文件"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as exc:
            raise SkillError("E003", f"无法创建输出目录: {exc}")

        filepath = os.path.join(self.output_dir, f"{doc.slug}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(doc.to_json())
        except OSError as exc:
            raise SkillError("E003", f"无法写入文件: {exc}")


def load_conversation(filepath: str) -> List[ConversationEntry]:
    """从JSON文件加载对话数据"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SkillError("E002", f"文件不存在: {filepath}")
    except json.JSONDecodeError as exc:
        raise SkillError("E004", f"JSON解析失败: {exc}")
    except OSError as exc:
        raise SkillError("E002", f"读取失败: {exc}")

    if not isinstance(data, list):
        raise SkillError("E004", "对话数据必须是列表")

    entries = []
    for item in data:
        if not isinstance(item, dict):
            raise SkillError("E004", "对话条目必须是对象")
        entries.append(ConversationEntry.from_dict(item))
    return entries


# ---------- 自检模块 ----------

def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检"""
    print("=== 自检开始 ===")

    # 硬编码样例对话数据
    sample_entries = [
        ConversationEntry(
            role="user",
            content="我的网站部署后一直报500错误，怎么排查？",
            timestamp="2026-01-01T10:00:00+00:00",
        ),
        ConversationEntry(
            role="assistant",
            content="首先查看应用日志，通常位于 /var/log/app/ 目录。然后检查数据库连接是否正常，最后确认配置文件是否正确。",
            timestamp="2026-01-01T10:00:05+00:00",
        ),
        ConversationEntry(
            role="user",
            content="日志里显示数据库连接超时，应该怎么处理？",
            timestamp="2026-01-01T10:00:10+00:00",
        ),
        ConversationEntry(
            role="assistant",
            content="建议检查数据库服务是否启动，然后验证连接参数，可以尝试增加连接超时时间。",
            timestamp="2026-01-01T10:00:15+00:00",
        ),
        ConversationEntry(
            role="user",
            content="好的，我试试。另外我的邮箱是 test@example.com，有什么需要注意的吗？",
            timestamp="2026-01-01T10:00:20+00:00",
        ),
        ConversationEntry(
            role="assistant",
            content="邮箱建议使用企业邮箱，避免使用个人邮箱。同时注意不要在日志中记录敏感信息。",
            timestamp="2026-01-01T10:00:25+00:00",
        ),
    ]

    # 测试1: 经验提取
    print("测试1: 经验提取...")
    extractor = ExperienceExtractor()
    experience = extractor.extract(sample_entries)
    assert experience["topic"], "主题不能为空"
    assert len(experience["steps"]) > 0, "应提取到至少一个步骤"
    assert len(experience["examples"]) > 0, "应提取到至少一个示例"
    assert len(experience["trigger_words"]) > 0, "应提取到至少一个触发词"
    assert 0.0 <= experience["confidence"] <= 1.0, "置信度应在0-1之间"
    print("  通过 ✓")

    # 测试2: 技能文档生成
    print("测试2: 技能文档生成...")
    generator = SkillGenerator()
    doc = generator.generate(experience)
    assert doc.slug, "slug不能为空"
    assert doc.version == "1.0.0", "首个版本应为1.0.0"
    assert doc.display_name, "显示名称不能为空"
    assert doc.description, "描述不能为空"
    doc_dict = doc.to_dict()
    assert "createdAt" in doc_dict, "应有创建时间"
    assert "updatedAt" in doc_dict, "应有更新时间"
    print("  通过 ✓")

    # 测试3: 版本迭代
    print("测试3: 版本迭代...")
    doc2 = generator.generate(experience, existing=doc)
    assert doc2.version != doc.version, "版本号应递增"
    assert doc2.version > doc.version, "新版本应大于旧版本"
    print(f"  通过 ✓ (版本 {doc.version} -> {doc2.version})")

    # 测试4: 脱敏处理
    print("测试4: 脱敏处理...")
    sanitizer = DataSanitizer()
    assert "[邮箱]" in sanitizer.sanitize("联系我 test@example.com"), "邮箱应被脱敏"
    assert "[手机号]" in sanitizer.sanitize("电话 13812345678"), "手机号应被脱敏"
    assert "[IP地址]" in sanitizer.sanitize("服务器 192.168.1.1"), "IP应被脱敏"
    print("  通过 ✓")

    # 测试5: 完整流程（使用临时目录）
    print("测试5: 完整流程...")
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillManager(output_dir=tmpdir)
        result_doc = manager.process_conversation(sample_entries, sanitize=True)
        assert result_doc.slug, "生成文档应有slug"
        # 检查文件是否生成
        filepath = os.path.join(tmpdir, f"{result_doc.slug}.json")
        assert os.path.exists(filepath), "技能文件应已生成"
        # 验证文件内容
        with open(filepath, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["name"] == result_doc.name, "保存的数据应一致"
        # 验证脱敏生效
        assert "[邮箱]" in json.dumps(saved_data, ensure_ascii=False), "输出中不应包含原始邮箱"
    print("  通过 ✓")

    # 测试6: 错误处理
    print("测试6: 错误处理...")
    try:
        extractor.extract([])
        assert False, "空对话应抛错"
    except SkillError as exc:
        assert exc.code == "E006", f"错误码应为E006，实际: {exc.code}"
    print("  通过 ✓")

    # 测试7: 敏感信息不泄露
    print("测试7: 敏感信息检查...")
    # 使用完整流程处理后的文档进行检查
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SkillManager(output_dir=tmpdir)
        sanitized_doc = manager.process_conversation(sample_entries, sanitize=True)
        all_output_text = json.dumps(sanitized_doc.to_dict(), ensure_ascii=False)
        assert "test@example.com" not in all_output_text, "输出不应包含原始邮箱"
        assert "[邮箱]" in all_output_text, "输出应包含脱敏后的邮箱标记"
    print("  通过 ✓")

    print("=== 全部自检通过 ===")
    return True


# ---------- 命令行入口 ----------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="会话经验提炼与技能生成工具",
        epilog="示例: python main.py --input conversation.json --output skills",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入对话JSON文件路径",
    )
    parser.add_argument(
        "--output", "-o",
        default="skills",
        help="技能文档输出目录（默认: skills）",
    )
    parser.add_argument(
        "--no-sanitize",
        action="store_true",
        help="禁用数据脱敏（不推荐）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检并退出",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="self-learning-skills 1.0.2",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code != 0:
            print(f"[E001] {ERROR_CODES['E001']}", file=sys.stderr)
        return exc.code if isinstance(exc.code, int) else 1

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as exc:
            print(f"[E007] 自检异常: {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}: 请提供 --input 参数或使用 --selftest", file=sys.stderr)
        return 1

    try:
        # 加载对话
        entries = load_conversation(args.input)

        # 处理对话
        manager = SkillManager(output_dir=args.output)
        doc = manager.process_conversation(
            entries,
            sanitize=not args.no_sanitize,
        )

        # 输出结果
        output_path = os.path.join(args.output, f"{doc.slug}.json")
        print(f"✅ 技能文档已生成: {output_path}")
        print(f"   标题: {doc.display_name}")
        print(f"   版本: {doc.version}")
        print(f"   步骤数: {len(doc.steps)}")
        print(f"   示例数: {len(doc.examples)}")
        return 0

    except SkillError as exc:
        print(f"{exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] {ERROR_CODES['E010']}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
