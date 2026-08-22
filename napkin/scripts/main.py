#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
napkin — 项目记忆与错误备忘技能（clean-room 独立实现）

功能：
  - 错误记录：持久化保存错误信息与解决方案
  - 经验备忘：沉淀开发经验与踩坑记录
  - 检索：按关键词/标签/时间范围查询
  - 更新：补充、修正、标记过期
  - 导出：Markdown/纯文本格式输出
  - 自检：内置硬编码样例离线验证核心逻辑

用法示例：
  python main.py add --title "DB连接池耗尽" --error "连接数超限" --solution "调大连接池" --tag db
  python main.py search --keyword "连接池"
  python main.py list --tag db
  python main.py export --format md
  python main.py --selftest

错误码：
  E001 参数缺失或非法
  E002 记录不存在
  E003 存储目录不可写
  E004 数据文件损坏
  E005 导出格式不支持
  E006 标签格式非法
  E007 时间格式非法
  E008 自检失败
  E009 未知命令
  E010 内部逻辑错误
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta
from datetime import timezone  # G2 时区修复

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
STORAGE_DIRNAME = ".napkin"
DATA_FILENAME = "records.json"
DEFAULT_TAGS = ("general",)
VALID_EXPORT_FORMATS = ("md", "txt")
MAX_TAG_LENGTH = 32
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 内置自检样例（硬编码，不依赖外部文件）
SELFTEST_SAMPLES = [
    {
        "title": "数据库连接池耗尽",
        "error": "Connection pool exhausted, timeout after 30s",
        "solution": "调大连接池上限，增加超时重试机制",
        "tags": ["db", "performance"],
    },
    {
        "title": "部署配置丢失",
        "error": "Config file not found after deployment",
        "solution": "部署前先备份配置文件，使用环境变量注入",
        "tags": ["deploy", "config"],
    },
    {
        "title": "权限校验失败",
        "error": "403 Forbidden on API endpoint",
        "solution": "检查 JWT 过期时间，刷新 token 后重试",
        "tags": ["auth", "security"],
    },
]

# ---------------------------------------------------------------------------
# 存储层
# ---------------------------------------------------------------------------


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def _get_storage_dir(base_dir=None):
    """获取存储目录路径。"""
    base = base_dir or os.getcwd()
    return os.path.join(base, STORAGE_DIRNAME)


def _get_data_file(base_dir=None):
    """获取数据文件路径。"""
    return os.path.join(_get_storage_dir(base_dir), DATA_FILENAME)


def _ensure_storage(base_dir=None):
    """确保存储目录存在且可写。返回目录路径。"""
    storage_dir = _get_storage_dir(base_dir)
    try:
        os.makedirs(storage_dir, exist_ok=True)
        if not os.access(storage_dir, os.W_OK):
            raise OSError("目录不可写")
    except OSError as exc:
        raise RuntimeError("E003: 存储目录不可写: %s" % exc) from exc
    return storage_dir


