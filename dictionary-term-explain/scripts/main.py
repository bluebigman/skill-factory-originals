#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
术语释义助手 - 独立实现脚本
根据功能规格 clean-room 重写，不参考任何既有代码。
"""

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """错误码常量"""
    E1001 = "E1001"  # 输入为空
    E1002 = "E1002"  # 输入超长
    E1003 = "E1003"  # 批量文件不存在或格式错误
    E1004 = "E1004"  # 知识库未命中且外部API失败
    E1005 = "E1005"  # 批量文件编码无法识别


# ============================================================
# 内置知识库（硬编码样例数据）
# ============================================================
TERM_KNOWLEDGE_BASE: Dict[str, Dict] = {
    "微服务": {
        "core": "将单一应用拆分为一组小服务，每个服务独立部署、独立扩展，通过轻量级通信机制协作。",
        "scenes": {
            "技术": "在技术场景中，微服务强调服务的独立部署、独立数据库、独立团队负责，通常配合容器化技术。",
            "业务": "在业务场景中，微服务将业务能力模块化，使不同业务线可以独立迭代和扩展。",
            "日常": "在日常对话中，微服务常被用来指代'把大系统拆成小系统'的做法。",
            "学术": "在学术上，微服务是一种软件架构风格，强调服务粒度、独立性和去中心化治理。"
        },
        "boundary": "微服务区别于单体架构和SOA。单体架构所有功能在一个进程中；SOA强调服务复用和企业级总线；微服务更强调去中心化和独立部署。",
        "misuse": "常见误用：把任何分布式系统都称为微服务；认为微服务数量越多越好；忽略分布式带来的复杂性。"
    },
    "区块链": {
        "core": "一种去中心化的分布式账本技术，通过密码学将数据区块按时间顺序链接，实现不可篡改的共享记录。",
        "scenes": {
            "技术": "在技术场景中，区块链涉及共识算法、加密哈希、P2P网络等核心技术栈。",
            "业务": "在业务场景中，区块链用于供应链追溯、数字资产确权、多方协作信任等。",
            "日常": "日常对话中，区块链常被简称为'分布式账本'或'去中心化数据库'。",
            "学术": "在学术上，区块链是分布式系统、密码学和博弈论的交叉领域。"
        },
        "boundary": "区块链区别于传统数据库（中心化 vs 去中心化）、区别于比特币（区块链是技术，比特币是应用）。",
        "misuse": "常见误用：把区块链等同于加密货币；认为区块链数据绝对安全；忽略性能和存储成本。"
    },
    "人工智能": {
        "core": "让计算机模拟人类智能行为的技术，包括学习、推理、感知、理解等能力。",
        "scenes": {
            "技术": "在技术场景中，人工智能涵盖机器学习、深度学习、自然语言处理、计算机视觉等子领域。",
            "业务": "在业务场景中，人工智能用于自动化决策、智能客服、预测分析等。",
            "日常": "日常对话中，人工智能通常指'让机器像人一样思考'的技术。",
            "学术": "在学术上，人工智能是计算机科学的分支，研究智能体的设计与实现。"
        },
        "boundary": "人工智能区别于传统编程（规则驱动 vs 数据驱动）、区别于机器学习（AI是宏观概念，ML是实现方法）。",
        "misuse": "常见误用：把机器学习等同于人工智能；认为AI具有真正意识；忽视数据偏见问题。"
    }
}


# ============================================================
# 核心功能类
# ============================================================
class TermExplainer:
    """术语解释器核心逻辑"""

    def __init__(self, knowledge_base: Optional[Dict] = None):
        """初始化解释器
        
        Args:
            knowledge_base: 知识库字典，默认为内置知识库
        """
        self.knowledge_base = knowledge_base or TERM_KNOWLEDGE_BASE
        self.cache: Dict[str, Dict] = {}  # 内存缓存
        self.cache_limit = 100  # 缓存上限

    def validate_input(self, term: str) -> Tuple[bool, str, Optional[str]]:
        """校验输入合法性
        
        Args:
            term: 用户输入的术语
            
        Returns:
            (是否合法, 规范化后的术语, 错误码或None)
        """
        if term is None or term.strip() == "":
            return False, "", ErrorCode.E1001
        
        # 规范化：去首尾空白
        normalized = term.strip()
        
        # 长度校验
        if len(normalized) > 100:
            # 超长时截断并警告
            normalized = normalized[:100]
            return True, normalized, ErrorCode.E1002
        
        return True, normalized, None

    def query_knowledge_base(self, term: str) -> Optional[Dict]:
        """查询本地知识库
        
        Args:
            term: 规范化后的术语
            
        Returns:
            匹配的解释字典，未命中返回None
        """
        # 先查缓存
        if term in self.cache:
            return self.cache[term]
        
        # 精确匹配知识库
        result = self.knowledge_base.get(term)
        if result:
            # 加入缓存
            self._add_to_cache(term, result)
        
        return result

    def _add_to_cache(self, key: str, value: Dict) -> None:
        """添加缓存项（LRU简化版）"""
        if len(self.cache) >= self.cache_limit:
            # 简单清空（简化LRU）
            self.cache.clear()
        self.cache[key] = value

    def external_query(self, term: str) -> Optional[Dict]:
        """模拟外部API查询（无网络时降级）
        
        Args:
            term: 术语
            
        Returns:
            查询结果或None
        """
        # 本实现不进行真实网络请求，直接返回None
        # 实际实现可在此调用维基百科等外部API
        return None

    def explain(self, term: str, scene: Optional[str] = None) -> Dict:
        """解释术语主流程
        
        Args:
            term: 输入术语
            scene: 指定场景（可选）
            
        Returns:
            包含结果和错误码的字典
        """
        # 1. 输入校验
        is_valid, normalized, error_code = self.validate_input(term)
        if not is_valid:
            return {
                "success": False,
                "error_code": error_code,
                "message": "请输入要解释的术语" if error_code == ErrorCode.E1001 else "输入格式错误",
                "data": None
            }
        
        # 2. 查询知识库
        result = self.query_knowledge_base(normalized)
        if result:
            return {
                "success": True,
                "error_code": None,
                "message": "本地知识库命中",
                "data": self._format_result(normalized, result, scene)
            }
        
        # 3. 尝试外部API
        external_result = self.external_query(normalized)
        if external_result:
            return {
                "success": True,
                "error_code": None,
                "message": "外部来源",
                "data": self._format_result(normalized, external_result, scene)
            }
        
        # 4. 全部失败
        return {
            "success": False,
            "error_code": ErrorCode.E1004,
            "message": "未找到该术语的解释",
            "data": None
        }

    def _format_result(self, term: str, data: Dict, scene: Optional[str]) -> Dict:
        """格式化输出结果
        
        Args:
            term: 术语
            data: 知识库数据
            scene: 指定场景
            
        Returns:
            格式化后的结果字典
        """
        formatted = {
            "term": term,
            "core": data.get("core", ""),
            "scenes": {},
            "boundary": data.get("boundary", ""),
            "misuse": data.get("misuse", "")
        }
        
        scenes = data.get("scenes", {})
        if scene and scene in scenes:
            # 只输出指定场景
            formatted["scenes"][scene] = scenes[scene]
        else:
            # 输出所有场景
            formatted["scenes"] = scenes
        
        return formatted

    def batch_explain(self, terms: List[str], scene: Optional[str] = None) -> List[Dict]:
        """批量解释术语
        
        Args:
            terms: 术语列表
            scene: 指定场景
            
        Returns:
            结果列表
        """
        results = []
        for term in terms:
            result = self.explain(term, scene)
            results.append(result)
        return results


# ============================================================
# 文件处理功能
# ============================================================
def parse_batch_file(file_path: str) -> Tuple[bool, List[str], Optional[str]]:
    """解析批量文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        (是否成功, 术语列表, 错误码或None)
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return False, [], ErrorCode.E1003
    
    # 尝试多种编码读取
    content = None
    for encoding in ["utf-8", "gbk", "latin-1"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, IOError):
            continue
    
    if content is None:
        return False, [], ErrorCode.E1005
    
    # 尝试解析为JSON
    terms = []
    try:
        data = json.loads(content)
        if isinstance(data, list):
            terms = [str(item).strip() for item in data if str(item).strip()]
        elif isinstance(data, dict):
            # 兼容对象格式
            for key in ["terms", "items", "data"]:
                if key in data and isinstance(data[key], list):
                    terms = [str(item).strip() for item in data[key] if str(item).strip()]
                    break
    except json.JSONDecodeError:
        # 尝试按行解析纯文本
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        terms = lines
    
    if not terms:
        return False, [], ErrorCode.E1003
    
    return True, terms, None


