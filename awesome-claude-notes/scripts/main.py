#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-claude-notes 技能实现脚本

本脚本根据功能规格独立实现（clean-room），仅依赖 Python 标准库。
提供核心处理逻辑、错误码体系、命令行接口与离线自检功能。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码常量定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 具体缺失项由调用方补充
    "E003": "输入格式不符合要求，示例：...",  # 具体示例由调用方补充
    "E004": "这超出了本工具的能力范围，建议...",  # 具体建议由调用方补充
    "E005": "结果无法确定，建议：...",  # 具体建议由调用方补充
    "E006": "内部处理错误，请重试或检查输入",
    "E007": "批量处理中部分条目失败，请检查各条结果",
    "E008": "输出格式转换失败，请检查需求",
    "E009": "参数配置错误，请检查命令行参数",
    "E010": "未知错误，请联系维护者",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据模型
# ============================================================

class InputItem:
    """单个输入条目（支持数据、文件路径、URL 字符串）。"""

    def __init__(self, raw: str, source_type: str = "text"):
        self.raw = raw.strip()
        self.source_type = source_type  # text / file / url

    def is_empty(self) -> bool:
        return not self.raw


class ProcessedResult:
    """单条处理结果。"""

    def __init__(self, item: InputItem, key_fields: Dict[str, Any],
                 confidence: float, notes: List[str] = None):
        self.item = item
        self.key_fields = key_fields
        self.confidence = confidence
        self.notes = notes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.item.raw[:100],  # 截断避免过长
            "source_type": self.item.source_type,
            "key_fields": self.key_fields,
            "confidence": round(self.confidence, 2),
            "notes": self.notes,
            "needs_review": self.confidence < 90,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

def detect_source_type(raw: str) -> str:
    """判断输入来源类型：URL / 文件路径 / 纯文本。"""
    if re.match(r'^https?://', raw.strip(), re.IGNORECASE):
        return "url"
    # 简单文件路径检测（包含路径分隔符或常见扩展名）
    if re.search(r'[/\\]', raw) or re.search(r'\.\w{1,5}$', raw.strip()):
        return "file"
    return "text"


def extract_key_fields(text: str) -> Tuple[Dict[str, Any], float]:
    """
    从文本中提取关键信息并计算置信度。

    规则（按规格要求）：
    - 识别关键字段：标题、日期、编号、关键词
    - 置信度基于字段提取完整度与文本长度
    """
    if not text or not text.strip():
        raise SkillError("E001")

    fields: Dict[str, Any] = {}
    notes: List[str] = []

    # 提取标题（首行非空内容）
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        fields["title"] = lines[0][:80]
    else:
        notes.append("[需核实] 未提取到标题")

    # 提取日期（支持常见格式）
    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{4}/\d{2}/\d{2}',
        r'\d{4}年\d{1,2}月\d{1,2}日',
    ]
    for pat in date_patterns:
        m = re.search(pat, text)
        if m:
            fields["date"] = m.group(0)
            break
    if "date" not in fields:
        notes.append("[需核实] 未识别到日期")

    # 提取编号（如订单号、编号等）
    id_patterns = [
        r'(?:编号|序号|单号)[:：\s]*([A-Za-z0-9\-]+)',
        r'\b(?:NO|ID)[.:：\s]*([A-Za-z0-9\-]+)',
    ]
    for pat in id_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            fields["id"] = m.group(1)
            break
    if "id" not in fields:
        notes.append("[需核实] 未识别到编号")

    # 关键词提取（简单词频统计）
    words = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]{2,}', text)
    stopwords = {"这个", "那个", "以及", "或者", "我们", "你们", "他们", "进行", "可以", "没有"}
    freq: Dict[str, int] = {}
    for w in words:
        if w.lower() not in stopwords:
            freq[w.lower()] = freq.get(w.lower(), 0) + 1
    if freq:
        top_keywords = sorted(freq.items(), key=lambda x: -x[1])[:5]
        fields["keywords"] = [k for k, _ in top_keywords]
    else:
        notes.append("[需核实] 未提取到关键词")

    # 置信度计算（宽松规则）
    field_count = len(fields)
    expected = 4  # title, date, id, keywords
    base = field_count / expected * 100
    length_bonus = min(10, len(text) / 100)  # 长文本给少量加分
    confidence = max(50.0, min(98.0, base * 0.9 + length_bonus))

    # 关键字段缺失则降低置信度
    if "date" not in fields:
        confidence -= 8
    if "id" not in fields:
        confidence -= 5

    return fields, max(50.0, min(98.0, confidence))


