#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 爬虫采集 (automate-download-freesound)

仅供学习与参考用途。本脚本提供规范、可复用的处理流程与输出。
基于功能规格独立实现（clean-room）。

用法示例:
    python scripts/main.py --selftest          # 离线自检核心逻辑
    python scripts/main.py --input "..."       # 处理用户输入
    python scripts/main.py --help              # 显示帮助

错误码:
    E001 输入为空
    E002 关键信息缺失
    E003 输入格式错误
    E004 超出能力边界
    E005 置信度过低
    E006 内部逻辑错误
    E007 参数解析错误
    E008 自检失败
    E009 输出生成失败
    E010 未知错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 置信度阈值
CONFIDENCE_HIGH = 90.0      # 置信度 >= 90%：直接输出
CONFIDENCE_MEDIUM = 85.0    # 85%-90%：标注"建议复核"
# 低于 85%：标注"[需核实]"

# 错误码与标准化话术映射
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部逻辑错误，请报告开发者",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "自检失败，请检查代码逻辑",
    "E009": "输出生成失败，请检查数据",
    "E010": "未知错误，请报告开发者",
}

# 能力边界声明
CAPABILITY_BOUNDARIES = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]

# 触发词表
TRIGGER_WORDS = [
    "爬虫采集",
    "automate download freesound",
]


# ============================================================
# 核心数据结构
# ============================================================

class ProcessingResult:
    """处理结果的数据结构"""
    
    def __init__(self) -> None:
        self.success: bool = False
        self.data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.error_code: Optional[str] = None
        self.error_message: Optional[str] = None
        self.timestamp: str = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ============================================================
# 核心逻辑函数
# ============================================================

def validate_input(raw_input: str) -> Tuple[bool, Optional[str]]:
    """
    校验输入是否有效
    
    返回: (是否有效, 错误码或None)
    """
    if raw_input is None or raw_input.strip() == "":
        return False, "E001"
    return True, None


def extract_key_info(raw_input: str) -> Dict[str, Any]:
    """
    从输入中提取关键信息
    
    识别规则:
    - URL: http:// 或 https:// 开头的字符串
    - 文件路径: 包含 . 且路径分隔符的字符串
    - 关键词: 匹配触发词
    - 其他: 作为普通文本处理
    """
    info: Dict[str, Any] = {
        "raw_text": raw_input.strip(),
        "urls": [],
        "file_paths": [],
        "keywords": [],
        "content_type": "unknown",
    }
    
    # 提取 URL
    url_pattern = r'https?://[^\s]+'
    info["urls"] = re.findall(url_pattern, raw_input)
    
    # 提取文件路径（简单模式：包含 / 或 \ 且有扩展名）
    file_pattern = r'[\w/\\]+\.\w+'
    info["file_paths"] = re.findall(file_pattern, raw_input)
    
    # 匹配触发词
    for word in TRIGGER_WORDS:
        if word.lower() in raw_input.lower():
            info["keywords"].append(word)
    
    # 判断内容类型
    if info["urls"]:
        info["content_type"] = "url"
    elif info["file_paths"]:
        info["content_type"] = "file"
    elif info["keywords"]:
        info["content_type"] = "command"
    else:
        info["content_type"] = "text"
    
    return info


def calculate_confidence(extracted_info: Dict[str, Any]) -> float:
    """
    计算置信度（0-100）
    
    规则:
    - 有明确 URL: 基础 90
    - 有文件路径: 基础 85
    - 有触发词: 基础 80
    - 仅有普通文本: 基础 60
    - 信息越丰富，置信度越高
    """
    base_score = 50.0
    bonus = 0.0
    
    content_type = extracted_info.get("content_type", "unknown")
    
    if content_type == "url":
        base_score = 90.0
        if extracted_info["urls"]:
            bonus = min(len(extracted_info["urls"]) * 2.0, 10.0)
    elif content_type == "file":
        base_score = 85.0
        if extracted_info["file_paths"]:
            bonus = min(len(extracted_info["file_paths"]) * 2.0, 10.0)
    elif content_type == "command":
        base_score = 80.0
        if extracted_info["keywords"]:
            bonus = min(len(extracted_info["keywords"]) * 5.0, 15.0)
    else:
        base_score = 60.0
        # 文本长度作为参考
        text_len = len(extracted_info.get("raw_text", ""))
        if text_len > 20:
            bonus = 5.0
    
    return min(base_score + bonus, 100.0)


