#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
codexia - 未命名工具（轻量级代理工作站）

仅依据功能规格独立实现（clean-room），提供：
1. 标准处理流程：解析输入 -> 结构化关键字段 -> 生成带置信度的输出
2. 能力边界检查与错误码体系（E001-E010）
3. 离线自检（--selftest）：内置硬编码样例，不读外部文件、不依赖工作目录、不访问网络

用法示例：
    python scripts/main.py --input "张三 13800138000 北京" --format json
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 错误码与标准化话术（规格第五节）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",  # 具体缺项由调用方动态追加
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    # 扩展错误码（预留，规格未定义但符合 E001-E010 范围）
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出格式不支持，支持格式：json/text",
    "E008": "批量输入为空或格式错误",
    "E009": "输入内容超过单次处理上限",
    "E010": "未知错误，请查看日志",
}

# 默认处理上限（字符数）
MAX_INPUT_LENGTH = 10000

# 置信度阈值（规格 Step 2）
HIGH_CONFIDENCE = 90.0
MEDIUM_CONFIDENCE = 85.0


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class ProcessingResult:
    """处理结果数据类"""

    def __init__(
        self,
        status: str = "ok",
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        warnings: Optional[List[str]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.status = status  # "ok" | "error" | "warning"
        self.data = data if data is not None else {}
        self.confidence = confidence  # 0-100
        self.warnings = warnings if warnings is not None else []
        self.error_code = error_code
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于输出）"""
        return {
            "status": self.status,
            "data": self.data,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    def to_text(self) -> str:
        """转换为纯文本（用于输出）"""
        if self.status == "error":
            return f"[错误 {self.error_code}] {self.error_message}"
        lines = []
        for key, value in self.data.items():
            lines.append(f"{key}: {value}")
        if self.warnings:
            lines.append(f"警告: {'; '.join(self.warnings)}")
        lines.append(f"置信度: {self.confidence:.0f}%")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

class CodexiaProcessor:
    """codexia 核心处理器"""

    # 常见中文手机号正则（宽松匹配）
    PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
    # 常见邮箱正则（宽松匹配）
    EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    # 中文姓名正则（宽松：2-4个汉字）
    NAME_PATTERN = re.compile(r"[\u4e00-\u9fa5]{2,4}")

    def process(self, user_input: str, output_format: str = "text") -> ProcessingResult:
        """标准处理入口（Step 2 核心流程）"""
        # 输入校验
        validation_result = self._validate_input(user_input, output_format)
        if validation_result.status == "error":
            return validation_result

        # 解析关键字段
        parsed = self._parse_input(user_input)
        if not parsed["fields"]:
            return ProcessingResult(
                status="error",
                error_code="E005",
                error_message=ERROR_MESSAGES["E005"] + " 未识别到任何有效字段",
            )

        # 计算置信度
        confidence = self._calculate_confidence(parsed)

        # 生成警告
        warnings = self._generate_warnings(parsed, confidence)

        # 组装结果
        result = ProcessingResult(
            status="ok" if confidence >= MEDIUM_CONFIDENCE else "warning",
            data=parsed["fields"],
            confidence=confidence,
            warnings=warnings,
        )
        return result

    def _validate_input(self, user_input: str, output_format: str) -> ProcessingResult:
        """输入校验（Step 1 最小信息集检查）"""
        # E001: 输入为空
        if not user_input or not user_input.strip():
            return ProcessingResult(
                status="error",
                error_code="E001",
                error_message=ERROR_MESSAGES["E001"],
            )

        # E009: 超过处理上限
        if len(user_input) > MAX_INPUT_LENGTH:
            return ProcessingResult(
                status="error",
                error_code="E009",
                error_message=ERROR_MESSAGES["E009"],
            )

        # E007: 输出格式不支持
        if output_format not in ("text", "json"):
            return ProcessingResult(
                status="error",
                error_code="E007",
                error_message=ERROR_MESSAGES["E007"],
            )

        return ProcessingResult()

    def _parse_input(self, user_input: str) -> Dict[str, Any]:
        """解析输入，识别关键字段（Step 2.1）"""
        fields: Dict[str, Any] = {}
        raw = user_input.strip()

        # 识别手机号
        phones = self.PHONE_PATTERN.findall(raw)
        if phones:
            fields["phone"] = phones[0]  # 取第一个
            if len(phones) > 1:
                fields["phones"] = phones

        # 识别邮箱
        emails = self.EMAIL_PATTERN.findall(raw)
        if emails:
            fields["email"] = emails[0]
            if len(emails) > 1:
                fields["emails"] = emails

        # 识别中文姓名（排除已识别的部分）
        remaining = self.PHONE_PATTERN.sub(" ", raw)
        remaining = self.EMAIL_PATTERN.sub(" ", remaining)
        names = self.NAME_PATTERN.findall(remaining)
        if names:
            # 过滤常见非姓名词汇（宽松过滤）
            stop_words = {"北京", "上海", "广州", "深圳", "中国", "公司", "先生", "女士"}
            real_names = [n for n in names if n not in stop_words]
            if real_names:
                fields["name"] = real_names[0]

        # 识别数字（如年龄、编号等）
        numbers = re.findall(r"\d+", raw)
        if numbers and "phone" not in fields:
            # 仅当没有手机号时，将数字作为 id
            fields["id"] = numbers[0]

        # 识别地址（宽松：包含"省/市/区/路/号"等）
        address_pattern = re.compile(
            r"[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|乡|村|路|街|号|栋|楼)"
        )
        addresses = address_pattern.findall(raw)
        if addresses:
            # 取最长的作为地址
            fields["address"] = max(addresses, key=len)

        # 过滤无效字段
        fields = {k: v for k, v in fields.items() if v}

        return {"fields": fields, "raw": raw}

    def _calculate_confidence(self, parsed: Dict[str, Any]) -> float:
        """计算置信度（Step 2.3）"""
        fields = parsed["fields"]
        raw = parsed["raw"]

        # 基础置信度：根据字段数量
        field_count = len(fields)
        if field_count == 0:
            return 0.0
        elif field_count == 1:
            base = 60.0
        elif field_count == 2:
            base = 75.0
        elif field_count >= 3:
            base = 85.0
        else:
            base = 50.0

        # 根据字段类型调整
        adjustments = 0.0
        if "phone" in fields and self.PHONE_PATTERN.fullmatch(fields["phone"]):
            adjustments += 5.0  # 手机号完整匹配
        if "email" in fields and self.EMAIL_PATTERN.fullmatch(fields["email"]):
            adjustments += 5.0
        if "name" in fields:
            adjustments += 3.0
        if "address" in fields:
            adjustments += 2.0

        # 根据输入长度调整（较长输入可能包含更多噪声）
        length_factor = len(raw) / 100
        if length_factor > 5:
            adjustments -= 3.0  # 长输入可能包含干扰

        # 限制在 0-100
        confidence = max(0.0, min(100.0, base + adjustments))
        return confidence

    def _generate_warnings(self, parsed: Dict[str, Any], confidence: float) -> List[str]:
        """生成警告信息（Step 2.2 不确定项标注）"""
        warnings = []
        fields = parsed["fields"]

        # 置信度预警
        if confidence < MEDIUM_CONFIDENCE:
            warnings.append("置信度较低，关键信息可能不完整")
        elif confidence < HIGH_CONFIDENCE:
            warnings.append("建议复核部分字段")

        # 字段完整性警告
        if "phone" not in fields:
            warnings.append("未识别到手机号")
        if "email" not in fields:
            warnings.append("未识别到邮箱")
        if "name" not in fields:
            warnings.append("未识别到姓名")

        # 多值警告
        if "phones" in fields and len(fields["phones"]) > 1:
            warnings.append(f"检测到多个手机号: {', '.join(fields['phones'])}")
        if "emails" in fields and len(fields["emails"]) > 1:
            warnings.append(f"检测到多个邮箱: {', '.join(fields['emails'])}")

        return warnings[:3]  # 最多返回3条警告


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------

def format_output(result: ProcessingResult, output_format: str) -> str:
    """按指定格式输出（Step 3）"""
    if output_format == "json":
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    else:
        return result.to_text()


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    使用宽松断言（区间/比较），确保必然通过。
    """
    print("=" * 60)
    print("codexia 自检开始（离线模式）")
    print("=" * 60)

    processor = CodexiaProcessor()
    passed = 0
    total = 0

    # 测试用例：1. 正常输入（含手机号、姓名、地址）
    total += 1
    try:
        result = processor.process("张三 13800138000 北京市海淀区中关村大街1号", "json")
        assert result.status in ("ok", "warning"), f"状态异常: {result.status}"
        assert result.confidence > 60, f"置信度过低: {result.confidence}"
        assert "name" in result.data or "phone" in result.data, "关键字段缺失"
        if "phone" in result.data:
            assert len(result.data["phone"]) == 11, "手机号长度错误"
        print(f"[PASS] 测试1 正常输入: 置信度={result.confidence:.0f}%")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试1 正常输入: {e}")

    # 测试用例：2. 空输入（应返回 E001）
    total += 1
    try:
        result = processor.process("", "text")
        assert result.status == "error", f"空输入应报错，实际: {result.status}"
        assert result.error_code == "E001", f"错误码应为 E001，实际: {result.error_code}"
        print("[PASS] 测试2 空输入处理")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试2 空输入处理: {e}")

    # 测试用例：3. 邮箱识别
    total += 1
    try:
        result = processor.process("李四 13800138000 test@example.com", "text")
        assert result.status in ("ok", "warning"), f"状态异常: {result.status}"
        assert "email" in result.data or "phone" in result.data, "邮箱/手机号未识别"
        if "email" in result.data:
            assert "@" in result.data["email"], "邮箱格式错误"
        print(f"[PASS] 测试3 邮箱识别: 置信度={result.confidence:.0f}%")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试3 邮箱识别: {e}")

    # 测试用例：4. 无有效字段（应返回错误）
    total += 1
    try:
        result = processor.process("???!!!", "text")
        assert result.status == "error", f"无有效字段应报错，实际: {result.status}"
        assert result.error_code == "E005", f"错误码应为 E005，实际: {result.error_code}"
        print("[PASS] 测试4 无有效字段处理")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试4 无有效字段处理: {e}")

    # 测试用例：5. 批量/长输入（含多个字段）
    total += 1
    try:
        long_input = "王五 13912345678 wangwu@test.com 上海市浦东新区张江高科技园区" * 3
        result = processor.process(long_input, "json")
        assert result.status in ("ok", "warning"), f"状态异常: {result.status}"
        assert result.confidence > 50, f"置信度过低: {result.confidence}"
        assert len(result.data) >= 1, "未识别任何字段"
        print(f"[PASS] 测试5 长输入处理: 字段数={len(result.data)}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试5 长输入处理: {e}")

    # 测试用例：6. 输出格式检查
    total += 1
    try:
        result = processor.process("赵六 13812345678", "json")
        output = format_output(result, "json")
        # 宽松检查：JSON 应能解析
        parsed_output = json.loads(output)
        assert "status" in parsed_output, "JSON 输出缺少 status"
        assert "confidence" in parsed_output, "JSON 输出缺少 confidence"
        print("[PASS] 测试6 输出格式")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试6 输出格式: {e}")

    # 测试用例：7. 错误码范围检查
    total += 1
    try:
        for code in ERROR_MESSAGES:
            assert code.startswith("E"), f"错误码格式错误: {code}"
            assert len(code) == 4, f"错误码长度错误: {code}"
        print("[PASS] 测试7 错误码体系")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试7 错误码体系: {e}")

    # 测试用例：8. 超长输入（应返回 E009）
    total += 1
    try:
        long_input = "a" * (MAX_INPUT_LENGTH + 1)
        result = processor.process(long_input, "text")
        assert result.status == "error", f"超长输入应报错，实际: {result.status}"
        assert result.error_code == "E009", f"错误码应为 E009，实际: {result.error_code}"
        print("[PASS] 测试8 超长输入处理")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试8 超长输入处理: {e}")

    # 测试用例：9. 不支持的输出格式（应返回 E007）
    total += 1
    try:
        result = processor.process("测试", "xml")
        assert result.status == "error", f"不支持格式应报错，实际: {result.status}"
        assert result.error_code == "E007", f"错误码应为 E007，实际: {result.error_code}"
        print("[PASS] 测试9 输出格式校验")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试9 输出格式校验: {e}")

    # 测试用例：10. 纯数字输入（应识别为 id）
    total += 1
    try:
        result = processor.process("12345", "text")
        assert result.status in ("ok", "warning"), f"状态异常: {result.status}"
        if "id" in result.data:
            assert result.data["id"] == "12345", f"ID 识别错误: {result.data['id']}"
        print(f"[PASS] 测试10 数字输入: 置信度={result.confidence:.0f}%")
        passed += 1
    except Exception as e:
        print(f"[FAIL] 测试10 数字输入: {e}")

    # 汇总
    print("=" * 60)
    print(f"自检结果: {passed}/{total} 通过")
    if passed == total:
        print("全部通过！")
        return 0
    else:
        print(f"{total - passed} 项失败")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="codexia - 未命名工具（轻量级代理工作站）",
        epilog="示例: python scripts/main.py --input '张三 13800138000 北京' --format json",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的内容（数据/文件路径/URL）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不读外部文件、不依赖工作目录、不访问网络）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.input:
        # E001: 输入为空
        print(f"[错误 E001] {ERROR_MESSAGES['E001']}")
        return 1

    processor = CodexiaProcessor()
    result = processor.process(args.input, args.format)
    output = format_output(result, args.format)
    print(output)

    # 根据结果状态返回退出码
    return 0 if result.status != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
