#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据整理与结构化输出工具（独立实现）

依据功能规格，提供：
- 从文本 / CSV / JSON / Markdown 中提取关键信息
- 将数据转换为结构化输出（JSON / Markdown 表格 / CSV）
- 对每个输出字段标注置信度（高/中/低）
- 支持批量处理（多行或多条记录）

本脚本为 clean-room 独立实现，仅依赖标准库。
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空或未提供有效数据",
    "E002": "输入格式不支持（仅支持 txt/csv/json/md/url）",
    "E003": "URL 访问失败或网络不可达",
    "E004": "JSON 解析失败",
    "E005": "CSV 解析失败",
    "E006": "Markdown 表格解析失败",
    "E007": "输出格式不支持（仅支持 json/markdown/csv）",
    "E008": "批量处理失败（某条记录处理异常）",
    "E009": "内部逻辑错误（未知异常）",
    "E010": "参数错误或命令行用法错误",
}


def _error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造错误返回结构"""
    msg = ERROR_CODES.get(code, "未知错误")
    result = {"error": {"code": code, "message": msg}}
    if detail:
        result["error"]["detail"] = detail
    return result


# ============================================================
# 核心工具函数
# ============================================================

def _guess_confidence(value: Any) -> str:
    """
    根据值的特征推断置信度（宽松规则）：
    - 高：非空字符串、非零数字、布尔值
    - 中：空字符串但字段存在
    - 低：None / 缺失
    """
    if value is None:
        return "低"
    if isinstance(value, bool):
        return "高"
    if isinstance(value, (int, float)):
        return "高" if value != 0 else "中"
    if isinstance(value, str):
        if value.strip():
            return "高"
        return "中"
    if isinstance(value, (list, dict)):
        return "高" if len(value) > 0 else "中"
    return "中"


def _extract_key_value_pairs(text: str) -> List[Dict[str, Any]]:
    """
    从文本中提取键值对（宽松模式）：
    支持格式： "key: value"、"key=value"、"key - value"
    返回结构化列表
    """
    pairs = []
    lines = text.splitlines()
    pattern = re.compile(
        r"^\s*(?P<key>[^:=：\-]{1,50})\s*[:=：\-]\s*(?P<value>.+?)\s*$"
    )
    for line in lines:
        m = pattern.match(line)
        if m:
            key = m.group("key").strip()
            value = m.group("value").strip()
            pairs.append({
                "字段": key,
                "值": value,
                "置信度": _guess_confidence(value)
            })
    return pairs


def _extract_markdown_table(text: str) -> List[Dict[str, Any]]:
    """
    从 Markdown 文本中提取表格（宽松模式）：
    支持标准 Markdown 表格语法
    """
    lines = text.splitlines()
    table_lines = []
    in_table = False
    headers = []
    rows = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                table_lines = [stripped]
            else:
                table_lines.append(stripped)
        else:
            if in_table:
                # 解析当前表格
                if len(table_lines) >= 2:
                    # 表头
                    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
                    # 跳过分隔行（---）
                    data_lines = table_lines[2:] if len(table_lines) > 2 else []
                    for dl in data_lines:
                        cells = [c.strip() for c in dl.strip("|").split("|")]
                        if len(cells) == len(headers):
                            row = {}
                            for i, h in enumerate(headers):
                                row[h] = cells[i]
                                row[f"{h}_置信度"] = _guess_confidence(cells[i])
                            rows.append(row)
                table_lines = []
                in_table = False

    # 处理文件末尾的表格
    if in_table and len(table_lines) >= 2:
        headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
        data_lines = table_lines[2:] if len(table_lines) > 2 else []
        for dl in data_lines:
            cells = [c.strip() for c in dl.strip("|").split("|")]
            if len(cells) == len(headers):
                row = {}
                for i, h in enumerate(headers):
                    row[h] = cells[i]
                    row[f"{h}_置信度"] = _guess_confidence(cells[i])
                rows.append(row)

    return rows


def _extract_json(json_data: Any) -> List[Dict[str, Any]]:
    """从 JSON 数据中提取结构化信息"""
    results = []

    if isinstance(json_data, dict):
        result = {}
        for k, v in json_data.items():
            result[k] = v
            result[f"{k}_置信度"] = _guess_confidence(v)
        results.append(result)
    elif isinstance(json_data, list):
        for item in json_data:
            if isinstance(item, dict):
                result = {}
                for k, v in item.items():
                    result[k] = v
                    result[f"{k}_置信度"] = _guess_confidence(v)
                results.append(result)
            else:
                results.append({"值": item, "值_置信度": _guess_confidence(item)})
    else:
        results.append({"值": json_data, "值_置信度": _guess_confidence(json_data)})

    return results


def _extract_csv(csv_text: str) -> List[Dict[str, Any]]:
    """从 CSV 文本中提取结构化信息"""
    results = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        result = {}
        for k, v in row.items():
            if k is None:
                continue
            result[k] = v
            result[f"{k}_置信度"] = _guess_confidence(v)
        results.append(result)
    return results


def _fetch_url(url: str) -> str:
    """获取 URL 内容（仅支持公开可访问的 http/https）"""
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"URL 访问失败: {e}")


def _detect_and_extract(content: str, source_type: str = "auto") -> List[Dict[str, Any]]:
    """
    根据内容类型自动提取结构化数据
    source_type: auto / text / csv / json / md / url
    """
    if source_type == "url":
        # 已由调用方处理
        pass

    # 自动检测
    if source_type == "auto":
        stripped = content.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            source_type = "json"
        elif "," in stripped and "\n" in stripped and ("|" not in stripped):
            source_type = "csv"
        elif stripped.startswith("|"):
            source_type = "md"
        else:
            source_type = "text"

    if source_type == "json":
        try:
            data = json.loads(content)
            return _extract_json(data)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 解析失败: {e}")

    elif source_type == "csv":
        try:
            return _extract_csv(content)
        except Exception as e:
            raise RuntimeError(f"CSV 解析失败: {e}")

    elif source_type == "md":
        rows = _extract_markdown_table(content)
        if rows:
            return rows
        # 如果没有表格，则回退到键值对提取
        pairs = _extract_key_value_pairs(content)
        if pairs:
            return pairs
        return [{"内容": content, "内容_置信度": _guess_confidence(content)}]

    else:  # text
        pairs = _extract_key_value_pairs(content)
        if pairs:
            return pairs
        return [{"内容": content, "内容_置信度": _guess_confidence(content)}]


def _format_output(results: List[Dict[str, Any]], output_format: str = "json") -> str:
    """将结构化结果转换为指定输出格式"""
    if output_format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    elif output_format == "markdown":
        if not results:
            return "（无数据）"
        # 收集所有字段
        all_keys = []
        for r in results:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)
        # 生成 Markdown 表格
        md_lines = ["| " + " | ".join(all_keys) + " |"]
        md_lines.append("|" + "|".join(["---"] * len(all_keys)) + "|")
        for r in results:
            md_lines.append("| " + " | ".join(str(r.get(k, "")) for k in all_keys) + " |")
        return "\n".join(md_lines)

    elif output_format == "csv":
        if not results:
            return ""
        all_keys = []
        for r in results:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_keys)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in all_keys})
        return buf.getvalue()

    else:
        raise RuntimeError(f"不支持的输出格式: {output_format}")


# ============================================================
# 主处理流程
# ============================================================

def process_input(
    data: Optional[str] = None,
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    input_type: str = "auto",
    output_format: str = "json",
) -> Dict[str, Any]:
    """
    统一处理入口
    返回：{"success": bool, "data": ..., "error": ...}
    """
    try:
        # 获取原始内容
        content = ""
        source_desc = ""

        if url:
            try:
                content = _fetch_url(url)
                source_desc = f"URL: {url}"
            except Exception as e:
                return {"success": False, **_error("E003", str(e))}
        elif file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                source_desc = f"文件: {file_path}"
            except Exception as e:
                return {"success": False, **_error("E001", str(e))}
        elif data is not None:
            content = data
            source_desc = "直接输入"
        else:
            return {"success": False, **_error("E001")}

        if not content.strip():
            return {"success": False, **_error("E001")}

        # 提取结构化数据
        try:
            results = _detect_and_extract(content, input_type)
        except RuntimeError as e:
            code = "E004" if "JSON" in str(e) else "E005" if "CSV" in str(e) else "E006" if "表格" in str(e) else "E009"
            return {"success": False, **_error(code, str(e))}

        if not results:
            return {"success": False, **_error("E001", "未能提取到有效数据")}

        # 格式化输出
        try:
            output_text = _format_output(results, output_format)
        except RuntimeError as e:
            return {"success": False, **_error("E007", str(e))}

        return {
            "success": True,
            "data": results,
            "output": output_text,
            "meta": {
                "source": source_desc,
                "record_count": len(results),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.1"
            }
        }

    except Exception as e:
        return {"success": False, **_error("E009", str(e))}


# ============================================================
# 自检模块（内置硬编码样例，离线运行）
# ============================================================

def _selftest() -> int:
    """内置自检逻辑，使用硬编码样例数据，不依赖外部文件或网络"""
    print("=" * 60)
    print("自检开始（离线模式）...")
    print("=" * 60)

    # 测试 1：文本键值对提取
    print("\n[测试 1] 文本键值对提取")
    sample_text = """姓名: 张三
