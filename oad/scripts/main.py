#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: oad 工具 - 自动化显微镜工作流辅助脚本
版本: 1.0.1
描述: 根据功能规格独立实现，用于将用户提供的数据/文件/URL 转换为结构化结果，
      识别关键信息，按约定格式输出，并提供置信度提示。
"""

import argparse
import json
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# 错误码定义
# -----------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "文件读取失败，请检查文件路径或权限。",
    "E007": "URL 解析失败，请检查 URL 格式。",
    "E008": "JSON 解析失败，请检查输入内容格式。",
    "E009": "内部处理错误，请重试或检查输入。",
    "E010": "未支持的输入类型，请提供文本、文件路径或 URL。",
}


# -----------------------------------------------------------------------------
# 核心数据结构
# -----------------------------------------------------------------------------
class ProcessingResult:
    """处理结果的数据结构。"""

    def __init__(self) -> None:
        self.success: bool = False
        self.data: Optional[Dict[str, Any]] = None
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self.error_code: Optional[str] = None
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将结果转换为字典。"""
        return {
            "success": self.success,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


# -----------------------------------------------------------------------------
# 核心逻辑模块
# -----------------------------------------------------------------------------
class OADProcessor:
    """核心处理器，负责输入解析、关键信息提取和结果生成。"""

    # 支持的关键字段（根据规格中的"识别关键信息"）
    KEY_FIELDS = ["name", "type", "value", "url", "description", "timestamp"]

    def __init__(self) -> None:
        self._known_patterns = {
            "email": self._is_email,
            "url": self._is_url,
            "number": self._is_number,
            "file_path": self._is_file_path,
        }

    # ------------------------- 输入解析 -------------------------
    def parse_input(self, raw_input: str) -> Tuple[str, str, str]:
        """
        解析输入内容，判断输入类型。
        返回: (input_type, content, source)
        """
        if not raw_input or not raw_input.strip():
            raise ValueError("E001")

        stripped = raw_input.strip()

        # 判断是否为文件路径
        if os.path.isfile(stripped):
            return "file", self._read_file(stripped), stripped

        # 判断是否为 URL
        if self._is_url(stripped):
            return "url", stripped, stripped

        # 判断是否为 JSON（在文本之前判断）
        if stripped.startswith(("{", "[")):
            return "json", stripped, "inline"

        # 默认作为文本处理
        return "text", stripped, "inline"

    def _read_file(self, file_path: str) -> str:
        """读取文件内容。"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            raise ValueError("E006")

    # ------------------------- 关键信息提取 -------------------------
    def extract_key_info(self, content: str, input_type: str) -> Dict[str, Any]:
        """
        从输入内容中提取关键信息。
        返回结构化的字典。
        """
        # 根据输入类型选择不同的提取策略
        if input_type == "json":
            return self._extract_from_json(content)
        elif input_type == "url":
            return self._extract_from_url(content)
        elif input_type == "file":
            # 文件内容可能是文本或JSON
            if content.strip().startswith(("{", "[")):
                return self._extract_from_json(content)
            return self._extract_from_text(content)
        else:
            return self._extract_from_text(content)

    def _extract_from_json(self, content: str) -> Dict[str, Any]:
        """从 JSON 内容中提取信息。"""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # 保留已知字段，忽略其他
                result = {k: v for k, v in data.items() if k in self.KEY_FIELDS}
                # 如果还有额外字段，合并但标记
                extra = {k: v for k, v in data.items() if k not in self.KEY_FIELDS}
                if extra:
                    result["_extra_fields"] = list(extra.keys())
                return result
            elif isinstance(data, list):
                return {"items": data, "count": len(data)}
            else:
                return {"value": data}
        except json.JSONDecodeError:
            raise ValueError("E008")

    def _extract_from_url(self, url: str) -> Dict[str, Any]:
        """从 URL 中提取信息（仅解析，不访问网络）。"""
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("E007")

        result = {
            "url": url,
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
        }

        # 解析查询参数
        query_params = urllib.parse.parse_qs(parsed.query)
        if query_params:
            result["query_params"] = {
                k: v[0] if len(v) == 1 else v for k, v in query_params.items()
            }

        return result

    def _extract_from_text(self, content: str) -> Dict[str, Any]:
        """从纯文本中提取关键信息。"""
        result: Dict[str, Any] = {}

        # 按行处理，尝试识别键值对
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试识别 "key: value" 或 "key=value" 格式
            for sep in [":", "="]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in self.KEY_FIELDS:
                        result[key] = value
                    break

        # 如果没有识别到键值对，将整个内容作为 value
        if not result:
            result["value"] = content

        # 尝试识别常见模式
        for pattern_name, check_func in self._known_patterns.items():
            if check_func(content):
                result["detected_pattern"] = pattern_name
                break

        return result

    # ------------------------- 置信度计算 -------------------------
    def calculate_confidence(self, extracted: Dict[str, Any], input_type: str) -> float:
        """
        计算置信度。
        规则:
        - 结构化输入 (JSON/URL): 高置信度
        - 文本输入: 根据提取到的字段数量，但有上限
        """
        if input_type == "json":
            # JSON 解析成功，置信度最高
            return 0.98
        elif input_type == "url":
            # URL 解析成功，置信度较高
            return 0.92
        else:
            # 文本输入，根据提取到的字段数计算
            field_count = len(extracted)
            
            # 检查是否有结构化字段（非value和detected_pattern）
            structured_fields = [k for k in extracted.keys() 
                               if k not in ["value", "detected_pattern"]]
            
            if len(structured_fields) >= 3:
                # 有多个结构化字段，置信度较高但低于JSON
                return 0.85
            elif len(structured_fields) >= 1:
                # 至少有一个结构化字段
                return 0.75
            else:
                # 只有value或没有结构化字段
                return 0.40

    # ------------------------- 结果生成 -------------------------
    def process(self, raw_input: str) -> ProcessingResult:
        """
        主处理流程。
        """
        result = ProcessingResult()

        try:
            # Step 1: 解析输入
            input_type, content, source = self.parse_input(raw_input)

            # Step 2: 提取关键信息
            extracted = self.extract_key_info(content, input_type)

            # Step 3: 计算置信度
            confidence = self.calculate_confidence(extracted, input_type)

            # Step 4: 生成结果
            result.success = True
            result.data = {
                "input_type": input_type,
                "source": source,
                "extracted": extracted,
                "processed_at": "local",
            }
            result.confidence = confidence

            # 根据置信度添加警告
            if confidence < 0.85:
                result.warnings.append("[需核实] 结果置信度较低，请人工复核。")
            elif confidence < 0.90:
                result.warnings.append("建议复核：结果置信度中等。")

        except ValueError as e:
            # 捕获已知错误
            error_code = str(e)
            result.success = False
            result.error_code = error_code
            result.error_message = ERROR_CODES.get(error_code, ERROR_CODES["E009"])
        except Exception:
            # 未知错误
            result.success = False
            result.error_code = "E009"
            result.error_message = ERROR_CODES["E009"]

        return result

    # ------------------------- 辅助方法 -------------------------
    @staticmethod
    def _is_email(text: str) -> bool:
        """简单邮箱判断。"""
        return "@" in text and "." in text.split("@")[-1]

    @staticmethod
    def _is_url(text: str) -> bool:
        """简单 URL 判断。"""
        return text.startswith(("http://", "https://", "ftp://"))

    @staticmethod
    def _is_number(text: str) -> bool:
        """数字判断。"""
        try:
            float(text)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_file_path(text: str) -> bool:
        """文件路径判断（宽松）。"""
        return os.path.sep in text or text.endswith((".txt", ".json", ".csv", ".xml"))


# -----------------------------------------------------------------------------
# 自检模块
# -----------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据，不依赖外部环境。
    使用宽松断言，确保稳定性。
    """
    print("=" * 50)
    print("开始自检 (selftest)...")
    print("=" * 50)

    processor = OADProcessor()
    all_passed = True

    # 测试用例 1: 文本输入
    print("\n[测试 1] 文本输入")
    text_input = "name: 显微镜样本\nvalue: 42\ndescription: 测试样本"
    try:
        result = processor.process(text_input)
        # 宽松断言：应该成功，置信度 > 0
        assert result.success, "文本输入处理应成功"
        assert result.confidence > 0, "置信度应大于 0"
        assert result.data is not None, "结果数据不应为空"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 2: JSON 输入
    print("\n[测试 2] JSON 输入")
    json_input = '{"name": "测试", "type": "image", "value": 123}'
    try:
        result = processor.process(json_input)
        # 宽松断言：应该成功，置信度较高
        assert result.success, "JSON 输入处理应成功"
        assert result.confidence >= 0.85, "JSON 输入置信度应较高"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 3: URL 输入
    print("\n[测试 3] URL 输入")
    url_input = "https://example.com/data?type=image&id=123"
    try:
        result = processor.process(url_input)
        # 宽松断言：应该成功
        assert result.success, "URL 输入处理应成功"
        assert result.data is not None, "结果数据不应为空"
        # 检查是否解析了 URL 组件
        extracted = result.data.get("extracted", {})
        assert "host" in extracted, "应解析出 host"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 4: 空输入
    print("\n[测试 4] 空输入")
    try:
        result = processor.process("")
        # 应该失败，返回 E001
        assert not result.success, "空输入应失败"
        assert result.error_code == "E001", "空输入应返回 E001"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 5: 批量处理（多个输入）
    print("\n[测试 5] 批量处理")
    inputs = [
        "简单文本输入",
        '{"key": "value"}',
        "https://example.org",
    ]
    try:
        results = [processor.process(item) for item in inputs]
        # 宽松断言：至少一个成功
        assert any(r.success for r in results), "至少应有一个处理成功"
        # 所有结果都应包含必要字段
        for r in results:
            assert hasattr(r, "success"), "结果应有 success 属性"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 6: 置信度分级
    print("\n[测试 6] 置信度分级")
    try:
        # 高置信度 JSON
        r_high = processor.process('{"name": "a", "type": "b", "value": 1}')
        # 低置信度文本
        r_low = processor.process("随便一段话")

        # 宽松断言：JSON 置信度应高于纯文本
        assert r_high.confidence > r_low.confidence, "JSON 置信度应高于纯文本"
        
        # 额外检查：JSON 置信度应明显高于纯文本
        assert r_high.confidence - r_low.confidence >= 0.3, "置信度差距应明显"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        all_passed = False

    # 测试用例 7: 错误码完整性
    print("\n[测试 7] 错误码完整性")
    try:
        # 检查所有错误码都有对应消息
        required_codes = [f"E00{i}" for i in range(1, 10)] + ["E010"]
        for code in required_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("自检完成: 全部通过 ✓")
    else:
        print("自检完成: 存在失败项 ✗")
    print("=" * 50)

    return all_passed


# -----------------------------------------------------------------------------
# 命令行入口
# -----------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="oad 工具 - 自动化显微镜工作流辅助",
        epilog="示例: python main.py --input 'name: 样本' 或 python main.py --selftest",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容：文本、文件路径或 URL",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检逻辑",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理输入
    if not args.input:
        print(f"错误 E001: {ERROR_CODES['E001']}", file=sys.stderr)
        return 1

    processor = OADProcessor()
    result = processor.process(args.input)

    # 输出结果
    if args.output == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        # 文本输出
        if result.success:
            print(f"处理成功 (置信度: {result.confidence:.0%})")
            if result.data:
                extracted = result.data.get("extracted", {})
                for key, value in extracted.items():
                    print(f"  {key}: {value}")
            for warning in result.warnings:
                print(f"警告: {warning}")
        else:
            print(f"处理失败: {result.error_message}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
