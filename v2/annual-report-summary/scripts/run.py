#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
annual-report-summary — 配套执行器（原创实现，clean-room）
技能「annual-report-summary」的轻量辅助脚本：解析同目录 SKILL.md，提供 CLI 入口、触发词匹配、能力速览。
零第三方依赖。
"""
from __future__ import annotations
import argparse, re, sys, json, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
TRIGGERS = ["annual-report-summary", "年报解读", "财报分析", "投资要点摘要", ""]

# 非数值模式（用于过滤无效数据）
NON_NUMERIC_PATTERNS = [
    r'[a-zA-Z\u4e00-\u9fff]+',  # 字母或中文
    r'[^\d.\-+%]',  # 非数字、点、负号、加号、百分号
    r'^\s*$',  # 空字符串
]

# 数值范围校验（ROE、净利润增长率等指标的合理范围）
VALUE_RANGES = {
    'roe': (-100, 100),  # ROE 百分比范围
    'net_profit_growth': (-1000, 1000),  # 净利润增长率百分比范围
    'revenue_growth': (-1000, 1000),  # 营收增长率百分比范围
    'debt_ratio': (0, 100),  # 资产负债率百分比范围
}

# 真实数据源配置（东方财富公开接口）
DATA_SOURCE_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
DATA_SOURCE_PARAMS = {
    "reportName": "RPT_LICO_FN_CPD",
    "columns": "ALL",
    "filter": "(SECURITY_CODE=\"600519\")",
    "pageNumber": "1",
    "pageSize": "1",
    "sortTypes": "-1",
    "sortColumns": "REPORT_DATE",
    "source": "WEB",
    "client": "WEB",
    "v": "1"
}
REQUEST_TIMEOUT = 10  # 秒
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 秒


class IndicatorExtractor:
    """从年报文本中提取财务指标"""

    def __init__(self):
        self.patterns = {
            'roe': [
                r'加权平均净资产收益率[^\d\-]*([\d.]+)%',
                r'净资产收益率[^\d\-]*([\d.]+)%',
                r'ROE[^\d\-]*([\d.]+)%',
            ],
            'net_profit_growth': [
                r'归属于上市公司股东的净利润增长率[^\d\-]*([\d.]+)%',
                r'净利润增长率[^\d\-]*([\d.]+)%',
                r'净利润同比增长[^\d\-]*([\d.]+)%',
            ],
            'revenue_growth': [
                r'营业收入增长率[^\d\-]*([\d.]+)%',
                r'营收增长率[^\d\-]*([\d.]+)%',
                r'营业收入同比增长[^\d\-]*([\d.]+)%',
            ],
            'debt_ratio': [
                r'资产负债率[^\d\-]*([\d.]+)%',
                r'负债率[^\d\-]*([\d.]+)%',
            ],
        }

    def _is_valid_number(self, value: float, indicator: str) -> bool:
        """校验数值是否在合理范围内"""
        if indicator in VALUE_RANGES:
            min_val, max_val = VALUE_RANGES[indicator]
            return min_val <= value <= max_val
        return True

    def _clean_value(self, raw: str) -> float | None:
        """清理并转换数值，过滤非数值模式"""
        raw = raw.strip()
        # 过滤非数值模式
        for pattern in NON_NUMERIC_PATTERNS:
            if re.search(pattern, raw) and not re.search(r'[\d.]+', raw):
                return None
        # 提取数值
        match = re.search(r'-?\d+\.?\d*', raw)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def extract(self, text: str) -> dict:
        """从文本中提取所有财务指标"""
        results = {}
        for indicator, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = self._clean_value(match.group(1))
                    if value is not None and self._is_valid_number(value, indicator):
                        results[indicator] = value
                        break
        return results


def load_spec() -> str:
    # 资产池/发布目录均为 SKILL.md 在技能根目录、scripts/ 为其子目录，故读父目录
    p = HERE.parent / "SKILL.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def match_trigger(text: str):
    low = text.lower()
    return [t for t in TRIGGERS if t.lower() in low]


def extract_from_file(file_path: str) -> dict:
    """从文件读取文本并提取指标"""
    try:
        text = Path(file_path).read_text(encoding='utf-8')
    except Exception as e:
        raise ValueError(f"无法读取文件: {e}")
    extractor = IndicatorExtractor()
    return extractor.extract(text)


def _fetch_with_retry(url: str) -> dict:
    """
    带重试退避的HTTP请求函数
    使用urllib发起请求，按指数退避重试，处理超时和HTTP错误
    """
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/"
            })
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == MAX_RETRIES - 1:
                raise ConnectionError(f"请求失败（已重试{MAX_RETRIES}次）: {e}")
            # 指数退避
            time.sleep(RETRY_BACKOFF * (2 ** attempt))
    raise ConnectionError("请求失败")


def fetch_real_data() -> dict:
    """
    从东方财富公开接口获取真实年报数据（贵州茅台示例）
    带重试退避和超时控制
    """
    params = urllib.parse.urlencode(DATA_SOURCE_PARAMS)
    url = f"{DATA_SOURCE_URL}?{params}"

    try:
        data = _fetch_with_retry(url)
        if data.get("result") and data["result"].get("data"):
            record = data["result"]["data"][0]
            # 提取关键财务指标
            indicators = {}
            # 净资产收益率
            if record.get("WEIGHTAVG_ROE") is not None:
                indicators['roe'] = float(record["WEIGHTAVG_ROE"])
            # 净利润增长率
            if record.get("PARENT_NETPROFIT_YOY") is not None:
                indicators['net_profit_growth'] = float(record["PARENT_NETPROFIT_YOY"])
            # 营收增长率
            if record.get("TOTAL_OPERATE_INCOME_YOY") is not None:
                indicators['revenue_growth'] = float(record["TOTAL_OPERATE_INCOME_YOY"])
            # 资产负债率
            if record.get("DEBT_ASSET_RATIO") is not None:
                indicators['debt_ratio'] = float(record["DEBT_ASSET_RATIO"])

            if indicators:
                return indicators
            else:
                raise ValueError("接口返回数据中未找到有效财务指标")
        else:
            raise ValueError("接口返回数据格式异常")
    except (ValueError, KeyError) as e:
        raise ConnectionError(f"数据解析失败: {e}")


def selftest() -> int:
    """自检核心提取链路（使用真实数据源）"""
    print("== 运行自检 ==")

    # 测试1: 触发器
    assert TRIGGERS, "触发器列表为空"
    assert load_spec().strip(), "SKILL.md 为空"
    sample = " ".join(TRIGGERS[:1])
    got = match_trigger(sample)
    assert got, "触发匹配失败"
    print("  [OK] 触发器匹配:", got)

    # 测试2: 核心提取逻辑（使用真实数据源）
    try:
        real_data = fetch_real_data()
        assert real_data, "真实数据获取失败"
        assert 'roe' in real_data, "真实数据缺少ROE"
        assert 'net_profit_growth' in real_data, "真实数据缺少净利润增长率"
        print("  [OK] 真实数据源获取:", real_data)
    except ConnectionError as e:
        print(f"  [WARN] 真实数据源不可用，使用本地样本验证: {e}")
        # 使用本地样本作为备选验证
        test_text = """
        公司年报显示，2023年度加权平均净资产收益率为15.23%，
        归属于上市公司股东的净利润增长率为25.67%，
        营业收入增长率为18.45%，资产负债率为45.67%。
        """
        extractor = IndicatorExtractor()
        results = extractor.extract(test_text)
        assert 'roe' in results, "ROE 提取失败"
        assert 'net_profit_growth' in results, "净利润增长率提取失败"
        assert 'revenue_growth' in results, "营收增长率提取失败"
        assert 'debt_ratio' in results, "资产负债率提取失败"
        assert abs(results['roe'] - 15.23) < 0.01, f"ROE 值错误: {results['roe']}"
        assert abs(results['net_profit_growth'] - 25.67) < 0.01, f"净利润增长率错误: {results['net_profit_growth']}"
        print("  [OK] 本地样本提取逻辑:", results)

    # 测试3: 无效数据过滤
    invalid_text = "ROE为abc%，净利润增长率为xyz%"
    extractor = IndicatorExtractor()
    invalid_results = extractor.extract(invalid_text)
    assert 'roe' not in invalid_results, "无效ROE未被过滤"
    assert 'net_profit_growth' not in invalid_results, "无效净利润增长率未被过滤"
    print("  [OK] 无效数据过滤")

    # 测试4: 数值范围校验
    out_of_range_text = "ROE为150%，净利润增长率为2000%"
    range_results = extractor.extract(out_of_range_text)
    assert 'roe' not in range_results, "超出范围的ROE未被过滤"
    assert 'net_profit_growth' not in range_results, "超出范围的净利润增长率未被过滤"
    print("  [OK] 数值范围校验")

    # 测试5: 文件提取
    test_file = HERE / "test_annual_report.txt"
    test_text = """
    公司年报显示，2023年度加权平均净资产收益率为15.23%，
    归属于上市公司股东的净利润增长率为25.67%，
    营业收入增长率为18.45%，资产负债率为45.67%。
    """
    test_file.write_text(test_text, encoding='utf-8')
    try:
        file_results = extract_from_file(str(test_file))
        assert 'roe' in file_results, "文件提取失败"
        print("  [OK] 文件提取:", file_results)
    finally:
        test_file.unlink(missing_ok=True)

    # 测试6: 主流程调用（通过CLI入口）
    import subprocess
    test_text = """
    公司年报显示，2023年度加权平均净资产收益率为15.23%，
    归属于上市公司股东的净利润增长率为25.67%，
    营业收入增长率为18.45%，资产负债率为45.67%。
    """
    result = subprocess.run(
        [sys.executable, str(__file__), "--text", test_text, "--json"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"主流程退出码非0: {result.returncode}"
    output = json.loads(result.stdout)
    assert 'indicators' in output, "主流程输出缺少indicators"
    assert 'roe' in output['indicators'], "主流程输出缺少ROE"
    assert abs(output['indicators']['roe'] - 15.23) < 0.01, f"主流程ROE值错误: {output['indicators']['roe']}"
    print("  [OK] 主流程CLI调用:", output['indicators'])

    # 测试7: 文件参数主流程调用
    test_file = HERE / "test_annual_report_cli.txt"
    test_file.write_text(test_text, encoding='utf-8')
    try:
        result = subprocess.run(
            [sys.executable, str(__file__), "--file", str(test_file), "--json"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"文件参数主流程退出码非0: {result.returncode}"
        output = json.loads(result.stdout)
        assert 'indicators' in output, "文件参数主流程输出缺少indicators"
        assert 'roe' in output['indicators'], "文件参数主流程输出缺少ROE"
        assert abs(output['indicators']['roe'] - 15.23) < 0.01, f"文件参数主流程ROE值错误: {output['indicators']['roe']}"
        print("  [OK] 文件参数主流程CLI调用:", output['indicators'])
    finally:
        test_file.unlink(missing_ok=True)

    # 测试8: 真实数据源调用（如果可用）
    try:
        real_data = fetch_real_data()
        assert 'roe' in real_data, "真实数据源ROE缺失"
        assert 'net_profit_growth' in real_data, "真实数据源净利润增长率缺失"
        print("  [OK] 真实数据源调用:", real_data)
    except ConnectionError as e:
        print(f"  [WARN] 真实数据源不可用（不影响自检通过）: {e}")

    print("== annual-report-summary 配套执行器自检通过 ✅ ==")
    return 0


def main():
    ap = argparse.ArgumentParser(description="annual-report-summary 配套执行器")
    ap.add_argument("--text", default="", help="输入年报文本，提取财务指标")
    ap.add_argument("--file", default="", help="输入年报文件路径，提取财务指标")
    ap.add_argument("--json", action="store_true", help="以JSON格式输出结果")
    ap.add_argument("--guide", action="store_true", help="打印能力速览")
    ap.add_argument("--match", default="", help="输入文本，匹配触发词")
    ap.add_argument("--selftest", action="store_true", help="离线自检")
    ap.add_argument("--realtime", action="store_true", help="从真实数据源获取最新年报数据")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.match:
        print("命中触发词:", match_trigger(args.match))
        return 0

    if args.guide:
        md = load_spec()
        print("\n".join(l for l in md.splitlines() if l.strip())[:40])
        return 0

    # 提取财务指标
    extractor = IndicatorExtractor()
    results = {}

    if args.realtime:
        try:
            results = fetch_real_data()
        except ConnectionError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1
    elif args.text:
        results = extractor.extract(args.text)
    elif args.file:
        try:
            results = extract_from_file(args.file)
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    if results:
        if args.json:
            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "indicators": results
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            for key, value in results.items():
                print(f"{key}: {value}%")
        return 0
    else:
        print("未提取到有效财务指标", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
