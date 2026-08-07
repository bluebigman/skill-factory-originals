#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hec-commander 命令行工具（全新独立实现）

面向 HEC-RAS / HEC-HMS 的脚本自动化辅助工具。
本脚本仅依据功能规格独立编写，不包含任何既有代码。

功能：
  - 解析模型参数（糙率、流量、降雨等）
  - 生成脚本框架（Python 调用序列）
  - 置信度标注与占位提示
  - 离线自检（--selftest）
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入参数无效
ERR_MISSING_PARAM = "E002"      # 缺少必要参数
ERR_UNSUPPORTED_MODEL = "E003"  # 不支持的模型类型
ERR_PARSE_FAILED = "E004"       # 解析失败
ERR_GENERATE_FAILED = "E005"    # 脚本生成失败
ERR_CONFIG_ERROR = "E006"       # 配置错误
ERR_IO_ERROR = "E007"           # 文件读写错误
ERR_SELFTEST_FAILED = "E008"    # 自检失败
ERR_UNKNOWN = "E009"            # 未知错误
ERR_DEPENDENCY = "E010"         # 依赖缺失


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ModelParam:
    """模型参数"""
    name: str
    value: Any
    unit: str = ""
    confidence: float = 1.0          # 置信度 0~1
    need_verify: bool = False        # 是否需要人工核实
    description: str = ""


@dataclass
class ScriptTemplate:
    """脚本模板"""
    model_type: str                  # "RAS" 或 "HMS"
    api_calls: List[str] = field(default_factory=list)
    params: Dict[str, ModelParam] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


# ============================================================
# 核心逻辑：参数识别与映射
# ============================================================
# 关键参数识别规则（关键词 -> 参数名）
PARAM_RULES: Dict[str, Dict[str, Any]] = {
    "roughness": {
        "keywords": ["糙率", "roughness", "曼宁", "manning"],
        "param_name": "roughness",
        "unit": "s/m^(1/3)",
        "description": "曼宁糙率系数"
    },
    "flow": {
        "keywords": ["流量", "flow", "discharge", "q"],
        "param_name": "flow",
        "unit": "m³/s",
        "description": "边界流量"
    },
    "rainfall": {
        "keywords": ["降雨", "rainfall", "precipitation", "rain"],
        "param_name": "rainfall",
        "unit": "mm",
        "description": "降雨量"
    },
    "time_step": {
        "keywords": ["时间步长", "timestep", "time step", "dt"],
        "param_name": "time_step",
        "unit": "s",
        "description": "计算时间步长"
    },
    "duration": {
        "keywords": ["历时", "duration", "period", "时长"],
        "param_name": "duration",
        "unit": "h",
        "description": "模拟历时"
    },
    "elevation": {
        "keywords": ["高程", "elevation", "水位", "stage"],
        "param_name": "elevation",
        "unit": "m",
        "description": "水位/高程"
    }
}


def identify_params(text: str) -> Dict[str, ModelParam]:
    """
    从自然语言文本中识别关键参数。

    Args:
        text: 用户输入的描述文本

    Returns:
        识别到的参数字典

    Raises:
        ValueError: 当输入为空时
    """
    if not text or not text.strip():
        raise ValueError(ERR_INVALID_INPUT)

    result: Dict[str, ModelParam] = {}
    text_lower = text.lower()

    for rule_key, rule in PARAM_RULES.items():
        for kw in rule["keywords"]:
            if kw.lower() in text_lower:
                # 简单提取参数值（取关键词后第一个数字）
                value = _extract_number_after_keyword(text, kw)
                result[rule["param_name"]] = ModelParam(
                    name=rule["param_name"],
                    value=value,
                    unit=rule["unit"],
                    confidence=0.7 if value is not None else 0.3,
                    need_verify=value is None,
                    description=rule["description"]
                )
                break

    return result


def _extract_number_after_keyword(text: str, keyword: str) -> Optional[float]:
    """
    提取关键词后的第一个数字。

    Args:
        text: 输入文本
        keyword: 关键词

    Returns:
        提取到的数值，若无则返回 None
    """
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return None

    # 在关键词后查找数字
    remaining = text[idx + len(keyword):]
    import re
    match = re.search(r'[-+]?\d*\.?\d+', remaining)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


