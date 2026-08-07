#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - awesome 技能核心处理脚本（全新独立实现）

本脚本依据功能规格（clean-room）独立编写，不参考任何既有实现。
提供命令行处理入口与 --selftest 离线自检功能。
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# 常量定义
# ============================================================
APP_NAME = "awesome"
APP_VERSION = "1.0.0"
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "内部处理错误",
    "E007": "参数错误",
    "E008": "输出生成失败",
    "E009": "配置错误",
    "E010": "未知错误",
}

# 置信度阈值常量
CONFIDENCE_HIGH = 0.90       # >=90% 直接输出
CONFIDENCE_MEDIUM = 0.85     # 85%-90% 建议复核
# <85% 标注 [需核实]

# 可识别的输入类型
INPUT_TYPES = ("data", "file", "url")
OUTPUT_FORMATS = ("json", "text", "table")


# ============================================================
# 错误处理辅助类
# ============================================================
class SkillError(Exception):
    """技能自定义异常，携带错误码与消息。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


def make_error_response(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应结构。"""
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": ERROR_CODES.get(code, ERROR_CODES["E010"]),
            "detail": detail,
        },
    }


# ============================================================
# 核心处理逻辑
# ============================================================
def collect_minimum_info(
    input_source: str,
    output_format: str,
    completeness: str = "详细成品",
) -> Dict[str, str]:
    """
    Step 1: 收集最小信息集。

    参数:
        input_source: 输入来源描述
        output_format: 输出格式要求
        completeness: 期望完整度

    返回:
        标准化信息字典

    异常:
        E001: 输入为空
        E002: 关键信息缺失
        E007: 参数错误
    """
    # 校验输入来源
    if not input_source or not input_source.strip():
        raise SkillError("E001", "请提供待处理的内容，格式为：用户提供的数据/文件/URL")

    # 校验输出格式
    if not output_format or output_format.strip().lower() not in OUTPUT_FORMATS:
        raise SkillError("E007", f"输出格式必须是以下之一: {', '.join(OUTPUT_FORMATS)}")

    # 校验完整度
    if not completeness or completeness.strip() not in ("快速骨架", "详细成品"):
        raise SkillError("E007", "完整度必须是 '快速骨架' 或 '详细成品'")

    return {
        "input_source": input_source.strip(),
        "output_format": output_format.strip().lower(),
        "completeness": completeness.strip(),
    }


def parse_input_content(raw_content: Any, input_type: str = "data") -> Dict[str, Any]:
    """
    Step 2a: 解析输入内容，识别关键信息。

    参数:
        raw_content: 原始输入内容
        input_type: 输入类型 (data/file/url)

    返回:
        结构化解析结果

    异常:
        E003: 输入格式错误
        E004: 超出能力边界
    """
    # 能力边界检查
    if input_type not in INPUT_TYPES:
        raise SkillError("E004", f"不支持的输入类型 '{input_type}'，仅支持: {', '.join(INPUT_TYPES)}")

    if raw_content is None:
        raise SkillError("E003", "输入内容为空，无法解析")

    # 根据输入类型进行不同处理
    if input_type == "data":
        # 数据输入：尝试解析为 JSON 或字符串
        if isinstance(raw_content, (dict, list)):
            return {"type": "structured", "content": raw_content, "field_count": len(raw_content)}
        elif isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                return {"type": "json", "content": parsed, "field_count": len(parsed) if isinstance(parsed, (dict, list)) else 1}
            except json.JSONDecodeError:
                return {"type": "text", "content": raw_content, "field_count": len(raw_content.split())}
        else:
            # 其他类型转为字符串
            return {"type": "text", "content": str(raw_content), "field_count": len(str(raw_content).split())}

    elif input_type == "file":
        # 文件输入：读取文件内容
        if not isinstance(raw_content, str) or not os.path.isfile(raw_content):
            raise SkillError("E003", f"文件不存在或无法访问: {raw_content}")
        try:
            with open(raw_content, "r", encoding="utf-8") as f:
                content = f.read()
            return {"type": "file", "content": content, "field_count": len(content.split())}
        except (OSError, UnicodeDecodeError) as e:
            raise SkillError("E003", f"文件读取失败: {str(e)}") from e

    elif input_type == "url":
        # URL输入：按规格不做网络访问，仅做格式校验
        if not isinstance(raw_content, str) or not raw_content.startswith(("http://", "https://")):
            raise SkillError("E003", "URL格式无效，应以 http:// 或 https:// 开头")
        # 不访问网络，只返回元信息
        return {"type": "url", "url": raw_content, "field_count": 1, "note": "URL未访问（按规格不访问外部服务）"}

    # 不应到达
    raise SkillError("E010", "未预期的解析路径")