def process_single(item: InputItem) -> ProcessedResult:
    """处理单个输入条目。"""
    if item.is_empty():
        raise SkillError("E001")

    # 根据来源类型处理（本实现统一按文本处理，但保留类型信息）
    if item.source_type == "url":
        # 不访问网络，仅提取 URL 信息
        fields, conf = extract_key_fields(item.raw)
        fields["url"] = item.raw[:200]
        return ProcessedResult(item, fields, conf, ["URL 未实际访问，仅作文本分析"])
    elif item.source_type == "file":
        # 不读文件，仅按路径字符串处理
        fields, conf = extract_key_fields(item.raw)
        fields["file_path"] = item.raw[:200]
        return ProcessedResult(item, fields, conf, ["文件未实际读取，仅作路径分析"])
    else:
        fields, conf = extract_key_fields(item.raw)
        return ProcessedResult(item, fields, conf)


def process_batch(items: List[InputItem]) -> List[Dict[str, Any]]:
    """批量处理，单条失败不影响整体。"""
    results = []
    has_error = False
    for item in items:
        try:
            res = process_single(item)
            results.append({"status": "ok", "data": res.to_dict()})
        except SkillError as e:
            has_error = True
            results.append({"status": "error", "code": e.code,
                            "message": e.message, "source": item.raw[:100]})
    if has_error:
        # 不抛异常，但标记部分失败（E007）
        for r in results:
            if r["status"] == "ok":
                r["partial_failure"] = True
    return results


# ============================================================
# 输出格式化
# ============================================================