# ============================================================
# 核心逻辑：脚本生成
# ============================================================
def generate_script(
    model_type: str,
    params: Dict[str, ModelParam],
    project_name: str = "hec_project"
) -> ScriptTemplate:
    """
    根据模型类型和参数生成脚本模板。

    Args:
        model_type: "RAS" 或 "HMS"
        params: 参数列表
        project_name: 项目名称

    Returns:
        生成的脚本模板

    Raises:
        ValueError: 模型类型不支持或参数缺失
    """
    if model_type.upper() not in ("RAS", "HMS"):
        raise ValueError(ERR_UNSUPPORTED_MODEL)

    if not params:
        raise ValueError(ERR_MISSING_PARAM)

    template = ScriptTemplate(model_type=model_type.upper())
    template.params = params

    # 生成 API 调用序列
    if model_type.upper() == "RAS":
        template.api_calls = _generate_ras_calls(params, project_name)
    else:
        template.api_calls = _generate_hms_calls(params, project_name)

    # 添加注释
    template.notes = [
        "生成的脚本为框架代码，需在本地 HEC 环境中验证运行。",
        "请确认模型文件路径正确，并安装必要的 Python 库。"
    ]

    # 对置信度低的参数添加占位提示
    for param in params.values():
        if param.need_verify:
            template.notes.append(
                f"[需核实:{param.name}] 参数值未识别，请手动确认。"
            )

    return template


def _generate_ras_calls(params: Dict[str, ModelParam], project: str) -> List[str]:
    """生成 HEC-RAS API 调用序列"""
    calls = [
        f"# HEC-RAS 脚本框架 - 项目: {project}",
        "import hecras",
        f"ras = hecras.open_project('{project}.prj')",
    ]

    # 几何设置
    calls.append("geom = ras.get_geometry()")

    # 糙率设置
    if "roughness" in params:
        r = params["roughness"]
        val = r.value if r.value is not None else "None"
        calls.append(f"geom.set_roughness({val})  # 糙率 [{r.unit}]")

    # 流量设置
    if "flow" in params:
        f = params["flow"]
        val = f.value if f.value is not None else "None"
        calls.append(f"ras.set_boundary_flow({val})  # 流量 [{f.unit}]")

    # 水位设置
    if "elevation" in params:
        e = params["elevation"]
        val = e.value if e.value is not None else "None"
        calls.append(f"ras.set_stage({val})  # 水位 [{e.unit}]")

    # 时间设置
    if "time_step" in params:
        t = params["time_step"]
        val = t.value if t.value is not None else "None"
        calls.append(f"ras.set_timestep({val})  # 时间步长 [{t.unit}]")

    if "duration" in params:
        d = params["duration"]
        val = d.value if d.value is not None else "None"
        calls.append(f"ras.set_duration({val})  # 历时 [{d.unit}]")

    # 运行
    calls.append("ras.run_simulation()")
    calls.append("ras.save_results()")
    calls.append("ras.close()")

    return calls


def _generate_hms_calls(params: Dict[str, ModelParam], project: str) -> List[str]:
    """生成 HEC-HMS API 调用序列"""
    calls = [
        f"# HEC-HMS 脚本框架 - 项目: {project}",
        "import hechms",
        f"hms = hechms.open_project('{project}.hms')",
    ]

    # 降雨设置
    if "rainfall" in params:
        r = params["rainfall"]
        val = r.value if r.value is not None else "None"
        calls.append(f"hms.set_rainfall({val})  # 降雨量 [{r.unit}]")

    # 流量设置
    if "flow" in params:
        f = params["flow"]
        val = f.value if f.value is not None else "None"
        calls.append(f"hms.set_inflow({val})  # 入流 [{f.unit}]")

    # 时间设置
    if "time_step" in params:
        t = params["time_step"]
        val = t.value if t.value is not None else "None"
        calls.append(f"hms.set_timestep({val})  # 时间步长 [{t.unit}]")

    if "duration" in params:
        d = params["duration"]
        val = d.value if d.value is not None else "None"
        calls.append(f"hms.set_duration({val})  # 历时 [{d.unit}]")

    # 运行
    calls.append("hms.run_simulation()")
    calls.append("hms.export_results()")
    calls.append("hms.close()")

    return calls


