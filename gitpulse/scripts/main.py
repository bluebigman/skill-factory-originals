#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gitpulse 周报生成技能 - 独立实现
=================================
仅依据功能规格进行 clean-room 重写。

功能概述:
    将用户提供的文本数据/文件内容/URL 文本转换为结构化周报结果。
    支持置信度标注、错误码体系、标准流程输出。

用法:
    python scripts/main.py --selftest   # 离线自检
    python scripts/main.py --input "..."  # 处理输入文本
    python scripts/main.py --input "..." --format json  # JSON 输出
    python scripts/main.py --file "path/to/file.txt"  # 处理文件
    python scripts/main.py --url "https://example.com"  # 处理 URL
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import timezone, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望完整度",
    "E003": "输入格式不符合要求，示例：请提供有效的文本内容或文件路径",
    "E004": "这超出了本工具的能力范围，建议：明确输入范围或使用专业工具",
    "E005": "结果无法确定，建议：补充更多上下文信息或人工复核",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "URL 格式无效，请提供完整的 http(s) 链接",
    "E008": "输出目录不可写，请检查权限",
    "E009": "内部处理异常，请重试或检查输入内容",
    "E010": "参数错误，请检查命令行参数",
    "E011": "URL 内容获取失败，请检查网络连接或 URL 有效性",
}

# 置信度阈值
HIGH_CONFIDENCE = 90.0
MEDIUM_CONFIDENCE = 85.0

# 默认模板字段
DEFAULT_TEMPLATE = {
    "标题": "周报",
    "日期范围": "",
    "关键信息": [],
    "摘要": "",
    "置信度": 0.0,
    "标注": ""
}

# URL 请求配置
URL_TIMEOUT = 10  # 秒
URL_MAX_RETRIES = 3
URL_RETRY_BACKOFF = 1.0  # 秒


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果数据类"""
    def __init__(self):
        self.success: bool = False
        self.error_code: Optional[str] = None
        self.error_message: str = ""
        self.data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.annotation: str = ""


# ============================================================
# 核心处理逻辑
# ============================================================
def validate_input(raw_input: str) -> Tuple[bool, str]:
    """
    校验输入内容有效性。
    返回 (是否有效, 错误信息)
    """
    if not raw_input or not raw_input.strip():
        return False, ERROR_CODES["E001"]
    if len(raw_input.strip()) < 3:
        return False, ERROR_CODES["E003"]
    return True, ""


def fetch_url_content(url: str) -> Tuple[bool, str]:
    """
    获取 URL 内容，带超时和指数退避重试机制。
    返回 (是否成功, 内容或错误信息)
    """
    for attempt in range(URL_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "gitpulse/1.0"})
            with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as response:
                if response.status != 200:
                    return False, f"HTTP 状态码: {response.status}"
                content = response.read().decode("utf-8", errors="replace")
                return True, content
        except urllib.error.URLError as e:
            if attempt < URL_MAX_RETRIES - 1:
                # 指数退避：每次重试等待时间翻倍
                backoff_time = URL_RETRY_BACKOFF * (2 ** attempt)
                time.sleep(backoff_time)
            else:
                return False, f"URL 请求失败: {str(e)}"
        except Exception as e:
            if attempt < URL_MAX_RETRIES - 1:
                # 指数退避：每次重试等待时间翻倍
                backoff_time = URL_RETRY_BACKOFF * (2 ** attempt)
                time.sleep(backoff_time)
            else:
                return False, f"URL 请求异常: {str(e)}"
    return False, "重试次数耗尽"


def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，提取关键信息。
    支持:
      - 纯文本
      - 文件路径 (自动读取，带异常捕获)
      - URL (真实获取内容，带超时和重试)
    """
    parsed = {
        "source_type": "text",
        "content": "",
        "metadata": {}
    }

    # 检查是否为文件路径
    if os.path.isfile(raw_input):
        try:
            with open(raw_input, "r", encoding="utf-8") as f:
                parsed["content"] = f.read()
            parsed["source_type"] = "file"
            parsed["metadata"]["filename"] = os.path.basename(raw_input)
        except (IOError, OSError) as e:
            # 文件读取失败，返回错误信息
            parsed["source_type"] = "file_error"
            parsed["metadata"]["error"] = str(e)
            return parsed
        except Exception:
            parsed["source_type"] = "file_error"
            parsed["metadata"]["error"] = "未知文件读取错误"
            return parsed
    # 检查是否为 URL
    elif raw_input.startswith(("http://", "https://")):
        try:
            url_parts = urllib.parse.urlparse(raw_input)
            if not url_parts.netloc:
                return {"source_type": "invalid_url", "content": "", "metadata": {}}
            parsed["source_type"] = "url"
            parsed["metadata"]["domain"] = url_parts.netloc
            # 真实获取 URL 内容
            success, content = fetch_url_content(raw_input)
            if success:
                parsed["content"] = content
                parsed["metadata"]["fetched"] = True
            else:
                parsed["source_type"] = "url_error"
                parsed["metadata"]["error"] = content
                return parsed
        except Exception:
            parsed["source_type"] = "invalid_url"
            parsed["content"] = ""
    else:
        # 纯文本
        parsed["content"] = raw_input.strip()

    return parsed


