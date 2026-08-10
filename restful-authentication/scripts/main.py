#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RESTful 认证数据解析与结构化输出工具

本脚本根据功能规格独立实现，用于解析 RESTful 认证相关数据，
生成结构化的校验结果与置信度提示。

仅依赖 Python 标准库，无需第三方安装。
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "参数解析失败",
    "E002": "输入数据格式不支持",
    "E003": "JSON 解析错误",
    "E004": "YAML 解析错误",
    "E005": "Key-Value 解析错误",
    "E006": "URL 参数解析错误",
    "E007": "输出格式序列化失败",
    "E008": "缺少必要输入数据",
    "E009": "字段提取失败",
    "E010": "内部逻辑错误",
}

# 置信度等级定义
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 常见认证相关字段的识别模式
FIELD_PATTERNS = {
    "token": r"(?i)(token|access_token|auth_token|jwt)",
    "api_key": r"(?i)(api[_-]?key|apikey)",
    "secret": r"(?i)(secret|client_secret|app_secret)",
    "username": r"(?i)(username|user_name|login|account)",
    "password": r"(?i)(password|passwd|pwd)",
    "client_id": r"(?i)(client[_-]?id|app[_-]?id)",
    "refresh_token": r"(?i)(refresh[_-]?token)",
    "expires_in": r"(?i)(expires[_-]?in|expiration|expiry)",
    "grant_type": r"(?i)(grant[_-]?type)",
    "scope": r"(?i)(scope|permissions?)",
    "user_id": r"(?i)(user[_-]?id|uid|sub)",
}


