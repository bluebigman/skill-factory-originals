#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser-fingerprinting 技能的核心逻辑实现（独立重写）

本脚本仅依据功能规格文档实现，不参考任何已有代码。
提供能力：
- C1: 指纹采集方案设计
- C2: 反爬机制识别
- C3: 指纹对抗策略生成
- C4: 采集代码框架搭建
- C5: 风险等级评估

仅用于学习研究，请遵守法律法规及目标站点规则。
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数缺失或为空",
    "E002": "输入格式不合法",
    "E003": "不支持的浏览器指纹类型",
    "E004": "不支持的编程语言",
    "E005": "风险等级计算失败",
    "E006": "策略生成失败",
    "E007": "内部数据异常",
    "E008": "自检数据初始化失败",
    "E009": "自检断言失败",
    "E010": "未知错误",
}


class SkillError(Exception):
    """技能执行异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class FingerprintPlan:
    """指纹采集方案（能力C1）"""
    target_url: str
    categories: List[str] = field(default_factory=list)
    data_points: List[str] = field(default_factory=list)
    collection_method: str = ""
    recommended_frequency: str = ""


@dataclass
class AntiBotDetection:
    """反爬机制识别结果（能力C2）"""
    engine: str = "unknown"
    confidence: float = 0.0
    indicators: List[str] = field(default_factory=list)
    protection_level: str = "low"


@dataclass
class CounterStrategy:
    """指纹对抗策略（能力C3）"""
    strategy_type: str = ""
    description: str = ""
    actions: List[str] = field(default_factory=list)
    risk_level: str = "low"


@dataclass
class CodeFramework:
    """代码框架（能力C4）"""
    language: str = ""
    purpose: str = ""
    code_template: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RiskAssessment:
    """风险等级评估（能力C5）"""
    score: int = 0
    level: str = "low"
    suggestions: List[str] = field(default_factory=list)


# ============================================================
# 内置知识库（硬编码，不读外部文件）
# ============================================================
# 常见反爬引擎特征指标
ANTIBOT_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "akamai": {
        "keywords": ["akamai", "ak_bmsc", "_abck"],
        "headers": ["x-akamai-transformed", "x-akamai-request-id"],
        "js_patterns": ["bm-verify", "bm-sz"],
        "weight": 0.9,
    },
    "cloudflare": {
        "keywords": ["cloudflare", "cf-ray", "__cf_bm"],
        "headers": ["cf-ray", "cf-cache-status"],
        "js_patterns": ["challenge-platform", "cf-chl"],
        "weight": 0.8,
    },
    "datadome": {
        "keywords": ["datadome", "x-datadome"],
        "headers": ["x-datadome"],
        "js_patterns": ["geo.captcha-delivery.com"],
        "weight": 0.85,
    },
    "perimeterx": {
        "keywords": ["perimeterx", "px-captcha"],
        "headers": ["px"],
        "js_patterns": ["perimeterx", "px.js"],
        "weight": 0.75,
    },
    "shape": {
        "keywords": ["shape", "shape.security"],
        "headers": ["x-shape"],
        "js_patterns": ["shape-security"],
        "weight": 0.7,
    },
}


# 指纹采集维度定义
FINGERPRINT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "hardware": {
        "name": "硬件指纹",
        "data_points": [
            "canvas指纹", "webgl指纹", "显卡信息", "CPU核心数",
            "内存大小", "设备内存", "硬件并发数"
        ],
    },
    "software": {
        "name": "软件指纹",
        "data_points": [
            "浏览器版本", "操作系统", "浏览器语言", "时区",
            "屏幕分辨率", "颜色深度", "字体列表", "插件列表"
        ],
    },
    "network": {
        "name": "网络指纹",
        "data_points": [
            "IP地址", "User-Agent", "Accept-Language", "TCP指纹",
            "TLS指纹", "HTTP/2指纹", "网络延迟特征"
        ],
    },
    "behavioral": {
        "name": "行为指纹",
        "data_points": [
            "鼠标轨迹", "键盘输入特征", "滚动行为", "点击模式",
            "页面停留时间", "表单填写速度"
        ],
    },
}


# 反爬保护级别与风险映射
PROTECTION_LEVELS: Dict[str, Dict[str, Any]] = {
    "low": {
        "name": "低",
        "score_range": (0, 30),
        "description": "基本无反爬或仅简单UA检测",
        "suggestions": ["普通请求即可", "注意请求频率"],
    },
    "medium": {
        "name": "中",
        "score_range": (31, 60),
        "description": "存在基础指纹检测或IP频率限制",
        "suggestions": ["需要基础指纹伪装", "建议使用代理轮换"],
    },
    "high": {
        "name": "高",
        "score_range": (61, 80),
        "description": "使用专业反爬引擎或复杂指纹检测",
        "suggestions": ["需要全面指纹伪装", "建议使用浏览器自动化"],
    },
    "critical": {
        "name": "极高",
        "score_range": (81, 100),
        "description": "多重反爬叠加或AI行为分析",
        "suggestions": ["建议评估采集可行性", "可能需要专业对抗方案"],
    },
}


# ============================================================
# 核心逻辑类
# ============================================================
class FingerprintService:
    """浏览器指纹识别与对抗核心服务"""

    def __init__(self) -> None:
        """初始化服务，加载内置知识库"""
        self._signatures = ANTIBOT_SIGNATURES
        self._categories = FINGERPRINT_CATEGORIES
        self._levels = PROTECTION_LEVELS

    # ---------- 能力C1: 指纹采集方案设计 ----------
    def design_collection_plan(self, target_url: str, requirements: Optional[str] = None) -> FingerprintPlan:
        """设计指纹采集方案"""
        if not target_url or not target_url.strip():
            raise SkillError("E001", "目标URL不能为空")

        # 根据需求关键词决定采集维度
        categories = []
        if requirements:
            req_lower = requirements.lower()
            if "硬件" in req_lower or "canvas" in req_lower or "webgl" in req_lower:
                categories.append("hardware")
            if "软件" in req_lower or "浏览器" in req_lower or "系统" in req_lower:
                categories.append("software")
            if "网络" in req_lower or "网络层" in req_lower or "ip" in req_lower:
                categories.append("network")
            if "行为" in req_lower or "鼠标" in req_lower or "键盘" in req_lower:
                categories.append("behavioral")

        # 默认全部采集
        if not categories:
            categories = list(self._categories.keys())

        # 收集数据点
        data_points = []
        for cat in categories:
            if cat in self._categories:
                data_points.extend(self._categories[cat]["data_points"])

        # 限制数据点数量，避免过度设计
        if len(data_points) > 20:
            data_points = data_points[:20]

        plan = FingerprintPlan(
            target_url=target_url,
            categories=categories,
            data_points=data_points,
            collection_method="浏览器自动化 + 网络层抓包",
            recommended_frequency="建议低频采集，避免触发风控",
        )
        return plan

    # ---------- 能力C2: 反爬机制识别 ----------
    def detect_antibot(self, headers: Optional[Dict[str, str]] = None,
                       js_content: Optional[str] = None,
                       page_content: Optional[str] = None) -> AntiBotDetection:
        """识别反爬引擎"""
        headers = headers or {}
        js_content = js_content or ""
        page_content = page_content or ""

        # 合并所有文本用于关键词匹配
        combined_text = " ".join([
            " ".join(headers.values()),
            js_content,
            page_content,
        ]).lower()

        # 检查各引擎特征
        best_match = None
        best_score = 0.0
        indicators_found = []

        for engine_name, signature in self._signatures.items():
            score = 0.0
            found_indicators = []

            # 检查关键词
            for kw in signature["keywords"]:
                if kw.lower() in combined_text:
                    score += 0.3
                    found_indicators.append(f"关键词: {kw}")

            # 检查响应头
            for h in signature["headers"]:
                if h.lower() in {k.lower() for k in headers.keys()}:
                    score += 0.4
                    found_indicators.append(f"响应头: {h}")

            # 检查JS特征
            for pattern in signature["js_patterns"]:
                if pattern.lower() in js_content.lower():
                    score += 0.3
                    found_indicators.append(f"JS特征: {pattern}")

            # 加权
            score *= signature["weight"]

            if score > best_score:
                best_score = score
                best_match = engine_name
                indicators_found = found_indicators

        # 判定结果
        if best_match and best_score > 0.3:
            confidence = min(best_score, 0.95)
            protection_level = self._map_engine_to_level(best_match, best_score)
            return AntiBotDetection(
                engine=best_match,
                confidence=confidence,
                indicators=indicators_found,
                protection_level=protection_level,
            )

        # 未识别到明确引擎
        return AntiBotDetection(
            engine="unknown",
            confidence=0.1,
            indicators=["未检测到明确反爬引擎特征"],
            protection_level="low",
        )

    def _map_engine_to_level(self, engine: str, score: float) -> str:
        """根据引擎和置信度映射保护级别"""
        if score > 0.8:
            return "high"
        elif score > 0.5:
            return "medium"
        return "low"

    # ---------- 能力C3: 指纹对抗策略生成 ----------
    def generate_strategy(self, detection: AntiBotDetection) -> CounterStrategy:
        """基于检测结果生成对抗策略"""
        engine = detection.engine.lower()

        if engine == "akamai":
            return CounterStrategy(
                strategy_type="高级指纹伪装",
                description="Akamai 主要检测 TLS 指纹和 HTTP/2 指纹，需要模拟真实浏览器的网络指纹",
                actions=[
                    "使用真实浏览器的 TLS 指纹（如 Chrome 111+）",
                    "模拟 HTTP/2 帧顺序和设置参数",
                    "保持 cookie 一致性（_abck 等）",
                    "控制请求频率，模拟人类行为",
                ],
                risk_level="high",
            )
        elif engine == "cloudflare":
            return CounterStrategy(
                strategy_type="浏览器环境模拟",
                description="Cloudflare 重点检测浏览器环境一致性和 JS 执行能力",
                actions=[
                    "使用无头浏览器执行完整 JS",
                    "保持 WebGL、Canvas 等指纹一致性",
                    "处理 Turnstile 验证",
                    "使用真实的浏览器UA和Accept-Language",
                ],
                risk_level="medium",
            )
        elif engine == "datadome":
            return CounterStrategy(
                strategy_type="行为模拟与IP管理",
                description="DataDome 结合行为分析和 IP 信誉，需要多维度对抗",
                actions=[
                    "使用高质量住宅代理",
                    "模拟真实鼠标移动和滚动行为",
                    "控制采集频率，避免高频请求",
                    "保持浏览器指纹稳定",
                ],
                risk_level="high",
            )
        elif engine == "perimeterx":
            return CounterStrategy(
                strategy_type="验证流程模拟",
                description="PerimeterX 主要通过 JS 挑战和验证码拦截",
                actions=[
                    "完整执行 JS 挑战流程",
                    "处理 px-captcha 验证",
                    "保持 cookie 一致性",
                    "模拟浏览器环境",
                ],
                risk_level="high",
            )
        elif engine == "shape":
            return CounterStrategy(
                strategy_type="请求特征伪装",
                description="Shape 主要检测请求特征和浏览器环境",
                actions=[
                    "伪装 HTTP 请求头",
                    "模拟浏览器 TLS 指纹",
                    "使用真实浏览器环境",
                    "控制请求节奏",
                ],
                risk_level="medium",
            )
        else:
            # 未知引擎，提供通用策略
            return CounterStrategy(
                strategy_type="通用指纹优化",
                description="未识别到特定引擎，提供通用指纹优化建议",
                actions=[
                    "使用最新版 Chrome/Firefox 浏览器",
                    "保持指纹一致性（Canvas、WebGL、字体等）",
                    "使用合理的 User-Agent 和请求头",
                    "控制请求频率，避免触发风控",
                ],
                risk_level="low",
            )

    # ---------- 能力C4: 采集代码框架搭建 ----------
    def build_code_framework(self, language: str = "python",
                             target_url: str = "https://example.com",
                             use_proxy: bool = False) -> CodeFramework:
        """生成采集代码框架"""
        lang = language.lower()

        if lang not in ("python", "node", "nodejs", "javascript"):
            raise SkillError("E004", f"不支持的编程语言: {language}")

        # 生成Python框架
        if lang == "python":
            code = self._generate_python_framework(target_url, use_proxy)
            deps = ["selenium", "requests", "fake-useragent"]
            if use_proxy:
                deps.append("requests[socks]")
            return CodeFramework(
                language="python",
                purpose="浏览器指纹对抗采集框架",
                code_template=code,
                dependencies=deps,
            )

        # 生成Node.js框架
        code = self._generate_node_framework(target_url, use_proxy)
        deps = ["puppeteer", "axios", "user-agents"]
        if use_proxy:
            deps.append("https-proxy-agent")
        return CodeFramework(
            language="nodejs",
            purpose="浏览器指纹对抗采集框架",
            code_template=code,
            dependencies=deps,
        )

    def _generate_python_framework(self, target_url: str, use_proxy: bool) -> str:
        """生成Python代码模板"""
        proxy_code = ""
        if use_proxy:
            proxy_code = """
    # 代理配置（示例，请替换为实际代理）
    proxy = "http://user:pass@host:port"
    options.add_argument(f'--proxy-server={proxy}')
