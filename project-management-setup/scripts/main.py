#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
项目管理工具配置 (project-management-setup)

基于开源项目管理工具 Kaneo，根据团队规模、项目类型和流程偏好，
生成项目看板、任务分类、权限设置等配置方案。

本脚本为 clean-room 独立实现，仅依据功能规格设计。
支持 --selftest 参数进行离线自检。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：团队规模、项目类型、流程偏好",
    "E003": "输入格式不符合要求，示例：{\"team_size\": 10, \"project_type\": \"web\", \"workflow\": \"kanban\"}",
    "E004": "这超出了本工具的能力范围，建议：调整输入内容或使用其他专业工具",
    "E005": "结果无法确定，建议：补充更多信息后重试",
    "E006": "内部处理异常，请检查输入数据后重试",
    "E007": "输出序列化失败，请检查数据完整性",
    "E008": "参数解析失败，请检查命令行参数",
    "E009": "自检数据初始化失败，无法执行离线自检",
    "E010": "自检断言失败，核心逻辑可能存在问题",
}

# 看板默认列（依据 Kaneo 常见实践）
DEFAULT_BOARD_COLUMNS: List[str] = ["待办", "进行中", "评审", "已完成"]

# 任务分类模板
TASK_CATEGORIES: Dict[str, List[str]] = {
    "web": ["前端开发", "后端开发", "接口联调", "测试", "部署"],
    "mobile": ["UI实现", "业务逻辑", "兼容性测试", "发布准备"],
    "data": ["数据采集", "清洗加工", "建模分析", "可视化"],
    "general": ["需求分析", "设计", "开发", "测试", "上线"],
}

# 权限角色模板
ROLE_TEMPLATES: Dict[str, List[str]] = {
    "small": ["管理员", "成员"],
    "medium": ["管理员", "项目经理", "开发", "测试"],
    "large": ["超级管理员", "项目经理", "开发", "测试", "产品", "运维"],
}

# 置信度阈值（依据规格）
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85


# ============================================================
# 核心数据结构
# ============================================================

class ProjectConfig:
    """项目配置方案数据结构"""

    def __init__(self) -> None:
        self.board: List[str] = []
        self.categories: List[str] = []
        self.roles: List[str] = []
        self.confidence: float = 0.0
        self.summary: str = ""
        self.warnings: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "board": self.board,
            "categories": self.categories,
            "roles": self.roles,
            "confidence": self.confidence,
            "summary": self.summary,
            "warnings": self.warnings,
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"E007: 输出序列化失败 - {exc}") from exc


# ============================================================
# 核心逻辑模块
# ============================================================

def validate_input(data: Dict[str, Any]) -> None:
    """
    校验输入数据的完整性和合法性。
    依据规格 Step 1 最小信息集要求：团队规模、项目类型、流程偏好。
    """
    if not data:
        raise ValueError("E001")

    # 检查关键字段
    missing = []
    if "team_size" not in data or data.get("team_size") is None:
        missing.append("团队规模(team_size)")
    if "project_type" not in data or not data.get("project_type"):
        missing.append("项目类型(project_type)")
    if "workflow" not in data or not data.get("workflow"):
        missing.append("流程偏好(workflow)")

    if missing:
        raise ValueError(f"E002: 缺少字段 - {', '.join(missing)}")

    # 类型检查
    if not isinstance(data["team_size"], (int, float)) or data["team_size"] <= 0:
        raise ValueError("E003: team_size 必须为正数")

    if not isinstance(data["project_type"], str):
        raise ValueError("E003: project_type 必须为字符串")

    if not isinstance(data["workflow"], str):
        raise ValueError("E003: workflow 必须为字符串")


def determine_team_scale(team_size: float) -> str:
    """根据团队规模确定规模级别"""
    if team_size < 5:
        return "small"
    elif team_size < 20:
        return "medium"
    else:
        return "large"


def build_board(workflow: str) -> List[str]:
    """
    根据流程偏好生成看板列。
    支持：kanban / scrum / custom
    """
    workflow_lower = workflow.lower().strip()

    if workflow_lower == "scrum":
        return ["待办", "冲刺中", "评审", "已完成"]
    elif workflow_lower == "custom":
        # 自定义流程使用默认列
        return list(DEFAULT_BOARD_COLUMNS)
    else:
        # 默认 kanban 或其他
        return list(DEFAULT_BOARD_COLUMNS)


def build_categories(project_type: str) -> List[str]:
    """根据项目类型生成任务分类"""
    ptype = project_type.lower().strip()
    # 模糊匹配
    if "web" in ptype or "前端" in ptype:
        return list(TASK_CATEGORIES["web"])
    elif "mobile" in ptype or "app" in ptype or "移动" in ptype:
        return list(TASK_CATEGORIES["mobile"])
    elif "data" in ptype or "数据" in ptype:
        return list(TASK_CATEGORIES["data"])
    else:
        return list(TASK_CATEGORIES["general"])


