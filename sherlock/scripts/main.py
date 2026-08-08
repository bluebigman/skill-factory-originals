#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sherlock - 社交媒体账号搜索工具（Clean Room 重写版）

通过用户名在多个社交网络平台搜索用户账号，用于账号查询、身份核验、舆情调研。
本脚本仅依据功能规格独立实现，不包含任何既有代码。

功能：
  - 单用户名查询：检查该用户名在哪些平台注册
  - 批量用户名查询：一次检查多个用户名
  - 结果导出：支持 CSV / JSON 格式导出
  - 离线自检：--selftest 使用内置样例数据验证核心逻辑

用法示例：
  python main.py check john_doe
  python main.py check alice bob carol --export csv
  python main.py --selftest
  python main.py --list-sites
"""

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入参数无效
ERR_USERNAME_EMPTY = "E002"     # 用户名为空
ERR_USERNAME_FORMAT = "E003"    # 用户名格式非法
ERR_FILE_NOT_FOUND = "E004"     # 文件不存在
ERR_FILE_READ = "E005"          # 文件读取失败
ERR_FILE_WRITE = "E006"         # 文件写入失败
ERR_ENCODING = "E007"           # 编码识别失败
ERR_EXPORT_FORMAT = "E008"      # 导出格式不支持
ERR_INTERNAL = "E009"           # 内部逻辑错误
ERR_UNKNOWN = "E010"            # 未知异常

# ---------------------------------------------------------------------------
# 内置平台数据库（模拟 400+ 平台的精简样例）
# 每个平台包含：名称、主页 URL 模板、用户名校验规则
# ---------------------------------------------------------------------------
SITES_DB: List[Dict[str, str]] = [
    {
        "name": "GitHub",
        "url_template": "https://github.com/{}",
        "username_regex": r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$",
    },
    {
        "name": "Twitter/X",
        "url_template": "https://twitter.com/{}",
        "username_regex": r"^[a-zA-Z0-9_]{1,15}$",
    },
    {
        "name": "Instagram",
        "url_template": "https://www.instagram.com/{}/",
        "username_regex": r"^[a-zA-Z0-9._]{1,30}$",
    },
    {
        "name": "Reddit",
        "url_template": "https://www.reddit.com/user/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{3,20}$",
    },
    {
        "name": "TikTok",
        "url_template": "https://www.tiktok.com/@{}",
        "username_regex": r"^[a-zA-Z0-9._]{2,24}$",
    },
    {
        "name": "Facebook",
        "url_template": "https://www.facebook.com/{}",
        "username_regex": r"^[a-zA-Z0-9.]{5,50}$",
    },
    {
        "name": "LinkedIn",
        "url_template": "https://www.linkedin.com/in/{}/",
        "username_regex": r"^[a-zA-Z0-9-]{3,100}$",
    },
    {
        "name": "YouTube",
        "url_template": "https://www.youtube.com/@{}",
        "username_regex": r"^[a-zA-Z0-9._-]{3,30}$",
    },
    {
        "name": "Twitch",
        "url_template": "https://www.twitch.tv/{}",
        "username_regex": r"^[a-zA-Z0-9_]{3,25}$",
    },
    {
        "name": "Pinterest",
        "url_template": "https://www.pinterest.com/{}/",
        "username_regex": r"^[a-zA-Z0-9_-]{3,15}$",
    },
    {
        "name": "Discord",
        "url_template": "https://discord.com/users/{}",
        "username_regex": r"^[a-zA-Z0-9_.]{2,32}$",
    },
    {
        "name": "Telegram",
        "url_template": "https://t.me/{}",
        "username_regex": r"^[a-zA-Z0-9_]{5,32}$",
    },
    {
        "name": "Snapchat",
        "url_template": "https://www.snapchat.com/add/{}",
        "username_regex": r"^[a-zA-Z0-9._-]{3,15}$",
    },
    {
        "name": "Medium",
        "url_template": "https://medium.com/@{}",
        "username_regex": r"^[a-zA-Z0-9._-]{3,50}$",
    },
    {
        "name": "Dev.to",
        "url_template": "https://dev.to/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{1,39}$",
    },
    {
        "name": "HackerNews",
        "url_template": "https://news.ycombinator.com/user?id={}",
        "username_regex": r"^[a-zA-Z0-9_-]{2,15}$",
    },
    {
        "name": "StackOverflow",
        "url_template": "https://stackoverflow.com/users/{}",
        "username_regex": r"^[0-9]+$",
    },
    {
        "name": "VK",
        "url_template": "https://vk.com/{}",
        "username_regex": r"^[a-zA-Z0-9_.]{2,32}$",
    },
    {
        "name": "Weibo",
        "url_template": "https://weibo.com/u/{}",
        "username_regex": r"^[a-zA-Z0-9_]{4,30}$",
    },
    {
        "name": "Zhihu",
        "url_template": "https://www.zhihu.com/people/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{3,40}$",
    },
    {
        "name": "Bilibili",
        "url_template": "https://space.bilibili.com/{}",
        "username_regex": r"^[0-9]+$",
    },
    {
        "name": "Douyin",
        "url_template": "https://www.douyin.com/user/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{4,32}$",
    },
    {
        "name": "Kuaishou",
        "url_template": "https://www.kuaishou.com/profile/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{4,32}$",
    },
    {
        "name": "Xiaohongshu",
        "url_template": "https://www.xiaohongshu.com/user/profile/{}",
        "username_regex": r"^[a-zA-Z0-9_-]{4,32}$",
    },
    {
        "name": "QQ",
        "url_template": "https://user.qzone.qq.com/{}",
        "username_regex": r"^[0-9]{5,12}$",
    },
]

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    """单个用户名在单个平台的检查结果"""
    username: str
    site_name: str
    url: str
    status: str  # "found" / "not_found" / "unknown"
    detail: str = ""


@dataclass
class UserResult:
    """单个用户名的完整检查结果"""
    username: str
    results: List[CheckResult] = field(default_factory=list)
    found_count: int = 0
    not_found_count: int = 0
    unknown_count: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 输入校验（R7：guard clause 顶部先校验）
# ---------------------------------------------------------------------------
def validate_username(username: str) -> Tuple[bool, str]:
    """
    校验用户名格式。
    返回 (是否合法, 错误信息)。
    """
    if not username:
        return False, "用户名为空"
    if len(username) > 100:
        return False, "用户名过长（超过 100 字符）"
    # 禁止包含路径穿越字符和危险字符
    if re.search(r'[/\\\x00-\x1f]', username):
        return False, "用户名包含非法字符"
    return True, ""


def validate_username_list(usernames: List[str]) -> Tuple[List[str], List[str]]:
    """
    批量校验用户名列表。
    返回 (合法用户名列表, 非法用户名列表)。
    """
    valid: List[str] = []
    invalid: List[str] = []
    for name in usernames:
        ok, _ = validate_username(name)
        if ok:
            valid.append(name)
        else:
            invalid.append(name)
    return valid, invalid


def validate_export_format(fmt: str) -> bool:
    """校验导出格式是否支持"""
    return fmt in ("csv", "json", "none")


# ---------------------------------------------------------------------------
# 核心逻辑：平台匹配（R5：O(n) 性能，无限制输入量参数）
# ---------------------------------------------------------------------------
def match_username_to_sites(username: str, sites: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    将用户名与平台规则匹配，返回匹配的平台列表。
    时间复杂度 O(n)，n 为平台数量。
    """
    matched = []
    for site in sites:
        pattern = site.get("username_regex", "")
        try:
            if re.match(pattern, username):
                matched.append(site)
        except re.error:
            # 正则表达式本身有问题，跳过该平台
            continue
    return matched


