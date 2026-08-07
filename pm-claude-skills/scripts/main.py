#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pm-claude-skills — 独立实现脚本

本脚本依据功能规格独立编写（clean-room），不复制任何既有代码。
提供核心工具函数与命令行入口，支持 --selftest 离线自检。
"""

import argparse
import sys
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# 错误码定义（E001-E010）
# ------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空",
    "E002": "关键信息缺失",
    "E003": "输入格式错误",
    "E004": "超出能力边界",
    "E005": "置信度过低",
    "E006": "输出格式错误",
    "E007": "批量处理中断",
    "E008": "参数配置错误",
    "E009": "内部逻辑异常",
    "E010": "外部依赖不可用",
}


class SkillError(Exception):
    """技能运行异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


# ------------------------------------------------------------
# 核心数据结构
# ------------------------------------------------------------
class ProcessedItem:
    """单条处理结果。"""

    def __init__(self, key: str, value: Any, confidence: float, note: str = ""):
        self.key = key
        self.value = value
        self.confidence = confidence
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "note": self.note,
        }


# ------------------------------------------------------------
# 核心逻辑：信息提取与结构化
# ------------------------------------------------------------
def parse_input(raw: str) -> List[Dict[str, str]]:
    """
    将原始输入解析为结构化字段列表。
    支持格式：
      - "key=value" 每行一个
      - "key: value" 每行一个
      - JSON 对象（单行）
    返回字段字典列表。
    """
    if not raw or not raw.strip():
        raise SkillError("E001")

    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    fields: List[Dict[str, str]] = []

    # 尝试 JSON 解析（单行）
    if len(lines) == 1 and lines[0].startswith("{"):
        import json
        try:
            data = json.loads(lines[0])
            if isinstance(data, dict):
                fields.append({str(k): str(v) for k, v in data.items()})
                return fields
        except Exception:
            pass  # 不是合法 JSON，继续按行解析

    # 按行解析 key=value 或 key: value
    for line in lines:
        item: Dict[str, str] = {}
        for sep in ("=", ":"):
            if sep in line:
                k, v = line.split(sep, 1)
                item[str(k).strip()] = str(v).strip()
                break
        if item:
            fields.append(item)
        else:
            # 无法识别，整体作为 value
            fields.append({"content": line})

    if not fields:
        raise SkillError("E003")

    return fields


