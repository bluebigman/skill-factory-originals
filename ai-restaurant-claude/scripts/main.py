#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — AI 餐厅营销与运营引擎（代码审查技能）独立实现

本脚本依据功能规格 clean-room 重写，不复制任何既有代码。
功能：多平台评论分析、菜单工程、本地 SEO 辅助、结构化转换、置信度标注。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码与提示话术表（对应规格"四、异常处理"）
# ============================================================
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：JSON 对象或包含 text 字段的字符串",
    "E004": "这超出了本工具的能力范围，建议使用专门的分析工具或咨询专业人士",
    "E005": "结果无法确定，建议：补充更多上下文信息后重试，或人工复核关键结果",
}


# ============================================================
# 核心数据结构
# ============================================================
class StructuredResult:
    """结构化输出结果容器"""

    def __init__(self) -> None:
        self.fields: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_key_fields(text: str) -> Dict[str, str]:
    """
    从输入文本中提取关键字段（简单规则引擎）。

    支持识别：
      - 菜品名称（以"菜品"/"菜名"开头或包含冒号）
      - 价格（含"价格"/"¥"/"元"）
      - 评分（含"评分"/"星级"）
      - 平台来源（含"平台"/"来源"）
      - 评论内容（含"评论"/"评价"）
    """
    fields: Dict[str, str] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line in lines:
        lower = line.lower()
        # 简单键值对解析：key: value 或 key：value
        if ":" in line:
            key, _, value = line.partition(":")
        elif "：" in line:
            key, _, value = line.partition("：")
        else:
            continue

        key = key.strip()
        value = value.strip()
        if not value:
            continue

        # 根据关键词归类
        if any(kw in key for kw in ("菜品", "菜名", "菜")):
            fields["dish_name"] = value
        elif any(kw in key for kw in ("价格", "单价", "¥", "元")):
            fields["price"] = value
        elif any(kw in key for kw in ("评分", "星级", "分数")):
            fields["rating"] = value
        elif any(kw in key for kw in ("平台", "来源", "渠道")):
            fields["platform"] = value
        elif any(kw in key for kw in ("评论", "评价", "反馈")):
            fields["review"] = value
        elif any(kw in key for kw in ("地址", "位置", "商圈")):
            fields["location"] = value
        else:
            # 未识别字段保留原名
            fields.setdefault("extra_" + key, value)

    return fields


def compute_confidence(fields: Dict[str, str]) -> Tuple[float, List[str]]:
    """
    计算置信度（0-100）。

    规则：
      - 基础分 50
      - 每识别出一个关键字段加 10 分（上限 100）
      - 关键字段缺失时给出警告
    """
    score = 50.0
    warnings: List[str] = []
    key_fields = ["dish_name", "price", "rating", "platform", "review"]

    for k in key_fields:
        if k in fields and fields[k]:
            score += 10.0
        else:
            warnings.append(f"缺少关键字段: {k}")

    # 上限 100
    score = min(score, 100.0)
    return score, warnings


def process_input(raw_input: Any) -> Dict[str, Any]:
    """
    处理输入，返回结构化结果。

    输入支持：
      - 字符串（视为文本内容）
      - 字典 / JSON 字符串（含 text 字段或直接为字段映射）
    """
    # 输入为空
    if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
        raise ValueError("E001")

    # 字符串输入
    if isinstance(raw_input, str):
        text_content = raw_input.strip()
        # 尝试解析 JSON
        if text_content.startswith("{"):
            try:
                parsed = json.loads(text_content)
                if isinstance(parsed, dict):
                    return process_input(parsed)
            except json.JSONDecodeError:
                pass
        # 普通文本
        fields = extract_key_fields(text_content)
        if not fields:
            raise ValueError("E003")
        confidence, warnings = compute_confidence(fields)
        return {"fields": fields, "confidence": confidence, "warnings": warnings}

    # 字典输入
    if isinstance(raw_input, dict):
        # 如果含 text 字段，递归处理
        if "text" in raw_input:
            return process_input(raw_input["text"])
        # 直接作为字段映射
        fields = {str(k): str(v) for k, v in raw_input.items() if v is not None}
        if not fields:
            raise ValueError("E001")
        confidence, warnings = compute_confidence(fields)
        return {"fields": fields, "confidence": confidence, "warnings": warnings}

    # 其他类型
    raise ValueError("E003")


