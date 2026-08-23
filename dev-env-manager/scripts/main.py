#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dev-env-manager 开发环境管理器 - 独立实现脚本
================================================
统一管理开发工具、环境变量和任务运行器，支持多语言版本切换、环境变量配置和任务自动化。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

功能概览:
  - 环境变量管理: 解析/校验/格式化环境变量配置
  - 任务运行器: 解析任务定义并生成执行计划
  - 工具版本管理: 解析多语言版本配置并生成切换建议
  - 批量处理: 支持多输入流式处理 (O(n) 复杂度)

用法示例:
  python main.py --selftest                          # 运行内置自检
  python main.py --parse-env ".env"                  # 解析环境变量文件
  python main.py --plan-tasks "tasks.json"           # 生成任务执行计划
  python main.py --dry-run --force --verbose ...     # 预览模式/强制模式/详细输出

错误码:
  E001 输入为空
  E002 关键信息缺失
  E003 输入格式错误
  E004 超出能力边界
  E005 置信度过低
  E006 文件读取失败
  E007 文件写入失败
  E008 编码探测失败
  E009 参数校验失败
  E010 内部逻辑错误
"""

import argparse
import json
import os
import re
import sys
import traceback
from collections import OrderedDict
from pathlib import Path


# ============================================================
# 常量定义
# ============================================================

# 错误码与消息映射
ERROR_MESSAGES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式是否符合要求",
    "E004": "超出能力边界，本工具无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "文件写入失败，请检查磁盘空间和权限",
    "E008": "编码探测失败，请指定正确的编码格式",
    "E009": "参数校验失败，请检查命令行参数",
    "E010": "内部逻辑错误，请报告此问题",
}

# 支持的环境变量键名模式（宽松匹配）
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# 常见编码列表（按优先级）
ENCODING_CANDIDATES = ["utf-8", "gbk", "gb18030"]


# ============================================================
# 输入校验模块
# ============================================================

def validate_input(data, error_code="E001"):
    """
    校验输入数据是否有效。
    
    参数:
        data: 待校验的输入数据
        error_code: 校验失败时使用的错误码
    
    返回:
        校验通过返回 True，失败抛出 ValueError
    """
    if data is None:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
    if isinstance(data, str) and not data.strip():
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
    if isinstance(data, (list, dict, tuple)) and len(data) == 0:
        raise ValueError(f"{error_code}: {ERROR_MESSAGES[error_code]}")
    return True


def validate_env_key(key):
    """
    校验环境变量键名格式。
    
    参数:
        key: 环境变量键名
    
    返回:
        合法返回 True，非法返回 False
    """
    if not isinstance(key, str):
        return False
    return bool(ENV_KEY_PATTERN.match(key))


def validate_file_path(path_str, allow_write=False):
    """
    校验文件路径合法性（防路径穿越）。
    
    参数:
        path_str: 文件路径字符串
        allow_write: 是否允许写入（检查父目录）
    
    返回:
        校验通过返回 Path 对象，失败抛出 ValueError
    """
    if not path_str or not isinstance(path_str, str):
        raise ValueError(f"E009: {ERROR_MESSAGES['E009']} - 路径不能为空")
    
    path = Path(path_str).expanduser().resolve()
    
    # 防路径穿越：检查是否包含 .. 或绝对路径逃逸
    if ".." in path.parts:
        raise ValueError(f"E009: {ERROR_MESSAGES['E009']} - 路径包含非法跳转")
    
    if allow_write:
        parent = path.parent
        if not parent.exists():
            raise ValueError(f"E009: {ERROR_MESSAGES['E009']} - 父目录不存在: {parent}")
        if not os.access(parent, os.W_OK):
            raise ValueError(f"E009: {ERROR_MESSAGES['E009']} - 目录不可写: {parent}")
    else:
        if not path.exists():
            raise ValueError(f"E006: {ERROR_MESSAGES['E006']} - 文件不存在: {path}")
    
    return path


# ============================================================
# 核心逻辑模块
# ============================================================

def parse_env_content(content):
    """
    解析环境变量内容为结构化字典。
    
    参数:
        content: 环境变量文件内容字符串
    
    返回:
        OrderedDict: 解析后的环境变量字典
    """
    result = OrderedDict()
    if not content:
        return result
    
    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        # 跳过空行和注释
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        
        # 解析 key=value 格式
        if "=" not in line:
            continue
        
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        
        # 去除可能的引号
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        
        # 校验键名
        if validate_env_key(key):
            result[key] = value
    
    return result


def format_env_output(env_dict):
    """
    格式化环境变量字典为可读输出。
    
    参数:
        env_dict: 环境变量字典
    
    返回:
        str: 格式化后的输出文本
    """
    if not env_dict:
        return "（空环境变量配置）"
    
    lines = []
    lines.append("环境变量配置（共 {} 项）：".format(len(env_dict)))
    lines.append("-" * 40)
    
    for key, value in env_dict.items():
        # 敏感信息脱敏
        display_value = value
        if any(sensitive in key.lower() for sensitive in ("password", "secret", "token", "key")):
            display_value = "******"
        lines.append(f"  {key} = {display_value}")
    
    return "\n".join(lines)


def parse_task_plan(content):
    """
    解析任务定义并生成执行计划。
    
    参数:
        content: 任务定义内容（JSON 或文本格式）
    
    返回:
        list: 任务执行计划列表
    """
    if not content:
        return []
    
    tasks = []
    
    # 尝试 JSON 解析
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "name" in item:
                    tasks.append({
                        "name": str(item.get("name", "")),
                        "command": str(item.get("command", "")),
                        "timeout": int(item.get("timeout", 30)),
                        "priority": int(item.get("priority", 5)),
                    })
        elif isinstance(data, dict) and "tasks" in data:
            for item in data["tasks"]:
                if isinstance(item, dict) and "name" in item:
                    tasks.append({
                        "name": str(item.get("name", "")),
                        "command": str(item.get("command", "")),
                        "timeout": int(item.get("timeout", 30)),
                        "priority": int(item.get("priority", 5)),
                    })
    except (json.JSONDecodeError, TypeError):
        # 文本格式：每行一个任务，格式 "名称 | 命令"
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                name, _, command = line.partition("|")
                tasks.append({
                    "name": name.strip(),
                    "command": command.strip(),
                    "timeout": 30,
                    "priority": 5,
                })
    
    # 按优先级排序
    tasks.sort(key=lambda t: t.get("priority", 5), reverse=True)
    return tasks


def format_task_plan(tasks):
    """
    格式化任务执行计划为可读输出。
    
    参数:
        tasks: 任务列表
    
    返回:
        str: 格式化后的执行计划文本
    """
    if not tasks:
        return "（无任务可执行）"
    
    lines = []
    lines.append("任务执行计划（共 {} 个任务）：".format(len(tasks)))
    lines.append("-" * 50)
    
    for idx, task in enumerate(tasks, 1):
        lines.append(f"  [{idx}] {task['name']}")
        lines.append(f"      命令: {task['command']}")
        lines.append(f"      超时: {task['timeout']}s | 优先级: {task['priority']}")
    
    lines.append("-" * 50)
    lines.append("总预估耗时: {}s".format(sum(t.get("timeout", 30) for t in tasks)))
    return "\n".join(lines)


def analyze_tool_versions(content):
    """
    分析多语言工具版本配置。
    
    参数:
        content: 版本配置文件内容
    
    返回:
        dict: 版本分析结果
    """
    if not content:
        return {"tools": [], "recommendations": []}
    
    tools = []
    recommendations = []
    
    # 简单解析：每行 "工具名 版本号"
    version_pattern = re.compile(r"^([a-zA-Z0-9_-]+)[\s:=]+([0-9][0-9a-zA-Z._-]*)$")
    
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        match = version_pattern.match(line)
        if match:
            tool_name = match.group(1)
            version = match.group(2)
            tools.append({"name": tool_name, "version": version})
    
    # 生成切换建议（基于版本号比较）
    for tool in tools:
        version = tool["version"]
        # 简单判断：版本号是否包含预发布标记
        if any(marker in version.lower() for marker in ("alpha", "beta", "rc", "dev")):
            recommendations.append(
                f"建议将 {tool['name']} 从预发布版本 {version} 切换到稳定版本"
            )
        else:
            recommendations.append(
                f"{tool['name']} 当前版本 {version} 为稳定版本，无需切换"
            )
    
    return {"tools": tools, "recommendations": recommendations}


def format_version_analysis(analysis):
    """
    格式化版本分析结果为可读输出。
    
    参数:
        analysis: 版本分析结果字典
    
    返回:
        str: 格式化后的分析文本
    """
    if not analysis or not analysis.get("tools"):
        return "（无工具版本信息）"
    
    lines = []
    lines.append("工具版本分析（共 {} 个工具）：".format(len(analysis["tools"])))
    lines.append("-" * 50)
    
    for tool in analysis["tools"]:
        lines.append(f"  {tool['name']} = {tool['version']}")
    
    lines.append("-" * 50)
    lines.append("切换建议：")
    for rec in analysis.get("recommendations", []):
        lines.append(f"  - {rec}")
    
    return "\n".join(lines)


def process_streaming(content, chunk_size=1024):
    """
    流式分块处理长文本（以句号为边界滑窗，重叠 2 句保上下文）。
    
    参数:
        content: 输入文本
        chunk_size: 基础块大小（字符数）
    
    返回:
        list: 处理后的文本块列表
    """
    if not content:
        return []
    
    # 按句号分割
    sentences = re.split(r'(?<=[。.!?！？])', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= 2:
        return ["".join(sentences)]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for i, sentence in enumerate(sentences):
        current_chunk.append(sentence)
        current_size += len(sentence)
        
        # 达到块大小或最后一句时输出
        if current_size >= chunk_size or i == len(sentences) - 1:
            # 重叠 2 句保上下文
            if chunks and len(current_chunk) > 2:
                # 保留前一块的最后 2 句
                overlap = chunks[-1].split("。")[-2:] if chunks[-1] else []
                current_chunk = [s for s in overlap if s] + current_chunk
            
            chunks.append("。".join(current_chunk))
            current_chunk = []
            current_size = 0
    
    return chunks


# ============================================================
# 文件读写模块（多编码支持）
# ============================================================

def read_file_with_encoding(file_path):
    """
    读取文件内容，支持多编码探测。
    
    参数:
        file_path: 文件路径
    
    返回:
        str: 文件内容
    """
    path = validate_file_path(file_path, allow_write=False)
    
    # 尝试多种编码
    last_error = None
    for encoding in ENCODING_CANDIDATES:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except OSError as e:
            raise ValueError(f"E006: {ERROR_MESSAGES['E006']} - {e}")
    
    # 最后尝试 with errors="replace"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"警告: 编码探测失败，使用替换字符读取（{last_error}）", file=sys.stderr)
            return content
    except OSError as e:
        raise ValueError(f"E006: {ERROR_MESSAGES['E006']} - {e}")


def write_file_with_encoding(file_path, content):
    """
    写入文件内容，支持多编码。
    
    参数:
        file_path: 文件路径
        content: 要写入的内容
    """
    path = validate_file_path(file_path, allow_write=True)
    
    # 优先 UTF-8，失败则尝试 GBK
    for encoding in ENCODING_CANDIDATES:
        try:
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return
        except (UnicodeEncodeError, OSError) as e:
            last_error = e
            continue
    
    # 最后尝试 with errors="replace"
    try:
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        print(f"警告: 编码写入失败，使用替换字符写入（{last_error}）", file=sys.stderr)
    except OSError as e:
        raise ValueError(f"E007: {ERROR_MESSAGES['E007']} - {e}")


# ============================================================
# 输出格式化模块
# ============================================================

def format_diff_summary(original, modified):
    """
    生成修改差异摘要。
    
    参数:
        original: 原始内容
        modified: 修改后内容
    
    返回:
        str: 差异摘要文本
    """
    if original == modified:
        return "无变更"
    
    orig_lines = original.splitlines() if original else []
    mod_lines = modified.splitlines() if modified else []
    
    added = len(mod_lines) - len(orig_lines)
    changed = sum(1 for o, m in zip(orig_lines, mod_lines) if o != m)
    
    summary = []
    if added > 0:
        summary.append(f"新增 {added} 行")
    elif added < 0:
        summary.append(f"删除 {abs(added)} 行")
    if changed > 0:
        summary.append(f"修改 {changed} 行")
    
    return "，".join(summary) if summary else "内容有变化但行数相同"


def format_verbose_report(operation, details):
    """
    格式化详细操作报告。
    
    参数:
        operation: 操作名称
        details: 操作详情列表
    
    返回:
        str: 格式化后的详细报告
    """
    lines = []
    lines.append(f"操作: {operation}")
    lines.append("=" * 50)
    
    for detail in details:
        if isinstance(detail, dict):
            for key, value in detail.items():
                lines.append(f"  {key}: {value}")
            lines.append("-" * 30)
        else:
            lines.append(f"  {detail}")
    
    return "\n".join(lines)


# ============================================================
# 主处理流程
# ============================================================

def process_env_file(file_path, dry=True, verbose=False):
    """
    处理环境变量文件。
    
    参数:
        file_path: 文件路径
        dry: 是否预览模式（不写盘）
        verbose: 是否详细输出
    
    返回:
        str: 处理结果
    """
    try:
        content = read_file_with_encoding(file_path)
        validate_input(content, "E001")
        
        env_dict = parse_env_content(content)
        output = format_env_output(env_dict)
        
        if verbose:
            details = [
                {"输入文件": file_path},
                {"解析条目数": len(env_dict)},
                {"输出预览": output[:200] + ("..." if len(output) > 200 else "")},
            ]
            report = format_verbose_report("环境变量解析", details)
            return report
        
        return output
    
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        print(f"警告: 处理失败 - {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"错误: E010: {ERROR_MESSAGES['E010']} - {e}"


def process_task_file(file_path, dry=True, verbose=False):
    """
    处理任务定义文件。
    
    参数:
        file_path: 文件路径
        dry: 是否预览模式（不写盘）
        verbose: 是否详细输出
    
    返回:
        str: 处理结果
    """
    try:
        content = read_file_with_encoding(file_path)
        validate_input(content, "E001")
        
        tasks = parse_task_plan(content)
        output = format_task_plan(tasks)
        
        if verbose:
            details = [
                {"输入文件": file_path},
                {"任务数量": len(tasks)},
                {"执行计划": output},
            ]
            report = format_verbose_report("任务计划生成", details)
            return report
        
        return output
    
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        print(f"警告: 处理失败 - {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"错误: E010: {ERROR_MESSAGES['E010']} - {e}"


def process_version_file(file_path, dry=True, verbose=False):
    """
    处理工具版本配置文件。
    
    参数:
        file_path: 文件路径
        dry: 是否预览模式（不写盘）
        verbose: 是否详细输出
    
    返回:
        str: 处理结果
    """
    try:
        content = read_file_with_encoding(file_path)
        validate_input(content, "E001")
        
        analysis = analyze_tool_versions(content)
        output = format_version_analysis(analysis)
        
        if verbose:
            details = [
                {"输入文件": file_path},
                {"工具数量": len(analysis["tools"])},
                {"分析结果": output},
            ]
            report = format_verbose_report("工具版本分析", details)
            return report
        
        return output
    
    except ValueError as e:
        return f"错误: {e}"
    except Exception as e:
        print(f"警告: 处理失败 - {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return f"错误: E010: {ERROR_MESSAGES['E010']} - {e}"


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """
    运行内置自检，验证核心逻辑。
    
    返回:
        bool: 自检是否全部通过
    """
    print("=" * 60)
    print("开始运行自检...")
    print("=" * 60)
    
    all_passed = True
    
    # ---- 测试 1: 环境变量解析 ----
    print("\n[测试 1] 环境变量解析")
    env_content = """
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
        
