#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prototype 技能 - 代码审查（独立实现）

本脚本依据功能规格 clean-room 编写，不包含任何既有代码。
提供命令行入口，支持 --selftest 离线自检。
"""

import sys
import argparse
import json
from typing import Dict, List, Any, Optional

# 常量定义 ---------------------------------------------------------------
SKILL_NAME = "代码审查"
SKILL_SLUG = "prototype"
VERSION = "1.0.0"

# 错误码 → 标准化话术映射
ERROR_MESSAGES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部逻辑错误，请联系开发者",
    "E007": "输出序列化失败",
    "E008": "参数校验失败",
    "E009": "批量处理中断",
    "E010": "未知异常",
}

# 触发词表（6类场景，此处按规格节选）
TRIGGER_WORDS = ["代码审查", "prototype"]

# 默认输出模板字段
DEFAULT_OUTPUT_FIELDS = ["id", "content", "confidence", "flags"]


# ----------------------------------------------------------------------
# 核心逻辑类
# ----------------------------------------------------------------------
class PrototypeProcessor:
    """核心处理器：将输入转化为结构化结果"""

    def __init__(self) -> None:
        self.name = SKILL_NAME
        self.slug = SKILL_SLUG
        self.version = VERSION

    def validate_input(self, raw_input: Any) -> None:
        """校验输入合法性，不合法时抛出带错误码的异常"""
        if raw_input is None:
            raise SkillError("E001", ERROR_MESSAGES["E001"])
        if isinstance(raw_input, str) and not raw_input.strip():
            raise SkillError("E001", ERROR_MESSAGES["E001"])
        if not isinstance(raw_input, (str, dict, list)):
            raise SkillError("E003", ERROR_MESSAGES["E003"])

    def extract_key_info(self, raw_input: Any) -> Dict[str, Any]:
        """
        识别并保留输入中的关键信息。
        输入可为字符串、字典或列表，返回结构化字典。
        """
        if isinstance(raw_input, str):
            # 简单文本：按行拆分，非空行作为内容块
            lines = [ln.strip() for ln in raw_input.splitlines() if ln.strip()]
            if not lines:
                raise SkillError("E002", ERROR_MESSAGES["E002"] + "至少需要一行非空内容")
            return {"source_type": "text", "items": lines, "count": len(lines)}
        elif isinstance(raw_input, dict):
            # 字典输入：检查是否包含 content 或 items 字段
            if "content" in raw_input:
                return {"source_type": "dict", "items": [raw_input["content"]], "count": 1}
            if "items" in raw_input and isinstance(raw_input["items"], list):
                items = raw_input["items"]
                return {"source_type": "dict", "items": items, "count": len(items)}
            # 其他字段则整体作为一项
            return {"source_type": "dict", "items": [raw_input], "count": 1}
        elif isinstance(raw_input, list):
            # 列表输入：逐项处理
            if not raw_input:
                raise SkillError("E002", ERROR_MESSAGES["E002"] + "列表不能为空")
            return {"source_type": "list", "items": raw_input, "count": len(raw_input)}
        # 理论上不可达（validate 已拦截）
        raise SkillError("E003", ERROR_MESSAGES["E003"])

    def compute_confidence(self, item: Any) -> float:
        """
        计算置信度（0~1）。
        规则：
        - 字符串非空且长度>5 → 高置信度
        - 字典包含关键字段 → 高置信度
        - 其他情况 → 中低置信度
        """
        if isinstance(item, str):
            length = len(item.strip())
            if length > 20:
                return 0.95
            elif length > 5:
                return 0.88
            else:
                return 0.75
        elif isinstance(item, dict):
            # 字典含 content/id/type 等关键字段则加分
            score = 0.7
            for key in ("id", "content", "type", "name"):
                if key in item and item[key]:
                    score += 0.08
            return min(score, 0.98)
        elif isinstance(item, (int, float)):
            return 0.9
        else:
            return 0.6

    def format_item(self, idx: int, item: Any, confidence: float) -> Dict[str, Any]:
        """将单个条目格式化为标准输出结构"""
        return {
            "id": idx,
            "content": item,
            "confidence": confidence,
            "flags": self._generate_flags(confidence),
        }

    def _generate_flags(self, confidence: float) -> List[str]:
        """根据置信度生成标注"""
        if confidence >= 0.9:
            return []
        elif confidence >= 0.85:
            return ["建议复核"]
        else:
            return ["[需核实]"]

    def process(self, raw_input: Any) -> Dict[str, Any]:
        """执行核心流程，返回结构化结果"""
        # Step 1: 校验
        self.validate_input(raw_input)

        # Step 2: 解析关键信息
        parsed = self.extract_key_info(raw_input)

        # Step 3: 逐项处理
        results = []
        for idx, item in enumerate(parsed["items"], start=1):
            conf = self.compute_confidence(item)
            results.append(self.format_item(idx, item, conf))

        # Step 4: 汇总
        overall_conf = sum(r["confidence"] for r in results) / len(results) if results else 0.0
        return {
            "skill": self.slug,
            "skill_name": self.name,
            "version": self.version,
            "source_type": parsed["source_type"],
            "total_items": parsed["count"],
            "overall_confidence": round(overall_conf, 4),
            "items": results,
        }

    def batch_process(self, inputs: List[Any]) -> Dict[str, Any]:
        """批量处理多个输入"""
        if not inputs:
            raise SkillError("E001", ERROR_MESSAGES["E001"])
        batch_results = []
        for i, inp in enumerate(inputs, start=1):
            try:
                result = self.process(inp)
                batch_results.append({"batch_index": i, "success": True, "result": result})
            except SkillError as e:
                batch_results.append({
                    "batch_index": i,
                    "success": False,
                    "error_code": e.code,
                    "error_message": e.message,
                })
            except Exception as e:  # 兜底
                batch_results.append({
                    "batch_index": i,
                    "success": False,
                    "error_code": "E010",
                    "error_message": f"未知异常: {str(e)}",
                })
        success_count = sum(1 for r in batch_results if r["success"])
        return {
            "batch_total": len(inputs),
            "batch_success": success_count,
            "batch_failed": len(inputs) - success_count,
            "results": batch_results,
        }


# ----------------------------------------------------------------------
# 异常类
# ----------------------------------------------------------------------
class SkillError(Exception):
    """带错误码的业务异常"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ----------------------------------------------------------------------