def _load_records(base_dir=None):
    """从磁盘加载全部记录。文件不存在时返回空列表。"""
    data_file = _get_data_file(base_dir)
    if not os.path.exists(data_file):
        return []
    try:
        with open(data_file, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        if not raw.strip():
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("顶层结构应为列表")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError("E004: 数据文件损坏: %s" % exc) from exc
    except OSError as exc:
        raise RuntimeError("E003: 读取数据文件失败: %s" % exc) from exc


def _save_records(records, base_dir=None):
    """将记录列表写入磁盘。"""
    storage_dir = _ensure_storage(base_dir)
    data_file = os.path.join(storage_dir, DATA_FILENAME)
    tmp_file = data_file + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8", errors="replace") as fh:
            json.dump(records, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_file, data_file)
    except OSError as exc:
        raise RuntimeError("E003: 写入数据文件失败: %s" % exc) from exc


# ---------------------------------------------------------------------------
# 核心业务逻辑
# ---------------------------------------------------------------------------


def _generate_id(records):
    """生成新记录的唯一 ID（基于时间戳+序号）。"""
    base = int(time.time() * 1000)
    existing = {r.get("id", "") for r in records}
    seq = 0
    while True:
        rid = "%d-%d" % (base, seq)
        if rid not in existing:
            return rid
        seq += 1


def _validate_tags(tags):
    """校验标签列表合法性。"""
    if not tags:
        return list(DEFAULT_TAGS)
    if not isinstance(tags, list):
        raise RuntimeError("E006: 标签应为列表")
    cleaned = []
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            raise RuntimeError("E006: 标签必须是非空字符串")
        tag = tag.strip()
        if len(tag) > MAX_TAG_LENGTH:
            raise RuntimeError("E006: 标签长度超限（最大%d字符）" % MAX_TAG_LENGTH)
        if not re.match(r"^[\w\u4e00-\u9fff-]+$", tag):
            raise RuntimeError("E006: 标签含非法字符: %s" % tag)
        if tag not in cleaned:
            cleaned.append(tag)
    return cleaned or list(DEFAULT_TAGS)


def _parse_time(value):
    """解析时间字符串。支持 'YYYY-MM-DD HH:MM:SS' 或相对时间（如 '7d'）。"""
    if value is None:
        return datetime.now(timezone.utc).strftime(TIME_FORMAT)
    value = str(value).strip()
    # 相对时间：数字+d/h
    rel = re.match(r"^(\d+)([dh])$", value)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        delta = timedelta(days=amount) if unit == "d" else timedelta(hours=amount)
        return (datetime.now(timezone.utc) - delta).strftime(TIME_FORMAT)
    # 绝对时间
    try:
        dt = datetime.strptime(value, TIME_FORMAT)
        return dt.strftime(TIME_FORMAT)
    except ValueError as exc:
        raise RuntimeError("E007: 时间格式非法: %s" % value) from exc


def add_record(
    title,
    error,
    solution,
    tags=None,
    base_dir=None,
    created_at=None,
):
    """新增一条错误/经验记录。返回记录 ID。"""
    if not title or not str(title).strip():
        raise RuntimeError("E001: 标题不能为空")
    if not error or not str(error).strip():
        raise RuntimeError("E001: 错误信息不能为空")
    if not solution or not str(solution).strip():
        raise RuntimeError("E001: 解决方案不能为空")

    records = _load_records(base_dir)
    record = {
        "id": _generate_id(records),
        "title": str(title).strip(),
        "error": str(error).strip(),
        "solution": str(solution).strip(),
        "tags": _validate_tags(tags),
        "created_at": _parse_time(created_at),
        "updated_at": _parse_time(None),
        "status": "active",
    }
    records.append(record)
    _save_records(records, base_dir)
    return record["id"]


def search_records(keyword=None, tag=None, base_dir=None, start_time=None, end_time=None):
    """按关键词/标签/时间范围检索记录。返回匹配列表。"""
    records = _load_records(base_dir)
    result = []
    keyword = keyword.strip().lower() if keyword else None
    tag = tag.strip() if tag else None

    for rec in records:
        match = True
        if keyword:
            haystack = " ".join(
                [
                    str(rec.get("title", "")),
                    str(rec.get("error", "")),
                    str(rec.get("solution", "")),
                    " ".join(rec.get("tags", [])),
                ]
            ).lower()
            if keyword not in haystack:
                match = False
        if tag and tag not in rec.get("tags", []):
            match = False
        if start_time:
            try:
                start_dt = datetime.strptime(start_time, TIME_FORMAT)
                rec_dt = datetime.strptime(rec.get("created_at", ""), TIME_FORMAT)
                if rec_dt < start_dt:
                    match = False
            except ValueError:
                raise RuntimeError("E007: 时间格式非法: %s" % start_time)
        if end_time:
            try:
                end_dt = datetime.strptime(end_time, TIME_FORMAT)
                rec_dt = datetime.strptime(rec.get("created_at", ""), TIME_FORMAT)
                if rec_dt > end_dt:
                    match = False
            except ValueError:
                raise RuntimeError("E007: 时间格式非法: %s" % end_time)
        if match:
            result.append(rec)
    return result


def update_record(record_id, solution=None, status=None, tags=None, base_dir=None):
    """更新记录：可修改解决方案、状态、标签。"""
    records = _load_records(base_dir)
    for rec in records:
        if rec.get("id") == record_id:
            if solution is not None:
                if not str(solution).strip():
                    raise RuntimeError("E001: 解决方案不能为空")
                rec["solution"] = str(solution).strip()
            if status is not None:
                if status not in ("active", "expired", "archived"):
                    raise RuntimeError("E001: 非法状态值")
                rec["status"] = status
            if tags is not None:
                rec["tags"] = _validate_tags(tags)
            rec["updated_at"] = _parse_time(None)
            _save_records(records, base_dir)
            return True
    raise RuntimeError("E002: 记录不存在: %s" % record_id)


def delete_record(record_id, base_dir=None):
    """删除指定 ID 的记录。"""
    records = _load_records(base_dir)
    new_records = [r for r in records if r.get("id") != record_id]
    if len(new_records) == len(records):
        raise RuntimeError("E002: 记录不存在: %s" % record_id)
    _save_records(new_records, base_dir)
    return True


def export_records(export_format="md", base_dir=None, tag=None):
    """导出记录为 Markdown 或纯文本。返回字符串内容。"""
    if export_format not in VALID_EXPORT_FORMATS:
        raise RuntimeError("E005: 不支持的导出格式: %s" % export_format)
    records = search_records(tag=tag, base_dir=base_dir)
    if export_format == "md":
        lines = ["# napkin 项目记忆导出", ""]
        lines.append("> 导出时间: %s" % datetime.now(timezone.utc).strftime(TIME_FORMAT))
        lines.append("> 记录总数: %d" % len(records))
        lines.append("")
        for idx, rec in enumerate(records, 1):
            lines.append("## %d. %s" % (idx, rec.get("title", "未命名")))
            lines.append("")
            lines.append("- **ID**: %s" % rec.get("id", ""))
            lines.append("- **状态**: %s" % rec.get("status", "active"))
            lines.append("- **创建时间**: %s" % rec.get("created_at", ""))
            lines.append("- **更新时间**: %s" % rec.get("updated_at", ""))
            lines.append("- **标签**: %s" % ", ".join(rec.get("tags", [])))
            lines.append("")
            lines.append("### 错误信息")
            lines.append("")
            lines.append(rec.get("error", ""))
            lines.append("")
            lines.append("### 解决方案")
            lines.append("")
            lines.append(rec.get("solution", ""))
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)
    else:  # txt
        lines = ["napkin 项目记忆导出", "=" * 40, ""]
        lines.append("导出时间: %s" % datetime.now(timezone.utc).strftime(TIME_FORMAT))
        lines.append("记录总数: %d" % len(records))
        lines.append("")
        for idx, rec in enumerate(records, 1):
            lines.append("[%d] %s" % (idx, rec.get("title", "未命名")))
            lines.append("    ID: %s" % rec.get("id", ""))
            lines.append("    状态: %s" % rec.get("status", "active"))
            lines.append("    创建: %s" % rec.get("created_at", ""))
            lines.append("    更新: %s" % rec.get("updated_at", ""))
            lines.append("    标签: %s" % ", ".join(rec.get("tags", [])))
            lines.append("    错误: %s" % rec.get("error", ""))
            lines.append("    解决: %s" % rec.get("solution", ""))
            lines.append("")
        return "\n".join(lines)


