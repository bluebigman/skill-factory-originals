#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docspect — 合同审查与风险提示工具（独立实现）

功能：
  1. 解析合同文本，提取关键字段（主体、标的、金额、期限、违约责任等）
  2. 识别 12 类常见风险条款，并给出置信度（高/中/低）
  3. 输出 Markdown 格式的结构化审查报告

用法：
  python main.py <file_or_text> [--output report.md] [--batch file1 file2 ...]
  python main.py --selftest

错误码：
  E001 参数错误
  E002 文件不存在
  E003 文件过大（>2MB）
  E004 不支持的文件类型
  E005 文本过长（>50,000字符）
  E006 网络访问失败（备用，当前未实现）
  E007 批量处理文件数超限（>5）
  E008 输入内容为空
  E009 内部处理异常
  E010 输出文件写入失败
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 2 * 1024 * 1024       # 2MB
MAX_TEXT_LENGTH = 50000               # 50,000 字符
MAX_BATCH_FILES = 5                   # 最多 5 个文件
SUPPORTED_EXT = {".txt", ".md", ".pdf", ".docx"}

# 风险条款关键词库（12 类）
RISK_PATTERNS = {
    "单方解除权": {
        "keywords": ["单方解除", "任意解除", "随时解除", "单方终止"],
        "suggestion": "建议将单方解除权限制为特定情形，并约定提前通知期限。"
    },
    "违约金过高": {
        "keywords": ["违约金", "赔偿金", "罚金"],
        "suggestion": "违约金建议不超过实际损失的30%，避免被法院调减。"
    },
    "免责条款过宽": {
        "keywords": ["免责", "不承担责任", "免除责任", "概不负责"],
        "suggestion": "建议明确免责范围，排除故意或重大过失情形。"
    },
    "知识产权归属不明": {
        "keywords": ["知识产权", "著作权", "专利权", "商标权"],
        "suggestion": "建议明确约定知识产权归属及使用许可范围。"
    },
    "保密义务缺失": {
        "keywords": ["保密", "机密", "不得披露"],
        "suggestion": "建议补充保密条款，明确保密期限和违约责任。"
    },
    "自动续约条款": {
        "keywords": ["自动续约", "自动续期", "自动延长"],
        "suggestion": "建议约定续约前书面通知期，避免被动续约。"
    },
    "管辖法院单方指定": {
        "keywords": ["管辖", "诉讼地", "仲裁地"],
        "suggestion": "建议约定双方协商一致的管辖法院或仲裁机构。"
    },
    "付款条件苛刻": {
        "keywords": ["预付", "全款", "一次性支付", "货到付款"],
        "suggestion": "建议分阶段付款，降低资金风险。"
    },
    "交付标准模糊": {
        "keywords": ["交付", "验收", "合格标准"],
        "suggestion": "建议明确交付物内容、验收标准和验收期限。"
    },
    "不可抗力定义狭窄": {
        "keywords": ["不可抗力", "免责事由"],
        "suggestion": "建议扩大不可抗力定义范围，包含常见例外情形。"
    },
    "限制竞争条款": {
        "keywords": ["竞业限制", "不得竞争", "禁止竞争"],
        "suggestion": "建议审查竞业限制的范围、期限和补偿金。"
    },
    "数据隐私条款缺失": {
        "keywords": ["个人信息", "数据保护", "隐私"],
        "suggestion": "建议补充数据保护条款，明确数据使用范围。"
    },
}

# 关键字段提取正则
FIELD_PATTERNS = {
    "甲方": r"甲方[：:]\s*([^\n，。；;]{2,50})",
    "乙方": r"乙方[：:]\s*([^\n，。；;]{2,50})",
    "合同金额": r"(?:合同金额|总金额|价款)[：:]\s*([^\n，。；;]{2,50})",
    "合同期限": r"(?:合同期限|有效期|期限)[：:]\s*([^\n，。；;]{2,50})",
    "签订日期": r"(?:签订日期|签署日期|日期)[：:]\s*([^\n，。；;]{2,50})",
}