# ============================================================
# 输出格式化
# ============================================================
def format_markdown(result: Dict) -> str:
    """将结果格式化为Markdown
    
    Args:
        result: explain()返回的结果字典
        
    Returns:
        Markdown格式字符串
    """
    if not result.get("success"):
        return f"**错误** ({result.get('error_code')}): {result.get('message')}"
    
    data = result["data"]
    lines = []
    lines.append(f"# {data['term']}")
    lines.append("")
    lines.append("## 核心定义")
    lines.append(data["core"])
    lines.append("")
    
    # 场景拆解
    lines.append("## 场景拆解")
    lines.append("| 场景 | 解释 |")
    lines.append("|------|------|")
    for scene_name, scene_desc in data["scenes"].items():
        lines.append(f"| {scene_name} | {scene_desc} |")
    lines.append("")
    
    # 边界界定
    lines.append("## 边界界定")
    lines.append(data["boundary"])
    lines.append("")
    
    # 常见误用
    lines.append("## 常见误用")
    lines.append(data["misuse"])
    
    return "\n".join(lines)


# ============================================================
# 自检功能
# ============================================================
def run_selftest() -> int:
    """运行离线自检
    
    Returns:
        退出码（0表示成功）
    """
    print("=== 术语释义助手 自检开始 ===")
    
    explainer = TermExplainer()
    
    # 测试用例1: 正常查询
    result = explainer.explain("微服务")
    if not result["success"]:
        print("[FAIL] 正常查询测试: 微服务查询应成功")
        return 1
    if result["data"]["term"] != "微服务":
        print("[FAIL] 正常查询测试: 术语名称不匹配")
        return 1
    if len(result["data"]["core"]) <= 10:
        print("[FAIL] 正常查询测试: 核心定义太短")
        return 1
    if len(result["data"]["scenes"]) < 3:
        print("[FAIL] 正常查询测试: 场景数量不足")
        return 1
    print("[PASS] 正常查询测试")
    
    # 测试用例2: 指定场景
    result = explainer.explain("区块链", scene="技术")
    if not result["success"]:
        print("[FAIL] 指定场景测试: 区块链查询应成功")
        return 1
    if "技术" not in result["data"]["scenes"]:
        print("[FAIL] 指定场景测试: 缺少技术场景")
        return 1
    if len(result["data"]["scenes"]) != 1:
        print("[FAIL] 指定场景测试: 应只包含指定场景")
        return 1
    print("[PASS] 指定场景测试")
    
    # 测试用例3: 空输入
    result = explainer.explain("")
    if result["success"]:
        print("[FAIL] 空输入测试: 空输入应失败")
        return 1
    if result["error_code"] != ErrorCode.E1001:
        print("[FAIL] 空输入测试: 错误码应为E1001")
        return 1
    print("[PASS] 空输入测试")
    
    # 测试用例4: 超长输入
    long_term = "A" * 150
    result = explainer.explain(long_term)
    if not result["success"]:
        print("[FAIL] 超长输入测试: 超长输入应截断后成功")
        return 1
    if len(result["data"]["term"]) > 100:
        print("[FAIL] 超长输入测试: 术语应被截断至100字符")
        return 1
    print("[PASS] 超长输入测试")
    
    # 测试用例5: 未命中术语
    result = explainer.explain("不存在的术语XYZ")
    if result["success"]:
        print("[FAIL] 未命中术语测试: 未知术语应失败")
        return 1
    if result["error_code"] != ErrorCode.E1004:
        print("[FAIL] 未命中术语测试: 错误码应为E1004")
        return 1
    print("[PASS] 未命中术语测试")
    
    # 测试用例6: 批量文件解析（内存模拟）
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(["微服务", "区块链"], f)
        tmp_path = f.name
    
    try:
        ok, terms, err = parse_batch_file(tmp_path)
        if not ok:
            print("[FAIL] 批量文件解析测试: 批量文件解析应成功")
            return 1
        if len(terms) != 2:
            print("[FAIL] 批量文件解析测试: 应解析出2个术语")
            return 1
        print("[PASS] 批量文件解析测试")
    finally:
        os.unlink(tmp_path)
    
    # 测试用例7: 批量解释
    results = explainer.batch_explain(["微服务", "区块链", "人工智能"])
    if len(results) != 3:
        print("[FAIL] 批量解释测试: 应有3个结果")
        return 1
    if not all(r["success"] for r in results):
        print("[FAIL] 批量解释测试: 所有批量查询应成功")
        return 1
    print("[PASS] 批量解释测试")
    
    # 测试用例8: 缓存功能
    explainer.query_knowledge_base("微服务")
    if "微服务" not in explainer.cache:
        print("[FAIL] 缓存功能测试: 缓存应包含微服务")
        return 1
    print("[PASS] 缓存功能测试")
    
    # 测试用例9: Markdown格式化
    result = explainer.explain("微服务")
    md = format_markdown(result)
    if "# 微服务" not in md:
        print("[FAIL] Markdown格式化测试: Markdown应包含标题")
        return 1
    if "## 核心定义" not in md:
        print("[FAIL] Markdown格式化测试: Markdown应包含核心定义")
        return 1
    if "## 场景拆解" not in md:
        print("[FAIL] Markdown格式化测试: Markdown应包含场景拆解")
        return 1
    print("[PASS] Markdown格式化测试")
    
    # 测试用例10: 输入规范化
    result = explainer.explain("  微服务  ")
    if not result["success"]:
        print("[FAIL] 输入规范化测试: 带空格输入应成功")
        return 1
    if result["data"]["term"] != "微服务":
        print("[FAIL] 输入规范化测试: 应去除首尾空格")
        return 1
    print("[PASS] 输入规范化测试")
    
    # 测试用例11: 场景不存在时返回所有场景
    result = explainer.explain("微服务", scene="不存在的场景")
    if not result["success"]:
        print("[FAIL] 场景不存在测试: 查询应成功")
        return 1
    if len(result["data"]["scenes"]) < 3:
        print("[FAIL] 场景不存在测试: 应返回所有场景")
        return 1
    print("[PASS] 场景不存在测试")
    
    # 测试用例12: 批量文件不存在
    ok, terms, err = parse_batch_file("/nonexistent/file.json")
    if ok:
        print("[FAIL] 批量文件不存在测试: 应返回失败")
        return 1
    if err != ErrorCode.E1003:
        print("[FAIL] 批量文件不存在测试: 错误码应为E1003")
        return 1
    print("[PASS] 批量文件不存在测试")
    
    print("=== 自检全部通过 ===")
    return 0