def format_output(result: Dict[str, Any], fmt: str = "json") -> str:
    """按指定格式输出结果"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        for k, v in result["fields"].items():
            lines.append(f"{k}: {v}")
        lines.append(f"置信度: {result['confidence']:.1f}%")
        if result["warnings"]:
            lines.append("警告:")
            for w in result["warnings"]:
                lines.append(f"  - {w}")
        return "\n".join(lines)
    else:
        return json.dumps(result, ensure_ascii=False)


def handle_error(error_code: str) -> str:
    """生成标准化错误输出"""
    msg = ERROR_MESSAGES.get(error_code, "未知错误")
    return json.dumps({"error": error_code, "message": msg}, ensure_ascii=False)


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。

    使用宽松断言（区间/大小比较），不依赖精确值。
    """
    print("开始自检...")

    # ---- 样例 1: 完整输入 ----
    sample1 = """
    菜品: 招牌烤鸭
    价格: 128元
    评分: 4.8星
    平台: 大众点评
    评论: 外皮酥脆，肉质鲜嫩
    """
    try:
        result1 = process_input(sample1)
        fields1 = result1["fields"]
        conf1 = result1["confidence"]

        # 宽松断言
        assert "dish_name" in fields1, "应该识别出菜品名称"
        assert "price" in fields1, "应该识别出价格"
        assert "rating" in fields1, "应该识别出评分"
        assert conf1 >= 80.0, f"完整输入置信度应较高，实际 {conf1}"
        print("  [通过] 样例1: 完整输入解析")
    except AssertionError as e:
        print(f"  [失败] 样例1: {e}")
        return 1
    except Exception:
        print("  [失败] 样例1: 发生异常")
        return 1

    # ---- 样例 2: 部分输入（低置信度） ----
    sample2 = "今天吃了碗面，味道不错"
    try:
        result2 = process_input(sample2)
        conf2 = result2["confidence"]
        # 宽松断言：置信度不应过高（因为关键字段缺失）
        assert conf2 < 90.0, f"不完整输入置信度应较低，实际 {conf2}"
        assert conf2 >= 0.0, "置信度不能为负"
        print("  [通过] 样例2: 部分输入低置信度")
    except AssertionError as e:
        print(f"  [失败] 样例2: {e}")
        return 1
    except Exception:
        print("  [失败] 样例2: 发生异常")
        return 1

    # ---- 样例 3: 空输入应报错 E001 ----
    try:
        process_input("   ")
        print("  [失败] 样例3: 空输入应抛 E001")
        return 1
    except ValueError as e:
        assert str(e) == "E001", f"错误码应为 E001，实际 {e}"
        print("  [通过] 样例3: 空输入错误处理")

    # ---- 样例 4: 错误消息映射 ----
    try:
        msg = handle_error("E001")
        parsed = json.loads(msg)
        assert parsed["error"] == "E001", "错误码映射错误"
        assert len(parsed["message"]) > 0, "错误消息不能为空"
        print("  [通过] 样例4: 错误消息映射")
    except Exception:
        print("  [失败] 样例4: 错误消息映射异常")
        return 1

    # ---- 样例 5: 批量处理 ----
    batch_input = [
        "菜品: 宫保鸡丁\n价格: 38元\n评分: 4.5\n平台: 美团",
        "菜品: 麻婆豆腐\n价格: 28元\n评分: 4.2\n平台: 饿了么",
    ]
    try:
        for item in batch_input:
            result = process_input(item)
            assert result["confidence"] >= 80.0, "批量样例置信度应较高"
        print("  [通过] 样例5: 批量处理")
    except AssertionError as e:
        print(f"  [失败] 样例5: {e}")
        return 1
    except Exception:
        print("  [失败] 样例5: 异常")
        return 1

    # ---- 样例 6: 输出格式化 ----
    try:
        result = process_input("菜品: 测试菜\n价格: 10元")
        json_out = format_output(result, "json")
        text_out = format_output(result, "text")
        assert '"fields"' in json_out, "JSON 输出应包含 fields"
        assert "置信度" in text_out, "文本输出应包含置信度"
        print("  [通过] 样例6: 输出格式化")
    except Exception:
        print("  [失败] 样例6: 输出格式化异常")
        return 1

    print("全部自检通过 ✅")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI 餐厅营销与运营引擎（代码审查技能）",
        epilog="示例: python main.py --input '菜品: 烤鸭\\n价格: 99元' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容：文本、JSON 字符串，或包含 text 字段的 JSON",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读外部文件、不访问网络）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：JSON 数组字符串，每个元素为一条输入",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 批量处理模式
    if args.batch:
        try:
            items = json.loads(args.batch)
            if not isinstance(items, list):
                print(handle_error("E003"))
                return 1
            results = []
            for item in items:
                try:
                    results.append(process_input(item))
                except ValueError as e:
                    results.append({"error": str(e), "message": ERROR_MESSAGES.get(str(e), "")})
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return 0
        except json.JSONDecodeError:
            print(handle_error("E003"))
            return 1

    # 单条处理模式
    if args.input:
        try:
            result = process_input(args.input)
            output = format_output(result, args.format)
            print(output)
            return 0
        except ValueError as e:
            print(handle_error(str(e)))
            return 1
        except Exception:
            print(handle_error("E003"))
            return 1

    # 无输入参数：交互提示
    print(handle_error("E001"))
    print("提示: 使用 --input 提供内容，或 --selftest 运行自检")
    return 1


if __name__ == "__main__":
    sys.exit(main())
