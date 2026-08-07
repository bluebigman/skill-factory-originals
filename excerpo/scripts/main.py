#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
excerpo - 爬虫采集 技能实现（clean-room 重写）
===============================================
依据功能规格独立实现，不复制任何既有代码。

功能边界：
- 将输入内容（文本/文件路径/URL 字符串）解析为结构化结果
- 识别关键字段、按模板组织输出、标注置信度
- 支持批量处理、自定义字段
- 不访问网络、不执行超出输入范围的分析

错误码：
E001 输入为空
E002 关键信息缺失
E003 输入格式错误
E004 超出能力边界
E005 置信度过低
E006 文件读取失败
E007 输出写入失败
E008 未知字段类型
E009 批量处理中断
E010 内部逻辑错误
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
VERSION = "1.0.0"
SLUG = "excerpo"
DISPLAY_NAME = "爬虫采集"

# 默认输出模板（字段 -> 提取规则关键词）
DEFAULT_TEMPLATE: Dict[str, List[str]] = {
    "title": ["标题", "书名", "名称", "title"],
    "author": ["作者", "author"],
    "content": ["正文", "内容", "content"],
    "url": ["网址", "链接", "url", "http"],
    "date": ["日期", "时间", "date"],
}

# 置信度阈值
CONFIDENCE_HIGH = 90
CONFIDENCE_MEDIUM = 85

# 错误码 -> 标准话术
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：",
    "E003": "输入格式不符合要求，示例：{\"title\": \"...\", \"content\": \"...\"}",
    "E004": "这超出了本工具的能力范围，建议：简化输入或拆分处理",
    "E005": "结果无法确定，建议：补充更多上下文信息",
    "E006": "文件读取失败，请检查路径和权限",
    "E007": "输出写入失败，请检查目标路径",
    "E008": "未知字段类型，无法处理",
    "E009": "批量处理中断，已处理部分结果",
    "E010": "内部逻辑错误，请报告此问题",
}

# 能力边界说明
BOUNDARY_NOTES = {
    "url": "URL 已记录，未访问网络（遵循能力边界）",
    "file": "文件已读取，仅处理本地内容",
    "text": "文本已解析，未执行外部操作",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果封装"""

    def __init__(
        self,
        data: Dict[str, Any],
        confidence: int,
        warnings: Optional[List[str]] = None,
        boundary_note: Optional[str] = None,
    ) -> None:
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.boundary_note = boundary_note

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        result = {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "timestamp": datetime.now().isoformat(),
        }
        if self.boundary_note:
            result["boundary_note"] = self.boundary_note
        return result

    def to_json(self) -> str:
        """转为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 输入解析模块
# ---------------------------------------------------------------------------
def parse_input(raw_input: Any) -> Tuple[str, Dict[str, Any]]:
    """
    解析输入内容，返回 (输入类型, 解析后的内容)
    输入类型: "text", "json", "file", "url"
    """
    if raw_input is None:
        raise ValueError("E001")

    # 处理输入为字符串
    if isinstance(raw_input, str):
        text = raw_input.strip()
        if not text:
            raise ValueError("E001")

        # 尝试解析 JSON
        if text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
                return "json", data
            except json.JSONDecodeError:
                pass

        # 检查是否为文件路径
        if len(text) < 500 and os.path.isfile(text):
            return "file", {"path": text}

        # 检查是否为 URL（仅识别，不访问）
        if re.match(r"^https?://", text, re.IGNORECASE):
            return "url", {"url": text}

        # 默认作为普通文本
        return "text", {"text": text}

    # 处理输入为字典
    if isinstance(raw_input, dict):
        if not raw_input:
            raise ValueError("E001")
        return "json", raw_input

    # 处理输入为列表
    if isinstance(raw_input, list):
        if not raw_input:
            raise ValueError("E001")
        return "json", raw_input

    # 其他类型不支持
    raise ValueError("E003")


def read_file_content(file_path: str) -> str:
    """读取文件内容"""
    try:
        path = Path(file_path)
        if not path.is_file():
            raise ValueError("E006")
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError) as exc:
        raise ValueError("E006") from exc