"""
        return f'''# -*- coding: utf-8 -*-
"""
浏览器指纹对抗采集框架 (Python)
目标: {target_url}
"""
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def create_driver() -> webdriver.Chrome:
    """创建配置好的浏览器实例"""
    options = Options()
    # 基础配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    {proxy_code}
    # 隐藏自动化特征
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    # 覆盖 navigator.webdriver 属性
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}})"
    )
    return driver


def fetch_page(driver: webdriver.Chrome, url: str) -> str:
    """带反检测的页面获取"""
    # 随机等待，模拟人类行为
    time.sleep(random.uniform(1, 3))
    driver.get(url)
    # 模拟滚动
    for _ in range(random.randint(1, 3)):
        driver.execute_script("window.scrollBy(0, window.innerHeight / 2)")
        time.sleep(random.uniform(0.5, 1.5))
    return driver.page_source


def main():
    """主函数"""
    url = "{target_url}"
    driver = create_driver()
    try:
        html = fetch_page(driver, url)
        print(f"成功获取页面，长度: {{len(html)}}")
        # TODO: 在此处添加数据解析逻辑
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
'''

    def _generate_node_framework(self, target_url: str, use_proxy: bool) -> str:
        """生成Node.js代码模板"""
        proxy_code = ""
        if use_proxy:
            proxy_code = """
    // 代理配置（示例，请替换为实际代理）
    const proxyUrl = 'http://user:pass@host:port';
    await page.authenticate({{ username: 'user', password: 'pass' }});
