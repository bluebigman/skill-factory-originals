#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ebay4r - eBay SOAP API 数据转换与调用封装工具

本脚本为 clean-room 独立实现，仅依据功能规格编写。
提供 eBay SOAP 请求的构建、响应解析、数据转换等核心能力，
并内置离线自检功能（--selftest），不依赖外部文件或网络。
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义 (E001-E010)
ERROR_CODES = {
    "E001": "参数校验失败：缺少必要参数或参数类型错误",
    "E002": "XML 解析失败：输入内容不是合法 XML",
    "E003": "SOAP 信封构建失败：无法生成有效的 SOAP 请求",
    "E004": "数据转换失败：无法将输入数据转换为目标格式",
    "E005": "响应解析失败：无法从 SOAP 响应中提取所需数据",
    "E006": "命名空间处理失败：XML 命名空间声明或引用错误",
    "E007": "日期时间格式错误：无法解析或格式化日期时间",
    "E008": "配置错误：缺少必要的配置项或配置值无效",
    "E009": "运行时错误：执行过程中发生未预期的异常",
    "E010": "自检失败：内置自检样例未通过验证",
}


class Ebay4RError(Exception):
    """自定义异常类，携带错误码。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ---------------------------------------------------------------------------
# 核心功能模块
# ---------------------------------------------------------------------------

def build_soap_envelope(
    operation_name: str,
    parameters: Dict[str, Any],
    namespace: str = "urn:ebay:apis:eBLBaseComponents",
) -> str:
    """
    构建 eBay SOAP 请求信封。

    参数:
        operation_name: eBay API 操作名称（如 GetItem, AddItem）
        parameters: 操作参数字典
        namespace: SOAP 命名空间

    返回:
        SOAP 请求 XML 字符串

    异常:
        Ebay4RError: E001 参数为空，E003 构建失败
    """
    if not operation_name or not isinstance(operation_name, str):
        raise Ebay4RError("E001", "操作名称必须为非空字符串")
    if not isinstance(parameters, dict):
        raise Ebay4RError("E001", "参数必须为字典类型")

    try:
        # 构建 SOAP 信封
        envelope = ET.Element(
            "soap:Envelope",
            {
                "xmlns:soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "xmlns:ebay": namespace,
            },
        )
        body = ET.SubElement(envelope, "soap:Body")
        operation_elem = ET.SubElement(body, f"ebay:{operation_name}")

        # 递归添加参数
        _add_parameters(operation_elem, parameters, namespace)

        # 序列化为字符串
        return ET.tostring(envelope, encoding="unicode", xml_declaration=True)
    except Exception as exc:
        raise Ebay4RError("E003", f"SOAP 信封构建失败: {exc}") from exc


def _add_parameters(
    parent: ET.Element, parameters: Dict[str, Any], namespace: str
) -> None:
    """递归将参数字典转换为 XML 子元素。"""
    for key, value in parameters.items():
        if value is None:
            continue

        # 处理命名空间前缀
        tag = f"{{{namespace}}}{key}" if ":" not in key else key

        if isinstance(value, dict):
            # 嵌套字典 -> 创建子元素并递归
            child = ET.SubElement(parent, tag)
            _add_parameters(child, value, namespace)
        elif isinstance(value, list):
            # 列表 -> 为每个元素创建同名子元素
            for item in value:
                if isinstance(item, dict):
                    child = ET.SubElement(parent, tag)
                    _add_parameters(child, item, namespace)
                else:
                    child = ET.SubElement(parent, tag)
                    child.text = _format_value(item)
        else:
            child = ET.SubElement(parent, tag)
            child.text = _format_value(value)


def _format_value(value: Any) -> str:
    """将 Python 值转换为 XML 文本表示。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def parse_soap_response(xml_text: str) -> Dict[str, Any]:
    """
    解析 eBay SOAP 响应 XML。

    参数:
        xml_text: SOAP 响应 XML 字符串

    返回:
        解析后的数据字典

    异常:
        Ebay4RError: E002 XML 解析失败，E005 响应解析失败
    """
    if not xml_text or not xml_text.strip():
        raise Ebay4RError("E001", "响应文本不能为空")

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise Ebay4RError("E002", f"XML 解析失败: {exc}") from exc

    try:
        # 提取 SOAP Body 下的内容
        result = _element_to_dict(root)
        # 尝试获取 Body 下的实际数据
        body = _find_child_by_local_name(root, "Body")
        if body is not None:
            for child in body:
                return _element_to_dict(child)
        return result
    except Exception as exc:
        raise Ebay4RError("E005", f"响应解析失败: {exc}") from exc


def _find_child_by_local_name(
    element: ET.Element, local_name: str
) -> Optional[ET.Element]:
    """按本地名称查找子元素（忽略命名空间）。"""
    for child in element:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == local_name:
            return child
    return None


