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
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.parse
from datetime import datetime, timedelta
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


def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，提取关键信息。
    支持:
      - 纯文本
      - 文件路径 (自动读取)
      - URL (仅解析格式，不访问网络)
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
        except Exception:
            parsed["content"] = raw_input  # 回退为文本处理
    # 检查是否为 URL
    elif raw_input.startswith(("http://", "https://")):
        try:
            url_parts = urllib.parse.urlparse(raw_input)
            if not url_parts.netloc:
                return {"source_type": "invalid_url", "content": "", "metadata": {}}
            parsed["source_type"] = "url"
            parsed["content"] = raw_input
            parsed["metadata"]["domain"] = url_parts.netloc
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
    
    # 日期范围 (当前周)
    today = datetime.now()
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
    if parsed["source_type"] == "invalid_url":
        result.error_code = "E007"
        result.error_message = ERROR_CODES["E007"]
        return result
    
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


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件/网络。
    """
    print("=" * 60)
    print("gitpulse 自检模式 - 验证核心逻辑")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "正常文本输入",
            "input": """
            2024-01-15 完成用户登录模块开发
            2024-01-16 修复支付接口超时问题
            2024-01-17 优化数据库查询性能
            2024-01-18 新增数据导出功能
            2024-01-19 处理客户反馈问题
            """,
            "should_succeed": True
        },
        {
            "name": "空输入",
            "input": "",
            "should_succeed": False
        },
        {
            "name": "短文本输入",
            "input": "hi",
            "should_succeed": False
        },
        {
            "name": "无关键信息文本",
            "input": "这是一个普通的描述性文本，没有具体的工作内容。",
            "should_succeed": True
        },
        {
            "name": "URL输入",
            "input": "https://example.com/project",
            "should_succeed": True
        },
        {
            "name": "无效URL",
            "input": "http://",
            "should_succeed": False
        },
    ]
    
    all_passed = True
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}: {test['name']}")
        result = process_input(test["input"])
        
        # 验证成功/失败状态
        status_ok = (result.success == test["should_succeed"])
        print(f"  期望成功: {test['should_succeed']}, 实际: {result.success}")
        
        # 验证错误码
        if not result.success:
            error_code_ok = result.error_code in ERROR_CODES
            print(f"  错误码: {result.error_code}, 有效: {error_code_ok}")
            if error_code_ok:
                print(f"  错误信息: {result.error_message}")
            status_ok = status_ok and error_code_ok
        
        # 验证成功场景的数据结构
        if result.success:
            data_ok = (
                "标题" in result.data and
                "日期范围" in result.data and
                "关键信息" in result.data and
                "摘要" in result.data and
                "置信度" in result.data and
                "标注" in result.data
            )
            print(f"  数据结构完整: {data_ok}")
            
            # 置信度范围验证（宽松阈值）
            conf_ok = 0 <= result.data["置信度"] <= 100
            print(f"  置信度范围 [0-100]: {conf_ok}, 值: {result.data['置信度']}")
            
            # 关键信息列表验证（允许为空）
            info_ok = isinstance(result.data["关键信息"], list)
            print(f"  关键信息类型: {info_ok}, 数量: {len(result.data['关键信息'])}")
            
            status_ok = status_ok and data_ok and conf_ok and info_ok
        
        # 汇总
        if status_ok:
            print("  ✓ 通过")
        else:
            all_passed = False
            print("  ✗ 失败")
    
    # 测试文件读取功能（使用临时文件）
    print(f"\n测试 {len(test_cases)+1}: 文件输入")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write("2024-01-15 完成项目部署\n2024-01-16 修复bug\n")
        tmp_path = tmp.name
    
    try:
        result = process_input(tmp_path)
        file_ok = result.success and result.data["关键信息"]
        print(f"  文件读取成功: {result.success}")
        print(f"  关键信息提取: {bool(result.data.get('关键信息'))}")
        print(f"  ✓ 通过" if file_ok else "  ✗ 失败")
        all_passed = all_passed and file_ok
    finally:
        os.unlink(tmp_path)
    
    # 测试批量处理
    print(f"\n测试 {len(test_cases)+2}: 批量处理")
    batch_inputs = [
        "2024-01-15 完成A模块",
        "2024-01-16 修复B问题",
        "2024-01-17 优化C功能",
    ]
    batch_results = [process_input(inp) for inp in batch_inputs]
    batch_ok = all(r.success for r in batch_results) and len(batch_results) == 3
    print(f"  批量处理成功: {batch_ok}, 处理数量: {len(batch_results)}")
    print(f"  ✓ 通过" if batch_ok else "  ✗ 失败")
    all_passed = all_passed and batch_ok
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print("自检完成: 全部通过 ✓")
    else:
        print("自检完成: 存在失败项 ✗")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """
    主入口函数。
    返回进程退出码 (0=成功, 1=失败)。
    """
    parser = argparse.ArgumentParser(
        description="gitpulse 周报生成工具 - 将输入内容转换为结构化周报",
        epilog="示例: python main.py --input '2024-01-15 完成登录模块开发'"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容: 文本、文件路径或 URL"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不访问外部资源）"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（JSON格式）"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 正常处理模式
    if not args.input:
        print(f"错误 [E010]: {ERROR_CODES['E010']}", file=sys.stderr)
        print("请使用 --input 提供输入内容，或使用 --selftest 运行自检", file=sys.stderr)
        return 1
    
    # 处理输入
    result = process_input(args.input)
    
    if not result.success:
        print(f"错误 [{result.error_code}]: {result.error_message}", file=sys.stderr)
        return 1
    
    # 输出结果
    if args.json or args.output:
        output_data = {
            "success": True,
            "data": result.data,
            "confidence": result.confidence,
            "annotation": result.annotation
        }
        json_str = json.dumps(output_data, ensure_ascii=False, indent=2)
        
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(json_str)
                print(f"结果已保存到: {args.output}")
            except Exception as e:
                print(f"错误 [E008]: {ERROR_CODES['E008']}: {e}", file=sys.stderr)
                return 1
        else:
            print(json_str)
    else:
        # 人类可读格式输出
        print("\n" + "=" * 60)
        print(f"📋 {result.data['标题']} ({result.data['日期范围']})")
        print("=" * 60)
        print(f"\n📝 摘要: {result.data['摘要']}")
        
        print(f"\n🔑 关键信息 ({len(result.data['关键信息'])} 项):")
        for i, point in enumerate(result.data["关键信息"], 1):
            print(f"  {i}. {point}")
        
        print(f"\n📊 置信度: {result.data['置信度']:.1f}%")
        print(f"🏷️  标注: {result.data['标注']}")
        print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
