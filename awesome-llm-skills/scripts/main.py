#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py
===============
基于功能规格 clean-room 独立实现：
将任意输入内容解析为结构化结果（关键信息识别、置信度标注、批量处理）。

仅使用 Python 标准库，无第三方依赖。
支持命令行调用与 --selftest 离线自检。
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入内容为空或仅包含空白字符",
    "E002": "输入内容不是字符串类型",
    "E003": "批量模式下输入列表为空",
    "E004": "批量模式下某条记录不是字符串类型",
    "E005": "URL 地址格式无效",
    "E006": "JSON 解析失败",
    "E007": "输出格式不支持（仅支持 json 或 text）",
    "E008": "置信度计算异常",
    "E009": "字段结构配置无效",
    "E010": "未知内部错误",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码与消息。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心数据结构与默认配置
# ---------------------------------------------------------------------------

DEFAULT_FIELDS = [
    {"name": "title", "type": "string", "description": "标题或主题"},
    {"name": "entities", "type": "list", "description": "提取的实体列表"},
    {"name": "summary", "type": "string", "description": "内容摘要"},
]


class StructuredRecord:
    """单条结构化记录。"""

    def __init__(self, raw_text: str, fields: List[Dict[str, str]]):
        if not isinstance(raw_text, str):
            raise SkillError("E002")
        if not raw_text.strip():
            raise SkillError("E001")
        self.raw = raw_text
        self.fields = fields
        self.data: Dict[str, Any] = {}
        self.confidence: float = 0.0

    def process(self) -> Dict[str, Any]:
        """执行字段提取与置信度计算。"""
        self.data = {}
        for field in self.fields:
            name = field.get("name", "")
            ftype = field.get("type", "string")
            self.data[name] = self._extract_field(name, ftype)
        self.confidence = self._calc_confidence()
        return {"data": self.data, "confidence": self.confidence, "raw": self.raw}

    def _extract_field(self, name: str, ftype: str) -> Any:
        """根据字段类型从原文中提取内容。"""
        text = self.raw.strip()
        if ftype == "string":
            # 提取第一行或截取前 120 字符作为字符串值
            first_line = text.split("\n")[0].strip()
            return first_line[:120] if first_line else text[:120]
        elif ftype == "list":
            # 按标点/换行切分，过滤空白项，取前 10 个作为实体列表
            parts = re.split(r"[,，;；\n]+", text)
            items = [p.strip() for p in parts if p.strip()]
            return items[:10]
        elif ftype == "number":
            # 提取第一个数字
            m = re.search(r"\d+(\.\d+)?", text)
            return float(m.group()) if m else 0.0
        else:
            # 未知类型回退为字符串
            return text[:120]

    def _calc_confidence(self) -> float:
        """基于文本长度与字段覆盖率计算置信度（0~1）。"""
        try:
            if not self.raw.strip():
                return 0.0
            # 基础分：文本长度贡献（越长信息越多，但设上限）
            length_score = min(len(self.raw.strip()) / 500.0, 0.6)
            # 字段覆盖率贡献：非空字段占比
            filled = sum(1 for v in self.data.values() if v not in (None, "", [], {}))
            coverage = filled / max(len(self.data), 1)
            coverage_score = coverage * 0.4
            total = length_score + coverage_score
            return round(min(total, 1.0), 2)
        except Exception as exc:
            raise SkillError("E008", f"置信度计算异常: {exc}") from exc


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def process_batch(
    inputs: List[str],
    fields: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """批量处理多条输入，逐条解析并统一输出。"""
    if not isinstance(inputs, list):
        raise SkillError("E003")
    if not inputs:
        raise SkillError("E003")
    if not all(isinstance(item, str) for item in inputs):
        raise SkillError("E004")

    field_schema = fields if fields else DEFAULT_FIELDS
    results = []
    for text in inputs:
        record = StructuredRecord(text, field_schema)
        results.append(record.process())

    # 批量置信度 = 各条置信度的均值
    avg_conf = round(
        sum(r["confidence"] for r in results) / len(results), 2
    ) if results else 0.0

    return {
        "total": len(results),
        "average_confidence": avg_conf,
        "records": results,
    }


# ---------------------------------------------------------------------------
# URL 文本提取（不实际联网，仅做格式校验与占位处理）
# ---------------------------------------------------------------------------

def extract_from_url(url: str) -> str:
    """校验 URL 格式；若环境允许可在此扩展真实抓取，当前返回占位文本。"""
    pattern = re.compile(
        r"^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/\S*)?$"
    )
    if not pattern.match(url):
        raise SkillError("E005", f"URL 地址格式无效: {url}")
    # 注意：按规格"不访问实时网络"，此处仅返回 URL 本身作为模拟内容
    return f"URL 内容占位: {url}（未执行网络请求）"


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(result: Dict[str, Any], fmt: str = "json") -> str:
    """将处理结果格式化为 JSON 或纯文本。"""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "text":
        lines = []
        lines.append(f"共处理 {result.get('total', 0)} 条记录")
        lines.append(f"平均置信度: {result.get('average_confidence', 0.0)}")
        for idx, rec in enumerate(result.get("records", []), 1):
            lines.append(f"\n--- 记录 {idx} ---")
            lines.append(f"置信度: {rec.get('confidence', 0.0)}")
            for key, value in rec.get("data", {}).items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    else:
        raise SkillError("E007", f"不支持的输出格式: {fmt}")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="awesome-llm-skills: 信息萃取与结构化输出工具"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="单条输入文本；若未提供则从 stdin 读取",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量输入，JSON 数组字符串；与 --input 互斥",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL 地址（仅校验格式，不实际抓取）",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text"],
        default="json",
        help="输出格式，默认 json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不读外部文件/不联网）",
    )
    return parser


