#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai-api-router 主脚本

根据预算、延迟、模型需求，推荐并配置AI API中转服务，生成接入代码。
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 内置数据（硬编码样例，不依赖外部文件）
# ============================================================

# 内置中转服务参数表
# 字段: name, base_url, price_per_million_tokens, latency_ms, models
BUILTIN_PROVIDERS = [
    {
        "name": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "price_per_million_tokens": 0.5,
        "latency_ms": 300,
        "models": ["gpt-4o", "claude-3.5-sonnet", "llama-3.1-70b"],
    },
    {
        "name": "one-api",
        "base_url": "https://one-api.example.com/v1",
        "price_per_million_tokens": 0.3,
        "latency_ms": 500,
        "models": ["gpt-4o", "claude-3.5-sonnet"],
    },
    {
        "name": "new-api",
        "base_url": "https://new-api.example.com/v1",
        "price_per_million_tokens": 0.2,
        "latency_ms": 800,
        "models": ["gpt-3.5-turbo", "llama-3.1-70b"],
    },
    {
        "name": "closeai",
        "base_url": "https://closeai.example.com/v1",
        "price_per_million_tokens": 0.1,
        "latency_ms": 1200,
        "models": ["gpt-3.5-turbo"],
    },
]


# ============================================================
# 错误码定义
# ============================================================
class AppError(Exception):
    """应用自定义异常基类"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# 输入校验（R7: guard clause 顶部先校验）
# ============================================================
def validate_budget(budget: Optional[float]) -> float:
    """校验预算参数，返回合法值或抛异常"""
    if budget is None:
        return 1.0  # 默认预算
    if not isinstance(budget, (int, float)):
        raise AppError("E001", f"预算必须是数字，收到: {type(budget).__name__}")
    if budget <= 0:
        raise AppError("E002", f"预算必须为正数，收到: {budget}")
    return float(budget)


def validate_latency(latency: Optional[int]) -> int:
    """校验延迟阈值参数"""
    if latency is None:
        return 1000  # 默认延迟阈值 ms
    if not isinstance(latency, int):
        raise AppError("E003", f"延迟阈值必须是整数，收到: {type(latency).__name__}")
    if latency <= 0:
        raise AppError("E004", f"延迟阈值必须为正数，收到: {latency}")
    return latency


def validate_model_type(model_type: Optional[str]) -> str:
    """校验模型类型参数"""
    if model_type is None:
        return "chat"  # 默认模型类型
    if not isinstance(model_type, str):
        raise AppError("E005", f"模型类型必须是字符串，收到: {type(model_type).__name__}")
    if model_type not in ("chat", "embedding", "image"):
        raise AppError("E006", f"不支持的模型类型: {model_type}，可选: chat/embedding/image")
    return model_type


def validate_monthly_tokens(tokens: Optional[int]) -> int:
    """校验月度调用量参数"""
    if tokens is None:
        return 1000000  # 默认每月 100 万 tokens
    if not isinstance(tokens, int):
        raise AppError("E007", f"月度调用量必须是整数，收到: {type(tokens).__name__}")
    if tokens <= 0:
        raise AppError("E008", f"月度调用量必须为正数，收到: {tokens}")
    return tokens


# ============================================================
# 核心逻辑（R8: 函数短小单一）
# ============================================================
def parse_requirements(
    budget: Optional[float],
    latency: Optional[int],
    model_type: Optional[str],
    monthly_tokens: Optional[int],
) -> Dict:
    """解析用户需求为结构化参数（能力1: 需求解析）"""
    # 校验所有输入
    validated_budget = validate_budget(budget)
    validated_latency = validate_latency(latency)
    validated_model_type = validate_model_type(model_type)
    validated_tokens = validate_monthly_tokens(monthly_tokens)

    # 返回结构化需求
    return {
        "budget": validated_budget,
        "latency_ms": validated_latency,
        "model_type": validated_model_type,
        "monthly_tokens": validated_tokens,
    }


def recommend_providers(requirements: Dict, providers: Optional[List[Dict]] = None) -> List[Dict]:
    """根据需求匹配候选服务（能力2: 服务推荐）"""
    # 使用内置数据或自定义数据
    source_providers = providers if providers is not None else BUILTIN_PROVIDERS

    # 防御性拷贝，避免修改外部数据
    candidates = [dict(p) for p in source_providers]

    # 按预算过滤
    budget_filtered = [
        p for p in candidates
        if p["price_per_million_tokens"] <= requirements["budget"]
    ]

    # 按延迟过滤
    latency_filtered = [
        p for p in budget_filtered
        if p["latency_ms"] <= requirements["latency_ms"]
    ]

    # 按模型类型过滤（简化：chat 类型匹配所有，其他类型仅匹配包含对应模型的）
    if requirements["model_type"] == "chat":
        final_candidates = latency_filtered
    else:
        final_candidates = [
            p for p in latency_filtered
            if any(requirements["model_type"] in m for m in p["models"])
        ]

    # 按性价比排序（价格优先，延迟次之）
    final_candidates.sort(
        key=lambda p: (p["price_per_million_tokens"], p["latency_ms"])
    )

    # 返回前 3 个
    return final_candidates[:3]


def estimate_cost(provider: Dict, monthly_tokens: int) -> float:
    """估算月度开销（能力4: 成本估算）"""
    # 成本 = 每百万 tokens 价格 × 月度调用量（百万）
    cost = provider["price_per_million_tokens"] * (monthly_tokens / 1_000_000)
    return round(cost, 2)


def generate_config(provider: Dict, api_key_placeholder: str = "YOUR_API_KEY") -> Dict:
    """生成配置信息（能力3: 配置生成）"""
    return {
        "base_url": provider["base_url"],
        "api_key": api_key_placeholder,
        "model": provider["models"][0] if provider["models"] else "gpt-3.5-turbo",
    }


def generate_python_code(config: Dict) -> str:
    """生成 Python 调用代码"""
    return f'''import openai

client = openai.OpenAI(
    base_url="{config["base_url"]}",
    api_key="{config["api_key"]}",
)

response = client.chat.completions.create(
    model="{config["model"]}",
    messages=[{{"role": "user", "content": "Hello"}}],
)
print(response.choices[0].message.content)
'''


def generate_curl_code(config: Dict) -> str:
    """生成 curl 调用代码"""
    return f'''curl {config["base_url"]}/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {config["api_key"]}" \\
  -d '{{"model": "{config["model"]}", "messages": [{{"role": "user", "content": "Hello"}}]}}'
'''


def generate_migration_steps(old_provider: str, new_provider: Dict) -> List[str]:
    """生成迁移步骤（能力5: 迁移辅助）"""
    return [
        f"1. 修改环境变量 OPENAI_BASE_URL 为 {new_provider['base_url']}",
        f"2. 修改环境变量 OPENAI_API_KEY 为新的 API Key",
        f"3. 将代码中的模型名改为 {new_provider['models'][0] if new_provider['models'] else 'gpt-3.5-turbo'}",
        f"4. 测试新配置：运行 curl 或 Python 示例代码",
        f"5. 确认无误后，更新生产环境配置",
    ]


# ============================================================
# 输出格式化（R6: 可解释输出）
# ============================================================
def format_recommendation(
    requirements: Dict,
    candidates: List[Dict],
    verbose: bool = False,
) -> str:
    """格式化推荐结果输出"""
    lines = []
    lines.append("=" * 60)
    lines.append("AI API 中转服务推荐结果")
    lines.append("=" * 60)

    # 需求摘要
    lines.append("\n【需求参数】")
    lines.append(f"  预算上限: ${requirements['budget']}/百万 tokens")
    lines.append(f"  延迟阈值: {requirements['latency_ms']}ms")
    lines.append(f"  模型类型: {requirements['model_type']}")
    lines.append(f"  月度调用量: {requirements['monthly_tokens']:,} tokens")

    if not candidates:
        lines.append("\n【推荐结果】")
        lines.append("  未找到满足条件的中转服务，请放宽预算或延迟限制。")
        return "\n".join(lines)

    # 推荐列表
    lines.append("\n【候选方案对比】")
    for idx, provider in enumerate(candidates, 1):
        cost = estimate_cost(provider, requirements["monthly_tokens"])
        lines.append(f"\n  方案{idx}: {provider['name']}")
        lines.append(f"    - base_url: {provider['base_url']}")
        lines.append(f"    - 价格: ${provider['price_per_million_tokens']}/百万 tokens")
        lines.append(f"    - 延迟: {provider['latency_ms']}ms")
        lines.append(f"    - 支持模型: {', '.join(provider['models'])}")
        lines.append(f"    - 预估月成本: ${cost}")

        if verbose:
            # 详细模式：输出决策明细（R6）
            lines.append(f"    [决策明细] 价格 {provider['price_per_million_tokens']} <= 预算 {requirements['budget']}, "
                        f"延迟 {provider['latency_ms']} <= 阈值 {requirements['latency_ms']}")

    # 最佳方案配置
    best = candidates[0]
    config = generate_config(best)
    lines.append("\n【推荐配置】")
    lines.append(f"  base_url: {config['base_url']}")
    lines.append(f"  api_key: {config['api_key']}  (请替换为真实密钥)")
    lines.append(f"  model: {config['model']}")

    # 接入代码
    lines.append("\n【Python 接入代码】")
    lines.append(generate_python_code(config))

    lines.append("\n【curl 接入代码】")
    lines.append(generate_curl_code(config))

    # 迁移步骤
    lines.append("\n【迁移步骤】")
    for step in generate_migration_steps("旧服务", best):
        lines.append(f"  {step}")

    lines.append("\n" + "=" * 60)
    lines.append("提示: 以上配置仅为示例，请替换为真实 API Key 并确认服务可用性。")
    lines.append("=" * 60)

    return "\n".join(lines)


# ============================================================
# 自检函数（R1: 契约先于代码）
# ============================================================
def run_selftest() -> bool:
    """
    内置硬编码样例数据离线自检核心逻辑。
    不读外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。
    """
    print("开始自检...")

    # 测试1: 需求解析（正常输入）
    try:
        req = parse_requirements(0.5, 500, "chat", 1000000)
        assert req["budget"] == 0.5, "预算解析错误"
        assert req["latency_ms"] == 500, "延迟解析错误"
        assert req["model_type"] == "chat", "模型类型解析错误"
        assert req["monthly_tokens"] == 1000000, "月度调用量解析错误"
        print("  ✓ 需求解析正常输入通过")
    except Exception as e:
        print(f"  ✗ 需求解析正常输入失败: {e}")
        return False

    # 测试2: 需求解析（默认值）
    try:
        req = parse_requirements(None, None, None, None)
        assert req["budget"] > 0, "默认预算应为正数"
        assert req["latency_ms"] > 0, "默认延迟应为正数"
        assert req["model_type"] == "chat", "默认模型类型应为 chat"
        assert req["monthly_tokens"] > 0, "默认月度调用量应为正数"
        print("  ✓ 需求解析默认值通过")
    except Exception as e:
        print(f"  ✗ 需求解析默认值失败: {e}")
        return False

    # 测试3: 需求解析（异常输入）
    try:
        try:
            parse_requirements(-1, 500, "chat", 1000000)
            print("  ✗ 负数预算未抛异常")
            return False
        except AppError as e:
            assert e.code == "E002", f"错误码应为 E002，收到 {e.code}"
        print("  ✓ 需求解析异常输入通过")
    except Exception as e:
        print(f"  ✗ 需求解析异常输入失败: {e}")
        return False

    # 测试4: 服务推荐（正常场景）
    try:
        req = parse_requirements(0.5, 1000, "chat", 1000000)
        candidates = recommend_providers(req)
        assert len(candidates) > 0, "应至少推荐一个服务"
        assert len(candidates) <= 3, "推荐服务不应超过 3 个"
        for c in candidates:
            assert c["price_per_million_tokens"] <= 0.5, "推荐服务价格应不超过预算"
            assert c["latency_ms"] <= 1000, "推荐服务延迟应不超过阈值"
        print("  ✓ 服务推荐正常场景通过")
    except Exception as e:
        print(f"  ✗ 服务推荐正常场景失败: {e}")
        return False

    # 测试5: 服务推荐（无匹配场景）
    try:
        req = parse_requirements(0.01, 10, "chat", 1000000)
        candidates = recommend_providers(req)
        assert len(candidates) == 0, "极端限制下不应有推荐"
        print("  ✓ 服务推荐无匹配场景通过")
    except Exception as e:
        print(f"  ✗ 服务推荐无匹配场景失败: {e}")
        return False

    # 测试6: 成本估算
    try:
        test_provider = {"name": "test", "price_per_million_tokens": 0.5}
        cost = estimate_cost(test_provider, 2000000)
        assert cost == 1.0, f"成本估算错误: {cost}"
        print("  ✓ 成本估算通过")
    except Exception as e:
        print(f"  ✗ 成本估算失败: {e}")
        return False

    # 测试7: 配置生成
    try:
        test_provider = {"name": "test", "base_url": "https://test.example.com/v1", "models": ["gpt-4o"]}
        config = generate_config(test_provider)
        assert config["base_url"] == "https://test.example.com/v1", "base_url 错误"
        assert config["api_key"] == "YOUR_API_KEY", "api_key 占位符错误"
        assert config["model"] == "gpt-4o", "模型选择错误"
        print("  ✓ 配置生成通过")
    except Exception as e:
        print(f"  ✗ 配置生成失败: {e}")
        return False

    # 测试8: 代码生成
    try:
        test_config = {"base_url": "https://test.example.com/v1", "api_key": "KEY", "model": "gpt-4o"}
        py_code = generate_python_code(test_config)
        assert "https://test.example.com/v1" in py_code, "Python 代码缺少 base_url"
        assert "KEY" in py_code, "Python 代码缺少 api_key"
        curl_code = generate_curl_code(test_config)
        assert "https://test.example.com/v1" in curl_code, "curl 代码缺少 base_url"
        assert "KEY" in curl_code, "curl 代码缺少 api_key"
        print("  ✓ 代码生成通过")
    except Exception as e:
        print(f"  ✗ 代码生成失败: {e}")
        return False

    # 测试9: 迁移步骤
    try:
        test_provider = {"name": "new", "base_url": "https://new.example.com/v1", "models": ["gpt-4o"]}
        steps = generate_migration_steps("old", test_provider)
        assert len(steps) == 5, f"迁移步骤应为 5 步，收到 {len(steps)}"
        assert "new.example.com" in steps[0], "迁移步骤应包含新地址"
        print("  ✓ 迁移步骤生成通过")
    except Exception as e:
        print(f"  ✗ 迁移步骤生成失败: {e}")
        return False

    # 测试10: 输出格式化
    try:
        req = parse_requirements(0.5, 1000, "chat", 1000000)
        candidates = recommend_providers(req)
        output = format_recommendation(req, candidates, verbose=True)
        assert "推荐结果" in output, "输出缺少标题"
        assert "候选方案" in output, "输出缺少候选方案"
        assert "Python" in output, "输出缺少 Python 代码"
        assert "curl" in output, "输出缺少 curl 代码"
        print("  ✓ 输出格式化通过")
    except Exception as e:
        print(f"  ✗ 输出格式化失败: {e}")
        return False

    # 测试11: 空输入边界
    try:
        req = parse_requirements(None, None, None, None)
        assert req["budget"] == 1.0, "空输入预算默认值错误"
        assert req["latency_ms"] == 1000, "空输入延迟默认值错误"
        print("  ✓ 空输入边界通过")
    except Exception as e:
        print(f"  ✗ 空输入边界失败: {e}")
        return False

    # 测试12: 超长输入（不崩溃即可）
    try:
        req = parse_requirements(999999999, 999999999, "chat", 999999999)
        assert req["budget"] == 999999999, "超长预算解析错误"
        assert req["latency_ms"] == 999999999, "超长延迟解析错误"
        print("  ✓ 超长输入边界通过")
    except Exception as e:
        print(f"  ✗ 超长输入边界失败: {e}")
        return False

    print("\n全部自检通过 ✓")
    return True


# ============================================================
# 主入口
# ============================================================
def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="AI API 中转服务配置助手",
        epilog="示例: python main.py --budget 0.5 --latency 500 --model-type chat --monthly-tokens 1000000",
    )

    # 输入参数
    parser.add_argument("--budget", type=float, help="预算上限（美元/百万 tokens）")
    parser.add_argument("--latency", type=int, help="延迟阈值（毫秒）")
    parser.add_argument("--model-type", choices=["chat", "embedding", "image"], help="模型类型")
    parser.add_argument("--monthly-tokens", type=int, help="月度调用量（tokens）")

    # 行为参数
    parser.add_argument("--verbose", action="store_true", help="输出详细决策信息")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不执行（本脚本无写盘操作，保留兼容）")
    parser.add_argument("--force", action="store_true", help="强制执行（本脚本无写盘操作，保留兼容）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")

    # 解析参数
    args = parser.parse_args(argv)

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 正常模式
    try:
        # 解析需求
        requirements = parse_requirements(
            args.budget,
            args.latency,
            args.model_type,
            args.monthly_tokens,
        )

        # 推荐服务
        candidates = recommend_providers(requirements)

        # 格式化输出
        output = format_recommendation(requirements, candidates, verbose=args.verbose)

        # 输出结果
        print(output)

        return 0

    except AppError as e:
        # 业务逻辑错误（警告级别）
        print(f"错误: {e.message}", file=sys.stderr)
        print(f"错误码: {e.code}", file=sys.stderr)
        print("请检查输入参数后重试。", file=sys.stderr)
        return 1

    except Exception as e:
        # 系统级异常（耻辱级别）
        print(f"系统异常: {e}", file=sys.stderr)
        print("错误码: E010", file=sys.stderr)
        print("请报告此问题，并附上完整错误信息。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
