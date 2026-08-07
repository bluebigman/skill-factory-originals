#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ruby Asset Manager (RAM) - 独立实现脚本
========================================
本脚本依据功能规格文档进行 clean-room 重写，实现核心逻辑：
  - 输入内容解析与结构化
  - 置信度评估与标注
  - 批量处理与自定义格式输出
  - 错误码体系 (E001-E010)
  - 内置离线自检 (--selftest)

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码话术表（依据规格 E001-E005，扩展至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "输出格式指定错误，支持格式：json / text / csv",
    "E008": "批量输入为空或格式错误",
    "E009": "输入内容包含无法识别的关键字段",
    "E010": "系统资源不足，无法完成处理",
}

# 置信度阈值（依据规格）
CONFIDENCE_HIGH = 0.90      # ≥90% 直接输出
CONFIDENCE_MEDIUM = 0.85    # 85%-90% 建议复核
CONFIDENCE_LOW = 0.85       # <85% 需核实

# 默认输出字段模板
DEFAULT_FIELDS = ["key", "value", "confidence", "note"]

# 支持的关键字段识别模式（用于结构化提取）
KEY_PATTERNS = {
    "id": r"(?:id|编号|序号)\s*[:：=]?\s*([A-Za-z0-9_-]+)",
    "name": r"(?:name|名称|标题)\s*[:：=]?\s*([\w\u4e00-\u9fff\s-]+)",
    "type": r"(?:type|类型|种类)\s*[:：=]?\s*([\w\u4e00-\u9fff]+)",
    "value": r"(?:value|值|内容|数据)\s*[:：=]?\s*([\w\u4e00-\u9fff\s%.-]+)",
    "url": r"(?:url|链接|网址)\s*[:：=]?\s*(https?://[^\s]+)",
    "date": r"(?:date|日期|时间)\s*[:：=]?\s*([\d-]{8,10})",
}

