#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awsome-cash — 数据解析与结构化提取工具
版本: 1.0.2
许可: MIT
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple, Union
from urllib.parse import urlparse
from urllib.request import urlopen

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误",
    "E002": "文件读取失败",
    "E003": "文件格式不支持",
    "E004": "JSON解析失败",
    "E005": "CSV解析失败",
    "E006": "URL访问失败",
    "E007": "文本解析失败",
    "E008": "格式转换失败",
    "E009": "内部逻辑错误",
    "E010": "自检失败",
}


class CashError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


def parse_text(text: str) -> Dict[str, Any]:
    """
    从纯文本中提取关键字段（姓名、日期、金额）。
    使用正则模式匹配，不进行语义推理。
    """
    if not isinstance(text, str) or not text.strip():
        raise CashError("E007", "输入文本为空或类型错误")

    result: Dict[str, Any] = {}

    # 提取姓名（支持中英文，常见格式）
    # 模式：姓名：XXX 或 姓名:XXX 或 姓名 XXX
    name_patterns = [
        r"姓名[:：]\s*([\u4e00-\u9fa5]{2,4}|[A-Za-z\s]{2,30})",
        r"name[:：]\s*([A-Za-z\s]{2,30})",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["name"] = match.group(1).strip()
            break

    # 提取日期（支持多种格式）
    date_patterns = [
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            # 统一格式化为 YYYY-MM-DD
            date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
            date_str = date_str.replace("/", "-")
            result["date"] = date_str
            break

    # 提取金额（支持小数、千分位）
    amount_patterns = [
        r"金额[:：]\s*([¥￥]?\s*\d[\d,]*\.?\d*)",
        r"amount[:：]\s*([¥￥]?\s*\d[\d,]*\.?\d*)",
        r"([¥￥]\s*\d[\d,]*\.?\d*)",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "").replace("¥", "").replace("￥", "").strip()
            try:
                result["amount"] = float(amount_str)
            except ValueError:
                result["amount"] = amount_str
            break

    return result


def parse_file(file_path: str) -> List[Dict[str, Any]]:
    """
    解析支持的文件类型（CSV、JSON、TXT、Markdown）。
    返回结构化记录列表。
    """
    if not os.path.exists(file_path):
        raise CashError("E002", f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise CashError("E002", f"文件读取失败: {str(e)}")

    if ext == ".json":
        return parse_json(content)
    elif ext == ".csv":
        return parse_csv(content)
    elif ext in (".txt", ".md", ".yaml", ".log"):
        # 文本文件：整体作为一个记录，包含文件名和内容摘要
        return [{
            "file": os.path.basename(file_path),
            "content_preview": content[:500],
            "line_count": content.count("\n") + 1,
        }]
    else:
        raise CashError("E003", f"不支持的文件格式: {ext}")


def parse_json(content: str) -> List[Dict[str, Any]]:
    """解析 JSON 字符串为记录列表"""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise CashError("E004", f"JSON 解析失败: {str(e)}")

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]
    else:
        raise CashError("E004", "JSON 顶层必须是对象或数组")


def parse_csv(content: str) -> List[Dict[str, Any]]:
    """解析 CSV 字符串为记录列表"""
    try:
        reader = csv.DictReader(io.StringIO(content))
        records = list(reader)
    except Exception as e:
        raise CashError("E005", f"CSV 解析失败: {str(e)}")

    return records


def fetch_url(url: str) -> Dict[str, Any]:
    """
    从 URL 提取内容。
    返回标题、正文摘要、元数据。
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise CashError("E006", f"不支持的 URL 协议: {parsed.scheme}")
    except Exception as e:
        raise CashError("E006", f"URL 格式错误: {str(e)}")

    try:
        with urlopen(url, timeout=10) as response:
            content = response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        raise CashError("E006", f"URL 访问失败: {str(e)}")

    # 提取标题（简化处理）
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "[未找到标题]"

    # 去除 HTML 标签获取正文摘要
    text_content = re.sub(r"<[^>]+>", " ", content)
    text_content = re.sub(r"\s+", " ", text_content).strip()

    return {
        "url": url,
        "title": title,
        "content_preview": text_content[:500],
        "content_length": len(text_content),
    }


def convert_format(data: Union[Dict, List], target: str) -> str:
    """
    格式转换：支持 JSON / CSV / YAML。
    """
    target = target.lower()
    if target == "json":
        return json.dumps(data, ensure_ascii=False, indent=2)
    elif target == "csv":
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            raise CashError("E008", "CSV 转换需要非空对象列表")
        try:
            output = io.StringIO()
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            return output.getvalue()
        except Exception as e:
            raise CashError("E008", f"CSV 转换失败: {str(e)}")
    elif target == "yaml":
        # 简化 YAML 输出（不依赖第三方库）
        lines = []
        if isinstance(data, list):
            for item in data:
                lines.append("-")
                if isinstance(item, dict):
                    for k, v in item.items():
                        lines.append(f"  {k}: {v}")
        elif isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"{k}: {v}")
        else:
            raise CashError("E008", "YAML 转换需要对象或数组")
        return "\n".join(lines)
    else:
        raise CashError("E008", f"不支持的目标格式: {target}")


def analyze_code(code: str) -> Dict[str, Any]:
    """
    代码审查辅助：提取函数签名、依赖、TODO 标记。
    """
    if not isinstance(code, str) or not code.strip():
        raise CashError("E007", "代码内容为空")

    result: Dict[str, Any] = {
        "functions": [],
        "dependencies": [],
        "todos": [],
    }

    # 提取函数定义
    for match in re.finditer(r"def\s+(\w+)\s*\(([^)]*)\)\s*:", code):
        func_name = match.group(1)
        params = [p.strip() for p in match.group(2).split(",") if p.strip()]
        result["functions"].append({
            "name": func_name,
            "params": params,
        })

    # 提取 import 语句
    import_patterns = [
        r"^\s*import\s+(\w+)",
        r"^\s*from\s+(\w+)\s+import",
    ]
    for pattern in import_patterns:
        for match in re.finditer(pattern, code, re.MULTILINE):
            dep = match.group(1)
            if dep not in result["dependencies"]:
                result["dependencies"].append(dep)

    # 提取 TODO 标记
    for match in re.finditer(r"#\s*TODO[:\s]*(.*)$", code, re.MULTILINE):
        result["todos"].append(match.group(1).strip())

    return result


def confidence_score(data: Dict[str, Any]) -> float:
    """
    计算结构化结果的置信度（0-1）。
    基于字段完整性和数据质量。
    """
    if not data:
        return 0.0

    score = 0.0
    total_fields = len(data)

    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str) and value.startswith("[需核实"):
            continue
        if isinstance(value, (str, int, float, bool)):
            score += 1.0
        elif isinstance(value, (list, dict)) and len(value) > 0:
            score += 0.8
        else:
            score += 0.5

    if total_fields == 0:
        return 0.0

    return round(score / total_fields, 2)


def process_input(data: Union[str, Dict, List]) -> Dict[str, Any]:
    """
    统一处理入口：根据输入类型调用相应解析函数。
    """
    try:
        if isinstance(data, str):
            # 判断是 URL、文件路径还是纯文本
            if data.startswith(("http://", "https://")):
                result = fetch_url(data)
            elif os.path.exists(data):
                records = parse_file(data)
                result = {"records": records, "count": len(records)}
            else:
                # 尝试 JSON 解析
                try:
                    json_data = json.loads(data)
                    result = {"data": json_data, "format": "json"}
                except json.JSONDecodeError:
                    # 作为纯文本处理
                    extracted = parse_text(data)
                    result = {"data": extracted, "format": "text"}
        elif isinstance(data, dict):
            result = {"data": data, "format": "dict"}
        elif isinstance(data, list):
            result = {"data": data, "format": "list"}
        else:
            raise CashError("E001", f"不支持的数据类型: {type(data)}")

        # 计算置信度
        if "data" in result:
            if isinstance(result["data"], list):
                confidences = [confidence_score(item) for item in result["data"] if isinstance(item, dict)]
                result["confidence"] = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
            elif isinstance(result["data"], dict):
                result["confidence"] = confidence_score(result["data"])
        elif "records" in result:
            confidences = [confidence_score(item) for item in result["records"] if isinstance(item, dict)]
            result["confidence"] = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        return result
    except CashError:
        raise
    except Exception as e:
        raise CashError("E009", f"处理过程中发生错误: {str(e)}")


def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不依赖当前工作目录、不访问网络。
    """
    try:
        # 测试 1: 文本解析
        text_sample = "姓名：张三 日期：2024-03-15 金额：¥1,280.50"
        text_result = parse_text(text_sample)
        assert "name" in text_result, "文本解析缺少 name 字段"
        assert "date" in text_result, "文本解析缺少 date 字段"
        assert "amount" in text_result, "文本解析缺少 amount 字段"
        assert text_result["name"] == "张三", "姓名提取错误"
        assert float(text_result["amount"]) > 1000, "金额提取错误"

        # 测试 2: JSON 解析
        json_sample = '[{"id": 1, "value": "test"}, {"id": 2, "value": "demo"}]'
        json_result = parse_json(json_sample)
        assert len(json_result) == 2, "JSON 解析数量错误"
        assert json_result[0]["id"] == 1, "JSON 解析内容错误"

        # 测试 3: CSV 解析
        csv_sample = "name,age\nAlice,30\nBob,25"
        csv_result = parse_csv(csv_sample)
        assert len(csv_result) == 2, "CSV 解析数量错误"
        assert csv_result[0]["name"] == "Alice", "CSV 解析内容错误"

        # 测试 4: 代码分析
        code_sample = """
import os
import sys

def hello(name):
    # TODO: 添加参数验证
    return f"Hello {name}"

def add(a, b):
    return a + b
"""
        code_result = analyze_code(code_sample)
        assert len(code_result["functions"]) == 2, "函数提取数量错误"
        assert "os" in code_result["dependencies"], "依赖提取错误"
        assert len(code_result["todos"]) == 1, "TODO 提取错误"

        # 测试 5: 格式转换
        convert_data = {"name": "测试", "value": 123}
        json_output = convert_format(convert_data, "json")
        assert "测试" in json_output, "JSON 转换失败"
        csv_output = convert_format(convert_data, "csv")
        assert "name" in csv_output, "CSV 转换失败"

        # 测试 6: 置信度计算
        conf_data = {"a": 1, "b": "text", "c": None}
        conf_score = confidence_score(conf_data)
        assert 0.5 <= conf_score <= 1.0, "置信度计算超出合理范围"

        # 测试 7: 统一处理入口
        process_result = process_input(text_sample)
        assert "data" in process_result, "统一处理入口失败"
        assert process_result["confidence"] > 0, "置信度标注失败"

        print("[自检] 全部测试通过 ✓")
        return True

    except AssertionError as e:
        print(f"[自检] 断言失败: {str(e)}")
        return False
    except Exception as e:
        print(f"[自检] 异常: {str(e)}")
        return False


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="awsome-cash - 数据解析与结构化提取工具 v1.0.2"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部资源）"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据：文本、文件路径或 URL"
    )
    parser.add_argument(
        "--convert",
        type=str,
        choices=["json", "csv", "yaml"],
        help="格式转换目标格式"
    )
    parser.add_argument(
        "--analyze-code",
        type=str,
        help="分析代码片段（从文件读取）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 代码分析模式
    if args.analyze_code:
        try:
            with open(args.analyze_code, "r", encoding="utf-8") as f:
                code_content = f.read()
            result = analyze_code(code_content)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        except Exception as e:
            print(f"错误: {str(e)}")
            sys.exit(1)

    # 输入处理模式
    if args.input:
        try:
            result = process_input(args.input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        except CashError as e:
            print(f"错误: {e}")
            sys.exit(1)

    # 无参数时显示帮助
    parser.print_help()


if __name__ == "__main__":
    main()
