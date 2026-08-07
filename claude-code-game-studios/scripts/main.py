#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 游戏工坊 数据转换 结构化输出（独立实现）

依据功能规格 clean-room 重写，不参考任何既有代码。
提供：
  - 文本/字典 → 结构化 JSON/表格/Markdown 转换
  - 关键字段提取与置信度标注
  - 批量处理与自定义格式输出
  - 命令行入口与内置自检（--selftest）
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================
# 错误码定义（E001–E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空或格式不合法",
    "E002": "输入必须是字符串或字典列表",
    "E003": "自定义字段映射格式错误",
    "E004": "输出格式不支持",
    "E005": "批量处理输入必须为列表",
    "E006": "字段提取失败：缺少必要键",
    "E007": "置信度标注失败：数值超出范围",
    "E008": "文件读取失败",
    "E009": "文件写入失败",
    "E010": "自检断言未通过",
}


def _err(code: str, detail: str = "") -> str:
    """构造统一错误消息。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        return f"[{code}] {msg}: {detail}"
    return f"[{code}] {msg}"


# ============================================================
# 核心数据结构
# ============================================================
class GameDataItem:
    """单项游戏数据对象，保存原始输入与结构化结果。"""

    def __init__(self, raw: Union[str, Dict[str, Any]]):
        self.raw = raw
        self.fields: Dict[str, Any] = {}
        self.confidence: Dict[str, float] = {}
        self.source_type = "dict" if isinstance(raw, dict) else "text"
        self._parse()

    def _parse(self) -> None:
        """解析原始输入为字段字典。"""
        if isinstance(self.raw, dict):
            # 字典直接复制，保留全部键值
            self.fields = dict(self.raw)
            for key in self.fields:
                self.confidence[key] = 1.0
        else:
            # 文本尝试识别 key: value 或 key=value 模式
            text = str(self.raw).strip()
            if not text:
                raise ValueError(_err("E001", "空文本"))
            # 按行解析
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # 匹配 "key: value" 或 "key=value"
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)$", line)
                if m:
                    key, val = m.group(1), m.group(2).strip()
                    self.fields[key] = val
                    self.confidence[key] = 0.95  # 文本解析置信度略低
                else:
                    # 无法识别的行，放入 "_raw_lines"
                    self.fields.setdefault("_raw_lines", []).append(line)
                    self.confidence["_raw_lines"] = 0.5
            if not self.fields:
                raise ValueError(_err("E002", "无法从文本提取字段"))

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)

    def to_dict(self, with_confidence: bool = False) -> Dict[str, Any]:
        """转换为字典，可选包含置信度。"""
        if with_confidence:
            return {"data": self.fields, "confidence": self.confidence}
        return dict(self.fields)


# ============================================================
# 转换器类
# ============================================================
class GameDataConverter:
    """核心转换引擎：支持 JSON / 表格 / Markdown 输出。"""

    def __init__(self, field_order: Optional[List[str]] = None):
        self.field_order = field_order  # 自定义字段顺序
        self.items: List[GameDataItem] = []

    def load(self, data: Union[str, Dict[str, Any], List[Any]]) -> None:
        """加载数据，支持单项或批量。"""
        if isinstance(data, list):
            if not data:
                raise ValueError(_err("E005", "空列表"))
            for item in data:
                self.items.append(GameDataItem(item))
        else:
            self.items.append(GameDataItem(data))

    def _ordered_fields(self) -> List[str]:
        """确定输出字段顺序。"""
        if self.field_order:
            return self.field_order
        # 收集所有键，保持出现顺序
        keys: List[str] = []
        for item in self.items:
            for k in item.fields:
                if k not in keys:
                    keys.append(k)
        return keys

    def to_json(self, pretty: bool = True, with_confidence: bool = False) -> str:
        """输出 JSON 字符串。"""
        result = [item.to_dict(with_confidence) for item in self.items]
        if pretty:
            return json.dumps(result, ensure_ascii=False, indent=2)
        return json.dumps(result, ensure_ascii=False)

    def to_table(self, separator: str = "\t") -> str:
        """输出表格（默认制表符分隔）。"""
        fields = self._ordered_fields()
        lines = [separator.join(fields)]
        for item in self.items:
            row = []
            for f in fields:
                val = item.get(f, "")
                # 列表转为逗号连接
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                row.append(str(val))
            lines.append(separator.join(row))
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """输出 Markdown 表格。"""
        fields = self._ordered_fields()
        lines = ["| " + " | ".join(fields) + " |"]
        lines.append("| " + " | ".join(["---"] * len(fields)) + " |")
        for item in self.items:
            row = []
            for f in fields:
                val = item.get(f, "")
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                row.append(str(val))
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    def to_custom(self, template: str) -> str:
        """自定义模板输出，{field} 占位符替换。"""
        try:
            lines = []
            for item in self.items:
                line = template
                for key, val in item.fields.items():
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val)
                    line = line.replace("{" + key + "}", str(val))
                lines.append(line)
            return "\n".join(lines)
        except Exception as exc:
            raise ValueError(_err("E003", str(exc)))


# ============================================================
# 关键信息提取与置信度
# ============================================================
def extract_key_fields(data: List[Dict[str, Any]], key_names: List[str]) -> List[Dict[str, Any]]:
    """从数据中提取指定关键字段，缺失字段标注置信度。"""
    if not isinstance(data, list):
        raise ValueError(_err("E005", "必须为列表"))
    if not key_names:
        raise ValueError(_err("E006", "未指定关键字段"))

    results = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(_err("E002", f"第 {idx} 项不是字典"))
        extracted: Dict[str, Any] = {}
        for key in key_names:
            if key in item:
                extracted[key] = item[key]
            else:
                # 缺失字段标注 [需核实:key]
                extracted[key] = f"[需核实:{key}]"
        results.append(extracted)
    return results


def annotate_confidence(data: Dict[str, Any], base: float = 0.8) -> Dict[str, Any]:
    """为字段添加置信度标注，返回 {字段: 置信度}。"""
    if not isinstance(data, dict):
        raise ValueError(_err("E002", "输入必须为字典"))
    if base < 0.0 or base > 1.0:
        raise ValueError(_err("E007", "置信度必须在 0–1 之间"))

    conf: Dict[str, float] = {}
    for key, val in data.items():
        if isinstance(val, str) and val.startswith("[需核实:"):
            conf[key] = 0.3  # 低置信度
        else:
            conf[key] = base
    return conf


# ============================================================
# 批量处理与格式定制
# ============================================================
def batch_convert(
    items: List[Any],
    output_format: str = "json",
    field_order: Optional[List[str]] = None,
    template: Optional[str] = None,
) -> str:
    """批量转换，支持 json/table/markdown/custom。"""
    converter = GameDataConverter(field_order=field_order)
    converter.load(items)

    fmt = output_format.lower()
    if fmt == "json":
        return converter.to_json()
    if fmt == "table":
        return converter.to_table()
    if fmt == "markdown":
        return converter.to_markdown()
    if fmt == "custom":
        if not template:
            raise ValueError(_err("E003", "自定义格式需提供模板"))
        return converter.to_custom(template)
    raise ValueError(_err("E004", f"不支持格式: {output_format}"))


# ============================================================
# 命令行入口
# ============================================================
def _run_selftest() -> int:
    """内置硬编码样例自检，不依赖外部文件或网络。"""
    print("[自检] 开始运行内置样例测试...")

    # --- 样例 1: 字典转 JSON ---
    sample1 = [
        {"player_id": "P001", "level": 10, "score": 2500},
        {"player_id": "P002", "level": 7, "score": 1800},
    ]
    try:
        converter = GameDataConverter()
        converter.load(sample1)
        json_out = converter.to_json(pretty=False)
        assert "P001" in json_out, "JSON 输出缺少玩家 ID"
        assert "2500" in json_out, "JSON 输出缺少分数"
        print("[自检] 字典转 JSON: 通过")
    except AssertionError as exc:
        print(_err("E010", f"JSON 样例失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"JSON 样例异常: {exc}"))
        return 1

    # --- 样例 2: 文本解析 ---
    sample2 = "player_name: Alice\nlevel=5\nclass: warrior"
    try:
        item = GameDataItem(sample2)
        assert item.get("player_name") == "Alice", "文本解析玩家名失败"
        assert item.get("level") == "5", "文本解析等级失败"
        assert item.get("class") == "warrior", "文本解析职业失败"
        print("[自检] 文本解析: 通过")
    except AssertionError as exc:
        print(_err("E010", f"文本解析失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"文本解析异常: {exc}"))
        return 1

    # --- 样例 3: 关键字段提取与置信度 ---
    sample3 = [
        {"player_id": "P003", "level": 3},
        {"player_id": "P004"},  # 缺少 level
    ]
    try:
        extracted = extract_key_fields(sample3, ["player_id", "level"])
        assert extracted[1]["level"] == "[需核实:level]", "缺失字段标注失败"
        conf = annotate_confidence(extracted[1], base=0.9)
        assert conf["level"] < 0.5, "低置信度标注失败"
        assert conf["player_id"] >= 0.5, "高置信度标注失败"
        print("[自检] 关键字段与置信度: 通过")
    except AssertionError as exc:
        print(_err("E010", f"字段提取失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"字段提取异常: {exc}"))
        return 1

    # --- 样例 4: Markdown 输出 ---
    try:
        md = converter.to_markdown()
        assert "| player_id |" in md, "Markdown 表头缺失"
        assert "| --- |" in md, "Markdown 分隔行缺失"
        print("[自检] Markdown 输出: 通过")
    except AssertionError as exc:
        print(_err("E010", f"Markdown 失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"Markdown 异常: {exc}"))
        return 1

    # --- 样例 5: 自定义模板 ---
    try:
        custom = converter.to_custom("玩家 {player_id} 等级 {level}")
        assert "玩家 P001 等级 10" in custom, "自定义模板替换失败"
        print("[自检] 自定义模板: 通过")
    except AssertionError as exc:
        print(_err("E010", f"自定义模板失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"自定义模板异常: {exc}"))
        return 1

    # --- 样例 6: 批量处理 ---
    try:
        batch = batch_convert(sample1, output_format="table")
        assert "P001" in batch and "P002" in batch, "批量表格输出缺失"
        print("[自检] 批量处理: 通过")
    except AssertionError as exc:
        print(_err("E010", f"批量处理失败: {exc}"))
        return 1
    except Exception as exc:
        print(_err("E010", f"批量处理异常: {exc}"))
        return 1

    print("[自检] 全部测试通过 ✔")
    return 0


def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="游戏工坊 数据转换 结构化输出工具",
        epilog="示例: python main.py --input data.json --format json",
    )
    parser.add_argument("--input", type=str, help="输入数据文件路径（JSON 或文本）")
    parser.add_argument("--format", type=str, default="json",
                        choices=["json", "table", "markdown", "custom"],
                        help="输出格式")
    parser.add_argument("--fields", type=str, default="",
                        help="自定义字段顺序，逗号分隔")
    parser.add_argument("--template", type=str, default="",
                        help="自定义模板，如 '玩家 {name} 等级 {level}'")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线样例）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 正常模式：需要输入
    if not args.input:
        print(_err("E001", "请提供 --input 或使用 --selftest"))
        parser.print_help()
        return 1

    # 读取输入
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(_err("E008", str(exc)))
        return 1

    # 解析输入：尝试 JSON，否则按文本
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = content  # 作为纯文本处理

    # 处理字段顺序
    field_order = None
    if args.fields:
        field_order = [f.strip() for f in args.fields.split(",") if f.strip()]

    # 转换
    try:
        if isinstance(data, list):
            result = batch_convert(
                data,
                output_format=args.format,
                field_order=field_order,
                template=args.template or None,
            )
        else:
            converter = GameDataConverter(field_order=field_order)
            converter.load(data)
            if args.format == "json":
                result = converter.to_json()
            elif args.format == "table":
                result = converter.to_table()
            elif args.format == "markdown":
                result = converter.to_markdown()
            elif args.format == "custom":
                if not args.template:
                    raise ValueError(_err("E003", "自定义格式需要 --template"))
                result = converter.to_custom(args.template)
            else:
                raise ValueError(_err("E004", args.format))

        # 输出结果
        print(result)
        return 0

    except Exception as exc:
        print(f"[错误] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