def extract_key_info(content: str) -> List[str]:
    """
    从文本内容中提取关键信息。
    识别模式: 日期、数字、关键词、项目名等。
    """
    key_points = []
    
    # 按行拆分，过滤空行
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    
    for line in lines:
        # 跳过过长或过短的行
        if len(line) < 5 or len(line) > 200:
            continue
        
        # 识别日期模式 (如 2024-01-01 或 01/01)
        has_date = any(
            marker in line 
            for marker in ["-", "/", "年", "月", "日"]
        )
        
        # 识别数字模式
        has_number = any(char.isdigit() for char in line)
        
        # 识别常见关键词
        keywords = ["完成", "修复", "优化", "新增", "更新", "处理", "解决", "开发", "测试"]
        has_keyword = any(kw in line for kw in keywords)
        
        # 综合判断是否为关键信息
        if has_date or (has_number and has_keyword):
            key_points.append(line)
    
    # 去重并限制数量
    unique_points = list(dict.fromkeys(key_points))[:20]
    return unique_points


def calculate_confidence(key_points: List[str], source_type: str) -> float:
    """
    计算置信度。
    - 文本内容充足且关键信息多: 高置信度
    - 信息不足: 低置信度
    """
    base_score = 50.0
    
    # 根据关键信息数量加分
    info_score = min(len(key_points) * 5, 30)
    
    # 根据来源类型加分
    source_score = {"text": 10, "file": 15, "url": 5}.get(source_type, 5)
    
    # 内容长度加分
    content_length = sum(len(point) for point in key_points)
    length_score = min(content_length / 100, 10)
    
    confidence = base_score + info_score + source_score + length_score
    return min(confidence, 100.0)


def generate_report(parsed_input: Dict[str, Any], key_points: List[str], confidence: float) -> Dict[str, Any]:
    """
    按默认模板生成结构化报告。
    """
    report = dict(DEFAULT_TEMPLATE)
    
    # 日期范围 (当前周，使用 UTC 时间)
    today = datetime.now(timezone.utc)
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    report["日期范围"] = f"{monday.strftime('%Y-%m-%d')} 至 {friday.strftime('%Y-%m-%d')}"
    
    # 关键信息
    report["关键信息"] = key_points
    
    # 摘要
    if key_points:
        report["摘要"] = f"本周共完成 {len(key_points)} 项工作，主要涉及: " + "；".join(key_points[:3])
    else:
        report["摘要"] = "本周暂无关键工作记录"
    
    # 置信度与标注
    report["置信度"] = round(confidence, 1)
    if confidence >= HIGH_CONFIDENCE:
        report["标注"] = "直接输出"
    elif confidence >= MEDIUM_CONFIDENCE:
        report["标注"] = "建议复核"
    else:
        report["标注"] = "[需核实] 信息不足，请补充更多内容"
    
    return report


def process_input(raw_input: str) -> ProcessingResult:
    """
    标准处理流程:
    1. 校验输入
    2. 解析输入
    3. 提取关键信息
    4. 计算置信度
    5. 生成报告
    """
    result = ProcessingResult()
    
    # Step 1: 校验输入
    valid, error_msg = validate_input(raw_input)
    if not valid:
        # 根据错误信息确定错误码
        if "E001" in error_msg:
            result.error_code = "E001"
        else:
            result.error_code = "E003"
        result.error_message = error_msg
        return result
    
    # Step 2: 解析输入
    parsed = parse_input(raw_input)
    
    # 处理文件读取错误
    if parsed["source_type"] == "file_error":
        result.error_code = "E006"
        result.error_message = f"{ERROR_CODES['E006']}: {parsed['metadata'].get('error', '')}"
        return result
    
    # 处理 URL 错误
    if parsed["source_type"] == "url_error":
        result.error_code = "E011"
        result.error_message = f"{ERROR_CODES['E011']}: {parsed['metadata'].get('error', '')}"
        return result
    
    # 处理无效 URL
    if parsed["source_type"] == "invalid_url":
        result.error_code = "E007"
        result.error_message = ERROR_CODES["E007"]
        return result
    
    # 处理空内容
    if not parsed["content"]:
        result.error_code = "E001"
        result.error_message = ERROR_CODES["E001"]
        return result
    
    # Step 3: 提取关键信息
    key_points = extract_key_info(parsed["content"])
    
    # Step 4: 计算置信度
    confidence = calculate_confidence(key_points, parsed["source_type"])
    
    # Step 5: 生成报告
    report = generate_report(parsed, key_points, confidence)
    
    result.success = True
    result.data = report
    result.confidence = confidence
    result.annotation = report["标注"]
    
    return result


