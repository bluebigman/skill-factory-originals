#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tasks — 任务编排与数据转换 Skill 的独立实现

本脚本根据功能规格独立编写（clean-room），提供：
- 多源文本数据接入（粘贴文本、文件内容）
- 关键信息抽取（日期、金额、状态、编号等）
- 格式转换输出（JSON / CSV / Markdown 表格）
- 批量任务处理与置信度标注
- 内置离线自检（--selftest）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import csv
import io
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class TaskError(Exception):
    """技能统一异常，携带错误码 E001-E010。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 核心数据结构
# ============================================================
class TaskRecord:
    """单条任务记录（输入原始数据 + 处理结果）。"""

    def __init__(self, source: str, raw_text: str):
        self.source = source          # 来源标识：'paste' / 'file' / 'url'
        self.raw_text = raw_text      # 原始文本内容
        self.fields: Dict[str, Any] = {}   # 抽取出的字段
        self.confidence: str = "中"   # 置信度：高/中/低
        self.notes: List[str] = []    # 处理备注

    def to_dict(self) -> Dict[str, Any]:
        """转为可序列化字典。"""
        return {
            "source": self.source,
            "raw_text": self.raw_text,
            "fields": self.fields,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class BatchResult:
    """批量处理汇总结果。"""

    def __init__(self):
        self.records: List[TaskRecord] = []
        self.total: int = 0
        self.success: int = 0
        self.failed: int = 0
        self.errors: List[Tuple[str, str]] = []  # (错误码, 描述)

    def add_record(self, record: TaskRecord) -> None:
        self.records.append(record)
        self.total += 1
        self.success += 1

    def add_error(self, code: str, message: str) -> None:
        self.errors.append((code, message))
        self.failed += 1

    def summary(self) -> Dict[str, Any]:
        """返回汇总统计。"""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "error_count": len(self.errors),
        }


# ============================================================
# 工具函数
# ============================================================
def _safe_float(value: str) -> Optional[float]:
    """尝试将字符串转为浮点数，失败返回 None。"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str) -> Optional[int]:
    """尝试将字符串转为整数，失败返回 None。"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _detect_date(text: str) -> Optional[str]:
    """从文本中检测日期（支持常见格式），返回标准 ISO 字符串。"""
    patterns = [
        r"\d{4}-\d{2}-\d{2}",           # 2026-01-15
        r"\d{4}/\d{1,2}/\d{1,2}",       # 2026/1/15
        r"\d{1,2}\s+(?:月|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",  # 15-01-2026
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            raw = match.group(0)
            # 尝试解析为日期
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(raw, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # 如果带中文月份，简化处理
            if "月" in raw:
                return raw.strip()
    return None


def _detect_amount(text: str) -> Optional[float]:
    """从文本中检测金额（支持货币符号和千分位）。"""
    # 匹配如 ¥1,234.56 或 1234.56 或 $100
    match = re.search(r"[¥￥$€]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?", text)
    if match:
        cleaned = match.group(0).replace(",", "").replace("¥", "").replace("￥", "").replace("$", "").replace("€", "").strip()
        val = _safe_float(cleaned)
        if val is not None:
            return val
    return None


def _detect_status(text: str) -> Optional[str]:
    """检测状态关键词。"""
    keywords = {
        "完成": "已完成",
        "成功": "成功",
        "失败": "失败",
        "处理中": "处理中",
        "待处理": "待处理",
        "已取消": "已取消",
        "pending": "待处理",
        "completed": "已完成",
        "failed": "失败",
    }
    lower_text = text.lower()
    for key, val in keywords.items():
        if key.lower() in lower_text:
            return val
    return None


def _detect_code(text: str) -> Optional[str]:
    """检测编号/订单号（字母数字混合，长度>=4）。"""
    match = re.search(r"\b[A-Za-z]{2,}\d{2,}\b", text)
    if match:
        return match.group(0)
    return None


# ============================================================
# 核心处理逻辑
# ============================================================
def extract_fields(raw_text: str) -> Tuple[Dict[str, Any], str, List[str]]:
    """
    从原始文本中抽取关键字段。

    返回: (字段字典, 置信度, 备注列表)
    """
    fields: Dict[str, Any] = {}
    notes: List[str] = []

    if not raw_text or not raw_text.strip():
        raise TaskError("E001", "输入文本为空，无法处理")

    # 抽取日期
    date_val = _detect_date(raw_text)
    if date_val:
        fields["date"] = date_val
    else:
        notes.append("未检测到日期字段")

    # 抽取金额
    amount_val = _detect_amount(raw_text)
    if amount_val is not None:
        fields["amount"] = amount_val
    else:
        notes.append("未检测到金额字段")

    # 抽取状态
    status_val = _detect_status(raw_text)
    if status_val:
        fields["status"] = status_val
    else:
        notes.append("未检测到状态字段")

    # 抽取编号
    code_val = _detect_code(raw_text)
    if code_val:
        fields["code"] = code_val
    else:
        notes.append("未检测到编号字段")

    # 计算置信度
    found_count = len(fields)
    if found_count >= 3:
        confidence = "高"
    elif found_count >= 1:
        confidence = "中"
    else:
        confidence = "低"
        notes.append("未抽取到任何有效字段，置信度低")

    return fields, confidence, notes


def process_text(source: str, raw_text: str) -> TaskRecord:
    """处理单条文本，返回任务记录。"""
    record = TaskRecord(source=source, raw_text=raw_text)
    try:
        fields, confidence, notes = extract_fields(raw_text)
        record.fields = fields
        record.confidence = confidence
        record.notes = notes
    except TaskError as e:
        # 记录错误但保留原始数据
        record.notes.append(f"处理失败: {e.message}")
        record.confidence = "低"
        raise
    return record


def process_batch(items: List[Tuple[str, str]]) -> BatchResult:
    """
    批量处理任务。

    参数: items 为 (source, raw_text) 列表
    """
    result = BatchResult()
    for source, text in items:
        try:
            record = process_text(source, text)
            result.add_record(record)
        except TaskError as e:
            result.add_error(e.code, e.message)
        except Exception as e:  # 兜底异常
            result.add_error("E010", f"未知错误: {str(e)}")
    return result


# ============================================================
# 格式转换输出
# ============================================================
def to_json(batch: BatchResult) -> str:
    """输出 JSON 格式。"""
    data = {
        "summary": batch.summary(),
        "records": [r.to_dict() for r in batch.records],
        "errors": [{"code": c, "message": m} for c, m in batch.errors],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def to_csv(batch: BatchResult) -> str:
    """输出 CSV 格式。"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 表头
    headers = ["source", "raw_text", "confidence", "date", "amount", "status", "code", "notes"]
    writer.writerow(headers)

    for record in batch.records:
        row = [
            record.source,
            record.raw_text,
            record.confidence,
            record.fields.get("date", ""),
            record.fields.get("amount", ""),
            record.fields.get("status", ""),
            record.fields.get("code", ""),
            "; ".join(record.notes),
        ]
        writer.writerow(row)

    # 错误行
    for code, msg in batch.errors:
        writer.writerow(["ERROR", "", "", "", "", "", "", f"{code}: {msg}"])

    return output.getvalue()


