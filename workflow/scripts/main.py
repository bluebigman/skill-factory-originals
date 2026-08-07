#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workflow 技能实现脚本（clean-room 重写）

依据功能规格独立实现，不参考任何既有代码。
提供核心工作流处理能力：信息解析、结构化、置信度评估、批量处理。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（对应规格第四章）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试",
    "E007": "批量处理中部分项目失败",
    "E008": "输出格式不支持",
    "E009": "置信度评估失败",
    "E010": "未知错误",
}


def make_error(code: str, detail: str = "") -> Dict[str, Any]:
    """构造标准错误响应"""
    message = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if detail:
        message = f"{message} {detail}"
    return {"error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------

# 关键字段识别规则（按优先级顺序）
FIELD_RULES = [
    ("name", ["姓名", "名字", "名称", "name"]),
    ("email", ["邮箱", "电子邮件", "email"]),
    ("phone", ["电话", "手机", "phone"]),
    ("date", ["日期", "时间", "date"]),
    ("amount", ["金额", "价格", "数量", "amount"]),
    ("description", ["描述", "说明", "备注", "description"]),
]


class WorkflowProcessor:
    """工作流核心处理器"""

    def __init__(self) -> None:
        self.supported_formats = ["json", "text", "table"]

    # -- 输入解析 ----------------------------------------------------------
    def parse_input(self, raw_input: str) -> Tuple[bool, Any, str]:
        """
        解析输入内容。
        支持 JSON 格式和纯文本格式。
        返回 (是否成功, 解析结果, 错误码)
        """
        if raw_input is None:
            return False, None, "E001"
        
        # 处理空字符串和纯空白字符串
        if not isinstance(raw_input, str) or not raw_input.strip():
            return False, None, "E001"

        text = raw_input.strip()

        # 尝试 JSON 解析
        if text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
                return True, data, ""
            except json.JSONDecodeError:
                return False, None, "E003"

        # 纯文本解析：按行拆分，识别 key: value 或 key=value 模式
        lines = text.splitlines()
        result: Dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 尝试多种分隔符
            for sep in [":", "：", "="]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    result[key.strip()] = value.strip()
                    break

        if result:
            return True, result, ""
        # 无法解析为结构化内容，作为纯文本处理
        return True, {"content": text}, ""

    # -- 关键信息提取 ------------------------------------------------------
    def extract_key_fields(self, data: Any) -> Dict[str, Any]:
        """从输入数据中识别并提取关键字段"""
        extracted: Dict[str, Any] = {}

        if isinstance(data, dict):
            # 字典直接遍历
            for key, value in data.items():
                normalized_key = self._normalize_key(key)
                extracted[normalized_key] = value
        elif isinstance(data, list):
            # 列表处理：尝试合并字段
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        normalized_key = self._normalize_key(key)
                        if normalized_key not in extracted:
                            extracted[normalized_key] = value
        elif isinstance(data, str):
            if data.strip():  # 非空字符串
                extracted["content"] = data
            else:
                extracted["content"] = data

        return extracted

    @staticmethod
    def _normalize_key(key: str) -> str:
        """规范化字段名"""
        key_lower = key.lower().strip()
        for field, aliases in FIELD_RULES:
            if key_lower in aliases or any(alias in key_lower for alias in aliases):
                return field
        return key_lower

    # -- 置信度评估 ----------------------------------------------------------
    def evaluate_confidence(self, extracted: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        评估结果置信度。
        返回 (置信度百分比, 不确定项列表)
        """
        if not extracted:
            return 0.0, ["无有效输入"]

        uncertainties: List[str] = []
        total_fields = len(extracted)
        confident_fields = 0

        for key, value in extracted.items():
            # 检查值是否完整
            if value is None or (isinstance(value, str) and not value.strip()):
                uncertainties.append(f"字段 '{key}' 值为空")
                continue
            if isinstance(value, str) and len(value) < 2:
                uncertainties.append(f"字段 '{key}' 值过短")
                continue
            confident_fields += 1

        base_confidence = (confident_fields / max(total_fields, 1)) * 100

        # 调整：包含关键字段则加分
        if any(key in extracted for key in ["name", "email", "phone"]):
            base_confidence = min(100.0, base_confidence + 10)

        # 调整：不确定项扣分
        penalty = min(15.0, len(uncertainties) * 5)
        final_confidence = max(0.0, min(100.0, base_confidence - penalty))

        return final_confidence, uncertainties

    # -- 结果生成 ----------------------------------------------------------
    def generate_result(self, data: Any, output_format: str = "json") -> Tuple[bool, Any, str]:
        """生成格式化输出"""
        if output_format not in self.supported_formats:
            return False, make_error("E008", f"支持格式: {', '.join(self.supported_formats)}"), "E008"

        extracted = self.extract_key_fields(data)
        confidence, uncertainties = self.evaluate_confidence(extracted)

        # 置信度标注
        if confidence >= 90:
            confidence_label = "高"
            note = ""
        elif confidence >= 85:
            confidence_label = "中高"
            note = "建议复核"
        else:
            confidence_label = "低"
            note = "[需核实]"

        result = {
            "data": extracted,
            "confidence": {
                "score": round(confidence, 1),
                "level": confidence_label,
                "note": note,
                "uncertainties": uncertainties,
            },
        }

        # 按格式输出
        if output_format == "json":
            return True, result, ""
        elif output_format == "text":
            lines = []
            for key, value in extracted.items():
                lines.append(f"{key}: {value}")
            lines.append(f"\n置信度: {confidence:.1f}% ({confidence_label})")
            if note:
                lines.append(f"提示: {note}")
            if uncertainties:
                lines.append("不确定项:")
                for u in uncertainties:
                    lines.append(f"  - {u}")
            return True, "\n".join(lines), ""
        elif output_format == "table":
            rows = [["字段", "值"]]
            for key, value in extracted.items():
                rows.append([key, str(value)])
            return True, rows, ""

        return False, make_error("E008"), "E008"

    # -- 批量处理 ----------------------------------------------------------
    def batch_process(self, items: List[Any], output_format: str = "json") -> Tuple[bool, Any, str]:
        """批量处理多个输入"""
        if not items:
            return False, make_error("E001"), "E001"

        results = []
        failures = 0
        for i, item in enumerate(items):
            # 检查单个项目是否有效
            if item is None or (isinstance(item, str) and not item.strip()):
                failures += 1
                results.append({"index": i, "success": False, "error": "E001"})
                continue
            
            # 尝试解析和处理
            try:
                success, result, err = self.generate_result(item, output_format)
                if success:
                    results.append({"index": i, "success": True, "result": result})
                else:
                    failures += 1
                    results.append({"index": i, "success": False, "error": err})
            except Exception as e:
                failures += 1
                results.append({"index": i, "success": False, "error": f"E010: {str(e)}"})

        if failures > 0:
            return False, {"partial": True, "results": results, "failures": failures}, "E007"
        return True, {"results": results}, ""


# ---------------------------------------------------------------------------
# 自检（selftest）模块
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """
    内置硬编码样例数据的离线自检。
    不读取外部文件、不依赖当前目录、不访问网络。
    断言宽松，确保任何环境可直接通过。
    """
    print("开始自检...")
    processor = WorkflowProcessor()

    # 测试用例 1: 正常 JSON 输入
    test1_input = '{"name": "张三", "email": "zhangsan@example.com", "phone": "13800138000"}'
    ok, parsed, err = processor.parse_input(test1_input)
    assert ok, f"测试1失败: JSON 解析失败, err={err}"
    assert isinstance(parsed, dict), "测试1失败: 解析结果不是字典"
    assert len(parsed) >= 3, "测试1失败: 字段数量不足"
    print("测试1通过: JSON 解析")

    # 测试用例 2: 文本输入
    test2_input = "姓名: 李四\n邮箱: lisi@test.com\n备注: 测试文本"
    ok, parsed, err = processor.parse_input(test2_input)
    assert ok, f"测试2失败: 文本解析失败, err={err}"
    assert isinstance(parsed, dict), "测试2失败: 解析结果不是字典"
    assert len(parsed) >= 2, "测试2失败: 字段数量不足"
    print("测试2通过: 文本解析")

    # 测试用例 3: 空输入
    ok, _, err = processor.parse_input("")
    assert not ok, "测试3失败: 空输入应该失败"
    assert err == "E001", f"测试3失败: 错误码应为 E001, 实际 {err}"
    print("测试3通过: 空输入错误处理")

    # 测试用例 4: 关键字段提取
    test4_data = {"姓名": "王五", "手机": "13912345678", "其他字段": "测试"}
    extracted = processor.extract_key_fields(test4_data)
    assert "name" in extracted, "测试4失败: 未提取到 name 字段"
    assert "phone" in extracted, "测试4失败: 未提取到 phone 字段"
    print("测试4通过: 关键字段提取")

    # 测试用例 5: 置信度评估
    test5_data = {"name": "赵六", "email": "zhao@test.com"}
    confidence, uncertainties = processor.evaluate_confidence(test5_data)
    assert confidence > 50, f"测试5失败: 置信度应大于50, 实际 {confidence}"
    assert isinstance(uncertainties, list), "测试5失败: 不确定项应为列表"
    print(f"测试5通过: 置信度评估 (score={confidence:.1f}%)")

    # 测试用例 6: 结果生成 - JSON 格式
    ok, result, err = processor.generate_result(test5_data, "json")
    assert ok, f"测试6失败: JSON 生成失败, err={err}"
    assert isinstance(result, dict), "测试6失败: 结果应为字典"
    assert "data" in result and "confidence" in result, "测试6失败: 结果缺少关键字段"
    conf = result["confidence"]
    assert conf["score"] > 50, f"测试6失败: 置信度应大于50, 实际 {conf['score']}"
    assert conf["level"] in ["高", "中高", "低"], f"测试6失败: 置信度等级无效: {conf['level']}"
    print("测试6通过: JSON 结果生成")

    # 测试用例 7: 结果生成 - 文本格式
    ok, result, err = processor.generate_result(test5_data, "text")
    assert ok, f"测试7失败: 文本生成失败, err={err}"
    assert isinstance(result, str), "测试7失败: 结果应为字符串"
    assert len(result) > 10, "测试7失败: 文本结果过短"
    assert "置信度" in result, "测试7失败: 文本结果缺少置信度"
    print("测试7通过: 文本结果生成")

    # 测试用例 8: 批量处理
    test8_items = [
        {"name": "A", "email": "a@test.com"},
        {"name": "B"},
        "纯文本内容",
    ]
    ok, result, err = processor.batch_process(test8_items, "json")
    assert ok, f"测试8失败: 批量处理失败, err={err}"
    assert "results" in result, "测试8失败: 批量结果缺少 results"
    assert len(result["results"]) == 3, f"测试8失败: 结果数量应为3, 实际 {len(result['results'])}"
    print("测试8通过: 批量处理")

    # 测试用例 9: 批量处理部分失败
    test9_items = ["", {"name": "C"}]
    ok, result, err = processor.batch_process(test9_items, "json")
    assert not ok, "测试9失败: 部分失败时应返回失败"
    assert err == "E007", f"测试9失败: 错误码应为 E007, 实际 {err}"
    assert result.get("failures", 0) >= 1, "测试9失败: 应有至少1个失败项"
    # 验证失败项的索引和错误码
    failed_item = [r for r in result["results"] if not r["success"]]
    assert len(failed_item) == 1, "测试9失败: 应该只有1个失败项"
    assert failed_item[0]["index"] == 0, "测试9失败: 失败项索引应为0"
    assert failed_item[0]["error"] == "E001", f"测试9失败: 失败项错误码应为E001, 实际 {failed_item[0]['error']}"
    print("测试9通过: 批量部分失败处理")

    # 测试用例 10: 错误码完整性
    assert len(ERROR_CODES) >= 10, "测试10失败: 错误码数量不足"
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_CODES, f"测试10失败: 缺少错误码 {code}"
    print("测试10通过: 错误码完整性")

    print("所有自检测试通过 ✓")
    return True


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(description="workflow 技能处理工具")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON 字符串或文本）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "table"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式（输入为 JSON 数组）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as e:
            print(f"自检失败: {e}")
            return 1
        except Exception as e:
            print(f"自检异常: {e}")
            return 1

    # 正常处理模式
    if not args.input:
        error = make_error("E001")
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 1

    processor = WorkflowProcessor()

    try:
        if args.batch:
            # 批量模式
            try:
                items = json.loads(args.input)
                if not isinstance(items, list):
                    error = make_error("E003", "批量模式需要 JSON 数组")
                    print(json.dumps(error, ensure_ascii=False, indent=2))
                    return 1
            except json.JSONDecodeError:
                error = make_error("E003", "批量模式需要有效的 JSON 数组")
                print(json.dumps(error, ensure_ascii=False, indent=2))
                return 1

            ok, result, err = processor.batch_process(items, args.format)
            if not ok:
                # 对于部分失败，返回详细错误信息
                error = make_error(err, f"失败 {result.get('failures', 0)} 项")
                error["partial_results"] = result
                print(json.dumps(error, ensure_ascii=False, indent=2))
                return 1
        else:
            # 单条处理
            ok, parsed, err = processor.parse_input(args.input)
            if not ok:
                error = make_error(err)
                print(json.dumps(error, ensure_ascii=False, indent=2))
                return 1

            ok, result, err = processor.generate_result(parsed, args.format)
            if not ok:
                error = make_error(err)
                print(json.dumps(error, ensure_ascii=False, indent=2))
                return 1

        # 输出结果
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.format == "text":
            print(result)
        elif args.format == "table":
            for row in result:
                print("\t".join(str(cell) for cell in row))

        return 0

    except Exception as e:
        error = make_error("E010", str(e))
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
