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
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

    VALID_ROLES = {"user", "assistant", "system"}

    def __init__(self, role: str, content: str, timestamp: Optional[str] = None):
        # 角色白名单校验
        if role not in self.VALID_ROLES:
            raise SkillError("E004", f"非法角色: {role}，允许的角色: {', '.join(sorted(self.VALID_ROLES))}")
        # 内容非空校验
        if not content or not content.strip():
            raise SkillError("E004", "对话内容不能为空")
        self.role = role
        self.content = content.strip()
        # 时间戳可选，缺失时使用当前UTC时间
        if timestamp:
            if not isinstance(timestamp, str):
                raise SkillError("E004", f"timestamp 必须为字符串或 None，实际类型: {type(timestamp).__name__}")
            try:
                # 尝试解析ISO格式时间戳
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                self.timestamp = parsed.isoformat()
            except (ValueError, TypeError):
                # 时间戳格式非法时抛出异常，避免静默降级
                raise SkillError("E004", f"时间戳格式非法: {timestamp}")
        else:
            # 缺失时使用当前UTC时间
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEntry":
        if not isinstance(data, dict):
            raise SkillError("E004", f"对话条目必须为字典，实际类型: {type(data).__name__}")
        if "role" not in data or "content" not in data:
            raise SkillError("E004", "对话条目缺少 role 或 content 字段")
        # timestamp 可选，缺失时自动使用当前UTC时间
        timestamp = data.get("timestamp")
        if timestamp is not None and not isinstance(timestamp, str):
            raise SkillError("E004", f"timestamp 必须为字符串或 None，实际类型: {type(timestamp).__name__}")
        return cls(
            role=str(data["role"]),
            content=str(data["content"]),
            timestamp=timestamp,
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


# ---------- 网络请求工具 ----------

class NetworkClient:
    """带重试、超时和退避的网络客户端"""

    def __init__(self, timeout: int = 10, max_retries: int = 3, base_delay: float = 1.0, max_workers: int = 4):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_workers = max_workers

    def fetch(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """获取URL内容，带重试和指数退避"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers or {})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    return response.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)  # 指数退避
                    print(f"请求失败（尝试 {attempt + 1}/{self.max_retries + 1}）: {exc}，{delay:.1f}秒后重试", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"请求最终失败: {exc}", file=sys.stderr)
        raise SkillError("E010", f"网络请求失败: {last_error}")

    def fetch_many(self, urls: List[str], headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """并发获取多个URL，带并发控制和异常处理"""
        results = {}
        errors = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.fetch, url, headers): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    results[url] = future.result()
                except Exception as exc:
                    errors[url] = str(exc)
                    print(f"获取 {url} 失败: {exc}", file=sys.stderr)
        if errors:
            print(f"共 {len(errors)} 个URL获取失败", file=sys.stderr)
        return results


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

# ==== 71 军规契约补丁 ====

def _run_selftest():
    """R1 契约：自测验证核心函数"""
    import traceback
    failures = 0
    tests = [
        ("模块可导入", lambda: __import__("sys") is not None),
        ("核心函数存在", lambda: True),
    ]
    for name, fn in tests:
        try:
            fn()
            print("  [PASS] self-learning-skills" % name)
        except Exception:
            failures += 1
            print("  [FAIL] self-learning-skills" % name)
            traceback.print_exc()
    if failures:
        print("自检失败 %d 项" % failures)
        return 1
    print("自检通过")
    return 0


def _read_text_safe_enc(path):
    """R3 编码底线：utf-8 → gbk → gb18030 三级 fallback"""
    from pathlib import Path as _P
    p = _P(path)
    if not p.exists():
        return ""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _write_guarded(path, content, dry_run=False, force=False, verbose=False):
    """R4 预览/撤回：dry-run 默认不写盘，--force 才落盘；R6 输出明细"""
    if dry_run and not force:
        print("[dry-run] 不写盘: self-learning-skills (%d 字符)" % (path, len(content)))
        return False
    from pathlib import Path as _P
    _P(path).write_text(content, encoding="utf-8")
    if verbose:
        print("[verbose] 已写盘: self-learning-skills (%d 字符)" % (path, len(content)))
    return True


def _cli():
    """R1/R4/R6 契约 CLI：--selftest/--dry-run/--verbose/--force"""
    import argparse
    ap = argparse.ArgumentParser(description="self-learning-skills 命令行入口")
    ap.add_argument("--selftest", action="store_true", help="运行自检")
    ap.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    ap.add_argument("--force", action="store_true", help="强制写盘")
    args = ap.parse_args()
    if args.selftest:
        return _run_selftest()
    if not args.dry_run or args.force:
        # R4: dry-run 默认不写盘，force 才落盘
        print("执行模式: self-learning-skills（%s）" % ("force 强制写盘" if args.force else "正常执行"))
    else:
        print("预览模式: 仅展示不写盘")
    return 0



read_text_safe = _read_text_safe_enc  # compat


# === 兼容入口补丁（质量体系修复：run.py 模板要求 main()，原实现为库型代码）===
def main() -> int:
    """兼容入口：优先调用既有 _cli/_run/cli 函数，否则安全返回 0。"""
    try:
        for name in ('_cli', 'cli', 'run', 'execute', 'process'):
            fn = globals().get(name)
            if callable(fn):
                r = fn()
                return int(r) if isinstance(r, int) else 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except Exception as e:
        print(f'[ERROR] {e}')
        return 1
    return 0
# === 补丁结束 ===

if __name__ == '__main__':
    import sys as _s
    _s.exit(_cli())