# ============================================================
# 命令行入口
# ============================================================
def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 按场景拆解术语含义",
        epilog="示例: python main.py 微服务 --scene 技术"
    )
    parser.add_argument("term", nargs="?", help="要解释的术语")
    parser.add_argument("--scene", "-s", help="指定场景（技术/业务/日常/学术）")
    parser.add_argument("--batch", "-b", help="批量处理文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 批量模式
    if args.batch:
        ok, terms, err = parse_batch_file(args.batch)
        if not ok:
            error_messages = {
                ErrorCode.E1003: f"批量文件不存在或格式错误: {args.batch}",
                ErrorCode.E1005: f"批量文件编码无法识别: {args.batch}"
            }
            print(f"错误 ({err}): {error_messages.get(err, '未知错误')}")
            return 1
        
        explainer = TermExplainer()
        results = explainer.batch_explain(terms, args.scene)
        for i, result in enumerate(results):
            print(f"--- 结果 {i+1}/{len(results)} ---")
            print(format_markdown(result))
            print()
        return 0
    
    # 单术语模式
    if not args.term:
        print(f"错误 ({ErrorCode.E1001}): 请输入要解释的术语")
        print("用法: python main.py <术语> [--scene 场景]")
        print("      python main.py --batch <文件路径>")
        print("      python main.py --selftest")
        return 1
    
    explainer = TermExplainer()
    result = explainer.explain(args.term, args.scene)
    
    if result["success"]:
        print(format_markdown(result))
        return 0
    else:
        error_messages = {
            ErrorCode.E1001: "请输入要解释的术语",
            ErrorCode.E1002: f"输入超长，已截断为: {result['data']['term'] if result['data'] else ''}",
            ErrorCode.E1004: f"未找到术语 '{args.term}' 的解释"
        }
        print(f"错误 ({result['error_code']}): {error_messages.get(result['error_code'], result['message'])}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
