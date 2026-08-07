#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-agent-master-cyber-skills-list 独立实现
=========================================
基于功能规格的 clean-room 重写脚本。

功能概述:
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

用法:
    python main.py --selftest          # 运行内置自检
    python main.py --input "文本"       # 处理单条输入
    python main.py --batch "a,b,c"     # 批量处理
    python main.py --format json       # 自定义输出格式(json/text)

错误码:
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 参数解析失败
    E007 输出格式不支持
    E008 批量输入为空
    E009 自检数据异常
    E010 未知内部错误
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
VERSION = "1.0.0"
DEFAULT_CONFIDENCE_HIGH = 0.95
DEFAULT_CONFIDENCE_MEDIUM = 0.88
DEFAULT_CONFIDENCE_LOW = 0.80

# 支持的关键字段列表（用于识别输入中的关键信息）
KEY_FIELDS = [
    "name", "type", "source", "target", "action",
    "data", "url", "file", "format", "priority",
]


# ============================================================
# 核心逻辑类
# ============================================================
class DataProcessor:
    """数据处理核心类"""

    def __init__(self) -> None:
        """初始化处理器"""
        self.errors: List[Dict[str, str]] = []

    def process_single(self, raw_input: str, output_format: str = "text") -> Dict[str, Any]:
        """
        处理单条输入数据

        参数:
            raw_input: 原始输入字符串
            output_format: 输出格式 (text/json)

        返回:
            包含处理结果和置信度的字典

        错误:
            E001: 输入为空
            E003: 输入格式错误
            E007: 输出格式不支持
        """
        # 检查输入是否为空
        if not raw_input or not raw_input.strip():
            return self._make_error("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

        # 检查输出格式
        if output_format not in ("text", "json"):
            return self._make_error("E007", f"不支持的输出格式: {output_format}，支持: text, json")

        try:
            # 解析输入内容
            parsed_data = self._parse_input(raw_input)

            # 识别关键信息
            key_info = self._extract_key_info(parsed_data)

            # 计算置信度
            confidence = self._calculate_confidence(parsed_data, key_info)

            # 生成结构化结果
            result = {
                "original": raw_input.strip(),
                "parsed": parsed_data,
                "key_info": key_info,
                "confidence": confidence,
                "confidence_label": self._get_confidence_label(confidence),
                "format": output_format,
            }

            # 根据置信度添加提示
            if confidence < 0.85:
                result["warning"] = "[需核实] 置信度过低，请人工复核关键结果"
            elif confidence < 0.90:
                result["warning"] = "建议复核: 部分信息可能存在偏差"

            return result

        except ValueError as e:
            return self._make_error("E003", f"输入格式不符合要求: {str(e)}")
        except Exception as e:
            return self._make_error("E010", f"内部错误: {str(e)}")

    def process_batch(self, inputs: List[str], output_format: str = "text") -> List[Dict[str, Any]]:
        """
        批量处理多条输入

        参数:
            inputs: 输入字符串列表
            output_format: 输出格式

        返回:
            处理结果列表

        错误:
            E008: 批量输入为空
        """
        if not inputs:
            return [self._make_error("E008", "批量输入为空，请提供至少一条输入")]

        results = []
        for item in inputs:
            result = self.process_single(item, output_format)
            results.append(result)
        return results

    def _parse_input(self, raw_input: str) -> Dict[str, Any]:
        """
        解析输入内容

        尝试将输入解析为:
        - JSON 格式 (如果输入是 JSON)
        - 键值对格式 (如 key=value, 用逗号或分号分隔)
        - 纯文本 (作为 data 字段)

        参数:
            raw_input: 原始输入字符串

        返回:
            解析后的字典

        错误:
            E003: 输入格式错误
        """
        raw_input = raw_input.strip()

        # 尝试解析 JSON
        if raw_input.startswith("{") and raw_input.endswith("}"):
            try:
                data = json.loads(raw_input)
                if isinstance(data, dict):
                    return data
                else:
                    raise ValueError("JSON 必须是对象类型")
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {str(e)}")

        # 尝试解析键值对
        kv_pattern = re.compile(r'(\w+)\s*=\s*([^,;]+)')
        matches = kv_pattern.findall(raw_input)
        if matches:
            data = {}
            for key, value in matches:
                data[key.strip()] = value.strip()
            # 检查是否有未匹配的内容
            remainder = kv_pattern.sub('', raw_input).strip()
            if remainder:
                data["extra"] = remainder
            return data

        # 纯文本格式
        return {"data": raw_input}

    def _extract_key_info(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        识别输入中的关键信息

        参数:
            parsed_data: 解析后的数据字典

        返回:
            关键信息字典
        """
        key_info = {}

        # 遍历已知的关键字段
        for field in KEY_FIELDS:
            if field in parsed_data:
                value = parsed_data[field]
                # 检查值是否有效
                if value is not None and str(value).strip():
                    key_info[field] = value

        # 如果没有找到任何关键字段，尝试从 data 字段提取
        if not key_info and "data" in parsed_data:
            data_str = str(parsed_data["data"])
            # 简单提取可能的关键信息
            for field in ["type", "name", "source"]:
                pattern = re.compile(rf'{field}[\s:：]+([^\s,，;；]+)')
                match = pattern.search(data_str)
                if match:
                    key_info[field] = match.group(1)

        return key_info

    def _calculate_confidence(self, parsed_data: Dict[str, Any], key_info: Dict[str, Any]) -> float:
        """
        计算置信度

        规则:
        - 完整解析且关键信息完整: 高置信度 (>=0.90)
        - 部分关键信息缺失: 中等置信度 (0.85-0.90)
        - 信息不完整或模糊: 低置信度 (<0.85)

        参数:
            parsed_data: 解析后的数据
            key_info: 提取的关键信息

        返回:
            置信度值 (0.0 - 1.0)
        """
        # 基础置信度
        base = 0.80

        # 根据解析质量调整
        if isinstance(parsed_data, dict) and len(parsed_data) > 0:
            if "data" in parsed_data and len(parsed_data) == 1:
                # 只有 data 字段，可能是纯文本
                base += 0.05
            else:
                # 结构化数据
                base += 0.10

        # 根据关键信息完整度调整
        if key_info:
            # 有关键信息
            base += 0.05
            if len(key_info) >= 3:
                base += 0.05

        # 限制在合理范围
        return min(max(base, 0.0), 1.0)

    def _get_confidence_label(self, confidence: float) -> str:
        """
        获取置信度标签

        参数:
            confidence: 置信度值

        返回:
            置信度标签
        """
        if confidence >= 0.90:
            return "高置信度"
        elif confidence >= 0.85:
            return "中置信度"
        else:
            return "低置信度"

    def _make_error(self, code: str, message: str) -> Dict[str, Any]:
        """
        构造错误结果

        参数:
            code: 错误码
            message: 错误信息

        返回:
            错误结果字典
        """
        return {
            "error_code": code,
            "error_message": message,
            "success": False,
        }

    def format_output(self, result: Dict[str, Any], output_format: str = "text") -> str:
        """
        格式化输出结果

        参数:
            result: 处理结果字典
            output_format: 输出格式

        返回:
            格式化后的字符串
        """
        # 检查是否有错误
        if "error_code" in result:
            return f"[{result['error_code']}] {result['error_message']}"

        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)

        # 文本格式
        lines = []
        lines.append("=" * 50)
        lines.append(f"处理结果 (置信度: {result['confidence']:.0%} - {result['confidence_label']})")
        lines.append("=" * 50)

        # 输出解析数据
        if "parsed" in result:
            lines.append("\n[解析数据]")
            for key, value in result["parsed"].items():
                lines.append(f"  {key}: {value}")

        # 输出关键信息
        if "key_info" in result and result["key_info"]:
            lines.append("\n[关键信息]")
            for key, value in result["key_info"].items():
                lines.append(f"  {key}: {value}")

        # 输出警告
        if "warning" in result:
            lines.append(f"\n[提示] {result['warning']}")

        lines.append("=" * 50)
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检

    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。

    返回:
        0 成功, 非 0 失败
    """
    print("开始自检...")
    processor = DataProcessor()
    passed = 0
    failed = 0

    # 测试用例 1: 正常文本输入
    print("\n[测试 1] 正常文本输入")
    result = processor.process_single("这是一条测试数据，type=security, source=test")
    assert "error_code" not in result, f"不应有错误: {result}"
    assert result["confidence"] > 0.8, f"置信度应大于0.8: {result['confidence']}"
    assert "key_info" in result, "应包含关键信息"
    assert len(result["key_info"]) > 0, "关键信息不应为空"
    print(f"  通过 - 置信度: {result['confidence']:.0%}")
    passed += 1

    # 测试用例 2: JSON 输入
    print("\n[测试 2] JSON 输入")
    json_input = '{"name": "test", "type": "scan", "priority": "high"}'
    result = processor.process_single(json_input)
    assert "error_code" not in result, f"不应有错误: {result}"
    assert result["parsed"]["name"] == "test", "JSON 解析错误"
    assert result["confidence"] >= 0.9, f"结构化输入置信度应较高: {result['confidence']}"
    print(f"  通过 - 置信度: {result['confidence']:.0%}")
    passed += 1

    # 测试用例 3: 空输入
    print("\n[测试 3] 空输入")
    result = processor.process_single("")
    assert result.get("error_code") == "E001", f"应返回 E001: {result}"
    print("  通过 - 正确返回 E001")
    passed += 1

    # 测试用例 4: 批量处理
    print("\n[测试 4] 批量处理")
    batch_input = ["测试数据1", "测试数据2", "测试数据3"]
    results = processor.process_batch(batch_input)
    assert len(results) == 3, f"应返回3个结果: {len(results)}"
    for r in results:
        assert "error_code" not in r, f"批量处理不应有错误: {r}"
    print("  通过 - 批量处理成功")
    passed += 1

    # 测试用例 5: 键值对输入
    print("\n[测试 5] 键值对输入")
    result = processor.process_single("name=test, action=scan, target=192.168.1.1")
    assert "error_code" not in result, f"不应有错误: {result}"
    assert "name" in result["key_info"], "应识别 name 字段"
    assert "action" in result["key_info"], "应识别 action 字段"
    print(f"  通过 - 识别到 {len(result['key_info'])} 个关键字段")
    passed += 1

    # 测试用例 6: 输出格式化
    print("\n[测试 6] 输出格式化")
    result = processor.process_single("测试数据")
    text_output = processor.format_output(result, "text")
    json_output = processor.format_output(result, "json")
    assert "处理结果" in text_output, "文本输出应包含标题"
    assert json.loads(json_output), "JSON 输出应可解析"
    print("  通过 - 两种格式输出正常")
    passed += 1

    # 测试用例 7: 错误处理
    print("\n[测试 7] 错误处理")
    # 无效格式
    result = processor.process_single("测试", "invalid_format")
    assert result.get("error_code") == "E007", f"应返回 E007: {result}"
    # 空批量
    results = processor.process_batch([])
    assert results[0].get("error_code") == "E008", f"应返回 E008: {results}"
    print("  通过 - 错误处理正确")
    passed += 1

    # 测试用例 8: 置信度标签
    print("\n[测试 8] 置信度标签")
    # 高置信度
    result = processor.process_single('{"name": "a", "type": "b", "source": "c", "target": "d"}')
    assert result["confidence_label"] == "高置信度", f"应为高置信度: {result}"
    # 低置信度
    result = processor.process_single("简单文本")
    assert result["confidence_label"] in ("中置信度", "低置信度"), f"置信度标签不合理: {result}"
    print("  通过 - 置信度标签正确")
    passed += 1

    # 测试用例 9: 批量空输入
    print("\n[测试 9] 批量空输入")
    results = processor.process_batch(["", "有效数据"])
    assert results[0].get("error_code") == "E001", f"第一个应返回 E001: {results[0]}"
    assert "error_code" not in results[1], f"第二个不应有错误: {results[1]}"
    print("  通过 - 批量中个别错误正确处理")
    passed += 1

    # 测试用例 10: URL 输入
    print("\n[测试 10] URL 输入")
    result = processor.process_single("https://example.com/data")
    assert "error_code" not in result, f"不应有错误: {result}"
    assert "data" in result["key_info"] or "url" in result["key_info"], "应识别 URL 信息"
    print(f"  通过 - URL 处理成功")
    passed += 1

    # 汇总
    print(f"\n{'='*50}")
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print(f"{'='*50}")

    if failed > 0:
        return 1
    return 0


# ============================================================
# 主程序
# ============================================================
def main() -> int:
    """
    主程序入口

    返回:
        退出码 (0 成功, 非 0 失败)
    """
    parser = argparse.ArgumentParser(
        description="ai-agent-master-cyber-skills-list - 数据处理工具",
        epilog="示例: python main.py --input '处理这条数据' --format json"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--input", type=str, help="输入文本")
    parser.add_argument("--batch", type=str, help="批量输入，用逗号分隔")
    parser.add_argument("--format", type=str, choices=["text", "json"], default="text",
                        help="输出格式 (默认: text)")
    parser.add_argument("--version", action="store_true", help="显示版本信息")

    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"[E006] 参数解析失败: {str(e)}")
        return 1

    # 版本信息
    if args.version:
        print(f"ai-agent-master-cyber-skills-list v{VERSION}")
        return 0

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 创建处理器
    processor = DataProcessor()

    # 处理输入
    if args.input:
        # 单条处理
        result = processor.process_single(args.input, args.format)
        output = processor.format_output(result, args.format)
        print(output)
        return 0
    elif args.batch:
        # 批量处理
        inputs = [x.strip() for x in args.batch.split(",") if x.strip()]
        results = processor.process_batch(inputs, args.format)
        for result in results:
            output = processor.format_output(result, args.format)
            print(output)
            print()  # 空行分隔
        return 0
    else:
        # 无输入参数，显示帮助
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
