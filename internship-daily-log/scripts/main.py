#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实习日志结构化整理工具（internship-daily-log）

功能：将杂乱实习笔记转换为结构化日志，支持批量处理与置信度标注。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法示例：
    python scripts/main.py --input note.txt --format md
    python scripts/main.py --selftest
"""

import argparse
import json
import re
import sys
from datetime import timezone, datetime, timedelta
from typing import Any, Dict, List, Optional


# ============================================================
# 错误码定义 (E001-E010)
# ============================================================
ERROR_CODES = {
    "E001": "输入内容为空或无法识别任何记录",
    "E002": "输入文件不存在或无法读取",
    "E003": "输出格式不支持（仅支持 md/json/txt）",
    "E004": "单批次记录数超过50条上限",
    "E005": "日期范围过滤参数格式错误（应为 YYYY-MM-DD）",
    "E006": "状态筛选参数无效（应为 进行中/已完成/阻塞）",
    "E007": "字段别名配置格式错误",
    "E008": "内部解析错误：无法从文本提取有效字段",
    "E009": "JSON 序列化失败",
    "E010": "未知错误",
}


class DailyLogError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

# 预设字段名（规格中定义的可识别字段）
FIELD_NAMES = ["date", "task", "owner", "status", "deliverable", "blocker"]

# 状态映射（支持中英文别名归一化）
STATUS_ALIASES = {
    "进行中": "进行中",
    "in progress": "进行中",
    "ongoing": "进行中",
    "已完成": "已完成",
    "done": "已完成",
    "completed": "已完成",
    "阻塞": "阻塞",
    "blocked": "阻塞",
    "block": "阻塞",
}

# 时间/日期模式（宽松匹配）
DATE_PATTERNS = [
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?",  # 2024-01-01 / 2024/1/1 / 2024年1月1日
    r"\d{1,2}[-/月]\d{1,2}日?",  # 1-5 / 1/5 / 1月5日
    r"今天|昨天|前天|今日|昨日",  # 相对日期
]

# 默认字段别名（用户可自定义覆盖）
DEFAULT_ALIASES = {
    "date": ["日期", "时间", "date", "time", "when"],
    "task": ["任务", "工作内容", "事项", "task", "todo", "what"],
    "owner": ["负责人", "执行人", "owner", "who", "assignee"],
    "status": ["状态", "进度", "status", "state"],
    "deliverable": ["产出物", "成果", "交付物", "deliverable", "output"],
    "blocker": ["阻塞项", "问题", "风险", "blocker", "risk", "issue"],
}


# ============================================================
# 工具函数
# ============================================================

def normalize_status(raw: str) -> str:
    """将状态文本归一化为标准状态值。"""
    if not raw:
        return "进行中"
    key = raw.strip().lower()
    for alias, standard in STATUS_ALIASES.items():
        if key == alias.lower():
            return standard
    # 模糊匹配：包含关键词
    if "完成" in raw or "done" in raw.lower():
        return "已完成"
    if "阻塞" in raw or "block" in raw.lower():
        return "阻塞"
    return "进行中"


def extract_date(text: str) -> Optional[str]:
    """从文本中提取日期，返回标准 YYYY-MM-DD 格式或相对日期描述。"""
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            raw = match.group()
            # 处理相对日期
            if raw in ("今天", "今日"):
                return datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if raw in ("昨天", "昨日"):
                return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            if raw == "前天":
                return (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
            # 处理绝对日期
            try:
                raw_clean = raw.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
                # 补全年份
                parts = raw_clean.split("-")
                if len(parts) == 2:  # 只有月-日
                    now = datetime.now(timezone.utc)
                    parts = [str(now.year)] + parts
                if len(parts) == 3:
                    year = int(parts[0])
                    month = int(parts[1])
                    day = int(parts[2])
                    # 宽松校验：年份 2000-2100，月份 1-12，日期 1-31
                    if 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                        return f"{year:04d}-{month:02d}-{day:02d}"
            except (ValueError, IndexError):
                continue
    return None


def parse_field_value(text: str, field: str, aliases: Dict[str, List[str]]) -> Optional[str]:
    """根据别名从文本中提取指定字段的值。"""
    field_aliases = aliases.get(field, DEFAULT_ALIASES.get(field, []))
    for alias in field_aliases:
        # 匹配 "别名: 值" 或 "别名：值"
        pattern = rf"{re.escape(alias)}\s*[:：]\s*([^\n,;，；]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def split_records(text: str) -> List[str]:
    """将原始文本拆分为多条记录。
    按空行或常见分隔符（如序号、时间前缀）拆分。
    """
    # 先按空行拆分
    blocks = re.split(r"\n\s*\n", text.strip())
    records = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        # 如果块内包含多个时间标记，进一步拆分
        lines = block.split("\n")
        current = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 判断是否为新记录的开始
            # 新记录开始的条件：
            # 1. 行包含日期标记
            # 2. 行包含任务/工作内容标记（如 "任务:"、"工作内容:" 等）
            # 3. 行以序号开头（如 "1."、"2、" 等）
            # 4. 当前已有内容，且新行包含字段标记（如 "负责人:" 等）
            is_new_record = False
            
            if current:  # 当前已有内容
                if extract_date(line):
                    is_new_record = True
                elif re.match(r"^\d+\s*[.、)]", line):  # 序号开头
                    is_new_record = True
                elif parse_field_value(line, "task", DEFAULT_ALIASES):
                    is_new_record = True
                elif re.match(r"^(任务|工作内容|事项|task|todo|what)\s*[:：]", line, re.IGNORECASE):
                    is_new_record = True
            
            if is_new_record:
                records.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        
        if current:
            records.append("\n".join(current))
    
    # 如果没有通过上述方式拆分，尝试按行拆分（每行一条记录）
    if not records:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if lines:
            records = lines
    
    return records


def parse_record(text: str, aliases: Dict[str, List[str]]) -> Dict[str, Any]:
    """解析单条记录文本为结构化字典。"""
    if not text or not text.strip():
        raise DailyLogError("E008")

    record: Dict[str, Any] = {}
    confidence = 0.0
    total_fields = 0

    # 提取日期
    date = extract_date(text)
    if date:
        record["date"] = date
        total_fields += 1
        confidence += 0.3
    else:
        record["date"] = None

    # 提取任务描述（核心字段）
    task = parse_field_value(text, "task", aliases)
    if not task:
        # 尝试从文本中提取第一行作为任务描述
        first_line = text.strip().split("\n")[0].strip()
        # 去掉日期前缀
        if extract_date(first_line):
            first_line = re.sub(r"^\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?\s*", "", first_line)
        # 去掉序号前缀
        first_line = re.sub(r"^\d+\s*[.、)]\s*", "", first_line)
        # 去掉常见的字段标签
        for field_name in ["任务", "工作内容", "事项", "task", "todo", "what"]:
            first_line = re.sub(rf"^{field_name}\s*[:：]\s*", "", first_line, flags=re.IGNORECASE)
        if first_line:
            task = first_line
    if task:
        record["task"] = task
        total_fields += 1
        confidence += 0.3
    else:
        record["task"] = ""

    # 提取负责人
    owner = parse_field_value(text, "owner", aliases)
    if owner:
        record["owner"] = owner
        total_fields += 1
        confidence += 0.15

    # 提取状态
    status = parse_field_value(text, "status", aliases)
    if status:
        record["status"] = normalize_status(status)
        total_fields += 1
        confidence += 0.1
    else:
        record["status"] = "进行中"

    # 提取产出物
    deliverable = parse_field_value(text, "deliverable", aliases)
    if deliverable:
        record["deliverable"] = deliverable
        total_fields += 1
        confidence += 0.1

    # 提取阻塞项
    blocker = parse_field_value(text, "blocker", aliases)
    if blocker:
        record["blocker"] = blocker
        total_fields += 1
        confidence += 0.05

    # 计算置信度（基于字段覆盖率）
    record["confidence"] = round(min(confidence, 1.0), 2)

    # 校验：至少要有日期或任务之一
    if not record.get("date") and not record.get("task"):
        raise DailyLogError("E008")

    return record


def process_text(text: str, aliases: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
    """处理原始文本，返回结构化记录列表。"""
    if not text or not text.strip():
        raise DailyLogError("E001")

    aliases = aliases or DEFAULT_ALIASES

    # 拆分记录
    raw_records = split_records(text)
    
    # 如果没有成功拆分，尝试按行拆分
    if len(raw_records) <= 1:
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if len(lines) > 1:
            raw_records = lines
    
    if not raw_records:
        raise DailyLogError("E001")

    # 批量限制检查
    if len(raw_records) > 50:
        raise DailyLogError("E004")

    # 逐条解析
    records = []
    for raw in raw_records:
        try:
            record = parse_record(raw, aliases)
            records.append(record)
        except DailyLogError:
            # 单条解析失败则跳过（保持宽容）
            continue

    if not records:
        raise DailyLogError("E001")

    return records


def filter_records(records: List[Dict[str, Any]], date_from: Optional[str] = None,
                   date_to: Optional[str] = None, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """按日期范围和状态过滤记录。"""
    result = records

    # 日期过滤
    if date_from or date_to:
        filtered = []
        for rec in result:
            rec_date = rec.get("date")
            if not rec_date:
                continue
            if date_from and rec_date < date_from:
                continue
            if date_to and rec_date > date_to:
                continue
            filtered.append(rec)
        result = filtered

    # 状态过滤
    if status_filter:
        status_filter_norm = normalize_status(status_filter)
        result = [rec for rec in result if rec.get("status") == status_filter_norm]

    return result


# ============================================================
# 输出格式化
# ============================================================

def format_markdown(records: List[Dict[str, Any]]) -> str:
    """输出为 Markdown 表格。"""
    if not records:
        return "（无记录）"

    lines = ["| 日期 | 任务 | 负责人 | 状态 | 产出物 | 阻塞项 | 置信度 |",
             "|------|------|--------|------|--------|--------|--------|"]
    for rec in records:
        lines.append(
            f"| {rec.get('date') or '-'} | {rec.get('task') or '-'} | "
            f"{rec.get('owner') or '-'} | {rec.get('status') or '-'} | "
            f"{rec.get('deliverable') or '-'} | {rec.get('blocker') or '-'} | "
            f"{rec.get('confidence', 0):.0%} |"
        )
    return "\n".join(lines)


def format_json(records: List[Dict[str, Any]]) -> str:
    """输出为 JSON。"""
    try:
        return json.dumps({"records": records}, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as exc:
        raise DailyLogError("E009", f"JSON 序列化失败: {exc}")


def format_text(records: List[Dict[str, Any]]) -> str:
    """输出为纯文本清单。"""
    if not records:
        return "（无记录）"

    lines = []
    for i, rec in enumerate(records, 1):
        lines.append(f"[{i}] 日期: {rec.get('date') or '未知'}")
        lines.append(f"    任务: {rec.get('task') or '未知'}")
        lines.append(f"    负责人: {rec.get('owner') or '未知'}")
        lines.append(f"    状态: {rec.get('status') or '未知'}")
        lines.append(f"    产出物: {rec.get('deliverable') or '无'}")
        lines.append(f"    阻塞项: {rec.get('blocker') or '无'}")
        lines.append(f"    置信度: {rec.get('confidence', 0):.0%}")
        lines.append("")
    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检。不读外部文件、不依赖目录、不访问网络。"""
    print("=== 实习日志 Skill 自检开始 ===")

    # 硬编码测试样例
    sample_text = """
    2026-03-10 完成用户登录模块开发
    负责人: 张三
    状态: 已完成
    产出物: 登录接口文档

    2026-03-11 修复支付回调 bug
    负责人: 李四
    状态: 阻塞
    阻塞项: 等待第三方接口响应

    今天 整理项目周报
    负责人: 王五
    产出物: 周报文档
    """

    expected_min_count = 3  # 至少解析出3条记录

    try:
        # 1. 基础解析测试
        records = process_text(sample_text)
        assert len(records) >= expected_min_count, f"解析记录数不足，期望>={expected_min_count}，实际={len(records)}"
        print(f"[PASS] 基础解析: 成功解析 {len(records)} 条记录")

        # 2. 字段完整性测试
        for rec in records:
            assert "task" in rec and rec["task"], "记录缺少任务字段"
            assert "status" in rec, "记录缺少状态字段"
            assert 0.0 <= rec.get("confidence", 0) <= 1.0, "置信度超出范围"
        print("[PASS] 字段完整性: 所有记录包含必要字段，置信度在有效范围")

        # 3. 状态归一化测试
        statuses = [rec["status"] for rec in records]
        for s in statuses:
            assert s in ("进行中", "已完成", "阻塞"), f"状态值非法: {s}"
        assert "已完成" in statuses, "应包含已完成状态"
        print(f"[PASS] 状态归一化: 状态值合法 {set(statuses)}")

        # 4. 日期提取测试
        dates = [rec.get("date") for rec in records]
        assert any(d for d in dates), "应至少提取到一个日期"
        # 宽松验证日期格式
        for d in dates:
            if d:
                assert re.match(r"^\d{4}-\d{2}-\d{2}$", d), f"日期格式异常: {d}"
        print(f"[PASS] 日期提取: {dates}")

        # 5. 批量限制测试
        too_many = "\n".join([f"任务{i}" for i in range(51)])
        try:
            process_text(too_many)
            assert False, "应触发 E004 批量限制错误"
        except DailyLogError as e:
            assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"
        print("[PASS] 批量限制: 超过50条正确触发 E004")

        # 6. 空输入测试
        try:
            process_text("")
            assert False, "应触发 E001 空输入错误"
        except DailyLogError as e:
            assert e.code == "E001", f"错误码应为 E001，实际 {e.code}"
        print("[PASS] 空输入处理: 正确触发 E001")

        # 7. 过滤功能测试
        filtered = filter_records(records, status_filter="已完成")
        assert len(filtered) >= 1, "按状态过滤应至少返回1条"
        for rec in filtered:
            assert rec["status"] == "已完成", "过滤结果状态不正确"
        print(f"[PASS] 状态过滤: 过滤后 {len(filtered)} 条记录")

        # 8. 输出格式测试
        md = format_markdown(records)
        assert "| 日期 |" in md and "| 任务 |" in md, "Markdown 表格头缺失"
        js = format_json(records)
        json_data = json.loads(js)
        assert "records" in json_data, "JSON 缺少 records 键"
        assert len(json_data["records"]) >= expected_min_count, "JSON 记录数不足"
        txt = format_text(records)
        assert "任务:" in txt, "文本格式缺少任务字段"
        print("[PASS] 输出格式: md/json/txt 三种格式均正常生成")

        print("=== 自检全部通过 ===")
        return True

    except AssertionError as e:
        print(f"[FAIL] 断言失败: {e}")
        return False
    except DailyLogError as e:
        print(f"[FAIL] 业务错误: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] 未知异常: {e}")
        return False


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="实习日志结构化整理工具",
        epilog="示例: python scripts/main.py --input note.txt --format md"
    )
    parser.add_argument("--input", "-i", help="输入文件路径（.txt/.md）")
    parser.add_argument("--text", "-t", help="直接输入文本内容")
    parser.add_argument("--format", "-f", choices=["md", "json", "txt"], default="md",
                        help="输出格式（默认 md）")
    parser.add_argument("--date-from", help="起始日期过滤（YYYY-MM-DD）")
    parser.add_argument("--date-to", help="结束日期过滤（YYYY-MM-DD）")
    parser.add_argument("--status", help="状态过滤（进行中/已完成/阻塞）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--alias-file", help="字段别名配置文件（JSON格式）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 获取输入内容
    input_text = ""
    if args.text:
        input_text = args.text
    elif args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                input_text = f.read()
        except (IOError, OSError) as e:
            print(f"[E002] 无法读取文件: {e}", file=sys.stderr)
            return 2
    else:
        # 从标准输入读取
        input_text = sys.stdin.read()

    # 加载自定义别名（可选）
    aliases = DEFAULT_ALIASES
    if args.alias_file:
        try:
            with open(args.alias_file, "r", encoding="utf-8") as f:
                custom_aliases = json.load(f)
            # 合并到默认别名
            for field, alias_list in custom_aliases.items():
                if field in aliases:
                    aliases[field] = list(set(aliases[field] + alias_list))
                else:
                    aliases[field] = alias_list
        except (IOError, json.JSONDecodeError) as e:
            print(f"[E007] 别名配置错误: {e}", file=sys.stderr)
            return 7

    try:
        # 处理文本
        records = process_text(input_text, aliases)

        # 过滤
        date_from = args.date_from
        date_to = args.date_to
        status_filter = args.status

        # 日期参数校验
        if date_from:
            try:
                datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                print("[E005] 起始日期格式错误", file=sys.stderr)
                return 5
        if date_to:
            try:
                datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                print("[E005] 结束日期格式错误", file=sys.stderr)
                return 5

        records = filter_records(records, date_from, date_to, status_filter)

        # 输出
        if args.format == "md":
            output = format_markdown(records)
        elif args.format == "json":
            output = format_json(records)
        elif args.format == "txt":
            output = format_text(records)
        else:
            raise DailyLogError("E003")

        print(output)
        return 0

    except DailyLogError as e:
        print(f"{e}", file=sys.stderr)
        code_num = int(e.code[1:]) if e.code.startswith("E") else 10
        return code_num
    except Exception as e:
        print(f"[E010] 未知错误: {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