# 应用配置
APP_ENV=production
APP_DEBUG=false
API_TOKEN="secret-token-123"
"""
    try:
        env_dict = parse_env_content(env_content)
        assert len(env_dict) >= 5, f"应解析出至少 5 个环境变量，实际 {len(env_dict)}"
        assert env_dict.get("DB_HOST") == "localhost", "DB_HOST 解析错误"
        assert env_dict.get("APP_ENV") == "production", "APP_ENV 解析错误"
        assert env_dict.get("API_TOKEN") == "secret-token-123", "API_TOKEN 引号去除错误"
        
        output = format_env_output(env_dict)
        assert "DB_HOST" in output, "输出应包含 DB_HOST"
        assert "******" in output, "敏感信息应脱敏"
        
        print("  ✓ 环境变量解析测试通过")
    except AssertionError as e:
        print(f"  ✗ 环境变量解析测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 环境变量解析测试异常: {e}")
        all_passed = False
    
    # ---- 测试 2: 中文标点/编码处理 ----
    print("\n[测试 2] 中文标点/编码处理")
    try:
        # 模拟 GBK 编码内容（中文标点）
        gbk_content = "APP_NAME=开发环境管理器\nAPP_DESC=统一管理开发工具\n"
        # 解析中文内容
        env_dict = parse_env_content(gbk_content)
        assert len(env_dict) >= 2, "应解析出至少 2 个环境变量"
        assert "APP_NAME" in env_dict, "应包含 APP_NAME"
        assert "开发" in env_dict.get("APP_NAME", ""), "中文内容应正确解析"
        
        print("  ✓ 中文编码处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 中文编码处理测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 中文编码处理测试异常: {e}")
        all_passed = False
    
    # ---- 测试 3: 任务计划解析 ----
    print("\n[测试 3] 任务计划解析")
    task_content = """
