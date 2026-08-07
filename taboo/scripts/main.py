#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
taboo — 浏览器标签页会话管理状态修复工具
========================================
轻量级标签页异常诊断与修复方案生成器。
仅依据功能规格独立实现（clean-room），不复制任何既有代码。

功能能力:
  C1 输入解析        — 解析 URL / 会话快照 / 浏览器导出数据
  C2 关键信息识别    — 提取标题、URL、时间戳、分组、优先级
  C3 状态诊断        — 判断异常类型（崩溃/挂起/重定向/内存）
  C4 修复方案生成    — 输出可执行修复步骤序列
  C5 批量与自定义    — 多标签页处理、自定义输出字段

明确边界（不实现）:
  X1 不直接操作浏览器
  X2 不恢复已丢失数据
  X3 不处理非浏览器问题
  X4 不保证修复成功率

用法示例:
  python main.py --url "https://example.com/page" --title "测试页"
  python main.py --file session.json --format json
  python main.py --selftest

错误码:
  E001 参数解析失败
  E002 输入数据为空
  E003 URL 格式非法
  E004 文件读取失败
  E005 JSON 解析失败
  E006 缺少必要字段
  E007 诊断过程异常
  E008 方案生成异常
  E009 输出格式不支持
  E010 自检失败
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse

# 版本信息
__version__ = "1.0.1"
__author__ = "Lin Chen"


# ============================================================
# 常量定义
# ============================================================

# 异常类型标识
CRASH = "crash"                # 崩溃
HANG = "hang"                  # 挂起
REDIRECT_LOOP = "redirect_loop"  # 重定向循环
MEMORY_OVERFLOW = "memory_overflow"  # 内存溢出
NORMAL = "normal"              # 正常

# 优先级
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# 支持的输出格式
SUPPORTED_FORMATS = ("text", "json", "csv")

# URL 正则（宽松校验）
URL_PATTERN = re.compile(
    r"^(https?|ftp)://"          # 协议
    r"([A-Za-z0-9.-]+)"          # 域名
    r"(:\d+)?"                   # 端口
    r"(/.*)?$",                  # 路径
    re.IGNORECASE
)

# 标签页状态关键词映射
STATUS_KEYWORDS = {
    CRASH: ["crash", "崩溃", "异常退出", "aw snap", "页面崩溃"],
    HANG: ["hang", "挂起", "无响应", "卡死", "unresponsive", "frozen"],
    REDIRECT_LOOP: ["redirect", "重定向", "循环", "loop", "too many redirects"],
    MEMORY_OVERFLOW: ["memory", "内存", "out of memory", "oom", "内存不足"],
}

# 修复方案模板
FIX_TEMPLATES = {
    CRASH: [
        {"step": 1, "action": "重新加载页面", "detail": "点击刷新按钮或按 Ctrl+R (Cmd+R)", "expect": "页面重新加载"},
        {"step": 2, "action": "清理浏览器缓存", "detail": "设置 → 隐私与安全 → 清除浏览数据", "expect": "缓存清除"},
        {"step": 3, "action": "禁用可疑扩展", "detail": "逐一禁用最近安装的扩展后重试", "expect": "排除扩展冲突"},
        {"step": 4, "action": "更新浏览器", "detail": "检查并安装最新版本", "expect": "修复已知 bug"},
    ],
    HANG: [
        {"step": 1, "action": "强制刷新", "detail": "Ctrl+Shift+R (Cmd+Shift+R) 绕过缓存", "expect": "页面刷新"},
        {"step": 2, "action": "关闭标签页重开", "detail": "关闭后从历史记录恢复", "expect": "标签页重建"},
        {"step": 3, "action": "检查脚本执行", "detail": "查看开发者工具 Console 是否有死循环", "expect": "定位卡死原因"},
        {"step": 4, "action": "更新显卡驱动", "detail": "硬件加速问题可能导致挂起", "expect": "硬件兼容性修复"},
    ],
    REDIRECT_LOOP: [
        {"step": 1, "action": "检查 URL 拼写", "detail": "确认无多余斜杠或参数", "expect": "URL 正确"},
        {"step": 2, "action": "清除该站点 Cookie", "detail": "站点设置 → 删除 Cookie", "expect": "清除会话状态"},
        {"step": 3, "action": "检查服务端配置", "detail": "可能是服务器重定向规则错误", "expect": "服务端修复"},
        {"step": 4, "action": "使用无痕模式", "detail": "排除扩展与 Cookie 干扰", "expect": "确认是否第三方因素"},
    ],
    MEMORY_OVERFLOW: [
        {"step": 1, "action": "关闭其他标签页", "detail": "释放内存资源", "expect": "内存占用下降"},
        {"step": 2, "action": "使用内存监控", "detail": "任务管理器查看浏览器内存占用", "expect": "确认内存泄漏"},
        {"step": 3, "action": "减少扩展数量", "detail": "每个扩展都消耗内存", "expect": "降低内存压力"},
        {"step": 4, "action": "重启浏览器", "detail": "彻底释放内存", "expect": "恢复正常状态"},
    ],
    NORMAL: [
        {"step": 1, "action": "无需修复", "detail": "标签页状态正常", "expect": "保持现状"},
    ],
}


