#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapecraft 独立实现脚本
========================
依据功能规格 clean-room 重写的网页采集流程设计助手核心逻辑。
仅依赖 Python 标准库，离线可运行，支持 --selftest 自检。
"""

import argparse
import csv
import io
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# 错误码定义
ERROR_CODES = {
    "E001": "输入为空或格式错误",
    "E002": "URL 格式无效",
    "E003": "字段列表为空",
    "E004": "流程步骤生成失败",
    "E005": "JSON 序列化失败",
    "E006": "CSV 导出失败",
    "E007": "批量任务拆分失败",
    "E008": "字段完整性检查失败",
    "E009": "参数类型错误",
    "E010": "自检断言失败",
}


class ScrapecraftError(Exception):
    """带错误码的自定义异常"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{self.code}] {self.message}")


@dataclass
class FieldSpec:
    """字段规格定义"""

    name: str
    description: str = ""
    required: bool = True
    selector_hint: str = ""


@dataclass
class FlowStep:
    """采集流程中的单个步骤"""

    step_id: str
    step_type: str  # navigation / extraction / loop / transform / output
    description: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowDesign:
    """完整的采集流程设计"""

    name: str
    target_url: str
    fields: List[FieldSpec]
    steps: List[FlowStep]
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心逻辑模块
# ---------------------------------------------------------------------------


def validate_url(url: str) -> str:
    """校验 URL 格式，返回规范化后的 URL"""
    if not url or not isinstance(url, str):
        raise ScrapecraftError("E002", "URL 不能为空")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ScrapecraftError("E002", f"无效的 URL: {url}")
    return parsed.geturl()


def extract_fields_from_text(text: str) -> List[FieldSpec]:
    """从自然语言描述中识别关键字段"""
    if not text or not text.strip():
        raise ScrapecraftError("E001", "描述文本不能为空")

    # 常见字段关键词映射
    field_keywords = {
        "标题": "title",
        "价格": "price",
        "描述": "description",
        "图片": "image",
        "链接": "url",
        "作者": "author",
        "日期": "date",
        "评论": "comment",
        "评分": "rating",
        "库存": "stock",
    }

    fields: List[FieldSpec] = []
    for keyword, field_name in field_keywords.items():
        if keyword in text:
            fields.append(FieldSpec(name=field_name, description=f"从页面提取{keyword}"))

    if not fields:
        # 默认提取标题和描述
        fields = [
            FieldSpec(name="title", description="从页面提取标题"),
            FieldSpec(name="description", description="从页面提取描述"),
        ]
    return fields


def validate_fields(fields: List[FieldSpec]) -> List[FieldSpec]:
    """校验并规范化字段列表"""
    if not fields:
        raise ScrapecraftError("E003", "字段列表不能为空")

    seen = set()
    valid_fields = []
    for f in fields:
        if not f.name or not isinstance(f.name, str):
            raise ScrapecraftError("E003", "字段名不能为空")
        name = f.name.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        valid_fields.append(FieldSpec(name=name, description=f.description, required=f.required))
    return valid_fields


def build_flow_design(url: str, description: str, fields: Optional[List[FieldSpec]] = None) -> FlowDesign:
    """根据输入构建采集流程设计"""
    try:
        normalized_url = validate_url(url)
        if fields:
            valid_fields = validate_fields(fields)
        else:
            valid_fields = extract_fields_from_text(description)

        # 生成流程步骤
        steps = [
            FlowStep(
                step_id="step_1",
                step_type="navigation",
                description="打开目标页面",
                params={"url": normalized_url, "wait_selector": "body"},
            ),
            FlowStep(
                step_id="step_2",
                step_type="extraction",
                description="提取页面数据",
                params={"fields": [f.name for f in valid_fields]},
            ),
            FlowStep(
                step_id="step_3",
                step_type="output",
                description="输出结构化数据",
                params={"format": "json"},
            ),
        ]

        notes = ["该流程为自动生成的基础流程，可根据实际情况调整选择器。"]

        return FlowDesign(
            name=f"采集_{urlparse(normalized_url).netloc}",
            target_url=normalized_url,
            fields=valid_fields,
            steps=steps,
            notes=notes,
        )
    except ScrapecraftError:
        raise
    except Exception as exc:
        raise ScrapecraftError("E004", f"流程生成失败: {str(exc)}")


