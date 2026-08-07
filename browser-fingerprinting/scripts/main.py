#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
browser-fingerprinting - 反爬识别与浏览器指纹对抗工具

功能：
- 指纹采集方案设计（C1）
- 反爬机制识别（C2）
- 指纹对抗策略生成（C3）
- 采集代码框架搭建（C4）
- 风险等级评估（C5）

仅用于学习与研究目的。
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数类型不正确",
    "E002": "输入数据格式错误：无法解析输入内容",
    "E003": "不支持的反爬类型标识",
    "E004": "内部数据异常：指纹特征库缺失或损坏",
    "E005": "策略生成失败：无法为当前输入生成有效策略",
    "E006": "风险评估失败：输入数据不完整",
    "E007": "代码框架生成失败：语言类型不支持",
    "E008": "自检失败：核心逻辑验证未通过",
    "E009": "文件读写异常",
    "E010": "未知错误",
}


def raise_error(code: str, detail: str = "") -> None:
    """抛出带错误码的异常"""
    msg = ERROR_CODES.get(code, ERROR_CODES["E010"])
    if detail:
        msg = f"{msg} | {detail}"
    raise RuntimeError(f"[{code}] {msg}")


# ============================================================
# 数据模型
# ============================================================
@dataclass
class FingerprintProfile:
    """浏览器指纹画像"""
    user_agent: str = ""
    language: str = "zh-CN"
    platform: str = "Win32"
    screen_resolution: str = "1920x1080"
    color_depth: int = 24
    timezone: str = "Asia/Shanghai"
    hardware_concurrency: int = 8
    device_memory: int = 8
    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
    canvas_fingerprint: str = "a1b2c3d4e5f6"
    fonts: List[str] = field(default_factory=lambda: ["Arial", "Times New Roman", "Microsoft YaHei"])
    plugins: List[str] = field(default_factory=lambda: ["PDF Viewer", "Chrome PDF Viewer"])
    do_not_track: str = "unknown"
    touch_support: bool = False
    cookies_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "userAgent": self.user_agent,
            "language": self.language,
            "platform": self.platform,
            "screenResolution": self.screen_resolution,
            "colorDepth": self.color_depth,
            "timezone": self.timezone,
            "hardwareConcurrency": self.hardware_concurrency,
            "deviceMemory": self.device_memory,
            "webglVendor": self.webgl_vendor,
            "webglRenderer": self.webgl_renderer,
            "canvasFingerprint": self.canvas_fingerprint,
            "fonts": self.fonts,
            "plugins": self.plugins,
            "doNotTrack": self.do_not_track,
            "touchSupport": self.touch_support,
            "cookiesEnabled": self.cookies_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FingerprintProfile":
        """从字典创建"""
        profile = cls()
        mapping = {
            "userAgent": "user_agent",
            "language": "language",
            "platform": "platform",
            "screenResolution": "screen_resolution",
            "colorDepth": "color_depth",
            "timezone": "timezone",
            "hardwareConcurrency": "hardware_concurrency",
            "deviceMemory": "device_memory",
            "webglVendor": "webgl_vendor",
            "webglRenderer": "webgl_renderer",
            "canvasFingerprint": "canvas_fingerprint",
            "fonts": "fonts",
            "plugins": "plugins",
            "doNotTrack": "do_not_track",
            "touchSupport": "touch_support",
            "cookiesEnabled": "cookies_enabled",
        }
        for src_key, dst_attr in mapping.items():
            if src_key in data:
                setattr(profile, dst_attr, data[src_key])
        return profile


