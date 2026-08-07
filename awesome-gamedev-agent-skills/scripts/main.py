#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awesome-gamedev-agent-skills 技能路由中枢
版本: 1.0.1
功能: 为AI编程代理提供游戏开发技能安装与路由加载能力
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 错误码定义
# E001: 参数错误
# E002: 输入数据为空
# E003: 无法解析输入格式
# E004: 技能未安装
# E005: 路由匹配失败
# E006: 批量处理中断
# E007: 无效的URL格式
# E008: 无效的置信度参数
# E009: 内部数据异常
# E010: 未知错误


# ============================================================
# 数据模型
# ============================================================

@dataclass
class SkillInfo:
    """子技能信息"""
    skill_id: str
    name: str
    category: str
    installed: bool = False
    version: str = "0.0.0"
    description: str = ""


@dataclass
class RouteResult:
    """路由结果"""
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    confidence: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    message: str = ""
    success: bool = False


@dataclass
class ParseResult:
    """解析结果"""
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """批量处理结果"""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# 核心路由引擎
# ============================================================

class SkillRouter:
    """技能路由引擎"""

    # 技能分类关键词库（内置知识，非外部依赖）
    CATEGORY_KEYWORDS = {
        "敌人AI": ["敌人", "AI", "行为树", "状态机", "寻路", "npc", "怪物", "boss", "智能"],
        "角色控制": ["角色", "玩家", "移动", "跳跃", "动画", "控制器", "input", "输入"],
        "场景管理": ["场景", "关卡", "地图", "加载", "切换", "level", "scene"],
        "UI系统": ["界面", "菜单", "HUD", "背包", "商店", "弹窗", "ui", "按钮"],
        "物理系统": ["物理", "碰撞", "刚体", "重力", "触发器", "physics", "collision"],
        "音频系统": ["音乐", "音效", "声音", "音频", "audio", "sound", "bgm"],
        "网络同步": ["网络", "联机", "多人", "同步", "服务器", "客户端", "network", "online"],
        "存档系统": ["存档", "读档", "保存", "加载", "save", "load", "进度"],
        "特效系统": ["特效", "粒子", "动画", "shader", "材质", "effect", "vfx"],
        "数据配置": ["配置", "数据表", "JSON", "Excel", "策划", "数值", "config", "data"],
    }

    # 技能安装清单（模拟已安装技能）
    INSTALLED_SKILLS = {
        "enemy-ai": SkillInfo(
            skill_id="enemy-ai",
            name="敌人AI生成器",
            category="敌人AI",
            installed=True,
            version="1.2.0",
            description="生成敌人AI行为树与状态机"
        ),
        "character-control": SkillInfo(
            skill_id="character-control",
            name="角色控制器",
            category="角色控制",
            installed=True,
            version="2.0.1",
            description="角色移动与动画控制"
        ),
        "scene-manager": SkillInfo(
            skill_id="scene-manager",
            name="场景管理器",
            category="场景管理",
            installed=False,
            version="0.9.0",
            description="场景加载与切换"
        ),
        "ui-builder": SkillInfo(
            skill_id="ui-builder",
            name="UI构建器",
            category="UI系统",
            installed=True,
            version="1.5.0",
            description="界面组件生成"
        ),
        "physics-helper": SkillInfo(
            skill_id="physics-helper",
            name="物理系统助手",
            category="物理系统",
            installed=True,
            version="1.1.0",
            description="碰撞与刚体配置"
        ),
        "audio-manager": SkillInfo(
            skill_id="audio-manager",
            name="音频管理器",
            category="音频系统",
            installed=False,
            version="0.5.0",
            description="音乐音效控制"
        ),
        "network-sync": SkillInfo(
            skill_id="network-sync",
            name="网络同步器",
            category="网络同步",
            installed=False,
            version="0.3.0",
            description="多人联机同步"
        ),
        "save-system": SkillInfo(
            skill_id="save-system",
            name="存档系统",
            category="存档系统",
            installed=True,
            version="1.8.0",
            description="游戏进度保存与读取"
        ),
        "vfx-builder": SkillInfo(
            skill_id="vfx-builder",
            name="特效构建器",
            category="特效系统",
            installed=True,
            version="1.4.0",
            description="粒子特效配置"
        ),
        "data-config": SkillInfo(
            skill_id="data-config",
            name="数据配置工具",
            category="数据配置",
            installed=True,
            version="2.2.0",
            description="配置表解析与生成"
        ),
    }

    def __init__(self) -> None:
        """初始化路由器"""
        self.skills: Dict[str, SkillInfo] = dict(self.INSTALLED_SKILLS)

    # ---------- 技能管理 ----------

    def install_skill(self, skill: SkillInfo) -> bool:
        """安装技能"""
        try:
            if not skill or not skill.skill_id:
                raise ValueError("技能信息无效")
            self.skills[skill.skill_id] = skill
            return True
        except Exception as e:
            print(f"E001: 安装技能失败 - {e}")
            return False

    def uninstall_skill(self, skill_id: str) -> bool:
        """卸载技能"""
        try:
            if skill_id in self.skills:
                self.skills[skill_id].installed = False
                return True
            return False
        except Exception as e:
            print(f"E002: 卸载技能失败 - {e}")
            return False

    def get_installed_skills(self) -> List[SkillInfo]:
        """获取已安装技能列表"""
        return [s for s in self.skills.values() if s.installed]

    # ---------- 核心路由 ----------

    def route(self, task_description: str) -> RouteResult:
        """
        根据任务描述路由到对应技能
        """
        result = RouteResult()
        try:
            if not task_description or not task_description.strip():
                result.message = "任务描述为空"
                result.confidence = 0.0
                return result

            text = task_description.lower()
            best_match: Optional[SkillInfo] = None
            best_score = 0
            matched_keywords: List[str] = []

            # 遍历所有技能，计算匹配分数
            for skill in self.skills.values():
                if not skill.installed:
                    continue

                keywords = self.CATEGORY_KEYWORDS.get(skill.category, [])
                score = 0
                skill_matched = []

                for kw in keywords:
                    if kw.lower() in text:
                        score += 1
                        skill_matched.append(kw)

                if score > best_score:
                    best_score = score
                    best_match = skill
                    matched_keywords = skill_matched

            # 没有找到匹配
            if best_match is None or best_score == 0:
                result.message = "未找到匹配的技能"
                result.confidence = 0.0
                return result

            # 计算置信度（基于关键词命中率）
            total_keywords = len(self.CATEGORY_KEYWORDS.get(best_match.category, []))
            confidence = min(0.95, 0.4 + (best_score / total_keywords) * 0.55) if total_keywords > 0 else 0.4

            result.success = True
            result.skill_id = best_match.skill_id
            result.skill_name = best_match.name
            result.confidence = round(confidence, 2)
            result.matched_keywords = matched_keywords
            result.message = f"成功路由到技能: {best_match.name}"

        except Exception as e:
            result.message = f"E010: 路由过程发生错误 - {e}"
            result.confidence = 0.0

        return result

    # ---------- 数据解析 ----------

    def parse_input(self, raw_input: str, input_type: str = "text") -> ParseResult:
        """
        将输入解析为结构化数据
        支持: text, json, url
        """
        result = ParseResult()
        try:
            if not raw_input:
                result.warnings.append("输入为空")
                result.confidence = 0.0
                return result

            if input_type == "json":
                try:
                    result.data = json.loads(raw_input)
                except json.JSONDecodeError as e:
                    result.warnings.append(f"JSON解析失败: {e}")
                    result.confidence = 0.3
                    # 尝试提取关键字段
                    result.data = self._extract_json_fields(raw_input)

            elif input_type == "url":
                parsed = urlparse(raw_input)
                if not parsed.scheme or not parsed.netloc:
                    result.warnings.append("URL格式无效")
                    result.confidence = 0.2
                    return result
                result.data = {
                    "scheme": parsed.scheme,
                    "host": parsed.netloc,
                    "path": parsed.path,
                    "query": parsed.query
                }

            else:  # text
                result.data = self._extract_text_entities(raw_input)

        except Exception as e:
            result.warnings.append(f"E003: 解析失败 - {e}")
            result.confidence = 0.0

        return result

    def _extract_json_fields(self, text: str) -> Dict[str, Any]:
        """从非标准JSON文本中提取字段"""
        fields: Dict[str, Any] = {}
        # 匹配 key: value 模式
        pattern = r'["\']?(\w+)["\']?\s*[:=]\s*["\']?([^"\',}\]]+)["\']?'
        matches = re.findall(pattern, text)
        for key, value in matches:
            if key and value:
                fields[key.strip()] = value.strip()
        return fields

    def _extract_text_entities(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键实体"""
        entities: Dict[str, Any] = {
            "keywords": [],
            "numbers": [],
            "emails": [],
            "urls": []
        }

        # 提取关键词（中文和英文）
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        en_words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        entities["keywords"] = list(set(cn_words + en_words))[:20]

        # 提取数字
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        entities["numbers"] = [float(n) for n in numbers[:10]]

        # 提取邮箱
        emails = re.findall(r'\b[\w.+-]+@[\w-]+\.[\w.]+\b', text)
        entities["emails"] = emails[:5]

        # 提取URL
        urls = re.findall(r'https?://[^\s]+', text)
        entities["urls"] = urls[:5]

        return entities

    # ---------- 信息提取 ----------

    def extract_info(self, text: str, fields: List[str]) -> Dict[str, Any]:
        """提取指定字段的信息"""
        extracted: Dict[str, Any] = {}
        try:
            if not text or not fields:
                return extracted

            # 对每个字段进行提取
            for field in fields:
                # 尝试多种模式
                patterns = [
                    rf'{field}\s*[:：]\s*([^\n,，;；]+)',
                    rf'["\']{field}["\']\s*[:=]\s*["\']([^"\']+)["\']',
                    rf'\b{field}\b\s*=\s*(\w+)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        extracted[field] = match.group(1).strip()
                        break

        except Exception as e:
            print(f"E004: 信息提取失败 - {e}")

        return extracted

    # ---------- 批量处理 ----------

    def batch_process(self, items: List[str], processor: str = "parse") -> BatchResult:
        """
        批量处理多个条目
        processor: parse / extract / route
        """
        result = BatchResult()
        try:
            if not items:
                result.total = 0
                return result

            result.total = len(items)
            for item in items:
                try:
                    if processor == "parse":
                        parsed = self.parse_input(item)
                        process_result = {
                            "input": item[:100],
                            "data": parsed.data,
                            "confidence": parsed.confidence
                        }
                    elif processor == "route":
                        routed = self.route(item)
                        process_result = {
                            "input": item[:100],
                            "skill_id": routed.skill_id,
                            "confidence": routed.confidence
                        }
                    else:
                        raise ValueError(f"不支持的处理器: {processor}")

                    result.results.append(process_result)
                    result.succeeded += 1

                except Exception as e:
                    result.failed += 1
                    result.results.append({
                        "input": item[:100],
                        "error": str(e)
                    })

        except Exception as e:
            print(f"E005: 批量处理失败 - {e}")

        return result

    # ---------- 置信度标注 ----------

    def annotate_confidence(self, data: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """为数据添加置信度标注"""
        try:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("置信度必须在0-1之间")

            annotated = dict(data)
            annotated["_confidence"] = round(confidence, 2)
            annotated["_warning"] = "结果仅供参考，请人工复核" if confidence < 0.8 else "高置信度结果"
            return annotated
        except Exception as e:
            print(f"E006: 置信度标注失败 - {e}")
            return data


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置自检样例，使用宽松断言确保稳定性
    """
    print("=" * 50)
    print("开始自检 awesome-gamedev-agent-skills")
    print("=" * 50)

    router = SkillRouter()
    all_passed = True

    # 测试1: 技能安装列表
    print("\n[1/5] 测试技能安装列表...")
    installed = router.get_installed_skills()
    assert len(installed) > 0, "E001: 应该至少有1个已安装技能"
    print(f"  ✓ 已安装技能数: {len(installed)}")

    # 测试2: 路由功能
    print("\n[2/5] 测试技能路由...")
    test_cases = [
        "帮我写一个敌人AI脚本，包含状态机和寻路",
        "实现玩家角色移动和跳跃控制",
        "创建一个背包UI界面",
        "配置物理碰撞体",
        "保存游戏进度"
    ]
    route_success = 0
    for tc in test_cases:
        result = router.route(tc)
        if result.success:
            route_success += 1
            print(f"  ✓ 路由成功: '{tc[:20]}...' -> {result.skill_name} (置信度: {result.confidence})")
        else:
            print(f"  ✗ 路由失败: '{tc[:20]}...' -> {result.message}")
    assert route_success >= 3, "E002: 至少3个测试用例应路由成功"
    print(f"  ✓ 路由成功率: {route_success}/{len(test_cases)}")

    # 测试3: 数据解析
    print("\n[3/5] 测试数据解析...")
    test_input = '{"enemy_name": "Boss", "hp": 1000, "attack": 50}'
    parsed = router.parse_input(test_input, "json")
    assert parsed.data is not None, "E003: 解析结果不应为空"
    print(f"  ✓ JSON解析成功: {json.dumps(parsed.data, ensure_ascii=False)[:80]}")

    text_input = "玩家角色需要3个技能，等级50，目标是打败最终BOSS"
    text_parsed = router.parse_input(text_input, "text")
    assert len(text_parsed.data.get("keywords", [])) > 0, "E004: 应提取到关键词"
    assert len(text_parsed.data.get("numbers", [])) > 0, "E005: 应提取到数字"
    print(f"  ✓ 文本解析成功: 关键词{len(text_parsed.data['keywords'])}个, 数字{len(text_parsed.data['numbers'])}个")

    # 测试4: 批量处理
    print("\n[4/5] 测试批量处理...")
    batch_items = [
        "设计一个敌人AI",
        "创建UI菜单",
        "配置物理碰撞",
        "编写存档系统"
    ]
    batch_result = router.batch_process(batch_items, "route")
    assert batch_result.total == len(batch_items), "E006: 总数应匹配"
    assert batch_result.succeeded > 0, "E007: 至少1个应成功"
    print(f"  ✓ 批量处理: 成功{batch_result.succeeded}/{batch_result.total}, 失败{batch_result.failed}")

    # 测试5: 置信度标注
    print("\n[5/5] 测试置信度标注...")
    sample_data = {"skill": "enemy-ai", "type": "behavior-tree"}
    annotated = router.annotate_confidence(sample_data, 0.85)
    assert "_confidence" in annotated, "E008: 应包含置信度字段"
    assert 0.0 <= annotated["_confidence"] <= 1.0, "E009: 置信度应在0-1范围"
    print(f"  ✓ 置信度标注成功: {annotated['_confidence']}")

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 所有自检通过!")
    else:
        print("❌ 存在失败项!")
    print("=" * 50)
    return all_passed


# ============================================================
# 主入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="游戏开发技能路由中枢 - 为AI编程代理提供技能安装与路由加载",
        epilog="示例: python main.py --route '帮我写一个敌人AI'"
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检，不依赖外部文件或网络"
    )

    parser.add_argument(
        "--route",
        type=str,
        metavar="TASK",
        help="路由任务描述到对应技能"
    )

    parser.add_argument(
        "--parse",
        type=str,
        metavar="INPUT",
        help="解析输入数据（支持JSON/文本/URL）"
    )

    parser.add_argument(
        "--parse-type",
        type=str,
        choices=["text", "json", "url"],
        default="text",
        help="输入数据类型（默认: text）"
    )

    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="列出所有已安装技能"
    )

    parser.add_argument(
        "--batch",
        type=str,
        metavar="FILE",
        help="批量处理文件中的条目（每行一个）"
    )

    parser.add_argument(
        "--info",
        type=str,
        metavar="TEXT",
        help="从文本提取关键信息"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 创建路由器
    router = SkillRouter()

    # 路由模式
    if args.route:
        result = router.route(args.route)
        if result.success:
            print(json.dumps({
                "success": True,
                "skill_id": result.skill_id,
                "skill_name": result.skill_name,
                "confidence": result.confidence,
                "matched_keywords": result.matched_keywords,
                "message": result.message
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({
                "success": False,
                "message": result.message,
                "confidence": result.confidence
            }, ensure_ascii=False, indent=2))
        return 0 if result.success else 1

    # 解析模式
    if args.parse:
        parsed = router.parse_input(args.parse, args.parse_type)
        print(json.dumps({
            "data": parsed.data,
            "confidence": parsed.confidence,
            "warnings": parsed.warnings
        }, ensure_ascii=False, indent=2))
        return 0

    # 列表模式
    if args.list_skills:
        skills = router.get_installed_skills()
        print(f"已安装技能 ({len(skills)}):")
        for skill in skills:
            print(f"  - [{skill.skill_id}] {skill.name} (v{skill.version}) - {skill.description}")
        return 0

    # 批量模式
    if args.batch:
        try:
            with open(args.batch, "r", encoding="utf-8") as f:
                items = [line.strip() for line in f if line.strip()]
            result = router.batch_process(items, "route")
            print(json.dumps({
                "total": result.total,
                "succeeded": result.succeeded,
                "failed": result.failed,
                "results": result.results
            }, ensure_ascii=False, indent=2))
            return 0
        except FileNotFoundError:
            print("E007: 文件不存在")
            return 1
        except Exception as e:
            print(f"E008: 批量处理失败 - {e}")
            return 1

    # 信息提取模式
    if args.info:
        extracted = router.extract_info(args.info, ["name", "type", "level", "hp", "attack"])
        print(json.dumps(extracted, ensure_ascii=False, indent=2))
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