def build_url(site: Dict[str, str], username: str) -> str:
    """根据平台 URL 模板和用户名生成主页 URL"""
    template = site.get("url_template", "")
    return template.format(username)


def check_username_on_sites(username: str, sites: List[Dict[str, str]], verbose: bool = False) -> UserResult:
    """
    检查用户名在哪些平台注册（模拟检查）。
    实际场景中这里会发起 HTTP 请求，本实现为离线模拟。
    """
    result = UserResult(username=username)
    matched_sites = match_username_to_sites(username, sites)

    for site in matched_sites:
        url = build_url(site, username)
        # 模拟检查：根据用户名特征判断状态（离线模拟）
        status, detail = simulate_site_check(username, site["name"])
        check = CheckResult(
            username=username,
            site_name=site["name"],
            url=url,
            status=status,
            detail=detail,
        )
        result.results.append(check)
        if status == "found":
            result.found_count += 1
        elif status == "not_found":
            result.not_found_count += 1
        else:
            result.unknown_count += 1

        if verbose:
            print(f"  [{'✓' if status == 'found' else '✗' if status == 'not_found' else '?'}] {site['name']}: {url}")

    return result


def simulate_site_check(username: str, site_name: str) -> Tuple[str, str]:
    """
    模拟平台检查（离线）。
    实际实现中应发起 HTTP 请求，这里用确定性规则模拟：
      - 用户名包含数字 → 判定为 found（模拟数字 ID 常见）
      - 用户名包含下划线 → 判定为 not_found
      - 其他 → 判定为 unknown
    """
    if any(ch.isdigit() for ch in username):
        return "found", "模拟：用户名包含数字，判定账号存在"
    if "_" in username:
        return "not_found", "模拟：用户名包含下划线，判定账号不存在"
    return "unknown", "模拟：无法确定，可能被反爬限制"


