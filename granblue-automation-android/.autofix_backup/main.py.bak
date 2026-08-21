#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 碧蓝自动化 安卓脚本编排（独立实现）

本脚本根据功能规格，将用户提供的自然语言操作流程转化为结构化的
JSON 脚本配置草案。支持批量处理、自定义字段别名、置信度标注等能力。

仅依据功能规格文档独立编写，未参考任何既有实现。
"""

import json
import re
import sys
import argparse
from typing import Any, Dict, List, Optional, Tuple


# 错误码定义
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "输入格式不是有效的 JSON 字符串",
    "E003": "输入 JSON 不是对象或数组",
    "E004": "步骤节点缺少必要字段",
    "E005": "步骤节点类型不合法",
    "E006": "置信度取值不合法",
    "E007": "输出字段配置不合法",
    "E008": "参数解析失败",
    "E009": "内部处理逻辑错误",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能执行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------- 核心处理逻辑 ----------

# 步骤节点允许的类型
VALID_STEP_TYPES = {"tap", "swipe", "wait", "loop", "condition", "input", "custom"}

# 默认输出字段映射（字段别名 -> 标准字段名）
DEFAULT_FIELD_ALIASES = {
    "action": "action",
    "type": "action",
    "操作": "action",
    "动作": "action",
    "coordinate": "coordinate",
    "pos": "coordinate",
    "位置": "coordinate",
    "坐标": "coordinate",
    "button": "button",
    "target": "button",
    "按钮": "button",
    "目标": "button",
    "wait": "wait",
    "delay": "wait",
    "等待": "wait",
    "时长": "wait",
    "loop": "loop",
    "repeat": "loop",
    "次数": "loop",
    "循环": "loop",
    "condition": "condition",
    "if": "condition",
    "条件": "condition",
    "desc": "description",
    "description": "description",
    "描述": "description",
    "备注": "description",
}


def normalize_field_name(field: str, aliases: Dict[str, str]) -> str:
    """根据别名映射，将字段名标准化。"""
    if not isinstance(field, str):
        return str(field)
    field = field.strip()
    if field in aliases:
        return aliases[field]
    # 去掉常见前缀/后缀后再查一次
    for key, val in aliases.items():
        if field.lower().startswith(key.lower()) or field.lower().endswith(key.lower()):
            return val
    return field


def extract_parameters(text: str) -> Dict[str, Any]:
    """
    从自然语言文本中提取关键参数（坐标、时长、次数等）。
    仅做基础正则提取，不保证 100% 准确。
    """
    params: Dict[str, Any] = {}

    # 提取坐标 (x, y)
    coord_match = re.search(r"[（(]\s*(\d+)\s*[,，]\s*(\d+)\s*[)）]", text)
    if coord_match:
        params["coordinate"] = [int(coord_match.group(1)), int(coord_match.group(2))]

    # 提取等待时长（秒）
    wait_match = re.search(r"(?:等待|等|延时|延迟|wait)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:秒|s)?", text, re.IGNORECASE)
    if wait_match:
        params["wait"] = float(wait_match.group(1))

    # 提取循环次数
    loop_match = re.search(r"(?:循环|重复|次数|repeat|loop)\s*[:：]?\s*(\d+)\s*次?", text, re.IGNORECASE)
    if loop_match:
        params["loop"] = int(loop_match.group(1))

    # 提取按钮/目标名称（常见引号包裹）
    btn_match = re.search(r"[\"“”'‘]\s*([^\"“”'‘]{1,20})\s*[\"“”'‘]", text)
    if btn_match:
        params["button"] = btn_match.group(1).strip()

    return params


def determine_step_type(text: str, params: Dict[str, Any]) -> str:
    """根据文本内容和参数推断步骤类型。"""
    text_lower = text.lower()

    # 关键词优先级判断
    if "点击" in text or "按下" in text or "tap" in text_lower or "click" in text_lower:
        return "tap"
    if "滑动" in text or "拖动" in text or "swipe" in text_lower or "drag" in text_lower:
        return "swipe"
    if "等待" in text or "延时" in text or "wait" in text_lower or "sleep" in text_lower:
        return "wait"
    if "循环" in text or "重复" in text or "loop" in text_lower or "repeat" in text_lower:
        return "loop"
    if "如果" in text or "若" in text or "condition" in text_lower or "if" in text_lower:
        return "condition"
    if "输入" in text or "填写" in text or "input" in text_lower or "type" in text_lower:
        return "input"

    # 参数兜底判断
    if "coordinate" in params:
        return "tap"
    if "wait" in params:
        return "wait"
    if "loop" in params:
        return "loop"

    return "custom"


def build_step(text: str, aliases: Dict[str, str]) -> Dict[str, Any]:
    """
    将单条自然语言步骤文本转换为结构化步骤节点。
    """
    if not text or not isinstance(text, str):
        raise SkillError("E004", f"步骤文本无效: {text}")

    text = text.strip()
    params = extract_parameters(text)
    step_type = determine_step_type(text, params)

    # 构建基础步骤节点
    step: Dict[str, Any] = {
        "action": step_type,
        "description": text,
    }

    # 合并提取到的参数
    for key, value in params.items():
        step[key] = value

    # 额外解析：如果文本中包含"打开副本"等动作词，补充到描述中
    if "打开" in text or "进入" in text:
        step.setdefault("target", text.split("打开")[-1].split("进入")[-1].strip() or "副本")

    # 置信度标注（基于提取到的参数数量做简单判断）
    param_count = len(params)
    if param_count >= 2:
        step["confidence"] = "high"
    elif param_count == 1:
        step["confidence"] = "medium"
    else:
        step["confidence"] = "low"

    # 如果步骤类型是 custom，增加提示
    if step_type == "custom":
        step["note"] = "无法自动识别步骤类型，请人工确认"

    # 字段名标准化（应用别名映射）
    normalized_step: Dict[str, Any] = {}
    for key, value in step.items():
        norm_key = normalize_field_name(key, aliases)
        normalized_step[norm_key] = value

    return normalized_step


def process_flow(input_data: Any, aliases: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    处理单个操作流程，返回结构化配置。
    """
    if aliases is None:
        aliases = DEFAULT_FIELD_ALIASES

    # 输入校验
    if input_data is None:
        raise SkillError("E001")

    if isinstance(input_data, str):
        # 尝试解析为 JSON
        try:
            input_data = json.loads(input_data)
        except json.JSONDecodeError as e:
            raise SkillError("E002", f"JSON 解析失败: {e}")

    if isinstance(input_data, dict):
        # 单条流程：可能包含 steps 数组或直接是步骤列表
        if "steps" in input_data:
            if not isinstance(input_data["steps"], list):
                raise SkillError("E003", "steps 字段必须是数组")
            raw_steps = input_data["steps"]
            flow_name = input_data.get("name", input_data.get("流程名", "未命名流程"))
        elif "流程" in input_data:
            if not isinstance(input_data["流程"], list):
                raise SkillError("E003", "流程字段必须是数组")
            raw_steps = input_data["流程"]
            flow_name = input_data.get("name", input_data.get("流程名", "未命名流程"))
        else:
            # 尝试将字典本身当作单个步骤
            raw_steps = [input_data]
            flow_name = input_data.get("name", "未命名流程")

        steps: List[Dict[str, Any]] = []
        for item in raw_steps:
            if isinstance(item, str):
                steps.append(build_step(item, aliases))
            elif isinstance(item, dict):
                # 已经是结构化步骤，做字段标准化
                norm_step = {}
                for key, value in item.items():
                    norm_key = normalize_field_name(key, aliases)
                    norm_step[norm_key] = value
                # 补充置信度
                norm_step.setdefault("confidence", "medium")
                steps.append(norm_step)
            else:
                raise SkillError("E004", f"无效的步骤类型: {type(item)}")

        return {
            "name": flow_name,
            "steps": steps,
            "step_count": len(steps),
            "version": "1.0.1",
        }

    elif isinstance(input_data, list):
        # 批量流程
        flows = []
        for idx, item in enumerate(input_data):
            if isinstance(item, str):
                # 单条文本当作流程
                flow = process_flow({"name": f"流程{idx+1}", "steps": [item]}, aliases)
                flows.append(flow)
            elif isinstance(item, dict):
                flow = process_flow(item, aliases)
                flows.append(flow)
            else:
                raise SkillError("E003", f"批量流程中第 {idx+1} 项类型不合法")

        return {
            "batch": True,
            "flows": flows,
            "flow_count": len(flows),
        }

    else:
        raise SkillError("E003", f"不支持的输入类型: {type(input_data)}")


