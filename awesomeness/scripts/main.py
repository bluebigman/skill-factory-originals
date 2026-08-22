#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesomeness — Rails 组件速查与代码片段检索工具

本脚本根据功能规格独立实现，提供以下能力：
1. 将零散的 Rails 代码片段、组件说明或仓库链接转化为结构化速查卡片
2. 输出带置信度标注的检索结果，便于后续查阅与集成
3. 内置离线自检模式（--selftest），不依赖外部文件或网络

仅使用 Python 标准库实现。
"""

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式不正确（应为 JSON 字符串或字典）",
    "E003": "缺少必填字段（slug、name、description 至少其一）",
    "E004": "输入内容不是有效的 Rails 相关文本",
    "E005": "置信度计算失败（内部错误）",
    "E006": "输出序列化失败",
    "E007": "自检断言失败",
    "E008": "不支持的参数组合",
    "E009": "内部逻辑异常",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能运行异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class RailsComponent:
    """Rails 组件速查卡片"""
    slug: str
    name: str
    description: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    snippets: List[str] = field(default_factory=list)
    source_url: str = ""
    confidence: float = 0.0
    raw_input: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ============================================================
# 核心逻辑：Rails 内容识别与解析
# ============================================================
# Rails 相关关键词，用于内容识别
RAILS_KEYWORDS = [
    "rails", "ruby", "gem", "activerecord", "activesupport", "actionpack",
    "actionview", "actionmailer", "activejob", "actioncable", "activestorage",
    "actionmailbox", "actiontext", "railties", "bundler", "rake", "migration",
    "model", "controller", "view", "helper", "concern", "callback", "validator",
    "scope", "association", "has_many", "belongs_to", "has_one", "has_and_belongs_to_many",
    "find_each", "find_in_batches", "pluck", "select", "where", "order", "limit",
    "offset", "group", "having", "joins", "includes", "preload", "eager_load",
    "ransack", "devise", "cancancan", "pundit", "kaminari", "will_paginate",
    "sidekiq", "delayed_job", "resque", "carrierwave", "shrine", "paperclip",
    "sprockets", "webpacker", "importmap", "turbo", "stimulus", "hotwire",
    "api", "rest", "graphql", "websocket", "redis", "sqlite", "postgresql", "mysql",
]

# 组件类别关键词映射
CATEGORY_KEYWORDS = {
    "activerecord": ["activerecord", "model", "migration", "association", "scope", "find_each", "find_in_batches", "pluck", "where", "order", "group", "having", "joins", "includes", "preload", "eager_load", "has_many", "belongs_to", "has_one"],
    "actionpack": ["actionpack", "controller", "view", "helper", "routing", "params", "session", "cookies", "flash"],
    "actioncable": ["actioncable", "websocket", "channel", "broadcast", "stream"],
    "activejob": ["activejob", "sidekiq", "delayed_job", "resque", "queue", "worker", "perform"],
    "activestorage": ["activestorage", "attachment", "blob", "upload", "file"],
    "authentication": ["devise", "cancancan", "pundit", "authentication", "authorization", "login", "signup"],
    "api": ["api", "rest", "graphql", "serializer", "json"],
    "frontend": ["sprockets", "webpacker", "importmap", "turbo", "stimulus", "hotwire", "javascript", "css"],
    "caching": ["cache", "redis", "memcached", "fragment"],
    "testing": ["rspec", "minitest", "factory_bot", "faker", "test", "spec"],
}


def normalize_text(text: str) -> str:
    """标准化文本：去除多余空白，统一换行符"""
    if not text:
        return ""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除多余空白
    text = re.sub(r"[ \t]+", " ", text)
    # 去除多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_rails_relevance(text: str) -> float:
    """
    检测文本与 Rails 的相关性，返回 0.0 ~ 1.0 的置信度。
    基于关键词命中率计算。
    """
    if not text:
        return 0.0
    
    normalized = normalize_text(text).lower()
    if not normalized:
        return 0.0
    
    # 统计关键词命中
    hit_count = 0
    for keyword in RAILS_KEYWORDS:
        if keyword.lower() in normalized:
            hit_count += 1
    
    # 计算置信度：命中 1 个关键词为 0.3，每多命中 1 个增加 0.15，上限 0.95
    if hit_count == 0:
        return 0.0
    confidence = min(0.3 + (hit_count - 1) * 0.15, 0.95)
    return round(confidence, 2)


def detect_category(text: str) -> str:
    """根据关键词检测组件类别"""
    if not text:
        return "general"
    
    normalized = normalize_text(text).lower()
    max_score = 0
    best_category = "general"
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in normalized)
        if score > max_score:
            max_score = score
            best_category = category
    
    return best_category


def extract_tags(text: str) -> List[str]:
    """从文本中提取标签（关键词）"""
    if not text:
        return []
    
    normalized = normalize_text(text).lower()
    tags = []
    for keyword in RAILS_KEYWORDS:
        if keyword.lower() in normalized and keyword not in tags:
            tags.append(keyword)
    
    # 限制标签数量
    return tags[:10]


def generate_slug(text: str) -> str:
    """从文本生成 slug"""
    if not text:
        return "rails-component"
    
    # 提取关键词并生成 slug
    normalized = normalize_text(text).lower()
    # 移除特殊字符
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    # 取前 5 个词
    words = normalized.split()[:5]
    if not words:
        return "rails-component"
    
    slug = "-".join(words)
    # 确保 slug 不以数字开头
    if slug[0].isdigit():
        slug = "rails-" + slug
    
    return slug[:80]


def extract_snippets(text: str) -> List[str]:
    """从文本中提取代码片段（以 ``` 包裹的内容）"""
    if not text:
        return []
    
    snippets = []
    # 匹配 ``` 包裹的代码块
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        snippet = match.strip()
        if snippet:
            snippets.append(snippet)
    
    return snippets[:5]


