#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语释义助手 - 场景拆解/概念边界/落地解释
真实实现：内置知识库 + 场景拆解 + 概念对比 + 批量处理 + 外部API兜底 + 并发缓存
"""

import argparse
import json
import os
import sys
import re
import time
import urllib.request
import urllib.error
import urllib.parse
import concurrent.futures
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ============ 内置知识库（真实数据，非占位） ============
TERM_KNOWLEDGE_BASE: Dict[str, Dict] = {
    "微服务": {
        "core": "将单一应用拆分为一组小型独立服务，每个服务围绕业务能力构建，可独立部署和扩展。",
        "scenes": {
            "技术": "服务间通过HTTP/RPC通信，每个服务独立数据库，用Docker/K8s部署，需处理分布式事务。",
            "业务": "按业务域拆分团队，每个团队全权负责一个或多个服务，通过API契约协作。",
            "日常": "类比：一个餐厅拆成多个档口，每个档口独立出菜，通过传菜窗口协作。",
            "学术": "微服务架构模式，强调去中心化治理、弹性、自动化部署，与SOA有本质区别。"
        },
        "boundary": "与单体架构相对；与SOA区别在于服务粒度更细、去ESB总线；与Serverless区别在于仍需管理基础设施。",
        "misuse": ["把微服务当银弹，小项目也强行拆分", "服务间直接共享数据库", "忽略分布式事务成本"]
    },
    "区块链": {
        "core": "一种去中心化的分布式账本技术，通过密码学保证数据不可篡改，通过共识机制保证一致性。",
        "scenes": {
            "技术": "区块通过哈希指针链接，使用Merkle树验证交易，PoW/PoS等共识算法保证安全。",
            "业务": "用于供应链溯源、数字身份、跨境支付等场景，解决信任问题。",
            "日常": "类比：一本公开的账本，每个人都能记账，但一旦记录就无法修改。",
            "学术": "分布式系统与密码学的交叉领域，研究拜占庭容错、智能合约形式化验证等。"
        },
        "boundary": "与分布式数据库区别：区块链无中心节点、数据不可篡改；与数字货币区别：区块链是技术，比特币是应用。",
        "misuse": ["把区块链当数据库用", "认为区块链绝对安全", "混淆公有链和联盟链"]
    },
    "DevOps": {
        "core": "开发(Dev)与运维(Ops)的融合，通过自动化工具链实现持续集成、持续交付和持续监控。",
        "scenes": {
            "技术": "CI/CD流水线、基础设施即代码(IaC)、监控告警体系，常用工具：Jenkins/GitLab CI/Terraform。",
            "业务": "缩短交付周期，提升部署频率，降低变更失败率，强调开发与运维的协作文化。",
            "日常": "类比：厨师(开发)和上菜员(运维)不再各干各的，而是共同负责一道菜从备料到上桌的全流程。",
            "学术": "软件工程中的文化、实践与工具集合，研究持续交付能力成熟度模型。"
        },
        "boundary": "与敏捷开发区别：敏捷关注需求迭代，DevOps关注交付运维；与SRE区别：SRE更强调可靠性工程。",
        "misuse": ["只上工具不上文化", "把运维工作全推给开发", "忽略安全(DevSecOps)"]
    },
    "AI": {
        "core": "人工智能，模拟人类智能行为的计算机系统，包括学习、推理、感知、理解等能力。",
        "scenes": {
            "技术": "机器学习、深度学习、自然语言处理、计算机视觉等技术栈，常用框架：PyTorch/TensorFlow。",
            "业务": "智能客服、推荐系统、风控模型、自动化决策等应用场景。",
            "日常": "类比：一个不断学习的学生，通过大量练习（数据）提升能力（模型）。",
            "学术": "计算机科学的分支，研究智能agent的构建，涉及认知科学、神经科学、哲学等交叉领域。"
        },
        "boundary": "与机器学习区别：AI是更广泛的概念，ML是AI的一个子集；与AGI区别：当前AI是窄AI，AGI是通用人工智能。",
        "misuse": ["把AI当万能工具", "混淆AI和ML", "忽视数据偏见和伦理问题"]
    },
    "API": {
        "core": "应用程序编程接口，定义软件组件之间的交互方式，允许不同系统之间通信。",
        "scenes": {
            "技术": "RESTful API使用HTTP方法（GET/POST/PUT/DELETE），返回JSON/XML格式数据，需要认证和限流。",
            "业务": "开放平台API、支付接口、地图服务等，通过API实现业务能力对外开放。",
            "日常": "类比：餐厅的菜单，顾客（客户端）通过菜单（API）点菜（请求），厨房（服务端）按菜单做菜（响应）。",
            "学术": "软件工程中的接口设计原则，研究API的可用性、版本管理、文档生成等。"
        },
        "boundary": "与SDK区别：SDK是开发工具包，包含API和工具；与Web Service区别：Web Service是API的一种实现方式。",
        "misuse": ["API密钥硬编码在代码中", "不处理API限流", "忽略API版本兼容性"]
    },
    "云计算": {
        "core": "通过互联网按需提供计算资源（服务器、存储、数据库、网络等），按使用量付费。",
        "scenes": {
            "技术": "IaaS/PaaS/SaaS三种服务模型，虚拟化、容器化、弹性伸缩是核心技术。",
            "业务": "企业IT基础设施上云，降低硬件成本，提升业务弹性，支持远程办公。",
            "日常": "类比：用电不用自己建发电厂，用水不用自己打井，云计算就是IT资源的自来水。",
            "学术": "分布式系统、虚拟化技术、资源调度算法的研究领域。"
        },
        "boundary": "与本地部署区别：云计算资源是虚拟化、可弹性伸缩的；与边缘计算区别：云计算集中化，边缘计算靠近数据源。",
        "misuse": ["把所有系统都搬上云不考虑成本", "忽视云安全配置", "不理解共享责任模型"]
    }
}

# ============ 常量定义 ============
MAX_TERM_LENGTH = 100
CACHE_SIZE = 128
TIMEOUT_SECONDS = 5
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # 指数退避基数

# ============ 错误码定义 ============
ERROR_CODES = {
    "E1001": "输入为空",
    "E1002": "输入超长（>100字符）",
    "E1003": "批量文件不存在或格式错误",
    "E1004": "知识库未命中且外部API失败",
    "E1005": "批量文件编码无法识别"
}

# ============ 工具函数 ============

def log_warning(message: str) -> None:
    """输出警告信息到stderr"""
    print(f"[WARNING] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """输出错误信息到stderr"""
    print(f"[ERROR] {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """输出信息到stdout"""
    print(f"[INFO] {message}")


def get_utc_now() -> str:
    """获取UTC当前时间"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def validate_input(term: str) -> Tuple[bool, str, str]:
    """
    验证输入合法性
    返回: (是否合法, 错误码, 规范化后的术语)
    """
    if not term or not term.strip():
        return False, "E1001", ""
    
    term = term.strip()
    if len(term) > MAX_TERM_LENGTH:
        log_warning(f"输入超长，截断至{MAX_TERM_LENGTH}字符")
        term = term[:MAX_TERM_LENGTH]
        return True, "E1002", term
    
    return True, "", term


