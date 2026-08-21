#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI应用构建器底座 - 独立实现脚本

根据功能规格 clean-room 重写，仅依赖标准库。
提供：输入解析、关键信息提取、结构化输出、置信度标注、批量处理、构建验证与部署调用。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import unified_diff

# ============================================================
# 错误码定义（与规格一致）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果需人工复核",
    "E006": "文件读取失败，请检查文件路径",
    "E007": "文件写入失败，请检查权限",
    "E008": "参数校验失败，请检查命令行参数",
    "E009": "内部逻辑错误，请联系开发者",
    "E010": "未知异常，请查看错误详情",
    "E011": "构建验证失败，请检查构建配置",
    "E012": "部署调用失败，请检查部署配置",
}


# ============================================================
# 输入校验模块
# ============================================================
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


# 批处理流式读取工具（复用 _read_text_safe 的编码回退逻辑）
def _iter_lines(path):
    """流式读取文件行，支持多编码回退"""
    content = _read_text_safe(path)
    for line in content.splitlines():
        yield line + "\n"


def validate_input(raw_text):
    """
    校验输入文本的有效性。

    参数:
        raw_text: 原始输入字符串

    返回:
        (是否有效, 错误码或None)
    """
    if raw_text is None:
        return False, "E001"
    if not isinstance(raw_text, str):
        return False, "E003"
    if not raw_text.strip():
        return False, "E001"
    return True, None


def validate_output_format(fmt):
    """
    校验输出格式参数。

    参数:
        fmt: 输出格式字符串

    返回:
        (是否有效, 错误码或None)
    """
    valid_formats = {"text", "json", "table"}
    if fmt not in valid_formats:
        return False, "E003"
    return True, None


def validate_confidence_threshold(threshold):
    """
    校验置信度阈值参数。

    参数:
        threshold: 置信度阈值（0-100）

    返回:
        (是否有效, 错误码或None)
    """
    if threshold is None:
        return True, None
    try:
        val = float(threshold)
    except (TypeError, ValueError):
        return False, "E003"
    if val < 0 or val > 100:
        return False, "E003"
    # 边界值校验
    if val == 0 or val == 100:
        return True, None
    # 检查是否为有限数
    if not isinstance(val, float) or val != val or val in (float('inf'), float('-inf')):
        return False, "E003"
    return True, None


# ============================================================
# 核心逻辑模块
# ============================================================
def extract_key_info(text):
    """
    从输入文本中提取关键信息。

    策略：
    - 识别中英文标点作为句子边界
    - 提取包含关键字的句子作为关键信息
    - 统计文本统计特征用于置信度计算

    参数:
        text: 输入文本

    返回:
        dict: 包含关键信息、统计特征、置信度
    """
    # 防御性处理
    if not text or not text.strip():
        return {
            "key_points": [],
            "stats": {"total_chars": 0, "sentence_count": 0},
            "confidence": 0.0,
        }

    # 按中英文标点切分句子
    sentences = re.split(r'[。！？!?；;]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 关键信息关键词
    keywords = [
        "需求", "功能", "目标", "用户", "系统", "数据",
        "require", "feature", "goal", "user", "system", "data",
        "构建", "部署", "模板", "生成", "验证",
        "build", "deploy", "template", "generate", "verify",
    ]

    key_points = []
    for sent in sentences:
        # 检查是否包含关键词
        has_keyword = any(kw.lower() in sent.lower() for kw in keywords)
        # 检查句子长度（太短或太长都降低重要性）
        length_score = min(len(sent) / 50, 1.0) if len(sent) > 5 else 0.3
        if has_keyword and length_score > 0.3:
            key_points.append({
                "text": sent,
                "importance": round(length_score, 2),
            })

    # 计算统计特征
    total_chars = len(text)
    sentence_count = len(sentences)
    # 粗略估计信息密度（非空字符占比）
    non_space_chars = len(re.sub(r'\s', '', text))
    density = non_space_chars / max(total_chars, 1)

    # 置信度计算（基于信息完整度）
    confidence = min(95.0, 60.0 + sentence_count * 5 + density * 20)
    if not key_points:
        confidence = min(confidence, 70.0)

    return {
        "key_points": key_points[:10],  # 最多保留10条
        "stats": {
            "total_chars": total_chars,
            "sentence_count": sentence_count,
            "info_density": round(density, 3),
        },
        "confidence": round(confidence, 1),
    }


def format_output(result, fmt="text"):
    """
    将处理结果格式化为指定格式。

    参数:
        result: 处理结果字典
        fmt: 输出格式（text/json/table）

    返回:
        str: 格式化后的字符串
    """
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)

    if fmt == "table":
        lines = ["| 序号 | 关键信息 | 重要度 |", "|------|----------|--------|"]
        for i, point in enumerate(result.get("key_points", []), 1):
            lines.append(
                f"| {i} | {point['text'][:30]}... | {point['importance']} |"
            )
        lines.append("")
        lines.append(f"置信度: {result.get('confidence', 0)}%")
        return "\n".join(lines)

    # 默认 text 格式
    lines = ["=== AI应用构建器底座 - 处理结果 ===", ""]
    lines.append(f"输入统计: {result['stats']['total_chars']} 字符, "
                 f"{result['stats']['sentence_count']} 句")
    lines.append(f"信息密度: {result['stats']['info_density']}")
    lines.append("")
    lines.append("关键信息:")
    for i, point in enumerate(result.get("key_points", []), 1):
        lines.append(f"  {i}. {point['text']}")
    lines.append("")
    lines.append(f"置信度: {result['confidence']}%")
    if result["confidence"] < 85:
        lines.append("[需核实] 置信度较低，请人工复核关键结果")
    return "\n".join(lines)


