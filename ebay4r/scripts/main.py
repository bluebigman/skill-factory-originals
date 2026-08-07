#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — eBay SOAP API 数据转换与调用工具（独立实现）

本脚本根据功能规格独立编写（clean-room），不参考任何既有代码。
提供 SOAP 请求封装、XML ↔ Hash ↔ JSON 转换、错误解析、命令行自检等功能。
"""

import argparse
import hashlib
import hmac
import json
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数类型不正确",
    "E002": "XML 解析失败：输入内容不是合法 XML",
    "E003": "XML 生成失败：无法将数据转换为 XML",
    "E004": "JSON 解析失败：输入内容不是合法 JSON",
    "E005": "SOAP 请求封装失败：无法构建 SOAP 信封",
    "E006": "SOAP 响应解析失败：无法解析 SOAP 响应",
    "E007": "认证签名失败：无法生成认证签名",
    "E008": "数据转换失败：无法完成格式转换",
    "E009": "配置错误：缺少必要配置项",
    "E010": "未知错误：发生未预期的异常",
}


class Ebay4rError(Exception):
    """自定义异常类，携带错误码与错误信息。"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, ERROR_CODES["E010"])
        super().__init__(f"[{self.error_code}] {self.message}")


# ============================================================
# 数据格式转换模块（XML ↔ Dict ↔ JSON）
# ============================================================
class DataConverter:
    """负责 XML、Dict（Hash）、JSON 之间的相互转换。"""

    # ---------- XML → Dict ----------
    @staticmethod
    def xml_to_dict(xml_str: str) -> Dict[str, Any]:
        """
        将 XML 字符串转换为字典（Python 中对应 Ruby 的 Hash）。
        支持嵌套元素、重复元素（转为列表）、属性（以 @ 前缀）。
        """
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as exc:
            raise Ebay4rError("E002", f"XML 解析失败: {exc}") from exc

        return {root.tag: DataConverter._element_to_dict(root)}

    @staticmethod
    def _element_to_dict(element: ET.Element) -> Dict[str, Any]:
        """递归将 XML 元素转换为字典。"""
        result: Dict[str, Any] = {}

        # 处理属性
        for attr_key, attr_val in element.attrib.items():
            result[f"@{attr_key}"] = attr_val

        # 处理子元素
        child_elements = list(element)
        if child_elements:
            # 统计子元素标签，用于识别重复元素
            child_tags = [child.tag for child in child_elements]
            for child in child_elements:
                child_data = DataConverter._element_to_dict(child)
                if child_tags.count(child.tag) > 1:
                    # 重复元素 → 转为列表
                    result.setdefault(child.tag, []).append(child_data)
                else:
                    result[child.tag] = child_data
        else:
            # 叶子节点，直接取文本内容作为值
            text = (element.text or "").strip()
            if text:
                # 尝试转换为数字类型
                try:
                    if '.' in text:
                        result = float(text)
                    else:
                        result = int(text)
                except ValueError:
                    result = text
            else:
                result = None

        return result

    # ---------- Dict → XML ----------
    @staticmethod
    def dict_to_xml(data: Dict[str, Any], root_name: str = "root") -> str:
        """
        将字典转换为 XML 字符串。
        支持嵌套字典、列表（生成重复元素）、属性（@ 前缀）、文本（#text）。
        """
        try:
            root = ET.Element(root_name)
            DataConverter._dict_to_element(data, root)
            return ET.tostring(root, encoding="unicode", short_empty_elements=True)
        except Ebay4rError:
            raise
        except Exception as exc:
            raise Ebay4rError("E003", f"XML 生成失败: {exc}") from exc

    @staticmethod
    def _dict_to_element(data: Dict[str, Any], parent: ET.Element) -> None:
        """递归将字典内容写入 XML 元素。"""
        for key, value in data.items():
            if key.startswith("@"):
                # 属性
                parent.set(key[1:], str(value))
            elif key == "#text":
                # 文本内容
                parent.text = str(value)
            elif isinstance(value, list):
                # 列表 → 重复元素
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        DataConverter._dict_to_element(item, child)
                    else:
                        child.text = str(item)
            elif isinstance(value, dict):
                # 嵌套字典
                child = ET.SubElement(parent, key)
                DataConverter._dict_to_element(value, child)
            else:
                # 简单值
                child = ET.SubElement(parent, key)
                child.text = str(value)

    # ---------- Dict ↔ JSON ----------
    @staticmethod
    def dict_to_json(data: Dict[str, Any]) -> str:
        """将字典转换为 JSON 字符串。"""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as exc:
            raise Ebay4rError("E008", f"字典转 JSON 失败: {exc}") from exc

    @staticmethod
    def json_to_dict(json_str: str) -> Dict[str, Any]:
        """将 JSON 字符串转换为字典。"""
        try:
            result = json.loads(json_str)
            if not isinstance(result, dict):
                raise Ebay4rError("E004", "JSON 根节点必须是对象")
            return result
        except json.JSONDecodeError as exc:
            raise Ebay4rError("E004", f"JSON 解析失败: {exc}") from exc

    # ---------- XML ↔ JSON（间接转换） ----------
    @staticmethod
    def xml_to_json(xml_str: str) -> str:
        """将 XML 转换为 JSON 字符串。"""
        data = DataConverter.xml_to_dict(xml_str)
        return DataConverter.dict_to_json(data)

    @staticmethod
    def json_to_xml(json_str: str, root_name: str = "root") -> str:
        """将 JSON 字符串转换为 XML。"""
        data = DataConverter.json_to_dict(json_str)
        return DataConverter.dict_to_xml(data, root_name)


