#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fastagent-plugins 技能实现脚本

功能：将用户提供的任意数据、文件或URL转换为结构化结果，并标注置信度。
本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件读取失败：文件不存在或无法读取",
    "E003": "文件解析失败：文件格式不支持或内容损坏",
    "E004": "URL访问失败：无法访问指定的URL",
    "E005": "URL解析失败：URL内容无法解析为有效数据",
    "E006": "数据转换失败：无法将输入转换为目标格式",
    "E007": "批量处理失败：批次中部分条目处理出错",
    "E008": "输出生成失败：无法生成指定格式的输出",
    "E009": "内部逻辑错误：发生未预期的异常",
    "E010": "输入数据为空：没有可处理的内容",
}

# 支持的输入文件扩展名
SUPPORTED_EXTENSIONS = {".txt", ".csv", ".json", ".md"}

# 置信度等级
CONFIDENCE_LEVELS = ["高", "中", "低"]


class FastAgentError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, error_code: str, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


def extract_fields_from_text(text: str) -> Dict[str, Any]:
    """
    从纯文本中提取关键字段。
    识别常见模式：邮箱、电话、日期、URL、IP地址等。
    """
    if not text or not text.strip():
        return {}

    fields: Dict[str, Any] = {}

    # 提取邮箱
    email_pattern = r'[\w\.\-]+@[\w\-]+(?:\.[\w\-]+)+'
    emails = re.findall(email_pattern, text)
    if emails:
        fields["emails"] = list(set(emails))

    # 提取电话号码（简单模式，支持中划线、空格、括号）
    phone_pattern = r'(?:\+?\d{1,3}[- ]?)?\(?\d{2,4}\)?[- ]?\d{3,4}[- ]?\d{3,4}'
    phones = re.findall(phone_pattern, text)
    if phones:
        fields["phones"] = list(set(phones))

    # 提取日期（支持多种格式）
    date_pattern = r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
    dates = re.findall(date_pattern, text)
    if dates:
        fields["dates"] = list(set(dates))

    # 提取URL
    url_pattern = r'https?://[^\s<>"\']+'
    urls = re.findall(url_pattern, text)
    if urls:
        fields["urls"] = list(set(urls))

    # 提取IP地址
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ips = re.findall(ip_pattern, text)
    if ips:
        fields["ips"] = list(set(ips))

    # 提取标题（假设第一行非空文本为标题）
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        fields["title"] = lines[0][:100]  # 截断长标题

    # 统计信息
    fields["char_count"] = len(text)
    fields["word_count"] = len(re.findall(r'\b\w+\b', text))

    return fields


def parse_csv_content(content: str) -> List[Dict[str, Any]]:
    """解析CSV内容为字典列表"""
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = [dict(row) for row in reader]
        return rows
    except Exception as exc:
        raise FastAgentError("E003", f"CSV解析失败: {exc}") from exc


def parse_json_content(content: str) -> Any:
    """解析JSON内容"""
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise FastAgentError("E003", f"JSON解析失败: {exc}") from exc


def parse_markdown_content(content: str) -> Dict[str, Any]:
    """解析Markdown内容，提取标题和表格"""
    result: Dict[str, Any] = {}
    headings = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
    if headings:
        result["headings"] = headings

    # 提取表格行
    table_rows = []
    for line in content.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells:
                table_rows.append(cells)
    if table_rows:
        result["tables"] = table_rows

    # 提取链接
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    if links:
        result["links"] = [{"text": t, "url": u} for t, u in links]

    return result


