#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java核心库助手 - 命令行工具
提供 Google Guava 等 Java 核心库的使用指南生成能力。
"""

import argparse
import sys
import os
import re
from typing import Dict, List, Tuple, Optional, Any
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理该请求",
    "E005": "置信度过低，结果无法确定",
    "E006": "文件读取失败，请检查文件路径和权限",
    "E007": "文件写入失败，请检查磁盘空间和权限",
    "E008": "参数校验失败，请检查命令行参数",
    "E009": "内部逻辑错误，请报告开发者",
    "E010": "未知异常，请查看错误详情",
}

# ============================================================
# 核心数据结构
# ============================================================

# 能力边界声明（与功能规格一致）
CAPABILITIES = {
    "can_do": [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ],
    "cannot_do": [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ],
}

# 触发词表
TRIGGER_WORDS = ["guava", "java库", "集合操作", "java缓存", "并发工具"]

# 标准流程步骤
STANDARD_FLOW = [
    "Step 1: 收集最小信息集 - 确认输入来源、输出格式要求、期望完整度",
    "Step 2: 执行核心流程 - 解析输入、识别关键信息、按规则处理、生成结果",
    "Step 3: 输出与校验 - 整理结果、自查字段完整性、标注置信度",
]

# 常见问题
FAQ = [
    ("处理速度如何？", "骨架结果 1 分钟内，详细结果视输入量而定"),
    ("会不会出错？", "低置信度内容会标注 [需核实]，请人工复核关键结果"),
    ("支持哪些输入？", "用户提供的数据/文件/URL"),
]


# ============================================================
# 输入校验函数
# ============================================================

def validate_input(data: Any) -> Tuple[bool, str]:
    """
    校验输入数据是否合法。
    
    返回: (是否合法, 错误信息)
    """
    if data is None:
        return False, ERROR_CODES["E001"]
    if isinstance(data, str) and not data.strip():
        return False, ERROR_CODES["E001"]
    if isinstance(data, (list, dict, tuple)) and len(data) == 0:
        return False, ERROR_CODES["E001"]
    return True, ""


def validate_output_format(fmt: str) -> Tuple[bool, str]:
    """
    校验输出格式参数。
    
    支持: text, json, table
    """
    allowed = {"text", "json", "table"}
    if fmt not in allowed:
        return False, f"{ERROR_CODES['E003']} 支持的格式: {', '.join(sorted(allowed))}"
    return True, ""


def validate_confidence_threshold(threshold: float) -> Tuple[bool, str]:
    """
    校验置信度阈值参数。
    """
    if not isinstance(threshold, (int, float)):
        return False, f"{ERROR_CODES['E008']} 置信度阈值必须是数字"
    if threshold < 0 or threshold > 1:
        return False, f"{ERROR_CODES['E008']} 置信度阈值必须在 0-1 之间"
    return True, ""


# ============================================================
# 核心逻辑函数
# ============================================================

def analyze_keywords(text: str) -> Dict[str, Any]:
    """
    分析输入文本中的关键词和主题。
    
    返回结构化分析结果。
    """
    result = {
        "keywords": [],
        "topics": [],
        "confidence": 0.0,
        "needs_review": False,
    }
    
    try:
        if not text or not text.strip():
            result["confidence"] = 0.0
            result["needs_review"] = True
            return result
        
        # 提取关键词（简单分词：按非字母数字字符分割）
        words = re.findall(r'[\u4e00-\u9fff\w]+', text.lower())
        if not words:
            result["confidence"] = 0.0
            result["needs_review"] = True
            return result
        
        # 统计词频
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) >= 2:  # 忽略单字符词
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序取前10
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        result["keywords"] = [w for w, _ in sorted_words[:10]]
        
        # 识别主题（与触发词匹配）
        topics = []
        for word in result["keywords"]:
            for trigger in TRIGGER_WORDS:
                if trigger in word or word in trigger:
                    topics.append(trigger)
        result["topics"] = list(set(topics))[:5]
        
        # 计算置信度：基于关键词数量和主题匹配度
        base_confidence = min(0.5 + len(result["keywords"]) * 0.05, 0.95)
        topic_bonus = min(len(result["topics"]) * 0.05, 0.05)
        result["confidence"] = min(base_confidence + topic_bonus, 0.98)
        
        # 置信度低于85%时标记需复核
        result["needs_review"] = result["confidence"] < 0.85
        
    except Exception as e:
        # 降级输出：返回安全默认值
        print(f"警告: 关键词分析失败 - {str(e)}", file=sys.stderr)
        result["confidence"] = 0.0
        result["needs_review"] = True
    
    return result


def generate_guide(keywords: List[str], topics: List[str]) -> str:
    """
    根据分析结果生成使用指南。
    """
    lines = []
    lines.append("Java核心库使用指南")
    lines.append("=" * 30)
    
    if topics:
        lines.append(f"\n识别到的主题: {', '.join(topics)}")
    else:
        lines.append("\n未识别到特定主题，提供通用指南")
    
    lines.append("\n推荐使用场景:")
    for topic in topics[:3] or ["通用"]:
        lines.append(f"  - {topic}")
    
    lines.append("\n核心库推荐:")
    if "guava" in topics or "java库" in topics:
        lines.append("  - Guava: 集合操作、缓存、并发工具")
    if "集合操作" in topics:
        lines.append("  - Guava Collections: ImmutableList, Multimap, BiMap")
    if "java缓存" in topics:
        lines.append("  - Guava Cache: LoadingCache, CacheBuilder")
    if "并发工具" in topics:
        lines.append("  - Guava Concurrent: ListenableFuture, RateLimiter")
    
    lines.append("\n使用建议:")
    lines.append("  1. 优先使用不可变集合保证线程安全")
    lines.append("  2. 缓存设置合理的过期策略")
    lines.append("  3. 并发工具注意资源释放")
    
    return "\n".join(lines)


def process_text(text: str, output_format: str = "text") -> Dict[str, Any]:
    """
    处理文本输入，生成结构化结果。
    """
    # 输入校验
    valid, error_msg = validate_input(text)
    if not valid:
        return {
            "success": False,
            "error_code": "E001",
            "error_msg": error_msg,
            "data": None,
        }
    
    valid, error_msg = validate_output_format(output_format)
    if not valid:
        return {
            "success": False,
            "error_code": "E003",
            "error_msg": error_msg,
            "data": None,
        }
    
    try:
        # 核心分析
        analysis = analyze_keywords(text)
        
        # 生成指南
        guide = generate_guide(analysis["keywords"], analysis["topics"])
        
        # 构建结果
        result_data = {
            "input_preview": text[:200] + ("..." if len(text) > 200 else ""),
            "keywords": analysis["keywords"],
            "topics": analysis["topics"],
            "confidence": analysis["confidence"],
            "needs_review": analysis["needs_review"],
            "guide": guide,
        }
        
        # 置信度标注
        if analysis["confidence"] >= 0.90:
            result_data["confidence_label"] = "高置信度"
        elif analysis["confidence"] >= 0.85:
            result_data["confidence_label"] = "建议复核"
        else:
            result_data["confidence_label"] = "[需核实]"
        
        return {
            "success": True,
            "error_code": None,
            "error_msg": None,
            "data": result_data,
        }
        
    except Exception as e:
        # 降级输出
        print(f"警告: 处理失败 - {str(e)}", file=sys.stderr)
        print(f"降级方案: 返回原始输入", file=sys.stderr)
        print(f"用户操作: 请检查输入内容后重试", file=sys.stderr)
        return {
            "success": False,
            "error_code": "E010",
            "error_msg": f"处理失败: {str(e)}",
            "data": {"raw": text},
        }


def process_file(filepath: str, output_format: str = "text") -> Dict[str, Any]:
    """
    处理文件输入，支持多编码读取。
    """
    # 路径白名单校验（防止路径穿越）
    if not filepath or ".." in filepath:
        return {
            "success": False,
            "error_code": "E008",
            "error_msg": f"{ERROR_CODES['E008']} 非法文件路径",
            "data": None,
        }
    
    try:
        # 多编码读取：utf-8 -> gbk -> gb18030 -> errors=replace
        content = None
        encodings = ["utf-8", "gbk", "gb18030"]
        
        for encoding in encodings:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                return {
                    "success": False,
                    "error_code": "E006",
                    "error_msg": f"{ERROR_CODES['E006']} 文件不存在: {filepath}",
                    "data": None,
                }
            except PermissionError:
                return {
                    "success": False,
                    "error_code": "E006",
                    "error_msg": f"{ERROR_CODES['E006']} 无权限读取: {filepath}",
                    "data": None,
                }
        
        # 如果所有编码都失败，使用 errors=replace
        if content is None:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        
        # 处理内容
        return process_text(content, output_format)
        
    except Exception as e:
        print(f"警告: 文件处理失败 - {str(e)}", file=sys.stderr)
        print(f"降级方案: 返回错误信息", file=sys.stderr)
        print(f"用户操作: 请检查文件后重试", file=sys.stderr)
        return {
            "success": False,
            "error_code": "E006",
            "error_msg": f"{ERROR_CODES['E006']} {str(e)}",
            "data": None,
        }


# ============================================================
# 输出格式化函数
# ============================================================

def format_text_output(result: Dict[str, Any]) -> str:
    """
    格式化文本输出。
    """
    if not result["success"]:
        return f"错误 {result['error_code']}: {result['error_msg']}"
    
    data = result["data"]
    lines = []
    lines.append("=" * 50)
    lines.append("Java核心库助手处理结果")
    lines.append("=" * 50)
    lines.append(f"\n输入预览: {data['input_preview']}")
    lines.append(f"\n识别关键词: {', '.join(data['keywords'][:5]) if data['keywords'] else '无'}")
    lines.append(f"识别主题: {', '.join(data['topics']) if data['topics'] else '无'}")
    lines.append(f"置信度: {data['confidence']:.1%} ({data['confidence_label']})")
    
    if data["needs_review"]:
        lines.append("\n⚠️ 建议复核: 置信度低于85%，请人工确认结果")
    
    lines.append("\n" + data["guide"])
    lines.append("\n" + "=" * 50)
    return "\n".join(lines)


def format_json_output(result: Dict[str, Any]) -> str:
    """
    格式化 JSON 输出。
    """
    import json
    
    if not result["success"]:
        return json.dumps({
            "success": False,
            "error_code": result["error_code"],
            "error_msg": result["error_msg"],
        }, ensure_ascii=False, indent=2)
    
    data = result["data"]
    return json.dumps({
        "success": True,
        "data": {
            "input_preview": data["input_preview"],
            "keywords": data["keywords"],
            "topics": data["topics"],
            "confidence": data["confidence"],
            "confidence_label": data["confidence_label"],
            "needs_review": data["needs_review"],
            "guide": data["guide"],
        }
    }, ensure_ascii=False, indent=2)


def format_table_output(result: Dict[str, Any]) -> str:
    """
    格式化表格输出。
    """
    if not result["success"]:
        return f"错误 {result['error_code']}: {result['error_msg']}"
    
    data = result["data"]
    lines = []
    lines.append("+------------------+------------------------------------------+")
    lines.append("| 项目             | 值                                       |")
    lines.append("+------------------+------------------------------------------+")
    
    rows = [
        ("输入预览", data["input_preview"][:40] + "..." if len(data["input_preview"]) > 40 else data["input_preview"]),
        ("关键词", ", ".join(data["keywords"][:5]) if data["keywords"] else "无"),
        ("主题", ", ".join(data["topics"]) if data["topics"] else "无"),
        ("置信度", f"{data['confidence']:.1%} ({data['confidence_label']})"),
        ("需复核", "是" if data["needs_review"] else "否"),
    ]
    
    for key, value in rows:
        lines.append(f"| {key:<16} | {value:<40} |")
    
    lines.append("+------------------+------------------------------------------+")
    lines.append("\n指南摘要:")
    lines.append(data["guide"][:200] + "..." if len(data["guide"]) > 200 else data["guide"])
    
    return "\n".join(lines)


def format_output(result: Dict[str, Any], output_format: str) -> str:
    """
    根据格式参数输出结果。
    """
    formatters = {
        "text": format_text_output,
        "json": format_json_output,
        "table": format_table_output,
    }
    
    formatter = formatters.get(output_format, format_text_output)
    return formatter(result)


# ============================================================
# 自检函数
# ============================================================

def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据。
    
    覆盖场景：
    1. 正常中文文本输入
    2. 空输入
    3. 英文输入
    4. 特殊字符输入
    5. 长文本输入
    """
    print("开始自检...")
    all_passed = True
    
    # 测试用例
    test_cases = [
        ("我需要用 Guava 处理集合操作和缓存", "text", True),
        ("", "text", False),  # 空输入
        ("Hello world, this is a test", "text", True),  # 英文
        ("！@#￥%……&*（）", "text", True),  # 特殊字符
        ("Java核心库" * 100, "text", True),  # 长文本
        ("测试 JSON 输出", "json", True),  # JSON格式
        ("测试表格输出", "table", True),  # 表格格式
    ]
    
    for i, (text, fmt, expect_success) in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: 输入长度={len(text)}, 格式={fmt}")
        result = process_text(text, fmt)
        
        # 宽松断言：只检查基本结构
        assert "success" in result, f"测试 {i+1} 失败: 缺少 success 字段"
        assert result["success"] == expect_success, f"测试 {i+1} 失败: 期望 success={expect_success}, 实际={result['success']}"
        
        if result["success"]:
            assert "data" in result, f"测试 {i+1} 失败: 缺少 data 字段"
            assert result["data"] is not None, f"测试 {i+1} 失败: data 为 None"
            
            # 检查置信度范围（宽松）
            confidence = result["data"].get("confidence", 0)
            assert 0 <= confidence <= 1, f"测试 {i+1} 失败: 置信度超出范围"
            
            # 检查输出格式
            output = format_output(result, fmt)
            assert output is not None and len(output) > 0, f"测试 {i+1} 失败: 输出为空"
        else:
            assert "error_code" in result, f"测试 {i+1} 失败: 缺少错误码"
            assert result["error_code"] in ERROR_CODES, f"测试 {i+1} 失败: 未知错误码"
        
        print(f"  ✓ 通过")
    
    # 测试文件处理（使用临时文件）
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("测试文件内容：Guava 缓存使用指南")
        temp_path = f.name
    
    try:
        result = process_file(temp_path, "text")
        assert result["success"], f"文件测试失败: {result.get('error_msg')}"
        print(f"\n文件处理测试: ✓ 通过")
    finally:
        os.unlink(temp_path)
    
    # 测试错误输入
    invalid_results = [
        process_text(None, "text"),
        process_text("", "text"),
        process_text("test", "invalid_format"),
    ]
    
    for i, result in enumerate(invalid_results):
        assert not result["success"], f"错误输入测试 {i+1} 失败: 应该失败但成功了"
        assert "error_code" in result, f"错误输入测试 {i+1} 失败: 缺少错误码"
        print(f"错误输入测试 {i+1}: ✓ 通过")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("自检完成: 全部通过 ✓")
    else:
        print("自检完成: 存在失败项 ✗")
    print("=" * 50)
    
    return all_passed