# 置信度阈值（宽松判断）
HIGH_CONF_THRESHOLD = 3     # 命中 >=3 个关键词 → 高
MED_CONF_THRESHOLD = 2      # 命中 >=2 个关键词 → 中
# 低于 MED → 低


# ---------------------------------------------------------------------------
# 核心逻辑
# ---------------------------------------------------------------------------
def validate_input(text: str) -> None:
    """校验输入文本有效性，出错抛 ValueError（带错误码）。"""
    if not text or not text.strip():
        raise ValueError("E008: 输入内容为空")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError("E005: 文本长度超过 50,000 字符限制")


def extract_key_fields(text: str) -> dict:
    """提取合同关键字段。"""
    fields = {}
    for field_name, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, text)
        if match:
            fields[field_name] = match.group(1).strip()
    return fields


def detect_risks(text: str) -> list:
    """识别风险条款，返回 [{type, confidence, suggestion, evidence}]。"""
    risks = []
    for risk_type, info in RISK_PATTERNS.items():
        hits = []
        for keyword in info["keywords"]:
            if keyword in text:
                hits.append(keyword)

        if not hits:
            continue

        # 置信度：宽松判断
        hit_count = len(hits)
        if hit_count >= HIGH_CONF_THRESHOLD:
            confidence = "高"
        elif hit_count >= MED_CONF_THRESHOLD:
            confidence = "中"
        else:
            confidence = "低"

        # 提取上下文作为证据（前后各 20 字符）
        first_hit_pos = text.find(hits[0])
        start = max(0, first_hit_pos - 20)
        end = min(len(text), first_hit_pos + len(hits[0]) + 20)
        evidence = text[start:end].replace("\n", " ").strip()

        risks.append({
            "type": risk_type,
            "confidence": confidence,
            "suggestion": info["suggestion"],
            "evidence": evidence,
            "hit_keywords": hits,
        })

    # 按置信度排序（高 > 中 > 低）
    conf_order = {"高": 0, "中": 1, "低": 2}
    risks.sort(key=lambda x: conf_order.get(x["confidence"], 3))
    return risks


def generate_markdown_report(text: str) -> str:
    """生成 Markdown 格式审查报告。"""
    validate_input(text)

    # 提取字段与风险
    fields = extract_key_fields(text)
    risks = detect_risks(text)

    # 合同概要
    lines = []
    lines.append("# 合同审查报告\n")
    lines.append("## 一、合同概要\n")
    if fields:
        for key, value in fields.items():
            lines.append(f"- **{key}**：{value}")
    else:
        lines.append("- 未能自动提取关键字段（请手动核对）")
    lines.append("")

    # 关键条款清单（从字段中推断）
    lines.append("## 二、关键条款清单\n")
    if fields:
        for key in fields:
            lines.append(f"- {key}")
    else:
        lines.append("- 未识别到关键条款")
    lines.append("")

    # 风险条款列表
    lines.append("## 三、风险条款列表\n")
    if risks:
        for i, risk in enumerate(risks, 1):
            lines.append(f"### {i}. {risk['type']}（置信度：{risk['confidence']}）")
            lines.append(f"- 命中关键词：{'、'.join(risk['hit_keywords'])}")
            lines.append(f"- 参考上下文：…{risk['evidence']}…")
            lines.append(f"- 修改建议：{risk['suggestion']}")
            lines.append("")
    else:
        lines.append("- 未识别到明显风险条款")
        lines.append("")

    # 免责声明
    lines.append("---")
    lines.append("> ⚠️ 本报告由 AI 自动生成，仅供一般信息参考，不构成法律意见。")
    lines.append("> 涉及合同签署等专业决策时，请务必咨询持证专业人士。")
    lines.append("")

    return "\n".join(lines)