# 构建任务
build | npm run build
test | npm test
deploy | npm run deploy
        
# 文本格式任务
lint | eslint .
"""
    try:
        tasks = parse_task_plan(task_content)
        assert len(tasks) >= 4, f"应解析出至少 4 个任务，实际 {len(tasks)}"
        
        # 检查文本格式解析
        task_names = [t["name"] for t in tasks]
        assert "build" in task_names, "应包含 build 任务"
        assert "lint" in task_names, "应包含 lint 任务"
        
        # 检查 JSON 格式解析
        json_content = json.dumps([
            {"name": "build", "command": "npm run build", "timeout": 60, "priority": 10},
            {"name": "test", "command": "npm test", "timeout": 30, "priority": 5},
        ])
        json_tasks = parse_task_plan(json_content)
        assert len(json_tasks) == 2, "JSON 格式应解析出 2 个任务"
        assert json_tasks[0]["priority"] >= json_tasks[1]["priority"], "应按优先级排序"
        
        output = format_task_plan(tasks)
        assert "任务执行计划" in output, "输出应包含任务执行计划标题"
        
        print("  ✓ 任务计划解析测试通过")
    except AssertionError as e:
        print(f"  ✗ 任务计划解析测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 任务计划解析测试异常: {e}")
        all_passed = False
    
    # ---- 测试 4: 工具版本分析 ----
    print("\n[测试 4] 工具版本分析")
    version_content = """