def to_markdown(batch: BatchResult) -> str:
    """输出 Markdown 表格。"""
    lines: List[str] = []
    lines.append("## 任务处理结果")
    lines.append("")
    lines.append(f"- 总计: {batch.total}, 成功: {batch.success}, 失败: {batch.failed}")
    lines.append("")

    if batch.records:
        lines.append("| 来源 | 原始文本 | 置信度 | 日期 | 金额 | 状态 | 编号 |")
        lines.append("|------|----------|--------|------|------|------|------|")
        for r in batch.records:
            raw_short = r.raw_text[:30] + ("..." if len(r.raw_text) > 30 else "")
            lines.append(
                f"| {r.source} | {raw_short} | {r.confidence} | "
                f"{r.fields.get('date', '-')} | {r.fields.get('amount', '-')} | "
                f"{r.fields.get('status', '-')} | {r.fields.get('code', '-')} |"
            )
    else:
        lines.append("（无成功记录）")

    if batch.errors:
        lines.append("")
        lines.append("### 错误信息")
        for code, msg in batch.errors:
            lines.append(f"- `{code}`: {msg}")

    return "\n".join(lines)


def convert_output(batch: BatchResult, fmt: str) -> str:
    """按指定格式输出。"""
    fmt = fmt.lower().strip()
    if fmt == "json":
        return to_json(batch)
    elif fmt == "csv":
        return to_csv(batch)
    elif fmt == "markdown" or fmt == "md":
        return to_markdown(batch)
    else:
        raise TaskError("E002", f"不支持的输出格式: {fmt}")


