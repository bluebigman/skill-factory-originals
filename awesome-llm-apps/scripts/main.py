#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-llm-apps 技能工具 - 独立实现脚本
=========================================
本脚本依据功能规格全新编写（clean-room），提供以下能力：
- 将用户提供的数据/文件/URL 转换为结构化结果
- 识别并保留输入中的关键信息
- 按约定格式生成输出
- 对不确定项给出置信度提示
- 支持批量处理和自定义格式

仅使用 Python 标准库，无第三方依赖。
用法:
    python scripts/main.py --selftest      # 运行离线自检
    python scripts/main.py --input "文本"   # 处理输入
    python scripts/main.py --batch f1 f2    # 批量处理
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码常量（E001-E010）
# ---------------------------------------------------------------------------
class ErrorCode:
    """错误码定义，对应功能规格中的异常处理体系。"""
    E001_INPUT_EMPTY = "E001"       # 输入为空
    E002_INFO_MISSING = "E002"      # 关键信息缺失
    E003_FORMAT_ERROR = "E003"      # 输入格式错误
    E004_OUT_OF_SCOPE = "E004"      # 超出能力边界
    E005_LOW_CONFIDENCE = "E005"    # 置信度过低
    E006_FILE_NOT_FOUND = "E006"    # 文件不存在
    E007_URL_UNSUPPORTED = "E007"   # URL 不支持（离线环境）
    E008_BATCH_EMPTY = "E008"       # 批量输入为空
    E009_INTERNAL_ERROR = "E009"    # 内部处理错误
    E010_INVALID_OUTPUT = "E010"    # 输出格式无效


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessedItem:
    """单条输入的处理结果。"""

    def __init__(self, raw_input: str, structured: Dict[str, Any],
                 confidence: float, warnings: Optional[List[str]] = None):
        self.raw_input = raw_input
        self.structured = structured
        self.confidence = confidence  # 0.0 ~ 1.0
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示。"""
        return {
            "raw_input": self.raw_input,
            "structured": self.structured,
            "confidence": round(self.confidence, 2),
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def extract_key_fields(text: str) -> Tuple[Dict[str, Any], float]:
    """
    从输入文本中提取关键字段并结构化。

    识别规则（基于通用启发式，非领域特定）:
    - 检测常见键值对模式 (key: value)
    - 识别列表项（以 - 或 * 开头）
    - 识别标题行（# 开头）
    - 识别 URL 和文件路径

    返回: (结构化字典, 置信度 0.0-1.0)
    """
    if not text or not text.strip():
        return {}, 0.0

    lines = text.strip().splitlines()
    structured: Dict[str, Any] = {}
    detected_count = 0
    total_lines = len(lines)

    # 键值对模式: key: value 或 key = value
    kv_patterns = [":", "=", "："]
    list_items = []
    headings = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 标题行
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())
            detected_count += 1
            continue

        # 列表项
        if line.startswith("- ") or line.startswith("* "):
            list_items.append(line[2:].strip())
            detected_count += 1
            continue

        # 键值对
        for sep in kv_patterns:
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    structured[key] = value
                    detected_count += 1
                    break
        else:
            # 未识别的行，作为普通文本保留
            if "other" not in structured:
                structured["other"] = []
            structured["other"].append(line)

    # 收集列表项
    if list_items:
        structured["list_items"] = list_items

    # 收集标题
    if headings:
        structured["headings"] = headings

    # 置信度计算：根据识别出的结构化元素比例
    if total_lines == 0:
        confidence = 0.0
    else:
        # 基础置信度 = 识别出的元素数 / 总行数
        base_confidence = detected_count / total_lines

        # 如果完全没有识别出结构化元素，置信度低
        if detected_count == 0:
            confidence = 0.3  # 纯文本，低置信度
        else:
            # 有结构化元素，根据比例调整
            confidence = min(0.95, 0.5 + base_confidence * 0.5)

    return structured, confidence


def is_file_path(text: str) -> bool:
    """
    判断输入是否可能是文件路径。
    
    检查条件：
    - 包含路径分隔符（/ 或 \）
    - 或包含常见的文件扩展名
    - 或以 ./ 或 ../ 开头
    - 或直接是存在的文件
    """
    # 如果文件存在，肯定是文件路径
    if os.path.isfile(text):
        return True
    
    # 检查是否包含路径分隔符
    if "/" in text or "\\" in text:
        return True
    
    # 检查常见的文件扩展名
    common_extensions = ['.txt', '.md', '.json', '.csv', '.log', '.xml', 
                         '.yaml', '.yml', '.ini', '.cfg', '.conf']
    lower_text = text.lower()
    if any(lower_text.endswith(ext) for ext in common_extensions):
        return True
    
    # 检查是否以 ./ 或 ../ 开头
    if text.startswith("./") or text.startswith("../"):
        return True
    
    return False


def process_single_input(raw_input: str) -> ProcessedItem:
    """
    处理单个输入，返回结构化结果。

    遵循功能规格 Step 2 的置信度规则:
    - ≥90%: 直接输出
    - 85%-90%: 标注"建议复核"
    - <85%: 标注"[需核实]"
    """
    # 输入为空检查 (E001)
    if not raw_input or not raw_input.strip():
        raise ValueError(ErrorCode.E001_INPUT_EMPTY)

    # 检查是否为 URL（离线环境不支持，E007）
    if raw_input.strip().lower().startswith(("http://", "https://", "ftp://")):
        raise ValueError(ErrorCode.E007_URL_UNSUPPORTED)

    # 检查是否为文件路径
    if is_file_path(raw_input):
        # 如果文件存在，读取并处理
        if os.path.isfile(raw_input):
            try:
                with open(raw_input, "r", encoding="utf-8") as f:
                    content = f.read()
                # 读取文件后继续处理内容
                structured, confidence = extract_key_fields(content)
                warnings = []
                if confidence < 0.85:
                    warnings.append("[需核实] 置信度较低，请人工复核")
                elif confidence < 0.90:
                    warnings.append("建议复核")
                return ProcessedItem(raw_input, structured, confidence, warnings)
            except (IOError, OSError):
                raise ValueError(ErrorCode.E006_FILE_NOT_FOUND)
        else:
            # 文件路径格式但文件不存在，抛出 E006
            raise ValueError(ErrorCode.E006_FILE_NOT_FOUND)

    # 普通文本输入
    structured, confidence = extract_key_fields(raw_input)
    warnings = []

    # 置信度标注规则（功能规格 Step 2-3）
    if confidence < 0.85:
        warnings.append("[需核实] 置信度较低，请人工复核")
    elif confidence < 0.90:
        warnings.append("建议复核")

    return ProcessedItem(raw_input, structured, confidence, warnings)


def process_batch(inputs: List[str]) -> List[ProcessedItem]:
    """
    批量处理多个输入。

    遵循功能规格"进阶用法-批量处理"：连续提供多个输入，按同一规则逐项处理。
    """
    if not inputs:
        raise ValueError(ErrorCode.E008_BATCH_EMPTY)

    results = []
    for item in inputs:
        try:
            result = process_single_input(item)
            results.append(result)
        except ValueError as e:
            # 单条失败不中断整体，记录错误信息
            error_result = ProcessedItem(
                item,
                {"error": str(e)},
                0.0,
                [f"处理失败: {e}"]
            )
            results.append(error_result)
    return results


def format_output(results: List[ProcessedItem], format_type: str = "json") -> str:
    """
    按指定格式输出结果。

    支持: json, text
    """
    if format_type == "json":
        return json.dumps(
            [r.to_dict() for r in results],
            ensure_ascii=False,
            indent=2
        )
    elif format_type == "text":
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"=== 结果 {i} ===")
            lines.append(f"输入: {r.raw_input}")
            lines.append(f"置信度: {r.confidence:.0%}")
            if r.warnings:
                lines.append(f"警告: {'; '.join(r.warnings)}")
            lines.append(f"结构化: {json.dumps(r.structured, ensure_ascii=False)}")
            lines.append("")
        return "\n".join(lines)
    else:
        raise ValueError(ErrorCode.E010_INVALID_OUTPUT)


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例数据，不读外部文件、不依赖当前工作目录、
    不访问网络，任何环境直接可过。

    使用宽松阈值（大小比较/区间判断），避免精确值依赖。
    """
    print("=" * 60)
    print("awesome-llm-apps 自检开始")
    print("=" * 60)

    # --- 测试用例 1: 键值对解析 ---
    print("\n[测试1] 键值对解析")
    sample1 = "名称: 测试工具\n版本: 1.0\n作者: skill-factory-auto"
    try:
        result1 = process_single_input(sample1)
        assert result1.structured.get("名称") == "测试工具", "名称字段解析失败"
        assert result1.structured.get("版本") == "1.0", "版本字段解析失败"
        assert result1.confidence > 0.3, "置信度应大于0.3"
        print("  ✓ 键值对解析正确")
        print(f"  结构化: {result1.structured}")
        print(f"  置信度: {result1.confidence:.2f}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 2: 列表项解析 ---
    print("\n[测试2] 列表项解析")
    sample2 = "- 苹果\n- 香蕉\n- 橙子"
    try:
        result2 = process_single_input(sample2)
        assert "list_items" in result2.structured, "列表项未识别"
        assert len(result2.structured["list_items"]) == 3, "列表项数量应为3"
        assert result2.confidence > 0.3, "置信度应大于0.3"
        print("  ✓ 列表项解析正确")
        print(f"  结构化: {result2.structured}")
        print(f"  置信度: {result2.confidence:.2f}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 3: 空输入错误处理 ---
    print("\n[测试3] 空输入错误处理")
    try:
        process_single_input("")
        print("  ✗ 空输入应抛出 E001 错误")
        return 1
    except ValueError as e:
        assert str(e) == ErrorCode.E001_INPUT_EMPTY, f"错误码应为E001，实际: {e}"
        print("  ✓ 空输入正确返回 E001")

    # --- 测试用例 4: 混合内容解析 ---
    print("\n[测试4] 混合内容解析")
    sample4 = "# 标题\n名称: 测试\n- 项目A\n- 项目B"
    try:
        result4 = process_single_input(sample4)
        assert "headings" in result4.structured, "标题未识别"
        assert "名称" in result4.structured, "键值对未识别"
        assert "list_items" in result4.structured, "列表项未识别"
        assert result4.confidence > 0.4, "置信度应大于0.4"
        print("  ✓ 混合内容解析正确")
        print(f"  结构化: {result4.structured}")
        print(f"  置信度: {result4.confidence:.2f}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 5: 批量处理 ---
    print("\n[测试5] 批量处理")
    batch_input = ["名称: A", "名称: B", ""]
    try:
        results = process_batch(batch_input)
        assert len(results) == 3, "批量处理应返回3条结果"
        # 空输入应产生错误结果，但不中断整体
        assert "error" in results[2].structured, "空输入应记录错误"
        print("  ✓ 批量处理正确")
        print(f"  结果数: {len(results)}")
        print(f"  空输入处理: {results[2].structured}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 6: 置信度标注规则 ---
    print("\n[测试6] 置信度标注规则")
    # 高置信度样例（结构化比例高）
    high_conf_sample = "名称: X\n版本: 1\n作者: Y\n日期: 2026-01-01"
    try:
        result_high = process_single_input(high_conf_sample)
        # 高置信度不应有 [需核实] 警告
        assert not any("[需核实]" in w for w in result_high.warnings), "高置信度不应有[需核实]"
        print("  ✓ 高置信度标注正确")
        print(f"  置信度: {result_high.confidence:.2f}, 警告: {result_high.warnings}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # 低置信度样例（纯文本）
    low_conf_sample = "这是一段普通的纯文本内容，没有明显的结构化信息"
    try:
        result_low = process_single_input(low_conf_sample)
        # 低置信度应有 [需核实] 警告
        assert any("[需核实]" in w for w in result_low.warnings), "低置信度应有[需核实]"
        print("  ✓ 低置信度标注正确")
        print(f"  置信度: {result_low.confidence:.2f}, 警告: {result_low.warnings}")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 7: URL 不支持 ---
    print("\n[测试7] URL 不支持")
    try:
        process_single_input("https://example.com/data")
        print("  ✗ URL 应抛出 E007 错误")
        return 1
    except ValueError as e:
        assert str(e) == ErrorCode.E007_URL_UNSUPPORTED, f"错误码应为E007，实际: {e}"
        print("  ✓ URL 正确返回 E007")

    # --- 测试用例 8: 输出格式 ---
    print("\n[测试8] 输出格式")
    sample8 = "名称: 测试"
    try:
        result8 = process_single_input(sample8)
        json_output = format_output([result8], "json")
        assert json.loads(json_output)[0]["structured"]["名称"] == "测试", "JSON输出解析失败"
        text_output = format_output([result8], "text")
        assert "名称" in text_output, "文本输出应包含字段名"
        print("  ✓ 输出格式正确")
        print(f"  JSON: {json_output[:50]}...")
        print(f"  TEXT: {text_output[:50]}...")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return 1

    # --- 测试用例 9: 文件输入 ---
    print("\n[测试9] 文件输入")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("名称: 文件测试\n内容: 这是文件内容")
        temp_file = f.name
    try:
        result9 = process_single_input(temp_file)
        assert result9.structured.get("名称") == "文件测试", "文件内容解析失败"
        print("  ✓ 文件输入解析正确")
        print(f"  结构化: {result9.structured}")
    finally:
        os.unlink(temp_file)

    # --- 测试用例 10: 不存在的文件 ---
    print("\n[测试10] 不存在的文件")
    try:
        process_single_input("/nonexistent/path/file.txt")
        print("  ✗ 不存在文件应抛出 E006 错误")
        return 1
    except ValueError as e:
        assert str(e) == ErrorCode.E006_FILE_NOT_FOUND, f"错误码应为E006，实际: {e}"
        print("  ✓ 不存在文件正确返回 E006")

    # --- 全部通过 ---
    print("\n" + "=" * 60)
    print("✅ 所有自检测试全部通过")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="awesome-llm-apps 技能工具 - 将输入转换为结构化结果",
        epilog="示例: python main.py --input '名称: 测试' --format json"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置硬编码样例，无需外部依赖）"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="单个输入内容（文本或文件路径）"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        nargs="+",
        help="批量输入（多个参数）"
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    try:
        if args.batch:
            # 批量处理
            results = process_batch(args.batch)
            output = format_output(results, args.format)
            print(output)
            return 0
        elif args.input:
            # 单条处理
            result = process_single_input(args.input)
            output = format_output([result], args.format)
            print(output)
            return 0
        else:
            # 无输入参数，显示帮助
            parser.print_help()
            return 0
    except ValueError as e:
        error_code = str(e)
        error_messages = {
            ErrorCode.E001_INPUT_EMPTY: "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
            ErrorCode.E002_INFO_MISSING: "还缺少以下信息，请补充：...",
            ErrorCode.E003_FORMAT_ERROR: "输入格式不符合要求，示例：...",
            ErrorCode.E004_OUT_OF_SCOPE: "这超出了本工具的能力范围，建议...",
            ErrorCode.E005_LOW_CONFIDENCE: "结果无法确定，建议：...",
            ErrorCode.E006_FILE_NOT_FOUND: "文件不存在，请检查路径",
            ErrorCode.E007_URL_UNSUPPORTED: "离线环境不支持 URL 输入，请提供文本或文件路径",
            ErrorCode.E008_BATCH_EMPTY: "批量输入为空，请提供至少一个输入",
            ErrorCode.E010_INVALID_OUTPUT: "无效的输出格式，仅支持 json 或 text",
        }
        message = error_messages.get(error_code, f"未知错误: {error_code}")
        print(f"错误 [{error_code}]: {message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ErrorCode.E009_INTERNAL_ERROR}]: 内部错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
