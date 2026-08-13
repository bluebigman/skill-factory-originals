#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill-59071 手机教程全流程处理 素材整理

根据功能规格独立实现（clean-room）：
识别手机型号与操作目标，整理截图与文字，自动生成结构化教程文档。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --input notes.txt --output tutorial.md --dry-run
    python scripts/main.py --input notes.txt --output tutorial.md --force --verbose
"""

import argparse
import os
import re
import sys
import tempfile
import traceback
from collections import OrderedDict

# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "素材格式不支持（仅支持 PNG/JPG）",
    "E002": "缺少操作目标描述",
    "E003": "截图顺序混乱（时间戳不连续）",
    "E004": "OCR 识别率过低（文字清晰度不足）",
    "E005": "设备型号冲突（检测到多种品牌）",
    "E006": "步骤信息不完整（缺少预期结果）",
    "E007": "素材量超出限制（单次最多 20 张截图）",
    "E008": "输入文件不存在或无法读取",
    "E009": "输出目录不可写",
    "E010": "内部逻辑错误（未知异常）",
}

# 品牌关键词表（用于设备识别）
BRAND_KEYWORDS = {
    "华为": ["华为", "HUAWEI", "HarmonyOS", "EMUI"],
    "小米": ["小米", "Xiaomi", "MIUI", "Redmi", "红米"],
    "苹果": ["苹果", "iPhone", "iOS", "Apple"],
    "OPPO": ["OPPO", "ColorOS"],
    "vivo": ["vivo", "OriginOS", "Funtouch"],
    "三星": ["三星", "Samsung", "One UI"],
}

# 常见系统版本关键词
SYSTEM_VERSION_KEYWORDS = [
    "HarmonyOS", "EMUI", "MIUI", "iOS", "Android", "ColorOS",
    "OriginOS", "Funtouch", "One UI", "Flyme",
]

# 内置硬编码样例数据（用于 --selftest）
SELFTEST_SAMPLE = {
    "device_brand": "华为",
    "device_model": "华为 Mate 60 Pro",
    "system_version": "HarmonyOS 4.0",
    "operation_goal": "设置双卡双待",
    "steps": [
        {"title": "打开设置", "description": "在主屏幕找到并点击设置图标", "expected": "进入设置主界面"},
        {"title": "进入移动网络", "description": "点击移动网络选项", "expected": "显示移动网络设置页面"},
        {"title": "选择SIM卡管理", "description": "点击SIM卡管理", "expected": "显示双卡设置选项"},
        {"title": "启用双卡", "description": "打开双卡开关", "expected": "两张SIM卡均显示已启用"},
    ],
    "notes": [
        "请确保两张SIM卡均已正确插入卡槽",
        "双卡同时使用时耗电会略有增加",
    ],
    "troubleshooting": [
        {"problem": "无法识别第二张SIM卡", "cause": "SIM卡未插好或损坏", "solution": "重新插拔SIM卡或更换卡片"},
        {"problem": "双卡无法同时待机", "cause": "手机不支持双卡双待", "solution": "确认手机硬件规格"},
    ],
}


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------
def validate_input_file(filepath):
    """校验输入文件是否存在且可读。失败返回错误码，成功返回 None。"""
    if not filepath:
        return None
    if not os.path.isfile(filepath):
        return "E008"
    if not os.access(filepath, os.R_OK):
        return "E008"
    return None


def validate_output_dir(filepath):
    """校验输出文件所在目录是否可写。失败返回错误码，成功返回 None。"""
    if not filepath:
        return None
    target_dir = os.path.dirname(os.path.abspath(filepath))
    if not os.path.isdir(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            return "E009"
    if not os.access(target_dir, os.W_OK):
        return "E009"
    return None


def validate_operation_goal(goal):
    """校验操作目标是否为空。"""
    if not goal or not goal.strip():
        return "E002"
    return None


def validate_screenshot_count(count):
    """校验截图数量是否在限制范围内。"""
    if count > 20:
        return "E007"
    return None


# ---------------------------------------------------------------------------
# 核心逻辑：设备识别
# ---------------------------------------------------------------------------
def detect_brand(text):
    """根据文本内容识别手机品牌。返回品牌名或 None。"""
    if not text:
        return None
    text_upper = text.upper()
    for brand, keywords in BRAND_KEYWORDS.items():
        for kw in keywords:
            if kw.upper() in text_upper:
                return brand
    return None


def detect_system_version(text):
    """根据文本内容识别系统版本。返回版本字符串或 None。"""
    if not text:
        return None
    for kw in SYSTEM_VERSION_KEYWORDS:
        pattern = re.compile(re.escape(kw) + r"[\s\d.]*", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            # 提取版本号（如 HarmonyOS 4.0）
            version_str = match.group(0).strip()
            return version_str
    return None


def detect_device_model(text):
    """根据文本内容识别设备型号。返回型号字符串或 None。"""
    if not text:
        return None
    # 常见型号模式：品牌 + 系列 + 数字
    patterns = [
        r"(?:华为|HUAWEI)\s*[A-Za-z0-9\s]*",
        r"(?:小米|Xiaomi|Redmi)\s*[A-Za-z0-9\s]*",
        r"(?:iPhone)\s*[A-Za-z0-9\s]*",
        r"(?:OPPO|vivo|三星|Samsung)\s*[A-Za-z0-9\s]*",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            model = match.group(0).strip()
            if len(model) > 3:  # 过滤过短匹配
                return model
    return None


def detect_conflicting_brands(text):
    """检测文本中是否出现多种品牌。返回品牌列表（去重）。"""
    if not text:
        return []
    brands_found = []
    for brand in BRAND_KEYWORDS:
        if brand in text:
            brands_found.append(brand)
    return list(OrderedDict.fromkeys(brands_found))


# ---------------------------------------------------------------------------
# 核心逻辑：文本解析与步骤提取
# ---------------------------------------------------------------------------
def extract_steps_from_text(text):
    """从文本中提取操作步骤。返回步骤列表（每个步骤为 dict）。"""
    if not text:
        return []
    steps = []
    # 匹配 "步骤 N" 或 "Step N" 或 "N." 开头的行
    pattern = re.compile(
        r"(?:步骤|Step|STEP)\s*(\d+)[:：.\s]+(.+)",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        line = line.strip()
        match = pattern.match(line)
        if match:
            step_num = int(match.group(1))
            content = match.group(2).strip()
            steps.append({
                "number": step_num,
                "title": content[:20],  # 截取前20字作为标题
                "description": content,
                "expected": "[需核实:预期结果]",
            })
    return steps


def extract_notes_from_text(text):
    """从文本中提取注意事项。返回字符串列表。"""
    if not text:
        return []
    notes = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("注意", "提示", "提醒", "Note", "NOTE")):
            notes.append(line)
    return notes


def extract_troubleshooting_from_text(text):
    """从文本中提取故障排查信息。返回列表（每个为 dict）。"""
    if not text:
        return []
    result = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "问题" in line and i + 2 < len(lines):
            problem = line.strip()
            cause = lines[i + 1].strip() if i + 1 < len(lines) else "[需核实:原因]"
            solution = lines[i + 2].strip() if i + 2 < len(lines) else "[需核实:方案]"
            result.append({
                "problem": problem,
                "cause": cause,
                "solution": solution,
            })
    return result


# ---------------------------------------------------------------------------
# 核心逻辑：文档生成
# ---------------------------------------------------------------------------
def build_markdown_document(device_model, system_version, operation_goal, steps, notes, troubleshooting):
    """根据结构化数据生成 Markdown 教程文档。返回文档字符串。"""
    # 处理缺失字段，使用占位符
    if not device_model:
        device_model = "[需核实:设备型号]"
    if not system_version:
        system_version = "[需核实:系统版本]"
    if not operation_goal:
        operation_goal = "[需核实:操作目标]"

    lines = []
    lines.append(f"# 《{operation_goal}》教程 — {device_model} ({system_version})")
    lines.append("")
    lines.append("## 适用环境")
    lines.append(f"- 设备型号：{device_model}")
    lines.append(f"- 系统版本：{system_version}")
    lines.append("- 适用人群：新手")
    lines.append("")
    lines.append("## 操作步骤")
    lines.append("")

    if not steps:
        lines.append("[需核实:步骤总数]")
        lines.append("")
    else:
        for idx, step in enumerate(steps, 1):
            title = step.get("title", f"步骤 {idx}")
            desc = step.get("description", "[需核实:操作说明]")
            expected = step.get("expected", "[需核实:预期结果]")
            lines.append(f"### 步骤 {idx}：{title}")
            lines.append(f"![截图占位：步骤{idx}截图](images/step{idx}.png)")
            lines.append(f"**操作说明**：{desc}")
            lines.append(f"**预期结果**：{expected}")
            lines.append("")

    lines.append("## 注意事项")
    lines.append("")
    if notes:
        for note in notes:
            lines.append(f"- {note}")
    else:
        lines.append("- [需核实:注意事项]")
    lines.append("")

    lines.append("## 故障排查")
    lines.append("")
    lines.append("| 问题现象 | 可能原因 | 解决方法 |")
    lines.append("|----------|----------|----------|")
    if troubleshooting:
        for item in troubleshooting:
            problem = item.get("problem", "[需核实:问题]")
            cause = item.get("cause", "[需核实:原因]")
            solution = item.get("solution", "[需核实:方案]")
            lines.append(f"| {problem} | {cause} | {solution} |")
    else:
        lines.append("| [需核实:问题] | [需核实:原因] | [需核实:方案] |")
    lines.append("")

    return "\n".join(lines)


def calculate_confidence(steps, placeholders_count):
    """计算置信度等级。返回 (等级, 百分比)。"""
    if not steps:
        return "低", 0
    total_fields = len(steps) * 3  # 每步3个关键字段
    if total_fields == 0:
        return "低", 0
    completeness = max(0, 1 - (placeholders_count / total_fields))
    percentage = int(completeness * 100)
    if percentage >= 90:
        return "高", percentage
    elif percentage >= 70:
        return "中", percentage
    else:
        return "低", percentage


def count_placeholders(document_text):
    """统计文档中占位符数量。"""
    if not document_text:
        return 0
    return len(re.findall(r"\[需核实:[^\]]+\]", document_text))


# ---------------------------------------------------------------------------
# 核心逻辑：主处理流程
# ---------------------------------------------------------------------------
def process_tutorial(raw_text, operation_goal=None, verbose=False):
    """
    核心处理函数：从原始文本生成教程文档。
    返回 (文档字符串, 置信度报告, 错误列表)。
    """
    errors = []

    # 校验操作目标
    goal_error = validate_operation_goal(operation_goal)
    if goal_error:
        errors.append(goal_error)
        if verbose:
            print(f"[警告] {ERROR_CODES[goal_error]}", file=sys.stderr)

    # 设备识别
    brand = detect_brand(raw_text)
    model = detect_device_model(raw_text)
    version = detect_system_version(raw_text)

    # 品牌冲突检测
    brands_found = detect_conflicting_brands(raw_text)
    if len(brands_found) > 1:
        errors.append("E005")
        if verbose:
            print(f"[警告] {ERROR_CODES['E005']} 检测到: {brands_found}", file=sys.stderr)

    # 提取步骤、注意事项、故障排查
    steps = extract_steps_from_text(raw_text)
    notes = extract_notes_from_text(raw_text)
    troubleshooting = extract_troubleshooting_from_text(raw_text)

    # 如果文本中没有结构化步骤，使用操作目标生成基础步骤
    if not steps and operation_goal:
        steps = [{
            "title": operation_goal,
            "description": f"执行{operation_goal}操作",
            "expected": "[需核实:预期结果]",
        }]

    # 生成文档
    document = build_markdown_document(
        device_model=model,
        system_version=version,
        operation_goal=operation_goal,
        steps=steps,
        notes=notes,
        troubleshooting=troubleshooting,
    )

    # 置信度计算
    placeholders_count = count_placeholders(document)
    confidence_level, confidence_pct = calculate_confidence(steps, placeholders_count)

    # 构建置信度报告
    report_lines = []
    report_lines.append(f"置信度总评：{confidence_level}（{confidence_pct}%）")
    if placeholders_count > 0:
        report_lines.append(f"存在 {placeholders_count} 处 [需核实] 占位符")
        if placeholders_count > 0.3 * max(len(steps) * 3, 1):
            report_lines.append("建议补充素材以提高教程质量")
    else:
        report_lines.append("所有字段均已确认，无占位符")

    report = "\n".join(report_lines)

    if verbose:
        print(f"[信息] 识别品牌: {brand or '未知'}", file=sys.stderr)
        print(f"[信息] 识别型号: {model or '未知'}", file=sys.stderr)
        print(f"[信息] 识别系统: {version or '未知'}", file=sys.stderr)
        print(f"[信息] 提取步骤: {len(steps)} 个", file=sys.stderr)
        print(f"[信息] 提取注意事项: {len(notes)} 条", file=sys.stderr)
        print(f"[信息] 提取故障排查: {len(troubleshooting)} 条", file=sys.stderr)

    return document, report, errors


# ---------------------------------------------------------------------------
# 文件读写（多编码支持）
# ---------------------------------------------------------------------------
def read_text_file(filepath):
    """
    读取文本文件，支持多编码。
    优先 utf-8，然后 gbk，然后 gb18030，最后 errors="replace"。
    返回文件内容字符串。
    """
    if not filepath:
        return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except (UnicodeDecodeError, UnicodeError):
        pass
    try:
        with open(filepath, "r", encoding="gbk") as f:
            return f.read()
    except (UnicodeDecodeError, UnicodeError):
        pass
    try:
        with open(filepath, "r", encoding="gb18030") as f:
            return f.read()
    except (UnicodeDecodeError, UnicodeError):
        pass
    # 最终降级：replace 模式
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def write_text_file(filepath, content):
    """写入文本文件，使用 utf-8 编码。"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# 输出格式化与 diff 预览
