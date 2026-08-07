#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merb-core: 数据提炼与结构化输出工具

本脚本根据功能规格独立实现（clean-room），提供：
- 数据源解析（文本/URL）
- 关键信息识别（实体、数字、日期、状态）
- 结构化输出（JSON）
- 置信度标注（高/中/低）
- 批量处理能力
- 内置自检（--selftest）

错误码说明：
    E001: 参数错误
    E002: 输入数据为空
    E003: 输入类型不支持
    E004: URL 访问失败
    E005: 文件读取失败
    E006: 数据解析失败
    E007: 字段提取失败
    E008: 输出序列化失败
    E009: 内部逻辑错误
    E010: 自检失败
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# ============================================================
# 常量定义
# ============================================================

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"

# 日期格式模式（支持常见格式）
DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",
    r"\d{1,2}[-/月]\d{1,2}[-/日]\d{2,4}",
    r"\d{4}年\d{1,2}月\d{1,2}日",
]

# 数字模式（整数、小数、百分比）
NUMBER_PATTERN = r"-?\d+(?:\.\d+)?%?"

# 邮箱模式
EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# 手机号模式（中国大陆）
PHONE_PATTERN = r"1[3-9]\d{9}"

# URL 模式
URL_PATTERN = r"https?://[^\s<>\"']+|www\.[^\s<>\"']+"


# ============================================================
# 工具函数
# ============================================================

def _get_error_message(code: str) -> str:
    """获取错误码对应的中文描述"""
    messages = {
        "E001": "参数错误",
        "E002": "输入数据为空",
        "E003": "输入类型不支持",
        "E004": "URL 访问失败",
        "E005": "文件读取失败",
        "E006": "数据解析失败",
        "E007": "字段提取失败",
        "E008": "输出序列化失败",
        "E009": "内部逻辑错误",
        "E010": "自检失败",
    }
    return messages.get(code, "未知错误")


class MerbError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or _get_error_message(code)
        super().__init__(f"[{code}] {self.message}")


def _safe_date_parse(text: str) -> Optional[str]:
    """尝试从文本中提取日期，返回标准化的日期字符串或 None"""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            # 尝试标准化日期格式
            try:
                # 处理中文字符
                date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
                # 统一分隔符
                date_str = date_str.replace("/", "-")
                # 解析并重新格式化
                parts = date_str.split("-")
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    # 处理两位年份
                    if year < 100:
                        year += 2000
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, IndexError):
                continue
    return None


def _calculate_confidence(value: Any, source_type: str) -> Tuple[str, str]:
    """
    根据字段值和来源类型计算置信度
    
    返回: (置信度等级, 理由)
    """
    if value is None or value == "":
        return CONFIDENCE_LOW, "字段为空或未找到"
    
    if source_type == "email":
        return CONFIDENCE_HIGH, "标准邮箱格式"
    elif source_type == "phone":
        return CONFIDENCE_HIGH, "标准手机号格式"
    elif source_type == "date":
        if re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
            return CONFIDENCE_HIGH, "符合标准日期格式"
        else:
            return CONFIDENCE_MEDIUM, "日期格式可能不标准"
    elif source_type == "number":
        return CONFIDENCE_HIGH, "明确数字格式"
    elif source_type == "url":
        return CONFIDENCE_MEDIUM, "URL 格式验证通过"
    elif source_type == "name":
        return CONFIDENCE_MEDIUM, "名称字段需人工确认"
    else:
        return CONFIDENCE_MEDIUM, "常规字段提取"


# ============================================================
# 核心解析类
# ============================================================

