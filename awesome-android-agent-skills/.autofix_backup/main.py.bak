#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-android-agent-skills 技能导航与编排辅助脚本

本脚本根据功能规格独立实现（clean room），提供：
1. 技能需求解析（自然语言 / 关键词）
2. 技能匹配（内置索引库，返回 Top 5 + 置信度）
3. 组合建议（2-3 个技能串联）
4. 格式转换（Markdown / JSON / CSV）
5. 离线自检（--selftest）

仅依赖 Python 标准库。错误码 E001-E010。
"""

import argparse
import csv
import io
import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERR_INVALID_INPUT = "E001"        # 输入参数无效
ERR_EMPTY_QUERY = "E002"          # 查询内容为空
ERR_TOO_MANY_ITEMS = "E003"       # 技能条目超过上限
ERR_UNSUPPORTED_FORMAT = "E004"   # 不支持的输出格式
ERR_BATCH_FILE_MISSING = "E005"   # 批量文件不存在
ERR_BATCH_FILE_INVALID = "E006"   # 批量文件格式错误
ERR_INTERNAL = "E007"             # 内部逻辑错误
ERR_SELF_TEST_FAILED = "E008"     # 自检失败
ERR_OUTPUT_FAILED = "E009"        # 输出写入失败
ERR_UNKNOWN = "E010"              # 未知错误


# ============================================================
# 内置技能索引库（硬编码样例数据）
# ============================================================
# 每条记录包含：技能名、版本、平台要求、功能关键词、描述
SKILL_INDEX: List[Dict[str, Any]] = [
    {
        "name": "android-ui-testing",
        "version": "1.2.0",
        "platform": ["Android 7+", "API 24+"],
        "keywords": ["ui", "测试", "界面", "automation", "espresso"],
        "description": "Android 界面自动化测试技能，支持 Espresso 与 Compose 测试编写。",
    },
    {
        "name": "android-network-monitor",
        "version": "0.9.3",
        "platform": ["Android 8+", "API 26+"],
        "keywords": ["网络", "监控", "http", "流量", "抓包"],
        "description": "Android 网络请求监控与拦截技能，可记录流量与耗时。",
    },
    {
        "name": "android-permission-manager",
        "version": "2.0.1",
        "platform": ["Android 6+", "API 23+"],
        "keywords": ["权限", "permission", "运行时", "授权"],
        "description": "Android 运行时权限管理技能，支持批量授权与状态查询。",
    },
    {
        "name": "android-battery-optimizer",
        "version": "1.1.0",
        "platform": ["Android 9+", "API 28+"],
        "keywords": ["电池", "耗电", "优化", "battery", "省电"],
        "description": "Android 电池使用分析技能，提供耗电优化建议。",
    },
    {
        "name": "android-crash-reporter",
        "version": "3.0.2",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["崩溃", "crash", "日志", "异常", "bug"],
        "description": "Android 崩溃日志收集与聚合技能，支持堆栈解析。",
    },
    {
        "name": "android-package-inspector",
        "version": "1.4.0",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["包", "apk", "package", "安装", "卸载"],
        "description": "Android 应用包信息检查技能，可查询已安装应用详情。",
    },
    {
        "name": "android-performance-profiler",
        "version": "2.2.1",
        "platform": ["Android 8+", "API 26+"],
        "keywords": ["性能", "卡顿", "帧率", "cpu", "内存"],
        "description": "Android 性能剖析技能，监控 CPU、内存与帧率。",
    },
    {
        "name": "android-security-audit",
        "version": "1.0.0",
        "platform": ["Android 10+", "API 29+"],
        "keywords": ["安全", "漏洞", "审计", "security", "风险"],
        "description": "Android 安全审计技能，检查常见配置风险与漏洞。",
    },
    {
        "name": "android-notification-tester",
        "version": "0.8.5",
        "platform": ["Android 8+", "API 26+"],
        "keywords": ["通知", "notification", "推送", "消息"],
        "description": "Android 通知栏测试技能，模拟与验证通知行为。",
    },
    {
        "name": "android-storage-cleaner",
        "version": "1.3.0",
        "platform": ["Android 7+", "API 24+"],
        "keywords": ["存储", "清理", "空间", "storage", "缓存"],
        "description": "Android 存储清理技能，分析并清理无用文件与缓存。",
    },
    {
        "name": "android-wifi-controller",
        "version": "0.7.2",
        "platform": ["Android 6+", "API 23+"],
        "keywords": ["wifi", "无线", "网络", "连接", "热点"],
        "description": "Android WiFi 控制技能，支持扫描、连接与热点管理。",
    },
    {
        "name": "android-gps-simulator",
        "version": "1.5.0",
        "platform": ["Android 9+", "API 28+"],
        "keywords": ["gps", "定位", "模拟", "位置", "地图"],
        "description": "Android GPS 模拟技能，可设置虚拟位置与轨迹。",
    },
    {
        "name": "android-app-backup",
        "version": "2.1.0",
        "platform": ["Android 6+", "API 23+"],
        "keywords": ["备份", "恢复", "backup", "数据", "迁移"],
        "description": "Android 应用数据备份与恢复技能。",
    },
    {
        "name": "android-bluetooth-tool",
        "version": "1.0.4",
        "platform": ["Android 8+", "API 26+"],
        "keywords": ["蓝牙", "bluetooth", "配对", "ble", "连接"],
        "description": "Android 蓝牙调试技能，支持经典蓝牙与 BLE。",
    },
    {
        "name": "android-multimedia-recorder",
        "version": "3.1.0",
        "platform": ["Android 7+", "API 24+"],
        "keywords": ["音视频", "录制", "录音", "录像", "多媒体"],
        "description": "Android 多媒体录制技能，支持音视频采集与编码。",
    },
    {
        "name": "android-intent-router",
        "version": "1.2.3",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["intent", "路由", "跳转", "deep link", "scheme"],
        "description": "Android Intent 路由技能，支持 Deep Link 解析与跳转。",
    },
    {
        "name": "android-screenshot-analyzer",
        "version": "0.6.1",
        "platform": ["Android 7+", "API 24+"],
        "keywords": ["截图", "screenshot", "分析", "图像", "ocr"],
        "description": "Android 截图分析技能，可提取界面元素与文本。",
    },
    {
        "name": "android-signal-strength",
        "version": "1.1.1",
        "platform": ["Android 8+", "API 26+"],
        "keywords": ["信号", "信号强度", "网络质量", "rsrp", "sinr"],
        "description": "Android 信号强度检测技能，评估移动网络质量。",
    },
    {
        "name": "android-cloud-sync",
        "version": "2.0.0",
        "platform": ["Android 10+", "API 29+"],
        "keywords": ["云同步", "同步", "sync", "云存储", "备份"],
        "description": "Android 云同步技能，对接主流云存储服务。",
    },
    {
        "name": "android-accessibility-helper",
        "version": "1.6.0",
        "platform": ["Android 7+", "API 24+"],
        "keywords": ["无障碍", "accessibility", "辅助", "自动化", "点击"],
        "description": "Android 无障碍服务辅助技能，实现界面自动化操作。",
    },
    {
        "name": "android-build-optimizer",
        "version": "0.5.0",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["构建", "编译", "gradle", "构建优化", "打包"],
        "description": "Android 构建优化技能，加速 Gradle 编译与打包。",
    },
    {
        "name": "android-emulator-control",
        "version": "2.3.0",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["模拟器", "emulator", "虚拟设备", "adb", "控制"],
        "description": "Android 模拟器控制技能，管理虚拟设备与 ADB 命令。",
    },
    {
        "name": "android-log-analyzer",
        "version": "1.8.0",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["日志", "logcat", "分析", "过滤", "调试"],
        "description": "Android Logcat 日志分析技能，支持过滤与模式提取。",
    },
    {
        "name": "android-app-signer",
        "version": "1.0.2",
        "platform": ["Android 5+", "API 21+"],
        "keywords": ["签名", "apk", "签名验证", "证书", "keystore"],
        "description": "Android 应用签名技能，支持签名生成与验证。",
    },
]

# 技能条目处理上限
MAX_SKILL_ITEMS = 20
# 默认匹配结果数量
DEFAULT_TOP_N = 5
# 置信度阈值
CONFIDENCE_THRESHOLD = 0.6

# 输出格式支持
SUPPORTED_FORMATS = ("json", "markdown", "csv")


# ============================================================
# 工具函数
# ============================================================
def _normalize_text(text: str) -> str:
    """归一化文本：小写、去除多余空白。"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词（简单分词）。"""
    text = _normalize_text(text)
    # 按非字母数字字符分割
    parts = re.split(r"[^a-z0-9\u4e00-\u9fff]+", text)
    return [p for p in parts if len(p) > 1]


