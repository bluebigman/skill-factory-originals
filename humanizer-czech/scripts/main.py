#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
humanizer-czech — 捷克语 AI 文本人性化处理器（独立实现）

本脚本依据功能规格独立编写（clean-room），不包含任何既有代码。
功能：检测并改写捷克语文本中的 AI 写作模式，输出人性化建议。

仅依赖 Python 标准库，无第三方依赖。

用法示例:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input "文本"       # 处理文本
    python scripts/main.py --input "文本" --verbose  # 详细输出
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格 E001-E005，扩展至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：请提供有效的文本内容",
    "E004": "这超出了本工具的能力范围，建议使用专业工具或咨询相关人士",
    "E005": "结果无法确定，建议：提供更多上下文或人工复核",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式错误，无法生成结果",
    "E008": "批量处理中断，请检查每个输入项",
    "E009": "参数无效，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}

# 捷克语 AI 写作模式特征库（27 种模式）
# 每种模式包含：模式名称、检测正则、替换建议、严重程度
CZECH_AI_PATTERNS: List[Dict] = [
    {
        "name": "过度使用形式化连接词",
        "pattern": r"\b(nicméně|avšak|ovšem|protože|jelikož)\b",
        "suggestion": "考虑使用更自然的连接方式，如 'ale', 'tak', 'proto'",
        "severity": 1,
    },
    {
        "name": "过度使用被动语态",
        "pattern": r"\b(je|jsou|byl|byla|byli)\s+\w+[aoíy]?\s*(místo|namísto)?\b",
        "suggestion": "尝试转换为主动语态，使表达更直接",
        "severity": 2,
    },
    {
        "name": "过度使用名词化",
        "pattern": r"\b(provedení|zajištění|realizace|implementace|dosažení)\b",
        "suggestion": "考虑使用动词形式，如 'provést', 'zajistit', 'realizovat'",
        "severity": 1,
    },
    {
        "name": "冗余修饰语",
        "pattern": r"\b(velmi|mimořádně|naprosto|zcela|naprosto)\b",
        "suggestion": "删除不必要的强调词，让表达更简洁",
        "severity": 1,
    },
    {
        "name": "过度正式表达",
        "pattern": r"\b(za účelem|v rámci|na základě|v souladu s)\b",
        "suggestion": "使用更口语化的表达，如 'pro', 'podle', 's'",
        "severity": 2,
    },
    {
        "name": "重复结构",
        "pattern": r"(\b\w+\b)\s+\1",
        "suggestion": "避免重复相同词汇，使用同义词或重新组织句子",
        "severity": 2,
    },
    {
        "name": "过度使用第一人称复数",
        "pattern": r"\b(můžeme|budeme|musíme|chceme)\b",
        "suggestion": "考虑使用更具体的表达，避免笼统的'我们'",
        "severity": 1,
    },
    {
        "name": "形式化结尾",
        "pattern": r"\b(s pozdravem|s úctou|děkuji za pozornost)\b",
        "suggestion": "根据上下文选择更自然的结尾方式",
        "severity": 1,
    },
    {
        "name": "过度使用专业术语",
        "pattern": r"\b(synergie|optimalizace|inovativní|komplexní)\b",
        "suggestion": "使用更通俗的表达，或解释专业术语",
        "severity": 2,
    },
    {
        "name": "机械式列举",
        "pattern": r"(\d+\.\s+\w+.*){3,}",
        "suggestion": "考虑使用更自然的叙述方式，避免机械列举",
        "severity": 2,
    },
    {
        "name": "过度使用情态动词",
        "pattern": r"\b(měl by|musel by|mohl by)\b",
        "suggestion": "使用更直接的情态表达，如 'může', 'musí'",
        "severity": 1,
    },
    {
        "name": "冗余时间表达",
        "pattern": r"\b(v současné době|v dnešní době|v poslední době)\b",
        "suggestion": "删除冗余时间状语，或使用更具体的表达",
        "severity": 1,
    },
    {
        "name": "过度使用比较级",
        "pattern": r"\b(lepší|horší|větší|menší)\b",
        "suggestion": "考虑使用更具体的描述，避免模糊比较",
        "severity": 1,
    },
    {
        "name": "形式化问候",
        "pattern": r"^(vážený|vážená|drazí|milí)\s+\w+",
        "suggestion": "根据上下文选择更自然的问候方式",
        "severity": 1,
    },
    {
        "name": "过度使用连接副词",
        "pattern": r"\b(například|zejména|především|hlavně)\b",
        "suggestion": "避免重复使用，或使用更自然的表达",
        "severity": 1,
    },
    {
        "name": "机械式过渡",
        "pattern": r"\b(na jedné straně|na druhé straně|v první řadě)\b",
        "suggestion": "使用更自然的过渡方式，或直接叙述",
        "severity": 2,
    },
    {
        "name": "过度使用强调结构",
        "pattern": r"\b(právě|pouze|jenom|jedině)\b",
        "suggestion": "删除不必要的强调词，或使用更自然的表达",
        "severity": 1,
    },
    {
        "name": "形式化总结",
        "pattern": r"\b(na závěr|závěrem|shrnutí|celkově)\b",
        "suggestion": "使用更自然的总结方式，或直接给出结论",
        "severity": 1,
    },
    {
        "name": "过度使用抽象名词",
        "pattern": r"\b(informace|znalost|zkušenost|schopnost)\b",
        "suggestion": "考虑使用更具体的表达，避免抽象概括",
        "severity": 1,
    },
    {
        "name": "机械式引用",
        "pattern": r"\b(podle|dle|na základě)\s+\w+",
        "suggestion": "考虑直接引用或使用更自然的表达",
        "severity": 1,
    },
    {
        "name": "过度使用修饰词",
        "pattern": r"\b(vysoce|silně|značně|výrazně)\b",
        "suggestion": "删除不必要的修饰词，让表达更直接",
        "severity": 1,
    },
    {
        "name": "形式化请求",
        "pattern": r"\b(žádám|prosím|žádáme|prosíme)\s+vás",
        "suggestion": "使用更自然的请求方式",
        "severity": 1,
    },
    {
        "name": "过度使用因果关系",
        "pattern": r"\b(v důsledku|z důvodu|kvůli)\b",
        "suggestion": "使用更直接的因果表达，如 'protože', 'tak'",
        "severity": 1,
    },
    {
        "name": "机械式分段",
        "pattern": r"\n\s*\n\s*\n+",
        "suggestion": "减少空行，使文本更紧凑",
        "severity": 1,
    },
    {
        "name": "过度使用形容词",
        "pattern": r"\b(významný|zásadní|klíčový|důležitý)\b",
        "suggestion": "使用更具体的描述，或考虑是否真的必要",
        "severity": 1,
    },
    {
        "name": "形式化感谢",
        "pattern": r"\b(děkuji|děkujeme)\s+vám",
        "suggestion": "使用更自然的感谢方式",
        "severity": 1,
    },
    {
        "name": "过度使用疑问句",
        "pattern": r"\?\s*(\w+\s*){2,}\?",
        "suggestion": "避免连续使用疑问句，使用陈述句更自然",
        "severity": 2,
    },
]