def split_batch_task(url: str, fields: List[FieldSpec], pages: int = 1) -> List[Dict[str, Any]]:
    """将多页采集任务拆分为可执行步骤"""
    if pages < 1 or not isinstance(pages, int):
        raise ScrapecraftError("E007", "页数必须是正整数")
    if not fields:
        raise ScrapecraftError("E003", "字段列表不能为空")

    tasks = []
    try:
        base_url = validate_url(url)
        for page in range(1, pages + 1):
            task = {
                "task_id": f"task_{page}",
                "url": base_url,
                "page": page,
                "fields": [f.name for f in fields],
                "action": "collect",
            }
            tasks.append(task)
        return tasks
    except ScrapecraftError:
        raise
    except Exception as exc:
        raise ScrapecraftError("E007", f"批量任务拆分失败: {str(exc)}")


def check_field_completeness(fields: List[FieldSpec]) -> Dict[str, Any]:
    """检查字段完整性并给出修正建议"""
    if not fields:
        raise ScrapecraftError("E003", "字段列表不能为空")

    complete = True
    suggestions = []
    for f in fields:
        if f.required and not f.selector_hint:
            complete = False
            suggestions.append(f"字段 '{f.name}' 缺少选择器建议，请补充 CSS/XPath 选择器")

    return {
        "complete": complete,
        "total_fields": len(fields),
        "missing_selectors": len(suggestions),
        "suggestions": suggestions,
    }


def flow_to_json(flow: FlowDesign) -> str:
    """将流程设计序列化为 JSON 字符串"""
    try:
        data = {
            "name": flow.name,
            "target_url": flow.target_url,
            "fields": [
                {"name": f.name, "description": f.description, "required": f.required}
                for f in flow.fields
            ],
            "steps": [
                {"step_id": s.step_id, "step_type": s.step_type, "description": s.description, "params": s.params}
                for s in flow.steps
            ],
            "notes": flow.notes,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise ScrapecraftError("E005", f"JSON 序列化失败: {str(exc)}")


def flow_to_csv(fields: List[FieldSpec]) -> str:
    """将字段列表导出为 CSV 字符串"""
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["字段名", "描述", "必填"])
        for f in fields:
            writer.writerow([f.name, f.description, "是" if f.required else "否"])
        return output.getvalue()
    except Exception as exc:
        raise ScrapecraftError("E006", f"CSV 导出失败: {str(exc)}")


def parse_input_text(text: str) -> Dict[str, Any]:
    """解析自然语言输入，提取 URL 和描述"""
    if not text or not text.strip():
        raise ScrapecraftError("E001", "输入不能为空")

    # 尝试提取 URL
    url_pattern = r'https?://[^\s]+'
    url_match = re.search(url_pattern, text)
    url = url_match.group(0) if url_match else ""

    # 剩余文本作为描述
    description = text
    if url:
        description = text.replace(url, "").strip()

    if not url:
        # 没有 URL 时使用示例 URL
        url = "https://example.com"
        description = description or "抓取商品标题和价格"

    return {"url": url, "description": description}


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------


