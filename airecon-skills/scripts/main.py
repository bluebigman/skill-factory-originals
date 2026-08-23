#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
airecon-skills 生产级实现

功能：
- 将任意文本/CSV/JSON/URL 内容解析为结构化数据
- 支持字段映射、批量处理、置信度标注
- 输出格式：JSON / CSV / Markdown
- 内置 --dry-run 预览、--verbose 详细日志、--selftest 自检

用法：
    python run.py --input "文本内容" [--format json|csv|md] [--fields 字段1,字段2]
    python run.py --file 输入文件 [--format json|csv|md] [--fields 字段1,字段2]
    python run.py --url https://example.com [--timeout 10] [--fields 字段1,字段2]
    python run.py --selftest

错误码：
    E001 参数错误
    E002 输入为空
    E003 文件不存在
    E004 编码错误
    E005 解析失败
    E006 网络请求失败
    E007 输出格式错误
    E008 字段映射失败
    E009 置信度过低
    E010 未知错误
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


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
def _now_utc() -> str:
    """返回 UTC 时间字符串"""
    return datetime.now(timezone.utc).isoformat()


def _safe_read_file(file_path: str) -> str:
    """安全读取文件，支持多编码"""
    if not os.path.exists(file_path):
        raise AppError("E003", f"文件不存在: {file_path}")
    
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error = None
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            raise AppError("E010", f"读取文件失败: {e}")
    
    raise AppError("E004", f"无法识别文件编码: {last_error}")