def _process_single(item, fmt="text"):
    """处理单个输入项（供线程池调用）"""
    try:
        valid, err_code = validate_input(item)
        if not valid:
            return {
                "input": item,
                "error": err_code,
                "error_msg": ERROR_CODES[err_code],
                "result": None,
            }
        result = extract_key_info(item)
        result["formatted"] = format_output(result, fmt)
        return {
            "input": item,
            "error": None,
            "result": result,
        }
    except Exception as exc:
        # 单条失败不影响整体
        return {
            "input": item,
            "error": "E010",
            "error_msg": f"处理失败: {str(exc)}",
            "result": None,
        }


def process_batch(inputs, fmt="text", max_workers=4):
    """
    批量处理多个输入（并行）。

    参数:
        inputs: 输入列表
        fmt: 输出格式
        max_workers: 最大并发数

    返回:
        list: 处理结果列表
    """
    # 限制最大并发数，防止资源耗尽
    max_workers = min(max_workers, 4)
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(_process_single, item, fmt): item
            for item in inputs
        }
        for future in as_completed(future_to_item):
            results.append(future.result())
    # 保持输入顺序
    results.sort(key=lambda x: inputs.index(x["input"]) if x["input"] in inputs else 0)
    return results


# ============================================================
# 构建验证与部署模块
# ============================================================
def verify_build(project_dir=None, build_command=None, timeout=30):
    """
    验证构建配置和构建过程。

    参数:
        project_dir: 项目目录（可选）
        build_command: 构建命令（可选）
        timeout: 构建超时时间（秒）

    返回:
        dict: 构建验证结果
    """
    result = {
        "verified": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": [],
    }

    # 检查项目目录
    if project_dir:
        if not os.path.isdir(project_dir):
            result["details"].append(f"项目目录不存在: {project_dir}")
            result["error"] = "E011"
            return result
        result["details"].append(f"项目目录存在: {project_dir}")

        # 检查常见构建配置文件
        build_files = ["build.gradle", "pom.xml", "package.json", "Makefile", "Dockerfile"]
        found_build_files = [f for f in build_files if os.path.isfile(os.path.join(project_dir, f))]
        if found_build_files:
            result["details"].append(f"找到构建配置文件: {', '.join(found_build_files)}")
        else:
            result["details"].append("未找到标准构建配置文件")

    # 检查构建命令
    if build_command:
        result["details"].append(f"构建命令: {build_command}")
        try:
            # 实际执行构建命令（带超时）
            proc = subprocess.run(
                build_command,
                shell=True,
                cwd=project_dir if project_dir else None,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode == 0:
                result["verified"] = True
                result["details"].append(f"构建成功 (退出码 0)")
                if proc.stdout:
                    result["details"].append(f"构建输出: {proc.stdout[-500:]}")
            else:
                result["error"] = "E011"
                result["details"].append(f"构建失败 (退出码 {proc.returncode})")
                if proc.stderr:
                    result["details"].append(f"错误输出: {proc.stderr[-500:]}")
        except subprocess.TimeoutExpired:
            result["error"] = "E011"
            result["details"].append(f"构建超时（{timeout}秒）")
        except Exception as exc:
            result["error"] = "E011"
            result["details"].append(f"构建执行异常: {str(exc)}")
    else:
        result["details"].append("未指定构建命令")
        # 无构建命令时，仅验证配置存在
        if project_dir and found_build_files:
            result["verified"] = True
            result["details"].append("构建配置验证通过（未执行构建）")
        else:
            result["error"] = "E011"
            result["details"].append("构建验证失败：无构建命令且无构建配置")

    return result


def deploy_application(deploy_url=None, deploy_token=None, project_name=None, timeout=10, max_retries=3):
    """
    调用部署API（带重试退避和超时）。

    参数:
        deploy_url: 部署API地址
        deploy_token: 部署令牌
        project_name: 项目名称
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数

    返回:
        dict: 部署结果
    """
    result = {
        "deployed": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": [],
    }

    if not deploy_url:
        result["details"].append("未指定部署URL")
        result["error"] = "E012"
        return result

    if not project_name:
        result["details"].append("未指定项目名称")
        result["error"] = "E012"
        return result

    # 构建请求数据
    request_data = {
        "project": project_name,
        "timestamp": result["timestamp"],
    }

    # 准备请求头
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AI-App-Builder-Foundation/1.0",
    }
    if deploy_token:
        headers["Authorization"] = f"Bearer {deploy_token}"

    # 执行部署请求（带重试和超时）
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                deploy_url,
                data=json.dumps(request_data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                result["deployed"] = True
                result["response"] = response_data
                result["details"].append(f"部署成功 (尝试 {attempt + 1}/{max_retries})")
                return result
        except urllib.error.URLError as exc:
            result["details"].append(f"部署尝试 {attempt + 1} 失败: {str(exc)}")
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = 2 ** attempt
                result["details"].append(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        except Exception as exc:
            result["details"].append(f"部署异常: {str(exc)}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                result["details"].append(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    result["error"] = "E012"
    result["details"].append("部署失败，已重试多次")
    return result


# ============================================================
# 文件处理模块（多编码支持）
# ============================================================
def read_text_file(filepath):
    """
    读取文本文件，支持多编码。

    尝试顺序: utf-8 -> gbk -> gb18030 -> latin-1(replace)

    参数:
        filepath: 文件路径

    返回:
        str: 文件内容

    异常:
        E006: 文件读取失败
    """
    if not os.path.isfile(filepath):
        raise IOError(f"文件不存在: {filepath}")

    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error = None

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except OSError as exc:
            raise IOError(f"读取文件失败: {exc}") from exc

    # 最后尝试 replace 模式
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"警告: 使用 replace 模式读取，部分字符可能已替换", file=sys.stderr)
            return content
    except OSError as exc:
        raise IOError(f"读取文件失败: {exc}") from exc


def write_text_file(filepath, content, dry_run=False):
    """
    写入文本文件。

    参数:
        filepath: 文件路径
        content: 内容字符串
        dry_run: 是否仅预览不写入

    返回:
        str: 操作结果描述
    """
    if dry_run:
        # 预览模式：输出 diff
        if os.path.exists(filepath):
            try:
                old_content = read_text_file(filepath)
                diff = list(unified_diff(
                    old_content.splitlines(True),
                    content.splitlines(True),
                    fromfile=f"a/{filepath}",
                    tofile=f"b/{filepath}",
                ))
                if diff:
                    return "预览变更:\n" + "".join(diff)
                return "无变更"
            except IOError:
                return f"预览: 新文件将创建 {filepath}"
        else:
            return f"预览: 新文件将创建 {filepath}"
