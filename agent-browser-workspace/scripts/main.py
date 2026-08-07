#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-browser-workspace 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不复制任何既有实现。
提供核心处理流程、错误码体系、以及离线自检功能。
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
APP_NAME = "agent-browser-workspace"
VERSION = "1.0.0"

# 错误码与标准化话术映射（依据功能规格）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{}",
    "E003": "输入格式不符合要求，示例：{}",
    "E004": "这超出了本工具的能力范围，建议：{}",
    "E005": "结果无法确定，建议：{}",
    # 内部错误码（扩展）
    "E006": "内部处理错误：{}",
    "E007": "文件读取失败：{}",
    "E008": "JSON 解析失败：{}",
    "E009": "输出写入失败：{}",
    "E010": "未知错误：{}",
}

# 置信度阈值（依据规格）
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.85

# 关键字段列表（依据规格 Step 2）
KEY_FIELDS = ["title", "content", "url", "author", "date"]


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class BrowserWorkspaceProcessor:
    """核心处理器：将输入内容转换为结构化结果"""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def process(self, input_data: Any, output_format: str = "json") -> Dict[str, Any]:
        """
        主处理入口

        Args:
            input_data: 用户提供的数据（字符串 / 字典 / 列表）
            output_format: 输出格式（json / text）

        Returns:
            包含处理结果和元信息的字典
        """
        # Step 1: 输入校验
        if input_data is None or (isinstance(input_data, str) and not input_data.strip()):
            return self._make_error_result("E001")

        # Step 2: 解析输入
        parsed_data, parse_error = self._parse_input(input_data)
        if parse_error:
            return self._make_error_result(parse_error)

        # Step 3: 提取关键字段
        extracted, extraction_error = self._extract_key_fields(parsed_data)
        if extraction_error:
            return self._make_error_result(extraction_error)

        # Step 4: 计算置信度
        confidence = self._calculate_confidence(extracted)

        # Step 5: 生成输出
        result = self._build_result(extracted, confidence, output_format)
        return result

    def _parse_input(self, input_data: Any) -> Tuple[Any, Optional[str]]:
        """
        解析输入数据

        Returns:
            (解析后的数据, 错误码或None)
        """
        if isinstance(input_data, str):
            # 尝试 JSON 解析
            try:
                return json.loads(input_data), None
            except json.JSONDecodeError:
                # 不是 JSON，作为纯文本处理
                return {"raw_text": input_data}, None
        elif isinstance(input_data, (dict, list)):
            return input_data, None
        else:
            return None, "E003"

    def _extract_key_fields(self, data: Any) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        从解析后的数据中提取关键字段

        Returns:
            (提取的字段字典, 错误码或None)
        """
        extracted: Dict[str, Any] = {}

        # 检查是否为纯文本输入
        if isinstance(data, dict) and "raw_text" in data and len(data) == 1:
            # 纯文本输入
            text = data["raw_text"]
            extracted = {"text": text, "length": len(text)}
            return extracted, None

        if isinstance(data, dict):
            # 从字典中提取已知字段
            for field in KEY_FIELDS:
                if field in data:
                    extracted[field] = data[field]

            # 如果没有任何关键字段，但字典非空，保留原始数据
            if not extracted and data:
                extracted = {"data": data}

        elif isinstance(data, list):
            # 列表数据：逐项提取
            items = []
            for item in data:
                if isinstance(item, dict):
                    item_extracted, _ = self._extract_key_fields(item)
                    items.append(item_extracted)
                else:
                    items.append({"value": item})
            extracted = {"items": items}

        return extracted, None

    def _calculate_confidence(self, extracted: Dict[str, Any]) -> float:
        """
        计算置信度（0.0 - 1.0）

        规则（依据规格）：
        - 字段完整度高 → 置信度高
        - 字段缺失 → 置信度降低
        """
        if not extracted:
            return 0.0

        # 基于字段完整度计算
        if "items" in extracted:
            # 列表数据：基于项目完整性
            items = extracted["items"]
            if not items:
                return 0.0
            avg_completeness = sum(
                1.0 if isinstance(item, dict) and item else 0.5
                for item in items
            ) / len(items)
            return min(0.95, avg_completeness)

        if "text" in extracted:
            # 纯文本：基于长度和内容
            text = extracted.get("text", "")
            if len(text) > 100:
                return 0.85
            elif len(text) > 10:
                return 0.70
            return 0.50

        # 字典数据：基于字段数量
        field_count = len(extracted)
        if field_count >= 4:
            return 0.95
        elif field_count >= 2:
            return 0.85
        return 0.60

    def _build_result(
        self,
        extracted: Dict[str, Any],
        confidence: float,
        output_format: str,
    ) -> Dict[str, Any]:
        """
        构建最终结果

        Args:
            extracted: 提取的关键字段
            confidence: 置信度（0-1）
            output_format: 输出格式

        Returns:
            结果字典
        """
        # 置信度标注（依据规格）
        if confidence >= CONFIDENCE_HIGH:
            confidence_note = "直接输出"
        elif confidence >= CONFIDENCE_MEDIUM:
            confidence_note = "建议复核"
        else:
            confidence_note = "[需核实]"

        # 构建结果
        result: Dict[str, Any] = {
            "status": "success",
            "data": extracted,
            "confidence": round(confidence, 2),
            "confidence_note": confidence_note,
            "format": output_format,
            "app": APP_NAME,
            "version": VERSION,
        }

        # 低置信度时添加提示
        if confidence < CONFIDENCE_MEDIUM:
            result["warning"] = "结果无法确定，建议：人工复核或补充更多信息。"

        return result

    def _make_error_result(self, error_code: str, *args: Any) -> Dict[str, Any]:
        """
        构建错误结果

        Args:
            error_code: 错误码（E001-E010）
            *args: 补充参数（用于格式化错误消息）

        Returns:
            错误结果字典
        """
        message_template = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES["E010"])
        if args:
            message = message_template.format(*args)
        else:
            message = message_template

        return {
            "status": "error",
            "error_code": error_code,
            "message": message,
            "app": APP_NAME,
            "version": VERSION,
        }


# ---------------------------------------------------------------------------
# 文件处理辅助函数
# ---------------------------------------------------------------------------
def read_input_file(file_path: str) -> Tuple[Any, Optional[str]]:
    """
    读取输入文件（支持 JSON / 文本）

    Args:
        file_path: 文件路径

    Returns:
        (文件内容, 错误码或None)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, None
    except FileNotFoundError:
        return None, "E007"
    except PermissionError:
        return None, "E007"
    except Exception as e:
        return None, "E010"


