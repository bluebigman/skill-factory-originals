#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — awesomeness 技能独立实现

功能：Rails 组件速查、代码片段检索与整理。
本脚本为 clean-room 独立实现，仅依据功能规格编写。

用法：
    python scripts/main.py --selftest     # 离线自检核心逻辑
    python scripts/main.py --search 分页  # 检索组件（示例）
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件错误：无法读取或写入文件",
    "E003": "数据错误：数据格式不符合预期",
    "E004": "检索错误：未找到匹配结果",
    "E005": "网络错误：网络访问失败",
    "E006": "权限错误：没有足够的权限执行操作",
    "E007": "资源错误：系统资源不足",
    "E008": "配置错误：配置信息不正确",
    "E009": "依赖错误：缺少必要的依赖库",
    "E010": "未知错误：发生未预期的错误",
}


@dataclass
class RailsComponent:
    """Rails 组件数据模型"""
    name: str                       # 组件名称
    category: str                   # 分类（如：模型、控制器、视图、路由等）
    description: str                # 简要描述
    code_snippet: str               # 代码片段
    tags: List[str] = field(default_factory=list)   # 标签
    confidence: float = 0.8         # 置信度（0-1）
    source_url: str = ""            # 来源链接


# ---------------------------------------------------------------------------
# 内置硬编码样例数据（用于 --selftest 离线自检）
# ---------------------------------------------------------------------------
BUILTIN_SAMPLE_COMPONENTS: List[RailsComponent] = [
    RailsComponent(
        name="scaffold",
        category="命令行工具",
        description="快速生成模型、控制器、视图的完整 CRUD 骨架",
        code_snippet="rails generate scaffold Post title:string body:text",
        tags=["生成器", "CRUD", "快速原型"],
        confidence=0.95,
        source_url="https://guides.rubyonrails.org/command_line.html",
    ),
    RailsComponent(
        name="strong_parameters",
        category="控制器",
        description="白名单方式过滤请求参数，防止批量赋值漏洞",
        code_snippet="""
        def post_params
          params.require(:post).permit(:title, :body, :tag_ids)
        end
        """,
        tags=["安全", "参数过滤", "批量赋值"],
        confidence=0.92,
        source_url="https://guides.rubyonrails.org/action_controller_overview.html",
    ),
    RailsComponent(
        name="partial",
        category="视图",
        description="视图模板复用，通过下划线前缀文件实现局部渲染",
        code_snippet="""
        <%= render partial: 'post', locals: { post: @post } %>
        """,
        tags=["视图复用", "模板", "DRY"],
        confidence=0.88,
        source_url="https://guides.rubyonrails.org/layouts_and_rendering.html",
    ),
    RailsComponent(
        name="named_route",
        category="路由",
        description="通过路由命名生成 URL 辅助方法",
        code_snippet="""
        resources :posts do
          member do
            get :publish
          end
        end
        """,
        tags=["路由", "URL辅助", "RESTful"],
        confidence=0.85,
        source_url="https://guides.rubyonrails.org/routing.html",
    ),
    RailsComponent(
        name="migration",
        category="数据库",
        description="数据库结构版本化迁移",
        code_snippet="""
        class CreatePosts < ActiveRecord::Migration[7.0]
          def change
            create_table :posts do |t|
              t.string :title
              t.text :body
              t.timestamps
            end
          end
        end
        """,
        tags=["数据库", "版本控制", "schema"],
        confidence=0.93,
        source_url="https://guides.rubyonrails.org/active_record_migrations.html",
    ),
    RailsComponent(
        name="before_action",
        category="控制器",
        description="在控制器动作执行前运行指定方法",
        code_snippet="""
        before_action :authenticate_user!, only: [:edit, :update]
        """,
        tags=["过滤器", "认证", "生命周期"],
        confidence=0.90,
        source_url="https://guides.rubyonrails.org/action_controller_overview.html",
    ),
]