def parse_input_text(text: str) -> Dict[str, Any]:
    """
    解析输入文本，生成速查卡片数据。
    
    参数:
        text: 输入的 Rails 相关文本
    
    返回:
        包含速查卡片字段的字典
    
    异常:
        SkillError: 当输入为空或不是有效的 Rails 相关文本时
    """
    if not text or not text.strip():
        raise SkillError("E001", "输入文本为空")
    
    normalized = normalize_text(text)
    if not normalized:
        raise SkillError("E001", "输入文本为空")
    
    # 检测 Rails 相关性
    confidence = detect_rails_relevance(normalized)
    if confidence < 0.3:
        raise SkillError("E004", f"输入内容与 Rails 相关性过低（置信度: {confidence}）")
    
    # 提取信息
    category = detect_category(normalized)
    tags = extract_tags(normalized)
    slug = generate_slug(normalized)
    snippets = extract_snippets(normalized)
    
    # 生成名称：取前 3 个词作为名称
    words = normalized.split()[:3]
    name = " ".join(words) if words else "Rails Component"
    
    # 生成描述：取前 100 个字符
    description = normalized[:100] + ("..." if len(normalized) > 100 else "")
    
    return {
        "slug": slug,
        "name": name,
        "description": description,
        "category": category,
        "tags": tags,
        "snippets": snippets,
        "source_url": "",
        "confidence": confidence,
        "raw_input": normalized[:500],  # 限制原始输入长度
    }


def parse_input_json(json_str: str) -> List[Dict[str, Any]]:
    """
    解析 JSON 格式的输入，支持单个对象或对象数组。
    
    参数:
        json_str: JSON 字符串
    
    返回:
        速查卡片数据列表
    
    异常:
        SkillError: 当 JSON 格式不正确或缺少必要字段时
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise SkillError("E002", f"JSON 解析失败: {e}")
    
    # 如果是单个对象，转为数组
    if isinstance(data, dict):
        data = [data]
    
    if not isinstance(data, list):
        raise SkillError("E002", "输入应为 JSON 对象或数组")
    
    results = []
    for item in data:
        if not isinstance(item, dict):
            raise SkillError("E002", "数组中的每个元素应为 JSON 对象")
        
        # 支持两种格式：直接包含 content 字段，或包含 slug/name/description
        if "content" in item:
            content = item["content"]
            if not isinstance(content, str):
                raise SkillError("E002", "content 字段应为字符串")
            try:
                result = parse_input_text(content)
            except SkillError as e:
                # 单条失败不中断整体，记录错误并跳过
                print(f"警告: 跳过无效记录: {e}", file=sys.stderr)
                continue
        elif "slug" in item and "name" in item and "description" in item:
            # 已经是结构化数据，直接使用
            result = {
                "slug": str(item["slug"]),
                "name": str(item["name"]),
                "description": str(item["description"]),
                "category": str(item.get("category", "general")),
                "tags": item.get("tags", []),
                "snippets": item.get("snippets", []),
                "source_url": str(item.get("source_url", "")),
                "confidence": float(item.get("confidence", 0.0)),
                "raw_input": str(item.get("raw_input", "")),
            }
        else:
            raise SkillError("E003", "每条记录需包含 content 字段或 slug/name/description 字段")
        
        results.append(result)
    
    if not results:
        raise SkillError("E003", "没有有效的输入记录")
    
    return results


def format_output(results: List[Dict[str, Any]], verbose: bool = False) -> str:
    """
    格式化输出结果。
    
    参数:
        results: 速查卡片数据列表
        verbose: 是否输出详细决策信息
    
    返回:
        格式化后的 JSON 字符串
    """
    try:
        if verbose:
            # 详细模式：输出决策明细
            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total": len(results),
                "results": results,
                "decisions": [
                    {
                        "slug": r["slug"],
                        "confidence": r["confidence"],
                        "category": r["category"],
                        "tags_count": len(r["tags"]),
                        "snippets_count": len(r["snippets"]),
                    }
                    for r in results
                ],
            }
        else:
            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total": len(results),
                "results": results,
            }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    except Exception as e:
        raise SkillError("E006", f"输出序列化失败: {e}")


def atomic_write_file(filepath: str, content: str) -> None:
    """
    原子化写入文件：先写入临时文件，再替换目标文件。
    
    参数:
        filepath: 目标文件路径
        content: 要写入的内容
    """
    dirname = os.path.dirname(os.path.abspath(filepath))
    if not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(dir=dirname, prefix=".awesomeness_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # 替换目标文件
        os.replace(temp_path, filepath)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def read_file_with_encoding(filepath: str) -> str:
    """
    读取文件内容，支持多编码（utf-8 → gbk → gb18030 三级 fallback）。
    
    参数:
        filepath: 文件路径
    
    返回:
        文件内容字符串
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    last_error = None
    
    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
    
    # 所有编码都失败，使用 errors="replace"
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        raise SkillError("E009", f"读取文件失败: {e}")


