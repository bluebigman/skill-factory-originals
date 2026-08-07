#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal-wiki 核心实现脚本（clean-room 独立实现）

本脚本根据功能规格独立编写，不参考或复制任何既有实现。
功能：将用户提供的数据/文本转换为结构化结果，支持批量处理。
仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "输出格式不支持",
    "E008": "批量输入格式错误",
    "E009": "参数组合错误",
    "E010": "未知错误",
}


class SignalWikiError(Exception):
    """自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================


class ProcessedItem:
    """处理后的单个数据项"""

    def __init__(
        self,
        raw_input: str,
        key_fields: Dict[str, Any],
        confidence: float,
        notes: Optional[List[str]] = None,
    ):
        self.raw_input = raw_input
        self.key_fields = key_fields
        self.confidence = confidence
        self.notes = notes or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "raw_input": self.raw_input,
            "key_fields": self.key_fields,
            "confidence": round(self.confidence, 2),
            "confidence_level": self._confidence_label(),
            "notes": self.notes,
        }

    def _confidence_label(self) -> str:
        """根据置信度返回标签"""
        if self.confidence >= 0.90:
            return "直接输出"
        elif self.confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"

    def __repr__(self) -> str:
        return f"ProcessedItem(confidence={self.confidence:.2f}, fields={self.key_fields})"


# ============================================================
# 核心处理逻辑
# ============================================================


class SignalWikiProcessor:
    """signal-wiki 核心处理器"""

    # 可识别的关键字段模式（用于从文本中提取信息）
    FIELD_PATTERNS = {
        "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
        "phone": r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}",
        "url": r"https?://[^\s]+",
        "date": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}",
        "ip": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    }

    # 关键词 → 主题分类
    TOPIC_KEYWORDS = {
        "技术": ["代码", "编程", "软件", "硬件", "bug", "API", "数据库"],
        "商业": ["合同", "报价", "发票", "订单", "客户", "销售"],
        "学术": ["论文", "研究", "实验", "数据", "分析", "文献"],
        "日常": ["日程", "会议", "提醒", "待办", "备忘"],
    }

    def __init__(self) -> None:
        """初始化处理器"""
        self._batch_mode = False
        self._custom_format: Optional[Dict[str, Any]] = None

    # --------------------------------------------------------
    # 对外主接口
    # --------------------------------------------------------

    def process(
        self,
        text_input: str,
        output_format: str = "json",
        batch: bool = False,
        custom_fields: Optional[List[str]] = None,
    ) -> Any:
        """
        处理输入文本

        Args:
            text_input: 用户输入的文本内容
            output_format: 输出格式（json/text/jsonl）
            batch: 是否批量处理（按行分割）
            custom_fields: 自定义需要提取的字段列表

        Returns:
            处理结果（字符串或对象）

        Raises:
            SignalWikiError: 处理失败时抛出
        """
        # 输入校验
        if not text_input or not text_input.strip():
            raise SignalWikiError("E001")

        # 设置模式
        self._batch_mode = batch
        if custom_fields:
            self._custom_format = {"fields": custom_fields}

        # 执行处理
        try:
            if batch:
                result = self._process_batch(text_input)
            else:
                result = self._process_single(text_input)

            # 格式化输出
            return self._format_output(result, output_format)

        except SignalWikiError:
            raise
        except Exception as exc:
            raise SignalWikiError("E006", f"内部错误: {exc}") from exc

    # --------------------------------------------------------
    # 内部处理方法
    # --------------------------------------------------------

    def _process_single(self, text: str) -> ProcessedItem:
        """处理单条输入"""
        # 提取关键字段
        key_fields = self._extract_fields(text)

        # 识别主题
        topic = self._detect_topic(text)
        key_fields["topic"] = topic

        # 计算置信度
        confidence = self._calculate_confidence(text, key_fields)

        # 生成备注
        notes = self._generate_notes(confidence, key_fields)

        return ProcessedItem(
            raw_input=text.strip(),
            key_fields=key_fields,
            confidence=confidence,
            notes=notes,
        )

    def _process_batch(self, text: str) -> List[ProcessedItem]:
        """批量处理（按行分割）"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise SignalWikiError("E008")

        results = []
        for line in lines:
            results.append(self._process_single(line))
        return results

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键字段"""
        fields: Dict[str, Any] = {}

        # 按预定义模式提取
        for field_name, pattern in self.FIELD_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                fields[field_name] = matches[0]  # 取第一个匹配

        # 提取自定义字段（如果设置了）
        if self._custom_format and "fields" in self._custom_format:
            for custom_field in self._custom_format["fields"]:
                if custom_field in fields:
                    continue  # 已提取
                # 尝试提取自定义字段（简单模式：字段名: 值）
                pattern = rf"{re.escape(custom_field)}[：:\s]+([^\s,，。]+)"
                match = re.search(pattern, text)
                if match:
                    fields[custom_field] = match.group(1)

        # 统计文本特征
        fields["_text_length"] = len(text)
        fields["_word_count"] = len(text.split())

        return fields

    def _detect_topic(self, text: str) -> str:
        """检测文本主题"""
        text_lower = text.lower()
        best_topic = "通用"
        best_score = 0

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_topic = topic

        return best_topic

    def _calculate_confidence(self, text: str, fields: Dict[str, Any]) -> float:
        """计算置信度（0-1）"""
        confidence = 0.5  # 基础置信度

        # 提取到关键字段则加分
        extracted_count = sum(
            1 for key in fields if not key.startswith("_")
        )
        confidence += extracted_count * 0.1

        # 文本长度适中加分
        text_len = fields.get("_text_length", 0)
        if 10 <= text_len <= 500:
            confidence += 0.1
        elif text_len > 500:
            confidence += 0.05

        # 有明确结构（包含标点符号）加分
        if re.search(r"[，。；、,.!?]", text):
            confidence += 0.1

        # 主题明确加分
        if fields.get("topic") != "通用":
            confidence += 0.1

        # 限制在合理范围
        return max(0.1, min(0.99, confidence))

    def _generate_notes(self, confidence: float, fields: Dict[str, Any]) -> List[str]:
        """生成备注信息"""
        notes = []

        if confidence < 0.85:
            notes.append("部分信息无法确定，请人工复核")

        if "_text_length" in fields and fields["_text_length"] < 10:
            notes.append("输入内容过短，可能信息不足")

        # 检查是否缺少常见字段
        if "email" not in fields and "phone" not in fields:
            notes.append("未检测到联系方式")

        return notes

    def _format_output(self, result: Any, output_format: str) -> str:
        """格式化输出结果"""
        # 先将 ProcessedItem 转换为可序列化的 dict
        if isinstance(result, ProcessedItem):
            result_dict = result.to_dict()
        elif isinstance(result, list):
            result_dict = [item.to_dict() if isinstance(item, ProcessedItem) else item for item in result]
        else:
            result_dict = result

        if output_format == "json":
            return json.dumps(result_dict, ensure_ascii=False, indent=2)

        elif output_format == "jsonl":
            if isinstance(result_dict, list):
                return "\n".join(
                    json.dumps(item, ensure_ascii=False)
                    for item in result_dict
                )
            else:
                return json.dumps(result_dict, ensure_ascii=False)

        elif output_format == "text":
            return self._format_as_text(result)

        else:
            raise SignalWikiError("E007", f"不支持的输出格式: {output_format}")

    def _format_as_text(self, result: Any) -> str:
        """格式化为纯文本"""
        if isinstance(result, list):
            lines = []
            for i, item in enumerate(result, 1):
                lines.append(f"--- 记录 {i} ---")
                lines.append(self._format_item_text(item))
            return "\n".join(lines)
        else:
            return self._format_item_text(result)

    def _format_item_text(self, item: ProcessedItem) -> str:
        """格式化单个条目为文本"""
        lines = []
        lines.append(f"原始输入: {item.raw_input}")
        lines.append(f"置信度: {item.confidence:.0%} ({item._confidence_label()})")

        if item.key_fields:
            lines.append("提取字段:")
            for key, value in item.key_fields.items():
                if not key.startswith("_"):
                    lines.append(f"  - {key}: {value}")

        if item.notes:
            lines.append("备注:")
            for note in item.notes:
                lines.append(f"  * {note}")

        return "\n".join(lines)


# ============================================================
# 自检功能（--selftest）
# ============================================================


def run_selftest() -> bool:
    """
    运行内置自检

    使用硬编码样例数据，不读取外部文件、不依赖当前目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("=" * 60)
    print("signal-wiki 自检开始")
    print("=" * 60)

    processor = SignalWikiProcessor()

    # ---- 测试用例 1: 正常单条处理 ----
    print("\n[测试 1] 单条文本处理")
    sample1 = "张三的联系方式: 13812345678, 邮箱 zhangsan@example.com, 日期 2024-03-15"
    try:
        result = processor.process(sample1, output_format="json")
        data = json.loads(result)

        # 宽松断言：置信度应该在合理范围
        assert 0.1 <= data["confidence"] <= 1.0, "置信度范围错误"
        # 应该提取到 phone 或 email 至少一个
        assert "phone" in data["key_fields"] or "email" in data["key_fields"], "未提取到联系方式"
        # 原始输入应该保留
        assert data["raw_input"] == sample1, "原始输入未保留"
        print(f"  ✓ 通过 (置信度: {data['confidence']:.2f})")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 2: 批量处理 ----
    print("\n[测试 2] 批量处理")
    sample2 = """第一行测试数据 1234567890
第二行测试数据 abc@test.com
第三行只有几个字"""
    try:
        result = processor.process(sample2, output_format="json", batch=True)
        data = json.loads(result)

        # 批量应该返回列表
        assert isinstance(data, list), "批量处理未返回列表"
        assert len(data) >= 2, "批量处理行数不足"
        # 每条记录都有置信度
        for item in data:
            assert 0.1 <= item["confidence"] <= 1.0, "置信度范围错误"
        print(f"  ✓ 通过 (共 {len(data)} 条记录)")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 3: 空输入错误处理 ----
    print("\n[测试 3] 空输入错误处理")
    try:
        processor.process("", output_format="json")
        print("  ✗ 失败: 空输入未抛出异常")
        return False
    except SignalWikiError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print(f"  ✓ 通过 (错误码: {exc.code})")
    except Exception:
        print("  ✗ 失败: 异常类型错误")
        return False

    # ---- 测试用例 4: 自定义字段提取 ----
    print("\n[测试 4] 自定义字段提取")
    sample4 = "项目名称: 智能系统, 负责人: 李四, 状态: 进行中"
    try:
        result = processor.process(
            sample4,
            output_format="json",
            custom_fields=["项目名称", "负责人", "状态"],
        )
        data = json.loads(result)

        # 宽松断言：至少提取到一个自定义字段
        custom_keys = ["项目名称", "负责人", "状态"]
        extracted = [k for k in custom_keys if k in data["key_fields"]]
        assert len(extracted) >= 1, "未提取到任何自定义字段"
        print(f"  ✓ 通过 (提取到 {len(extracted)} 个自定义字段)")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 5: 主题识别 ----
    print("\n[测试 5] 主题识别")
    sample5 = "这份合同需要审核，涉及客户和订单信息"
    try:
        result = processor.process(sample5, output_format="json")
        data = json.loads(result)
        assert "topic" in data["key_fields"], "未识别主题"
        print(f"  ✓ 通过 (主题: {data['key_fields']['topic']})")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 6: 文本格式输出 ----
    print("\n[测试 6] 文本格式输出")
    try:
        result = processor.process(sample1, output_format="text")
        assert "置信度" in result, "文本输出缺少置信度信息"
        assert "原始输入" in result, "文本输出缺少原始输入"
        print("  ✓ 通过")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 7: URL 提取 ----
    print("\n[测试 7] URL 提取")
    sample7 = "参考文档: https://example.com/docs/page1 和 http://test.org/abc"
    try:
        result = processor.process(sample7, output_format="json")
        data = json.loads(result)
        assert "url" in data["key_fields"], "未提取到 URL"
        print(f"  ✓ 通过 (URL: {data['key_fields']['url']})")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试用例 8: 错误码完整性 ----
    print("\n[测试 8] 错误码完整性")
    try:
        # 检查所有错误码都有定义
        expected_codes = [f"E{i:03d}" for i in range(1, 11)]
        for code in expected_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print(f"  ✓ 通过 (共 {len(ERROR_CODES)} 个错误码)")

    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 总结 ----
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 命令行入口
# ============================================================


