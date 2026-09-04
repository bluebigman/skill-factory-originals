# -*- coding: utf-8 -*-
"""template_lib.py — 市场分析报告章节模板库（数据层）"""

# 章节模板：每章 = {title, framework(框架引导), questions(必答问题), sources(建议信源)}
SECTIONS = {
    "overview": {
        "title": "行业概述",
        "framework": "用 3 句话说清：行业在做什么、服务谁、处于什么阶段。",
        "questions": [
            "该行业近 5 年处于导入/成长/成熟/衰退哪一阶段？依据是什么？",
            "有哪些标志性事件（政策、并购、技术突破）重塑过行业？",
        ],
        "sources": ["行业协会官网", "头部公司年报开篇", "行业白皮书"],
    },
    "scale": {
        "title": "市场规模与增速",
        "framework": "给出市场总规模与增速估计，逐条标注口径与来源。",
        "questions": [
            "最近一年市场规模的权威估计是多少？（注明咨询机构与口径）",
            "过去 3 年复合增速是多少？未来 3 年预测增速区间？",
        ],
        "sources": ["券商行业研报", "咨询公司报告（艾瑞/欧睿/弗若斯特沙利文等）", "国家统计局"],
    },
    "drivers": {
        "title": "增长驱动因素",
        "framework": "区分需求拉动（消费/企业支出）与供给推动（技术/成本）两类驱动。",
        "questions": [
            "需求端：哪些人群/场景的未被满足需求在放大？",
            "供给端：哪些技术或成本变化在降低进入门槛？",
        ],
        "sources": ["用户调研报告", "技术专利趋势", "供应链成本数据"],
    },
    "competition": {
        "title": "竞争格局",
        "framework": "波特五力 + 市场参与者分层（头部/腰部/长尾）双视角。",
        "questions": [
            "CR5/CR10 集中度大致多少？（注明数据来源）",
            "头部玩家的差异化壁垒分别是什么（品牌/渠道/技术/成本）？",
            "新进入者威胁与替代品威胁强度如何？",
        ],
        "sources": ["上市公司财报市场份额披露", "第三方销量监测（如尼尔森/奥维）"],
    },
    "customer": {
        "title": "目标客群画像",
        "framework": "按人口/地理/行为/心理四维拆解核心客群与边缘客群。",
        "questions": [
            "核心客群是谁？付费意愿最强的子群体是哪个？",
            "客群需求随年龄/收入迁移的趋势是什么？",
        ],
        "sources": ["客群调研问卷", "电商平台品类人群报告"],
    },
    "channel": {
        "title": "渠道与商业模式",
        "framework": "梳理从生产到消费的价值链与主要触达渠道。",
        "questions": [
            "线上/线下/出海渠道各自占比与增速？（注明来源）",
            "行业主流商业模式（卖货/订阅/抽佣/授权）与毛利结构？",
        ],
        "sources": ["财报渠道分部数据", "电商平台行业报告"],
    },
    "policy": {
        "title": "政策与监管环境",
        "framework": "列出直接相关的准入、补贴、合规监管政策。",
        "questions": [
            "哪些现行政策直接影响行业？（标注文号与生效时间）",
            "监管趋势是收紧还是放松？对中小玩家影响如何？",
        ],
        "sources": ["政府官网政策文件", "监管处罚案例库"],
    },
    "tech": {
        "title": "技术趋势",
        "framework": "识别正在改变行业成本结构或产品形态的技术。",
        "questions": [
            "哪些技术在 1-3 年内可能成为标配？",
            "技术专利集中在哪些玩家手中？",
        ],
        "sources": ["专利数据库", "技术白皮书"],
    },
    "supply": {
        "title": "供应链结构",
        "framework": "梳理上游原材料/中游制造/下游分销的议价关系。",
        "questions": [
            "上游集中度高不高？原材料价格波动影响多大？",
            "供应链瓶颈环节在哪？",
        ],
        "sources": ["供应商公告", "大宗商品价格数据"],
    },
    "risk": {
        "title": "风险清单",
        "framework": "分政策/市场/技术/经营四类列出风险与缓解思路。",
        "questions": [
            "最可能让行业逻辑失效的三个风险是什么？",
            "每个风险的先行指标（可监测信号）是什么？",
        ],
        "sources": ["行业负面事件库", "政策变化监测"],
    },
    "opportunity": {
        "title": "机会窗口",
        "framework": "结合空白客群/空白场景/空白渠道识别结构性机会。",
        "questions": [
            "头部玩家尚未覆盖的细分场景/人群有哪些？",
            "渠道迁移（如出海、私域）带来哪些窗口？",
        ],
        "sources": ["竞品产品功能更新", "社媒需求词监测"],
    },
    "conclusion": {
        "title": "结论与待验证假设",
        "framework": "输出 3-5 条可验证的核心假设，而非绝对结论。",
        "questions": [
            "如果只验证一个假设，验证它需要哪些数据？",
            "哪些信息缺口最影响判断？（列出优先级）",
        ],
        "sources": ["前述各章信源汇总"],
    },
}

# 视角 → 章节子集与顺序（invest 全量，startup 轻政策重机会，等）
VIEWS = {
    "invest": {
        "name": "投资尽调视角",
        "order": ["overview", "scale", "drivers", "competition", "channel",
                  "risk", "opportunity", "conclusion"],
    },
    "startup": {
        "name": "创业立项视角",
        "order": ["overview", "customer", "competition", "channel",
                  "opportunity", "risk", "conclusion"],
    },
    "marketing": {
        "name": "营销策略视角",
        "order": ["overview", "customer", "competition", "channel",
                  "drivers", "opportunity", "conclusion"],
    },
    "academic": {
        "name": "学术研究视角",
        "order": ["overview", "scale", "drivers", "competition", "policy",
                  "tech", "conclusion"],
    },
}

# deep 深度增补的章节
DEEP_EXTRAS = ["policy", "tech", "supply"]

PLACEHOLDER_DATA = "【待填·注明来源】"
PLACEHOLDER_SOURCE = "【来源：……】"

# 敏感/需要警示的行业词（触发报告头合规提醒）
WARN_INDUSTRY_WORDS = ["医疗", "医药", "金融", "证券", "保险", "教育", "烟草", "食品"]