def format_output(result: ProcessingResult, format_type: str) -> str:
    """
    根据指定格式输出结果。
    """
    if format_type == "json":
        output_data = {
            "success": result.success,
            "data": result.data,
            "confidence": result.confidence,
            "annotation": result.annotation
        }
        return json.dumps(output_data, ensure_ascii=False, indent=2)
    else:
        # 默认人类可读格式
        lines = []
        lines.append("=" * 60)
        lines.append(f"📋 {result.data['标题']} ({result.data['日期范围']})")
        lines.append("=" * 60)
        lines.append(f"\n📝 摘要: {result.data['摘要']}")
        lines.append(f"\n🔑 关键信息 ({len(result.data['关键信息'])} 项):")
        for i, point in enumerate(result.data["关键信息"], 1):
            lines.append(f"  {i}. {point}")
        lines.append(f"\n📊 置信度: {result.data['置信度']:.1f}%")
        lines.append(f"🏷️  标注: {result.data['标注']}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    真实调用主流程/核心函数并断言关键输出。
    """
    print("=" * 60)
    print("gitpulse 自检模式 - 验证核心逻辑")
    print("=" * 60)
    
    all_passed = True
    
    # 测试 1: 正常文本输入
    print("\n测试 1: 正常文本输入")
    test_input = """
    2024-01-15 完成用户登录模块开发
    2024-01-16 修复支付接口超时问题
    2024-01-17 优化数据库查询性能
    """
    result = process_input(test_input)
    assert result.success, "正常文本输入应成功"
    assert result.data["关键信息"], "应提取到关键信息"
    assert 0 <= result.data["置信度"] <= 100, "置信度应在 0-100 范围"
    assert result.data["标注"] in ["直接输出", "建议复核", "[需核实] 信息不足，请补充更多内容"], "标注应有效"
    print("  ✓ 通过")
    
    # 测试 2: 空输入
    print("\n测试 2: 空输入")
    result = process_input("")
    assert not result.success, "空输入应失败"
    assert result.error_code == "E001", "错误码应为 E001"
    print(f"  ✓ 通过 (错误码: {result.error_code})")
    
    # 测试 3: 短文本输入
    print("\n测试 3: 短文本输入")
    result = process_input("hi")
    assert not result.success, "短文本应失败"
    assert result.error_code == "E003", "错误码应为 E003"
    print(f"  ✓ 通过 (错误码: {result.error_code})")
    
    # 测试 4: 文件读取（正常）
    print("\n测试 4: 文件读取（正常）")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write("2024-01-15 完成项目部署\n2024-01-16 修复bug\n")
        tmp_path = tmp.name
    try:
        result = process_input(tmp_path)
        assert result.success, "文件读取应成功"
        assert result.data["关键信息"], "应提取到关键信息"
        print("  ✓ 通过")
    finally:
        os.unlink(tmp_path)
    
    # 测试 5: 文件读取（不存在）
    print("\n测试 5: 文件读取（不存在）")
    result = process_input("/nonexistent/path/file.txt")
    assert not result.success, "不存在的文件应失败"
    assert result.error_code == "E006", "错误码应为 E006"
    print(f"  ✓ 通过 (错误码: {result.error_code})")
    
    # 测试 6: 无效 URL
    print("\n测试 6: 无效 URL")
    result = process_input("http://")
    assert not result.success, "无效 URL 应失败"
    assert result.error_code == "E007", "错误码应为 E007"
    print(f"  ✓ 通过 (错误码: {result.error_code})")
    
    # 测试 7: 无关键信息文本
    print("\n测试 7: 无关键信息文本")
    result = process_input("这是一个普通的描述性文本，没有具体的工作内容。")
    assert result.success, "无关键信息文本应成功"
    assert isinstance(result.data["关键信息"], list), "关键信息应为列表"
    print("  ✓ 通过")
    
    # 测试 8: JSON 格式输出
    print("\n测试 8: JSON 格式输出")
    result = process_input("2024-01-15 完成登录模块开发")
    json_output = format_output(result, "json")
    parsed_json = json.loads(json_output)
    assert parsed_json["success"] == True, "JSON 输出应包含 success 字段"
    assert "data" in parsed_json, "JSON 输出应包含 data 字段"
    print("  ✓ 通过")
    
    # 测试 9: 批量处理
    print("\n测试 9: 批量处理")
