#!/usr/bin/env python3
"""
run.py - 作业引导 Skill 主脚本
实现 SKILL.md 声明的全部能力，含 argparse/main/selftest。
"""

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

dry_run = False  # v3.274 模块级 dry-run 标志

# ========== 常量 ==========
SUBJECTS = {"math", "chinese", "english", "physics", "chemistry"}
GRADE_RANGES = {"小学": (3, 6), "初中": (7, 9), "高中": (10, 12)}
MAX_ROUNDS = 5
TIMEOUT_SEC = 5
MAX_RETRIES = 3
BASE_DELAY = 1.0  # 指数退避基数

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== 工具函数 ==========

def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

def _iter_lines(path):
    """批处理流式读取工具"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line


def utc_now() -> str:
    """返回 UTC 时间 ISO 格式"""
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, content: str) -> None:
    """原子化写入文件（先写临时文件再替换）"""
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


def http_get_with_retry(url: str, params: dict = None) -> str:
    """带超时和指数退避重试的 GET 请求
    
    重试策略：
    - 网络层错误（URLError, TimeoutError, OSError）：重试 MAX_RETRIES 次
    - HTTP 5xx 和 429 状态码：重试 MAX_RETRIES 次
    - HTTP 4xx 状态码：直接抛出，不重试
    """
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"E_HTTP_{resp.status}: HTTP状态码 {resp.status}")
                content = resp.read().decode("utf-8")
                if not content or len(content.strip()) < 2:
                    raise RuntimeError("E_EMPTY_RESPONSE: 响应内容为空")
                return content
        except urllib.error.HTTPError as e:
            if e.code >= 500 or e.code == 429:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"E_HTTP_{e.code}: HTTP错误: {e.reason}")
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"HTTP {e.code} 错误，{delay:.1f}秒后重试 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                raise RuntimeError(f"E_HTTP_{e.code}: HTTP错误: {e.reason}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(f"E_NETWORK: 网络请求失败: {e}")
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"网络错误，{delay:.1f}秒后重试 ({attempt+1}/{MAX_RETRIES})")
            time.sleep(delay)
    raise RuntimeError("E_NETWORK: 不可达")


# ========== 本地知识库（内置，无外部依赖） ==========

LOCAL_KNOWLEDGE_BASE = {
    "math": {
        "小学": "四则运算、分数、小数、几何初步、应用题",
        "初中": "方程与不等式、函数初步、几何证明、概率统计",
        "高中": "函数与导数、数列、三角函数、向量、解析几何、立体几何"
    },
    "chinese": {
        "小学": "拼音、字词、阅读理解基础、看图写话",
        "初中": "文言文、现代文阅读、作文、古诗词",
        "高中": "古诗文鉴赏、论述类文本、实用类文本、写作"
    },
    "english": {
        "小学": "基础词汇、简单句型、日常对话",
        "初中": "时态、语态、从句、阅读理解",
        "高中": "虚拟语气、非谓语动词、高级句型、写作"
    },
    "physics": {
        "初中": "力学、光学、电学基础、声学",
        "高中": "牛顿定律、电磁学、热学、原子物理"
    },
    "chemistry": {
        "初中": "元素、化合物、化学方程式、实验基础",
        "高中": "化学反应原理、有机化学、结构化学、实验化学"
    }
}

LOCAL_MISTAKE_ANALYSIS = {
    "计算错误": "建议：加强口算练习，检查每一步运算，使用草稿纸。",
    "概念混淆": "建议：重新阅读课本定义，制作概念对比表。",
    "审题不清": "建议：圈出关键词，复述题目要求。",
    "思路中断": "建议：回顾类似题型，建立解题模板。",
    "粗心大意": "建议：做完后检查单位、符号、小数点。",
    "知识遗忘": "建议：复习相关章节，做基础练习巩固。",
    "方法不当": "建议：学习多种解题方法，选择最适合的。",
    "时间不足": "建议：练习限时做题，提高效率。"
}

# 完整知识点库（覆盖 K3-K12 核心题型）
KNOWLEDGE_BASE = {
    "math": {
        "小学": {
            "四则运算": ["加减乘除混合运算", "运算顺序", "括号使用"],
            "分数": ["分数加减", "分数乘除", "分数比较"],
            "小数": ["小数加减", "小数乘除", "小数与分数转换"],
            "几何初步": ["长方形面积", "正方形面积", "三角形面积", "圆周长"],
            "应用题": ["行程问题", "工程问题", "价格问题", "年龄问题"]
        },
        "初中": {
            "方程": ["一元一次方程", "二元一次方程组", "分式方程"],
            "不等式": ["一元一次不等式", "不等式组"],
            "函数": ["正比例函数", "一次函数", "反比例函数"],
            "几何": ["三角形全等", "三角形相似", "勾股定理", "圆的性质"],
            "概率统计": ["平均数", "中位数", "众数", "概率计算"]
        },
        "高中": {
            "函数": ["函数定义域", "函数值域", "单调性", "奇偶性"],
            "导数": ["导数计算", "导数应用", "极值问题"],
            "数列": ["等差数列", "等比数列", "数列求和"],
            "三角函数": ["三角恒等变换", "三角函数图像", "解三角形"],
            "向量": ["向量运算", "向量平行垂直", "向量应用"],
            "解析几何": ["直线方程", "圆方程", "椭圆", "双曲线", "抛物线"],
            "立体几何": ["空间几何体", "线面关系", "面面关系", "体积表面积"]
        }
    },
    "chinese": {
        "小学": {
            "拼音": ["声母韵母", "整体认读音节", "声调"],
            "字词": ["形近字", "多音字", "近义词反义词"],
            "阅读理解": ["找中心句", "概括段意", "理解词语"],
            "看图写话": ["观察图片", "组织语言", "表达完整"]
        },
        "初中": {
            "文言文": ["实词虚词", "句式翻译", "文言文理解"],
            "现代文阅读": ["记叙文阅读", "说明文阅读", "议论文阅读"],
            "作文": ["审题立意", "结构安排", "语言表达"],
            "古诗词": ["诗词鉴赏", "名句默写", "意象分析"]
        },
        "高中": {
            "古诗文鉴赏": ["诗歌意象", "诗歌手法", "诗歌情感"],
            "论述类文本": ["论点论据", "论证方法", "逻辑分析"],
            "实用类文本": ["信息筛选", "概括分析", "评价应用"],
            "写作": ["材料作文", "议论文写作", "记叙文写作"]
        }
    },
    "english": {
        "小学": {
            "基础词汇": ["颜色", "数字", "动物", "食物"],
            "简单句型": ["be动词", "一般疑问句", "特殊疑问句"],
            "日常对话": ["问候", "介绍", "购物", "问路"]
        },
        "初中": {
            "时态": ["一般现在时", "一般过去时", "现在进行时", "现在完成时"],
            "语态": ["被动语态", "主动语态转换"],
            "从句": ["宾语从句", "定语从句", "状语从句"],
            "阅读理解": ["细节理解", "主旨大意", "推理判断"]
        },
        "高中": {
            "虚拟语气": ["条件虚拟", "愿望虚拟", "建议虚拟"],
            "非谓语动词": ["不定式", "动名词", "分词"],
            "高级句型": ["倒装句", "强调句", "省略句"],
            "写作": ["应用文写作", "议论文写作", "图表作文"]
        }
    },
    "physics": {
        "初中": {
            "力学": ["力的概念", "重力", "摩擦力", "压强"],
            "光学": ["光的反射", "光的折射", "透镜"],
            "电学基础": ["电路连接", "电流电压", "电阻"],
            "声学": ["声音产生", "声音传播", "乐音三要素"]
        },
        "高中": {
            "牛顿定律": ["牛顿第一定律", "牛顿第二定律", "牛顿第三定律"],
            "电磁学": ["电场", "磁场", "电磁感应"],
            "热学": ["分子动理论", "热力学定律", "气体性质"],
            "原子物理": ["原子结构", "核反应", "放射性"]
        }
    },
    "chemistry": {
        "初中": {
            "元素": ["元素符号", "元素周期表", "元素性质"],
            "化合物": ["氧化物", "酸碱盐", "有机物"],
            "化学方程式": ["方程式配平", "方程式计算", "反应类型"],
            "实验基础": ["实验仪器", "实验操作", "实验安全"]
        },
        "高中": {
            "化学反应原理": ["反应速率", "化学平衡", "电离平衡"],
            "有机化学": ["烷烃烯烃", "醇醛酸", "酯化反应"],
            "结构化学": ["原子结构", "分子结构", "晶体结构"],
            "实验化学": ["定量实验", "定性实验", "实验设计"]
        }
    }
}


def review_knowledge_local(subject: str, grade: str) -> str:
    """本地知识点回顾（内置知识库）"""
    if subject in KNOWLEDGE_BASE and grade in KNOWLEDGE_BASE[subject]:
        topics = KNOWLEDGE_BASE[subject][grade]
        return "、".join(topics.keys())
    return "请参考课本对应章节，重点掌握基本概念和典型例题。"


def analyze_mistake_local(error_type: str) -> str:
    """本地错题归因分析（内置知识库）"""
    return LOCAL_MISTAKE_ANALYSIS.get(
        error_type,
        "建议：分析错误原因，针对性练习。"
    )


# ========== 外部知识 API（真实可用的公共 API） ==========

def fetch_knowledge(subject: str, grade: int) -> dict:
    """从外部知识库获取知识点（带降级机制）
    
    使用 Wikipedia 公共 API 作为真实可用的知识来源。
    失败时降级到本地知识库。
    """
    subject_keywords = {
        "math": "mathematics",
        "chinese": "Chinese language",
        "english": "English grammar",
        "physics": "physics",
        "chemistry": "chemistry"
    }
    keyword = subject_keywords.get(subject, subject)
    
    grade_keywords = {
        "小学": "elementary",
        "初中": "middle school",
        "高中": "high school"
    }
    grade_str = ""
    for stage, (lo, hi) in GRADE_RANGES.items():
        if lo <= grade <= hi:
            grade_str = grade_keywords[stage]
            break
    
    search_term = f"{grade_str} {keyword} education"
    
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "format": "json",
            "srlimit": "1"
        }
        response = http_get_with_retry(url, params)
        data = json.loads(response)
        
        search_results = data.get("query", {}).get("search", [])
        if search_results:
            title = search_results[0]["title"]
            snippet = search_results[0].get("snippet", "")
            snippet = re.sub(r'<[^>]+>', '', snippet)
            knowledge = f"参考知识点：{title} - {snippet}"
            return {"source": "external", "data": {"knowledge": knowledge}}
        else:
            logger.warning("外部知识库无搜索结果，降级为本地知识库")
            return {"source": "local", "data": review_knowledge_local(subject, grade)}
            
    except (RuntimeError, json.JSONDecodeError) as e:
        logger.warning(f"外部知识库API调用失败，降级为本地知识库: {e}")
        return {"source": "local", "data": review_knowledge_local(subject, grade)}


def fetch_mistake_analysis(error_type: str) -> dict:
    """从外部 API 获取错题分析（带降级机制）
    
    使用 DuckDuckGo 公共 API 作为真实可用的知识来源。
    失败时降级到本地知识库。
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": f"{error_type} study tips",
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        response = http_get_with_retry(url, params)
        data = json.loads(response)
        
        abstract = data.get("AbstractText", "")
        if abstract:
            advice = f"参考建议：{abstract}"
            return {"source": "external", "data": {"advice": advice}}
        else:
            logger.warning("外部错题分析API无结果，降级为本地知识库")
            return {"source": "local", "data": analyze_mistake_local(error_type)}
            
    except (RuntimeError, json.JSONDecodeError) as e:
        logger.warning(f"外部错题分析API调用失败，降级为本地知识库: {e}")
        return {"source": "local", "data": analyze_mistake_local(error_type)}