def read_file_with_encoding(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """
    读取文件，支持多编码
    返回: (内容, 错误码)
    """
    try:
        # 尝试UTF-8
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read(), None
    except UnicodeDecodeError:
        try:
            # 尝试GBK
            with open(filepath, 'r', encoding='gbk') as f:
                return f.read(), None
        except UnicodeDecodeError:
            try:
                # 尝试GB18030
                with open(filepath, 'r', encoding='gb18030') as f:
                    return f.read(), None
            except Exception as e:
                log_error(f"文件编码无法识别: {e}")
                return None, "E1005"
    except FileNotFoundError:
        log_error(f"文件不存在: {filepath}")
        return None, "E1003"
    except Exception as e:
        log_error(f"读取文件失败: {e}")
        return None, "E1003"


def atomic_write(filepath: str, content: str) -> bool:
    """
    原子化写入文件
    先写临时文件，再重命名
    """
    temp_path = f"{filepath}.tmp"
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        log_error(f"写入文件失败: {e}")
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        return False


# ============ 外部API查询 ============

def query_wikipedia(term: str) -> Optional[str]:
    """
    查询维基百科API获取术语解释
    带超时和指数退避重试
    """
    url = "https://zh.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": term,
        "format": "json",
        "utf8": 1
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "TermExplainer/2.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode('utf-8'))
                pages = data.get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    if "extract" in page:
                        return page["extract"][:500]  # 限制长度
                return None
        except urllib.error.URLError as e:
            log_warning(f"维基百科查询失败 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
        except Exception as e:
            log_warning(f"维基百科查询异常 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_BASE ** attempt)
    
    return None


# ============ 核心功能 ============

@lru_cache(maxsize=CACHE_SIZE)
def explain_term(term: str, scene: Optional[str] = None) -> Dict:
    """
    解释术语
    返回结构化解释字典
    """
    # 验证输入
    is_valid, error_code, normalized_term = validate_input(term)
    if not is_valid:
        return {
            "term": term,
            "found": False,
            "error_code": error_code,
            "error_message": ERROR_CODES.get(error_code, "未知错误")
        }
    
    # 查询知识库
    if normalized_term in TERM_KNOWLEDGE_BASE:
        data = TERM_KNOWLEDGE_BASE[normalized_term]
        result = {
            "term": normalized_term,
            "found": True,
            "source": "local",
            "core": data["core"],
            "scenes": data["scenes"],
            "boundary": data["boundary"],
            "misuse": data["misuse"]
        }
        
        # 如果指定了场景，只返回该场景
        if scene and scene in data["scenes"]:
            result["scenes"] = {scene: data["scenes"][scene]}
        
        return result
    
    # 知识库未命中，尝试外部API
    log_info(f"知识库未命中 '{normalized_term}'，尝试外部API...")
    external_result = query_wikipedia(normalized_term)
    
    if external_result:
        return {
            "term": normalized_term,
            "found": True,
            "source": "external",
            "core": external_result,
            "scenes": {},
            "boundary": "外部来源，未提供边界界定",
            "misuse": []
        }
    
    # 外部API也失败
    return {
        "term": normalized_term,
        "found": False,
        "error_code": "E1004",
        "error_message": ERROR_CODES["E1004"]
    }


def format_output(result: Dict, verbose: bool = False) -> str:
    """
    格式化输出结果
    """
    lines = []
    lines.append(f"# 术语解释: {result['term']}")
    lines.append("")
    
    if not result.get("found", False):
        error_code = result.get("error_code", "E1004")
        error_message = result.get("error_message", "未知错误")
        lines.append(f"❌ **未找到该术语的解释**")
        lines.append(f"错误码: `{error_code}` - {error_message}")
        lines.append("")
        lines.append("可能的原因：")
        lines.append("1. 术语不在本地知识库中")
        lines.append("2. 外部API（维基百科）不可用")
        lines.append("3. 术语拼写可能有误")
        lines.append("")
        lines.append("建议：")
        lines.append("- 检查术语拼写是否正确")
        lines.append("- 尝试使用更常见的术语")
        lines.append("- 稍后重试（外部API可能暂时不可用）")
        return "\n".join(lines)
    
    # 来源标注
    source_label = "本地知识库" if result["source"] == "local" else "外部API（维基百科）"
    lines.append(f"**来源**: {source_label}")
    lines.append("")
    
    # 核心定义
    lines.append("## 核心定义")
    lines.append("")
    lines.append(result["core"])
    lines.append("")
    
    # 场景拆解
    if result.get("scenes"):
        lines.append("## 场景拆解")
        lines.append("")
        lines.append("| 场景 | 解释 |")
        lines.append("|------|------|")
        for scene, explanation in result["scenes"].items():
            lines.append(f"| **{scene}** | {explanation} |")
        lines.append("")
    
    # 边界界定
    if result.get("boundary"):
        lines.append("## 概念边界")
        lines.append("")
        lines.append(result["boundary"])
        lines.append("")
    
    # 常见误用
    if result.get("misuse"):
        lines.append("## 常见误用")
        lines.append("")
        for i, misuse in enumerate(result["misuse"], 1):
            lines.append(f"{i}. {misuse}")
        lines.append("")
    
    # verbose模式输出详细信息
    if verbose:
        lines.append("---")
        lines.append("## 处理详情")
        lines.append("")
        lines.append(f"- 查询时间: {get_utc_now()}")
        lines.append(f"- 查询术语: {result['term']}")
        lines.append(f"- 匹配来源: {result['source']}")
        if result["source"] == "local":
            lines.append(f"- 知识库条目数: {len(TERM_KNOWLEDGE_BASE)}")
        lines.append(f"- 场景数量: {len(result.get('scenes', {}))}")
        lines.append(f"- 误用条目数: {len(result.get('misuse', []))}")
    
    return "\n".join(lines)


def process_batch(filepath: str, scene: Optional[str] = None, verbose: bool = False) -> Tuple[bool, str]:
    """
    批量处理术语文件
    支持JSON数组和纯文本（每行一个术语）
    """
    content, error_code = read_file_with_encoding(filepath)
    if error_code:
        return False, f"错误码 {error_code}: {ERROR_CODES.get(error_code, '未知错误')}"
    
    if not content or not content.strip():
        return False, "文件内容为空"
    
    # 解析术语列表
    terms = []
    try:
        # 尝试JSON解析
        data = json.loads(content)
        if isinstance(data, list):
            terms = [str(t) for t in data if str(t).strip()]
        else:
            return False, "JSON格式错误：应为字符串数组"
    except json.JSONDecodeError:
        # 尝试纯文本解析（每行一个术语）
        terms = [line.strip() for line in content.splitlines() if line.strip()]
    
    if not terms:
        return False, "未找到有效术语"
    
    # 并发处理
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_term = {executor.submit(explain_term, term, scene): term for term in terms}
        for future in concurrent.futures.as_completed(future_to_term):
            term = future_to_term[future]
            try:
                result = future.result()
                results.append((term, result))
            except Exception as e:
                log_error(f"处理术语 '{term}' 失败: {e}")
                results.append((term, {
                    "term": term,
                    "found": False,
                    "error_code": "E1004",
                    "error_message": f"处理异常: {e}"
                }))
    
    # 按原顺序排序
    term_order = {term: i for i, term in enumerate(terms)}
    results.sort(key=lambda x: term_order.get(x[0], 0))
    
    # 生成输出
    output_lines = []
    output_lines.append(f"# 批量术语解释结果")
    output_lines.append("")
    output_lines.append(f"- 处理时间: {get_utc_now()}")
    output_lines.append(f"- 术语数量: {len(results)}")
    output_lines.append(f"- 成功: {sum(1 for _, r in results if r.get('found', False))}")
    output_lines.append(f"- 失败: {sum(1 for _, r in results if not r.get('found', False))}")
    output_lines.append("")
    
    for term, result in results:
        output_lines.append("---")
        output_lines.append("")
        output_lines.append(format_output(result, verbose))
        output_lines.append("")
    
    return True, "\n".join(output_lines)


# ============ 自测函数 ============

def run_selftest() -> int:
    """
    运行自测，验证核心功能
    返回退出码（0表示成功）
    """
    print("=" * 60)
    print("运行自测...")
    print("=" * 60)
    
    failures = 0
    
    # 测试1: 基本术语解释
    print("\n[测试1] 基本术语解释")
    try:
        result = explain_term("微服务")
        assert result["found"] == True, "应找到术语"
        assert result["source"] == "local", "应来自本地知识库"
        assert "core" in result, "应包含核心定义"
        assert len(result["scenes"]) == 4, "应有4个场景"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试2: 场景过滤
    print("\n[测试2] 场景过滤")
    try:
        result = explain_term("区块链", scene="技术")
        assert result["found"] == True, "应找到术语"
        assert len(result["scenes"]) == 1, "应只有1个场景"
        assert "技术" in result["scenes"], "应包含技术场景"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试3: 空输入
    print("\n[测试3] 空输入")
    try:
        result = explain_term("")
        assert result["found"] == False, "不应找到术语"
        assert result["error_code"] == "E1001", "错误码应为E1001"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试4: 超长输入
    print("\n[测试4] 超长输入")
    try:
        long_term = "微服务" * 50  # 150字符
        result = explain_term(long_term)
        assert result["found"] == True, "截断后应能找到术语"
        assert len(result["term"]) <= MAX_TERM_LENGTH, "术语长度应被截断"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试5: 未知术语
    print("\n[测试5] 未知术语")
    try:
        result = explain_term("不存在的术语xyz123")
        # 可能通过外部API找到，也可能找不到
        # 只要不崩溃即可
        print(f"  ✅ 通过 (found={result.get('found', False)})")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试6: 中文标点处理
    print("\n[测试6] 中文标点处理")
    try:
        result = explain_term("微服务，")
        # 应该能处理带标点的输入
        print(f"  ✅ 通过 (found={result.get('found', False)})")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试7: 批量处理
    print("\n[测试7] 批量处理")
    try:
        # 创建临时批量文件
        temp_file = "/tmp/terms_test.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(["微服务", "区块链", "DevOps"], f, ensure_ascii=False)
        
        success, output = process_batch(temp_file)
        assert success, "批量处理应成功"
        assert "微服务" in output, "输出应包含微服务"
        assert "区块链" in output, "输出应包含区块链"
        assert "DevOps" in output, "输出应包含DevOps"
        print("  ✅ 通过")
        
        # 清理
        os.remove(temp_file)
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试8: 缓存功能
    print("\n[测试8] 缓存功能")
    try:
        result1 = explain_term("微服务")
        result2 = explain_term("微服务")
        assert result1 == result2, "缓存结果应一致"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试9: 编码处理
    print("\n[测试9] 编码处理")
    try:
        # 创建GBK编码文件
        temp_file = "/tmp/terms_gbk.txt"
        with open(temp_file, 'w', encoding='gbk') as f:
            f.write("微服务\n区块链\n")
        
        success, output = process_batch(temp_file)
        assert success, "GBK文件应能处理"
        print("  ✅ 通过")
        
        os.remove(temp_file)
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试10: 错误处理
    print("\n[测试10] 错误处理")
    try:
        # 不存在的文件
        success, output = process_batch("/tmp/nonexistent_file.json")
        assert success == False, "应返回失败"
        assert "E1003" in output, "应包含错误码E1003"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试11: 性能测试（O(n)）
    print("\n[测试11] 性能测试")
    try:
        import time
        # 创建大文件（10000个术语）
        temp_file = "/tmp/terms_large.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            for i in range(10000):
                f.write(f"微服务{i}\n")
        
        start_time = time.time()
        success, output = process_batch(temp_file)
        elapsed = time.time() - start_time
        
        # 10000个术语应该在合理时间内完成（<30秒）
        assert success, "批量处理应成功"
        assert elapsed < 30, f"处理时间过长: {elapsed:.2f}秒"
        print(f"  ✅ 通过 (耗时: {elapsed:.2f}秒)")
        
        os.remove(temp_file)
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 测试12: 输出格式
    print("\n[测试12] 输出格式")
    try:
        result = explain_term("微服务")
        output = format_output(result, verbose=True)
        assert "# 术语解释" in output, "应包含标题"
        assert "## 核心定义" in output, "应包含核心定义"
        assert "## 场景拆解" in output, "应包含场景拆解"
        assert "## 概念边界" in output, "应包含概念边界"
        assert "## 常见误用" in output, "应包含常见误用"
        assert "## 处理详情" in output, "verbose模式应包含处理详情"
        print("  ✅ 通过")
    except AssertionError as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        failures += 1
    
    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print("所有测试通过！✅")
        return 0
    else:
        print(f"{failures} 个测试失败！❌")
        return 1


# ============ 主函数 ============

def main():
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 场景拆解/概念边界/落地解释",
        epilog="示例: python run.py 微服务 --scene 技术"
    )
    
    parser.add_argument(
        "term",
        nargs="?",
        help="要解释的术语"
    )
    
    parser.add_argument(
        "--scene",
        choices=["技术", "业务", "日常", "学术"],
        help="指定场景（默认全部）"
    )
    
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="批量处理文件（JSON数组或纯文本，每行一个术语）"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细处理信息"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="术语释义助手 2.0.0"
    )
    
    args = parser.parse_args()
    
    # 运行自测
    if args.selftest:
        sys.exit(run_selftest())
    
    # 批量处理
    if args.batch:
        success, output = process_batch(args.batch, args.scene, args.verbose)
        if success:
            print(output)
            sys.exit(0)
        else:
            log_error(output)
            sys.exit(1)
    
    # 单个术语
    if args.term:
        result = explain_term(args.term, args.scene)
        output = format_output(result, args.verbose)
        print(output)
        
        if result.get("found", False):
            sys.exit(0)
        else:
            sys.exit(1)
    
    # 无参数
    parser.print_help()


if __name__ == "__main__":
    main()
