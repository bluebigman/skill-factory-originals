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
import re
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
# 片段生成功能（核心能力实现）
# ---------------------------------------------------------------------------
def generate_snippet(
    model_name: str,
    fields: Optional[List[str]] = None,
    associations: Optional[List[str]] = None,
    validations: Optional[List[str]] = None,
) -> Snippet:
    """
    根据用户输入动态生成 Rails 模型片段。
    
    Args:
        model_name: 模型名称（如 "Post"）
        fields: 字段列表（如 ["title:string", "content:text"]）
        associations: 关联列表（如 ["belongs_to:user"]）
        validations: 验证列表（如 ["presence:title"]）
    
    Returns:
        生成的 Snippet 对象
    """
    if not model_name or not model_name.strip():
        fail("E009", "模型名称不能为空")
    
    # 清理模型名称
    model_name = model_name.strip()
    if not re.match(r'^[A-Z][A-Za-z0-9]*$', model_name):
        fail("E009", f"模型名称 '{model_name}' 格式不正确，应为驼峰命名")
    
    fields = fields or []
    associations = associations or []
    validations = validations or []
    
    # 生成模型代码
    lines = [f"class {model_name} < ApplicationRecord"]
    
    # 添加关联
    for assoc in associations:
        assoc = assoc.strip()
        if ":" in assoc:
            assoc_type, assoc_name = assoc.split(":", 1)
            assoc_type = assoc_type.strip()
            assoc_name = assoc_name.strip()
            if assoc_type in ("belongs_to", "has_many", "has_one", "has_and_belongs_to_many"):
                lines.append(f"  {assoc_type} :{assoc_name}")
            else:
                fail("E009", f"不支持的关联类型: {assoc_type}")
    
    # 添加验证
    for validation in validations:
        validation = validation.strip()
        if ":" in validation:
            v_type, v_field = validation.split(":", 1)
            v_type = v_type.strip()
            v_field = v_field.strip()
            if v_type in ("presence", "uniqueness", "numericality", "length"):
                if v_type == "length":
                    lines.append(f"  validates :{v_field}, length: {{ maximum: 255 }}")
                else:
                    lines.append(f"  validates :{v_field}, {v_type}: true")
            else:
                fail("E009", f"不支持的验证类型: {v_type}")
    
    # 添加字段作为 attr_accessor 注释（实际字段由迁移管理）
    if fields:
        lines.append("")
        lines.append("  # 字段（由迁移管理）:")
        for field in fields:
            field = field.strip()
            if ":" in field:
                f_name, f_type = field.split(":", 1)
                lines.append(f"  #   {f_name.strip()}: {f_type.strip()}")
            else:
                lines.append(f"  #   {field}")
    
    lines.append("end")
    code = "\n".join(lines)
    
    # 生成标签
    tags = ["生成", "模型"]
    tags.extend([a.split(":")[0].strip() for a in associations if ":" in a])
    tags.extend([v.split(":")[0].strip() for v in validations if ":" in v])
    
    return Snippet(
        key=f"generated_{model_name.lower()}",
        title=f"生成的 {model_name} 模型",
        category="model",
        tags=tags,
        code=code,
        description=f"根据用户输入动态生成的 {model_name} 模型片段",
    )


def generate_controller(
    resource_name: str,
    actions: Optional[List[str]] = None,
) -> Snippet:
    """
    根据用户输入动态生成 Rails 控制器片段。
    
    Args:
        resource_name: 资源名称（如 "posts"）
        actions: 需要生成的动作列表（如 ["index", "show", "create"]）
    
    Returns:
        生成的 Snippet 对象
    """
    if not resource_name or not resource_name.strip():
        fail("E009", "资源名称不能为空")
    
    resource_name = resource_name.strip().lower()
    if not re.match(r'^[a-z][a-z0-9_]*$', resource_name):
        fail("E009", f"资源名称 '{resource_name}' 格式不正确，应为小写蛇形命名")
    
    actions = actions or ["index", "show", "new", "create", "edit", "update", "destroy"]
    model_name = resource_name.singularize() if hasattr(resource_name, 'singularize') else resource_name.rstrip('s')
    model_class = model_name.capitalize()
    
    lines = [f"class {model_class}Controller < ApplicationController"]
    
    # 添加 before_action
    if any(a in actions for a in ["show", "edit", "update", "destroy"]):
        lines.append(f"  before_action :set_{model_name}, only: {[a for a in actions if a in ['show', 'edit', 'update', 'destroy']]}")
        lines.append("")
    
    # 生成动作
    for action in actions:
        action = action.strip()
        if action == "index":
            lines.append(f"  def index")
            lines.append(f"    @{resource_name} = {model_class}.all")
            lines.append(f"  end")
        elif action == "show":
            lines.append(f"  def show")
            lines.append(f"  end")
        elif action == "new":
            lines.append(f"  def new")
            lines.append(f"    @{model_name} = {model_class}.new")
            lines.append(f"  end")
        elif action == "create":
            lines.append(f"  def create")
            lines.append(f"    @{model_name} = {model_class}.new({model_name}_params)")
            lines.append(f"    if @{model_name}.save")
            lines.append(f"      redirect_to @{model_name}, notice: \"{model_class}创建成功\"")
            lines.append(f"    else")
            lines.append(f"      render :new, status: :unprocessable_entity")
            lines.append(f"    end")
            lines.append(f"  end")
        elif action == "edit":
            lines.append(f"  def edit")
            lines.append(f"  end")
        elif action == "update":
            lines.append(f"  def update")
            lines.append(f"    if @{model_name}.update({model_name}_params)")
            lines.append(f"      redirect_to @{model_name}, notice: \"{model_class}更新成功\"")
            lines.append(f"    else")
            lines.append(f"      render :edit, status: :unprocessable_entity")
            lines.append(f"    end")
            lines.append(f"  end")
        elif action == "destroy":
            lines.append(f"  def destroy")
            lines.append(f"    @{model_name}.destroy")
            lines.append(f"    redirect_to {resource_name}_url, notice: \"{model_class}已删除\"")
            lines.append(f"  end")
        else:
            fail("E009", f"不支持的动作: {action}")
        lines.append("")
    
    # 添加 private 方法
    lines.append("  private")
    lines.append("")
    lines.append(f"  def set_{model_name}")
    lines.append(f"    @{model_name} = {model_class}.find(params[:id])")
    lines.append(f"  end")
    lines.append("")
    lines.append(f"  def {model_name}_params")
    lines.append(f"    params.require(:{model_name}).permit(:title, :content)")
    lines.append(f"  end")
    lines.append("end")
    
    code = "\n".join(lines)
    
    return Snippet(
        key=f"generated_{resource_name}_controller",
        title=f"生成的 {model_class} 控制器",
        category="controller",
        tags=["生成", "控制器", "RESTful"],
        code=code,
        description=f"根据用户输入动态生成的 {model_class} 控制器片段",
    )


def generate_route(
    resource_name: str,
    nested_resources: Optional[List[str]] = None,
) -> Snippet:
    """
    根据用户输入动态生成 Rails 路由片段。
    
    Args:
        resource_name: 资源名称（如 "posts"）
        nested_resources: 嵌套资源列表（如 ["comments"]）
    
    Returns:
        生成的 Snippet 对象
    """
    if not resource_name or not resource_name.strip():
        fail("E009", "资源名称不能为空")
    
    resource_name = resource_name.strip().lower()
    if not re.match(r'^[a-z][a-z0-9_]*$', resource_name):
        fail("E009", f"资源名称 '{resource_name}' 格式不正确，应为小写蛇形命名")
    
    nested_resources = nested_res
