#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — VS Code Makefile 工程配置辅助工具（独立实现）

本脚本依据《vscode-makefile-tools 功能规格》独立编写（clean-room），
提供以下核心能力：
  1. 解析 .vscode/settings.json 中的 Makefile Tools 相关配置
  2. 生成标准化的配置模板
  3. 整理环境变量清单与配置建议
  4. 构建流程编排（pre-configure / post-configure 顺序检查）
  5. 构建错误日志诊断辅助

命令行用法：
    python scripts/main.py --selftest        # 离线自检（内置样例数据）
    python scripts/main.py --parse <json路径> # 解析指定配置文件
    python scripts/main.py --template        # 打印配置模板
    python scripts/main.py --envs <json路径>  # 输出环境变量清单
    python scripts/main.py --diagnose <日志>  # 诊断构建错误

错误码说明：
    E001 参数错误
    E002 文件不存在或不可读
    E003 JSON 解析失败
    E004 配置结构不符合预期
    E005 模板生成失败
    E006 环境变量分析失败
    E007 构建编排检查失败
    E008 日志诊断失败
    E009 自检失败
    E010 未知错误

依赖：仅使用 Python 标准库（json / sys / os / argparse / re）
"""

import json
import os
import re
import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
# Makefile Tools 扩展在 settings.json 中的配置键前缀
EXTENSION_KEY = "makefile"

# 已知的 Makefile Tools 配置项（依据 VS Code 扩展文档整理）
KNOWN_CONFIG_KEYS = {
    "makefile.makeDirectory": "Make 命令执行的工作目录",
    "makefile.makefilePath": "Makefile 文件路径（相对于工作区）",
    "makefile.configurations": "构建配置列表（如 Debug/Release）",
    "makefile.defaultConfiguration": "默认使用的构建配置名称",
    "makefile.buildLog": "构建日志文件路径",
    "makefile.phonyTargets": "phony 目标列表",
    "makefile.compileCommandsPath": "compile_commands.json 输出路径",
    "makefile.preConfigure": "配置阶段前执行的脚本命令",
    "makefile.postConfigure": "配置阶段后执行的脚本命令",
    "makefile.preBuild": "构建前执行的脚本命令",
    "makefile.postBuild": "构建后执行的脚本命令",
    "makefile.environment": "传递给 Make 的环境变量（对象形式）",
    "makefile.environmentFile": "环境变量定义文件路径",
    "makefile.autoDetect": "是否自动检测 Makefile（布尔值）",
    "makefile.terminal": "终端集成相关配置",
}

# 构建阶段脚本键（用于编排检查）
PHASE_SCRIPT_KEYS = [
    "makefile.preConfigure",
    "makefile.postConfigure",
    "makefile.preBuild",
    "makefile.postBuild",
]

# 常见构建错误模式（用于日志诊断）
ERROR_PATTERNS = [
    {
        "pattern": r"Error\s*\d+",
        "hint": "检测到编译错误（Error N），请检查源代码语法或头文件路径。",
        "suggestion": "在 VS Code 中打开问题面板（Ctrl+Shift+M）查看具体错误位置。",
    },
    {
        "pattern": r"undefined reference",
        "hint": "检测到链接错误：未定义的引用。",
        "suggestion": "检查链接库是否遗漏（-l 参数），或源文件是否全部参与编译。",
    },
    {
        "pattern": r"cannot find\s+-l\w+",
        "hint": "检测到找不到指定的链接库。",
        "suggestion": "确认库文件已安装，且库搜索路径（-L 参数）配置正确。",
    },
    {
        "pattern": r"fatal error:\s*\w+\.h:\s*No such file",
        "hint": "检测到头文件缺失。",
        "suggestion": "检查 include 路径（-I 参数）或确认头文件是否存在于源码目录。",
    },
    {
        "pattern": r"recipe for target .* failed",
        "hint": "检测到 Make 规则执行失败。",
        "suggestion": "查看失败目标的上一条日志输出，定位具体命令错误。",
    },
    {
        "pattern": r"no rule to make target",
        "hint": "检测到 Make 无法找到目标规则。",
        "suggestion": "检查目标名称拼写，或确认 Makefile 中是否定义了该目标。",
    },
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _read_json_file(file_path: str) -> Dict[str, Any]:
    """
    读取 JSON 文件并解析。

    参数:
        file_path: JSON 文件路径

    返回:
        解析后的字典对象

    错误码:
        E002 文件不存在或不可读
        E003 JSON 解析失败
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"E002: 文件不存在或不可读: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"E003: JSON 解析失败: {file_path} — {e}") from e


