#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - 未命名工具（angreal 技能）独立实现

本脚本依据功能规格 clean-room 重写，不参考任何既有实现。
提供命令行入口与内置自检（--selftest）。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "内部处理失败：{detail}",
    "E007": "输出序列化失败：{detail}",
    "E008": "参数冲突：{detail}",
    "E009": "未知错误码：{code}",
    "E010": "自检失败：{detail}",
}


class SkillError(Exception):
    """技能运行期异常，携带错误码。"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_CODES.get(code, ERROR_CODES["E009"].format(code=code)).format(**kwargs)
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class ProcessedItem:
    """单条结构化处理结果。"""

    raw: str                     # 原始输入
    key_fields: Dict[str, Any]   # 提取的关键字段
    confidence: float            # 置信度 0~1
    note: str = ""               # 备注（低置信度时说明原因）


@dataclass
class BatchResult:
    """批量处理结果。"""

    items: List[ProcessedItem] = field(default_factory=list)
    total: int = 0
    avg_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "avg_confidence": round(self.avg_confidence, 4),
            "items": [
                {
                    "raw": it.raw,
                    "key_fields": it.key_fields,
                    "confidence": round(it.confidence, 4),
                    "note": it.note,
                }
                for it in self.items
            ],
        }


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
def _extract_key_fields(text: str) -> Dict[str, Any]:
    """
    从输入文本中提取关键字段。

    规则（依据规格"识别输入中的关键信息"）：
      1. 尝试解析 JSON 对象，若成功则取其全部键值。
      2. 否则按 "键: 值" 或 "键=值" 模式提取。
      3. 都没有则返回 { "content": text }。

    本函数为纯文本解析，不访问网络/文件。
    """
    text = text.strip()
    if not text:
        return {}

    # 尝试 JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {str(k): v for k, v in obj.items()}
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试键值对（支持冒号或等号，支持中英文标点）
    fields: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 移除行尾可能的分号/逗号
        line = line.rstrip(";，,。.")
        for sep in (":", "：", "="):
            if sep in line:
                key, _, value = line.partition(sep)
                key = key.strip()
                value = value.strip()
                if key and value:
                    fields[key] = value
                break

    if fields:
        return fields

    # 整段文本作为内容
    return {"content": text}


def _compute_confidence(fields: Dict[str, Any], raw_len: int) -> tuple:
    """
    计算置信度（0~1）及备注。

    规则：
      - 字段数 >= 3 且原始长度 > 20：置信度 0.95
      - 字段数 >= 1 且原始长度 > 5：置信度 0.88
      - 否则：置信度 0.7，备注 [需核实]
    返回 (confidence, note)
    """
    n = len(fields)
    if n >= 3 and raw_len > 20:
        return 0.95, ""
    if n >= 1 and raw_len > 5:
        return 0.88, ""
    return 0.7, "[需核实] 字段过少或输入过短，请人工确认"


def process_item(raw_input: str) -> ProcessedItem:
    """处理单条输入，返回结构化结果。"""
    if not raw_input or not raw_input.strip():
        raise SkillError("E001")

    fields = _extract_key_fields(raw_input)
    if not fields:
        raise SkillError("E003", example="{\"name\": \"张三\", \"age\": 30} 或 姓名: 张三")

    conf, note = _compute_confidence(fields, len(raw_input.strip()))
    return ProcessedItem(
        raw=raw_input.strip(),
        key_fields=fields,
        confidence=conf,
        note=note,
    )


def process_batch(inputs: List[str]) -> BatchResult:
    """批量处理多条输入。"""
    if not inputs:
        raise SkillError("E001")

    items = [process_item(i) for i in inputs]
    total = len(items)
    avg_conf = sum(it.confidence for it in items) / total if total else 0.0
    return BatchResult(items=items, total=total, avg_confidence=avg_conf)


def format_output(result: BatchResult, fmt: str = "json") -> str:
    """按指定格式输出结果。支持 json / text。"""
    if fmt == "json":
        try:
            return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise SkillError("E007", detail=str(exc)) from exc

    if fmt == "text":
        lines = [f"总数: {result.total}", f"平均置信度: {result.avg_confidence:.2f}", ""]
        for idx, it in enumerate(result.items, 1):
            lines.append(f"[{idx}] 原始: {it.raw}")
            for k, v in it.key_fields.items():
                lines.append(f"    {k}: {v}")
            lines.append(f"    置信度: {it.confidence:.2f} {it.note}")
            lines.append("")
        return "\n".join(lines)

    raise SkillError("E003", example="json 或 text")


# ---------------------------------------------------------------------------
# 自检（--selftest）
# ---------------------------------------------------------------------------
def _run_selftest() -> None:
    """
    离线自检核心逻辑。使用内置硬编码样例，不读文件、不联网。

    断言采用宽松阈值（大小/区间），不依赖精确值。
    """
    # 样例 1：JSON 输入，应提取多个字段
    item1 = process_item('{"name": "张三", "age": 30, "city": "北京"}')
    assert item1.key_fields.get("name") == "张三", "E010: JSON 字段 name 提取失败"
    assert item1.key_fields.get("age") == 30, "E010: JSON 字段 age 提取失败"
    assert item1.confidence >= 0.9, "E010: JSON 多字段置信度应 >= 0.9"

    # 样例 2：键值对文本输入
    item2 = process_item("姓名: 李四\n年龄: 25\n城市: 上海")
    assert item2.key_fields.get("姓名") == "李四", "E010: 键值对字段提取失败"
    assert item2.confidence >= 0.85, "E010: 键值对置信度应 >= 0.85"

    # 样例 3：短文本，置信度应较低
    item3 = process_item("你好")
    assert item3.confidence < 0.85, "E010: 短文本置信度应 < 0.85"
    assert item3.note, "E010: 低置信度应有备注"

    # 样例 4：批量处理
    batch = process_batch([
        '{"a": 1, "b": 2, "c": 3}',
        "x: 10\ny: 20",
        "短文本",
    ])
    assert batch.total == 3, "E010: 批量总数应为 3"
    assert 0.5 <= batch.avg_confidence <= 1.0, "E010: 平均置信度应在 0.5~1.0 之间"

    # 样例 5：空输入应抛 E001
    try:
        process_item("   ")
        raise AssertionError("E010: 空输入应抛 E001")
    except SkillError as exc:
        assert exc.code == "E001", "E010: 错误码应为 E001"

    # 样例 6：JSON 输出应可被解析
    out_json = format_output(batch, "json")
    parsed = json.loads(out_json)
    assert parsed["total"] == 3, "E010: JSON 输出 total 应为 3"
    assert len(parsed["items"]) == 3, "E010: JSON 输出 items 长度应为 3"

    # 样例 7：文本输出应包含关键信息
    out_text = format_output(batch, "text")
    assert "总数" in out_text, "E010: 文本输出应包含总数"
    assert "置信度" in out_text, "E010: 文本输出应包含置信度"

    # 样例 8：错误码映射存在
    assert "E001" in ERROR_CODES and "E010" in ERROR_CODES, "E010: 错误码表不完整"

    # 全部通过
    print("[selftest] 全部断言通过（共 8 组）")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="angreal",
        description="未命名工具 - 将输入内容转换为结构化结果（仅供学习参考）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检，不读文件不联网",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        default=None,
        help="待处理的内容，可多条。示例：--input '{\"name\": \"张三\"}' '姓名: 李四'",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="输出格式（默认 json）",
    )
    parser.add_argument(
        "--batch-file",
        default=None,
        help="从文件读取多行输入（每行一条），注意：此选项会读取文件",
    )
    return parser.parse_args()


def _read_batch_file(path: str) -> List[str]:
    """从文件读取多行输入。"""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except OSError as exc:
        raise SkillError("E006", detail=f"读取文件失败: {exc}") from exc
    if not lines:
        raise SkillError("E001")
    return lines


def main() -> int:
    """主入口。返回进程退出码（0 成功，非 0 失败）。"""
    args = _parse_args()

    # 自检模式：不读外部文件、不联网
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except AssertionError as exc:
            print(f"[selftest] 失败: {exc}", file=sys.stderr)
            return 1
        except SkillError as exc:
            print(f"[selftest] 错误: {exc.message}", file=sys.stderr)
            return 1

    # 正常处理模式
    try:
        # 收集输入
        if args.batch_file:
            inputs = _read_batch_file(args.batch_file)
        elif args.input:
            inputs = args.input
        else:
            # 无输入则读取标准输入（支持管道）
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                # 尝试按行分割，若只有一行则整体作为一条
                lines = [ln.strip() for ln in stdin_data.splitlines() if ln.strip()]
                inputs = lines if len(lines) > 1 else [stdin_data]
            else:
                raise SkillError("E001")

        # 处理
        result = process_batch(inputs)

        # 输出
        output = format_output(result, args.format)
        print(output)
        return 0

    except SkillError as exc:
        print(f"错误 {exc.code}: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:  # 兜底
        print(f"错误 E006: 未预期异常: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