class AuthenticationParser:
    """认证数据解析器主类"""

    def __init__(self) -> None:
        """初始化解析器"""
        self.supported_formats = ["json", "yaml", "keyvalue", "url"]

    def parse(self, data: str, input_format: Optional[str] = None) -> Dict[str, Any]:
        """
        解析认证数据，返回结构化结果

        Args:
            data: 输入的认证数据文本
            input_format: 输入格式（json/yaml/keyvalue/url），None 时自动检测

        Returns:
            结构化解析结果字典

        Raises:
            ValueError: 当数据无法解析时抛出，包含错误码
        """
        if not data or not data.strip():
            raise ValueError(f"[{ERROR_CODES['E008']}] {ERROR_CODES['E008']}: 输入数据为空")

        # 自动检测格式或使用指定格式
        if input_format is None:
            detected_format = self._detect_format(data)
            if detected_format is None:
                raise ValueError(f"[{ERROR_CODES['E002']}] {ERROR_CODES['E002']}: 无法识别输入格式")
            input_format = detected_format
        elif input_format not in self.supported_formats:
            raise ValueError(f"[{ERROR_CODES['E002']}] {ERROR_CODES['E002']}: 不支持的格式: {input_format}")

        # 根据格式调用对应的解析方法
        try:
            if input_format == "json":
                parsed_data = self._parse_json(data)
            elif input_format == "yaml":
                parsed_data = self._parse_yaml(data)
            elif input_format == "keyvalue":
                parsed_data = self._parse_keyvalue(data)
            elif input_format == "url":
                parsed_data = self._parse_url(data)
            else:
                raise ValueError(f"[{ERROR_CODES['E002']}] {ERROR_CODES['E002']}: 未知格式 {input_format}")

            # 生成结构化输出
            return self._build_result(parsed_data)

        except ValueError as e:
            # 重新抛出带错误码的异常
            if str(e).startswith("["):
                raise
            raise ValueError(f"[{ERROR_CODES['E003']}] {ERROR_CODES['E003']}: {str(e)}")

    def _detect_format(self, data: str) -> Optional[str]:
        """检测数据格式"""
        stripped = data.strip()

        # JSON 格式检测
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                json.loads(stripped)
                return "json"
            except json.JSONDecodeError:
                pass

        # URL 格式检测
        if "://" in stripped or stripped.startswith("?"):
            return "url"

        # YAML 格式检测（包含冒号+空格）
        if re.search(r"^[\w\-]+\s*:", stripped, re.MULTILINE):
            return "yaml"

        # Key-Value 格式检测
        if re.search(r"[\w\-]+\s*[=:]\s*\S+", stripped):
            return "keyvalue"

        return None

    def _parse_json(self, data: str) -> Dict[str, Any]:
        """解析 JSON 格式"""
        try:
            result = json.loads(data)
            if not isinstance(result, dict):
                # 如果是列表，尝试转换为字典
                if isinstance(result, list) and result:
                    result = {"data": result}
                else:
                    raise ValueError("JSON 数据不是对象类型")
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析错误: {str(e)}")

    def _parse_yaml(self, data: str) -> Dict[str, Any]:
        """解析 YAML 格式（简化实现，支持基本键值对）"""
        result: Dict[str, Any] = {}
        try:
            lines = data.strip().split("\n")
            current_key: Optional[str] = None
            current_indent = 0

            for line in lines:
                if not line.strip() or line.strip().startswith("#"):
                    continue

                # 计算缩进
                indent = len(line) - len(line.lstrip())

                # 处理嵌套结构（简化：只支持一层嵌套）
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if not value:  # 嵌套结构开始
                        current_key = key
                        current_indent = indent
                        result[key] = {}
                    else:
                        # 处理引号
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        # 处理布尔值和数字
                        elif value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False
                        else:
                            try:
                                value = int(value)
                            except ValueError:
                                try:
                                    value = float(value)
                                except ValueError:
                                    pass

                        if current_key and indent > current_indent:
                            # 属于嵌套结构
                            if isinstance(result.get(current_key), dict):
                                result[current_key][key] = value
                            else:
                                result[current_key] = {key: value}
                        else:
                            result[key] = value
                            current_key = None

            return result
        except Exception as e:
            raise ValueError(f"YAML 解析错误: {str(e)}")

    def _parse_keyvalue(self, data: str) -> Dict[str, Any]:
        """解析 Key-Value 格式"""
        result: Dict[str, Any] = {}
        try:
            lines = data.strip().split("\n")
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # 支持 = 或 : 分隔
                match = re.match(r"^([\w\-]+)\s*[=:]\s*(.+)$", line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # 去除可能的引号
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    # 尝试转换类型
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    else:
                        try:
                            value = int(value)
                        except ValueError:
                            try:
                                value = float(value)
                            except ValueError:
                                pass

                    result[key] = value

            return result
        except Exception as e:
            raise ValueError(f"Key-Value 解析错误: {str(e)}")

    def _parse_url(self, data: str) -> Dict[str, Any]:
        """解析 URL 参数"""
        try:
            # 处理完整 URL 或纯查询字符串
            if "://" in data:
                parsed = urlparse(data)
                query_string = parsed.query
                # 同时提取 URL 路径中的可能参数
                path_params = self._extract_path_params(parsed.path)
            else:
                query_string = data.lstrip("?")
                path_params = {}

            # 解析查询参数
            query_params = parse_qs(query_string, keep_blank_values=True)
            # 将列表值转换为单值（如果只有一个元素）
            result = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}

            # 合并路径参数
            result.update(path_params)

            return result
        except Exception as e:
            raise ValueError(f"URL 参数解析错误: {str(e)}")

    def _extract_path_params(self, path: str) -> Dict[str, str]:
        """从 URL 路径提取参数"""
        params = {}
        # 匹配类似 /users/123/token/abc 的模式
        parts = path.strip("/").split("/")
        for i, part in enumerate(parts):
            if part in ("users", "token", "auth", "api", "oauth"):
                if i + 1 < len(parts):
                    # 尝试识别 ID 类参数
                    if re.match(r"^[\w\-]+$", parts[i + 1]):
                        params[f"{part}_id"] = parts[i + 1]
        return params

    def _build_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建结构化输出结果"""
        try:
            result = {
                "meta": {
                    "version": "1.0.1",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "parser": "restful-authentication",
                },
                "fields": [],
                "summary": {
                    "total_fields": 0,
                    "high_confidence": 0,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "missing_required": [],
                },
            }

            # 提取并分析每个字段
            for key, value in data.items():
                field_info = self._analyze_field(key, value)
                result["fields"].append(field_info)

                # 更新统计
                result["summary"]["total_fields"] += 1
                if field_info["confidence"] == CONFIDENCE_HIGH:
                    result["summary"]["high_confidence"] += 1
                elif field_info["confidence"] == CONFIDENCE_MEDIUM:
                    result["summary"]["medium_confidence"] += 1
                else:
                    result["summary"]["low_confidence"] += 1

            # 检查缺失的必填字段
            missing = self._check_missing_required(data)
            result["summary"]["missing_required"] = missing

            return result

        except Exception as e:
            raise ValueError(f"[{ERROR_CODES['E009']}] {ERROR_CODES['E009']}: 字段提取失败: {str(e)}")

    def _analyze_field(self, key: str, value: Any) -> Dict[str, Any]:
        """分析单个字段的类型和置信度"""
        field_type = self._detect_field_type(key, value)
        confidence = self._calculate_confidence(key, value, field_type)

        # 敏感字段脱敏处理
        display_value = self._mask_sensitive_value(key, value)

        return {
            "key": key,
            "value": display_value,
            "type": field_type,
            "confidence": confidence,
            "description": self._get_field_description(key, field_type),
        }

    def _detect_field_type(self, key: str, value: Any) -> str:
        """检测字段类型"""
        # 根据键名判断
        lower_key = key.lower()
        if any(word in lower_key for word in ["token", "key", "secret"]):
            return "credential"
        elif any(word in lower_key for word in ["username", "user", "account"]):
            return "identity"
        elif any(word in lower_key for word in ["expires", "expiry", "timeout"]):
            return "time"
        elif any(word in lower_key for word in ["scope", "permission", "role"]):
            return "scope"
        elif any(word in lower_key for word in ["type", "grant"]):
            return "type"
        else:
            # 根据值类型判断
            if isinstance(value, bool):
                return "boolean"
            elif isinstance(value, int):
                return "integer"
            elif isinstance(value, float):
                return "number"
            elif isinstance(value, str):
                if value.startswith("http"):
                    return "url"
                elif re.match(r"^[\w\-\.]+@[\w\-\.]+\.\w+$", value):
                    return "email"
                elif re.match(r"^\d{4}-\d{2}-\d{2}", value):
                    return "date"
                return "string"
            elif isinstance(value, dict):
                return "object"
            elif isinstance(value, list):
                return "array"
            return "unknown"

    def _calculate_confidence(self, key: str, value: Any, field_type: str) -> str:
        """计算字段置信度"""
        # 高置信度：明确的认证字段且值非空
        high_patterns = [
            r"^(access[_-]?token|auth[_-]?token|jwt|bearer)$",
            r"^(api[_-]?key|client[_-]?secret|app[_-]?secret)$",
            r"^(client[_-]?id|app[_-]?id)$",
            r"^(refresh[_-]?token)$",
        ]
        for pattern in high_patterns:
            if re.match(pattern, key, re.IGNORECASE) and value is not None:
                return CONFIDENCE_HIGH

        # 中置信度：常见认证相关字段
        medium_patterns = [
            r"(token|secret|key|credential)",
            r"(username|login|account)",
            r"(expires|expiry|timeout)",
            r"(grant[_-]?type|scope|permission)",
        ]
        for pattern in medium_patterns:
            if re.match(pattern, key, re.IGNORECASE):
                return CONFIDENCE_MEDIUM

        # 低置信度：其他字段
        return CONFIDENCE_LOW

    def _mask_sensitive_value(self, key: str, value: Any) -> Any:
        """对敏感字段进行脱敏处理"""
        if value is None:
            return None

        # 判断是否为敏感字段
        sensitive_keywords = ["token", "secret", "password", "api_key", "apikey"]
        is_sensitive = any(keyword in key.lower() for keyword in sensitive_keywords)

        if isinstance(value, str) and is_sensitive and len(value) > 8:
            # 保留前4位和后4位，中间用 * 替代
            return value[:4] + "****" + value[-4:]
        return value

    def _get_field_description(self, key: str, field_type: str) -> str:
        """获取字段描述"""
        descriptions = {
            "credential": "认证凭据",
            "identity": "用户身份标识",
            "time": "时间相关参数",
            "scope": "权限范围",
            "type": "认证类型",
            "boolean": "布尔值",
            "integer": "整数值",
            "number": "数值",
            "url": "URL地址",
            "email": "邮箱地址",
            "date": "日期时间",
            "string": "字符串",
            "object": "对象",
            "array": "数组",
            "unknown": "未知类型",
        }
        return descriptions.get(field_type, f"字段: {key}")

    def _check_missing_required(self, data: Dict[str, Any]) -> List[str]:
        """检查缺失的必填字段"""
        # 常见必填字段
        required_fields = ["token", "client_id", "client_secret"]
        missing = []
        for field in required_fields:
            if field not in data:
                missing.append(f"[需核实:{field}]")
        return missing


class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def format(data: Dict[str, Any], output_format: str = "json") -> str:
        """格式化输出"""
        try:
            if output_format == "json":
                return json.dumps(data, ensure_ascii=False, indent=2)
            elif output_format == "yaml":
                return OutputFormatter._to_yaml(data)
            else:
                raise ValueError(f"[{ERROR_CODES['E007']}] 不支持的输出格式: {output_format}")
        except Exception as e:
            raise ValueError(f"[{ERROR_CODES['E007']}] {ERROR_CODES['E007']}: 输出格式化失败: {str(e)}")

    @staticmethod
    def _to_yaml(data: Any, indent: int = 0) -> str:
        """转换为 YAML 格式（简化实现）"""
        lines = []
        prefix = " " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(OutputFormatter._to_yaml(value, indent + 2))
                else:
                    lines.append(f"{prefix}{key}: {OutputFormatter._format_value(value)}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(OutputFormatter._to_yaml(item, indent + 2))
                else:
                    lines.append(f"{prefix}- {OutputFormatter._format_value(item)}")
        else:
            lines.append(f"{prefix}{OutputFormatter._format_value(data)}")

        return "\n".join(lines)

    @staticmethod
    def _format_value(value: Any) -> str:
        """格式化单个值"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # 需要引号的情况
            if ":" in value or value.startswith((" ", "-", "?")):
                return f'"{value}"'
            return value
        return str(value)