def process_file(file_path: str) -> str:
    """处理单个文件，返回 Markdown 报告。"""
    path = Path(file_path)

    # 检查文件是否存在
    if not path.is_file():
        raise FileNotFoundError(f"E002: 文件不存在 — {file_path}")

    # 检查文件大小
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"E003: 文件超过 2MB 限制 — {file_path} ({file_size} bytes)")

    # 检查扩展名
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise ValueError(f"E004: 不支持的文件类型 — {ext}（仅支持 {SUPPORTED_EXT}）")

    # 读取文本（PDF/DOCX 需额外处理，此处简化）
    try:
        if ext in {".txt", ".md"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
        else:
            # PDF/DOCX 需要第三方库，此处给出提示
            raise ValueError(
                f"E004: 当前实现仅支持 .txt/.md 文件，{ext} 需安装额外依赖 "
                "（# pip install pypdf python-docx）"
            )
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"E009: 文件读取失败 — {exc}") from exc

    return generate_markdown_report(content)


def process_batch(file_paths: list) -> dict:
    """批量处理多个文件，返回 {文件名: 报告}。"""
    if len(file_paths) > MAX_BATCH_FILES:
        raise ValueError(f"E007: 批量处理文件数超过 {MAX_BATCH_FILES} 个限制")

    results = {}
    for f in file_paths:
        results[f] = process_file(f)
    return results


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def selftest() -> None:
    """内置硬编码样例数据自检核心逻辑，不依赖外部文件。"""
    print("=" * 60)
    print("docspect 自检开始")
    print("=" * 60)

    # 硬编码测试样例
    sample_text = """
    甲方：北京某科技有限公司
    乙方：上海某软件服务有限公司
    合同金额：人民币 500,000 元
    合同期限：自 2026 年 1 月 1 日起至 2026 年 12 月 31 日
    签订日期：2025 年 12 月 15 日

    第一条 甲方有权随时单方解除本合同，无需提前通知乙方。
    第二条 如乙方违约，需支付违约金，金额为合同总额的 50%。
    第三条 甲方对因使用本软件导致的任何损失概不负责，包括但不限于数据丢失。
    第四条 乙方开发的软件知识产权归甲方所有，乙方不得主张任何权利。
    第五条 双方应对合作内容保密，任何一方不得向第三方披露。
    第六条 本合同到期后自动续约一年，除非任一方提前 30 天书面通知终止。
    第七条 因本合同引起的争议，由甲方所在地人民法院管辖。
    第八条 乙方需在合同签订后 3 日内一次性支付全部款项。
    第九条 乙方交付的软件应符合甲方验收标准，具体标准另行协商。
    第十条 因不可抗力导致无法履行合同的，双方互不承担责任，不可抗力仅指自然灾害。
    第十一条 乙方在合同期满后 2 年内不得从事与甲方相竞争的业务。
    第十二条 甲方有权收集乙方员工的个人信息用于市场分析。
    """

    # 测试 1：字段提取
    print("\n[1/4] 测试字段提取...")
    fields = extract_key_fields(sample_text)
    assert "甲方" in fields, "E009: 甲方字段未提取"
    assert "乙方" in fields, "E009: 乙方字段未提取"
    assert "合同金额" in fields, "E009: 金额字段未提取"
    assert "合同期限" in fields, "E009: 期限字段未提取"
    assert "签订日期" in fields, "E009: 日期字段未提取"
    print("  ✓ 关键字段提取正常")
    print(f"    提取结果: {fields}")

    # 测试 2：风险检测
    print("\n[2/4] 测试风险检测...")
    risks = detect_risks(sample_text)
    assert len(risks) >= 5, f"E009: 风险识别数量偏少，仅 {len(risks)} 条"
    risk_types = [r["type"] for r in risks]
    for expected in ["单方解除权", "违约金过高", "免责条款过宽", "知识产权归属不明", "自动续约条款"]:
        assert expected in risk_types, f"E009: 未识别到风险类型 {expected}"
    # 置信度检查（宽松）
    for r in risks:
        assert r["confidence"] in {"高", "中", "低"}, f"E009: 非法置信度 {r['confidence']}"
        assert r["suggestion"], "E009: 缺少修改建议"
        assert r["evidence"], "E009: 缺少证据上下文"
    print(f"  ✓ 风险检测正常，共识别 {len(risks)} 条风险")
    for r in risks[:3]:
        print(f"    - {r['type']} [{r['confidence']}]")

    # 测试 3：报告生成
    print("\n[3/4] 测试报告生成...")
    report = generate_markdown_report(sample_text)
    assert "# 合同审查报告" in report, "E009: 报告缺少标题"
    assert "## 一、合同概要" in report, "E009: 报告缺少概要章节"
    assert "## 二、关键条款清单" in report, "E009: 报告缺少条款清单"
    assert "## 三、风险条款列表" in report, "E009: 报告缺少风险列表"
    assert "免责" in report or "不构成法律意见" in report, "E009: 报告缺少免责声明"
    print("  ✓ 报告生成正常")
    print(f"    报告长度: {len(report)} 字符")

    # 测试 4：边界与错误处理
    print("\n[4/4] 测试边界与错误处理...")
    # 空输入
    try:
        generate_markdown_report("")
        assert False, "E009: 空输入未报错"
    except ValueError as exc:
        assert "E008" in str(exc), f"E009: 错误码不正确 — {exc}"
    print("  ✓ 空输入错误处理正常")

    # 超长输入
    try:
        generate_markdown_report("a" * (MAX_TEXT_LENGTH + 1))
        assert False, "E009: 超长输入未报错"
    except ValueError as exc:
        assert "E005" in str(exc), f"E009: 错误码不正确 — {exc}"
    print("  ✓ 超长输入错误处理正常")

    # 批量超限
    try:
        process_batch(["a.txt"] * (MAX_BATCH_FILES + 1))
        assert False, "E009: 批量超限未报错"
    except ValueError as exc:
        assert "E007" in str(exc), f"E009: 错误码不正确 — {exc}"
    print("  ✓ 批量超限错误处理正常")

    # 文件不存在
    try:
        process_file("/nonexistent/path/file.txt")
        assert False, "E009: 文件不存在未报错"
    except FileNotFoundError as exc:
        assert "E002" in str(exc), f"E009: 错误码不正确 — {exc}"
    print("  ✓ 文件不存在错误处理正常")

    print("\n" + "=" * 60)
    print("✅ 自检全部通过")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="docspect — 合同审查与风险提示工具",
        epilog="示例: python main.py contract.txt --output report.md",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="输入文件路径或合同文本（文件优先）",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="输出报告文件路径（默认 stdout）",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        help="批量处理多个文件（最多 5 个）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不依赖外部文件）",
    )
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            selftest()
            sys.exit(0)
        except AssertionError as exc:
            print(f"E009: 自检失败 — {exc}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"E009: 自检异常 — {exc}", file=sys.stderr)
            sys.exit(1)

    # 参数校验
    if not args.input and not args.batch:
        parser.error("E001: 必须提供输入文件、文本或 --batch 参数")

    try:
        # 批量处理
        if args.batch:
            results = process_batch(args.batch)
            output_lines = []
            for fname, report in results.items():
                output_lines.append(f"<!-- 文件: {fname} -->")
                output_lines.append(report)
                output_lines.append("")
            output_text = "\n".join(output_lines)
        else:
            # 单文件/文本处理
            path = Path(args.input)
            if path.is_file():
                output_text = process_file(args.input)
            else:
                # 视为直接粘贴的文本
                output_text = generate_markdown_report(args.input)

        # 输出
        if args.output:
            try:
                Path(args.output).write_text(output_text, encoding="utf-8")
                print(f"报告已写入: {args.output}")
            except Exception as exc:
                raise RuntimeError(f"E010: 输出文件写入失败 — {exc}") from exc
        else:
            print(output_text)

    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"E009: 未预期错误 — {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