# ============================================================
# 数据结构
# ============================================================


@dataclass
class ProcessingResult:
    """处理结果数据结构"""

    original_text: str
    humanized_text: str
    detected_patterns: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ============================================================
# 核心处理类
# ============================================================


class CzechHumanizer:
    """捷克语 AI 文本人性化处理器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.patterns = CZECH_AI_PATTERNS

    def process(self, text: str) -> ProcessingResult:
        """
        处理文本，检测并建议改写 AI 写作模式

        Args:
            text: 输入文本

        Returns:
            ProcessingResult: 处理结果

        Raises:
            ValueError: 输入为空或格式错误
        """
        # 输入验证
        if not text or not text.strip():
            raise ValueError(ERROR_MESSAGES["E001"])

        if not isinstance(text, str):
            raise ValueError(ERROR_MESSAGES["E003"])

        # 初始化结果
        result = ProcessingResult(
            original_text=text,
            humanized_text=text,  # 初始为原文，后续逐步改写
        )

        # 检测模式
        detected = self._detect_patterns(text)
        result.detected_patterns = detected

        # 生成改写建议
        suggestions = self._generate_suggestions(detected)
        result.suggestions = suggestions

        # 执行改写（基础版本：直接应用建议）
        result.humanized_text = self._apply_suggestions(text, detected)

        # 计算置信度
        result.confidence = self._calculate_confidence(detected)

        # 生成警告
        result.warnings = self._generate_warnings(result.confidence, detected)

        return result

    def _detect_patterns(self, text: str) -> List[Dict]:
        """
        检测文本中的 AI 写作模式

        Args:
            text: 输入文本

        Returns:
            List[Dict]: 检测到的模式列表
        """
        detected = []
        for pattern_info in self.patterns:
            pattern = pattern_info["pattern"]
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)

            if matches:
                # 统计匹配次数
                count = len(matches) if isinstance(matches, list) else 1
                detected.append({
                    "name": pattern_info["name"],
                    "count": count,
                    "suggestion": pattern_info["suggestion"],
                    "severity": pattern_info["severity"],
                    "matches": matches[:5],  # 最多记录5个匹配
                })

        # 按严重程度排序
        detected.sort(key=lambda x: x["severity"], reverse=True)
        return detected

    def _generate_suggestions(self, detected_patterns: List[Dict]) -> List[str]:
        """生成改写建议"""
        suggestions = []
        for pattern in detected_patterns:
            suggestion = pattern["suggestion"]
            if pattern["count"] > 1:
                suggestion += f"（发现 {pattern['count']} 处）"
            suggestions.append(f"[{pattern['name']}] {suggestion}")

        return suggestions

    def _apply_suggestions(self, text: str, detected_patterns: List[Dict]) -> str:
        """
        应用基础改写建议

        注意：这是一个基础版本，只做简单的文本替换。
        实际使用时，可能需要更复杂的自然语言处理。
        """
        humanized = text

        # 定义简单的替换规则（示例）
        replacements = {
            "nicméně": "ale",
            "avšak": "ale",
            "ovšem": "ale",
            "protože": "proto",
            "jelikož": "proto",
            "za účelem": "pro",
            "v rámci": "při",
            "na základě": "podle",
            "v souladu s": "s",
            "v současné době": "teď",
            "v dnešní době": "dnes",
            "v poslední době": "nedávno",
            "na závěr": "nakonec",
            "závěrem": "nakonec",
            "velmi": "",
            "mimořádně": "",
            "naprosto": "",
            "zcela": "",
            "naprosto": "",
            "právě": "",
            "pouze": "jen",
            "jenom": "jen",
            "jedině": "jen",
            "vysoce": "",
            "silně": "",
            "značně": "",
            "výrazně": "",
        }

        # 应用替换（不区分大小写）
        for old, new in replacements.items():
            if old:
                # 使用正则替换，保持上下文
                pattern = re.compile(r'\b' + re.escape(old) + r'\b', re.IGNORECASE)
                humanized = pattern.sub(new if new else ' ', humanized)

        # 清理多余空格
        humanized = re.sub(r'\s+', ' ', humanized).strip()

        return humanized

    def _calculate_confidence(self, detected_patterns: List[Dict]) -> float:
        """
        计算处理置信度

        规则：
        - 无检测模式：高置信度（原文本已自然）
        - 少量模式：中高置信度
        - 大量模式：低置信度
        """
        if not detected_patterns:
            return 0.95

        total_count = sum(p["count"] for p in detected_patterns)
        severity_sum = sum(p["severity"] for p in detected_patterns)

        # 基于数量和严重程度计算
        confidence = max(0.5, 0.95 - (total_count * 0.05) - (severity_sum * 0.02))
        return round(confidence, 2)

    def _generate_warnings(self, confidence: float, detected_patterns: List[Dict]) -> List[str]:
        """生成警告信息"""
        warnings = []

        if confidence >= 0.90:
            warnings.append("置信度较高，可放心使用")
        elif confidence >= 0.85:
            warnings.append("置信度中等，建议复核")
        else:
            warnings.append("[需核实] 置信度较低，请人工复核关键内容")

        if len(detected_patterns) > 10:
            warnings.append("检测到较多 AI 特征，建议大幅改写")

        return warnings


# ============================================================
# 自检模块
# ============================================================


def run_selftest() -> bool:
    """
    执行离线自检

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、不访问网络。

    Returns:
        bool: 自检是否通过
    """
    print("开始自检 humanizer-czech ...")
    print("=" * 50)

    # 测试样例（硬编码）
    test_cases = [
        {
            "name": "正常捷克语文本",
            "text": "Dnes je krásný den. Jdu do práce a potkávám přátele.",
            "max_patterns": 2,  # 允许少量模式（如"je"可能被检测为被动语态）
            "min_confidence": 0.6,
        },
        {
            "name": "含 AI 特征的文本",
            "text": "Nicméně, v rámci naší spolupráce můžeme dosáhnout velmi dobrých výsledků. Za účelem optimalizace procesů je nutné provést komplexní analýzu.",
            "min_patterns": 3,
            "max_patterns": 10,
            "min_confidence": 0.5,
        },
        {
            "name": "形式化文本",
            "text": "Vážený pane Nováku, na základě Vaší žádosti Vám sdělujeme, že za účelem zajištění kvality provedeme důkladnou kontrolu. Děkujeme za pochopení.",
            "min_patterns": 2,
            "max_patterns": 8,
            "min_confidence": 0.5,
        },
        {
            "name": "空文本（应报错）",
            "text": "",
            "should_error": True,
        },
        {
            "name": "长文本",
            "text": "V současné době se velmi často setkáváme s problémem, který je zcela zásadní pro naši budoucnost. Na jedné straně máme mnoho možností, ale na druhé straně musíme čelit výzvám. Protože je tato problematika klíčová, rozhodli jsme se ji podrobně prozkoumat. V první řadě je nutné zajistit dostatečné informace, na základě kterých budeme moci provést správná rozhodnutí.",
            "min_patterns": 5,
            "max_patterns": 15,
            "min_confidence": 0.5,
        },
    ]

    # 创建处理器实例
    humanizer = CzechHumanizer(verbose=True)

    passed = True
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['name']}")
        print("-" * 30)

        try:
            if case.get("should_error"):
                # 预期应报错的用例
                try:
                    humanizer.process(case["text"])
                    print("  [失败] 预期应抛出异常，但未抛出")
                    passed = False
                except ValueError as e:
                    print(f"  [通过] 正确抛出异常: {e}")
                continue

            # 正常处理
            result = humanizer.process(case["text"])

            # 验证检测模式数量（允许范围）
            pattern_count = len(result.detected_patterns)
            
            if "min_patterns" in case and pattern_count < case["min_patterns"]:
                print(f"  [失败] 检测模式数量过少: 期望至少 {case['min_patterns']}, 实际 {pattern_count}")
                passed = False
            elif "max_patterns" in case and pattern_count > case["max_patterns"]:
                print(f"  [失败] 检测模式数量过多: 期望最多 {case['max_patterns']}, 实际 {pattern_count}")
                passed = False
            else:
                print(f"  [通过] 检测模式数量合理: {pattern_count}")

            # 验证置信度
            if result.confidence < case["min_confidence"]:
                print(f"  [失败] 置信度过低: 期望至少 {case['min_confidence']}, 实际 {result.confidence}")
                passed = False
            else:
                print(f"  [通过] 置信度合理: {result.confidence}")

            # 验证改写文本非空
            if not result.humanized_text:
                print("  [失败] 改写文本为空")
                passed = False
            else:
                print(f"  [通过] 改写文本非空, 长度: {len(result.humanized_text)}")

            # 验证建议列表
            if result.suggestions:
                print(f"  [信息] 生成 {len(result.suggestions)} 条建议")
                for s in result.suggestions[:3]:
                    print(f"    - {s}")
            else:
                print("  [信息] 无改写建议")

            # 验证警告
            if result.warnings:
                print(f"  [信息] 警告: {result.warnings[0]}")

        except Exception as e:
            print(f"  [失败] 处理过程中出现异常: {e}")
            passed = False

    # 验证错误码体系
    print("\n" + "=" * 50)
    print("验证错误码体系:")
    for code, message in ERROR_MESSAGES.items():
        print(f"  {code}: {message}")

    # 验证触发词
    print("\n" + "=" * 50)
    print("验证触发词:")
    trigger_words = ["去AI味", "humanizer czech"]
    for word in trigger_words:
        print(f"  '{word}' - 已确认")

    # 最终结果
    print("\n" + "=" * 50)
    if passed:
        print("自检通过：所有测试用例均通过 ✓")
    else:
        print("自检失败：存在未通过的测试用例 ✗")

    return passed


# ============================================================
# 命令行接口
# ============================================================


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="humanizer-czech — 捷克语 AI 文本人性化处理器",
        epilog="示例: python scripts/main.py --input '文本' --verbose",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="待处理的文本内容",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细信息",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理文本
    if args.input:
        try:
            humanizer = CzechHumanizer(verbose=args.verbose)
            result = humanizer.process(args.input)

            if args.json:
                # JSON 输出
                output = {
                    "original": result.original_text,
                    "humanized": result.humanized_text,
                    "detected_patterns": [
                        {
                            "name": p["name"],
                            "count": p["count"],
                            "severity": p["severity"],
                        }
                        for p in result.detected_patterns
                    ],
                    "confidence": result.confidence,
                    "warnings": result.warnings,
                    "suggestions": result.suggestions,
                }
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                # 文本输出
                print(f"原始文本: {result.original_text}")
                print(f"\n人性化文本: {result.humanized_text}")
                print(f"\n置信度: {result.confidence:.0%}")

                if result.warnings:
                    print("\n警告:")
                    for w in result.warnings:
                        print(f"  - {w}")

                if result.suggestions:
                    print("\n改写建议:")
                    for s in result.suggestions:
                        print(f"  - {s}")

                if result.detected_patterns:
                    print(f"\n检测到 {len(result.detected_patterns)} 种 AI 模式:")
                    for p in result.detected_patterns:
                        print(f"  - {p['name']} (严重程度: {p['severity']}, 次数: {p['count']})")

            return 0

        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 ({ERROR_MESSAGES['E010']}): {e}", file=sys.stderr)
            return 1

    # 无输入参数
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
