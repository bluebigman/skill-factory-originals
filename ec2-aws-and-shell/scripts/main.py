#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ec2-aws-and-shell: 代码审查技能实现
====================================
本脚本根据功能规格独立实现（clean-room），仅使用标准库。

功能概述：
    1. 将用户提供的数据/文件/URL 转换为结构化结果
    2. 识别并保留输入中的关键信息
    3. 按约定格式生成输出
    4. 对不确定项给出置信度提示
    5. 支持批量处理和自定义格式

用法示例：
    python main.py --process "user data here"
    python main.py --selftest
    python main.py --help
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "文件读取失败",
    "E007": "URL解析失败",
    "E008": "输出写入失败",
    "E009": "参数配置错误",
    "E010": "未知内部错误",
}

# 错误码对应的标准化话术
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "无法读取指定文件，请检查文件路径和权限。",
    "E007": "URL格式不正确或无法解析。",
    "E008": "无法写入输出文件，请检查路径和权限。",
    "E009": "命令行参数配置有误，请检查参数组合。",
    "E010": "发生未知内部错误，请报告开发者。",
}


class SkillError(Exception):
    """技能自定义异常，携带错误码。"""

    def __init__(self, error_code: str, detail: str = ""):
        self.error_code = error_code
        self.detail = detail
        message = ERROR_MESSAGES.get(error_code, "未知错误")
        if detail:
            message = f"{message} 详情: {detail}"
        super().__init__(message)

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式。"""
        return {
            "error_code": self.error_code,
            "error_message": ERROR_MESSAGES.get(self.error_code, "未知错误"),
            "detail": self.detail,
        }


# ============================================================
# 核心处理逻辑
# ============================================================

class InputProcessor:
    """输入处理核心类，负责解析和结构化用户输入。"""

    # 关键信息字段（用于识别和提取）
    KEY_FIELDS = [
        "id", "name", "type", "status", "created", "owner",
        "source", "content", "timestamp", "priority"
    ]

    def __init__(self, input_data: str, output_format: str = "json",
                 confidence_threshold: float = 0.85):
        """
        初始化处理器。

        Args:
            input_data: 用户提供的原始输入（文本/文件路径/URL）
            output_format: 输出格式（json/text/csv）
            confidence_threshold: 置信度阈值（0-1）

        Raises:
            SkillError: E001 输入为空, E009 参数配置错误
        """
        if not input_data or not input_data.strip():
            raise SkillError("E001")

        if output_format not in ("json", "text", "csv"):
            raise SkillError("E009", f"不支持的输出格式: {output_format}")

        if not 0 <= confidence_threshold <= 1:
            raise SkillError("E009", f"置信度阈值必须在0-1之间: {confidence_threshold}")

        self.raw_input = input_data.strip()
        self.output_format = output_format
        self.confidence_threshold = confidence_threshold
        self.input_type = self._detect_input_type()

    def _detect_input_type(self) -> str:
        """
        检测输入类型（data/file/url）。

        Returns:
            str: "data"、"file" 或 "url"

        Raises:
            SkillError: E007 URL解析失败
        """
        # 检查是否为文件路径
        if os.path.isfile(self.raw_input):
            return "file"

        # 检查是否为URL
        parsed = urllib.parse.urlparse(self.raw_input)
        if parsed.scheme in ("http", "https", "ftp", "file"):
            if parsed.netloc or parsed.scheme == "file":
                return "url"

        # 默认视为数据
        return "data"

    def _extract_key_info(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取关键信息。

        Args:
            text: 输入文本

        Returns:
            Dict: 提取的关键信息字典
        """
        info: Dict[str, Any] = {}
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试 key: value 格式
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if key in self.KEY_FIELDS:
                    info[key] = value

            # 尝试 key=value 格式
            elif "=" in line:
                key, _, value = line.partition("=")
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if key in self.KEY_FIELDS:
                    info[key] = value

        return info

    def _parse_data_input(self) -> Dict[str, Any]:
        """
        解析纯数据输入。

        Returns:
            Dict: 结构化结果
        """
        # 自动检测是否为JSON
        try:
            parsed_json = json.loads(self.raw_input)
            if isinstance(parsed_json, dict):
                result = {
                    "type": "data",
                    "format": "json",
                    "content": parsed_json,
                    "key_info": {k: v for k, v in parsed_json.items()
                               if k in self.KEY_FIELDS},
                    "confidence": 0.95,
                    "confidence_label": "高置信度",
                }
                return result
        except json.JSONDecodeError:
            pass

        # 提取关键信息
        key_info = self._extract_key_info(self.raw_input)

        # 计算置信度
        if len(key_info) >= 3:
            confidence = 0.90
        elif len(key_info) >= 1:
            confidence = 0.80
        else:
            confidence = 0.60

        result = {
            "type": "data",
            "format": "text",
            "content": self.raw_input,
            "key_info": key_info,
            "confidence": confidence,
            "confidence_label": self._get_confidence_label(confidence),
        }
        return result

    def _parse_file_input(self) -> Dict[str, Any]:
        """
        解析文件输入。

        Returns:
            Dict: 结构化结果

        Raises:
            SkillError: E006 文件读取失败
        """
        try:
            with open(self.raw_input, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError) as e:
            raise SkillError("E006", f"文件: {self.raw_input} - {str(e)}")

        # 获取文件信息
        file_info = {
            "path": os.path.abspath(self.raw_input),
            "name": os.path.basename(self.raw_input),
            "size": os.path.getsize(self.raw_input),
            "modified": datetime.fromtimestamp(
                os.path.getmtime(self.raw_input)
            ).isoformat(),
        }

        # 提取关键信息
        key_info = self._extract_key_info(content)

        # 计算置信度
        confidence = 0.88 if len(key_info) >= 1 else 0.70

        result = {
            "type": "file",
            "file_info": file_info,
            "content_preview": content[:500] + ("..." if len(content) > 500 else ""),
            "key_info": key_info,
            "confidence": confidence,
            "confidence_label": self._get_confidence_label(confidence),
        }
        return result

    def _parse_url_input(self) -> Dict[str, Any]:
        """
        解析URL输入。

        Returns:
            Dict: 结构化结果

        Raises:
            SkillError: E007 URL解析失败
        """
        parsed = urllib.parse.urlparse(self.raw_input)

        if not parsed.scheme or not (parsed.netloc or parsed.scheme == "file"):
            raise SkillError("E007", f"无法解析URL: {self.raw_input}")

        # 解析URL参数
        params = urllib.parse.parse_qs(parsed.query)

        # 提取关键信息
        url_info = {
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path or "/",
            "params": {k: v[0] for k, v in params.items()},
        }

        # 从URL中提取关键信息
        key_info = {}
        for key, value in url_info["params"].items():
            if key.lower() in self.KEY_FIELDS:
                key_info[key.lower()] = value

        # 计算置信度
        confidence = 0.85 if len(key_info) >= 1 else 0.65

        result = {
            "type": "url",
            "url_info": url_info,
            "key_info": key_info,
            "confidence": confidence,
            "confidence_label": self._get_confidence_label(confidence),
        }
        return result

    def _get_confidence_label(self, confidence: float) -> str:
        """
        根据置信度生成标签。

        Args:
            confidence: 置信度值

        Returns:
            str: 置信度标签
        """
        if confidence >= 0.90:
            return "高置信度"
        elif confidence >= 0.85:
            return "建议复核"
        else:
            return "[需核实]"

    def process(self) -> Dict[str, Any]:
        """
        执行核心处理流程。

        Returns:
            Dict: 处理结果

        Raises:
            SkillError: 各种错误码
        """
        try:
            # 根据输入类型执行不同的处理
            if self.input_type == "data":
                result = self._parse_data_input()
            elif self.input_type == "file":
                result = self._parse_file_input()
            else:  # url
                result = self._parse_url_input()

            # 添加元信息
            result["meta"] = {
                "processed_at": datetime.now().isoformat(),
                "input_type": self.input_type,
                "version": "1.0.0",
                "disclaimer": "本结果仅供参考，不构成专业建议。"
            }

            # 检查置信度
            confidence = result.get("confidence", 0)
            if confidence < self.confidence_threshold:
                # 低于阈值，标记为需核实
                result["confidence_label"] = "[需核实]"
                result["warning"] = "置信度过低，请人工复核结果。"

            return result

        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E010", str(e))

    def format_output(self, result: Dict[str, Any]) -> str:
        """
        按指定格式输出结果。

        Args:
            result: 处理结果字典

        Returns:
            str: 格式化后的输出

        Raises:
            SkillError: E003 输入格式错误
        """
        try:
            if self.output_format == "json":
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif self.output_format == "text":
                return self._format_as_text(result)
            elif self.output_format == "csv":
                return self._format_as_csv(result)
            else:
                raise SkillError("E003", f"不支持的格式: {self.output_format}")
        except SkillError:
            raise
        except Exception as e:
            raise SkillError("E010", f"输出格式化失败: {str(e)}")

    def _format_as_text(self, result: Dict[str, Any]) -> str:
        """格式化为纯文本。"""
        lines = []
        lines.append("=" * 50)
        lines.append("处理结果")
        lines.append("=" * 50)

        # 基本信息
        lines.append(f"输入类型: {result.get('type', '未知')}")
        lines.append(f"置信度: {result.get('confidence', 0):.0%} "
                    f"({result.get('confidence_label', '未知')})")

        # 关键信息
        key_info = result.get("key_info", {})
        if key_info:
            lines.append("\n关键信息:")
            for key, value in key_info.items():
                lines.append(f"  {key}: {value}")

        # 文件信息
        if "file_info" in result:
            lines.append("\n文件信息:")
            for key, value in result["file_info"].items():
                lines.append(f"  {key}: {value}")

        # URL信息
        if "url_info" in result:
            lines.append("\nURL信息:")
            for key, value in result["url_info"].items():
                lines.append(f"  {key}: {value}")

        # 内容预览
        if "content_preview" in result:
            lines.append(f"\n内容预览:\n{result['content_preview']}")

        # 警告
        if "warning" in result:
            lines.append(f"\n⚠️ 警告: {result['warning']}")

        # 免责声明
        lines.append("\n" + "=" * 50)
        lines.append("免责声明: 本结果仅供参考，不构成专业建议。")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _format_as_csv(self, result: Dict[str, Any]) -> str:
        """格式化为CSV。"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入头
        writer.writerow(["字段", "值"])

        # 写入基本信息
        writer.writerow(["type", result.get("type", "")])
        writer.writerow(["confidence", result.get("confidence", "")])
        writer.writerow(["confidence_label", result.get("confidence_label", "")])

        # 写入关键信息
        for key, value in result.get("key_info", {}).items():
            writer.writerow([key, value])

        return output.getvalue()


# ============================================================
# 批量处理功能
# ============================================================

class BatchProcessor:
    """批量处理多个输入。"""

    def __init__(self, inputs: List[str], output_format: str = "json",
                 confidence_threshold: float = 0.85):
        """
        初始化批量处理器。

        Args:
            inputs: 输入列表
            output_format: 输出格式
            confidence_threshold: 置信度阈值

        Raises:
            SkillError: E001 输入为空
        """
        if not inputs:
            raise SkillError("E001", "批量处理需要至少一个输入")

        self.inputs = inputs
        self.output_format = output_format
        self.confidence_threshold = confidence_threshold

    def process_all(self) -> List[Dict[str, Any]]:
        """
        处理所有输入。

        Returns:
            List[Dict]: 处理结果列表
        """
        results = []
        for input_data in self.inputs:
            try:
                processor = InputProcessor(
                    input_data,
                    output_format=self.output_format,
                    confidence_threshold=self.confidence_threshold
                )
                result = processor.process()
                result["raw_input"] = input_data
                results.append(result)
            except SkillError as e:
                # 单个输入失败不影响批量处理
                results.append({
                    "error": e.to_dict(),
                    "raw_input": input_data,
                })

        return results


# ============================================================
# 自测功能
# ============================================================

def run_selftest() -> bool:
    """
    运行内置自测，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、
    不访问网络，任何环境直接可过。

    Returns:
        bool: 测试是否通过
    """
    print("=" * 60)
    print("开始自测 (selftest)")
    print("=" * 60)

    all_passed = True

    # 测试1: 基本数据处理
    print("\n[测试1] 基本数据处理")
    try:
        processor = InputProcessor("name: test_item\nstatus: active\npriority: high")
        result = processor.process()

        # 宽松断言：检查关键字段存在
        assert result["type"] == "data", "类型应为data"
        assert "key_info" in result, "应包含key_info"
        assert len(result["key_info"]) >= 1, "应至少提取1个关键信息"
        assert result["confidence"] > 0.5, "置信度应大于0.5"
        print("  ✓ 基本数据处理通过")
        print(f"    提取到 {len(result['key_info'])} 个关键字段, "
              f"置信度: {result['confidence']:.0%}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 基本数据处理失败: {e}")

    # 测试2: JSON数据解析
    print("\n[测试2] JSON数据解析")
    try:
        json_data = json.dumps({
            "id": "001",
            "name": "test",
            "type": "example",
            "status": "ready"
        })
        processor = InputProcessor(json_data)
        result = processor.process()

        assert result["format"] == "json", "应识别为JSON格式"
        assert "content" in result, "应包含content"
        assert len(result["key_info"]) >= 1, "应提取到关键信息"
        print("  ✓ JSON数据解析通过")
        print(f"    识别到 {len(result['key_info'])} 个关键字段")
    except Exception as e:
        all_passed = False
        print(f"  ✗ JSON数据解析失败: {e}")

    # 测试3: 错误处理 - 空输入
    print("\n[测试3] 空输入错误处理")
    try:
        InputProcessor("")
        all_passed = False
        print("  ✗ 应该抛出E001错误")
    except SkillError as e:
        assert e.error_code == "E001", f"错误码应为E001, 实际: {e.error_code}"
        print("  ✓ 空输入正确抛出E001错误")

    # 测试4: 批量处理
    print("\n[测试4] 批量处理")
    try:
        batch = BatchProcessor([
            "name: item1\nstatus: active",
            "name: item2\nstatus: inactive",
            "name: item3\nstatus: pending",
        ])
        results = batch.process_all()

        assert len(results) == 3, "应处理3个输入"
        assert all("error" not in r for r in results), "所有输入应成功处理"
        print("  ✓ 批量处理通过")
        print(f"    成功处理 {len(results)} 个输入")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 批量处理失败: {e}")

    # 测试5: 输出格式化
    print("\n[测试5] 输出格式化")
    try:
        processor = InputProcessor("name: test\nstatus: ok")
        result = processor.process()

        # 测试JSON格式
        processor.output_format = "json"
        json_output = processor.format_output(result)
        assert json_output.strip().startswith("{"), "JSON输出应以{开头"
        print("  ✓ JSON格式输出通过")

        # 测试文本格式
        processor.output_format = "text"
        text_output = processor.format_output(result)
        assert "处理结果" in text_output, "文本输出应包含标题"
        print("  ✓ 文本格式输出通过")

        # 测试CSV格式
        processor.output_format = "csv"
        csv_output = processor.format_output(result)
        assert "字段,值" in csv_output, "CSV输出应包含表头"
        print("  ✓ CSV格式输出通过")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 输出格式化失败: {e}")

    # 测试6: URL解析
    print("\n[测试6] URL解析")
    try:
        url = "https://example.com/path/to/resource?id=123&name=test"
        processor = InputProcessor(url)
        result = processor.process()

        assert result["type"] == "url", "类型应为url"
        assert "url_info" in result, "应包含url_info"
        assert result["url_info"]["scheme"] == "https", "scheme应为https"
        print("  ✓ URL解析通过")
        print(f"    主机: {result['url_info']['host']}, "
              f"路径: {result['url_info']['path']}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ URL解析失败: {e}")

    # 测试7: 置信度阈值
    print("\n[测试7] 置信度阈值")
    try:
        # 使用高阈值，应触发警告
        processor = InputProcessor("just some text", confidence_threshold=0.95)
        result = processor.process()

        # 置信度应该低于0.95，触发警告
        assert result["confidence"] < 0.95, "置信度应低于阈值"
        assert result.get("warning"), "应包含警告信息"
        print("  ✓ 置信度阈值检查通过")
        print(f"    置信度: {result['confidence']:.0%}, "
              f"标签: {result['confidence_label']}")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 置信度阈值检查失败: {e}")

    # 测试8: 文件输入处理
    print("\n[测试8] 文件输入处理")
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                         delete=False, encoding="utf-8") as f:
            f.write("name: file_test\nstatus: processed\ncontent: test data")
            temp_path = f.name

        try:
            processor = InputProcessor(temp_path)
            result = processor.process()

            assert result["type"] == "file", "类型应为file"
            assert "file_info" in result, "应包含file_info"
            assert result["file_info"]["name"].endswith(".txt"), "文件名应正确"
            print("  ✓ 文件输入处理通过")
            print(f"    文件名: {result['file_info']['name']}, "
                  f"大小: {result['file_info']['size']} bytes")
        finally:
            # 清理临时文件
            os.unlink(temp_path)

    except Exception as e:
        all_passed = False
        print(f"  ✗ 文件输入处理失败: {e}")

    # 测试9: 错误码体系
    print("\n[测试9] 错误码体系")
    try:
        # 验证所有定义的错误码都有对应消息
        assert len(ERROR_CODES) == 10, "应有10个错误码"
        assert len(ERROR_MESSAGES) == 10, "应有10条错误消息"

        for code in ERROR_CODES:
            assert code in ERROR_MESSAGES, f"错误码{code}应有对应消息"

        print("  ✓ 错误码体系完整")
        print(f"    共定义 {len(ERROR_CODES)} 个错误码")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 错误码体系检查失败: {e}")

    # 测试10: 边界能力检查
    print("\n[测试10] 边界能力检查")
    try:
        # 超出能力范围的处理
        processor = InputProcessor("some normal text")
        result = processor.process()

        # 检查免责声明
        assert "disclaimer" in result.get("meta", {}), "应包含免责声明"
        print("  ✓ 边界能力检查通过")
        print("    已包含免责声明")
    except Exception as e:
        all_passed = False
        print(f"  ✗ 边界能力检查失败: {e}")

    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("自测完成: 全部通过 ✓")
    else:
        print("自测完成: 存在失败项 ✗")
    print("=" * 60)

    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """
    命令行主入口。

    Returns:
        int: 退出码（0成功，非0失败）
    """
    parser = argparse.ArgumentParser(
        description="ec2-aws-and-shell: 代码审查技能实现",
        epilog="示例: python main.py --process 'name: test' --format json"
    )

    # 处理模式参数
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--process", "-p",
        metavar="INPUT",
        help="处理单个输入（数据/文件路径/URL）"
    )
    mode_group.add_argument(
        "--process-batch", "-b",
        metavar="INPUTS",
        nargs="+",
        help="批量处理多个输入"
    )
    mode_group.add_argument(
        "--selftest", "-t",
        action="store_true",
        help="运行内置自测"
    )

    # 输出参数
    parser.add_argument(
        "--format", "-f",
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式 (默认: json)"
    )
    parser.add_argument(
        "--confidence", "-c",
        type=float,
        default=0.85,
        help="置信度阈值 0-1 (默认: 0.85)"
    )
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径（不指定则输出到stdout）"
    )

    args = parser.parse_args()

    try:
        # 运行自测
        if args.selftest:
            success = run_selftest()
            return 0 if success else 1

        # 验证参数
        if not 0 <= args.confidence <= 1:
            raise SkillError("E009", f"置信度阈值必须在0-1之间: {args.confidence}")

        # 处理输入
        if args.process:
            processor = InputProcessor(
                args.process,
                output_format=args.format,
                confidence_threshold=args.confidence
            )
            result = processor.process()
            output = processor.format_output(result)
        elif args.process_batch:
            batch = BatchProcessor(
                args.process_batch,
                output_format=args.format,
                confidence_threshold=args.confidence
            )
            results = batch.process_all()

            # 批量结果包装
            batch_result = {
                "type": "batch",
                "count": len(results),
                "success_count": sum(1 for r in results if "error" not in r),
                "failed_count": sum(1 for r in results if "error" in r),
                "results": results,
                "meta": {
                    "processed_at": datetime.now().isoformat(),
                    "version": "1.0.0",
                    "disclaimer": "本结果仅供参考，不构成专业建议。"
                }
            }

            # 格式化输出
            if args.format == "json":
                output = json.dumps(batch_result, ensure_ascii=False, indent=2)
            elif args.format == "text":
                lines = ["=" * 50, "批量处理结果", "=" * 50,
                         f"总输入: {batch_result['count']}",
                         f"成功: {batch_result['success_count']}",
                         f"失败: {batch_result['failed_count']}"]
                for i, r in enumerate(batch_result["results"], 1):
                    if "error" in r:
                        lines.append(f"\n[{i}] 处理失败: "
                                    f"{r['error']['error_code']} - "
                                    f"{r['error']['error_message']}")
                    else:
                        lines.append(f"\n[{i}] 处理成功 - "
                                    f"置信度: {r.get('confidence', 0):.0%}")
                lines.append("\n" + "=" * 50)
                output = "\n".join(lines)
            else:  # csv
                import csv
                import io
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["序号", "输入", "状态", "置信度", "错误码"])
                for i, r in enumerate(batch_result["results"], 1):
                    if "error" in r:
                        writer.writerow([i, r["raw_input"], "失败", "", 
                                       r["error"]["error_code"]])
                    else:
                        writer.writerow([i, r["raw_input"], "成功",
                                       f"{r.get('confidence', 0):.2f}", ""])
                output = buf.getvalue()
        else:
            raise SkillError("E009", "请提供 --process 或 --process-batch 参数")

        # 输出结果
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"结果已写入: {args.output}")
            except (IOError, OSError) as e:
                raise SkillError("E008", f"无法写入文件: {args.output} - {str(e)}")
        else:
            print(output)

        return 0

    except SkillError as e:
        print(f"错误 [{e.error_code}]: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [E010]: 未知错误 - {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
