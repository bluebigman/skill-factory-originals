#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
股票预测与推荐（数据可视化）技能的独立实现脚本。

本脚本仅依据功能规格进行全新编写（clean-room），不包含任何既有代码。
遵循规格中的能力边界：不访问网络、不读取外部文件（除用户显式传入外）、
不保证绝对准确，低置信度时给出标注。

错误码约定：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部计算异常（数据无效）
    E007: 命令行参数错误
    E008: 输出写入失败
    E009: 未知错误
    E010: 自检断言失败（仅用于 --selftest）
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 版本与元数据（对应规格中的元数据）
SKILL_NAME = "stock-prediction-and-recommendation"
DISPLAY_NAME = "数据可视化"
VERSION = "1.0.0"
AUTHOR = "skill-factory-auto"
LICENSE = "MIT"

# 置信度阈值（对应规格中的置信度规则）
CONFIDENCE_HIGH = 90.0    # >=90 直接输出
CONFIDENCE_MEDIUM = 85.0  # 85-90 建议复核
# <85 标注 [需核实]

# 输出字段的默认模板（对应规格 Step 2 中的"按默认模板组织输出"）
DEFAULT_OUTPUT_FIELDS = [
    "symbol",       # 股票代码
    "name",         # 名称
    "latest_price", # 最新价
    "trend",        # 趋势判断（up/down/flat）
    "confidence",   # 置信度（0-100）
    "suggestion",   # 建议（buy/hold/sell）
    "note",         # 备注（如 [需核实]）
]