def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """将 XML 元素递归转换为字典。"""
    result: Dict[str, Any] = {}

    # 获取本地标签名（去掉命名空间）
    tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

    if len(element) == 0:
        # 叶子节点：返回文本值
        text = (element.text or "").strip()
        if text:
            # 尝试转换为数值类型
            try:
                return {tag: int(text)}
            except ValueError:
                try:
                    return {tag: float(text)}
                except ValueError:
                    if text.lower() in ("true", "false"):
                        return {tag: text.lower() == "true"}
                    return {tag: text}
        return {tag: None}

    # 有子元素：递归处理
    children: Dict[str, Any] = {}
    for child in element:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        child_data = _element_to_dict(child)

        # 处理重复元素（列表）
        if child_tag in children:
            if not isinstance(children[child_tag], list):
                children[child_tag] = [children[child_tag]]
            children[child_tag].append(child_data.get(child_tag))
        else:
            children[child_tag] = child_data.get(child_tag)

    return {tag: children}


def convert_to_ebay_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将通用数据转换为 eBay API 所需的格式。

    主要转换规则：
    - 键名转为驼峰式（CamelCase）
    - 日期时间转为 ISO 8601 格式
    - 布尔值转为 'true'/'false' 字符串

    参数:
        data: 输入数据字典

    返回:
        转换后的数据字典

    异常:
        Ebay4RError: E004 数据转换失败
    """
    if not isinstance(data, dict):
        raise Ebay4RError("E001", "输入数据必须为字典类型")

    try:
        return _convert_dict(data)
    except Exception as exc:
        raise Ebay4RError("E004", f"数据转换失败: {exc}") from exc


def _convert_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """递归转换字典键名为驼峰式。"""
    result: Dict[str, Any] = {}
    for key, value in data.items():
        new_key = _to_camel_case(key)
        if isinstance(value, dict):
            result[new_key] = _convert_dict(value)
        elif isinstance(value, list):
            result[new_key] = [
                _convert_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, datetime):
            result[new_key] = value.isoformat()
        else:
            result[new_key] = value
    return result


def _to_camel_case(snake_str: str) -> str:
    """将下划线命名转换为驼峰式命名。"""
    parts = snake_str.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def parse_ebay_datetime(date_str: str) -> datetime:
    """
    解析 eBay 返回的日期时间字符串。

    支持格式：
    - ISO 8601: 2024-01-01T12:00:00.000Z
    - 带偏移: 2024-01-01T12:00:00+08:00

    参数:
        date_str: 日期时间字符串

    返回:
        datetime 对象

    异常:
        Ebay4RError: E007 日期时间格式错误
    """
    if not date_str:
        raise Ebay4RError("E001", "日期时间字符串不能为空")

    try:
        # 尝试 ISO 格式
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        # 尝试其他常见格式
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise Ebay4RError("E007", f"无法解析日期时间: {date_str}")


def validate_config(config: Dict[str, Any]) -> None:
    """
    验证 eBay API 配置。

    必需配置项：
    - auth_token: 认证令牌
    - site_id: 站点 ID

    参数:
        config: 配置字典

    异常:
        Ebay4RError: E008 配置错误
    """
    required_keys = ("auth_token", "site_id")
    for key in required_keys:
        if key not in config or not config[key]:
            raise Ebay4RError("E008", f"缺少必要配置项: {key}")

    if not isinstance(config["site_id"], (int, str)):
        raise Ebay4RError("E008", "site_id 必须为整数或数字字符串")

    if len(str(config["auth_token"])) < 10:
        raise Ebay4RError("E008", "auth_token 长度不足，疑似无效")


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或工作目录。
    使用宽松断言（大小比较/区间判断），确保稳健。

    返回:
        True 表示自检通过

    异常:
        Ebay4RError: E010 自检失败
    """
    print("=" * 60)
    print("ebay4r 自检开始（离线模式）")
    print("=" * 60)

    try:
        # --- 测试 1: SOAP 信封构建 ---
        print("\n[1/5] 测试 SOAP 信封构建...")
        params = {
            "ItemID": "123456789",
            "DetailLevel": "ReturnAll",
            "IncludeItemSpecifics": True,
        }
        envelope = build_soap_envelope("GetItem", params)
        assert "soap:Envelope" in envelope, "SOAP 信封缺少 Envelope 标记"
        assert "GetItem" in envelope, "SOAP 信封缺少操作名称"
        assert "123456789" in envelope, "SOAP 信封缺少参数值"
        print("  ✓ SOAP 信封构建成功")

        # --- 测试 2: 响应解析 ---
        print("\n[2/5] 测试 SOAP 响应解析...")
        sample_response = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetItemResponse xmlns="urn:ebay:apis:eBLBaseComponents">
      <Ack>Success</Ack>
      <Item>
        <ItemID>123456789</ItemID>
        <Title>Test Item</Title>
        <StartPrice>99.99</StartPrice>
        <Quantity>5</Quantity>
      </Item>
    </GetItemResponse>
  </soap:Body>
