#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语释义助手 (dictionary-term-explain)
按场景拆解术语含义，给出边界清晰、可落地的概念解释。
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码
ERR_INPUT_EMPTY = "E1001"       # 输入为空
ERR_INPUT_TOO_LONG = "E1002"    # 输入超长
ERR_BATCH_FILE = "E1003"        # 批量文件不存在或格式错误
ERR_KB_MISS_EXTERNAL_FAIL = "E1004"  # 知识库未命中且外部API失败
ERR_ENCODING = "E1005"          # 批量文件编码无法识别

# 本地知识库（内置硬编码）
# 格式: 术语 -> {定义, 场景拆解, 边界, 误用}
TERM_KNOWLEDGE_BASE: Dict[str, Dict[str, str]] = {
    "微服务": {
        "定义": "一种将单一应用程序划分为一组小服务的架构风格，每个服务独立部署、独立扩展。",
        "场景拆解": {
            "技术": "微服务将单体应用拆分为多个独立部署的小服务，每个服务可独立开发、测试、部署和扩展，服务间通过轻量级通信机制（如HTTP/REST）交互。",
            "业务": "业务团队可以独立负责某个微服务，加快交付速度，降低跨团队协调成本。",
            "日常": "可以理解为将一个大型项目拆分成多个小项目，每个小项目独立运行、独立维护。",
            "学术": "微服务架构是一种分布式系统架构模式，强调服务的独立性和自治性，是面向服务架构（SOA）的一种演进。"
        },
        "边界": "微服务与单体架构相对，但并非所有系统都适合微服务；微服务与SOA有相似之处，但微服务更强调服务的独立部署和去中心化治理。",
        "误用": "常见误用包括将微服务与SOA混为一谈，或认为微服务是解决所有架构问题的银弹。"
    },
    "容器化": {
        "定义": "将应用程序及其依赖打包到一个可移植的容器中，实现环境一致性和快速部署。",
        "场景拆解": {
            "技术": "容器化通过操作系统级虚拟化，将应用及其依赖打包成镜像，实现一次构建、到处运行。",
            "业务": "容器化可以显著提升应用交付效率，减少环境不一致导致的问题。",
            "日常": "可以理解为将应用连同其运行环境一起打包，像集装箱一样标准化运输和部署。",
            "学术": "容器化是一种轻量级虚拟化技术，通过命名空间和控制组实现资源隔离和限制。"
        },
        "边界": "容器化与虚拟机不同，容器共享宿主机内核，资源占用更小；容器化与微服务相关但不同，容器化是部署方式，微服务是架构模式。",
        "误用": "常见误用包括将容器化等同于虚拟化，或认为容器化只适用于微服务架构。"
    },
    "API网关": {
        "定义": "位于客户端和后端服务之间的中间层，负责请求路由、协议转换、认证授权、限流等。",
        "场景拆解": {
            "技术": "API网关作为系统的统一入口，将客户端的请求转发到相应的后端服务，并处理跨横切关注点。",
            "业务": "API网关可以统一管理对外接口，提供安全、监控、计费等能力。",
            "日常": "可以理解为大楼的前台，所有访客都通过前台找到对应的人。",
            "学术": "API网关是一种架构模式，是分布式系统中的一个核心组件，用于管理和控制API流量。"
        },
        "边界": "API网关与负载均衡器不同，负载均衡器主要做流量分发，API网关还包含协议转换、认证等功能；API网关与BFF（Backend for Frontend）不同，BFF更专注于为特定前端提供聚合接口。",
        "误用": "常见误用包括将API网关等同于负载均衡器，或认为API网关是必须的组件。"
    },
    "区块链": {
        "定义": "一种去中心化的分布式账本技术，通过密码学保证数据不可篡改和可追溯。",
        "场景拆解": {
            "技术": "区块链通过区块链接的方式存储数据，每个区块包含前一个区块的哈希，形成链式结构，任何篡改都会被检测到。",
            "业务": "区块链可以用于供应链溯源、数字资产、跨境支付等场景，提高透明度和信任度。",
            "日常": "可以理解为一种公开的、不可篡改的账本，每个人都可以查看但没有人能单独修改。",
            "学术": "区块链是一种分布式数据库技术，结合了密码学、共识算法、P2P网络等技术，实现去中心化的信任机制。"
        },
        "边界": "区块链与分布式数据库不同，区块链强调去中心化和不可篡改，分布式数据库通常由中心化机构管理；区块链与比特币不同，比特币是区块链的一种应用。",
        "误用": "常见误用包括将区块链等同于比特币，或认为所有数据都适合上链。"
    },
    "DevOps": {
        "定义": "一种文化和实践，旨在促进开发（Development）和运维（Operations）团队之间的协作，实现持续交付。",
        "场景拆解": {
            "技术": "DevOps通过自动化工具链（CI/CD、配置管理、监控等）实现软件交付的自动化和持续化。",
            "业务": "DevOps可以缩短交付周期，提高部署频率，快速响应市场需求。",
            "日常": "可以理解为开发人员和运维人员不再各自为政，而是紧密合作，共同负责软件的整个生命周期。",
            "学术": "DevOps是一种软件工程文化和实践，强调自动化、协作、度量和共享。"
        },
        "边界": "DevOps与敏捷开发不同，敏捷关注需求开发和迭代，DevOps关注交付和运维；DevOps与SRE（站点可靠性工程）不同，SRE更关注系统的可靠性。",
        "误用": "常见误用包括将DevOps等同于CI/CD工具，或认为DevOps只是运维团队的事情。"
    }
}


