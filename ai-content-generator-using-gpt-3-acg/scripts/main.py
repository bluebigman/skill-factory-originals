#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件撰写技能 - 独立实现脚本

本脚本依据功能规格独立实现，不复制任何既有代码。
提供邮件撰写相关的核心逻辑：信息收集引导、内容处理、置信度评估、错误处理。
"""

import argparse
import sys
import re
from typing import Dict, List, Optional, Tuple, Any


# ============================================================
# 常量定义
# ============================================================

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}

# 触发词表
TRIGGER_WORDS = [
    "邮件撰写",
    "ai content generator using gpt 3 acg",
    "帮我处理一下这个",
    "把这个转成另一种格式",
    "批量弄一下这些",
]

# 能力边界声明
CAPABILITY_NOTES = {
    "do": [
        "将用户提供的数据/文件/URL转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "not_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 默认输出模板字段
DEFAULT_FIELDS = ["标题", "正文", "关键信息", "置信度"]


# ============================================================
# 核心逻辑类
# ============================================================

class ContentProcessor:
    """内容处理器 - 负责解析输入、识别关键信息、生成结构化输出"""

    def __init__(self) -> None:
        """初始化处理器"""
        self.fields = DEFAULT_FIELDS
        self.min_confidence_direct = 0.90  # 直接输出阈值
        self.min_confidence_review = 0.85  # 建议复核阈值

    def validate_input(self, raw_input: str) -> Tuple[bool, Optional[str]]:
        """
        验证输入是否有效

        参数:
            raw_input: 原始输入字符串

        返回:
            (是否有效, 错误码或None)
        """
        if not raw_input or not raw_input.strip():
            return False, "E001"
        return True, None

    def extract_key_info(self, raw_input: str) -> Dict[str, Any]:
        """
        从输入中提取关键信息

        参数:
            raw_input: 原始输入字符串

        返回:
            包含关键信息的字典
        """
        info = {
            "content": raw_input.strip(),
            "length": len(raw_input.strip()),
            "has_url": self._detect_url(raw_input),
            "has_email": self._detect_email(raw_input),
            "has_date": self._detect_date(raw_input),
            "keywords": self._extract_keywords(raw_input),
        }
        return info

    def _detect_url(self, text: str) -> bool:
        """检测是否包含URL"""
        url_pattern = r'https?://[^\s]+'
        return bool(re.search(url_pattern, text))

    def _detect_email(self, text: str) -> bool:
        """检测是否包含邮箱地址"""
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        return bool(re.search(email_pattern, text))

    def _detect_date(self, text: str) -> bool:
        """检测是否包含日期"""
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',  # 2024-01-01 或 2024年1月1日
            r'\d{1,2}[-/月]\d{1,2}日?',  # 01-01 或 1月1日
        ]
        return any(re.search(pattern, text) for pattern in date_patterns)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单分词）"""
        # 简单关键词提取：按空格分割，过滤短词和常见停用词
        stop_words = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "她", "它",
                      "the", "a", "an", "and", "or", "but", "is", "are", "was", "were"}
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]
        return list(set(keywords))[:10]  # 最多返回10个关键词

    def calculate_confidence(self, key_info: Dict[str, Any]) -> float:
        """
        计算置信度

        参数:
            key_info: 关键信息字典

        返回:
            置信度分数 (0-1)
        """
        # 基准置信度
        confidence = 0.70

        # 根据关键信息丰富度调整
        if key_info["content"]:
            confidence += 0.05

        if key_info["has_url"]:
            confidence += 0.05

        if key_info["has_email"]:
            confidence += 0.05

        if key_info["has_date"]:
            confidence += 0.05

        # 关键词数量影响
        keyword_count = len(key_info["keywords"])
        if keyword_count >= 5:
            confidence += 0.05
        elif keyword_count >= 3:
            confidence += 0.03
        elif keyword_count >= 1:
            confidence += 0.01

        # 内容长度影响
        content_length = key_info["length"]
        if content_length > 200:
            confidence += 0.05
        elif content_length > 100:
            confidence += 0.03
        elif content_length > 50:
            confidence += 0.01

        # 限制在合理范围内
        return max(0.1, min(0.99, confidence))

    def generate_output(self, raw_input: str) -> Dict[str, Any]:
        """
        生成结构化输出

        参数:
            raw_input: 原始输入

        返回:
            结构化输出字典
        """
        # 验证输入
        valid, error_code = self.validate_input(raw_input)
        if not valid:
            return {
                "success": False,
                "error_code": error_code,
                "error_message": ERROR_CODES[error_code],
            }

        # 提取关键信息
        key_info = self.extract_key_info(raw_input)

        # 计算置信度
        confidence = self.calculate_confidence(key_info)

        # 生成输出
        output = {
            "success": True,
            "title": self._generate_title(key_info),
            "content": self._generate_content(key_info),
            "key_info": key_info,
            "confidence": confidence,
            "confidence_label": self._get_confidence_label(confidence),
        }

        return output

    def _generate_title(self, key_info: Dict[str, Any]) -> str:
        """生成标题"""
        keywords = key_info["keywords"]
        if keywords:
            return f"关于{'、'.join(keywords[:3])}的邮件"
        return "待处理邮件"

    def _generate_content(self, key_info: Dict[str, Any]) -> str:
        """生成正文内容"""
        parts = []

        # 开头问候
        parts.append("您好，")

        # 正文主体
        content = key_info["content"]
        if len(content) > 100:
            parts.append(content[:100] + "...")
        else:
            parts.append(content)

        # 结尾
        parts.append("此致")

        return "\n\n".join(parts)

    def _get_confidence_label(self, confidence: float) -> str:
        """获取置信度标签"""
        if confidence >= self.min_confidence_direct:
            return "直接输出"
        elif confidence >= self.min_confidence_review:
            return "建议复核"
        else:
            return "[需核实]"

    def process_batch(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理输入

        参数:
            inputs: 输入列表

        返回:
            结果列表
        """
        return [self.generate_output(item) for item in inputs]


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    运行自检测试

    使用内置硬编码样例数据，不依赖外部文件、网络或特定工作目录。

    返回:
        测试是否通过
    """
    print("=" * 60)
    print("开始自检 (Self-Test)")
    print("=" * 60)

    processor = ContentProcessor()
    all_passed = True

    # 测试用例 1: 正常输入
    print("\n[测试 1] 正常输入处理")
    test_input_1 = "请帮我撰写一封关于项目进度的邮件，收件人是客户张三，日期是2024年3月15日，主要内容是汇报本周完成的工作和下周计划。"
    result_1 = processor.generate_output(test_input_1)
    assert result_1["success"], f"测试1失败: 处理失败 {result_1.get('error_message')}"
    assert result_1["confidence"] > 0.7, f"测试1失败: 置信度过低 {result_1['confidence']}"
    assert result_1["title"], "测试1失败: 标题为空"
    assert result_1["content"], "测试1失败: 内容为空"
    print(f"  ✓ 通过 (置信度: {result_1['confidence']:.2f}, 标签: {result_1['confidence_label']})")

    # 测试用例 2: 空输入处理
    print("\n[测试 2] 空输入处理")
    test_input_2 = ""
    result_2 = processor.generate_output(test_input_2)
    assert not result_2["success"], "测试2失败: 空输入应该失败"
    assert result_2["error_code"] == "E001", f"测试2失败: 错误码应为E001, 实际为{result_2['error_code']}"
    print(f"  ✓ 通过 (错误码: {result_2['error_code']})")

    # 测试用例 3: 批量处理
    print("\n[测试 3] 批量处理")
    test_inputs_3 = [
        "请处理这个文档，包含合同信息，签署日期2024年1月1日，金额100万。",
        "这是另一个请求，关于税务申报，截止日期3月31日。",
        "简单请求",
    ]
    results_3 = processor.process_batch(test_inputs_3)
    assert len(results_3) == 3, f"测试3失败: 应返回3个结果, 实际{len(results_3)}"
    assert results_3[0]["success"], "测试3失败: 第一个输入处理失败"
    assert results_3[1]["success"], "测试3失败: 第二个输入处理失败"
    print(f"  ✓ 通过 ({len(results_3)} 个结果)")

    # 测试用例 4: 关键信息提取
    print("\n[测试 4] 关键信息提取")
    test_input_4 = "请处理 https://example.com/doc/123 和 test@email.com 的相关内容，日期2024年6月1日。"
    key_info_4 = processor.extract_key_info(test_input_4)
    assert key_info_4["has_url"], "测试4失败: 应检测到URL"
    assert key_info_4["has_email"], "测试4失败: 应检测到邮箱"
    assert key_info_4["has_date"], "测试4失败: 应检测到日期"
    print(f"  ✓ 通过 (URL: {key_info_4['has_url']}, 邮箱: {key_info_4['has_email']}, 日期: {key_info_4['has_date']})")

    # 测试用例 5: 置信度评估
    print("\n[测试 5] 置信度评估")
    test_input_5a = "简单输入"
    test_input_5b = "这是一段较长的输入内容，包含多个关键词：项目、进度、客户、合同、日期、金额、方案、执行、验收、交付。同时包含URL https://example.com 和邮箱 test@email.com，日期为2024年12月31日。"
    conf_5a = processor.calculate_confidence(processor.extract_key_info(test_input_5a))
    conf_5b = processor.calculate_confidence(processor.extract_key_info(test_input_5b))
    assert 0 < conf_5a < 1, f"测试5失败: 置信度应在0-1之间, 实际{conf_5a}"
    assert 0 < conf_5b < 1, f"测试5失败: 置信度应在0-1之间, 实际{conf_5b}"
    assert conf_5b > conf_5a, f"测试5失败: 信息丰富输入置信度应更高 ({conf_5a} vs {conf_5b})"
    print(f"  ✓ 通过 (简单: {conf_5a:.2f}, 丰富: {conf_5b:.2f})")

    # 测试用例 6: 错误处理
    print("\n[测试 6] 错误处理")
    error_test_cases = [
        ("", "E001"),  # 空输入
    ]
    for test_input, expected_error in error_test_cases:
        result = processor.generate_output(test_input)
        assert result["error_code"] == expected_error, \
            f"测试6失败: 期望{expected_error}, 实际{result['error_code']}"
    print(f"  ✓ 通过 ({len(error_test_cases)} 个错误场景)")

    # 测试用例 7: 触发词识别
    print("\n[测试 7] 触发词识别")
    trigger_test_cases = [
        "邮件撰写",  # 直接触发词
        "帮我处理一下这个",  # 大白话触发
        "ai content generator using gpt 3 acg",  # 英文触发词
    ]
    for trigger in trigger_test_cases:
        assert trigger in TRIGGER_WORDS, f"测试7失败: '{trigger}' 应在触发词表中"
    print(f"  ✓ 通过 ({len(trigger_test_cases)} 个触发词)")

    # 测试用例 8: 能力边界
    print("\n[测试 8] 能力边界")
    assert len(CAPABILITY_NOTES["do"]) == 5, "测试8失败: 应有5项能做声明"
    assert len(CAPABILITY_NOTES["not_do"]) == 3, "测试8失败: 应有3项不做声明"
    print(f"  ✓ 通过 (能做: {len(CAPABILITY_NOTES['do'])}项, 不做: {len(CAPABILITY_NOTES['not_do'])}项)")

    # 测试用例 9: 输出格式
    print("\n[测试 9] 输出格式")
    test_input_9 = "请生成一封商务邮件，包含合同、报价、时间安排等信息。"
    result_9 = processor.generate_output(test_input_9)
    required_fields = ["title", "content", "confidence", "success"]
    for field in required_fields:
        assert field in result_9, f"测试9失败: 输出缺少字段 '{field}'"
    print(f"  ✓ 通过 (字段: {', '.join(required_fields)})")

    # 测试用例 10: 批量输入错误处理
    print("\n[测试 10] 批量输入错误处理")
    mixed_inputs = ["有效输入", "", "另一个有效输入"]
    mixed_results = processor.process_batch(mixed_inputs)
    assert mixed_results[0]["success"], "测试10失败: 第一个输入应成功"
    assert not mixed_results[1]["success"], "测试10失败: 空输入应失败"
    assert mixed_results[2]["success"], "测试10失败: 第三个输入应成功"
    print(f"  ✓ 通过 (成功: {sum(1 for r in mixed_results if r['success'])}/{len(mixed_results)})")

    print("\n" + "=" * 60)
    if all_passed:
        print("全部自检通过 ✓")
    else:
        print("存在自检失败 ✗")
    print("=" * 60)
    return all_passed


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """
    主入口函数

    返回:
        退出码 (0: 成功, 非0: 失败)
    """
    parser = argparse.ArgumentParser(
        description="邮件撰写技能 - 内容处理工具",
        epilog="示例: python main.py --input '请帮我写一封邮件'"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的输入内容"
    )

    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个输入"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检测试"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="邮件撰写技能 v1.0.0"
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 创建处理器
    processor = ContentProcessor()

    # 批量处理
    if args.batch:
        results = processor.process_batch(args.batch)
        for i, result in enumerate(results, 1):
            print(f"\n--- 结果 {i} ---")
            if result["success"]:
                print(f"标题: {result['title']}")
                print(f"内容: {result['content']}")
                print(f"置信度: {result['confidence']:.2f} ({result['confidence_label']})")
            else:
                print(f"错误: {result['error_message']}")
        return 0

    # 单个处理
    if args.input:
        result = processor.generate_output(args.input)
        if result["success"]:
            print(f"标题: {result['title']}")
            print(f"内容: {result['content']}")
            print(f"置信度: {result['confidence']:.2f} ({result['confidence_label']})")
            return 0
        else:
            print(f"错误: {result['error_message']}")
            return 1

    # 无输入参数，显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