def calculate_confidence(parsed_data: Dict[str, Any]) -> float:
    """
    根据解析结果计算置信度。

    参数:
        parsed_data: 解析后的数据

    返回:
        置信度（0.0 - 1.0）
    """
    content = parsed_data.get("content", parsed_data.get("url", ""))
    field_count = parsed_data.get("field_count", 0)

    # 基础置信度
    base = 0.80

    # 根据字段数量调整
    if field_count >= 10:
        base += 0.10
    elif field_count >= 5:
        base += 0.05
    elif field_count == 0:
        base -= 0.20

    # 根据类型调整
    data_type = parsed_data.get("type", "")
    if data_type == "structured":
        base += 0.05
    elif data_type == "url":
        base -= 0.10  # 未实际访问

    # 内容非空检查
    if not content:
        base -= 0.30

    # 限制在 0.1 - 0.99 之间
    return max(0.1, min(0.99, base))


def generate_output(
    parsed_data: Dict[str, Any],
    confidence: float,
    output_format: str,
    completeness: str,
) -> Dict[str, Any]:
    """
    Step 2b/3: 生成结果并标注置信度。

    参数:
        parsed_data: 解析后的数据
        confidence: 置信度值
        output_format: 输出格式 (json/text/table)
        completeness: 完整度

    返回:
        格式化输出结果

    异常:
        E005: 置信度过低
        E008: 输出生成失败
    """
    # 置信度过低处理
    if confidence < CONFIDENCE_MEDIUM:
        raise SkillError("E005", f"结果无法确定（置信度 {confidence:.0%}），建议：补充更多信息或人工复核")

    # 构建基础结果
    result = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())[:8],
        "confidence": round(confidence, 4),
        "completeness": completeness,
    }

    # 根据置信度添加标注
    if confidence >= CONFIDENCE_HIGH:
        result["confidence_label"] = "直接输出"
    elif confidence >= CONFIDENCE_MEDIUM:
        result["confidence_label"] = "建议复核"
    else:
        result["confidence_label"] = "[需核实]"

    # 提取内容主体
    content = parsed_data.get("content", parsed_data.get("url", ""))

    # 按格式生成输出
    try:
        if output_format == "json":
            result["data"] = {
                "type": parsed_data.get("type", "unknown"),
                "content": content,
                "field_count": parsed_data.get("field_count", 0),
            }
            return {"ok": True, "format": "json", "result": result}

        elif output_format == "text":
            # 文本格式
            lines = [
                f"=== {APP_NAME} 处理结果 ===",
                f"时间: {result['timestamp']}",
                f"置信度: {result['confidence']:.0%} ({result['confidence_label']})",
                f"类型: {parsed_data.get('type', 'unknown')}",
                f"字段数: {parsed_data.get('field_count', 0)}",
                "--- 内容摘要 ---",
            ]
            # 截断内容显示
            content_str = str(content)
            if len(content_str) > 200 and completeness == "快速骨架":
                content_str = content_str[:200] + "... [已截断]"
            lines.append(content_str)
            return {"ok": True, "format": "text", "result": "\n".join(lines)}

        elif output_format == "table":
            # 表格格式（简化版）
            rows = [
                ["字段", "值"],
                ["应用", APP_NAME],
                ["版本", APP_VERSION],
                ["时间", result["timestamp"]],
                ["置信度", f"{result['confidence']:.0%}"],
                ["类型", parsed_data.get("type", "unknown")],
                ["字段数", str(parsed_data.get("field_count", 0))],
            ]
            # 格式化表格
            table_lines = []
            for row in rows:
                table_lines.append(" | ".join(str(cell) for cell in row))
            return {"ok": True, "format": "table", "result": "\n".join(table_lines)}

        else:
            raise SkillError("E007", f"不支持的输出格式: {output_format}")

    except SkillError:
        raise
    except Exception as e:
        raise SkillError("E008", f"输出生成失败: {str(e)}") from e


