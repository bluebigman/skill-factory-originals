#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
技能: qa-prompt-library (未命名工具)
版本: 1.1.0
说明: 独立实现，仅依据功能规格编写（clean-room）。
     提供标准流程处理、错误码体系、置信度标注与离线自检。
     修复：增强停用词过滤逻辑，确保无有效信息时正确触发 E005。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 常量定义（错误码与话术）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 具体缺失项由调用方拼接
    "E003": "输入格式不符合要求，示例：{\"content\": \"...\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议：简化输入或使用其他专用工具",
    "E005": "结果无法确定，建议：补充更多上下文或人工复核",
}

# 扩展停用词表（中英文）
STOPWORDS = {
    # 中文停用词
    "的", "了", "和", "是", "在", "我", "有", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
    "他", "她", "它", "们", "与", "及", "或", "等", "被", "把",
    "让", "向", "从", "为", "对", "于", "之", "其", "此", "该",
    "每", "各", "某", "什么", "怎么", "如何", "为什么", "哪些",
    "个", "只", "但", "而", "且", "并", "或者", "还是", "因为",
    "所以", "如果", "虽然", "但是", "即使", "无论", "只要",
    # 英文停用词
    "the", "a", "an", "is", "are", "was", "were", "to", "of",
    "in", "for", "on", "with", "as", "by", "at", "from",
    "and", "or", "but", "not", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "must", "this", "that",
    "these", "those", "it", "its", "he", "she", "they", "we",
    "you", "them", "his", "her", "their", "our", "your",
    # 纯标点和常见无意义字符
    ".", ",", "!", "?", ";", ":", "-", "_", "(", ")", "[", "]",
    "{", "}", "<", ">", "/", "\\", "|", "@", "#", "$", "%", "^",
    "&", "*", "+", "=", "~", "`", "'", "\"",
}


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class PromptLibraryProcessor:
    """QA Prompt Library 核心处理器（clean-room 实现）。"""

    def __init__(self) -> None:
        """初始化处理器，设置默认参数。"""
        self._default_format: str = "json"

    # -- 主入口 ------------------------------------------------------------
    def process(
        self,
        content: Optional[str],
        output_format: Optional[str] = None,
        completeness: str = "auto",
    ) -> Dict[str, Any]:
        """
        执行标准流程：
          1. 校验输入（E001/E003）
          2. 解析关键信息
          3. 生成结构化结果并标注置信度
          4. 返回结果字典（含元信息）

        参数:
            content: 用户提供的原始内容（字符串）
            output_format: 输出格式（json/text），默认 json
            completeness: 完整度（skeleton/detail/auto）

        返回:
            结果字典，包含: status, data, confidence, warnings, errors
        """
        # Step 1: 输入校验
        if content is None or content.strip() == "":
            return self._make_error("E001", ERROR_MESSAGES["E001"])

        if output_format is None:
            output_format = self._default_format

        if output_format not in ("json", "text"):
            return self._make_error(
                "E003", ERROR_MESSAGES["E003"] + f" 当前格式: {output_format}"
            )

        # Step 2: 解析内容（仅提取关键信息，不做超出输入的分析）
        parsed = self._parse_content(content)
        
        # 检查是否有有效信息（关键词或摘要）
        if not parsed["keywords"] or not parsed["summary"]:
            # 无有效信息 -> 置信度低
            return self._make_error(
                "E005",
                ERROR_MESSAGES["E005"] + " 未能从输入中提取有效信息。",
            )

        # Step 3: 生成结果
        result_data = self._build_output(parsed, completeness)

        # 计算置信度（基于信息完整度）
        confidence = self._calc_confidence(parsed, completeness)

        # 组装返回
        result: Dict[str, Any] = {
            "status": "ok",
            "data": result_data,
            "confidence": confidence,
            "warnings": [],
            "errors": [],
        }

        # 置信度标注
        if confidence < 85:
            result["warnings"].append("结果置信度较低，请人工复核关键内容。")
            result["data"]["needs_review"] = True
        elif confidence < 90:
            result["warnings"].append("建议复核部分内容。")
            result["data"]["needs_review"] = True
        else:
            result["data"]["needs_review"] = False

        return result

    # -- 内部方法 ----------------------------------------------------------
    @staticmethod
    def _parse_content(content: str) -> Dict[str, Any]:
        """
        解析输入内容，提取关键信息。
        规则：
          - 按常见分隔符拆分（逗号、分号、换行、句号）
          - 提取高频词作为关键词（简单词频统计）
          - 生成摘要（取前 N 个字符）
        注意：不执行任何超出输入范围的分析。
        """
        text = content.strip()

        # 按常见分隔符拆分
        parts = re.split(r"[,，;；。\n\t]+", text)
        parts = [p.strip() for p in parts if p.strip()]

        # 简单词频统计（过滤停用词和纯标点）
        word_count: Dict[str, int] = {}
        for part in parts:
            # 将每个部分再按空格拆分
            words = part.split()
            for w in words:
                # 清理标点
                clean_w = re.sub(r"[^\w\u4e00-\u9fff]", "", w)
                # 转为小写（英文）
                lower_w = clean_w.lower()
                # 过滤：非空、非纯数字、非停用词
                if (clean_w and 
                    lower_w not in STOPWORDS and 
                    not clean_w.isdigit() and
                    len(clean_w) >= 2):  # 至少2个字符才有意义
                    word_count[clean_w] = word_count.get(clean_w, 0) + 1

        # 取出现次数最多的前 5 个词作为关键词
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        keywords = [w for w, _ in sorted_words[:5]]

        # 摘要：取前 100 字符（若内容过长）
        # 需要过滤掉只有停用词的情况
        meaningful_text = " ".join(keywords) if keywords else ""
        if meaningful_text:
            summary = text[:100] + ("..." if len(text) > 100 else "")
        else:
            summary = ""  # 没有有效内容时摘要为空

        return {
            "summary": summary,
            "keywords": keywords,
            "raw_parts": parts,
        }

    @staticmethod
    def _build_output(parsed: Dict[str, Any], completeness: str) -> Dict[str, Any]:
        """根据解析结果和完整度生成输出数据。"""
        data: Dict[str, Any] = {
            "summary": parsed["summary"],
            "keywords": parsed["keywords"],
            "field_count": len(parsed["keywords"]) + 1,  # summary + keywords
        }

        # 按完整度调整（骨架 vs 详细）
        if completeness == "skeleton":
            # 骨架结果：只保留摘要和关键词
            data["detail_level"] = "skeleton"
        elif completeness == "detail":
            # 详细结果：增加更多字段（但仍是基于输入）
            data["detail_level"] = "detail"
            data["segment_count"] = len(parsed["raw_parts"])
        else:
            # auto 模式：根据内容长度决定
            data["detail_level"] = "detail" if len(parsed["summary"]) > 50 else "skeleton"

        return data

    @staticmethod
    def _calc_confidence(parsed: Dict[str, Any], completeness: str) -> float:
        """
        计算置信度（0-100）。
        规则：
          - 有关键词 + 有摘要：基础 85 分
          - 关键词数量多：加分
          - 内容长度长：加分
          - 骨架模式：减分
        """
        base = 70.0
        if parsed["keywords"]:
            base += 15.0  # 有关键词
        if len(parsed["summary"]) > 10:
            base += 5.0  # 摘要长度足够

        # 关键词数量加成（最多 +5）
        base += min(len(parsed["keywords"]) * 1.0, 5.0)

        # 完整度调整
        if completeness == "skeleton":
            base -= 5.0

        # 限制在 0-100 之间
        return max(0.0, min(100.0, base))

    @staticmethod
    def _make_error(code: str, message: str) -> Dict[str, Any]:
        """构造错误返回。"""
        return {
            "status": "error",
            "code": code,
            "message": message,
            "data": None,
            "confidence": 0.0,
            "warnings": [],
            "errors": [{"code": code, "message": message}],
        }


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例，不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保稳健匹配。
    """
    print("[selftest] 开始自检 (qa-prompt-library) ...")

    processor = PromptLibraryProcessor()

    # 测试用例 1: 正常输入
    print("[selftest] 用例1: 正常输入")
    result1 = processor.process(
        "测试用例：验证登录功能，包括正确密码、错误密码、空密码，以及锁定策略。",
        output_format="json",
        completeness="detail",
    )
    assert result1["status"] == "ok", f"用例1失败: 状态不是 ok, 实际: {result1['status']}"
    assert result1["confidence"] >= 60.0, f"用例1失败: 置信度过低 {result1['confidence']}"
    assert isinstance(result1["data"]["keywords"], list), "用例1失败: keywords 不是列表"
    assert len(result1["data"]["keywords"]) > 0, "用例1失败: 关键词为空"
    assert result1["data"]["summary"], "用例1失败: 摘要为空"
    print(f"  [通过] 置信度={result1['confidence']:.1f}, 关键词数={len(result1['data']['keywords'])}")

    # 测试用例 2: 空输入 -> E001
    print("[selftest] 用例2: 空输入 (期望 E001)")
    result2 = processor.process("   ", output_format="json")
    assert result2["status"] == "error", "用例2失败: 空输入应返回 error"
    assert result2["code"] == "E001", f"用例2失败: 错误码应为 E001, 实际: {result2['code']}"
    print("  [通过] 正确触发 E001")

    # 测试用例 3: 格式错误 -> E003
    print("[selftest] 用例3: 非法格式 (期望 E003)")
    result3 = processor.process("有效内容", output_format="xml")
    assert result3["status"] == "error", "用例3失败: 非法格式应返回 error"
    assert result3["code"] == "E003", f"用例3失败: 错误码应为 E003, 实际: {result3['code']}"
    print("  [通过] 正确触发 E003")

    # 测试用例 4: 无有效信息 -> E005
    print("[selftest] 用例4: 无有效信息 (期望 E005)")
    # 输入只有标点/停用词
    test_inputs = [
        "的 了 和 是 在 我 有 就 不 人 都",  # 纯停用词
        "，，，，",  # 纯标点
        "the a an is are",  # 英文停用词
        "123 456 789",  # 纯数字
    ]
    for i, test_input in enumerate(test_inputs, 1):
        result4 = processor.process(test_input, output_format="json")
        assert result4["status"] == "error", f"用例4-{i}失败: 无有效信息应返回 error"
        assert result4["code"] == "E005", f"用例4-{i}失败: 错误码应为 E005, 实际: {result4['code']}"
    print(f"  [通过] 正确触发 E005 (共测试 {len(test_inputs)} 种无有效输入)")

    # 测试用例 5: 批量处理（多段输入）
    print("[selftest] 用例5: 批量处理")
    inputs = [
        "第一段：接口测试，验证返回码和响应时间。",
        "第二段：UI自动化，覆盖主要页面跳转。",
    ]
    results = [processor.process(inp) for inp in inputs]
    assert all(r["status"] == "ok" for r in results), "用例5失败: 批量处理存在失败项"
    assert len(results) == 2, "用例5失败: 批量结果数量不对"
    print(f"  [通过] 批量处理 {len(results)} 条，全部成功")

    # 测试用例 6: 文本格式输出
    print("[selftest] 用例6: text 格式")
    result6 = processor.process("简单的测试内容", output_format="text")
    assert result6["status"] == "ok", "用例6失败: text 格式处理失败"
    print("  [通过] text 格式处理成功")

    # 测试用例 7: 置信度区间检查（宽松）
    print("[selftest] 用例7: 置信度区间")
    for inp in ["正常内容输入", "短", "这是一段比较长的内容，用于测试置信度计算逻辑是否正确。"]:
        r = processor.process(inp)
        if r["status"] == "ok":
            assert 0.0 <= r["confidence"] <= 100.0, f"置信度超出范围: {r['confidence']}"
    print("  [通过] 置信度均在 0-100 区间")

    # 测试用例 8: 边界情况
    print("[selftest] 用例8: 边界情况")
    # 单个有效词
    result8a = processor.process("测试")
    assert result8a["status"] == "ok", "用例8a失败: 单个有效词应该成功"
    # 混合有效和无效内容
    result8b = processor.process("的 了 测试 和 是")
    assert result8b["status"] == "ok", "用例8b失败: 混合内容应该成功"
    assert "测试" in result8b["data"]["keywords"], "用例8b失败: 应提取到有效关键词"
    print("  [通过] 边界情况处理正确")

    print("[selftest] 全部自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="qa-prompt-library 技能 - 独立实现 (clean-room)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码样例，无需外部依赖）",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="待处理的内容（字符串）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--completeness",
        type=str,
        default="auto",
        choices=["auto", "skeleton", "detail"],
        help="完整度 (默认: auto)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        print(json.dumps(
            PromptLibraryProcessor()._make_error("E001", ERROR_MESSAGES["E001"]),
            ensure_ascii=False,
            indent=2,
        ), file=sys.stderr)
        return 1

    processor = PromptLibraryProcessor()
    result = processor.process(
        content=args.input,
        output_format=args.format,
        completeness=args.completeness,
    )

    # 输出结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 文本格式
        if result["status"] == "ok":
            print(f"摘要: {result['data']['summary']}")
            print(f"关键词: {', '.join(result['data']['keywords'])}")
            print(f"置信度: {result['confidence']:.1f}%")
            if result["data"]["needs_review"]:
                print("提示: 建议人工复核")
        else:
            print(f"错误 [{result['code']}]: {result['message']}", file=sys.stderr)
            return 1

    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
