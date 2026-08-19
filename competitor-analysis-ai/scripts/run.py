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
import io
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# 版本信息
VERSION = "3.1.4"

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
MAX_RETRY_DELAY = 10.0  # 最大退避延迟（秒）

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
    从 URL 获取数据，带超时、指数退避重试（含 jitter）和 Retry-After 支持
    
    Args:
        url: 数据源 URL
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    
    Returns:
        响应内容字符串
    
    Raises:
        urllib.error.URLError: 所有重试均失败时抛出
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "competitor-analysis-skill/3.1.4"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 检查响应编码
                charset = response.headers.get_content_charset() or "utf-8"
                data = response.read()
                try:
                    return data.decode(charset)
                except (UnicodeDecodeError, LookupError):
                    # 编码探测失败，尝试常见编码
                    for enc in ["utf-8", "gbk", "gb18030", "latin-1"]:
                        try:
                            return data.decode(enc)
                        except UnicodeDecodeError:
                            continue
                    # 最后使用 replace 模式
                    return data.decode("utf-8", errors="replace")
        
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429 and attempt < max_retries:
                # 处理 Rate Limit，读取 Retry-After 头
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = min(float(retry_after), MAX_RETRY_DELAY)
                    except ValueError:
                        delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                else:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                time.sleep(delay)
                continue
            elif e.code >= 500 and attempt < max_retries:
                # 服务器错误，退避重试
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                time.sleep(delay)
                continue
            else:
                raise
        
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                # 添加 jitter 避免惊群
                import random
                delay = delay * (0.5 + random.random() * 0.5)
                time.sleep(delay)
                continue
            else:
                break
    
    # 所有重试失败
    if last_error:
        raise urllib.error.URLError(f"URL 请求失败，已重试 {max_retries} 次: {last_error}")
    raise urllib.error.URLError("URL 请求失败：未知错误")


def read_file_with_encoding(filepath: str) -> str:
    """
    读取文件内容，自动处理多种编码
    
    Args:
        filepath: 文件路径
    
    Returns:
        文件内容字符串
    
    Raises:
        FileNotFoundError: 文件不存在
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 尝试多种编码
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error: Optional[Exception] = None
    
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError) as e:
            last_error = e
            continue
    
    # 最后使用 replace 模式
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_json_data(content: str) -> List[Dict[str, Any]]:
    """
    解析 JSON 数据，支持数组或单个对象
    
    Args:
        content: JSON 字符串
    
    Returns:
        竞品数据列表
    
    Raises:
        json.JSONDecodeError: JSON 格式错误
    """
    data = json.loads(content)
    if isinstance(data, dict):
        # 单个对象包装为列表
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("JSON 数据必须是对象或数组")


def validate_competitors(data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    校验竞品数据，返回有效数据和警告信息
    
    Args:
        data: 竞品数据列表
    
    Returns:
        (有效数据列表, 警告信息列表)
    """
    valid_data = []
    warnings = []
    
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            warnings.append(f"第 {idx+1} 条数据不是对象，已跳过")
            continue
        
        # 检查必填字段
        missing = [f for f in REQUIRED_FIELDS if f not in item or not item[f]]
        if missing:
            warnings.append(f"第 {idx+1} 条数据缺少必填字段: {', '.join(missing)}，已跳过")
            continue
        
        # 检查 name 类型
        if not isinstance(item["name"], str):
            warnings.append(f"第 {idx+1} 条数据 name 字段不是字符串，已跳过")
            continue
        
        # 检查字段类型
        for field in ["features", "tech_stack"]:
            if field in item and not isinstance(item[field], list):
                warnings.append(f"第 {idx+1} 条数据 {field} 字段不是数组，已重置为空列表")
                item[field] = []
        
        for field in ["pricing", "ux", "positioning", "operations"]:
            if field in item and not isinstance(item[field], str):
                warnings.append(f"第 {idx+1} 条数据 {field} 字段不是字符串，已重置为空字符串")
                item[field] = ""
        
        valid_data.append(item)
    
    # 限制数量
    if len(valid_data) > MAX_COMPETITORS:
        warnings.append(f"竞品数量超过 {MAX_COMPETITORS} 个，仅保留前 {MAX_COMPETITORS} 个")
        valid_data = valid_data[:MAX_COMPETITORS]
    
    return valid_data, warnings