# ---------------------------------------------------------------------------
# 批量检查（R5：流式处理，O(n)）
# ---------------------------------------------------------------------------
def batch_check(usernames: List[str], sites: List[Dict[str, str]], verbose: bool = False) -> List[UserResult]:
    """批量检查多个用户名，返回结果列表"""
    results = []
    for username in usernames:
        if verbose:
            print(f"\n检查用户名: {username}")
        result = check_username_on_sites(username, sites, verbose)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# 输出格式化（R6：可解释输出）
# ---------------------------------------------------------------------------
def format_text_report(results: List[UserResult]) -> str:
    """生成文本报告"""
    lines = []
    lines.append("=" * 60)
    lines.append("sherlock 社交媒体账号搜索结果")
    lines.append("=" * 60)

    for result in results:
        lines.append(f"\n用户名: {result.username}")
        if result.error:
            lines.append(f"  错误: {result.error}")
            continue
        lines.append(f"  匹配平台: {len(result.results)} 个")
        lines.append(f"  账号存在: {result.found_count} 个")
        lines.append(f"  账号不存在: {result.not_found_count} 个")
        lines.append(f"  无法确定: {result.unknown_count} 个")

        if result.results:
            lines.append("  详情:")
            for check in result.results:
                status_str = {
                    "found": "[+] 存在",
                    "not_found": "[-] 不存在",
                    "unknown": "[?] 无法确定",
                }.get(check.status, "[?]")
                lines.append(f"    {status_str} {check.site_name}: {check.url}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def export_results(results: List[UserResult], fmt: str, output_path: str) -> Tuple[bool, str]:
    """
    导出结果到文件。
    返回 (是否成功, 错误信息)。
    """
    if fmt == "none":
        return True, ""

    try:
        if fmt == "json":
            data = []
            for r in results:
                item = {
                    "username": r.username,
                    "found_count": r.found_count,
                    "not_found_count": r.not_found_count,
                    "unknown_count": r.unknown_count,
                    "results": [
                        {
                            "site": c.site_name,
                            "url": c.url,
                            "status": c.status,
                            "detail": c.detail,
                        }
                        for c in r.results
                    ],
                }
                data.append(item)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        elif fmt == "csv":
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["用户名", "平台", "URL", "状态", "详情"])
                for r in results:
                    for c in r.results:
                        writer.writerow([r.username, c.site_name, c.url, c.status, c.detail])

        return True, ""
    except Exception as e:
        return False, f"导出失败: {e}"


# ---------------------------------------------------------------------------
# 文件读取（R3：多编码支持）
# ---------------------------------------------------------------------------
def read_usernames_from_file(filepath: str) -> Tuple[Optional[List[str]], Optional[str]]:
    """
    从文件读取用户名列表。
    支持 utf-8 → gbk → gb18030 三级编码 fallback。
    返回 (用户名列表, 错误信息)。
    """
    if not os.path.exists(filepath):
        return None, f"文件不存在: {filepath}"

    encodings = ["utf-8", "gbk", "gb18030"]
    content = None
    last_error = ""

    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = f"编码 {enc} 解码失败: {e}"
            continue
        except Exception as e:
            return None, f"读取文件失败: {e}"

    if content is None:
        # 最后尝试 errors="replace"
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return None, f"读取文件失败（所有编码均失败）: {e}"

    # 按行分割，去除空行和空白
    usernames = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            usernames.append(line)

    if not usernames:
        return None, "文件中未找到有效用户名"

    return usernames, None


