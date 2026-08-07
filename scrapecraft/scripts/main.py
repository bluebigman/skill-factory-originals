#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapecraft - 爬虫采集技能核心逻辑（独立实现）
================================================
本脚本依据功能规格独立实现，不复制任何既有代码。
提供核心的数据结构化处理能力，支持命令行调用与自检。
"""

import sys
import json
import argparse
from typing import Dict, List, Any, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 具体缺失项在返回中补充
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 置信度阈值
CONFIDENCE_HIGH = 90        # 高置信度阈值（>=90 直接输出）
CONFIDENCE_MEDIUM = 85      # 中置信度阈值（85-89 建议复核）

# 默认输出字段模板（根据规格中的"关键字段"设计）
DEFAULT_FIELDS = ["title", "content", "url", "timestamp"]


# ============================================================
# 核心功能类
# ============================================================
class ScrapeCraftCore:
    """爬虫采集核心处理类，负责输入解析、结构化、置信度评估。"""

    def __init__(self) -> None:
        """初始化处理器。"""
        self.error_code: Optional[str] = None

    # ---------- 输入验证 ----------
    def validate_input(self, raw_input: Any) -> Tuple[bool, Optional[str]]:
        """
        验证输入有效性。
        返回: (是否有效, 错误码或None)
        """
        # E001: 输入为空
        if raw_input is None or raw_input == "":
            return False, "E001"

        # E003: 输入格式错误（必须是字符串或可序列化为字符串的对象）
        if not isinstance(raw_input, (str, dict, list, int, float)):
            return False, "E003"

        return True, None

    # ---------- 信息提取 ----------
    def extract_key_info(self, raw_input: Any) -> Dict[str, Any]:
        """
        从输入中提取关键信息并结构化。
        支持字符串、字典、列表等常见输入格式。
        """
        result: Dict[str, Any] = {}

        # 处理字符串输入
        if isinstance(raw_input, str):
            # 尝试解析JSON
            try:
                parsed = json.loads(raw_input)
                if isinstance(parsed, dict):
                    result = self._extract_from_dict(parsed)
                elif isinstance(parsed, list):
                    result = self._extract_from_list(parsed)
                else:
                    result = {"content": raw_input}
            except json.JSONDecodeError:
                # 非JSON字符串，作为纯文本处理
                result = {"content": raw_input.strip()}

        # 处理字典输入
        elif isinstance(raw_input, dict):
            result = self._extract_from_dict(raw_input)

        # 处理列表输入
        elif isinstance(raw_input, list):
            result = self._extract_from_list(raw_input)

        # 处理数值输入
        elif isinstance(raw_input, (int, float)):
            result = {"content": str(raw_input)}

        return result

    def _extract_from_dict(self, data: Dict) -> Dict[str, Any]:
        """从字典中提取关键字段。"""
        extracted: Dict[str, Any] = {}

        # 常见字段映射（不依赖特定键名，灵活匹配）
        field_mappings = {
            "title": ["title", "标题", "name", "subject"],
            "content": ["content", "正文", "text", "body", "描述"],
            "url": ["url", "链接", "link", "href"],
            "timestamp": ["timestamp", "时间", "date", "created_at", "time"],
        }

        for standard_key, aliases in field_mappings.items():
            for alias in aliases:
                if alias in data and data[alias] is not None:
                    extracted[standard_key] = data[alias]
                    break

        # 保留所有原始字段作为补充
        raw_keys = [k for k in data.keys() if k not in
                    [v for vals in field_mappings.values() for v in vals]]
        for key in raw_keys:
            extracted[f"raw_{key}"] = data[key]

        return extracted

    def _extract_from_list(self, data: List) -> Dict[str, Any]:
        """从列表中提取信息（批量处理场景）。"""
        if not data:
            return {"content": ""}

        # 如果列表元素是字典，尝试提取公共字段
        if all(isinstance(item, dict) for item in data):
            # 合并所有字典的键
            all_keys = set()
            for item in data:
                all_keys.update(item.keys())

            # 提取公共字段
            common_keys = [k for k in all_keys
                          if all(k in item for item in data)]
            if common_keys:
                extracted = {k: [item[k] for item in data]
                            for k in common_keys}
                extracted["count"] = len(data)
                return extracted

        # 简单列表，直接转为字符串
        return {"content": json.dumps(data, ensure_ascii=False)}

    # ---------- 置信度评估 ----------
    def evaluate_confidence(self, extracted: Dict[str, Any]) -> int:
        """
        基于提取结果的完整性评估置信度（0-100）。
        评分规则：
        - 基础分 50
        - 每个关键字段（title/content）存在 +15
        - 辅助字段（url/timestamp）存在 +10
        - 内容长度超过50字符 +5
        """
        score = 50

        # 关键字段检查
        if extracted.get("title"):
            score += 15
        if extracted.get("content"):
            score += 15

        # 辅助字段检查
        if extracted.get("url"):
            score += 10
        if extracted.get("timestamp"):
            score += 10

        # 内容充实度检查
        content = str(extracted.get("content", ""))
        if len(content) > 50:
            score += 5

        # 确保不超过100
        return min(score, 100)

    def format_output(self, extracted: Dict[str, Any],
                      confidence: int) -> Dict[str, Any]:
        """
        根据置信度格式化输出结果。
        - >=90%: 直接输出
        - 85-89%: 标注"建议复核"
        - <85%: 标注"[需核实]"
        """
        output = {
            "data": extracted,
            "confidence": confidence,
            "status": "success",
        }

        if confidence >= CONFIDENCE_HIGH:
            output["level"] = "直接输出"
        elif confidence >= CONFIDENCE_MEDIUM:
            output["level"] = "建议复核"
            output["warning"] = "结果部分字段可能不完整，请复核关键信息"
        else:
            output["level"] = "需核实"
            output["warning"] = "[需核实] 结果置信度较低，请人工确认以下不确定点："
            # 找出缺失的字段
            missing = [f for f in DEFAULT_FIELDS if not extracted.get(f)]
            if missing:
                output["uncertain_fields"] = missing

        return output

    # ---------- 主处理流程 ----------
    def process(self, raw_input: Any) -> Dict[str, Any]:
        """
        执行标准处理流程：
        1. 输入验证
        2. 信息提取
        3. 置信度评估
        4. 结果格式化
        """
        # Step 1: 输入验证
        valid, error_code = self.validate_input(raw_input)
        if not valid:
            self.error_code = error_code
            return {
                "status": "error",
                "error_code": error_code,
                "message": ERROR_MESSAGES.get(error_code, "未知错误"),
            }

        # Step 2: 信息提取
        extracted = self.extract_key_info(raw_input)

        # Step 3: 置信度评估
        confidence = self.evaluate_confidence(extracted)

        # Step 4: 结果格式化
        return self.format_output(extracted, confidence)

    # ---------- 批量处理 ----------
    def batch_process(self, inputs: List[Any]) -> List[Dict[str, Any]]:
        """批量处理多个输入。"""
        return [self.process(item) for item in inputs]


# ============================================================
# 自检模块（离线硬编码测试数据）
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检逻辑。
    使用硬编码样例数据，不依赖外部文件或网络。
    使用宽松断言（区间/大小比较），确保稳健性。
    """
    print("=" * 60)
    print("scrapecraft 自检开始")
    print("=" * 60)

    core = ScrapeCraftCore()
    all_passed = True

    # ---------- 测试用例 1: 完整字典输入 ----------
    print("\n[测试1] 完整字典输入")
    sample1 = {
        "title": "爬虫技术实践指南",
        "content": "这是一篇关于网络爬虫技术的详细教程，涵盖基础概念、常用工具和实践案例。"
                   "内容较长，用于测试置信度评估功能。",
        "url": "https://example.com/crawler-guide",
        "timestamp": "2026-01-15T10:30:00",
    }
    result1 = core.process(sample1)

    # 断言：状态成功，置信度应较高（宽松判断）
    assert result1["status"] == "success", "测试1失败：状态应为success"
    assert result1["confidence"] > 80, "测试1失败：置信度应较高"
    assert result1["data"].get("title") == sample1["title"], \
        "测试1失败：标题提取不正确"
    print(f"  ✓ 通过 (置信度: {result1['confidence']}%)")

    # ---------- 测试用例 2: 空输入 ----------
    print("\n[测试2] 空输入处理")
    result2 = core.process("")
    assert result2["status"] == "error", "测试2失败：空输入应报错"
    assert result2["error_code"] == "E001", "测试2失败：错误码应为E001"
    print("  ✓ 通过 (错误码: E001)")

    # ---------- 测试用例 3: JSON字符串输入 ----------
    print("\n[测试3] JSON字符串输入")
    sample3 = json.dumps({
        "name": "测试项目",
        "description": "这是一个自检用的测试数据",
    })
    result3 = core.process(sample3)
    assert result3["status"] == "success", "测试3失败：状态应为success"
    assert result3["confidence"] > 60, "测试3失败：置信度应中等"
    print(f"  ✓ 通过 (置信度: {result3['confidence']}%)")

    # ---------- 测试用例 4: 纯文本输入（低置信度场景） ----------
    print("\n[测试4] 纯文本输入")
    result4 = core.process("简单文本")
    assert result4["status"] == "success", "测试4失败：状态应为success"
    # 纯文本置信度应较低（宽松判断 < 85）
    assert result4["confidence"] < 85, "测试4失败：纯文本置信度应较低"
    print(f"  ✓ 通过 (置信度: {result4['confidence']}%)")

    # ---------- 测试用例 5: 批量处理 ----------
    print("\n[测试5] 批量处理")
    batch_inputs = [
        {"title": "项目A", "content": "内容A" * 20},
        {"title": "项目B", "content": "内容B" * 20},
        "简单文本",
    ]
    batch_results = core.batch_process(batch_inputs)
    assert len(batch_results) == 3, "测试5失败：应返回3个结果"
    assert all(r["status"] == "success" for r in batch_results), \
        "测试5失败：所有结果应为success"
    print(f"  ✓ 通过 ({len(batch_results)}个结果)")

    # ---------- 测试用例 6: 错误输入类型 ----------
    print("\n[测试6] 错误输入类型")
    # 使用不支持的类型（如None）
    result6 = core.process(None)
    assert result6["status"] == "error", "测试6失败：None应报错"
    assert result6["error_code"] in ("E001", "E003"), \
        "测试6失败：错误码应为E001或E003"
    print(f"  ✓ 通过 (错误码: {result6['error_code']})")

    # ---------- 测试用例 7: 置信度分级验证 ----------
    print("\n[测试7] 置信度分级")
    # 构造不同完整度的输入
    high_conf = core.process({
        "title": "完整标题",
        "content": "这是一段足够长的内容，用于测试高置信度场景。"
                  "包含多个句子来增加长度。",
        "url": "https://example.com",
        "timestamp": "2026-01-01",
    })
    low_conf = core.process("短文本")

    # 宽松断言：高置信度应明显高于低置信度
    assert high_conf["confidence"] > low_conf["confidence"], \
        "测试7失败：高置信度应大于低置信度"
    print(f"  ✓ 通过 (高: {high_conf['confidence']}%, "
          f"低: {low_conf['confidence']}%)")

    # ---------- 测试用例 8: 列表输入 ----------
    print("\n[测试8] 列表输入")
    list_input = [
        {"name": "条目1", "value": "值1"},
        {"name": "条目2", "value": "值2"},
    ]
    result8 = core.process(list_input)
    assert result8["status"] == "success", "测试8失败：状态应为success"
    assert result8["data"].get("count") == 2, "测试8失败：应提取到2条记录"
    print("  ✓ 通过 (提取到2条记录)")

    # ---------- 汇总结果 ----------
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 全部自检通过！")
    else:
        print("❌ 存在失败用例")
    print("=" * 60)
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="scrapecraft - 爬虫采集技能核心逻辑",
        epilog="示例: python main.py --input '{\"title\": \"测试\"}'"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容（字符串或JSON格式）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（离线，不依赖外部环境）"
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：传入JSON数组字符串"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 创建核心处理器
    core = ScrapeCraftCore()

    # 批量处理模式
    if args.batch:
        try:
            batch_data = json.loads(args.batch)
            if not isinstance(batch_data, list):
                print(json.dumps({
                    "status": "error",
                    "error_code": "E003",
                    "message": "批量输入必须是JSON数组",
                }, ensure_ascii=False))
                return 1
            results = core.batch_process(batch_data)
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError:
            print(json.dumps({
                "status": "error",
                "error_code": "E003",
                "message": "批量输入JSON解析失败",
            }, ensure_ascii=False))
            return 1

    # 单条处理模式
    if args.input:
        # 尝试解析JSON
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            input_data = args.input

        result = core.process(input_data)

        if args.output == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 文本输出格式
            if result["status"] == "error":
                print(f"[错误] {result['message']}")
            else:
                print(f"状态: {result['status']}")
                print(f"置信度: {result['confidence']}%")
                print(f"级别: {result['level']}")
                for key, value in result["data"].items():
                    print(f"  {key}: {value}")
                if "warning" in result:
                    print(f"警告: {result['warning']}")
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
