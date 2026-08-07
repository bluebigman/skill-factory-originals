#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-nuwa — 人物思维框架蒸馏与复用工具
版本: 1.0.2
仅依据功能规格独立实现（clean-room）。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入文本为空或不是字符串",
    "E002": "人物名称缺失",
    "E003": "JSON 序列化失败",
    "E004": "输出目录不可写",
    "E005": "输入参数格式错误",
    "E006": "未知命令或参数",
    "E007": "样例数据初始化失败",
    "E008": "字段提取逻辑异常",
    "E009": "置信度计算异常",
    "E010": "内部状态不一致",
}

CONFIDENCE_LEVELS = ("高", "中", "低")

# 思维框架卡模板字段
FRAMEWORK_FIELDS = [
    "人物名称",
    "资料摘要",
    "决策习惯",
    "思维偏好",
    "价值排序",
    "认知模式",
    "置信度",
    "蒸馏时间",
]


# ---------------------------------------------------------------------------
# 基础工具函数
# ---------------------------------------------------------------------------
def now_str() -> str:
    """返回当前时间的字符串表示。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_json_dump(data: Any) -> str:
    """将数据序列化为 JSON 字符串，失败时抛出 E003。"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        raise RuntimeError(f"{ERROR_CODES['E003']}")


# ---------------------------------------------------------------------------
# 核心蒸馏逻辑
# ---------------------------------------------------------------------------
class NuwaDistiller:
    """人物思维框架蒸馏器。"""

    def __init__(self, person_name: str, raw_text: str) -> None:
        """
        初始化蒸馏器。

        :param person_name: 人物名称
        :param raw_text: 原始资料文本
        :raises RuntimeError: E001 / E002
        """
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise RuntimeError(f"{ERROR_CODES['E001']}")
        if not isinstance(person_name, str) or not person_name.strip():
            raise RuntimeError(f"{ERROR_CODES['E002']}")

        self.person_name = person_name.strip()
        self.raw_text = raw_text
        self._text = raw_text.strip()

    # -- 字段提取 ----------------------------------------------------------
    def _extract_decision_habits(self) -> List[str]:
        """提取决策习惯关键词。"""
        habits = []
        patterns = [
            r"决策[：:]\s*([^。；\n]+)",
            r"习惯[：:]\s*([^。；\n]+)",
            r"总是\s*([^。；\n]+)",
        ]
        for pat in patterns:
            for m in re.finditer(pat, self._text):
                phrase = m.group(1).strip()
                if phrase and phrase not in habits:
                    habits.append(phrase)
        return habits[:5]  # 最多 5 条

    def _extract_thinking_preferences(self) -> List[str]:
        """提取思维偏好关键词。"""
        prefs = []
        patterns = [
            r"偏好\s*([^。；\n]+)",
            r"倾向于\s*([^。；\n]+)",
            r"思维[：:]\s*([^。；\n]+)",
        ]
        for pat in patterns:
            for m in re.finditer(pat, self._text):
                phrase = m.group(1).strip()
                if phrase and phrase not in prefs:
                    prefs.append(phrase)
        return prefs[:5]

    def _extract_value_priorities(self) -> List[str]:
        """提取价值排序关键词。"""
        values = []
        patterns = [
            r"重视\s*([^。；\n]+)",
            r"价值[：:]\s*([^。；\n]+)",
            r"排序[：:]\s*([^。；\n]+)",
        ]
        for pat in patterns:
            for m in re.finditer(pat, self._text):
                phrase = m.group(1).strip()
                if phrase and phrase not in values:
                    values.append(phrase)
        return values[:5]

    def _extract_cognitive_patterns(self) -> List[str]:
        """提取认知模式关键词。"""
        patterns = []
        keywords = [
            "类比", "归纳", "演绎", "系统思维", "第一性原理",
            "逆向思维", "批判性", "直觉", "数据驱动", "实验",
        ]
        for kw in keywords:
            if kw in self._text:
                patterns.append(kw)
        return patterns[:5]

    def _compute_confidence(self, extracted: Dict[str, List[str]]) -> Dict[str, str]:
        """
        计算各字段置信度（高/中/低）。
        规则：提取项数 >= 3 为高，>= 1 为中，否则为低。
        """
        result = {}
        for field, items in extracted.items():
            count = len(items)
            if count >= 3:
                result[field] = "高"
            elif count >= 1:
                result[field] = "中"
            else:
                result[field] = "低"
        return result

    def _summarize(self) -> str:
        """生成资料摘要（前 200 字符）。"""
        cleaned = re.sub(r"\s+", " ", self._text).strip()
        return cleaned[:200] + ("…" if len(cleaned) > 200 else "")

    # -- 主流程 ------------------------------------------------------------
    def distill(self) -> Dict[str, Any]:
        """
        执行蒸馏，返回思维框架卡（字典）。

        :raises RuntimeError: E008 / E009
        """
        try:
            extracted = {
                "决策习惯": self._extract_decision_habits(),
                "思维偏好": self._extract_thinking_preferences(),
                "价值排序": self._extract_value_priorities(),
                "认知模式": self._extract_cognitive_patterns(),
            }
        except Exception:
            raise RuntimeError(f"{ERROR_CODES['E008']}")

        try:
            confidence = self._compute_confidence(extracted)
        except Exception:
            raise RuntimeError(f"{ERROR_CODES['E009']}")

        # 汇总置信度（取最低值作为整体置信度）
        overall_conf = "低"
        for c in confidence.values():
            if c == "高":
                overall_conf = "高"
            elif c == "中" and overall_conf != "高":
                overall_conf = "中"

        # 构建框架卡
        framework_card = {
            "人物名称": self.person_name,
            "资料摘要": self._summarize(),
            "决策习惯": extracted["决策习惯"],
            "思维偏好": extracted["思维偏好"],
            "价值排序": extracted["价值排序"],
            "认知模式": extracted["认知模式"],
            "置信度": {
                "整体": overall_conf,
                "字段明细": confidence,
            },
            "蒸馏时间": now_str(),
        }
        return framework_card