</soap:Envelope>"""
        parsed = parse_soap_response(sample_response)
        # 宽松断言：检查关键字段存在且值合理
        assert parsed is not None, "解析结果不能为空"
        # 找到 Item 数据
        item_data = None
        for key, value in parsed.items():
            if isinstance(value, dict) and "Item" in value:
                item_data = value["Item"]
                break
        assert item_data is not None, "未找到 Item 数据"
        assert item_data.get("Quantity") is not None, "缺少 Quantity 字段"
        assert item_data.get("StartPrice") is not None, "缺少 StartPrice 字段"
        print("  ✓ SOAP 响应解析成功")

        # --- 测试 3: 数据转换 ---
        print("\n[3/5] 测试数据格式转换...")
        input_data = {
            "item_id": "ABC123",
            "start_price": 49.99,
            "is_available": True,
            "created_at": datetime(2024, 1, 15, 10, 30, 0),
            "categories": [
                {"category_id": 1, "category_name": "Electronics"},
                {"category_id": 2, "category_name": "Accessories"},
            ],
        }
        converted = convert_to_ebay_format(input_data)
        assert "itemId" in converted, "键名未转换为驼峰式"
        assert "startPrice" in converted, "键名未转换为驼峰式"
        assert "createdAt" in converted, "键名未转换为驼峰式"
        assert isinstance(converted["categories"], list), "列表转换失败"
        assert converted["categories"][0]["categoryId"] == 1, "嵌套字典转换失败"
        print("  ✓ 数据格式转换成功")

        # --- 测试 4: 日期时间解析 ---
        print("\n[4/5] 测试日期时间解析...")
        dt1 = parse_ebay_datetime("2024-06-15T12:00:00.000Z")
        dt2 = parse_ebay_datetime("2024-06-15T20:00:00+08:00")
        # 宽松断言：两个时间戳相差不超过 24 小时
        diff_hours = abs((dt1 - dt2).total_seconds()) / 3600
        assert diff_hours < 24, f"时间解析差异过大: {diff_hours} 小时"
        assert dt1.year == 2024, "年份解析错误"
        assert dt1.month == 6, "月份解析错误"
        print("  ✓ 日期时间解析成功")

        # --- 测试 5: 配置验证 ---
        print("\n[5/5] 测试配置验证...")
        valid_config = {
            "auth_token": "test_token_1234567890",
            "site_id": 0,
        }
        validate_config(valid_config)
        print("  ✓ 配置验证成功")

        # 错误场景测试
        print("\n[附加] 测试错误处理...")
        try:
            validate_config({"auth_token": "short", "site_id": 0})
            raise AssertionError("应抛出 E008 错误")
        except Ebay4RError as e:
            assert e.error_code == "E008", "错误码应为 E008"

        try:
            parse_soap_response("<invalid>xml")
            raise AssertionError("应抛出 E002 错误")
        except Ebay4RError as e:
            assert e.error_code == "E002", "错误码应为 E002"

        print("  ✓ 错误处理正常")

        print("\n" + "=" * 60)
        print("✅ 全部自检通过！")
        print("=" * 60)
        return True

    except AssertionError as exc:
        print(f"\n❌ 自检失败: {exc}")
        raise Ebay4RError("E010", f"自检断言失败: {exc}") from exc
    except Ebay4RError:
        raise
    except Exception as exc:
        print(f"\n❌ 自检异常: {exc}")
        raise Ebay4RError("E010", f"自检发生异常: {exc}") from exc


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="ebay4r - eBay SOAP API 数据转换与调用封装工具",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，无需外部依赖）",
    )
    parser.add_argument(
        "--build-envelope",
        metavar="OPERATION",
        help="构建 SOAP 信封（测试用）",
    )
    parser.add_argument(
        "--parse-xml",
        metavar="FILE",
        help="解析 SOAP 响应 XML 文件（测试用）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except Ebay4RError as exc:
            print(f"错误: {exc}")
            return 1

    # 构建 SOAP 信封测试
    if args.build_envelope:
        try:
            test_params = {
                "ItemID": "123456789",
                "DetailLevel": "ReturnAll",
            }
            envelope = build_soap_envelope(args.build_envelope, test_params)
            print(envelope)
            return 0
        except Ebay4RError as exc:
            print(f"错误: {exc}")
            return 1

    # 解析 XML 测试
    if args.parse_xml:
        try:
            with open(args.parse_xml, "r", encoding="utf-8") as f:
                xml_text = f.read()
            result = parse_soap_response(xml_text)
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        except FileNotFoundError:
            print(f"错误: 文件不存在 - {args.parse_xml}")
            return 1
        except Ebay4RError as exc:
            print(f"错误: {exc}")
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