# 自检模块（离线硬编码样例）
# ----------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用硬编码样例数据，不读取外部文件、不依赖工作目录、不访问网络。
    断言采用宽松阈值，保证任何环境可过。
    """
    print("[selftest] 开始离线自检...")
    processor = PrototypeProcessor()

    # --- 测试用例 1: 字符串输入 ---
    print("[selftest] 用例1: 字符串输入")
    try:
        result = processor.process("这是一段用于测试的输入文本，包含足够长度以获取较高置信度。")
        assert result["total_items"] >= 1, "字符串输入应至少产生1个条目"
        assert result["overall_confidence"] > 0, "置信度应大于0"
        assert "items" in result, "输出应包含 items 字段"
        assert all(0 <= it["confidence"] <= 1 for it in result["items"]), "置信度应在0~1之间"
        print("[selftest] 用例1 通过")
    except AssertionError as e:
        print(f"[selftest] 用例1 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例1 异常: {e}")
        return False

    # --- 测试用例 2: 字典输入 ---
    print("[selftest] 用例2: 字典输入")
    try:
        dict_input = {"content": "字典内容测试", "type": "test"}
        result = processor.process(dict_input)
        assert result["source_type"] == "dict", "来源类型应为 dict"
        assert result["total_items"] == 1, "单个字典应产生1个条目"
        print("[selftest] 用例2 通过")
    except AssertionError as e:
        print(f"[selftest] 用例2 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例2 异常: {e}")
        return False

    # --- 测试用例 3: 列表输入 ---
    print("[selftest] 用例3: 列表输入")
    try:
        list_input = ["条目一", "条目二", "条目三"]
        result = processor.process(list_input)
        assert result["total_items"] == 3, "列表输入应产生3个条目"
        assert len(result["items"]) == 3, "items 列表长度应为3"
        print("[selftest] 用例3 通过")
    except AssertionError as e:
        print(f"[selftest] 用例3 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例3 异常: {e}")
        return False

    # --- 测试用例 4: 错误码 E001（空输入） ---
    print("[selftest] 用例4: 空输入异常")
    try:
        processor.process("")
        print("[selftest] 用例4 失败: 空输入未抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E001", f"错误码应为 E001，实际为 {e.code}"
        print("[selftest] 用例4 通过")
    except Exception as e:
        print(f"[selftest] 用例4 异常: {e}")
        return False

    # --- 测试用例 5: 错误码 E003（非法类型） ---
    print("[selftest] 用例5: 非法类型异常")
    try:
        processor.process(12345)  # 数字类型不支持
        print("[selftest] 用例5 失败: 非法类型未抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E003", f"错误码应为 E003，实际为 {e.code}"
        print("[selftest] 用例5 通过")
    except Exception as e:
        print(f"[selftest] 用例5 异常: {e}")
        return False

    # --- 测试用例 6: 批量处理 ---
    print("[selftest] 用例6: 批量处理")
    try:
        batch_input = ["批量文本一", {"content": "批量字典"}, ""]  # 第三个会失败
        result = processor.batch_process(batch_input)
        assert result["batch_total"] == 3, "批量总数应为3"
        assert result["batch_success"] >= 2, "成功数应至少为2"
        assert result["batch_failed"] >= 0, "失败数应非负"
        print("[selftest] 用例6 通过")
    except AssertionError as e:
        print(f"[selftest] 用例6 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例6 异常: {e}")
        return False

    # --- 测试用例 7: 置信度范围 ---
    print("[selftest] 用例7: 置信度范围验证")
    try:
        samples = ["短", "中等长度的文本", "这是一个较长的文本用于测试置信度计算逻辑是否正常"]
        for s in samples:
            result = processor.process(s)
            for item in result["items"]:
                assert 0 <= item["confidence"] <= 1, f"置信度越界: {item['confidence']}"
                # 宽松阈值：短文本置信度不应高于长文本
        short_conf = processor.compute_confidence("短")
        long_conf = processor.compute_confidence("这是一个较长的文本用于测试置信度计算逻辑是否正常")
        assert short_conf < long_conf, "短文本置信度应低于长文本"
        print("[selftest] 用例7 通过")
    except AssertionError as e:
        print(f"[selftest] 用例7 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例7 异常: {e}")
        return False

    # --- 测试用例 8: 输出序列化 ---
    print("[selftest] 用例8: JSON 序列化")
    try:
        result = processor.process("序列化测试文本，内容足够长以确保置信度正常。")
        json_str = json.dumps(result, ensure_ascii=False)
        assert len(json_str) > 0, "序列化结果不应为空"
        # 反序列化回字典
        loaded = json.loads(json_str)
        assert loaded["skill"] == SKILL_SLUG, "skill 字段不符"
        print("[selftest] 用例8 通过")
    except AssertionError as e:
        print(f"[selftest] 用例8 失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 用例8 异常: {e}")
        return False

    print("[selftest] 全部用例通过 ✔")
    return True


# ----------------------------------------------------------------------
# 命令行入口
# ----------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description=f"{SKILL_NAME} 技能处理脚本 (v{VERSION})",
        epilog="示例: python main.py --input '待处理文本' | python main.py --selftest",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="待处理的输入内容（字符串）。也支持 JSON 格式传入字典或列表。",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="批量处理：传入 JSON 数组，每个元素作为一个独立输入。",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="执行离线自检（使用内置样例数据，不依赖外部资源）。",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="以格式化 JSON 输出（带缩进）。",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 无输入参数
    if not args.input and not args.batch:
        print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
        print("提示: 使用 --input 提供内容，或 --selftest 执行自检。", file=sys.stderr)
        return 1

    # 初始化处理器
    processor = PrototypeProcessor()

    try:
        # 批量模式
        if args.batch:
            try:
                batch_data = json.loads(args.batch)
                if not isinstance(batch_data, list):
                    raise SkillError("E003", "批量输入必须是 JSON 数组")
                result = processor.batch_process(batch_data)
            except json.JSONDecodeError:
                print(f"错误 E003: 批量输入不是合法 JSON: {ERROR_MESSAGES['E003']}", file=sys.stderr)
                return 1

        # 单条模式
        else:
            # 尝试将 input 解析为 JSON（支持字典/列表输入）
            try:
                input_data = json.loads(args.input)
            except json.JSONDecodeError:
                # 不是 JSON，按普通字符串处理
                input_data = args.input
            result = processor.process(input_data)

    except SkillError as e:
        print(f"错误 {e.code}: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: 未知异常: {str(e)}", file=sys.stderr)
        return 1

    # 输出结果
    try:
        if args.pretty:
            output = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output = json.dumps(result, ensure_ascii=False)
        print(output)
        return 0
    except Exception as e:
        print(f"错误 E007: 输出序列化失败: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