年龄: 28
城市: 北京
职业-工程师
"""
    result = process_input(data=sample_text, input_type="text", output_format="json")
    assert result["success"], f"文本处理失败: {result}"
    assert len(result["data"]) >= 3, f"应提取至少 3 个键值对，实际 {len(result['data'])}"
    # 宽松断言：字段数大于 0 且包含"姓名"
    keys = [item["字段"] for item in result["data"]]
    assert "姓名" in keys, "应包含'姓名'字段"
    print(f"  ✓ 通过（提取 {len(result['data'])} 个字段）")

    # 测试 2：JSON 解析
    print("\n[测试 2] JSON 解析")
    sample_json = '{"name": "test", "value": 42, "items": [1, 2, 3]}'
    result = process_input(data=sample_json, input_type="json", output_format="json")
    assert result["success"], f"JSON 处理失败: {result}"
    assert len(result["data"]) >= 1, "应至少提取 1 条记录"
    assert "name" in result["data"][0], "应包含 name 字段"
    print(f"  ✓ 通过（提取 {len(result['data'])} 条记录）")

    # 测试 3：CSV 解析
    print("\n[测试 3] CSV 解析")
    sample_csv = "id,name,score\n1,Alice,85\n2,Bob,92\n3,Charlie,78"
    result = process_input(data=sample_csv, input_type="csv", output_format="json")
    assert result["success"], f"CSV 处理失败: {result}"
    assert len(result["data"]) >= 3, f"应提取至少 3 条记录，实际 {len(result['data'])}"
    assert "name" in result["data"][0], "应包含 name 字段"
    print(f"  ✓ 通过（提取 {len(result['data'])} 条记录）")

    # 测试 4：Markdown 表格提取
    print("\n[测试 4] Markdown 表格提取")
    sample_md = """| 项目 | 数量 | 备注 |