# 自定义异常（用于内部错误传递）
class RamError(Exception):
    """RAM 工具自定义异常，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心功能类
# ============================================================

class RamProcessor:
    """
    Ruby Asset Manager 核心处理器
    负责输入解析、结构化、置信度评估和输出生成
    """

    def __init__(self) -> None:
        """初始化处理器，设定默认配置"""
        self.supported_formats = ["json", "text", "csv"]
        self.default_output_format = "json"
        self.fields = DEFAULT_FIELDS.copy()

    # ---------- 公共接口 ----------

    def process(self, raw_input: Any, output_format: Optional[str] = None,
                custom_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        处理输入并返回结构化结果

        参数:
            raw_input: 用户提供的数据（字符串、字典、列表等）
            output_format: 输出格式（json/text/csv）
            custom_fields: 自定义输出字段列表

        返回:
            包含处理结果和元信息的字典

        异常:
            RamError: 携带错误码 E001-E010
        """
        # 1. 输入验证
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            raise RamError("E001")
        if isinstance(raw_input, (list, tuple)) and len(raw_input) == 0:
            raise RamError("E008")
        if not isinstance(raw_input, (str, dict, list, tuple, int, float)):
            raise RamError("E003")

        # 2. 格式验证
        fmt = output_format or self.default_output_format
        if fmt not in self.supported_formats:
            raise RamError("E007")

        # 3. 字段设置
        if custom_fields:
            if not isinstance(custom_fields, list) or not all(isinstance(f, str) for f in custom_fields):
                raise RamError("E007")
            self.fields = custom_fields

        # 4. 解析与结构化
        try:
            parsed_items = self._parse_input(raw_input)
            if not parsed_items:
                raise RamError("E009")

            structured_results = []
            for item in parsed_items:
                structured = self._structure_item(item)
                confidence = self._evaluate_confidence(structured)
                structured["confidence"] = confidence
                structured["note"] = self._generate_note(confidence)
                structured_results.append(structured)

            # 5. 生成输出
            output = self._format_output(structured_results, fmt)

            # 6. 组装最终结果
            return {
                "success": True,
                "data": output,
                "items_count": len(structured_results),
                "avg_confidence": self._average_confidence(structured_results),
                "format": fmt,
                "disclaimer": "本结果仅供参考，低置信度内容请人工核实。",
            }

        except RamError:
            raise
        except Exception as exc:
            # 捕获意外异常，转为内部错误
            raise RamError("E006", str(exc)) from exc

    def batch_process(self, inputs: List[Any], output_format: str = "json") -> Dict[str, Any]:
        """
        批量处理多个输入

        参数:
            inputs: 输入列表，每个元素为独立输入
            output_format: 输出格式

        返回:
            批量处理结果汇总
        """
        if not isinstance(inputs, list) or len(inputs) == 0:
            raise RamError("E008")

        results = []
        errors = []
        for idx, inp in enumerate(inputs):
            try:
                result = self.process(inp, output_format=output_format)
                results.append({"index": idx, "success": True, "result": result})
            except RamError as err:
                errors.append({"index": idx, "success": False, "error": err.code, "message": err.message})

        return {
            "success": len(errors) == 0,
            "total": len(inputs),
            "succeeded": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }

    # ---------- 内部解析方法 ----------

    def _parse_input(self, raw_input: Any) -> List[Any]:
        """
        解析输入为统一的项目列表

        支持的输入类型:
            - 字符串: 按行分割，每行视为一个项目
            - 字典: 单个项目
            - 列表/元组: 多个项目
            - 数字: 转换为字符串后作为单个项目

        返回:
            项目列表，每个项目是待结构化的原始数据
        """
        if isinstance(raw_input, str):
            # 尝试解析 JSON 字符串
            stripped = raw_input.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    return self._parse_input(parsed)
                except json.JSONDecodeError:
                    pass
            # 按行分割
            lines = [line.strip() for line in stripped.splitlines() if line.strip()]
            return lines if lines else [stripped]

        if isinstance(raw_input, dict):
            return [raw_input]

        if isinstance(raw_input, (list, tuple)):
            items = []
            for item in raw_input:
                items.extend(self._parse_input(item))
            return items

        # 数字或其他类型
        return [str(raw_input)]

    def _structure_item(self, item: Any) -> Dict[str, Any]:
        """
        将单个项目结构化为字段字典

        对字符串输入，尝试提取关键字段；对字典输入，直接使用其键值。
        无法识别的部分保留原始内容。

        参数:
            item: 单个输入项目

        返回:
            结构化字段字典
        """
        if isinstance(item, dict):
            # 字典输入：直接映射，并补充缺失字段
            structured = {}
            for key, value in item.items():
                structured[str(key)] = value
            # 确保有 key 字段
            if "key" not in structured:
                structured["key"] = str(item.get("id", item.get("name", "")))
            return structured

        # 字符串输入：尝试提取关键字段
        text = str(item)
        structured: Dict[str, Any] = {}

        # 尝试识别各关键字段
        for field, pattern in KEY_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                structured[field] = match.group(1).strip()

        # 如果没有识别到任何字段，将整段作为 value
        if not structured:
            structured["value"] = text
            structured["key"] = text[:30]  # 截取前30字符作为key

        # 补充 key（如果缺失）
        if "key" not in structured:
            structured["key"] = structured.get("id", structured.get("name", structured.get("value", "")))

        return structured

    def _evaluate_confidence(self, item: Dict[str, Any]) -> float:
        """
        评估结构化结果的置信度

        规则:
            - 识别到 3 个及以上字段: ≥0.90
            - 识别到 2 个字段: 0.85-0.90
            - 识别到 1 个字段: 0.60-0.80
            - 未识别（整段作为value）: 0.50

        返回:
            0.0 到 1.0 之间的置信度
        """
        # 统计有效字段数（排除 key 和 value 之外的字段）
        known_fields = [f for f in item.keys() if f in KEY_PATTERNS]
        field_count = len(known_fields)

        if field_count >= 3:
            return 0.95
        elif field_count == 2:
            return 0.88
        elif field_count == 1:
            return 0.75
        else:
            # 只有 value 或 key，置信度较低
            return 0.55

    def _generate_note(self, confidence: float) -> str:
        """根据置信度生成标注"""
        if confidence >= CONFIDENCE_HIGH:
            return ""  # 无标注
        elif confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"

    def _format_output(self, items: List[Dict[str, Any]], fmt: str) -> Any:
        """
        按指定格式生成输出

        支持格式:
            - json: 字典列表
            - text: 可读文本
            - csv: 逗号分隔（含表头）
        """
        if fmt == "json":
            return items

        if fmt == "text":
            lines = []
            for idx, item in enumerate(items, 1):
                lines.append(f"--- 项目 {idx} ---")
                for key, value in item.items():
                    lines.append(f"  {key}: {value}")
            return "\n".join(lines)

        if fmt == "csv":
            # 获取所有可能的字段
            all_fields = []
            for item in items:
                for key in item.keys():
                    if key not in all_fields:
                        all_fields.append(key)

            # 生成 CSV
            header = ",".join(all_fields)
            rows = [header]
            for item in items:
                row = []
                for field in all_fields:
                    value = item.get(field, "")
                    # 处理包含逗号的值
                    if isinstance(value, str) and "," in value:
                        value = f'"{value}"'
                    row.append(str(value))
                rows.append(",".join(row))
            return "\n".join(rows)

        raise RamError("E007")

    def _average_confidence(self, items: List[Dict[str, Any]]) -> float:
        """计算平均置信度"""
        if not items:
            return 0.0
        total = sum(item.get("confidence", 0.0) for item in items)
        return round(total / len(items), 2)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置离线自检程序

    使用硬编码样例数据验证核心逻辑，不访问外部资源。
    断言采用宽松阈值，确保在任何环境稳定通过。

    返回:
        True 表示全部通过，否则抛出 AssertionError
    """
    print("=" * 60)
    print("RAM 工具自检程序启动")
    print("=" * 60)

    processor = RamProcessor()

    # ---- 测试用例 1: 基本字符串处理 ----
    print("\n[1/5] 测试基本字符串处理...")
    sample_text = "id: A001, name: 测试项目, type: 文档, value: 这是内容"
    try:
        result = processor.process(sample_text)
        assert result["success"] is True, "处理应成功"
        assert result["items_count"] == 1, "应识别 1 个项目"
        item = result["data"][0]
        assert "key" in item, "应包含 key 字段"
        assert "confidence" in item, "应包含 confidence 字段"
        assert item["confidence"] >= 0.8, "置信度应不低于 0.8"
        print(f"  ✓ 通过 (置信度: {item['confidence']})")
    except AssertionError as err:
        print(f"  ✗ 失败: {err}")
        return False

    # ---- 测试用例 2: 批量处理 ----
    print("\n[2/5] 测试批量处理...")
    batch_inputs = [
        "id: B001, name: 项目一",
        "id: B002, name: 项目二, type: 数据",
        {"id": "B003", "name": "项目三", "type": "报告", "value": "内容三"},
    ]
    try:
        batch_result = processor.batch_process(batch_inputs)
        assert batch_result["total"] == 3, "总数应为 3"
        assert batch_result["succeeded"] == 3, "全部应成功"
        assert batch_result["failed"] == 0, "不应有失败"
        assert batch_result["success"] is True, "整体应成功"
        print(f"  ✓ 通过 (成功 {batch_result['succeeded']}/{batch_result['total']})")
    except AssertionError as err:
        print(f"  ✗ 失败: {err}")
        return False

    # ---- 测试用例 3: 错误处理 ----
    print("\n[3/5] 测试错误处理...")
    try:
        processor.process("")  # 空输入
        print("  ✗ 失败: 空输入应抛出 E001")
        return False
    except RamError as err:
        assert err.code == "E001", f"错误码应为 E001，实际为 {err.code}"
        print(f"  ✓ 通过 (错误码: {err.code})")

    # ---- 测试用例 4: 置信度标注 ----
    print("\n[4/5] 测试置信度标注...")
    low_conf_text = "随便一段没有结构的内容"
    try:
        result = processor.process(low_conf_text)
        item = result["data"][0]
        assert item["confidence"] < 0.8, "低信息量内容置信度应较低"
        assert item["note"] == "[需核实]", "低置信度应标注 [需核实]"
        print(f"  ✓ 通过 (置信度: {item['confidence']:.2f}, 标注: {item['note']})")
    except AssertionError as err:
        print(f"  ✗ 失败: {err}")
        return False

    # ---- 测试用例 5: 输出格式 ----
    print("\n[5/5] 测试多种输出格式...")
    sample = "id: C001, name: 格式测试"
    try:
        # JSON 格式
        json_result = processor.process(sample, output_format="json")
        assert isinstance(json_result["data"], list), "JSON 格式应返回列表"

        # Text 格式
        text_result = processor.process(sample, output_format="text")
        assert isinstance(text_result["data"], str), "Text 格式应返回字符串"
        assert "C001" in text_result["data"], "Text 输出应包含内容"

        # CSV 格式
        csv_result = processor.process(sample, output_format="csv")
        assert isinstance(csv_result["data"], str), "CSV 格式应返回字符串"
        assert "id" in csv_result["data"].splitlines()[0], "CSV 应包含表头"

        # 非法格式
        try:
            processor.process(sample, output_format="xml")
            print("  ✗ 失败: 非法格式应抛出 E007")
            return False
        except RamError as err:
            assert err.code == "E007", f"错误码应为 E007，实际为 {err.code}"

        print("  ✓ 通过 (json/text/csv/非法格式均正确)")
    except AssertionError as err:
        print(f"  ✗ 失败: {err}")
        return False

    # ---- 全部通过 ----
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="Ruby Asset Manager - 通用数据处理工具",
        epilog="示例: python main.py --input 'id: A1, name: 测试' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（字符串、JSON 或文件路径）")
    parser.add_argument("--file", "-f", type=str, help="输入文件路径（替代 --input）")
    parser.add_argument("--format", "-fmt", type=str, default="json",
                        choices=["json", "text", "csv"], help="输出格式")
    parser.add_argument("--fields", type=str, help="自定义输出字段（逗号分隔）")
    parser.add_argument("--batch", action="store_true", help="批量模式（输入为 JSON 数组）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检程序")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    processor = RamProcessor()

    try:
        # 获取输入
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    raw_input = f.read()
            except OSError as err:
                print(f"[E010] 无法读取文件: {err}", file=sys.stderr)
                return 10
        elif args.input:
            raw_input = args.input
        else:
            print(f"[E001] {ERROR_MESSAGES['E001']}", file=sys.stderr)
            print("使用 --help 查看用法", file=sys.stderr)
            return 1

        # 解析自定义字段
        custom_fields = None
        if args.fields:
            custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 批量或单条处理
        if args.batch:
            try:
                import json as json_mod
                batch_data = json_mod.loads(raw_input) if isinstance(raw_input, str) else raw_input
                if not isinstance(batch_data, list):
                    raise ValueError("批量模式需要 JSON 数组")
                result = processor.batch_process(batch_data, output_format=args.format)
            except (json.JSONDecodeError, ValueError) as err:
                print(f"[E008] 批量输入格式错误: {err}", file=sys.stderr)
                return 8
        else:
            result = processor.process(raw_input, output_format=args.format,
                                       custom_fields=custom_fields)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["data"])

        return 0

    except RamError as err:
        print(f"[{err.code}] {err.message}", file=sys.stderr)
        return int(err.code[1:])  # E001 -> 1, E010 -> 10
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
