#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器指纹识别与反爬对抗工具 - 独立实现
========================================
本脚本仅依据功能规格独立编写，不包含任何既有代码。
提供核心能力：指纹采集方案设计、反爬机制识别、对抗策略生成、风险等级评估。
"""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：输入参数缺失或格式不正确",
    "E002": "文件错误：无法读取或写入文件",
    "E003": "网络错误：网络请求失败",
    "E004": "数据错误：输入数据格式不正确",
    "E005": "配置错误：配置信息缺失或错误",
    "E006": "逻辑错误：内部逻辑处理异常",
    "E007": "依赖错误：缺少必要的依赖库",
    "E008": "权限错误：没有足够的权限执行操作",
    "E009": "超时错误：操作超时",
    "E010": "未知错误：未定义的异常情况",
}


# ============================================================
# 核心数据结构
# ============================================================

class FingerprintProfile:
    """浏览器指纹画像数据类"""
    
    def __init__(self, user_agent: str = "", screen: str = "", timezone: str = "",
                 language: str = "", hardware: str = "", webgl: str = ""):
        self.user_agent = user_agent
        self.screen = screen
        self.timezone = timezone
        self.language = language
        self.hardware = hardware
        self.webgl = webgl
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "user_agent": self.user_agent,
            "screen": self.screen,
            "timezone": self.timezone,
            "language": self.language,
            "hardware": self.hardware,
            "webgl": self.webgl
        }
    
    def compute_hash(self) -> str:
        """计算指纹哈希值"""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class RiskAssessment:
    """风险等级评估结果"""
    
    def __init__(self, level: str, score: int, recommendations: List[str]):
        self.level = level
        self.score = score
        self.recommendations = recommendations
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "recommendations": self.recommendations
        }


# ============================================================
# 反爬机制识别模块
# ============================================================

class AntiBotDetector:
    """反爬机制识别器"""
    
    # 已知反爬服务特征标记
    KNOWN_SERVICES = {
        "Akamai": ["akamai", "ak_bmsc", "_abck"],
        "Cloudflare": ["cloudflare", "__cfduid", "cf-ray"],
        "DataDome": ["datadome", "datadome"],
        "PerimeterX": ["perimeterx", "_pxhd"],
        "Shape Security": ["shape", "shape"],
        "Distil Networks": ["distil", "_distil"],
        "Incapsula": ["incapsula", "incap_ses"],
        "Imperva": ["imperva", "x-iinfo"],
    }
    
    # 反爬特征头
    ANTI_BOT_HEADERS = [
        "x-csrf-token",
        "x-requested-with",
        "x-request-id",
        "x-forwarded-for",
        "x-real-ip",
        "sec-ch-ua",
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-user",
        "sec-fetch-dest"
    ]
    
    def __init__(self, headers: Dict[str, str] = None, html: str = "",
                 html_content: str = None):
        """
        初始化反爬检测器
        
        参数兼容性说明:
        - html: 兼容旧接口的HTML内容参数
        - html_content: 新接口的HTML内容参数（优先级更高）
        """
        self.headers = headers or {}
        
        # 兼容两种参数方式
        if html_content is not None:
            self.html_content = html_content
        else:
            self.html_content = html or ""
    
    def detect_service(self) -> List[str]:
        """检测已知反爬服务"""
        detected = []
        combined_text = json.dumps(self.headers).lower() + self.html_content.lower()
        
        for service, markers in self.KNOWN_SERVICES.items():
            for marker in markers:
                if marker.lower() in combined_text:
                    detected.append(service)
                    break
        
        return detected
    
    def detect_anti_bot_headers(self) -> List[str]:
        """检测反爬相关头信息"""
        detected_headers = []
        for header in self.ANTI_BOT_HEADERS:
            if header in self.headers:
                detected_headers.append(header)
        return detected_headers
    
    def detect_js_challenges(self) -> List[str]:
        """检测JS挑战特征"""
        challenges = []
        
        # 检测JavaScript挑战
        if re.search(r'(?i)(challenge|verify|check|validate)', self.html_content):
            challenges.append("javascript_challenge")
        
        # 检测Cookie挑战
        if re.search(r'(?i)(set-cookie|document\.cookie|createcookie)', self.html_content):
            challenges.append("cookie_challenge")
        
        # 检测验证码
        if re.search(r'(?i)(captcha|recaptcha|hcaptcha|geetest)', self.html_content):
            challenges.append("captcha")
        
        # 检测行为分析
        if re.search(r'(?i)(behavior|mouse|keyboard|gesture)', self.html_content):
            challenges.append("behavior_analysis")
        
        return challenges
    
    def analyze(self) -> Dict[str, Any]:
        """综合分析反爬机制"""
        services = self.detect_service()
        headers = self.detect_anti_bot_headers()
        challenges = self.detect_js_challenges()
        
        return {
            "services": services,
            "anti_bot_headers": headers,
            "challenges": challenges,
            "total_indicators": len(services) + len(headers) + len(challenges)
        }


# ============================================================
# 指纹对抗策略生成模块
# ============================================================

class StrategyGenerator:
    """指纹对抗策略生成器"""
    
    # 指纹维度定义
    FINGERPRINT_DIMENSIONS = [
        "user_agent",
        "screen_resolution",
        "timezone",
        "language",
        "hardware_concurrency",
        "webgl_renderer",
        "canvas_hash",
        "audio_hash",
        "fonts",
        "plugins"
    ]
    
    # 策略级别
    STRATEGY_LEVELS = {
        "basic": "基础伪装：修改User-Agent、屏幕分辨率等简单参数",
        "intermediate": "中级伪装：模拟浏览器行为、修改硬件参数",
        "advanced": "高级伪装：WebGL/Canvas指纹伪造、字体指纹模拟"
    }
    
    def __init__(self, target_service: str = "", risk_level: str = "low"):
        self.target_service = target_service
        self.risk_level = risk_level
    
    def generate_basic_strategies(self) -> List[str]:
        """生成基础对抗策略"""
        strategies = [
            "修改User-Agent：使用最新版Chrome/Firefox的UA字符串",
            "调整屏幕分辨率：设置为常见分辨率(1920x1080, 1366x768等)",
            "设置时区：使用目标用户所在地的时区",
            "配置语言：设置浏览器语言为接受语言列表",
            "使用无头浏览器：配置为有头模式运行"
        ]
        return strategies
    
    def generate_intermediate_strategies(self) -> List[str]:
        """生成中级对抗策略"""
        strategies = [
            "模拟鼠标移动轨迹：使用贝塞尔曲线模拟人类操作",
            "模拟键盘输入：添加随机延迟和打字速度变化",
            "修改硬件并发数：设置为CPU核心数的合理值",
            "配置浏览器插件：添加常见插件如Adobe PDF Reader",
            "设置WebRTC：禁用或伪装IP泄露"
        ]
        return strategies
    
    def generate_advanced_strategies(self) -> List[str]:
        """生成高级对抗策略"""
        strategies = [
            "WebGL渲染器伪装：修改GPU信息和渲染参数",
            "Canvas指纹噪声：添加微小像素扰动",
            "音频指纹伪造：修改音频处理参数",
            "字体指纹模拟：添加/删除特定字体",
            "使用指纹管理工具：如FingerprintJS的对抗方案"
        ]
        return strategies
    
    def generate(self) -> Dict[str, Any]:
        """生成完整对抗策略"""
        # 根据风险等级选择策略组合
        if self.risk_level == "high":
            strategies = (self.generate_basic_strategies() +
                         self.generate_intermediate_strategies() +
                         self.generate_advanced_strategies())
            level = "advanced"
        elif self.risk_level == "medium":
            strategies = (self.generate_basic_strategies() +
                         self.generate_intermediate_strategies())
            level = "intermediate"
        else:
            strategies = self.generate_basic_strategies()
            level = "basic"
        
        return {
            "level": level,
            "level_description": self.STRATEGY_LEVELS[level],
            "strategies": strategies,
            "target_service": self.target_service or "通用目标"
        }


# ============================================================
# 风险等级评估模块
# ============================================================

class RiskAssessor:
    """风险等级评估器"""
    
    def __init__(self):
        # 评估权重配置
        self.weights = {
            "anti_bot_services": 30,
            "challenge_complexity": 25,
            "header_indicators": 15,
            "behavior_analysis": 20,
            "ip_blocking": 10
        }
    
    def assess(self, detection_result: Dict[str, Any], access_frequency: int = 10) -> RiskAssessment:
        """评估风险等级"""
        score = 0
        
        # 反爬服务数量评估
        service_count = len(detection_result.get("services", []))
        if service_count > 0:
            score += min(service_count * 10, self.weights["anti_bot_services"])
        
        # 挑战复杂度评估
        challenges = detection_result.get("challenges", [])
        if "captcha" in challenges:
            score += self.weights["challenge_complexity"]
        elif "javascript_challenge" in challenges:
            score += int(self.weights["challenge_complexity"] * 0.7)
        elif "cookie_challenge" in challenges:
            score += int(self.weights["challenge_complexity"] * 0.5)
        
        # 头信息指标
        header_count = len(detection_result.get("anti_bot_headers", []))
        if header_count > 0:
            score += min(header_count * 3, self.weights["header_indicators"])
        
        # 行为分析检测
        if "behavior_analysis" in challenges:
            score += self.weights["behavior_analysis"]
        
        # 访问频率评估
        if access_frequency > 100:
            score += self.weights["ip_blocking"]
        elif access_frequency > 50:
            score += int(self.weights["ip_blocking"] * 0.6)
        
        # 确定等级
        if score >= 80:
            level = "高"
            recommendations = [
                "建议降低访问频率，使用代理IP池",
                "采用高级指纹伪装策略",
                "考虑使用浏览器自动化工具配合人工验证"
            ]
        elif score >= 50:
            level = "中"
            recommendations = [
                "使用中级指纹伪装策略",
                "控制采集频率，避免触发行为分析",
                "定期更换User-Agent和浏览器配置"
            ]
        else:
            level = "低"
            recommendations = [
                "使用基础指纹伪装策略",
                "保持正常的访问频率",
                "定期检查目标站点反爬策略变化"
            ]
        
        return RiskAssessment(level=level, score=score, recommendations=recommendations)


# ============================================================
# 指纹采集方案设计模块
# ============================================================

class FingerprintCollector:
    """浏览器指纹采集器"""
    
    # 可采集的指纹维度
    COLLECTABLE_DIMENSIONS = {
        "user_agent": "User-Agent字符串",
        "screen": "屏幕分辨率",
        "timezone": "时区",
        "language": "语言设置",
        "hardware": "硬件信息",
        "webgl": "WebGL渲染器",
        "canvas": "Canvas指纹",
        "audio": "音频指纹",
        "fonts": "字体列表",
        "plugins": "浏览器插件"
    }
    
    def __init__(self, target_url: str = ""):
        self.target_url = target_url
    
    def design_collection_plan(self, dimensions: List[str] = None) -> Dict[str, Any]:
        """设计指纹采集方案"""
        if dimensions is None:
            dimensions = list(self.COLLECTABLE_DIMENSIONS.keys())
        
        # 验证维度
        valid_dimensions = [d for d in dimensions if d in self.COLLECTABLE_DIMENSIONS]
        
        # 生成采集方案
        plan = {
            "target_url": self.target_url or "未指定",
            "dimensions_to_collect": valid_dimensions,
            "dimension_details": {d: self.COLLECTABLE_DIMENSIONS[d] for d in valid_dimensions},
            "collection_method": "使用JavaScript在浏览器端采集",
            "recommended_tool": "Playwright/Puppeteer + FingerprintJS",
            "collection_steps": [
                "1. 加载目标页面",
                "2. 执行指纹采集JavaScript",
                "3. 收集并序列化指纹数据",
                "4. 计算指纹哈希值",
                "5. 存储指纹数据用于分析"
            ]
        }
        
        return plan
    
    def simulate_collection(self, profile: FingerprintProfile) -> Dict[str, Any]:
        """模拟指纹采集过程"""
        fingerprint_data = profile.to_dict()
        
        # 计算指纹哈希
        fingerprint_hash = profile.compute_hash()
        
        # 计算指纹熵（信息量估计）
        entropy = len(fingerprint_hash) * 4  # 每个十六进制字符约4比特
        
        return {
            "fingerprint_data": fingerprint_data,
            "fingerprint_hash": fingerprint_hash,
            "estimated_entropy": entropy,
            "collection_time": time.time(),
            "collection_status": "success"
        }


# ============================================================
# 主控制器
# ============================================================

class FingerprintAnalyzer:
    """浏览器指纹分析与对抗主控制器"""
    
    def __init__(self):
        self.detector = AntiBotDetector()
        self.strategy_gen = StrategyGenerator()
        self.risk_assessor = RiskAssessor()
        self.collector = FingerprintCollector()
    
    def analyze_anti_bot(self, headers: Dict[str, str] = None, 
                         html: str = "", frequency: int = 10) -> Dict[str, Any]:
        """分析反爬机制"""
        if headers is None:
            headers = {}
        
        self.detector = AntiBotDetector(headers, html)
        detection = self.detector.analyze()
        
        # 评估风险
        risk = self.risk_assessor.assess(detection, frequency)
        
        return {
            "detection": detection,
            "risk_assessment": risk.to_dict()
        }
    
    def generate_strategy(self, target_service: str = "", 
                          risk_level: str = "low") -> Dict[str, Any]:
        """生成对抗策略"""
        self.strategy_gen = StrategyGenerator(target_service, risk_level)
        return self.strategy_gen.generate()
    
    def design_collection(self, target_url: str = "", 
                          dimensions: List[str] = None) -> Dict[str, Any]:
        """设计指纹采集方案"""
        self.collector = FingerprintCollector(target_url)
        return self.collector.design_collection_plan(dimensions)
    
    def simulate_fingerprint(self, profile: FingerprintProfile) -> Dict[str, Any]:
        """模拟指纹采集"""
        return self.collector.simulate_collection(profile)
    
    def full_analysis(self, headers: Dict[str, str] = None, html: str = "",
                      frequency: int = 10, target_url: str = "") -> Dict[str, Any]:
        """完整分析流程"""
        # 1. 反爬机制检测
        analysis = self.analyze_anti_bot(headers, html, frequency)
        
        # 2. 生成对抗策略
        risk_level = "high" if analysis["risk_assessment"]["level"] == "高" else \
                    "medium" if analysis["risk_assessment"]["level"] == "中" else "low"
        strategies = self.generate_strategy(risk_level=risk_level)
        
        # 3. 设计采集方案
        collection_plan = self.design_collection(target_url)
        
        return {
            "analysis": analysis,
            "strategies": strategies,
            "collection_plan": collection_plan,
            "timestamp": time.time()
        }


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> bool:
    """内置自测函数，使用硬编码样例数据验证核心逻辑"""
    print("[自测开始] 浏览器指纹分析工具核心逻辑测试...")
    
    # 测试1: 反爬机制检测
    print("\n[测试1] 反爬机制检测...")
    test_headers = {
        "cf-ray": "test-ray-123",
        "x-csrf-token": "test-token",
        "sec-ch-ua": '"Chromium";v="120"',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    test_html = """
    <html>
        <head>
            <script>
                // Challenge script
                function verifyUser() {
                    document.cookie = "challenge=test";
                    // Captcha check
                    if (typeof grecaptcha !== 'undefined') {
                        grecaptcha.execute();
                    }
                }
            </script>
        </head>
        <body>
            <div class="captcha-container"></div>
            <script>
                // Behavior tracking
                document.addEventListener('mousemove', trackBehavior);
            </script>
        </body>
    </html>
    """
    
    detector = AntiBotDetector(test_headers, test_html)
    detection_result = detector.analyze()
    
    # 验证检测结果
    assert len(detection_result["services"]) > 0, "应该检测到Cloudflare服务"
    assert "cloudflare" in detection_result["services"][0].lower(), "应检测到Cloudflare"
    assert len(detection_result["anti_bot_headers"]) >= 2, "应检测到至少2个反爬头"
    assert "captcha" in detection_result["challenges"], "应检测到验证码挑战"
    assert "javascript_challenge" in detection_result["challenges"], "应检测到JS挑战"
    assert detection_result["total_indicators"] >= 4, "总指标数应至少为4"
    print("  ✓ 反爬机制检测通过")
    
    # 测试2: 风险等级评估
    print("\n[测试2] 风险等级评估...")
    assessor = RiskAssessor()
    risk = assessor.assess(detection_result, access_frequency=80)
    
    # 验证风险评估
    assert risk.score > 30, "风险得分应大于30"
    assert risk.score <= 100, "风险得分应不超过100"
    assert risk.level in ["低", "中", "高"], "风险等级应为低/中/高之一"
    assert len(risk.recommendations) > 0, "应有至少一条建议"
    print(f"  ✓ 风险评估通过 (等级: {risk.level}, 得分: {risk.score})")
    
    # 测试3: 策略生成
    print("\n[测试3] 对抗策略生成...")
    strategy_gen = StrategyGenerator("Cloudflare", "high")
    strategies = strategy_gen.generate()
    
    # 验证策略
    assert strategies["level"] in ["basic", "intermediate", "advanced"], "策略级别不正确"
    assert len(strategies["strategies"]) >= 5, "应至少生成5条策略"
    assert strategies["target_service"] == "Cloudflare", "目标服务应为Cloudflare"
    print(f"  ✓ 策略生成通过 (级别: {strategies['level']}, 策略数: {len(strategies['strategies'])})")
    
    # 测试4: 指纹采集方案设计
    print("\n[测试4] 指纹采集方案设计...")
    collector = FingerprintCollector("https://example.com")
    plan = collector.design_collection_plan(["user_agent", "screen", "timezone"])
    
    # 验证方案
    assert plan["target_url"] == "https://example.com", "目标URL应正确"
    assert len(plan["dimensions_to_collect"]) == 3, "应采集3个维度"
    assert len(plan["collection_steps"]) == 5, "应有5个采集步骤"
    print("  ✓ 采集方案设计通过")
    
    # 测试5: 指纹模拟采集
    print("\n[测试5] 指纹模拟采集...")
    test_profile = FingerprintProfile(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        screen="1920x1080",
        timezone="Asia/Shanghai",
        language="zh-CN,en-US",
        hardware="8",
        webgl="ANGLE (NVIDIA GeForce GTX 1080 Direct3D11)"
    )
    sim_result = collector.simulate_collection(test_profile)
    
    # 验证模拟结果
    assert len(sim_result["fingerprint_hash"]) == 16, "指纹哈希应为16字符"
    assert sim_result["estimated_entropy"] >= 32, "指纹熵应至少为32比特"
    assert sim_result["collection_status"] == "success", "采集状态应为成功"
    assert sim_result["fingerprint_data"]["screen"] == "1920x1080", "屏幕分辨率应正确"
    print("  ✓ 指纹模拟采集通过")
    
    # 测试6: 完整分析流程
    print("\n[测试6] 完整分析流程...")
    analyzer = FingerprintAnalyzer()
    full_result = analyzer.full_analysis(
        headers=test_headers,
        html=test_html,
        frequency=60,
        target_url="https://example.com"
    )
    
    # 验证完整流程
    assert "analysis" in full_result, "分析结果应存在"
    assert "strategies" in full_result, "策略应存在"
    assert "collection_plan" in full_result, "采集方案应存在"
    assert full_result["analysis"]["risk_assessment"]["score"] > 30, "风险得分应大于30"
    print("  ✓ 完整分析流程通过")
    
    # 测试7: 错误处理
    print("\n[测试7] 错误处理机制...")
    try:
        # 测试无效输入
        detector_with_none = AntiBotDetector(headers=None, html=None)
        assert detector_with_none.headers == {}, "None头应转换为空字典"
        assert detector_with_none.html_content == "", "None内容应转换为空字符串"
        
        # 测试html_content参数
        detector_with_content = AntiBotDetector(headers={}, html_content="test content")
        assert detector_with_content.html_content == "test content", "html_content参数应正确"
        print("  ✓ 错误处理通过")
    except Exception as e:
        print(f"  ✗ 错误处理失败: {e}")
        return False
    
    print("\n[自测完成] 所有核心逻辑测试通过！")
    return True


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="浏览器指纹识别与反爬对抗工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --selftest                    # 运行自测
  python main.py --analyze --url example.com   # 分析反爬机制
  python main.py --strategy --service cloudflare --risk high
  python main.py --design-collection --url example.com
        """
    )
    
    parser.add_argument("--selftest", action="store_true",
                       help="运行内置自测，验证核心逻辑")
    parser.add_argument("--analyze", action="store_true",
                       help="分析反爬机制")
    parser.add_argument("--url", type=str, default="",
                       help="目标站点URL")
    parser.add_argument("--strategy", action="store_true",
                       help="生成对抗策略")
    parser.add_argument("--service", type=str, default="",
                       help="目标反爬服务")
    parser.add_argument("--risk", type=str, default="low",
                       choices=["low", "medium", "high"],
                       help="风险等级")
    parser.add_argument("--design-collection", action="store_true",
                       help="设计指纹采集方案")
    parser.add_argument("--frequency", type=int, default=10,
                       help="访问频率(次/分钟)")
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    analyzer = FingerprintAnalyzer()
    
    # 分析反爬机制
    if args.analyze:
        print(f"[分析] 目标站点: {args.url or '未指定'}")
        result = analyzer.analyze_anti_bot(frequency=args.frequency)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    # 生成对抗策略
    if args.strategy:
        print(f"[策略] 目标服务: {args.service or '通用'}, 风险等级: {args.risk}")
        result = analyzer.generate_strategy(args.service, args.risk)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    # 设计采集方案
    if args.design_collection:
        print(f"[方案] 目标站点: {args.url or '未指定'}")
        result = analyzer.design_collection(args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    
    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户中断操作")
        sys.exit(130)
    except Exception as e:
        print(f"[错误] E010: {ERROR_CODES['E010']} - {str(e)}")
        sys.exit(1)
