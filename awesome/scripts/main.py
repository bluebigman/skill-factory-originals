#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未命名工具 - 核心实现脚本
版本: 1.0.0
描述: 将用户提供的数据/文件/URL 转换为结构化结果，支持批量处理和自定义格式。
"""

import argparse
import sys
import json
import os
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：需为文本、JSON 或 URL 字符串",
    "E004": "这超出了本工具的能力范围，建议：仅处理可解析的文本/JSON/URL",
    "E005": "结果无法确定，建议：提供更多上下文信息",
    "E006": "内部处理错误，请检查输入内容",
    "E007": "输出格式不支持，支持格式：text, json",
    "E008": "批量处理时出现错误，请检查每个输入项",
    "E009": "URL 处理失败，仅支持 http/https 协议",
    "E010": "文件读取失败，请检查文件路径和权限",
}

DEFAULT_OUTPUT_FORMAT = "text"
SUPPORTED_OUTPUT_FORMATS = ["text", "json"]
SUPPORTED_INPUT_TYPES = ["text", "json", "url"]
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85


# ============================================================
# 核心逻辑类
# ============================================================
class AwesomeProcessor:
    """核心处理器 - 负责输入解析、结构化处理和输出生成"""

    def __init__(self) -> None:
        self.error_message: Optional[str] = None

    # ---------- 主入口 ----------
    def process(
        self,
        input_data: Any,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        completeness: str = "detailed",
    ) -> Dict[str, Any]:
        """
        处理输入数据并返回结构化结果。

        参数:
            input_data: 用户输入（文本、JSON 对象或 URL 字符串）
            output_format: 输出格式（text 或 json）
            completeness: 期望完整度（quick 或 detailed）

        返回:
            结构化结果字典，包含 status、data、confidence、error_code 等字段
        """
        # 步骤 1: 校验输出格式
        if output_format not in SUPPORTED_OUTPUT_FORMATS:
            return self._make_error("E007", f"输出格式 '{output_format}' 不支持")

        # 步骤 2: 校验输入非空
        if input_data is None or (isinstance(input_data, str) and not input_data.strip()):
            return self._make_error("E001")

        # 步骤 3: 解析输入
        parsed = self._parse_input(input_data)
        if parsed["error_code"]:
            return self._make_error(parsed["error_code"], parsed.get("message"))

        # 步骤 4: 提取关键信息
        extracted = self._extract_key_info(parsed["data"])
        if extracted["error_code"]:
            return self._make_error(extracted["error_code"], extracted.get("message"))

        # 步骤 5: 计算置信度
        confidence = self._calculate_confidence(extracted["fields"], completeness)

        # 步骤 6: 生成输出
        output = self._generate_output(
            extracted["fields"],
            confidence,
            output_format,
            completeness,
        )

        return {
            "status": "success",
            "data": output,
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
            "error_code": None,
            "message": None,
        }

    # ---------- 输入解析 ----------
    def _parse_input(self, input_data: Any) -> Dict[str, Any]:
        """解析输入数据，识别类型并转换为字典"""
        # 处理 JSON 对象（字典类型）
        if isinstance(input_data, dict):
            return {"error_code": None, "data": input_data, "message": None}

        # 处理字符串
        if isinstance(input_data, str):
            text = input_data.strip()

            # 尝试解析为 URL
            if text.startswith(("http://", "https://")):
                # 不访问网络，仅提取 URL 信息
                return {
                    "error_code": None,
                    "data": {"source": "url", "url": text},
                    "message": None,
                }

            # 尝试解析为 JSON 字符串
            try:
                json_data = json.loads(text)
                if isinstance(json_data, dict):
                    return {"error_code": None, "data": json_data, "message": None}
                else:
                    return {"error_code": "E003", "data": None,
                            "message": "JSON 必须为对象类型"}
            except json.JSONDecodeError:
                # 作为纯文本处理
                return {
                    "error_code": None,
                    "data": {"source": "text", "content": text},
                    "message": None,
                }

        # 处理列表（批量输入）
        if isinstance(input_data, list):
            return {
                "error_code": None,
                "data": {"source": "batch", "items": input_data},
                "message": None,
            }

        # 其他类型不支持
        return {"error_code": "E003", "data": None,
                "message": f"不支持的输入类型: {type(input_data).__name__}"}

    # ---------- 关键信息提取 ----------
    def _extract_key_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """从解析后的数据中提取关键字段"""
        try:
            fields: Dict[str, Any] = {
                "title": None,
                "description": None,
                "keywords": [],
                "source": data.get("source", "unknown"),
                "content_length": 0,
                "has_url": False,
                "item_count": 0,
            }

            # 从 URL 输入提取
            if data.get("source") == "url":
                url = data.get("url", "")
                fields["has_url"] = True
                fields["title"] = self._extract_title_from_url(url)
                fields["content_length"] = len(url)
                return {"error_code": None, "fields": fields, "message": None}

            # 从纯文本输入提取
            if data.get("source") == "text":
                content = data.get("content", "")
                fields["content_length"] = len(content)
                fields["title"] = self._generate_title(content)
                fields["description"] = content[:200] if content else None
                fields["keywords"] = self._extract_keywords(content)
                return {"error_code": None, "fields": fields, "message": None}

            # 从 JSON 对象提取
            if isinstance(data, dict) and "source" not in data:
                # 尝试常见字段名
                title_key = self._find_key(data, ["title", "标题", "name", "名称"])
                desc_key = self._find_key(data, ["description", "描述", "desc", "摘要"])
                kw_key = self._find_key(data, ["keywords", "关键词", "tags", "标签"])

                fields["title"] = data.get(title_key) if title_key else None
                fields["description"] = data.get(desc_key) if desc_key else None
                fields["keywords"] = data.get(kw_key, []) if kw_key else []

                # 计算内容长度
                fields["content_length"] = len(json.dumps(data, ensure_ascii=False))

                # 统计条目数
                for key in ["items", "list", "data", "results", "内容"]:
                    if key in data and isinstance(data[key], list):
                        fields["item_count"] = len(data[key])
                        break

                return {"error_code": None, "fields": fields, "message": None}

            # 批量输入
            if data.get("source") == "batch":
                items = data.get("items", [])
                fields["item_count"] = len(items)
                fields["title"] = f"批量数据（共 {len(items)} 项）"
                fields["content_length"] = len(json.dumps(items, ensure_ascii=False))
                return {"error_code": None, "fields": fields, "message": None}

            # 未知结构
            return {"error_code": "E002", "fields": None,
                    "message": "无法识别输入结构，缺少关键信息"}

        except Exception as exc:
            return {"error_code": "E006", "fields": None,
                    "message": f"提取关键信息时出错: {str(exc)}"}

    # ---------- 辅助方法 ----------
    @staticmethod
    def _find_key(data: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """在字典中查找第一个存在的键"""
        for key in candidates:
            if key in data:
                return key
        return None

    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """从 URL 中提取标题（简单提取域名或路径）"""
        # 去除协议部分
        clean_url = url.replace("http://", "").replace("https://", "")
        # 取第一段作为标题
        parts = clean_url.split("/")
        if parts and parts[0]:
            return parts[0]
        return clean_url

    @staticmethod
    def _generate_title(content: str) -> str:
        """从文本内容生成标题"""
        if not content:
            return "未命名内容"
        # 取前 30 个字符作为标题
        title = content.strip().split("\n")[0]
        return title[:30] + ("..." if len(title) > 30 else "")

    @staticmethod
    def _extract_keywords(content: str) -> List[str]:
        """从文本中提取关键词（简单方法：取出现频率高的词）"""
        words = content.split()
        word_count: Dict[str, int] = {}
        for word in words:
            clean_word = word.strip(",.!?;:()[]{}").lower()
            if len(clean_word) >= 3 and not clean_word.isdigit():
                word_count[clean_word] = word_count.get(clean_word, 0) + 1

        # 按频率排序，取前 5 个
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:5]]

    # ---------- 置信度计算 ----------
    @staticmethod
    def _calculate_confidence(fields: Dict[str, Any], completeness: str) -> float:
        """根据提取字段的完整度计算置信度"""
        if not fields:
            return 0.5

        score = 0.0
        total_weight = 0.0

        # 标题权重
        if fields.get("title"):
            score += 0.3
        total_weight += 0.3

        # 描述权重
        if fields.get("description"):
            score += 0.25
        total_weight += 0.25

        # 关键词权重
        if fields.get("keywords"):
            score += 0.2
        total_weight += 0.2

        # 内容长度权重
        if fields.get("content_length", 0) > 0:
            score += 0.15
        total_weight += 0.15

        # 结构完整度
        if fields.get("source") != "unknown":
            score += 0.1
        total_weight += 0.1

        # 归一化
        confidence = score / total_weight if total_weight > 0 else 0.5

        # 根据完整度调整
        if completeness == "quick" and confidence > 0.8:
            confidence = min(confidence, 0.85)

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _confidence_label(confidence: float) -> str:
        """根据置信度生成标签"""
        if confidence >= CONFIDENCE_HIGH:
            return "高置信度"
        elif confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"

    # ---------- 输出生成 ----------
    def _generate_output(
        self,
        fields: Dict[str, Any],
        confidence: float,
        output_format: str,
        completeness: str,
    ) -> Any:
        """根据格式生成输出结果"""
        if output_format == "json":
            return self._generate_json_output(fields, confidence, completeness)
        else:
            return self._generate_text_output(fields, confidence, completeness)

    @staticmethod
    def _generate_json_output(
        fields: Dict[str, Any],
        confidence: float,
        completeness: str,
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出"""
        result = {
            "提取结果": {
                "标题": fields.get("title"),
                "描述": fields.get("description"),
                "关键词": fields.get("keywords", []),
                "来源": fields.get("source", "unknown"),
                "内容长度": fields.get("content_length", 0),
                "条目数": fields.get("item_count", 0),
            },
            "置信度": {
                "分数": round(confidence, 2),
                "标签": AwesomeProcessor._confidence_label(confidence),
            },
        }

        # 详细模式增加额外信息
        if completeness == "detailed":
            result["元信息"] = {
                "处理时间": "未记录（离线处理）",
                "处理模式": completeness,
                "是否包含URL": fields.get("has_url", False),
            }

        return result

    @staticmethod
    def _generate_text_output(
        fields: Dict[str, Any],
        confidence: float,
        completeness: str,
    ) -> str:
        """生成文本格式输出"""
        lines = []
        lines.append("=" * 50)
        lines.append("处理结果")
        lines.append("=" * 50)

        # 标题
        title = fields.get("title") or "未识别标题"
        lines.append(f"标题: {title}")

        # 描述
        if fields.get("description"):
            lines.append(f"描述: {fields['description']}")

        # 关键词
        keywords = fields.get("keywords", [])
        if keywords:
            lines.append(f"关键词: {', '.join(keywords)}")

        # 来源
        lines.append(f"来源: {fields.get('source', 'unknown')}")

        # 内容长度
        lines.append(f"内容长度: {fields.get('content_length', 0)} 字符")

        # 条目数
        if fields.get("item_count"):
            lines.append(f"条目数: {fields['item_count']}")

        # 置信度
        lines.append("-" * 50)
        label = AwesomeProcessor._confidence_label(confidence)
        lines.append(f"置信度: {confidence:.0%} ({label})")

        # 详细模式
        if completeness == "detailed":
            lines.append("-" * 50)
            lines.append("处理模式: 详细")
            if fields.get("has_url"):
                lines.append("包含URL: 是")

        lines.append("=" * 50)
        return "\n".join(lines)

    # ---------- 错误处理 ----------
    @staticmethod
    def _make_error(error_code: str, message: Optional[str] = None) -> Dict[str, Any]:
        """构造错误响应"""
        standard_message = ERROR_CODES.get(error_code, "未知错误")
        return {
            "status": "error",
            "data": None,
            "confidence": 0.0,
            "confidence_label": "错误",
            "error_code": error_code,
            "message": message or standard_message,
        }


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。
    断言使用宽松阈值，确保在不同环境下都能通过。

    返回:
        True 表示自检通过，False 表示失败
    """
    print("=" * 60)
    print("自检开始 - 未命名工具核心逻辑验证")
    print("=" * 60)

    processor = AwesomeProcessor()
    all_passed = True

    # ---------- 测试用例 1: 文本输入 ----------
    print("\n[测试 1] 文本输入处理")
    text_input = "这是一个测试文本，包含一些关键词：Python、编程、自动化。用于验证文本处理功能是否正常工作。"
    result = processor.process(text_input, output_format="text", completeness="detailed")

    if result["status"] == "success":
        assert result["data"] is not None, "文本处理结果不应为空"
        assert "标题" in result["data"], "文本输出应包含标题"
        assert result["confidence"] >= 0.5, "文本处理置信度应至少为 0.5"
        print(f"  ✓ 文本输入处理成功，置信度: {result['confidence']:.0%}")
    else:
        print(f"  ✗ 文本输入处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 测试用例 2: JSON 输入 ----------
    print("\n[测试 2] JSON 输入处理")
    json_input = {
        "title": "测试项目",
        "description": "这是一个JSON格式的测试数据",
        "keywords": ["测试", "JSON", "处理"],
        "items": [1, 2, 3, 4, 5],
        "extra_field": "额外字段",
    }
    result = processor.process(json_input, output_format="json", completeness="quick")

    if result["status"] == "success":
        assert result["data"] is not None, "JSON处理结果不应为空"
        assert "提取结果" in result["data"], "JSON输出应包含提取结果"
        assert "置信度" in result["data"], "JSON输出应包含置信度"
        print(f"  ✓ JSON输入处理成功，置信度: {result['confidence']:.0%}")
    else:
        print(f"  ✗ JSON输入处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 测试用例 3: URL 输入 ----------
    print("\n[测试 3] URL 输入处理")
    url_input = "https://example.com/path/to/page"
    result = processor.process(url_input, output_format="text", completeness="detailed")

    if result["status"] == "success":
        assert result["data"] is not None, "URL处理结果不应为空"
        assert "example.com" in result["data"], "URL输出应包含域名信息"
        print(f"  ✓ URL输入处理成功，置信度: {result['confidence']:.0%}")
    else:
        print(f"  ✗ URL输入处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 测试用例 4: 空输入错误处理 ----------
    print("\n[测试 4] 空输入错误处理")
    result = processor.process("", output_format="text")

    if result["status"] == "error":
        assert result["error_code"] == "E001", "空输入应返回 E001 错误码"
        print(f"  ✓ 空输入正确返回错误码: {result['error_code']}")
    else:
        print("  ✗ 空输入未正确返回错误")
        all_passed = False

    # ---------- 测试用例 5: 批量输入 ----------
    print("\n[测试 5] 批量输入处理")
    batch_input = ["第一条数据", "第二条数据", "第三条数据"]
    result = processor.process(batch_input, output_format="json", completeness="detailed")

    if result["status"] == "success":
        assert result["data"] is not None, "批量处理结果不应为空"
        assert result["confidence"] >= 0.5, "批量处理置信度应至少为 0.5"
        print(f"  ✓ 批量输入处理成功，置信度: {result['confidence']:.0%}")
    else:
        print(f"  ✗ 批量输入处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 测试用例 6: 不支持格式错误处理 ----------
    print("\n[测试 6] 不支持格式错误处理")
    result = processor.process("有效输入", output_format="xml")

    if result["status"] == "error":
        assert result["error_code"] == "E007", "不支持格式应返回 E007 错误码"
        print(f"  ✓ 不支持格式正确返回错误码: {result['error_code']}")
    else:
        print("  ✗ 不支持格式未正确返回错误")
        all_passed = False

    # ---------- 测试用例 7: 置信度标签 ----------
    print("\n[测试 7] 置信度标签验证")
    assert processor._confidence_label(0.95) == "高置信度", ">90% 应为高置信度"
    assert processor._confidence_label(0.87) == "建议复核", "85-90% 应为建议复核"
    assert processor._confidence_label(0.80) == "[需核实]", "<85% 应为需核实"
    print("  ✓ 置信度标签判定正确")

    # ---------- 测试用例 8: 错误码完整性 ----------
    print("\n[测试 8] 错误码完整性")
    expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
    for code in expected_codes:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print(f"  ✓ 全部 {len(expected_codes)} 个错误码定义完整")

    # ---------- 测试用例 9: 复杂 JSON 输入 ----------
    print("\n[测试 9] 复杂 JSON 输入")
    complex_input = {
        "标题": "中文标题测试",
        "描述": "包含中文描述的测试数据",
        "关键词": ["中文", "测试", "关键词"],
        "data": [{"id": 1, "name": "项目A"}, {"id": 2, "name": "项目B"}],
        "count": 2,
    }
    result = processor.process(complex_input, output_format="json")

    if result["status"] == "success":
        assert result["data"]["提取结果"]["标题"] == "中文标题测试", "应正确提取中文标题"
        assert result["data"]["提取结果"]["条目数"] == 2, "应正确统计条目数"
        print(f"  ✓ 复杂JSON处理成功，提取标题: {result['data']['提取结果']['标题']}")
    else:
        print(f"  ✗ 复杂JSON处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 测试用例 10: 长文本输入 ----------
    print("\n[测试 10] 长文本输入")
    long_text = " ".join(["这是第{}个测试词".format(i) for i in range(100)])
    result = processor.process(long_text, output_format="text")

    if result["status"] == "success":
        assert result["confidence"] >= 0.5, "长文本置信度应至少为 0.5"
        print(f"  ✓ 长文本处理成功，长度: {len(long_text)} 字符")
    else:
        print(f"  ✗ 长文本处理失败: {result['error_code']} {result['message']}")
        all_passed = False

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检通过: 全部 10 项测试用例通过 ✓")
    else:
        print("自检失败: 存在未通过的测试用例 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="未命名工具 - 将用户提供的数据转换为结构化结果",
        epilog="示例: python main.py --input '要处理的数据' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（文本、JSON 字符串或 URL）",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=SUPPORTED_OUTPUT_FORMATS,
        help=f"输出格式，默认: {DEFAULT_OUTPUT_FORMAT}",
    )
    parser.add_argument(
        "--completeness", "-c",
        type=str,
        default="detailed",
        choices=["quick", "detailed"],
        help="期望完整度，默认: detailed",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，验证核心逻辑",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="未命名工具 1.0.0",
    )

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理输入
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 参数提供输入数据，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # 尝试解析 JSON 输入
    input_data: Any = args.input
    try:
        parsed_json = json.loads(args.input)
        input_data = parsed_json
    except json.JSONDecodeError:
        pass  # 保持为字符串

    # 创建处理器并处理
    processor = AwesomeProcessor()
    result = processor.process(input_data, output_format=args.format, completeness=args.completeness)

    # 输出结果
    if result["status"] == "success":
        output = result["data"]
        if isinstance(output, str):
            print(output)
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    else:
        print(f"错误 {result['error_code']}: {result['message']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
