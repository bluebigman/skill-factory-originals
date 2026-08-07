#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
airecon-skills 独立实现脚本

功能：
- 将用户提供的任意文本数据解析为结构化结果
- 自动识别关键信息（姓名、邮箱、电话、日期、金额等）
- 对每个字段标注置信度（高/中/低）
- 支持 JSON / YAML / Markdown 三种输出格式
- 支持批量处理多条记录

用法：
    python main.py --input "文本内容" [--format json|yaml|md] [--fields 字段1,字段2]
    python main.py --selftest

错误码：
    E001 参数错误
    E002 输入为空
    E003 不支持的输出格式
    E004 字段配置错误
    E005 解析失败
    E006 正则编译错误
    E007 内部逻辑错误
    E008 批量处理失败
    E009 文件读取失败
    E010 未知错误
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用异常基类"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 工具函数
# ============================================================
def _extract_email(text: str) -> Optional[str]:
    """提取邮箱地址"""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    """提取电话号码（支持中划线、空格、括号）"""
    pattern = r'(?:\+?86[- ]?)?1[3-9]\d{9}|\+?[1-9]\d{1,3}[- ]?\d{3,4}[- ]?\d{4}'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def _extract_date(text: str) -> Optional[str]:
    """提取日期（支持多种格式）"""
    patterns = [
        r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?',
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
        r'\d{1,2}月\d{1,2}日',
        r'\d{4}年\d{1,2}月\d{1,2}日',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def _extract_money(text: str) -> Optional[str]:
    """提取金额"""
    pattern = r'(?:¥|￥|RMB|CNY)?\s?\d+(?:,\d{3})*(?:\.\d{1,2})?\s?(?:元|块|万元)?'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def _extract_name(text: str) -> Optional[str]:
    """提取姓名（简单启发式：中文姓名或英文姓名）"""
    # 中文姓名：2-4个汉字，前面有"姓名/名字/联系人"等关键词
    cn_pattern = r'(?:姓名|名字|联系人)[:：\s]*([\u4e00-\u9fa5]{2,4})'
    match = re.search(cn_pattern, text)
    if match:
        return match.group(1)
    # 英文姓名：两个单词，首字母大写
    en_pattern = r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
    match = re.search(en_pattern, text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return None


def _extract_address(text: str) -> Optional[str]:
    """提取地址（简单启发式）"""
    pattern = r'(?:地址|住址|location|address)[:：\s]*([^\n，,。;；]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_id_number(text: str) -> Optional[str]:
    """提取身份证号"""
    pattern = r'\b\d{17}[\dXx]\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def _extract_company(text: str) -> Optional[str]:
    """提取公司/组织名称"""
    pattern = r'(?:公司|单位|企业|organization|company)[:：\s]*([^\n，,。;；]+)'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


# ============================================================
# 核心解析逻辑
# ============================================================
# 字段提取器注册表
FIELD_EXTRACTORS = {
    'name': _extract_name,
    'email': _extract_email,
    'phone': _extract_phone,
    'date': _extract_date,
    'money': _extract_money,
    'address': _extract_address,
    'id_number': _extract_id_number,
    'company': _extract_company,
}

# 字段中文名映射
FIELD_LABELS = {
    'name': '姓名',
    'email': '邮箱',
    'phone': '电话',
    'date': '日期',
    'money': '金额',
    'address': '地址',
    'id_number': '身份证号',
    'company': '公司',
}


def _compute_confidence(field: str, value: Optional[str], text: str) -> str:
    """
    计算字段置信度

    规则：
    - 未提取到值 -> 低
    - 提取到值且文本中有明确关键词 -> 高
    - 提取到值但无明确关键词 -> 中
    """
    if value is None:
        return "低"
    keywords = {
        'name': ['姓名', '名字', '联系人'],
        'email': ['邮箱', '邮件', 'email'],
        'phone': ['电话', '手机', '联系方式'],
        'date': ['日期', '时间', 'date'],
        'money': ['金额', '价格', '费用', 'money'],
        'address': ['地址', '住址', 'location'],
        'id_number': ['身份证', '证件号', 'id'],
        'company': ['公司', '单位', '企业', 'company'],
    }
    field_keywords = keywords.get(field, [])
    for kw in field_keywords:
        if kw.lower() in text.lower():
            return "高"
    return "中"


def parse_record(text: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    解析单条记录

    参数：
        text: 输入文本
        fields: 需要提取的字段列表，None 表示提取全部

    返回：
        结构化字典，包含字段值和置信度
    """
    if not text or not text.strip():
        raise AppError("E002", "输入文本为空")

    # 确定要提取的字段
    if fields is None:
        extract_fields = list(FIELD_EXTRACTORS.keys())
    else:
        extract_fields = []
        for f in fields:
            f = f.strip().lower()
            if f not in FIELD_EXTRACTORS:
                raise AppError("E004", f"不支持的字段: {f}")
            extract_fields.append(f)

    result = {}
    for field in extract_fields:
        try:
            extractor = FIELD_EXTRACTORS[field]
            value = extractor(text)
            confidence = _compute_confidence(field, value, text)
            result[field] = {
                "value": value,
                "confidence": confidence,
            }
        except Exception as e:
            raise AppError("E005", f"解析字段 {field} 失败: {str(e)}")

    return result


def parse_batch(texts: List[str], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """批量解析多条记录"""
    if not texts:
        raise AppError("E002", "输入列表为空")
    results = []
    for i, text in enumerate(texts):
        try:
            results.append(parse_record(text, fields))
        except AppError as e:
            raise AppError("E008", f"第 {i+1} 条记录解析失败: {e.message}")
    return results


# ============================================================
# 输出格式化
# ============================================================
def format_json(data: Any) -> str:
    """格式化为 JSON"""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        raise AppError("E007", f"JSON 格式化失败: {str(e)}")


def format_markdown(data: Dict[str, Any]) -> str:
    """格式化为 Markdown 表格"""
    if isinstance(data, list):
        # 批量模式：生成多个表格
        lines = []
        for i, record in enumerate(data, 1):
            lines.append(f"### 记录 {i}")
            lines.append("")
            lines.append("| 字段 | 值 | 置信度 |")
            lines.append("|------|-----|--------|")
            for field, info in record.items():
                label = FIELD_LABELS.get(field, field)
                value = info.get("value", "")
                if value is None:
                    value = "-"
                confidence = info.get("confidence", "低")
                lines.append(f"| {label} | {value} | {confidence} |")
            lines.append("")
        return "\n".join(lines)
    else:
        # 单条模式
        lines = ["| 字段 | 值 | 置信度 |", "|------|-----|--------|"]
        for field, info in data.items():
            label = FIELD_LABELS.get(field, field)
            value = info.get("value", "")
            if value is None:
                value = "-"
            confidence = info.get("confidence", "低")
            lines.append(f"| {label} | {value} | {confidence} |")
        return "\n".join(lines)


def format_yaml(data: Any) -> str:
    """格式化为 YAML（简化实现，仅处理本工具的数据结构）"""
    def _yaml_value(value: Any, indent: int = 0) -> str:
        prefix = " " * indent
        if value is None:
            return f"{prefix}null"
        if isinstance(value, bool):
            return f"{prefix}{str(value).lower()}"
        if isinstance(value, (int, float)):
            return f"{prefix}{value}"
        if isinstance(value, str):
            return f"{prefix}\"{value}\""
        if isinstance(value, list):
            if not value:
                return f"{prefix}[]"
            lines = [f"{prefix}- {_yaml_value(value[0], indent + 2).strip()}"]
            for item in value[1:]:
                lines.append(f"{prefix}  - {_yaml_value(item, indent + 2).strip()}")
            return "\n".join(lines)
        if isinstance(value, dict):
            if not value:
                return f"{prefix}{{}}"
            lines = []
            for k, v in value.items():
                lines.append(f"{prefix}{k}: {_yaml_value(v, indent + 2).strip()}")
            return "\n".join(lines)
        return f"{prefix}{value}"

    return _yaml_value(data)


# ============================================================
# 命令行入口
# ============================================================
def run_selftest() -> int:
    """
    自检函数：使用内置硬编码样例验证核心逻辑

    返回：0 表示通过，非 0 表示失败
    """
    print("开始自检...")

    # 测试样例 1：完整的联系人信息
    sample1 = "姓名：张三，电话：13812345678，邮箱：zhangsan@example.com，地址：北京市朝阳区建国路88号"
    try:
        result1 = parse_record(sample1)
        assert result1["name"]["value"] is not None, "姓名提取失败"
        assert result1["phone"]["value"] is not None, "电话提取失败"
        assert result1["email"]["value"] is not None, "邮箱提取失败"
        assert result1["address"]["value"] is not None, "地址提取失败"
        assert result1["name"]["confidence"] == "高", "姓名置信度应为高"
        print("✓ 样例1（完整联系人）通过")
    except AssertionError as e:
        print(f"✗ 样例1失败: {e}")
        return 1
    except AppError as e:
        print(f"✗ 样例1异常: {e.message}")
        return 1

    # 测试样例 2：不完整信息（缺少部分字段）
    sample2 = "今天开会讨论项目预算，预计花费 5000 元，会议日期是 2025-03-15"
    try:
        result2 = parse_record(sample2)
        # 金额和日期应该有值
        assert result2["money"]["value"] is not None, "金额提取失败"
        assert result2["date"]["value"] is not None, "日期提取失败"
        # 姓名应该没有值（低置信度）
        assert result2["name"]["value"] is None, "不应提取到姓名"
        assert result2["name"]["confidence"] == "低", "姓名置信度应为低"
        print("✓ 样例2（部分信息）通过")
    except AssertionError as e:
        print(f"✗ 样例2失败: {e}")
        return 1
    except AppError as e:
        print(f"✗ 样例2异常: {e.message}")
        return 1

    # 测试样例 3：批量处理
    try:
        batch = [
            "联系人：李四，手机：13912345678，邮箱：lisi@test.com",
            "项目A预算：20000 元，截止日期：2025年6月30日",
        ]
        results = parse_batch(batch)
        assert len(results) == 2, "批量处理数量不对"
        assert results[0]["name"]["value"] is not None, "批量第1条姓名提取失败"
        assert results[1]["money"]["value"] is not None, "批量第2条金额提取失败"
        print("✓ 样例3（批量处理）通过")
    except AssertionError as e:
        print(f"✗ 样例3失败: {e}")
        return 1
    except AppError as e:
        print(f"✗ 样例3异常: {e.message}")
        return 1

    # 测试样例 4：输出格式
    try:
        sample4 = "姓名：王五，电话：13712345678"
        result4 = parse_record(sample4)
        json_str = format_json(result4)
        assert json_str is not None and len(json_str) > 0, "JSON 格式化失败"
        md_str = format_markdown(result4)
        assert md_str is not None and "姓名" in md_str, "Markdown 格式化失败"
        yaml_str = format_yaml(result4)
        assert yaml_str is not None and len(yaml_str) > 0, "YAML 格式化失败"
        print("✓ 样例4（输出格式）通过")
    except AssertionError as e:
        print(f"✗ 样例4失败: {e}")
        return 1
    except AppError as e:
        print(f"✗ 样例4异常: {e.message}")
        return 1

    # 测试样例 5：边界情况 - 空输入
    try:
        parse_record("")
        print("✗ 样例5（空输入）应当抛出异常")
        return 1
    except AppError as e:
        assert e.code == "E002", f"错误码应为 E002，实际为 {e.code}"
        print("✓ 样例5（空输入处理）通过")
    except Exception as e:
        print(f"✗ 样例5异常: {str(e)}")
        return 1

    print("\n所有自检通过！")
    return 0


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="airecon-skills: 数据解析、结构化输出、置信度标注工具",
        epilog="示例: python main.py --input '姓名：张三，电话：13812345678' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="输入文本内容")
    parser.add_argument("--file", "-f", type=str, help="从文件读取输入（每行一条记录）")
    parser.add_argument("--format", "-fmt", type=str, default="json",
                        choices=["json", "yaml", "md", "markdown"],
                        help="输出格式: json/yaml/md (默认: json)")
    parser.add_argument("--fields", type=str, default=None,
                        help="需要提取的字段，逗号分隔 (默认: 全部字段)")
    parser.add_argument("--selftest", action="store_true",
                        help="运行自检函数，无需其他参数")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 检查输入
    if not args.input and not args.file:
        parser.print_help()
        print("\n错误: 必须提供 --input 或 --file 参数", file=sys.stderr)
        return 1

    try:
        # 读取输入
        if args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    raise AppError("E002", "文件内容为空")
                batch_mode = len(lines) > 1
                data = lines
            except OSError as e:
                raise AppError("E009", f"文件读取失败: {str(e)}")
        else:
            data = args.input
            batch_mode = False

        # 解析字段配置
        fields = None
        if args.fields:
            fields = args.fields.split(",")
            fields = [f.strip() for f in fields if f.strip()]

        # 执行解析
        if batch_mode:
            results = parse_batch(data, fields)
        else:
            results = parse_record(data, fields)

        # 格式化输出
        fmt = args.format.lower()
        if fmt == "json":
            output = format_json(results)
        elif fmt in ("md", "markdown"):
            output = format_markdown(results)
        elif fmt == "yaml":
            output = format_yaml(results)
        else:
            raise AppError("E003", f"不支持的输出格式: {args.format}")

        # 打印结果
        print(output)
        return 0

    except AppError as e:
        print(f"错误: {e.code} - {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: E010 - 未知错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
