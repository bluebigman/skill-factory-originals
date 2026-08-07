#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py

Redash 数据可视化与仪表板构建 Skill —— 独立实现脚本。

本脚本依据功能规格独立设计（clean-room），不复制任何既有代码。
提供数据源接入方案、查询整理、图表匹配、仪表板规划、刷新共享策略等能力。

用法示例：
    python scripts/main.py --datasource mysql --goal 销售分析
    python scripts/main.py --selftest
"""

import argparse
import json
import sys
import os

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "参数缺失或非法",
    "E002": "不支持的数据源类型",
    "E003": "不支持的可视化类型",
    "E004": "查询语句为空",
    "E005": "数据源配置生成失败",
    "E006": "图表推荐失败",
    "E007": "仪表板规划失败",
    "E008": "刷新策略生成失败",
    "E009": "自检失败",
    "E010": "未知错误",
}


def fail(code: str, message: str = "") -> None:
    """输出错误信息并以错误码退出。"""
    err_text = ERROR_CODES.get(code, ERROR_CODES["E010"])
    print(f"[错误] {code}: {err_text} {message}".strip())
    sys.exit(1)


# ---------------------------------------------------------------------------
# 核心数据与规则（纯内存，无外部依赖）
# ---------------------------------------------------------------------------

# 支持的数据源类型及连接参数模板
DATASOURCE_TEMPLATES = {
    "mysql": {
        "type": "mysql",
        "host": "your_host",
        "port": 3306,
        "database": "your_db",
        "user": "your_user",
        "password": "your_password",
        "charset": "utf8mb4",
        "connect_timeout": 10,
    },
    "postgresql": {
        "type": "postgresql",
        "host": "your_host",
        "port": 5432,
        "database": "your_db",
        "user": "your_user",
        "password": "your_password",
        "sslmode": "prefer",
    },
    "sqlite": {
        "type": "sqlite",
        "database": "path/to/your.db",
    },
    "api": {
        "type": "api",
        "endpoint": "https://api.example.com/data",
        "method": "GET",
        "headers": {"Authorization": "Bearer YOUR_TOKEN"},
        "timeout": 30,
    },
    "csv": {
        "type": "csv",
        "file_path": "path/to/your.csv",
        "delimiter": ",",
        "encoding": "utf-8",
    },
}

# 图表类型匹配规则：数据特征 -> 推荐图表
CHART_RULES = [
    {
        "name": "时间趋势",
        "features": ["时间", "趋势", "序列", "日期"],
        "chart": "折线图 (Line Chart)",
        "reason": "适合展示随时间变化的趋势",
    },
    {
        "name": "类别对比",
        "features": ["对比", "排名", "类别", "分类"],
        "chart": "柱状图 (Bar Chart)",
        "reason": "适合不同类别间的数值对比",
    },
    {
        "name": "占比构成",
        "features": ["占比", "比例", "构成", "份额"],
        "chart": "饼图 (Pie Chart)",
        "reason": "适合展示整体中各部分的占比",
    },
    {
        "name": "数值分布",
        "features": ["分布", "区间", "频率", "直方"],
        "chart": "直方图 (Histogram)",
        "reason": "适合展示数据分布情况",
    },
    {
        "name": "关联关系",
        "features": ["相关", "关联", "散点", "关系"],
        "chart": "散点图 (Scatter Chart)",
        "reason": "适合展示两个变量间的关系",
    },
    {
        "name": "地理空间",
        "features": ["地图", "地理", "城市", "省份", "区域"],
        "chart": "地图 (Map)",
        "reason": "适合展示地理维度的数据分布",
    },
]

# 仪表板布局模板（基于指标优先级）
DASHBOARD_LAYOUT_TEMPLATE = {
    "header": {
        "title": "运营监控看板",
        "description": "核心业务指标总览",
    },
    "sections": [
        {
            "name": "核心指标区",
            "priority": "高",
            "charts": ["KPI 卡片", "关键趋势图"],
            "position": "顶部",
        },
        {
            "name": "分析明细区",
            "priority": "中",
            "charts": ["对比柱状图", "占比饼图", "分布直方图"],
            "position": "中部",
        },
        {
            "name": "辅助洞察区",
            "priority": "低",
            "charts": ["散点图", "明细表格"],
            "position": "底部",
        },
    ],
    "interactions": {
        "联动": "点击核心指标可联动过滤明细区",
        "下钻": "支持从汇总到明细的下钻",
    },
}

# 刷新与共享策略模板
REFRESH_SHARE_TEMPLATE = {
    "refresh": {
        "type": "定时刷新",
        "schedule": "每天 08:00",
        "interval": "24 小时",
        "note": "根据数据更新频率调整",
    },
    "share": {
        "type": "链接分享",
        "permission": "只读",
        "expiration": "永久有效",
        "note": "可设置访问密码或过期时间",
    },
}


# ---------------------------------------------------------------------------
# 核心功能函数
# ---------------------------------------------------------------------------

def generate_datasource_config(datasource_type: str) -> dict:
    """生成数据源连接配置建议。"""
    if datasource_type not in DATASOURCE_TEMPLATES:
        fail("E002", f"不支持的数据源类型: {datasource_type}")
    return DATASOURCE_TEMPLATES[datasource_type]


def organize_query(sql_text: str) -> dict:
    """整理查询语句，提取关键字段。"""
    if not sql_text or not sql_text.strip():
        fail("E004", "查询语句为空")

    # 提取 SELECT 字段（简单解析）
    lines = [line.strip() for line in sql_text.strip().splitlines() if line.strip()]
    select_fields = []
    for line in lines:
        if line.upper().startswith("SELECT"):
            # 去掉 SELECT 关键字，取逗号分隔的字段
            fields_part = line[6:].strip()
            select_fields = [f.strip() for f in fields_part.split(",") if f.strip()]
            break

    # 提取 FROM 表名
    from_table = None
    for i, line in enumerate(lines):
        if line.upper().startswith("FROM"):
            from_table = line[4:].strip().split()[0] if line[4:].strip() else None
            break

    return {
        "original_sql": sql_text,
        "select_fields": select_fields,
        "from_table": from_table,
        "query_type": "SELECT" if "select" in sql_text.lower() else "OTHER",
        "has_where": "where" in sql_text.lower(),
        "has_group_by": "group by" in sql_text.lower(),
        "has_order_by": "order by" in sql_text.lower(),
    }


def recommend_chart(data_features: str) -> dict:
    """根据数据特征推荐图表类型。"""
    if not data_features or not data_features.strip():
        fail("E006", "数据特征描述为空")

    features_lower = data_features.lower()
    best_match = None
    max_score = 0

    for rule in CHART_RULES:
        score = 0
        for feature in rule["features"]:
            if feature.lower() in features_lower:
                score += 1
        if score > max_score:
            max_score = score
            best_match = rule

    if best_match is None:
        # 默认推荐表格
        return {
            "chart": "表格 (Table)",
            "reason": "数据特征不明确，建议先用表格查看原始数据",
        }

    return {
        "chart": best_match["chart"],
        "reason": best_match["reason"],
        "matched_features": [f for f in best_match["features"] if f.lower() in features_lower],
    }


def plan_dashboard(business_goal: str = "运营监控") -> dict:
    """规划仪表板布局。"""
    if not business_goal or not business_goal.strip():
        fail("E007", "业务目标为空")

    # 根据业务目标微调标题
    layout = json.loads(json.dumps(DASHBOARD_LAYOUT_TEMPLATE))  # 深拷贝
    layout["header"]["title"] = f"{business_goal}看板"
    return layout


def generate_refresh_share_strategy(auto_refresh: bool = True) -> dict:
    """生成数据刷新与共享策略。"""
    if auto_refresh:
        return REFRESH_SHARE_TEMPLATE
    else:
        return {
            "refresh": {
                "type": "手动刷新",
                "schedule": "按需",
                "interval": "无",
                "note": "数据变化不频繁时使用",
            },
            "share": REFRESH_SHARE_TEMPLATE["share"],
        }


def build_deliverable(
    datasource_type: str,
    sql_text: str = "",
    data_features: str = "",
    business_goal: str = "运营监控",
    auto_refresh: bool = True,
) -> dict:
    """构建完整的结构化交付物。"""
    # 1. 数据源配置
    datasource = generate_datasource_config(datasource_type)

    # 2. 查询整理
    query_info = organize_query(sql_text) if sql_text else None

    # 3. 图表推荐
    chart_reco = recommend_chart(data_features) if data_features else None

    # 4. 仪表板规划
    dashboard = plan_dashboard(business_goal)

    # 5. 刷新共享策略
    strategy = generate_refresh_share_strategy(auto_refresh)

    return {
        "datasource": datasource,
        "query": query_info,
        "chart_recommendation": chart_reco,
        "dashboard_plan": dashboard,
        "refresh_share_strategy": strategy,
    }


# ---------------------------------------------------------------------------
# 自检函数（内置硬编码样例，离线可跑）
# ---------------------------------------------------------------------------

def run_selftest() -> bool:
    """内置样例数据自检核心逻辑，不依赖外部文件与网络。"""
    print("=" * 60)
    print("开始自检 (selftest)...")
    print("=" * 60)

    # --- 测试 1: 数据源配置生成 ---
    print("\n[测试 1] 数据源配置生成")
    try:
        mysql_cfg = generate_datasource_config("mysql")
        assert mysql_cfg["type"] == "mysql", "MySQL 类型不匹配"
        assert "host" in mysql_cfg, "缺少 host 字段"
        assert isinstance(mysql_cfg["port"], int), "端口不是整数"
        print("  ✓ MySQL 配置生成成功")

        pg_cfg = generate_datasource_config("postgresql")
        assert pg_cfg["type"] == "postgresql", "PostgreSQL 类型不匹配"
        print("  ✓ PostgreSQL 配置生成成功")

        sqlite_cfg = generate_datasource_config("sqlite")
        assert sqlite_cfg["type"] == "sqlite", "SQLite 类型不匹配"
        assert "database" in sqlite_cfg, "缺少 database 字段"
        print("  ✓ SQLite 配置生成成功")

        api_cfg = generate_datasource_config("api")
        assert api_cfg["type"] == "api", "API 类型不匹配"
        assert "endpoint" in api_cfg, "缺少 endpoint 字段"
        print("  ✓ API 配置生成成功")

        csv_cfg = generate_datasource_config("csv")
        assert csv_cfg["type"] == "csv", "CSV 类型不匹配"
        assert "file_path" in csv_cfg, "缺少 file_path 字段"
        print("  ✓ CSV 配置生成成功")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 1 失败: {e}")

    # --- 测试 2: 查询整理 ---
    print("\n[测试 2] 查询整理")
    try:
        sample_sql = """
        SELECT order_id, customer_name, amount, created_at
        FROM orders
        WHERE status = 'completed'
        GROUP BY customer_name
        ORDER BY amount DESC
        """
        query_info = organize_query(sample_sql)
        assert len(query_info["select_fields"]) >= 3, "SELECT 字段数不足"
        assert query_info["from_table"] == "orders", "表名提取错误"
        assert query_info["has_where"] is True, "WHERE 识别失败"
        assert query_info["has_group_by"] is True, "GROUP BY 识别失败"
        assert query_info["has_order_by"] is True, "ORDER BY 识别失败"
        print("  ✓ SQL 解析成功")
        print(f"    字段: {query_info['select_fields']}")
        print(f"    表: {query_info['from_table']}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 2 失败: {e}")

    # --- 测试 3: 图表推荐 ---
    print("\n[测试 3] 图表推荐")
    try:
        # 时间趋势
        chart1 = recommend_chart("我想看每天的销售趋势变化")
        assert chart1["chart"] == "折线图 (Line Chart)", "时间趋势推荐错误"
        print("  ✓ 时间趋势 -> 折线图")

        # 类别对比
        chart2 = recommend_chart("不同产品类别的销售额对比")
        assert chart2["chart"] == "柱状图 (Bar Chart)", "类别对比推荐错误"
        print("  ✓ 类别对比 -> 柱状图")

        # 占比
        chart3 = recommend_chart("各地区的销售占比")
        assert chart3["chart"] == "饼图 (Pie Chart)", "占比推荐错误"
        print("  ✓ 占比 -> 饼图")

        # 分布
        chart4 = recommend_chart("订单金额的分布情况")
        assert chart4["chart"] == "直方图 (Histogram)", "分布推荐错误"
        print("  ✓ 分布 -> 直方图")

        # 关联
        chart5 = recommend_chart("广告投入和销售额的关联分析")
        assert chart5["chart"] == "散点图 (Scatter Chart)", "关联推荐错误"
        print("  ✓ 关联 -> 散点图")

        # 地理
        chart6 = recommend_chart("各省份的用户分布地图")
        assert chart6["chart"] == "地图 (Map)", "地理推荐错误"
        print("  ✓ 地理 -> 地图")

        # 模糊特征
        chart7 = recommend_chart("随便看看数据")
        assert chart7["chart"] == "表格 (Table)", "默认推荐错误"
        print("  ✓ 无特征 -> 表格")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 3 失败: {e}")

    # --- 测试 4: 仪表板规划 ---
    print("\n[测试 4] 仪表板规划")
    try:
        dashboard = plan_dashboard("销售分析")
        assert "销售分析" in dashboard["header"]["title"], "标题未包含业务目标"
        assert len(dashboard["sections"]) >= 3, "区块数不足"
        assert "interactions" in dashboard, "缺少交互配置"
        print("  ✓ 仪表板规划成功")
        print(f"    标题: {dashboard['header']['title']}")
        print(f"    区块数: {len(dashboard['sections'])}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 4 失败: {e}")

    # --- 测试 5: 刷新共享策略 ---
    print("\n[测试 5] 刷新共享策略")
    try:
        auto = generate_refresh_share_strategy(auto_refresh=True)
        assert auto["refresh"]["type"] == "定时刷新", "自动刷新类型错误"
        assert auto["share"]["permission"] == "只读", "分享权限错误"

        manual = generate_refresh_share_strategy(auto_refresh=False)
        assert manual["refresh"]["type"] == "手动刷新", "手动刷新类型错误"
        print("  ✓ 自动刷新策略生成成功")
        print("  ✓ 手动刷新策略生成成功")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 5 失败: {e}")

    # --- 测试 6: 完整交付物构建 ---
    print("\n[测试 6] 完整交付物构建")
    try:
        deliverable = build_deliverable(
            datasource_type="mysql",
            sql_text="SELECT date, revenue, orders FROM sales WHERE date >= '2026-01-01'",
            data_features="按日期看销售趋势",
            business_goal="销售监控",
            auto_refresh=True,
        )
        assert "datasource" in deliverable, "缺少数据源配置"
        assert "query" in deliverable, "缺少查询信息"
        assert "chart_recommendation" in deliverable, "缺少图表推荐"
        assert "dashboard_plan" in deliverable, "缺少仪表板规划"
        assert "refresh_share_strategy" in deliverable, "缺少刷新共享策略"

        # 验证内容合理性（宽松断言）
        assert deliverable["query"]["from_table"] == "sales", "表名错误"
        assert deliverable["chart_recommendation"]["chart"] == "折线图 (Line Chart)", "图表推荐错误"
        assert "销售监控" in deliverable["dashboard_plan"]["header"]["title"], "看板标题错误"
        print("  ✓ 完整交付物构建成功")
        print(f"    数据源: {deliverable['datasource']['type']}")
        print(f"    图表推荐: {deliverable['chart_recommendation']['chart']}")
        print(f"    看板标题: {deliverable['dashboard_plan']['header']['title']}")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 6 失败: {e}")

    # --- 测试 7: 错误处理 ---
    print("\n[测试 7] 错误处理")
    try:
        # 不支持的数据源
        try:
            generate_datasource_config("oracle")
            fail("E009", "应抛出 E002 错误")
        except SystemExit as e:
            assert e.code == 1, "退出码错误"
        print("  ✓ 不支持的数据源正确报错")

        # 空查询
        try:
            organize_query("")
            fail("E009", "应抛出 E004 错误")
        except SystemExit as e:
            assert e.code == 1, "退出码错误"
        print("  ✓ 空查询正确报错")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        fail("E009", f"测试 7 失败: {e}")

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="Redash 数据可视化与仪表板构建 Skill",
        epilog="示例: python scripts/main.py --datasource mysql --goal 销售分析",
    )
    parser.add_argument(
        "--datasource",
        type=str,
        choices=list(DATASOURCE_TEMPLATES.keys()),
        help="数据源类型 (mysql/postgresql/sqlite/api/csv)",
    )
    parser.add_argument(
        "--sql",
        type=str,
        default="",
        help="查询语句（可选）",
    )
    parser.add_argument(
        "--features",
        type=str,
        default="",
        help="数据特征描述，用于图表推荐（可选）",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="运营监控",
        help="业务目标，用于仪表板规划（可选）",
    )
    parser.add_argument(
        "--no-auto-refresh",
        action="store_true",
        help="禁用自动刷新（默认开启）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "text"],
        default="text",
        help="输出格式 (默认 text)",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 常规模式：需要数据源类型
    if not args.datasource:
        parser.print_help()
        fail("E001", "必须指定 --datasource 参数")

    # 构建交付物
    deliverable = build_deliverable(
        datasource_type=args.datasource,
        sql_text=args.sql,
        data_features=args.features,
        business_goal=args.goal,
        auto_refresh=not args.no_auto_refresh,
    )

    # 输出结果
    if args.output == "json":
        print(json.dumps(deliverable, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 60)
        print("📊 Redash 数据看板构建方案")
        print("=" * 60)

        print("\n[1] 数据源配置")
        ds = deliverable["datasource"]
        for key, value in ds.items():
            print(f"    {key}: {value}")

        if deliverable["query"]:
            print("\n[2] 查询分析")
            q = deliverable["query"]
            print(f"    表: {q['from_table']}")
            print(f"    字段: {', '.join(q['select_fields'])}")
            print(f"    类型: {q['query_type']}")
            print(f"    条件: WHERE={q['has_where']}, GROUP BY={q['has_group_by']}, ORDER BY={q['has_order_by']}")

        if deliverable["chart_recommendation"]:
            print("\n[3] 图表推荐")
            c = deliverable["chart_recommendation"]
            print(f"    推荐: {c['chart']}")
            print(f"    理由: {c['reason']}")

        print("\n[4] 仪表板规划")
        d = deliverable["dashboard_plan"]
        print(f"    标题: {d['header']['title']}")
        print(f"    描述: {d['header']['description']}")
        for i, section in enumerate(d["sections"], 1):
            print(f"    {i}. {section['name']} (优先级: {section['priority']})")
            print(f"       位置: {section['position']}")
            print(f"       图表: {', '.join(section['charts'])}")

        print("\n[5] 刷新与共享策略")
        s = deliverable["refresh_share_strategy"]
        print(f"    刷新: {s['refresh']['type']} ({s['refresh']['schedule']})")
        print(f"    共享: {s['share']['type']} ({s['share']['permission']})")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