def _safe_write_file(file_path: str, content: str, dry_run: bool = False) -> None:
    """原子化写入文件，支持 dry-run 模式"""
    if not dry_run:
        # 原子化写入：先写临时文件，再替换
        dir_path = os.path.dirname(os.path.abspath(file_path))
        fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(temp_path, file_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise AppError("E010", f"写入文件失败: {e}")
        print(f"[写入] {file_path}")
        return
    print(f"[dry-run] 将写入 {file_path}（{len(content)} 字节），未落盘")


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


def _extract_name(text: str) -> Optional[str]:
    """提取姓名（中文2-4字或英文名）"""
    # 中文姓名：2-4个汉字
    cn_pattern = r'[\u4e00-\u9fa5]{2,4}'
    # 英文姓名：首字母大写的单词组合
    en_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    
    # 优先匹配中文姓名
    cn_matches = re.findall(cn_pattern, text)
    if cn_matches:
        # 过滤掉常见非姓名词
        stopwords = {"公司", "有限", "集团", "地址", "电话", "邮箱", "日期"}
        for name in cn_matches:
            if name not in stopwords and len(name) >= 2:
                return name
    
    # 匹配英文姓名
    en_matches = re.findall(en_pattern, text)
    if en_matches:
        for name in en_matches:
            if len(name.split()) >= 2:  # 至少两个单词
                return name
    
    return None


def _extract_address(text: str) -> Optional[str]:
    """提取地址（含省/市/区/路/号关键词）"""
    pattern = r'[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|乡|村|路|街|道|号|栋|楼|室)'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def _extract_amount(text: str) -> Optional[str]:
    """提取金额"""
    pattern = r'(?:￥|¥|RMB|CNY)?\s*\d+(?:\.\d{1,2})?\s*(?:元|块|人民币)?'
    match = re.search(pattern, text)
    return match.group(0).strip() if match else None


# ============================================================
# 字段提取器注册表
# ============================================================
FIELD_EXTRACTORS = {
    "name": _extract_name,
    "phone": _extract_phone,
    "email": _extract_email,
    "date": _extract_date,
    "address": _extract_address,
    "amount": _extract_amount,
}

DEFAULT_FIELDS = ["name", "phone", "email", "date", "address"]


# ============================================================
# 核心解析逻辑
# ============================================================
def parse_record(text: str, fields: List[str]) -> Dict[str, Any]:
    """解析单条记录，返回字段与置信度"""
    if not text or not text.strip():
        raise AppError("E002", "输入为空")
    
    result: Dict[str, Any] = {}
    placeholders = 0
    
    for field in fields:
        extractor = FIELD_EXTRACTORS.get(field)
        if not extractor:
            raise AppError("E008", f"不支持的字段: {field}")
        
        try:
            value = extractor(text)
        except Exception as e:
            print(f"[WARN] 字段 {field} 提取失败: {e}", file=sys.stderr)
            value = None
        
        if value:
            result[field] = value
        else:
            result[field] = f"[需核实:{field}]"
            placeholders += 1
    
    # 计算置信度
    total_fields = len(fields)
    if total_fields == 0:
        confidence = 0.0
    elif placeholders == 0:
        confidence = 0.95 + (0.05 * min(len(text) / 100, 1.0))  # 文本越长置信度略高
    elif placeholders == 1:
        confidence = 0.7 + (0.2 * (1 - placeholders / total_fields))
    else:
        confidence = 0.5 + (0.2 * (1 - placeholders / total_fields))
    
    confidence = max(0.0, min(1.0, confidence))
    result["confidence"] = round(confidence, 2)
    
    # 标记需要人工复核的记录
    if placeholders > total_fields * 0.5:
        result["needs_review"] = True
    
    return result


def parse_batch(items: List[str], fields: List[str]) -> List[Dict[str, Any]]:
    """批量解析多条记录"""
    results = []
    for item in items:
        try:
            record = parse_record(item, fields)
            results.append(record)
        except AppError as e:
            print(f"[WARN] 记录解析失败: {e}", file=sys.stderr)
            results.append({
                "error": e.code,
                "message": e.message,
                "confidence": 0.0,
                "needs_review": True,
            })
    return results


def detect_input_type(text: str) -> str:
    """检测输入数据类型"""
    if not text or not text.strip():
        return "empty"
    
    stripped = text.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return "json_array"
    if stripped.startswith("{") and stripped.endswith("}"):
        return "json_object"
    if "," in stripped and "\n" in stripped:
        return "csv"
    if "|" in stripped and "\n" in stripped:
        return "markdown_table"
    return "text"


def parse_input(text: str, fields: List[str]) -> Dict[str, Any]:
    """解析输入数据，自动识别格式"""
    input_type = detect_input_type(text)
    
    if input_type == "empty":
        raise AppError("E002", "输入为空")
    
    if input_type == "json_array":
        try:
            items = json.loads(text)
            if not isinstance(items, list):
                raise AppError("E005", "JSON 数组格式错误")
            records = parse_batch([str(item) for item in items], fields)
        except json.JSONDecodeError as e:
            raise AppError("E005", f"JSON 解析失败: {e}")
    elif input_type == "json_object":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # 将字典转为单条记录
                record = {}
                for field in fields:
                    if field in data:
                        record[field] = data[field]
                    else:
                        record[field] = f"[需核实:{field}]"
                record["confidence"] = 0.9 if len(record) > 0 else 0.0
                records = [record]
            else:
                raise AppError("E005", "JSON 对象格式错误")
        except json.JSONDecodeError as e:
            raise AppError("E005", f"JSON 解析失败: {e}")
    elif input_type == "csv":
        try:
            reader = csv.DictReader(io.StringIO(text))
            records = []
            for row in reader:
                record = {}
                for field in fields:
                    if field in row and row[field]:
                        record[field] = row[field]
                    else:
                        record[field] = f"[需核实:{field}]"
                record["confidence"] = 0.9
                records.append(record)
        except Exception as e:
            raise AppError("E005", f"CSV 解析失败: {e}")
    elif input_type == "markdown_table":
        try:
            lines = text.strip().split("\n")
            if len(lines) < 2:
                raise AppError("E005", "Markdown 表格格式错误")
            
            # 解析表头
            headers = [h.strip() for h in lines[0].split("|") if h.strip()]
            records = []
            
            for line in lines[2:]:  # 跳过表头和分隔行
                if not line.strip():
                    continue
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) != len(headers):
                    continue
                record = {}
                for i, header in enumerate(headers):
                    if header in fields:
                        record[header] = cells[i] if cells[i] else f"[需核实:{header}]"
                record["confidence"] = 0.9
                records.append(record)
        except Exception as e:
            raise AppError("E005", f"Markdown 表格解析失败: {e}")
    else:
        # 纯文本：按行分割，每行一条记录
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        records = parse_batch(lines, fields)
    
    return {
        "status": "success",
        "total": len(records),
        "processed": len([r for r in records if "error" not in r]),
        "failed": len([r for r in records if "error" in r]),
        "data": records,
        "_meta": {
            "source_type": input_type,
            "batch_size": len(records),
            "avg_confidence": round(
                sum(r.get("confidence", 0) for r in records) / len(records), 2
            ) if records else 0.0,
            "timestamp": _now_utc(),
        },
    }