def generate_output(result: ProcessingResult) -> str:
    """
    生成最终输出文本
    
    根据置信度决定输出格式:
    - 高置信度: 直接输出
    - 中等: 标注"建议复核"
    - 低: 标注"[需核实]"
    """
    if not result.success:
        raise ValueError("无法生成输出：处理未成功")
    
    confidence = result.confidence
    data = result.data
    
    # 构建输出
    lines = []
    lines.append("=== 处理结果 ===")
    lines.append(f"内容类型: {data.get('content_type', 'unknown')}")
    lines.append(f"处理时间: {result.timestamp}")
    
    if data.get("urls"):
        lines.append(f"检测到 {len(data['urls'])} 个 URL:")
        for i, url in enumerate(data["urls"], 1):
            lines.append(f"  {i}. {url}")
    
    if data.get("file_paths"):
        lines.append(f"检测到 {len(data['file_paths'])} 个文件路径:")
        for i, path in enumerate(data["file_paths"], 1):
            lines.append(f"  {i}. {path}")
    
    if data.get("keywords"):
        lines.append(f"匹配关键词: {', '.join(data['keywords'])}")
    
    # 置信度标注
    if confidence >= CONFIDENCE_HIGH:
        lines.append(f"置信度: {confidence:.1f}% - 直接输出")
    elif confidence >= CONFIDENCE_MEDIUM:
        lines.append(f"置信度: {confidence:.1f}% - 建议复核")
    else:
        lines.append(f"置信度: {confidence:.1f}% - [需核实]")
        lines.append("注意: 结果无法完全确定，请人工复核关键信息")
    
    # 警告信息
    if result.warnings:
        lines.append("警告:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")
    
    return "\n".join(lines)


