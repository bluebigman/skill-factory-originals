#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
net-automate 技能实现脚本（独立实现版）

功能概述：
    将用户提供的数据/文件/URL 转换为结构化结果，识别关键信息，
    按约定格式输出，并对不确定项给出置信度提示。

设计原则：
    1. 仅依据功能规格独立实现，不含任何既有代码片段。
    2. 优先使用标准库，不依赖第三方包。
    3. 提供 --selftest 离线自检，使用内置硬编码样例数据。
    4. 错误处理使用错误码 E001-E010。
"""

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码与标准化话术映射（依据规格书第四章）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议：...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请稍后重试或联系管理员。",
    "E007": "文件读取失败，请检查文件路径和权限。",
    "E008": "数据解析失败，请检查输入数据的格式。",
    "E009": "输出写入失败，请检查目标路径和权限。",
    "E010": "参数配置错误，请检查命令行参数。",
}

# 置信度阈值（依据规格书第三章）
HIGH_CONFIDENCE_THRESHOLD = 90
MEDIUM_CONFIDENCE_THRESHOLD = 85

# 默认输出字段结构
DEFAULT_FIELDS = ["text", "keywords", "confidence", "label"]


# ============================================================
# 核心功能类
# ============================================================


class NetAutomateProcessor:
    """
    核心处理器：负责输入解析、关键信息提取、结果生成与置信度评估。
    """

    def __init__(self) -> None:
        """初始化处理器，设置内部状态。"""
        self.input_data: Optional[Any] = None
        self.output_format: str = "json"
        self.detail_level: str = "standard"
        self.parsed_items: List[Dict[str, Any]] = []
        self.error_code: Optional[str] = None

    # --------------------------------------------------------
    # 输入处理
    # --------------------------------------------------------

    def process_input(self, raw_input: str) -> bool:
        """
        处理原始输入，识别输入类型并解析。

        参数:
            raw_input: 用户提供的原始输入字符串。

        返回:
            bool: 处理是否成功。
        """
        if not raw_input or not raw_input.strip():
            self.error_code = "E001"
            return False

        self.input_data = raw_input.strip()

        # 判断输入类型
        if self._looks_like_url(self.input_data):
            # 规格书明确：不访问网络，因此 URL 仅做记录，不实际请求
            self.parsed_items.append(
                {
                    "source_type": "URL",
                    "content": self.input_data,
                    "note": "URL 已记录，但不执行网络访问",
                }
            )
            return True

        if self._looks_like_file_path(self.input_data):
            return self._process_file(self.input_data)

        # 默认作为纯文本处理
        return self._process_text(self.input_data)

    def _process_text(self, text: str) -> bool:
        """
        处理纯文本输入，提取关键信息。

        参数:
            text: 文本内容。

        返回:
            bool: 处理是否成功。
        """
        if not text:
            self.error_code = "E001"
            return False

        # 提取关键词（简单实现：提取长度>1的中英文单词）
        keywords = self._extract_keywords(text)

        # 评估置信度
        confidence = self._evaluate_confidence(text, keywords)

        self.parsed_items.append(
            {
                "source_type": "text",
                "content": text,
                "keywords": keywords,
                "confidence": confidence,
                "label": self._classify_content(text),
            }
        )
        return True

    def _process_file(self, file_path: str) -> bool:
        """
        处理文件输入。

        参数:
            file_path: 文件路径。

        返回:
            bool: 处理是否成功。
        """
        if not os.path.exists(file_path):
            self.error_code = "E007"
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError) as e:
            self.error_code = "E007"
            return False

        if not content.strip():
            self.error_code = "E001"
            return False

        return self._process_text(content)

    # --------------------------------------------------------
    # 输出生成
    # --------------------------------------------------------

    def generate_output(self, output_format: str = "json") -> Tuple[bool, Optional[str]]:
        """
        生成结构化输出。

        参数:
            output_format: 输出格式（json/text）。

        返回:
            Tuple[bool, Optional[str]]: 是否成功及输出内容。
        """
        if not self.parsed_items:
            self.error_code = "E001"
            return False, None

        if output_format == "json":
            try:
                result = json.dumps(self.parsed_items, ensure_ascii=False, indent=2)
                return True, result
            except (TypeError, ValueError):
                self.error_code = "E008"
                return False, None

        elif output_format == "text":
            # 生成可读文本
            lines = []
            for i, item in enumerate(self.parsed_items, 1):
                lines.append(f"条目 {i}:")
                for key, value in item.items():
                    lines.append(f"  {key}: {value}")
                lines.append("")
            return True, "\n".join(lines)

        else:
            self.error_code = "E010"
            return False, None

    # --------------------------------------------------------
    # 内部辅助函数
    # --------------------------------------------------------

    def _looks_like_url(self, text: str) -> bool:
        """判断字符串是否为 URL。"""
        pattern = r"^(https?://|ftp://|www\.)\S+"
        return bool(re.match(pattern, text, re.IGNORECASE))

    def _looks_like_file_path(self, text: str) -> bool:
        """判断字符串是否为文件路径。"""
        # 检查是否存在该路径，且为文件
        if os.path.isfile(text):
            return True
        # 检查是否像路径（包含路径分隔符）
        if ("/" in text or "\\" in text) and len(text) > 3:
            return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词。

        实现说明：
            提取长度大于2的中英文单词，去重，最多返回10个。

        参数:
            text: 输入文本。

        返回:
            List[str]: 关键词列表。
        """
        # 提取英文单词和中文字符串
        words = re.findall(r"[a-zA-Z]{3,}|[\u4e00-\u9fff]{2,}", text)
        # 去重并限制数量
        seen = set()
        keywords = []
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen:
                seen.add(word_lower)
                keywords.append(word)
            if len(keywords) >= 10:
                break
        return keywords

    def _evaluate_confidence(self, text: str, keywords: List[str]) -> int:
        """
        评估处理结果的置信度。

        评估规则：
            - 基础置信度 80
            - 有关键词 +10
            - 文本长度>50 +5
            - 文本长度>200 +5（上限95）

        参数:
            text: 输入文本。
            keywords: 提取的关键词。

        返回:
            int: 置信度百分比（0-100）。
        """
        confidence = 80

        if keywords:
            confidence += 10

        if len(text) > 50:
            confidence += 5

        if len(text) > 200:
            confidence += 5

        # 限制范围
        return max(0, min(100, confidence))

    def _classify_content(self, text: str) -> str:
        """
        对内容进行简单分类。

        参数:
            text: 输入文本。

        返回:
            str: 内容分类标签。
        """
        text_lower = text.lower()

        if any(word in text_lower for word in ["网络", "router", "switch", "cisco"]):
            return "网络设备"
        if any(word in text_lower for word in ["配置", "config", "setup"]):
            return "配置管理"
        if any(word in text_lower for word in ["故障", "error", "fail"]):
            return "故障排查"
        if any(word in text_lower for word in ["数据", "data", "信息"]):
            return "数据处理"
        return "通用文本"

    # --------------------------------------------------------
    # 校验与检查
    # --------------------------------------------------------

    def validate_result(self, result: Dict[str, Any]) -> bool:
        """
        校验处理结果是否符合规格要求。

        检查项：
            - 必备字段是否存在
            - 置信度是否在有效范围
            - 内容是否非空

        参数:
            result: 待校验的结果字典。

        返回:
            bool: 是否通过校验。
        """
        if not result:
            return False

        # 检查必备字段
        if "content" not in result or not result["content"]:
            return False

        # 检查置信度
        if "confidence" in result:
            conf = result["confidence"]
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 100:
                return False

        return True


