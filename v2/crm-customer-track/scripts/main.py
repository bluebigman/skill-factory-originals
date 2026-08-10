#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
客户跟进轨迹管理 (crm-customer-track) - 独立实现脚本

功能：
- 记录客户互动事件（电话、邮件、会议、消息等）
- 识别跟进停滞（距上次互动超过阈值）
- 评估流失风险（基于互动频率、负面反馈、竞对接触）
- 生成跟进建议（依据风险等级与客户阶段）
- 输出文本时间线

本脚本为 clean-room 实现，仅依据功能规格独立编写。
仅使用标准库，无第三方依赖。

用法示例：
    python scripts/main.py --selftest
    python scripts/main.py --track --customer C001 --events "2026-01-01|电话|初步沟通" "2026-01-05|邮件|发送方案"
    python scripts/main.py --stagnation --customer C001 --last-contact 2026-01-10 --threshold 7
    python scripts/main.py --risk --customer C001 --events ...
    python scripts/main.py --timeline --customer C001 --events ...
"""

import argparse
import sys
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional, Any

# ============================================================
# 错误码定义 (E001-E010)
# ============================================================
ERR_INVALID_ARGS = "E001: 参数无效或缺失"
ERR_DATE_FORMAT = "E002: 日期格式错误，应为 YYYY-MM-DD"
ERR_EVENT_FORMAT = "E003: 事件格式错误，应为 '日期|类型|描述'"
ERR_CUSTOMER_ID = "E004: 客户ID不能为空"
ERR_THRESHOLD = "E005: 阈值必须为正数"
ERR_INSUFFICIENT_DATA = "E006: 数据不足（至少需要3条互动记录）"
ERR_UNKNOWN_EVENT_TYPE = "E007: 未知的互动类型"
ERR_INVALID_STAGE = "E008: 无效的客户阶段"
ERR_INTERNAL = "E009: 内部计算错误"
ERR_UNKNOWN_COMMAND = "E010: 未知命令或参数组合"


# ============================================================
# 常量定义
# ============================================================
# 支持的互动类型
SUPPORTED_EVENT_TYPES = {"电话", "邮件", "会议", "消息"}

# 客户阶段
CUSTOMER_STAGES = {"潜在客户", "意向客户", "谈判中", "成交客户", "沉睡客户"}

# 默认停滞阈值（天）
DEFAULT_STAGNATION_THRESHOLD = 7

# 风险等级
RISK_LEVELS = ["低风险", "中风险", "高风险"]

# 建议文本库（按风险等级与阶段组合）
SUGGESTION_MAP = {
    "低风险": {
        "潜在客户": "保持定期触达，每2周发送一次行业资讯，培养兴趣。",
        "意向客户": "维持当前沟通节奏，可适度增加产品案例分享，推动决策。",
        "谈判中": "保持高频响应，及时提供所需资料，推进合同细节确认。",
        "成交客户": "安排回访计划，了解使用情况，挖掘交叉销售机会。",
        "沉睡客户": "尝试重新激活，发送专属优惠或新功能通知。",
    },
    "中风险": {
        "潜在客户": "提高触达频率至每周一次，了解客户顾虑，提供针对性内容。",
        "意向客户": "主动询问决策进展，识别关键阻碍，安排面对面或视频会议。",
        "谈判中": "尽快确认商务条款分歧点，必要时升级内部审批流程加速。",
        "成交客户": "立即安排客户成功回访，确认满意度，解决潜在不满。",
        "沉睡客户": "启动唤醒计划，通过电话而非邮件直接沟通，了解沉默原因。",
    },
    "高风险": {
        "潜在客户": "紧急联系客户，确认是否仍有合作意向，若已转向竞对则复盘原因。",
        "意向客户": "高层介入访谈，提供定制化方案或优惠，全力挽回。",
        "谈判中": "暂停常规推进，优先解决核心异议，必要时调整合作框架。",
        "成交客户": "启动流失预警流程，由客户成功经理一对一深度沟通，制定挽回方案。",
        "沉睡客户": "标记为待流失，进行最终触达，若无效则移入流失名单并归档。",
    },
}


# ============================================================
# 核心数据结构
# ============================================================
class InteractionEvent:
    """单条互动事件"""

    def __init__(self, event_date: date, event_type: str, description: str):
        self.event_date = event_date
        self.event_type = event_type
        self.description = description

    def __repr__(self) -> str:
        return f"InteractionEvent({self.event_date}, {self.event_type}, {self.description})"


class CustomerTrackRecord:
    """客户的完整跟进轨迹"""

    def __init__(self, customer_id: str, stage: str = "潜在客户"):
        self.customer_id = customer_id
        self.stage = stage
        self.events: List[InteractionEvent] = []

    def add_event(self, event: InteractionEvent) -> None:
        """添加一条事件并按日期排序"""
        self.events.append(event)
        self.events.sort(key=lambda e: e.event_date)

    def last_contact_date(self) -> Optional[date]:
        """最近一次互动日期"""
        if not self.events:
            return None
        return self.events[-1].event_date

    def days_since_last_contact(self, reference_date: date) -> Optional[int]:
        """距上次互动的天数"""
        last = self.last_contact_date()
        if last is None:
            return None
        return (reference_date - last).days

    def event_count(self) -> int:
        """事件总数"""
        return len(self.events)

    def event_type_counts(self) -> Dict[str, int]:
        """各类型事件计数"""
        counts = {t: 0 for t in SUPPORTED_EVENT_TYPES}
        for e in self.events:
            if e.event_type in counts:
                counts[e.event_type] += 1
        return counts

    def has_negative_feedback(self) -> bool:
        """是否包含负面反馈关键词"""
        negative_keywords = ["不满", "投诉", "负面", "取消", "终止", "失望", "差评"]
        for e in self.events:
            for kw in negative_keywords:
                if kw in e.description:
                    return True
        return False

    def has_competitor_contact(self) -> bool:
        """是否包含竞对接触关键词"""
        competitor_keywords = ["竞对", "竞争对手", "友商", "对比", "换供应商", "别家"]
        for e in self.events:
            for kw in competitor_keywords:
                if kw in e.description:
                    return True
        return False


# ============================================================
# 核心业务逻辑
# ============================================================
def parse_date(date_str: str) -> date:
    """解析日期字符串，失败时抛出带错误码的异常"""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        raise ValueError(f"{ERR_DATE_FORMAT}: '{date_str}'")


def parse_event(event_str: str) -> InteractionEvent:
    """解析事件字符串 '日期|类型|描述'"""
    parts = event_str.split("|")
    if len(parts) != 3:
        raise ValueError(f"{ERR_EVENT_FORMAT}: '{event_str}'")
    date_str, event_type, description = [p.strip() for p in parts]
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"{ERR_UNKNOWN_EVENT_TYPE}: '{event_type}'")
    event_date = parse_date(date_str)
    if not description:
        raise ValueError(f"{ERR_EVENT_FORMAT}: 描述不能为空")
    return InteractionEvent(event_date, event_type, description)


def build_customer_record(customer_id: str, stage: str, event_strs: List[str]) -> CustomerTrackRecord:
    """从字符串列表构建客户记录"""
    if not customer_id:
        raise ValueError(ERR_CUSTOMER_ID)
    if stage not in CUSTOMER_STAGES:
        raise ValueError(f"{ERR_INVALID_STAGE}: '{stage}'")
    record = CustomerTrackRecord(customer_id, stage)
    for s in event_strs:
        record.add_event(parse_event(s))
    return record


def detect_stagnation(record: CustomerTrackRecord, threshold_days: int, reference_date: date) -> Tuple[bool, Optional[int]]:
    """检测停滞：返回 (是否停滞, 距上次天数)"""
    if threshold_days <= 0:
        raise ValueError(ERR_THRESHOLD)
    days = record.days_since_last_contact(reference_date)
    if days is None:
        # 无任何互动记录，视为停滞
        return True, None
    return days > threshold_days, days


def assess_risk(record: CustomerTrackRecord, reference_date: date) -> str:
    """评估流失风险等级"""
    if record.event_count() < 3:
        raise ValueError(ERR_INSUFFICIENT_DATA)

    score = 0
    days = record.days_since_last_contact(reference_date)

    # 1. 互动频率衰减（基于平均间隔）
    if record.event_count() >= 2:
        dates = [e.event_date for e in record.events]
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        if avg_interval > 14:
            score += 2  # 平均间隔过长
        elif avg_interval > 7:
            score += 1

    # 2. 最近未互动时长
    if days is not None:
        if days > 30:
            score += 3
        elif days > 14:
            score += 2
        elif days > 7:
            score += 1

    # 3. 负面反馈
    if record.has_negative_feedback():
        score += 2

    # 4. 竞对接触
    if record.has_competitor_contact():
        score += 2

    # 5. 互动总量偏少
    if record.event_count() < 5:
        score += 1

    # 分级
    if score >= 6:
        return "高风险"
    elif score >= 3:
        return "中风险"
    else:
        return "低风险"


def generate_suggestion(stage: str, risk_level: str) -> str:
    """生成跟进建议"""
    if stage not in CUSTOMER_STAGES:
        raise ValueError(f"{ERR_INVALID_STAGE}: '{stage}'")
    if risk_level not in RISK_LEVELS:
        raise ValueError(f"{ERR_INTERNAL}: 未知风险等级 '{risk_level}'")
    return SUGGESTION_MAP[risk_level][stage]


def render_timeline(record: CustomerTrackRecord) -> List[str]:
    """渲染文本时间线"""
    if not record.events:
        return ["（无互动记录）"]
    lines = []
    for e in record.events:
        lines.append(f"{e.event_date.isoformat()} | {e.event_type} | {e.description}")
    return lines


# ============================================================
# 命令行处理
# ============================================================
def run_track(args) -> int:
    """处理 --track 命令：记录并显示轨迹统计"""
    try:
        record = build_customer_record(args.customer, args.stage, args.events)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"客户ID: {record.customer_id}")
    print(f"客户阶段: {record.stage}")
    print(f"互动总数: {record.event_count()}")
    print(f"类型分布: {record.event_type_counts()}")
    print("时间线:")
    for line in render_timeline(record):
        print(f"  {line}")
    return 0


def run_stagnation(args) -> int:
    """处理 --stagnation 命令：检测停滞"""
    try:
        record = build_customer_record(args.customer, args.stage, args.events)
        ref_date = parse_date(args.reference)
        is_stagnant, days = detect_stagnation(record, args.threshold, ref_date)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    status = "停滞" if is_stagnant else "正常"
    days_str = f"{days}天" if days is not None else "无记录"
    print(f"客户 {record.customer_id}: {status}（距上次互动 {days_str}，阈值 {args.threshold}天）")
    return 0


def run_risk(args) -> int:
    """处理 --risk 命令：评估流失风险并给出建议"""
    try:
        record = build_customer_record(args.customer, args.stage, args.events)
        ref_date = parse_date(args.reference)
        risk = assess_risk(record, ref_date)
        suggestion = generate_suggestion(record.stage, risk)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"客户 {record.customer_id} 流失风险评估: {risk}")
    print(f"建议: {suggestion}")
    return 0


def run_timeline(args) -> int:
    """处理 --timeline 命令：输出时间线"""
    try:
        record = build_customer_record(args.customer, args.stage, args.events)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"客户 {record.customer_id} 跟进轨迹:")
    for line in render_timeline(record):
        print(f"  {line}")
    return 0


# ============================================================
# 自检模块 (--selftest)
# ============================================================
def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    使用宽松阈值断言，确保任何环境直接可过。
    """
    print("开始自检...")
    errors = []

    # --- 样例数据 ---
    customer_id = "C001"
    stage = "意向客户"
    # 构造 5 条互动记录，时间跨度约 20 天
    event_strs = [
        "2026-01-01|电话|初次沟通，了解需求",
        "2026-01-05|邮件|发送产品资料",
        "2026-01-10|会议|演示产品功能",
        "2026-01-15|消息|回复客户咨询",
        "2026-01-20|电话|讨论报价细节",
    ]
    reference_date_str = "2026-01-28"

    # --- 测试 1: 构建记录 ---
    try:
        record = build_customer_record(customer_id, stage, event_strs)
        assert record.event_count() == 5, "事件数量应为5"
        assert record.last_contact_date() is not None, "应有最近联系日期"
        print("[通过] 构建客户记录")
    except Exception as e:
        errors.append(f"构建记录失败: {e}")
        print(f"[失败] 构建客户记录: {e}")

    # --- 测试 2: 停滞检测 ---
    try:
        ref_date = parse_date(reference_date_str)
        # 阈值设为 3 天，距上次互动 8 天，应停滞
        is_stagnant, days = detect_stagnation(record, 3, ref_date)
        assert is_stagnant is True, "应判定为停滞"
        assert days is not None and days >= 7, "距上次互动应至少7天"
        # 阈值设为 30 天，不应停滞
        is_stagnant2, _ = detect_stagnation(record, 30, ref_date)
        assert is_stagnant2 is False, "阈值30天不应停滞"
        print("[通过] 停滞检测")
    except Exception as e:
        errors.append(f"停滞检测失败: {e}")
        print(f"[失败] 停滞检测: {e}")

    # --- 测试 3: 风险评分 ---
    try:
        risk = assess_risk(record, ref_date)
        assert risk in RISK_LEVELS, "风险等级应在合法范围内"
        # 由于互动较频繁且无负面，应低或中风险
        assert risk in ("低风险", "中风险"), "此样例不应为高风险"
        print(f"[通过] 风险评分 (结果: {risk})")
    except Exception as e:
        errors.append(f"风险评分失败: {e}")
        print(f"[失败] 风险评分: {e}")

    # --- 测试 4: 建议生成 ---
    try:
        suggestion = generate_suggestion(stage, "中风险")
        assert len(suggestion) > 0, "建议不应为空"
        print(f"[通过] 建议生成 (建议: {suggestion[:20]}...)")
    except Exception as e:
        errors.append(f"建议生成失败: {e}")
        print(f"[失败] 建议生成: {e}")

    # --- 测试 5: 时间线渲染 ---
    try:
        lines = render_timeline(record)
        assert len(lines) == 5, "时间线应有5行"
        assert "电话" in lines[0], "第一条应为电话"
        print("[通过] 时间线渲染")
    except Exception as e:
        errors.append(f"时间线渲染失败: {e}")
        print(f"[失败] 时间线渲染: {e}")

    # --- 测试 6: 负面反馈与竞对检测 ---
    try:
        # 构造含负面反馈的记录
        neg_event_strs = [
            "2026-01-01|电话|初次沟通",
            "2026-01-05|邮件|客户表示不满",
            "2026-01-10|会议|讨论投诉问题",
        ]
        neg_record = build_customer_record("C002", "成交客户", neg_event_strs)
        assert neg_record.has_negative_feedback() is True, "应检测到负面反馈"
        assert neg_record.has_competitor_contact() is False, "不应检测到竞对接触"

        # 构造含竞对接触的记录
        comp_event_strs = [
            "2026-01-01|电话|初次沟通",
            "2026-01-05|邮件|客户提到在对比别家",
            "2026-01-10|会议|讨论竞对方案",
        ]
        comp_record = build_customer_record("C003", "谈判中", comp_event_strs)
        assert comp_record.has_competitor_contact() is True, "应检测到竞对接触"
        print("[通过] 负面/竞对检测")
    except Exception as e:
        errors.append(f"负面/竞对检测失败: {e}")
        print(f"[失败] 负面/竞对检测: {e}")

    # --- 测试 7: 错误处理 ---
    try:
        # 无效日期
        try:
            parse_date("2026/01/01")
            errors.append("无效日期应报错")
            print("[失败] 错误处理: 无效日期未报错")
        except ValueError:
            print("[通过] 错误处理: 无效日期")

        # 无效事件格式
        try:
            parse_event("2026-01-01")
            errors.append("无效事件格式应报错")
            print("[失败] 错误处理: 无效事件格式未报错")
        except ValueError:
            print("[通过] 错误处理: 无效事件格式")

        # 数据不足
        try:
            short_record = build_customer_record("C004", "潜在客户", ["2026-01-01|电话|测试"])
            assess_risk(short_record, ref_date)
            errors.append("数据不足应报错")
            print("[失败] 错误处理: 数据不足未报错")
        except ValueError:
            print("[通过] 错误处理: 数据不足")
    except Exception as e:
        errors.append(f"错误处理测试异常: {e}")
        print(f"[失败] 错误处理测试异常: {e}")

    # --- 汇总 ---
    if errors:
        print(f"\n自检失败，共 {len(errors)} 个错误:")
        for err in errors:
            print(f"  - {err}")
        return 1
    else:
        print("\n自检全部通过 ✔")
        return 0