def parse_file_content(file_path: str) -> Tuple[str, Any]:
    """
    根据文件扩展名解析文件内容。
    返回 (内容类型, 解析后的数据)
    """
    path = Path(file_path)
    if not path.exists():
        raise FastAgentError("E002", f"文件不存在: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise FastAgentError("E003", f"不支持的文件格式: {ext}")

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise FastAgentError("E002", f"文件读取失败: {exc}") from exc

    if not content.strip():
        raise FastAgentError("E010", "文件内容为空")

    if ext == ".csv":
        return "csv", parse_csv_content(content)
    elif ext == ".json":
        return "json", parse_json_content(content)
    elif ext == ".md":
        return "markdown", parse_markdown_content(content)
    else:  # .txt 和其他文本
        return "text", content


def fetch_url_content(url: str) -> str:
    """从URL获取文本内容"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FastAgent/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            # 尝试多种编码
            for encoding in ["utf-8", "gbk", "latin-1"]:
                try:
                    return data.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise FastAgentError("E004", f"URL访问失败: {exc}") from exc


def calculate_confidence(data: Any) -> str:
    """
    根据数据完整性和结构计算置信度。
    宽松规则：有数据返回高，部分数据返回中，几乎无数据返回低。
    """
    if data is None:
        return "低"

    if isinstance(data, dict):
        if len(data) >= 3:
            return "高"
        elif len(data) >= 1:
            return "中"
        else:
            return "低"
    elif isinstance(data, list):
        if len(data) >= 5:
            return "高"
        elif len(data) >= 1:
            return "中"
        else:
            return "低"
    elif isinstance(data, str):
        if len(data.strip()) >= 100:
            return "高"
        elif len(data.strip()) >= 10:
            return "中"
        else:
            return "低"
    else:
        return "中"


def process_text_input(text: str) -> Dict[str, Any]:
    """处理纯文本输入"""
    if not text or not text.strip():
        raise FastAgentError("E010", "输入文本为空")

    fields = extract_fields_from_text(text)
    if not fields:
        # 至少返回基本统计
        fields = {
            "content_preview": text[:200],
            "char_count": len(text),
            "word_count": len(re.findall(r'\b\w+\b', text)),
        }

    confidence = calculate_confidence(fields)
    return {
        "input_type": "text",
        "structured_data": fields,
        "confidence": confidence,
        "field_count": len(fields),
    }


def process_file_input(file_path: str) -> Dict[str, Any]:
    """处理文件输入"""
    content_type, data = parse_file_content(file_path)

    if content_type == "text":
        fields = extract_fields_from_text(data)
        structured = fields
    elif content_type == "csv":
        structured = {"rows": data, "row_count": len(data)}
    elif content_type == "json":
        structured = data if isinstance(data, dict) else {"data": data}
    elif content_type == "markdown":
        structured = data
    else:
        structured = {"content": data}

    confidence = calculate_confidence(structured)
    return {
        "input_type": f"file:{content_type}",
        "structured_data": structured,
        "confidence": confidence,
        "field_count": len(structured) if isinstance(structured, dict) else 1,
    }


def process_url_input(url: str) -> Dict[str, Any]:
    """处理URL输入"""
    content = fetch_url_content(url)

    # 尝试解析JSON
    if url.endswith(".json") or content.strip().startswith("{"):
        try:
            data = parse_json_content(content)
            structured = data if isinstance(data, dict) else {"data": data}
            input_type = "url:json"
        except FastAgentError:
            structured = extract_fields_from_text(content)
            input_type = "url:text"
    else:
        structured = extract_fields_from_text(content)
        input_type = "url:text"

    if not structured:
        structured = {"content_preview": content[:200]}

    confidence = calculate_confidence(structured)
    return {
        "input_type": input_type,
        "structured_data": structured,
        "confidence": confidence,
        "field_count": len(structured) if isinstance(structured, dict) else 1,
    }


def process_batch_inputs(inputs: List[str], input_type: str = "auto") -> Dict[str, Any]:
    """
    批量处理多个输入（最多100条）
    input_type: auto/text/file/url
    """
    if len(inputs) > 100:
        raise FastAgentError("E007", f"批量处理超过100条限制: {len(inputs)}")

    results = []
    errors = []

    for idx, item in enumerate(inputs):
        try:
            if input_type == "text" or (input_type == "auto" and not item.startswith(("http", "file:"))):
                result = process_text_input(item)
            elif input_type == "url" or (input_type == "auto" and item.startswith("http")):
                result = process_url_input(item)
            elif input_type == "file" or (input_type == "auto" and item.startswith("file:")):
                file_path = item[5:] if item.startswith("file:") else item
                result = process_file_input(file_path)
            else:
                # 尝试自动检测
                if item.startswith("http"):
                    result = process_url_input(item)
                elif Path(item).exists():
                    result = process_file_input(item)
                else:
                    result = process_text_input(item)

            results.append({"index": idx, "status": "success", "result": result})
        except FastAgentError as exc:
            errors.append({"index": idx, "status": "error", "error_code": exc.error_code, "message": exc.message})
        except Exception as exc:
            errors.append({"index": idx, "status": "error", "error_code": "E009", "message": str(exc)})

    return {
        "batch_size": len(inputs),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


def generate_output(data: Dict[str, Any], output_format: str = "json") -> str:
    """生成指定格式的输出"""
    if output_format == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif output_format == "csv":
        # 将结构化数据转为CSV
        structured = data.get("structured_data", {})
        if isinstance(structured, dict):
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["字段", "值"])
            for key, value in structured.items():
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                writer.writerow([key, value])
            return output.getvalue()
        else:
            return str(structured)
    elif output_format == "markdown":
        lines = ["# 结构化输出结果", ""]
        lines.append("- **输入类型**: " + str(data.get('input_type', '未知')))
        lines.append("- **置信度**: " + str(data.get('confidence', '未知')))
        lines.append("- **字段数量**: " + str(data.get('field_count', 0)))
        lines.append("")
        lines.append("## 结构化数据")
        lines.append("")
        structured = data.get("structured_data", {})
        if isinstance(structured, dict):
            lines.append("| 字段 | 值 |")
            lines.append("|------|-----|")
            for key, value in structured.items():
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                lines.append("| " + str(key) + " | " + str(value) + " |")
        else:
            lines.append(str(structured))
        return "\n".join(lines)
    else:
        raise FastAgentError("E008", f"不支持的输出格式: {output_format}")


def run_selftest() -> bool:
    """运行自测，验证核心功能"""
    print("开始运行自测...")
    
    # 测试1：文本处理
    test_text = "联系人：张三，邮箱：zhangsan@example.com，电话：138-1234-5678。"
    try:
        result = process_text_input(test_text)
        assert result["input_type"] == "text"
        assert "emails" in result["structured_data"]
        assert "phones" in result["structured_data"]
        print("✓ 文本处理测试通过")
    except Exception as e:
        print(f"✗ 文本处理测试失败: {e}")
        return False
    
    # 测试2：JSON解析
    test_json = '{"name": "张三", "age": 30, "city": "北京"}'
    try:
        data = parse_json_content(test_json)
        assert data["name"] == "张三"
        assert data["age"] == 30
        print("✓ JSON解析测试通过")
    except Exception as e:
        print(f"✗ JSON解析测试失败: {e}")
        return False
    
    # 测试3：CSV解析
    test_csv = "name,age,city\n张三,30,北京\n李四,25,上海"
    try:
        rows = parse_csv_content(test_csv)
        assert len(rows) == 2
        assert rows[0]["name"] == "张三"
        print("✓ CSV解析测试通过")
    except Exception as e:
        print(f"✗ CSV解析测试失败: {e}")
        return False
    
    # 测试4：置信度计算
    try:
        assert calculate_confidence({"a": 1, "b": 2, "c": 3}) == "高"
        assert calculate_confidence({"a": 1}) == "中"
        assert calculate_confidence({}) == "低"
        assert calculate_confidence([]) == "低"
        assert calculate_confidence(["a", "b", "c", "d", "e"]) == "高"
        print("✓ 置信度计算测试通过")
    except Exception as e:
        print(f"✗ 置信度计算测试失败: {e}")
        return False
    
    # 测试5：输出格式生成
    try:
        test_data = {
            "input_type": "text",
            "structured_data": {"name": "张三", "age": 30},
            "confidence": "高",
            "field_count": 2
        }
        json_output = generate_output(test_data, "json")
        assert json.loads(json_output)["confidence"] == "高"
        
        md_output = generate_output(test_data, "markdown")
        assert "# 结构化输出结果" in md_output
        assert "| 字段 | 值 |" in md_output
        
        csv_output = generate_output(test_data, "csv")
        assert "字段,值" in csv_output or "字段,值" in csv_output
        
        print("✓ 输出格式生成测试通过")
    except Exception as e:
        print(f"✗ 输出格式生成测试失败: {e}")
        return False
    
    # 测试6：批量处理
    try:
        batch_result = process_batch_inputs(["测试文本1", "测试文本2", "测试文本3"])
        assert batch_result["success_count"] == 3
        assert batch_result["error_count"] == 0
        print("✓ 批量处理测试通过")
    except Exception as e:
        print(f"✗ 批量处理测试失败: {e}")
        return False
    
    # 测试7：错误处理
    try:
        process_file_input("nonexistent_file.txt")
        print("✗ 错误处理测试失败: 应该抛出异常")
        return False
    except FastAgentError as e:
        assert e.error_code == "E002"
        print("✓ 错误处理测试通过")
    except Exception as e:
        print(f"✗ 错误处理测试失败: {e}")
        return False
    
    print("所有自测通过！")
    return True


def main():
    parser = argparse.ArgumentParser(description="fastagent-plugins 技能实现脚本")
    parser.add_argument("--text", type=str, help="处理纯文本输入")
    parser.add_argument("--file", type=str, help="处理文件输入")
    parser.add_argument("--url", type=str, help="处理URL输入")
    parser.add_argument("--batch", type=str, help="批量处理，逗号分隔的输入")
    parser.add_argument("--batch-type", type=str, default="auto", 
                        choices=["auto", "text", "file", "url"], help="批量处理输入类型")
    parser.add_argument("--output", type=str, default="json", 
                        choices=["json", "csv", "markdown"], help="输出格式")
    parser.add_argument("--selftest", action="store_true", help="运行自测")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    try:
        if args.text:
            result = process_text_input(args.text)
        elif args.file:
            result = process_file_input(args.file)
        elif args.url:
            result = process_url_input(args.url)
        elif args.batch:
            inputs = [item.strip() for item in args.batch.split(",")]
            result = process_batch_inputs(inputs, args.batch_type)
        else:
            parser.print_help()
            return
        
        output = generate_output(result, args.output)
        print(output)
        
    except FastAgentError as exc:
        print(f"错误: [{exc.error_code}] {exc.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"错误: [E009] 发生未预期的异常: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