# ========== 核心能力实现 ==========

def parse_subject_grade(subject: str, grade: int) -> tuple[str, str]:
    """识别学科与年级段，返回 (学科, 年级段)"""
    if subject not in SUBJECTS:
        raise ValueError("E_INVALID_SUBJECT")
    if grade < 3 or grade > 12:
        raise ValueError("E_INVALID_GRADE")
    for stage, (lo, hi) in GRADE_RANGES.items():
        if lo <= grade <= hi:
            return subject, stage
    raise ValueError("E_INVALID_GRADE")


def confidence_gate(subject: str, question: str) -> tuple[float, str | None]:
    """置信度门控：返回 (置信度, 错误码或None)"""
    if subject not in SUBJECTS:
        return 0.3, "E_INVALID_SUBJECT"
    if not question or len(question.strip()) < 5:
        return 0.5, "E_INCOMPLETE"
    return 0.9, None


def decompose_problem(question: str, subject: str, grade: int) -> list[dict]:
    """将题目拆解为 3-5 个可独立思考的步骤
    
    基于题目文本的语义解析，提取已知条件和目标，动态生成针对性提问。
    """
    # 基础步骤模板（所有学科通用）
    base_steps = [
        {"step": 1, "question": "题目中有哪些已知条件？请列出来。", "hint": "找数字和关系词"},
        {"step": 2, "question": "要求解的是什么？用一句话说明。", "hint": "看最后一句问句"},
        {"step": 3, "question": "需要用到哪个知识点？", "hint": "回顾相关概念"},
        {"step": 4, "question": "尝试解答并检查。", "hint": "验证合理性"},
    ]
    
    # 语义解析：提取数字、关键词