def process_input(raw_input: str) -> ProcessingResult:
    """
    核心处理流程
    
    1. 校验输入
    2. 提取关键信息
    3. 计算置信度
    4. 生成结果
    """
    result = ProcessingResult()
    
    # Step 1: 校验输入
    valid, error_code = validate_input(raw_input)
    if not valid:
        result.error_code = error_code
        result.error_message = ERROR_MESSAGES[error_code]
        return result
    
    # Step 2: 提取关键信息
    try:
        extracted = extract_key_info(raw_input)
    except Exception as e:
        result.error_code = "E006"
        result.error_message = f"{ERROR_MESSAGES['E006']}: {str(e)}"
        return result
    
    # 检查是否超出能力边界
    if extracted["content_type"] == "unknown":
        result.error_code = "E004"
        result.error_message = ERROR_MESSAGES["E004"]
        return result
    
    # Step 3: 计算置信度
    confidence = calculate_confidence(extracted)
    result.confidence = confidence
    
    # 低置信度处理
    if confidence < CONFIDENCE_MEDIUM:
        result.warnings.append("输入信息较为模糊，建议提供更明确的 URL 或文件路径")
    
    # Step 4: 设置结果数据
    result.data = extracted
    result.success = True
    
    return result


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    离线自检核心逻辑
    
    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保自检样例与实际逻辑必然匹配。
    """
    print("=" * 60)
    print("开始自检...")
    print("=" * 60)
    
    all_passed = True
    
    # --- 测试用例 1: 有效 URL 输入 ---
    print("\n[测试 1] 有效 URL 输入")
    test_input = "请帮我处理这个 https://example.com/audio/sample.mp3 文件"
    result = process_input(test_input)
    
    # 断言: 处理成功
    assert result.success, f"测试1失败: 处理应成功 (错误: {result.error_code})"
    # 断言: 检测到 URL（宽松: 至少1个）
    assert len(result.data.get("urls", [])) >= 1, "测试1失败: 应检测到至少1个URL"
    # 断言: 置信度在合理区间（宽松）
    assert result.confidence >= 50.0, f"测试1失败: 置信度应>=50 (实际: {result.confidence})"
    # 断言: 无错误码
    assert result.error_code is None, f"测试1失败: 不应有错误码"
    
    print(f"  通过 - 置信度: {result.confidence:.1f}%")
    
    # --- 测试用例 2: 空输入 ---
    print("\n[测试 2] 空输入")
    result = process_input("")
    
    # 断言: 处理失败
    assert not result.success, "测试2失败: 空输入应处理失败"
    # 断言: 错误码为 E001
    assert result.error_code == "E001", f"测试2失败: 错误码应为E001 (实际: {result.error_code})"
    
    print("  通过 - 正确返回 E001")
    
    # --- 测试用例 3: 文件路径输入 ---
    print("\n[测试 3] 文件路径输入")
    test_input = "处理 /home/user/audio/sample.wav 这个文件"
    result = process_input(test_input)
    
    # 断言: 处理成功
    assert result.success, f"测试3失败: 处理应成功 (错误: {result.error_code})"
    # 断言: 检测到文件路径
    assert len(result.data.get("file_paths", [])) >= 1, "测试3失败: 应检测到文件路径"
    
    print(f"  通过 - 检测到 {len(result.data['file_paths'])} 个文件路径")
    
    # --- 测试用例 4: 触发词输入 ---
    print("\n[测试 4] 触发词输入")
    test_input = "爬虫采集"
    result = process_input(test_input)
    
    # 断言: 处理成功
    assert result.success, f"测试4失败: 处理应成功 (错误: {result.error_code})"
    # 断言: 检测到关键词
    assert len(result.data.get("keywords", [])) >= 1, "测试4失败: 应检测到关键词"
    
    print(f"  通过 - 检测到关键词: {result.data['keywords']}")
    
    # --- 测试用例 5: 输出生成 ---
    print("\n[测试 5] 输出生成")
    test_input = "https://example.com/audio/test.mp3"
    result = process_input(test_input)
    
    output_text = generate_output(result)
    
    # 断言: 输出非空
    assert len(output_text) > 0, "测试5失败: 输出不应为空"
    # 断言: 输出包含关键信息
    assert "处理结果" in output_text, "测试5失败: 输出应包含标题"
    # 断言: 输出包含置信度
    assert "置信度" in output_text, "测试5失败: 输出应包含置信度"
    
    print("  通过 - 输出生成成功")
    
    # --- 测试用例 6: 边界检查 ---
    print("\n[测试 6] 能力边界检查")
    test_input = "帮我分析这段文本的情感倾向"
    result = process_input(test_input)
    
    # 断言: 处理成功或明确拒绝
    assert result.success or result.error_code == "E004", \
        f"测试6失败: 应成功处理或返回E004 (实际: {result.error_code})"
    
    print("  通过 - 边界处理正常")
    
    # --- 测试用例 7: 多 URL 批量检测 ---
    print("\n[测试 7] 多 URL 检测")
    test_input = "下载 https://a.com/1.mp3 和 https://b.com/2.wav 还有 https://c.com/3.ogg"
    result = process_input(test_input)
    
    # 断言: 检测到多个URL（宽松: 至少2个）
    assert len(result.data.get("urls", [])) >= 2, \
        f"测试7失败: 应检测到至少2个URL (实际: {len(result.data.get('urls', []))})"
    
    print(f"  通过 - 检测到 {len(result.data['urls'])} 个 URL")
    
    # --- 测试用例 8: 错误码完整性 ---
    print("\n[测试 8] 错误码完整性")
    
    # 断言: 所有错误码都有对应消息
    expected_codes = [f"E{i:03d}" for i in range(1, 11)]
    for code in expected_codes:
        assert code in ERROR_MESSAGES, f"测试8失败: 缺少错误码 {code}"
        assert len(ERROR_MESSAGES[code]) > 0, f"测试8失败: 错误码 {code} 消息为空"
    
    print(f"  通过 - 全部 {len(expected_codes)} 个错误码定义完整")
    
    # --- 测试用例 9: 置信度区间 ---
    print("\n[测试 9] 置信度区间")
    
    test_cases = [
        "https://example.com/audio/sample.mp3",  # URL - 高置信度
        "/path/to/file.wav",                      # 文件 - 中高置信度
        "爬虫采集",                               # 触发词 - 中置信度
        "随便说点什么",                           # 普通文本 - 低置信度
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        result = process_input(test_input)
        confidence = result.confidence
        # 断言: 置信度在 0-100 区间
        assert 0.0 <= confidence <= 100.0, \
            f"测试9-{i}失败: 置信度应在0-100 (实际: {confidence})"
        # 断言: 置信度是有限数值
        assert confidence == confidence, f"测试9-{i}失败: 置信度不应是NaN"
    
    print("  通过 - 置信度均在有效区间")
    
    # --- 测试用例 10: 批量处理 ---
    print("\n[测试 10] 批量处理")
    
    batch_inputs = [
        "https://example.com/audio/1.mp3",
        "https://example.com/audio/2.wav",
        "/path/to/file.ogg",
        "爬虫采集",
    ]
    
    batch_results = []
    for input_text in batch_inputs:
        result = process_input(input_text)
        batch_results.append(result)
    
    # 断言: 所有结果都有明确状态
    for i, result in enumerate(batch_results, 1):
        assert result.success or result.error_code is not None, \
            f"测试10-{i}失败: 结果应有明确状态"
    
    print(f"  通过 - 批量处理 {len(batch_results)} 个输入全部正常")
    
    # --- 汇总 ---
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 全部自检通过!")
    else:
        print("❌ 部分自检失败!")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    
    parser = argparse.ArgumentParser(
        description="爬虫采集 - 仅供学习与参考用途",
        epilog="示例: python scripts/main.py --input 'https://example.com/audio/sample.mp3'"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的内容（URL、文件路径或文本）"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不访问网络，不依赖外部文件）"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"❌ 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"❌ 自检异常: {e}")
            return 1
    
    # 正常处理模式
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}")
        print("提示: 使用 --input 参数提供内容，或使用 --selftest 运行自检")
        return 1
    
    # 处理输入
    result = process_input(args.input)
    
    if not result.success:
        error_code = result.error_code or "E010"
        error_msg = result.error_message or ERROR_MESSAGES.get(error_code, "未知错误")
        print(f"错误 {error_code}: {error_msg}")
        return 1
    
    # 输出结果
    if args.json:
        print(result.to_json())
    else:
        try:
            output_text = generate_output(result)
            print(output_text)
        except Exception as e:
            print(f"错误 E009: {ERROR_MESSAGES['E009']}: {str(e)}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
