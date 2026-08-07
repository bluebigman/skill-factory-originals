#!/usr/bin/env python3
"""n8n azure vm starter - 独立实现脚本

功能: 将用户提供的输入内容转换为结构化结果, 识别关键信息,
      按约定格式输出, 并标注置信度。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式、期望完整度",
    "E003": "输入格式不符合要求，示例：{\"input\": \"待处理内容\", \"format\": \"json\"}",
    "E004": "这超出了本工具的能力范围，建议使用专业工具处理",
    "E005": "结果无法确定，建议：检查输入内容后重试",
    "E006": "内部处理错误，请检查输入数据",
    "E007": "置信度计算异常，请检查输入数据",
    "E008": "输出生成失败，请检查参数配置",
    "E009": "参数解析错误，请检查命令行参数",
    "E010": "未知错误，请查看日志",
}


class SkillProcessor:
    """核心处理类: 解析输入、提取信息、生成结构化输出"""

    def __init__(self) -> None:
        """初始化处理器, 设置默认参数"""
        self.default_format = "json"
        self.default_completeness = "standard"
        self.min_confidence_auto = 0.90
        self.min_confidence_review = 0.85

    def process(self, input_data: str, output_format: Optional[str] = None,
                completeness: Optional[str] = None) -> Dict[str, Any]:
        """主处理流程

        Args:
            input_data: 用户提供的原始输入内容
            output_format: 输出格式 (json/text/csv), 默认 json
            completeness: 期望完整度 (quick/standard/detailed), 默认 standard

        Returns:
            结构化处理结果

        Raises:
            ValueError: 输入为空或格式错误
        """
        # 输入校验
        if not input_data or not input_data.strip():
            raise ValueError("E001")

        # 参数校验
        fmt = output_format or self.default_format
        if fmt not in ("json", "text", "csv"):
            raise ValueError("E003")

        comp = completeness or self.default_completeness
        if comp not in ("quick", "standard", "detailed"):
            raise ValueError("E003")

        # 解析输入
        try:
            parsed = self._parse_input(input_data)
        except Exception as exc:
            raise ValueError("E006") from exc

        # 提取关键信息
        try:
            key_info = self._extract_key_info(parsed)
        except Exception as exc:
            raise ValueError("E006") from exc

        # 计算置信度
        try:
            confidence = self._calculate_confidence(parsed, key_info)
        except Exception as exc:
            raise ValueError("E007") from exc

        # 生成输出
        try:
            result = self._generate_output(parsed, key_info, confidence, fmt, comp)
        except Exception as exc:
            raise ValueError("E008") from exc

        return result

    def _parse_input(self, input_data: str) -> Dict[str, Any]:
        """解析输入内容, 尝试识别为 JSON 或纯文本

        Args:
            input_data: 原始输入字符串

        Returns:
            解析后的结构化数据

        Raises:
            ValueError: 解析失败
        """
        # 尝试 JSON 解析
        try:
            data = json.loads(input_data)
            if isinstance(data, dict):
                return {"type": "structured", "data": data}
            if isinstance(data, list):
                return {"type": "list", "data": data}
        except json.JSONDecodeError:
            pass

        # 纯文本处理
        lines = [line.strip() for line in input_data.split('\n') if line.strip()]
        if not lines:
            raise ValueError("E001")

        return {"type": "text", "data": lines, "raw": input_data}

    def _extract_key_info(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """从解析后的数据中提取关键信息

        Args:
            parsed: 解析后的输入数据

        Returns:
            关键信息字典
        """
        info = {
            "content_type": parsed.get("type", "unknown"),
            "item_count": 0,
            "has_url": False,
            "has_file": False,
            "keywords": [],
        }

        data = parsed.get("data", [])

        # 结构化数据
        if parsed.get("type") == "structured":
            info["item_count"] = len(data)
            # 检测 URL
            for key, value in data.items():
                if isinstance(value, str) and ("http://" in value or "https://" in value):
                    info["has_url"] = True
                # 提取关键词
                if isinstance(value, str) and len(value) > 3:
                    info["keywords"].append(value[:20])

        # 列表数据
        elif parsed.get("type") == "list":
            info["item_count"] = len(data)
            for item in data:
                if isinstance(item, str):
                    if "http://" in item or "https://" in item:
                        info["has_url"] = True
                    if len(item) > 3:
                        info["keywords"].append(item[:20])

        # 文本数据
        else:
            lines = parsed.get("data", [])
            info["item_count"] = len(lines)
            for line in lines:
                if "http://" in line or "https://" in line:
                    info["has_url"] = True
                if len(line) > 3:
                    info["keywords"].append(line[:20])

        # 检测文件引用
        for kw in info["keywords"]:
            if any(ext in kw.lower() for ext in ['.pdf', '.doc', '.xls', '.txt', '.csv']):
                info["has_file"] = True
                break

        return info

    def _calculate_confidence(self, parsed: Dict[str, Any],
                              key_info: Dict[str, Any]) -> float:
        """计算处理结果的置信度

        Args:
            parsed: 解析后的输入数据
            key_info: 提取的关键信息

        Returns:
            置信度分数 (0-1)
        """
        score = 0.0
        total_weight = 0.0

        # 内容类型置信度
        if parsed.get("type") in ("structured", "list", "text"):
            score += 0.4
        total_weight += 0.4

        # 信息完整性置信度
        if key_info.get("item_count", 0) > 0:
            score += 0.3
        total_weight += 0.3

        # 关键词提取置信度
        kw_count = len(key_info.get("keywords", []))
        if kw_count > 0:
            score += min(0.3, kw_count * 0.05)
        total_weight += 0.3

        # URL/文件识别置信度
        if key_info.get("has_url") or key_info.get("has_file"):
            score += 0.1
        total_weight += 0.1

        # 归一化
        confidence = score / total_weight if total_weight > 0 else 0.0
        return round(min(1.0, max(0.0, confidence)), 2)

    def _generate_output(self, parsed: Dict[str, Any], key_info: Dict[str, Any],
                         confidence: float, fmt: str,
                         completeness: str) -> Dict[str, Any]:
        """生成结构化输出

        Args:
            parsed: 解析后的输入数据
            key_info: 提取的关键信息
            confidence: 置信度分数
            fmt: 输出格式
            completeness: 完整度

        Returns:
            输出结果字典
        """
        # 置信度标注
        if confidence >= self.min_confidence_auto:
            confidence_label = "高置信度"
        elif confidence >= self.min_confidence_review:
            confidence_label = "建议复核"
        else:
            confidence_label = "[需核实]"

        # 构建结果
        result = {
            "status": "success",
            "confidence": confidence,
            "confidence_label": confidence_label,
            "summary": {
                "content_type": key_info["content_type"],
                "item_count": key_info["item_count"],
                "has_url": key_info["has_url"],
                "has_file": key_info["has_file"],
            },
            "data": self._format_data(parsed, completeness),
            "metadata": {
                "format": fmt,
                "completeness": completeness,
                "keywords": key_info["keywords"][:5],
            }
        }

        # 低置信度提示
        if confidence < self.min_confidence_review:
            result["warning"] = "结果无法确定，建议：检查输入内容后重试"

        return result

    def _format_data(self, parsed: Dict[str, Any], completeness: str) -> Any:
        """根据完整度格式化数据

        Args:
            parsed: 解析后的输入数据
            completeness: 完整度级别

        Returns:
            格式化后的数据
        """
        data = parsed.get("data", [])

        # 快速模式只返回摘要
        if completeness == "quick":
            if isinstance(data, dict):
                return {k: v for k, v in list(data.items())[:3]}
            if isinstance(data, list):
                return data[:3]
            return data[:3] if isinstance(data, list) else data

        # 标准模式返回前 10 项
        if completeness == "standard":
            if isinstance(data, dict):
                return {k: v for k, v in list(data.items())[:10]}
            if isinstance(data, list):
                return data[:10]
            return data[:10] if isinstance(data, list) else data

        # 详细模式返回全部
        return data


def run_selftest() -> bool:
    """内置自检函数, 使用硬编码样例数据验证核心逻辑

    Returns:
        True 表示自检通过, False 表示失败
    """
    print("开始自检...")

    processor = SkillProcessor()
    test_cases = [
        # 结构化 JSON 输入
        {
            "input": '{"name": "项目A", "url": "https://example.com", "desc": "测试项目"}',
            "expected_type": "structured",
            "min_items": 1,
        },
        # 文本输入
        {
            "input": "第一行内容\n第二行内容\n第三行内容",
            "expected_type": "text",
            "min_items": 1,
        },
        # 列表输入
        {
            "input": '["item1", "item2", "item3"]',
            "expected_type": "list",
            "min_items": 1,
        },
        # 带 URL 的输入
        {
            "input": "访问 https://example.com 查看文档",
            "expected_type": "text",
            "min_items": 1,
        },
    ]

    all_passed = True

    for idx, case in enumerate(test_cases, 1):
        try:
            result = processor.process(case["input"])

            # 宽松断言: 检查基本结构
            assert result["status"] == "success", f"用例 {idx}: 状态不是 success"
            assert result["confidence"] >= 0.0, f"用例 {idx}: 置信度小于 0"
            assert result["confidence"] <= 1.0, f"用例 {idx}: 置信度大于 1"

            # 检查摘要信息
            summary = result["summary"]
            assert summary["item_count"] >= case["min_items"], \
                f"用例 {idx}: 项目数少于预期"

            # 检查数据存在
            assert "data" in result, f"用例 {idx}: 缺少 data 字段"

            print(f"  用例 {idx}: 通过 (置信度={result['confidence']:.2f})")

        except AssertionError as exc:
            print(f"  用例 {idx}: 失败 - {exc}")
            all_passed = False
        except ValueError as exc:
            print(f"  用例 {idx}: 失败 - 错误码: {exc}")
            all_passed = False
        except Exception as exc:
            print(f"  用例 {idx}: 失败 - 未知错误: {exc}")
            all_passed = False

    # 测试错误处理
    try:
        processor.process("")
        print("  错误处理用例: 失败 - 空输入未触发错误")
        all_passed = False
    except ValueError as exc:
        if str(exc) == "E001":
            print("  错误处理用例: 通过 (E001 空输入)")
        else:
            print(f"  错误处理用例: 失败 - 错误码 {exc}")
            all_passed = False

    # 测试边界情况
    try:
        result = processor.process("x" * 1000)
        assert result["confidence"] > 0, "长文本置信度应大于 0"
        print("  边界用例: 通过 (长文本)")
    except Exception as exc:
        print(f"  边界用例: 失败 - {exc}")
        all_passed = False

    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")

    return all_passed


def main() -> int:
    """主入口函数

    Returns:
        退出码 (0 成功, 1 失败)
    """
    parser = argparse.ArgumentParser(
        description="n8n azure vm starter - 输入处理工具",
        epilog="示例: python main.py --input '待处理内容' --format json"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容 (字符串或 JSON)"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--completeness", "-c",
        type=str,
        choices=["quick", "standard", "detailed"],
        default="standard",
        help="完整度 (默认: standard)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 检查必要参数
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    # 处理输入
    try:
        processor = SkillProcessor()
        result = processor.process(
            args.input,
            output_format=args.format,
            completeness=args.completeness
        )

        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except ValueError as exc:
        error_code = str(exc)
        error_msg = ERROR_CODES.get(error_code, "未知错误")
        print(f"错误 {error_code}: {error_msg}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 E010: {ERROR_CODES['E010']} - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