def extract_key_info(fields: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    从字段列表中提取关键信息。
    关键字段：name/title, type/category, desc/description
    缺失时抛出 E002。
    """
    if not fields:
        raise SkillError("E001")

    result: Dict[str, Any] = {}
    # 定义关键字段映射（别名 → 标准名）
    key_map = {
        "name": "name", "title": "name",
        "type": "type", "category": "type",
        "desc": "description", "description": "description",
    }

    for field in fields:
        for alias, std_name in key_map.items():
            if alias in field and std_name not in result:
                result[std_name] = field[alias]
                break

    # 检查关键信息完整性
    missing = [k for k in ("name", "type") if k not in result]
    if missing:
        raise SkillError("E002", f"还缺少以下信息，请补充：{', '.join(missing)}")

    return result


def compute_confidence(info: Dict[str, Any], required: List[str]) -> float:
    """
    根据已获取字段占比计算置信度。
    返回 0-1 之间的浮点数。
    """
    if not required:
        return 0.0
    hit = sum(1 for k in required if k in info and info[k])
    return hit / len(required)


def generate_output(info: Dict[str, Any], confidence: float) -> Dict[str, Any]:
    """
    生成最终输出，附置信度标注。
    置信度 < 0.85 时添加 [需核实] 标记。
    """
    output = {
        "data": info,
        "confidence": round(confidence, 2),
        "level": "",
        "note": "",
    }

    if confidence >= 0.9:
        output["level"] = "直接输出"
    elif confidence >= 0.85:
        output["level"] = "建议复核"
    else:
        output["level"] = "[需核实]"
        output["note"] = "部分字段置信度较低，请人工确认"

    return output


# ------------------------------------------------------------
# 批量处理
# ------------------------------------------------------------
def batch_process(items: List[str]) -> List[Dict[str, Any]]:
    """
    批量处理多个输入项。
    每项独立解析、提取、生成输出。
    单项失败时记录错误并继续（E007 批量中断）。
    """
    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        try:
            fields = parse_input(item)
            info = extract_key_info(fields)
            conf = compute_confidence(info, ["name", "type", "description"])
            out = generate_output(info, conf)
            out["index"] = idx
            results.append(out)
        except SkillError as e:
            results.append({
                "index": idx,
                "error": e.code,
                "message": e.message,
            })
    return results


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def run_selftest() -> bool:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    """
    print("[selftest] 开始自检...")
    try:
        # 样例1：正常输入
        raw1 = "name=项目A\ntype=PRD\ndescription=产品需求文档"
        fields1 = parse_input(raw1)
        info1 = extract_key_info(fields1)
        conf1 = compute_confidence(info1, ["name", "type", "description"])
        out1 = generate_output(info1, conf1)

        # 断言：核心字段存在
        assert out1["data"]["name"] == "项目A"
        assert out1["data"]["type"] == "PRD"
        # 宽松阈值：置信度应大于 0.8（实际应为 1.0）
        assert conf1 > 0.8

        # 样例2：带别名输入
        raw2 = "title: 项目B\ncategory: 复盘\n"
        fields2 = parse_input(raw2)
        info2 = extract_key_info(fields2)
        conf2 = compute_confidence(info2, ["name", "type"])
        out2 = generate_output(info2, conf2)

        assert out2["data"]["name"] == "项目B"
        assert out2["data"]["type"] == "复盘"
        # 宽松阈值：置信度应 >= 0.5（实际为 1.0）
        assert conf2 >= 0.5

        # 样例3：缺失关键信息 → 应抛出 E002
        try:
            parse_input("")
            assert False, "空输入应抛出 E001"
        except SkillError as e:
            assert e.code == "E001"

        try:
            extract_key_info([{"foo": "bar"}])
            assert False, "缺少关键字段应抛出 E002"
        except SkillError as e:
            assert e.code == "E002"

        # 样例4：批量处理
        batch = ["name=任务1\ntype=计划", "name=任务2\ntype=执行", "无效输入"]
        results = batch_process(batch)
        assert len(results) == 3
        # 前两项成功，第三项失败（应包含 error）
        assert results[0]["data"]["name"] == "任务1"
        assert results[1]["data"]["name"] == "任务2"
        assert "error" in results[2]

        # 样例5：置信度阈值判断
        info_low = {"name": "测试", "type": ""}
        conf_low = compute_confidence(info_low, ["name", "type"])
        out_low = generate_output(info_low, conf_low)
        # 宽松断言：低置信度时 level 应为 [需核实] 或 建议复核
        assert out_low["level"] in ("[需核实]", "建议复核")

        print("[selftest] 全部断言通过 ✓")
        return True
    except AssertionError as e:
        print(f"[selftest] 断言失败: {e}")
        return False
    except Exception as e:
        print(f"[selftest] 异常: {e}")
        return False


def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="pm-claude-skills — 信息结构化处理工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="",
        help="输入文本（支持 key=value 或 key: value 每行一个）",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default="",
        help="批量输入，用 '||' 分隔多个条目",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="输出格式（默认 text）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        ok = run_selftest()
        return 0 if ok else 1

    # 正常处理模式
    try:
        if args.batch:
            # 批量模式
            items = [x for x in args.batch.split("||") if x.strip()]
            if not items:
                raise SkillError("E001")
            results = batch_process(items)
            if args.output_format == "json":
                import json
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for r in results:
                    if "error" in r:
                        print(f"[{r['error']}] 第{r['index']}项: {r['message']}")
                    else:
                        print(f"第{r['index']}项: {r['data']} 置信度={r['confidence']} {r['level']}")
            return 0

        # 单条模式
        if not args.input:
            raise SkillError("E001")
        fields = parse_input(args.input)
        info = extract_key_info(fields)
        conf = compute_confidence(info, ["name", "type", "description"])
        out = generate_output(info, conf)

        if args.output_format == "json":
            import json
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"数据: {out['data']}")
            print(f"置信度: {out['confidence']:.2f} ({out['level']})")
            if out["note"]:
                print(f"提示: {out['note']}")
        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[E009] 内部逻辑异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