def write_output_file(file_path: str, data: Dict[str, Any]) -> Optional[str]:
    """
    写入输出文件

    Args:
        file_path: 输出路径
        data: 要写入的数据

    Returns:
        错误码或None
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            if file_path.endswith(".json"):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                # 文本格式输出
                if data.get("status") == "success":
                    f.write(json.dumps(data.get("data", {}), ensure_ascii=False, indent=2))
                else:
                    f.write(data.get("message", "处理失败"))
        return None
    except Exception:
        return "E009"


# ---------------------------------------------------------------------------
# 自检功能（--selftest）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑

    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。

    Returns:
        True 表示自检通过，False 表示失败
    """
    print("[自检] 开始执行离线自检...")
    processor = BrowserWorkspaceProcessor()

    # 测试用例 1: 有效的 JSON 字符串输入
    print("[自检] 用例 1: JSON 字符串输入")
    test_json = json.dumps({
        "title": "测试文章",
        "content": "这是一段测试内容",
        "url": "https://example.com/test",
        "author": "测试作者",
    })
    result1 = processor.process(test_json)
    assert result1["status"] == "success", "用例 1 失败: 状态应为 success"
    assert result1["confidence"] >= 0.85, "用例 1 失败: 置信度应 >= 0.85"
    assert "title" in result1["data"], "用例 1 失败: 应包含 title 字段"
    print(f"  ✓ 通过 (置信度: {result1['confidence']})")

    # 测试用例 2: 纯文本输入
    print("[自检] 用例 2: 纯文本输入")
    result2 = processor.process("这是一段用于测试的纯文本内容，长度适中。")
    assert result2["status"] == "success", "用例 2 失败: 状态应为 success"
    assert "text" in result2["data"], "用例 2 失败: 应包含 text 字段"
    assert "length" in result2["data"], "用例 2 失败: 应包含 length 字段"
    print(f"  ✓ 通过 (置信度: {result2['confidence']})")

    # 测试用例 3: 空输入
    print("[自检] 用例 3: 空输入")
    result3 = processor.process("")
    assert result3["status"] == "error", "用例 3 失败: 状态应为 error"
    assert result3["error_code"] == "E001", "用例 3 失败: 错误码应为 E001"
    print("  ✓ 通过")

    # 测试用例 4: 列表输入
    print("[自检] 用例 4: 列表输入")
    test_list = [{"name": "item1", "value": 10}, {"name": "item2", "value": 20}]
    result4 = processor.process(test_list)
    assert result4["status"] == "success", "用例 4 失败: 状态应为 success"
    assert "items" in result4["data"], "用例 4 失败: 应包含 items 字段"
    print(f"  ✓ 通过 (置信度: {result4['confidence']})")

    # 测试用例 5: 字典输入（部分字段）
    print("[自检] 用例 5: 字典输入（部分字段）")
    result5 = processor.process({"title": "只有标题"})
    assert result5["status"] == "success", "用例 5 失败: 状态应为 success"
    assert result5["confidence"] < 0.90, "用例 5 失败: 置信度应 < 0.90（字段不完整）"
    print(f"  ✓ 通过 (置信度: {result5['confidence']})")

    # 测试用例 6: 错误码映射
    print("[自检] 用例 6: 错误码映射")
    err_result = processor._make_error_result("E002", "标题")
    assert err_result["error_code"] == "E002", "用例 6 失败: 错误码应为 E002"
    assert "标题" in err_result["message"], "用例 6 失败: 错误消息应包含补充信息"
    print("  ✓ 通过")

    # 测试用例 7: 文件读写（使用临时目录）
    print("[自检] 用例 7: 文件读写（临时目录）")
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入测试
        test_out_path = os.path.join(tmpdir, "test_output.json")
        test_data = {"status": "success", "data": {"test": True}}
        write_err = write_output_file(test_out_path, test_data)
        assert write_err is None, "用例 7 失败: 写入不应返回错误"

        # 读取测试
        content, read_err = read_input_file(test_out_path)
        assert read_err is None, "用例 7 失败: 读取不应返回错误"
        parsed = json.loads(content)
        assert parsed["data"]["test"] is True, "用例 7 失败: 数据应正确解析"
    print("  ✓ 通过")

    # 测试用例 8: 置信度边界（宽松判断）
    print("[自检] 用例 8: 置信度边界")
    high_conf = processor._calculate_confidence({"a": 1, "b": 2, "c": 3, "d": 4})
    assert high_conf >= 0.90, "用例 8 失败: 完整字段应高置信度"
    low_conf = processor._calculate_confidence({})
    assert low_conf < 0.50, "用例 8 失败: 空数据应低置信度"
    print(f"  ✓ 通过 (高: {high_conf}, 低: {low_conf})")

    print("[自检] 全部用例通过 ✓")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """
    主入口函数

    Returns:
        退出码（0 成功，非 0 失败）
    """
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{VERSION} - 本地浏览器工具集（数据处理核心）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（内置样例数据，不依赖外部资源）",
    )
    parser.add_argument(
        "-i", "--input",
        help="输入文件路径（JSON 或文本）",
    )
    parser.add_argument(
        "-d", "--data",
        help="直接输入数据（JSON 字符串或文本）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出文件路径（默认输出到 stdout）",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {VERSION}",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"[自检] 失败: {e}")
            return 1
        except Exception as e:
            print(f"[自检] 异常: {e}")
            return 1

    # 正常处理模式
    processor = BrowserWorkspaceProcessor()

    # 收集输入
    input_data = None
    if args.input:
        # 从文件读取
        content, read_err = read_input_file(args.input)
        if read_err:
            result = processor._make_error_result(read_err, args.input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1
        input_data = content
    elif args.data:
        # 直接使用命令行数据
        input_data = args.data
    else:
        # 尝试从 stdin 读取
        if not sys.stdin.isatty():
            input_data = sys.stdin.read().strip()
        else:
            # 无输入，显示错误
            result = processor._make_error_result("E001")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1

    # 处理数据
    result = processor.process(input_data, args.format)

    # 输出结果
    if args.output:
        write_err = write_output_file(args.output, result)
        if write_err:
            err_result = processor._make_error_result(write_err, args.output)
            print(json.dumps(err_result, ensure_ascii=False, indent=2))
            return 1
        print(f"结果已写入: {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 根据处理状态返回退出码
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