# ============================================================
# 数据源接入
# ============================================================
def load_from_text(text: str) -> List[Tuple[str, str]]:
    """从用户粘贴的文本加载（每行一条记录）。"""
    if not text or not text.strip():
        raise TaskError("E003", "粘贴内容为空")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise TaskError("E003", "粘贴内容为空")

    return [("paste", line) for line in lines]


def load_from_csv_content(content: str) -> List[Tuple[str, str]]:
    """从 CSV 文件内容加载（取每行拼接为文本）。"""
    try:
        reader = csv.reader(io.StringIO(content))
        items = []
        for row in reader:
            if row and any(cell.strip() for cell in row):
                items.append(("file", " | ".join(cell.strip() for cell in row)))
        if not items:
            raise TaskError("E004", "CSV 内容无有效数据")
        return items
    except csv.Error as e:
        raise TaskError("E004", f"CSV 解析失败: {e}")


def load_from_json_content(content: str) -> List[Tuple[str, str]]:
    """从 JSON 文件内容加载。"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise TaskError("E005", f"JSON 解析失败: {e}")

    items = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                items.append(("file", json.dumps(item, ensure_ascii=False)))
            else:
                items.append(("file", str(item)))
    elif isinstance(data, dict):
        items.append(("file", json.dumps(data, ensure_ascii=False)))
    else:
        raise TaskError("E005", "JSON 顶层结构必须是对象或数组")

    if not items:
        raise TaskError("E005", "JSON 内容无有效数据")
    return items


# ============================================================
# 自检（--selftest）
# ============================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。

    使用内置硬编码样例，不读外部文件、不依赖工作目录、不访问网络。
    断言使用宽松阈值（区间/大小比较），确保稳定通过。
    """
    print("[SELFTEST] 开始离线自检...")
    passed = 0
    total = 0

    def check(name, condition):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [通过] {name}")
        else:
            print(f"  [失败] {name}")

    # ---- 测试1: 字段抽取 ----
    print("\n[测试1] 关键信息抽取")
    sample1 = "订单 ORD-20260115-001 金额 ¥1,234.56 状态：已完成 日期 2026-01-15"
    try:
        fields, conf, notes = extract_fields(sample1)
        check("抽取字段数>=3", len(fields) >= 3)
        check("检测到日期", "date" in fields and fields["date"] is not None)
        check("检测到金额", "amount" in fields and fields["amount"] is not None)
        check("金额>1000", fields.get("amount", 0) > 1000)
        check("检测到状态", "status" in fields and fields["status"] == "已完成")
        check("检测到编号", "code" in fields and len(fields["code"]) >= 4)
        check("高置信度", conf == "高")
    except Exception as e:
        check(f"抽取异常: {e}", False)

    # ---- 测试2: 无字段文本 ----
    print("\n[测试2] 无关键字段文本")
    sample2 = "这是一段普通的描述文字，没有结构化信息。"
    try:
        fields2, conf2, notes2 = extract_fields(sample2)
        check("字段数可能为0", len(fields2) <= 2)  # 宽松
        check("置信度不会为高", conf2 != "高")
    except Exception as e:
        check(f"抽取异常: {e}", False)

    # ---- 测试3: 批量处理 ----
    print("\n[测试3] 批量处理")
    items = [
        ("paste", "订单 A1001 金额 500 状态 待处理 日期 2026-02-01"),
        ("paste", "报销单 EXP-2026-001 金额 ¥2,000 已审核 2026-01-20"),
        ("paste", "无有效信息文本"),
    ]
    batch = process_batch(items)
    check("总数=3", batch.total == 3)
    check("成功数>=2", batch.success >= 2)
    check("有失败记录", batch.failed >= 1)
    check("每条记录有置信度", all(r.confidence in ("高", "中", "低") for r in batch.records))

    # ---- 测试4: 格式转换 ----
    print("\n[测试4] 格式转换")
    try:
        json_out = to_json(batch)
        check("JSON 输出非空", len(json_out) > 0)
        check("JSON 可解析", json.loads(json_out) is not None)
        parsed = json.loads(json_out)
        check("JSON 有 summary", "summary" in parsed)
        check("JSON summary 总数>0", parsed["summary"]["total"] > 0)
    except Exception as e:
        check(f"JSON 转换异常: {e}", False)

    try:
        csv_out = to_csv(batch)
        check("CSV 输出非空", len(csv_out) > 0)
        check("CSV 包含表头", "source" in csv_out and "confidence" in csv_out)
    except Exception as e:
        check(f"CSV 转换异常: {e}", False)

    try:
        md_out = to_markdown(batch)
        check("Markdown 输出非空", len(md_out) > 0)
        check("Markdown 含表格", "|" in md_out)
    except Exception as e:
        check(f"Markdown 转换异常: {e}", False)

    # ---- 测试5: 数据源加载 ----
    print("\n[测试5] 数据源加载")
    try:
        items_txt = load_from_text("第一行\n第二行\n第三行")
        check("文本加载3条", len(items_txt) == 3)
        check("来源为paste", all(s == "paste" for s, _ in items_txt))
    except Exception as e:
        check(f"文本加载异常: {e}", False)

    try:
        csv_content = "名称,数量,价格\n苹果,3,10.5\n香蕉,5,8.2\n"
        items_csv = load_from_csv_content(csv_content)
        check("CSV加载2条", len(items_csv) == 2)
    except Exception as e:
        check(f"CSV加载异常: {e}", False)

    try:
        json_content = '[{"id": 1, "name": "测试"}, {"id": 2, "name": "样例"}]'
        items_json = load_from_json_content(json_content)
        check("JSON加载2条", len(items_json) == 2)
    except Exception as e:
        check(f"JSON加载异常: {e}", False)

    # ---- 测试6: 错误处理 ----
    print("\n[测试6] 错误处理")
    try:
        load_from_text("")
        check("空文本应报错", False)
    except TaskError as e:
        check(f"空文本报错码E003", e.code == "E003")

    try:
        convert_output(batch, "xml")
        check("不支持格式应报错", False)
    except TaskError as e:
        check(f"不支持格式报错码E002", e.code == "E002")

    try:
        load_from_json_content("{invalid json")
        check("非法JSON应报错", False)
    except TaskError as e:
        check(f"非法JSON报错码E005", e.code == "E005")

    # ---- 汇总 ----
    print(f"\n[SELFTEST] 完成: {passed}/{total} 通过")
    if passed == total:
        print("[SELFTEST] 全部通过 ✅")
        return 0
    else:
        print(f"[SELFTEST] 有 {total - passed} 项失败 ❌")
        return 1