def build_roles(team_size: float) -> List[str]:
    """根据团队规模生成权限角色"""
    scale = determine_team_scale(team_size)
    return list(ROLE_TEMPLATES[scale])


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    计算置信度。
    依据规格：字段完整则基础置信度 0.95，有缺失或异常则降低。
    """
    confidence = 0.95

    # 团队规模合理性
    team_size = float(data.get("team_size", 0))
    if team_size <= 0 or team_size > 1000:
        confidence -= 0.05

    # 项目类型是否在已知模板中
    ptype = data.get("project_type", "").lower()
    known_types = ["web", "mobile", "data", "general", "前端", "app", "移动", "数据"]
    if not any(k in ptype for k in known_types):
        confidence -= 0.05

    # 流程偏好是否已知
    workflow = data.get("workflow", "").lower()
    if workflow not in ["kanban", "scrum", "custom", "看板", "敏捷"]:
        confidence -= 0.05

    return max(0.0, min(1.0, confidence))


def generate_config(data: Dict[str, Any]) -> ProjectConfig:
    """
    核心生成逻辑：根据输入生成项目配置方案。
    依据规格 Step 2 执行核心流程。
    """
    # 校验输入（Step 1）
    validate_input(data)

    config = ProjectConfig()
    team_size = float(data["team_size"])

    # 1. 生成看板
    config.board = build_board(data["workflow"])

    # 2. 生成任务分类
    config.categories = build_categories(data["project_type"])

    # 3. 生成权限角色
    config.roles = build_roles(team_size)

    # 4. 计算置信度
    config.confidence = calculate_confidence(data)

    # 5. 生成摘要
    scale = determine_team_scale(team_size)
    config.summary = (
        f"已为{scale}规模团队（{int(team_size)}人）生成配置方案："
        f"{len(config.board)}个看板列、{len(config.categories)}个任务分类、"
        f"{len(config.roles)}个权限角色。"
    )

    # 6. 置信度标注（依据规格 Step 2 规则）
    if config.confidence < CONFIDENCE_MEDIUM:
        config.warnings.append("[需核实] 输入信息不完整或非常规，结果仅供参考")
    elif config.confidence < CONFIDENCE_HIGH:
        config.warnings.append("建议复核：部分字段使用了默认模板")

    # 7. 能力边界检查（规格第一条边界声明：不执行超出输入范围的分析）
    if team_size > 500:
        config.warnings.append("团队规模过大，建议拆分项目或分批管理")

    return config


# ============================================================
# 输出格式化
# ============================================================

def format_output(config: ProjectConfig, fmt: str = "text") -> str:
    """按指定格式输出结果"""
    if fmt == "json":
        return config.to_json()

    # 默认文本格式
    lines = []
    lines.append("=" * 50)
    lines.append("项目管理工具配置方案")
    lines.append("=" * 50)
    lines.append(f"看板列：{', '.join(config.board)}")
    lines.append(f"任务分类：{', '.join(config.categories)}")
    lines.append(f"权限角色：{', '.join(config.roles)}")
    lines.append(f"置信度：{config.confidence * 100:.1f}%")
    lines.append(f"摘要：{config.summary}")
    if config.warnings:
        lines.append("提示：")
        for w in config.warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    """
    print("开始离线自检...")

    # ---- 测试用例 1: 标准小型团队 ----
    test1: Dict[str, Any] = {
        "team_size": 5,
        "project_type": "web",
        "workflow": "kanban",
    }
    try:
        cfg1 = generate_config(test1)
        assert len(cfg1.board) >= 3, "看板列数应至少3个"
        assert len(cfg1.categories) >= 3, "任务分类应至少3个"
        assert len(cfg1.roles) >= 2, "角色数应至少2个"
        assert cfg1.confidence > 0.8, "标准输入置信度应较高"
        print("  [PASS] 测试1: 标准小型团队")
    except AssertionError as exc:
        print(f"  [FAIL] 测试1: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 测试1: 异常 - {exc}")
        return 1

    # ---- 测试用例 2: 中型 Scrum 团队 ----
    test2: Dict[str, Any] = {
        "team_size": 15,
        "project_type": "mobile",
        "workflow": "scrum",
    }
    try:
        cfg2 = generate_config(test2)
        assert len(cfg2.board) >= 3, "Scrum看板列数应至少3个"
        assert "冲刺" in "".join(cfg2.board), "Scrum流程应包含冲刺列"
        assert len(cfg2.categories) >= 3, "移动端任务分类应至少3个"
        print("  [PASS] 测试2: 中型Scrum团队")
    except AssertionError as exc:
        print(f"  [FAIL] 测试2: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 测试2: 异常 - {exc}")
        return 1

    # ---- 测试用例 3: 大型团队 ----
    test3: Dict[str, Any] = {
        "team_size": 50,
        "project_type": "data",
        "workflow": "custom",
    }
    try:
        cfg3 = generate_config(test3)
        assert len(cfg3.roles) >= 5, "大型团队角色数应至少5个"
        assert len(cfg3.board) >= 3, "看板列数应至少3个"
        assert cfg3.confidence > 0.7, "置信度应保持在合理范围"
        print("  [PASS] 测试3: 大型团队")
    except AssertionError as exc:
        print(f"  [FAIL] 测试3: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 测试3: 异常 - {exc}")
        return 1

    # ---- 测试用例 4: 边界输入（极小团队） ----
    test4: Dict[str, Any] = {
        "team_size": 1,
        "project_type": "general",
        "workflow": "kanban",
    }
    try:
        cfg4 = generate_config(test4)
        assert len(cfg4.roles) >= 1, "最小团队也应有角色"
        assert len(cfg4.board) >= 3, "看板列数应至少3个"
        print("  [PASS] 测试4: 边界输入（1人团队）")
    except AssertionError as exc:
        print(f"  [FAIL] 测试4: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 测试4: 异常 - {exc}")
        return 1

    # ---- 测试用例 5: 错误处理 - 空输入 ----
    try:
        generate_config({})
        print("  [FAIL] 测试5: 空输入应抛出E001")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E001"), f"错误码应为E001，实际: {exc}"
        print("  [PASS] 测试5: 空输入错误处理")
    except Exception as exc:
        print(f"  [FAIL] 测试5: 异常 - {exc}")
        return 1

    # ---- 测试用例 6: 错误处理 - 缺失关键字段 ----
    try:
        generate_config({"team_size": 10})
        print("  [FAIL] 测试6: 缺失字段应抛出E002")
        return 1
    except ValueError as exc:
        assert str(exc).startswith("E002"), f"错误码应为E002，实际: {exc}"
        print("  [PASS] 测试6: 缺失字段错误处理")
    except Exception as exc:
        print(f"  [FAIL] 测试6: 异常 - {exc}")
        return 1

    # ---- 测试用例 7: JSON 输出 ----
    try:
        cfg7 = generate_config(test1)
        json_str = cfg7.to_json()
        parsed = json.loads(json_str)
        assert "board" in parsed and "roles" in parsed, "JSON输出应包含关键字段"
        print("  [PASS] 测试7: JSON输出格式")
    except Exception as exc:
        print(f"  [FAIL] 测试7: 异常 - {exc}")
        return 1

    # ---- 测试用例 8: 输出格式 ----
    try:
        cfg8 = generate_config(test1)
        text_out = format_output(cfg8, "text")
        assert "看板" in text_out and "置信度" in text_out, "文本输出应包含关键信息"
        print("  [PASS] 测试8: 文本输出格式")
    except Exception as exc:
        print(f"  [FAIL] 测试8: 异常 - {exc}")
        return 1

    print("\n全部自检通过 ✅")
    return 0