class StockAnalyzer:
    """核心分析引擎：对输入数据进行结构化处理、趋势判断与建议生成。"""

    def __init__(self) -> None:
        # 内部状态：记录最近一次分析的原始输入与结果
        self._last_input: Optional[Dict[str, Any]] = None
        self._last_result: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 对外主入口：处理输入并返回结构化结果（对应规格 Step 2）
    # ------------------------------------------------------------------
    def process(self, raw_input: Any) -> Dict[str, Any]:
        """
        接收用户输入（数据/文件路径/URL 字符串），返回结构化结果字典。

        参数 raw_input 可以是：
            - 字符串：可能是文件路径、URL、或 JSON 文本
            - 字典/列表：已解析的结构化数据
            - 其他：尝试转为字典

        返回结果包含：
            - status: "success" 或 "error"
            - error_code: 仅当 status=="error" 时存在（E001-E010）
            - message: 人类可读信息
            - data: 结构化输出（成功时）
        """
        try:
            # 空输入检查（E001）
            if raw_input is None:
                return self._make_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

            # 解析输入为统一格式
            parsed = self._parse_input(raw_input)
            if isinstance(parsed, dict) and "error_code" in parsed:
                return parsed  # 解析失败，直接返回错误

            # 提取关键信息（对应规格 Step 1 的最小信息集）
            # 这里我们要求至少包含 symbol 和价格序列，否则报 E002/E003
            required_keys = ["symbol", "prices"]
            missing = [k for k in required_keys if k not in parsed]
            if missing:
                return self._make_error(
                    "E002",
                    f"还缺少以下信息，请补充：{', '.join(missing)}（示例：{{'symbol': 'AAPL', 'prices': [100, 101, 102]}}）",
                )

            # 校验价格序列格式（E003）
            prices = parsed["prices"]
            if not isinstance(prices, list) or len(prices) < 2:
                return self._make_error(
                    "E003",
                    "输入格式不符合要求，示例：{'symbol': 'AAPL', 'prices': [100, 101, 102]}（至少需要2个价格点）",
                )
            for p in prices:
                if not isinstance(p, (int, float)) or p <= 0:
                    return self._make_error(
                        "E003",
                        f"价格序列包含无效值：{p}。价格必须为正数。",
                    )

            # 执行核心分析
            result = self._analyze(parsed)
            if isinstance(result, dict) and "error_code" in result:
                return result

            # 记录最近一次输入与结果（供内部使用）
            self._last_input = parsed
            self._last_result = result

            # 组装成功响应
            return {
                "status": "success",
                "message": "处理完成",
                "data": result,
                "skill": SKILL_NAME,
                "version": VERSION,
            }

        except Exception as exc:  # 兜底异常（E009）
            return self._make_error("E009", f"发生未知错误：{exc}")

    # ------------------------------------------------------------------
    # 输入解析：字符串/字典/文件路径/URL 统一转为字典
    # ------------------------------------------------------------------
    def _parse_input(self, raw: Any) -> Union[Dict[str, Any], Dict[str, str]]:
        """
        将各种输入形式转为内部统一字典格式。
        成功返回数据字典；失败返回含 "error_code" 的错误字典。
        """
        # 情况1：已经是字典
        if isinstance(raw, dict):
            return raw

        # 情况2：列表 → 尝试按 [symbol, [prices]] 或 [prices] 解释
        if isinstance(raw, list):
            try:
                if len(raw) == 2 and isinstance(raw[0], str) and isinstance(raw[1], list):
                    return {"symbol": raw[0], "prices": raw[1]}
                if len(raw) >= 2 and all(isinstance(i, (int, float)) for i in raw):
                    return {"symbol": "UNKNOWN", "prices": raw}
            except Exception:
                pass
            return self._make_error("E003", "列表格式无法识别，示例：['AAPL', [100, 101]]")

        # 情况3：字符串 → 尝试 JSON 解析，否则视为文件路径或 URL
        if isinstance(raw, str):
            # 先尝试 JSON
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    return self._parse_input(data)  # 递归处理
            except json.JSONDecodeError:
                pass  # 不是 JSON

            # 尝试作为文件路径（仅当文件存在时读取，否则视为 URL/普通字符串）
            if os.path.isfile(raw):
                try:
                    with open(raw, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 尝试将文件内容解析为 JSON
                    data = json.loads(content)
                    if isinstance(data, dict):
                        return data
                    if isinstance(data, list):
                        return self._parse_input(data)
                    return self._make_error("E003", "文件内容不是有效的 JSON 对象或数组")
                except json.JSONDecodeError:
                    return self._make_error("E003", f"文件 {raw} 内容不是有效 JSON")
                except OSError as exc:
                    return self._make_error("E008", f"无法读取文件：{exc}")

            # 尝试将整个字符串视为单个 symbol（无价格数据）
            if raw.strip():
                # 检查是否包含价格数据（如 "AAPL 100 101 102"）
                parts = raw.strip().split()
                if len(parts) >= 2 and all(p.replace(".", "", 1).isdigit() for p in parts[1:]):
                    try:
                        prices = [float(p) for p in parts[1:]]
                        return {"symbol": parts[0], "prices": prices}
                    except ValueError:
                        pass
                # 否则视为 URL 或纯文本（超出能力边界 E004）
                return self._make_error(
                    "E004",
                    f"这超出了本工具的能力范围。输入 '{raw[:50]}...' 无法识别为有效的股票数据。"
                    "请提供格式如：{'symbol': 'AAPL', 'prices': [100, 101, 102]} 或 'AAPL 100 101'",
                )

            return self._make_error("E001", "输入为空")

        # 其他类型
        return self._make_error("E003", f"不支持的输入类型：{type(raw).__name__}")

    # ------------------------------------------------------------------
    # 核心分析逻辑（对应规格 Step 2 的处理规则）
    # ------------------------------------------------------------------
    def _analyze(self, data: Dict[str, Any]) -> Union[Dict[str, Any], Dict[str, str]]:
        """根据输入数据计算趋势、置信度与建议。"""
        symbol = data["symbol"]
        prices = data["prices"]

        try:
            # 基本统计
            latest_price = prices[-1]
            first_price = prices[0]
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)

            # 简单趋势判断：比较首尾价格
            change_ratio = (latest_price - first_price) / first_price if first_price else 0

            # 趋势方向
            if change_ratio > 0.01:  # 涨幅超过1%
                trend = "up"
            elif change_ratio < -0.01:  # 跌幅超过1%
                trend = "down"
            else:
                trend = "flat"

            # 计算波动率（标准差）用于置信度评估
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = math.sqrt(variance)
            volatility = std_dev / avg_price if avg_price else 0

            # 置信度计算（基于数据点数量和波动率）
            # 规则：数据点越多置信度越高；波动率越低置信度越高
            confidence = 70.0  # 基础值
            confidence += min(len(prices) * 2.0, 20.0)  # 每个数据点+2，最多+20
            confidence -= min(volatility * 50.0, 15.0)  # 高波动降低置信度
            confidence = max(0.0, min(100.0, confidence))  # 限制在0-100

            # 建议生成（基于趋势与置信度）
            if trend == "up" and confidence >= CONFIDENCE_MEDIUM:
                suggestion = "buy"
            elif trend == "down" and confidence >= CONFIDENCE_MEDIUM:
                suggestion = "sell"
            else:
                suggestion = "hold"

            # 备注（置信度标注）
            note = ""
            if confidence < CONFIDENCE_MEDIUM:
                note = "[需核实] 数据不足或波动过大，结果仅供参考"
            elif confidence < CONFIDENCE_HIGH:
                note = "建议复核"

            # 组装结果
            result = {
                "symbol": symbol,
                "name": data.get("name", symbol),  # 可选字段
                "latest_price": round(latest_price, 4),
                "first_price": round(first_price, 4),
                "avg_price": round(avg_price, 4),
                "max_price": round(max_price, 4),
                "min_price": round(min_price, 4),
                "change_ratio": round(change_ratio, 6),
                "trend": trend,
                "confidence": round(confidence, 2),
                "suggestion": suggestion,
                "note": note,
                "data_points": len(prices),
            }
            return result

        except ZeroDivisionError:
            return self._make_error("E006", "数据无效：价格序列包含零或空值")
        except Exception as exc:
            return self._make_error("E006", f"内部计算异常：{exc}")

    # ------------------------------------------------------------------
    # 输出格式化（对应规格 Step 3）
    # ------------------------------------------------------------------
    def format_output(self, result: Dict[str, Any], output_format: str = "json") -> str:
        """将分析结果格式化为 JSON / 文本 / 表格。"""
        if result.get("status") == "error":
            return json.dumps(result, ensure_ascii=False, indent=2)

        data = result.get("data", {})
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif output_format == "text":
            lines = [
                f"股票代码: {data.get('symbol', 'N/A')}",
                f"名称: {data.get('name', 'N/A')}",
                f"最新价: {data.get('latest_price', 'N/A')}",
                f"趋势: {data.get('trend', 'N/A')}",
                f"置信度: {data.get('confidence', 'N/A')}%",
                f"建议: {data.get('suggestion', 'N/A')}",
            ]
            if data.get("note"):
                lines.append(f"备注: {data['note']}")
            return "\n".join(lines)
        elif output_format == "table":
            # 简单表格输出
            headers = ["字段", "值"]
            rows = [
                ("股票代码", data.get("symbol", "")),
                ("名称", data.get("name", "")),
                ("最新价", str(data.get("latest_price", ""))),
                ("趋势", data.get("trend", "")),
                ("置信度", f"{data.get('confidence', '')}%"),
                ("建议", data.get("suggestion", "")),
            ]
            if data.get("note"):
                rows.append(("备注", data["note"]))
            # 计算列宽
            col1_w = max(len(str(r[0])) for r in rows + [headers[0]])
            col2_w = max(len(str(r[1])) for r in rows + [headers[1]])
            sep = "+" + "-" * (col1_w + 2) + "+" + "-" * (col2_w + 2) + "+"
            lines = [sep]
            lines.append(f"| {headers[0]:<{col1_w}} | {headers[1]:<{col2_w}} |")
            lines.append(sep)
            for r in rows:
                lines.append(f"| {str(r[0]):<{col1_w}} | {str(r[1]):<{col2_w}} |")
            lines.append(sep)
            return "\n".join(lines)
        else:
            return json.dumps(result, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _make_error(code: str, message: str) -> Dict[str, str]:
        """构造标准错误响应。"""
        return {"status": "error", "error_code": code, "message": message}

    # ------------------------------------------------------------------
    # 自检（--selftest）
    # ------------------------------------------------------------------
    def selftest(self) -> bool:
        """
        离线自检核心逻辑。使用内置硬编码样例数据，不依赖外部文件/网络。
        返回 True 表示全部通过，否则抛异常或返回 False。
        """
        print("[SELFTEST] 开始自检...")
        all_ok = True

        # 测试用例1：正常上涨数据
        test1 = {"symbol": "TEST1", "prices": [100, 101, 102, 103, 104, 105]}
        try:
            result1 = self.process(test1)
            assert result1["status"] == "success", "测试1失败：状态不是 success"
            data1 = result1["data"]
            # 宽松断言：趋势应为 up，置信度应 > 80
            assert data1["trend"] == "up", f"测试1失败：趋势应为 up，实际 {data1['trend']}"
            assert data1["confidence"] > 80, f"测试1失败：置信度应 > 80，实际 {data1['confidence']}"
            assert data1["suggestion"] in ("buy", "hold"), "测试1失败：建议应为 buy 或 hold"
            assert data1["latest_price"] > data1["first_price"], "测试1失败：最新价应大于首价"
            print("  用例1（上涨趋势）: PASS")
        except AssertionError as e:
            print(f"  用例1（上涨趋势）: FAIL - {e}")
            all_ok = False

        # 测试用例2：下跌数据
        test2 = {"symbol": "TEST2", "prices": [200, 190, 180, 170]}
        try:
            result2 = self.process(test2)
            assert result2["status"] == "success", "测试2失败：状态不是 success"
            data2 = result2["data"]
            assert data2["trend"] == "down", f"测试2失败：趋势应为 down，实际 {data2['trend']}"
            assert data2["latest_price"] < data2["first_price"], "测试2失败：最新价应小于首价"
            print("  用例2（下跌趋势）: PASS")
        except AssertionError as e:
            print(f"  用例2（下跌趋势）: FAIL - {e}")
            all_ok = False

        # 测试用例3：空输入 → E001
        try:
            result3 = self.process(None)
            assert result3["status"] == "error", "测试3失败：应返回错误"
            assert result3["error_code"] == "E001", f"测试3失败：错误码应为 E001，实际 {result3.get('error_code')}"
            print("  用例3（空输入 E001）: PASS")
        except AssertionError as e:
            print(f"  用例3（空输入 E001）: FAIL - {e}")
            all_ok = False

        # 测试用例4：缺失关键信息 → E002
        try:
            result4 = self.process({"symbol": "TEST4"})  # 缺少 prices
            assert result4["status"] == "error", "测试4失败：应返回错误"
            assert result4["error_code"] == "E002", f"测试4失败：错误码应为 E002，实际 {result4.get('error_code')}"
            print("  用例4（缺失信息 E002）: PASS")
        except AssertionError as e:
            print(f"  用例4（缺失信息 E002）: FAIL - {e}")
            all_ok = False

        # 测试用例5：格式错误（价格非正数）→ E003
        try:
            result5 = self.process({"symbol": "TEST5", "prices": [100, -5]})
            assert result5["status"] == "error", "测试5失败：应返回错误"
            assert result5["error_code"] == "E003", f"测试5失败：错误码应为 E003，实际 {result5.get('error_code')}"
            print("  用例5（格式错误 E003）: PASS")
        except AssertionError as e:
            print(f"  用例5（格式错误 E003）: FAIL - {e}")
            all_ok = False

        # 测试用例6：字符串输入（JSON）
        try:
            json_str = '{"symbol": "TEST6", "prices": [50, 55, 60]}'
            result6 = self.process(json_str)
            assert result6["status"] == "success", "测试6失败：状态不是 success"
            assert result6["data"]["symbol"] == "TEST6", "测试6失败：symbol 不匹配"
            print("  用例6（JSON字符串）: PASS")
        except AssertionError as e:
            print(f"  用例6（JSON字符串）: FAIL - {e}")
            all_ok = False

        # 测试用例7：低置信度标注
        try:
            # 只有2个数据点且波动大 → 置信度应较低
            result7 = self.process({"symbol": "TEST7", "prices": [100, 200]})
            assert result7["status"] == "success", "测试7失败：状态不是 success"
            data7 = result7["data"]
            # 置信度应 < 85（因为数据点少）
            assert data7["confidence"] < 85, f"测试7失败：置信度应 < 85，实际 {data7['confidence']}"
            assert "[需核实]" in data7["note"] or "建议复核" in data7["note"], "测试7失败：应有低置信度标注"
            print("  用例7（低置信度标注）: PASS")
        except AssertionError as e:
            print(f"  用例7（低置信度标注）: FAIL - {e}")
            all_ok = False

        # 测试用例8：输出格式化（text 格式）
        try:
            result8 = self.process({"symbol": "TEST8", "prices": [10, 12, 11, 13]})
            text_out = self.format_output(result8, "text")
            assert "股票代码" in text_out, "测试8失败：text 输出缺少股票代码"
            assert "TEST8" in text_out, "测试8失败：text 输出缺少 symbol"
            print("  用例8（文本格式化）: PASS")
        except AssertionError as e:
            print(f"  用例8（文本格式化）: FAIL - {e}")
            all_ok = False

        # 测试用例9：表格格式化
        try:
            result9 = self.process({"symbol": "TEST9", "prices": [100, 110, 120]})
            table_out = self.format_output(result9, "table")
            assert "|" in table_out, "测试9失败：表格输出缺少竖线分隔"
            print("  用例9（表格格式化）: PASS")
        except AssertionError as e:
            print(f"  用例9（表格格式化）: FAIL - {e}")
            all_ok = False

        # 测试用例10：超出能力边界（无法识别的字符串）→ E004
        try:
            result10 = self.process("this is not stock data at all")
            assert result10["status"] == "error", "测试10失败：应返回错误"
            assert result10["error_code"] == "E004", f"测试10失败：错误码应为 E004，实际 {result10.get('error_code')}"
            print("  用例10（超出边界 E004）: PASS")
        except AssertionError as e:
            print(f"  用例10（超出边界 E004）: FAIL - {e}")
            all_ok = False

        if all_ok:
            print("[SELFTEST] 全部通过 ✔")
        else:
            print("[SELFTEST] 存在失败用例 ✘")
            return False
        return True


# ----------------------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------------------
def main() -> int:
    """命令行主函数。返回进程退出码（0成功，非0失败）。"""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=f"{DISPLAY_NAME} - 股票数据分析与预测工具（{SKILL_NAME} v{VERSION}）",
        epilog="示例：python main.py --input '{\"symbol\": \"AAPL\", \"prices\": [100, 101, 102]}' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据：JSON字符串、文件路径、或 'SYMBOL price1 price2...' 格式",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "table"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检，不读取外部数据",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SKILL_NAME} v{VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        analyzer = StockAnalyzer()
        ok = analyzer.selftest()
        return 0 if ok else 1

    # 需要输入数据
    if not args.input:
        parser.print_help()
        print("\n错误: 需要提供 --input 参数（或使用 --selftest 自检）", file=sys.stderr)
        return 1

    # 处理输入
    analyzer = StockAnalyzer()
    result = analyzer.process(args.input)

    # 输出结果
    output = analyzer.format_output(result, args.format)
    print(output)

    # 错误时返回非零退出码
    if result.get("status") == "error":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