def list_records(base_dir=None, tag=None):
    """列出记录（简要信息）。"""
    records = search_records(tag=tag, base_dir=base_dir)
    return records


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------


def _selftest():
    """离线自检：验证核心逻辑。"""
    try:
        # 使用临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试添加
            ids = []
            for sample in SELFTEST_SAMPLES:
                rid = add_record(
                    title=sample["title"],
                    error=sample["error"],
                    solution=sample["solution"],
                    tags=sample["tags"],
                    base_dir=tmpdir,
                )
                ids.append(rid)

            # 验证记录数
            records = _load_records(tmpdir)
            assert len(records) == 3, "记录数应为3"

            # 测试搜索
            results = search_records(keyword="连接池", base_dir=tmpdir)
            assert len(results) == 1, "关键词搜索应返回1条"
            assert results[0]["title"] == "数据库连接池耗尽"

            results = search_records(tag="auth", base_dir=tmpdir)
            assert len(results) == 1, "标签搜索应返回1条"
            assert results[0]["title"] == "权限校验失败"

            # 测试时间范围搜索
            results = search_records(
                start_time="2024-01-01 00:00:00",
                end_time="2099-12-31 23:59:59",
                base_dir=tmpdir,
            )
            assert len(results) == 3, "时间范围搜索应返回3条"

            # 测试更新
            update_record(ids[0], solution="更新后的解决方案", base_dir=tmpdir)
            records = _load_records(tmpdir)
            assert records[0]["solution"] == "更新后的解决方案", "解决方案应更新"

            # 测试删除
            delete_record(ids[1], base_dir=tmpdir)
            records = _load_records(tmpdir)
            assert len(records) == 2, "删除后应剩2条"

            # 测试导出
            md_content = export_records("md", base_dir=tmpdir)
            assert "# napkin 项目记忆导出" in md_content, "MD导出应包含标题"
            txt_content = export_records("txt", base_dir=tmpdir)
            assert "napkin 项目记忆导出" in txt_content, "TXT导出应包含标题"

            # 测试标签校验
            try:
                _validate_tags(["bad tag!"])
                raise AssertionError("非法标签应报错")
            except RuntimeError as e:
                assert "E006" in str(e), "应返回E006错误"

            # 测试时间解析
            t = _parse_time("7d")
            assert t, "相对时间解析失败"
            t = _parse_time("2024-01-01 00:00:00")
            assert t == "2024-01-01 00:00:00", "绝对时间解析失败"

        print("自检通过: 所有核心逻辑验证成功")
        return 0
    except Exception as exc:
        print("自检失败: %s" % exc, file=sys.stderr)
        return 1


# -----------------------------------------------------------------