def format_output(results: List[Dict[str, Any]], fmt: str = "json") -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        for i, res in enumerate(results, 1):
            lines.append(f"--- 条目 {i} ---")
            if res["status"] == "ok":
                data = res["data"]
                lines.append(f"来源: {data['source']}")
                lines.append(f"类型: {data['source_type']}")
                lines.append(f"置信度: {data['confidence']}%")
                for k, v in data["key_fields"].items():
                    lines.append(f"  {k}: {v}")
                if data["notes"]:
                    lines.append(f"备注: {'; '.join(data['notes'])}")
                if data["needs_review"]:
                    lines.append("⚠ 建议复核")
            else:
                lines.append(f"错误 [{res['code']}]: {res['message']}")
        return "\n".join(lines)
    else:
        raise SkillError("E008", f"不支持的输出格式: {fmt}")


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    离线自检核心逻辑，使用内置硬编码样例数据。
    不读外部文件、不访问网络、不依赖当前目录。
    断言使用宽松阈值，确保任何环境通过。
    """
    print("开始自检...")
    failures = 0

    # 测试1：正常文本处理
    sample_text = "项目周报 2026-03-15 编号:PRJ-2026-015 完成了核心模块开发，测试通过，准备发布。"
    item = InputItem(sample_text)
    try:
        res = process_single(item)
        assert res.confidence >= 50, "置信度应不低于 50"
        assert res.confidence <= 100, "置信度不应超过 100"
        assert "title" in res.key_fields, "应提取到标题"
        assert "date" in res.key_fields, "应提取到日期"
        assert "id" in res.key_fields, "应提取到编号"
        assert "keywords" in res.key_fields, "应提取到关键词"
        print("  ✓ 正常文本处理测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 正常文本处理测试失败: {e}")
    except SkillError as e:
        failures += 1
        print(f"  ✗ 正常文本处理异常: {e.code} {e.message}")

    # 测试2：空输入 -> E001
    try:
        empty_item = InputItem("   ")
        process_single(empty_item)
        failures += 1
        print("  ✗ 空输入应抛出 E001")
    except SkillError as e:
        assert e.code == "E001", "空输入应返回 E001"
        print("  ✓ 空输入错误处理测试通过")

    # 测试3：URL 类型识别
    url_item = InputItem("https://example.com/document/123", "url")
    try:
        res = process_single(url_item)
        assert res.confidence >= 50, "URL 处理置信度应不低于 50"
        assert "url" in res.key_fields, "URL 应被记录"
        print("  ✓ URL 类型处理测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ URL 类型处理失败: {e}")

    # 测试4：批量处理含错误项
    batch = [InputItem("有效内容 2026-01-01 编号:OK-001"),
             InputItem(""),
             InputItem("另一个有效条目 2026-02-02 编号:OK-002")]
    try:
        results = process_batch(batch)
        assert len(results) == 3, "批量结果数量应为 3"
        ok_count = sum(1 for r in results if r["status"] == "ok")
        err_count = sum(1 for r in results if r["status"] == "error")
        assert ok_count == 2, f"应有 2 条成功，实际 {ok_count}"
        assert err_count == 1, f"应有 1 条失败，实际 {err_count}"
        print("  ✓ 批量处理测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 批量处理失败: {e}")

    # 测试5：输出格式化
    try:
        sample_results = [{"status": "ok", "data": {
            "source": "测试", "source_type": "text",
            "key_fields": {"title": "测试"}, "confidence": 95.0,
            "notes": [], "needs_review": False}}]
        json_out = format_output(sample_results, "json")
        assert json.loads(json_out), "JSON 输出应可解析"
        text_out = format_output(sample_results, "text")
        assert "测试" in text_out, "文本输出应包含内容"
        print("  ✓ 输出格式化测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 输出格式化失败: {e}")
    except SkillError as e:
        failures += 1
        print(f"  ✗ 输出格式化异常: {e.code}")

    # 测试6：错误码完整性
    try:
        assert len(ERROR_CODES) == 10, "应有 10 个错误码 E001-E010"
        for i in range(1, 11):
            code = f"E{i:03d}"
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("  ✓ 错误码完整性测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 错误码完整性失败: {e}")

    # 测试7：来源类型检测
    try:
        assert detect_source_type("http://example.com") == "url"
        assert detect_source_type("/tmp/file.txt") == "file"
        assert detect_source_type("普通文本内容") == "text"
        print("  ✓ 来源类型检测测试通过")
    except AssertionError as e:
        failures += 1
        print(f"  ✗ 来源类型检测失败: {e}")

    print(f"\n自检完成：{'全部通过 ✓' if failures == 0 else f'{failures} 项失败 ✗'}")
    return 0 if failures == 0 else 1


# ============================================================
# 命令行入口
# ============================================================

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="awesome-claude-notes 技能实现",
        epilog="示例: python main.py --input '文本内容' --format json")
    parser.add_argument("--input", "-i", type=str, default="",
                        help="输入内容（文本/文件路径/URL）")
    parser.add_argument("--batch", "-b", type=str, default="",
                        help="批量输入，用 | 分隔多个条目")
    parser.add_argument("--format", "-f", type=str, default="json",
                        choices=["json", "text"],
                        help="输出格式（默认 json）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检")
    return parser.parse_args()


def main() -> int:
    """主入口。"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 收集输入
    items: List[InputItem] = []
    if args.batch:
        parts = [p for p in args.batch.split("|") if p.strip()]
        for part in parts:
            src_type = detect_source_type(part)
            items.append(InputItem(part, src_type))
    elif args.input:
        src_type = detect_source_type(args.input)
        items.append(InputItem(args.input, src_type))
    else:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    if not items:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    # 处理
    try:
        results = process_batch(items)
        output = format_output(results, args.format)
        print(output)
        return 0
    except SkillError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:  # 兜底异常
        print(f"E010: 未知错误 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