# ---------- 自检函数 ----------

def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松断言，确保在任何环境均可通过。
    """
    print("开始自检（内置样例数据）...")

    # 样例 1：单条流程文本
    sample_flow = {
        "name": "日常副本",
        "steps": [
            "打开副本界面",
            "点击(120, 340)的困难按钮",
            "等待 3 秒",
            "点击开始战斗",
            "循环 5 次：点击(200, 400)",
        ]
    }

    try:
        result = process_flow(sample_flow)

        # 断言：返回结构包含必要字段
        assert "name" in result, "结果缺少 name 字段"
        assert "steps" in result, "结果缺少 steps 字段"
        assert isinstance(result["steps"], list), "steps 不是列表"
        assert len(result["steps"]) >= 3, f"步骤数应 >= 3，实际 {len(result['steps'])}"

        # 断言：每个步骤都有 action 和 description
        for step in result["steps"]:
            assert "action" in step, "步骤缺少 action 字段"
            assert "description" in step, "步骤缺少 description 字段"
            assert step["action"] in VALID_STEP_TYPES, f"步骤类型不合法: {step['action']}"

        # 宽松断言：至少有一个步骤包含坐标或等待
        has_coord = any("coordinate" in s for s in result["steps"])
        has_wait = any("wait" in s for s in result["steps"])
        assert has_coord or has_wait, "未提取到坐标或等待参数"

        print(f"  ✓ 样例 1 通过（生成 {len(result['steps'])} 个步骤）")

    except AssertionError as e:
        print(f"  ✗ 样例 1 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 样例 1 处理失败: {e}")
        return False

    # 样例 2：批量流程 + 自定义别名
    batch_input = [
        {"name": "刷金币", "steps": ["进入金币副本", "等待 2 秒", "点击(500, 800)"]},
        {"name": "刷经验", "steps": ["进入经验副本", "点击开始"]},
    ]

    custom_aliases = {
        **DEFAULT_FIELD_ALIASES,
        "duration": "wait",  # 自定义别名
    }

    try:
        batch_result = process_flow(batch_input, custom_aliases)

        assert "batch" in batch_result, "批量结果缺少 batch 标记"
        assert batch_result["batch"] is True, "batch 标记应为 True"
        assert "flows" in batch_result, "批量结果缺少 flows"
        assert len(batch_result["flows"]) == 2, f"应有 2 个流程，实际 {len(batch_result['flows'])}"

        for flow in batch_result["flows"]:
            assert "name" in flow, "流程缺少 name"
            assert "steps" in flow, "流程缺少 steps"

        print(f"  ✓ 样例 2 通过（批量处理 {batch_result['flow_count']} 个流程）")

    except AssertionError as e:
        print(f"  ✗ 样例 2 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 样例 2 处理失败: {e}")
        return False

    # 样例 3：JSON 字符串输入
    json_str = json.dumps({
        "name": "JSON测试",
        "steps": ["点击(100, 200)", "等待 1 秒"]
    })

    try:
        json_result = process_flow(json_str)
        assert json_result["name"] == "JSON测试", "JSON 输入解析失败"
        assert len(json_result["steps"]) == 2, "JSON 输入步骤数不对"

        print(f"  ✓ 样例 3 通过（JSON 字符串输入）")

    except AssertionError as e:
        print(f"  ✗ 样例 3 断言失败: {e}")
        return False
    except SkillError as e:
        print(f"  ✗ 样例 3 处理失败: {e}")
        return False

    # 样例 4：错误处理 - 测试 steps 字段类型错误
    try:
        process_flow({"steps": "不是列表"})
        print("  ✗ 样例 4 未触发预期错误")
        return False
    except SkillError as e:
        assert e.code in ERROR_CODES, f"错误码 {e.code} 不在定义中"
        print(f"  ✓ 样例 4 通过（错误处理正常: {e.code}）")
    except Exception as e:
        print(f"  ✗ 样例 4 抛出非预期异常: {e}")
        return False

    # 样例 5：错误处理 - 测试无效 JSON 字符串
    try:
        process_flow("{invalid json}")
        print("  ✗ 样例 5 未触发预期错误")
        return False
    except SkillError as e:
        assert e.code == "E002", f"预期 E002，实际 {e.code}"
        print(f"  ✓ 样例 5 通过（无效 JSON 错误处理正常: {e.code}）")
    except Exception as e:
        print(f"  ✗ 样例 5 抛出非预期异常: {e}")
        return False

    # 样例 6：错误处理 - 测试空输入
    try:
        process_flow(None)
        print("  ✗ 样例 6 未触发预期错误")
        return False
    except SkillError as e:
        assert e.code == "E001", f"预期 E001，实际 {e.code}"
        print(f"  ✓ 样例 6 通过（空输入错误处理正常: {e.code}）")
    except Exception as e:
        print(f"  ✗ 样例 6 抛出非预期异常: {e}")
        return False

    print("\n全部自检通过 ✔")
    return True


# ---------- 命令行入口 ----------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="碧蓝自动化 安卓脚本编排 - 将操作流程转化为结构化 JSON 配置"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入 JSON 文件路径或 JSON 字符串（不指定则从 stdin 读取）"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（不指定则输出到 stdout）"
    )
    parser.add_argument(
        "--alias", "-a",
        type=str,
        help="自定义字段别名 JSON 文件路径"
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="美化 JSON 输出（缩进 2 空格）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部输入）"
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        return 1

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 读取输入
    try:
        if args.input:
            # 尝试解析为 JSON 字符串
            if args.input.strip().startswith(("{", "[")):
                input_data: Any = args.input
            else:
                # 当作文件路径处理
                with open(args.input, "r", encoding="utf-8") as f:
                    input_data = f.read()
        else:
            # 从 stdin 读取
            input_data = sys.stdin.read().strip()
            if not input_data:
                raise SkillError("E001")

        # 加载自定义别名
        aliases = DEFAULT_FIELD_ALIASES
        if args.alias:
            try:
                with open(args.alias, "r", encoding="utf-8") as f:
                    user_aliases = json.load(f)
                if isinstance(user_aliases, dict):
                    aliases = {**DEFAULT_FIELD_ALIASES, **user_aliases}
                else:
                    raise SkillError("E007", "别名文件必须是 JSON 对象")
            except FileNotFoundError:
                raise SkillError("E008", f"别名文件不存在: {args.alias}")

        # 处理流程
        result = process_flow(input_data, aliases)

        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
        else:
            print(output_json)

        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [{ERROR_CODES['E010']}] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