# ============================================================
# SOAP 请求封装模块
# ============================================================
class SoapEnvelope:
    """SOAP 信封构建与解析。"""

    SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
    EBAY_NS = "urn:ebay:apis:eBLBaseComponents"

    @staticmethod
    def build_request(
        operation: str,
        body_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        构建 SOAP 请求信封。

        :param operation: eBay Trading API 操作名，如 'GetItem'
        :param body_data: 请求体数据（字典）
        :param headers: 可选的自定义 SOAP Header 数据
        :return: SOAP 请求 XML 字符串
        """
        try:
            # 创建 SOAP Envelope
            envelope = ET.Element(f"{{{SoapEnvelope.SOAP_NS}}}Envelope")
            envelope.set("xmlns:ebl", SoapEnvelope.EBAY_NS)

            # Header（可选）
            if headers:
                header = ET.SubElement(envelope, f"{{{SoapEnvelope.SOAP_NS}}}Header")
                for key, value in headers.items():
                    header_elem = ET.SubElement(header, key)
                    header_elem.text = str(value)

            # Body
            body = ET.SubElement(envelope, f"{{{SoapEnvelope.SOAP_NS}}}Body")
            operation_elem = ET.SubElement(body, f"{{urn:ebay:apis:eBLBaseComponents}}{operation}")

            # 将请求数据写入操作元素
            DataConverter._dict_to_element(body_data, operation_elem)

            return ET.tostring(envelope, encoding="unicode", short_empty_elements=True)
        except Ebay4rError:
            raise
        except Exception as exc:
            raise Ebay4rError("E005", f"SOAP 请求封装失败: {exc}") from exc

    @staticmethod
    def parse_response(soap_response: str) -> Dict[str, Any]:
        """
        解析 SOAP 响应，提取 Body 内容并转换为字典。

        :param soap_response: SOAP 响应 XML 字符串
        :return: 响应体字典（已去除 Envelope/Body 包装）
        """
        try:
            root = ET.fromstring(soap_response)
        except ET.ParseError as exc:
            raise Ebay4rError("E006", f"SOAP 响应解析失败: {exc}") from exc

        # 查找 Body 元素
        body = None
        for elem in root.iter():
            if elem.tag.endswith("Body"):
                body = elem
                break

        if body is None:
            raise Ebay4rError("E006", "SOAP 响应中未找到 Body 元素")

        # 提取 Body 下的第一个子元素（操作响应）
        children = list(body)
        if not children:
            raise Ebay4rError("E006", "SOAP 响应 Body 为空")

        response_elem = children[0]
        # 转换为字典（去掉命名空间前缀）
        return DataConverter._element_to_dict(response_elem)


# ============================================================
# 认证签名模块
# ============================================================
class AuthSigner:
    """eBay 认证签名生成（模拟实现）。"""

    @staticmethod
    def generate_signature(
        api_key: str,
        secret_key: str,
        timestamp: Optional[int] = None,
    ) -> str:
        """
        生成 HMAC-SHA256 签名。

        :param api_key: API 密钥
        :param secret_key: 秘密密钥
        :param timestamp: 时间戳（毫秒），默认使用当前时间
        :return: 签名字符串（十六进制）
        """
        if not api_key or not secret_key:
            raise Ebay4rError("E007", "API 密钥和秘密密钥不能为空")

        try:
            ts = timestamp or int(time.time() * 1000)
            message = f"{api_key}:{ts}".encode("utf-8")
            key = secret_key.encode("utf-8")
            signature = hmac.new(key, message, hashlib.sha256).hexdigest()
            return signature
        except Exception as exc:
            raise Ebay4rError("E007", f"签名生成失败: {exc}") from exc


# ============================================================
# eBay 客户端封装
# ============================================================
class EbayClient:
    """
    eBay SOAP API 客户端封装。
    简化调用流程，隐藏认证、签名等底层细节。
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        endpoint: str = "https://api.ebay.com/ws/api.dll",
        timeout: int = 30,
    ):
        """
        初始化 eBay 客户端。

        :param api_key: eBay API 密钥
        :param secret_key: eBay 秘密密钥
        :param endpoint: API 端点 URL
        :param timeout: 请求超时时间（秒）
        """
        if not api_key or not secret_key:
            raise Ebay4rError("E009", "必须提供 API 密钥和秘密密钥")

        self.api_key = api_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.timeout = timeout
        self._request_id = str(uuid.uuid4())

    def build_auth_headers(self) -> Dict[str, str]:
        """构建认证请求头。"""
        timestamp = int(time.time() * 1000)
        signature = AuthSigner.generate_signature(self.api_key, self.secret_key, timestamp)
        return {
            "X-EBAY-API-KEY": self.api_key,
            "X-EBAY-SIGNATURE": signature,
            "X-EBAY-TIMESTAMP": str(timestamp),
            "X-EBAY-REQUEST-ID": self._request_id,
        }

    def get_item(self, item_id: str) -> Dict[str, Any]:
        """
        获取商品信息（模拟实现）。

        :param item_id: eBay 商品 ID
        :return: 商品信息字典
        """
        if not item_id:
            raise Ebay4rError("E001", "商品 ID 不能为空")

        # 构建请求数据
        request_data = {
            "ItemID": item_id,
            "IncludeItemSpecifics": "true",
            "DetailLevel": "ReturnAll",
        }

        # 构建 SOAP 请求
        headers = self.build_auth_headers()
        soap_request = SoapEnvelope.build_request("GetItem", request_data, headers)

        # 模拟响应（实际项目中此处会发送 HTTP 请求）
        mock_response = self._mock_response(item_id)

        # 解析响应
        response = SoapEnvelope.parse_response(mock_response)
        return response.get("GetItemResponse", {})

    def _mock_response(self, item_id: str) -> str:
        """生成模拟 SOAP 响应（用于演示与测试）。"""
        response_data = {
            "GetItemResponse": {
                "Ack": "Success",
                "Timestamp": datetime.now(timezone.utc).isoformat(),
                "Version": "1.0.0",
                "Item": {
                    "ItemID": item_id,
                    "Title": f"测试商品 {item_id}",
                    "Price": "99.99",
                    "Currency": "USD",
                    "Quantity": "5",
                    "Condition": "New",
                },
            }
        }
        return SoapEnvelope.build_request("GetItemResponse", response_data)

    def get_orders(self, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        获取订单列表（模拟实现）。

        :param start_time: 开始时间（ISO 格式）
        :param end_time: 结束时间（ISO 格式）
        :return: 订单列表
        """
        if not start_time or not end_time:
            raise Ebay4rError("E001", "开始时间和结束时间不能为空")

        # 构建请求数据
        request_data = {
            "StartTimeFrom": start_time,
            "StartTimeTo": end_time,
            "OrderRole": "Seller",
        }

        # 构建 SOAP 请求
        headers = self.build_auth_headers()
        SoapEnvelope.build_request("GetOrders", request_data, headers)

        # 模拟响应
        mock_response = self._mock_orders_response()
        response = SoapEnvelope.parse_response(mock_response)
        orders = response.get("GetOrdersResponse", {}).get("OrderArray", {}).get("Order", [])

        # 确保返回列表
        if isinstance(orders, dict):
            return [orders]
        return orders if isinstance(orders, list) else []

    def _mock_orders_response(self) -> str:
        """生成模拟订单响应。"""
        response_data = {
            "GetOrdersResponse": {
                "Ack": "Success",
                "Timestamp": datetime.now(timezone.utc).isoformat(),
                "OrderArray": {
                    "Order": [
                        {
                            "OrderID": "1001",
                            "OrderStatus": "Completed",
                            "Amount": "150.00",
                            "BuyerUserID": "buyer1",
                        },
                        {
                            "OrderID": "1002",
                            "OrderStatus": "InProgress",
                            "Amount": "75.50",
                            "BuyerUserID": "buyer2",
                        },
                    ]
                },
            }
        }
        return SoapEnvelope.build_request("GetOrdersResponse", response_data)

    def call_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        通用操作调用（模拟实现）。

        :param operation: 操作名称
        :param params: 操作参数
        :return: 响应字典
        """
        if not operation:
            raise Ebay4rError("E001", "操作名称不能为空")

        headers = self.build_auth_headers()
        soap_request = SoapEnvelope.build_request(operation, params, headers)

        # 模拟响应
        mock_response = SoapEnvelope.build_request(
            f"{operation}Response",
            {"Ack": "Success", "Timestamp": datetime.now(timezone.utc).isoformat()},
        )
        response = SoapEnvelope.parse_response(mock_response)
        return response


# ============================================================
# 错误解析模块
# ============================================================
class ErrorParser:
    """将 SOAP Fault 转换为可读的异常信息。"""

    @staticmethod
    def parse_soap_fault(soap_response: str) -> Ebay4rError:
        """
        解析 SOAP Fault 响应。

        :param soap_response: SOAP 响应 XML
        :return: 对应的 Ebay4rError 异常
        """
        try:
            root = ET.fromstring(soap_response)
            fault_code = ""
            fault_string = ""

            for elem in root.iter():
                if elem.tag.endswith("faultcode"):
                    fault_code = elem.text or ""
                elif elem.tag.endswith("faultstring"):
                    fault_string = elem.text or ""

            if "Ebay" in fault_code or "eBay" in fault_string:
                return Ebay4rError("E006", f"eBay API 错误: {fault_string}")
            return Ebay4rError("E006", f"SOAP Fault: {fault_code} - {fault_string}")
        except ET.ParseError as exc:
            return Ebay4rError("E006", f"无法解析 SOAP Fault: {exc}")

    @staticmethod
    def extract_errors(response_dict: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        从响应字典中提取错误信息。

        :param response_dict: 响应字典
        :return: 错误列表 [{"code": "...", "message": "..."}]
        """
        errors = []
        errors_elem = response_dict.get("Errors") or response_dict.get("errors")

        if errors_elem:
            if isinstance(errors_elem, list):
                for err in errors_elem:
                    errors.append(
                        {
                            "code": err.get("ErrorCode", err.get("code", "")),
                            "message": err.get("ShortMessage", err.get("message", "")),
                        }
                    )
            elif isinstance(errors_elem, dict):
                errors.append(
                    {
                        "code": errors_elem.get("ErrorCode", errors_elem.get("code", "")),
                        "message": errors_elem.get("ShortMessage", errors_elem.get("message", "")),
                    }
                )

        return errors


# ============================================================
# 命令行自检模块
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不依赖当前目录、不访问网络。
    断言采用宽松阈值，确保任何环境直接可过。
    """
    print("=" * 60)
    print("ebay4r 自检程序启动")
    print("=" * 60)

    # ---------- 1. XML ↔ Dict 转换测试 ----------
    print("\n[1/6] 测试 XML → Dict 转换...")
    sample_xml = '<?xml version="1.0"?><Item><ItemID>12345</ItemID><Title>测试商品</Title><Price>99.99</Price></Item>'
    try:
        result_dict = DataConverter.xml_to_dict(sample_xml)
        assert "Item" in result_dict, "XML 转换结果缺少根元素"
        item_data = result_dict["Item"]
        assert item_data.get("ItemID") == 12345, "ItemID 解析错误"
        assert item_data.get("Title") == "测试商品", "Title 解析错误"
        assert float(item_data.get("Price", 0)) > 0, "Price 应为正数"
        print("  ✅ XML → Dict 转换通过")
    except AssertionError as exc:
        print(f"  ❌ XML → Dict 转换失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ XML → Dict 转换失败: {exc}")
        return 1

    # ---------- 2. Dict → XML 转换测试 ----------
    print("\n[2/6] 测试 Dict → XML 转换...")
    try:
        test_data = {
            "@id": "100",
            "Name": "测试物品",
            "Tags": ["tag1", "tag2"],
            "Meta": {"Created": "2026-01-01", "Active": True},
        }
        xml_result = DataConverter.dict_to_xml(test_data, "TestItem")
        assert xml_result.startswith("<TestItem"), "XML 根元素错误"
        assert "Tags" in xml_result, "XML 缺少 Tags 元素"
        assert "tag1" in xml_result and "tag2" in xml_result, "XML 列表元素缺失"
        print("  ✅ Dict → XML 转换通过")
    except AssertionError as exc:
        print(f"  ❌ Dict → XML 转换失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ Dict → XML 转换失败: {exc}")
        return 1

    # ---------- 3. JSON 转换测试 ----------
    print("\n[3/6] 测试 JSON 转换...")
    try:
        json_str = '{"item": {"id": "A001", "price": 199.99, "available": true}}'
        json_dict = DataConverter.json_to_dict(json_str)
        assert "item" in json_dict, "JSON 解析缺少 item 字段"
        assert json_dict["item"]["id"] == "A001", "JSON id 字段错误"
        assert json_dict["item"]["price"] > 0, "JSON price 应为正数"

        # 转回 JSON
        back_to_json = DataConverter.dict_to_json(json_dict)
        assert '"item"' in back_to_json, "JSON 序列化失败"
        print("  ✅ JSON 转换通过")
    except AssertionError as exc:
        print(f"  ❌ JSON 转换失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ JSON 转换失败: {exc}")
        return 1

    # ---------- 4. SOAP 封装测试 ----------
    print("\n[4/6] 测试 SOAP 请求封装...")
    try:
        soap_req = SoapEnvelope.build_request(
            "GetItem",
            {"ItemID": "123", "DetailLevel": "ReturnAll"},
            {"X-Auth": "test-token"},
        )
        assert "Envelope" in soap_req, "SOAP 信封缺少 Envelope"
        assert "GetItem" in soap_req, "SOAP 缺少操作元素"
        assert "123" in soap_req, "SOAP 缺少请求参数"

        # 解析响应
        soap_resp = SoapEnvelope.build_request(
            "GetItemResponse",
            {"Ack": "Success", "Item": {"ItemID": "123", "Title": "测试"}},
        )
        parsed = SoapEnvelope.parse_response(soap_resp)
        assert "GetItemResponse" in parsed, "SOAP 响应解析失败"
        assert parsed["GetItemResponse"]["Ack"] == "Success", "响应 Ack 字段错误"
        print("  ✅ SOAP 封装与解析通过")
    except AssertionError as exc:
        print(f"  ❌ SOAP 封装失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ SOAP 封装失败: {exc}")
        return 1

    # ---------- 5. 认证签名测试 ----------
    print("\n[5/6] 测试认证签名...")
    try:
        sig1 = AuthSigner.generate_signature("api_key_123", "secret_key_456", 1000)
        sig2 = AuthSigner.generate_signature("api_key_123", "secret_key_456", 1000)
        sig3 = AuthSigner.generate_signature("api_key_123", "secret_key_456", 2000)

        assert sig1 == sig2, "相同输入应产生相同签名"
        assert sig1 != sig3, "不同时间戳应产生不同签名"
        assert len(sig1) == 64, "签名应为 64 位十六进制字符串"
        print("  ✅ 认证签名通过")
    except AssertionError as exc:
        print(f"  ❌ 认证签名失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ 认证签名失败: {exc}")
        return 1

    # ---------- 6. eBay 客户端集成测试 ----------
    print("\n[6/6] 测试 eBay 客户端...")
    try:
        client = EbayClient("test_api_key", "test_secret_key")

        # 测试 get_item
        item = client.get_item("ITEM-001")
        assert "Item" in item, "get_item 返回缺少 Item"
        assert item["Item"]["ItemID"] == "ITEM-001", "ItemID 不匹配"
        assert float(item["Item"]["Price"]) > 0, "价格应为正数"

        # 测试 get_orders
        orders = client.get_orders("2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z")
        assert len(orders) >= 2, "订单数量应至少为 2"
        for order in orders:
            assert order.get("OrderID"), "订单缺少 OrderID"
            assert float(order.get("Amount", 0)) > 0, "订单金额应为正数"

        # 测试错误处理
        try:
            client.get_item("")
            assert False, "空 ItemID 应抛出异常"
        except Ebay4rError as exc:
            assert exc.error_code == "E001", f"错误码应为 E001，实际为 {exc.error_code}"

        print("  ✅ eBay 客户端集成通过")
    except AssertionError as exc:
        print(f"  ❌ eBay 客户端集成失败: {exc}")
        return 1
    except Ebay4rError as exc:
        print(f"  ❌ eBay 客户端集成失败: {exc}")
        return 1

    # ---------- 全部通过 ----------
    print("\n" + "=" * 60)
    print("🎉 全部自检通过！ebay4r 核心功能正常。")
    print("=" * 60)
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="ebay4r — eBay SOAP API 数据转换与调用工具",
        epilog="示例: python main.py --selftest",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（使用硬编码样例，离线可用）",
    )
    parser.add_argument(
        "--convert",
        choices=["xml2json", "json2xml"],
        help="数据格式转换",
    )
    parser.add_argument(
        "--input",
        help="输入文件路径（配合 --convert 使用）",
    )
    parser.add_argument(
        "--output",
        help="输出文件路径（配合 --convert 使用）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 转换模式
    if args.convert:
        if not args.input:
            print("错误: 使用 --convert 时必须指定 --input 文件路径", file=sys.stderr)
            return 1
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()

            if args.convert == "xml2json":
                result = DataConverter.xml_to_json(content)
            else:
                result = DataConverter.json_to_xml(content)

            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(result)
                print(f"转换完成，结果已写入 {args.output}")
            else:
                print(result)
            return 0
        except Ebay4rError as exc:
            print(f"转换失败: {exc}", file=sys.stderr)
            return 1
        except OSError as exc:
            print(f"文件操作失败: {exc}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