def run_selftest() -> bool:
    """运行内置自检测试"""
    print("=" * 60)
    print("运行自检测试...")
    print("=" * 60)

    test_cases = [
        {
            "name": "JSON 格式测试",
            "data": '{"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "token_type": "Bearer", "expires_in": 3600, "scope": "read write"}',
            "format": "json",
        },
        {
            "name": "Key-Value 格式测试",
            "data": 'client_id=my_client_123\nclient_secret=secret_key_abc\nusername=test_user\ngrant_type=authorization_code',
            "format": "keyvalue",
        },
        {
            "name": "URL 格式测试",
            "data": "https://api.example.com/oauth/callback?code=auth_code_123&state=xyz&scope=read",
            "format": "url",
        },
        {
            "name": "YAML 格式测试",
            "data": 'api_key: my_api_key_123\nusername: admin\npassword: pass123\nroles:\n  - admin\n  - user',
            "format": "yaml",
        },
        {
            "name": "自动检测测试",
            "data": '{"refresh_token": "refresh_abc_123", "client_id": "app_001"}',
            "format": None,
        },
    ]

    all_passed = True
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        try:
            parser = AuthenticationParser()
            result = parser.parse(test["data"], test["format"])
            formatter = OutputFormatter()
            output = formatter.format(result, "json")

            # 验证结果结构
            assert "meta" in result, "缺少 meta 字段"
            assert "fields" in result, "缺少 fields 字段"
            assert "summary" in result, "缺少 summary 字段"
            assert result["summary"]["total_fields"] > 0, "字段数量为 0"
            assert output, "输出为空"

            print("  ✓ 通过")
            print(f"  解析字段数: {result['summary']['total_fields']}")
            print(f"  高置信度: {result['summary']['high_confidence']}")
            print(f"  中置信度: {result['summary']['medium_confidence']}")
            print(f"  低置信度: {result['summary']['low_confidence']}")

        except Exception as e:
            all_passed = False
            print(f"  ✗ 失败: {str(e)}")

    print("\n" + "=" * 60)
    if all_passed:
        print("所有测试通过 ✓")
    else:
        print("存在失败的测试 ✗")
    print("=" * 60)

    return all_passed


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RESTful 认证数据解析与结构化输出工具",
        epilog="示例: python main.py --input '{\"token\": \"abc123\"}' --format json",
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入的认证数据文本",
    )
    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["json", "yaml", "keyvalue", "url"],
        help="输入格式（默认自动检测）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "yaml"],
        default="json",
        help="输出格式（默认 JSON）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检测试",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="restful-authentication 1.0.1",
    )

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        print(f"错误 [{ERROR_CODES['E008']}]: 请提供输入数据（使用 --input 参数）", file=sys.stderr)
        print("提示: 使用 --selftest 运行内置测试，或 --help 查看帮助", file=sys.stderr)
        return 1

    try:
        # 解析数据
        parser = AuthenticationParser()
        result = parser.parse(args.input, args.format)

        # 格式化输出
        formatter = OutputFormatter()
        output = formatter.format(result, args.output)

        # 输出结果
        print(output)

        # 输出摘要信息到 stderr
        summary = result["summary"]
        print(f"\n处理完成: 共 {summary['total_fields']} 个字段", file=sys.stderr)
        print(f"置信度分布: 高={summary['high_confidence']}, 中={summary['medium_confidence']}, 低={summary['low_confidence']}", file=sys.stderr)
        if summary["missing_required"]:
            missing_str = ", ".join(summary["missing_required"])
            print(f"提示缺失字段: {missing_str}", file=sys.stderr)

        return 0

    except ValueError as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERROR_CODES['E010']}]: 未预期的错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