# ============================================================
# 自检模块（--selftest）
# ============================================================


def run_selftest() -> bool:
    """
    运行离线自检，验证核心逻辑。

    使用内置硬编码样例数据，不读取外部文件，不访问网络。

    返回:
        bool: 自检是否通过。
    """
    print("开始自检...")
    
    # 创建处理器实例
    processor = NetAutomateProcessor()

    # 测试用例1：正常文本处理
    print("测试用例1: 正常文本处理")
    test_input_1 = "请帮我处理这份网络设备配置文档，包含路由器基本配置和接口信息。"
    assert processor.process_input(test_input_1), "处理正常文本应成功"
    assert len(processor.parsed_items) == 1, "应生成一个处理结果"
    result_1 = processor.parsed_items[0]
    assert result_1["content"] == test_input_1, "内容应保持原样"
    assert len(result_1["keywords"]) > 0, "应提取到关键词"
    assert 0 <= result_1["confidence"] <= 100, "置信度应在有效范围"
    assert "label" in result_1, "应包含分类标签"
    print(f"  ✓ 通过 (置信度: {result_1['confidence']}%, 关键词: {result_1['keywords'][:3]}...)")

    # 测试用例2：空输入处理
    print("测试用例2: 空输入处理")
    processor2 = NetAutomateProcessor()
    assert not processor2.process_input(""), "空输入应失败"
    assert processor2.error_code == "E001", "应返回E001错误码"
    print(f"  ✓ 通过 (错误码: {processor2.error_code})")

    # 测试用例3：URL处理（不访问网络）
    print("测试用例3: URL处理")
    processor3 = NetAutomateProcessor()
    test_url = "https://example.com/config"
    assert processor3.process_input(test_url), "URL处理应成功"
    assert processor3.parsed_items[0]["source_type"] == "URL", "应识别为URL类型"
    assert "note" in processor3.parsed_items[0], "应包含URL处理说明"
    print(f"  ✓ 通过 (类型: {processor3.parsed_items[0]['source_type']})")

    # 测试用例4：置信度评估
    print("测试用例4: 置信度评估")
    short_text = "你好"
    long_text = "这是一段较长的中文文本，用于测试置信度评估功能。" * 10
    conf_short = processor._evaluate_confidence(short_text, [])
    conf_long = processor._evaluate_confidence(long_text, ["测试", "置信度"])
    assert conf_short >= 80, "短文本基础置信度应不低于80"
    assert conf_long >= 85, "长文本带关键词置信度应不低于85"
    assert conf_long > conf_short, "长文本置信度应高于短文本"
    print(f"  ✓ 通过 (短文本: {conf_short}%, 长文本: {conf_long}%)")

    # 测试用例5：输出生成
    print("测试用例5: 输出生成")
    processor5 = NetAutomateProcessor()
    processor5.process_input("测试批量处理功能，处理多条数据。")
    success, output = processor5.generate_output("json")
    assert success, "JSON输出应成功"
    assert output is not None and len(output) > 0, "输出不应为空"
    # 验证JSON格式
    parsed_output = json.loads(output)
    assert isinstance(parsed_output, list), "输出应为列表"
    assert len(parsed_output) > 0, "输出列表不应为空"
    print(f"  ✓ 通过 (输出长度: {len(output)}字符)")

    # 测试用例6：关键词提取
    print("测试用例6: 关键词提取")
    keywords = processor._extract_keywords("Cisco router configuration and network setup")
    assert len(keywords) > 0, "应提取到关键词"
    assert any("cisco" in k.lower() for k in keywords), "应包含cisco关键词"
    print(f"  ✓ 通过 (关键词: {keywords[:3]}...)")

    # 测试用例7：结果校验
    print("测试用例7: 结果校验")
    valid_result = {"content": "测试内容", "confidence": 90, "keywords": ["测试"]}
    invalid_result = {"content": "", "confidence": 99}
    assert processor.validate_result(valid_result), "有效结果应通过校验"
    assert not processor.validate_result(invalid_result), "无效结果应不通过校验"
    assert not processor.validate_result(None), "空结果应不通过校验"
    print("  ✓ 通过")

    # 测试用例8：错误消息映射
    print("测试用例8: 错误消息映射")
    for code in ["E001", "E002", "E003", "E004", "E005"]:
        assert code in ERROR_MESSAGES, f"错误码 {code} 应存在"
        assert len(ERROR_MESSAGES[code]) > 0, f"错误码 {code} 的消息不应为空"
    print(f"  ✓ 通过 (共 {len(ERROR_MESSAGES)} 个错误码)")

    print("\n所有自检用例通过 ✔")
    return True