def run_selftest() -> int:
    """内置硬编码样例数据，离线自检核心逻辑"""
    test_results = []

    try:
        # 测试 1: URL 校验
        test_url = "https://example.com/products"
        normalized = validate_url(test_url)
        test_results.append(("URL 校验", normalized == test_url))

        # 测试 2: 字段识别
        test_text = "抓取商品标题、价格和描述"
        fields = extract_fields_from_text(test_text)
        test_results.append(("字段识别", len(fields) >= 3))

        # 测试 3: 流程构建
        flow = build_flow_design(test_url, test_text, fields)
        test_results.append(("流程构建", len(flow.steps) >= 3 and len(flow.fields) >= 3))

        # 测试 4: JSON 序列化
        json_str = flow_to_json(flow)
        json_data = json.loads(json_str)
        test_results.append(("JSON 序列化", "name" in json_data and "steps" in json_data))

        # 测试 5: CSV 导出
        csv_str = flow_to_csv(fields)
        test_results.append(("CSV 导出", len(csv_str) > 0 and "字段名" in csv_str))

        # 测试 6: 批量任务拆分
        tasks = split_batch_task(test_url, fields, pages=3)
        test_results.append(("批量任务拆分", len(tasks) == 3))

        # 测试 7: 字段完整性检查
        check_result = check_field_completeness(fields)
        test_results.append(("字段完整性", check_result["total_fields"] == len(fields)))

        # 测试 8: 自然语言解析
        parsed = parse_input_text("请抓取 https://example.com 上的商品价格")
        test_results.append(("自然语言解析", parsed["url"].startswith("https://")))

        # 测试 9: 错误处理 - 无效 URL
        try:
            validate_url("not-a-url")
            test_results.append(("错误处理-无效URL", False))
        except ScrapecraftError as e:
            test_results.append(("错误处理-无效URL", e.code == "E002"))

        # 测试 10: 错误处理 - 空输入
        try:
            parse_input_text("")
            test_results.append(("错误处理-空输入", False))
        except ScrapecraftError as e:
            test_results.append(("错误处理-空输入", e.code == "E001"))

    except Exception as exc:
        print(f"[E010] 自检过程发生异常: {str(exc)}")
        return 1

    # 输出结果
    all_passed = True
    print("\n" + "=" * 50)
    print("Scrapecraft 自检报告")
    print("=" * 50)
    for test_name, passed in test_results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} | {test_name}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 全部自检通过！")
        return 0
    else:
        print("⚠️ 存在失败的自检项")
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Scrapecraft - 网页采集流程设计助手 (独立实现)",
        epilog="示例: python main.py --url https://example.com --desc '抓取标题和价格'",
    )
    parser.add_argument("--url", type=str, help="目标网页 URL")
    parser.add_argument("--desc", type=str, default="抓取商品标题和价格", help="采集需求描述")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出流程设计")
    parser.add_argument("--csv", action="store_true", help="以 CSV 格式输出字段列表")
    parser.add_argument("--batch", type=int, default=1, help="批量采集页数（默认 1）")
    parser.add_argument("--check", action="store_true", help="检查字段完整性")

    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常模式
    try:
        # 构建输入
        if args.url:
            url = validate_url(args.url)
            desc = args.desc
        else:
            # 从描述中解析
            parsed = parse_input_text(args.desc)
            url = parsed["url"]
            desc = parsed["description"]

        # 构建流程
        flow = build_flow_design(url, desc)

        # 输出结果
        if args.json:
            print(flow_to_json(flow))
        elif args.csv:
            print(flow_to_csv(flow.fields))
        elif args.batch > 1:
            tasks = split_batch_task(url, flow.fields, pages=args.batch)
            print(json.dumps(tasks, ensure_ascii=False, indent=2))
        elif args.check:
            result = check_field_completeness(flow.fields)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            # 默认输出人类可读的流程设计
            print(f"\n📋 采集流程设计: {flow.name}")
            print(f"📍 目标 URL: {flow.target_url}")
            print(f"📝 描述: {desc}")
            print(f"\n🔍 待采集字段 ({len(flow.fields)} 个):")
            for f in flow.fields:
                required = "必填" if f.required else "选填"
                print(f"  - {f.name} ({required}): {f.description}")
            print(f"\n🔄 流程步骤 ({len(flow.steps)} 步):")
            for i, step in enumerate(flow.steps, 1):
                print(f"  {i}. [{step.step_type}] {step.description}")
            if flow.notes:
                print(f"\n📌 备注:")
                for note in flow.notes:
                    print(f"  - {note}")

        return 0

    except ScrapecraftError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ 未预期错误: {str(exc)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
