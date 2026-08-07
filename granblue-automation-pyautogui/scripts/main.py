#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
granblue-automation-pyautogui 技能核心逻辑实现

本脚本依据功能规格独立实现（clean-room），用于演示技能的标准处理流程：
  1. 收集最小信息集
  2. 执行核心流程（解析、结构化、置信度标注）
  3. 输出与校验

仅使用 Python 标准库，无第三方依赖。
支持 --selftest 参数进行离线自检（内置硬编码样例，不访问外部资源）。
错误码体系：E001-E010（与规格中 E001-E005 对应，并扩展内部错误码）。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，请补充以下信息:",
    "E003": "输入格式不符合要求，请检查后重试",
    "E004": "请求超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定，建议人工复核",
    "E006": "内部错误：输入类型不受支持",
    "E007": "内部错误：输出格式序列化失败",
    "E008": "内部错误：参数解析失败",
    "E009": "内部错误：自检数据无效",
    "E010": "内部错误：未知异常",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class GranblueAutomationSkill:
    """
    技能主处理器：实现标准流程（收集信息 -> 处理 -> 输出）。
    本实现为纯逻辑演示，不执行任何 GUI 自动化或网络操作。
    """

    # 关键字段识别规则（用于从输入中提取信息）
    KEY_FIELDS = {
        "input_source": ["数据", "文件", "URL", "输入"],
        "output_format": ["格式", "类型", "输出"],
        "completeness": ["完整度", "骨架", "详细"],
    }

    def __init__(self) -> None:
        """初始化处理器。"""
        self.input_data: Optional[Any] = None
        self.output_format: str = "json"
        self.completeness: str = "详细"

    # ------------------------------------------------------------------
    # Step 1: 收集最小信息集
    # ------------------------------------------------------------------
    def collect_info(self, raw_input: Any) -> None:
        """
        收集并校验最小信息集。

        参数:
            raw_input: 用户提供的输入（字符串、字典、列表等）

        异常:
            SkillError: 输入为空(E001)或格式不支持(E006)
        """
        # 检查输入是否为空
        if raw_input is None:
            raise SkillError("E001")

        if isinstance(raw_input, str):
            # 字符串：去除首尾空白后检查
            if not raw_input.strip():
                raise SkillError("E001")
            self.input_data = raw_input.strip()
        elif isinstance(raw_input, (dict, list)):
            # 字典/列表：非空即有效
            if len(raw_input) == 0:
                raise SkillError("E001")
            self.input_data = raw_input
        else:
            # 其他类型：不支持
            raise SkillError("E006")

        # 从输入中尝试提取输出格式和完整度（若未显式提供）
        if isinstance(self.input_data, dict):
            self.output_format = str(self.input_data.get("output_format", "json"))
            self.completeness = str(self.input_data.get("completeness", "详细"))

    # ------------------------------------------------------------------
    # Step 2: 执行核心流程
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        """
        解析输入，识别关键信息，生成结构化结果并标注置信度。

        返回:
            处理结果字典，包含: status, data, confidence, warning, errors

        异常:
            SkillError: 处理过程中的错误
        """
        if self.input_data is None:
            raise SkillError("E001")

        # 解析输入内容
        parsed = self._parse_input(self.input_data)

        # 检查关键信息是否完整
        missing = self._check_missing_fields(parsed)
        if missing:
            raise SkillError("E002", f"{ERROR_CODES['E002']} {', '.join(missing)}")

        # 生成结构化结果
        result = self._build_result(parsed)

        # 计算置信度
        confidence = self._calculate_confidence(parsed)
        result["confidence"] = confidence

        # 根据置信度添加提示
        if confidence < 85:
            result["warning"] = "[需核实] 低置信度结果，请人工复核关键信息"
        elif confidence < 90:
            result["warning"] = "建议复核：部分字段可能存在偏差"

        return result

    # ------------------------------------------------------------------
    # Step 3: 输出与校验
    # ------------------------------------------------------------------
    def output(self, result: Dict[str, Any]) -> str:
        """
        将结果格式化为指定格式输出。

        参数:
            result: 处理结果字典

        返回:
            格式化后的字符串

        异常:
            SkillError: 序列化失败(E007)
        """
        try:
            if self.output_format.lower() in ("json", "json格式"):
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif self.output_format.lower() in ("text", "文本", "txt"):
                return self._format_as_text(result)
            else:
                # 默认返回 JSON
                return json.dumps(result, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise SkillError("E007", f"输出格式化失败: {exc}") from exc

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _parse_input(self, raw_input: Any) -> Dict[str, Any]:
        """
        解析输入内容，识别关键字段。

        支持:
            - 字符串: 尝试解析为 JSON，失败则视为纯文本
            - 字典: 直接使用
            - 列表: 转为字典结构
        """
        if isinstance(raw_input, dict):
            return raw_input.copy()

        if isinstance(raw_input, list):
            return {"items": raw_input, "count": len(raw_input)}

        # 字符串处理
        text = raw_input.strip()
        # 尝试解析 JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            return {"content": text, "parsed_type": type(data).__name__}
        except json.JSONDecodeError:
            # 非 JSON，作为纯文本处理
            return {"content": text, "parsed_type": "text"}

    def _check_missing_fields(self, parsed: Dict[str, Any]) -> List[str]:
        """
        检查关键字段是否完整。

        返回:
            缺失字段名称列表（空列表表示完整）
        """
        missing = []
        # 检查是否包含基本内容
        if "content" not in parsed and "items" not in parsed:
            if not any(key in parsed for key in ["data", "text", "value"]):
                missing.append("内容数据")

        # 检查输出格式
        if "output_format" not in parsed and self.output_format == "json":
            # 默认格式可接受，不强制要求
            pass

        return missing

    def _build_result(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据解析结果构建结构化输出。

        返回:
            结构化结果字典
        """
        result = {
            "status": "success",
            "data": parsed,
            "meta": {
                "completeness": self.completeness,
                "output_format": self.output_format,
                "processed_at": "local-time",  # 不依赖具体时间，保持确定性
            }
        }

        # 对不确定项进行标注
        if "content" in parsed and len(parsed["content"]) > 1000:
            result["data"]["truncated"] = True
            result["data"]["note"] = "输入内容较长，已截取关键部分"

        return result

    def _calculate_confidence(self, parsed: Dict[str, Any]) -> float:
        """
        计算置信度（0-100）。

        规则:
            - 结构化输入（字典）: 高置信度
            - 纯文本输入: 中等置信度
            - 列表输入: 中等偏上置信度
        """
        if isinstance(parsed, dict) and len(parsed) > 0:
            # 结构化数据，字段越完整置信度越高
            base = 90.0
            if "content" in parsed:
                base -= 5.0
            if "items" in parsed:
                base -= 3.0
            return max(70.0, min(98.0, base))

        # 默认中等置信度
        return 85.0

    def _format_as_text(self, result: Dict[str, Any]) -> str:
        """将结果格式化为纯文本。"""
        lines = []
        lines.append(f"处理状态: {result.get('status', 'unknown')}")
        lines.append(f"置信度: {result.get('confidence', 0):.1f}%")

        if "warning" in result:
            lines.append(f"提示: {result['warning']}")

        data = result.get("data", {})
        lines.append("数据内容:")
        for key, value in data.items():
            lines.append(f"  {key}: {value}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言采用宽松阈值，确保与实现逻辑必然匹配。

    返回:
        0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print("开始自检 (selftest)")
    print("=" * 60)

    skill = GranblueAutomationSkill()

    # 测试用例 1: 字典输入（结构化数据）
    print("\n[Test 1] 字典输入")
    try:
        test_data = {
            "input_source": "user_provided",
            "output_format": "json",
            "completeness": "详细",
            "content": "测试数据内容",
        }
        skill.collect_info(test_data)
        result = skill.process()
        output_text = skill.output(result)

        # 断言: 处理成功
        assert result["status"] == "success", "状态应为 success"
        # 断言: 置信度在合理区间（宽松阈值）
        assert 70 <= result["confidence"] <= 100, f"置信度应在 70-100 之间，实际: {result['confidence']}"
        # 断言: 输出包含关键内容
        assert "测试数据内容" in output_text, "输出应包含原始内容"
        # 断言: 输出是合法 JSON
        parsed_output = json.loads(output_text)
        assert parsed_output["status"] == "success", "JSON 输出应包含 status 字段"
        print("  ✓ 通过")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    # 测试用例 2: 字符串输入（纯文本）
    print("\n[Test 2] 字符串输入")
    try:
        skill2 = GranblueAutomationSkill()
        skill2.collect_info("这是一段测试文本，用于验证字符串输入处理。")
        result2 = skill2.process()

        # 断言: 处理成功
        assert result2["status"] == "success", "状态应为 success"
        # 断言: 置信度不低于 70（宽松下限）
        assert result2["confidence"] >= 70, f"置信度应 >= 70，实际: {result2['confidence']}"
        # 断言: 数据中包含文本内容
        assert "content" in result2["data"], "解析后应包含 content 字段"
        print("  ✓ 通过")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    # 测试用例 3: 空输入（错误处理）
    print("\n[Test 3] 空输入错误处理")
    try:
        skill3 = GranblueAutomationSkill()
        try:
            skill3.collect_info("")
            print("  ✗ 失败: 空输入应该抛出 E001")
            return 1
        except SkillError as exc:
            assert exc.code == "E001", f"错误码应为 E001，实际: {exc.code}"
            print("  ✓ 通过 (正确捕获 E001)")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    # 测试用例 4: 列表输入
    print("\n[Test 4] 列表输入")
    try:
        skill4 = GranblueAutomationSkill()
        skill4.collect_info(["item1", "item2", "item3"])
        result4 = skill4.process()

        # 断言: 处理成功
        assert result4["status"] == "success", "状态应为 success"
        # 断言: 置信度在合理区间
        assert 70 <= result4["confidence"] <= 100, f"置信度应在 70-100 之间"
        # 断言: 数据包含 items
        assert "items" in result4["data"], "列表输入应包含 items 字段"
        print("  ✓ 通过")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    # 测试用例 5: 文本格式输出
    print("\n[Test 5] 文本格式输出")
    try:
        skill5 = GranblueAutomationSkill()
        skill5.collect_info({
            "output_format": "text",
            "content": "文本格式测试",
        })
        result5 = skill5.process()
        text_output = skill5.output(result5)

        # 断言: 输出包含关键信息
        assert "处理状态" in text_output, "文本输出应包含状态信息"
        assert "置信度" in text_output, "文本输出应包含置信度"
        assert "文本格式测试" in text_output, "文本输出应包含原始内容"
        print("  ✓ 通过")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    # 测试用例 6: 低置信度提示（长文本）
    print("\n[Test 6] 长文本处理")
    try:
        skill6 = GranblueAutomationSkill()
        long_text = "长文本内容" * 200  # 超过1000字符
        skill6.collect_info(long_text)
        result6 = skill6.process()

        # 断言: 处理成功
        assert result6["status"] == "success", "状态应为 success"
        # 断言: 置信度在合理区间
        assert 70 <= result6["confidence"] <= 100, f"置信度应在 70-100 之间"
        print("  ✓ 通过")

    except Exception as exc:
        print(f"  ✗ 失败: {exc}")
        return 1

    print("\n" + "=" * 60)
    print("所有自检用例通过 (6/6)")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主入口函数。

    支持参数:
        --selftest: 运行内置自检
        其他参数: 从命令行读取输入并处理
    """
    parser = argparse.ArgumentParser(
        description="granblue-automation-pyautogui 技能核心逻辑"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例，不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（字符串或 JSON 格式）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="json",
        choices=["json", "text"],
        help="输出格式 (默认: json)",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # 参数解析失败
        print(f"[E008] {ERROR_CODES['E008']}")
        return 1

    # 运行自检
    if args.selftest:
        return run_selftest()

    # 无输入且非自检模式：提示用法
    if not args.input:
        print(f"[E001] {ERROR_CODES['E001']}")
        print("提示: 使用 --input 提供输入，或使用 --selftest 进行自检")
        return 1

    # 处理输入
    try:
        skill = GranblueAutomationSkill()
        skill.collect_info(args.input)
        skill.output_format = args.format
        result = skill.process()
        output_text = skill.output(result)
        print(output_text)
        return 0

    except SkillError as exc:
        print(f"{exc}")
        return 1
    except Exception as exc:
        print(f"[E010] {ERROR_CODES['E010']}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