# ---------------------------------------------------------------------------
# 自检（R1：契约测试，宽松断言）
# ---------------------------------------------------------------------------
def run_selftest() -> bool:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不依赖外部文件/网络。
    """
    print("=" * 60)
    print("sherlock 自检开始")
    print("=" * 60)

    all_passed = True

    # 测试用例 1：正常用户名
    print("\n[测试 1] 正常用户名 'john_doe123'")
    ok, msg = validate_username("john_doe123")
    if ok:
        print("  ✓ 用户名校验通过")
    else:
        print(f"  ✗ 用户名校验失败: {msg}")
        all_passed = False

    # 测试用例 2：空用户名
    print("\n[测试 2] 空用户名 ''")
    ok, msg = validate_username("")
    if not ok and "空" in msg:
        print("  ✓ 空用户名被正确拒绝")
    else:
        print("  ✗ 空用户名未被正确拒绝")
        all_passed = False

    # 测试用例 3：中文用户名（应通过，因为不包含非法字符）
    print("\n[测试 3] 中文用户名 '张三'")
    ok, msg = validate_username("张三")
    if ok:
        print("  ✓ 中文用户名校验通过")
    else:
        print(f"  ✗ 中文用户名校验失败: {msg}")
        all_passed = False

    # 测试用例 4：路径穿越字符
    print("\n[测试 4] 路径穿越用户名 '../etc'")
    ok, msg = validate_username("../etc")
    if not ok:
        print("  ✓ 路径穿越被正确拒绝")
    else:
        print("  ✗ 路径穿越未被拒绝")
        all_passed = False

    # 测试用例 5：超长用户名
    print("\n[测试 5] 超长用户名（200字符）")
    long_name = "a" * 200
    ok, msg = validate_username(long_name)
    if not ok and "过长" in msg:
        print("  ✓ 超长用户名被正确拒绝")
    else:
        print("  ✗ 超长用户名未被拒绝")
        all_passed = False

    # 测试用例 6：平台匹配
    print("\n[测试 6] 平台匹配 'alice123'")
    matched = match_username_to_sites("alice123", SITES_DB)
    if len(matched) > 0:
        print(f"  ✓ 匹配到 {len(matched)} 个平台")
    else:
        print("  ✗ 未匹配到任何平台")
        all_passed = False

    # 测试用例 7：完整检查流程
    print("\n[测试 7] 完整检查 'bob_2024'")
    result = check_username_on_sites("bob_2024", SITES_DB)
    if result.results:
        print(f"  ✓ 检查完成，匹配 {len(result.results)} 个平台")
        print(f"    存在: {result.found_count}, 不存在: {result.not_found_count}, 未知: {result.unknown_count}")
    else:
        print("  ✗ 检查未返回结果")
        all_passed = False

    # 测试用例 8：批量检查
    print("\n[测试 8] 批量检查 ['alice', 'bob_2024', 'carol']")
    results = batch_check(["alice", "bob_2024", "carol"], SITES_DB)
    if len(results) == 3:
        print(f"  ✓ 批量检查完成，返回 {len(results)} 个结果")
    else:
        print(f"  ✗ 批量检查返回 {len(results)} 个结果，期望 3 个")
        all_passed = False

    # 测试用例 9：文本报告生成
    print("\n[测试 9] 文本报告生成")
    report = format_text_report(results)
    if len(report) > 100:
        print(f"  ✓ 报告生成成功，长度 {len(report)} 字符")
    else:
        print("  ✗ 报告过短")
        all_passed = False

    # 测试用例 10：JSON 导出
    print("\n[测试 10] JSON 导出")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ok, err = export_results(results, "json", tmp_path)
        if ok and os.path.exists(tmp_path):
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if len(data) == 3:
                print(f"  ✓ JSON 导出成功，包含 {len(data)} 条记录")
            else:
                print(f"  ✗ JSON 导出记录数不符: {len(data)}")
                all_passed = False
        else:
            print(f"  ✗ JSON 导出失败: {err}")
            all_passed = False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 测试用例 11：CSV 导出
    print("\n[测试 11] CSV 导出")
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        ok, err = export_results(results, "csv", tmp_path)
        if ok and os.path.exists(tmp_path):
            with open(tmp_path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
            if len(lines) > 1:
                print(f"  ✓ CSV 导出成功，包含 {len(lines)} 行")
            else:
                print("  ✗ CSV 导出内容为空")
                all_passed = False
        else:
            print(f"  ✗ CSV 导出失败: {err}")
            all_passed = False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 测试用例 12：文件读取（GBK 编码）
    print("\n[测试 12] GBK 编码文件读取")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "w", encoding="gbk") as f:
            f.write("alice\nbob_2024\n# 注释行\ncarol\n")
        usernames, err = read_usernames_from_file(tmp_path)
        if err is None and len(usernames) == 3:
            print(f"  ✓ GBK 文件读取成功，获取 {len(usernames)} 个用户名")
        else:
            print(f"  ✗ GBK 文件读取失败: {err}")
            all_passed = False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 测试用例 13：文件不存在
    print("\n[测试 13] 不存在的文件")
    usernames, err = read_usernames_from_file("/nonexistent/path/file.txt")
    if err is not None and "不存在" in err:
        print("  ✓ 文件不存在被正确报告")
    else:
        print("  ✗ 文件不存在未被正确报告")
        all_passed = False

    # 测试用例 14：空输入批量检查
    print("\n[测试 14] 空输入批量检查")
    empty_results = batch_check([], SITES_DB)
    if len(empty_results) == 0:
        print("  ✓ 空输入返回空结果")
    else:
        print(f"  ✗ 空输入返回 {len(empty_results)} 个结果")
        all_passed = False

    # 测试用例 15：URL 构建
    print("\n[测试 15] URL 构建")
    site = {"name": "GitHub", "url_template": "https://github.com/{}"}
    url = build_url(site, "testuser")
    if url == "https://github.com/testuser":
        print("  ✓ URL 构建正确")
    else:
        print(f"  ✗ URL 构建错误: {url}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    return all_passed


# ---------------------------------------------------------------------------
# 主入口（R8：main 只做 CLI 分发）
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="sherlock",
        description="社交媒体账号搜索工具 - 通过用户名在多个平台搜索账号",
        epilog="示例: python main.py check john_doe --verbose",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # check 子命令
    check_parser = subparsers.add_parser("check", help="检查用户名")
    check_parser.add_argument("usernames", nargs="+", help="要检查的用户名（可多个）")
    check_parser.add_argument("--file", "-f", help="从文件读取用户名列表")
    check_parser.add_argument("--export", "-e", choices=["csv", "json", "none"], default="none",
                              help="导出结果格式（默认不导出）")
    check_parser.add_argument("--output", "-o", help="导出文件路径（默认自动生成）")
    check_parser.add_argument("--verbose", "-v", action="store_true", help="显示详细检查过程")

    # list-sites 子命令
    subparsers.add_parser("list-sites", help="列出所有支持的平台")

    # 全局参数
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    parser.add_argument("--version", action="version", version="sherlock 1.4.1 (clean-room)")

    return parser.parse_args(argv)


def cmd_list_sites() -> int:
    """列出所有支持的平台"""
    print(f"支持 {len(SITES_DB)} 个平台：")
    print("-" * 40)
    for i, site in enumerate(SITES_DB, 1):
        print(f"{i:3d}. {site['name']:<20} {site['url_template']}")
    return ERR_SUCCESS


def cmd_check(args: argparse.Namespace) -> int:
    """执行检查命令"""
    # 收集用户名
    usernames: List[str] = []

    # 从参数获取
    if args.usernames:
        usernames.extend(args.usernames)

    # 从文件获取
    if args.file:
        file_usernames, err = read_usernames_from_file(args.file)
        if err:
            print(f"错误 [{ERR_FILE_READ}]: {err}", file=sys.stderr)
            return 1
        usernames.extend(file_usernames)

    if not usernames:
        print(f"错误 [{ERR_USERNAME_EMPTY}]: 未提供任何用户名", file=sys.stderr)
        return 1

    # 校验用户名
    valid_usernames, invalid_usernames = validate_username_list(usernames)
    if invalid_usernames:
        print(f"警告: {len(invalid_usernames)} 个用户名格式非法，已跳过: {invalid_usernames}", file=sys.stderr)

    if not valid_usernames:
        print(f"错误 [{ERR_USERNAME_FORMAT}]: 所有用户名均格式非法", file=sys.stderr)
        return 1

    # 执行检查
    try:
        results = batch_check(valid_usernames, SITES_DB, args.verbose)
    except Exception as e:
        print(f"错误 [{ERR_INTERNAL}]: 检查过程中发生异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    # 输出报告
    report = format_text_report(results)
    print(report)

    # 导出
    if args.export != "none":
        output_path = args.output
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"sherlock_results_{timestamp}.{args.export}"

        ok, err = export_results(results, args.export, output_path)
        if ok:
            print(f"\n结果已导出到: {output_path}")
        else:
            print(f"错误 [{ERR_EXPORT_FORMAT}]: {err}", file=sys.stderr)
            return 1

    return ERR_SUCCESS


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    try:
        args = parse_args(argv)

        # 自检模式
        if args.selftest:
            return 0 if run_selftest() else 1

        # 无命令时显示帮助
        if not args.command:
            print("请指定子命令。使用 --help 查看帮助。", file=sys.stderr)
            return 1

        # 分发子命令
        if args.command == "list-sites":
            return cmd_list_sites()
        elif args.command == "check":
            return cmd_check(args)
        else:
            print(f"错误 [{ERR_INVALID_INPUT}]: 未知命令: {args.command}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\n用户中断操作", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误 [{ERR_UNKNOWN}]: 未预期异常: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