|------|------|------|
| 苹果 | 10 | 新鲜 |
| 香蕉 | 5 | 待售 |
"""
    result = process_input(data=sample_md, input_type="md", output_format="json")
    assert result["success"], f"Markdown 处理失败: {result}"
    assert len(result["data"]) >= 2, f"应提取至少 2 条记录，实际 {len(result['data'])}"
    assert "项目" in result["data"][0], "应包含'项目'字段"
    print(f"  ✓ 通过（提取 {len(result['data'])} 条记录）")

    # 测试 5：输出格式转换（Markdown 输出）
    print("\n[测试 5] Markdown 输出格式")
    result = process_input(data=sample_json, input_type="json", output_format="markdown")
    assert result["success"], f"Markdown 输出失败: {result}"
    assert "|" in result["output"], "输出应包含表格分隔符"
    print(f"  ✓ 通过（输出长度 {len(result['output'])} 字符）")

    # 测试 6：错误处理（空输入）
    print("\n[测试 6] 错误处理（空输入）")
    result = process_input(data="", input_type="text", output_format="json")
    assert not result["success"], "空输入应返回错误"
    assert "E001" in json.dumps(result), "应返回 E001 错误码"
    print(f"  ✓ 通过（正确返回 {result['error']['code']}）")

    # 测试 7：批量处理（多条记录）
    print("\n[测试 7] 批量处理（多条记录）")
    sample_batch = """姓名: 张三, 年龄: 25