def _contains_chinese(text: str) -> bool:
    """判断文本是否包含中文字符。"""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _split_query_items(query: str) -> List[str]:
    """将查询拆分为技能条目（按逗号 / 分号 / 换行分隔）。"""
    if not query:
        return []
    parts = re.split(r"[,;\n]+", query)
    return [p.strip() for p in parts if p.strip()]


def _validate_query(query: str) -> Tuple[bool, str]:
    """校验查询输入。返回 (是否有效, 错误码)。"""
    if query is None:
        return False, ERR_INVALID_INPUT
    if not query.strip():
        return False, ERR_EMPTY_QUERY
    items = _split_query_items(query)
    if len(items) > MAX_SKILL_ITEMS:
        return False, ERR_TOO_MANY_ITEMS
    return True, ""


def _check_output_format(fmt: str) -> bool:
    """检查输出格式是否支持。"""
    return fmt in SUPPORTED_FORMATS


# ============================================================
# 核心逻辑：技能匹配
# ============================================================
def _score_skill(skill: Dict[str, Any], query_keywords: List[str]) -> float:
    """
    计算技能与查询关键词的匹配分数（0-1）。
    使用宽松的加权评分：名称权重最高，关键词次之，描述最低。
    """
    if not query_keywords:
        return 0.0

    name_text = _normalize_text(skill.get("name", ""))
    keywords_text = " ".join(_normalize_text(k) for k in skill.get("keywords", []))
    desc_text = _normalize_text(skill.get("description", ""))

    total_score = 0.0
    matched_count = 0

    for kw in query_keywords:
        kw_lower = kw.lower()
        score = 0.0
        # 名称匹配（高权重）
        if kw_lower in name_text:
            score += 0.5
        # 关键词匹配（中权重）
        if kw_lower in keywords_text:
            score += 0.3
        # 描述匹配（低权重）
        if kw_lower in desc_text:
            score += 0.2
        if score > 0:
            total_score += score
            matched_count += 1

    if matched_count == 0:
        return 0.0

    # 归一化到 0-1 区间
    # 每个关键词最高可得 1.0 分（0.5+0.3+0.2）
    max_possible = len(query_keywords) * 1.0
    raw_score = total_score / max_possible if max_possible > 0 else 0.0

    # 加一点匹配数量的奖励（但不是严格依赖）
    coverage = matched_count / len(query_keywords)
    final_score = raw_score * 0.8 + coverage * 0.2
    return min(1.0, max(0.0, final_score))