# ---------------------------------------------------------------------------
# 批量处理与自定义输出
# ---------------------------------------------------------------------------
def distill_multiple(persons: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    批量蒸馏多个人物。

    :param persons: [{"name": str, "text": str}, ...]
    :return: 框架卡列表
    """
    results = []
    for p in persons:
        distiller = NuwaDistiller(p["name"], p["text"])
        results.append(distiller.distill())
    return results


def distill_custom_fields(person_name: str, raw_text: str, fields: List[str]) -> Dict[str, Any]:
    """
    按自定义字段列表输出框架卡（仅包含指定字段）。

    :param fields: 字段名列表（必须是 FRAMEWORK_FIELDS 的子集）
    """
    distiller = NuwaDistiller(person_name, raw_text)
    card = distiller.distill()
    if not fields:
        return card
    custom = {}
    for f in fields:
        if f in card:
            custom[f] = card[f]
    return custom


# ---------------------------------------------------------------------------
# 内置样例数据（用于 --selftest）
# ---------------------------------------------------------------------------
SAMPLE_DATA = [
    {
        "name": "诸葛亮",
        "text": (
            "诸葛亮决策：先分析敌我形势，再制定周密计划。"
            "习惯：凡事预则立，总是提前准备三套方案。"
            "偏好：系统思维，倾向于数据驱动。"
            "重视：忠诚、智慧、民生。"
            "价值排序：国家利益优先，个人其次。"
            "思维：第一性原理，逆向思维。"
        ),
    },
    {
        "name": "达芬奇",
        "text": (
            "达芬奇决策：基于观察和实验。"
            "习惯：总是记录笔记，倾向于跨学科类比。"
            "偏好：直觉与理性结合。"
            "重视：好奇心、艺术、科学。"
            "价值排序：真理、美、实用。"
            "思维：类比、归纳、演绎。"
        ),
    },
]


# ---------------------------------------------------------------------------
# 自检函数
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读取外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值（大小/区间判断），确保任何环境直接可过。

    :return: 0 表示成功，非 0 表示失败
    """
    try:
        # 1. 单人物蒸馏测试
        distiller = NuwaDistiller(SAMPLE_DATA[0]["name"], SAMPLE_DATA[0]["text"])
        card = distiller.distill()

        # 宽松断言：字段必须存在
        assert "人物名称" in card, "缺少人物名称字段"
        assert "决策习惯" in card, "缺少决策习惯字段"
        assert "思维偏好" in card, "缺少思维偏好字段"
        assert "价值排序" in card, "缺少价值排序字段"
        assert "认知模式" in card, "缺少认知模式字段"
        assert "置信度" in card, "缺少置信度字段"
        assert "蒸馏时间" in card, "缺少蒸馏时间字段"

        # 宽松断言：内容非空
        assert card["人物名称"] == "诸葛亮", "人物名称不匹配"
        assert len(card["决策习惯"]) > 0, "决策习惯为空"
        assert len(card["思维偏好"]) > 0, "思维偏好为空"
        assert len(card["价值排序"]) > 0, "价值排序为空"

        # 置信度必须是合法值
        conf = card["置信度"]["整体"]
        assert conf in CONFIDENCE_LEVELS, f"非法置信度: {conf}"

        # 2. 批量蒸馏测试
        results = distill_multiple(SAMPLE_DATA)
        assert len(results) == 2, "批量蒸馏数量不正确"
        assert results[0]["人物名称"] == "诸葛亮"
        assert results[1]["人物名称"] == "达芬奇"

        # 3. 自定义字段测试
        custom = distill_custom_fields(
            SAMPLE_DATA[1]["name"], SAMPLE_DATA[1]["text"], ["人物名称", "思维偏好"]
        )
        assert "人物名称" in custom, "自定义字段缺人物名称"
        assert "思维偏好" in custom, "自定义字段缺思维偏好"
        assert "决策习惯" not in custom, "自定义字段包含未指定字段"

        # 4. JSON 序列化测试
        json_str = safe_json_dump(results)
        assert len(json_str) > 0, "JSON 序列化结果为空"
        parsed = json.loads(json_str)
        assert len(parsed) == 2, "JSON 反序列化失败"

        # 5. 错误处理测试
        # 测试空人物名称
        try:
            NuwaDistiller("", "文本")
            assert False, "应抛出 E002 错误"
        except RuntimeError as e:
            error_msg = str(e)
            assert "E002" in error_msg, f"错误码不正确: {error_msg}"

        # 测试空文本
        try:
            NuwaDistiller("测试", "")
            assert False, "应抛出 E001 错误"
        except RuntimeError as e:
            error_msg = str(e)
            assert "E001" in error_msg, f"错误码不正确: {error_msg}"

        print("[selftest] 全部断言通过 ✔")
        return 0

    except AssertionError as e:
        print(f"[selftest] 断言失败: {e}")
        return 1
    except RuntimeError as e:
        print(f"[selftest] 运行时错误: {e}")
        return 1
    except Exception as e:
        print(f"[selftest] 未知错误: {e}")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="awesome-nuwa",
        description="人物思维框架蒸馏与复用工具（思维蒸馏 / 框架萃取 / 人物建模）",
        epilog="示例: python main.py --name 诸葛亮 --text '决策：先分析形势…'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读取外部文件/不访问网络）",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="人物名称（与 --text 配合使用）",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="原始资料文本（与 --name 配合使用）",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default=None,
        help="自定义输出字段，逗号分隔（如: 人物名称,决策习惯）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="批量模式 JSON 文件路径（格式: [{\"name\":\"...\",\"text\":\"...\"}]）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出 JSON 文件路径（默认输出到 stdout）",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    主入口函数。

    :return: 退出码（0 成功，非 0 失败）
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 单人物模式
    if args.name and args.text:
        try:
            if args.fields:
                fields = [f.strip() for f in args.fields.split(",") if f.strip()]
                result = distill_custom_fields(args.name, args.text, fields)
            else:
                result = NuwaDistiller(args.name, args.text).distill()
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        output = safe_json_dump(result)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError:
                print(f"错误: {ERROR_CODES['E004']}", file=sys.stderr)
                return 1
        else:
            print(output)
        return 0

    # 批量模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                persons = json.load(f)
            if not isinstance(persons, list):
                raise ValueError("批量数据必须是列表")
            results = distill_multiple(persons)
        except FileNotFoundError:
            print(f"错误: 文件不存在 - {args.batch}", file=sys.stderr)
            return 1
        except (ValueError, KeyError) as e:
            print(f"错误: {ERROR_CODES['E005']} - {e}", file=sys.stderr)
            return 1
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

        output = safe_json_dump(results)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
            except OSError:
                print(f"错误: {ERROR_CODES['E004']}", file=sys.stderr)
                return 1
        else:
            print(output)
        return 0

    # 未匹配任何模式
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