# ============================================================
# 核心功能类
# ============================================================

class TermExplainer:
    """术语解释器，负责查询、解释和格式化输出。"""

    def __init__(self, knowledge_base: Dict[str, Dict[str, str]] = None):
        """初始化解释器，设置知识库和缓存。"""
        self.knowledge_base = knowledge_base or TERM_KNOWLEDGE_BASE
        # 使用 OrderedDict 模拟 LRU 缓存
        self.cache: "OrderedDict[str, Dict[str, str]]" = OrderedDict()
        self.cache_limit = 100

    def validate_input(self, term: str) -> Tuple[bool, str, Optional[str]]:
        """
        校验输入合法性。
        返回: (是否合法, 规范化后的术语, 错误码或None)
        """
        if not term or not term.strip():
            return False, "", ERR_INPUT_EMPTY

        normalized = term.strip().lower()
        if len(normalized) > 100:
            # 超长截断并警告
            return True, normalized[:100], ERR_INPUT_TOO_LONG

        return True, normalized, None

    def query_knowledge_base(self, term: str) -> Optional[Dict[str, str]]:
        """查询本地知识库，命中则返回解释，否则返回None。"""
        # 先查缓存
        if term in self.cache:
            # 更新缓存顺序（LRU）
            self.cache.move_to_end(term)
            return self.cache[term]

        # 查知识库
        result = self.knowledge_base.get(term)
        if result:
            # 更新缓存
            self.cache[term] = result
            self.cache.move_to_end(term)
            if len(self.cache) > self.cache_limit:
                self.cache.popitem(last=False)

        return result

    def query_external_api(self, term: str) -> Optional[Dict[str, str]]:
        """
        查询外部API（维基百科）作为兜底。
        此函数在离线/无网环境下会返回None。
        """
        try:
            # 使用维基百科 API（仅作示例，实际可能不可用）
            url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{term}"
            req = urllib.request.Request(url, headers={"User-Agent": "TermExplainer/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "extract" in data:
                    return {
                        "定义": data["extract"],
                        "场景拆解": {
                            "通用": data["extract"]
                        },
                        "边界": "外部来源，未做本地边界界定。",
                        "误用": "外部来源，未做本地误用分析。",
                        "来源": "维基百科"
                    }
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, TimeoutError):
            pass

        return None

    def explain(self, term: str, scene: Optional[str] = None) -> Dict[str, object]:
        """
        解释术语的主流程。
        返回包含解释结果和错误信息的字典。
        """
        # 1. 校验输入
        valid, normalized, err_code = self.validate_input(term)
        if not valid:
            return {"success": False, "error": err_code, "message": "请输入要解释的术语"}

        # 2. 查询知识库
        result = self.query_knowledge_base(normalized)
        source = "本地知识库"

        # 3. 知识库未命中，尝试外部API
        if not result:
            result = self.query_external_api(normalized)
            if result:
                source = "外部API"
            else:
                return {
                    "success": False,
                    "error": ERR_KB_MISS_EXTERNAL_FAIL,
                    "message": "未找到该术语的解释",
                    "term": normalized
                }

        # 4. 根据场景过滤输出
        scene_breakdown = result.get("场景拆解", {})
        if scene:
            # 指定场景时，只输出该场景的解释
            if scene in scene_breakdown:
                filtered_breakdown = {scene: scene_breakdown[scene]}
            else:
                # 场景不存在时，输出全部
                filtered_breakdown = scene_breakdown
        else:
            filtered_breakdown = scene_breakdown

        # 5. 组装输出
        output = {
            "success": True,
            "term": normalized,
            "definition": result.get("定义", ""),
            "scene_breakdown": filtered_breakdown,
            "boundary": result.get("边界", ""),
            "misuse": result.get("误用", ""),
            "source": source
        }

        # 如果输入超长，附加警告
        if err_code == ERR_INPUT_TOO_LONG:
            output["warning"] = "输入超过100字符，已截断处理"

        return output

    def format_markdown(self, result: Dict[str, object]) -> str:
        """将解释结果格式化为 Markdown 文本。"""
        if not result.get("success"):
            return f"**错误**: {result.get('message', '未知错误')}"

        lines = []
        lines.append(f"## {result['term']}")
        lines.append("")
        lines.append(f"**来源**: {result.get('source', '未知')}")
        lines.append("")
        lines.append("### 核心定义")
        lines.append("")
        lines.append(result["definition"])
        lines.append("")
        lines.append("### 场景拆解")
        lines.append("")
        lines.append("| 场景 | 解释 |")
        lines.append("|------|------|")
        for scene, desc in result["scene_breakdown"].items():
            # 处理描述中的换行符
            desc_clean = desc.replace("\n", " ").replace("|", "\\|")
            lines.append(f"| {scene} | {desc_clean} |")
        lines.append("")
        lines.append("### 边界界定")
        lines.append("")
        lines.append(result["boundary"])
        lines.append("")
        lines.append("### 常见误用")
        lines.append("")
        lines.append(result["misuse"])

        if result.get("warning"):
            lines.append("")
            lines.append(f"> ⚠️ {result['warning']}")

        return "\n".join(lines)

    def batch_explain(self, file_path: str) -> List[Dict[str, object]]:
        """
        批量解释文件中的术语。
        支持 JSON 数组格式和纯文本（每行一个术语）。
        """
        results = []
        try:
            # 读取文件（多编码尝试）
            content = None
            for encoding in ["utf-8", "gbk", "latin-1"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if content is None:
                return [{"success": False, "error": ERR_ENCODING, "message": "文件编码无法识别"}]

            # 解析内容
            terms = []
            stripped = content.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                # JSON 数组
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        terms = [str(t) for t in data]
                except json.JSONDecodeError:
                    return [{"success": False, "error": ERR_BATCH_FILE, "message": "JSON格式错误"}]
            else:
                # 纯文本，每行一个
                terms = [line.strip() for line in content.splitlines() if line.strip()]

            if not terms:
                return [{"success": False, "error": ERR_BATCH_FILE, "message": "文件中没有术语"}]

            # 逐个解释
            for term in terms:
                results.append(self.explain(term))

        except FileNotFoundError:
            return [{"success": False, "error": ERR_BATCH_FILE, "message": f"文件不存在: {file_path}"}]
        except Exception as e:
            return [{"success": False, "error": ERR_BATCH_FILE, "message": f"读取文件失败: {str(e)}"}]

        return results


# ============================================================
# 自测模块
# ============================================================

def run_selftest() -> int:
    """内置自测，使用硬编码样例数据验证核心逻辑。"""
    print("开始自测...")
    explainer = TermExplainer()

    # 测试1: 正常查询
    result = explainer.explain("微服务")
    assert result["success"], f"测试1失败: 正常查询失败 {result}"
    assert "微服务" in result["term"], f"测试1失败: 术语不匹配 {result['term']}"
    assert len(result["definition"]) > 0, "测试1失败: 定义为空"
    assert len(result["scene_breakdown"]) >= 1, "测试1失败: 场景拆解为空"
    print("✅ 测试1通过: 正常查询")

    # 测试2: 空输入
    result = explainer.explain("")
    assert not result["success"], "测试2失败: 空输入应该失败"
    assert result["error"] == ERR_INPUT_EMPTY, f"测试2失败: 错误码不匹配 {result['error']}"
    print("✅ 测试2通过: 空输入处理")

    # 测试3: 超长输入
    long_term = "x" * 150
    result = explainer.explain(long_term)
    assert result["success"], "测试3失败: 超长输入应该成功（截断）"
    assert len(result["term"]) <= 100, f"测试3失败: 截断失败 {len(result['term'])}"
    assert result.get("warning"), "测试3失败: 应该有警告"
    print("✅ 测试3通过: 超长输入截断")

    # 测试4: 未命中术语（外部API失败时）
    result = explainer.explain("完全不存在xyzzy")
    # 可能命中外部API或失败，两种情况都算通过
    if not result["success"]:
        assert result["error"] == ERR_KB_MISS_EXTERNAL_FAIL, f"测试4失败: 错误码不匹配 {result['error']}"
    print("✅ 测试4通过: 未命中术语处理")

    # 测试5: 场景过滤
    result = explainer.explain("容器化", scene="技术")
    assert result["success"], "测试5失败: 场景查询失败"
    assert "技术" in result["scene_breakdown"], "测试5失败: 技术场景不包含"
    assert len(result["scene_breakdown"]) == 1, "测试5失败: 场景过滤不生效"
    print("✅ 测试5通过: 场景过滤")

    # 测试6: 批量处理（JSON格式）
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(["微服务", "区块链"], f)
        tmp_path = f.name
    try:
        results = explainer.batch_explain(tmp_path)
        assert len(results) == 2, f"测试6失败: 批量结果数量不对 {len(results)}"
        assert results[0]["success"], "测试6失败: 第一个术语失败"
        assert results[1]["success"], "测试6失败: 第二个术语失败"
        print("✅ 测试6通过: 批量JSON处理")
    finally:
        os.unlink(tmp_path)

    # 测试7: 批量处理（纯文本格式）
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("微服务\n容器化\n")
        tmp_path = f.name
    try:
        results = explainer.batch_explain(tmp_path)
        assert len(results) == 2, f"测试7失败: 批量结果数量不对 {len(results)}"
        assert results[0]["success"], "测试7失败: 第一个术语失败"
        print("✅ 测试7通过: 批量纯文本处理")

        # 测试8: Markdown格式化
        md = explainer.format_markdown(results[0])
        assert "微服务" in md, "测试8失败: Markdown不包含术语"
        assert "核心定义" in md, "测试8失败: Markdown不包含定义"
        assert "场景拆解" in md, "测试8失败: Markdown不包含场景"
        assert "边界界定" in md, "测试8失败: Markdown不包含边界"
        assert "常见误用" in md, "测试8失败: Markdown不包含误用"
        print("✅ 测试8通过: Markdown格式化")
    finally:
        os.unlink(tmp_path)

    # 测试9: 批量文件不存在
    results = explainer.batch_explain("/nonexistent/path/terms.json")
    assert len(results) == 1, "测试9失败: 应返回一个错误结果"
    assert not results[0]["success"], "测试9失败: 应该失败"
    assert results[0]["error"] == ERR_BATCH_FILE, "测试9失败: 错误码不匹配"
    print("✅ 测试9通过: 批量文件不存在")

    # 测试10: 缓存功能
    explainer.explain("DevOps")
    assert "devops" in explainer.cache, "测试10失败: 缓存未命中"
    explainer.explain("DevOps")  # 再次查询
    print("✅ 测试10通过: 缓存功能")

    # 测试11: 中文术语查询
    result = explainer.explain("API网关")
    assert result["success"], "测试11失败: 中文术语查询失败"
    assert "API网关" in result["term"], "测试11失败: 术语不匹配"
    print("✅ 测试11通过: 中文术语查询")

    # 测试12: 不存在的场景
    result = explainer.explain("微服务", scene="不存在的场景")
    assert result["success"], "测试12失败: 不存在的场景应该返回全部"
    assert len(result["scene_breakdown"]) >= 1, "测试12失败: 场景拆解为空"
    print("✅ 测试12通过: 不存在的场景处理")

    print("\n🎉 所有自测通过！")
    return 0


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主函数，解析命令行参数并执行相应操作。"""
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 按场景拆解术语含义",
        epilog="示例: python main.py 微服务 --scene 技术"
    )
    parser.add_argument("term", nargs="?", help="要解释的术语")
    parser.add_argument("--scene", "-s", help="指定场景（技术/业务/日常/学术）")
    parser.add_argument("--batch", "-b", metavar="FILE", help="批量解释文件中的术语（JSON数组或纯文本）")
    parser.add_argument("--selftest", action="store_true", help="运行内置自测")

    args = parser.parse_args()

    # 自测模式
    if args.selftest:
        return run_selftest()

    # 创建解释器
    explainer = TermExplainer()

    # 批量模式
    if args.batch:
        results = explainer.batch_explain(args.batch)
        for i, result in enumerate(results, 1):
            print(f"\n--- 结果 {i} ---")
            print(explainer.format_markdown(result))
        return 0

    # 单术语模式
    if not args.term:
        parser.print_help()
        return 1

    result = explainer.explain(args.term, args.scene)
    print(explainer.format_markdown(result))

    # 如果有错误，返回非零退出码
    if not result.get("success"):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
