#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crawlee - 爬虫采集（独立实现）

本脚本根据功能规格独立编写，不参考任何既有实现。
提供核心的数据结构化处理能力，包含离线自检功能。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "输出序列化错误",
    "E008": "参数解析错误",
    "E009": "自检失败",
    "E010": "未知错误",
}


class CrawleeError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心处理逻辑
# ============================================================
class CrawleeProcessor:
    """爬虫采集核心处理器。"""

    # 关键字段识别模式（宽松匹配）
    FIELD_PATTERNS = {
        "url": r"(?:https?://)?[\w\-\.]+\.\w{2,}(?:/\S*)?",
        "email": r"[\w\.\-]+@[\w\-\.]+\.\w{2,}",
        "phone": r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}",
        "date": r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
        "price": r"￥?\d+(?:\.\d{1,2})?元?",
        "name": r"[\u4e00-\u9fa5]{2,8}(?:先生|女士|小姐|同学)?",
    }

    def __init__(self, input_data: Any, output_format: str = "json"):
        """初始化处理器。

        Args:
            input_data: 输入数据（字符串、字典、列表等）
            output_format: 输出格式（json / text）
        """
        self.input_data = input_data
        self.output_format = output_format
        self.confidence = 0.0
        self.extracted: Dict[str, Any] = {}
        self.warnings: List[str] = []

    def process(self) -> Dict[str, Any]:
        """执行核心处理流程。

        Returns:
            处理结果字典，包含结构化数据、置信度和警告信息。
        """
        # 1. 输入校验
        if self.input_data is None or self.input_data == "":
            raise CrawleeError("E001")

        # 2. 解析输入
        try:
            parsed = self._parse_input()
        except ValueError as e:
            raise CrawleeError("E003", str(e))

        # 3. 提取关键信息
        self._extract_fields(parsed)

        # 4. 计算置信度
        self._calculate_confidence(parsed)

        # 5. 生成结果
        result = {
            "status": "success",
            "data": self.extracted,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "format": self.output_format,
        }

        # 6. 置信度标注
        if self.confidence < 85:
            result["flag"] = "[需核实]"
            result["message"] = "结果置信度较低，请人工复核关键字段"
        elif self.confidence < 90:
            result["flag"] = "建议复核"
            result["message"] = "结果置信度中等，建议快速复核"
        else:
            result["flag"] = "直接输出"
            result["message"] = "结果置信度较高，可直接使用"

        return result

    def _parse_input(self) -> Any:
        """解析输入数据，尝试识别 JSON 或其他格式。

        Returns:
            解析后的数据对象。

        Raises:
            ValueError: 当输入格式无法解析时。
        """
        if isinstance(self.input_data, (dict, list, int, float, bool)):
            return self.input_data

        if isinstance(self.input_data, str):
            # 尝试 JSON 解析
            try:
                return json.loads(self.input_data)
            except json.JSONDecodeError:
                pass

            # 尝试多行文本解析（每行一个条目）
            lines = [line.strip() for line in self.input_data.splitlines() if line.strip()]
            if lines:
                return lines

            # 单行文本
            return self.input_data

        # 其他类型
        try:
            return str(self.input_data)
        except Exception:
            raise ValueError("无法识别的输入类型")

    def _extract_fields(self, parsed: Any) -> None:
        """从解析后的数据中提取关键字段。

        Args:
            parsed: 解析后的输入数据。
        """
        # 将数据转为文本进行正则提取
        if isinstance(parsed, dict):
            # 如果已有结构化字段，直接使用
            for key in self.FIELD_PATTERNS:
                if key in parsed:
                    self.extracted[key] = parsed[key]
            text = json.dumps(parsed, ensure_ascii=False)
        elif isinstance(parsed, list):
            items = []
            for item in parsed:
                if isinstance(item, dict):
                    items.append(item)
                else:
                    items.append(str(item))
            self.extracted["items"] = items
            text = json.dumps(parsed, ensure_ascii=False)
        else:
            text = str(parsed)

        # 正则提取关键字段
        for field, pattern in self.FIELD_PATTERNS.items():
            if field not in self.extracted:
                matches = re.findall(pattern, text)
                if matches:
                    # 去重并保留前3个
                    unique_matches = list(dict.fromkeys(matches))[:3]
                    self.extracted[field] = unique_matches if len(unique_matches) > 1 else unique_matches[0]

        # 特殊处理：如果没有识别到任何字段，保留原始文本
        if not self.extracted:
            self.extracted["raw_text"] = text[:200]  # 截断保存

    def _calculate_confidence(self, parsed: Any) -> None:
        """计算处理结果的置信度。

        规则：
        - 基础置信度 80%
        - 提取到关键字段，每个 +5%（上限 95%）
        - 有警告信息，每个 -10%

        Args:
            parsed: 解析后的输入数据。
        """
        base = 80.0

        # 依据提取到的字段数量加分
        field_count = len([k for k in self.extracted.keys() if k != "raw_text"])
        base += min(field_count * 5, 15)  # 最多加15%

        # 依据输入类型调整
        if isinstance(parsed, dict):
            base += 5  # 结构化输入加分
        elif isinstance(parsed, list):
            base += 3

        # 依据输入长度调整
        text_len = len(str(parsed))
        if text_len > 50:
            base += 2

        # 警告扣分
        base -= len(self.warnings) * 10

        # 限制范围
        self.confidence = max(0.0, min(100.0, base))

    def to_output(self, result: Dict[str, Any]) -> str:
        """将结果转换为指定格式的输出。

        Args:
            result: 处理结果字典。

        Returns:
            格式化后的输出字符串。

        Raises:
            CrawleeError: 当输出序列化失败时。
        """
        try:
            if self.output_format == "json":
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif self.output_format == "text":
                # 文本格式输出
                lines = []
                lines.append(f"处理状态: {result['status']}")
                lines.append(f"置信度: {result['confidence']:.1f}%")
                lines.append(f"标注: {result.get('flag', '')}")

                if result.get("message"):
                    lines.append(f"提示: {result['message']}")

                if result["data"]:
                    lines.append("提取结果:")
                    for key, value in result["data"].items():
                        lines.append(f"  {key}: {value}")

                if result["warnings"]:
                    lines.append("警告:")
                    for warning in result["warnings"]:
                        lines.append(f"  - {warning}")

                return "\n".join(lines)
            else:
                raise CrawleeError("E007", f"不支持的输出格式: {self.output_format}")
        except (TypeError, ValueError) as e:
            raise CrawleeError("E007", str(e))


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件或网络。

    Returns:
        True 表示自检通过，否则抛出异常。
    """
    print("=" * 50)
    print("开始自检（内置样例数据）...")
    print("=" * 50)

    # 测试用例 1: 结构化字典输入
    print("\n测试用例 1: 字典输入")
    test_data_1 = {
        "url": "https://example.com/product/123",
        "name": "张三先生",
        "price": 99.5,
    }
    try:
        processor = CrawleeProcessor(test_data_1, "json")
        result = processor.process()
        assert result["status"] == "success", "状态应为 success"
        assert "url" in result["data"], "应提取到 url 字段"
        assert "name" in result["data"], "应提取到 name 字段"
        assert result["confidence"] > 80, f"置信度应大于80，实际: {result['confidence']}"
        assert result["confidence"] <= 100, f"置信度应不超过100，实际: {result['confidence']}"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 2: 文本输入
    print("\n测试用例 2: 文本输入")
    test_data_2 = "联系邮箱: test@example.com, 电话: 138-1234-5678, 日期: 2024-03-15"
    try:
        processor = CrawleeProcessor(test_data_2, "text")
        result = processor.process()
        assert result["status"] == "success", "状态应为 success"
        assert "email" in result["data"], "应提取到 email 字段"
        assert "phone" in result["data"], "应提取到 phone 字段"
        assert "date" in result["data"], "应提取到 date 字段"
        assert result["confidence"] > 75, f"置信度应大于75，实际: {result['confidence']}"
        output = processor.to_output(result)
        assert len(output) > 0, "输出不应为空"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 3: 列表输入
    print("\n测试用例 3: 列表输入")
    test_data_3 = ["item1", "item2", "item3"]
    try:
        processor = CrawleeProcessor(test_data_3, "json")
        result = processor.process()
        assert result["status"] == "success", "状态应为 success"
        assert "items" in result["data"], "应提取到 items 字段"
        assert len(result["data"]["items"]) == 3, "items 数量应为3"
        assert result["confidence"] > 70, f"置信度应大于70，实际: {result['confidence']}"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 4: 空输入（应报错 E001）
    print("\n测试用例 4: 空输入")
    try:
        processor = CrawleeProcessor("", "json")
        processor.process()
        print("  ✗ 失败: 应抛出 E001 错误")
        return False
    except CrawleeError as e:
        assert e.code == "E001", f"错误码应为 E001，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # 测试用例 5: 低置信度标注
    print("\n测试用例 5: 低置信度输入")
    test_data_5 = "abc"  # 无关键信息
    try:
        processor = CrawleeProcessor(test_data_5, "json")
        result = processor.process()
        assert result["confidence"] < 90, f"置信度应小于90，实际: {result['confidence']}"
        assert result["flag"] in ("[需核实]", "建议复核"), f"应标注需要核实，实际: {result['flag']}"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%, 标注: {result['flag']})")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 6: JSON 字符串输入
    print("\n测试用例 6: JSON 字符串输入")
    test_data_6 = '{"name": "李四", "url": "https://example.org"}'
    try:
        processor = CrawleeProcessor(test_data_6, "json")
        result = processor.process()
        assert result["status"] == "success", "状态应为 success"
        assert "name" in result["data"], "应提取到 name 字段"
        assert "url" in result["data"], "应提取到 url 字段"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 7: 输出格式验证
    print("\n测试用例 7: 输出格式")
    try:
        processor = CrawleeProcessor({"test": "data"}, "json")
        result = processor.process()
        json_output = processor.to_output(result)
        # 验证 JSON 可解析
        parsed_output = json.loads(json_output)
        assert parsed_output["status"] == "success", "JSON 输出应包含 status 字段"
        print("  ✓ JSON 输出格式正确")

        processor2 = CrawleeProcessor({"test": "data"}, "text")
        result2 = processor2.process()
        text_output = processor2.to_output(result2)
        assert "处理状态" in text_output, "文本输出应包含状态信息"
        print("  ✓ 文本输出格式正确")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 8: 批量处理
    print("\n测试用例 8: 批量处理")
    batch_data = [
        {"url": "https://example.com/1"},
        {"url": "https://example.com/2"},
        {"url": "https://example.com/3"},
    ]
    try:
        results = []
        for item in batch_data:
            processor = CrawleeProcessor(item, "json")
            results.append(processor.process())
        assert len(results) == 3, f"应处理3条数据，实际: {len(results)}"
        for r in results:
            assert r["status"] == "success", "每条处理都应成功"
        print(f"  ✓ 通过 (处理 {len(results)} 条数据)")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    # 测试用例 9: 自定义输出格式错误
    print("\n测试用例 9: 不支持的输出格式")
    try:
        processor = CrawleeProcessor("test", "xml")
        result = processor.process()
        processor.to_output(result)
        print("  ✗ 失败: 应抛出 E007 错误")
        return False
    except CrawleeError as e:
        assert e.code == "E007", f"错误码应为 E007，实际: {e.code}"
        print(f"  ✓ 通过 (错误码: {e.code})")

    # 测试用例 10: 高置信度输入
    print("\n测试用例 10: 高置信度输入")
    test_data_10 = {
        "url": "https://example.com/page",
        "name": "王五先生",
        "email": "wangwu@example.com",
        "phone": "139-1234-5678",
        "date": "2024-06-01",
        "price": 199.99,
    }
    try:
        processor = CrawleeProcessor(test_data_10, "json")
        result = processor.process()
        assert result["confidence"] >= 90, f"置信度应大于等于90，实际: {result['confidence']}"
        assert result["flag"] == "直接输出", f"应直接输出，实际: {result['flag']}"
        assert len(result["data"]) >= 5, f"应提取至少5个字段，实际: {len(result['data'])}"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%, 字段数: {len(result['data'])})")
    except CrawleeError as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 50)
    print("全部自检通过！")
    print("=" * 50)
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。

    Returns:
        退出码（0 成功，非 0 失败）。
    """
    parser = argparse.ArgumentParser(
        description="crawlee - 爬虫采集工具",
        epilog="示例: python main.py --input 'https://example.com' --format json",
    )
    parser.add_argument("--input", "-i", help="输入数据（文本、JSON 字符串或文件路径）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--file", help="从文件读取输入")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse 解析失败
        print(f"[E008] 参数解析错误: {e}")
        return 1

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Exception as e:
            print(f"[E009] 自检失败: {e}")
            return 1

    # 正常处理模式
    try:
        # 获取输入
        if args.file:
            # 从文件读取
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except FileNotFoundError:
                print("[E001] 输入文件不存在")
                return 1
            except Exception as e:
                print(f"[E010] 读取文件失败: {e}")
                return 1
        elif args.input:
            input_data = args.input
        else:
            # 从标准输入读取
            print("请输入数据（输入空行结束）:")
            lines = []
            try:
                while True:
                    line = sys.stdin.readline()
                    if not line or line.strip() == "":
                        break
                    lines.append(line.strip())
            except KeyboardInterrupt:
                print("\n[E001] 输入被中断")
                return 1

            if not lines:
                print("[E001] 输入为空")
                return 1
            input_data = "\n".join(lines) if len(lines) > 1 else lines[0]

        # 处理数据
        processor = CrawleeProcessor(input_data, args.format)
        result = processor.process()

        # 输出结果
        output = processor.to_output(result)
        print(output)

        # 根据置信度返回适当的退出码
        if result["confidence"] < 85:
            return 2  # 低置信度
        return 0

    except CrawleeError as e:
        print(f"{e}")
        return 1
    except Exception as e:
        print(f"[E010] 未知错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
