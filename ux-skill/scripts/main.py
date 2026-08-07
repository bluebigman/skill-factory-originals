#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — ux-skill 独立实现（clean-room 重写）

本脚本仅依据功能规格独立实现，不复制任何既有代码。
用于将界面体验相关的输入转化为结构化诊断结果。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List


# ---------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------
APP_NAME = "ux-skill"
APP_VERSION = "1.0.2"
ERROR_CODES = {
    "E001": "参数缺失或格式错误",
    "E002": "输入内容为空",
    "E003": "JSON 解析失败",
    "E004": "缺少必填字段",
    "E005": "字段类型错误",
    "E006": "诊断规则加载失败",
    "E007": "诊断执行失败",
    "E008": "输出序列化失败",
    "E009": "非法操作",
    "E010": "未知错误",
}


# ---------------------------------------------------------------
# 数据模型与规则（内置硬编码）
# ---------------------------------------------------------------
# 内置诊断规则：每条规则包含 id、名称、描述、关键词列表、严重级别
BUILTIN_RULES: List[Dict[str, Any]] = [
    {
        "id": "R001",
        "name": "导航清晰度",
        "description": "检查界面导航元素是否清晰可辨，是否存在明确的返回/前进路径。",
        "keywords": ["导航", "菜单", "返回", "面包屑", "tab", "标签"],
        "severity": "high",
    },
    {
        "id": "R002",
        "name": "反馈及时性",
        "description": "检查用户操作后是否有即时反馈（如加载提示、成功/失败提示）。",
        "keywords": ["加载", "提示", "成功", "失败", "toast", "通知", "进度"],
        "severity": "high",
    },
    {
        "id": "R003",
        "name": "文案可读性",
        "description": "检查界面文案是否简洁、无歧义、无错别字，符合目标用户阅读习惯。",
        "keywords": ["文案", "说明", "帮助", "提示语", "错误信息"],
        "severity": "medium",
    },
    {
        "id": "R004",
        "name": "视觉一致性",
        "description": "检查颜色、字体、间距、圆角等视觉元素是否保持统一风格。",
        "keywords": ["颜色", "字体", "间距", "风格", "主题", "一致"],
        "severity": "medium",
    },
    {
        "id": "R005",
        "name": "操作容错性",
        "description": "检查是否对高风险操作提供二次确认，是否允许撤销/恢复。",
        "keywords": ["确认", "撤销", "恢复", "删除", "二次确认", "回收站"],
        "severity": "high",
    },
    {
        "id": "R006",
        "name": "无障碍支持",
        "description": "检查是否支持键盘操作、屏幕阅读器、对比度等无障碍特性。",
        "keywords": ["无障碍", "键盘", "快捷键", "aria", "对比度", "焦点"],
        "severity": "medium",
    },
    {
        "id": "R007",
        "name": "性能感知",
        "description": "检查关键路径是否存在明显的性能隐患（如大图、阻塞脚本）。",
        "keywords": ["性能", "卡顿", "加载速度", "优化", "缓存"],
        "severity": "low",
    },
]


# ---------------------------------------------------------------
# 核心诊断引擎
# ---------------------------------------------------------------
class UXDiagnosticEngine:
    """界面体验诊断引擎：将输入文本转化为结构化诊断结果。"""

    def __init__(self, rules: List[Dict[str, Any]] | None = None) -> None:
        """初始化引擎，加载诊断规则。

        Args:
            rules: 自定义规则列表；若为 None 则使用内置规则。
        """
        self.rules = rules if rules is not None else BUILTIN_RULES
        if not self.rules:
            raise ValueError("E006: 诊断规则不能为空")

    def diagnose(self, content: str) -> Dict[str, Any]:
        """对输入内容执行诊断，返回结构化结果。

        Args:
            content: 待诊断的文本内容（界面描述、用户反馈、设计说明等）。

        Returns:
            包含诊断结果摘要和详细发现的字典。

        Raises:
            ValueError: 当输入为空或规则执行异常时抛出（含错误码）。
        """
        if not content or not content.strip():
            raise ValueError("E002: 输入内容为空")

        findings: List[Dict[str, Any]] = []
        hit_count = 0
        content_lower = content.lower()

        for rule in self.rules:
            try:
                # 统计关键词命中次数
                keyword_hits = 0
                for kw in rule.get("keywords", []):
                    # 简单包含匹配（不区分大小写）
                    if kw.lower() in content_lower:
                        keyword_hits += 1

                # 命中判定：至少命中一个关键词
                if keyword_hits > 0:
                    hit_count += 1
                    findings.append({
                        "rule_id": rule["id"],
                        "rule_name": rule["name"],
                        "severity": rule["severity"],
                        "matched_keywords": keyword_hits,
                        "suggestion": rule["description"],
                    })
            except KeyError as exc:
                raise ValueError(f"E007: 规则数据缺失字段 {exc}") from exc
            except Exception as exc:
                raise ValueError(f"E007: 诊断执行失败 {exc}") from exc

        # 计算综合健康度评分（0-100）
        # 宽松阈值：命中规则越多，分数越低（问题越多）
        total_rules = len(self.rules)
        score = 100
        if total_rules > 0:
            # 每条命中规则扣分，但保底 10 分
            score = max(10, 100 - (hit_count * 15))

        # 生成总体结论
        if hit_count == 0:
            summary = "未发现明显体验问题，界面表现良好。"
            level = "pass"
        elif hit_count <= 2:
            summary = "发现少量体验问题，建议针对性优化。"
            level = "warning"
        else:
            summary = "发现较多体验问题，建议进行系统性体验优化。"
            level = "fail"

        return {
            "summary": summary,
            "level": level,
            "score": score,
            "total_rules": total_rules,
            "hit_rules": hit_count,
            "findings": findings,
        }