"""
        return f'''/**
 * 浏览器指纹对抗采集框架 (Node.js)
 * 目标: {target_url}
 */
const puppeteer = require('puppeteer');
const userAgents = require('user-agents');

async function createPage(browser) {{
    const page = await browser.newPage();

    // 随机User-Agent
    await page.setUserAgent(userAgents.random().toString());

    // 设置视口
    await page.setViewport({{
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        hasTouch: false,
    }});
{proxy_code}
    // 隐藏自动化特征
    await page.evaluateOnNewDocument(() => {{
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
    }});

    return page;
}}

async function fetchPage(page, url) {{
    // 随机延迟
    await new Promise(r => setTimeout(r, Math.random() * 2000 + 1000));

    await page.goto(url, {{ waitUntil: 'networkidle2', timeout: 30000 }});

    // 模拟滚动
    for (let i = 0; i < Math.floor(Math.random() * 3) + 1; i++) {{
        await page.evaluate(() => {{
            window.scrollBy(0, window.innerHeight / 2);
        }});
        await new Promise(r => setTimeout(r, Math.random() * 1000 + 500));
    }}

    return await page.content();
}}

async function main() {{
    const browser = await puppeteer.launch({{
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage'],
    }});

    try {{
        const page = await createPage(browser);
        const html = await fetchPage(page, '{target_url}');
        console.log(`成功获取页面，长度: ${{html.length}}`);
        // TODO: 在此处添加数据解析逻辑
    }} finally {{
        await browser.close();
    }}
}}

main().catch(console.error);
'''

    # ---------- 能力C5: 风险等级评估 ----------
    def assess_risk(self, detection: AntiBotDetection,
                    request_frequency: int = 10,
                    data_sensitivity: int = 1) -> RiskAssessment:
        """评估采集风险等级"""
        if request_frequency <= 0:
            raise SkillError("E005", "请求频率必须大于0")

        # 基础分：根据引擎类型
        engine_scores = {
            "akamai": 75,
            "cloudflare": 60,
            "datadome": 80,
            "perimeterx": 70,
            "shape": 55,
            "unknown": 20,
        }
        base_score = engine_scores.get(detection.engine, 20)

        # 置信度加成
        confidence_bonus = int(detection.confidence * 10)

        # 请求频率惩罚
        if request_frequency > 100:
            freq_penalty = 15
        elif request_frequency > 50:
            freq_penalty = 10
        elif request_frequency > 20:
            freq_penalty = 5
        else:
            freq_penalty = 0

        # 数据敏感度加成
        sensitivity_bonus = min(data_sensitivity * 5, 15)

        # 计算总分
        score = min(base_score + confidence_bonus + freq_penalty + sensitivity_bonus, 100)

        # 映射等级
        level = "low"
        suggestions = []
        for level_name, level_info in self._levels.items():
            if level_info["score_range"][0] <= score <= level_info["score_range"][1]:
                level = level_name
                suggestions = level_info["suggestions"]
                break

        # 添加引擎特定建议
        if detection.engine != "unknown":
            strategy = self.generate_strategy(detection)
            suggestions.extend(strategy.actions[:2])

        return RiskAssessment(
            score=score,
            level=level,
            suggestions=suggestions,
        )


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置硬编码样例数据的离线自检"""
    service = FingerprintService()

    # ---------- 测试C1: 指纹采集方案设计 ----------
    try:
        plan = service.design_collection_plan("https://example.com", "需要硬件和网络指纹")
        assert plan.target_url == "https://example.com", "C1: target_url 错误"
        assert len(plan.categories) >= 1, "C1: 分类数量异常"
        assert len(plan.data_points) > 0, "C1: 数据点为空"
        print("[PASS] C1 指纹采集方案设计")
    except SkillError as e:
        print(f"[FAIL] C1: {e}")
        return False

    # ---------- 测试C2: 反爬机制识别 ----------
    try:
        # 模拟Cloudflare特征
        test_headers = {
            "cf-ray": "abc123",
            "server": "cloudflare",
            "content-type": "text/html",
        }
        test_js = "window.__cf_chl_opt = {};"
        detection = service.detect_antibot(headers=test_headers, js_content=test_js)
        assert detection.engine == "cloudflare", f"C2: 识别引擎错误, got {detection.engine}"
        assert detection.confidence > 0.5, "C2: 置信度异常"
        assert len(detection.indicators) > 0, "C2: 无明显指标"
        print("[PASS] C2 反爬机制识别")
    except SkillError as e:
        print(f"[FAIL] C2: {e}")
        return False

    # ---------- 测试C3: 指纹对抗策略生成 ----------
    try:
        test_detection = AntiBotDetection(
            engine="cloudflare",
            confidence=0.8,
            indicators=["test"],
            protection_level="medium",
        )
        strategy = service.generate_strategy(test_detection)
        assert strategy.strategy_type != "", "C3: 策略类型为空"
        assert len(strategy.actions) > 0, "C3: 策略动作为空"
        print("[PASS] C3 指纹对抗策略生成")
    except SkillError as e:
        print(f"[FAIL] C3: {e}")
        return False

    # ---------- 测试C4: 采集代码框架搭建 ----------
    try:
        framework = service.build_code_framework("python", "https://example.com")
        assert framework.language == "python", "C4: 语言错误"
        assert len(framework.code_template) > 100, "C4: 代码模板过短"
        assert len(framework.dependencies) > 0, "C4: 依赖列表为空"

        # 测试Node.js
        node_framework = service.build_code_framework("nodejs", "https://example.com")
        assert node_framework.language == "nodejs", "C4: Node.js语言错误"
        assert len(node_framework.code_template) > 100, "C4: Node.js代码模板过短"
        print("[PASS] C4 采集代码框架搭建")
    except SkillError as e:
        print(f"[FAIL] C4: {e}")
        return False

    # ---------- 测试C5: 风险等级评估 ----------
    try:
        test_detection = AntiBotDetection(
            engine="datadome",
            confidence=0.85,
            indicators=["test"],
            protection_level="high",
        )
        risk = service.assess_risk(test_detection, request_frequency=10, data_sensitivity=1)
        assert risk.score > 50, "C5: 风险评分异常"
        assert risk.level in ("medium", "high", "critical"), "C5: 风险等级异常"
        assert len(risk.suggestions) > 0, "C5: 建议为空"
        print("[PASS] C5 风险等级评估")
    except SkillError as e:
        print(f"[FAIL] C5: {e}")
        return False

    # ---------- 测试错误处理 ----------
    try:
        service.design_collection_plan("")
        print("[FAIL] 错误处理: 空URL未抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E001", "错误码错误"
        print("[PASS] 错误处理 E001")

    try:
        service.build_code_framework("ruby")
        print("[FAIL] 错误处理: 不支持的语言未抛出异常")
        return False
    except SkillError as e:
        assert e.code == "E004", "错误码错误"
        print("[PASS] 错误处理 E004")

    print("\n=== 全部自检通过 ===")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """命令行主入口"""
    parser = argparse.ArgumentParser(
        description="浏览器指纹识别与反爬对抗工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest                    # 运行自检
  python main.py --plan https://example.com    # 设计采集方案
  python main.py --detect --headers '{"cf-ray":"x"}'  # 识别反爬
  python main.py --framework python --url https://example.com  # 生成代码
  python main.py --risk --url https://example.com --freq 20    # 风险评估
        """,
    )

    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--plan", type=str, metavar="URL", help="设计指纹采集方案")
    parser.add_argument("--requirements", type=str, default="", help="采集需求描述")
    parser.add_argument("--detect", action="store_true", help="识别反爬机制")
    parser.add_argument("--headers", type=str, default="{}", help="响应头JSON")
    parser.add_argument("--js", type=str, default="", help="JS代码内容")
    parser.add_argument("--framework", type=str, choices=["python", "nodejs"], help="生成代码框架")
    parser.add_argument("--url", type=str, default="https://example.com", help="目标URL")
    parser.add_argument("--proxy", action="store_true", help="是否使用代理")
    parser.add_argument("--risk", action="store_true", help="风险评估")
    parser.add_argument("--freq", type=int, default=10, help="请求频率(次/分钟)")
    parser.add_argument("--sensitivity", type=int, default=1, choices=[1, 2, 3], help="数据敏感度(1-3)")

    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 初始化服务
    service = FingerprintService()

    try:
        # 设计采集方案
        if args.plan:
            plan = service.design_collection_plan(args.plan, args.requirements)
            print(json.dumps({
                "target_url": plan.target_url,
                "categories": plan.categories,
                "data_points": plan.data_points,
                "collection_method": plan.collection_method,
                "recommended_frequency": plan.recommended_frequency,
            }, ensure_ascii=False, indent=2))
            return 0

        # 识别反爬
        if args.detect:
            try:
                headers = json.loads(args.headers)
            except json.JSONDecodeError:
                raise SkillError("E002", "headers参数必须是合法JSON")

            detection = service.detect_antibot(headers=headers, js_content=args.js)
            print(json.dumps({
                "engine": detection.engine,
                "confidence": detection.confidence,
                "indicators": detection.indicators,
                "protection_level": detection.protection_level,
            }, ensure_ascii=False, indent=2))
            return 0

        # 生成代码框架
        if args.framework:
            framework = service.build_code_framework(args.framework, args.url, args.proxy)
            print(f"# 语言: {framework.language}")
            print(f"# 用途: {framework.purpose}")
            print(f"# 依赖: {', '.join(framework.dependencies)}")
            print("#" + "=" * 60)
            print(framework.code_template)
            return 0

        # 风险评估
        if args.risk:
            # 先尝试识别反爬
            detection = service.detect_antibot(headers={}, js_content="")
            risk = service.assess_risk(
                detection,
                request_frequency=args.freq,
                data_sensitivity=args.sensitivity,
            )
            print(json.dumps({
                "score": risk.score,
                "level": risk.level,
                "suggestions": risk.suggestions,
            }, ensure_ascii=False, indent=2))
            return 0

        # 无参数时显示帮助
        parser.print_help()
        return 0

    except SkillError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