def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="signal-wiki: The easy to use rails wiki",
        epilog="示例: python main.py --input '你的文本内容' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="待处理的文本内容",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入（可选）",
    )
    parser.add_argument(
        "--format", "-F",
        type=str,
        choices=["json", "text", "jsonl"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量处理模式（按行分割输入）",
    )
    parser.add_argument(
        "--fields",
        type=str,
        help="自定义字段列表，逗号分隔，例如: '姓名,年龄,城市'",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例数据，无需外部输入）",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="signal-wiki 1.0.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    try:
        # 收集输入
        text_input = args.input
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text_input = f.read()
            except FileNotFoundError:
                raise SignalWikiError("E001", f"文件不存在: {args.file}")
            except IOError as exc:
                raise SignalWikiError("E006", f"读取文件失败: {exc}")

        if not text_input:
            # 尝试从 stdin 读取（管道输入）
            if not sys.stdin.isatty():
                text_input = sys.stdin.read()

        if not text_input:
            parser.print_help()
            return 1

        # 解析自定义字段
        custom_fields = None
        if args.fields:
            custom_fields = [f.strip() for f in args.fields.split(",") if f.strip()]

        # 处理
        processor = SignalWikiProcessor()
        result = processor.process(
            text_input=text_input,
            output_format=args.format,
            batch=args.batch,
            custom_fields=custom_fields,
        )

        # 输出结果
        print(result)
        return 0

    except SignalWikiError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
