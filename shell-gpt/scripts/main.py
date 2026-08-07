#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shell-gpt 技能实现脚本（clean-room 重写）

仅依据功能规格独立实现，不复制任何既有代码。
标准库实现，无第三方依赖。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

用法示例：
    python main.py --input "姓名:张三 年龄:30 城市:北京"
    python main.py --batch "文件1,文件2,文件3" --format json
    python main.py --selftest
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class ProcessedItem:
    """单条处理结果"""

    source: str  # 输入来源（原文/文件路径/URL）
    source_type: str  # 类型：text / file / url
    key_fields: Dict[str, str]  # 提取的关键字段
    confidence: float  # 置信度 0-100
    note: str = ""  # 备注（如：[需核实]）
    raw_output: str = ""  # 格式化后的输出


@dataclass
class ProcessingResult:
    """批量处理结果"""

    items: List[ProcessedItem] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (错误码, 说明)

    def add_item(self, item: ProcessedItem) -> None:
        self.items.append(item)

    def add_error(self, code: str, detail: str = "") -> None:
        self.errors.append((code, detail))

    @property
    def success_count(self) -> int:
        return len(self.items)

    @property
    def error_count(self) -> int:
        return len(self.errors)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class CoreProcessor:
    """核心处理器：解析输入、提取字段、计算置信度、生成输出"""

    # 常见的关键字段模式（用于识别键值对）
    FIELD_PATTERNS = [
        re.compile(r"(?P<key>姓名|名字|name)\s*[:：]\s*(?P<value>[^\s,，;；]+)"),
        re.compile(r"(?P<key>年龄|年纪|age)\s*[:：]\s*(?P<value>\d+)"),
        re.compile(r"(?P<key>城市|城市名|city)\s*[:：]\s*(?P<value>[^\s,，;；]+)"),
        re.compile(r"(?P<key>邮箱|email|邮件)\s*[:：]\s*(?P<value>[^\s,，;；]+@[^\s,，;；]+)"),
        re.compile(r"(?P<key>电话|手机|phone)\s*[:：]\s*(?P<value>\d{6,15})"),
        re.compile(r"(?P<key>地址|address)\s*[:：]\s*(?P<value>[^\s,，;；]+)"),
        re.compile(r"(?P<key>日期|date)\s*[:：]\s*(?P<value>\d{4}[-/]\d{1,2}[-/]\d{1,2})"),
    ]

    # 通用键值对模式（兜底）
    GENERIC_KEY_VALUE = re.compile(
        r"(?P<key>[^\s:=：]+)\s*[:=：]\s*(?P<value>[^\s,，;；]+)"
    )

    # 支持的字段白名单（用于判断关键信息）
    KNOWN_KEYS = {"姓名", "名字", "name", "年龄", "age", "城市", "city",
                  "邮箱", "email", "电话", "phone", "地址", "address", "日期", "date"}

    # 输出模板
    DEFAULT_TEMPLATE = "字段: {fields} | 置信度: {confidence}% {note}"

    def __init__(self, custom_template: str = ""):
        self.template = custom_template or self.DEFAULT_TEMPLATE

    # ------------------------------------------------------------------
    # 输入解析
    # ------------------------------------------------------------------
    def parse_input(self, raw_input: str) -> Tuple[str, str, str]:
        """
        解析输入内容，返回 (来源类型, 实际内容, 来源标识)

        支持三种形式：
            1. 纯文本：直接作为文本处理
            2. 文件路径：读取文件内容（若文件存在）
            3. URL：解析 URL 参数（不访问网络）
        """
        if not raw_input or not raw_input.strip():
            raise SkillError("E001")

        stripped = raw_input.strip()

        # 判断是否为文件路径
        if os.path.isfile(stripped):
            try:
                with open(stripped, "r", encoding="utf-8") as f:
                    content = f.read()
                return "file", content, stripped
            except (IOError, OSError) as e:
                raise SkillError("E003", f"文件读取失败: {e}")

        # 判断是否为 URL（仅解析，不访问网络）
        if stripped.startswith(("http://", "https://", "ftp://")):
            parsed = urllib.parse.urlparse(stripped)
            query_params = urllib.parse.parse_qs(parsed.query)
            # 将 URL 参数转换为文本形式
            param_text = " ".join(f"{k}:{v[0]}" for k, v in query_params.items())
            if not param_text:
                # 无参数时，使用路径最后一段作为内容
                path_part = parsed.path.split("/")[-1] if parsed.path else ""
                param_text = path_part
            return "url", param_text, stripped

        # 默认为纯文本
        return "text", stripped, stripped

    # ------------------------------------------------------------------
    # 关键字段提取
    # ------------------------------------------------------------------
    def extract_fields(self, content: str) -> Dict[str, str]:
        """从文本中提取关键字段"""
        fields: Dict[str, str] = {}

        # 先尝试特定模式
        for pattern in self.FIELD_PATTERNS:
            for match in pattern.finditer(content):
                key = match.group("key").lower()
                value = match.group("value").strip()
                # 统一键名
                normalized_key = self._normalize_key(key)
                if normalized_key and normalized_key not in fields:
                    fields[normalized_key] = value

        # 若特定模式未命中，使用通用模式
        if not fields:
            for match in self.GENERIC_KEY_VALUE.finditer(content):
                key = match.group("key").strip()
                value = match.group("value").strip()
                normalized_key = self._normalize_key(key)
                if normalized_key and normalized_key not in fields:
                    fields[normalized_key] = value

        return fields

    def _normalize_key(self, key: str) -> Optional[str]:
        """标准化字段名"""
        key_lower = key.lower().strip()
        # 同义词映射
        synonyms = {
            "姓名": "姓名", "名字": "姓名", "name": "姓名",
            "年龄": "年龄", "年纪": "年龄", "age": "年龄",
            "城市": "城市", "city": "城市",
            "邮箱": "邮箱", "email": "邮箱", "邮件": "邮箱",
            "电话": "电话", "手机": "电话", "phone": "电话",
            "地址": "地址", "address": "地址",
            "日期": "日期", "date": "日期",
        }
        return synonyms.get(key_lower, key_lower if key_lower in self.KNOWN_KEYS else None)

    # ------------------------------------------------------------------
    # 置信度计算
    # ------------------------------------------------------------------
    def compute_confidence(self, content: str, fields: Dict[str, str]) -> float:
        """
        根据字段提取完整度计算置信度
        规则：
            - 提取到 ≥3 个关键字段：90%
            - 提取到 2 个关键字段：85%
            - 提取到 1 个关键字段：70%
            - 未提取到字段：50%
        """
        field_count = len(fields)
        if field_count >= 3:
            return 90.0
        elif field_count == 2:
            return 85.0
        elif field_count == 1:
            return 70.0
        else:
            return 50.0

    # ------------------------------------------------------------------
    # 输出生成
    # ------------------------------------------------------------------
    def generate_output(self, item: ProcessedItem) -> str:
        """根据模板生成输出文本"""
        fields_str = ", ".join(f"{k}:{v}" for k, v in item.key_fields.items())
        note = item.note
        if item.confidence < 85:
            note = "[需核实]" + (note or "")
        elif item.confidence < 90:
            note = "建议复核"

        return self.template.format(
            fields=fields_str,
            confidence=item.confidence,
            note=note,
        )

    # ------------------------------------------------------------------
    # 主处理流程
    # ------------------------------------------------------------------
    def process(self, raw_input: str, custom_format: str = "") -> ProcessedItem:
        """
        处理单个输入，返回处理结果

        参数：
            raw_input: 原始输入（文本/文件路径/URL）
            custom_format: 自定义输出格式（预留，当前仅支持默认模板）
        """
        # Step 1: 解析输入
        source_type, content, source_id = self.parse_input(raw_input)

        # Step 2: 提取字段
        fields = self.extract_fields(content)

        # Step 3: 计算置信度
        confidence = self.compute_confidence(content, fields)

        # Step 4: 判断是否需要标注
        note = ""
        if confidence < 85:
            missing_keys = [k for k in self.KNOWN_KEYS if k not in fields]
            note = f"缺少字段: {', '.join(missing_keys[:3])}"

        # Step 5: 生成输出
        item = ProcessedItem(
            source=source_id,
            source_type=source_type,
            key_fields=fields,
            confidence=confidence,
            note=note,
        )
        item.raw_output = self.generate_output(item)

        return item

    def process_batch(self, inputs: List[str], custom_format: str = "") -> ProcessingResult:
        """批量处理多个输入"""
        result = ProcessingResult()

        for raw_input in inputs:
            try:
                item = self.process(raw_input, custom_format)
                result.add_item(item)
            except SkillError as e:
                result.add_error(e.code, e.message)
            except Exception as e:
                result.add_error("E005", f"处理异常: {e}")

        return result


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------
class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format_text(result: ProcessingResult) -> str:
        """文本格式输出"""
        lines = []
        for item in result.items:
            lines.append(item.raw_output)
        for code, detail in result.errors:
            lines.append(f"[{code}] {detail}")
        return "\n".join(lines)

    @staticmethod
    def format_json(result: ProcessingResult) -> str:
        """JSON 格式输出"""
        output = {
            "success_count": result.success_count,
            "error_count": result.error_count,
            "items": [
                {
                    "source": item.source,
                    "source_type": item.source_type,
                    "fields": item.key_fields,
                    "confidence": item.confidence,
                    "note": item.note,
                    "output": item.raw_output,
                }
                for item in result.items
            ],
            "errors": [{"code": code, "message": detail} for code, detail in result.errors],
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    @staticmethod
    def format_table(result: ProcessingResult) -> str:
        """表格格式输出（简单文本表格）"""
        if not result.items:
            return "无有效结果"

        headers = ["来源", "类型", "字段", "置信度", "备注"]
        rows = []
        for item in result.items:
            fields_str = "; ".join(f"{k}:{v}" for k, v in item.key_fields.items())
            rows.append([
                item.source[:20],
                item.source_type,
                fields_str[:50],
                f"{item.confidence}%",
                item.note or "-",
            ])

        # 计算列宽
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # 生成表格
        table_lines = []
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        table_lines.append(header_line)
        table_lines.append("-" * len(header_line))
        for row in rows:
            line = " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
            table_lines.append(line)

        # 错误信息
        if result.errors:
            table_lines.append("")
            table_lines.append("错误信息:")
            for code, detail in result.errors:
                table_lines.append(f"  [{code}] {detail}")

        return "\n".join(table_lines)


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置自检样例，离线验证核心逻辑"""
    print("=== shell-gpt 自检开始 ===")
    processor = CoreProcessor()
    formatter = OutputFormatter()
    passed = 0
    total = 0

    # 测试用例 1: 正常文本
    test_cases = [
        # (输入, 期望字段数, 期望置信度范围)
        ("姓名:张三 年龄:30 城市:北京", 3, 90.0),
        ("name:Alice age:25 city:Shanghai email:alice@test.com", 4, 90.0),
        ("姓名:李四 年龄:28", 2, 85.0),
        ("随便写点什么没有结构", 0, 50.0),
        ("电话:13800138000 地址:北京市朝阳区", 2, 85.0),
    ]

    for input_text, expected_fields, expected_conf in test_cases:
        total += 1
        try:
            result = processor.process(input_text)
            field_ok = len(result.key_fields) == expected_fields
            conf_ok = abs(result.confidence - expected_conf) < 0.01
            if field_ok and conf_ok:
                passed += 1
                print(f"  [PASS] 输入: {input_text[:30]}... 字段数={len(result.key_fields)}, 置信度={result.confidence}%")
            else:
                print(f"  [FAIL] 输入: {input_text[:30]}... 期望字段数={expected_fields}, 实际={len(result.key_fields)}; "
                      f"期望置信度={expected_conf}, 实际={result.confidence}")
        except SkillError as e:
            print(f"  [FAIL] 输入: {input_text[:30]}... 异常: {e}")

    # 测试用例 2: 错误处理
    total += 1
    try:
        processor.process("")
        print("  [FAIL] 空输入未触发 E001 错误")
    except SkillError as e:
        if e.code == "E001":
            passed += 1
            print("  [PASS] 空输入正确触发 E001")
        else:
            print(f"  [FAIL] 空输入错误码不正确: {e.code}")

    # 测试用例 3: 批量处理
    total += 1
    batch_result = processor.process_batch([
        "姓名:王五 年龄:35 城市:广州",
        "invalid input without structure",
        "",
    ])
    if batch_result.success_count == 2 and batch_result.error_count == 1:
        passed += 1
        print("  [PASS] 批量处理: 2 成功, 1 失败")
    else:
        print(f"  [FAIL] 批量处理结果异常: 成功={batch_result.success_count}, 失败={batch_result.error_count}")

    # 测试用例 4: 文件输入
    total += 1
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
        f.write("姓名:赵六 年龄:40 城市:深圳 地址:南山区")
        temp_path = f.name
    try:
        result = processor.process(temp_path)
        if result.source_type == "file" and len(result.key_fields) >= 3:
            passed += 1
            print("  [PASS] 文件输入解析成功")
        else:
            print(f"  [FAIL] 文件输入解析失败: type={result.source_type}, fields={len(result.key_fields)}")
    finally:
        os.unlink(temp_path)

    # 测试用例 5: URL 输入
    total += 1
    url_result = processor.process("https://example.com/data?name=Test&age=20&city=Beijing")
    if url_result.source_type == "url" and len(url_result.key_fields) >= 2:
        passed += 1
        print("  [PASS] URL 输入解析成功")
    else:
        print(f"  [FAIL] URL 输入解析失败: type={url_result.source_type}, fields={len(url_result.key_fields)}")

    # 测试用例 6: 输出格式化
    total += 1
    sample_result = processor.process("姓名:张三 年龄:30 城市:北京")
    json_output = formatter.format_json(ProcessingResult(items=[sample_result]))
    try:
        parsed = json.loads(json_output)
        if parsed["success_count"] == 1 and parsed["items"][0]["fields"]["姓名"] == "张三":
            passed += 1
            print("  [PASS] JSON 输出格式正确")
        else:
            print("  [FAIL] JSON 输出内容不正确")
    except json.JSONDecodeError:
        print("  [FAIL] JSON 输出无法解析")

    print(f"\n=== 自检完成: {passed}/{total} 通过 ===")
    return 0 if passed == total else 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="shell-gpt: AI 驱动的命令行生产力工具",
        epilog="示例: python main.py --input '姓名:张三 年龄:30' --format text",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入内容（文本/文件路径/URL）",
    )
    parser.add_argument(
        "--batch",
        help="批量输入，用逗号分隔多个输入",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "table"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--template",
        help="自定义输出模板，使用 {fields} {confidence} {note} 占位符",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    processor = CoreProcessor(custom_template=args.template or "")
    formatter = OutputFormatter()

    try:
        if args.batch:
            # 批量模式
            inputs = [x.strip() for x in args.batch.split(",") if x.strip()]
            if not inputs:
                raise SkillError("E001")
            result = processor.process_batch(inputs)
        elif args.input:
            # 单条模式
            result = ProcessingResult()
            try:
                item = processor.process(args.input)
                result.add_item(item)
            except SkillError as e:
                result.add_error(e.code, e.message)
        else:
            # 无输入参数
            raise SkillError("E001")

        # 输出结果
        if args.format == "json":
            output = formatter.format_json(result)
        elif args.format == "table":
            output = formatter.format_table(result)
        else:
            output = formatter.format_text(result)

        print(output)

        # 若有错误，返回非零状态码
        return 1 if result.error_count > 0 else 0

    except SkillError as e:
        print(f"[{e.code}] {e.message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("操作已取消", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[E005] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
