#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
eycap — Engine Yard 平台 Capistrano 部署配方工作台
==================================================
提供部署配方的生成、校验与解释功能（纯离线实现，不访问网络）。

仅依据功能规格独立实现（clean-room），所有核心逻辑均包含在
本文件中，可通过 `--selftest` 进行内置样例自检。

错误码说明：
    E001: 未知/不支持的命令行参数
    E002: 应用类型不支持（非 rails/node/static）
    E003: 配方内容为空或不是字符串
    E004: 配方语法错误（任务定义不完整）
    E005: 任务依赖缺失（引用了未定义的任务）
    E006: 变量引用未定义
    E007: 角色类型无效（非 app/util/db）
    E008: 生成配方时参数缺失
    E009: 解释配方时输入格式错误
    E010: 内部逻辑错误（不应发生）
"""

import sys
import re
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------

# 支持的应用类型
SUPPORTED_APP_TYPES = ("rails", "node", "static")

# 支持的角色类型
SUPPORTED_ROLES = ("app", "util", "db")

# 各应用类型的默认任务模板
TASK_TEMPLATES = {
    "rails": [
        "checkout",
        "bundle_install",
        "db_migrate",
        "assets_precompile",
        "restart",
    ],
    "node": [
        "checkout",
        "npm_install",
        "build",
        "restart",
    ],
    "static": [
        "checkout",
        "build",
        "deploy_static",
    ],
}

# 各角色的默认说明
ROLE_DESCRIPTIONS = {
    "app": "应用服务器（运行主应用进程）",
    "util": "工具服务器（运行辅助任务，如 cron、队列）",
    "db": "数据库服务器（运行数据库服务）",
}

# 各任务的自然语言解释模板
TASK_EXPLANATIONS = {
    "checkout": "从版本仓库检出最新代码到发布目录",
    "bundle_install": "安装 Ruby 依赖（bundle install）",
    "db_migrate": "执行数据库迁移（db:migrate）",
    "assets_precompile": "预编译静态资源（assets:precompile）",
    "restart": "重启应用进程",
    "npm_install": "安装 Node.js 依赖（npm install）",
    "build": "执行构建步骤（编译/打包）",
    "deploy_static": "将构建产物同步到 Web 根目录",
}


# ---------------------------------------------------------------------------
# 核心数据结构
# ---------------------------------------------------------------------------

class Recipe:
    """部署配方对象。"""

    def __init__(self, app_type: str, roles: List[str], tasks: List[str]):
        self.app_type = app_type
        self.roles = roles
        self.tasks = tasks

    def to_capistrano_script(self) -> str:
        """将配方对象序列化为 Capistrano 风格的 Ruby 脚本。"""
        lines = []
        lines.append("# 由 eycap 生成的 Capistrano 部署配方")
        lines.append("# 应用类型: %s" % self.app_type)
        lines.append("")
        lines.append("set :application, 'my_app'")
        lines.append("set :repo_url, 'git@example.com:my_app.git'")
        lines.append("")
        lines.append("# 角色定义")
        for role in self.roles:
            if role not in SUPPORTED_ROLES:
                raise ValueError("E007: 无效角色类型 '%s'" % role)
            lines.append("role :%s, ['%s.example.com']" % (role, role))
        lines.append("")
        lines.append("# 任务定义")
        for task in self.tasks:
            lines.append("desc '%s'" % TASK_EXPLANATIONS.get(task, task))
            lines.append("task :%s do" % task)
            lines.append("  # 此处填充 %s 的具体实现" % task)
            lines.append("end")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心功能函数
# ---------------------------------------------------------------------------

def generate_recipe(app_type: str, roles: List[str], custom_tasks: List[str] = None) -> str:
    """
    根据应用类型和角色生成部署配方脚本。

    参数:
        app_type: 应用类型（rails / node / static）
        roles: 角色列表（app / util / db）
        custom_tasks: 自定义任务列表（可选，追加到默认任务之后）

    返回:
        生成的 Capistrano 脚本字符串

    错误:
        E002: 应用类型不支持
        E007: 角色类型无效
        E008: 参数缺失
    """
    if not app_type or not roles:
        raise ValueError("E008: 生成配方时参数缺失")

    if app_type not in SUPPORTED_APP_TYPES:
        raise ValueError("E002: 不支持的应用类型 '%s'" % app_type)

    for role in roles:
        if role not in SUPPORTED_ROLES:
            raise ValueError("E007: 无效角色类型 '%s'" % role)

    # 合并默认任务与自定义任务
    tasks = list(TASK_TEMPLATES.get(app_type, []))
    if custom_tasks:
        tasks.extend(custom_tasks)

    recipe = Recipe(app_type=app_type, roles=roles, tasks=tasks)
    return recipe.to_capistrano_script()


def validate_recipe(script: str) -> List[Dict[str, str]]:
    """
    校验 Capistrano 配方脚本的语法、任务依赖和变量引用。

    参数:
        script: 配方脚本内容

    返回:
        校验报告列表，每个元素为 {'code': 错误码, 'message': 说明}

    错误:
        E003: 输入为空或不是字符串
        E004: 语法错误（任务定义不完整）
        E005: 任务依赖缺失
        E006: 变量引用未定义
    """
    if not script or not isinstance(script, str):
        raise ValueError("E003: 配方内容为空或不是字符串")

    report = []

    # --- 语法检查：提取所有 task 定义 ---
    task_pattern = re.compile(r"task\s+:(\w+)\s+do")
    end_pattern = re.compile(r"^\s*end\s*$")

    defined_tasks = []
    lines = script.splitlines()
    in_task = False
    current_task = None
    task_lines_count = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测任务开始
        m = task_pattern.search(line)
        if m and not in_task:
            in_task = True
            current_task = m.group(1)
            defined_tasks.append(current_task)
            task_lines_count = 0
            continue

        # 检测任务结束
        if in_task and end_pattern.match(stripped):
            # 任务体必须至少有一行内容
            if task_lines_count < 1:
                report.append({
                    "code": "E004",
                    "message": "任务 :%s 定义不完整（缺少任务体）" % current_task
                })
            in_task = False
            current_task = None
            continue

        # 统计任务体行数
        if in_task:
            task_lines_count += 1

    # 如果脚本在任务中间结束，说明语法不完整
    if in_task:
        report.append({
            "code": "E004",
            "message": "任务 :%s 缺少 end 关键字" % current_task
        })

    # 如果没有定义任何任务，视为语法错误
    if not defined_tasks:
        report.append({
            "code": "E004",
            "message": "配方中未定义任何任务"
        })

    # --- 任务依赖检查：查找 invoke / after / before 引用 ---
    invoke_pattern = re.compile(r"(?:invoke|after|before)\s+['\"]:?(\w+)['\"]")
    for i, line in enumerate(lines):
        for m in invoke_pattern.finditer(line):
            ref_task = m.group(1)
            if ref_task not in defined_tasks and ref_task not in ("deploy", "deploy:starting", "deploy:updating", "deploy:publishing", "deploy:finishing"):
                report.append({
                    "code": "E005",
                    "message": "第 %d 行引用了未定义的任务 ':%s'" % (i + 1, ref_task)
                })

    # --- 变量引用检查 ---
    var_pattern = re.compile(r"fetch\s*\(?\s*:(\w+)")
    defined_vars = set()
    # 收集 set 定义的变量
    set_pattern = re.compile(r"set\s+[:\[](\w+)")
    for line in lines:
        m = set_pattern.search(line)
        if m:
            defined_vars.add(m.group(1))

    # 检查 fetch 引用
    for i, line in enumerate(lines):
        for m in var_pattern.finditer(line):
            var_name = m.group(1)
            if var_name not in defined_vars and var_name not in ("application", "repo_url", "deploy_to", "branch"):
                report.append({
                    "code": "E006",
                    "message": "第 %d 行引用了未定义的变量 ':%s'" % (i + 1, var_name)
                })

    return report


def explain_recipe(script: str) -> List[str]:
    """
    将 Capistrano 配方脚本解释为自然语言步骤说明。

    参数:
        script: 配方脚本内容

    返回:
        步骤说明列表

    错误:
        E003: 输入为空或不是字符串
        E009: 无法解析的配方格式
    """
    if not script or not isinstance(script, str):
        raise ValueError("E003: 配方内容为空或不是字符串")

    if "task" not in script:
        raise ValueError("E009: 配方格式错误（未找到任务定义）")

    steps = []
    task_pattern = re.compile(r"task\s+:(\w+)\s+do")

    for line in script.splitlines():
        m = task_pattern.search(line)
        if m:
            task_name = m.group(1)
            explanation = TASK_EXPLANATIONS.get(task_name, "执行自定义任务 %s" % task_name)
            steps.append("步骤: %s" % explanation)

    # 添加角色信息
    role_pattern = re.compile(r"role\s+:(\w+)")
    for line in script.splitlines():
        m = role_pattern.search(line)
        if m:
            role = m.group(1)
            desc = ROLE_DESCRIPTIONS.get(role, "未知角色")
            steps.append("角色: %s（%s）" % (role, desc))

    if not steps:
        raise ValueError("E009: 无法从配方中提取有效信息")

    return steps


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。使用内置硬编码样例数据，不依赖外部文件。

    返回:
        0 表示全部通过，非 0 表示有失败项
    """
    print("[eycap] 开始自检...")
    failures = 0

    # --- 测试 1: 配方生成 ---
    print("[eycap] 测试 1: 配方生成")
    try:
        script = generate_recipe("rails", ["app", "db"])
        assert "task :checkout" in script, "生成的配方缺少 checkout 任务"
        assert "role :app" in script, "生成的配方缺少 app 角色"
        assert "role :db" in script, "生成的配方缺少 db 角色"
        assert len(script.splitlines()) > 10, "生成的配方行数过少"
        print("[eycap]   通过")
    except Exception as e:
        failures += 1
        print("[eycap]   失败: %s" % e)

    # --- 测试 2: 配方校验（正确配方） ---
    print("[eycap] 测试 2: 配方校验（正确配方）")
    try:
        valid_script = """
set :application, 'demo'
set :repo_url, 'git@example.com:demo.git'

role :app, ['app.example.com']

desc '检出代码'
task :checkout do
  # 检出代码
end

desc '安装依赖'
task :bundle_install do
  # 安装依赖
end

desc '重启应用'
task :restart do
  # 重启
end
"""
        report = validate_recipe(valid_script)
        # 允许少量警告，但不能有致命错误
        fatal_codes = {"E004", "E005", "E006"}
        fatal_errors = [r for r in report if r["code"] in fatal_codes]
        assert len(fatal_errors) == 0, "正确配方被误报: %s" % fatal_errors
        print("[eycap]   通过")
    except Exception as e:
        failures += 1
        print("[eycap]   失败: %s" % e)

    # --- 测试 3: 配方校验（错误配方） ---
    print("[eycap] 测试 3: 配方校验（错误配方）")
    try:
        invalid_script = """
set :application, 'demo'

role :app, ['app.example.com']

desc '不完整任务'
task :broken do
  # 缺少 end
"""
        report = validate_recipe(invalid_script)
        codes = [r["code"] for r in report]
        assert "E004" in codes, "未检测到语法错误"
        print("[eycap]   通过")
    except Exception as e:
        failures += 1
        print("[eycap]   失败: %s" % e)

    # --- 测试 4: 配方解释 ---
    print("[eycap] 测试 4: 配方解释")
    try:
        explain_script = """
role :app, ['app.example.com']
role :db, ['db.example.com']

task :checkout do
end

task :restart do
end
"""
        steps = explain_recipe(explain_script)
        assert len(steps) >= 3, "解释步骤数量过少"
        assert any("检出" in s for s in steps), "缺少检出步骤说明"
        assert any("重启" in s for s in steps), "缺少重启步骤说明"
        print("[eycap]   通过")
    except Exception as e:
        failures += 1
        print("[eycap]   失败: %s" % e)

    # --- 测试 5: 错误处理 ---
    print("[eycap] 测试 5: 错误处理")
    try:
        # 不支持的 app_type
        try:
            generate_recipe("php", ["app"])
            failures += 1
            print("[eycap]   失败: 未捕获 E002")
        except ValueError as e:
            assert "E002" in str(e), "错误码不正确: %s" % e

        # 空配方校验
        try:
            validate_recipe("")
            failures += 1
            print("[eycap]   失败: 未捕获 E003")
        except ValueError as e:
            assert "E003" in str(e), "错误码不正确: %s" % e

        print("[eycap]   通过")
    except Exception as e:
        failures += 1
        print("[eycap]   失败: %s" % e)

    # --- 汇总 ---
    if failures == 0:
        print("[eycap] 全部自检通过 ✓")
        return 0
    else:
        print("[eycap] 自检失败: %d 项未通过 ✗" % failures)
        return 1


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    args = sys.argv[1:]

    # 自检模式
    if "--selftest" in args:
        return run_selftest()

    # 无参数时显示帮助
    if not args:
        print("eycap — Engine Yard Capistrano 部署配方工作台")
        print("用法:")
        print("  python main.py --selftest           # 运行离线自检")
        print("  python main.py generate --type rails --roles app,db")
        print("  python main.py validate --file deploy.rb")
        print("  python main.py explain --file deploy.rb")
        return 0

    # 解析子命令
    command = args[0]

    if command == "generate":
        # 解析参数
        app_type = None
        roles = []
        for i in range(1, len(args)):
            if args[i] == "--type" and i + 1 < len(args):
                app_type = args[i + 1]
            elif args[i] == "--roles" and i + 1 < len(args):
                roles = [r.strip() for r in args[i + 1].split(",") if r.strip()]

        try:
            script = generate_recipe(app_type or "rails", roles or ["app"])
            print(script)
            return 0
        except ValueError as e:
            print("错误: %s" % e, file=sys.stderr)
            return 1

    elif command == "validate":
        # 校验模式需要读取文件
        file_path = None
        for i in range(1, len(args)):
            if args[i] == "--file" and i + 1 < len(args):
                file_path = args[i + 1]

        if not file_path:
            print("错误: E008 缺少 --file 参数", file=sys.stderr)
            return 1

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            report = validate_recipe(content)
            if not report:
                print("校验通过：配方语法正确，无依赖或变量错误")
                return 0
            else:
                print("校验结果（%d 项）:" % len(report))
                for item in report:
                    print("  [%s] %s" % (item["code"], item["message"]))
                return 2
        except FileNotFoundError:
            print("错误: 文件不存在: %s" % file_path, file=sys.stderr)
            return 1
        except ValueError as e:
            print("错误: %s" % e, file=sys.stderr)
            return 1

    elif command == "explain":
        # 解释模式需要读取文件
        file_path = None
        for i in range(1, len(args)):
            if args[i] == "--file" and i + 1 < len(args):
                file_path = args[i + 1]

        if not file_path:
            print("错误: E008 缺少 --file 参数", file=sys.stderr)
            return 1

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            steps = explain_recipe(content)
            print("部署步骤说明:")
            for step in steps:
                print("  - %s" % step)
            return 0
        except FileNotFoundError:
            print("错误: 文件不存在: %s" % file_path, file=sys.stderr)
            return 1
        except ValueError as e:
            print("错误: %s" % e, file=sys.stderr)
            return 1

    else:
        print("错误: E001 未知命令 '%s'" % command, file=sys.stderr)
        print("可用命令: generate, validate, explain, --selftest", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