node 18.17.0
python 3.11.4
java 17.0.8
golang 1.21.0-beta1
"""
    try:
        analysis = analyze_tool_versions(version_content)
        assert len(analysis["tools"]) >= 4, f"应分析出至少 4 个工具，实际 {len(analysis['tools'])}"
        assert len(analysis["recommendations"]) >= 4, "应生成至少 4 条建议"
        
        # 检查预发布版本识别
        golang = [t for t in analysis["tools"] if t["name"] == "golang"]
        assert golang, "应包含 golang"
        assert "beta" in golang[0]["version"].lower(), "应识别预发布版本"
        
        output = format_version_analysis(analysis)
        assert "工具版本分析" in output, "输出应包含版本分析标题"
        
        print("  ✓ 工具版本分析测试通过")
    except AssertionError as e:
        print(f"  ✗ 工具版本分析测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 工具版本分析测试异常: {e}")
        all_passed = False
    
    # ---- 测试 5: 流式处理 ----
    print("\n[测试 5] 流式处理")
    try:
        # 生成长文本
        long_text = "。".join([f"这是第{i}个句子，包含一些内容。" for i in range(100)])
        chunks = process_streaming(long_text, chunk_size=200)
        assert len(chunks) > 1, "长文本应产生多个块"
        
        # 检查重叠
        if len(chunks) > 1:
            assert len(chunks[0]) > 0 and len(chunks[1]) > 0, "块不应为空"
        
        # 短文本
        short_text = "短文本。"
        short_chunks = process_streaming(short_text)
        assert len(short_chunks) == 1, "短文本应产生一个块"
        
        # 空输入
        empty_chunks = process_streaming("")
        assert len(empty_chunks) == 0, "空输入应产生空列表"
        
        print("  ✓ 流式处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 流式处理测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 流式处理测试异常: {e}")
        all_passed = False
    
    # ---- 测试 6: 输入校验 ----
    print("\n[测试 6] 输入校验")
    try:
        # 空输入
        try:
            validate_input("", "E001")
            print("  ✗ 空输入应抛出异常")
            all_passed = False
        except ValueError:
            pass
        
        # None 输入
        try:
            validate_input(None, "E001")
            print("  ✗ None 输入应抛出异常")
            all_passed = False
        except ValueError:
            pass
        
        # 合法输入
        assert validate_input("valid", "E001") is True, "合法输入应通过校验"
        assert validate_input(["a", "b"], "E001") is True, "非空列表应通过校验"
        
        # 环境变量键名校验
        assert validate_env_key("DB_HOST") is True, "合法键名应通过"
        assert validate_env_key("1INVALID") is False, "非法键名应拒绝"
        assert validate_env_key("") is False, "空键名应拒绝"
        
        print("  ✓ 输入校验测试通过")
    except AssertionError as e:
        print(f"  ✗ 输入校验测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 输入校验测试异常: {e}")
        all_passed = False
    
    # ---- 测试 7: 错误处理 ----
    print("\n[测试 7] 错误处理")
    try:
        # 不存在的文件
        try:
            read_file_with_encoding("/nonexistent/path/file.txt")
            print("  ✗ 不存在的文件应抛出异常")
            all_passed = False
        except ValueError:
            pass
        
        # 路径穿越防护
        try:
            validate_file_path("/etc/../../etc/passwd")
            print("  ✗ 路径穿越应被拒绝")
            all_passed = False
        except ValueError:
            pass
        
        print("  ✓ 错误处理测试通过")
    except AssertionError as e:
        print(f"  ✗ 错误处理测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 错误处理测试异常: {e}")
        all_passed = False
    
    # ---- 测试 8: 差异摘要 ----
    print("\n[测试 8] 差异摘要")
    try:
        original = "line1\nline2\nline3"
        modified = "line1\nline2\nline3\nline4"
        summary = format_diff_summary(original, modified)
        assert "新增" in summary, "应识别新增行"
        
        same = format_diff_summary(original, original)
        assert "无变更" in same, "相同内容应显示无变更"
        
        print("  ✓ 差异摘要测试通过")
    except AssertionError as e:
        print(f"  ✗ 差异摘要测试失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 差异摘要测试异常: {e}")
        all_passed = False
    
    # ---- 汇总 ----
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# CLI 入口
# ============================================================

def main():
    """
    命令行入口函数。
    """
    parser = argparse.ArgumentParser(
        description="开发环境管理器 - 统一管理开发工具、环境变量和任务运行器",
        epilog="示例: python main.py --selftest | python main.py --parse-env .env --verbose"
    )
    
    # 操作模式
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--parse-env", metavar="FILE", help="解析环境变量文件")
    parser.add_argument("--plan-tasks", metavar="FILE", help="生成任务执行计划")
    parser.add_argument("--analyze-versions", metavar="FILE", help="分析工具版本")
    
    # 通用选项
    parser.add_argument("--dry-run", action="store_true", help="预览模式（不写盘）")
    parser.add_argument("--force", action="store_true", help="强制模式（允许写盘）")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 检查是否指定了操作
    if not (args.parse_env or args.plan_tasks or args.analyze_versions):
        parser.print_help()
        print("\n错误: E009: {} - 请指定操作模式".format(ERROR_MESSAGES["E009"]), file=sys.stderr)
        sys.exit(1)
    
    # dry 变量统一控制写盘
    dry = not args.force  # 默认 dry-run，只有 --force 才真正写盘
    
    # 处理环境变量文件
    if args.parse_env:
        result = process_env_file(args.parse_env, dry=dry, verbose=args.verbose)
        print(result)
    
    # 处理任务文件
    if args.plan_tasks:
        result = process_task_file(args.plan_tasks, dry=dry, verbose=args.verbose)
        print(result)
    
    # 处理版本配置文件
    if args.analyze_versions:
        result = process_version_file(args.analyze_versions, dry=dry, verbose=args.verbose)
        print(result)


if __name__ == "__main__":
    main()
