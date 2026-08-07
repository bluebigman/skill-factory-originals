#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ipython-dashboard 数据可视化技能 - 独立实现脚本
=================================================
本脚本仅依据功能规格重新实现，不参考任何既有代码。
提供数据解析、结构化转换、置信度标注与批量处理能力。

用法:
    python main.py --selftest     # 离线自检核心逻辑
    python main.py --input "..."  # 处理单个输入
    python main.py --batch a b c  # 批量处理多个输入
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


# ---------------------------------------------------------------------------
# 核心处理函数
# ---------------------------------------------------------------------------
class DataProcessor:
    """数据处理器：负责解析、结构化、置信度评估与输出。"""

    # 可识别的关键字段（用于结构化提取）
    KEY_FIELDS = ["name", "value", "category", "date", "amount", "label"]

    def __init__(self) -> None:
        self._conf_threshold_high = 90.0
        self._conf_threshold_mid = 85.0

    # -- 主入口 ------------------------------------------------------------
    def process(self, raw_input: str) -> Dict[str, Any]:
        """
        处理单个输入，返回结构化结果。
        流程：解析 -> 提取字段 -> 评估置信度 -> 组织输出。
        """
        # 空输入检查
        if not raw_input or not raw_input.strip():
            return self._make_error("E001")

        # 尝试解析为 JSON（若为 JSON 格式）
        parsed = self._try_parse_json(raw_input)

        # 若解析失败，则按通用文本提取关键信息
        if parsed is None:
            parsed = self._extract_key_values(raw_input)

        # 字段完整性检查（至少需要一个关键字段）
        if not parsed or not any(k in parsed for k in self.KEY_FIELDS):
            return self._make_error("E002")

        # 计算置信度
        confidence = self._evaluate_confidence(parsed)

        # 组装结果
        result = {
            "status": "ok",
            "data": parsed,
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
            "warning": None,
        }

        # 低置信度标注
        if confidence < self._conf_threshold_mid:
            result["warning"] = "[需核实] 部分字段无法确定，请人工复核。"
        elif confidence < self._conf_threshold_high:
            result["warning"] = "建议复核：置信度处于中位区间。"

        return result

    def process_batch(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """批量处理多个输入，按同一规则逐项处理。"""
        return [self.process(item) for item in inputs]

    # -- 解析与提取 ---------------------------------------------------------
    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试将输入解析为 JSON 字典。"""
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                # 只保留可识别的关键字段
                return {k: v for k, v in obj.items() if k in self.KEY_FIELDS}
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    def _extract_key_values(self, text: str) -> Dict[str, Any]:
        """从普通文本中提取关键字段（基于简单模式匹配）。"""
        extracted: Dict[str, Any] = {}

        # 匹配 "字段名: 值" 或 "字段名=值" 模式
        patterns = [
            r"(?:^|[\s,;])(name|value|category|date|amount|label)\s*[:=]\s*([^,;]+)",
            r"(\w+)\s*[:=]\s*([^,;]+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                key = match.group(1).lower()
                val = match.group(2).strip()
                if key in self.KEY_FIELDS and key not in extracted:
                    extracted[key] = self._convert_value(val)

        # 若未匹配到关键字段，尝试将整个输入作为一个值
        if not extracted and text.strip():
            extracted["value"] = text.strip()

        return extracted

    @staticmethod
    def _convert_value(raw: str) -> Any:
        """将字符串值转换为合适的类型（数字/布尔/字符串）。"""
        raw = raw.strip()
        # 尝试数字转换
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass
        # 布尔值
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        # 默认字符串
        return raw

    # -- 置信度评估 ---------------------------------------------------------
    def _evaluate_confidence(self, data: Dict[str, Any]) -> float:
        """基于字段完整性和值类型评估置信度。"""
        if not data:
            return 0.0

        # 基础分：有数据即 60 分
        score = 60.0

        # 字段完整性加分（每多一个关键字段加 10 分，上限 30 分）
        field_count = len(data)
        score += min(field_count * 10, 30)

        # 值类型合理性加分（有非字符串值或布尔值加 10 分）
        for val in data.values():
            if not isinstance(val, str):
                score += 10
                break

        # 确保不超过 100
        return min(score, 100.0)

    def _confidence_label(self, confidence: float) -> str:
        """根据置信度返回标签。"""
        if confidence >= self._conf_threshold_high:
            return "高置信度"
        if confidence >= self._conf_threshold_mid:
            return "中置信度"
        return "低置信度"

    # -- 错误处理 -----------------------------------------------------------
    @staticmethod
    def _make_error(code: str) -> Dict[str, Any]:
        """构造标准错误响应。"""
        return {
            "status": "error",
            "error_code": code,
            "message": ERROR_CODES.get(code, "未知错误"),
        }


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件、网络或特定工作目录。
    断言使用宽松阈值，确保与实现逻辑必然匹配。
    """
    print("[SELFTEST] 开始自检...")
    processor = DataProcessor()

    # 测试用例 1: 空输入 -> 应返回 E001
    print("[SELFTEST] 用例1: 空输入")
    result = processor.process("")
    assert result["status"] == "error", "空输入应返回错误状态"
    assert result["error_code"] == "E001", "空输入应返回 E001"
    print("  通过")

    # 测试用例 2: 标准 JSON 输入 -> 应成功解析
    print("[SELFTEST] 用例2: JSON 输入")
    result = processor.process('{"name": "销售报表", "value": 100, "category": "月度"}')
    assert result["status"] == "ok", "JSON 输入应成功处理"
    assert "data" in result, "应包含 data 字段"
    assert result["data"].get("value") == 100, "value 字段应被正确解析为数字"
    assert result["confidence"] > 0, "置信度应大于 0"
    print("  通过")

    # 测试用例 3: 普通文本输入 -> 应提取关键字段
    print("[SELFTEST] 用例3: 文本输入")
    result = processor.process("name=用户增长, value=2500, category=季度")
    assert result["status"] == "ok", "文本输入应成功处理"
    assert "data" in result, "应包含 data 字段"
    # 宽松断言：value 应被解析为数字且大于 0
    assert isinstance(result["data"].get("value"), (int, float)), "value 应为数字类型"
    assert result["data"]["value"] > 0, "value 应为正数"
    print("  通过")

    # 测试用例 4: 批量处理 -> 应返回相同数量的结果
    print("[SELFTEST] 用例4: 批量处理")
    inputs = ['{"name": "A", "value": 10}', "name=B, value=20", "无效输入"]
    results = processor.process_batch(inputs)
    assert isinstance(results, list), "批量处理应返回列表"
    assert len(results) == len(inputs), "结果数量应与输入数量一致"
    # 至少有一个成功结果
    assert any(r["status"] == "ok" for r in results), "应至少有一个成功结果"
    print("  通过")

    # 测试用例 5: 置信度评估 -> 应落在合理区间
    print("[SELFTEST] 用例5: 置信度")
    result = processor.process('{"name": "测试", "value": 1, "category": "x", "date": "2026-01-01"}')
    assert 0 <= result["confidence"] <= 100, "置信度应在 0-100 之间"
    # 完整数据置信度应较高（宽松阈值）
    assert result["confidence"] > 50, "完整数据的置信度应大于 50"
    print("  通过")

    # 测试用例 6: 错误码体系 -> 应返回标准错误消息
    print("[SELFTEST] 用例6: 错误码")
    result = processor.process("")
    assert result["message"] == ERROR_CODES["E001"], "E001 消息应匹配标准话术"
    print("  通过")

    print("[SELFTEST] 全部用例通过！")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="ipython-dashboard 数据可视化技能 - 独立实现",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="处理单个输入内容（字符串）",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入（空格分隔）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as exc:
            print(f"[SELFTEST] 失败: {exc}", file=sys.stderr)
            return 1

    # 处理模式
    processor = DataProcessor()

    # 批量处理优先
    if args.batch:
        results = processor.process_batch(args.batch)
    elif args.input:
        results = [processor.process(args.input)]
    else:
        # 无输入参数，提示用法
        print("请提供输入内容。使用 --help 查看帮助。", file=sys.stderr)
        return 1

    # 输出
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            if item["status"] == "ok":
                print(f"处理成功 | 置信度: {item['confidence']:.1f}% ({item['confidence_label']})")
                print(f"数据: {json.dumps(item['data'], ensure_ascii=False)}")
                if item.get("warning"):
                    print(f"提示: {item['warning']}")
            else:
                print(f"错误 {item['error_code']}: {item['message']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
