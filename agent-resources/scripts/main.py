#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-resources 技能脚本
========================
将任意数据源（文本/文件/URL）转换为结构化结果，支持批量处理与置信度标注。

本脚本为 clean-room 独立实现，仅依据功能规格编写。
"""

import argparse
import re
import sys
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入数据为空或格式错误",
    "E002": "输入数据不是字符串",
    "E003": "无法解析的日期格式",
    "E004": "无法解析的金额格式",
    "E005": "无效的URL格式",
    "E006": "批量处理时输入格式错误",
    "E007": "输出模板格式错误",
    "E008": "置信度计算失败",
    "E009": "文件读取失败",
    "E010": "未知错误",
}


class ResourceProcessor:
    """核心处理类：负责将非结构化数据转换为结构化结果。"""

    def __init__(self) -> None:
        """初始化处理器，设置默认配置。"""
        self.default_template = {
            "title": "",
            "date": "",
            "amount": None,
            "category": "",
            "description": "",
            "tags": [],
            "confidence": 0.0,
        }

    # ------------------------------------------------------------------
    # 对外主接口
    # ------------------------------------------------------------------
    def process(
        self,
        data: Union[str, List[str]],
        template: Optional[Dict[str, Any]] = None,
        batch: bool = False,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        处理单个或多个数据源。

        参数:
            data: 单个字符串或字符串列表
            template: 自定义输出模板（可选）
            batch: 是否为批量模式

        返回:
            结构化结果字典或字典列表

        错误码:
            E001: 输入为空
            E002: 输入类型错误
            E006: 批量模式输入格式错误
            E007: 模板格式错误
        """
        # 校验输入
        if data is None or (isinstance(data, str) and not data.strip()):
            raise ValueError(f"E001: {ERROR_CODES['E001']}")
        if not isinstance(data, (str, list)):
            raise TypeError(f"E002: {ERROR_CODES['E002']}")

        # 校验模板
        if template is not None and not isinstance(template, dict):
            raise TypeError(f"E007: {ERROR_CODES['E007']}")

        if batch:
            if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
                raise TypeError(f"E006: {ERROR_CODES['E006']}")
            return [self._process_single(item, template) for item in data]
        else:
            if isinstance(data, list):
                # 非批量模式但传入列表，取第一个元素
                data = data[0] if data else ""
            return self._process_single(data, template)

    # ------------------------------------------------------------------
    # 内部处理方法
    # ------------------------------------------------------------------
    def _process_single(
        self, text: str, template: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理单个文本数据源。

        参数:
            text: 输入文本
            template: 自定义模板

        返回:
            结构化结果字典
        """
        # 基础校验
        if not isinstance(text, str):
            raise TypeError(f"E002: {ERROR_CODES['E002']}")
        if not text.strip():
            raise ValueError(f"E001: {ERROR_CODES['E001']}")

        # 合并模板
        merged_template = self.default_template.copy()
        if template:
            merged_template.update(template)

        # 提取字段（只覆盖模板中的空值）
        result = merged_template.copy()
        
        # 提取标题
        extracted_title = self._extract_title(text)
        if extracted_title and not result.get("title"):
            result["title"] = extracted_title
            
        # 提取日期
        extracted_date = self._extract_date(text)
        if extracted_date and not result.get("date"):
            result["date"] = extracted_date
            
        # 提取金额
        extracted_amount = self._extract_amount(text)
        if extracted_amount and result.get("amount") is None:
            result["amount"] = extracted_amount
            
        # 提取分类
        extracted_category = self._extract_category(text)
        if extracted_category and not result.get("category"):
            result["category"] = extracted_category
            
        # 提取描述
        extracted_description = self._extract_description(text)
        if extracted_description and not result.get("description"):
            result["description"] = extracted_description
            
        # 提取标签
        extracted_tags = self._extract_tags(text)
        if extracted_tags and not result.get("tags"):
            result["tags"] = extracted_tags

        # 计算置信度
        result["confidence"] = self._calculate_confidence(result)

        return result

    # ------------------------------------------------------------------
    # 字段提取方法
    # ------------------------------------------------------------------
    def _extract_title(self, text: str) -> Optional[str]:
        """
        提取标题：优先匹配常见标题格式。

        规则:
            - 匹配以#开头的一级标题（允许前导空格）
            - 匹配第一行较短的文本
        """
        # 匹配 # 开头的标题（允许前导空格）
        hash_match = re.search(r"^\s*#\s+(.+)$", text, re.MULTILINE)
        if hash_match:
            return hash_match.group(1).strip()

        # 匹配第一行且长度适中
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            first_line = lines[0]
            if 2 <= len(first_line) <= 100:
                return first_line

        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """
        提取日期：支持多种常见格式。

        规则:
            - YYYY-MM-DD
            - YYYY/MM/DD
            - YYYY年MM月DD日
            - MM-DD-YYYY
        """
        patterns = [
            r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",  # YYYY-MM-DD 或 YYYY/MM/DD
            r"\b(\d{4})年(\d{1,2})月(\d{1,2})日\b",  # 中文日期
            r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b",  # MM-DD-YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[0]) == 4:  # YYYY 开头
                        year, month, day = map(int, groups)
                    else:  # MM 开头
                        month, day, year = map(int, groups)
                    parsed_date = date(year, month, day)
                    return parsed_date.isoformat()
                except ValueError:
                    continue

        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        """
        提取金额：支持货币符号和数字格式。

        规则:
            - 支持 $, ¥, € 等符号
            - 支持千分位分隔符
        """
        # 匹配带货币符号的金额
        currency_patterns = [
            r"[¥￥]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)",  # 人民币
            r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)",  # 美元
            r"€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)",  # 欧元
        ]

        for pattern in currency_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    return float(amount_str)
                except ValueError:
                    continue

        # 匹配纯数字金额（带小数）
        plain_pattern = r"\b(\d{1,3}(?:,\d{3})*\.\d{2})\b"
        match = re.search(plain_pattern, text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return float(amount_str)
            except ValueError:
                pass

        return None

    def _extract_category(self, text: str) -> Optional[str]:
        """
        提取分类：基于关键词匹配。

        规则:
            - 匹配常见分类关键词
        """
        categories = {
            "科技": ["科技", "技术", "软件", "硬件", "互联网", "AI", "人工智能"],
            "金融": ["金融", "银行", "投资", "股票", "基金", "保险", "理财"],
            "教育": ["教育", "学校", "学习", "课程", "培训", "考试"],
            "医疗": ["医疗", "医院", "健康", "药品", "医生", "治疗"],
            "商业": ["商业", "企业", "公司", "市场", "营销", "销售"],
            "生活": ["生活", "家居", "美食", "旅游", "娱乐", "购物"],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return category

        return None

    def _extract_description(self, text: str) -> Optional[str]:
        """
        提取描述：从文本中提取关键描述信息。

        规则:
            - 去除标题行后的第一段有效文本
            - 限制长度在200字以内
        """
        # 去除标题行
        lines = text.splitlines()
        content_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                content_lines.append(stripped)

        if content_lines:
            description = " ".join(content_lines[:3])  # 取前三行
            if len(description) > 200:
                description = description[:200] + "..."
            return description

        return None

    def _extract_tags(self, text: str) -> List[str]:
        """
        提取标签：基于关键词和格式。

        规则:
            - 匹配 # 标签
            - 匹配常见实体词
        """
        tags = []

        # 匹配 # 标签
        hash_tags = re.findall(r"#(\w+)", text)
        tags.extend(hash_tags)

        # 匹配常见实体词
        entity_patterns = [
            (r"\b(?:https?://)?(?:www\.)?(\w+\.\w+)\b", "域名"),
            (r"\b[A-Z]{2,10}\b", "缩写"),
            (r"\b\d{3}-\d{4}\b", "编号"),
        ]

        for pattern, tag_type in entity_patterns:
            matches = re.findall(pattern, text)
            for match in matches[:5]:  # 每种类型最多取5个
                if isinstance(match, tuple):
                    match = match[0]
                if match not in tags:
                    tags.append(match)

        return tags[:10]  # 最多返回10个标签

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """
        计算置信度：基于字段填充率。

        规则:
            - 每个非空字段贡献一定比例
            - 置信度范围 0.0 ~ 1.0
        """
        try:
            fields = ["title", "date", "amount", "category", "description", "tags"]
            filled = sum(1 for field in fields if result.get(field))

            # 基础置信度
            confidence = filled / len(fields)

            # 加权：标题和描述权重更高
            if result.get("title"):
                confidence += 0.1
            if result.get("description"):
                confidence += 0.1

            return min(confidence, 1.0)
        except Exception:
            raise RuntimeError(f"E008: {ERROR_CODES['E008']}")

    def validate_url(self, url: str) -> bool:
        """
        验证URL格式是否有效。

        参数:
            url: 待验证的URL字符串

        返回:
            True 如果URL格式有效，否则 False

        错误码:
            E005: URL格式无效
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"E005: {ERROR_CODES['E005']}")
            if parsed.scheme not in ["http", "https"]:
                raise ValueError(f"E005: {ERROR_CODES['E005']}")
            return True
        except Exception as e:
            if str(e).startswith("E005"):
                raise
            raise ValueError(f"E005: {ERROR_CODES['E005']}")

    def read_file(self, filepath: str) -> str:
        """
        读取文本文件内容。

        参数:
            filepath: 文件路径

        返回:
            文件内容字符串

        错误码:
            E009: 文件读取失败
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"E009: {ERROR_CODES['E009']}: {str(e)}")


# ------------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------------
def run_selftest() -> bool:
    """
    运行内置自检样例，验证核心逻辑。

    使用硬编码数据，不依赖外部文件、网络或当前工作目录。

    返回:
        True 如果所有测试通过，否则 False
    """
    print("=" * 60)
    print("开始自检 (Self-Test)...")
    print("=" * 60)

    processor = ResourceProcessor()
    tests_passed = 0
    total_tests = 0

    # 测试用例 1: 基本处理
    print("\n[测试 1] 基本文本处理")
    total_tests += 1
    try:
        sample1 = """
        # 2024年度财务报告

        公司本年度总收入为 ¥1,234,567.89，较去年增长15%。
        主要业务集中在金融科技领域。
        日期: 2024-12-31
        """
        result = processor.process(sample1)
        assert result["title"] == "2024年度财务报告", f"标题提取失败: {result['title']}"
        assert result["date"] == "2024-12-31", f"日期提取失败: {result['date']}"
        assert result["amount"] is not None and result["amount"] > 1000000, f"金额提取失败: {result['amount']}"
        assert result["category"] == "金融", f"分类提取失败: {result['category']}"
        assert 0.0 < result["confidence"] <= 1.0, f"置信度范围错误: {result['confidence']}"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 2: 批量处理
    print("\n[测试 2] 批量处理")
    total_tests += 1
    try:
        samples = [
            "产品发布通知：新产品将于2025年3月1日上市，售价$99.99",
            "教育优惠活动：购买课程享受8折优惠，截止日期2025/06/30",
        ]
        results = processor.process(samples, batch=True)
        assert isinstance(results, list), "批量处理应返回列表"
        assert len(results) == 2, f"批量处理数量错误: {len(results)}"
        assert all(isinstance(r, dict) for r in results), "每个结果应为字典"
        assert all(0.0 <= r["confidence"] <= 1.0 for r in results), "置信度范围错误"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 3: 日期提取
    print("\n[测试 3] 多种日期格式")
    total_tests += 1
    try:
        date_samples = [
            "日期: 2025-01-15",
            "日期: 2025/02/20",
            "日期: 2025年3月25日",
        ]
        for sample in date_samples:
            result = processor.process(sample)
            assert result["date"], f"未能提取日期: {sample}"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 4: 金额提取
    print("\n[测试 4] 多种金额格式")
    total_tests += 1
    try:
        amount_samples = [
            "价格: $1,234.56",
            "价格: ¥999.00",
            "价格: €500.50",
        ]
        for sample in amount_samples:
            result = processor.process(sample)
            assert result["amount"] is not None, f"未能提取金额: {sample}"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 5: 错误处理
    print("\n[测试 5] 错误处理")
    total_tests += 1
    try:
        # 空输入
        try:
            processor.process("")
            raise AssertionError("空输入应抛出异常")
        except ValueError as e:
            assert str(e).startswith("E001"), f"错误码应为E001: {e}"

        # 错误类型
        try:
            processor.process(12345)
            raise AssertionError("数字输入应抛出异常")
        except TypeError as e:
            assert str(e).startswith("E002"), f"错误码应为E002: {e}"

        # 批量模式错误
        try:
            processor.process(["valid", 123], batch=True)
            raise AssertionError("批量模式混合类型应抛出异常")
        except TypeError as e:
            assert str(e).startswith("E006"), f"错误码应为E006: {e}"

        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 6: URL验证
    print("\n[测试 6] URL验证")
    total_tests += 1
    try:
        valid_urls = [
            "https://example.com",
            "http://www.test.org/path",
            "https://sub.domain.co.uk/api",
        ]
        for url in valid_urls:
            assert processor.validate_url(url), f"有效URL被拒绝: {url}"

        invalid_urls = [
            "not-a-url",
            "ftp://invalid.com",
            "https://",
        ]
        for url in invalid_urls:
            try:
                processor.validate_url(url)
                raise AssertionError(f"无效URL被接受: {url}")
            except ValueError as e:
                assert str(e).startswith("E005"), f"错误码应为E005: {e}"

        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 7: 自定义模板
    print("\n[测试 7] 自定义模板")
    total_tests += 1
    try:
        custom_template = {
            "title": "默认标题",
            "source": "未知来源",
        }
        result = processor.process("这是一段测试文本，没有明显的标题", template=custom_template)
        assert result["title"] == "默认标题", f"自定义模板未生效: {result['title']}"
        assert "source" in result, "自定义字段未添加"
        assert "confidence" in result, "置信度字段应保留"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 8: 标签提取
    print("\n[测试 8] 标签提取")
    total_tests += 1
    try:
        sample = "会议讨论 #AI 和 #机器学习 技术，涉及Python编程"
        result = processor.process(sample)
        assert len(result["tags"]) > 0, "应提取到标签"
        assert "AI" in result["tags"], f"应包含AI标签: {result['tags']}"
        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 9: 文件读取
    print("\n[测试 9] 文件读取")
    total_tests += 1
    try:
        # 使用临时文件测试
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("测试文件内容\n第二行")
            temp_path = f.name

        try:
            content = processor.read_file(temp_path)
            assert "测试文件内容" in content, f"文件内容读取错误: {content}"
        finally:
            os.unlink(temp_path)

        # 测试不存在的文件
        try:
            processor.read_file("/nonexistent/path/file.txt")
            raise AssertionError("不存在的文件应抛出异常")
        except IOError as e:
            assert str(e).startswith("E009"), f"错误码应为E009: {e}"

        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 测试用例 10: 置信度计算
    print("\n[测试 10] 置信度计算")
    total_tests += 1
    try:
        # 高置信度：完整信息
        full_sample = """
        # 产品发布会

        公司将于2025-06-15发布新产品，售价$299.99。
        产品定位在科技领域，主要面向开发者和企业用户。
        关键词: #创新 #技术
        """
        result = processor.process(full_sample)
        assert result["confidence"] > 0.7, f"完整信息置信度应较高: {result['confidence']}"

        # 低置信度：信息缺失
        sparse_sample = "简单文本"
        result = processor.process(sparse_sample)
        assert result["confidence"] < 0.7, f"稀疏信息置信度应较低: {result['confidence']}"

        print("  ✓ 通过")
        tests_passed += 1
    except Exception as e:
        print(f"  ✗ 失败: {e}")

    # 汇总结果
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed}/{total_tests} 测试通过")
    print("=" * 60)

    return tests_passed == total_tests


# ------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    支持参数:
        --input: 输入文本或文件路径
        --file: 从文件读取输入
        --batch: 批量处理模式（输入为JSON数组）
        --template: 自定义模板JSON文件
        --selftest: 运行自检

    返回:
        退出码: 0 成功, 非0 失败
    """
    parser = argparse.ArgumentParser(
        description="智能体技能库资源结构化转换工具",
        epilog="示例: python main.py --input '文本内容' | python main.py --selftest",
    )

    parser.add_argument(
        "--input",
        type=str,
        help="输入文本内容或JSON数组（配合--batch）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="从文件读取输入",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为JSON数组）",
    )
    parser.add_argument(
        "--template",
        type=str,
        help="自定义模板JSON文件路径",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 处理模式
    processor = ResourceProcessor()

    try:
        # 加载模板
        template = None
        if args.template:
            try:
                with open(args.template, "r", encoding="utf-8") as f:
                    template = json.load(f)
            except Exception as e:
                print(f"错误: 无法加载模板文件: {e}", file=sys.stderr)
                return 1

        # 获取输入
        if args.file:
            try:
                input_data = processor.read_file(args.file)
            except Exception as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1
        elif args.input:
            input_data = args.input
        else:
            print("错误: 需要提供 --input 或 --file 参数", file=sys.stderr)
            parser.print_help()
            return 1

        # 处理输入
        if args.batch:
            try:
                input_list = json.loads(input_data)
                if not isinstance(input_list, list):
                    raise ValueError("批量模式需要JSON数组")
                results = processor.process(input_list, template=template, batch=True)
            except json.JSONDecodeError:
                print("错误: 批量模式下输入必须是有效的JSON数组", file=sys.stderr)
                return 1
            except Exception as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1
        else:
            try:
                results = processor.process(input_data, template=template)
            except Exception as e:
                print(f"错误: {e}", file=sys.stderr)
                return 1

        # 输出结果
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"E010: {ERROR_CODES['E010']}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