def process_input_text(text: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    处理单条文本输入。
    
    参数:
        text: 输入的 Rails 相关文本
        verbose: 是否输出详细决策信息
    
    返回:
        速查卡片数据列表
    """
    try:
        result = parse_input_text(text)
        if verbose:
            print(f"决策明细: slug={result['slug']}, confidence={result['confidence']}, category={result['category']}", file=sys.stderr)
        return [result]
    except SkillError as e:
        raise
    except Exception as e:
        raise SkillError("E009", f"处理文本失败: {e}")


def process_input_file(filepath: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """
    处理 JSON 文件输入。
    
    参数:
        filepath: JSON 文件路径
        verbose: 是否输出详细决策信息
    
    返回:
        速查卡片数据列表
    """
    try:
        content = read_file_with_encoding(filepath)
        results = parse_input_json(content)
        if verbose:
            for r in results:
                print(f"决策明细: slug={r['slug']}, confidence={r['confidence']}, category={r['category']}", file=sys.stderr)
        return results
    except SkillError as e:
        raise
    except Exception as e:
        raise SkillError("E009", f"处理文件失败: {e}")


# ============================================================
# 自检模式
# ============================================================
def run_selftest() -> int:
    """
    运行自检，验证核心功能。
    
    返回:
        0 表示全部通过，非 0 表示失败
    """
    print("开始自检...")
    failures = 0
    
    # 测试 1: 正常 Rails 文本识别
    print("\n[测试 1] 正常 Rails 文本识别")
    try:
        result = parse_input_text("使用 find_each 批量处理 ActiveRecord 记录，避免内存溢出")
        assert result["confidence"] >= 0.3, f"置信度应 >= 0.3, 实际: {result['confidence']}"
        assert result["category"] == "activerecord", f"类别应为 activerecord, 实际: {result['category']}"
        assert len(result["tags"]) > 0, "标签不应为空"
        print(f"  ✅ 通过: confidence={result['confidence']}, category={result['category']}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 2: 中文标点与编码处理
    print("\n[测试 2] 中文标点与编码处理")
    try:
        result = parse_input_text("使用 Rails 的缓存机制，提高 API 响应速度。")
        assert result["confidence"] >= 0.3, f"置信度应 >= 0.3, 实际: {result['confidence']}"
        print(f"  ✅ 通过: confidence={result['confidence']}, slug={result['slug']}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 3: 空输入处理
    print("\n[测试 3] 空输入处理")
    try:
        parse_input_text("")
        failures += 1
        print("  ❌ 失败: 空输入应抛出异常")
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001, 实际: {e.code}"
        print(f"  ✅ 通过: 正确抛出 E001 错误")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 4: 非 Rails 文本处理
    print("\n[测试 4] 非 Rails 文本处理")
    try:
        parse_input_text("今天天气很好，适合出去散步。")
        failures += 1
        print("  ❌ 失败: 非 Rails 文本应抛出异常")
    except SkillError as e:
        assert e.code == "E004", f"错误码应为 E004, 实际: {e.code}"
        print(f"  ✅ 通过: 正确抛出 E004 错误")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 5: JSON 批量处理
    print("\n[测试 5] JSON 批量处理")
    try:
        json_str = json.dumps([
            {"content": "使用 find_each 批量处理 ActiveRecord 记录"},
            {"content": "ActionCable 实现实时通知功能"},
        ])
        results = parse_input_json(json_str)
        assert len(results) == 2, f"应返回 2 条结果, 实际: {len(results)}"
        print(f"  ✅ 通过: 返回 {len(results)} 条结果")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 6: 无效 JSON 处理
    print("\n[测试 6] 无效 JSON 处理")
    try:
        parse_input_json("{invalid json")
        failures += 1
        print("  ❌ 失败: 无效 JSON 应抛出异常")
    except SkillError as e:
        assert e.code == "E002", f"错误码应为 E002, 实际: {e.code}"
        print(f"  ✅ 通过: 正确抛出 E002 错误")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 7: 超长输入处理
    print("\n[测试 7] 超长输入处理")
    try:
        long_text = "Rails " * 1000 + " ActiveRecord find_each"
        result = parse_input_text(long_text)
        assert result["confidence"] >= 0.3, f"置信度应 >= 0.3, 实际: {result['confidence']}"
        print(f"  ✅ 通过: 处理 {len(long_text)} 字符输入, confidence={result['confidence']}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 8: 输出格式化
    print("\n[测试 8] 输出格式化")
    try:
        result = parse_input_text("使用 find_each 批量处理 ActiveRecord 记录")
        output = format_output([result], verbose=True)
        data = json.loads(output)
        assert "timestamp" in data, "输出应包含 timestamp"
        assert "results" in data, "输出应包含 results"
        assert "decisions" in data, "详细模式应包含 decisions"
        print(f"  ✅ 通过: 输出包含 {len(data['results'])} 条结果")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        atomic_write_file(temp_path, '{"test": true}')
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert json.loads(content) == {"test": True}, "写入内容应正确"
        os.unlink(temp_path)
        print(f"  ✅ 通过: 原子写入成功")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 10: 多编码读取
    print("\n[测试 10] 多编码读取")
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("测试中文内容".encode("gbk"))
            temp_path = f.name
        content = read_file_with_encoding(temp_path)
        assert "测试" in content, "应能正确读取 GBK 编码文件"
        os.unlink(temp_path)
        print(f"  ✅ 通过: 多编码读取成功")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 汇总
    print(f"\n自检完成: {10 - failures}/10 通过")
    if failures > 0:
        print(f"❌ {failures} 项测试失败")
        return 1
    else:
        print("✅ 全部测试通过")
        return 0


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="awesomeness — Rails 组件速查与代码片段检索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --input "使用 find_each 批量处理 ActiveRecord 记录"
  python run.py --file input.json --output result.json
  python run.py --selftest
        """,
    )
    
    # 输入参数（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本（Rails 相关代码片段或说明）",
    )
    input_group.add_argument(
        "--file", "-f",
        type=str,
        help="输入 JSON 文件路径（包含 content 字段的对象数组）",
    )
    
    # 输出参数
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（默认输出到 stdout）",
    )
    
    # 功能参数
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：只打印将写入的内容，不实际写盘",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细模式：输出每个决策的明细信息",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 参数校验
    if not args.input and not args.file:
        parser.error("必须提供 --input 或 --file 参数")
        return 1
    
    if args.input and args.file:
        parser.error("--input 和 --file 参数互斥，只能使用其中一个")
        return 1
    
    try:
        # 处理输入
        if args.input:
            results = process_input_text(args.input, verbose=args.verbose)
        else:
            results = process_input_file(args.file, verbose=args.verbose)
        
        # 格式化输出
        output = format_output(results, verbose=args.verbose)
        
        # 输出结果
        if args.output:
            if not dry_run:
                # 正式写盘
                atomic_write_file(args.output, output)
                print(f"✅ 结果已写入: {args.output}")
            else:
                # 预览模式：不写盘，只打印信息
                print(f"[dry-run] 将写入: {args.output}")
                print(f"[dry-run] 摘要: {len(results)} 条记录")
                for r in results:
                    print(f"[dry-run]   - {r['slug']} (置信度: {r['confidence']})")
        else:
            # 输出到 stdout
            print(output)
        
        return 0
        
    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        print(f"错误码: {e.code}", file=sys.stderr)
        print("提示: 请检查输入参数，或使用 --selftest 运行自检", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        print("错误码: E010", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
