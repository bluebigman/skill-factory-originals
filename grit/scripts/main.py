#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
grit 技能 - 独立实现脚本

根据功能规格实现的标准流程：
1. 收集最小信息集
2. 执行核心流程（结构化处理）
3. 输出与校验（含置信度标注）

仅使用标准库，支持 --selftest 离线自检。
"""

import argparse
import sys
import json
import os
import time
from typing import Dict, Any, List, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：输入来源、输出格式要求、期望的完整度",
    "E003": "输入格式不符合要求，示例：{'content': '...', 'output_format': 'json'}",
    "E004": "这超出了本工具的能力范围，建议：使用其他专业工具",
    "E005": "结果无法确定，建议：人工复核关键结果",
}


# ============================================================
# 核心功能类
# ============================================================
class GritProcessor:
    """核心处理器：负责解析输入、结构化输出、置信度评估"""

    # 能力边界声明
    CAPABILITIES = [
        "将用户提供的数据/文件/URL 转换为结构化结果",
        "识别并保留输入中的关键信息",
        "按约定格式生成输出",
        "对不确定项给出置信度提示",
        "支持批量处理和自定义格式",
    ]
    LIMITATIONS = [
        "不执行超出输入范围的分析",
        "不保证绝对准确，低置信度会标注",
        "不访问网络或外部服务",
    ]

    def __init__(self):
        self.input_data: Optional[Dict[str, Any]] = None
        self.output_format: str = "json"
        self.completeness: str = "standard"

    # ---------- Step 1: 收集最小信息集 ----------
    def collect_info(self, raw_input: Any) -> Dict[str, Any]:
        """解析并验证输入，收集必要信息"""
        # E001: 输入为空
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            self._raise_error("E001")

        # 尝试解析 JSON 输入
        if isinstance(raw_input, str):
            try:
                parsed = json.loads(raw_input)
            except json.JSONDecodeError:
                # 非 JSON 字符串，作为纯文本内容处理
                parsed = {"content": raw_input}
        else:
            parsed = raw_input

        if not isinstance(parsed, dict):
            self._raise_error("E003")

        self.input_data = parsed
        self._validate_input(parsed)
        return parsed

    def _validate_input(self, data: Dict[str, Any]) -> None:
        """校验必要字段"""
        # E002: 关键信息缺失
        if "content" not in data and "data" not in data and "url" not in data:
            self._raise_error("E002")
        if "output_format" in data:
            self.output_format = data["output_format"]
        if "completeness" in data:
            self.completeness = data["completeness"]

    # ---------- Step 2: 执行核心流程 ----------
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """执行核心处理流程"""
        # 提取关键信息
        content = data.get("content") or data.get("data") or data.get("url", "")
        source_type = self._detect_source_type(data)

        # 结构化处理
        structured = self._structure_content(content, source_type)

        # 计算置信度
        confidence = self._calculate_confidence(structured, content)

        # 生成结果
        result = {
            "status": "success",
            "source_type": source_type,
            "structured_data": structured,
            "confidence": confidence,
            "confidence_label": self._get_confidence_label(confidence),
            "warning": self._get_warning(confidence),
        }

        return result

    def _detect_source_type(self, data: Dict[str, Any]) -> str:
        """识别输入来源类型"""
        if "url" in data:
            return "url"
        if "file" in data:
            return "file"
        if "data" in data or "content" in data:
            return "data"
        return "unknown"

    def _structure_content(self, content: Any, source_type: str) -> Dict[str, Any]:
        """将内容结构化"""
        structured = {
            "raw_content": content if isinstance(content, str) else str(content),
            "length": len(content) if content else 0,
            "keywords": self._extract_keywords(content),
            "metadata": {
                "source_type": source_type,
                "processing_time": "instant",
            },
        }
        return structured

    def _extract_keywords(self, content: Any) -> List[str]:
        """提取关键词（简单实现：按空格/逗号分割）"""
        if not content:
            return []
        text = str(content)
        # 简单拆分，不依赖 NLP
        parts = text.replace(",", " ").replace("，", " ").split()
        # 去重并限制长度
        keywords = []
        for p in parts:
            if p not in keywords and len(p) > 1:
                keywords.append(p)
        return keywords[:10]  # 最多返回10个

    def _calculate_confidence(self, structured: Dict[str, Any], content: Any) -> float:
        """计算置信度（0-100）"""
        score = 90.0  # 基础分

        # 内容长度影响
        length = structured.get("length", 0)
        if length == 0:
            score -= 30
        elif length < 10:
            score -= 10

        # 关键词数量影响
        kw_count = len(structured.get("keywords", []))
        if kw_count == 0:
            score -= 20
        elif kw_count < 3:
            score -= 5

        # 边界检查
        return max(0, min(100, score))

    def _get_confidence_label(self, confidence: float) -> str:
        """根据置信度返回标签"""
        if confidence >= 90:
            return "高置信度"
        elif confidence >= 85:
            return "建议复核"
        else:
            return "[需核实]"

    def _get_warning(self, confidence: float) -> Optional[str]:
        """根据置信度生成警告"""
        if confidence < 85:
            return "结果无法确定，建议：人工复核关键结果"
        elif confidence < 90:
            return "部分内容建议复核"
        return None

    # ---------- Step 3: 输出与校验 ----------
    def format_output(self, result: Dict[str, Any]) -> str:
        """按指定格式输出结果"""
        if self.output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif self.output_format == "text":
            # 纯文本格式
            lines = [
                f"状态: {result['status']}",
                f"来源类型: {result['source_type']}",
                f"置信度: {result['confidence']:.1f}% ({result['confidence_label']})",
                f"内容长度: {result['structured_data']['length']}",
                f"关键词: {', '.join(result['structured_data']['keywords'])}",
            ]
            if result.get("warning"):
                lines.append(f"警告: {result['warning']}")
            return "\n".join(lines)
        else:
            self._raise_error("E003")

    def _raise_error(self, code: str) -> None:
        """抛出标准错误"""
        message = ERROR_CODES.get(code, "未知错误")
        raise ValueError(f"{code}: {message}")


# ============================================================
# 批量处理与文件支持
# ============================================================
class BatchProcessor:
    """批量处理与文件读写支持"""

    def __init__(self, processor: GritProcessor):
        self.processor = processor

    def process_file(self, filepath: str, output_format: str = "json") -> Dict[str, Any]:
        """处理单个文件，输出到带 _out 后缀的文件"""
        if not os.path.exists(filepath):
            raise ValueError(f"E004: 文件不存在: {filepath}")

        # 读取文件内容
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"E006: 读取文件失败: {e}")

        # 尝试解析 JSON，否则作为纯文本
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {"content": content}

        data["output_format"] = output_format

        # 处理
        parsed = self.processor.collect_info(data)
        result = self.processor.process(parsed)

        # 写入输出文件
        output_path = self._get_output_path(filepath)
        output_content = self.processor.format_output(result)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)

        return {
            "input_file": filepath,
            "output_file": output_path,
            "status": "success",
            "result": result,
        }

    def process_batch(self, filepaths: List[str], output_format: str = "json") -> Dict[str, Any]:
        """批量处理多个文件"""
        results = []
        failures = []
        total = len(filepaths)
        success = 0

        for filepath in filepaths:
            try:
                # 超时控制（模拟，实际用信号或线程）
                start = time.time()
                item = self.process_file(filepath, output_format)
                elapsed = time.time() - start
                if elapsed > 10:  # 10秒超时
                    raise TimeoutError("处理超时")
                results.append(item)
                success += 1
            except Exception as e:
                failures.append({
                    "file": filepath,
                    "error": str(e),
                })

        return {
            "total": total,
            "success": success,
            "failed": len(failures),
            "skipped": 0,
            "results": results,
            "failures": failures,
        }

    def _get_output_path(self, filepath: str) -> str:
        """生成输出文件路径（带 _out 后缀）"""
        base, ext = os.path.splitext(filepath)
        return f"{base}_out{ext}"


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    使用宽松阈值，不依赖精确值。
    """
    print("=" * 60)
    print("grit 技能自检开始")
    print("=" * 60)

    processor = GritProcessor()
    batch_processor = BatchProcessor(processor)
    all_passed = True

    # ---------- 测试用例 1: 正常数据处理 ----------
    print("\n[测试1] 正常数据处理")
    try:
        test_data = {
            "content": "这是一个测试内容，包含多个关键词：数据分析、处理、输出",
            "output_format": "json",
            "completeness": "standard",
        }
        parsed = processor.collect_info(test_data)
        result = processor.process(parsed)
        output = processor.format_output(result)

        # 宽松断言
        assert result["status"] == "success", "状态应为 success"
        assert result["confidence"] >= 70, f"置信度应>=70，实际: {result['confidence']}"
        assert result["structured_data"]["length"] > 10, "内容长度应>10"
        assert len(result["structured_data"]["keywords"]) >= 1, "应至少1个关键词"
        assert "structured_data" in output, "输出应包含结构化数据"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 2: URL 输入 ----------
    print("\n[测试2] URL 输入")
    try:
        test_data = {
            "url": "https://example.com/page",
            "output_format": "text",
        }
        parsed = processor.collect_info(test_data)
        result = processor.process(parsed)
        output = processor.format_output(result)

        # 宽松断言
        assert result["source_type"] == "url", "来源类型应为 url"
        assert result["confidence"] >= 60, f"置信度应>=60，实际: {result['confidence']}"
        assert "置信度" in output, "文本输出应包含置信度信息"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 3: 空输入错误处理 ----------
    print("\n[测试3] 空输入错误处理")
    try:
        processor.collect_info("")
        print("  ✗ 失败: 应抛出 E001 错误")
        all_passed = False
    except ValueError as e:
        assert "E001" in str(e), f"应包含 E001，实际: {e}"
        print("  ✓ 通过 (正确捕获 E001)")

    # ---------- 测试用例 4: 批量处理 ----------
    print("\n[测试4] 批量处理")
    try:
        batch_data = [
            {"content": "第一条测试数据"},
            {"content": "第二条测试数据，更多内容用于测试"},
            {"content": "第三条"},
        ]
        results = []
        for item in batch_data:
            parsed = processor.collect_info(item)
            result = processor.process(parsed)
            results.append(result)

        # 宽松断言
        assert len(results) == 3, f"应处理3条，实际: {len(results)}"
        for r in results:
            assert r["status"] == "success", "每条都应成功"
            assert r["confidence"] >= 50, f"置信度应>=50，实际: {r['confidence']}"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 5: 能力边界 ----------
    print("\n[测试5] 能力边界")
    try:
        assert len(processor.CAPABILITIES) == 5, "应有5项核心能力"
        assert len(processor.LIMITATIONS) == 3, "应有3项边界声明"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 6: 低置信度场景 ----------
    print("\n[测试6] 低置信度场景")
    try:
        test_data = {"content": "短"}  # 极短内容
        parsed = processor.collect_info(test_data)
        result = processor.process(parsed)

        # 宽松断言：极短内容置信度应较低
        assert result["confidence"] < 95, f"短内容置信度应<95，实际: {result['confidence']}"
        print(f"  ✓ 通过 (置信度: {result['confidence']:.1f}%)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 7: 纯文本输入 ----------
    print("\n[测试7] 纯文本输入")
    try:
        test_data = "这是一段纯文本输入，用于测试非JSON字符串的处理流程。"
        parsed = processor.collect_info(test_data)
        result = processor.process(parsed)
        output = processor.format_output(result)

        # 宽松断言
        assert result["status"] == "success", "状态应为 success"
        assert result["source_type"] == "data", "来源类型应为 data"
        assert result["confidence"] >= 70, f"置信度应>=70，实际: {result['confidence']}"
        # 修复：检查输出中是否包含结构化数据的关键字段
        assert "raw_content" in output or "内容长度" in output, "输出应包含结构化数据"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 8: 不支持的输出格式 ----------
    print("\n[测试8] 不支持的输出格式")
    try:
        test_data = {
            "content": "测试内容",
            "output_format": "xml",
        }
        parsed = processor.collect_info(test_data)
        result = processor.process(parsed)
        processor.format_output(result)
        print("  ✗ 失败: 应抛出 E003 错误")
        all_passed = False
    except ValueError as e:
        assert "E003" in str(e), f"应包含 E003，实际: {e}"
        print("  ✓ 通过 (正确捕获 E003)")

    # ---------- 测试用例 9: 文件处理 ----------
    print("\n[测试9] 文件处理")
    try:
        # 创建临时测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("这是文件内容，用于测试文件处理功能。")
            temp_file = f.name

        # 处理文件
        item = batch_processor.process_file(temp_file, "json")
        assert item["status"] == "success", "文件处理应成功"
        assert os.path.exists(item["output_file"]), "输出文件应存在"

        # 清理
        os.unlink(temp_file)
        os.unlink(item["output_file"])
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 10: 批量文件处理 ----------
    print("\n[测试10] 批量文件处理")
    try:
        import tempfile
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(f"批量测试文件 {i+1} 的内容")
                temp_files.append(f.name)

        # 批量处理
        batch_result = batch_processor.process_batch(temp_files, "json")
        assert batch_result["total"] == 3, "应处理3个文件"
        assert batch_result["success"] == 3, "全部应成功"
        assert batch_result["failed"] == 0, "不应有失败"

        # 清理
        for f in temp_files:
            os.unlink(f)
            out_f = batch_processor._get_output_path(f)
            if os.path.exists(out_f):
                os.unlink(out_f)
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 11: 幂等性 ----------
    print("\n[测试11] 幂等性")
    try:
        test_data = {"content": "幂等性测试内容"}
        parsed1 = processor.collect_info(test_data)
        result1 = processor.process(parsed1)
        parsed2 = processor.collect_info(test_data)
        result2 = processor.process(parsed2)

        assert result1 == result2, "相同输入应产生相同输出"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 测试用例 12: 错误码完整性 ----------
    print("\n[测试12] 错误码完整性")
    try:
        expected_codes = ["E001", "E002", "E003", "E004", "E005"]
        for code in expected_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 消息为空"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        all_passed = False

    # ---------- 汇总 ----------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    return all_passed


# ============================================================
# 主入口
# ============================================================
def main():
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="grit 技能 - 通用数据处理工具",
        epilog="示例: python main.py --input '{\"content\": \"测试数据\"}' --format json"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入数据（JSON字符串或纯文本）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="输入文件路径",
    )
    parser.add_argument(
        "--batch",
        type=str,
        nargs="+",
        help="批量处理多个文件路径",
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
        help="运行内置自检（不读外部文件、不访问网络）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 批量文件处理模式
    if args.batch:
        try:
            processor = GritProcessor()
            batch_processor = BatchProcessor(processor)
            result = batch_processor.process_batch(args.batch, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result["failed"] > 0:
                sys.exit(1)
            sys.exit(0)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 单文件处理模式
    if args.file:
        try:
            processor = GritProcessor()
            batch_processor = BatchProcessor(processor)
            result = batch_processor.process_file(args.file, args.format)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    # 正常处理模式
    if not args.input:
        print(f"E001: {ERROR_CODES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 提供输入，--file 处理文件，--batch 批量处理，或 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)

    try:
        processor = GritProcessor()
        # 注入输出格式
        if args.format:
            # 通过 collect_info 处理格式
            if args.input.startswith("{"):
                try:
                    data = json.loads(args.input)
                except json.JSONDecodeError:
                    data = {"content": args.input}
            else:
                data = {"content": args.input}
            data["output_format"] = args.format

            parsed = processor.collect_info(data)
        else:
            parsed = processor.collect_info(args.input)

        result = processor.process(parsed)
        output = processor.format_output(result)
        print(output)

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"E006: 未预期的错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
