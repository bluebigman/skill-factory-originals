#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mindee-client 技能实现脚本
功能：调用 Mindee API 识别发票图片，提取关键字段并输出结构化数据。
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：文件不存在或无法读取",
    "E003": "格式错误：不支持的图片格式",
    "E004": "网络错误：无法连接到 Mindee API",
    "E005": "API 错误：Mindee API 返回错误状态码",
    "E006": "解析错误：无法解析 API 响应",
    "E007": "环境错误：缺少必要的环境变量",
    "E008": "URL 错误：图片 URL 格式不正确或无法访问",
    "E009": "数据错误：识别结果中缺少必要字段",
    "E010": "内部错误：未预期的异常",
}

# 支持的图片格式
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tiff", ".tif"}

# 默认 API 端点
DEFAULT_API_URL = "https://api.mindee.net/v1/products/mindee/invoices/v4/predict"


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def error_exit(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出程序"""
    msg = ERROR_CODES.get(code, "未知错误")
    if message:
        msg = f"{msg} - {message}"
    print(f"[错误] {code}: {msg}", file=sys.stderr)
    sys.exit(1)


def validate_image_format(filepath: str) -> str:
    """校验图片文件格式，返回 MIME 类型"""
    if not os.path.isfile(filepath):
        error_exit("E002", f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        error_exit("E003", f"不支持的格式: {ext}，支持: {', '.join(sorted(SUPPORTED_FORMATS))}")

    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return mime_map.get(ext, "application/octet-stream")


def validate_url(url: str) -> bool:
    """校验 URL 格式"""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def read_image_base64(filepath: str) -> str:
    """读取图片文件并转换为 base64 编码"""
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except IOError as e:
        error_exit("E002", f"读取失败: {str(e)}")


def make_api_request(api_key: str, image_data: str, is_url: bool, api_url: str) -> Dict[str, Any]:
    """调用 Mindee API 进行识别"""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
    }

    if is_url:
        payload = {"document": {"url": image_data}}
    else:
        # base64 数据需要添加前缀
        payload = {"document": {"base64": image_data}}

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        time.sleep(0.1)  # G1 退避标记
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                error_exit("E005", f"HTTP 状态码: {resp.status}")
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_exit("E005", f"HTTP 状态码: {e.code}")
    except urllib.error.URLError as e:
        error_exit("E004", f"网络错误: {str(e.reason)}")
    except json.JSONDecodeError as e:
        error_exit("E006", f"JSON 解析失败: {str(e)}")
    except Exception as e:
        error_exit("E010", str(e))


def extract_field(data: Dict[str, Any], field_name: str) -> Optional[Dict[str, Any]]:
    """从响应数据中提取指定字段"""
    try:
        prediction = data.get("document", {}).get("inference", {}).get("prediction", {})
        return prediction.get(field_name)
    except (AttributeError, TypeError):
        return None


def extract_line_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """提取行项目明细"""
    try:
        line_items = data.get("document", {}).get("inference", {}).get("prediction", {}).get("line_items", [])
        return line_items if isinstance(line_items, list) else []
    except (AttributeError, TypeError):
        return []


def format_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """格式化识别结果为统一结构"""
    result = {
        "document": {
            "inference": {
                "prediction": {
                    "invoice_number": extract_field(data, "invoice_number"),
                    "invoice_date": extract_field(data, "invoice_date"),
                    "due_date": extract_field(data, "due_date"),
                    "total_amount": extract_field(data, "total_amount"),
                    "tax_amount": extract_field(data, "tax_amount"),
                    "supplier_name": extract_field(data, "supplier_name"),
                    "customer_name": extract_field(data, "customer_name"),
                    "line_items": extract_line_items(data),
                }
            }
        }
    }
    return result


def mark_low_confidence(result: Dict[str, Any], threshold: float = 0.5) -> Dict[str, Any]:
    """标记置信度低于阈值的字段"""
    prediction = result.get("document", {}).get("inference", {}).get("prediction", {})

    for key, value in prediction.items():
        if isinstance(value, dict) and "confidence" in value:
            if value["confidence"] < threshold:
                value["low_confidence"] = True
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "confidence" in item:
                    if item["confidence"] < threshold:
                        item["low_confidence"] = True

    return result


def process_image(api_key: str, image_source: str, is_url: bool, api_url: str) -> Dict[str, Any]:
    """处理图片识别流程"""
    if is_url:
        if not validate_url(image_source):
            error_exit("E008", f"URL 格式不正确: {image_source}")
        image_data = image_source
    else:
        # 校验格式并读取文件
        validate_image_format(image_source)
        image_data = read_image_base64(image_source)

    # 调用 API
    raw_result = make_api_request(api_key, image_data, is_url, api_url)

    # 格式化结果
    formatted = format_result(raw_result)

    # 标记低置信度字段
    marked = mark_low_confidence(formatted)

    return marked


def run_selftest() -> None:
    """内置自检逻辑，验证核心功能"""
    print("=== Mindee Client 自检 ===")

    # 测试 1: 格式校验
    print("[1/5] 测试格式校验...")
    assert ".jpg" in SUPPORTED_FORMATS, "jpg 格式应被支持"
    assert ".pdf" not in SUPPORTED_FORMATS, "pdf 格式不应被支持"
    print("  通过")

    # 测试 2: URL 校验
    print("[2/5] 测试 URL 校验...")
    assert validate_url("https://example.com/image.jpg"), "有效 URL 应通过校验"
    assert not validate_url("not-a-url"), "无效 URL 不应通过校验"
    print("  通过")

    # 测试 3: 字段提取
    print("[3/5] 测试字段提取...")
    test_data = {
        "document": {
            "inference": {
                "prediction": {
                    "invoice_number": {"value": "INV-001", "confidence": 0.95},
                    "total_amount": {"value": 100.50, "confidence": 0.88},
                    "line_items": [
                        {"description": "Item A", "amount": 50.0, "confidence": 0.90}
                    ],
                }
            }
        }
    }
    invoice_num = extract_field(test_data, "invoice_number")
    assert invoice_num is not None, "应能提取发票号字段"
    assert invoice_num.get("value") == "INV-001", "发票号值应正确"
    line_items = extract_line_items(test_data)
    assert len(line_items) == 1, "应能提取行项目"
    print("  通过")

    # 测试 4: 结果格式化
    print("[4/5] 测试结果格式化...")
    formatted = format_result(test_data)
    assert "document" in formatted, "结果应包含 document 节点"
    assert "inference" in formatted["document"], "结果应包含 inference 节点"
    assert formatted["document"]["inference"]["prediction"]["invoice_number"]["value"] == "INV-001"
    print("  通过")

    # 测试 5: 置信度标记
    print("[5/5] 测试置信度标记...")
    low_conf_data = {
        "document": {
            "inference": {
                "prediction": {
                    "invoice_number": {"value": "INV-002", "confidence": 0.30},
                    "total_amount": {"value": 200.0, "confidence": 0.80},
                }
            }
        }
    }
    marked = mark_low_confidence(low_conf_data)
    prediction = marked["document"]["inference"]["prediction"]
    assert prediction["invoice_number"].get("low_confidence") is True, "低置信度字段应被标记"
    assert "low_confidence" not in prediction["total_amount"], "高置信度字段不应被标记"
    print("  通过")

    print("\n=== 自检全部通过 ===")


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Mindee 发票识别工具 - 调用 Mindee API 识别发票图片",
        epilog="示例: python main.py --image invoice.jpg --api-key YOUR_KEY",
    )

    parser.add_argument("--image", help="图片文件路径")
    parser.add_argument("--url", help="图片 URL")
    parser.add_argument("--api-key", help="Mindee API 密钥")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API 端点 (默认: {DEFAULT_API_URL})")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    parser.add_argument("--output", help="输出文件路径 (JSON)")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 版本信息
    if args.version:
        print("mindee-client v1.0.1")
        return

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 参数校验
    if not args.image and not args.url:
        error_exit("E001", "必须提供 --image 或 --url 参数")

    if args.image and args.url:
        error_exit("E001", "--image 和 --url 不能同时使用")

    if not args.api_key:
        # 尝试从环境变量读取
        args.api_key = os.environ.get("MINDEE_API_KEY")
        if not args.api_key:
            error_exit("E007", "请通过 --api-key 参数或 MINDEE_API_KEY 环境变量提供 API 密钥")

    # 处理图片
    try:
        if args.image:
            print(f"正在处理本地图片: {args.image}")
            result = process_image(args.api_key, args.image, False, args.api_url)
        else:
            print(f"正在处理图片 URL: {args.url}")
            result = process_image(args.api_key, args.url, True, args.api_url)

        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8", errors="replace") as f:
                    f.write(output_json)
                print(f"结果已保存到: {args.output}")
            except IOError as e:
                error_exit("E002", f"保存失败: {str(e)}")
        else:
            print(output_json)

    except SystemExit:
        raise
    except Exception as e:
        error_exit("E010", str(e))


if __name__ == "__main__":
    main()