def score_features(competitor: Dict[str, Any]) -> int:
    """评估功能维度得分（1-10）"""
    features = competitor.get("features", [])
    if not features:
        return 3  # 无功能信息，给予基础分
    
    # 基于功能数量评分
    count = len(features)
    if count >= 10:
        return 9
    elif count >= 7:
        return 8
    elif count >= 5:
        return 7
    elif count >= 3:
        return 6
    elif count >= 1:
        return 5
    return 3


def score_pricing(competitor: Dict[str, Any]) -> int:
    """评估定价维度得分（1-10）"""
    pricing = competitor.get("pricing", "")
    if not pricing:
        return 3  # 无定价信息
    
    pricing_lower = pricing.lower()
    
    # 免费或开源
    if any(kw in pricing_lower for kw in ["free", "免费", "开源", "open source"]):
        return 9
    # 低价
    elif any(kw in pricing_lower for kw in ["低价", "便宜", "廉价", "low cost", "budget"]):
        return 8
    # 中等价格
    elif any(kw in pricing_lower for kw in ["中等", "适中", "mid", "standard"]):
        return 6
    # 高价
    elif any(kw in pricing_lower for kw in ["高价", "昂贵", "premium", "high"]):
        return 5
    # 有价格信息但无法判断
    else:
        return 6


def score_ux(competitor: Dict[str, Any]) -> int:
    """评估用户体验维度得分（1-10）"""
    ux = competitor.get("ux", "")
    if not ux:
        return 3  # 无 UX 信息
    
    ux_lower = ux.lower()
    score = 5  # 基础分
    
    # 正面关键词
    positive_kw = ["简洁", "易用", "直观", "流畅", "美观", "好用",
                   "simple", "easy", "intuitive", "smooth", "beautiful", "user-friendly"]
    for kw in positive_kw:
        if kw in ux_lower:
            score += 1
    
    # 负面关键词
    negative_kw = ["复杂", "难用", "混乱", "卡顿", "糟糕",
                   "complex", "difficult", "confusing", "laggy", "terrible"]
    for kw in negative_kw:
        if kw in ux_lower:
            score -= 1
    
    return max(1, min(10, score))


def score_positioning(competitor: Dict[str, Any]) -> int:
    """评估市场定位维度得分（1-10）"""
    positioning = competitor.get("positioning", "")
    if not positioning:
        return 3  # 无定位信息
    
    positioning_lower = positioning.lower()
    score = 5  # 基础分
    
    # 定位清晰度关键词
    clear_kw = ["高端", "低端", "中端", "专业", "大众", "细分", "垂直",
                "premium", "budget", "mid-range", "professional", "mass", "niche", "vertical"]
    for kw in clear_kw:
        if kw in positioning_lower:
            score += 1
    
    # 差异化关键词
    diff_kw = ["差异化", "独特", "创新", "领先", "第一",
               "differentiated", "unique", "innovative", "leading", "first"]
    for kw in diff_kw:
        if kw in positioning_lower:
            score += 1
    
    return max(1, min(10, score))


def score_tech_stack(competitor: Dict[str, Any]) -> int:
    """评估技术栈维度得分（1-10）"""
    tech_stack = competitor.get("tech_stack", [])
    if not tech_stack:
        return 3  # 无技术栈信息
    
    # 现代技术栈关键词
    modern_kw = ["python", "react", "vue", "node", "go", "rust", "kubernetes", "docker",
                 "aws", "gcp", "azure", "tensorflow", "pytorch", "llm", "ai"]
    score = 5  # 基础分
    
    for tech in tech_stack:
        tech_lower = str(tech).lower()
        for kw in modern_kw:
            if kw in tech_lower:
                score += 1
                break
    
    return max(1, min(10, score))


def score_operations(competitor: Dict[str, Any]) -> int:
    """评估运营维度得分（1-10）"""
    operations = competitor.get("operations", "")
    if not operations:
        return 3  # 无运营信息
    
    operations_lower = operations.lower()
    score = 5  # 基础分
    
    # 运营策略关键词
    strategy_kw = ["社区", "内容", "活动", "增长", "留存", "转化", "裂变",
                   "community", "content", "campaign", "growth", "retention", "conversion", "viral"]
    for kw in strategy_kw:
        if kw in operations_lower:
            score += 1
    
    return max(1, min(10, score))