# ---------------------------------------------------------------------------
# 核心功能：检索与整理
# ---------------------------------------------------------------------------
class RailsComponentIndex:
    """Rails 组件索引，提供检索与速查卡片生成功能"""

    def __init__(self, components: Optional[List[RailsComponent]] = None):
        self.components: List[RailsComponent] = components or []
        self._build_index()

    def _build_index(self) -> None:
        """构建内部索引（按名称和标签）"""
        self._name_index: Dict[str, RailsComponent] = {}
        self._tag_index: Dict[str, List[RailsComponent]] = {}
        for comp in self.components:
            key = comp.name.lower()
            if key not in self._name_index:
                self._name_index[key] = comp
            # 标签索引
            for tag in comp.tags:
                tag_key = tag.lower()
                if tag_key not in self._tag_index:
                    self._tag_index[tag_key] = []
                self._tag_index[tag_key].append(comp)

    def add_component(self, component: RailsComponent) -> None:
        """添加单个组件并更新索引"""
        self.components.append(component)
        key = component.name.lower()
        self._name_index[key] = component
        for tag in component.tags:
            tag_key = tag.lower()
            if tag_key not in self._tag_index:
                self._tag_index[tag_key] = []
            self._tag_index[tag_key].append(component)

    def search(self, query: str, limit: int = 10) -> List[RailsComponent]:
        """
        根据关键词检索组件。
        匹配范围：名称、描述、标签、代码片段。
        返回按置信度降序排列的结果。
        """
        if not query or not query.strip():
            return []
        q = query.strip().lower()
        results: List[Tuple[float, RailsComponent]] = []

        for comp in self.components:
            score = 0.0
            # 名称匹配（权重最高）
            if q in comp.name.lower():
                score += 1.0
            # 标签匹配
            for tag in comp.tags:
                if q in tag.lower():
                    score += 0.8
                    break
            # 描述匹配
            if q in comp.description.lower():
                score += 0.5
            # 代码片段匹配
            if q in comp.code_snippet.lower():
                score += 0.3

            if score > 0:
                # 结合置信度加权
                final_score = score * comp.confidence
                results.append((final_score, comp))

        # 按分数降序排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [comp for _, comp in results[:limit]]

    def search_by_category(self, category: str) -> List[RailsComponent]:
        """按分类筛选组件"""
        return [c for c in self.components if c.category == category]

    def generate_cheat_card(self, component: RailsComponent) -> Dict:
        """生成单个组件的速查卡片"""
        return {
            "name": component.name,
            "category": component.category,
            "description": component.description,
            "code_snippet": component.code_snippet.strip(),
            "tags": component.tags,
            "confidence": round(component.confidence, 2),
            "source_url": component.source_url,
        }

    def generate_all_cheat_cards(self) -> List[Dict]:
        """生成所有组件的速查卡片列表"""
        return [self.generate_cheat_card(c) for c in self.components]

    def export_json(self) -> str:
        """导出全部数据为 JSON 字符串"""
        data = {
            "components": self.generate_all_cheat_cards(),
            "total": len(self.components),
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用内置硬编码样例数据，不读外部文件、不依赖工作目录、不访问网络。
    返回 0 表示通过，非 0 表示失败。
    """
    print("=" * 60)
    print("awesomeness 技能自检开始")
    print("=" * 60)

    # 1. 初始化索引
    index = RailsComponentIndex(BUILTIN_SAMPLE_COMPONENTS)
    assert len(index.components) >= 5, "E003: 内置样例数据不足"
    print(f"[PASS] 索引初始化成功，共 {len(index.components)} 个组件")

    # 2. 测试名称检索（宽松断言）
    results = index.search("scaffold")
    assert len(results) >= 1, "E004: 名称检索失败"
    assert results[0].name.lower() == "scaffold", "E004: 名称检索结果不正确"
    print(f"[PASS] 名称检索成功，找到 {len(results)} 个结果")

    # 3. 测试标签检索（宽松断言）
    results = index.search("安全")
    assert len(results) >= 1, "E004: 标签检索失败"
    print(f"[PASS] 标签检索成功，找到 {len(results)} 个结果")

    # 4. 测试分类筛选
    controllers = index.search_by_category("控制器")
    assert len(controllers) >= 2, "E003: 控制器分类数据不足"
    print(f"[PASS] 分类筛选成功，控制器类组件 {len(controllers)} 个")

    # 5. 测试速查卡片生成
    card = index.generate_cheat_card(BUILTIN_SAMPLE_COMPONENTS[0])
    assert card["name"], "E003: 速查卡片缺少名称"
    assert card["code_snippet"], "E003: 速查卡片缺少代码片段"
    assert 0.0 <= card["confidence"] <= 1.0, "E003: 置信度超出范围"
    print(f"[PASS] 速查卡片生成成功: {card['name']}")

    # 6. 测试 JSON 导出（宽松断言）
    json_str = index.export_json()
    data = json.loads(json_str)
    assert data["total"] >= 5, "E003: JSON 导出数据量不足"
    assert len(data["components"]) == data["total"], "E003: JSON 导出数据不一致"
    print(f"[PASS] JSON 导出成功，共 {data['total']} 条记录")

    # 7. 测试空查询（边界情况）
    empty_results = index.search("")
    assert empty_results == [], "E003: 空查询应返回空列表"
    print("[PASS] 空查询处理正确")

    # 8. 测试无匹配查询（边界情况）
    no_match = index.search("不存在的关键词xyz")
    assert no_match == [], "E003: 无匹配查询应返回空列表"
    print("[PASS] 无匹配查询处理正确")

    # 9. 测试添加组件
    new_comp = RailsComponent(
        name="test_component",
        category="测试",
        description="自检临时组件",
        code_snippet="puts 'hello'",
        tags=["测试"],
    )
    index.add_component(new_comp)
    assert len(index.components) == len(BUILTIN_SAMPLE_COMPONENTS) + 1, "E003: 添加组件失败"
    print("[PASS] 添加组件成功")

    # 10. 测试检索结果排序（宽松断言）
    results = index.search("控制器")
    if len(results) > 1:
        # 验证结果按置信度降序（允许相等）
        confidences = [r.confidence for r in results]
        assert confidences == sorted(confidences, reverse=True), "E003: 排序不正确"
    print("[PASS] 检索排序正确")

    print("=" * 60)
    print("所有自检通过 ✔")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="awesomeness — Rails 组件速查与代码片段检索工具"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（使用内置样例数据，不依赖外部环境）",
    )
    parser.add_argument(
        "--search",
        type=str,
        metavar="关键词",
        help="检索 Rails 组件（支持名称、标签、描述匹配）",
    )
    parser.add_argument(
        "--category",
        type=str,
        metavar="分类",
        help="按分类筛选组件",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="导出全部组件为 JSON 格式",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="检索结果数量上限（默认 10）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            return run_selftest()
        except AssertionError as e:
            print(f"E003: 自检失败 — {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"E010: 自检发生未知错误 — {e}", file=sys.stderr)
            return 1

    # 初始化索引（使用内置样例数据）
    index = RailsComponentIndex(BUILTIN_SAMPLE_COMPONENTS)

    # 导出模式
    if args.export:
        print(index.export_json())
        return 0

    # 检索模式
    if args.search:
        results = index.search(args.search, limit=args.limit)
        if not results:
            print(f"E004: 未找到与 '{args.search}' 匹配的组件", file=sys.stderr)
            return 4
        print(f"\n找到 {len(results)} 个与 '{args.search}' 相关的组件：\n")
        for i, comp in enumerate(results, 1):
            print(f"--- [{i}] {comp.name} (置信度: {comp.confidence:.0%}) ---")
            print(f"分类: {comp.category}")
            print(f"描述: {comp.description}")
            print(f"标签: {', '.join(comp.tags)}")
            print(f"代码片段:\n{comp.code_snippet.strip()}\n")
        return 0

    # 分类筛选模式
    if args.category:
        results = index.search_by_category(args.category)
        if not results:
            print(f"E004: 分类 '{args.category}' 下没有组件", file=sys.stderr)
            return 4
        print(f"\n分类 '{args.category}' 下的组件（共 {len(results)} 个）：\n")
        for i, comp in enumerate(results, 1):
            print(f"--- [{i}] {comp.name} ---")
            print(f"描述: {comp.description}")
            print(f"置信度: {comp.confidence:.0%}\n")
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
