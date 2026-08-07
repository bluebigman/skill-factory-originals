#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mcafee-com-activate 技能实现脚本

本脚本仅依据功能规格独立实现，采用 clean-room 方式编写。
提供命令行入口与离线自检功能（--selftest）。
"""

import argparse
import sys
import re
from typing import Any, Dict, List, Optional

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "输出格式错误",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能异常基类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.msg = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.msg}")


class InputParser:
    """输入解析器：将用户输入转换为结构化数据"""

    @staticmethod
    def parse(data: Any) -> Dict[str, Any]:
        """解析输入，返回结构化字典

        支持：字符串、字典、列表。其他类型报 E003。
        """
        if data is None:
            raise SkillError("E001")

        if isinstance(data, str):
            # 简单键值对解析：key=value;key2=value2
            result = {}
            parts = [p.strip() for p in data.split(";") if p.strip()]
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    result[k.strip()] = v.strip()
                else:
                    # 无等号视为纯文本
                    result["text"] = part
            if not result:
                raise SkillError("E003", "字符串无法解析为键值对")
            return result

        if isinstance(data, dict):
            return data

        if isinstance(data, (list, tuple)):
            # 列表转为索引字典
            return {str(i): v for i, v in enumerate(data)}

        raise SkillError("E003", f"不支持的类型: {type(data).__name__}")


class ConfidenceCalculator:
    """置信度计算器"""

    @staticmethod
    def calculate(result: Dict[str, Any]) -> float:
        """计算置信度（0-100）

        规则：
        - 有明确键值对且无缺失：≥90
        - 有部分未知值：85-90
        - 结构不完整或含模糊内容：<85
        """
        if not result:
            return 0.0

        # 计算完整度
        total_keys = len(result)
        if total_keys == 0:
            return 0.0

        # 检查是否有空值或模糊标记
        fuzzy_count = 0
        for v in result.values():
            if v is None or (isinstance(v, str) and not v.strip()):
                fuzzy_count += 1
            elif isinstance(v, str) and v.startswith("?"):
                fuzzy_count += 1

        # 基础置信度
        base = 90.0
        # 每个模糊项扣分
        base -= fuzzy_count * 5
        # 结果太少（<2个键）扣分
        if total_keys < 2:
            base -= 10

        # 限制范围
        return max(0.0, min(100.0, base))


class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format(result: Dict[str, Any], confidence: float, fmt: str = "text") -> str:
        """按指定格式输出结果

        支持：text / json / table
        """
        if fmt == "json":
            import json
            return json.dumps({"result": result, "confidence": confidence}, ensure_ascii=False, indent=2)

        if fmt == "table":
            lines = ["字段\t值"]
            for k, v in result.items():
                lines.append(f"{k}\t{v}")
            lines.append(f"置信度\t{confidence:.1f}%")
            return "\n".join(lines)

        # 默认 text
        lines = []
        for k, v in result.items():
            lines.append(f"{k}: {v}")
        lines.append(f"置信度: {confidence:.1f}%")
        if confidence < 85:
            lines.append("[需核实] 部分内容不确定")
        elif confidence < 90:
            lines.append("建议复核")
        return "\n".join(lines)


class SkillProcessor:
    """核心处理器：执行标准流程"""

    def __init__(self):
        self.parser = InputParser()
        self.conf_calc = ConfidenceCalculator()
        self.formatter = OutputFormatter()

    def process(
        self,
        user_input: Any,
        output_format: str = "text",
        extra_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """执行主流程，返回结构化结果

        参数：
            user_input: 用户提供的数据
            output_format: text/json/table
            extra_fields: 需要额外提取的字段列表

        返回：
            {"result": {...}, "confidence": float, "output": str}
        """
        # Step 1: 解析输入
        parsed = self.parser.parse(user_input)

        # Step 2: 检查关键信息
        if not parsed:
            raise SkillError("E002", "解析结果为空，缺少关键信息")

        # Step 3: 提取额外字段（若指定）
        if extra_fields:
            for field in extra_fields:
                if field not in parsed:
                    parsed[field] = None  # 标记缺失

        # Step 4: 计算置信度
        confidence = self.conf_calc.calculate(parsed)

        # Step 5: 格式化输出
        output = self.formatter.format(parsed, confidence, output_format)

        return {
            "result": parsed,
            "confidence": confidence,
            "output": output,
        }

    def batch_process(
        self,
        inputs: List[Any],
        output_format: str = "text",
    ) -> List[Dict[str, Any]]:
        """批量处理多个输入"""
        results = []
        for i, item in enumerate(inputs):
            try:
                results.append(self.process(item, output_format))
            except SkillError as e:
                # 记录错误但不中断
                results.append({"error": e.code, "error_msg": e.msg, "index": i})
        return results


class SelfTest:
    """离线自检模块：使用内置样例数据验证核心逻辑"""

    @staticmethod
    def run() -> bool:
        """执行自检，全部通过返回 True，否则抛出异常"""
        processor = SkillProcessor()
        print("=== 开始自检 ===")

        # 测试 1: 正常字符串解析
        print("测试 1: 字符串解析...")
        r1 = processor.process("name=test;type=demo;count=3", "text")
        assert r1["confidence"] > 80, f"置信度应大于80，实际 {r1['confidence']}"
        assert "name" in r1["result"], "结果应包含 name 字段"
        assert r1["result"]["name"] == "test", "name 字段值错误"
        print("  通过 ✓")

        # 测试 2: 字典输入
        print("测试 2: 字典输入...")
        r2 = processor.process({"id": 1, "value": "abc"}, "json")
        assert r2["confidence"] > 85, f"置信度应大于85，实际 {r2['confidence']}"
        assert '"id"' in r2["output"], "JSON 输出应包含 id"
        print("  通过 ✓")

        # 测试 3: 空输入应报 E001
        print("测试 3: 空输入错误处理...")
        try:
            processor.process(None)
            assert False, "应抛出 E001 错误"
        except SkillError as e:
            assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("  通过 ✓")

        # 测试 4: 批量处理
        print("测试 4: 批量处理...")
        batch = ["a=1;b=2", {"x": 10}, None]
        results = processor.batch_process(batch)
        assert len(results) == 3, "批量处理应返回3个结果"
        assert results[2]["error"] == "E001", "第三个输入应报 E001"
        print("  通过 ✓")

        # 测试 5: 置信度分级
        print("测试 5: 置信度分级...")
        # 完整数据
        r_high = processor.process("a=1;b=2;c=3", "text")
        # 部分缺失
        r_low = processor.process("a=1;b=", "text")
        assert r_high["confidence"] > r_low["confidence"], "完整数据置信度应更高"
        print("  通过 ✓")

        # 测试 6: 表格输出
        print("测试 6: 表格输出...")
        r_table = processor.process("a=1;b=2", "table")
        assert "a\t1" in r_table["output"], "表格输出应包含 a=1"
        print("  通过 ✓")

        print("=== 全部自检通过 ===")
        return True


def main() -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="mcafee-com-activate 技能实现",
        epilog="示例: python main.py --input 'name=test;type=demo' --format json",
    )
    parser.add_argument("--input", help="输入数据（字符串，格式: key=value;key2=value2）")
    parser.add_argument("--format", choices=["text", "json", "table"], default="text", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--fields", nargs="*", help="需要提取的额外字段列表")
    parser.add_argument("--batch", nargs="+", help="批量输入（多个字符串）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            SelfTest.run()
            return 0
        except Exception as e:
            print(f"自检失败: {e}", file=sys.stderr)
            return 1

    # 参数校验
    if not args.input and not args.batch:
        print(f"[E007] 参数错误: 请提供 --input 或 --batch", file=sys.stderr)
        return 1

    processor = SkillProcessor()

    try:
        if args.batch:
            # 批量模式
            results = processor.batch_process(args.batch, args.format)
            for i, r in enumerate(results):
                print(f"--- 结果 {i+1} ---")
                if "error" in r:
                    print(f"错误: [{r['error']}] {r['error_msg']}")
                else:
                    print(r["output"])
        else:
            # 单条模式
            result = processor.process(args.input, args.format, args.fields)
            print(result["output"])
        return 0
    except SkillError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
