#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-guide: AI资源导航、教程速查与提示词手册（独立实现）
版本: 1.0.1 (clean-room implementation)
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数解析失败或缺少必要参数",
    "E002": "查询关键词为空或类型错误",
    "E003": "未找到匹配的资源或条目",
    "E004": "分类不存在或无效",
    "E005": "输入数据格式非法（非 JSON）",
    "E006": "缺少必需字段（如 name/type）",
    "E007": "内部数据加载失败",
    "E008": "自检断言失败",
    "E009": "文件读写异常",
    "E010": "未知运行时错误",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg}: {message}"
    print(f"[ERROR {code}] {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 内置数据（硬编码，不依赖外部文件）
# ---------------------------------------------------------------------------
BUILTIN_DATA: Dict[str, List[Dict[str, Union[str, List[str]]]]] = {
    "工具资源": [
        {"name": "ChatGPT", "type": "对话助手", "tags": ["OpenAI", "通用", "文本生成"]},
        {"name": "Claude", "type": "对话助手", "tags": ["Anthropic", "长文本", "分析"]},
        {"name": "Midjourney", "type": "图像生成", "tags": ["AI绘画", "艺术", "创意"]},
        {"name": "GitHub Copilot", "type": "编程辅助", "tags": ["代码补全", "IDE", "开发"]},
        {"name": "Hugging Face", "type": "模型平台", "tags": ["开源模型", "NLP", "社区"]},
    ],
    "教程章节": [
        {"name": "提示词基础", "type": "入门", "tags": ["prompt", "技巧", "模板"]},
        {"name": "Vibe Coding 入门", "type": "进阶", "tags": ["编程", "AI辅助", "工作流"]},
        {"name": "AI 绘画实战", "type": "实战", "tags": ["图像", "Midjourney", "Stable Diffusion"]},
        {"name": "大模型 API 调用", "type": "开发", "tags": ["API", "Python", "部署"]},
    ],
    "提示词模板": [
        {"name": "角色扮演模板", "type": "模板", "tags": ["角色", "对话", "情景"]},
        {"name": "结构化输出模板", "type": "模板", "tags": ["JSON", "表格", "格式"]},
        {"name": "代码审查模板", "type": "模板", "tags": ["代码", "质量", "Bug"]},
        {"name": "学习计划模板", "type": "模板", "tags": ["教育", "计划", "目标"]},
    ],
}


# ---------------------------------------------------------------------------
# 核心查询逻辑
# ---------------------------------------------------------------------------
def search_resources(
    keyword: str,
    category: Optional[str] = None,
    data: Optional[Dict[str, List[Dict[str, Union[str, List[str]]]]]] = None,
) -> List[Dict[str, Union[str, List[str]]]]:
    """
    根据关键词（匹配名称/类型/标签）和可选分类进行检索。
    返回匹配的资源列表。若关键词为空，返回指定分类下全部（或全部资源）。
    """
    if not isinstance(keyword, str):
        raise TypeError("关键词必须是字符串")

    dataset = data if data is not None else BUILTIN_DATA

    # 分类过滤
    if category:
        if category not in dataset:
            raise KeyError(f"分类不存在: {category}")
        candidates = dataset[category]
    else:
        # 展平所有分类
        candidates = [item for items in dataset.values() for item in items]

    # 关键词为空：返回全部候选
    if not keyword.strip():
        return candidates

    # 关键词匹配（不区分大小写）
    kw_lower = keyword.strip().lower()
    results = []
    for item in candidates:
        name = str(item.get("name", "")).lower()
        item_type = str(item.get("type", "")).lower()
        tags = [str(t).lower() for t in item.get("tags", [])]
        if kw_lower in name or kw_lower in item_type or any(kw_lower in t for t in tags):
            results.append(item)
    return results


def list_categories(data: Optional[Dict[str, List[Dict[str, Union[str, List[str]]]]]] = None) -> List[str]:
    """返回所有分类名称。"""
    dataset = data if data is not None else BUILTIN_DATA
    return list(dataset.keys())


def format_results(results: List[Dict[str, Union[str, List[str]]]]) -> str:
    """将结果格式化为可读文本（Markdown 风格）。"""
    if not results:
        return "（无匹配结果）"

    lines = []
    for idx, item in enumerate(results, 1):
        name = item.get("name", "未知")
        item_type = item.get("type", "未分类")
        tags = item.get("tags", [])
        tags_str = ", ".join(tags) if tags else "无标签"
        lines.append(f"{idx}. **{name}**（{item_type}） — 标签: {tags_str}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 数据校验与加载
# ---------------------------------------------------------------------------
def validate_data(data: Dict) -> bool:
    """
    校验数据结构是否符合预期：
    顶层为 dict，值为 list，每个元素是包含 name/type/tags 的 dict。
    返回 True 或抛出 ValueError。
    """
    if not isinstance(data, dict) or not data:
        raise ValueError("数据必须是非空字典")

    for category, items in data.items():
        if not isinstance(category, str) or not category:
            raise ValueError("分类名必须是非空字符串")
        if not isinstance(items, list):
            raise ValueError(f"分类 '{category}' 的值必须是列表")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"分类 '{category}' 中的条目必须是字典")
            if "name" not in item or "type" not in item:
                raise ValueError(f"分类 '{category}' 中的条目缺少 name 或 type 字段")
            if "tags" in item and not isinstance(item["tags"], list):
                raise ValueError(f"条目 '{item.get('name', '')}' 的 tags 必须是列表")
    return True


def load_json_data(json_str: str) -> Dict:
    """从 JSON 字符串加载并校验数据。失败时抛出异常。"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}")
    validate_data(data)
    return data


# ---------------------------------------------------------------------------
# 自检模块（离线，硬编码样例，宽松断言）
# ---------------------------------------------------------------------------
def run_selftest() -> None:
    """
    内置自检：使用硬编码样例验证核心逻辑。
    不读取外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值（大小/区间判断）确保稳健。
    """
    print("=== 自检开始 ===")

    # 1. 分类列表非空且包含预期分类
    cats = list_categories()
    assert len(cats) >= 3, "分类数量应至少为 3"
    assert "工具资源" in cats and "教程章节" in cats and "提示词模板" in cats, "缺少核心分类"
    print("[1/5] 分类列表检查通过")

    # 2. 关键词搜索返回结果数合理（宽松区间）
    results = search_resources("AI")
    # 至少应匹配到若干条目（我们硬编码数据中 "AI" 出现在多个标签）
    assert len(results) > 0, "关键词 'AI' 应至少匹配一条"
    assert len(results) <= 50, "结果数量不应过多（数据量限制）"
    print(f"[2/5] 关键词检索检查通过（匹配 {len(results)} 条）")

    # 3. 分类过滤 + 关键词组合
    filtered = search_resources("模板", category="提示词模板")
    # 模板分类中至少有一个包含“模板”关键词
    assert len(filtered) >= 1, "提示词模板分类中应至少有一条匹配 '模板'"
    print("[3/5] 分类过滤检查通过")

    # 4. 空关键词返回全部
    all_items = search_resources("")
    assert len(all_items) >= 10, "空关键词应返回全部条目（至少 10 条）"
    assert len(all_items) <= 100, "数据量不应过大"
    print("[4/5] 空关键词检查通过")

    # 5. 数据校验逻辑
    try:
        validate_data({"测试分类": [{"name": "X", "type": "Y", "tags": []}]})
        validate_data({"测试分类": [{"name": "X", "type": "Y"}]})  # tags 可选
        print("[5/5] 数据校验检查通过")
    except ValueError as e:
        raise AssertionError(f"数据校验不应失败: {e}")

    # 6. 错误处理检查（非法数据应抛异常）
    try:
        validate_data({"bad": [{"name": "no-type"}]})
        raise AssertionError("缺少 type 字段应触发 ValueError")
    except ValueError:
        pass  # 预期异常

    print("=== 自检全部通过 ===")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ai-guide: AI 资源导航、教程速查与提示词手册",
        epilog="示例: python main.py --search 'AI 绘画' --category 工具资源",
    )
    parser.add_argument("--search", type=str, default="", help="搜索关键词（匹配名称/类型/标签）")
    parser.add_argument("--category", type=str, default=None, help="限定分类（可选）")
    parser.add_argument("--list-categories", action="store_true", help="列出所有分类")
    parser.add_argument("--json", type=str, default=None, help="以 JSON 字符串提供自定义数据（覆盖内置数据）")
    parser.add_argument("--selftest", action="store_true", help="运行内置离线自检")

    args = parser.parse_args(argv)

    # 自检模式优先
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            fail("E008", str(e))
        except Exception as e:
            fail("E010", f"自检异常: {e}")

    # 加载数据（支持自定义 JSON）
    data = BUILTIN_DATA
    if args.json:
        try:
            data = load_json_data(args.json)
        except ValueError as e:
            fail("E005", str(e))
        except Exception as e:
            fail("E010", f"数据加载异常: {e}")

    # 列出分类
    if args.list_categories:
        try:
            cats = list_categories(data)
            print("可用分类:")
            for c in cats:
                print(f"  - {c}")
            return 0
        except Exception as e:
            fail("E010", str(e))

    # 搜索
    try:
        results = search_resources(args.search, args.category, data)
    except KeyError as e:
        fail("E004", str(e))
    except TypeError as e:
        fail("E002", str(e))
    except Exception as e:
        fail("E010", str(e))

    # 输出结果
    if not results:
        fail("E003", f"未找到匹配 '{args.search}' 的资源")
    print(format_results(results))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
