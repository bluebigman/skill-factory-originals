#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
competitor-analysis-ai Skill Runner
分析竞品信息，输出结构化报告

支持功能：
- 从文件/URL/命令行参数加载竞品数据
- 多维度竞品分析（功能、定价、用户体验、市场定位、技术架构、运营）
- 生成差异化策略建议
- 风险提示与数据完整性检查
- CSV 导出
- 自测试（--selftest）
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

# 版本信息
VERSION = "3.1.0"

# 错误码
ERR_SUCCESS = 0
ERR_PARAM = 1
ERR_INVALID_DATA = 2
ERR_FILE_NOT_FOUND = 3
ERR_URL_FAILED = 4
ERR_OUTPUT_DIR = 5

# 网络请求配置
REQUEST_TIMEOUT = 10  # 秒
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 秒

# 分析维度
ANALYSIS_DIMENSIONS = ["features", "pricing", "ux", "positioning", "tech_stack", "operations"]

# 必填字段
REQUIRED_FIELDS = ["name"]

# 最大竞品数量
MAX_COMPETITORS = 10


def load_spec() -> Dict[str, Any]:
    """加载技能规格说明"""
    spec_path = os.path.join(os.path.dirname(__file__), "spec.json")
    if not os.path.exists(spec_path):
        # 如果 spec.json 不存在，返回默认配置
        return {
            "name": "competitor-analysis",
            "version": VERSION,
            "triggers": [
                "competitor-analysis",
                "竞品分析",
                "竞品对比",
                "竞争策略",
                "市场分析",
                "竞品拆解",
                "差异化定位",
                "竞争情报"
            ]
        }
    with open(spec_path, "r", encoding="utf-8") as f:
        return json.load(f)


def match_trigger(user_input: str) -> bool:
    """判断输入是否匹配技能触发条件"""
    spec = load_spec()
    triggers = spec.get("triggers", [])
    for trigger in triggers:
        if trigger.lower() in user_input.lower():
            return True
    return False


def fetch_url_with_retry(url: str, timeout: int = REQUEST_TIMEOUT,
                         max_retries: int = MAX_RETRIES) -> str:
    """
    从 URL 获取数据，带超时和指数退避重试
    
    Args:
        url: 数据源 URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
    
    Returns:
        获取到的文本内容
    
    Raises:
        urllib.error.URLError: 当所有重试都失败时
        ValueError: 当 HTTP 状态码非 2xx 时
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CompetitorAnalysisSkill/3.1"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 检查 HTTP 状态码
                status_code = response.getcode()
                if status_code < 200 or status_code >= 300:
                    raise ValueError(f"HTTP 请求失败，状态码: {status_code}")
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
        except ValueError as e:
            # HTTP 状态码错误，不重试
            raise e
    raise last_error


def load_data_from_file(file_path: str) -> Dict[str, Any]:
    """从文件加载数据"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_from_url(url: str) -> Dict[str, Any]:
    """从 URL 加载数据"""
    try:
        content = fetch_url_with_retry(url)
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"URL 返回的数据不是有效的 JSON: {e}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"URL 请求失败: {e}")
    except ValueError as e:
        raise ConnectionError(f"URL 请求失败: {e}")


def load_data_from_args(data_str: str) -> Dict[str, Any]:
    """从命令行参数加载数据"""
    try:
        return json.loads(data_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"命令行参数不是有效的 JSON: {e}")