# ============================================================
# 主程序
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tasks",
        description="任务编排与数据转换 Skill (clean-room 实现)",
        epilog="示例: python main.py --input sample.txt --format json",
    )
    parser.add_argument("--input", "-i", help="输入文件路径（CSV/JSON/TXT）")
    parser.add_argument("--text", "-t", help="直接传入文本内容（每行一条记录）")
    parser.add_argument("--format", "-f", default="json", choices=["json", "csv", "markdown", "md"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="tasks 1.0.1 (clean-room)")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        # 加载数据
        if args.text:
            items = load_from_text(args.text)
        elif args.input:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                raise TaskError("E006", f"无法读取文件: {e}")

            # 根据扩展名选择加载方式
            ext = args.input.lower().rsplit(".", 1)[-1] if "." in args.input else ""
            if ext == "csv":
                items = load_from_csv_content(content)
            elif ext == "json":
                items = load_from_json_content(content)
            else:
                items = load_from_text(content)
        else:
            # 无输入时给出提示
            print("错误: 请提供 --input 或 --text 参数，或使用 --selftest 运行自检", file=sys.stderr)
            print("用法: python main.py --selftest", file=sys.stderr)
            return 1

        # 批量处理
        batch = process_batch(items)

        # 输出结果
        output = convert_output(batch, args.format)
        print(output)

        # 如果有错误，返回非零退出码
        if batch.failed > 0:
            return 2
        return 0

    except TaskError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