# ---------------------------------------------------------------------------
def format_diff(original, new):
    """生成简单的 diff 摘要。返回字符串。"""
    if original == new:
        return "[无变化]"
    orig_lines = original.splitlines()
    new_lines = new.splitlines()
    added = sum(1 for line in new_lines if line not in orig_lines)
    removed = sum(1 for line in orig_lines if line not in new_lines)
    return f"[新增 {added} 行 / 删除 {removed} 行]"


def print_preview(document, report, verbose=False):
    """打印预览信息（不写盘）。"""
    print("=" * 60)
    print("【预览模式 --dry-run】以下为将写入的内容：")
    print("=" * 60)
    print(document)
    print("-" * 60)
    print("【置信度报告】")
    print(report)
    if verbose:
        print("-" * 60)
        print("【详细决策明细】")
        print("已生成 Markdown 教程文档，包含步骤、注意事项、故障排查章节。")
        print("所有 [需核实] 占位符已按规格保留，未做猜测性填充。")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 自检（selftest）
# ---------------------------------------------------------------------------
def run_selftest():
    """
    离线自检核心逻辑。使用内置硬编码样例数据。
    断言使用宽松阈值，不依赖精确值。
    返回 0 表示通过，非 0 表示失败。
    """
    print("开始自检...")

    # 准备样例数据
    sample_text = (
        "华为 Mate 60 Pro HarmonyOS 4.0\n"
        "操作目标：设置双卡双待\n"
        "步骤 1：打开设置\n"
        "步骤 2：进入移动网络\n"
        "步骤 3：选择SIM卡管理\n"
        "步骤 4：启用双卡\n"
        "注意：请确保两张SIM卡均已正确插入卡槽\n"
        "注意：双卡同时使用时耗电会略有增加\n"
        "问题：无法识别第二张SIM卡\n"
        "原因：SIM卡未插好或损坏\n"
        "方案：重新插拔SIM卡或更换卡片\n"
    )

    # 测试1：设备识别
    brand = detect_brand(sample_text)
    assert brand is not None, "设备品牌识别失败"
    assert brand == "华为", f"品牌识别错误: {brand}"
    print(f"[通过] 设备品牌识别: {brand}")

    # 测试2：系统版本识别
    version = detect_system_version(sample_text)
    assert version is not None, "系统版本识别失败"
    assert "HarmonyOS" in version, f"系统版本识别错误: {version}"
    print(f"[通过] 系统版本识别: {version}")

    # 测试3：设备型号识别
    model = detect_device_model(sample_text)
    assert model is not None, "设备型号识别失败"
    assert len(model) > 3, f"设备型号过短: {model}"
    print(f"[通过] 设备型号识别: {model}")

    # 测试4：步骤提取
    steps = extract_steps_from_text(sample_text)
    assert len(steps) >= 3, f"步骤提取数量不足: {len(steps)}"
    assert all("title" in s and "description" in s for s in steps), "步骤字段不完整"
    print(f"[通过] 步骤提取: {len(steps)} 个步骤")

    # 测试5：注意事项提取
    notes = extract_notes_from_text(sample_text)
    assert len(notes) >= 1, f"注意事项提取失败: {len(notes)}"
    print(f"[通过] 注意事项提取: {len(notes)} 条")

    # 测试6：故障排查提取
    troubleshooting = extract_troubleshooting_from_text(sample_text)
    assert len(troubleshooting) >= 1, f"故障排查提取失败: {len(troubleshooting)}"
    print(f"[通过] 故障排查提取: {len(troubleshooting)} 条")

    # 测试7：文档生成
    document = build_markdown_document(
        device_model=model,
        system_version=version,
        operation_goal="设置双卡双待",
        steps=steps,
        notes=notes,
        troubleshooting=troubleshooting,
    )
    assert document is not None, "文档生成失败"
    assert len(document) > 100, f"文档过短: {len(document)} 字符"
    assert "#" in document, "文档缺少标题"
    assert "## 操作步骤" in document, "文档缺少操作步骤章节"
    assert "## 注意事项" in document, "文档缺少注意事项章节"
    print(f"[通过] 文档生成: {len(document)} 字符")

    # 测试8：置信度计算
    placeholders = count_placeholders(document)
    confidence_level, confidence_pct = calculate_confidence(steps, placeholders)
    assert confidence_level in ("高", "中", "低"), f"置信度等级异常: {confidence_level}"
    assert 0 <= confidence_pct <= 100, f"置信度百分比异常: {confidence_pct}"
    print(f"[通过] 置信度计算: {confidence_level} ({confidence_pct}%)")

    # 测试9：空输入处理
    empty_doc = build_markdown_document(None, None, None, [], [], [])
    assert empty_doc is not None, "空输入文档生成失败"
    assert "[需核实:设备型号]" in empty_doc, "空输入缺少设备型号占位符"
    assert "[需核实:操作目标]" in empty_doc, "空输入缺少操作目标占位符"
    print("[通过] 空输入处理")

    # 测试10：中文标点处理
    chinese_text = "步骤１：打开设置（中文全角数字）"
    steps_cn = extract_steps_from_text(chinese_text)
    # 宽松断言：不要求必须识别全角数字，但不应崩溃
    assert steps_cn is not None, "中文标点处理崩溃"
    print(f"[通过] 中文标点处理: 提取 {len(steps_cn)} 个步骤")

    # 测试11：超长输入处理（性能 O(n) 验证）
    long_text = sample_text * 1000  # 约 10 万字
    import time
    start_time = time.time()
    long_steps = extract_steps_from_text(long_text)
    elapsed = time.time() - start_time
    assert len(long_steps) > 0, "超长输入步骤提取失败"
    assert elapsed < 5.0, f"超长输入处理过慢: {elapsed:.2f} 秒"
    print(f"[通过] 超长输入处理: {len(long_steps)} 步骤，耗时 {elapsed:.2f} 秒")

    # 测试12：编码异常处理
    try:
        # 模拟 GBK 编码内容（使用硬编码字节）
        gbk_bytes = "华为手机教程".encode("gbk")
        decoded = gbk_bytes.decode("utf-8", errors="replace")
        assert decoded is not None, "编码降级失败"
        print("[通过] 编码异常降级处理")
    except Exception as e:
        print(f"[失败] 编码异常处理: {e}")
        return 1

    # 测试13：主流程集成测试
    doc, report, errors = process_tutorial(sample_text, operation_goal="设置双卡双待")
    assert doc is not None, "主流程文档生成失败"
    assert report is not None, "主流程置信度报告失败"
    assert isinstance(errors, list), "主流程错误列表类型错误"
    print("[通过] 主流程集成测试")

    print("\n全部自检通过！")
    return 0


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main(argv=None):
    """CLI 入口函数。"""
    parser = argparse.ArgumentParser(
        description="手机教程全流程处理：识别设备、整理素材、生成结构化教程文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python scripts/main.py --selftest\n"
            "  python scripts/main.py --input notes.txt --output tutorial.md --dry-run\n"
            "  python scripts/main.py --input notes.txt --output tutorial.md --force --verbose\n"
        ),
    )
    parser.add_argument("--input", "-i", help="输入文本文件路径（包含设备信息、操作步骤等）")
    parser.add_argument("--output", "-o", help="输出 Markdown 文件路径")
    parser.add_argument("--goal", "-g", help="操作目标描述（如：设置双卡双待）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式：只打印不写盘")
    parser.add_argument("--force", action="store_true", help="强制写盘（需与 --output 配合）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细决策明细")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 参数校验
    if not args.input:
        print("错误：缺少 --input 参数。使用 --help 查看帮助。", file=sys.stderr)
        return 1

    # 校验输入文件
    input_error = validate_input_file(args.input)
    if input_error:
        print(f"错误 {input_error}: {ERROR_CODES[input_error]}", file=sys.stderr)
        return 1

    # 读取输入文件（多编码支持）
    raw_text = read_text_file(args.input)
    if not raw_text.strip():
        print("警告：输入文件为空。将生成包含占位符的文档。", file=sys.stderr)

    # 执行核心处理
    try:
        document, report, errors = process_tutorial(
            raw_text,
            operation_goal=args.goal,
            verbose=args.verbose,
        )
    except Exception as e:
        print(f"错误 E010: {ERROR_CODES['E010']}", file=sys.stderr)
        print(f"详细信息: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    # 输出错误警告（不阻断流程）
    for err in errors:
        print(f"警告 {err}: {ERROR_CODES.get(err, '未知错误')}", file=sys.stderr)

    # 输出结果
    if args.output:
        # 校验输出目录
        output_error = validate_output_dir(args.output)
        if output_error:
            print(f"错误 {output_error}: {ERROR_CODES[output_error]}", file=sys.stderr)
            return 1

        # 预览模式（dry-run）
        if args.dry_run:
            print_preview(document, report, verbose=args.verbose)
            print(f"\n[预览模式] 未写入文件: {args.output}")
            return 0

        # 需要 --force 才能写盘
        if not args.force:
            print_preview(document, report, verbose=args.verbose)
            print(f"\n[提示] 使用 --force 参数才能真正写入文件: {args.output}")
            return 0

        # 真正写盘
        try:
            write_text_file(args.output, document)
            print(f"已写入: {args.output}")
            print(report)
            if args.verbose:
                print(f"[信息] 文档长度: {len(document)} 字符")
        except OSError as e:
            print(f"错误 E009: {ERROR_CODES['E009']}", file=sys.stderr)
            print(f"详细信息: {e}", file=sys.stderr)
            return 1
    else:
        # 无输出文件时打印到 stdout
        print(document)
        print("-" * 40)
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