# ============================================================
# 数据模型
# ============================================================

class TabInfo:
    """标签页信息结构化数据"""

    def __init__(self, url="", title="", timestamp=None, group="", priority=""):
        self.url = url
        self.title = title
        self.timestamp = timestamp if timestamp else datetime.now().isoformat()
        self.group = group
        self.priority = priority
        self.status = NORMAL
        self.diagnosis = []

    def to_dict(self):
        """转为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "group": self.group,
            "priority": self.priority,
            "status": self.status,
            "diagnosis": self.diagnosis,
        }


# ============================================================
# 核心功能模块
# ============================================================

def parse_input(source, source_type="url"):
    """
    C1 输入解析 — 将原始输入解析为结构化字段

    参数:
        source: 原始输入（URL、JSON 字符串、文件路径）
        source_type: 输入类型（url/json/file）

    返回:
        list[TabInfo] 标签页信息列表

    错误码:
        E002 输入为空
        E003 URL 格式非法
        E004 文件读取失败
        E005 JSON 解析失败
    """
    if not source or not str(source).strip():
        raise ValueError("E002: 输入数据为空")

    if source_type == "url":
        return [_parse_single_url(str(source).strip())]
    elif source_type == "json":
        return _parse_json_data(str(source).strip())
    elif source_type == "file":
        return _parse_file(str(source).strip())
    else:
        raise ValueError(f"E009: 不支持的输入类型: {source_type}")


def _parse_single_url(url):
    """解析单个 URL"""
    if not URL_PATTERN.match(url):
        raise ValueError(f"E003: URL 格式非法: {url}")

    tab = TabInfo(url=url)
    # 从 URL 提取标题（域名作为默认标题）
    parsed = urlparse(url)
    tab.title = parsed.netloc or url
    tab.priority = _infer_priority(url, tab.title)
    return tab


def _parse_json_data(json_str):
    """解析 JSON 数据"""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"E005: JSON 解析失败: {e}")

    return _convert_to_tabs(data)


def _parse_file(file_path):
    """解析文件"""
    if not os.path.isfile(file_path):
        raise ValueError(f"E004: 文件读取失败: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        raise ValueError(f"E004: 文件读取失败: {file_path} - {e}")

    # 尝试 JSON 解析
    try:
        return _parse_json_data(content)
    except ValueError:
        # 尝试按行解析（每行一个 URL）
        tabs = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    tabs.append(_parse_single_url(line))
                except ValueError:
                    continue  # 跳过非法行
        if not tabs:
            raise ValueError("E006: 缺少必要字段，文件中无有效 URL")
        return tabs


def _convert_to_tabs(data):
    """将 JSON 数据转换为 TabInfo 列表"""
    if isinstance(data, dict):
        # 单条数据
        return [_convert_dict_to_tab(data)]
    elif isinstance(data, list):
        # 批量数据
        tabs = []
        for item in data:
            if isinstance(item, dict):
                tabs.append(_convert_dict_to_tab(item))
        if not tabs:
            raise ValueError("E006: 缺少必要字段，JSON 中无有效标签页")
        return tabs
    else:
        raise ValueError("E006: 缺少必要字段，JSON 格式错误")


def _convert_dict_to_tab(data):
    """将字典转换为 TabInfo"""
    url = data.get("url", "")
    if not url:
        raise ValueError("E006: 缺少必要字段: url")

    tab = TabInfo(
        url=url,
        title=data.get("title", ""),
        timestamp=data.get("timestamp", ""),
        group=data.get("group", ""),
        priority=data.get("priority", ""),
    )
    if not tab.title:
        parsed = urlparse(url)
        tab.title = parsed.netloc or url
    if not tab.priority:
        tab.priority = _infer_priority(tab.url, tab.title)
    return tab


def _infer_priority(url, title):
    """推断优先级"""
    high_keywords = ["urgent", "重要", "紧急", "critical", "asap"]
    low_keywords = ["archive", "归档", "旧", "old", "temp", "临时"]

    combined = f"{url} {title}".lower()
    for kw in high_keywords:
        if kw in combined:
            return PRIORITY_HIGH
    for kw in low_keywords:
        if kw in combined:
            return PRIORITY_LOW
    return PRIORITY_MEDIUM


def diagnose(tab):
    """
    C3 状态诊断 — 判断标签页异常类型

    参数:
        tab: TabInfo 对象

    返回:
        str 状态标识（crash/hang/redirect_loop/memory_overflow/normal）

    错误码:
        E007 诊断过程异常
    """
    try:
        # 组合 URL 和标题进行关键词匹配
        combined = f"{tab.url} {tab.title}".lower()

        # 检查各异常类型关键词
        for status, keywords in STATUS_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in combined:
                    tab.status = status
                    tab.diagnosis.append(f"检测到关键词: {kw}")
                    return status

        # 启发式判断
        if "chrome://" in tab.url or "about:" in tab.url:
            tab.status = NORMAL
        elif tab.url.count("redirect") > 1:
            tab.status = REDIRECT_LOOP
            tab.diagnosis.append("多次重定向")
        elif "memory" in combined and "high" in combined:
            tab.status = MEMORY_OVERFLOW
            tab.diagnosis.append("内存占用高")
        else:
            tab.status = NORMAL

        return tab.status
    except Exception as e:
        raise ValueError(f"E007: 诊断过程异常: {e}")


def generate_fix_plan(tab):
    """
    C4 修复方案生成 — 输出可执行的修复步骤序列

    参数:
        tab: TabInfo 对象

    返回:
        list[dict] 修复步骤列表

    错误码:
        E008 方案生成异常
    """
    try:
        status = tab.status if tab.status else diagnose(tab)
        template = FIX_TEMPLATES.get(status, FIX_TEMPLATES[NORMAL])

        # 深拷贝模板，避免修改常量
        plan = []
        for step in template:
            plan.append({
                "step": step["step"],
                "action": step["action"],
                "detail": step["detail"],
                "expect": step["expect"],
            })
        return plan
    except Exception as e:
        raise ValueError(f"E008: 方案生成异常: {e}")


def batch_process(tabs):
    """
    C5 批量处理 — 处理多个标签页

    参数:
        tabs: list[TabInfo]

    返回:
        list[dict] 处理结果列表
    """
    results = []
    for tab in tabs:
        status = diagnose(tab)
        plan = generate_fix_plan(tab)
        results.append({
            "tab": tab.to_dict(),
            "status": status,
            "fix_plan": plan,
        })
    return results


def format_output(results, fmt="text"):
    """
    C5 自定义输出 — 按指定格式输出结果

    参数:
        results: 处理结果列表
        fmt: 输出格式（text/json/csv）

    返回:
        str 格式化后的输出

    错误码:
        E009 输出格式不支持
    """
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"E009: 输出格式不支持: {fmt}")

    if fmt == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)

    if fmt == "csv":
        lines = ["url,title,status,priority,group"]
        for r in results:
            tab = r["tab"]
            lines.append(
                f"{tab['url']},{tab['title']},{r['status']},{tab['priority']},{tab['group']}"
            )
        return "\n".join(lines)

    # text 格式
    lines = []
    for i, r in enumerate(results, 1):
        tab = r["tab"]
        lines.append(f"=== 标签页 #{i} ===")
        lines.append(f"URL: {tab['url']}")
        lines.append(f"标题: {tab['title']}")
        lines.append(f"状态: {r['status']}")
        lines.append(f"优先级: {tab['priority']}")
        lines.append(f"分组: {tab['group'] or '默认'}")
        lines.append("修复方案:")
        for step in r["fix_plan"]:
            lines.append(f"  [{step['step']}] {step['action']}: {step['detail']}")
            lines.append(f"      预期: {step['expect']}")
        lines.append("")
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest():
    """
    内置自检 — 使用硬编码样例数据离线验证核心逻辑

    返回:
        bool 自检是否通过

    错误码:
        E010 自检失败
    """
    test_cases = [
        # (输入, 期望状态, 期望修复步骤数)
        ("https://example.com/crash/page", CRASH, 4),
        ("https://example.com/hang/script", HANG, 4),
        ("https://example.com/redirect/loop", REDIRECT_LOOP, 4),
        ("https://example.com/memory/overflow", MEMORY_OVERFLOW, 4),
        ("https://example.com/normal/page", NORMAL, 1),
    ]

    try:
        # 测试 1: URL 解析
        for url, expected_status, expected_steps in test_cases:
            tabs = parse_input(url, "url")
            assert len(tabs) == 1, f"URL 解析数量错误: {url}"
            assert tabs[0].url == url, f"URL 解析内容错误: {url}"

            # 测试 2: 诊断
            status = diagnose(tabs[0])
            assert status == expected_status, f"诊断错误: {url} → {status}, 期望 {expected_status}"

            # 测试 3: 修复方案生成
            plan = generate_fix_plan(tabs[0])
            assert len(plan) >= expected_steps - 1, f"修复步骤过少: {url}"
            assert len(plan) <= expected_steps + 1, f"修复步骤过多: {url}"
            # 验证步骤结构
            for step in plan:
                assert "step" in step, "修复步骤缺少 step 字段"
                assert "action" in step, "修复步骤缺少 action 字段"
                assert "detail" in step, "修复步骤缺少 detail 字段"
                assert "expect" in step, "修复步骤缺少 expect 字段"

        # 测试 4: JSON 输入
        json_data = json.dumps([
            {"url": "https://example.com/crash/page", "title": "崩溃页"},
            {"url": "https://example.com/hang/page", "title": "挂起页"},
        ])
        tabs = parse_input(json_data, "json")
        assert len(tabs) == 2, f"JSON 解析数量错误: {len(tabs)}"
        assert tabs[0].title == "崩溃页", "JSON 标题解析错误"

        # 测试 5: 批量处理
        results = batch_process(tabs)
        assert len(results) == 2, f"批量处理数量错误: {len(results)}"
        assert results[0]["status"] == CRASH, "批量处理状态错误"

        # 测试 6: 输出格式
        text_out = format_output(results, "text")
        assert "修复方案" in text_out, "文本输出缺少修复方案"
        json_out = format_output(results, "json")
        parsed_out = json.loads(json_out)
        assert len(parsed_out) == 2, "JSON 输出解析错误"
        csv_out = format_output(results, "csv")
        assert "url,title,status" in csv_out, "CSV 输出头错误"

        # 测试 7: 优先级推断
        high_tab = TabInfo(url="https://example.com/urgent", title="重要任务")
        assert _infer_priority(high_tab.url, high_tab.title) == PRIORITY_HIGH, "高优先级推断错误"

        # 测试 8: 文件解析（使用临时文件）
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json.dumps({"url": "https://example.com/memory/overflow", "title": "内存问题"}))
            tmp_path = f.name
        try:
            tabs = parse_input(tmp_path, "file")
            assert len(tabs) == 1, "文件解析数量错误"
            assert tabs[0].title == "内存问题", "文件解析内容错误"
        finally:
            os.unlink(tmp_path)

        # 测试 9: 边界 — 空输入
        try:
            parse_input("", "url")
            assert False, "空输入应抛异常"
        except ValueError as e:
            assert "E002" in str(e), f"错误码错误: {e}"

        # 测试 10: 边界 — 非法 URL
        try:
            parse_input("not-a-url", "url")
            assert False, "非法 URL 应抛异常"
        except ValueError as e:
            assert "E003" in str(e), f"错误码错误: {e}"

        # 测试 11: 边界 — 不支持格式
        try:
            format_output([], "xml")
            assert False, "不支持格式应抛异常"
        except ValueError as e:
            assert "E009" in str(e), f"错误码错误: {e}"

        return True

    except AssertionError as e:
        print(f"E010: 自检失败 - 断言错误: {e}")
        return False
    except ValueError as e:
        print(f"E010: 自检失败 - 值错误: {e}")
        return False
    except Exception as e:
        print(f"E010: 自检失败 - 未预期异常: {e}")
        return False


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="taboo — 浏览器标签页会话管理状态修复工具",
        epilog="示例: python main.py --url https://example.com --selftest",
    )
    parser.add_argument("--url", type=str, help="单个标签页 URL")
    parser.add_argument("--title", type=str, help="标签页标题（可选）")
    parser.add_argument("--file", type=str, help="会话快照文件路径（JSON 或每行一个 URL）")
    parser.add_argument("--json", type=str, help="JSON 格式的输入数据")
    parser.add_argument("--format", type=str, default="text", choices=SUPPORTED_FORMATS,
                        help="输出格式: text/json/csv")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--version", action="version", version=f"taboo {__version__}")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        print("运行内置自检...")
        if run_selftest():
            print("自检通过 ✓")
            sys.exit(0)
        else:
            print("自检失败 ✗")
            sys.exit(1)

    # 输入解析
    try:
        if args.url:
            tabs = parse_input(args.url, "url")
            if args.title:
                tabs[0].title = args.title
        elif args.file:
            tabs = parse_input(args.file, "file")
        elif args.json:
            tabs = parse_input(args.json, "json")
        else:
            parser.error("E001: 请提供 --url、--file 或 --json 参数")
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 批量处理
    try:
        results = batch_process(tabs)
        output = format_output(results, args.format)
        print(output)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