# ============================================================
# 输出格式化
# ============================================================
def format_script(template: ScriptTemplate) -> str:
    """
    将脚本模板格式化为可读文本。

    Args:
        template: 脚本模板

    Returns:
        格式化后的脚本文本
    """
    lines: List[str] = []

    # 头部
    lines.append("=" * 60)
    lines.append(f"HEC-Commander 脚本方案 (模型: {template.model_type})")
    lines.append("=" * 60)

    # 参数表
    lines.append("\n[参数识别结果]")
    for name, param in template.params.items():
        verify = " [需核实]" if param.need_verify else ""
        conf = f" 置信度:{param.confidence:.0%}"
        lines.append(f"  - {name}: {param.value} {param.unit}{verify}{conf}")

    # API 调用序列
    lines.append("\n[脚本框架]")
    for call in template.api_calls:
        lines.append(f"  {call}")

    # 注释
    if template.notes:
        lines.append("\n[注意事项]")
        for note in template.notes:
            lines.append(f"  # {note}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不依赖外部文件或网络。

    Returns:
        0 表示成功，非 0 表示失败
    """
    print("[自检] 开始离线自检...")
    failures = 0

    # --- 测试用例 1: 参数识别 ---
    print("[自检] 测试参数识别...")
    test_text = "河道糙率0.035，流量120立方米每秒，降雨50毫米"
    try:
        params = identify_params(test_text)

        # 宽松断言：应识别至少 2 个参数
        assert len(params) >= 2, f"参数识别数量不足: {len(params)}"

        # 糙率应为正数且小于 1
        if "roughness" in params:
            r = params["roughness"].value
            assert r is not None and 0 < r < 1, f"糙率异常: {r}"

        # 流量应为正数
        if "flow" in params:
            f = params["flow"].value
            assert f is not None and f > 0, f"流量异常: {f}"

        print(f"  ✓ 参数识别通过，识别到 {len(params)} 个参数")
    except Exception as e:
        failures += 1
        print(f"  ✗ 参数识别失败: {e}")

    # --- 测试用例 2: 脚本生成 (RAS) ---
    print("[自检] 测试 RAS 脚本生成...")
    try:
        params_ras = {
            "roughness": ModelParam("roughness", 0.035, "s/m^(1/3)", 0.9),
            "flow": ModelParam("flow", 120.0, "m³/s", 0.95),
        }
        template_ras = generate_script("RAS", params_ras, "test_ras")

        # 宽松断言：至少 3 行 API 调用
        assert len(template_ras.api_calls) >= 3, "API 调用数量不足"
        assert template_ras.model_type == "RAS"

        print(f"  ✓ RAS 脚本生成通过，{len(template_ras.api_calls)} 行调用")
    except Exception as e:
        failures += 1
        print(f"  ✗ RAS 脚本生成失败: {e}")

    # --- 测试用例 3: 脚本生成 (HMS) ---
    print("[自检] 测试 HMS 脚本生成...")
    try:
        params_hms = {
            "rainfall": ModelParam("rainfall", 50.0, "mm", 0.85),
            "duration": ModelParam("duration", 24.0, "h", 0.9),
        }
        template_hms = generate_script("HMS", params_hms, "test_hms")

        assert len(template_hms.api_calls) >= 3, "API 调用数量不足"
        assert template_hms.model_type == "HMS"

        print(f"  ✓ HMS 脚本生成通过，{len(template_hms.api_calls)} 行调用")
    except Exception as e:
        failures += 1
        print(f"  ✗ HMS 脚本生成失败: {e}")

    # --- 测试用例 4: 错误处理 ---
    print("[自检] 测试错误处理...")
    try:
        # 无效模型类型
        try:
            generate_script("INVALID", {"flow": ModelParam("flow", 1.0)})
            failures += 1
            print("  ✗ 无效模型类型未抛出异常")
        except ValueError as e:
            assert str(e) == ERR_UNSUPPORTED_MODEL, f"错误码不正确: {e}"
            print("  ✓ 无效模型类型正确报错")

        # 空参数
        try:
            generate_script("RAS", {})
            failures += 1
            print("  ✗ 空参数未抛出异常")
        except ValueError as e:
            assert str(e) == ERR_MISSING_PARAM, f"错误码不正确: {e}"
            print("  ✓ 空参数正确报错")

        # 空文本
        try:
            identify_params("")
            failures += 1
            print("  ✗ 空文本未抛出异常")
        except ValueError as e:
            assert str(e) == ERR_INVALID_INPUT, f"错误码不正确: {e}"
            print("  ✓ 空文本正确报错")

    except Exception as e:
        failures += 1
        print(f"  ✗ 错误处理测试异常: {e}")

    # --- 测试用例 5: 格式化输出 ---
    print("[自检] 测试格式化输出...")
    try:
        template_fmt = generate_script(
            "RAS",
            {"flow": ModelParam("flow", 100.0, "m³/s", 0.9)},
            "fmt_test"
        )
        output = format_script(template_fmt)

        # 宽松断言：输出包含关键内容
        assert "HEC-Commander" in output, "输出缺少标题"
        assert "flow" in output, "输出缺少参数名"
        assert len(output) > 100, f"输出过短: {len(output)} 字符"

        print(f"  ✓ 格式化输出通过，输出 {len(output)} 字符")
    except Exception as e:
        failures += 1
        print(f"  ✗ 格式化输出失败: {e}")

    # --- 测试用例 6: 置信度与占位提示 ---
    print("[自检] 测试置信度与占位提示...")
    try:
        # 模拟无法提取数值的情况
        params_low_conf = identify_params("请设置合适的糙率参数")
        # 应识别糙率但置信度低
        assert "roughness" in params_low_conf
        assert params_low_conf["roughness"].need_verify is True

        template_verify = generate_script("RAS", params_low_conf, "verify_test")
        has_placeholder = any("[需核实" in note for note in template_verify.notes)
        assert has_placeholder, "缺少占位提示"

        print("  ✓ 置信度与占位提示通过")
    except Exception as e:
        failures += 1
        print(f"  ✗ 置信度与占位提示失败: {e}")

    # --- 汇总 ---
    if failures == 0:
        print("\n[自检] ✅ 全部测试通过！")
        return ERR_OK
    else:
        print(f"\n[自检] ❌ {failures} 项测试失败！")
        return 1


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="HEC-Commander: 水文建模脚本自动化工具",
        epilog="示例: python main.py --model RAS --text '糙率0.035，流量120'"
    )

    parser.add_argument(
        "--model", "-m",
        choices=["RAS", "HMS"],
        help="模型类型 (RAS 或 HMS)"
    )
    parser.add_argument(
        "--text", "-t",
        help="自然语言描述，如: '糙率0.035，流量120立方米每秒'"
    )
    parser.add_argument(
        "--project", "-p",
        default="hec_project",
        help="项目名称 (默认: hec_project)"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式：需要模型类型和文本
    if not args.model or not args.text:
        parser.error("需要 --model 和 --text 参数，或使用 --selftest")

    try:
        # 1. 识别参数
        params = identify_params(args.text)

        if not params:
            print(f"错误 [{ERR_MISSING_PARAM}]: 未能从文本中识别任何参数", file=sys.stderr)
            return 1

        # 2. 生成脚本
        template = generate_script(args.model, params, args.project)

        # 3. 输出
        if args.json:
            # JSON 输出
            output = {
                "model_type": template.model_type,
                "params": {
                    name: {
                        "value": p.value,
                        "unit": p.unit,
                        "confidence": p.confidence,
                        "need_verify": p.need_verify
                    }
                    for name, p in template.params.items()
                },
                "api_calls": template.api_calls,
                "notes": template.notes
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # 文本输出
            print(format_script(template))

        return ERR_OK

    except ValueError as e:
        err_code = str(e)
        if err_code not in (ERR_INVALID_INPUT, ERR_MISSING_PARAM, ERR_UNSUPPORTED_MODEL):
            err_code = ERR_GENERATE_FAILED
        print(f"错误 [{err_code}]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERR_UNKNOWN}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