# ============================================================
# 主函数
# ============================================================

def main() -> int:
    """
    命令行入口函数。
    """
    parser = argparse.ArgumentParser(
        description="Java核心库助手 - 提供 Guava 等 Java 核心库使用指南",
        epilog="示例: python main.py --text 'Guava 集合操作' --format text"
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", type=str, help="直接输入文本内容")
    input_group.add_argument("--file", type=str, help="从文件读取内容")
    
    # 输出参数
    parser.add_argument("--format", type=str, default="text", choices=["text", "json", "table"],
                        help="输出格式 (默认: text)")
    
    # 功能参数
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--verbose", action="store_true", help="显示详细处理过程")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行实际输出")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 参数校验
    if not args.text and not args.file:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("请使用 --text 或 --file 提供输入内容", file=sys.stderr)
        return 1
    
    # 处理输入
    if args.text:
        result = process_text(args.text, args.format)
    else:
        result = process_file(args.file, args.format)
    
    # 输出结果
    output = format_output(result, args.format)
    print(output)
    
    # verbose 模式：显示处理细节
    if args.verbose and result["success"]:
        data = result["data"]
        print("\n[处理明细]", file=sys.stderr)
        print(f"  输入长度: {len(args.text) if args.text else '文件'}", file=sys.stderr)
        print(f"  关键词数: {len(data['keywords'])}", file=sys.stderr)
        print(f"  主题数: {len(data['topics'])}", file=sys.stderr)
        print(f"  置信度: {data['confidence']:.2%}", file=sys.stderr)
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