# ============================================================
# 主程序入口
# ============================================================


def main() -> int:
    """
    主程序入口。

    返回:
        int: 退出码（0成功，非0失败）。
    """
    parser = argparse.ArgumentParser(
        description="net-automate: 将数据/文件/URL转换为结构化结果"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（文本、文件路径或URL）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    parser.add_argument(
        "--detail",
        type=str,
        choices=["quick", "standard", "detailed"],
        default="standard",
        help="期望的完整度 (默认: standard)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            return 0
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常处理模式
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}")
        return 1

    # 创建处理器并处理输入
    processor = NetAutomateProcessor()
    processor.detail_level = args.detail

    if not processor.process_input(args.input):
        error_code = processor.error_code or "E006"
        print(f"错误 {error_code}: {ERROR_MESSAGES.get(error_code, '未知错误')}")
        return 1

    # 生成输出
    success, output = processor.generate_output(args.format)
    if not success:
        error_code = processor.error_code or "E006"
        print(f"错误 {error_code}: {ERROR_MESSAGES.get(error_code, '未知错误')}")
        return 1

    # 输出结果
    print(output)

    # 置信度提示（依据规格书第三章）
    for item in processor.parsed_items:
        if "confidence" in item:
            conf = item["confidence"]
            if conf >= HIGH_CONFIDENCE_THRESHOLD:
                pass  # 高置信度，直接输出
            elif conf >= MEDIUM_CONFIDENCE_THRESHOLD:
                print("\n[提示] 部分内容置信度中等，建议复核。")
            else:
                print("\n[提示] 部分内容置信度较低，标注 [需核实]，请人工确认。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
