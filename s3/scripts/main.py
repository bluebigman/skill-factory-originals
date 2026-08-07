#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
s3 - 伪 S3 协议工具（针对 Mozilla 浏览器场景）
================================================
基于功能规格独立实现的 clean-room 版本。

核心能力：
  1. 将输入数据/文件/URL 转换为结构化结果
  2. 识别并保留关键信息
  3. 按约定格式生成输出
  4. 对不确定项给出置信度提示
  5. 支持批量处理和自定义格式

边界声明：
  - 不执行超出输入范围的分析
  - 不保证绝对准确，低置信度会标注
  - 不访问网络或外部服务

用法示例：
  python main.py --input "https://example.com/file.txt" --format json
  python main.py --input "data.txt" --batch
  python main.py --selftest
"""

import argparse
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
VERSION = "1.0.0"
NAME = "未命名工具"
DESCRIPTION = "psuedo s3 protocol for mozilla browsers"

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件不存在或不可读",
    "E007": "输出格式不支持",
    "E008": "批量处理中断",
    "E009": "参数冲突",
    "E010": "内部处理异常",
}

# 错误码对应的标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{missing}",
    "E003": "输入格式不符合要求，示例：{example}",
    "E004": "这超出了本工具的能力范围，建议：{suggestion}",
    "E005": "结果无法确定，建议：{suggestion}",
    "E006": "文件不存在或不可读：{path}",
    "E007": "不支持的输出格式：{fmt}，支持：json, text",
    "E008": "批量处理中断：{reason}",
    "E009": "参数冲突：{conflict}",
    "E010": "内部处理异常：{detail}",
}


class S3Error(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, code: str, **kwargs):
        self.code = code
        self.message = ERROR_MESSAGES[code].format(**kwargs)
        super().__init__(self.message)


class S3Processor:
    """核心处理器：实现功能规格中的标准流程"""

    # 触发词表（6类场景）
    TRIGGER_WORDS = ["s3", "处理", "转换", "批量", "格式化", "结构化"]

    # 关键字段识别正则（用于从输入中提取信息）
    URL_PATTERN = re.compile(r'https?://[^\s]+')
    FILE_PATTERN = re.compile(r'[\w\-\./\\]+\.(txt|json|csv|xml|log|md|html?)', re.IGNORECASE)
    KEY_VALUE_PATTERN = re.compile(r'(\w+)\s*[:=]\s*([^,\s]+)')

    # 中文字符范围
    CHINESE_CHARS = re.compile(r'[\u4e00-\u9fff]')
    
    # 标点符号（中英文）
    PUNCTUATION = re.compile(r'[，。！？；：、,\.!?;:\(\)\[\]{}"\'<>/\\|~`@#$%^&*_\-+=]')

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        """调试日志"""
        if self.verbose:
            print(f"[DEBUG] {msg}")

    def _count_words(self, text: str) -> int:
        """
        智能词数统计：
        - 英文按空格分词
        - 中文按字符计数（每个汉字算一个词）
        - 混合文本分别统计
        """
        if not text:
            return 0
        
        # 移除标点符号（保留空格和换行）
        cleaned_text = self.PUNCTUATION.sub(' ', text)
        
        # 统计中文字符数
        chinese_chars = len(self.CHINESE_CHARS.findall(cleaned_text))
        
        # 统计英文单词数（移除中文字符后的英文部分）
        english_text = self.CHINESE_CHARS.sub(' ', cleaned_text)
        english_words = len(english_text.split())
        
        # 中文字符 + 英文单词 = 总词数
        return chinese_chars + english_words

    def process(self, input_data: str, output_format: str = "json",
                batch: bool = False, **kwargs) -> Dict[str, Any]:
        """
        标准流程入口

        Args:
            input_data: 用户输入（数据/文件路径/URL 字符串）
            output_format: 输出格式（json 或 text）
            batch: 是否批量模式
            **kwargs: 附加参数

        Returns:
            结构化结果字典

        Raises:
            S3Error: 处理过程中的错误
        """
        # Step 0: 输入校验（E001）
        if not input_data or not input_data.strip():
            raise S3Error("E001")

        # Step 1: 收集最小信息集（自动识别输入类型）
        input_type, parsed = self._parse_input(input_data)

        # Step 2: 执行核心流程
        if batch:
            # 批量模式：按行拆分处理
            return self._process_batch(input_data, output_format)
        else:
            # 单条处理
            result = self._process_single(parsed, input_type)
            return self._format_output(result, output_format)

    def _parse_input(self, raw_input: str) -> Tuple[str, Any]:
        """
        解析输入内容，识别关键信息

        Returns:
            (输入类型, 解析后的数据)
        """
        raw_input = raw_input.strip()
        self._log(f"解析输入: {raw_input[:100]}...")

        # 识别 URL
        url_match = self.URL_PATTERN.search(raw_input)
        if url_match:
            return "url", {"url": url_match.group(0), "raw": raw_input}

        # 识别文件路径
        file_match = self.FILE_PATTERN.search(raw_input)
        if file_match:
            path = file_match.group(0)
            # 检查文件是否存在（E006）
            if not os.path.isfile(path):
                raise S3Error("E006", path=path)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return "file", {"path": path, "content": content, "raw": raw_input}
            except (IOError, OSError) as e:
                raise S3Error("E006", path=f"{path} ({str(e)})")

        # 尝试解析键值对
        kv_matches = self.KEY_VALUE_PATTERN.findall(raw_input)
        if kv_matches:
            data = dict(kv_matches)
            return "data", {"fields": data, "raw": raw_input}

        # 默认按纯文本处理
        return "text", {"text": raw_input, "raw": raw_input}

    def _process_single(self, parsed: Any, input_type: str) -> Dict[str, Any]:
        """
        单条数据处理核心逻辑

        Args:
            parsed: 解析后的输入数据
            input_type: 输入类型

        Returns:
            处理结果字典
        """
        self._log(f"处理类型: {input_type}")

        # 提取关键信息
        key_info = self._extract_key_info(parsed, input_type)

        # 计算置信度
        confidence = self._calculate_confidence(parsed, input_type, key_info)

        # 生成结构化结果
        result = {
            "type": input_type,
            "key_info": key_info,
            "confidence": confidence,
            "confidence_level": self._confidence_level(confidence),
            "needs_review": confidence < 90,
        }

        # 低置信度标注
        if confidence < 85:
            result["warning"] = "[需核实] 部分信息无法确定"
            result["uncertain_points"] = self._find_uncertain_points(parsed, input_type)

        return result

    def _extract_key_info(self, parsed: Any, input_type: str) -> Dict[str, Any]:
        """提取关键信息字段"""
        info = {}

        if input_type == "url":
            url = parsed["url"]
            info["url"] = url
            info["protocol"] = url.split("://")[0] if "://" in url else "unknown"
            info["host"] = url.split("://")[1].split("/")[0] if "://" in url else "unknown"
            info["path"] = "/" + "/".join(url.split("://")[1].split("/")[1:]) if "://" in url and "/" in url.split("://")[1] else "/"

        elif input_type == "file":
            info["path"] = parsed["path"]
            info["size"] = os.path.getsize(parsed["path"]) if os.path.exists(parsed["path"]) else 0
            content = parsed["content"]
            info["line_count"] = content.count("\n") + 1 if content else 0
            info["word_count"] = self._count_words(content)
            # 提取可能的标题（第一行非空行）
            for line in content.split("\n"):
                if line.strip():
                    info["title"] = line.strip()[:50]
                    break
            else:
                info["title"] = ""

        elif input_type == "data":
            info["fields"] = parsed["fields"]
            info["field_count"] = len(parsed["fields"])

        else:  # text
            text = parsed["text"]
            info["text"] = text
            info["length"] = len(text)
            info["word_count"] = self._count_words(text)
            # 尝试提取关键词
            words = re.findall(r'\w+', text.lower())
            if words:
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'of', 'for'}
                keywords = [w for w in words if w not in common_words]
                info["keywords"] = list(dict.fromkeys(keywords))[:10]  # 去重取前10
            else:
                # 如果是纯中文，提取连续的中文字符作为关键词
                chinese_keywords = re.findall(r'[\u4e00-\u9fff]{2,}', text)
                info["keywords"] = chinese_keywords[:10] if chinese_keywords else []

        return info

    def _calculate_confidence(self, parsed: Any, input_type: str, key_info: Dict[str, Any]) -> float:
        """计算置信度（0-100）"""
        base = 90.0

        # 根据输入类型调整
        if input_type == "url":
            # URL 格式校验
            if "://" in parsed["url"] and "." in parsed["url"].split("://")[1].split("/")[0]:
                base += 5
            else:
                base -= 10

        elif input_type == "file":
            # 文件读取成功且有内容
            if parsed["content"]:
                base += 5
            else:
                base -= 15

        elif input_type == "data":
            # 字段数量越多置信度越高
            field_count = len(parsed["fields"])
            if field_count >= 3:
                base += 5
            elif field_count < 1:
                base -= 20

        else:  # text
            text_length = len(parsed["text"])
            word_count = self._count_words(parsed["text"])
            if text_length < 10:
                base -= 15  # 太短无法确认
            elif text_length > 100:
                base += 3
            
            # 根据词数调整
            if word_count < 5:
                base -= 10  # 词数过少

        # 检查关键信息完整性
        for key, value in key_info.items():
            if value in (None, "", [], {}):
                base -= 5

        # 限制在合理范围
        return max(10.0, min(100.0, base))

    def _confidence_level(self, confidence: float) -> str:
        """置信度等级"""
        if confidence >= 90:
            return "高"
        elif confidence >= 85:
            return "中高"
        else:
            return "低"

    def _find_uncertain_points(self, parsed: Any, input_type: str) -> List[str]:
        """找出不确定点"""
        points = []

        if input_type == "text":
            text = parsed["text"]
            if len(text) < 20:
                points.append("输入内容过短，可能信息不完整")
            if not re.search(r'[\w\.-]+@[\w\.-]+', text):
                points.append("未识别到邮箱地址")
            if self._count_words(text) < 10:
                points.append("词数过少，可能信息不足")

        elif input_type == "data":
            for key, value in parsed["fields"].items():
                if not value or value == "?":
                    points.append(f"字段 '{key}' 值不确定")

        return points

    def _process_batch(self, input_data: str, output_format: str) -> Dict[str, Any]:
        """批量处理：按行拆分输入"""
        lines = [line.strip() for line in input_data.split("\n") if line.strip()]

        if not lines:
            raise S3Error("E001")

        results = []
        errors = []

        for i, line in enumerate(lines, 1):
            try:
                input_type, parsed = self._parse_input(line)
                result = self._process_single(parsed, input_type)
                results.append({"index": i, "data": result})
            except S3Error as e:
                errors.append({"index": i, "error_code": e.code, "error": str(e)})

        return {
            "type": "batch",
            "total": len(lines),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
            "confidence": 85.0 if results else 0.0,  # 批量处理默认中等置信度
            "confidence_level": "中高" if results else "低",
            "needs_review": True,
        }

    def _format_output(self, result: Dict[str, Any], output_format: str) -> Dict[str, Any]:
        """格式化输出"""
        if output_format == "json":
            return result
        elif output_format == "text":
            # 文本格式：转换为可读文本
            text = self._result_to_text(result)
            return {"text": text, "original": result}
        else:
            raise S3Error("E007", fmt=output_format)

    def _result_to_text(self, result: Dict[str, Any]) -> str:
        """将结果转为文本格式"""
        lines = []
        lines.append(f"=== {NAME} 处理结果 ===")
        lines.append(f"类型: {result.get('type', 'unknown')}")
        lines.append(f"置信度: {result.get('confidence', 0):.1f}% ({result.get('confidence_level', '未知')})")

        if result.get('needs_review'):
            lines.append("⚠️ 建议复核")

        for key, value in result.get('key_info', {}).items():
            if isinstance(value, (dict, list)):
                lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                lines.append(f"  {key}: {value}")

        if result.get('warning'):
            lines.append(f"⚠️ {result['warning']}")

        if result.get('uncertain_points'):
            lines.append("不确定点:")
            for point in result['uncertain_points']:
                lines.append(f"  - {point}")

        return "\n".join(lines)


def run_selftest() -> int:
    """
    内置硬编码样例数据离线自检

    Returns:
        0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print(f"{NAME} 自检程序 v{VERSION}")
    print("=" * 60)

    processor = S3Processor(verbose=False)
    passed = 0
    failed = 0

    # 测试用例 1: URL 输入
    print("\n[测试 1] URL 输入...")
    try:
        result = processor.process("https://example.com/data/file.txt", "json")
        assert result["type"] == "url", f"类型错误: {result['type']}"
        assert "example.com" in result["key_info"]["host"], "主机提取错误"
        assert result["confidence"] >= 70, f"置信度过低: {result['confidence']}"
        assert result["confidence"] <= 100, f"置信度超范围: {result['confidence']}"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 2: 键值对输入
    print("\n[测试 2] 键值对输入...")
    try:
        result = processor.process("name=测试项目, version=2.0, status=active", "json")
        assert result["type"] == "data", f"类型错误: {result['type']}"
        assert result["key_info"]["field_count"] >= 2, "字段数过少"
        assert "测试项目" in result["key_info"]["fields"].get("name", ""), "字段值错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 3: 文本输入
    print("\n[测试 3] 文本输入...")
    try:
        result = processor.process("这是一个测试文本，用于验证处理逻辑是否正常工作。", "json")
        assert result["type"] == "text", f"类型错误: {result['type']}"
        assert result["key_info"]["word_count"] >= 5, f"词数统计错误: {result['key_info']['word_count']}"
        assert len(result["key_info"]["keywords"]) >= 1, "关键词提取失败"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 4: 空输入错误处理
    print("\n[测试 4] 空输入错误处理...")
    try:
        processor.process("", "json")
        failed += 1
        print("  ✗ 失败: 未抛出 E001")
    except S3Error as e:
        assert e.code == "E001", f"错误码错误: {e.code}"
        passed += 1
        print("  ✓ 通过 (E001)")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 5: 批量处理
    print("\n[测试 5] 批量处理...")
    try:
        batch_input = "https://example.com/a.txt\nname=test, count=3\n普通文本内容"
        result = processor.process(batch_input, "json", batch=True)
        assert result["type"] == "batch", f"类型错误: {result['type']}"
        assert result["total"] == 3, f"总数错误: {result['total']}"
        assert result["success_count"] >= 2, f"成功率过低: {result['success_count']}"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 6: 文本格式输出
    print("\n[测试 6] 文本格式输出...")
    try:
        result = processor.process("key1=value1, key2=value2", "text")
        assert "text" in result, "缺少文本输出"
        assert "处理结果" in result["text"], "输出内容缺失"
        assert len(result["text"]) > 10, "输出过短"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 7: 置信度边界检查
    print("\n[测试 7] 置信度边界检查...")
    try:
        result = processor.process("https://example.com", "json")
        conf = result["confidence"]
        assert 0 <= conf <= 100, f"置信度超出范围: {conf}"
        assert result["confidence_level"] in ("高", "中高", "低"), "置信度等级错误"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 8: 错误码完整性
    print("\n[测试 8] 错误码完整性...")
    try:
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert code in ERROR_MESSAGES, f"缺少错误码消息 {code}"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 9: 触发词识别
    print("\n[测试 9] 触发词识别...")
    try:
        assert len(processor.TRIGGER_WORDS) >= 5, "触发词数量不足"
        assert "s3" in processor.TRIGGER_WORDS, "缺少 s3 触发词"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 测试用例 10: 版本信息
    print("\n[测试 10] 版本信息...")
    try:
        assert VERSION.count(".") == 2, f"版本格式错误: {VERSION}"
        assert NAME, "名称为空"
        assert DESCRIPTION, "描述为空"
        passed += 1
        print("  ✓ 通过")
    except Exception as e:
        failed += 1
        print(f"  ✗ 失败: {e}")

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return 0 if failed == 0 else 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description=f"{NAME} - {DESCRIPTION}",
        epilog="示例: python main.py --input 'https://example.com' --format json"
    )
    parser.add_argument("--input", "-i", help="输入内容（数据/文件路径/URL）")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json",
                        help="输出格式（默认: json）")
    parser.add_argument("--batch", "-b", action="store_true", help="批量模式（按行拆分输入）")
    parser.add_argument("--verbose", "-v", action="store_true", help="调试模式")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 处理模式
    if not args.input:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        parser.print_help()
        return 1

    try:
        processor = S3Processor(verbose=args.verbose)
        result = processor.process(args.input, args.format, batch=args.batch)

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["text"])

        return 0

    except S3Error as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010'].format(detail=str(e))}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