class DataParser:
    """数据解析器：负责从各种输入源提取结构化信息"""

    def __init__(self, custom_fields: Optional[List[str]] = None):
        """
        初始化解析器
        
        Args:
            custom_fields: 自定义字段列表，默认为内置字段
        """
        self.custom_fields = custom_fields or ["name", "email", "phone", "date", "number", "url", "content"]
        self._validate_fields()

    def _validate_fields(self):
        """验证字段配置"""
        if not self.custom_fields:
            raise MerbError("E001", "字段列表不能为空")
        # 去重并保持顺序
        seen = set()
        self.custom_fields = [f for f in self.custom_fields if not (f in seen or seen.add(f))]

    def _extract_field(self, text: str, field: str) -> Tuple[Optional[Any], str]:
        """
        从文本中提取指定字段
        
        Returns:
            (提取值, 置信度)
        """
        if not text or not isinstance(text, str):
            return None, CONFIDENCE_LOW

        field = field.lower().strip()

        # 根据字段类型执行不同提取逻辑
        if field in ("email", "邮箱"):
            match = re.search(EMAIL_PATTERN, text)
            value = match.group() if match else None
            conf = _calculate_confidence(value, "email")
            return value, conf[0]

        elif field in ("phone", "手机", "电话"):
            match = re.search(PHONE_PATTERN, text)
            value = match.group() if match else None
            conf = _calculate_confidence(value, "phone")
            return value, conf[0]

        elif field in ("date", "日期"):
            value = _safe_date_parse(text)
            conf = _calculate_confidence(value, "date")
            return value, conf[0]

        elif field in ("number", "数字", "金额"):
            matches = re.findall(NUMBER_PATTERN, text)
            value = matches[0] if matches else None
            conf = _calculate_confidence(value, "number")
            return value, conf[0]

        elif field in ("url", "链接", "网址"):
            match = re.search(URL_PATTERN, text)
            value = match.group() if match else None
            conf = _calculate_confidence(value, "url")
            return value, conf[0]

        elif field in ("name", "姓名", "名称"):
            # 简单启发式：在文本开头或特定标记后找名字
            patterns = [
                r"(?:姓名|名字|名称)[:：\s]*([\u4e00-\u9fa5]{2,8})",
                r"^([\u4e00-\u9fa5]{2,8})(?:\s|,|，|。)",
            ]
            value = None
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = match.group(1)
                    break
            conf = _calculate_confidence(value, "name")
            return value, conf[0]

        elif field in ("content", "内容", "文本"):
            # 内容字段直接返回完整文本
            value = text.strip()
            conf = _calculate_confidence(value, "content")
            return value, conf[0]

        else:
            # 自定义字段：尝试按常见模式提取
            return None, CONFIDENCE_LOW

    def parse(self, data: Any) -> Dict[str, Any]:
        """
        解析输入数据，返回结构化结果
        
        Args:
            data: 输入数据（字符串、字典、列表等）
            
        Returns:
            结构化结果字典
        """
        try:
            # 数据预处理
            processed_data = self._preprocess_data(data)
            if not processed_data:
                raise MerbError("E002")

            results = []
            
            # 处理单条数据
            if isinstance(processed_data, str):
                results.append(self._parse_single(processed_data))
            # 处理多条数据
            elif isinstance(processed_data, list):
                for item in processed_data:
                    if isinstance(item, str):
                        results.append(self._parse_single(item))
                    elif isinstance(item, dict):
                        results.append(self._parse_dict(item))
                    else:
                        results.append(self._parse_single(str(item)))
            elif isinstance(processed_data, dict):
                results.append(self._parse_dict(processed_data))
            else:
                raise MerbError("E003", f"不支持的数据类型: {type(data)}")

            return {
                "success": True,
                "count": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat(),
            }

        except MerbError:
            raise
        except Exception as e:
            raise MerbError("E006", f"数据解析失败: {str(e)}") from e

    def _preprocess_data(self, data: Any) -> Any:
        """数据预处理：支持 URL 和文件路径"""
        if isinstance(data, str):
            # 检查是否为 URL
            if data.startswith(("http://", "https://", "www.")):
                try:
                    return self._fetch_url(data)
                except Exception as e:
                    raise MerbError("E004", f"URL 访问失败: {str(e)}") from e
            # 检查是否为文件路径
            elif data.endswith((".txt", ".md", ".json", ".csv")):
                try:
                    with open(data, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception as e:
                    raise MerbError("E005", f"文件读取失败: {str(e)}") from e
        return data

    def _fetch_url(self, url: str) -> str:
        """获取 URL 内容"""
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10) as response:
                return response.read().decode("utf-8", errors="ignore")
        except (URLError, HTTPError) as e:
            raise MerbError("E004", f"URL 访问失败: {str(e)}") from e

    def _parse_single(self, text: str) -> Dict[str, Any]:
        """解析单条文本"""
        if not text or not text.strip():
            raise MerbError("E002")

        extracted = {}
        for field in self.custom_fields:
            value, confidence = self._extract_field(text, field)
            extracted[field] = {
                "value": value,
                "confidence": confidence,
            }
        
        return {
            "source": "text",
            "original": text[:200] + ("..." if len(text) > 200 else ""),
            "fields": extracted,
        }

    def _parse_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析字典类型数据"""
        if not data:
            raise MerbError("E002")

        extracted = {}
        for field in self.custom_fields:
            # 直接查找字段
            if field in data:
                value = data[field]
                conf = _calculate_confidence(value, field)
                extracted[field] = {
                    "value": value,
                    "confidence": conf[0],
                }
            else:
                # 尝试从字符串值中提取
                text = json.dumps(data, ensure_ascii=False)
                value, confidence = self._extract_field(text, field)
                extracted[field] = {
                    "value": value,
                    "confidence": confidence,
                }

        return {
            "source": "dict",
            "original": json.dumps(data, ensure_ascii=False)[:200],
            "fields": extracted,
        }


# ============================================================
# 输出格式化
# ============================================================

class OutputFormatter:
    """输出格式化器"""

    @staticmethod
    def to_json(data: Dict[str, Any], pretty: bool = True) -> str:
        """转换为 JSON 字符串"""
        try:
            if pretty:
                return json.dumps(data, ensure_ascii=False, indent=2)
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            raise MerbError("E008", f"JSON 序列化失败: {str(e)}") from e

    @staticmethod
    def to_markdown_table(data: Dict[str, Any]) -> str:
        """转换为 Markdown 表格"""
        try:
            if not data.get("results"):
                return "无数据"
            
            # 获取所有字段名
            fields = set()
            for result in data["results"]:
                fields.update(result["fields"].keys())
            fields = sorted(fields)

            # 构建表头
            lines = ["| 序号 | 来源 | " + " | ".join(fields) + " |",
                     "|------|------|" + "|".join(["------"] * len(fields)) + "|"]

            # 构建数据行
            for idx, result in enumerate(data["results"], 1):
                row_values = []
                for field in fields:
                    field_info = result["fields"].get(field, {})
                    value = field_info.get("value", "")
                    conf = field_info.get("confidence", "")
                    row_values.append(f"{value} ({conf})")
                lines.append(f"| {idx} | {result['source']} | " + " | ".join(row_values) + " |")

            return "\n".join(lines)
        except Exception as e:
            raise MerbError("E008", f"Markdown 转换失败: {str(e)}") from e


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自检
    
    使用硬编码样例数据验证核心逻辑，不依赖外部文件或网络。
    
    Returns:
        True 表示自检通过
    """
    print("开始自检...")
    
    try:
        # 测试数据
        test_cases = [
            {
                "name": "单条文本解析",
                "data": "张三的邮箱是 zhangsan@example.com，电话 13812345678，出生于1990年5月15日。",
                "expected_fields": ["name", "email", "phone", "date"],
            },
            {
                "name": "批量解析",
                "data": [
                    "李四 邮箱 lisi@test.com 电话 13987654321",
                    "王五 邮箱 wangwu@test.com 电话 13711112222",
                ],
                "expected_count": 2,
            },
            {
                "name": "字典解析",
                "data": {"name": "赵六", "email": "zhaoliu@example.com"},
                "expected_fields": ["name", "email"],
            },
            {
                "name": "空数据处理",
                "data": "",
                "expect_error": True,
            },
        ]

        parser = DataParser()
        formatter = OutputFormatter()

        # 执行测试
        for test in test_cases:
            print(f"  测试: {test['name']}")
            
            try:
                result = parser.parse(test["data"])
                
                # 验证预期字段
                if "expected_fields" in test:
                    for field in test["expected_fields"]:
                        assert field in result["results"][0]["fields"], f"缺少字段: {field}"
                        # 检查置信度
                        conf = result["results"][0]["fields"][field]["confidence"]
                        assert conf in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW), f"无效置信度: {conf}"
                
                # 验证预期条数
                if "expected_count" in test:
                    assert result["count"] == test["expected_count"], f"期望 {test['expected_count']} 条，实际 {result['count']} 条"
                
                # 测试 JSON 输出
                json_str = formatter.to_json(result)
                assert json_str, "JSON 输出为空"
                
                print(f"    ✓ 通过")
                
            except MerbError as e:
                if test.get("expect_error"):
                    print(f"    ✓ 预期错误: {e.code}")
                else:
                    raise
            except AssertionError as e:
                print(f"    ✗ 断言失败: {str(e)}")
                raise MerbError("E010", f"自检失败: {str(e)}")

        # 测试 Markdown 输出
        print("  测试: Markdown 输出")
        md_result = parser.parse(test_cases[0]["data"])
        md_str = formatter.to_markdown_table(md_result)
        assert md_str, "Markdown 输出为空"
        assert "|" in md_str, "Markdown 表格格式错误"
        print("    ✓ 通过")

        # 测试日期格式化
        print("  测试: 日期格式化")
        test_date = "2023年12月25日"
        formatted_date = _safe_date_parse(test_date)
        assert formatted_date == "2023-12-25", f"日期格式化错误: {formatted_date}"
        print("    ✓ 通过")

        # 测试置信度计算
        print("  测试: 置信度计算")
        high_conf = _calculate_confidence("test@example.com", "email")
        assert high_conf[0] == CONFIDENCE_HIGH, f"邮箱置信度应为高: {high_conf}"
        low_conf = _calculate_confidence(None, "email")
        assert low_conf[0] == CONFIDENCE_LOW, f"空值置信度应为低: {low_conf}"
        print("    ✓ 通过")

        print("\n所有自检测试通过!")
        return True

    except MerbError as e:
        print(f"\n✗ 自检失败: {e.code} - {e.message}")
        return False
    except Exception as e:
        print(f"\n✗ 自检异常: {str(e)}")
        return False


# ============================================================
# 主程序
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="merb-core: 数据提炼与结构化输出工具",
        epilog="示例: python main.py --input '张三 邮箱 zhangsan@example.com' --fields name,email"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入数据（文本、URL 或文件路径）"
    )
    
    parser.add_argument(
        "--fields", "-f",
        type=str,
        default="name,email,phone,date,number,url,content",
        help="要提取的字段列表，逗号分隔（默认: name,email,phone,date,number,url,content）"
    )
    
    parser.add_argument(
        "--output", "-o",
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认: json）"
    )
    
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="JSON 输出美化格式"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="merb-core 1.0.1"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查必要参数
    if not args.input:
        print("错误: 请提供输入数据 (--input)", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    try:
        # 解析字段配置
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        
        # 创建解析器
        parser_obj = DataParser(custom_fields=fields)
        formatter = OutputFormatter()

        # 执行解析
        result = parser_obj.parse(args.input)

        # 格式化输出
        if args.output == "json":
            output_str = formatter.to_json(result, pretty=args.pretty)
        else:
            output_str = formatter.to_markdown_table(result)

        print(output_str)

    except MerbError as e:
        print(f"错误: {e.code} - {e.message}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误: E009 - 未预期异常: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