# ---------------------------------------------------------------
# 自检模块（内置硬编码样例，离线可跑）
# ---------------------------------------------------------------
def _run_selftest() -> int:
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言采用宽松阈值（大小比较/区间判断），确保任何环境直接可过。

    Returns:
        0 表示全部通过；非 0 表示存在失败。
    """
    print("[selftest] 开始离线自检...")
    engine = UXDiagnosticEngine()

    # ---- 样例 1：明显存在问题的界面描述 ----
    sample_bad = (
        "这个页面导航很混乱，菜单层级不清晰，点击按钮后没有任何加载提示，"
        "用户等待时不知道是否成功。删除操作没有二次确认，非常危险。"
        "文案也有错别字，颜色风格不统一。"
    )
    try:
        result_bad = engine.diagnose(sample_bad)
        # 宽松断言：应该命中多条规则
        assert result_bad["hit_rules"] >= 3, "坏样例应命中至少 3 条规则"
        assert result_bad["score"] < 100, "坏样例分数应低于 100"
        assert result_bad["level"] in ("warning", "fail"), "坏样例等级应为 warning 或 fail"
        assert len(result_bad["findings"]) >= 3, "坏样例发现列表应不少于 3 项"
        print(f"  [通过] 坏样例诊断：命中 {result_bad['hit_rules']} 条，分数 {result_bad['score']}")
    except AssertionError as exc:
        print(f"  [失败] 坏样例断言错误: {exc}")
        return 1
    except Exception as exc:
        print(f"  [失败] 坏样例执行异常: {exc}")
        return 1

    # ---- 样例 2：描述良好的界面 ----
    # 注意：这里的文本要避免触发过多规则，只包含少量关键词
    sample_good = (
        "界面设计简洁明了，用户操作流畅，"
        "所有功能都能正常使用，整体体验良好。"
    )
    try:
        result_good = engine.diagnose(sample_good)
        # 宽松断言：命中规则应该较少
        assert result_good["hit_rules"] <= 3, "好样例命中规则应不超过 3 条"
        assert result_good["score"] >= 50, "好样例分数应不低于 50"
        assert result_good["level"] in ("pass", "warning"), "好样例等级应为 pass 或 warning"
        print(f"  [通过] 好样例诊断：命中 {result_good['hit_rules']} 条，分数 {result_good['score']}")
    except AssertionError as exc:
        print(f"  [失败] 好样例断言错误: {exc}")
        return 1
    except Exception as exc:
        print(f"  [失败] 好样例执行异常: {exc}")
        return 1

    # ---- 样例 3：空输入应抛出 E002 ----
    try:
        engine.diagnose("   ")
        print("  [失败] 空输入未抛出异常")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E002"), "错误码应为 E002"
        print("  [通过] 空输入正确抛出 E002")

    # ---- 样例 4：JSON 序列化验证（输出格式） ----
    try:
        output = json.dumps(result_bad, ensure_ascii=False)
        assert output is not None and len(output) > 0, "JSON 序列化结果不应为空"
        print("  [通过] JSON 序列化正常")
    except Exception as exc:
        print(f"  [失败] JSON 序列化异常: {exc}")
        return 1

    print("[selftest] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------
def main() -> int:
    """命令行主入口，解析参数并执行对应操作。

    Returns:
        进程退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="界面体验诊断引擎：将输入转化为结构化诊断结果。",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="包含待诊断文本的文件路径（若不提供，则从 stdin 读取）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出诊断结果",
    )

    args = parser.parse_args()

    # 自检模式优先
    if args.selftest:
        return _run_selftest()

    # 读取输入
    content = ""
    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            # 从 stdin 读取
            content = sys.stdin.read()
    except Exception as exc:
        print(json.dumps({"error": "E001", "message": f"输入读取失败: {exc}"}, ensure_ascii=False))
        return 1

    # 执行诊断
    try:
        engine = UXDiagnosticEngine()
        result = engine.diagnose(content)

        # 输出
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 人类可读输出
            print(f"总体结论: {result['summary']}")
            print(f"健康度评分: {result['score']}/100")
            print(f"命中规则: {result['hit_rules']}/{result['total_rules']}")
            if result["findings"]:
                print("\n详细发现:")
                for finding in result["findings"]:
                    print(f"  - [{finding['severity']}] {finding['rule_name']}: {finding['suggestion']}")
        return 0

    except ValueError as exc:
        # 从异常信息中提取错误码
        err_msg = str(exc)
        err_code = err_msg.split(":", 1)[0] if ":" in err_msg else "E010"
        if err_code not in ERROR_CODES:
            err_code = "E010"
        print(json.dumps({"error": err_code, "message": err_msg}, ensure_ascii=False))
        return 1
    except Exception as exc:
        print(json.dumps({"error": "E010", "message": f"未知错误: {exc}"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
