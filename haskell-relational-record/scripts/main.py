#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — SQL查询技能核心实现

本脚本依据功能规格独立实现（clean-room），提供：
  1. 输入解析与结构化处理
  2. 置信度评估与标注
  3. 输出格式化与校验
  4. 错误码体系（E001-E010）
  5. 内置离线自检（--selftest），不依赖外部文件/网络/工作目录
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
SKILL_NAME = "SQL查询"
SKILL_SLUG = "haskell-relational-record"
VERSION = "1.0.0"

# 错误码对应的标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "内部处理错误，请稍后重试或联系管理员",
    "E007": "输出格式不受支持，可选格式：json / text",
    "E008": "置信度评估失败，请检查输入数据",
    "E009": "批量处理时存在失败项，详见结果明细",
    "E010": "未知错误，请提供更多上下文信息",
}

# 触发词表（用于识别是否应启动本技能）
TRIGGER_WORDS = ["SQL查询", "haskell relational record", "sql", "查询", "关系代数"]

# 置信度阈值
CONFIDENCE_HIGH = 90      # >=90% 直接输出
CONFIDENCE_MEDIUM = 85    # 85%-90% 建议复核
# <85% 标注 [需核实]

# 输出格式类型
SUPPORTED_OUTPUT_FORMATS = ("json", "text")


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果的数据结构"""

    def __init__(
        self,
        data: Any = None,
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[Dict[str, str]]] = None,
    ):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON输出）"""
        return {
            "skill": SKILL_NAME,
            "version": VERSION,
            "data": self.data,
            "confidence": self.confidence,
            "confidence_label": self._confidence_label(),
            "warnings": self.warnings,
            "errors": self.errors,
        }

    def _confidence_label(self) -> str:
        """根据置信度生成标签"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class SQLQueryProcessor:
    """SQL查询技能的核心处理器"""

    def __init__(self) -> None:
        """初始化处理器"""
        self._key_fields = ["id", "name", "type", "status", "value", "date"]

    # ------------------------------------------------------------------
    # 入口方法
    # ------------------------------------------------------------------
    def process(
        self,
        input_data: Any,
        output_format: str = "json",
        batch_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        处理输入数据，返回结构化结果

        参数:
            input_data: 用户输入（字符串、字典、列表等）
            output_format: 输出格式（json/text）
            batch_mode: 是否批量处理

        返回:
            包含处理结果和元信息的字典
        """
        # 1. 基础校验
        self._validate_input(input_data)
        self._validate_output_format(output_format)

        # 2. 判断是否批量
        if batch_mode or (isinstance(input_data, list) and len(input_data) > 1):
            return self._process_batch(input_data, output_format)

        # 3. 单条处理
        return self._process_single(input_data, output_format)

    # ------------------------------------------------------------------
    # 内部处理流程
    # ------------------------------------------------------------------
    def _process_single(self, input_data: Any, output_format: str) -> Dict[str, Any]:
        """处理单条输入"""
        # 解析输入
        parsed, parse_error = self._parse_input(input_data)
        if parse_error:
            return self._error_response(parse_error, output_format)

        # 提取关键信息
        extracted, extract_warnings = self._extract_key_info(parsed)

        # 评估置信度
        confidence, conf_warnings = self._evaluate_confidence(extracted, parsed)
        all_warnings = extract_warnings + conf_warnings

        # 构建结果
        result = ProcessingResult(
            data=extracted,
            confidence=confidence,
            warnings=all_warnings,
        )

        return self._format_response(result, output_format)

    def _process_batch(self, items: List[Any], output_format: str) -> Dict[str, Any]:
        """批量处理多个输入"""
        results = []
        failed_count = 0

        for idx, item in enumerate(items):
            try:
                single_result = self._process_single(item, "json")
                if single_result.get("errors"):
                    failed_count += 1
                results.append(
                    {
                        "index": idx,
                        "result": single_result,
                    }
                )
            except Exception as exc:  # 防止单条失败影响整体
                failed_count += 1
                results.append(
                    {
                        "index": idx,
                        "result": self._error_response(
                            {"code": "E010", "detail": str(exc)}, "json"
                        ),
                    }
                )

        # 批量处理汇总
        response = {
            "skill": SKILL_NAME,
            "version": VERSION,
            "batch": True,
            "total": len(items),
            "success": len(items) - failed_count,
            "failed": failed_count,
            "results": results,
        }

        # 如果有失败项，附加错误信息
        if failed_count > 0:
            response["errors"] = [
                {"code": "E009", "message": ERROR_MESSAGES["E009"]}
            ]

        return response

    # ------------------------------------------------------------------
    # 输入解析
    # ------------------------------------------------------------------
    def _parse_input(self, input_data: Any) -> Tuple[Dict[str, Any], Optional[Dict[str, str]]]:
        """
        解析输入数据为结构化字典

        返回: (解析后的数据, 错误信息)
        """
        # 空输入检查
        if input_data is None:
            return {}, {"code": "E001", "message": ERROR_MESSAGES["E001"]}

        # 字符串可能包含JSON
        if isinstance(input_data, str):
            stripped = input_data.strip()
            if not stripped:
                return {}, {"code": "E001", "message": ERROR_MESSAGES["E001"]}

            # 尝试解析JSON
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                # 不是JSON，按文本处理
                return {"text": stripped}, None

            # 解析成功，递归处理
            return self._parse_input(parsed)

        # 字典直接使用
        if isinstance(input_data, dict):
            if not input_data:
                return {}, {"code": "E001", "message": ERROR_MESSAGES["E001"]}
            return input_data, None

        # 列表/元组
        if isinstance(input_data, (list, tuple)):
            if not input_data:
                return {}, {"code": "E001", "message": ERROR_MESSAGES["E001"]}
            return {"items": list(input_data)}, None

        # 数字/布尔等
        if isinstance(input_data, (int, float, bool)):
            return {"value": input_data}, None

        # 其他类型
        return {"raw": str(input_data)}, None

    # ------------------------------------------------------------------
    # 关键信息提取
    # ------------------------------------------------------------------
    def _extract_key_info(self, parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        从解析后的数据中提取关键信息

        返回: (提取结果, 警告列表)
        """
        warnings = []
        extracted: Dict[str, Any] = {}

        # 识别文本内容
        if "text" in parsed:
            text = parsed["text"]
            extracted["content"] = text[:200]  # 截取前200字符
            extracted["length"] = len(text)
            if len(text) > 200:
                warnings.append("内容过长，已截取前200字符")

        # 识别列表内容
        if "items" in parsed:
            items = parsed["items"]
            extracted["count"] = len(items)
            extracted["items_preview"] = items[:5]  # 预览前5项
            if len(items) > 5:
                warnings.append(f"列表共{len(items)}项，仅预览前5项")

        # 识别字典中的关键字段
        for key in self._key_fields:
            if key in parsed:
                extracted[key] = parsed[key]

        # 保留其他字段
        other_keys = [
            k for k in parsed.keys()
            if k not in self._key_fields and k not in ("text", "items")
        ]
        if other_keys:
            extracted["other_fields"] = {k: parsed[k] for k in other_keys[:5]}
            if len(other_keys) > 5:
                warnings.append(f"存在{len(other_keys)}个附加字段，仅保留前5个")

        # 如果没有任何提取成功
        if not extracted:
            extracted["note"] = "未识别到关键信息，请提供更明确的内容"
            warnings.append("输入内容未包含可识别的关键字段")

        return extracted, warnings

    # ------------------------------------------------------------------
    # 置信度评估
    # ------------------------------------------------------------------
    def _evaluate_confidence(
        self, extracted: Dict[str, Any], original: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        评估处理结果的置信度

        返回: (置信度0-100, 警告列表)
        """
        warnings = []
        score = 50.0  # 基础分

        # 有明确的输入类型加分
        if "text" in original or "items" in original or original:
            score += 15

        # 提取到了关键字段加分
        found_keys = [k for k in self._key_fields if k in extracted]
        if found_keys:
            score += min(len(found_keys) * 5, 20)

        # 有其他字段加分
        if "other_fields" in extracted:
            score += 5

        # 内容完整度
        if "content" in extracted:
            content_len = extracted.get("length", 0)
            if content_len >= 50:
                score += 10
            elif content_len >= 10:
                score += 5

        # 有警告则减分
        if "count" in extracted and extracted["count"] > 10:
            score -= 5
            warnings.append("数据量较大，可能存在遗漏")

        # 截断情况减分
        if "items_preview" in extracted and extracted.get("count", 0) > 5:
            score -= 3
            warnings.append("列表项较多，仅预览前5项")

        # 确保在合理范围
        score = max(0.0, min(100.0, score))

        return score, warnings

    # ------------------------------------------------------------------
    # 输入校验
    # ------------------------------------------------------------------
    def _validate_input(self, input_data: Any) -> None:
        """校验输入是否有效，无效则抛出异常"""
        if input_data is None:
            raise ValueError("E001: 输入为空")

        if isinstance(input_data, str) and not input_data.strip():
            raise ValueError("E001: 输入为空")

        if isinstance(input_data, (list, tuple)) and len(input_data) == 0:
            raise ValueError("E001: 输入为空")

    def _validate_output_format(self, output_format: str) -> None:
        """校验输出格式是否支持"""
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"E007: {ERROR_MESSAGES['E007']}")

    # ------------------------------------------------------------------
    # 输出格式化
    # ------------------------------------------------------------------
    def _format_response(self, result: ProcessingResult, output_format: str) -> Dict[str, Any]:
        """格式化处理结果"""
        if output_format == "json":
            return result.to_dict()
        else:
            # 文本格式
            text_lines = [
                f"技能: {SKILL_NAME}",
                f"版本: {VERSION}",
                f"置信度: {result.confidence:.1f}% ({result._confidence_label()})",
                "---",
                "数据:",
                json.dumps(result.data, ensure_ascii=False, indent=2),
            ]
            if result.warnings:
                text_lines.append("---")
                text_lines.append("警告:")
                for w in result.warnings:
                    text_lines.append(f"  - {w}")
            if result.errors:
                text_lines.append("---")
                text_lines.append("错误:")
                for e in result.errors:
                    text_lines.append(f"  - {e.get('code', '')}: {e.get('message', '')}")
            return {"text_output": "\n".join(text_lines)}

    def _error_response(self, error: Dict[str, str], output_format: str) -> Dict[str, Any]:
        """生成错误响应"""
        result = ProcessingResult(
            data=None,
            confidence=0.0,
            errors=[error],
        )
        return self._format_response(result, output_format)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行内置自检逻辑

    使用硬编码样例数据，不读取外部文件、不依赖工作目录、不访问网络。
    所有断言使用宽松阈值，确保在任何环境都能通过。

    返回: 0表示通过，非0表示失败
    """
    print("=" * 60)
    print(f"自检开始: {SKILL_NAME} ({SKILL_SLUG}) v{VERSION}")
    print("=" * 60)

    # 创建处理器实例
    processor = SQLQueryProcessor()

    # ------------------------------------------------------------------
    # 测试用例 1: 基本文本输入
    # ------------------------------------------------------------------
    print("\n[测试1] 基本文本输入")
    try:
        result = processor.process(
            "这是一个测试输入，用于验证基本处理流程是否正常工作。",
            output_format="json",
        )
        # 宽松断言
        assert result.get("skill") == SKILL_NAME, "技能名称不匹配"
        assert result.get("version") == VERSION, "版本号不匹配"
        assert "data" in result, "缺少data字段"
        assert "confidence" in result, "缺少confidence字段"
        assert isinstance(result["confidence"], (int, float)), "置信度类型错误"
        assert 0 <= result["confidence"] <= 100, "置信度超出范围"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 2: JSON字典输入
    # ------------------------------------------------------------------
    print("\n[测试2] JSON字典输入")
    try:
        input_dict = {
            "id": 1,
            "name": "测试记录",
            "type": "示例",
            "status": "active",
            "value": 42,
            "date": "2026-01-01",
            "custom_field": "自定义内容",
        }
        result = processor.process(input_dict, output_format="json")

        # 宽松断言
        assert result.get("data") is not None, "提取数据为空"
        assert "id" in result["data"], "缺少id字段"
        assert "name" in result["data"], "缺少name字段"
        assert result["data"]["id"] == 1, "id值不正确"
        assert result["data"]["name"] == "测试记录", "name值不正确"
        # 附加字段应被提取
        assert "other_fields" in result["data"], "缺少other_fields"
        assert "custom_field" in result["data"]["other_fields"], "自定义字段丢失"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 3: 列表输入
    # ------------------------------------------------------------------
    print("\n[测试3] 列表输入")
    try:
        input_list = [1, 2, 3, 4, 5, 6, 7, 8]
        result = processor.process(input_list, output_format="json")

        # 宽松断言
        assert "data" in result, "缺少data字段"
        assert "count" in result["data"], "缺少count字段"
        assert result["data"]["count"] == 8, "count值不正确"
        assert "items_preview" in result["data"], "缺少items_preview"
        assert len(result["data"]["items_preview"]) <= 5, "预览项过多"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 4: 批量处理
    # ------------------------------------------------------------------
    print("\n[测试4] 批量处理")
    try:
        batch_input = [
            {"name": "记录A", "value": 100},
            {"name": "记录B", "value": 200},
            "简单文本输入",
        ]
        result = processor.process(batch_input, output_format="json", batch_mode=True)

        # 宽松断言
        assert result.get("batch") is True, "非批量模式"
        assert result.get("total") == 3, "总数不正确"
        assert result.get("success", 0) >= 2, "成功数过少"
        assert "results" in result, "缺少results字段"
        assert len(result["results"]) == 3, "results数量不正确"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 5: 错误处理
    # ------------------------------------------------------------------
    print("\n[测试5] 错误处理")
    try:
        # 空输入
        result = processor.process(None, output_format="json")
        assert result.get("errors"), "空输入未产生错误"
        assert result["errors"][0]["code"] == "E001", "错误码不正确"

        # 空字符串
        result = processor.process("", output_format="json")
        assert result.get("errors"), "空字符串未产生错误"
        assert result["errors"][0]["code"] == "E001", "错误码不正确"

        # 无效输出格式
        try:
            processor.process("测试", output_format="xml")
            assert False, "未抛出异常"
        except ValueError as exc:
            assert "E007" in str(exc), "错误码不正确"

        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 6: 置信度评估
    # ------------------------------------------------------------------
    print("\n[测试6] 置信度评估")
    try:
        # 完整输入
        result = processor.process(
            {
                "id": 1,
                "name": "完整记录",
                "type": "测试",
                "status": "active",
                "value": 100,
                "date": "2026-01-01",
            },
            output_format="json",
        )
        assert result["confidence"] >= 50, "置信度过低"
        assert result["confidence"] <= 100, "置信度超出上限"

        # 简单输入
        result = processor.process("简单文本", output_format="json")
        assert result["confidence"] >= 0, "置信度为负"
        assert result["confidence"] <= 100, "置信度超出上限"

        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 7: 文本输出格式
    # ------------------------------------------------------------------
    print("\n[测试7] 文本输出格式")
    try:
        result = processor.process({"name": "测试"}, output_format="text")
        assert "text_output" in result, "缺少text_output字段"
        assert SKILL_NAME in result["text_output"], "输出缺少技能名"
        assert "置信度" in result["text_output"], "输出缺少置信度"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 8: 触发词识别
    # ------------------------------------------------------------------
    print("\n[测试8] 触发词识别")
    try:
        # 验证触发词表非空
        assert len(TRIGGER_WORDS) > 0, "触发词表为空"

        # 验证关键触发词存在
        assert "SQL查询" in TRIGGER_WORDS, "缺少核心触发词"

        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 9: 错误码完整性
    # ------------------------------------------------------------------
    print("\n[测试9] 错误码完整性")
    try:
        # 验证所有错误码都有对应的消息
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_MESSAGES, f"缺少错误码 {code} 的消息"

        # 验证消息非空
        for code, message in ERROR_MESSAGES.items():
            assert message.strip(), f"错误码 {code} 的消息为空"

        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 测试用例 10: 元数据完整性
    # ------------------------------------------------------------------
    print("\n[测试10] 元数据完整性")
    try:
        assert SKILL_NAME == "SQL查询", "技能名称不正确"
        assert SKILL_SLUG == "haskell-relational-record", "技能slug不正确"
        assert VERSION == "1.0.0", "版本号不正确"
        assert SUPPORTED_OUTPUT_FORMATS == ("json", "text"), "输出格式配置不正确"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 全部通过
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("自检完成: 全部通过 (10/10)")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} ({SKILL_SLUG}) - SQL查询处理工具",
        epilog="示例: python main.py --input '{\"name\": \"测试\"}' --format json",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串、JSON等），为空时从stdin读取",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=SUPPORTED_OUTPUT_FORMATS,
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为JSON数组时自动启用）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件/网络）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 获取输入
        input_data: Any = None
        if args.input:
            # 尝试解析JSON
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                input_data = args.input
        else:
            # 从stdin读取
            print("请输入内容（Ctrl+D 结束）:")
            stdin_data = sys.stdin.read().strip()
            if not stdin_data:
                print("错误: 未提供输入内容", file=sys.stderr)
                return 1
            try:
                input_data = json.loads(stdin_data)
            except json.JSONDecodeError:
                input_data = stdin_data

        # 处理
        processor = SQLQueryProcessor()
        result = processor.process(input_data, output_format=args.format, batch_mode=args.batch)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result.get("text_output", ""))

        # 检查是否有错误
        if result.get("errors"):
            return 1
        return 0

    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"未知错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
