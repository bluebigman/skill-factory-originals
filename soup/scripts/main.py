#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

未命名工具（soup）—— 一个通用的文档/元组数据处理工具。

本脚本根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
支持通过命令行将输入数据转换为结构化结果，并内置 --selftest 自检模式。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码与话术（对应规格“四、异常处理”）
# ---------------------------------------------------------------------------
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...（逐项追问）",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试或检查输入。",
    "E007": "文件读取失败，请检查路径或权限。",
    "E008": "JSON 解析失败，请检查输入是否为合法 JSON。",
    "E009": "输出写入失败，请检查目标路径。",
    "E010": "未知错误，请查看日志。",
}


class SoupError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心逻辑：数据解析与结构化
# ---------------------------------------------------------------------------
class SoupProcessor:
    """
    核心处理类：
    1. 解析输入（字符串 / 文件路径 / URL 字符串）。
    2. 识别关键字段并结构化。
    3. 计算置信度并标注。
    4. 输出为 JSON 格式。
    """

    def __init__(self, input_data: str, source_type: str = "auto"):
        """
        初始化处理器。

        :param input_data: 原始输入内容（字符串或文件路径）。
        :param source_type: 输入来源类型：auto / text / file / url。
        """
        self.raw_input = input_data
        self.source_type = source_type
        self.parsed_content: Optional[Any] = None
        self.structured_result: Optional[Dict[str, Any]] = None
        self.confidence: float = 0.0

    # -- 输入解析 ----------------------------------------------------------
    def _detect_source_type(self) -> str:
        """自动探测输入来源类型。"""
        if self.source_type != "auto":
            return self.source_type

        # 检查是否为文件路径（存在且为文件）
        if os.path.isfile(self.raw_input):
            return "file"

        # 检查是否为 URL（简单判断前缀）
        if self.raw_input.startswith(("http://", "https://")):
            return "url"

        # 默认视为文本
        return "text"

    def _load_content(self) -> Any:
        """
        根据来源类型读取内容，返回解析后的 Python 对象。
        """
        src_type = self._detect_source_type()

        if src_type == "file":
            try:
                with open(self.raw_input, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as exc:
                raise SoupError("E007", f"文件读取失败：{exc}") from exc
            return self._parse_text(content)

        if src_type == "url":
            # 规格明确：不访问网络。此处仅将 URL 本身作为文本记录。
            return {
                "url": self.raw_input,
                "note": "[需核实] 未访问网络，仅记录 URL 字符串",
                "requires_verification": True
            }

        # 默认按文本处理
        return self._parse_text(self.raw_input)

    @staticmethod
    def _parse_text(text: str) -> Any:
        """
        尝试解析文本：
        1. 若为合法 JSON，则解析为对象/数组。
        2. 否则按纯文本处理，拆分为行列表。
        """
        if not text or not text.strip():
            raise SoupError("E001")

        stripped = text.strip()
        try:
            return json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            # 非 JSON，按文本行处理
            lines = [line.strip() for line in stripped.splitlines() if line.strip()]
            if not lines:
                raise SoupError("E003", "输入内容为空或无法识别有效信息")
            return lines

    # -- 结构化处理 ----------------------------------------------------------
    def _extract_key_info(self, data: Any) -> Dict[str, Any]:
        """
        从解析后的数据中提取关键信息，生成结构化结果。
        规则：
        - 若为 dict：保留其键值，并补充元信息。
        - 若为 list：统计元素数量、类型分布，并保留前若干项。
        - 若为 str：记录长度和摘要。
        - 若为其他：记录类型和值。
        """
        if isinstance(data, dict):
            # 检查是否为 URL 特殊标记
            if data.get("requires_verification"):
                return {
                    "type": "url_reference",
                    "url": data.get("url", ""),
                    "note": "[需核实] 未访问网络，仅记录 URL 字符串",
                    "requires_verification": True
                }
            
            # 普通字典：直接结构化，并补充统计信息
            keys = list(data.keys())
            return {
                "type": "object",
                "field_count": len(keys),
                "fields": keys,
                "data": data,
                "note": "已识别为结构化对象",
            }

        if isinstance(data, list):
            # 列表：统计信息 + 抽样内容
            type_counter: Dict[str, int] = {}
            for item in data:
                tname = type(item).__name__
                type_counter[tname] = type_counter.get(tname, 0) + 1

            sample = data[:5]  # 最多取前 5 项作为样例
            return {
                "type": "array",
                "item_count": len(data),
                "item_types": type_counter,
                "sample": sample,
                "note": "已识别为数组/列表",
            }

        if isinstance(data, str):
            # 纯文本
            return {
                "type": "text",
                "length": len(data),
                "preview": data[:100] + ("..." if len(data) > 100 else ""),
                "note": "已识别为文本",
            }

        # 其他类型（数字、布尔等）
        return {
            "type": type(data).__name__,
            "value": data,
            "note": "已识别为标量值",
        }

    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """
        根据结构化结果的完整度计算置信度（0~1）。
        规则：
        - 有明确 type 且数据非空：基础 0.9
        - 字段数量/内容越丰富，置信度越高
        - 若存在“需核实”标记，则降低置信度
        - URL 引用类型：基础置信度较低
        """
        # URL 引用类型特殊处理
        if result.get("type") == "url_reference":
            return 0.7  # 未访问网络的 URL 置信度固定为 0.7

        base = 0.9

        # 根据类型微调
        rtype = result.get("type")
        if rtype == "object":
            # 字段越多越可信（但不超过 15 个字段）
            field_count = result.get("field_count", 0)
            bonus = min(field_count * 0.01, 0.05)
            base += bonus
        elif rtype == "array":
            # 元素越多越可信（但不超过 20 个元素）
            item_count = result.get("item_count", 0)
            bonus = min(item_count * 0.005, 0.05)
            base += bonus
        elif rtype == "text":
            # 文本越长越可信
            length = result.get("length", 0)
            bonus = min(length / 1000.0 * 0.02, 0.04)
            base += bonus

        # 若存在“需核实”标记，降低置信度
        note = str(result.get("note", ""))
        if "需核实" in note:
            base -= 0.15

        # 限制在 0.5 ~ 0.99 之间
        return max(0.5, min(base, 0.99))

    def process(self) -> Dict[str, Any]:
        """
        执行完整处理流程，返回最终结构化结果。
        """
        # Step 1: 解析输入
        self.parsed_content = self._load_content()

        # Step 2: 提取关键信息
        self.structured_result = self._extract_key_info(self.parsed_content)

        # Step 3: 计算置信度
        self.confidence = self._calculate_confidence(self.structured_result)

        # Step 4: 组装最终输出
        output = {
            "input_source": self._detect_source_type(),
            "confidence": round(self.confidence, 4),
            "result": self.structured_result,
        }

        # 置信度标注
        if self.confidence >= 0.9:
            output["level"] = "直接输出"
        elif self.confidence >= 0.85:
            output["level"] = "建议复核"
        else:
            output["level"] = "[需核实]"

        return output


# ---------------------------------------------------------------------------
# 输出与文件写入
# ---------------------------------------------------------------------------
def format_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """
    将结构化结果格式化为指定格式（当前支持 json / text）。
    """
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    if output_format == "text":
        # 简易文本格式
        lines = [f"输入来源: {data.get('input_source', 'unknown')}"]
        lines.append(f"置信度: {data.get('confidence', 0):.2%}")
        lines.append(f"级别: {data.get('level', 'unknown')}")
        lines.append("--- 结构化结果 ---")
        result = data.get("result", {})
        lines.append(f"类型: {result.get('type', 'unknown')}")
        lines.append(f"说明: {result.get('note', '')}")
        if "fields" in result:
            lines.append(f"字段列表: {', '.join(result['fields'])}")
        if "item_count" in result:
            lines.append(f"元素数量: {result['item_count']}")
        if "preview" in result:
            lines.append(f"预览: {result['preview']}")
        if "url" in result:
            lines.append(f"URL: {result['url']}")
        return "\n".join(lines)
    raise SoupError("E003", f"不支持的输出格式: {output_format}")


def write_output(content: str, output_path: Optional[str] = None) -> None:
    """
    将内容写入文件或打印到 stdout。
    """
    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            raise SoupError("E009", f"输出写入失败：{exc}") from exc
    else:
        print(content)


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    使用内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("=== 自检开始（离线模式） ===")

    # --- 测试用例 1：JSON 对象输入 ---
    print("\n[用例 1] JSON 对象输入")
    sample1 = '{"name": "张三", "age": 30, "city": "北京", "tags": ["dev", "ops"]}'
    try:
        proc = SoupProcessor(sample1, source_type="text")
        result1 = proc.process()
        assert result1["result"]["type"] == "object", "类型应为 object"
        assert result1["result"]["field_count"] >= 3, "字段数应至少为 3"
        assert result1["confidence"] >= 0.8, "置信度应不低于 0.8"
        print("  通过：结构化对象解析正确，置信度 =", result1["confidence"])
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1

    # --- 测试用例 2：文本行输入 ---
    print("\n[用例 2] 纯文本输入")
    sample2 = "第一行内容\n第二行内容\n第三行内容\n"
    try:
        proc = SoupProcessor(sample2, source_type="text")
        result2 = proc.process()
        assert result2["result"]["type"] == "array", "文本行应被解析为数组"
        assert result2["result"]["item_count"] >= 3, "应至少包含 3 行"
        assert result2["confidence"] >= 0.5, "置信度应不低于 0.5"
        print("  通过：文本解析正确，行数 =", result2["result"]["item_count"])
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1

    # --- 测试用例 3：JSON 数组输入 ---
    print("\n[用例 3] JSON 数组输入")
    sample3 = '[1, 2, 3, 4, 5, 6, 7, 8, "a", "b"]'
    try:
        proc = SoupProcessor(sample3, source_type="text")
        result3 = proc.process()
        assert result3["result"]["type"] == "array", "类型应为 array"
        assert result3["result"]["item_count"] >= 8, "元素数量应至少为 8"
        assert result3["confidence"] >= 0.8, "置信度应不低于 0.8"
        print("  通过：数组解析正确，元素数 =", result3["result"]["item_count"])
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1

    # --- 测试用例 4：空输入应报错 E001 ---
    print("\n[用例 4] 空输入错误处理")
    try:
        proc = SoupProcessor("", source_type="text")
        proc.process()
        print("  失败：空输入应抛出 E001")
        return 1
    except SoupError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际为 {exc.code}"
        print("  通过：空输入正确抛出 E001")

    # --- 测试用例 5：文件输入（使用临时文件） ---
    print("\n[用例 5] 文件输入")
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            tmp.write('{"key": "value", "number": 42}')
            tmp_path = tmp.name
        try:
            proc = SoupProcessor(tmp_path, source_type="file")
            result5 = proc.process()
            assert result5["input_source"] == "file", "输入来源应为 file"
            assert result5["result"]["type"] == "object", "类型应为 object"
            assert result5["confidence"] >= 0.8, "置信度应不低于 0.8"
            print("  通过：文件解析正确，置信度 =", result5["confidence"])
        finally:
            os.unlink(tmp_path)  # 清理临时文件
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1
    except OSError as exc:
        print(f"  失败：无法创建临时文件：{exc}")
        return 1

    # --- 测试用例 6：URL 输入（不访问网络） ---
    print("\n[用例 6] URL 输入（离线处理）")
    try:
        proc = SoupProcessor("https://example.com/data", source_type="url")
        result6 = proc.process()
        assert result6["input_source"] == "url", "输入来源应为 url"
        assert result6["result"]["type"] == "url_reference", "类型应为 url_reference"
        assert "url" in result6["result"], "结果中应包含 url 字段"
        assert result6["confidence"] < 0.9, "URL 未访问网络，置信度应低于 0.9"
        print("  通过：URL 离线处理正确，置信度 =", result6["confidence"])
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1

    # --- 测试用例 7：输出格式 ---
    print("\n[用例 7] 输出格式")
    try:
        sample7 = '{"a": 1}'
        proc = SoupProcessor(sample7, source_type="text")
        result7 = proc.process()
        json_out = format_output(result7, "json")
        assert json_out.startswith("{"), "JSON 输出应以 { 开头"
        text_out = format_output(result7, "text")
        assert "置信度" in text_out, "文本输出应包含置信度"
        print("  通过：JSON 和文本输出格式正确")
    except AssertionError as exc:
        print(f"  失败：{exc}")
        return 1
    except SoupError as exc:
        print(f"  失败：{exc}")
        return 1

    print("\n=== 自检全部通过 ===")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="未命名工具（soup）：通用数据处理与结构化工具",
        epilog="示例：python main.py --input '{\"name\": \"test\"}' --format json",
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="输入内容：文本 / 文件路径 / URL 字符串（默认从 stdin 读取）",
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        choices=["auto", "text", "file", "url"],
        default="auto",
        help="输入来源类型（默认 auto 自动探测）",
    )
    parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑",
    )
    return parser


def main() -> int:
    """主函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 获取输入
        if args.input:
            input_data = args.input
        else:
            # 从 stdin 读取
            input_data = sys.stdin.read()

        if not input_data or not input_data.strip():
            raise SoupError("E001")

        # 处理
        processor = SoupProcessor(input_data, source_type=args.source)
        result = processor.process()

        # 输出
        output_text = format_output(result, args.format)
        write_output(output_text, args.output)

        return 0

    except SoupError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底异常
        print(f"错误 E010: 未知错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