# ---------------------------------------------------------------------------
# 信息提取模块
# ---------------------------------------------------------------------------
def extract_fields(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    从数据中提取关键字段
    返回 (提取结果, 缺失字段列表)
    """
    result: Dict[str, Any] = {}
    missing: List[str] = []

    # 如果数据本身就是扁平结构，直接处理
    if isinstance(data, dict):
        for field, keywords in DEFAULT_TEMPLATE.items():
            value = _find_field_value(data, keywords)
            if value is not None:
                result[field] = value
            else:
                missing.append(field)

    # 如果数据是嵌套结构，尝试递归提取
    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            # 合并所有条目的字段
            merged: Dict[str, Any] = {}
            for item in data:
                if isinstance(item, dict):
                    merged.update(item)
            return extract_fields(merged)
        else:
            result["content"] = data
            missing = [f for f in DEFAULT_TEMPLATE if f != "content"]

    return result, missing


def _find_field_value(data: Dict[str, Any], keywords: List[str]) -> Any:
    """在字典中查找关键词对应的值"""
    # 先尝试精确键名匹配
    for key, value in data.items():
        if any(kw.lower() in str(key).lower() for kw in keywords):
            return value

    # 再尝试值内容匹配
    for value in data.values():
        if isinstance(value, str):
            if any(kw.lower() in value[:50].lower() for kw in keywords):
                return value

    # 递归查找嵌套字典
    for value in data.values():
        if isinstance(value, dict):
            found = _find_field_value(value, keywords)
            if found is not None:
                return found

    return None


# ---------------------------------------------------------------------------
# 置信度计算模块
# ---------------------------------------------------------------------------
def calculate_confidence(
    extracted: Dict[str, Any], missing: List[str]
) -> Tuple[int, List[str]]:
    """
    计算置信度
    规则：
    - 基础 60 分
    - 每个非空字段 +8 分（最多 5 个字段）
    - 关键字段（title, content）缺失时降 10 分
    - 上限 98 分
    """
    warnings: List[str] = []
    score = 60

    # 字段完整度加分
    field_count = len(extracted)
    score += min(field_count * 8, 30)

    # 关键字段检查
    if "title" not in extracted:
        score -= 10
        warnings.append("缺少标题字段")
    if "content" not in extracted:
        score -= 10
        warnings.append("缺少正文内容")

    # 内容长度检查（宽松）
    content = extracted.get("content", "")
    if isinstance(content, str) and len(content) < 20:
        score -= 5
        warnings.append("内容过短，可能不完整")

    # 限制范围
    score = max(0, min(score, 98))

    return score, warnings


def format_confidence(confidence: int) -> str:
    """格式化置信度提示"""
    if confidence >= CONFIDENCE_HIGH:
        return "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        return "建议复核"
    else:
        return "[需核实]"


# ---------------------------------------------------------------------------
# 输出格式化模块
# ---------------------------------------------------------------------------
def format_output(result: ProcessingResult, output_format: str = "json") -> str:
    """格式化输出结果"""
    if output_format == "json":
        return result.to_json()
    elif output_format == "text":
        lines = []
        lines.append(f"=== 处理结果（置信度: {result.confidence}%）===")
        lines.append(f"状态: {format_confidence(result.confidence)}")

        if result.boundary_note:
            lines.append(f"\n边界说明: {result.boundary_note}")

        if result.warnings:
            lines.append("\n警告:")
            for w in result.warnings:
                lines.append(f"  - {w}")

        lines.append("\n提取字段:")
        for key, value in result.data.items():
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            lines.append(f"  {key}: {value}")

        return "\n".join(lines)
    else:
        raise ValueError("E008")


# ---------------------------------------------------------------------------
# 核心处理流程
# ---------------------------------------------------------------------------
def process_input(
    raw_input: Any,
    output_format: str = "json",
    custom_template: Optional[Dict[str, Any]] = None,
) -> ProcessingResult:
    """
    核心处理流程
    1. 解析输入
    2. 提取关键信息
    3. 计算置信度
    4. 生成结果
    """
    # Step 1: 解析输入
    input_type, parsed_data = parse_input(raw_input)

    # Step 2: 根据输入类型处理
    boundary_note = BOUNDARY_NOTES.get(input_type, "输入已处理")

    if input_type == "file":
        # 读取文件内容
        file_path = parsed_data.get("path", "")
        content = read_file_content(file_path)
        parsed_data = {
            "content": content,
            "source": file_path,
            "file_path": file_path,
        }

    elif input_type == "url":
        # 不访问网络，仅记录 URL 和明确的边界说明
        url = parsed_data.get("url", "")
        parsed_data = {
            "url": url,
            "note": "URL 已记录，未访问网络（遵循能力边界：本工具不执行网络请求）",
            "boundary": "仅记录 URL，不进行网络访问。如需获取内容，请提供文本或文件。",
        }

    elif input_type == "text":
        # 纯文本，尝试提取基本信息
        text = parsed_data.get("text", "")
        # 提取可能的标题（第一行非空）
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            parsed_data["title"] = lines[0]
        parsed_data["content"] = text
        parsed_data["boundary"] = "文本已解析，未执行外部操作"

    # Step 3: 提取字段
    extracted, missing = extract_fields(parsed_data)

    # 确保 URL 输入时保留 url 字段
    if input_type == "url":
        extracted["url"] = parsed_data["url"]
        extracted["note"] = "URL 已记录，未访问网络（遵循能力边界）"

    # Step 4: 计算置信度
    confidence, warnings = calculate_confidence(extracted, missing)

    # Step 5: 生成结果
    return ProcessingResult(
        data=extracted,
        confidence=confidence,
        warnings=warnings,
        boundary_note=boundary_note,
    )


def process_batch(
    inputs: List[Any], output_format: str = "json"
) -> List[ProcessingResult]:
    """批量处理多个输入"""
    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_input(item, output_format)
            results.append(result)
        except ValueError as exc:
            # 单个失败不影响整体
            error_code = str(exc)
            results.append(
                ProcessingResult(
                    data={"error": ERROR_MESSAGES.get(error_code, str(exc))},
                    confidence=0,
                    warnings=[f"第 {idx+1} 项处理失败"],
                    boundary_note=f"第 {idx+1} 项处理失败，未完成处理",
                )
            )
    return results


# ---------------------------------------------------------------------------
# 命令行界面
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description=f"{DISPLAY_NAME} - 输入内容结构化处理工具 v{VERSION}"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入内容：文本、JSON 字符串、文件路径或 URL",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "-b",
        "--batch",
        help="批量处理：JSON 数组字符串或包含 JSON 数组的文件",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部输入）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    内置自检：使用硬编码样例数据验证核心逻辑
    不读外部文件、不访问网络、不依赖当前工作目录
    """
    print("=" * 60)
    print(f"{DISPLAY_NAME} 自检开始 (v{VERSION})")
    print("=" * 60)

    passed = 0
    failed = 0

    # 测试 1: JSON 输入解析
    print("\n[测试 1] JSON 输入解析")
    try:
        sample_json = json.dumps(
            {
                "title": "测试小说标题",
                "author": "测试作者",
                "content": "这是一段用于测试的正文内容，包含足够长度的文本信息以验证提取逻辑。",
            },
            ensure_ascii=False,
        )
        result = process_input(sample_json)
        assert result.confidence >= 70, f"置信度过低: {result.confidence}"
        assert "title" in result.data, "未提取到标题"
        assert "author" in result.data, "未提取到作者"
        print(f"  通过 (置信度: {result.confidence}%)")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 2: 纯文本输入
    print("\n[测试 2] 纯文本输入")
    try:
        sample_text = (
            "第一章 开始\n"
            "这是正文的第一段落，包含一些描述性内容。\n"
            "这是第二段落，继续补充细节信息。"
        )
        result = process_input(sample_text)
        assert result.confidence >= 50, f"置信度过低: {result.confidence}"
        assert "title" in result.data, "未提取到标题（应为第一行）"
        print(f"  通过 (置信度: {result.confidence}%)")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 3: 空输入错误处理
    print("\n[测试 3] 空输入错误处理")
    try:
        process_input("")
        print("  失败: 未抛出异常")
        failed += 1
    except ValueError as exc:
        assert str(exc) == "E001", f"错误码不符: {exc}"
        print(f"  通过 (错误码: {exc})")
        passed += 1

    # 测试 4: 批量处理
    print("\n[测试 4] 批量处理")
    try:
        batch_data = [
            {"title": "书一", "content": "内容一，足够长的正文文本。"},
            {"title": "书二", "content": "内容二，足够长的正文文本。"},
        ]
        results = process_batch(batch_data)
        assert len(results) == 2, "批量处理数量不符"
        assert all(r.confidence >= 50 for r in results), "批量处理置信度过低"
        print(f"  通过 (处理 {len(results)} 项)")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 5: 置信度格式
    print("\n[测试 5] 置信度格式")
    try:
        assert format_confidence(95) == "直接输出"
        assert format_confidence(87) == "建议复核"
        assert format_confidence(80) == "[需核实]"
        print("  通过")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 6: 输出格式
    print("\n[测试 6] 输出格式")
    try:
        result = process_input({"title": "测试", "content": "内容"})
        json_out = format_output(result, "json")
        text_out = format_output(result, "text")
        assert "confidence" in json_out, "JSON 输出缺少置信度"
        assert "提取字段" in text_out, "文本输出缺少提取字段"
        print("  通过")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 7: 错误码体系
    print("\n[测试 7] 错误码体系")
    try:
        assert "E001" in ERROR_MESSAGES
        assert "E002" in ERROR_MESSAGES
        assert "E003" in ERROR_MESSAGES
        assert "E004" in ERROR_MESSAGES
        assert "E005" in ERROR_MESSAGES
        print(f"  通过 (共 {len(ERROR_MESSAGES)} 个错误码)")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 测试 8: 能力边界
    print("\n[测试 8] 能力边界（URL 不访问网络）")
    try:
        result = process_input("https://example.com/novel/chapter1")
        assert "url" in result.data, "URL 未被记录"
        assert "note" in result.data, "缺少边界说明"
        assert "boundary" in result.data, "缺少边界说明字段"
        assert result.boundary_note is not None, "缺少边界说明"
        assert "未访问网络" in result.boundary_note, "边界说明不明确"
        print(f"  通过 (记录 URL，未访问网络)")
        passed += 1
    except Exception as exc:
        print(f"  失败: {exc}")
        failed += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主函数"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 无输入时显示帮助
    if not args.input and not args.batch:
        parser.print_help()
        return 0

    try:
        # 批量处理模式
        if args.batch:
            # 尝试解析批量输入
            try:
                batch_input = json.loads(args.batch)
                if isinstance(batch_input, str):
                    batch_input = json.loads(batch_input)
            except json.JSONDecodeError:
                # 尝试作为文件读取
                try:
                    content = read_file_content(args.batch)
                    batch_input = json.loads(content)
                except (ValueError, json.JSONDecodeError) as exc:
                    print(f"错误: {ERROR_MESSAGES.get('E003', 'E003')}")
                    print(f"批量输入必须是 JSON 数组或包含 JSON 数组的文件")
                    return 1

            if not isinstance(batch_input, list):
                print(f"错误: {ERROR_MESSAGES.get('E003', 'E003')}")
                print("批量输入必须是 JSON 数组")
                return 1

            results = process_batch(batch_input, args.format)
            for idx, result in enumerate(results, 1):
                print(f"\n--- 第 {idx} 项 ---")
                print(format_output(result, args.format))
            return 0

        # 单条处理模式
        result = process_input(args.input, args.format)
        print(format_output(result, args.format))

        # 输出边界说明
        if result.boundary_note:
            print(f"\n边界说明: {result.boundary_note}")

        # 输出置信度提示
        if result.confidence < CONFIDENCE_HIGH:
            print(f"\n提示: {format_confidence(result.confidence)}")
            if result.confidence < CONFIDENCE_MEDIUM:
                print("建议人工复核关键字段")

        return 0

    except ValueError as exc:
        error_code = str(exc)
        message = ERROR_MESSAGES.get(error_code, f"未知错误 ({error_code})")
        print(f"错误 [{error_code}]: {message}")
        return 1
    except Exception as exc:
        print(f"错误 [E010]: {ERROR_MESSAGES['E010']} - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