def validate_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证数据格式
    
    Returns:
        (是否有效, 错误信息列表)
    """
    errors = []
    if not isinstance(data, dict):
        return False, ["数据必须是 JSON 对象"]
    
    competitors = data.get("competitors")
    if competitors is None:
        return False, ["缺少 'competitors' 字段"]
    
    if not isinstance(competitors, list):
        return False, ["'competitors' 必须是数组"]
    
    if len(competitors) == 0:
        return False, ["'competitors' 数组不能为空"]
    
    if len(competitors) > MAX_COMPETITORS:
        errors.append(f"竞品数量超过最大限制 {MAX_COMPETITORS}，建议分批处理")
    
    for i, comp in enumerate(competitors):
        if not isinstance(comp, dict):
            errors.append(f"竞品 #{i+1} 必须是对象")
            continue
        
        # 检查必填字段
        for field in REQUIRED_FIELDS:
            if field not in comp or comp[field] is None or comp[field] == "":
                errors.append(f"竞品 #{i+1} 缺少必填字段 '{field}'")
    
    return len(errors) == 0, errors


def analyze_competitor(competitor: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析单个竞品
    
    Args:
        competitor: 竞品数据
    
    Returns:
        分析结果
    """
    result = {
        "name": competitor.get("name", "[需核实:name]"),
        "dimensions": {}
    }
    
    # 功能分析
    features = competitor.get("features")
    if features is None:
        result["dimensions"]["features"] = {"status": "missing", "data": "[需核实:features]"}
    elif isinstance(features, list):
        result["dimensions"]["features"] = {
            "status": "complete",
            "data": features,
            "count": len(features)
        }
    else:
        result["dimensions"]["features"] = {"status": "invalid", "data": "[需核实:features]"}
    
    # 定价分析
    pricing = competitor.get("pricing")
    if pricing is None:
        result["dimensions"]["pricing"] = {"status": "missing", "data": "[需核实:pricing]"}
    elif isinstance(pricing, dict):
        result["dimensions"]["pricing"] = {
            "status": "complete",
            "data": pricing
        }
    else:
        result["dimensions"]["pricing"] = {"status": "invalid", "data": "[需核实:pricing]"}
    
    # 用户体验分析
    ux = competitor.get("ux")
    if ux is None:
        result["dimensions"]["ux"] = {"status": "missing", "data": "[需核实:ux]"}
    else:
        result["dimensions"]["ux"] = {"status": "complete", "data": ux}
    
    # 市场定位分析
    positioning = competitor.get("positioning")
    if positioning is None:
        result["dimensions"]["positioning"] = {"status": "missing", "data": "[需核实:positioning]"}
    else:
        result["dimensions"]["positioning"] = {"status": "complete", "data": positioning}
    
    # 技术架构分析
    tech_stack = competitor.get("tech_stack")
    if tech_stack is None:
        result["dimensions"]["tech_stack"] = {"status": "missing", "data": "[需核实:tech_stack]"}
    elif isinstance(tech_stack, list):
        result["dimensions"]["tech_stack"] = {
            "status": "complete",
            "data": tech_stack,
            "count": len(tech_stack)
        }
    else:
        result["dimensions"]["tech_stack"] = {"status": "invalid", "data": "[需核实:tech_stack]"}
    
    # 运营策略分析
    operations = competitor.get("operations")
    if operations is None:
        result["dimensions"]["operations"] = {"status": "missing", "data": "[需核实:operations]"}
    else:
        result["dimensions"]["operations"] = {"status": "complete", "data": operations}
    
    return result


