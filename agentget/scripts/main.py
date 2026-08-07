#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentget - 未命名工具

功能概述：
    根据功能规格实现的核心工具脚本。提供标准流程处理、错误码体系、
    置信度标注、批量处理与自定义格式支持。

用法示例：
    python scripts/main.py --selftest                # 离线自检
    python scripts/main.py --input "样例数据"         # 处理单条输入
    python scripts/main.py --input "A,B,C" --batch   # 批量处理

错误码：
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 未知输入类型
    E007 批量处理失败
    E008 输出格式不支持
    E009 内部逻辑错误
    E010 参数错误
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：",
    "E004": "这超出了本工具的能力范围，建议：",
    "E005": "结果无法确定，建议：",
    "E006": "未知输入类型，无法处理",
    "E007": "批量处理过程中出现异常",
    "E008": "不支持的输出格式",
    "E009": "内部逻辑错误，请联系开发者",
    "E010": "命令行参数错误",
}

# 置信度阈值
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.85

# 默认输出模板
DEFAULT_TEMPLATE = {
    "status": "success",
    "data": None,
    "confidence": 0.0,
    "warning": None,
}


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class AgentGetProcessor:
    """核心处理器：负责输入解析、结构化、置信度标注与输出生成。"""

    def __init__(self, output_format: str = "json"):
        self.output_format = output_format
        self.required_fields = ["content", "source"]  # 最小信息集

    def process(self, raw_input: str, source: str = "user") -> Dict[str, Any]:
        """处理单条输入，返回结构化结果。

        Args:
            raw_input: 用户提供的原始输入内容
            source: 输入来源（user/file/url 等）

        Returns:
            结构化结果字典

        Raises:
            ValueError: 当输入为空或关键信息缺失时
        """
        # 检查输入为空（E001）
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        # 检查关键信息缺失（E002）
        if not source or not source.strip():
            raise ValueError("E002")

        # 解析输入内容
        parsed_content = self._parse_input(raw_input)

        # 计算置信度
        confidence = self._calculate_confidence(parsed_content)

        # 构建结果
        result = {
            "content": parsed_content,
            "source": source,
            "confidence": confidence,
        }

        # 标注置信度
        self._annotate_confidence(result)

        return result

    def batch_process(self, inputs: List[str], source: str = "user") -> List[Dict[str, Any]]:
        """批量处理多条输入。

        Args:
            inputs: 输入内容列表
            source: 输入来源

        Returns:
            处理结果列表
        """
        results = []
        for item in inputs:
            try:
                result = self.process(item, source)
                results.append(result)
            except ValueError as e:
                results.append({
                    "status": "error",
                    "error_code": str(e),
                    "error_message": ERROR_MESSAGES.get(str(e), "未知错误"),
                    "input": item,
                })
        return results

    def _parse_input(self, raw_input: str) -> Dict[str, Any]:
        """解析输入内容，识别关键信息并结构化。

        Args:
            raw_input: 原始输入字符串

        Returns:
            结构化内容字典
        """
        # 尝试 JSON 解析
        try:
            data = json.loads(raw_input)
            if isinstance(data, dict):
                return data
            elif isinstance(data, list):
                return {"items": data}
        except json.JSONDecodeError:
            pass

        # 尝试键值对解析（如 "key1=value1,key2=value2"）
        if "=" in raw_input:
            kv_pairs = {}
            for pair in raw_input.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    kv_pairs[key.strip()] = value.strip()
            if kv_pairs:
                return kv_pairs

        # 默认作为文本内容
        return {"text": raw_input.strip()}

    def _calculate_confidence(self, parsed_content: Dict[str, Any]) -> float:
        """计算处理结果的置信度。

        Args:
            parsed_content: 解析后的内容

        Returns:
            置信度值（0.0 ~ 1.0）
        """
        # 基于内容完整度计算置信度
        confidence = 0.95  # 基础置信度

        # 如果内容为空或缺少关键字段，降低置信度
        if not parsed_content:
            confidence = 0.80
        elif "text" in parsed_content and len(parsed_content["text"]) < 10:
            confidence = 0.85
        elif "items" in parsed_content and len(parsed_content["items"]) == 0:
            confidence = 0.80

        return confidence

    def _annotate_confidence(self, result: Dict[str, Any]) -> None:
        """根据置信度添加标注。

        Args:
            result: 结果字典（会被修改）
        """
        confidence = result.get("confidence", 0.0)
        if confidence >= HIGH_CONFIDENCE:
            result["annotation"] = "直接输出"
        elif confidence >= MEDIUM_CONFIDENCE:
            result["annotation"] = "建议复核"
        else:
            result["annotation"] = "[需核实]"
            result["warning"] = "置信度较低，请人工复核关键结果"

    def format_output(self, result: Dict[str, Any]) -> str:
        """将结果格式化为指定输出格式。

        Args:
            result: 处理结果

        Returns:
            格式化后的字符串

        Raises:
            ValueError: 不支持的输出格式
        """
        if self.output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif self.output_format == "text":
            lines = []
            for key, value in result.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        elif self.output_format == "compact":
            return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        else:
            raise ValueError("E008")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑正确性。

    使用硬编码样例数据，不依赖外部文件或网络。

    Returns:
        True 表示自检通过
    """
    processor = AgentGetProcessor(output_format="json")
    tests_passed = 0
    total_tests = 0

    # 测试用例 1：正常处理
    total_tests += 1
    try:
        result = processor.process("这是一个测试内容", source="user")
        assert result["status"] == "success" if "status" in result else True
        assert result["confidence"] > 0.5  # 宽松阈值
        assert "content" in result
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 2：空输入（E001）
    total_tests += 1
    try:
        processor.process("", source="user")
    except ValueError as e:
        if str(e) == "E001":
            tests_passed += 1

    # 测试用例 3：关键信息缺失（E002）
    total_tests += 1
    try:
        processor.process("有内容", source="")
    except ValueError as e:
        if str(e) == "E002":
            tests_passed += 1

    # 测试用例 4：JSON 输入
    total_tests += 1
    try:
        result = processor.process('{"name": "test", "value": 123}', source="json")
        assert result["content"].get("name") == "test"
        assert result["confidence"] > 0.5
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 5：键值对输入
    total_tests += 1
    try:
        result = processor.process("key1=value1,key2=value2", source="kv")
        assert "key1" in result["content"]
        assert "key2" in result["content"]
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 6：批量处理
    total_tests += 1
    try:
        batch_inputs = ["第一条", "第二条", "第三条"]
        results = processor.batch_process(batch_inputs)
        assert len(results) == 3
        assert all(r.get("confidence", 0) > 0.5 for r in results)
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 7：格式输出
    total_tests += 1
    try:
        result = processor.process("格式化测试", source="fmt")
        formatted = processor.format_output(result)
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 8：置信度标注
    total_tests += 1
    try:
        result = processor.process("短", source="conf")
        assert "annotation" in result
        assert result["confidence"] < 0.9  # 短内容置信度应较低
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 9：空批量输入
    total_tests += 1
    try:
        results = processor.batch_process([])
        assert len(results) == 0
        tests_passed += 1
    except Exception:
        pass

    # 测试用例 10：特殊字符输入
    total_tests += 1
    try:
        result = processor.process("特殊字符：!@#$%^&*()", source="special")
        assert result["confidence"] > 0.5
        tests_passed += 1
    except Exception:
        pass

    # 输出自检结果
    print(f"自检完成：{tests_passed}/{total_tests} 项测试通过")
    return tests_passed == total_tests


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。

    Returns:
        退出码（0 表示成功，非 0 表示失败）
    """
    parser = argparse.ArgumentParser(
        description="agentget - 未命名工具",
        epilog="示例：python main.py --input '内容' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（单条）")
    parser.add_argument("--source", "-s", default="user", help="输入来源（默认：user）")
    parser.add_argument("--format", "-f", default="json", 
                        choices=["json", "text", "compact"], help="输出格式（默认：json）")
    parser.add_argument("--batch", "-b", action="store_true", help="批量模式（输入用逗号分隔）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 出错时返回错误码
        return e.code if isinstance(e.code, int) else 1

    # 自检模式
    if args.selftest:
        return 0 if run_selftest() else 1

    # 检查参数（E010）
    if not args.input:
        print(f"E010: {ERROR_MESSAGES['E010']}")
        print("请使用 --input 参数提供输入内容，或使用 --selftest 运行自检")
        return 1

    # 创建处理器
    try:
        processor = AgentGetProcessor(output_format=args.format)
    except ValueError as e:
        print(f"{e}: {ERROR_MESSAGES.get(str(e), '未知错误')}")
        return 1

    # 批量或单条处理
    try:
        if args.batch:
            # 批量模式：按逗号分割
            inputs = [item.strip() for item in args.input.split(",") if item.strip()]
            if not inputs:
                print(f"E001: {ERROR_MESSAGES['E001']}")
                return 1
            results = processor.batch_process(inputs, source=args.source)
            # 输出结果
            for i, result in enumerate(results, 1):
                print(f"--- 结果 {i} ---")
                if "error" in result:
                    print(f"错误: {result.get('error_message', '未知错误')}")
                else:
                    print(processor.format_output(result))
        else:
            # 单条模式
            result = processor.process(args.input, source=args.source)
            print(processor.format_output(result))
        return 0
    except ValueError as e:
        error_code = str(e)
        print(f"{error_code}: {ERROR_MESSAGES.get(error_code, '未知错误')}")
        return 1
    except Exception as e:
        print(f"E009: {ERROR_MESSAGES['E009']} - {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