# ============================================================
# 输出格式化
# ============================================================
def format_output(data: Dict[str, Any], fmt: str = "json") -> str:
    """格式化输出"""
    if fmt == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif fmt == "csv":
        if not data.get("data"):
            return ""
        # 收集所有字段
        all_fields = set()
        for record in data["data"]:
            all_fields.update(record.keys())
        all_fields = sorted(all_fields)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_fields)
        writer.writeheader()
        for record in data["data"]:
            writer.writerow(record)
        return output.getvalue()
    elif fmt == "md":
        if not data.get("data"):
            return "无数据"
        # 收集所有字段
        all_fields = set()
        for record in data["data"]:
            all_fields.update(record.keys())
        all_fields = sorted(all_fields)
        
        lines = ["| " + " | ".join(all_fields) + " |"]
        lines.append("| " + " | ".join(["---"] * len(all_fields)) + " |")
        for record in data["data"]:
            lines.append("| " + " | ".join(str(record.get(f, "")) for f in all_fields) + " |")
        return "\n".join(lines)
    else:
        raise AppError("E007", f"不支持的输出格式: {fmt}")


# ============================================================
# URL 抓取
# ============================================================
def fetch_url(url: str, timeout: int = 10, max_retries: int = 3) -> str:
    """抓取 URL 内容，带超时与指数退避重试"""
    if not HAS_REQUESTS:
        raise AppError("E006", "未安装 requests 库，请先执行 pip install requests")
    
    if not url.startswith(("http://", "https://")):
        raise AppError("E006", f"无效的 URL: {url}")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            # 尝试多种编码
            for encoding in ["utf-8", "gbk", "gb18030"]:
                try:
                    return resp.content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return resp.text
        except requests.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"[WARN] 请求失败，{wait_time}秒后重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
                time.sleep(wait_time)
    
    raise AppError("E006", f"URL 抓取失败: {last_error}")


# ============================================================
# 主流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="airecon-skills 情报解析与数据转换工具")
    
    # 输入源（三选一）
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--input", type=str, help="直接输入文本内容")
    input_group.add_argument("--file", type=str, help="输入文件路径")
    input_group.add_argument("--url", type=str, help="抓取 URL 内容")
    input_group.add_argument("--selftest", action="store_true", help="运行自检")
    
    # 配置参数
    parser.add_argument("--format", choices=["json", "csv", "md"], default="json", help="输出格式")
    parser.add_argument("--fields", type=str, default=",".join(DEFAULT_FIELDS), help="要提取的字段，逗号分隔")
    parser.add_argument("--output", type=str, help="输出文件路径（默认输出到 stdout）")
    parser.add_argument("--timeout", type=int, default=10, help="URL 请求超时时间（秒）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写文件")
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")
    
    args = parser.parse_args()
    
    try:
        # 自检模式
        if args.selftest:
            run_selftest()
            return 0
        
        # 解析字段列表
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        if not fields:
            raise AppError("E008", "字段列表为空")
        
        # 获取输入内容
        if args.input:
            content = args.input
        elif args.file:
            content = _safe_read_file(args.file)
        elif args.url:
            content = fetch_url(args.url, timeout=args.timeout)
        else:
            raise AppError("E001", "请提供输入源")
        
        if args.verbose:
            print(f"[INFO] 输入类型: {detect_input_type(content)}", file=sys.stderr)
            print(f"[INFO] 字段列表: {fields}", file=sys.stderr)
        
        # 解析数据
        result = parse_input(content, fields)
        
        # 格式化输出
        output = format_output(result, args.format)
        
        # 输出结果
        if args.output:
            _safe_write_file(args.output, output, dry_run=args.dry_run)
            if not args.dry_run:
                print(f"[INFO] 结果已写入: {args.output}", file=sys.stderr)
        else:
            print(output)
        
        return 0
    
    except AppError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# ============================================================