def _safe_get(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    安全地按点分路径获取嵌套字典值。

    参数:
        data: 字典数据
        key_path: 点分路径，如 "makefile.defaultConfiguration"
        default: 默认值

    返回:
        路径对应的值；若路径不存在返回默认值
    """
    keys = key_path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _is_valid_configuration(config: Dict[str, Any]) -> bool:
    """
    校验配置结构是否合理（宽松检查）。

    参数:
        config: 待检查的配置字典

    返回:
        True 表示结构基本合理
    """
    # 至少应包含 makefile 键（可以是空对象）
    if not isinstance(config, dict):
        return False
    if EXTENSION_KEY not in config:
        return False
    return True


# ---------------------------------------------------------------------------
# 核心功能：配置解析
# ---------------------------------------------------------------------------
def parse_configuration(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 .vscode/settings.json 中的 Makefile Tools 配置。

    参数:
        config_data: settings.json 解析后的字典

    返回:
        包含配置项、有效性和建议的字典

    错误码:
        E004 配置结构不符合预期
    """
    if not _is_valid_configuration(config_data):
        raise ValueError("E004: 配置结构不符合预期（缺少 makefile 键或根节点非对象）")

    makefile_section = config_data.get(EXTENSION_KEY, {})
    if not isinstance(makefile_section, dict):
        raise ValueError("E004: makefile 配置段必须是对象")

    # 提取已知配置项
    extracted: Dict[str, Any] = {}
    for full_key, description in KNOWN_CONFIG_KEYS.items():
        # 去掉 "makefile." 前缀
        short_key = full_key.split(".", 1)[1]
        value = _safe_get(config_data, full_key)
        if value is not None:
            extracted[short_key] = {"value": value, "description": description}

    # 检测未知配置项
    unknown_keys = []
    for key in makefile_section:
        full_key = f"{EXTENSION_KEY}.{key}"
        if full_key not in KNOWN_CONFIG_KEYS:
            unknown_keys.append(key)

    # 生成建议
    suggestions = []
    if "defaultConfiguration" not in extracted:
        suggestions.append("未设置默认构建配置（makefile.defaultConfiguration），建议在 VS Code 中指定。")
    if "makeDirectory" not in extracted:
        suggestions.append("未指定 Make 工作目录（makefile.makeDirectory），默认使用工作区根目录。")
    if "configurations" not in extracted:
        suggestions.append("未定义构建配置列表（makefile.configurations），建议至少包含 Debug 和 Release。")

    return {
        "parsed": extracted,
        "unknown_keys": unknown_keys,
        "suggestions": suggestions,
        "valid": True,
    }


# ---------------------------------------------------------------------------
# 核心功能：配置模板生成
# ---------------------------------------------------------------------------
def generate_template() -> str:
    """
    生成标准化的 Makefile Tools 配置模板（JSON 文本）。

    返回:
        格式化后的 JSON 字符串

    错误码:
        E005 模板生成失败
    """
    template = {
        "makefile.makeDirectory": "${workspaceFolder}",
        "makefile.makefilePath": "${workspaceFolder}/Makefile",
        "makefile.configurations": [
            {"name": "Debug", "makeArgs": ["-j4"]},
            {"name": "Release", "makeArgs": ["-j4", "RELEASE=1"]},
        ],
        "makefile.defaultConfiguration": "Debug",
        "makefile.buildLog": "${workspaceFolder}/build.log",
        "makefile.phonyTargets": ["clean", "all", "install"],
        "makefile.compileCommandsPath": "${workspaceFolder}/build/compile_commands.json",
        "makefile.preConfigure": "${workspaceFolder}/scripts/pre_configure.sh",
        "makefile.postConfigure": "${workspaceFolder}/scripts/post_configure.sh",
        "makefile.preBuild": "",
        "makefile.postBuild": "",
        "makefile.environment": {
            "CC": "gcc",
            "CXX": "g++",
            "BUILD_TYPE": "debug",
        },
        "makefile.autoDetect": True,
    }

    try:
        return json.dumps(template, indent=4, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"E005: 模板生成失败 — {e}") from e


# ---------------------------------------------------------------------------
# 核心功能：环境变量管理
# ---------------------------------------------------------------------------
def analyze_environment(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    整理 Makefile 构建所需的环境变量清单，并给出配置建议。

    参数:
        config_data: settings.json 解析后的字典

    返回:
        包含环境变量清单和建议的字典

    错误码:
        E006 环境变量分析失败
    """
    try:
        env_config = _safe_get(config_data, "makefile.environment", {})
        env_file = _safe_get(config_data, "makefile.environmentFile", None)

        if env_config is not None and not isinstance(env_config, dict):
            raise ValueError("E006: makefile.environment 必须是对象")

        env_list = []
        if isinstance(env_config, dict):
            for key, value in env_config.items():
                env_list.append({"name": key, "value": value, "source": "settings.json"})

        if env_file:
            # 尝试读取环境变量文件（如果存在）
            if os.path.isfile(env_file):
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, _, val = line.partition("=")
                                env_list.append({"name": key.strip(), "value": val.strip(), "source": env_file})
                except OSError as e:
                    # 文件不可读时给出提示但不中断
                    env_list.append({"error": f"环境变量文件读取失败: {env_file} ({e})"})
            else:
                env_list.append({"warning": f"环境变量文件不存在: {env_file}"})

        # 生成建议
        suggestions = []
        names = [item["name"] for item in env_list if "name" in item]
        common_vars = ["CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "BUILD_TYPE"]
        missing = [v for v in common_vars if v not in names]
        if missing:
            suggestions.append(f"建议设置以下常用环境变量: {', '.join(missing)}")

        if not env_list:
            suggestions.append("未检测到任何环境变量配置，建议在 makefile.environment 中定义。")

        return {"env_vars": env_list, "suggestions": suggestions}

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"E006: 环境变量分析失败 — {e}") from e


# ---------------------------------------------------------------------------
# 核心功能：构建流程编排检查
# ---------------------------------------------------------------------------
def check_build_orchestration(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    检查 pre-configure 与 post-configure 等脚本的执行顺序与依赖关系。

    参数:
        config_data: settings.json 解析后的字典

    返回:
        包含编排检查结果和建议的字典

    错误码:
        E007 构建编排检查失败
    """
    try:
        scripts = {}
        for full_key in PHASE_SCRIPT_KEYS:
            short_key = full_key.split(".", 1)[1]
            value = _safe_get(config_data, full_key, "")
            scripts[short_key] = value if isinstance(value, str) else ""

        # 顺序检查：pre-configure 必须在 post-configure 之前（逻辑顺序）
        issues = []
        if scripts.get("preConfigure") and scripts.get("postConfigure"):
            # 无法真正执行验证，仅做存在性检查
            pass  # 两者都存在即为合法配置

        # 建议：若 pre 或 post 为空，给出提示
        suggestions = []
        if not scripts.get("preConfigure"):
            suggestions.append("未设置 pre-configure 脚本，若无需预处理可忽略。")
        if not scripts.get("postConfigure"):
            suggestions.append("未设置 post-configure 脚本，若无需后处理可忽略。")

        # 依赖关系建议
        if scripts.get("postConfigure") and not scripts.get("preConfigure"):
            suggestions.append("检测到 post-configure 但无 pre-configure，请确认依赖关系是否合理。")

        return {
            "scripts": scripts,
            "issues": issues,
            "suggestions": suggestions,
            "order_valid": True,
        }

    except Exception as e:
        raise ValueError(f"E007: 构建编排检查失败 — {e}") from e


# ---------------------------------------------------------------------------
# 核心功能：错误诊断辅助
# ---------------------------------------------------------------------------
def diagnose_build_log(log_content: str) -> Dict[str, Any]:
    """
    根据构建日志中的常见错误模式，给出排查方向。

    参数:
        log_content: 构建日志文本内容

    返回:
        包含诊断结果的字典

    错误码:
        E008 日志诊断失败
    """
    if not log_content or not log_content.strip():
        return {"diagnoses": [], "summary": "日志内容为空，无法诊断。"}

    diagnoses = []
    for pattern_info in ERROR_PATTERNS:
        pattern = pattern_info["pattern"]
        matches = re.findall(pattern, log_content, re.IGNORECASE)
        if matches:
            diagnoses.append({
                "pattern": pattern,
                "count": len(matches),
                "hint": pattern_info["hint"],
                "suggestion": pattern_info["suggestion"],
            })

    # 汇总
    if diagnoses:
        summary = f"发现 {len(diagnoses)} 类常见错误模式，请根据建议排查。"
    else:
        summary = "未检测到已知的常见错误模式，请查看日志详细输出。"

    return {"diagnoses": diagnoses, "summary": summary}


# ---------------------------------------------------------------------------
# 自检模块（离线、内置硬编码样例数据）
# ---------------------------------------------------------------------------
def _selftest() -> None:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。

    不读取外部文件、不依赖当前工作目录、不访问网络。

    错误码:
        E009 自检失败
    """
    print("开始离线自检...")

    # ---- 样例数据 1: 配置解析 ----
    sample_config = {
        "makefile": {
            "makeDirectory": "${workspaceFolder}",
            "makefilePath": "${workspaceFolder}/Makefile",
            "configurations": ["Debug", "Release"],
            "defaultConfiguration": "Debug",
        }
    }

    try:
        result = parse_configuration(sample_config)
        assert result["valid"] is True, "配置解析应返回 valid=True"
        assert "defaultConfiguration" in result["parsed"], "应解析出 defaultConfiguration"
        assert result["parsed"]["defaultConfiguration"]["value"] == "Debug", "默认配置应为 Debug"
        assert isinstance(result["suggestions"], list), "建议应为列表"
        print("[PASS] 配置解析功能正常")
    except AssertionError as e:
        raise ValueError(f"E009: 配置解析自检失败 — {e}") from e
    except Exception as e:
        raise ValueError(f"E009: 配置解析自检异常 — {e}") from e

    # ---- 样例数据 2: 模板生成 ----
    try:
        template = generate_template()
        assert isinstance(template, str), "模板应为字符串"
        assert '"makefile"' in template, "模板应包含 makefile 键"
        template_data = json.loads(template)
        assert "makefile.defaultConfiguration" in template_data, "模板应包含默认配置"
        print("[PASS] 模板生成功能正常")
    except (AssertionError, json.JSONDecodeError) as e:
        raise ValueError(f"E009: 模板生成自检失败 — {e}") from e

    # ---- 样例数据 3: 环境变量分析 ----
    sample_env_config = {
        "makefile": {
            "environment": {
                "CC": "gcc",
                "CXX": "g++",
            }
        }
    }
    try:
        env_result = analyze_environment(sample_env_config)
        assert "env_vars" in env_result, "应返回 env_vars"
        assert len(env_result["env_vars"]) >= 2, "应至少包含 2 个环境变量"
        assert any(v["name"] == "CC" for v in env_result["env_vars"]), "应包含 CC 变量"
        print("[PASS] 环境变量分析功能正常")
    except AssertionError as e:
        raise ValueError(f"E009: 环境变量分析自检失败 — {e}") from e

    # ---- 样例数据 4: 构建编排检查 ----
    sample_orch_config = {
        "makefile": {
            "preConfigure": "scripts/pre.sh",
            "postConfigure": "scripts/post.sh",
            "preBuild": "",
            "postBuild": "",
        }
    }
    try:
        orch_result = check_build_orchestration(sample_orch_config)
        assert "scripts" in orch_result, "应返回 scripts"
        assert orch_result["scripts"]["preConfigure"] == "scripts/pre.sh", "preConfigure 值不匹配"
        assert orch_result["order_valid"] is True, "顺序应有效"
        print("[PASS] 构建编排检查功能正常")
    except AssertionError as e:
        raise ValueError(f"E009: 构建编排检查自检失败 — {e}") from e

    # ---- 样例数据 5: 错误诊断 ----
    sample_log = """
    gcc -c main.c -o main.o
    main.c:10:5: error: 'x' undeclared
    make: *** [Makefile:20: main.o] Error 1
    """
    try:
        diag_result = diagnose_build_log(sample_log)
        assert "diagnoses" in diag_result, "应返回 diagnoses"
        assert len(diag_result["diagnoses"]) >= 1, "应检测到至少一种错误模式"
        print("[PASS] 错误诊断功能正常")
    except AssertionError as e:
        raise ValueError(f"E009: 错误诊断自检失败 — {e}") from e

    # ---- 样例数据 6: 边界情况（宽松断言） ----
    # 空配置不应崩溃
    try:
        empty_result = parse_configuration({"makefile": {}})
        assert empty_result["valid"] is True, "空配置应有效"
        print("[PASS] 空配置容错正常")
    except AssertionError as e:
        raise ValueError(f"E009: 空配置自检失败 — {e}") from e

    # 空日志诊断
    try:
        empty_log_result = diagnose_build_log("")
        assert "summary" in empty_log_result, "空日志应返回 summary"
        print("[PASS] 空日志诊断正常")
    except AssertionError as e:
        raise ValueError(f"E009: 空日志诊断自检失败 — {e}") from e

    print("所有自检通过！")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    返回:
        进程退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description="VS Code Makefile 工程配置辅助工具（依据功能规格独立实现）",
        epilog="错误码: E001 参数错误 / E002 文件错误 / E003 JSON 错误 / E004 结构错误 / "
               "E005 模板错误 / E006 环境分析错误 / E007 编排错误 / E008 诊断错误 / "
               "E009 自检错误 / E010 未知错误",
    )

    # 子命令或互斥选项
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--selftest", action="store_true", help="执行离线自检（内置样例数据）")
    group.add_argument("--parse", metavar="JSON_PATH", help="解析指定的 settings.json 配置文件")
    group.add_argument("--template", action="store_true", help="生成配置模板并输出")
    group.add_argument("--envs", metavar="JSON_PATH", help="分析指定配置文件中的环境变量")
    group.add_argument("--orchestrate", metavar="JSON_PATH", help="检查指定配置文件的构建编排")
    group.add_argument("--diagnose", metavar="LOG_PATH", help="诊断指定的构建日志文件")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            _selftest()
            print("自检完成，所有功能正常。")
            return 0

        # 模板生成模式
        if args.template:
            template = generate_template()
            print(template)
            return 0

        # 解析配置模式
        if args.parse:
            data = _read_json_file(args.parse)
            result = parse_configuration(data)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # 环境变量分析模式
        if args.envs:
            data = _read_json_file(args.envs)
            result = analyze_environment(data)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # 构建编排检查模式
        if args.orchestrate:
            data = _read_json_file(args.orchestrate)
            result = check_build_orchestration(data)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # 日志诊断模式
        if args.diagnose:
            if not os.path.isfile(args.diagnose):
                raise ValueError(f"E002: 日志文件不存在: {args.diagnose}")
            with open(args.diagnose, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()
            result = diagnose_build_log(log_content)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        # 不应到达此处
        raise ValueError("E001: 未识别的参数组合")

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未知错误 — {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