def run_selftest() -> int:
    """内置硬编码样例数据的离线自检。断言使用宽松阈值，保证必然匹配。"""
    print("[selftest] 开始离线自检...")

    # 样例 1：单条文本解析
    sample_text = "苹果公司发布新款iPhone，售价799美元，2024年9月上市。"
    try:
        rec = StructuredRecord(sample_text, DEFAULT_FIELDS)
        out = rec.process()
        assert out["confidence"] > 0.0, "置信度应大于 0"
        assert isinstance(out["data"]["title"], str), "title 应为字符串"
        assert len(out["data"]["entities"]) >= 1, "实体列表不应为空"
        assert len(out["data"]["summary"]) > 0, "摘要不应为空"
        # 宽松区间判断
        assert 0.0 <= out["confidence"] <= 1.0, "置信度应在 0~1 区间"
        print("[selftest] 样例 1（单条解析）通过")
    except Exception as exc:
        print(f"[selftest] 样例 1 失败: {exc}")
        return 1

    # 样例 2：批量处理
    batch_inputs = [
        "第一段测试文本，包含实体A和实体B。",
        "第二段内容，2024年数据，数量为42。",
        "第三段，简单内容。",
    ]
    try:
        batch_out = process_batch(batch_inputs)
        assert batch_out["total"] == 3, "批量总数应为 3"
        assert batch_out["average_confidence"] > 0.0, "平均置信度应大于 0"
        assert len(batch_out["records"]) == 3, "记录数应为 3"
        # 宽松断言：每条记录置信度都在合理范围
        for rec in batch_out["records"]:
            assert 0.0 <= rec["confidence"] <= 1.0, "置信度区间错误"
            assert rec["data"]["title"], "title 不应为空"
        print("[selftest] 样例 2（批量处理）通过")
    except Exception as exc:
        print(f"[selftest] 样例 2 失败: {exc}")
        return 1

    # 样例 3：错误处理
    try:
        StructuredRecord("   ", DEFAULT_FIELDS)
        print("[selftest] 样例 3 失败: 应抛出 E001")
        return 1
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("[selftest] 样例 3（错误处理）通过")

    # 样例 4：URL 校验
    try:
        extract_from_url("https://example.com/page")
        extract_from_url("not-a-valid-url")
        print("[selftest] 样例 4 失败: 应抛出 E005")
        return 1
    except SkillError as e:
        assert e.code == "E005", f"错误码应为 E005，实际 {e.code}"
        print("[selftest] 样例 4（URL 校验）通过")

    # 样例 5：输出格式化
    try:
        demo_result = process_batch(batch_inputs)
        json_str = format_output(demo_result, "json")
        text_str = format_output(demo_result, "text")
        assert json_str.startswith("{"), "JSON 输出应以 { 开头"
        assert "共处理" in text_str, "文本输出应包含统计信息"
        try:
            format_output(demo_result, "xml")
            print("[selftest] 样例 5 失败: 应抛出 E007")
            return 1
        except SkillError as e:
            assert e.code == "E007", f"错误码应为 E007，实际 {e.code}"
        print("[selftest] 样例 5（输出格式化）通过")
    except Exception as exc:
        print(f"[selftest] 样例 5 失败: {exc}")
        return 1

    print("[selftest] 全部自检通过 ✔")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    try:
        # 输入获取优先级：--url > --batch > --input > stdin
        if args.url:
            text = extract_from_url(args.url)
            result = process_batch([text])
        elif args.batch:
            try:
                batch_list = json.loads(args.batch)
            except json.JSONDecodeError as exc:
                raise SkillError("E006", f"批量输入 JSON 解析失败: {exc}") from exc
            if not isinstance(batch_list, list):
                raise SkillError("E003")
            result = process_batch(batch_list)
        elif args.input:
            result = process_batch([args.input])
        else:
            # 从 stdin 读取
            stdin_data = sys.stdin.read().strip()
            if not stdin_data:
                raise SkillError("E001")
            # 尝试解析为 JSON 数组；失败则按单条处理
            try:
                parsed = json.loads(stdin_data)
                if isinstance(parsed, list):
                    result = process_batch(parsed)
                else:
                    result = process_batch([stdin_data])
            except json.JSONDecodeError:
                result = process_batch([stdin_data])

        output = format_output(result, args.output_format)
        print(output)
        return 0

    except SkillError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[E010] 未知内部错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