def analyze_competitor(competitor: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析单个竞品，计算各维度得分
    
    Args:
        competitor: 竞品数据
    
    Returns:
        分析结果字典
    """
    result = dict(competitor)  # 防御性拷贝
    result["features_score"] = score_features(competitor)
    result["pricing_score"] = score_pricing(competitor)
    result["ux_score"] = score_ux(competitor)
    result["positioning_score"] = score_positioning(competitor)
    result["tech_stack_score"] = score_tech_stack(competitor)
    result["operations_score"] = score_operations(competitor)
    
    # 计算总分（平均分）
    scores = [
        result["features_score"],
        result["pricing_score"],
        result["ux_score"],
        result["positioning_score"],
        result["tech_stack_score"],
        result["operations_score"]
    ]
    result["overall_score"] = round(sum(scores) / len(scores), 1)
    
    return result


def generate_strategy(analysis: List[Dict[str, Any]]) -> List[str]:
    """
    生成差异化策略建议
    
    Args:
        analysis: 分析结果列表
    
    Returns:
        策略建议列表
    """
    strategies = []
    
    if not analysis:
        return ["无有效竞品数据，无法生成策略建议"]
    
    # 找出得分最高的竞品
    best = max(analysis, key=lambda x: x["overall_score"])
    strategies.append(f"市场领先者: {best['name']} (总分 {best['overall_score']})")
    
    # 找出各维度最强竞品
    for dim in ANALYSIS_DIMENSIONS:
        dim_key = f"{dim}_score"
        best_dim = max(analysis, key=lambda x: x[dim_key])
        strategies.append(f"{dim}维度领先: {best_dim['name']} ({best_dim[dim_key]}分)")
    
    # 生成差异化建议
    if len(analysis) >= 2:
        # 找出最弱维度
        weakest_dim = min(ANALYSIS_DIMENSIONS, key=lambda d: best[f"{d}_score"])
        strategies.append(f"差异化机会: 在'{weakest_dim}'维度建立优势，当前领先者仅{best[f'{weakest_dim}_score']}分")
    
    return strategies


def generate_risks(analysis: List[Dict[str, Any]]) -> List[str]:
    """
    生成风险提示
    
    Args:
        analysis: 分析结果列表
    
    Returns:
        风险提示列表
    """
    risks = []
    
    for comp in analysis:
        # 检查缺失字段
        missing = [f for f in ANALYSIS_DIMENSIONS if not comp.get(f)]
        if missing:
            risks.append(f"{comp['name']}: 缺少字段 {', '.join(missing)}，建议补充数据")
        
        # 检查低分维度
        low_dims = [f for f in ANALYSIS_DIMENSIONS if comp.get(f"{f}_score", 0) <= 3]
        if low_dims:
            risks.append(f"{comp['name']}: 维度 {', '.join(low_dims)} 得分较低，存在竞争风险")
    
    return risks


def generate_report(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    生成完整分析报告
    
    Args:
        data: 竞品数据列表
    
    Returns:
        报告字典
    """
    # 校验数据
    valid_data, warnings = validate_competitors(data)
    
    # 分析每个竞品
    analysis = [analyze_competitor(c) for c in valid_data]
    
    # 生成策略和风险
    strategies = generate_strategy(analysis)
    risks = generate_risks(analysis)
    
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "competitors": analysis,
        "strategies": strategies,
        "risks": risks,
        "warnings": warnings
    }
    
    return report


def export_csv(report: Dict[str, Any], filepath: str) -> None:
    """
    导出 CSV 报告
    
    Args:
        report: 报告字典
        filepath: 输出文件路径
    """
    fieldnames = ["name", "features_score", "pricing_score", "ux_score",
                  "positioning_score", "tech_stack_score", "operations_score", "overall_score"]
    
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for comp in report["competitors"]:
            row = {k: comp.get(k, "") for k in fieldnames}
            writer.writerow(row)


def atomic_write(filepath: str, content: str, dry_run: bool = False) -> None:
    """
    原子化写入文件
    
    Args:
        filepath: 文件路径
        content: 文件内容
        dry_run: 是否为预览模式
    """
    if not dry_run:
        # 确保目录存在
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # 原子写入
        fd, tmp_path = tempfile.mkstemp(dir=directory or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, filepath)
            print(f"[写入] {filepath}")
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
    else:
        print(f"[dry-run] 将写入 {filepath}（{len(content)} 字节），未落盘")


