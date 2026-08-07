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
VERSION = "2.0.0"

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
    从 URL 获取数据，带超时、指数退避重试和 Retry-After 支持
    
    Args:
        url: 数据源 URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
    
    Returns:
        获取到的文本内容
    
    Raises:
        urllib.error.URLError: 当 URL 请求失败时
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                # 读取内容并尝试解码
                raw_data = response.read()
                # 尝试多种编码
                for encoding in ["utf-8", "gbk", "gb18030"]:
                    try:
                        return raw_data.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                # 最后使用 replace 模式
                return raw_data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:  # Too Many Requests
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    delay = min(float(retry_after), MAX_RETRY_DELAY)
                else:
                    delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                print(f"HTTP 429: 请求过多，等待 {delay} 秒后重试...", file=sys.stderr)
                time.sleep(delay)
            elif e.code >= 500:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                print(f"HTTP {e.code}: 服务器错误，等待 {delay} 秒后重试...", file=sys.stderr)
                time.sleep(delay)
            else:
                raise
        except urllib.error.URLError as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(RETRY_BASE_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                print(f"URL 错误: {e.reason}，等待 {delay} 秒后重试...", file=sys.stderr)
                time.sleep(delay)
            else:
                raise
    
    raise last_error if last_error else urllib.error.URLError("Unknown error")


def read_file_with_encoding(filepath: str) -> str:
    """
    读取文件内容，支持多种编码
    
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
    for encoding in ["utf-8", "gbk", "gb18030"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    
    # 最后使用 replace 模式
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_csv_data(content: str) -> List[Dict[str, Any]]:
    """
    解析 CSV 数据为字典列表
    
    Args:
        content: CSV 内容字符串
    
    Returns:
        字典列表，每个字典代表一行数据
    """
    try:
        reader = csv.DictReader(content.splitlines())
        return [row for row in reader if any(row.values())]
    except Exception as e:
        print(f"CSV 解析失败: {e}", file=sys.stderr)
        return []


def parse_json_data(content: str) -> List[Dict[str, Any]]:
    """
    解析 JSON 数据为字典列表
    
    Args:
        content: JSON 内容字符串
    
    Returns:
        字典列表
    """
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            print(f"JSON 数据格式错误: 期望列表或字典，得到 {type(data).__name__}", file=sys.stderr)
            return []
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}", file=sys.stderr)
        return []


def parse_text_data(content: str) -> List[Dict[str, Any]]:
    """
    解析纯文本数据为字典列表
    
    支持格式：
    - 每行一个竞品，格式: 名称|功能|定价|用户体验|市场定位|技术架构|运营策略
    
    Args:
        content: 文本内容字符串
    
    Returns:
        字典列表
    """
    competitors = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 1:
            competitor = {"name": parts[0].strip()}
            if len(parts) > 1:
                competitor["features"] = parts[1].strip()
            if len(parts) > 2:
                competitor["pricing"] = parts[2].strip()
            if len(parts) > 3:
                competitor["ux"] = parts[3].strip()
            if len(parts) > 4:
                competitor["positioning"] = parts[4].strip()
            if len(parts) > 5:
                competitor["tech_stack"] = parts[5].strip()
            if len(parts) > 6:
                competitor["operations"] = parts[6].strip()
            competitors.append(competitor)
    return competitors


def load_data_from_file(filepath: str) -> List[Dict[str, Any]]:
    """
    从文件加载竞品数据
    
    Args:
        filepath: 文件路径
    
    Returns:
        竞品数据列表
    """
    content = read_file_with_encoding(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".csv":
        return parse_csv_data(content)
    elif ext == ".json":
        return parse_json_data(content)
    else:
        return parse_text_data(content)


def load_data_from_url(url: str) -> List[Dict[str, Any]]:
    """
    从 URL 加载竞品数据
    
    Args:
        url: 数据源 URL
    
    Returns:
        竞品数据列表
    """
    content = fetch_url_with_retry(url)
    # 尝试解析为 JSON
    data = parse_json_data(content)
    if data:
        return data
    # 尝试解析为 CSV
    data = parse_csv_data(content)
    if data:
        return data
    # 最后尝试纯文本
    return parse_text_data(content)


def validate_data(competitors: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    验证竞品数据完整性
    
    Args:
        competitors: 竞品数据列表
    
    Returns:
        (有效数据列表, 警告信息列表)
    """
    warnings = []
    valid_competitors = []
    
    for comp in competitors:
        if not isinstance(comp, dict):
            warnings.append(f"跳过无效数据: {comp}")
            continue
        
        # 检查必填字段
        missing_fields = [field for field in REQUIRED_FIELDS if field not in comp or not comp[field]]
        if missing_fields:
            warnings.append(f"竞品缺少必填字段 {missing_fields}: {comp}")
            continue
        
        # 标记缺失的可选字段
        for field in ANALYSIS_DIMENSIONS:
            if field not in comp or not comp[field]:
                comp[field] = f"[需核实:{field}]"
        
        valid_competitors.append(comp)
    
    # 检查竞品数量
    if len(valid_competitors) > MAX_COMPETITORS:
        warnings.append(f"竞品数量 {len(valid_competitors)} 超过建议上限 {MAX_COMPETITORS}，建议分批处理")
    
    return valid_competitors, warnings


def analyze_competitors(competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    执行竞品分析
    
    Args:
        competitors: 竞品数据列表
    
    Returns:
        分析结果字典
    """
    analysis = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "competitor_count": len(competitors),
        "competitors": competitors,
        "dimensions": ANALYSIS_DIMENSIONS,
        "summary": {}
    }
    
    # 生成摘要
    for dim in ANALYSIS_DIMENSIONS:
        values = [comp.get(dim, "") for comp in competitors if comp.get(dim)]
        analysis["summary"][dim] = {
            "count": len(values),
            "unique_values": len(set(values))
        }
    
    return analysis


def generate_strategy(analysis: Dict[str, Any]) -> List[str]:
    """
    生成差异化策略建议
    
    Args:
        analysis: 分析结果
    
    Returns:
        策略建议列表
    """
    strategies = []
    competitors = analysis["competitors"]
    
    if not competitors:
        strategies.append("无有效竞品数据，无法生成策略建议")
        return strategies
    
    # 分析功能维度
    features = [comp.get("features", "") for comp in competitors if comp.get("features")]
    if features:
        strategies.append(f"功能维度: 共分析 {len(features)} 个竞品的功能特性，建议关注差异化功能点")
    
    # 分析定价维度
    pricing = [comp.get("pricing", "") for comp in competitors if comp.get("pricing")]
    if pricing:
        strategies.append(f"定价维度: 共分析 {len(pricing)} 个竞品的定价策略，建议评估价格带覆盖")
    
    # 分析用户体验维度
    ux = [comp.get("ux", "") for comp in competitors if comp.get("ux")]
    if ux:
        strategies.append(f"用户体验维度: 共分析 {len(ux)} 个竞品的用户体验，建议优化关键交互流程")
    
    # 分析市场定位维度
    positioning = [comp.get("positioning", "") for comp in competitors if comp.get("positioning")]
    if positioning:
        strategies.append(f"市场定位维度: 共分析 {len(positioning)} 个竞品的市场定位，建议明确差异化定位")
    
    # 分析技术架构维度
    tech_stack = [comp.get("tech_stack", "") for comp in competitors if comp.get("tech_stack")]
    if tech_stack:
        strategies.append(f"技术架构维度: 共分析 {len(tech_stack)} 个竞品的技术架构，建议评估技术壁垒")
    
    # 分析运营策略维度
    operations = [comp.get("operations", "") for comp in competitors if comp.get("operations")]
    if operations:
        strategies.append(f"运营策略维度: 共分析 {len(operations)} 个竞品的运营策略，建议优化运营打法")
    
    # 生成综合建议
    strategies.append("综合建议: 基于多维度分析，建议聚焦 1-2 个核心差异化维度进行突破")
    
    return strategies


def generate_report(analysis: Dict[str, Any], strategies: List[str]) -> str:
    """
    生成结构化报告
    
    Args:
        analysis: 分析结果
        strategies: 策略建议
    
    Returns:
        报告文本
    """
    report = []
    report.append("# 竞品分析报告")
    report.append("")
    report.append(f"生成时间: {analysis['timestamp']}")
    report.append(f"竞品数量: {analysis['competitor_count']}")
    report.append("")
    
    # 竞品明细
    report.append("## 竞品明细")
    report.append("")
    for i, comp in enumerate(analysis["competitors"], 1):
        report.append(f"### {i}. {comp.get('name', '未知')}")
        for dim in ANALYSIS_DIMENSIONS:
            report.append(f"- {dim}: {comp.get(dim, '[需核实]')}")
        report.append("")
    
    # 策略建议
    report.append("## 差异化策略建议")
    report.append("")
    for strategy in strategies:
        report.append(f"- {strategy}")
    report.append("")
    
    return "\n".join(report)


def export_csv(competitors: List[Dict[str, Any]], output_path: str, dry: bool = False) -> bool:
    """
    导出竞品数据为 CSV 文件（原子写入）
    
    Args:
        competitors: 竞品数据列表
        output_path: 输出文件路径
        dry: 是否仅预览
    
    Returns:
        是否成功
    """
    if dry:
        print(f"[DRY-RUN] 将导出 {len(competitors)} 条竞品数据到 {output_path}")
        return True
    
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 原子写入
        fd, temp_path = tempfile.mkstemp(dir=output_dir if output_dir else ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                fieldnames = ["name"] + ANALYSIS_DIMENSIONS
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for comp in competitors:
                    row = {field: comp.get(field, "") for field in fieldnames}
                    writer.writerow(row)
            
            # 原子替换
            os.replace(temp_path, output_path)
        except Exception:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
        
        return True
    except Exception as e:
        print(f"CSV 导出失败: {e}", file=sys.stderr)
        return False


def run_selftest() -> int:
    """
    运行自测试，验证核心功能
    
    Returns:
        退出码（0 表示成功）
    """
    print("=== 运行自测试 ===")
    
    # 测试 1: 文本解析
    print("\n[测试 1] 文本解析")
    text_data = "竞品A|功能A|定价A|体验A|定位A|技术A|运营A\n竞品B|功能B|定价B|体验B|定位B|技术B|运营B"
    competitors = parse_text_data(text_data)
    assert len(competitors) == 2, f"预期 2 个竞品，实际 {len(competitors)}"
    assert competitors[0]["name"] == "竞品A", f"预期竞品A，实际 {competitors[0]['name']}"
    print("✓ 文本解析测试通过")
    
    # 测试 2: CSV 解析
    print("\n[测试 2] CSV 解析")
    csv_data = "name,features,pricing\n竞品C,功能C,定价C\n竞品D,功能D,定价D"
    csv_competitors = parse_csv_data(csv_data)
    assert len(csv_competitors) == 2, f"预期 2 个竞品，实际 {len(csv_competitors)}"
    assert csv_competitors[0]["name"] == "竞品C", f"预期竞品C，实际 {csv_competitors[0]['name']}"
    print("✓ CSV 解析测试通过")
    
    # 测试 3: JSON 解析
    print("\n[测试 3] JSON 解析")
    json_data = json.dumps([
        {"name": "竞品E", "features": "功能E"},
        {"name": "竞品F", "features": "功能F"}
    ])
    json_competitors = parse_json_data(json_data)
    assert len(json_competitors) == 2, f"预期 2 个竞品，实际 {len(json_competitors)}"
    assert json_competitors[1]["name"] == "竞品F", f"预期竞品F，实际 {json_competitors[1]['name']}"
    print("✓ JSON 解析测试通过")
    
    # 测试 4: 数据验证
    print("\n[测试 4] 数据验证")
    test_data = [
        {"name": "竞品G", "features": "功能G"},
        {"name": "", "features": "功能H"},
        {"name": "竞品I"}
    ]
    valid, warnings = validate_data(test_data)
    assert len(valid) == 2, f"预期 2 个有效竞品，实际 {len(valid)}"
    assert len(warnings) == 1, f"预期 1 个警告，实际 {len(warnings)}"
    assert valid[1]["pricing"] == "[需核实:pricing]", f"预期定价占位符，实际 {valid[1]['pricing']}"
    print("✓ 数据验证测试通过")
    
    # 测试 5: 分析功能
    print("\n[测试 5] 分析功能")
    analysis = analyze_competitors(valid)
    assert analysis["competitor_count"] == 2, f"预期 2 个竞品，实际 {analysis['competitor_count']}"
    assert "timestamp" in analysis, "缺少时间戳"
    print("✓ 分析功能测试通过")
    
    # 测试 6: 策略生成
    print("\n[测试 6] 策略生成")
    strategies = generate_strategy(analysis)
    assert len(strategies) > 0, "策略列表为空"
    print("✓ 策略生成测试通过")
    
    # 测试 7: 报告生成
    print("\n[测试 7] 报告生成")
    report = generate_report(analysis, strategies)
    assert "竞品分析报告" in report, "报告标题缺失"
    assert "差异化策略建议" in report, "策略建议缺失"
    print("✓ 报告生成测试通过")
    
    # 测试 8: CSV 导出（dry-run）
    print("\n[测试 8] CSV 导出（dry-run）")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test.csv")
        success = export_csv(valid, output_path, dry=True)
        assert success, "dry-run 导出失败"
        assert not os.path.exists(output_path), "dry-run 不应创建文件"
    print("✓ CSV 导出（dry-run）测试通过")
    
    # 测试 9: CSV 导出（实际写入）
    print("\n[测试 9] CSV 导出（实际写入）")
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test.csv")
        success = export_csv(valid, output_path, dry=False)
        assert success, "实际导出失败"
        assert os.path.exists(output_path), "导出文件不存在"
        # 验证文件内容
        content = read_file_with_encoding(output_path)
        assert "name" in content, "CSV 缺少表头"
    print("✓ CSV 导出（实际写入）测试通过")
    
    # 测试 10: 中文标点处理
    print("\n[测试 10] 中文标点处理")
    chinese_text = "竞品甲，功能：A、B、C；定价：100元"
    chinese_competitors = parse_text_data(chinese_text)
    assert len(chinese_competitors) == 1, f"预期 1 个竞品，实际 {len(chinese_competitors)}"
    assert chinese_competitors[0]["name"] == "竞品甲，功能：A、B、C；定价：100元", "中文标点处理异常"
    print("✓ 中文标点处理测试通过")
    
    # 测试 11: 空输入处理
    print("\n[测试 11] 空输入处理")
    empty_competitors = parse_text_data("")
    assert len(empty_competitors) == 0, f"预期 0 个竞品，实际 {len(empty_competitors)}"
    print("✓ 空输入处理测试通过")
    
    # 测试 12: 超长输入处理
    print("\n[测试 12] 超长输入处理")
    long_text = "|".join(["竞品" + str(i) for i in range(100)])
    long_competitors = parse_text_data(long_text)
    assert len(long_competitors) == 1, f"预期 1 个竞品，实际 {len(long_competitors)}"
    print("✓ 超长输入处理测试通过")
    
    print("\n=== 所有自测试通过 ===")
    return ERR_SUCCESS


def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="竞品分析工具 - 多维度拆解竞品，输出差异化策略建议",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --file competitors.csv
  %(prog)s --url https://example.com/competitors.json
  %(prog)s --text "竞品A|功能A|定价A"
  %(prog)s --selftest
        """
    )
    
    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", "-f", help="从文件加载竞品数据（支持 CSV/JSON/TXT）")
    input_group.add_argument("--url", "-u", help="从 URL 加载竞品数据")
    input_group.add_argument("--text", "-t", help="直接输入竞品文本数据")
    
    # 输出参数
    parser.add_argument("--output", "-o", help="输出报告文件路径")
    parser.add_argument("--csv", help="导出 CSV 文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不实际写入文件")
    parser.add_argument("--force", action="store_true", help="强制写入文件（跳过 dry-run 保护）")
    parser.add_argument("--verbose", "-v", action="store_true", help="输出详细处理信息")
    
    # 其他参数
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    
    args = parser.parse_args()
    
    # 运行自测试
    if args.selftest:
        return run_selftest()
    
    # 检查输入参数
    if not args.file and not args.url and not args.text:
        parser.error("请提供输入数据：--file、--url 或 --text")
    
    # 加载数据
    try:
        if args.file:
            if args.verbose:
                print(f"从文件加载数据: {args.file}", file=sys.stderr)
            competitors = load_data_from_file(args.file)
        elif args.url:
            if args.verbose:
                print(f"从 URL 加载数据: {args.url}", file=sys.stderr)
            competitors = load_data_from_url(args.url)
        else:
            if args.verbose:
                print("从命令行参数加载数据", file=sys.stderr)
            competitors = parse_text_data(args.text)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return ERR_FILE_NOT_FOUND
    except urllib.error.URLError as e:
        print(f"错误: URL 请求失败: {e}", file=sys.stderr)
        return ERR_URL_FAILED
    except Exception as e:
        print(f"错误: 数据加载失败: {e}", file=sys.stderr)
        return ERR_INVALID_DATA
    
    # 验证数据
    valid_competitors, warnings = validate_data(competitors)
    
    # 输出警告
    for warning in warnings:
        print(f"警告: {warning}", file=sys.stderr)
    
    if not valid_competitors:
        print("错误: 没有有效的竞品数据", file=sys.stderr)
        return ERR_INVALID_DATA
    
    if args.verbose:
        print(f"有效竞品数量: {len(valid_competitors)}", file=sys.stderr)
        for dim in ANALYSIS_DIMENSIONS:
            count = sum(1 for comp in valid_competitors if comp.get(dim) and not comp[dim].startswith("[需核实"))
            print(f"  {dim}: {count}/{len(valid_competitors)} 个竞品有数据", file=sys.stderr)
    
    # 执行分析
    analysis = analyze_competitors(valid_competitors)
    strategies = generate_strategy(analysis)
    report = generate_report(analysis, strategies)
    
    # 输出报告
    if args.output:
        # 检查 dry-run
        if args.dry_run and not args.force:
            print(f"[DRY-RUN] 将写入报告到: {args.output}")
            print("--- 报告预览 ---")
            print(report[:500] + ("..." if len(report) > 500 else ""))
            print("--- 预览结束 ---")
        else:
            try:
                # 确保输出目录存在
                output_dir = os.path.dirname(args.output)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                # 原子写入
                fd, temp_path = tempfile.mkstemp(dir=output_dir if output_dir else ".")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(report)
                    os.replace(temp_path, args.output)
                except Exception:
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise
                
                print(f"报告已写入: {args.output}")
            except Exception as e:
                print(f"错误: 报告写入失败: {e}", file=sys.stderr)
                return ERR_OUTPUT_DIR
    else:
        print(report)
    
    # 导出 CSV
    if args.csv:
        success = export_csv(valid_competitors, args.csv, dry=args.dry_run and not args.force)
        if not success:
            return ERR_OUTPUT_DIR
        if not (args.dry_run and not args.force):
            print(f"CSV 已导出: {args.csv}")
    
    return ERR_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
