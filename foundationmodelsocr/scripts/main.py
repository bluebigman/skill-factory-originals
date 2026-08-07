#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
发票识别 (foundationmodelsocr) - 独立实现

本脚本根据功能规格实现发票识别核心逻辑。
仅依赖 Python 标准库，无第三方依赖。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "批量处理中断",
    "E009": "输出序列化失败",
    "E010": "未知错误",
}


class InvoiceError(Exception):
    """发票处理异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class InvoiceField:
    """发票字段定义。"""

    # 必填字段（关键信息）
    REQUIRED_FIELDS = [
        "invoice_number",   # 发票号码
        "date",             # 开票日期
        "amount",           # 金额
    ]

    # 可选字段
    OPTIONAL_FIELDS = [
        "seller_name",      # 销售方名称
        "buyer_name",       # 购买方名称
        "tax_number",       # 税号
        "items",            # 商品明细
    ]

    ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS


# ---------------------------------------------------------------------------
# 核心识别逻辑
# ---------------------------------------------------------------------------
class InvoiceParser:
    """发票解析器：从文本中提取结构化信息。"""

    # 常用字段的正则模式（宽松匹配）
    PATTERNS = {
        "invoice_number": [
            r"(?:发票号码|发票号|NO\.?|No\.?)[:：\s]*([A-Za-z0-9\-]{6,})",
            r"(?:invoice\s*(?:number|no\.?))[:：\s]*([A-Za-z0-9\-]{6,})",
        ],
        "date": [
            r"(?:开票日期|日期|date)[:：\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
            r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        ],
        "amount": [
            r"(?:金额|合计|总计|amount|total)[:：\s]*[¥￥$]\s*([0-9]+(?:\.[0-9]{1,2})?)",
            r"[¥￥$]\s*([0-9]+(?:\.[0-9]{1,2})?)",
            r"(?:金额|合计|总计|amount|total)[:：\s]*([0-9]+(?:\.[0-9]{1,2})?)",
        ],
        "seller_name": [
            r"(?:销售方|销方|seller)[:：\s]*([^\n]{2,50})",
        ],
        "buyer_name": [
            r"(?:购买方|购方|buyer)[:：\s]*([^\n]{2,50})",
        ],
        "tax_number": [
            r"(?:税号|纳税人识别号|tax\s*(?:id|number))[:：\s]*([0-9A-Z]{15,20})",
        ],
    }

    def __init__(self, text: str):
        """初始化解析器。

        Args:
            text: 输入文本内容。

        Raises:
            InvoiceError: 输入为空时抛出 E001。
        """
        if not text or not text.strip():
            raise InvoiceError("E001")
        self.text = text.strip()
        self.fields: Dict[str, Any] = {}
        self.confidences: Dict[str, float] = {}

    def parse(self) -> Dict[str, Any]:
        """执行解析，返回结构化结果。

        Returns:
            Dict: 包含 fields、confidences、summary 的结果字典。
        """
        # 逐字段匹配
        for field, patterns in self.PATTERNS.items():
            match_result = self._match_field(field, patterns)
            if match_result:
                self.fields[field], self.confidences[field] = match_result

        # 尝试提取商品明细（简单按行拆分）
        self._extract_items()

        # 计算整体置信度
        overall_conf = self._calculate_overall_confidence()

        # 检查必填字段
        missing = [f for f in InvoiceField.REQUIRED_FIELDS if f not in self.fields]
        if missing:
            raise InvoiceError(
                "E002", f"缺少关键字段: {', '.join(missing)}"
            )

        # 构造结果
        result = {
            "fields": self.fields,
            "confidences": self.confidences,
            "overall_confidence": overall_conf,
            "needs_review": overall_conf < 0.85,
            "warning": self._build_warning(overall_conf),
        }
        return result

    def _match_field(self, field: str, patterns: List[str]) -> Optional[Tuple[str, float]]:
        """尝试用多个模式匹配字段。

        Returns:
            (值, 置信度) 元组，未匹配返回 None。
        """
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # 置信度基于匹配长度与模式复杂度（宽松估计）
                conf = min(0.95, 0.75 + len(value) / 100)
                return value, conf
        return None

    def _extract_items(self) -> None:
        """从文本中提取可能的商品明细行（启发式）。"""
        items = []
        lines = self.text.split("\n")
        for line in lines:
            line = line.strip()
            # 简单启发：包含数量与价格的短行
            if re.search(r"\d+\s*[xX*]\s*\d", line) or re.search(r"\d+\.\d{2}", line):
                if 3 < len(line) < 80:
                    items.append(line)
        if items:
            self.fields["items"] = items[:10]  # 最多保留 10 条
            self.confidences["items"] = 0.7

    def _calculate_overall_confidence(self) -> float:
        """计算整体置信度（加权平均）。"""
        if not self.confidences:
            return 0.0
        # 必填字段权重更高
        weights = []
        values = []
        for field, conf in self.confidences.items():
            w = 2.0 if field in InvoiceField.REQUIRED_FIELDS else 1.0
            weights.append(w)
            values.append(conf)
        total_w = sum(weights)
        return sum(v * w for v, w in zip(values, weights)) / total_w

    def _build_warning(self, conf: float) -> str:
        """根据置信度生成警告信息。"""
        if conf >= 0.9:
            return ""
        if conf >= 0.85:
            return "建议复核"
        return "[需核实] 置信度过低，请人工核对关键字段"


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------
def process_batch(inputs: List[str]) -> List[Dict[str, Any]]:
    """批量处理多个输入。

    Args:
        inputs: 输入文本列表。

    Returns:
        List[Dict]: 每个输入的处理结果。
    """
    results = []
    for idx, text in enumerate(inputs):
        try:
            parser = InvoiceParser(text)
            result = parser.parse()
            result["index"] = idx
            results.append(result)
        except InvoiceError as e:
            results.append({
                "index": idx,
                "error": e.code,
                "message": e.message,
            })
        except Exception as e:
            results.append({
                "index": idx,
                "error": "E006",
                "message": f"内部处理错误: {str(e)}",
            })
    return results


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
def format_output(result: Dict[str, Any], fmt: str = "json") -> str:
    """将结果格式化为指定格式。

    Args:
        result: 解析结果字典。
        fmt: 输出格式，支持 json / text。

    Returns:
        str: 格式化后的字符串。

    Raises:
        InvoiceError: 不支持的格式时抛出 E003。
    """
    try:
        if fmt == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif fmt == "text":
            return _format_text(result)
        else:
            raise InvoiceError("E003", f"不支持的输出格式: {fmt}")
    except InvoiceError:
        raise
    except Exception as e:
        raise InvoiceError("E009", f"输出序列化失败: {str(e)}")


def _format_text(result: Dict[str, Any]) -> str:
    """格式化为纯文本。"""
    lines = []
    if "error" in result:
        lines.append(f"错误 [{result['error']}]: {result['message']}")
        return "\n".join(lines)

    fields = result.get("fields", {})
    lines.append("=== 发票识别结果 ===")
    for key, value in fields.items():
        if isinstance(value, list):
            lines.append(f"{key}: {', '.join(map(str, value))}")
        else:
            lines.append(f"{key}: {value}")

    conf = result.get("overall_confidence", 0)
    lines.append(f"--- 置信度: {conf:.0%} ---")
    warning = result.get("warning", "")
    if warning:
        lines.append(f"提示: {warning}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检测试（硬编码样例）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检。

    使用硬编码样例数据离线验证核心逻辑。
    不读取外部文件，不依赖当前工作目录，不访问网络。

    Returns:
        bool: 自检是否通过。
    """
    print("[自检] 开始...")

    # 样例 1: 完整发票文本
    sample1 = """
    电子发票
    发票号码: INV2026001
    开票日期: 2026年1月15日
    销售方: 北京示例科技有限公司
    购买方: 上海测试有限公司
    税号: 91110000MA01XXXXX
    金额: ¥1234.56
    商品明细:
    1x 办公用品 800.00
    2x 打印纸 434.56
    """

    # 样例 2: 简略文本（英文）
    sample2 = """
    Invoice No.: INV-2026-002
    Date: 2026-02-01
    Total: $99.99
    Seller: Example Corp
    """

    # 样例 3: 错误输入（空文本）
    sample3 = ""

    # 测试 1: 完整解析
    try:
        parser = InvoiceParser(sample1)
        result1 = parser.parse()
        fields1 = result1["fields"]

        # 宽松断言：关键字段存在且非空
        assert fields1.get("invoice_number"), "发票号码缺失"
        assert fields1.get("date"), "日期缺失"
        assert fields1.get("amount"), "金额缺失"

        # 数值合理性检查（宽松阈值）
        amount = float(fields1["amount"])
        assert 0 < amount < 100000, f"金额异常: {amount}"

        # 置信度检查（宽松阈值）
        conf1 = result1["overall_confidence"]
        assert conf1 > 0.5, f"置信度过低: {conf1}"

        print(f"  [通过] 样例1 完整解析, 置信度={conf1:.0%}")
    except AssertionError as e:
        print(f"  [失败] 样例1: {e}")
        return False
    except InvoiceError as e:
        print(f"  [失败] 样例1: {e}")
        return False

    # 测试 2: 英文简略文本
    try:
        parser = InvoiceParser(sample2)
        result2 = parser.parse()
        fields2 = result2["fields"]

        assert fields2.get("invoice_number"), "发票号码缺失"
        assert fields2.get("date"), "日期缺失"
        assert fields2.get("amount"), "金额缺失"

        conf2 = result2["overall_confidence"]
        assert conf2 > 0.4, f"置信度过低: {conf2}"

        print(f"  [通过] 样例2 英文解析, 置信度={conf2:.0%}")
    except AssertionError as e:
        print(f"  [失败] 样例2: {e}")
        return False
    except InvoiceError as e:
        print(f"  [失败] 样例2: {e}")
        return False

    # 测试 3: 空输入应报 E001
    try:
        InvoiceParser(sample3)
        print("  [失败] 样例3: 空输入未报错")
        return False
    except InvoiceError as e:
        assert e.code == "E001", f"错误码错误: {e.code}"
        print("  [通过] 样例3 空输入错误处理")

    # 测试 4: 批量处理
    try:
        batch_results = process_batch([sample1, sample2, sample3])
        assert len(batch_results) == 3, "批量结果数量错误"
        assert "error" in batch_results[2], "第三条应包含错误"
        assert batch_results[2]["error"] == "E001", "错误码不匹配"
        print("  [通过] 样例4 批量处理")

    except AssertionError as e:
        print(f"  [失败] 样例4: {e}")
        return False

    # 测试 5: 输出格式化
    try:
        parser = InvoiceParser(sample1)
        result = parser.parse()
        json_out = format_output(result, "json")
        assert json_out.startswith("{"), "JSON 输出格式错误"
        text_out = format_output(result, "text")
        assert "发票识别结果" in text_out, "文本输出格式错误"
        print("  [通过] 样例5 输出格式化")

        # 测试不支持格式
        try:
            format_output(result, "xml")
            print("  [失败] 样例5: 不支持的格式未报错")
            return False
        except InvoiceError as e:
            assert e.code == "E003", f"错误码错误: {e.code}"
            print("  [通过] 样例5 不支持格式错误处理")

    except AssertionError as e:
        print(f"  [失败] 样例5: {e}")
        return False
    except InvoiceError as e:
        print(f"  [失败] 样例5: {e}")
        return False

    print("[自检] 全部通过 ✓")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="发票识别 (foundationmodelsocr) - 从文本中提取结构化发票信息"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="待处理的文本内容（直接传入）或文件路径（配合 --file）",
    )
    parser.add_argument(
        "--file",
        action="store_true",
        help="将第一个参数视为文件路径，读取文件内容",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部输入）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式：逐行读取标准输入作为多个输入",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 校验输入
    if not args.input and not args.batch:
        print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请提供输入内容，或使用 --selftest 运行自检。", file=sys.stderr)
        return 1

    # 批量模式：从标准输入读取
    if args.batch:
        inputs = []
        for line in sys.stdin:
            line = line.strip()
            if line:
                inputs.append(line)
        if not inputs:
            print(f"错误 [E001]: {ERROR_CODES['E001']}", file=sys.stderr)
            return 1
        results = process_batch(inputs)
        for result in results:
            print(format_output(result, args.format))
        return 0

    # 单条模式
    text = args.input
    if args.file:
        try:
            with open(text, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"错误 [E003]: 文件不存在: {text}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 [E006]: 读取文件失败: {str(e)}", file=sys.stderr)
            return 1

    try:
        parser = InvoiceParser(text)
        result = parser.parse()
        print(format_output(result, args.format))
        return 0
    except InvoiceError as e:
        print(f"错误 [{e.code}]: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [E010]: 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