# 自检
# ============================================================
def run_selftest():
    """运行自检，验证核心功能"""
    print("=" * 60)
    print("airecon-skills 自检")
    print("=" * 60)
    
    # 测试 1：基本文本解析
    print("\n[测试 1] 基本文本解析")
    text = "张三 13800138000 zhangsan@example.com 2024-03-15"
    result = parse_record(text, ["name", "phone", "email", "date"])
    assert result["name"] == "张三", f"姓名提取失败: {result}"
    assert result["phone"] == "13800138000", f"电话提取失败: {result}"
    assert result["email"] == "zhangsan@example.com", f"邮箱提取失败: {result}"
    assert result["date"] == "2024-03-15", f"日期提取失败: {result}"
    assert result["confidence"] >= 0.9, f"置信度异常: {result}"
    print(f"  ✓ 通过: {result}")
    
    # 测试 2：缺失字段处理
    print("\n[测试 2] 缺失字段处理")
    text = "李四 13900139000"
    result = parse_record(text, ["name", "phone", "email"])
    assert result["name"] == "李四", f"姓名提取失败: {result}"
    assert result["phone"] == "13900139000", f"电话提取失败: {result}"
    assert "[需核实" in result["email"], f"缺失字段未标记: {result}"
    assert result["confidence"] < 0.95, f"置信度应降低: {result}"
    print(f"  ✓ 通过: {result}")
    
    # 测试 3：批量解析
    print("\n[测试 3] 批量解析")
    items = [
        "王五 13700137000 wangwu@example.com",
        "赵六 13600136000 zhaoliu@example.com 2024-01-01",
        "孙七 13500135000",
    ]
    results = parse_batch(items, ["name", "phone", "email", "date"])
    assert len(results) == 3, f"批量解析数量错误: {len(results)}"
    assert all("confidence" in r for r in results), "缺少置信度字段"
    print(f"  ✓ 通过: 共 {len(results)} 条记录")
    
    # 测试 4：JSON 数组输入
    print("\n[测试 4] JSON 数组输入")
    json_input = json.dumps([
        {"name": "张三", "phone": "13800138000"},
        {"name": "李四", "phone": "13900139000"},
    ])
    result = parse_input(json_input, ["name", "phone"])
    assert result["total"] == 2, f"JSON 解析数量错误: {result['total']}"
    assert result["processed"] == 2, f"JSON 处理数量错误: {result['processed']}"
    print(f"  ✓ 通过: {result['total']} 条记录")
    
    # 测试 5：CSV 输入
    print("\n[测试 5] CSV 输入")
    csv_input = "name,phone,email\n张三,13800138000,zhangsan@example.com\n李四,13900139000,lisi@example.com"
    result = parse_input(csv_input, ["name", "phone", "email"])
    assert result["total"] == 2, f"CSV 解析数量错误: {result['total']}"
    assert result["data"][0]["name"] == "张三", f"CSV 解析内容错误: {result['data'][0]}"
    print(f"  ✓ 通过: {result['total']} 条记录")
    
    # 测试 6：空输入处理
    print("\n[测试 6] 空输入处理")
    try:
        parse_record("", ["name"])
        assert False, "空输入应抛出异常"
    except AppError as e:
        assert e.code == "E002", f"错误码错误: {e.code}"
        print(f"  ✓ 通过: 正确抛出 {e.code}")
    
    # 测试 7：输出格式化
    print("\n[测试 7] 输出格式化")
    data = {
        "status": "success",
        "total": 1,
        "processed": 1,
        "failed": 0,
        "data": [{"name": "张三", "confidence": 0.98}],
        "_meta": {"source_type": "text", "batch_size": 1, "avg_confidence": 0.98},
    }
    json_output = format_output(data, "json")
    assert json.loads(json_output)["total"] == 1, "JSON 输出格式错误"
    
    csv_output = format_output(data, "csv")
    assert "name" in csv_output, "CSV 输出缺少表头"
    
    md_output = format_output(data, "md")
    assert "| name |" in md_output, "Markdown 输出缺少表头"
    print("  ✓ 通过: JSON/CSV/Markdown 格式均正确")
    
    # 测试 8：URL 抓取（如果可用）
    print("\n[测试 8] URL 抓取")
    if HAS_REQUESTS:
        try:
            content = fetch_url("https://example.com", timeout=5, max_retries=1)
            assert len(content) > 0, "URL 抓取内容为空"
            print(f"  ✓ 通过: 抓取到 {len(content)} 字符")
        except AppError as e:
            print(f"  ⚠ 跳过: {e}")
    else:
        print("  ⚠ 跳过: 未安装 requests 库")
    
    # 测试 9：字段映射
    print("\n[测试 9] 字段映射")
    text = "张三 13800138000 zhangsan@example.com 2024-03-15 北京市朝阳区"
    result = parse_record(text, ["name", "phone", "email", "date", "address"])
    assert result["name"] == "张三", f"姓名提取失败: {result}"
    assert result["phone"] == "13800138000", f"电话提取失败: {result}"
    assert result["email"] == "zhangsan@example.com", f"邮箱提取失败: {result}"
    assert result["date"] == "2024-03-15", f"日期提取失败: {result}"
    assert "北京" in result["address"], f"地址提取失败: {result}"
    print(f"  ✓ 通过: {result}")
    
    # 测试 10：金额提取
    print("\n[测试 10] 金额提取")
    text = "商品价格 ￥199.99 元"
    result = parse_record(text, ["amount"])
    assert result["amount"] == "￥199.99 元", f"金额提取失败: {result}"
    print(f"  ✓ 通过: {result}")
    
    print("\n" + "=" * 60)
    print("所有自检通过！")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
