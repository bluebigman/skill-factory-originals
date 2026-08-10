#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oad — 显微成像自动化脚本编排助手

本脚本依据《oad 技能功能规格》独立实现（clean-room），
提供脚本结构解析、工作流步骤梳理、参数配置建议、错误排查辅助、批量任务编排等核心能力。

用法示例：
    python scripts/main.py --selftest          # 离线自检（不依赖外部文件/网络）
    python scripts/main.py --parse "print('hi')"
    python scripts/main.py --workflow "多通道采集;时间序列;拼图扫描"
    python scripts/main.py --params "型号=Axio Observer;目标=活细胞"
    python scripts/main.py --diagnose "设备未连接"
    python scripts/main.py --batch "96孔板;3通道;5视野"
"""

import argparse
import sys
import re
from typing import Dict, List, Tuple, Any

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_OK = 0
ERR_PARSE = "E001"       # 脚本解析失败
ERR_WORKFLOW = "E002"    # 工作流步骤无法识别
ERR_PARAMS = "E003"      # 参数配置建议失败
ERR_DIAGNOSE = "E004"    # 错误排查失败
ERR_BATCH = "E005"       # 批量任务编排失败
ERR_INPUT = "E006"       # 输入格式错误
ERR_UNKNOWN_CMD = "E007" # 未知命令
ERR_SELFTEST = "E008"    # 自检失败
ERR_INTERNAL = "E009"    # 内部错误
ERR_CONFIG = "E010"      # 配置错误

# ---------------------------------------------------------------------------
# 内置知识库（离线数据，不依赖外部文件）
# ---------------------------------------------------------------------------

# ZEN Blue OAD 常用工具函数关键词
OAD_FUNCTIONS = {
    "open_image": "打开图像文件",
    "acquire": "采集图像",
    "set_exposure": "设置曝光时间",
    "set_gain": "设置增益",
    "set_zstack": "设置Z层采集",
    "set_channel": "设置通道",
    "tile_scan": "拼图扫描",
    "time_series": "时间序列采集",
    "save_image": "保存图像",
    "analyze": "分析图像",
    "loop": "循环控制",
    "condition": "条件判断",
}

# 常见工作流模式关键词
WORKFLOW_PATTERNS = {
    "多通道采集": ["channel", "多通道", "dapi", "fitc", "cy5", "gfp", "rfp"],
    "时间序列": ["time", "时间", "series", "kinetics", "动态"],
    "拼图扫描": ["tile", "拼图", "mosaic", "扫描", "stitch"],
    "Z层扫描": ["zstack", "z层", "z-stack", "层扫", "depth"],
    "批量孔板": ["96孔", "孔板", "well", "plate", "批量", "batch"],
    "荧光成像": ["荧光", "fluorescence", "激发", "发射"],
    "明场成像": ["明场", "brightfield", "bf"],
    "活细胞成像": ["活细胞", "live cell", "incubator", "培养"],
}

# 硬件型号常见参数
HARDWARE_PARAMS = {
    "Axio Observer": {"曝光范围": "1-100ms", "增益范围": "1-10", "Z层间距": "0.5-5μm"},
    "Axio Imager": {"曝光范围": "5-200ms", "增益范围": "1-8", "Z层间距": "1-10μm"},
    "LSM 900": {"曝光范围": "0.1-50ms", "增益范围": "1-12", "Z层间距": "0.1-2μm"},
    "LSM 980": {"曝光范围": "0.1-50ms", "增益范围": "1-12", "Z层间距": "0.1-2μm"},
    "通用": {"曝光范围": "1-200ms", "增益范围": "1-10", "Z层间距": "0.5-10μm"},
}

# 常见错误信息与排查建议
ERROR_DATABASE = {
    "设备未连接": "请检查USB/网络连接，确认显微镜电源已开启，并在ZEN Blue中重新扫描设备。",
    "参数越界": "请检查曝光时间、增益等参数是否在硬件允许范围内，参考硬件手册。",
    "脚本语法错误": "请检查Python语法，注意缩进和括号匹配，可先在本地IDE中调试。",
    "通道未配置": "请确认在ZEN Blue中已正确配置所需通道，包括激发光波长和滤光片。",
    "内存不足": "请降低采集分辨率或减少Z层数量，或关闭其他占用内存的程序。",
    "图像保存失败": "请检查保存路径是否存在且可写，确认文件格式支持。",
    "ZEN Blue未启动": "请先启动ZEN Blue软件，再运行OAD脚本。",
    "未知错误": "请查看ZEN Blue日志，或联系设备厂商技术支持。",
}

# ---------------------------------------------------------------------------
# 核心逻辑函数
# ---------------------------------------------------------------------------


def parse_script(script_text: str) -> Dict[str, Any]:
    """
    解析用户提供的脚本，识别与 ZEN Blue OAD 框架的关联点。

    返回：
        {
            "function_count": int,
            "functions_found": List[str],
            "has_oad_keywords": bool,
            "has_loop": bool,
            "has_condition": bool,
            "suggestions": List[str],
        }
    """
    if not script_text or not isinstance(script_text, str):
        return {"error": ERR_INPUT, "message": "脚本内容为空或类型错误"}

    try:
        result = {
            "function_count": 0,
            "functions_found": [],
            "has_oad_keywords": False,
            "has_loop": False,
            "has_condition": False,
            "suggestions": [],
        }

        # 统计函数定义（粗略）
        func_matches = re.findall(r"def\s+(\w+)\s*\(", script_text)
        result["function_count"] = len(func_matches)
        result["functions_found"] = func_matches[:5]

        # 检查 OAD 关键词
        found_keywords = []
        for keyword, desc in OAD_FUNCTIONS.items():
            if keyword.lower() in script_text.lower():
                found_keywords.append(keyword)
                result["has_oad_keywords"] = True

        # 检查循环和条件
        result["has_loop"] = bool(re.search(r"\b(for|while)\b", script_text, re.IGNORECASE))
        result["has_condition"] = bool(re.search(r"\b(if|elif|else)\b", script_text, re.IGNORECASE))

        # 生成建议
        if not result["has_oad_keywords"]:
            result["suggestions"].append("未检测到明显的OAD工具函数调用，建议添加如 acquire()、set_exposure() 等。")
        if result["has_loop"]:
            result["suggestions"].append("检测到循环结构，可考虑用于批量样本处理。")
        if result["has_condition"]:
            result["suggestions"].append("检测到条件判断，可用于不同实验路线的分支控制。")
        if not result["suggestions"]:
            result["suggestions"].append("脚本结构清晰，可直接在ZEN Blue中运行。")

        return result

    except Exception as e:
        return {"error": ERR_PARSE, "message": f"脚本解析异常: {str(e)}"}


def workflow_steps(description: str) -> Dict[str, Any]:
    """
    将用户描述的实验流程拆解为可执行的步骤序列。

    返回：
        {
            "steps": List[str],
            "matched_patterns": List[str],
            "suggestions": List[str],
        }
    """
    if not description or not isinstance(description, str):
        return {"error": ERR_INPUT, "message": "流程描述为空或类型错误"}

    try:
        result = {
            "steps": [],
            "matched_patterns": [],
            "suggestions": [],
        }

        # 按分隔符拆分用户描述
        parts = re.split(r"[;；,，\n]+", description)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            return {"error": ERR_WORKFLOW, "message": "无法识别工作流描述"}

        # 匹配工作流模式
        matched = set()
        for part in parts:
            part_lower = part.lower()
            for pattern, keywords in WORKFLOW_PATTERNS.items():
                for kw in keywords:
                    if kw.lower() in part_lower:
                        matched.add(pattern)
                        break

        result["matched_patterns"] = list(matched)

        # 生成步骤序列
        for part in parts:
            step_desc = f"执行: {part}"
            result["steps"].append(step_desc)

        # 根据匹配模式补充建议
        if "多通道采集" in matched:
            result["suggestions"].append("建议使用 set_channel() 依次设置各通道，并分别设置曝光时间。")
        if "时间序列" in matched:
            result["suggestions"].append("建议使用 time_series() 设置时间间隔和总时长。")
        if "拼图扫描" in matched:
            result["suggestions"].append("建议使用 tile_scan() 设置扫描区域和重叠率。")
        if "Z层扫描" in matched:
            result["suggestions"].append("建议使用 set_zstack() 设置Z层范围和间距。")
        if "批量孔板" in matched:
            result["suggestions"].append("建议使用循环遍历孔位，配合 condition() 跳过无效孔。")
        if not result["suggestions"]:
            result["suggestions"].append("已生成基本步骤，请根据实际实验需求调整。")

        return result

    except Exception as e:
        return {"error": ERR_WORKFLOW, "message": f"工作流解析异常: {str(e)}"}


def param_suggestions(hardware: str = "通用", goal: str = "") -> Dict[str, Any]:
    """
    根据硬件型号与实验目标，给出采集参数建议。

    返回：
        {
            "hardware": str,
            "params": Dict[str, str],
            "goal_notes": List[str],
        }
    """
    if not hardware or not isinstance(hardware, str):
        hardware = "通用"

    try:
        # 匹配硬件型号
        hw_key = "通用"
        for key in HARDWARE_PARAMS:
            if key.lower() in hardware.lower():
                hw_key = key
                break

        params = HARDWARE_PARAMS.get(hw_key, HARDWARE_PARAMS["通用"])

        result = {
            "hardware": hw_key,
            "params": params,
            "goal_notes": [],
        }

        # 根据实验目标给出建议
        if goal:
            goal_lower = goal.lower()
            if "活细胞" in goal_lower or "live" in goal_lower:
                result["goal_notes"].append("活细胞成像建议降低曝光时间以减少光毒性，使用培养环境控制。")
                result["goal_notes"].append("建议使用时间序列采集观察动态变化。")
            if "荧光" in goal_lower or "fluorescence" in goal_lower:
                result["goal_notes"].append("荧光成像建议根据染料选择合适的激发/发射波长。")
                result["goal_notes"].append("注意避免过度曝光导致荧光淬灭。")
            if "高分辨" in goal_lower or "high" in goal_lower:
                result["goal_notes"].append("高分辨率成像建议减小Z层间距，使用更高数值孔径物镜。")
            if "大图" in goal_lower or "拼图" in goal_lower or "tile" in goal_lower:
                result["goal_notes"].append("大图拼图建议设置10-20%重叠率以保证拼接质量。")
            if not result["goal_notes"]:
                result["goal_notes"].append("根据实验目标，建议先进行预实验确定最佳参数。")

        return result

    except Exception as e:
        return {"error": ERR_PARAMS, "message": f"参数建议生成异常: {str(e)}"}


def error_diagnosis(error_msg: str) -> Dict[str, Any]:
    """
    针对用户报错信息，定位可能的原因并给出修正方向。

    返回：
        {
            "possible_causes": List[str],
            "suggestions": List[str],
            "severity": str,
        }
    """
    if not error_msg or not isinstance(error_msg, str):
        return {"error": ERR_INPUT, "message": "错误信息为空或类型错误"}

    try:
        result = {
            "possible_causes": [],
            "suggestions": [],
            "severity": "中",
        }

        error_lower = error_msg.lower()

        # 匹配已知错误
        matched = False
        for err_key, suggestion in ERROR_DATABASE.items():
            if err_key.lower() in error_lower:
                result["possible_causes"].append(err_key)
                result["suggestions"].append(suggestion)
                matched = True

        # 根据关键词进一步判断
        if "timeout" in error_lower or "超时" in error_lower:
            result["possible_causes"].append("通信超时")
            result["suggestions"].append("检查设备连接稳定性，增加超时时间设置。")
            result["severity"] = "高"
        if "memory" in error_lower or "内存" in error_lower:
            result["possible_causes"].append("内存不足")
            result["suggestions"].append("降低采集分辨率，减少Z层数量，或分批处理。")
            result["severity"] = "高"
        if "permission" in error_lower or "权限" in error_lower:
            result["possible_causes"].append("权限不足")
            result["suggestions"].append("以管理员身份运行ZEN Blue，检查文件保存路径权限。")
            result["severity"] = "低"
        if "index" in error_lower or "索引" in error_lower:
            result["possible_causes"].append("索引越界")
            result["suggestions"].append("检查循环变量范围，确认数组/列表索引有效。")
            result["severity"] = "中"

        if not matched and not result["possible_causes"]:
            result["possible_causes"].append("未知错误")
            result["suggestions"].append("请提供完整的错误堆栈信息，或查看ZEN Blue日志。")
            result["severity"] = "中"

        return result

    except Exception as e:
        return {"error": ERR_DIAGNOSE, "message": f"错误诊断异常: {str(e)}"}


def batch_workflow(description: str) -> Dict[str, Any]:
    """
    设计循环遍历、条件判断等控制结构，实现多组样本的自动化处理。

    返回：
        {
            "structure": str,
            "pseudo_code": str,
            "suggestions": List[str],
        }
    """
    if not description or not isinstance(description, str):
        return {"error": ERR_INPUT, "message": "批量任务描述为空或类型错误"}

    try:
        result = {
            "structure": "",
            "pseudo_code": "",
            "suggestions": [],
        }

        desc_lower = description.lower()

        # 识别批量模式
        if "96孔" in desc_lower or "孔板" in desc_lower or "plate" in desc_lower:
            result["structure"] = "96孔板遍历"
            result["pseudo_code"] = (
                "for well in plate_wells:\n"
                "    if is_valid_well(well):\n"
                "        move_to(well)\n"
                "        acquire()\n"
                "        save_image(f'well_{well}.tif')"
            )
            result["suggestions"].append("建议使用 try-except 处理个别孔位采集失败的情况。")
            result["suggestions"].append("可添加日志记录每个孔的采集状态。")
        elif "多通道" in desc_lower or "channel" in desc_lower:
            result["structure"] = "多通道循环"
            result["pseudo_code"] = (
                "for channel in channels:\n"
                "    set_channel(channel)\n"
                "    set_exposure(channel_exposure[channel])\n"
                "    acquire()"
            )
            result["suggestions"].append("建议为不同通道设置独立曝光时间。")
        elif "多视野" in desc_lower or "视野" in desc_lower or "view" in desc_lower:
            result["structure"] = "多视野采集"
            result["pseudo_code"] = (
                "for x, y in positions:\n"
                "    move_to(x, y)\n"
                "    acquire()\n"
                "    save_image(f'pos_{x}_{y}.tif')"
            )
            result["suggestions"].append("建议预先保存位置列表，避免重复定位。")
        elif "时间" in desc_lower or "time" in desc_lower:
            result["structure"] = "时间序列循环"
            result["pseudo_code"] = (
                "for t in time_points:\n"
                "    acquire()\n"
                "    wait(interval)\n"
                "    if t == critical_time:\n"
                "        alert_user()"
            )
            result["suggestions"].append("建议在关键时间点添加提醒或自动保存。")
        else:
            result["structure"] = "通用批量循环"
            result["pseudo_code"] = (
                "for sample in samples:\n"
                "    setup_sample(sample)\n"
                "    acquire()\n"
                "    save_image(f'{sample}.tif')"
            )
            result["suggestions"].append("建议根据实际需求调整循环体内的操作。")

        return result

    except Exception as e:
        return {"error": ERR_BATCH, "message": f"批量任务编排异常: {str(e)}"}


# ---------------------------------------------------------------------------
# 自检函数（内置硬编码样例数据，离线运行）
# ---------------------------------------------------------------------------


def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值断言，确保与环境无关。
    """
    print("=" * 60)
    print("oad 技能自检开始（离线模式）")
    print("=" * 60)

    all_passed = True

    # --- 测试1: 脚本结构解析 ---
    print("\n[测试1] 脚本结构解析")
    sample_script = """
def main():
    # 多通道采集示例
    set_channel("DAPI")
    set_exposure(50)
    acquire()
    for i in range(5):
        acquire()
    if condition:
        save_image("test.tif")
"""
    result = parse_script(sample_script)
    if "error" in result:
        print(f"  失败: {result['message']}")
        all_passed = False
    else:
        # 宽松断言: 应检测到函数定义、OAD关键词、循环、条件
        assert result["function_count"] >= 1, "应至少检测到1个函数定义"
        assert result["has_oad_keywords"] is True, "应检测到OAD关键词"
        assert result["has_loop"] is True, "应检测到循环"
        assert result["has_condition"] is True, "应检测到条件"
        assert len(result["suggestions"]) > 0, "应生成建议"
        print(f"  通过: 检测到 {result['function_count']} 个函数, OAD关键词: {result['has_oad_keywords']}")

    # --- 测试2: 工作流步骤梳理 ---
    print("\n[测试2] 工作流步骤梳理")
    result = workflow_steps("多通道采集;时间序列;拼图扫描")
    if "error" in result:
        print(f"  失败: {result['message']}")
        all_passed = False
    else:
        assert len(result["steps"]) >= 3, "应至少生成3个步骤"
        assert len(result["matched_patterns"]) >= 2, "应匹配至少2个模式"
        assert len(result["suggestions"]) >= 2, "应生成至少2条建议"
        print(f"  通过: 生成 {len(result['steps'])} 个步骤, 匹配 {len(result['matched_patterns'])} 个模式")

    # --- 测试3: 参数配置建议 ---
    print("\n[测试3] 参数配置建议")
    result = param_suggestions("Axio Observer", "活细胞荧光成像")
    if "error" in result:
        print(f"  失败: {result['message']}")
        all_passed = False
    else:
        assert result["hardware"] != "", "硬件型号不应为空"
        assert len(result["params"]) >= 3, "应返回至少3个参数建议"
        assert len(result["goal_notes"]) >= 1, "应返回至少1条目标建议"
        print(f"  通过: 硬件={result['hardware']}, 参数建议={len(result['params'])}条, 目标建议={len(result['goal_notes'])}条")

    # --- 测试4: 错误排查辅助 ---
    print("\n[测试4] 错误排查辅助")
    result = error_diagnosis("设备未连接，采集失败")
    if "error" in result:
        print(f"  失败: {result['message']}")
        all_passed = False
    else:
        assert len(result["possible_causes"]) >= 1, "应识别至少1个可能原因"
        assert len(result["suggestions"]) >= 1, "应给出至少1条建议"
        print(f"  通过: 识别原因={len(result['possible_causes'])}个, 建议={len(result['suggestions'])}条")

    # --- 测试5: 批量任务编排 ---
    print("\n[测试5] 批量任务编排")
    result = batch_workflow("96孔板多通道采集")
    if "error" in result:
        print(f"  失败: {result['message']}")
        all_passed = False
    else:
        assert result["structure"] != "", "结构描述不应为空"
        assert len(result["pseudo_code"]) > 10, "伪代码长度应大于10字符"
        assert len(result["suggestions"]) >= 1, "应生成至少1条建议"
        print(f"  通过: 结构={result['structure']}, 伪代码长度={len(result['pseudo_code'])}字符")

    # --- 测试6: 错误处理 ---
    print("\n[测试6] 错误处理")
    result = parse_script("")  # 空输入
    assert "error" in result, "空输入应返回错误"
    result = workflow_steps("")  # 空输入
    assert "error" in result, "空输入应返回错误"
    print("  通过: 空输入正确处理")

    # --- 测试7: 边界情况 ---
    print("\n[测试7] 边界情况")
    result = param_suggestions("未知型号XYZ", "")
    assert "error" not in result, "未知型号应使用通用配置"
    assert result["hardware"] == "通用", "应回退到通用配置"
    print("  通过: 未知型号回退到通用配置")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检测试通过（共7组测试）")
    else:
        print("❌ 部分自检测试失败")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(
        description="oad — 显微成像自动化脚本编排助手",
        epilog="示例: python scripts/main.py --selftest"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置离线自检")
    parser.add_argument("--parse", type=str, metavar="SCRIPT", help="解析Python脚本，识别OAD关联点")
    parser.add_argument("--workflow", type=str, metavar="DESC", help="梳理工作流步骤，如: '多通道采集;时间序列'")
    parser.add_argument("--params", type=str, metavar="HW:GOAL", help="参数配置建议，如: 'Axio Observer:活细胞'")
    parser.add_argument("--diagnose", type=str, metavar="ERROR", help="错误排查，如: '设备未连接'")
    parser.add_argument("--batch", type=str, metavar="DESC", help="批量任务编排，如: '96孔板'")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 解析脚本
    if args.parse:
        result = parse_script(args.parse)
        if "error" in result:
            print(f"错误[{result['error']}]: {result['message']}")
            sys.exit(1)
        print("脚本解析结果:")
        print(f"  函数数量: {result['function_count']}")
        print(f"  检测到函数: {', '.join(result['functions_found']) if result['functions_found'] else '无'}")
        print(f"  OAD关键词: {'是' if result['has_oad_keywords'] else '否'}")
        print(f"  包含循环: {'是' if result['has_loop'] else '否'}")
        print(f"  包含条件: {'是' if result['has_condition'] else '否'}")
        print("  建议:")
        for s in result["suggestions"]:
            print(f"    - {s}")
        sys.exit(0)

    # 工作流梳理
    if args.workflow:
        result = workflow_steps(args.workflow)
        if "error" in result:
            print(f"错误[{result['error']}]: {result['message']}")
            sys.exit(1)
        print("工作流步骤:")
        for step in result["steps"]:
            print(f"  {step}")
        print(f"匹配模式: {', '.join(result['matched_patterns']) if result['matched_patterns'] else '无'}")
        print("建议:")
        for s in result["suggestions"]:
            print(f"  - {s}")
        sys.exit(0)

    # 参数建议
    if args.params:
        # 支持 "硬件:目标" 格式
        if ":" in args.params:
            hw, goal = args.params.split(":", 1)
        else:
            hw, goal = args.params, ""
        result = param_suggestions(hw.strip(), goal.strip())
        if "error" in result:
            print(f"错误[{result['error']}]: {result['message']}")
            sys.exit(1)
        print(f"硬件型号: {result['hardware']}")
        print("参数建议:")
        for k, v in result["params"].items():
            print(f"  {k}: {v}")
        print("目标建议:")
        for s in result["goal_notes"]:
            print(f"  - {s}")
        sys.exit(0)

    # 错误诊断
    if args.diagnose:
        result = error_diagnosis(args.diagnose)
        if "error" in result:
            print(f"错误[{result['error']}]: {result['message']}")
            sys.exit(1)
        print(f"严重程度: {result['severity']}")
        print("可能原因:")
        for cause in result["possible_causes"]:
            print(f"  - {cause}")
        print("修正建议:")
        for s in result["suggestions"]:
            print(f"  - {s}")
        sys.exit(0)

    # 批量编排
    if args.batch:
        result = batch_workflow(args.batch)
        if "error" in result:
            print(f"错误[{result['error']}]: {result['message']}")
            sys.exit(1)
        print(f"批量结构: {result['structure']}")
        print("伪代码示例:")
        print(result["pseudo_code"])
        print("建议:")
        for s in result["suggestions"]:
            print(f"  - {s}")
        sys.exit(0)

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