# ============================================================
# 主程序入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="项目管理工具配置 - 生成项目看板、任务分类、权限设置方案"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help='输入JSON字符串，格式: {"team_size": 10, "project_type": "web", "workflow": "kanban"}',
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式 (默认: text)",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        # argparse 遇到错误会抛 SystemExit
        print(f"E008: 参数解析失败 - {exc}", file=sys.stderr)
        return 1

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except Exception as exc:
            print(f"E009: 自检初始化失败 - {exc}", file=sys.stderr)
            return 1

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 传入JSON数据，或使用 --selftest 运行自检", file=sys.stderr)
        return 1

    # 解析输入
    try:
        data = json.loads(args.input)
        if not isinstance(data, dict):
            raise ValueError("输入必须是JSON对象")
    except json.JSONDecodeError as exc:
        print(f"E003: JSON解析失败 - {exc}", file=sys.stderr)
        print(f"示例: {ERROR_MESSAGES['E003']}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"E003: {exc}", file=sys.stderr)
        return 1

    # 生成配置
    try:
        config = generate_config(data)
    except ValueError as exc:
        msg = str(exc)
        err_code = msg[:4] if msg[:4] in ERROR_MESSAGES else "E006"
        print(f"{err_code}: {ERROR_MESSAGES.get(err_code, msg)}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E006: 内部处理异常 - {exc}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        output = format_output(config, args.format)
        print(output)
    except Exception as exc:
        print(f"E007: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
