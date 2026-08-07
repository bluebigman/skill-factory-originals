#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
基于功能规格独立实现的通用数据处理工具。

核心能力：
1. 将用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

错误码：
    E001: 输入为空
    E002: 关键信息缺失
    E003: 输入格式错误
    E004: 超出能力边界
    E005: 置信度过低
    E006: 内部处理异常
    E007: 参数解析错误
    E008: 输出写入失败
    E009: 批量处理中断
    E010: 未知错误

用法示例：
    python scripts/main.py --input "示例数据" --format json
    python scripts/main.py --batch file1.txt file2.txt
    python scripts/main.py --selftest
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
CONFIDENCE_HIGH = 0.90          # 置信度 >= 90%：直接输出
CONFIDENCE_MEDIUM = 0.85       # 85%-90%：建议复核
CONFIDENCE_LOW = 0.85          # <85%：标注 [需核实]

DEFAULT_OUTPUT_FORMAT = "json"

# 支持的输出格式
SUPPORTED_FORMATS = {"json", "text", "csv"}

# 关键字段（用于结构化提取）
KEY_FIELDS = [
    "title", "content", "author", "date", "source", "url", "category", "tags"
]

# 错误码与消息映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing_fields}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理异常：{detail}",
    "E007": "参数解析错误：{detail}",
    "E008": "输出写入失败：{detail}",
    "E009": "批量处理中断：{detail}",
    "E010": "未知错误：{detail}",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------