def process_request(
    input_source: str,
    output_format: str = "json",
    completeness: str = "详细成品",
    input_type: str = "data",
) -> Dict[str, Any]:
    """
    标准流程总入口（Step 1 -> Step 2 -> Step 3）。

    参数:
        input_source: 输入内容或来源描述
        output_format: 输出格式 (json/text/table)
        completeness: 完整度 (快速骨架/详细成品)
        input_type: 输入类型 (data/file/url)

    返回:
        处理结果字典
    """
    try:
        # Step 1: 收集最小信息集
        info = collect_minimum_info(input_source, output_format, completeness)

        # Step 2: 解析输入并计算置信度
        parsed = parse_input_content(input_source, input_type)
        confidence = calculate_confidence(parsed)

        # Step 3: 生成输出
        output = generate_output(parsed, confidence, info["output_format"], info["completeness"])
        return output

    except SkillError as e:
        return make_error_response(e.code, e.message)
    except Exception as e:
        return make_error_response("E010", f"未预期错误: {str(e)}")


# ============================================================
# 自检模块（--selftest）
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。

    不读取外部文件、不依赖当前工作目录、不访问网络。

    返回:
        True 表示全部通过，False 表示存在失败
    """
    print("=" * 60)
    print(f"{APP_NAME} v{APP_VERSION} 自检开始")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # ---- 测试用例 1：正常数据处理（JSON输入） ----
    print("\n[测试1] 正常JSON数据处理")
    try:
        sample_data = {
            "name": "示例项目",
            "items": [1, 2, 3, 4, 5],
            "metadata": {"author": "测试", "version": "1.0"},
            "active": True,
            "count": 10,
            "tags": ["a", "b", "c"],
            "description": "这是一个用于自检的示例数据",
            "priority": "high",
            "status": "ready",
            "owner": "admin",
        }
        result = process_request(json.dumps(sample_data), "json", "详细成品", "data")
        # 宽松断言：检查基本结构
        assert result.get("ok") is True, f"处理失败: {result}"
        assert "result" in result, "缺少 result 字段"
        assert result["result"]["confidence"] > 0.5, f"置信度异常: {result['result']['confidence']}"
        assert result["result"]["app"] == APP_NAME, "应用名不匹配"
        assert result["format"] == "json", "输出格式不匹配"
        print(f"  ✅ 通过 (置信度: {result['result']['confidence']:.0%})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 2：文本输入处理 ----
    print("\n[测试2] 文本输入处理")
    try:
        text_input = "这是一个测试文本，用于验证文本处理能力。包含多个关键词和描述性内容。"
        result = process_request(text_input, "text", "快速骨架", "data")
        assert result.get("ok") is True, f"处理失败: {result}"
        assert result["format"] == "text", "输出格式不匹配"
        assert "处理结果" in result["result"], "缺少结果标题"
        print(f"  ✅ 通过 (输出长度: {len(result['result'])} 字符)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 3：空输入错误处理 ----
    print("\n[测试3] 空输入错误处理")
    try:
        result = process_request("", "json", "详细成品", "data")
        assert result.get("ok") is False, "空输入应该失败"
        assert result["error"]["code"] == "E001", f"错误码应为E001, 实际: {result['error']['code']}"
        print(f"  ✅ 通过 (错误码: {result['error']['code']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 4：无效输入类型 ----
    print("\n[测试4] 无效输入类型")
    try:
        result = process_request("测试内容", "json", "详细成品", "invalid_type")
        assert result.get("ok") is False, "无效类型应该失败"
        assert result["error"]["code"] in ("E003", "E004"), f"错误码异常: {result['error']['code']}"
        print(f"  ✅ 通过 (错误码: {result['error']['code']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 5：无效输出格式 ----
    print("\n[测试5] 无效输出格式")
    try:
        result = process_request("测试内容", "xml", "详细成品", "data")
        assert result.get("ok") is False, "无效格式应该失败"
        assert result["error"]["code"] == "E007", f"错误码应为E007, 实际: {result['error']['code']}"
        print(f"  ✅ 通过 (错误码: {result['error']['code']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 6：URL输入（不访问网络） ----
    print("\n[测试6] URL输入处理")
    try:
        url_input = "https://example.com/sample"
        result = process_request(url_input, "json", "详细成品", "url")
        assert result.get("ok") is True, f"URL处理失败: {result}"
        assert result["result"]["data"]["type"] == "url", "类型应为url"
        assert "URL未访问" in str(result["result"]["data"]), "应有未访问提示"
        print(f"  ✅ 通过 (URL未实际访问)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 7：批量处理能力 ----
    print("\n[测试7] 批量数据处理")
    try:
        batch_inputs = [
            {"id": 1, "name": "项目A", "status": "active"},
            {"id": 2, "name": "项目B", "status": "pending"},
            {"id": 3, "name": "项目C", "status": "completed"},
        ]
        results = []
        for item in batch_inputs:
            r = process_request(json.dumps(item), "json", "快速骨架", "data")
            assert r.get("ok") is True, f"批量项处理失败: {r}"
            results.append(r)

        assert len(results) == 3, f"应处理3项, 实际: {len(results)}"
        # 检查所有结果都成功
        assert all(r["ok"] for r in results), "存在失败项"
        print(f"  ✅ 通过 (成功处理 {len(results)} 项)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 8：表格输出 ----
    print("\n[测试8] 表格输出格式")
    try:
        result = process_request("测试表格内容", "table", "详细成品", "data")
        assert result.get("ok") is True, f"表格处理失败: {result}"
        assert result["format"] == "table", "格式应为table"
        assert "应用" in result["result"], "表格缺少应用行"
        assert "置信度" in result["result"], "表格缺少置信度行"
        print(f"  ✅ 通过 (表格输出正常)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 9：错误码完整性 ----
    print("\n[测试9] 错误码体系完整性")
    try:
        expected_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
        for code in expected_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
            assert ERROR_CODES[code], f"错误码 {code} 消息为空"
        print(f"  ✅ 通过 (共 {len(ERROR_CODES)} 个错误码)")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1

    # ---- 测试用例 10：置信度标注逻辑 ----
    print("\n[测试10] 置信度标注逻辑")
    try:
        # 构造高置信度场景
        rich_data = {"field" + str(i): f"value{i}" for i in range(20)}
        result = process_request(json.dumps(rich_data), "json", "详细成品", "data")
        assert result.get("ok") is True, f"处理失败: {result}"
        conf = result["result"]["confidence"]
        # 宽松断言：置信度应该合理
        assert 0.5 < conf <= 1.0, f"置信度超出合理范围: {conf}"
        # 检查标注存在
        assert "confidence_label" in result["result"], "缺少置信度标注"
        print(f"  ✅ 通过 (置信度: {conf:.0%}, 标注: {result['result']['confidence_label']})")
        tests_passed += 1
    except AssertionError as e:
        print(f"  ❌ 失败: {str(e)}")
        tests_failed += 1
    except Exception as e:
        print(f"  ❌ 异常: {str(e)}")
        tests_failed += 1

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    print(f"自检完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 60)
    return tests_failed == 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - 通用数据处理工具",
        epilog="示例: python main.py --input '测试内容' --format json",
    )
    parser.add_argument("--input", "-i", type=str, help="输入内容（数据/文件路径/URL）")
    parser.add_argument("--type", "-t", type=str, choices=INPUT_TYPES, default="data",
                        help=f"输入类型，默认: data (可选: {', '.join(INPUT_TYPES)})")
    parser.add_argument("--format", "-f", type=str, choices=OUTPUT_FORMATS, default="json",
                        help=f"输出格式，默认: json (可选: {', '.join(OUTPUT_FORMATS)})")
    parser.add_argument("--completeness", "-c", type=str, choices=["快速骨架", "详细成品"],
                        default="详细成品", help="完整度，默认: 详细成品")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检（不依赖外部输入）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常处理模式
    if not args.input:
        parser.print_help()
        print("\n错误: 请提供 --input 参数（或使用 --selftest 运行自检）")
        return 1

    # 执行处理
    result = process_request(
        input_source=args.input,
        output_format=args.format,
        completeness=args.completeness,
        input_type=args.type,
    )

    # 输出结果
    if result.get("ok"):
        output = result["result"]
        if isinstance(output, str):
            print(output)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