def run_selftest() -> int:
    """
    运行自测试，验证核心功能
    
    Returns:
        退出码（0 表示全部通过）
    """
    print("=== 自测试开始 ===")
    failures = 0
    
    # 测试 1: 数据校验
    print("\n[测试 1] 数据校验...")
    test_data = [
        {"name": "产品A", "features": ["f1", "f2"], "pricing": "免费"},
        {"name": "产品B", "pricing": "高价"},
        {"name": 123},  # 无效 name
        {"features": ["f1"]}  # 缺少 name
    ]
    valid, warnings = validate_competitors(test_data)
    assert len(valid) == 2, f"期望 2 个有效数据，实际 {len(valid)}"
    assert len(warnings) == 2, f"期望 2 条警告，实际 {len(warnings)}"
    print(f"  ✓ 通过 (有效数据: {len(valid)}, 警告: {len(warnings)})")
    
    # 测试 2: 评分逻辑
    print("\n[测试 2] 评分逻辑...")
    comp = {"name": "测试", "features": ["a", "b", "c", "d", "e"], "pricing": "免费", "ux": "简洁易用"}
    result = analyze_competitor(comp)
    assert result["features_score"] >= 5, f"功能评分异常: {result['features_score']}"
    assert result["pricing_score"] >= 8, f"定价评分异常: {result['pricing_score']}"
    assert result["ux_score"] >= 6, f"UX评分异常: {result['ux_score']}"
    assert 1 <= result["overall_score"] <= 10, f"总分异常: {result['overall_score']}"
    print(f"  ✓ 通过 (总分: {result['overall_score']})")
    
    # 测试 3: 报告生成
    print("\n[测试 3] 报告生成...")
    report = generate_report(test_data)
    assert "generated_at" in report, "报告缺少生成时间"
    assert len(report["competitors"]) == 2, f"报告竞品数量异常: {len(report['competitors'])}"
    assert len(report["strategies"]) > 0, "报告缺少策略建议"
    assert len(report["risks"]) > 0, "报告缺少风险提示"
    print(f"  ✓ 通过 (竞品: {len(report['competitors'])}, 策略: {len(report['strategies'])}, 风险: {len(report['risks'])})")
    
    # 测试 4: CSV 导出
    print("\n[测试 4] CSV 导出...")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test.csv")
        export_csv(report, csv_path)
        assert os.path.exists(csv_path), "CSV 文件未创建"
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        assert "name" in content, "CSV 缺少表头"
        assert "产品A" in content, "CSV 缺少数据"
    print("  ✓ 通过")
    
    # 测试 5: 空数据处理
    print("\n[测试 5] 空数据处理...")
    empty_report = generate_report([])
    assert len(empty_report["competitors"]) == 0, "空数据应返回空竞品列表"
    assert len(empty_report["strategies"]) == 1, "空数据应返回提示策略"
    print("  ✓ 通过")
    
    # 测试 6: 编码处理
    print("\n[测试 6] 编码处理...")
    with tempfile.NamedTemporaryFile(mode="w", encoding="gbk", suffix=".json", delete=False) as f:
        f.write(json.dumps([{"name": "中文产品", "pricing": "免费"}]))
        tmp_path = f.name
    try:
        content = read_file_with_encoding(tmp_path)
        data = parse_json_data(content)
        assert len(data) == 1, "GBK 编码解析失败"
        assert data[0]["name"] == "中文产品", "中文名称解析失败"
    finally:
        os.unlink(tmp_path)
    print("  ✓ 通过")
    
    # 测试 7: URL 重试逻辑（模拟失败）
    print("\n[测试 7] URL 重试逻辑...")
    try:
        fetch_url_with_retry("http://127.0.0.1:1/nonexistent", timeout=1, max_retries=1)
        assert False, "应抛出异常"
    except urllib.error.URLError:
        print("  ✓ 通过 (正确抛出异常)")
    
    # 测试 8: dry-run 模式
    print("\n[测试 8] dry-run 模式...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        atomic_write(test_file, "测试内容", dry_run=True)
        assert not os.path.exists(test_file), "dry-run 模式不应创建文件"
        atomic_write(test_file, "测试内容", dry_run=False)
        assert os.path.exists(test_file), "正常模式应创建文件"
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "测试内容", "文件内容不正确"
    print("  ✓ 通过")
    
    # 汇总
    print(f"\n=== 自测试完成: {failures} 个失败 ===")
    return ERR_SUCCESS if failures == 0 else 1


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="竞品分析工具 - 多维度拆解竞品，输出差异化策略建议",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --demo                     # 使用内置示例数据
  python run.py --input data.json          # 从文件读取数据
  python run.py --url https://...          # 从 URL 获取数据
  python run.py --input data.json --export report.csv  # 导出 CSV
  python run.py --selftest                 # 运行自测试
        """
    )
    
    # 输入源（互斥）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", type=str, help="输入 JSON 文件路径")
    input_group.add_argument("--url", type=str, help="数据源 URL")
    input_group.add_argument("--demo", action="store_true", help="使用内置示例数据")
    
    # 输出选项
    parser.add_argument("--export", type=str, help="导出 CSV 报告路径")
    parser.add_argument("--output-dir", type=str, default=".", help="输出目录（默认当前目录）")
    
    # 其他选项
    parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写文件")
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自测试模式
    if args.selftest:
        return run_selftest()
    
    # 加载数据
    try:
        if args.demo:
            # 内置示例数据
            demo_data = [
                {
                    "name": "示例产品A",
                    "features": ["用户管理", "数据分析", "报表导出", "权限控制", "API接口", "多语言", "移动端"],
                    "pricing": "免费版+付费版",
                    "ux": "界面简洁，操作直观，学习成本低",
                    "positioning": "面向中小企业的专业解决方案",
                    "tech_stack": ["Python", "React", "PostgreSQL", "Docker"],
                    "operations": "社区运营+内容营销+用户增长"
                },
                {
                    "name": "示例产品B",
                    "features": ["基础功能", "模板库"],
                    "pricing": "高价定制",
                    "ux": "功能强大但界面复杂",
                    "positioning": "高端企业级产品",
                    "tech_stack": ["Java", "Oracle", "WebLogic"],
                    "operations": "传统销售模式"
                },
                {
                    "name": "示例产品C",
                    "features": ["协作", "分享", "评论", "版本管理", "搜索", "标签"],
                    "pricing": "免费",
                    "ux": "简洁易用，上手快",
                    "positioning": "大众市场免费工具",
                    "tech_stack": ["Node.js", "Vue.js", "MongoDB"],
                    "operations": "用户口碑传播+社交媒体运营"
                }
            ]
            data = demo_data
            if args.verbose:
                print(f"[INFO] 使用内置示例数据，共 {len(data)} 个竞品")
        
        elif args.input:
            if args.verbose:
                print(f"[INFO] 从文件读取数据: {args.input}")
            content = read_file_with_encoding(args.input)
            data = parse_json_data(content)
            if args.verbose:
                print(f"[INFO] 成功解析 {len(data)} 个竞品")
        
        elif args.url:
            if args.verbose:
                print(f"[INFO] 从 URL 获取数据: {args.url}")
            content = fetch_url_with_retry(args.url)
            data = parse_json_data(content)
            if args.verbose:
                print(f"[INFO] 成功获取 {len(data)} 个竞品")
        
        else:
            parser.error("请指定输入源: --input, --url 或 --demo")
            return ERR_PARAM
    
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return ERR_FILE_NOT_FOUND
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}", file=sys.stderr)
        return ERR_INVALID_DATA
    except urllib.error.URLError as e:
        print(f"[ERROR] URL 请求失败: {e}", file=sys.stderr)
        return ERR_URL_FAILED
    except Exception as e:
        print(f"[ERROR] 数据加载失败: {e}", file=sys.stderr)
        return ERR_INVALID_DATA
    
    # 生成报告
    try:
        report = generate_report(data)
    except Exception as e:
        print(f"[ERROR] 报告生成失败: {e}", file=sys.stderr)
        return ERR_INVALID_DATA
    
    # 输出报告
    if args.verbose:
        print("\n=== 分析报告 ===")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        # 简洁输出
        print(f"分析完成: {len(report['competitors'])} 个竞品")
        for comp in report["competitors"]:
            print(f"  {comp['name']}: 总分 {comp['overall_score']}")
        if report["strategies"]:
            print("\n策略建议:")
            for s in report["strategies"]:
                print(f"  - {s}")
        if report["risks"]:
            print("\n风险提示:")
            for r in report["risks"]:
                print(f"  - {r}")
        if report["warnings"]:
            print("\n警告:")
            for w in report["warnings"]:
                print(f"  - {w}")
    
    # 导出 CSV
    if args.export:
        try:
            export_path = os.path.join(args.output_dir, args.export)
            if not args.dry_run:
                export_csv(report, export_path)
                print(f"\nCSV 已导出到: {export_path}")
            else:
                print(f"\n[dry-run] 将导出 CSV 到: {export_path}，未落盘")
        except Exception as e:
            print(f"[ERROR] CSV 导出失败: {e}", file=sys.stderr)
            return ERR_OUTPUT_DIR
    
    return ERR_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