# ============================================================
# 反爬类型识别
# ============================================================
class AntiBotDetector:
    """反爬机制识别器"""

    # 特征库：识别不同反爬服务的特征标志
    DETECTION_PATTERNS = {
        "Cloudflare": {
            "headers": ["cf-ray", "cf-cache-status", "__cfduid"],
            "js_markers": ["challenge-platform", "cf-chl"],
            "response_markers": ["Just a moment...", "Checking your browser"],
        },
        "Akamai": {
            "headers": ["akamai", "ak_bmsc", "bm_sz"],
            "js_markers": ["_abck", "bm-verify"],
            "response_markers": ["Access Denied", "You don't have permission"],
        },
        "DataDome": {
            "headers": ["datadome", "x-datadome"],
            "js_markers": ["datadome", "dd_"],
            "response_markers": ["DataDome", "captcha"],
        },
        "PerimeterX": {
            "headers": ["px", "pxhd"],
            "js_markers": ["px-captcha", "perimeterx"],
            "response_markers": ["PerimeterX", "px-block"],
        },
        "ShapeSecurity": {
            "headers": ["shape", "ashx"],
            "js_markers": ["shape", "f5"],
            "response_markers": ["Shape", "f5 networks"],
        },
        "reCAPTCHA": {
            "headers": [],
            "js_markers": ["recaptcha", "g-recaptcha"],
            "response_markers": ["recaptcha", "I'm not a robot"],
        },
        "hCaptcha": {
            "headers": [],
            "js_markers": ["hcaptcha", "h-captcha"],
            "response_markers": ["hcaptcha", "hCaptcha"],
        },
        "GenericBotDetection": {
            "headers": ["x-bot", "x-human"],
            "js_markers": ["bot-detect", "botguard"],
            "response_markers": ["bot detected", "automated access"],
        },
    }

    @classmethod
    def detect(
        cls,
        headers: Optional[Dict[str, str]] = None,
        js_content: Optional[str] = None,
        response_body: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        识别目标站点使用的反爬技术

        参数:
            headers: HTTP 响应头字典
            js_content: 页面 JS 代码片段
            response_body: 响应体内容

        返回:
            识别结果列表，每项包含 technology, confidence, matched_signals
        """
        headers = headers or {}
        js_content = (js_content or "").lower()
        response_body = (response_body or "").lower()

        results = []
        header_keys = {k.lower(): v for k, v in headers.items()}

        for tech_name, patterns in cls.DETECTION_PATTERNS.items():
            matched = []
            score = 0.0

            # 检查响应头
            for h in patterns["headers"]:
                if h in header_keys:
                    matched.append(f"header:{h}")
                    score += 0.4

            # 检查 JS 标记
            for marker in patterns["js_markers"]:
                if marker.lower() in js_content:
                    matched.append(f"js:{marker}")
                    score += 0.3

            # 检查响应体标记
            for marker in patterns["response_markers"]:
                if marker.lower() in response_body:
                    matched.append(f"body:{marker}")
                    score += 0.3

            if matched:
                confidence = min(0.95, score)
                results.append({
                    "technology": tech_name,
                    "confidence": round(confidence, 2),
                    "matched_signals": matched,
                })

        # 按置信度降序排序
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results


# ============================================================
# 指纹对抗策略生成
# ============================================================
class FingerprintStrategist:
    """指纹对抗策略生成器"""

    @staticmethod
    def generate_strategies(
        detected_technologies: List[Dict[str, Any]],
        profile: Optional[FingerprintProfile] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据识别的反爬类型生成对抗策略

        参数:
            detected_technologies: 反爬识别结果列表
            profile: 当前指纹画像（可选）

        返回:
            策略列表
        """
        profile = profile or FingerprintProfile()
        strategies = []

        for tech in detected_technologies:
            tech_name = tech["technology"]
            confidence = tech["confidence"]

            if tech_name == "Cloudflare":
                strategies.append({
                    "target": "Cloudflare",
                    "priority": "high" if confidence > 0.7 else "medium",
                    "actions": [
                        "使用真实浏览器指纹替代默认值",
                        "配置合理的 TLS 指纹（JA3/JA4）",
                        "保持 HTTP/2 与 HTTP/3 协议一致性",
                        "避免高频请求触发 JS 挑战",
                        "使用支持自动续期的 Cookie 管理",
                    ],
                    "expected_effect": "降低被 Cloudflare 标记为机器人的概率",
                })
            elif tech_name == "Akamai":
                strategies.append({
                    "target": "Akamai",
                    "priority": "high" if confidence > 0.7 else "medium",
                    "actions": [
                        "模拟真实用户鼠标轨迹与键盘输入",
                        "指纹需包含完整 WebGL 与 Canvas 数据",
                        "保持 IP 稳定性，避免频繁更换出口",
                        "使用真实设备型号与浏览器版本匹配",
                        "控制请求频率在人类行为阈值内",
                    ],
                    "expected_effect": "绕过 Akamai 行为分析引擎",
                })
            elif tech_name == "DataDome":
                strategies.append({
                    "target": "DataDome",
                    "priority": "high" if confidence > 0.7 else "medium",
                    "actions": [
                        "使用高质量代理池（住宅 IP）",
                        "指纹需模拟真实用户浏览行为",
                        "避免无头浏览器特征泄露",
                        "设置合理的浏览时序（阅读、滚动、点击）",
                        "定期轮换指纹配置",
                    ],
                    "expected_effect": "降低 DataDome 实时拦截率",
                })
            elif tech_name == "PerimeterX":
                strategies.append({
                    "target": "PerimeterX",
                    "priority": "high" if confidence > 0.7 else "medium",
                    "actions": [
                        "完整模拟浏览器渲染环境",
                        "确保 Canvas/WebGL/字体指纹一致性",
                        "使用真实 User-Agent 与 Sec-CH-UA 头",
                        "避免自动化工具特征（如 CDP 痕迹）",
                        "保持会话 Cookie 的连贯性",
                    ],
                    "expected_effect": "通过 PerimeterX 行为验证",
                })
            elif tech_name == "ShapeSecurity":
                strategies.append({
                    "target": "ShapeSecurity",
                    "priority": "medium",
                    "actions": [
                        "使用真实浏览器环境运行",
                        "模拟自然浏览路径",
                        "避免请求模式过于规律",
                        "合理设置 Referer 与浏览历史",
                    ],
                    "expected_effect": "减少被 Shape 标记的风险",
                })
            elif tech_name in ("reCAPTCHA", "hCaptcha"):
                strategies.append({
                    "target": tech_name,
                    "priority": "medium",
                    "actions": [
                        "该技术属于验证码范畴，本工具不提供破解方案",
                        "建议降低请求频率，使用合规采集方式",
                        "考虑使用官方 API 或人工验证",
                    ],
                    "expected_effect": "合规规避验证码触发",
                })
            elif tech_name == "GenericBotDetection":
                strategies.append({
                    "target": "通用机器人检测",
                    "priority": "medium",
                    "actions": [
                        "全面检查并修复指纹不一致项",
                        "使用 Playwright/Puppeteer 的真实浏览器模式",
                        "配置合理的浏览器环境参数",
                        "避免同时使用多个自动化框架",
                    ],
                    "expected_effect": "通过通用反爬检测",
                })
            else:
                strategies.append({
                    "target": tech_name,
                    "priority": "low",
                    "actions": ["根据具体情况制定自定义策略"],
                    "expected_effect": "待评估",
                })

        # 如果没有任何识别结果，给出通用建议
        if not strategies:
            strategies.append({
                "target": "未知反爬机制",
                "priority": "low",
                "actions": [
                    "收集更多响应头与 JS 特征进行分析",
                    "检查 robots.txt 与站点访问策略",
                    "考虑使用合规 API 或联系站点管理员",
                ],
                "expected_effect": "明确目标站点反爬策略",
            })

        return strategies


# ============================================================
# 代码框架生成
# ============================================================
class CodeFrameworkGenerator:
    """采集代码框架生成器"""

    @staticmethod
    def generate_python_framework(
        profile: FingerprintProfile,
        strategies: List[Dict[str, Any]],
    ) -> str:
        """生成 Python 代码框架"""
        profile_dict = profile.to_dict()
        strategy_summary = "; ".join(
            f"{s['target']}({s['priority']})" for s in strategies
        )

        # 使用字符串拼接而不是 f-string 来避免大括号问题
        code = '''#!/usr/bin/env python3
"""
浏览器指纹对抗采集框架（自动生成）
目标反爬: {strategy_summary}
"""

import json
import random
import time

# pip install playwright
from playwright.sync_api import sync_playwright

# 指纹配置
FINGERPRINT = {profile_json}

# 对抗策略摘要
STRATEGIES = {strategies_json}


def create_browser_context(browser):
    """创建带指纹配置的浏览器上下文"""
    context = browser.new_context(
        user_agent=FINGERPRINT["userAgent"],
        locale=FINGERPRINT["language"],
        timezone_id=FINGERPRINT["timezone"],
        viewport={{
            "width": int(FINGERPRINT["screenResolution"].split("x")[0]),
            "height": int(FINGERPRINT["screenResolution"].split("x")[1]),
        }},
        color_scheme="light",
        device_scale_factor=1,
        has_touch=FINGERPRINT["touchSupport"],
        is_mobile=False,
    )

    # 注入 WebGL 指纹
    context.add_init_script("""
        Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {{
            value: function() {{
                const real = originalGetContext.apply(this, arguments);
                // 此处可注入自定义 WebGL 渲染结果
                return real;
            }}
        }});
    """)

    return context


def human_like_delay(min_sec=1.0, max_sec=3.0):
    """模拟人类操作延迟"""
    time.sleep(random.uniform(min_sec, max_sec))


def fetch_page(url: str):
    """带指纹对抗的页面采集"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = create_browser_context(browser)
        page = context.new_page()

        try:
            print(f"[*] 访问: {{url}}")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # 模拟人类滚动行为
            for _ in range(random.randint(2, 5)):
                page.mouse.wheel(0, random.randint(300, 800))
                human_like_delay(0.3, 1.0)

            # 提取页面内容
            content = page.content()
            title = page.title()

            print(f"[+] 页面标题: {{title}}")
            print(f"[+] 内容长度: {{len(content)}} 字符")

            return {{
                "title": title,
                "content_length": len(content),
                "url": url,
            }}

        except Exception as e:
            print(f"[!] 采集失败: {{e}}")
            return None

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python script.py <目标URL>")
        sys.exit(1)
    result = fetch_page(sys.argv[1])
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
'''.format(
            strategy_summary=strategy_summary,
            profile_json=json.dumps(profile_dict, indent=2, ensure_ascii=False),
            strategies_json=json.dumps([s["target"] for s in strategies], ensure_ascii=False)
        )
        return code

    @staticmethod
    def generate_nodejs_framework(
        profile: FingerprintProfile,
        strategies: List[Dict[str, Any]],
    ) -> str:
        """生成 Node.js 代码框架"""
        profile_dict = profile.to_dict()
        strategy_summary = "; ".join(
            f"{s['target']}({s['priority']})" for s in strategies
        )

        # 使用字符串拼接而不是 f-string 来避免大括号问题
        code = '''/**
 * 浏览器指纹对抗采集框架（自动生成）
 * 目标反爬: {strategy_summary}
 */

// 需要安装: npm install puppeteer-extra puppeteer-extra-plugin-stealth

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

// 指纹配置
const FINGERPRINT = {profile_json};

/**
 * 创建带指纹配置的浏览器页面
 */
async function createPage(browser) {{
  const page = await browser.newPage();

  // 设置用户代理
  await page.setUserAgent(FINGERPRINT.userAgent);

  // 设置语言与时区
  await page.setExtraHTTPHeaders({{
    'Accept-Language': FINGERPRINT.language
  }});

  // 设置视口
  const [width, height] = FINGERPRINT.screenResolution.split('x').map(Number);
  await page.setViewport({{ width, height }});

  // 注入 WebGL 指纹
  await page.evaluateOnNewDocument(() => {{
    // 在此处可注入自定义 WebGL 渲染结果
  }});

  return page;
}}

/**
 * 模拟人类操作延迟
 */
function humanLikeDelay(minMs = 1000, maxMs = 3000) {{
  return new Promise(resolve => {{
    const delay = Math.random() * (maxMs - minMs) + minMs;
    setTimeout(resolve, delay);
  }});
}}

/**
 * 带指纹对抗的页面采集
 */
async function fetchPage(url) {{
  const browser = await puppeteer.launch({{
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }});

  try {{
    const page = await createPage(browser);
    console.log(`[*] 访问: ${{url}}`);
    await page.goto(url, {{ waitUntil: 'networkidle0', timeout: 30000 }});

    // 模拟人类滚动
    for (let i = 0; i < 3 + Math.floor(Math.random() * 3); i++) {{
      await page.mouse.wheel({{ deltaY: 300 + Math.random() * 500 }});
      await humanLikeDelay(300, 1000);
    }}

    const title = await page.title();
    const content = await page.content();

    console.log(`[+] 页面标题: ${{title}}`);
    console.log(`[+] 内容长度: ${{content.length}} 字符`);

    return {{
      title,
      contentLength: content.length,
      url
    }};

  }} catch (err) {{
    console.error(`[!] 采集失败: ${{err.message}}`);
    return null;
  }} finally {{
    await browser.close();
  }}
}}

// 主入口
if (require.main === module) {{
  const url = process.argv[2];
  if (!url) {{
    console.log('用法: node script.js <目标URL>');
    process.exit(1);
  }}
  fetchPage(url).then(result => {{
    if (result) {{
      console.log(JSON.stringify(result, null, 2));
    }
  }});
}}
'''.format(
            strategy_summary=strategy_summary,
            profile_json=json.dumps(profile_dict, indent=2, ensure_ascii=False)
        )
        return code

    @classmethod
    def generate(
        cls, language: str, profile: FingerprintProfile, strategies: List[Dict[str, Any]]
    ) -> str:
        """根据语言生成代码框架"""
        lang = language.lower().strip()
        if lang in ("python", "py"):
            return cls.generate_python_framework(profile, strategies)
        elif lang in ("node", "nodejs", "javascript", "js"):
            return cls.generate_nodejs_framework(profile, strategies)
        else:
            raise_error("E007", f"不支持的编程语言: {language}")


# ============================================================
# 风险评估
# ============================================================
class RiskAssessor:
    """反爬风险评估器"""

    # 技术权重映射
    TECH_WEIGHTS = {
        "Cloudflare": 0.7,
        "Akamai": 0.8,
        "DataDome": 0.85,
        "PerimeterX": 0.8,
        "ShapeSecurity": 0.75,
        "reCAPTCHA": 0.6,
        "hCaptcha": 0.6,
        "GenericBotDetection": 0.5,
    }

    @classmethod
    def assess(
        cls,
        detected_technologies: List[Dict[str, Any]],
        access_frequency: str = "low",
    ) -> Dict[str, Any]:
        """
        评估目标站点反爬强度

        参数:
            detected_technologies: 反爬识别结果
            access_frequency: 访问频率 (low/medium/high)

        返回:
            风险评估结果
        """
        if not detected_technologies:
            raise_error("E006", "缺少反爬识别结果")

        # 计算基础风险分（0-100）
        base_score = 0.0
        for tech in detected_technologies:
            tech_name = tech["technology"]
            confidence = tech.get("confidence", 0.5)
            weight = cls.TECH_WEIGHTS.get(tech_name, 0.5)
            base_score += weight * confidence * 100

        # 归一化（取平均）
        base_score = min(100.0, base_score / len(detected_technologies) * 1.5)

        # 频率加成
        freq_bonus = {"low": 0, "medium": 10, "high": 25}.get(
            access_frequency.lower(), 0
        )
        final_score = min(100.0, base_score + freq_bonus)

        # 等级划分
        if final_score >= 80:
            level = "极高"
            suggestion = "不建议直接采集，建议寻找官方 API 或人工处理"
        elif final_score >= 60:
            level = "高"
            suggestion = "需要高级对抗策略，成功率不确定"
        elif final_score >= 40:
            level = "中"
            suggestion = "可使用基础对抗策略尝试采集"
        else:
            level = "低"
            suggestion = "常规采集即可，注意控制频率"

        return {
            "score": round(final_score, 1),
            "level": level,
            "suggestion": suggestion,
            "detected_technologies": [t["technology"] for t in detected_technologies],
            "access_frequency": access_frequency,
        }


# ============================================================
# 主处理逻辑
# ============================================================
def process_fingerprint_analysis(
    headers: Optional[Dict[str, str]] = None,
    js_content: Optional[str] = None,
    response_body: Optional[str] = None,
    profile: Optional[FingerprintProfile] = None,
    language: str = "python",
    access_frequency: str = "low",
) -> Dict[str, Any]:
    """
    完整分析流程：识别 -> 策略生成 -> 代码框架 -> 风险评估

    参数:
        headers: HTTP 响应头
        js_content: JS 代码内容
        response_body: 响应体
        profile: 指纹画像
        language: 代码框架语言
        access_frequency: 访问频率

    返回:
        完整分析结果
    """
    # 1. 反爬识别
    detected = AntiBotDetector.detect(headers, js_content, response_body)

    # 2. 策略生成
    profile = profile or FingerprintProfile()
    strategies = FingerprintStrategist.generate_strategies(detected, profile)

    # 3. 代码框架生成
    try:
        framework_code = CodeFrameworkGenerator.generate(language, profile, strategies)
    except RuntimeError:
        framework_code = ""

    # 4. 风险评估
    try:
        risk = RiskAssessor.assess(detected, access_frequency)
    except RuntimeError:
        risk = {}

    return {
        "detected_technologies": detected,
        "strategies": strategies,
        "framework_code": framework_code,
        "risk_assessment": risk,
        "profile": profile.to_dict(),
    }


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    内置数据自检核心逻辑（离线、无外部依赖）
    """
    print("[*] 开始自检...")

    # 测试数据
    test_headers = {
        "cf-ray": "test-ray-12345",
        "server": "cloudflare",
        "x-datadome": "test-datadome-token",
    }
    test_js = "var _abck = 'test'; var recaptcha = document.getElementById('g-recaptcha');"
    test_body = "Just a moment... Checking your browser before accessing."

    # 测试1: 反爬识别
    print("[*] 测试1: 反爬识别")
    detected = AntiBotDetector.detect(test_headers, test_js, test_body)
    tech_names = [t["technology"] for t in detected]

    # 宽松断言：至少识别出 Cloudflare
    assert "Cloudflare" in tech_names, "自检失败: 未识别出 Cloudflare"
    assert len(detected) > 0, "自检失败: 识别结果为空"
    # 置信度应在合理范围
    for tech in detected:
        assert 0.0 <= tech["confidence"] <= 1.0, "自检失败: 置信度超出范围"
    print(f"    [+] 识别到 {len(detected)} 种反爬技术: {tech_names}")

    # 测试2: 策略生成
    print("[*] 测试2: 策略生成")
    profile = FingerprintProfile()
    strategies = FingerprintStrategist.generate_strategies(detected, profile)
    assert len(strategies) > 0, "自检失败: 策略列表为空"
    for strategy in strategies:
        assert "target" in strategy, "自检失败: 策略缺少 target"
        assert "actions" in strategy, "自检失败: 策略缺少 actions"
        assert len(strategy["actions"]) > 0, "自检失败: 策略 actions 为空"
    print(f"    [+] 生成 {len(strategies)} 条策略")

    # 测试3: 代码框架生成
    print("[*] 测试3: 代码框架生成")
    py_code = CodeFrameworkGenerator.generate("python", profile, strategies)
    assert "playwright" in py_code, "自检失败: Python 代码缺少 playwright"
    assert "def fetch_page" in py_code, "自检失败: Python 代码缺少主函数"

    node_code = CodeFrameworkGenerator.generate("nodejs", profile, strategies)
    assert "puppeteer" in node_code, "自检失败: Node.js 代码缺少 puppeteer"
    print(f"    [+] Python 代码 {len(py_code)} 字符, Node.js 代码 {len(node_code)} 字符")

    # 测试4: 风险评估
    print("[*] 测试4: 风险评估")
    risk = RiskAssessor.assess(detected, "low")
    assert "score" in risk, "自检失败: 风险评估缺少 score"
    assert "level" in risk, "自检失败: 风险评估缺少 level"
    assert 0.0 <= risk["score"] <= 100.0, "自检失败: 风险分数超出范围"
    assert risk["level"] in ("低", "中", "高", "极高"), "自检失败: 风险等级无效"
    print(f"    [+] 风险分: {risk['score']}, 等级: {risk['level']}")

    # 测试5: 完整流程
    print("[*] 测试5: 完整流程")
    result = process_fingerprint_analysis(
        headers=test_headers,
        js_content=test_js,
        response_body=test_body,
        language="python",
        access_frequency="medium",
    )
    assert "detected_technologies" in result, "自检失败: 完整流程缺少识别结果"
    assert "strategies" in result, "自检失败: 完整流程缺少策略"
    assert "framework_code" in result, "自检失败: 完整流程缺少代码框架"
    assert "risk_assessment" in result, "自检失败: 完整流程缺少风险评估"
    assert len(result["framework_code"]) > 100, "自检失败: 代码框架过短"
    print(f"    [+] 完整流程正常, 生成代码 {len(result['framework_code'])} 字符")

    # 测试6: 指纹序列化
    print("[*] 测试6: 指纹序列化")
    profile_dict = profile.to_dict()
    assert "userAgent" in profile_dict, "自检失败: 序列化缺少 userAgent"
    assert "screenResolution" in profile_dict, "自检失败: 序列化缺少 screenResolution"
    restored = FingerprintProfile.from_dict(profile_dict)
    assert restored.user_agent == profile.user_agent, "自检失败: 反序列化 user_agent 不一致"
    assert restored.screen_resolution == profile.screen_resolution, "自检失败: 反序列化分辨率不一致"
    print(f"    [+] 序列化/反序列化正常")

    print("[✓] 全部自检通过")
    return True


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="浏览器指纹识别与反爬对抗工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自检
  python main.py --selftest

  # 分析反爬类型
  python main.py --headers '{"cf-ray": "test"}' --js 'var _abck = "x"'

  # 生成完整方案
  python main.py --headers '{"server": "cloudflare"}' --lang python --freq medium
        """,
    )

    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--headers", type=str, help="HTTP 响应头 JSON")
    parser.add_argument("--js", type=str, help="JS 代码内容")
    parser.add_argument("--body", type=str, help="响应体内容")
    parser.add_argument("--lang", type=str, default="python", choices=["python", "nodejs"], help="代码框架语言")
    parser.add_argument("--freq", type=str, default="low", choices=["low", "medium", "high"], help="访问频率")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            ok = run_selftest()
            return 0 if ok else 1
        except AssertionError as e:
            print(f"[!] 自检失败: {e}")
            return 1
        except Exception as e:
            print(f"[!] 自检异常: {e}")
            return 1

    # 分析模式
    try:
        # 解析输入
        headers = None
        if args.headers:
            try:
                headers = json.loads(args.headers)
            except json.JSONDecodeError:
                raise_error("E002", "headers 不是合法 JSON")

        # 执行分析
        result = process_fingerprint_analysis(
            headers=headers,
            js_content=args.js,
            response_body=args.body,
            language=args.lang,
            access_frequency=args.freq,
        )

        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"[+] 结果已保存到: {args.output}")
            except OSError as e:
                raise_error("E009", f"写入文件失败: {e}")
        else:
            print(output_json)

        return 0

    except RuntimeError as e:
        print(f"[!] 错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[!] 未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