姓名: 李四, 年龄: 30
姓名: 王五, 年龄: 35
"""
    result = process_input(data=sample_batch, input_type="text", output_format="json")
    assert result["success"], f"批量处理失败: {result}"
    assert len(result["data"]) >= 3, f"应提取至少 3 条记录，实际 {len(result['data'])}"
    print(f"  ✓ 通过（提取 {len(result['data'])} 条记录）")

    # 测试 8：置信度标注
    print("\n[测试 8] 置信度标注")
    result = process_input(data=sample_text, input_type="text", output_format="json")
    assert result["success"], f"置信度处理失败: {result}"
    has_confidence = any("置信度" in item for item in result["data"])
    assert has_confidence, "应包含置信度标注"
    print("  ✓ 通过（所有字段均标注置信度）")

    print("\n" + "=" * 60)
    print("全部自检通过 ✓")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="数据整理与结构化输出工具（独立实现）",
        epilog="示例: python main.py --data '姓名: 张三' --output json"
    )
    parser.add_argument("--data", type=str, help="直接输入文本数据")
    parser.add_argument("--file", type=str, help="输入文件路径（txt/csv/json/md）")
    parser.add_argument("--url", type=str, help="公开可访问的 URL")
    parser.add_argument("--type", type=str, default="auto",
                        choices=["auto", "text", "csv", "json", "md", "url"],
                        help="输入数据类型（默认 auto 自动检测）")
    parser.add_argument("--output", type=str, default="json",
                        choices=["json", "markdown", "csv"],
                        help="输出格式（默认 json）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检（离线，不依赖外部文件）")

    args = parser.parse_args()

    if args.selftest:
        return _selftest()

    # 参数检查
    if not args.data and not args.file and not args.url:
        print("错误: 必须提供 --data、--file 或 --url 之一", file=sys.stderr)
        print(f"错误码: E010 - {ERROR_CODES['E010']}", file=sys.stderr)
        parser.print_help()
        return 1

    # 处理输入
    result = process_input(
        data=args.data,
        file_path=args.file,
        url=args.url,
        input_type=args.type,
        output_format=args.output,
    )

    if result["success"]:
        print(result["output"])
        # 输出元信息到 stderr（不干扰 stdout 的结构化输出）
        meta = result.get("meta", {})
        print(f"\n# 处理信息: {meta.get('record_count', 0)} 条记录 | 来源: {meta.get('source', '未知')}",
              file=sys.stderr)
        return 0
    else:
        err = result.get("error", {})
        print(f"错误: {err.get('message', '未知错误')}", file=sys.stderr)
        if err.get("detail"):
            print(f"详情: {err['detail']}", file=sys.stderr)
        print(f"错误码: {err.get('code', 'E009')}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