def generate_strategies(competitors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    生成差异化策略建议
    
    Args:
        competitors: 竞品列表
    
    Returns:
        策略建议列表
    """
    strategies = []
    
    # 基于功能差异生成策略
    feature_sets = []
    for comp in competitors:
        features = comp.get("features", [])
        if isinstance(features, list):
            feature_sets.append(set(features))
    
    if len(feature_sets) >= 2:
        # 找出差异化功能
        common_features = set.intersection(*feature_sets) if feature_sets else set()
        unique_features = []
        for i, comp in enumerate(competitors):
            if isinstance(comp.get("features"), list):
                unique = set(comp["features"]) - common_features
                if unique:
                    unique_features.append({
                        "competitor": comp.get("name", "未知"),
                        "unique_features": list(unique)
                    })
        
        if unique_features:
            strategies.append({
                "type": "feature_differentiation",
                "description": "基于功能差异化定位",
                "suggestion": f"重点关注以下竞品的独特功能: {', '.join([f['competitor'] + ': ' + ', '.join(f['unique_features'][:3]) for f in unique_features[:3]])}"
            })
    
    # 基于定价策略生成建议
    pricing_models = []
    for comp in competitors:
        pricing = comp.get("pricing")
        if isinstance(pricing, dict) and "model" in pricing:
            pricing_models.append(pricing["model"])
    
    if pricing_models:
        unique_models = list(set(pricing_models))
        if len(unique_models) > 1:
            strategies.append({
                "type": "pricing_strategy",
                "description": "定价策略差异化",
                "suggestion": f"市场存在多种定价模式: {', '.join(unique_models)}。建议评估是否有机会采用混合定价策略。"
            })
    
    # 基于市场定位生成建议
    positions = []
    for comp in competitors:
        pos = comp.get("positioning")
        if pos:
            positions.append(pos)
    
    if positions:
        strategies.append({
            "type": "positioning",
            "description": "市场定位分析",
            "suggestion": f"当前市场定位包括: {', '.join(positions[:5])}。建议寻找未被覆盖的细分市场。"
        })
    
    # 如果没有生成任何策略，提供通用建议
    if not strategies:
        strategies.append({
            "type": "general",
            "description": "通用策略建议",
            "suggestion": "建议深入分析用户需求，寻找未被满足的痛点，并评估技术可行性。"
        })
    
    return strategies


def generate_risks(competitors: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    生成风险提示
    
    Args:
        competitors: 竞品列表
    
    Returns:
        风险列表
    """
    risks = []
    
    # 检查数据完整性风险
    for i, comp in enumerate(competitors):
        missing_fields = []
        for dim in ANALYSIS_DIMENSIONS:
            if dim not in comp or comp[dim] is None:
                missing_fields.append(dim)
        if missing_fields:
            risks.append({
                "level": "warning",
                "type": "data_incomplete",
                "description": f"竞品 '{comp.get('name', f'#{i+1}')}' 缺少数据: {', '.join(missing_fields)}",
                "impact": "分析结果可能不完整"
            })
    
    # 检查竞品数量风险
    if len(competitors) > MAX_COMPETITORS:
        risks.append({
            "level": "warning",
            "type": "too_many_competitors",
            "description": f"竞品数量 ({len(competitors)}) 超过建议上限 ({MAX_COMPETITORS})",
            "impact": "分析深度可能不足"
        })
    
    # 如果没有风险，添加一个通用提示
    if not risks:
        risks.append({
            "level": "info",
            "type": "data_quality",
            "description": "数据完整性良好",
            "impact": "分析结果可信度较高"
        })
    
    return risks


def generate_report(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成完整分析报告
    
    Args:
        data: 输入数据
    
    Returns:
        报告字典
    """
    competitors = data.get("competitors", [])
    
    # 分析每个竞品
    findings = []
    for comp in competitors:
        if not isinstance(comp, dict) or "name" not in comp or not comp["name"]:
            continue
        findings.append(analyze_competitor(comp))
    
    # 生成策略和风险
    strategies = generate_strategies(competitors)
    risks = generate_risks(competitors)
    
    # 数据质量检查
    data_quality = {
        "total_competitors": len(competitors),
        "analyzed_competitors": len(findings),
        "skipped_competitors": len(competitors) - len(findings),
        "dimensions_checked": ANALYSIS_DIMENSIONS
    }
    
    # 统一使用 UTC 时间
    now_utc = datetime.now(timezone.utc)
    report = {
        "report_id": f"CA-{now_utc.strftime('%Y%m%d%H%M%S')}",
        "generated_at": now_utc.isoformat(),
        "timezone": "UTC",
        "competitors_analyzed": len(findings),
        "dimensions_analyzed": ANALYSIS_DIMENSIONS,
        "findings": findings,
        "strategies": strategies,
        "risks": risks,
        "data_quality": data_quality
    }
    
    return report


def export_csv(report: Dict[str, Any], output_path: str) -> None:
    """
    导出 CSV 报告
    
    Args:
        report: 报告数据
        output_path: 输出文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 写入临时文件，然后原子替换
    fd, temp_path = tempfile.mkstemp(dir=output_dir or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow(["竞品名称", "维度", "状态", "数据"])
            
            # 写入数据
            for finding in report["findings"]:
                name = finding["name"]
                for dim, dim_data in finding["dimensions"].items():
                    status = dim_data.get("status", "unknown")
                    data = dim_data.get("data", "")
                    if isinstance(data, (list, dict)):
                        data = json.dumps(data, ensure_ascii=False)
                    writer.writerow([name, dim, status, data])
            
            # 写入策略
            writer.writerow([])
            writer.writerow(["策略建议"])
            for strategy in report["strategies"]:
                writer.writerow([strategy["type"], strategy["description"], strategy["suggestion"]])
            
            # 写入风险
            writer.writerow([])
            writer.writerow(["风险提示"])
            for risk in report["risks"]:
                writer.writerow([risk["level"], risk["type"], risk["description"], risk["impact"]])
        
        # 原子替换
        os.replace(temp_path, output_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def run_selftest() -> int:
    """
    运行自测试，验证核心功能
    
    Returns:
        退出码（0 表示成功）
    """
    print("=== 运行自测试 ===")
    
    # 测试 1: 数据验证
    print("\n[测试 1] 数据验证...")
    valid_data = {"competitors": [{"name": "竞品A", "features": ["f1"]}]}
    is_valid, errors = validate_data(valid_data)
    assert is_valid, f"有效数据验证失败: {errors}"
    print("  ✓ 有效数据验证通过")
    
    invalid_data = {"competitors": [{"features": ["f1"]}]}
    is_valid, errors = validate_data(invalid_data)
    assert not is_valid, "无效数据验证失败"
    print("  ✓ 无效数据验证通过")
    
    # 测试 2