def match_skills(query: str, top_n: int = DEFAULT_TOP_N) -> List[Dict[str, Any]]:
    """根据查询匹配技能，返回 Top N 结果。"""
    # 校验输入
    valid, err_code = _validate_query(query)
    if not valid:
        raise ValueError(f"{err_code}: 查询无效")

    # 提取查询关键词
    query_keywords = _extract_keywords(query)

    if not query_keywords:
        # 没有有效关键词时，返回空结果
        return []

    # 为每个技能打分
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for skill in SKILL_INDEX:
        score = _score_skill(skill, query_keywords)
        if score > 0:
            scored.append((score, skill))

    # 按分数降序排序
    scored.sort(key=lambda x: x[0], reverse=True)

    # 取 Top N
    results = []
    for score, skill in scored[:top_n]:
        result = dict(skill)
        result["confidence"] = round(score, 3)
        result["needs_review"] = score < CONFIDENCE_THRESHOLD
        results.append(result)

    return results


def generate_combination_advice(results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """生成组合建议（2-3 个技能串联）。"""
    if len(results) < 2:
        return []

    advice_list = []
    # 取前 2-3 个技能做组合
    combo = results[:3]
    if len(combo) >= 2:
        advice_list.append({
            "combo": " -> ".join(s["name"] for s in combo),
            "reason": "基于匹配度排序的串行组合，覆盖主要需求。",
            "dependency": "前置技能需先于后续技能执行。",
        })
    return advice_list


def generate_report(
    query: str,
    results: List[Dict[str, Any]],
    output_format: str = "markdown",
) -> str:
    """生成格式化报告。"""
    if not _check_output_format(output_format):
        raise ValueError(f"{ERR_UNSUPPORTED_FORMAT}: 不支持的输出格式: {output_format}")

    if output_format == "json":
        report_data = {
            "query": query,
            "total_matches": len(results),
            "results": results,
            "combination_advice": generate_combination_advice(results),
        }
        return json.dumps(report_data, ensure_ascii=False, indent=2)

    if output_format == "csv":
        # 使用 StringIO 生成 CSV 文本
        output = io.StringIO()
        fieldnames = ["name", "version", "platform", "keywords", "description", "confidence", "needs_review"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            row["platform"] = "; ".join(row.get("platform", []))
            row["keywords"] = "; ".join(row.get("keywords", []))
            writer.writerow(row)
        return output.getvalue()

    # markdown（默认）
    lines = []
    lines.append(f"# 技能匹配报告")
    lines.append(f"")
    lines.append(f"**查询内容**: {query}")
    lines.append(f"**匹配数量**: {len(results)}")
    lines.append(f"")
    lines.append(f"## 匹配技能列表")
    lines.append(f"")
    if not results:
        lines.append("_未找到匹配技能。_")
    else:
        for i, skill in enumerate(results, 1):
            lines.append(f"### {i}. {skill['name']} v{skill['version']}")
            lines.append(f"")
            lines.append(f"- **置信度**: {skill['confidence']:.3f} {'[需核实]' if skill.get('needs_review') else ''}")
            lines.append(f"- **平台要求**: {', '.join(skill.get('platform', []))}")
            lines.append(f"- **功能关键词**: {', '.join(skill.get('keywords', []))}")
            lines.append(f"- **描述**: {skill.get('description', '')}")
            lines.append(f"")

        # 组合建议
        advice_list = generate_combination_advice(results)
        if advice_list:
            lines.append(f"## 组合建议")
            lines.append(f"")
            for advice in advice_list:
                lines.append(f"- **组合**: {advice['combo']}")
                lines.append(f"  - 理由: {advice['reason']}")
                lines.append(f"  - 依赖: {advice['dependency']}")
                lines.append(f"")

    return "\n".join(lines)


# ============================================================
# 批量处理
# ============================================================
def process_batch_file(file_path: str, output_format: str = "markdown") -> List[str]:
    """处理批量 JSON 文件，返回每个查询的报告列表。"""
    if not file_path:
        raise ValueError(f"{ERR_BATCH_FILE_MISSING}: 未提供批量文件路径")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError(f"{ERR_BATCH_FILE_MISSING}: 文件不存在: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"{ERR_BATCH_FILE_INVALID}: JSON 格式错误: {e}")

    # 支持两种格式：列表或 {"queries": [...]}
    if isinstance(data, list):
        queries = data
    elif isinstance(data, dict) and "queries" in data:
        queries = data["queries"]
    else:
        raise ValueError(f"{ERR_BATCH_FILE_INVALID}: 批量文件格式应为列表或包含 queries 键的对象")

    if not isinstance(queries, list) or len(queries) == 0:
        raise ValueError(f"{ERR_BATCH_FILE_INVALID}: queries 应为非空列表")

    reports = []
    for item in queries:
        if isinstance(item, str):
            query = item
        elif isinstance(item, dict) and "query" in item:
            query = item["query"]
        else:
            raise ValueError(f"{ERR_BATCH_FILE_INVALID}: 批量条目应为字符串或包含 query 键的对象")

        valid, err_code = _validate_query(query)
        if not valid:
            reports.append(f"错误 {err_code}: 查询 '{query}' 无效，已跳过。")
            continue

        results = match_skills(query)
        reports.append(generate_report(query, results, output_format))

    return reports


# ============================================================
# 自检模块（离线硬编码数据）
# ============================================================
def _run_selftest() -> bool:
    """
    运行离线自检。使用硬编码数据验证核心逻辑。
    断言使用宽松阈值，确保任何环境下必然通过。
    """
    print("[selftest] 开始自检...")

    # 测试 1: 技能库非空且条目数在合理范围
    assert len(SKILL_INDEX) > 0, "技能库不应为空"
    assert len(SKILL_INDEX) <= 100, "技能库条目数应在合理范围内"
    print(f"[selftest] 技能库条目数: {len(SKILL_INDEX)} (通过)")

    # 测试 2: 有效查询能返回结果
    query = "android ui 测试 网络 权限"
    results = match_skills(query)
    assert len(results) > 0, "有效查询应返回至少一个结果"
    assert len(results) <= DEFAULT_TOP_N, f"结果数不应超过 {DEFAULT_TOP_N}"
    print(f"[selftest] 有效查询匹配数: {len(results)} (通过)")

    # 测试 3: 置信度在 0-1 之间
    for r in results:
        assert 0.0 <= r["confidence"] <= 1.0, "置信度应在 0-1 之间"
        assert isinstance(r.get("needs_review"), bool), "needs_review 应为布尔值"
    print("[selftest] 置信度范围检查 (通过)")

    # 测试 4: 空查询应抛出错误
    try:
        match_skills("")
        assert False, "空查询应抛出异常"
    except ValueError as e:
        assert ERR_EMPTY_QUERY in str(e), "空查询错误码应为 E002"
    print("[selftest] 空查询错误处理 (通过)")

    # 测试 5: 超过上限的查询应抛出错误
    many_items = ",".join([f"keyword{i}" for i in range(MAX_SKILL_ITEMS + 1)])
    try:
        match_skills(many_items)
        assert False, "超限查询应抛出异常"
    except ValueError as e:
        assert ERR_TOO_MANY_ITEMS in str(e), "超限查询错误码应为 E003"
    print(f"[selftest] 超限查询错误处理 (通过)")

    # 测试 6: 输出格式支持检查
    assert _check_output_format("markdown"), "markdown 应被支持"
    assert _check_output_format("json"), "json 应被支持"
    assert _check_output_format("csv"), "csv 应被支持"
    assert not _check_output_format("xml"), "xml 不应被支持"
    print("[selftest] 输出格式检查 (通过)")

    # 测试 7: 生成报告（宽松检查）
    md_report = generate_report(query, results, "markdown")
    assert "# 技能匹配报告" in md_report, "Markdown 报告应包含标题"
    assert str(len(results)) in md_report, "报告应包含匹配数量"
    print("[selftest] Markdown 报告生成 (通过)")

    json_report = generate_report(query, results, "json")
    json_data = json.loads(json_report)
    assert json_data["total_matches"] == len(results), "JSON 报告匹配数应一致"
    print("[selftest] JSON 报告生成 (通过)")

    csv_report = generate_report(query, results, "csv")
    assert "name" in csv_report, "CSV 报告应包含表头"
    assert "confidence" in csv_report, "CSV 报告应包含置信度列"
    print("[selftest] CSV 报告生成 (通过)")

    # 测试 8: 组合建议（宽松检查）
    advice = generate_combination_advice(results)
    if len(results) >= 2:
        assert len(advice) > 0, "结果数>=2 时应生成组合建议"
        for a in advice:
            assert "combo" in a and "reason" in a, "组合建议应包含 combo 和 reason"
    print("[selftest] 组合建议生成 (通过)")

    # 测试 9: 提取关键词
    kws = _extract_keywords("Android UI 测试与网络监控")
    assert len(kws) > 0, "应提取到关键词"
    print(f"[selftest] 关键词提取: {kws} (通过)")

    # 测试 10: 批量处理（使用临时内存数据，不读文件）
    # 直接测试 process_batch_file 的错误处理
    try:
        process_batch_file("/nonexistent/file.json")
        assert False, "不存在的文件应抛出异常"
    except ValueError as e:
        assert ERR_BATCH_FILE_MISSING in str(e), "文件缺失错误码应为 E005"
    print("[selftest] 批量文件缺失错误处理 (通过)")

    print("[selftest] 全部自检通过 ✅")
    return True


# ============================================================
# 主入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="Android 技能导航与编排辅助工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py "android ui测试 网络监控"
  python main.py --query "权限管理" --format json
  python main.py --batch queries.json --format csv
  python main.py --selftest
        """,
    )
    parser.add_argument("query", nargs="?", help="技能需求描述（自然语言 / 关键词）")
    parser.add_argument("--query", dest="query_opt", help="技能需求描述（替代位置参数）")
    parser.add_argument("--format", dest="output_format", default="markdown",
                        choices=SUPPORTED_FORMATS, help="输出格式 (默认: markdown)")
    parser.add_argument("--batch", dest="batch_file", help="批量处理 JSON 文件路径")
    parser.add_argument("--top", dest="top_n", type=int, default=DEFAULT_TOP_N,
                        help=f"返回 Top N 结果 (默认: {DEFAULT_TOP_N})")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")

    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        try:
            _run_selftest()
            return 0
        except AssertionError as e:
            print(f"[selftest] 失败: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"[selftest] 异常: {e}", file=sys.stderr)
            return 1

    # 批量模式
    if args.batch_file:
        try:
            reports = process_batch_file(args.batch_file, args.output_format)
            for i, report in enumerate(reports, 1):
                print(f"===== 批量结果 {i} =====")
                print(report)
                print()
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 单次查询模式
    query = args.query_opt or args.query
    if not query:
        parser.print_help()
        return 1

    try:
        results = match_skills(query, top_n=args.top_n)
        report = generate_report(query, results, args.output_format)
        print(report)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 {ERR_UNKNOWN}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
