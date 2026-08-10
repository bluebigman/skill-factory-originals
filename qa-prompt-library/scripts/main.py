#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa-prompt-library 技能实现脚本
================================
独立实现，基于功能规格文档编写（clean-room）。
提供 QA Prompt 库的核心处理流程，支持命令行调用与离线自检。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
SKILL_NAME = "qa-prompt-library"
VERSION = "1.0.0"
DEFAULT_CONFIDENCE = 0.90          # 默认置信度阈值
REVIEW_CONFIDENCE = 0.85          # 建议复核阈值
MIN_CONFIDENCE = 0.0              # 最低置信度

# 错误码与话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
}


# ============================================================
# 核心数据结构
# ============================================================
class QAItem:
    """QA 提示词条目"""
    def __init__(self, title: str, category: str, prompt: str, tags: List[str] = None):
        self.title = title
        self.category = category
        self.prompt = prompt
        self.tags = tags or []
        self.confidence = DEFAULT_CONFIDENCE

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "category": self.category,
            "prompt": self.prompt,
            "tags": self.tags,
            "confidence": self.confidence,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
class QAPromptLibrary:
    """QA Prompt 库核心处理类"""

    def __init__(self):
        self.items: List[QAItem] = []
        self._load_default_items()

    def _load_default_items(self) -> None:
        """加载内置默认条目（离线可用）"""
        defaults = [
            QAItem(
                title="测试用例创建",
                category="手动测试",
                prompt="根据需求文档创建详细的测试用例，包括正常流程、边界条件和异常场景。",
                tags=["测试用例", "手动", "创建"],
            ),
            QAItem(
                title="自动化测试脚本生成",
                category="自动化测试",
                prompt="将手动测试用例转换为自动化测试脚本，使用适当的框架和断言。",
                tags=["自动化", "脚本", "转换"],
            ),
            QAItem(
                title="缺陷报告模板",
                category="缺陷管理",
                prompt="按照标准模板提交缺陷报告，包含复现步骤、预期结果、实际结果和环境信息。",
                tags=["缺陷", "报告", "模板"],
            ),
            QAItem(
                title="回归测试计划",
                category="测试管理",
                prompt="制定回归测试计划，确定受影响的功能模块和对应的测试范围。",
                tags=["回归", "计划", "管理"],
            ),
        ]
        self.items.extend(defaults)

    def add_item(self, item: QAItem) -> None:
        """添加新条目"""
        self.items.append(item)

    def search(self, keyword: str) -> List[QAItem]:
        """按关键词搜索条目"""
        keyword_lower = keyword.lower()
        results = []
        for item in self.items:
            # 检查标题、类别、提示词和标签
            searchable_text = " ".join([
                item.title,
                item.category,
                item.prompt,
                " ".join(item.tags),
            ]).lower()
            if keyword_lower in searchable_text:
                results.append(item)
        return results

    def get_by_category(self, category: str) -> List[QAItem]:
        """按类别获取条目"""
        return [item for item in self.items if item.category == category]

    def list_categories(self) -> List[str]:
        """列出所有类别"""
        return list(set(item.category for item in self.items))

    def export_json(self) -> str:
        """导出为 JSON 字符串"""
        data = {
            "skill": SKILL_NAME,
            "version": VERSION,
            "items": [item.to_dict() for item in self.items],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================
# 输入处理与验证
# ============================================================
def validate_input(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    验证输入数据
    返回：(是否有效, 错误码, 错误信息)
    """
    # E001: 输入为空
    if not data:
        return False, "E001", ERROR_MESSAGES["E001"]

    # 检查必填字段（根据规格，至少需要 title 和 prompt）
    required_fields = ["title", "prompt"]
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        # E002: 关键信息缺失
        return False, "E002", ERROR_MESSAGES["E002"].format(missing="、".join(missing))

    # E003: 输入格式错误（title 和 prompt 必须是字符串）
    for field in required_fields:
        if not isinstance(data[field], str):
            return False, "E003", ERROR_MESSAGES["E003"].format(example='{"title": "标题", "prompt": "提示词"}')

    return True, None, None


def process_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理输入数据，生成结构化结果
    """
    # 验证输入
    is_valid, error_code, error_message = validate_input(data)
    if not is_valid:
        return {
            "success": False,
            "error_code": error_code,
            "message": error_message,
        }

    # 提取关键信息
    title = data.get("title", "").strip()
    prompt = data.get("prompt", "").strip()
    category = data.get("category", "未分类").strip()
    tags = data.get("tags", [])

    # 处理标签
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    elif not isinstance(tags, list):
        tags = []

    # 创建条目
    item = QAItem(title=title, category=category, prompt=prompt, tags=tags)

    # 计算置信度（基于输入完整性）
    confidence = DEFAULT_CONFIDENCE
    if not category or category == "未分类":
        confidence = min(confidence, 0.85)
    if not tags:
        confidence = min(confidence, 0.90)

    item.confidence = confidence

    # 生成结果
    result = item.to_dict()
    result["success"] = True

    # 置信度标注
    if confidence >= DEFAULT_CONFIDENCE:
        result["note"] = "直接输出"
    elif confidence >= REVIEW_CONFIDENCE:
        result["note"] = "建议复核"
    else:
        result["note"] = "[需核实]"

    return result


# ============================================================
# 批量处理
# ============================================================
def batch_process(inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量处理多个输入"""
    results = []
    for data in inputs:
        result = process_input(data)
        results.append(result)
    return results


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑
    使用内置硬编码样例数据，不依赖外部资源
    """
    print("开始自检...")

    # ---- 测试 1: 库初始化 ----
    library = QAPromptLibrary()
    assert len(library.items) > 0, "库初始化失败"
    print("[PASS] 库初始化")

    # ---- 测试 2: 搜索功能 ----
    search_results = library.search("测试")
    assert len(search_results) > 0, "搜索功能失败"
    print("[PASS] 搜索功能")

    # ---- 测试 3: 类别管理 ----
    categories = library.list_categories()
    assert len(categories) > 0, "类别列表为空"
    print("[PASS] 类别管理")

    # ---- 测试 4: 输入验证（空输入） ----
    is_valid, error_code, error = validate_input({})
    assert not is_valid, "空输入应该无效"
    assert error_code == "E001", f"错误码不正确: 期望 E001, 实际 {error_code}"
    print("[PASS] 空输入验证")

    # ---- 测试 5: 输入验证（缺字段） ----
    is_valid, error_code, error = validate_input({"title": "测试"})
    assert not is_valid, "缺字段应该无效"
    assert error_code == "E002", f"错误码不正确: 期望 E002, 实际 {error_code}"
    print("[PASS] 缺字段验证")

    # ---- 测试 6: 正常处理 ----
    sample_input = {
        "title": "API 测试用例",
        "prompt": "为 REST API 创建完整的测试用例集",
        "category": "自动化测试",
        "tags": ["API", "REST", "自动化"],
    }
    result = process_input(sample_input)
    assert result["success"], "处理失败"
    assert result["confidence"] > 0.8, "置信度应较高"
    print("[PASS] 正常处理")

    # ---- 测试 7: 批量处理 ----
    batch_inputs = [
        {"title": "用例1", "prompt": "创建登录测试用例"},
        {"title": "用例2", "prompt": "创建注册测试用例", "category": "手动测试"},
    ]
    batch_results = batch_process(batch_inputs)
    assert len(batch_results) == 2, "批量处理数量错误"
    assert all(r["success"] for r in batch_results), "批量处理有失败项"
    print("[PASS] 批量处理")

    # ---- 测试 8: 导出功能 ----
    export_data = library.export_json()
    parsed = json.loads(export_data)
    assert parsed["skill"] == SKILL_NAME, "导出数据错误"
    assert len(parsed["items"]) > 0, "导出条目为空"
    print("[PASS] 导出功能")

    # ---- 测试 9: 置信度阈值 ----
    low_conf_input = {"title": "简单用例", "prompt": "测试"}
    low_conf_result = process_input(low_conf_input)
    assert low_conf_result["confidence"] <= DEFAULT_CONFIDENCE, "置信度不应超过默认值"
    print("[PASS] 置信度阈值")

    # ---- 测试 10: 错误处理 ----
    error_input = {"title": 123, "prompt": "测试"}  # 类型错误
    error_result = process_input(error_input)
    assert not error_result["success"], "类型错误应该处理失败"
    assert error_result["error_code"] == "E003", f"错误码不正确: 期望 E003, 实际 {error_result['error_code']}"
    print("[PASS] 错误处理")

    # ---- 测试 11: 边界条件 ----
    # 空字符串 title
    empty_title_input = {"title": "", "prompt": "测试"}
    empty_title_result = process_input(empty_title_input)
    assert not empty_title_result["success"], "空 title 应该无效"
    assert empty_title_result["error_code"] == "E002", f"错误码不正确: 期望 E002, 实际 {empty_title_result['error_code']}"
    print("[PASS] 空 title 边界")

    # 空字符串 prompt
    empty_prompt_input = {"title": "测试", "prompt": ""}
    empty_prompt_result = process_input(empty_prompt_input)
    assert not empty_prompt_result["success"], "空 prompt 应该无效"
    assert empty_prompt_result["error_code"] == "E002", f"错误码不正确: 期望 E002, 实际 {empty_prompt_result['error_code']}"
    print("[PASS] 空 prompt 边界")

    # 标签字符串处理
    tags_str_input = {"title": "测试", "prompt": "测试", "tags": "a, b, c"}
    tags_str_result = process_input(tags_str_input)
    assert tags_str_result["success"], "标签字符串处理失败"
    assert tags_str_result["tags"] == ["a", "b", "c"], f"标签解析错误: {tags_str_result['tags']}"
    print("[PASS] 标签字符串处理")

    # 标签非列表非字符串
    tags_invalid_input = {"title": "测试", "prompt": "测试", "tags": 123}
    tags_invalid_result = process_input(tags_invalid_input)
    assert tags_invalid_result["success"], "无效标签类型处理失败"
    assert tags_invalid_result["tags"] == [], "无效标签类型应转为空列表"
    print("[PASS] 无效标签类型处理")

    # 未分类处理
    uncategorized_input = {"title": "测试", "prompt": "测试"}
    uncategorized_result = process_input(uncategorized_input)
    assert uncategorized_result["success"], "未分类处理失败"
    assert uncategorized_result["category"] == "未分类", "默认类别错误"
    assert uncategorized_result["confidence"] == 0.85, f"未分类置信度错误: {uncategorized_result['confidence']}"
    print("[PASS] 未分类处理")

    # 无标签置信度
    no_tags_input = {"title": "测试", "prompt": "测试", "category": "手动测试"}
    no_tags_result = process_input(no_tags_input)
    assert no_tags_result["success"], "无标签处理失败"
    assert no_tags_result["confidence"] == 0.90, f"无标签置信度错误: {no_tags_result['confidence']}"
    print("[PASS] 无标签置信度")

    # 完整输入置信度
    full_input = {"title": "测试", "prompt": "测试", "category": "手动测试", "tags": ["a"]}
    full_result = process_input(full_input)
    assert full_result["success"], "完整输入处理失败"
    assert full_result["confidence"] == 0.90, f"完整输入置信度错误: {full_result['confidence']}"
    print("[PASS] 完整输入置信度")

    # ---- 测试 12: 搜索边界 ----
    # 空关键词搜索
    empty_search = library.search("")
    assert len(empty_search) == len(library.items), "空关键词应返回所有条目"
    print("[PASS] 空关键词搜索")

    # 不存在的关键词
    no_result_search = library.search("不存在的关键词xyz")
    assert len(no_result_search) == 0, "不存在的关键词应返回空结果"
    print("[PASS] 无结果搜索")

    # 大小写不敏感搜索
    case_search = library.search("TEST")
    assert len(case_search) > 0, "大小写不敏感搜索失败"
    print("[PASS] 大小写不敏感搜索")

    # ---- 测试 13: 类别过滤 ----
    manual_items = library.get_by_category("手动测试")
    assert len(manual_items) > 0, "按类别获取失败"
    assert all(item.category == "手动测试" for item in manual_items), "类别过滤错误"
    print("[PASS] 类别过滤")

    # 不存在的类别
    no_category_items = library.get_by_category("不存在的类别")
    assert len(no_category_items) == 0, "不存在的类别应返回空结果"
    print("[PASS] 不存在类别")

    # ---- 测试 14: 添加条目 ----
    new_item = QAItem("新条目", "新类别", "新提示词", ["新标签"])
    library.add_item(new_item)
    assert len(library.items) == 5, f"添加条目失败，期望 5 个，实际 {len(library.items)}"
    assert library.search("新条目")[0].title == "新条目", "添加后搜索失败"
    print("[PASS] 添加条目")

    # ---- 测试 15: 导出完整性 ----
    export_data = library.export_json()
    parsed = json.loads(export_data)
    assert parsed["version"] == VERSION, "版本号错误"
    assert len(parsed["items"]) == 5, f"导出条目数量错误，期望 5，实际 {len(parsed['items'])}"
    assert all("title" in item and "prompt" in item for item in parsed["items"]), "导出条目缺少字段"
    print("[PASS] 导出完整性")

    print("\n所有自检通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="QA Prompt Library - 技能实现",
        epilog="示例：python main.py --process '{\"title\": \"测试\", \"prompt\": \"创建测试用例\"}'"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）",
    )
    parser.add_argument(
        "--process",
        type=str,
        metavar="JSON",
        help="处理单个输入（JSON 字符串）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        metavar="JSON",
        help="批量处理输入（JSON 数组）",
    )
    parser.add_argument(
        "--search",
        type=str,
        metavar="KEYWORD",
        help="搜索库中的条目",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="导出整个库为 JSON",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} v{VERSION}",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"[FAIL] 自检失败: {e}")
            sys.exit(1)

    # 处理单个输入
    if args.process:
        try:
            data = json.loads(args.process)
            result = process_input(data)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print("错误：JSON 解析失败", file=sys.stderr)
            sys.exit(1)

    # 批量处理
    if args.batch:
        try:
            inputs = json.loads(args.batch)
            if not isinstance(inputs, list):
                print("错误：批量输入必须是数组", file=sys.stderr)
                sys.exit(1)
            results = batch_process(inputs)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print("错误：JSON 解析失败", file=sys.stderr)
            sys.exit(1)

    # 搜索
    if args.search:
        library = QAPromptLibrary()
        results = library.search(args.search)
        if results:
            for item in results:
                print(f"- [{item.category}] {item.title}")
        else:
            print("未找到匹配条目")

    # 导出
    if args.export:
        library = QAPromptLibrary()
        print(library.export_json())

    # 无参数时显示帮助
    if not any([args.selftest, args.process, args.batch, args.search, args.export]):
        parser.print_help()


if __name__ == "__main__":
    main()
