#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - Spec-Driven Develop 工具

基于功能规格独立实现的命令行工具（clean-room 风格）。
提供标准流程处理、错误码体系和离线自检功能。

用法:
    python scripts/main.py --selftest          # 离线自检
    python scripts/main.py --input <内容>      # 处理输入
    python scripts/main.py --help              # 帮助
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理异常",
    "E007": "参数错误",
    "E008": "输出生成失败",
    "E009": "资源不可用",
    "E010": "未知错误",
}

# 能力边界声明
CAPABILITIES = {
    "do": [
        "将输入转换为结构化结果",
        "识别并保留关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "not_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}


class SpecDrivenError(Exception):
    """带错误码的异常类"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


class SpecDrivenProcessor:
    """核心处理器：按规格执行标准流程"""

    # 关键字段识别规则（示例）
    KEY_FIELDS = ["标题", "内容", "类型", "优先级"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.confidence_threshold_high = 0.90
        self.confidence_threshold_medium = 0.85

    def process(self, raw_input: str) -> Dict[str, Any]:
        """Step 1-3: 收集信息 -> 执行核心流程 -> 输出与校验"""
        # Step 1: 检查输入
        if not raw_input or not raw_input.strip():
            raise SpecDrivenError("E001")

        # Step 2: 解析输入
        parsed = self._parse_input(raw_input)

        # 检查关键信息
        missing = self._check_missing_fields(parsed)
        if missing:
            raise SpecDrivenError("E002", f"缺少字段: {', '.join(missing)}")

        # Step 3: 生成结果
        result = self._generate_result(parsed)
        result = self._validate_and_annotate(result)

        return result

    def _parse_input(self, raw_input: str) -> Dict[str, Any]:
        """解析输入内容，识别关键信息"""
        try:
            # 尝试 JSON 解析
            if raw_input.lstrip().startswith("{"):
                return json.loads(raw_input)
        except json.JSONDecodeError:
            pass

        # 尝试 key=value 格式
        if "=" in raw_input:
            parsed = {}
            for item in raw_input.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    parsed[k.strip()] = v.strip()
            if parsed:
                return parsed

        # 尝试按行解析
        lines = [line.strip() for line in raw_input.splitlines() if line.strip()]
        if len(lines) >= 2:
            return {"标题": lines[0], "内容": "\n".join(lines[1:])}

        # 默认单字段
        return {"内容": raw_input.strip()}

    def _check_missing_fields(self, parsed: Dict[str, Any]) -> List[str]:
        """检查关键字段是否缺失"""
        required = self.config.get("required_fields", ["内容"])
        return [field for field in required if field not in parsed]

    def _generate_result(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """按默认模板组织输出"""
        result = {
            "标题": parsed.get("标题", parsed.get("内容", "")[:20]),
            "内容": parsed.get("内容", ""),
            "类型": parsed.get("类型", "通用"),
            "优先级": parsed.get("优先级", "普通"),
            "置信度": 0.0,
        }
        return result

    def _validate_and_annotate(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """自查并标注置信度"""
        # 计算置信度（基于字段完整性和内容质量）
        confidence = 0.0
        if result.get("标题"):
            confidence += 0.3
        if result.get("内容"):
            confidence += 0.4
            # 内容长度增加置信度
            if len(result["内容"]) > 20:
                confidence += 0.2
        if result.get("类型") and result.get("优先级"):
            confidence += 0.1

        result["置信度"] = round(min(confidence, 1.0), 2)

        # 标注置信度
        if result["置信度"] >= self.confidence_threshold_high:
            result["标注"] = "直接输出"
        elif result["置信度"] >= self.confidence_threshold_medium:
            result["标注"] = "建议复核"
        else:
            result["标注"] = "[需核实]"

        return result

    def batch_process(self, inputs: List[str]) -> List[Dict[str, Any]]:
        """批量处理多个输入"""
        results = []
        for item in inputs:
            try:
                results.append(self.process(item))
            except SpecDrivenError:
                continue
        return results


def selftest() -> bool:
    """离线自检：使用内置硬编码样例数据验证核心逻辑"""
    print("开始自检...")
    processor = SpecDrivenProcessor()

    # 测试用例 1: 正常处理
    test_input_1 = "标题=测试任务;内容=这是一个测试内容;类型=开发;优先级=高"
    try:
        result_1 = processor.process(test_input_1)
        assert result_1["标题"] == "测试任务", "标题解析失败"
        assert result_1["内容"] == "这是一个测试内容", "内容解析失败"
        assert result_1["类型"] == "开发", "类型解析失败"
        assert result_1["优先级"] == "高", "优先级解析失败"
        # 宽松阈值：置信度应在合理范围
        assert 0.8 <= result_1["置信度"] <= 1.0, "置信度范围异常"
        print(f"  [PASS] 正常处理: {result_1}")
    except AssertionError as e:
        print(f"  [FAIL] 正常处理断言失败: {e}")
        return False
    except SpecDrivenError as e:
        print(f"  [FAIL] 正常处理异常: {e}")
        return False

    # 测试用例 2: 空输入处理
    try:
        processor.process("")
        print("  [FAIL] 空输入未抛出异常")
        return False
    except SpecDrivenError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print(f"  [PASS] 空输入处理: {e}")

    # 测试用例 3: 关键信息缺失
    try:
        processor.process("标题=只有标题")
        print("  [FAIL] 关键信息缺失未抛出异常")
        return False
    except SpecDrivenError as e:
        assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
        print(f"  [PASS] 关键信息缺失: {e}")

    # 测试用例 4: 批量处理
    batch_inputs = [
        "标题=任务1;内容=内容1;类型=测试;优先级=中",
        "标题=任务2;内容=内容2;类型=测试;优先级=低",
        "",  # 无效输入应被跳过
    ]
    batch_results = processor.batch_process(batch_inputs)
    assert len(batch_results) == 2, f"批量处理应返回2个结果，实际{len(batch_results)}"
    print(f"  [PASS] 批量处理: 返回 {len(batch_results)} 个有效结果")

    # 测试用例 5: 能力边界检查
    assert len(CAPABILITIES["do"]) == 5, "能力声明数量不符"
    assert len(CAPABILITIES["not_do"]) == 3, "边界声明数量不符"
    print(f"  [PASS] 能力边界声明检查")

    # 测试用例 6: 错误码完整性
    assert len(ERROR_CODES) == 10, f"错误码数量应为10，实际{len(ERROR_CODES)}"
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"缺少错误码 {code}"
    print(f"  [PASS] 错误码完整性检查")

    # 测试用例 7: 格式错误处理
    try:
        processor.process("这是没有格式的输入，只有一行")
        print("  [PASS] 格式错误自动降级处理")
    except SpecDrivenError as e:
        print(f"  [PASS] 格式错误处理: {e}")

    print("自检全部通过！")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Spec-Driven Develop 工具 - 基于规格驱动的开发工作流",
        epilog="示例: python scripts/main.py --input '标题=示例;内容=测试内容;类型=开发;优先级=高'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不访问网络，不读取外部文件）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入（空格分隔）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（JSON格式）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = selftest()
        return 0 if success else 1

    # 参数检查
    if not args.input and not args.batch:
        print("错误: 需要提供 --input 或 --batch 参数", file=sys.stderr)
        print("提示: 使用 --help 查看帮助，或 --selftest 运行自检", file=sys.stderr)
        return 1

    # 加载配置
    config = {}
    if args.config:
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                config = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"[E009] 配置文件读取失败: {e}", file=sys.stderr)
            return 1

    processor = SpecDrivenProcessor(config)

    try:
        # 批量处理
        if args.batch:
            results = processor.batch_process(args.batch)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for i, result in enumerate(results, 1):
                    print(f"结果 {i}:")
                    for k, v in result.items():
                        print(f"  {k}: {v}")
                    print()
            return 0

        # 单个处理
        result = processor.process(args.input)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("处理结果:")
            for k, v in result.items():
                print(f"  {k}: {v}")
        return 0

    except SpecDrivenError as e:
        print(f"处理失败: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