class ProcessingResult:
    """处理结果数据类。"""

    def __init__(
        self,
        data: Any,
        confidence: float,
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.data = data
        self.confidence = confidence
        self.warnings = warnings or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    def confidence_label(self) -> str:
        """根据置信度返回标注标签。"""
        if self.confidence >= CONFIDENCE_HIGH:
            return "直接输出"
        elif self.confidence >= CONFIDENCE_MEDIUM:
            return "建议复核"
        else:
            return "[需核实]"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def parse_input(raw_input: str) -> Dict[str, Any]:
    """
    解析输入内容，识别关键信息。

    参数:
        raw_input: 用户提供的原始输入字符串

    返回:
        解析后的结构化字典

    异常:
        E001: 输入为空
        E003: 输入格式错误
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("E001")

    # 尝试解析 JSON
    stripped = raw_input.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            raise ValueError("E003")

    # 尝试解析键值对格式，例如: "key1=value1; key2=value2"
    if "=" in stripped and (";" in stripped or "\n" in stripped):
        result = {}
        for line in stripped.replace(";", "\n").split("\n"):
            line = line.strip()
            if not line:
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
        if result:
            return result

    # 尝试解析 CSV 格式
    if "," in stripped and "\n" in stripped:
        lines = [l.strip() for l in stripped.split("\n") if l.strip()]
        if len(lines) >= 2:
            headers = [h.strip() for h in lines[0].split(",")]
            records = []
            for line in lines[1:]:
                values = [v.strip() for v in line.split(",")]
                if len(values) == len(headers):
                    records.append(dict(zip(headers, values)))
            if records:
                return {"records": records}

    # 否则作为纯文本处理
    return {"text": stripped}


def extract_key_fields(parsed: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    从解析结果中提取关键字段。

    参数:
        parsed: 解析后的字典

    返回:
        (提取的关键字段字典, 缺失的关键字段列表)
    """
    extracted = {}
    missing = []

    # 如果是纯文本输入，将整个文本作为 content 处理
    if "text" in parsed and len(parsed) == 1:
        extracted["content"] = parsed["text"]
        return extracted, []

    for field in KEY_FIELDS:
        value = None
        if isinstance(parsed, dict):
            # 直接查找
            if field in parsed:
                value = parsed[field]
            # 嵌套查找
            elif "records" in parsed and isinstance(parsed["records"], list):
                for record in parsed["records"]:
                    if isinstance(record, dict) and field in record:
                        value = record[field]
                        break

        if value is not None and value != "":
            extracted[field] = value
        else:
            # 某些字段允许缺失（如 tags、url、category），不强制要求
            if field not in ["tags", "url", "category"]:
                missing.append(field)

    return extracted, missing


def calculate_confidence(
    extracted: Dict[str, Any], missing_fields: List[str]
) -> float:
    """
    根据提取结果计算置信度。

    参数:
        extracted: 提取的关键字段
        missing_fields: 缺失的字段列表

    返回:
        置信度分数 (0.0 - 1.0)
    """
    # 基础置信度
    base_confidence = 0.80

    # 每个成功提取的字段增加置信度
    field_bonus = 0.02 * len(extracted)
    confidence = base_confidence + field_bonus

    # 缺失字段降低置信度
    missing_penalty = 0.03 * len(missing_fields)
    confidence -= missing_penalty

    # 限制在合理范围
    return max(0.50, min(0.98, confidence))


def process_single(
    raw_input: str, output_format: str = DEFAULT_OUTPUT_FORMAT
) -> ProcessingResult:
    """
    处理单个输入。

    参数:
        raw_input: 原始输入
        output_format: 输出格式 (json/text/csv)

    返回:
        ProcessingResult 对象

    异常:
        E001-E005 相关错误
    """
    # Step 1: 解析输入
    parsed = parse_input(raw_input)

    # Step 2: 提取关键字段
    extracted, missing = extract_key_fields(parsed)

    # 检查关键信息缺失 - 放宽条件，允许更多缺失
    if len(missing) > 5:
        raise ValueError(f"E002:{','.join(missing[:3])}")

    # Step 3: 计算置信度
    confidence = calculate_confidence(extracted, missing)

    # Step 4: 按格式组织输出
    data = format_output(extracted, parsed, output_format)

    # 生成警告
    warnings = []
    if len(missing) > 0:
        warnings.append(f"缺失字段: {', '.join(missing)}")
    if confidence < CONFIDENCE_MEDIUM:
        warnings.append("置信度较低，建议人工复核")

    return ProcessingResult(
        data=data,
        confidence=confidence,
        warnings=warnings,
        metadata={
            "input_type": type(parsed).__name__,
            "extracted_fields": list(extracted.keys()),
            "missing_fields": missing,
        },
    )


def format_output(
    extracted: Dict[str, Any], parsed: Dict[str, Any], output_format: str
) -> Any:
    """
    按指定格式组织输出。

    参数:
        extracted: 提取的关键字段
        parsed: 解析后的原始数据
        output_format: 输出格式

    返回:
        格式化后的数据
    """
    if output_format == "json":
        return {
            "extracted": extracted,
            "raw_preview": str(parsed)[:500],  # 预览前500字符
        }
    elif output_format == "text":
        lines = ["=== 提取结果 ==="]
        for key, value in extracted.items():
            lines.append(f"{key}: {value}")
        if not extracted:
            lines.append("(未提取到关键字段)")
        return "\n".join(lines)
    elif output_format == "csv":
        if not extracted:
            return "字段,值\n"
        lines = ["字段,值"]
        for key, value in extracted.items():
            # 简单转义
            value_str = str(value).replace('"', '""')
            lines.append(f'"{key}","{value_str}"')
        return "\n".join(lines)
    else:
        raise ValueError("E003")


def process_batch(
    inputs: List[str], output_format: str = DEFAULT_OUTPUT_FORMAT
) -> List[ProcessingResult]:
    """
    批量处理多个输入。

    参数:
        inputs: 输入列表
        output_format: 输出格式

    返回:
        ProcessingResult 列表
    """
    results = []
    for idx, item in enumerate(inputs):
        try:
            result = process_single(item, output_format)
            results.append(result)
        except ValueError as e:
            error_code = str(e).split(":")[0]
            results.append(
                ProcessingResult(
                    data=None,
                    confidence=0.0,
                    warnings=[ERROR_MESSAGES.get(error_code, str(e))],
                    metadata={"error": error_code, "index": idx},
                )
            )
    return results


# ---------------------------------------------------------------------------
# 文件输入输出
# ---------------------------------------------------------------------------
def read_input_file(file_path: str) -> str:
    """
    读取输入文件内容。

    参数:
        file_path: 文件路径

    返回:
        文件内容字符串

    异常:
        E006: 文件读取失败
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise ValueError(f"E006:{str(e)}")


def write_output_file(content: str, file_path: Optional[str] = None) -> str:
    """
    写入输出文件。

    参数:
        content: 要写入的内容
        file_path: 输出文件路径（None 则使用临时文件）

    返回:
        写入的文件路径

    异常:
        E008: 写入失败
    """
    try:
        if file_path is None:
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="tasks_output_")
            os.close(fd)
            file_path = temp_path

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
    except Exception as e:
        raise ValueError(f"E008:{str(e)}")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件或网络。

    返回:
        True 表示自检通过
    """
    print("=" * 60)
    print("开始运行自检 (selftest)...")
    print("=" * 60)

    # 测试用例 1: 正常 JSON 输入
    print("\n[测试 1] JSON 输入解析")
    test_input_1 = '{"title": "测试标题", "content": "测试内容", "author": "张三"}'
    try:
        result_1 = process_single(test_input_1, "json")
        assert result_1.confidence >= 0.80, "置信度应大于 0.80"
        assert "title" in str(result_1.data), "应包含 title 字段"
        print(f"  ✓ 通过 (置信度: {result_1.confidence:.2f})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 2: 纯文本输入
    print("\n[测试 2] 纯文本输入")
    test_input_2 = "这是一段简单的文本内容，用于测试。"
    try:
        result_2 = process_single(test_input_2, "text")
        assert result_2.confidence > 0, "置信度应大于 0"
        assert "content" in str(result_2.data), "应包含文本处理结果"
        print(f"  ✓ 通过 (置信度: {result_2.confidence:.2f})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 3: 空输入应报错 E001
    print("\n[测试 3] 空输入错误处理")
    try:
        process_single("")
        print("  ✗ 失败: 空输入未触发错误")
        return False
    except ValueError as e:
        error_code = str(e).split(":")[0]
        assert error_code == "E001", f"错误码应为 E001, 实际为 {error_code}"
        print(f"  ✓ 通过 (错误码: {error_code})")

    # 测试用例 4: 批量处理
    print("\n[测试 4] 批量处理")
    test_inputs = [
        '{"title": "批量1", "content": "内容1"}',
        "纯文本批量测试",
        "",  # 空输入应产生错误结果
    ]
    try:
        batch_results = process_batch(test_inputs)
        assert len(batch_results) == 3, "应返回 3 个结果"
        assert batch_results[0].confidence > 0, "第一个结果应有置信度"
        assert batch_results[2].confidence == 0.0, "空输入置信度应为 0"
        print(f"  ✓ 通过 ({len(batch_results)} 个结果)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 5: 文件读写
    print("\n[测试 5] 文件读写")
    try:
        # 写入临时文件
        test_content = '{"title": "文件测试", "content": "文件内容"}'
        temp_path = write_output_file(test_content)
        assert os.path.exists(temp_path), "临时文件应存在"

        # 读取并处理
        file_content = read_input_file(temp_path)
        result_5 = process_single(file_content)
        assert result_5.confidence > 0, "文件内容处理应有置信度"

        # 清理
        os.unlink(temp_path)
        print(f"  ✓ 通过 (临时文件: {temp_path})")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 6: 置信度标注逻辑
    print("\n[测试 6] 置信度标注")
    try:
        # 构造低置信度场景
        low_conf_result = ProcessingResult(
            data={"partial": True},
            confidence=0.70,
            warnings=["测试警告"],
        )
        assert low_conf_result.confidence_label() == "[需核实]", \
            "低置信度应标注 [需核实]"

        # 构造高置信度场景
        high_conf_result = ProcessingResult(
            data={"full": True},
            confidence=0.95,
        )
        assert high_conf_result.confidence_label() == "直接输出", \
            "高置信度应标注 直接输出"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 7: 错误码覆盖
    print("\n[测试 7] 错误码覆盖")
    error_codes = ["E001", "E002", "E003", "E004", "E005"]
    for code in error_codes:
        assert code in ERROR_MESSAGES, f"错误码 {code} 应存在于映射表"
    print(f"  ✓ 通过 ({len(error_codes)} 个错误码)")

    # 测试用例 8: 输出格式
    print("\n[测试 8] 输出格式")
    try:
        test_data = {"title": "格式测试", "content": "内容"}
        json_out = format_output(test_data, {}, "json")
        text_out = format_output(test_data, {}, "text")
        csv_out = format_output(test_data, {}, "csv")

        assert isinstance(json_out, dict), "JSON 输出应为字典"
        assert isinstance(text_out, str), "文本输出应为字符串"
        assert "字段" in csv_out, "CSV 输出应包含表头"
        print(f"  ✓ 通过 (json/text/csv 三种格式)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 9: 关键字段提取
    print("\n[测试 9] 关键字段提取")
    try:
        test_parsed = {
            "title": "测试",
            "content": "内容",
            "author": "作者",
            "date": "2024-01-01",
        }
        extracted, missing = extract_key_fields(test_parsed)
        assert "title" in extracted, "应提取 title"
        assert "content" in extracted, "应提取 content"
        assert "author" in extracted, "应提取 author"
        # tags 和 url 允许缺失
        assert "tags" not in extracted, "tags 应允许缺失"
        print(f"  ✓ 通过 (提取 {len(extracted)} 个字段)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 10: 边界情况
    print("\n[测试 10] 边界情况")
    try:
        # 超长输入
        long_input = "x" * 10000
        result_long = process_single(long_input, "text")
        assert result_long.confidence > 0, "超长输入应能处理"

        # 特殊字符
        special_input = '{"title": "特殊\\"字符", "content": "包含\\n换行"}'
        result_special = process_single(special_input)
        assert result_special.confidence > 0, "特殊字符应能处理"

        # Unicode
        unicode_input = '{"title": "中文标题", "content": "日本語テキスト", "author": "한국어"}'
        result_unicode = process_single(unicode_input)
        assert result_unicode.confidence > 0, "Unicode 应能处理"

        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("所有自检测试通过！✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主函数，处理命令行参数。

    返回:
        退出码 (0 成功, 非 0 失败)
    """
    parser = argparse.ArgumentParser(
        description="通用数据处理工具 - 基于功能规格独立实现",
        epilog="示例: python scripts/main.py --input '{\"title\": \"测试\"}' --format json",
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（字符串或 JSON）",
    )
    input_group.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径",
    )
    input_group.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个输入",
    )

    # 输出参数
    parser.add_argument(
        "--format",
        choices=SUPPORTED_FORMATS,
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"输出格式 (默认: {DEFAULT_OUTPUT_FORMAT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（不指定则打印到控制台）",
    )

    # 其他参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息",
    )

    # 解析参数
    try:
        args = parser.parse_args()
    except SystemExit:
        return 1

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数验证
    if not args.input and not args.file and not args.batch:
        parser.print_help()
        print(f"\n错误 E007: 必须提供 --input, --file 或 --batch 参数")
        return 1

    try:
        # 收集输入
        if args.batch:
            # 批量模式
            raw_inputs = args.batch
            results = process_batch(raw_inputs, args.format)

            # 输出结果
            output_lines = []
            for idx, result in enumerate(results):
                label = result.confidence_label()
                output_lines.append(f"[{idx + 1}] {label}")
                if result.warnings:
                    for warn in result.warnings:
                        output_lines.append(f"    警告: {warn}")
                output_lines.append(f"    结果: {json.dumps(result.data, ensure_ascii=False)}")
                output_lines.append("")

            output_content = "\n".join(output_lines)

        else:
            # 单条模式
            if args.file:
                raw_input = read_input_file(args.file)
            else:
                raw_input = args.input

            result = process_single(raw_input, args.format)

            # 输出结果
            output_lines = []
            output_lines.append(f"处理完成，置信度: {result.confidence:.2f} ({result.confidence_label()})")
            if result.warnings:
                output_lines.append("警告:")
                for warn in result.warnings:
                    output_lines.append(f"  - {warn}")

            if args.format == "json":
                output_lines.append(json.dumps(result.data, ensure_ascii=False, indent=2))
            else:
                output_lines.append(str(result.data))

            output_content = "\n".join(output_lines)

        # 输出
        if args.output:
            write_output_file(output_content, args.output)
            print(f"结果已写入: {args.output}")
        else:
            print(output_content)

        return 0

    except ValueError as e:
        error_msg = str(e)
        if ":" in error_msg:
            error_code, detail = error_msg.split(":", 1)
        else:
            error_code, detail = error_msg, ""

        message = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        if detail:
            message = message.format(detail=detail)
        elif "{" in message:
            # 处理需要额外参数的错误消息
            message = message.format(
                missing_fields=detail,
                example="示例输入",
                suggestion="请提供更完整的信息",
            )

        print(f"错误 {error_code}: {message}")
        return 1

    except Exception as e:
        print(f"错误 E010: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
