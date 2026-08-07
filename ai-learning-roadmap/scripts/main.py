#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-learning-roadmap - AI学习路径分周规划与资源验收工具
版本: 1.0.1
许可证: MIT
"""

import sys
import json
import argparse
from datetime import datetime
from collections import OrderedDict

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要的输入参数",
    "E002": "参数错误：基础水平取值无效",
    "E003": "参数错误：目标类型取值无效",
    "E004": "参数错误：周数超出允许范围",
    "E005": "数据错误：内置模板数据缺失或损坏",
    "E006": "数据错误：生成结果为空",
    "E007": "运行时错误：JSON序列化失败",
    "E008": "运行时错误：文件写入失败",
    "E009": "运行时错误：文件读取失败",
    "E010": "未知错误",
}

# ============================================================
# 内置基础数据（硬编码模板，不依赖外部文件）
# ============================================================

# 基础水平等级定义
LEVELS = {
    "L0": {"name": "零基础", "desc": "无编程经验，数学基础薄弱"},
    "L1": {"name": "入门", "desc": "有基础编程能力，了解基本数学概念"},
    "L2": {"name": "进阶", "desc": "熟练掌握编程，具备线性代数和概率统计基础"},
    "L3": {"name": "高级", "desc": "有AI项目经验，需要系统化提升"},
}

# 学习目标类型定义
GOAL_TYPES = {
    "career": {"name": "就业", "desc": "以进入AI相关岗位为目标"},
    "research": {"name": "科研", "desc": "以学术研究为目标"},
    "project": {"name": "项目开发", "desc": "以完成具体项目为目标"},
    "teaching": {"name": "团队培训", "desc": "以团队能力建设为目标"},
}

# 技能模块定义（按目标类型组织）
SKILL_MODULES = {
    "career": [
        {"id": "M01", "name": "Python编程基础", "weeks": 2},
        {"id": "M02", "name": "数学基础", "weeks": 3},
        {"id": "M03", "name": "机器学习核心", "weeks": 4},
        {"id": "M04", "name": "深度学习基础", "weeks": 3},
        {"id": "M05", "name": "工程实践", "weeks": 2},
    ],
    "research": [
        {"id": "M01", "name": "数学基础深化", "weeks": 3},
        {"id": "M02", "name": "经典ML算法", "weeks": 3},
        {"id": "M03", "name": "深度学习理论", "weeks": 4},
        {"id": "M04", "name": "论文阅读与复现", "weeks": 3},
        {"id": "M05", "name": "研究方向探索", "weeks": 2},
    ],
    "project": [
        {"id": "M01", "name": "Python与工具链", "weeks": 2},
        {"id": "M02", "name": "ML快速上手", "weeks": 3},
        {"id": "M03", "name": "深度学习实战", "weeks": 3},
        {"id": "M04", "name": "项目开发实践", "weeks": 3},
    ],
    "teaching": [
        {"id": "M01", "name": "团队基础摸底", "weeks": 1},
        {"id": "M02", "name": "核心知识体系", "weeks": 4},
        {"id": "M03", "name": "实战项目训练", "weeks": 3},
        {"id": "M04", "name": "内部知识沉淀", "weeks": 2},
    ],
}

# 学习资源模板（按主题分类）
RESOURCES = {
    "python": [
        {"type": "课程", "name": "Python官方教程", "url": "https://docs.python.org/3/tutorial/"},
        {"type": "书籍", "name": "Python编程：从入门到实践", "url": ""},
        {"type": "练习", "name": "LeetCode 简单题", "url": "https://leetcode.com/"},
    ],
    "math": [
        {"type": "课程", "name": "3Blue1Brown 线性代数", "url": "https://www.3blue1brown.com/"},
        {"type": "课程", "name": "Khan Academy 概率统计", "url": "https://www.khanacademy.org/"},
        {"type": "书籍", "name": "统计学习方法", "url": ""},
    ],
    "ml": [
        {"type": "课程", "name": "吴恩达机器学习", "url": "https://www.coursera.org/learn/machine-learning"},
        {"type": "文档", "name": "scikit-learn 用户指南", "url": "https://scikit-learn.org/"},
        {"type": "书籍", "name": "机器学习（周志华）", "url": ""},
    ],
    "dl": [
        {"type": "课程", "name": "吴恩达深度学习专项", "url": "https://www.deeplearning.ai/"},
        {"type": "文档", "name": "PyTorch 官方教程", "url": "https://pytorch.org/tutorials/"},
        {"type": "论文", "name": "Attention Is All You Need", "url": "https://arxiv.org/abs/1706.03762"},
    ],
    "engineering": [
        {"type": "开源项目", "name": "Hugging Face Transformers", "url": "https://github.com/huggingface/transformers"},
        {"type": "工具", "name": "Docker 官方文档", "url": "https://docs.docker.com/"},
        {"type": "课程", "name": "MLOps 基础课程", "url": ""},
    ],
    "research_method": [
        {"type": "论文", "name": "BERT", "url": "https://arxiv.org/abs/1810.04805"},
        {"type": "论文", "name": "ResNet", "url": "https://arxiv.org/abs/1512.03385"},
        {"type": "工具", "name": "Google Scholar", "url": "https://scholar.google.com/"},
    ],
    "project_practice": [
        {"type": "平台", "name": "Kaggle 竞赛", "url": "https://www.kaggle.com/"},
        {"type": "开源项目", "name": "GitHub Trending", "url": "https://github.com/trending"},
    ],
    "team_training": [
        {"type": "工具", "name": "Confluence 知识库", "url": ""},
        {"type": "方法", "name": "费曼学习法", "url": ""},
        {"type": "平台", "name": "内部代码评审", "url": ""},
    ],
}

# 模块到资源的映射
MODULE_RESOURCE_MAP = {
    "Python编程基础": "python",
    "Python与工具链": "python",
    "数学基础": "math",
    "数学基础深化": "math",
    "机器学习核心": "ml",
    "经典ML算法": "ml",
    "ML快速上手": "ml",
    "深度学习基础": "dl",
    "深度学习理论": "dl",
    "深度学习实战": "dl",
    "工程实践": "engineering",
    "论文阅读与复现": "research_method",
    "研究方向探索": "research_method",
    "项目开发实践": "project_practice",
    "团队基础摸底": "team_training",
    "核心知识体系": "ml",
    "实战项目训练": "project_practice",
    "内部知识沉淀": "team_training",
}

# ============================================================
# 核心逻辑函数
# ============================================================

def validate_inputs(level, goal, total_weeks):
    """校验输入参数有效性"""
    # 先检查必需参数是否存在
    if not level or not goal:
        return False, "E001"
    
    # 检查水平是否有效
    if level not in LEVELS:
        return False, "E002"
    
    # 检查目标是否有效
    if goal not in GOAL_TYPES:
        return False, "E003"
    
    # 检查周数是否有效（注意：0 是无效值，但不是"缺少参数"）
    if total_weeks is None or total_weeks < 1 or total_weeks > 52:
        return False, "E004"
    
    return True, "OK"


def get_level_adjustment(level):
    """根据基础水平返回周数调整因子"""
    factors = {"L0": 1.3, "L1": 1.1, "L2": 0.9, "L3": 0.7}
    return factors.get(level, 1.0)


def get_goal_modules(goal):
    """获取目标对应的技能模块列表"""
    return SKILL_MODULES.get(goal, [])


def generate_weekly_plan(level, goal, total_weeks):
    """生成分周学习计划"""
    # 校验输入
    valid, err_code = validate_inputs(level, goal, total_weeks)
    if not valid:
        return None, err_code

    # 获取模块列表
    modules = get_goal_modules(goal)
    if not modules:
        return None, "E005"

    # 计算调整后的总周数
    adjustment = get_level_adjustment(level)
    adjusted_weeks = max(1, int(total_weeks * adjustment))

    # 按比例分配每周任务
    total_module_weeks = sum(m["weeks"] for m in modules)
    if total_module_weeks <= 0:
        return None, "E005"

    weekly_plan = []
    week_counter = 1

    for module in modules:
        # 计算该模块应分配的周数
        module_weeks = max(1, round(module["weeks"] / total_module_weeks * adjusted_weeks))

        for i in range(module_weeks):
            if week_counter > total_weeks:
                break

            # 获取该模块对应资源
            resource_key = MODULE_RESOURCE_MAP.get(module["name"], "ml")
            resources = RESOURCES.get(resource_key, [])

            # 构建每周计划项
            week_item = {
                "week": week_counter,
                "module_id": module["id"],
                "module_name": module["name"],
                "topic": f"{module['name']} - 第{i+1}周",
                "tasks": [
                    f"学习{module['name']}核心概念",
                    "完成配套练习",
                    "记录学习笔记",
                ],
                "resources": resources[:2],  # 每周围绕2个资源
                "acceptance": [
                    f"完成{module['name']}相关练习",
                    "能独立解释核心概念",
                    "完成本周复盘总结",
                ],
            }
            weekly_plan.append(week_item)
            week_counter += 1

        if week_counter > total_weeks:
            break

    # 如果生成的计划为空，返回错误
    if not weekly_plan:
        return None, "E006"

    return weekly_plan, "OK"


def format_plan_output(plan):
    """将计划格式化为可读文本"""
    if not plan:
        return ""

    lines = []
    lines.append("=" * 60)
    lines.append("AI学习路径规划")
    lines.append("=" * 60)

    current_module = None
    for item in plan:
        if item["module_name"] != current_module:
            current_module = item["module_name"]
            lines.append(f"\n【模块 {item['module_id']}】{current_module}")
            lines.append("-" * 40)

        lines.append(f"\n第{item['week']}周 - {item['topic']}")
        lines.append("  学习任务：")
        for task in item["tasks"]:
            lines.append(f"    ✓ {task}")

        lines.append("  推荐资源：")
        for res in item["resources"]:
            url_info = f" ({res['url']})" if res["url"] else ""
            lines.append(f"    • [{res['type']}] {res['name']}{url_info}")

        lines.append("  验收标准：")
        for acc in item["acceptance"]:
            lines.append(f"    ★ {acc}")

    lines.append("\n" + "=" * 60)
    lines.append("规划完成，祝你学习顺利！")
    lines.append("=" * 60)

    return "\n".join(lines)


def generate_json_output(plan):
    """生成JSON格式输出"""
    try:
        return json.dumps(plan, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return None


# ============================================================
# 自测试函数
# ============================================================

def run_selftest():
    """内置硬编码样例数据的离线自检"""
    print("开始自检...\n")

    # 测试1: 基础校验
    valid, err_code = validate_inputs("L0", "career", 8)
    assert valid, f"测试1失败: 基础校验应为通过，实际错误码 {err_code}"
    print("✓ 测试1通过: 基础校验")

    # 测试2: 无效水平
    valid, err_code = validate_inputs("L9", "career", 8)
    assert not valid and err_code == "E002", f"测试2失败: 应返回E002，实际 {err_code}"
    print("✓ 测试2通过: 无效水平校验")

    # 测试3: 无效目标
    valid, err_code = validate_inputs("L0", "invalid", 8)
    assert not valid and err_code == "E003", f"测试3失败: 应返回E003，实际 {err_code}"
    print("✓ 测试3通过: 无效目标校验")

    # 测试4: 无效周数（0）
    valid, err_code = validate_inputs("L0", "career", 0)
    assert not valid and err_code == "E004", f"测试4失败: 应返回E004，实际 {err_code}"
    print("✓ 测试4通过: 无效周数校验(0)")

    # 测试4b: 无效周数（过大）
    valid, err_code = validate_inputs("L0", "career", 53)
    assert not valid and err_code == "E004", f"测试4b失败: 应返回E004，实际 {err_code}"
    print("✓ 测试4b通过: 无效周数校验(53)")

    # 测试5: 生成计划 - 就业方向
    plan, err_code = generate_weekly_plan("L1", "career", 10)
    assert err_code == "OK" and plan, f"测试5失败: 计划生成失败，错误码 {err_code}"
    assert len(plan) > 0, "测试5失败: 计划为空"
    assert 0 < len(plan) <= 10, f"测试5失败: 计划周数 {len(plan)} 超出范围"
    # 验证计划结构
    first_week = plan[0]
    assert "week" in first_week and "module_name" in first_week, "测试5失败: 计划项缺少必要字段"
    assert len(first_week["tasks"]) > 0, "测试5失败: 计划项缺少任务"
    assert len(first_week["resources"]) > 0, "测试5失败: 计划项缺少资源"
    assert len(first_week["acceptance"]) > 0, "测试5失败: 计划项缺少验收标准"
    print(f"✓ 测试5通过: 就业方向计划生成 (共{len(plan)}周)")

    # 测试6: 生成计划 - 科研方向
    plan_r, err_code = generate_weekly_plan("L2", "research", 12)
    assert err_code == "OK" and plan_r, f"测试6失败: 科研计划生成失败，错误码 {err_code}"
    assert len(plan_r) > 0, "测试6失败: 科研计划为空"
    print(f"✓ 测试6通过: 科研方向计划生成 (共{len(plan_r)}周)")

    # 测试7: 生成计划 - 项目方向
    plan_p, err_code = generate_weekly_plan("L0", "project", 6)
    assert err_code == "OK" and plan_p, f"测试7失败: 项目计划生成失败，错误码 {err_code}"
    assert len(plan_p) > 0, "测试7失败: 项目计划为空"
    print(f"✓ 测试7通过: 项目方向计划生成 (共{len(plan_p)}周)")

    # 测试8: 生成计划 - 团队培训方向
    plan_t, err_code = generate_weekly_plan("L1", "teaching", 8)
    assert err_code == "OK" and plan_t, f"测试8失败: 培训计划生成失败，错误码 {err_code}"
    assert len(plan_t) > 0, "测试8失败: 培训计划为空"
    print(f"✓ 测试8通过: 团队培训计划生成 (共{len(plan_t)}周)")

    # 测试9: 不同水平生成计划比较（宽松比较）
    plan_l0, _ = generate_weekly_plan("L0", "career", 8)
    plan_l3, _ = generate_weekly_plan("L3", "career", 8)
    assert plan_l0 and plan_l3, "测试9失败: 计划生成失败"
    # L0调整因子1.3, L3调整因子0.7, 宽松验证L0的计划不应显著少于L3
    assert len(plan_l0) >= len(plan_l3) * 0.5, "测试9失败: 基础水平对计划长度影响异常"
    print(f"✓ 测试9通过: 不同水平计划差异 (L0:{len(plan_l0)}周, L3:{len(plan_l3)}周)")

    # 测试10: 输出格式验证
    text_output = format_plan_output(plan)
    assert text_output and "AI学习路径规划" in text_output, "测试10失败: 文本输出格式错误"
    json_output = generate_json_output(plan)
    assert json_output and json.loads(json_output), "测试10失败: JSON输出格式错误"
    print("✓ 测试10通过: 输出格式验证")

    # 测试11: 计划连续性验证
    week_numbers = [item["week"] for item in plan]
    assert week_numbers == sorted(week_numbers), "测试11失败: 周数未按顺序排列"
    assert len(set(week_numbers)) == len(week_numbers), "测试11失败: 周数存在重复"
    print("✓ 测试11通过: 计划周数连续性")

    # 测试12: 资源引用验证
    for item in plan:
        for res in item["resources"]:
            assert "type" in res and "name" in res, "测试12失败: 资源格式错误"
    print("✓ 测试12通过: 资源引用完整性")

    print("\n" + "=" * 40)
    print("所有自检测试通过！")
    print("=" * 40)
    return True


# ============================================================
# 主程序入口
# ============================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI学习路径规划器 - 根据基础与目标生成分周学习计划",
        epilog="示例: python main.py --level L1 --goal career --weeks 8"
    )
    parser.add_argument("--level", choices=["L0", "L1", "L2", "L3"],
                        help="基础水平: L0(零基础), L1(入门), L2(进阶), L3(高级)")
    parser.add_argument("--goal", choices=["career", "research", "project", "teaching"],
                        help="学习目标: career(就业), research(科研), project(项目), teaching(培训)")
    parser.add_argument("--weeks", type=int, default=8,
                        help="计划周数 (1-52, 默认8)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="输出格式: text(文本) 或 json(JSON)")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检测试")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            sys.exit(0 if success else 1)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自检异常: {e}")
            sys.exit(1)

    # 正常模式：检查参数
    if not args.level or not args.goal:
        print(f"错误码 E001: {ERROR_CODES['E001']}")
        print("请使用 --level 指定基础水平，--goal 指定学习目标")
        parser.print_help()
        sys.exit(1)

    # 生成计划
    plan, err_code = generate_weekly_plan(args.level, args.goal, args.weeks)

    if err_code != "OK":
        print(f"错误码 {err_code}: {ERROR_CODES.get(err_code, ERROR_CODES['E010'])}")
        sys.exit(1)

    # 输出结果
    if args.format == "json":
        output = generate_json_output(plan)
        if not output:
            print(f"错误码 E007: {ERROR_CODES['E007']}")
            sys.exit(1)
        print(output)
    else:
        output = format_plan_output(plan)
        if not output:
            print(f"错误码 E006: {ERROR_CODES['E006']}")
            sys.exit(1)
        print(output)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"错误码 E010: {ERROR_CODES['E010']} - {str(e)}")
        sys.exit(1)