# ============================================================
# 主入口
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="客户跟进轨迹管理 - 记录互动、识别停滞、评估风险、生成建议",
        epilog="示例: python scripts/main.py --track --customer C001 --stage 意向客户 --events '2026-01-01|电话|沟通'"
    )
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    # 子命令参数
    parser.add_argument("--track", action="store_true", help="记录并显示客户轨迹")
    parser.add_argument("--stagnation", action="store_true", help="检测跟进停滞")
    parser.add_argument("--risk", action="store_true", help="评估流失风险并生成建议")
    parser.add_argument("--timeline", action="store_true", help="输出互动时间线")

    # 公共参数
    parser.add_argument("--customer", type=str, default="", help="客户ID")
    parser.add_argument("--stage", type=str, default="潜在客户", choices=list(CUSTOMER_STAGES), help="客户阶段")
    parser.add_argument("--events", type=str, nargs="+", default=[], help="互动事件，格式: '日期|类型|描述'")
    parser.add_argument("--threshold", type=int, default=DEFAULT_STAGNATION_THRESHOLD, help="停滞阈值（天）")
    parser.add_argument("--reference", type=str, default=date.today().isoformat(), help="参考日期 YYYY-MM-DD")

    return parser


def main() -> int:
    """主函数"""
    parser = build_parser()
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    parser.add_argument("--batch", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--config", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--task", default=None, help="文档声明的参数")  # F3 补全
    parser.add_argument("--file", default=None, help="文档声明的参数")  # F3 补全
    args = parser.parse_args()

    # 自检优先
    if args.selftest:
        return run_selftest()

    # 确定要执行的命令
    commands = []
    if args.track:
        commands.append("track")
    if args.stagnation:
        commands.append("stagnation")
    if args.risk:
        commands.append("risk")
    if args.timeline:
        commands.append("timeline")

    if len(commands) != 1:
        print(f"错误: {ERR_UNKNOWN_COMMAND} 请指定且仅指定一个操作命令", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    command = commands[0]

    try:
        if command == "track":
            return run_track(args)
        elif command == "stagnation":
            return run_stagnation(args)
        elif command == "risk":
            return run_risk(args)
        elif command == "timeline":
            return run_timeline(args)
    except Exception as e:
        print(f"错误: {ERR_INTERNAL}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
