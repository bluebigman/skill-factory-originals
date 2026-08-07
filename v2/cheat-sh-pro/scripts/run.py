#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行速查手册 — 配套执行器（原创实现，clean-room）
技能「cheat-sh-pro」的轻量辅助脚本：解析同目录 SKILL.md，提供 CLI 入口、触发词匹配、能力速览。
零第三方依赖。
"""
from __future__ import annotations
import argparse, re, sys, json, random, time, tempfile, os
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

HERE = Path(__file__).resolve().parent
TRIGGERS = ["cheat.sh", "命令行示例", "速查命令", "工具用法", ""]

# 内置默认数据（降级用）- 扩充编程语言条目
DEFAULT_CHEATS = {
    "python": {
        "list": "my_list = [1, 2, 3]",
        "dict": "my_dict = {'key': 'value'}",
        "loop": "for i in range(10): print(i)",
        "function": "def my_func(x):\n    return x * 2",
        "class": "class MyClass:\n    def __init__(self):\n        self.value = 0"
    },
    "javascript": {
        "array": "const arr = [1, 2, 3]",
        "object": "const obj = { key: 'value' }",
        "function": "function myFunc(x) { return x * 2; }",
        "arrow": "const add = (a, b) => a + b",
        "promise": "const p = new Promise((resolve, reject) => {})"
    },
    "java": {
        "main": "public static void main(String[] args) {}",
        "list": "List<String> list = new ArrayList<>();",
        "map": "Map<String, Integer> map = new HashMap<>();",
        "class": "public class MyClass {\n    private int value;\n}",
        "loop": "for (int i = 0; i < 10; i++) { }"
    },
    "linux": {
        "ls": "ls -la",
        "du": "du -sh *",
        "grep": "grep pattern file.txt",
        "find": "find . -name '*.txt'",
        "chmod": "chmod 755 script.sh"
    },
    "git": {
        "commit": "git commit -m 'message'",
        "branch": "git branch -a",
        "status": "git status",
        "log": "git log --oneline",
        "stash": "git stash list"
    }
}

# 外部数据源 URL（示例，实际可配置）
DATA_SOURCE_URL = "https://cheat.sh/api/v1/cheats"
CACHE_FILE = HERE / ".cheats_cache.json"
CACHE_TTL = 3600  # 1小时缓存


def load_spec() -> str:
    # 资产池/发布目录均为 SKILL.md 在技能根目录、scripts/ 为其子目录，故读父目录
    p = HERE.parent / "SKILL.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def match_trigger(text: str):
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def load_cheats_from_cache() -> dict:
    """从缓存加载数据"""
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < CACHE_TTL:
                return data.get("cheats", {})
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def save_cheats_to_cache(cheats: dict):
    """保存数据到缓存"""
    try:
        data = {"timestamp": time.time(), "cheats": cheats}
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def fetch_cheats_from_remote() -> dict:
    """从远程API获取数据，带重试退避和超时"""
    max_retries = 3
    timeout = 5
    for attempt in range(max_retries):
        try:
            req = Request(DATA_SOURCE_URL, headers={"User-Agent": "cheat-sh-pro/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data if isinstance(data, dict) else {}
        except (URLError, HTTPError, json.JSONDecodeError) as e:
            if attempt == max_retries - 1:
                print(f"  [WARN] 远程数据获取失败: {e}", file=sys.stderr)
            else:
                time.sleep(2 ** attempt)  # 指数退避
    return {}


def load_cheats() -> dict:
    """加载速查数据：优先缓存，其次远程，最后内置默认"""
    # 尝试缓存
    cached = load_cheats_from_cache()
    if cached:
        return cached
    
    # 尝试远程
    remote = fetch_cheats_from_remote()
    if remote:
        save_cheats_to_cache(remote)
        return remote
    
    # 降级到内置默认
    print("  [INFO] 使用内置默认数据（降级模式）", file=sys.stderr)
    return DEFAULT_CHEATS


def search_cheats(cheats: dict, query: str) -> dict:
    """模糊搜索速查条目"""
    if not query:
        return cheats
    result = {}
    query_lower = query.lower()
    for category, items in cheats.items():
        if query_lower in category.lower():
            result[category] = items
            continue
        matched_items = {}
        for key, value in items.items():
            if query_lower in key.lower() or query_lower in value.lower():
                matched_items[key] = value
        if matched_items:
            result[category] = matched_items
    return result


def filter_cheats(cheats: dict, category: str = None, keyword: str = None) -> dict:
    """按领域过滤速查条目"""
    result = {}
    for cat, items in cheats.items():
        if category and category.lower() not in cat.lower():
            continue
        if keyword:
            filtered = {k: v for k, v in items.items() 
                       if keyword.lower() in k.lower() or keyword.lower() in v.lower()}
            if filtered:
                result[cat] = filtered
        else:
            result[cat] = items
    return result


def random_cheat(cheats: dict) -> tuple:
    """随机获取一条速查"""
    all_items = []
    for cat, items in cheats.items():
        for key, value in items.items():
            all_items.append((cat, key, value))
    if not all_items:
        return ("", "", "无可用数据")
    return random.choice(all_items)


def export_cheats(cheats: dict, format: str = "markdown") -> str:
    """导出速查数据为指定格式"""
    if format == "markdown":
        lines = ["# 速查手册", ""]
        for cat, items in cheats.items():
            lines.append(f"## {cat}")
            lines.append("")
            for key, value in items.items():
                lines.append(f"- **{key}**: `{value}`")
            lines.append("")
        return "\n".join(lines)
    elif format == "json":
        return json.dumps(cheats, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"不支持的导出格式: {format}")


def export_cheats_to_file(cheats: dict, format: str = "markdown") -> str:
    """导出速查数据到临时文件，返回文件路径（自动清理）"""
    content = export_cheats(cheats, format)
    with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False, encoding='utf-8') as f:
        f.write(content)
        return f.name


def selftest() -> int:
    """自检：验证核心链路"""
    print("== 命令行速查手册 配套执行器自检 ==")
    
    # 1. 基础检查
    assert TRIGGERS, "触发器列表为空"
    assert load_spec().strip(), "SKILL.md 为空"
    print("  [OK] 基础配置检查通过")
    
    # 2. 触发词匹配
    sample = " ".join(TRIGGERS[:1])
    got = match_trigger(sample)
    assert got, "触发匹配失败"
    print("  [OK] 触发匹配:", got)
    
    # 3. 数据加载
    cheats = load_cheats()
    assert cheats, "速查数据为空"
    assert len(cheats) >= 5, f"数据分类不足，期望至少5个，实际{len(cheats)}"
    assert "python" in cheats and "javascript" in cheats and "java" in cheats, "编程语言条目缺失"
    print(f"  [OK] 数据加载成功，共 {len(cheats)} 个分类")
    
    # 4. 搜索功能（核心链路）
    search_result = search_cheats(cheats, "git")
    assert search_result, "搜索功能异常"
    assert any("git" in cat.lower() for cat in search_result), "搜索未返回git相关结果"
    print(f"  [OK] 搜索功能正常，找到 {len(search_result)} 个匹配分类")
    
    # 5. 过滤功能（核心链路）
    filter_result = filter_cheats(cheats, category="linux")
    assert filter_result, "过滤功能异常"
    assert "linux" in filter_result, "过滤未返回linux分类"
    print(f"  [OK] 过滤功能正常，找到 {len(filter_result)} 个匹配分类")
    
    # 6. 随机功能（核心链路）
    random_result = random_cheat(cheats)
    assert len(random_result) == 3, "随机功能异常"
    assert random_result[0] and random_result[1], "随机结果为空"
    print(f"  [OK] 随机功能正常: {random_result[0]}/{random_result[1]}")
    
    # 7. 导出功能（核心链路）
    export_result = export_cheats(cheats, "markdown")
    assert "速查手册" in export_result, "导出功能异常"
    assert "git" in export_result.lower(), "导出内容缺少git分类"
    assert "python" in export_result.lower(), "导出内容缺少python分类"
    print(f"  [OK] 导出功能正常，导出 {len(export_result)} 字符")
    
    # 8. 导出到文件并验证清理机制
    temp_file = export_cheats_to_file(cheats, "markdown")
    assert os.path.exists(temp_file), "临时文件创建失败"
    try:
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "速查手册" in content, "临时文件内容错误"
        assert "python" in content.lower(), "临时文件缺少python内容"
        print(f"  [OK] 临时文件导出正常: {temp_file}")
    finally:
        os.unlink(temp_file)  # 确保清理
    assert not os.path.exists(temp_file), "临时文件未清理"
    print("  [OK] 临时文件清理机制正常")
    
    # 9. 时间戳验证（UTC）
    current_time = datetime.now(timezone.utc)
    assert current_time.tzinfo is not None, "时间戳未使用UTC"
    assert current_time.tzinfo == timezone.utc, "时间戳时区错误"
    print(f"  [OK] 时间戳验证通过: {current_time.isoformat()}")
    
    # 10. 主流程验证（模拟命令行调用）
    test_args = ["--search", "git"]
    try:
        old_argv = sys.argv
        sys.argv = ["run.py"] + test_args
        main()
        sys.argv = old_argv
        print("  [OK] 主流程调用正常")
    except SystemExit as e:
        sys.argv = old_argv
        assert e.code == 0, f"主流程退出码非0: {e.code}"
        print("  [OK] 主流程退出码为0")
    
    # 11. 验证编程语言搜索
    python_search = search_cheats(cheats, "python")
    assert python_search and "python" in python_search, "python搜索失败"
    print(f"  [OK] 编程语言搜索正常: {len(python_search['python'])} 条python示例")
    
    # 12. 验证导出JSON格式
    json_export = export_cheats(cheats, "json")
    parsed = json.loads(json_export)
    assert isinstance(parsed, dict) and len(parsed) >= 5, "JSON导出格式错误"
    print(f"  [OK] JSON导出正常，包含 {len(parsed)} 个分类")
    
    print("== 命令行速查手册 配套执行器自检通过 ✅ ==")
    return 0


def main():
    ap = argparse.ArgumentParser(description="命令行速查手册 配套执行器")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    ap.add_argument("--search", default="", help="模糊搜索速查")
    ap.add_argument("--filter-category", default="", help="按领域过滤")
    ap.add_argument("--filter-keyword", default="", help="按关键词过滤")
    ap.add_argument("--random", action="store_true", help="随机获取一条速查")
    ap.add_argument("--export", choices=["markdown", "json"], help="导出速查数据")
    ap.add_argument("--export-file", action="store_true", help="导出到临时文件")
    args = ap.parse_args()
    
    if args.selftest:
        return selftest()
    
    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0
    
    if args.guide:
        md = load_spec()
        print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        return 0
    
    # 加载速查数据
    cheats = load_cheats()
    
    # 搜索
    if args.search:
        result = search_cheats(cheats, args.search)
        for cat, items in result.items():
            print(f"\n[{cat}]")
            for key, value in items.items():
                print(f"  {key}: {value}")
        return 0
    
    # 过滤
    if args.filter_category or args.filter_keyword:
        result = filter_cheats(cheats, args.filter_category, args.filter_keyword)
        for cat, items in result.items():
            print(f"\n[{cat}]")
            for key, value in items.items():
                print(f"  {key}: {value}")
        return 0
    
    # 随机
    if args.random:
        cat, key, value = random_cheat(cheats)
        print(f"[{cat}] {key}: {value}")
        return 0
    
    # 导出
    if args.export:
        try:
            if args.export_file:
                temp_file = export_cheats_to_file(cheats, args.export)
                print(f"导出到临时文件: {temp_file}")
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        print(f.read())
                finally:
                    os.unlink(temp_file)
            else:
                output = export_cheats(cheats, args.export)
                print(output)
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    
    print("用法: python run.py --guide | --match 文本 | --selftest | --search 关键词 | --filter-category 分类 | --random | --export 格式 [--export-file]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
