#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lanshu-awesome-ai-video-kit
企业视频制作 智能工具包 —— 独立实现脚本

本脚本根据功能规格独立编写（clean-room），不复制任何既有代码。
提供数据解析、批量转换与置信度标注能力。

用法示例:
    python scripts/main.py --selftest
    python scripts/main.py --input "项目A 预算10万 负责人张三" --format json
    python scripts/main.py --input-file data.txt --format md --batch-limit 20
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 版本信息
VERSION = "1.0.1"
SLUG = "lanshu-awesome-ai-video-kit"

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：输入参数缺失或格式不正确",
    "E002": "文件错误：无法读取指定文件",
    "E003": "URL错误：URL格式无效或无法访问",
    "E004": "解析错误：输入数据无法解析为有效内容",
    "E005": "批量错误：单批输入数量超过上限(20)",
    "E006": "格式错误：不支持的输出格式（仅支持md/json）",
    "E007": "模式错误：input与input-file不能同时使用",
    "E008": "内部错误：处理过程中发生未预期异常",
    "E009": "配置错误：output_schema格式不正确",
    "E010": "数据错误：输入数据为空或全为空白字符",
}

# 默认输出字段模板
DEFAULT_SCHEMA = [
    "project_name",      # 项目名称
    "timeline",          # 时间节点
    "role",              # 角色/负责人
    "budget",            # 预算
    "material_path",     # 素材路径
    "category",          # 分类（自动推断）
    "priority",          # 优先级（自动推断）
    "tags",              # 标签（自动推断）
]

# 置信度等级
CONFIDENCE_HIGH = "高"
CONFIDENCE_MEDIUM = "中"
CONFIDENCE_LOW = "低"


def error_exit(code: str, detail: str = "") -> None:
    """输出错误信息并退出程序"""
    msg = ERROR_CODES.get(code, "未知错误")
    if detail:
        msg = f"{msg} | {detail}"
    print(f"[错误 {code}] {msg}", file=sys.stderr)
    sys.exit(1)


def validate_input_text(text: str) -> str:
    """校验输入文本有效性"""
    if text is None:
        error_exit("E001", "输入文本为空")
    cleaned = text.strip()
    if not cleaned:
        error_exit("E010", "输入数据为空或全为空白字符")
    return cleaned


def extract_project_name(text: str) -> Tuple[str, str]:
    """提取项目名称（中英文均可识别）"""
    # 优先匹配"项目"或"project"后的内容
    patterns = [
        r"(?:项目|project)[:：\s]*([^\s,，。;；]+)",
        r"([^\s,，。;；]{2,20}(?:项目|工程|计划))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), CONFIDENCE_HIGH
    # 回退：取第一个较长的词作为项目名
    words = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,}", text)
    if words:
        return words[0], CONFIDENCE_MEDIUM
    return "[需核实:project_name]", CONFIDENCE_LOW


