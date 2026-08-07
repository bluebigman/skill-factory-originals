#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — Rails 代码片段速查与生成工具（独立实现）

本脚本根据功能规格独立编写，不参考任何既有代码。
提供 Rails 常用代码模式的片段生成、检索与自检功能。

用法示例:
    python scripts/main.py --list                     # 列出所有可用片段
    python scripts/main.py --get model                # 获取指定片段
    python scripts/main.py --search 关联              # 按关键词搜索片段
    python scripts/main.py --selftest                 # 运行内置自检
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 错误码定义（E001 - E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "未知命令或参数错误",
    "E002": "片段不存在",
    "E003": "搜索关键词为空",
    "E004": "JSON 序列化失败",
    "E005": "输出目录不可写",
    "E006": "片段内容格式错误",
    "E007": "内置自检数据缺失",
    "E008": "自检断言失败",
    "E009": "参数类型错误",
    "E010": "运行时异常",
}


def fail(code: str, message: Optional[str] = None) -> None:
    """输出错误信息并退出。"""
    text = ERROR_CODES.get(code, "未知错误")
    if message:
        text = f"{text}: {message}"
    print(f"[错误 {code}] {text}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class Snippet:
    """代码片段数据类。"""
    key: str                                   # 唯一标识
    title: str                                 # 标题
    category: str                              # 分类（model/controller/route/migration/view）
    tags: List[str] = field(default_factory=list)  # 标签
    code: str = ""                             # 代码内容
    description: str = ""                      # 描述


# ---------------------------------------------------------------------------
# 内置片段库（根据功能规格整理的 Rails 常用模式）
# ---------------------------------------------------------------------------
def build_snippet_library() -> Dict[str, Snippet]:
    """构建内置 Rails 片段库。"""
    library = {}

    # --- 模型（Model） ---
    library["model_belongs_to"] = Snippet(
        key="model_belongs_to",
        title="模型 belongs_to 关联",
        category="model",
        tags=["关联", "belongs_to", "外键"],
        code='''class Post < ApplicationRecord
  belongs_to :user
  # 可选: optional: true 表示外键可空
end''',
        description="在模型中添加 belongs_to 关联",
    )

    library["model_has_many"] = Snippet(
        key="model_has_many",
        title="模型 has_many 关联",
        category="model",
        tags=["关联", "has_many", "一对多"],
        code='''class User < ApplicationRecord
  has_many :posts, dependent: :destroy
  # dependent: :destroy 表示删除用户时级联删除关联记录
end''',
        description="在模型中添加 has_many 关联",
    )

    library["model_validates"] = Snippet(
        key="model_validates",
        title="模型验证",
        category="model",
        tags=["验证", "validates", "presence"],
        code='''class User < ApplicationRecord
  validates :name, presence: true, length: { maximum: 50 }
  validates :email, presence: true, uniqueness: true
end''',
        description="添加常见模型验证规则",
    )

    # --- 控制器（Controller） ---
    library["controller_restful"] = Snippet(
        key="controller_restful",
        title="RESTful 控制器模板",
        category="controller",
        tags=["控制器", "RESTful", "CRUD"],
        code='''class PostsController < ApplicationController
  before_action :set_post, only: [:show, :edit, :update, :destroy]

  def index
    @posts = Post.all
  end

  def show
  end

  def new
    @post = Post.new
  end

  def create
    @post = Post.new(post_params)
    if @post.save
      redirect_to @post, notice: "文章创建成功"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @post.update(post_params)
      redirect_to @post, notice: "文章更新成功"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @post.destroy
    redirect_to posts_url, notice: "文章已删除"
  end

  private

  def set_post
    @post = Post.find(params[:id])
  end

  def post_params
    params.require(:post).permit(:title, :content)
  end
end''',
        description="标准 RESTful 控制器七个动作",
    )

    library["controller_strong_params"] = Snippet(
        key="controller_strong_params",
        title="强参数（Strong Parameters）",
        category="controller",
        tags=["参数", "安全", "strong_params"],
        code='''def post_params
  params.require(:post).permit(:title, :content, :status)
end''',
        description="控制器中定义强参数过滤",
    )

    # --- 路由（Route） ---
    library["route_resources"] = Snippet(
        key="route_resources",
        title="资源路由",
        category="route",
        tags=["路由", "resources", "RESTful"],
        code='''Rails.application.routes.draw do
  resources :posts do
    resources :comments, only: [:create, :destroy]
  end
  # 嵌套资源：/posts/:post_id/comments
end''',
        description="定义资源及其嵌套路由",
    )

    library["route_custom"] = Snippet(
        key="route_custom",
        title="自定义路由",
        category="route",
        tags=["路由", "自定义", "member"],
        code='''Rails.application.routes.draw do
  resources :posts do
    member do
      get :publish    # /posts/:id/publish
    end
    collection do
      get :archived  # /posts/archived
    end
  end
end''',
        description="添加自定义 member/collection 路由",
    )

    # --- 迁移（Migration） ---
    library["migration_create_table"] = Snippet(
        key="migration_create_table",
        title="创建表迁移",
        category="migration",
        tags=["迁移", "建表", "schema"],
        code='''class CreatePosts < ActiveRecord::Migration[7.0]
  def change
    create_table :posts do |t|
      t.string :title
      t.text :content
      t.references :user, null: false, foreign_key: true

      t.timestamps
    end
  end
end''',
        description="生成创建表的迁移文件",
    )

    library["migration_add_column"] = Snippet(
        key="migration_add_column",
        title="添加字段迁移",
        category="migration",
        tags=["迁移", "加字段", "schema"],
        code='''class AddStatusToPosts < ActiveRecord::Migration[7.0]
  def change
    add_column :posts, :status, :integer, default: 0
    add_index :posts, :status
  end
end''',
        description="为已有表添加新字段和索引",
    )

    # --- 视图（View） ---
    library["view_form"] = Snippet(
        key="view_form",
        title="表单视图",
        category="view",
        tags=["视图", "表单", "form_with"],
        code='''<%= form_with(model: @post) do |form| %>
  <% if @post.errors.any? %>
    <div id="error_explanation">
      <h2><%= pluralize(@post.errors.count, "个错误") %></h2>
      <ul>
        <% @post.errors.each do |error| %>
          <li><%= error.full_message %></li>
        <% end %>
      </ul>
    </div>
  <% end %>

  <div>
    <%= form.label :title %>
    <%= form.text_field :title %>
  </div>

  <div>
    <%= form.label :content %>
    <%= form.text_area :content %>
  </div>

  <div>
    <%= form.submit %>
  </div>
<% end %>''',
        description="使用 form_with 生成表单",
    )

    library["view_partial"] = Snippet(
        key="view_partial",
        title="局部视图（Partial）",
        category="view",
        tags=["视图", "partial", "局部"],
        code='''# 在 index.html.erb 中渲染集合
<%= render @posts %>

# _post.html.erb（局部文件）
<article>
  <h2><%= link_to post.title, post %></h2>
  <p><%= truncate(post.content, length: 100) %></p>
</article>''',
        description="渲染局部视图（含集合渲染）",
    )

    return library


# ---------------------------------------------------------------------------
# 核心功能函数
# ---------------------------------------------------------------------------
def list_snippets(library: Dict[str, Snippet]) -> None:
    """列出所有可用片段。"""
    print("=== Rails 代码片段列表 ===")
    print(f"共 {len(library)} 个片段\n")

    # 按分类分组
    grouped: Dict[str, List[Snippet]] = {}
    for snippet in library.values():
        grouped.setdefault(snippet.category, []).append(snippet)

    for category in sorted(grouped.keys()):
        print(f"--- {category} ---")
        for snippet in grouped[category]:
            print(f"  {snippet.key:30s} {snippet.title}")
        print()


def get_snippet(library: Dict[str, Snippet], key: str) -> None:
    """获取并输出指定片段。"""
    snippet = library.get(key)
    if not snippet:
        fail("E002", f"片段 '{key}' 不存在")

    print(f"=== {snippet.title} ===")
    print(f"分类: {snippet.category}")
    print(f"标签: {', '.join(snippet.tags)}")
    print(f"描述: {snippet.description}\n")
    print("代码:")
    print(snippet.code)


def search_snippets(library: Dict[str, Snippet], keyword: str) -> List[Snippet]:
    """按关键词搜索片段（匹配标题、标签、描述、代码）。"""
    keyword_lower = keyword.lower()

    results = []
    for snippet in library.values():
        # 搜索范围：标题、标签、描述、代码
        searchable_text = " ".join([
            snippet.title,
            snippet.category,
            " ".join(snippet.tags),
            snippet.description,
            snippet.code,
        ]).lower()

        if keyword_lower in searchable_text:
            results.append(snippet)

    print(f"搜索关键词: '{keyword}'")
    print(f"找到 {len(results)} 个匹配片段\n")

    for snippet in results:
        print(f"  [{snippet.category}] {snippet.key}: {snippet.title}")
        print(f"    标签: {', '.join(snippet.tags)}")
        print(f"    描述: {snippet.description}")
        print()

    return results


def export_json(library: Dict[str, Snippet], output_path: str) -> None:
    """将片段库导出为 JSON 文件。"""
    try:
        data = {
            key: {
                "key": s.key,
                "title": s.title,
                "category": s.category,
                "tags": s.tags,
                "code": s.code,
                "description": s.description,
            }
            for key, s in library.items()
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        fail("E004", str(e))

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"片段库已导出到: {output_path}")
    except OSError as e:
        fail("E005", str(e))


# ---------------------------------------------------------------------------
# 自检功能
# ---------------------------------------------------------------------------
def run_selftest() -> None:
    """运行内置自检，验证核心逻辑正确性。"""
    print("=== 开始自检 ===")

    # 1. 构建片段库
    library = build_snippet_library()
    if not library:
        fail("E007", "内置片段库为空")
    print(f"[通过] 片段库构建成功，共 {len(library)} 个片段")

    # 2. 验证关键片段存在
    required_keys = [
        "model_belongs_to",
        "model_has_many",
        "controller_restful",
        "route_resources",
        "migration_create_table",
        "view_form",
    ]
    for key in required_keys:
        if key not in library:
            fail("E007", f"缺少关键片段: {key}")
    print("[通过] 关键片段完整性检查")

    # 3. 验证片段内容非空
    for key, snippet in library.items():
        if not snippet.code.strip():
            fail("E006", f"片段 '{key}' 代码为空")
        if not snippet.title.strip():
            fail("E006", f"片段 '{key}' 标题为空")
        if not snippet.category.strip():
            fail("E006", f"片段 '{key}' 分类为空")
    print("[通过] 片段内容完整性检查")

    # 4. 验证搜索功能
    search_results = search_snippets(library, "关联")
    if len(search_results) < 2:  # 至少应有 belongs_to 和 has_many
        fail("E008", "搜索 '关联' 结果数量异常")
    print("[通过] 搜索功能（关键词: 关联）")

    # 5. 验证搜索无结果情况
    empty_results = search_snippets(library, "不存在的关键词xyz")
    if empty_results:
        fail("E008", "搜索不存在的关键词应返回空结果")
    print("[通过] 搜索功能（无匹配场景）")

    # 6. 验证获取片段功能
    test_snippet = library.get("model_belongs_to")
    if not test_snippet:
        fail("E002", "无法获取片段 model_belongs_to")
    if "belongs_to" not in test_snippet.code:
        fail("E008", "片段内容包含 belongs_to")
    print("[通过] 获取片段功能")

    # 7. 验证分类统计
    categories = {}
    for snippet in library.values():
        categories[snippet.category] = categories.get(snippet.category, 0) + 1
    if "model" not in categories or "controller" not in categories:
        fail("E008", "分类统计异常")
    print(f"[通过] 分类统计: {categories}")

    # 8. 验证 JSON 导出
    try:
        data = {
            key: {
                "key": s.key,
                "title": s.title,
                "category": s.category,
                "tags": s.tags,
                "code": s.code,
                "description": s.description,
            }
            for key, s in library.items()
        }
        json_str = json.dumps(data, ensure_ascii=False)
        if not json_str:
            fail("E004", "JSON 导出为空")
    except (TypeError, ValueError) as e:
        fail("E004", str(e))
    print("[通过] JSON 序列化")

    print("\n=== 全部自检通过 ===")


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> None:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="Rails 代码片段速查与生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  %(prog)s --list
  %(prog)s --get model_belongs_to
  %(prog)s --search 关联
  %(prog)s --export snippets.json
  %(prog)s --selftest
""",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用片段",
    )
    parser.add_argument(
        "--get",
        metavar="KEY",
        help="获取指定片段（使用片段 key）",
    )
    parser.add_argument(
        "--search",
        metavar="KEYWORD",
        help="按关键词搜索片段",
    )
    parser.add_argument(
        "--export",
        metavar="OUTPUT_FILE",
        help="将片段库导出为 JSON 文件",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return

    # 构建片段库
    library = build_snippet_library()

    # 根据参数执行对应操作
    try:
        if args.list:
            list_snippets(library)
        elif args.get:
            get_snippet(library, args.get)
        elif args.search:
            if not args.search.strip():
                fail("E003", "搜索关键词不能为空")
            search_snippets(library, args.search.strip())
        elif args.export:
            export_json(library, args.export)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        fail("E010", "用户中断操作")
    except Exception as e:  # 兜底异常处理
        fail("E010", str(e))


if __name__ == "__main__":
    main()
