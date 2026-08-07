#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notebooklm-py 技能实现脚本

本脚本依据功能规格独立实现（clean-room 风格），
提供标准流程处理、错误码体系和离线自检功能。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 补充内部错误码
    "E006": "内部处理错误，请重试",
    "E007": "输出格式错误，请检查配置",
    "E008": "批量处理中断，请检查输入",
    "E009": "置信度计算异常，请重试",
    "E010": "未知错误，请查看日志",
}

# 置信度阈值
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 默认输出模板字段
DEFAULT_FIELDS = ["content", "keywords", "summary", "confidence", "flags"]


# ============================================================
# 核心处理类
# ============================================================

class NotebookLMProcessor:
    """核心处理器：负责输入解析、关键信息提取、结构化输出。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化处理器，可传入自定义配置。"""
        self.config = config or {}
        self.fields = self.config.get("fields", DEFAULT_FIELDS)
        self.min_confidence = self.config.get("min_confidence", 0.0)

    # ---------- 输入校验 ----------
    def validate_input(self, raw_input: Any) -> Tuple[bool, Optional[str]]:
        """
        校验输入是否有效。
        返回 (是否有效, 错误码或None)
        """
        if raw_input is None:
            return False, "E001"
        if isinstance(raw_input, str) and not raw_input.strip():
            return False, "E001"
        if isinstance(raw_input, (list, tuple)) and len(raw_input) == 0:
            return False, "E001"
        return True, None

    # ---------- 关键信息提取 ----------
    def extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词。
        简单实现：按常见分隔符拆分，统计词频，返回高频词。
        """
        # 清洗文本：去除非字母数字字符（保留中文、英文、数字）
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]", " ", text.lower())
        words = [w for w in cleaned.split() if len(w) > 1]

        # 词频统计
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        # 按频率降序，返回前5个
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:5]]

    def generate_summary(self, text: str, max_len: int = 200) -> str:
        """
        生成摘要。
        简单实现：取前若干字符，并截断到句子边界。
        """
        if len(text) <= max_len:
            return text.strip()
        truncated = text[:max_len]
        # 尝试在句号、感叹号、问号处截断
        for punct in ["。", "！", "？", ".", "!", "?"]:
            idx = truncated.rfind(punct)
            if idx > max_len * 0.5:  # 至少保留一半长度
                return truncated[: idx + 1].strip()
        return truncated.strip() + "..."

    def compute_confidence(self, text: str, keywords: List[str]) -> float:
        """
        计算置信度。
        简单启发式：基于文本长度和关键词覆盖率。
        """
        if not text.strip():
            return 0.0

        # 文本长度因子（0.3 - 1.0）
        length_factor = min(1.0, len(text.strip()) / 100.0)
        length_score = 0.3 + 0.7 * length_factor

        # 关键词覆盖率因子（0.0 - 1.0）
        if not keywords:
            keyword_score = 0.5  # 无关键词时给中等分
        else:
            found = sum(1 for kw in keywords if kw in text.lower())
            keyword_score = found / len(keywords)

        # 综合置信度
        confidence = 0.4 * length_score + 0.6 * keyword_score
        return round(min(1.0, max(0.0, confidence)), 4)

    def flag_uncertainties(self, confidence: float) -> List[str]:
        """根据置信度生成标注标记。"""
        flags = []
        if confidence < CONFIDENCE_MEDIUM:
            flags.append("[需核实]")
        elif confidence < CONFIDENCE_HIGH:
            flags.append("建议复核")
        return flags

    # ---------- 主处理流程 ----------
    def process(self, raw_input: Any) -> Dict[str, Any]:
        """
        执行核心处理流程：
        1. 校验输入
        2. 解析内容
        3. 提取关键信息
        4. 生成输出并标注置信度
        """
        # Step 1: 输入校验
        valid, error_code = self.validate_input(raw_input)
        if not valid:
            return {"error": error_code, "message": ERROR_MESSAGES.get(error_code, "")}

        # Step 2: 解析输入（支持字符串、列表、字典）
        if isinstance(raw_input, str):
            text = raw_input.strip()
        elif isinstance(raw_input, (list, tuple)):
            text = " ".join(str(item) for item in raw_input).strip()
        elif isinstance(raw_input, dict):
            # 尝试从常见字段中提取文本
            text = str(raw_input.get("content") or raw_input.get("text") or raw_input).strip()
        else:
            text = str(raw_input).strip()

        if not text:
            return {"error": "E001", "message": ERROR_MESSAGES["E001"]}

        # Step 3: 提取关键信息
        keywords = self.extract_keywords(text)
        summary = self.generate_summary(text)

        # Step 4: 计算置信度并生成标记
        confidence = self.compute_confidence(text, keywords)
        flags = self.flag_uncertainties(confidence)

        # Step 5: 组装结果
        result = {
            "content": text,
            "keywords": keywords,
            "summary": summary,
            "confidence": confidence,
            "flags": flags,
            "length": len(text),
        }

        # 按配置字段过滤
        filtered = {k: v for k, v in result.items() if k in self.fields}
        filtered["confidence_label"] = self._confidence_label(confidence)

        return filtered

    def _confidence_label(self, confidence: float) -> str:
        """将置信度转换为文字标签。"""
        if confidence >= CONFIDENCE_HIGH:
            return "高置信度"
        elif confidence >= CONFIDENCE_MEDIUM:
            return "中置信度（建议复核）"
        else:
            return "低置信度（需核实）"

    # ---------- 批量处理 ----------
    def process_batch(self, inputs: List[Any]) -> List[Dict[str, Any]]:
        """批量处理多个输入。"""
        results = []
        for item in inputs:
            try:
                result = self.process(item)
                results.append(result)
            except Exception:
                results.append({"error": "E008", "message": ERROR_MESSAGES["E008"]})
        return results


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置离线自检，不依赖外部文件或网络。
    使用硬编码样例数据验证核心逻辑。
    采用宽松断言（区间/大小比较），确保稳健。
    """
    print("开始自检 (selftest)...")
    processor = NotebookLMProcessor()

    # 测试用例1: 正常文本处理
    sample_text = (
        "Python是一种广泛使用的编程语言。"
        "它支持多种编程范式，包括面向对象、函数式和过程式编程。"
        "Python拥有丰富的标准库和第三方库，适用于Web开发、数据分析、人工智能等领域。"
        "学习Python可以帮助开发者提高工作效率，快速实现各种功能。"
    )
    result = processor.process(sample_text)
    assert "error" not in result, f"正常处理不应报错: {result}"
    assert isinstance(result.get("content"), str) and len(result["content"]) > 0, "内容不应为空"
    assert isinstance(result.get("keywords"), list), "关键词应为列表"
    assert len(result.get("keywords", [])) > 0, "应提取到关键词"
    assert isinstance(result.get("summary"), str) and len(result["summary"]) > 0, "摘要不应为空"
    assert isinstance(result.get("confidence"), float), "置信度应为浮点数"
    assert 0.0 <= result["confidence"] <= 1.0, "置信度应在0-1之间"
    print("  ✓ 正常文本处理通过")

    # 测试用例2: 空输入
    empty_result = processor.process("")
    assert "error" in empty_result, "空输入应返回错误"
    assert empty_result["error"] == "E001", "空输入应返回E001错误码"
    print("  ✓ 空输入校验通过")

    # 测试用例3: None输入
    none_result = processor.process(None)
    assert "error" in none_result and none_result["error"] == "E001", "None输入应返回E001"
    print("  ✓ None输入校验通过")

    # 测试用例4: 批量处理
    batch_inputs = ["第一条测试内容", "第二条测试内容", ""]
    batch_results = processor.process_batch(batch_inputs)
    assert len(batch_results) == 3, "批量处理应有3个结果"
    assert "error" not in batch_results[0], "第一条应成功"
    assert "error" not in batch_results[1], "第二条应成功"
    assert "error" in batch_results[2], "第三条（空）应失败"
    print("  ✓ 批量处理通过")

    # 测试用例5: 置信度区间
    long_text = "这是一个较长的文本。 " * 50
    high_conf_result = processor.process(long_text)
    assert high_conf_result["confidence"] > 0.5, "长文本置信度应较高"
    print("  ✓ 置信度计算通过")

    # 测试用例6: 列表输入
    list_result = processor.process(["hello", "world", "test"])
    assert "error" not in list_result, "列表输入应成功"
    assert len(list_result["content"]) > 0, "列表输入内容不应为空"
    print("  ✓ 列表输入通过")

    # 测试用例7: 错误码完整性
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"缺少错误码 {code}"
    print("  ✓ 错误码完整")

    # 测试用例8: 摘要长度
    short_text = "短文本"
    short_result = processor.process(short_text)
    assert len(short_result["summary"]) <= len(short_text) + 3, "摘要不应比原文长太多"
    print("  ✓ 摘要生成通过")

    print("全部自检通过 ✓")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="notebooklm-py 技能实现 - 标准处理流程",
        epilog="示例: python main.py --input '待处理文本' --format json"
    )
    parser.add_argument(
        "--input", "-i", type=str, default=None,
        help="待处理的输入内容（文本或文件路径）"
    )
    parser.add_argument(
        "--format", "-f", type=str, choices=["json", "text"], default="json",
        help="输出格式（默认: json）"
    )
    parser.add_argument(
        "--fields", type=str, default=None,
        help="输出字段，逗号分隔（默认: content,keywords,summary,confidence,flags）"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置离线自检"
    )
    parser.add_argument(
        "--batch", type=str, default=None,
        help="批量处理：提供JSON数组字符串或文件路径"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"自检异常: {e}", file=sys.stderr)
            return 1

    # 配置处理器
    config = {}
    if args.fields:
        config["fields"] = [f.strip() for f in args.fields.split(",") if f.strip()]

    processor = NotebookLMProcessor(config)

    # 批量处理模式
    if args.batch:
        try:
            # 尝试解析JSON
            batch_data = json.loads(args.batch)
            if isinstance(batch_data, list):
                results = processor.process_batch(batch_data)
            else:
                print("批量输入应为JSON数组", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            print("批量输入JSON格式错误", file=sys.stderr)
            return 1

        # 输出结果
        if args.format == "json":
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for i, r in enumerate(results):
                print(f"--- 结果 {i+1} ---")
                if "error" in r:
                    print(f"错误: {r['error']} - {r.get('message', '')}")
                else:
                    print(f"内容: {r.get('content', '')[:50]}...")
                    print(f"关键词: {', '.join(r.get('keywords', []))}")
                    print(f"置信度: {r.get('confidence', 0):.2%}")
        return 0

    # 单条处理模式
    if not args.input:
        print("请提供输入内容 (--input) 或使用 --selftest 运行自检", file=sys.stderr)
        print(ERROR_MESSAGES["E001"], file=sys.stderr)
        return 1

    # 处理输入（支持文件路径）
    input_content = args.input
    try:
        # 如果输入是文件路径且文件存在，读取文件内容
        if len(args.input) < 260 and sys.platform != "win32" or len(args.input) < 260:
            import os
            if os.path.isfile(args.input):
                with open(args.input, "r", encoding="utf-8") as f:
                    input_content = f.read()
    except Exception:
        pass  # 忽略文件读取错误，按文本处理

    # 执行处理
    result = processor.process(input_content)

    # 输出结果
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if "error" in result:
            print(f"错误 [{result['error']}]: {result.get('message', '')}")
        else:
            print(f"内容: {result.get('content', '')}")
            print(f"关键词: {', '.join(result.get('keywords', []))}")
            print(f"摘要: {result.get('summary', '')}")
            print(f"置信度: {result.get('confidence', 0):.2%} ({result.get('confidence_label', '')})")
            if result.get("flags"):
                print(f"标记: {', '.join(result['flags'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