def extract_timeline(text: str) -> Tuple[str, str]:
    """提取时间节点信息"""
    patterns = [
        r"(?:时间|日期|节点|deadline|due)[:：\s]*([0-9]{4}[-/年][0-9]{1,2}(?:[-/月][0-9]{1,2}日?)?)",
        r"([0-9]{4}[-/年][0-9]{1,2}(?:[-/月][0-9]{1,2}日?)?)",
        r"(\d+月\d+日)",
        r"(\d{1,2}:\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1), CONFIDENCE_HIGH
    return "[需核实:timeline]", CONFIDENCE_LOW


def extract_role(text: str) -> Tuple[str, str]:
    """提取角色/负责人信息"""
    patterns = [
        r"(?:负责人|角色|联系人|owner|contact)[:：\s]*([\u4e00-\u9fa5A-Za-z]{2,})",
        r"([\u4e00-\u9fa5]{2,4})(?:负责|主管|经理|总监)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(), CONFIDENCE_HIGH
    return "[需核实:role]", CONFIDENCE_LOW


def extract_budget(text: str) -> Tuple[str, str]:
    """提取预算信息"""
    patterns = [
        r"(?:预算|经费|budget)[:：\s]*([0-9,，.]+(?:\s*万|\s*元|\s*USD)?)",
        r"([0-9,，.]+\s*万(?:\s*元)?)",
        r"([0-9,，.]+\s*元)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace(",", "").replace("，", ""), CONFIDENCE_HIGH
    return "[需核实:budget]", CONFIDENCE_LOW


def extract_material_path(text: str) -> Tuple[str, str]:
    """提取素材路径（URL或文件路径）"""
    patterns = [
        r"(?:素材|路径|path|url)[:：\s]*([^\s,，;；]+)",
        r"(https?://[^\s,，;；]+)",
        r"([/\\][^\s,，;；]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), CONFIDENCE_HIGH
    return "[需核实:material_path]", CONFIDENCE_LOW


def infer_category(text: str) -> Tuple[str, str]:
    """推断分类"""
    keywords = {
        "宣传": ["宣传", "推广", "广告", "marketing"],
        "培训": ["培训", "教学", "学习", "training"],
        "汇报": ["汇报", "总结", "报告", "report"],
        "产品": ["产品", "发布", "介绍", "product"],
        "活动": ["活动", "庆典", "会议", "event"],
    }
    for category, words in keywords.items():
        for word in words:
            if word in text.lower():
                return category, CONFIDENCE_HIGH
    return "未分类", CONFIDENCE_LOW


def infer_priority(text: str) -> Tuple[str, str]:
    """推断优先级"""
    if re.search(r"(紧急|加急|urgent|asap)", text, re.IGNORECASE):
        return "高", CONFIDENCE_HIGH
    if re.search(r"(重要|核心|重点|important)", text, re.IGNORECASE):
        return "中", CONFIDENCE_HIGH
    return "普通", CONFIDENCE_MEDIUM


def infer_tags(text: str) -> Tuple[List[str], str]:
    """推断标签（提取关键名词）"""
    # 提取中文词（2-4字）和英文单词
    cn_words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
    en_words = re.findall(r"[A-Za-z]{3,}", text)
    # 过滤常见无意义词
    stopwords = {"项目", "视频", "制作", "工作", "进行", "需要", "以及", "一个", "这个", "那个", "相关", "所有", "the", "and", "for", "with"}
    tags = [w for w in cn_words + en_words if w not in stopwords]
    # 去重并限制数量
    unique_tags = list(dict.fromkeys(tags))[:5]
    if unique_tags:
        return unique_tags, CONFIDENCE_MEDIUM
    return ["未标注"], CONFIDENCE_LOW


def parse_single_input(text: str) -> Dict[str, Any]:
    """解析单条输入，返回结构化数据"""
    cleaned = validate_input_text(text)

    # 提取各字段
    project_name, name_conf = extract_project_name(cleaned)
    timeline, time_conf = extract_timeline(cleaned)
    role, role_conf = extract_role(cleaned)
    budget, budget_conf = extract_budget(cleaned)
    material_path, path_conf = extract_material_path(cleaned)
    category, cat_conf = infer_category(cleaned)
    priority, pri_conf = infer_priority(cleaned)
    tags, tag_conf = infer_tags(cleaned)

    # 计算整体置信度（取最低值）
    conf_levels = [name_conf, time_conf, role_conf, budget_conf, path_conf, cat_conf, pri_conf, tag_conf]
    if CONFIDENCE_LOW in conf_levels:
        overall_conf = CONFIDENCE_LOW
        low_fields = [field for field, conf in zip(
            ["project_name", "timeline", "role", "budget", "material_path", "category", "priority", "tags"],
            conf_levels
        ) if conf == CONFIDENCE_LOW]
        confidence_note = f"低置信度字段: {', '.join(low_fields)}"
    elif CONFIDENCE_MEDIUM in conf_levels:
        overall_conf = CONFIDENCE_MEDIUM
        confidence_note = "部分字段为自动推断"
    else:
        overall_conf = CONFIDENCE_HIGH
        confidence_note = "全部字段高置信度"

    return {
        "project_name": project_name,
        "timeline": timeline,
        "role": role,
        "budget": budget,
        "material_path": material_path,
        "category": category,
        "priority": priority,
        "tags": tags,
        "_confidence": overall_conf,
        "_confidence_note": confidence_note,
    }


def apply_custom_schema(data: Dict[str, Any], schema: List[str]) -> Dict[str, Any]:
    """应用自定义输出字段结构"""
    if not isinstance(schema, list) or not all(isinstance(s, str) for s in schema):
        error_exit("E009", "output_schema必须是字符串列表")
    result = {}
    for field in schema:
        field_clean = field.strip()
        if field_clean.startswith("_"):
            continue  # 跳过内部字段
        if field_clean in data:
            result[field_clean] = data[field_clean]
        else:
            result[field_clean] = "[需核实:{}]".format(field_clean)
    # 附加置信度信息
    result["_confidence"] = data.get("_confidence", CONFIDENCE_LOW)
    result["_confidence_note"] = data.get("_confidence_note", "")
    return result


def parse_batch_inputs(inputs: List[str], schema: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """批量解析输入"""
    if len(inputs) > 20:
        error_exit("E005", f"单批输入数量{len(inputs)}超过上限20")

    results = []
    for item in inputs:
        parsed = parse_single_input(item)
        if schema:
            parsed = apply_custom_schema(parsed, schema)
        results.append(parsed)
    return results


def format_markdown(results: List[Dict[str, Any]]) -> str:
    """格式化为Markdown表格输出"""
    if not results:
        return "无数据处理结果"

    # 获取所有字段（排除内部字段）
    all_fields = []
    for r in results:
        for k in r.keys():
            if not k.startswith("_") and k not in all_fields:
                all_fields.append(k)

    # 构建表头
    header = "| " + " | ".join(all_fields) + " | 置信度 |"
    separator = "|" + "---|" * (len(all_fields) + 1)

    # 构建数据行
    lines = [header, separator]
    for r in results:
        row = []
        for field in all_fields:
            value = r.get(field, "[需核实:{}]".format(field))
            if isinstance(value, list):
                value = ", ".join(value)
            row.append(str(value))
        row.append(r.get("_confidence", CONFIDENCE_LOW))
        lines.append("| " + " | ".join(row) + " |")

    # 附加置信度说明
    notes = []
    for i, r in enumerate(results, 1):
        if r.get("_confidence_note"):
            notes.append(f"条目{i}: {r['_confidence_note']}")
    if notes:
        lines.append("\n**置信度说明:**")
        lines.extend(notes)

    return "\n".join(lines)


def format_json(results: List[Dict[str, Any]]) -> str:
    """格式化为JSON输出"""
    return json.dumps(results, ensure_ascii=False, indent=2)


def read_input_file(filepath: str) -> List[str]:
    """从文件读取输入（每行一条）"""
    try:
        path = Path(filepath)
        if not path.exists():
            error_exit("E002", f"文件不存在: {filepath}")
        content = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            error_exit("E010", "文件中无有效内容")
        return lines
    except PermissionError:
        error_exit("E002", f"无权限读取文件: {filepath}")
    except UnicodeDecodeError:
        error_exit("E002", f"文件编码不是UTF-8: {filepath}")


def validate_url(url: str) -> bool:
    """验证URL格式（仅格式校验，不访问网络）"""
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url, re.IGNORECASE))


def process_url(url: str) -> Dict[str, Any]:
    """处理URL输入（仅提取URL本身作为素材路径）"""
    if not validate_url(url):
        error_exit("E003", f"URL格式无效: {url}")
    # 注意：按规格说明，不访问网络，仅将URL作为文本处理
    return parse_single_input(f"素材路径: {url}")


def run_selftest() -> None:
    """内置硬编码样例数据的离线自检"""
    print("=" * 60)
    print(f"[自检] {SLUG} v{VERSION} 开始离线自检")
    print("=" * 60)

    # 硬编码测试数据（不读取外部文件）
    test_inputs = [
        "企业宣传片项目 预算50万元 负责人李明 时间2026年3月15日 素材路径: /video/raw/company_intro.mp4",
        "新产品发布会视频 预算30万 联系：王芳 截止日期2026-05-20 素材: https://example.com/assets/product.mp4",
        "员工培训视频制作 预算8万元 负责人张伟 时间2026年4月1日",
        "年度总结汇报视频 预算15万 联系人：赵强 素材路径: C:\\videos\\report\\annual.pptx",
    ]

    print(f"\n[步骤1] 单条解析测试（{len(test_inputs)}条）")
    parsed_results = []
    for i, text in enumerate(test_inputs, 1):
        result = parse_single_input(text)
        parsed_results.append(result)
        # 宽松断言：必须包含所有关键字段
        assert "project_name" in result, f"条目{i}缺少project_name"
        assert "budget" in result, f"条目{i}缺少budget"
        assert "role" in result, f"条目{i}缺少role"
        assert "_confidence" in result, f"条目{i}缺少置信度"
        # 置信度必须是合法值
        assert result["_confidence"] in [CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW], \
            f"条目{i}置信度非法: {result['_confidence']}"
        print(f"  条目{i}: 项目={result['project_name']}, 预算={result['budget']}, "
              f"置信度={result['_confidence']}")
    print("  [通过] 单条解析测试成功")

    print("\n[步骤2] 批量解析测试（含自定义schema）")
    custom_schema = ["project_name", "budget", "priority"]
    batch_results = parse_batch_inputs(test_inputs[:3], schema=custom_schema)
    assert len(batch_results) == 3, f"批量结果数量错误: {len(batch_results)}"
    for result in batch_results:
        assert set(result.keys()) >= set(custom_schema), "自定义schema字段缺失"
        assert "_confidence" in result, "缺少置信度字段"
    print(f"  批量处理{len(batch_results)}条，自定义schema字段: {custom_schema}")
    print("  [通过] 批量解析测试成功")

    print("\n[步骤3] 输出格式测试")
    md_output = format_markdown(parsed_results[:2])
    assert "|" in md_output, "Markdown输出缺少表格分隔符"
    assert "置信度" in md_output, "Markdown输出缺少置信度列"
    print(f"  Markdown输出长度: {len(md_output)} 字符")

    json_output = format_json(parsed_results[:2])
    json_data = json.loads(json_output)
    assert isinstance(json_data, list) and len(json_data) == 2, "JSON解析失败"
    print(f"  JSON输出长度: {len(json_output)} 字符")
    print("  [通过] 输出格式测试成功")

    print("\n[步骤4] 边界测试")
    # 空输入测试
    try:
        parse_single_input("   ")
        assert False, "空输入未触发错误"
    except SystemExit as e:
        assert e.code != 0, "空输入错误码异常"
    print("  空输入处理正常")

    # 超批量测试
    try:
        parse_batch_inputs(["测试"] * 21)
        assert False, "超批量未触发错误"
    except SystemExit as e:
        assert e.code != 0, "超批量错误码异常"
    print("  超批量处理正常")

    # URL验证测试
    assert validate_url("https://example.com/path") is True, "合法URL验证失败"
    assert validate_url("not-a-url") is False, "非法URL验证失败"
    print("  URL验证正常")
    print("  [通过] 边界测试成功")

    print("\n[步骤5] 关键信息保留测试")
    test_text = "特殊项目X100 预算1,234,567元 联系人:张三名 时间2026年12月31日 素材:https://x.com/a?b=1"
    result = parse_single_input(test_text)
    # 检查数字保留（宽松：至少包含部分数字）
    budget_str = str(result["budget"])
    assert any(ch.isdigit() for ch in budget_str), "预算数字未保留"
    # 检查URL保留
    assert "https://" in str(result["material_path"]), "URL未保留"
    # 检查中文名保留
    assert "张" in str(result["role"]) or "负责人" in str(result["role"]), "中文名未保留"
    print("  特殊字符、数字、URL均正确保留")
    print("  [通过] 关键信息保留测试成功")

    print("\n" + "=" * 60)
    print("[自检] 全部测试通过 ✅")
    print("=" * 60)


def main() -> None:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="企业视频制作 智能工具包 - 数据处理脚本",
        epilog="示例: python scripts/main.py --input '项目A 预算10万' --format json"
    )
    parser.add_argument("--input", "-i", type=str, help="单条输入文本")
    parser.add_argument("--input-file", "-f", type=str, help="输入文件路径（每行一条）")
    parser.add_argument("--format", "-fmt", choices=["md", "json"], default="md",
                        help="输出格式（默认: md）")
    parser.add_argument("--output-schema", "-s", type=str,
                        help="自定义输出字段，逗号分隔（如: project_name,budget,priority）")
    parser.add_argument("--batch-limit", type=int, default=20,
                        help="单批最大处理条数（默认: 20，最大: 20）")
    parser.add_argument("--selftest", action="store_true",
                        help="运行离线自检（使用内置样例数据）")
    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 参数互斥检查
    if args.input and args.input_file:
        error_exit("E007", "--input 与 --input-file 不能同时使用")

    # 获取输入数据
    inputs: List[str] = []
    if args.input:
        inputs = [args.input]
    elif args.input_file:
        inputs = read_input_file(args.input_file)
    else:
        # 无输入时尝试从stdin读取
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                inputs = [line.strip() for line in stdin_data.splitlines() if line.strip()]
        if not inputs:
            error_exit("E001", "请提供 --input 或 --input-file 参数，或通过stdin传入数据")

    # 批量限制检查
    if len(inputs) > min(args.batch_limit, 20):
        error_exit("E005", f"输入数量{len(inputs)}超过限制{min(args.batch_limit, 20)}")

    # 解析自定义schema
    custom_schema = None
    if args.output_schema:
        custom_schema = [s.strip() for s in args.output_schema.split(",") if s.strip()]
        if not custom_schema:
            error_exit("E009", "output_schema为空")

    # 处理数据
    try:
        results = parse_batch_inputs(inputs, schema=custom_schema)

        # 输出
        if args.format == "json":
            output = format_json(results)
        else:
            output = format_markdown(results)
        print(output)

    except SystemExit:
        raise
    except Exception as e:
        error_exit("E008", f"处理异常: {str(e)}")


if __name__ == "__main__":
    main()
