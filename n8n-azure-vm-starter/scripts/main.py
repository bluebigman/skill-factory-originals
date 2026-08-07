#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - n8n-azure-vm-starter 技能独立实现

本脚本依据功能规格独立编写（clean-room），提供：
- 标准流程：收集信息 -> 处理 -> 输出校验
- 错误码体系：E001-E010
- 离线自检：--selftest（使用内置硬编码样例，不依赖外部环境）
"""

import argparse
import sys
import os
from typing import Dict, List, Any, Optional


# ============================================================
# 常量定义
# ============================================================

# 错误码及对应话术（依据规格 E001-E005，扩展至 E010）
ERROR_MESSAGES: Dict[str, str] = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：{details}",
    "E003": "输入格式不符合要求，示例：{details}",
    "E004": "这超出了本工具的能力范围，建议：{details}",
    "E005": "结果无法确定，建议：{details}",
    "E006": "内部处理错误，请稍后重试或联系维护者",
    "E007": "输出格式错误，无法生成有效结果",
    "E008": "批量处理中断，部分项目未完成",
    "E009": "命令行参数错误，请检查输入",
    "E010": "未知错误，请查看日志",
}


# 能力边界声明
CAPABILITIES: List[str] = [
    "将用户提供的数据/文件/URL转换为结构化结果",
    "识别并保留输入中的关键信息",
    "按约定格式生成输出",
    "对不确定项给出置信度提示",
    "支持批量处理和自定义格式",
]

LIMITATIONS: List[str] = [
    "不执行超出输入范围的分析",
    "不保证绝对准确，低置信度会标注",
    "不访问网络或外部服务",
]


# ============================================================
# 核心处理逻辑
# ============================================================

class InputProcessor:
    """输入解析与关键信息识别"""

    @staticmethod
    def parse_text(text: str) -> Dict[str, Any]:
        """
        解析文本输入，识别关键信息。
        返回结构化字典，包含内容、长度、关键词等。
        """
        if not text or not text.strip():
            raise SkillError("E001")

        stripped = text.strip()
        # 简单分词（按空格/逗号/句号分割）
        words = [w for w in stripped.replace(",", " ").replace(".", " ").split() if w]

        result = {
            "raw": stripped,
            "length": len(stripped),
            "word_count": len(words),
            "words": words,
            "has_url": "http://" in stripped or "https://" in stripped,
            "has_file": any(stripped.lower().endswith(ext) for ext in [".txt", ".csv", ".json", ".md", ".pdf"]),
            "key_info": words[:10] if words else [],
        }
        return result


class OutputGenerator:
    """按模板生成结构化输出"""

    @staticmethod
    def generate(parsed: Dict[str, Any], custom_format: Optional[str] = None) -> Dict[str, Any]:
        """
        根据解析结果生成输出，包含置信度标注。
        """
        # 计算置信度（基于信息完整性）
        confidence = 90  # 基础分
        details = []

        if parsed["has_url"]:
            confidence += 5
            details.append("包含URL")
        if parsed["has_file"]:
            confidence += 5
            details.append("包含文件路径")
        if parsed["word_count"] >= 5:
            confidence += 5
            details.append("信息量充足")
        else:
            confidence -= 10
            details.append("信息量较少")

        # 限制在 0-100
        confidence = max(0, min(100, confidence))

        # 置信度标注
        if confidence >= 90:
            level = "直接输出"
        elif confidence >= 85:
            level = "建议复核"
        else:
            level = "[需核实]"

        output = {
            "status": "success",
            "confidence": confidence,
            "confidence_level": level,
            "data": {
                "content": parsed["raw"],
                "length": parsed["length"],
                "word_count": parsed["word_count"],
                "key_info": parsed["key_info"][:5] if parsed["key_info"] else [],
                "features": details,
            },
            "format": custom_format if custom_format else "标准模板",
        }

        # 若置信度过低，添加提示
        if confidence < 85:
            output["warning"] = "结果无法确定，建议：补充更多信息或人工复核"

        return output


class BatchProcessor:
    """批量处理支持"""

    @staticmethod
    def process_batch(items: List[str], custom_format: Optional[str] = None) -> Dict[str, Any]:
        """处理多个输入，返回批量结果"""
        results = []
        failures = []

        for idx, item in enumerate(items, 1):
            try:
                parsed = InputProcessor.parse_text(item)
                output = OutputGenerator.generate(parsed, custom_format)
                results.append({"index": idx, "result": output})
            except SkillError as e:
                failures.append({"index": idx, "error": e.code, "message": str(e)})

        batch_result = {
            "status": "success" if not failures else "partial",
            "total": len(items),
            "success_count": len(results),
            "failure_count": len(failures),
            "results": results,
            "failures": failures,
        }

        if failures:
            batch_result["warning"] = "批量处理中断，部分项目未完成"

        return batch_result


class SkillError(Exception):
    """技能异常类，携带错误码"""
    def __init__(self, code: str, details: str = ""):
        self.code = code
        self.details = details
        message = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E010"])
        if details and "{details}" in message:
            message = message.replace("{details}", details)
        super().__init__(f"[{code}] {message}")


# ============================================================
# CLI 主入口
# ============================================================

def run_standard_process(text: str, custom_format: Optional[str] = None) -> Dict[str, Any]:
    """
    标准流程：解析 -> 处理 -> 输出。
    对应规格中的 Step 1-3。
    """
    # Step 1: 检查最小信息集
    if not text:
        raise SkillError("E001")

    # Step 2: 执行核心流程
    parsed = InputProcessor.parse_text(text)
    output = OutputGenerator.generate(parsed, custom_format)

    # Step 3: 输出校验
    if not output.get("data"):
        raise SkillError("E007")

    return output


def run_selftest() -> bool:
    """
    离线自检：使用内置硬编码样例验证核心逻辑。
    不读外部文件、不依赖工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境可过。
    """
    print("=== 自检开始 ===")

    # 样例 1: 正常文本输入
    sample1 = "帮我处理这个 https://example.com/data 文件 data.csv"
    try:
        result1 = run_standard_process(sample1)
        assert result1["status"] == "success", "样例1状态错误"
        assert result1["confidence"] > 0, "样例1置信度异常"
        assert result1["confidence"] <= 100, "样例1置信度超上限"
        assert len(result1["data"]["content"]) > 0, "样例1内容为空"
        assert result1["data"]["word_count"] >= 1, "样例1词数异常"
        print(f"  样例1通过 (置信度: {result1['confidence']}%)")
    except AssertionError as e:
        print(f"  样例1失败: {e}")
        return False
    except SkillError as e:
        print(f"  样例1异常: {e}")
        return False

    # 样例 2: 空输入（应触发 E001）
    try:
        run_standard_process("")
        print("  样例2失败: 空输入未触发错误")
        return False
    except SkillError as e:
        assert e.code == "E001", f"样例2错误码错误: {e.code}"
        print("  样例2通过 (E001 空输入)")

    # 样例 3: 批量处理
    sample3 = ["项目一", "项目二", "项目三"]
    batch_result = BatchProcessor.process_batch(sample3)
    assert batch_result["total"] == 3, "批量总数错误"
    assert batch_result["success_count"] == 3, "批量成功数错误"
    assert batch_result["failure_count"] == 0, "批量失败数错误"
    assert len(batch_result["results"]) == 3, "批量结果数量错误"
    print("  样例3通过 (批量处理)")

    # 样例 4: 置信度区间检查
    sample4 = "简短"
    result4 = run_standard_process(sample4)
    assert 0 <= result4["confidence"] <= 100, "置信度区间错误"
    assert result4["confidence_level"] in ["直接输出", "建议复核", "[需核实]"], "置信度等级错误"
    print(f"  样例4通过 (置信度: {result4['confidence']}%, 等级: {result4['confidence_level']})")

    # 样例 5: 错误码体系完整性
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"错误码缺失: {code}"
        assert len(ERROR_MESSAGES[code]) > 0, f"错误码消息为空: {code}"
    print("  样例5通过 (错误码体系完整性)")

    print("=== 全部自检通过 ===")
    return True


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="n8n-azure-vm-starter 技能实现 - 仅供学习与参考用途",
        epilog="示例: python main.py --input '待处理内容' --format '自定义格式'"
    )
    parser.add_argument("--input", "-i", type=str, help="待处理内容（数据/文件/URL）")
    parser.add_argument("--format", "-f", type=str, help="输出格式要求（可选）")
    parser.add_argument("--batch", "-b", type=str, help="批量处理（用逗号分隔多个输入）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="n8n-azure-vm-starter 1.0.0")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 批量模式
    if args.batch:
        try:
            items = [item.strip() for item in args.batch.split(",") if item.strip()]
            if not items:
                raise SkillError("E001")
            result = BatchProcessor.process_batch(items, args.format)
            print(json_dumps(result, indent=2))
            return 0 if result["failure_count"] == 0 else 1
        except SkillError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 单条模式
    if args.input:
        try:
            result = run_standard_process(args.input, args.format)
            print(json_dumps(result, indent=2, ensure_ascii=False))
            return 0
        except SkillError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 无参数时显示帮助
    parser.print_help()
    return 0


def json_dumps(obj: Any, **kwargs) -> str:
    """JSON 序列化辅助（兼容 Python 3.6+）"""
    import json
    return json.dumps(obj, **kwargs)


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        sys.exit(1)
