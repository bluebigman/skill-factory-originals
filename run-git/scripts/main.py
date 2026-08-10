#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run-git 技能实现脚本（clean-room 独立实现）

本脚本依据功能规格文档，提供 Git 日常操作的结构化处理流程与规范输出。
仅提供指令与流程，不直接执行任何 Git 命令。
"""

import argparse
import sys
import re
from typing import Dict, List, Optional, Tuple


# ============================================================
# 常量定义
# ============================================================

# 错误码定义（E001-E010）
ERROR_CODES = {
    "E001": "未知操作类型",
    "E002": "缺少必要参数",
    "E003": "参数格式不合法",
    "E004": "仓库状态信息不完整",
    "E005": "操作流程生成失败",
    "E006": "不支持的操作组合",
    "E007": "输入内容超出处理范围",
    "E008": "内部逻辑错误",
    "E009": "自检失败",
    "E010": "未识别的错误",
}

# 支持的操作类型
SUPPORTED_ACTIONS = [
    "commit",       # 提交
    "branch",       # 分支
    "merge",        # 合并
    "rebase",       # 变基
    "push",         # 推送
    "pull",         # 拉取
    "status",       # 状态
    "log",          # 日志
    "stash",        # 暂存
    "tag",          # 标签
    "reset",        # 回退
    "revert",       # 还原
    "cherry-pick",  # 拣选
    "fetch",        # 获取
    "diff",         # 差异
]

# 操作风险级别
RISK_LEVELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
}

# 缺失字段标记
MISSING_FIELD_MARK = "【缺失】"


# ============================================================
# 核心数据结构
# ============================================================

class GitOperationRequest:
    """Git 操作请求对象"""
    
    def __init__(self, action: str, params: Dict[str, str] = None):
        self.action = action
        self.params = params or {}
        self.required_fields = self._get_required_fields(action)
        self.missing_fields = self._check_missing_fields()
    
    def _get_required_fields(self, action: str) -> List[str]:
        """根据操作类型获取必填字段列表"""
        required_map = {
            "commit": ["message"],
            "branch": ["branch_name"],
            "merge": ["target_branch"],
            "rebase": ["target_branch"],
            "push": ["remote"],
            "pull": ["remote"],
            "reset": ["commit_hash"],
            "revert": ["commit_hash"],
            "cherry-pick": ["commit_hash"],
            "tag": ["tag_name"],
        }
        return required_map.get(action, [])
    
    def _check_missing_fields(self) -> List[str]:
        """检查缺失的必填字段"""
        missing = []
        for field in self.required_fields:
            value = self.params.get(field, "").strip()
            if not value or value == MISSING_FIELD_MARK:
                missing.append(field)
        return missing
    
    def is_complete(self) -> bool:
        """判断请求是否完整"""
        return len(self.missing_fields) == 0


class RepositoryStatus:
    """仓库状态信息"""
    
    def __init__(self, branch: str = "", is_clean: bool = True, 
                 ahead_count: int = 0, behind_count: int = 0,
                 conflicted_files: List[str] = None):
        self.branch = branch
        self.is_clean = is_clean
        self.ahead_count = ahead_count
        self.behind_count = behind_count
        self.conflicted_files = conflicted_files or []
    
    def has_conflicts(self) -> bool:
        """是否存在冲突"""
        return len(self.conflicted_files) > 0


# ============================================================
# 核心处理逻辑
# ============================================================

class GitSkillProcessor:
    """Git 技能核心处理器"""
    
    def __init__(self):
        self.action_templates = self._init_action_templates()
    
    def _init_action_templates(self) -> Dict[str, Dict]:
        """初始化操作模板库"""
        templates = {
            "commit": {
                "description": "提交代码变更",
                "risk": "low",
                "steps": [
                    "git status  # 查看当前工作区状态",
                    "git add <files>  # 添加需要提交的文件",
                    "git commit -m \"<commit_message>\"  # 提交变更",
                ],
                "tips": "建议提交信息遵循 Conventional Commits 规范（如 feat: xxx, fix: xxx）",
            },
            "branch": {
                "description": "创建或切换分支",
                "risk": "low",
                "steps": [
                    "git branch <branch_name>  # 创建新分支",
                    "git checkout <branch_name>  # 切换到新分支",
                ],
                "tips": "分支命名建议：feature/xxx, bugfix/xxx, hotfix/xxx",
            },
            "merge": {
                "description": "合并分支",
                "risk": "medium",
                "steps": [
                    "git checkout <current_branch>  # 切换到目标分支",
                    "git merge <target_branch>  # 合并指定分支",
                    "git status  # 检查合并结果",
                ],
                "tips": "合并前建议先 pull 最新代码，合并冲突需手动解决",
            },
            "rebase": {
                "description": "变基操作",
                "risk": "high",
                "steps": [
                    "git checkout <current_branch>  # 切换到当前分支",
                    "git rebase <target_branch>  # 变基到目标分支",
                ],
                "tips": "⚠️ 变基会重写提交历史，禁止在公共分支上执行",
            },
            "push": {
                "description": "推送代码到远程仓库",
                "risk": "medium",
                "steps": [
                    "git push <remote> <branch>  # 推送当前分支",
                ],
                "tips": "推送前建议先 pull 最新代码，避免冲突",
            },
            "pull": {
                "description": "拉取远程代码",
                "risk": "low",
                "steps": [
                    "git pull <remote> <branch>  # 拉取并合并远程变更",
                ],
                "tips": "建议使用 --rebase 参数保持提交历史整洁",
            },
            "status": {
                "description": "查看仓库状态",
                "risk": "low",
                "steps": [
                    "git status  # 查看工作区状态",
                    "git branch -a  # 查看所有分支",
                ],
                "tips": "定期查看状态有助于及时发现未提交的变更",
            },
            "log": {
                "description": "查看提交日志",
                "risk": "low",
                "steps": [
                    "git log --oneline --graph --all  # 查看图形化日志",
                ],
                "tips": "可使用 --author, --since 等参数过滤日志",
            },
            "stash": {
                "description": "暂存工作区变更",
                "risk": "low",
                "steps": [
                    "git stash  # 暂存当前变更",
                    "git stash list  # 查看暂存列表",
                    "git stash pop  # 恢复最近一次暂存",
                ],
                "tips": "适合需要临时切换分支但不想提交的场景",
            },
            "tag": {
                "description": "创建标签",
                "risk": "low",
                "steps": [
                    "git tag <tag_name>  # 创建轻量标签",
                    "git tag -a <tag_name> -m \"<message>\"  # 创建附注标签",
                ],
                "tips": "标签常用于版本发布标记",
            },
            "reset": {
                "description": "回退提交",
                "risk": "high",
                "steps": [
                    "git reset --soft <commit_hash>  # 软回退，保留变更",
                    "git reset --mixed <commit_hash>  # 混合回退（默认）",
                    "git reset --hard <commit_hash>  # 硬回退，丢弃变更",
                ],
                "tips": "⚠️ --hard 回退会丢失变更，请谨慎使用",
            },
            "revert": {
                "description": "还原提交",
                "risk": "medium",
                "steps": [
                    "git revert <commit_hash>  # 生成反向提交",
                ],
                "tips": "revert 不会删除历史，比 reset 更安全",
            },
            "cherry-pick": {
                "description": "拣选提交",
                "risk": "medium",
                "steps": [
                    "git cherry-pick <commit_hash>  # 将指定提交应用到当前分支",
                ],
                "tips": "适合将特定修复从一个分支移植到另一个分支",
            },
            "fetch": {
                "description": "获取远程变更",
                "risk": "low",
                "steps": [
                    "git fetch <remote>  # 获取远程变更但不合并",
                ],
                "tips": "fetch 后可以查看远程分支状态，再决定合并策略",
            },
            "diff": {
                "description": "查看差异",
                "risk": "low",
                "steps": [
                    "git diff  # 查看工作区变更",
                    "git diff --cached  # 查看暂存区变更",
                    "git diff <commit1> <commit2>  # 查看提交间差异",
                ],
                "tips": "可使用 --stat 参数查看变更统计",
            },
        }
        return templates
    
    def process_request(self, request: GitOperationRequest) -> Dict:
        """处理用户请求，生成操作流程"""
        # 检查操作类型是否支持
        if request.action not in SUPPORTED_ACTIONS:
            return self._build_error_response("E001", f"不支持的操作类型: {request.action}")
        
        # 检查必填字段
        if not request.is_complete():
            missing_msg = ", ".join(request.missing_fields)
            return self._build_error_response("E002", f"缺少必要参数: {missing_msg}")
        
        # 生成操作流程
        try:
            template = self.action_templates[request.action]
            steps = self._fill_template_steps(template["steps"], request.params)
            
            response = {
                "success": True,
                "action": request.action,
                "description": template["description"],
                "risk_level": template["risk"],
                "risk_label": RISK_LEVELS.get(template["risk"], "未知"),
                "steps": steps,
                "tips": template["tips"],
                "confirmation": self._generate_confirmation_checklist(request.action),
            }
            return response
        except Exception as e:
            return self._build_error_response("E005", f"操作流程生成失败: {str(e)}")
    
    def _fill_template_steps(self, steps: List[str], params: Dict[str, str]) -> List[str]:
        """填充模板步骤中的参数"""
        filled_steps = []
        for step in steps:
            filled = step
            # 替换常见占位符
            replacements = {
                "<commit_message>": params.get("message", ""),
                "<branch_name>": params.get("branch_name", ""),
                "<target_branch>": params.get("target_branch", ""),
                "<current_branch>": params.get("current_branch", "当前分支"),
                "<commit_hash>": params.get("commit_hash", ""),
                "<remote>": params.get("remote", "origin"),
                "<tag_name>": params.get("tag_name", ""),
                "<files>": params.get("files", "."),
            }
            for placeholder, value in replacements.items():
                filled = filled.replace(placeholder, value)
            filled_steps.append(filled)
        return filled_steps
    
    def _generate_confirmation_checklist(self, action: str) -> List[str]:
        """生成操作后的确认清单"""
        common_checks = [
            "检查命令执行结果是否正常",
            "确认变更是否符合预期",
        ]
        
        action_checks = {
            "commit": ["确认提交信息准确无误", "确认提交的文件列表正确"],
            "push": ["确认推送成功且无错误", "确认远程分支状态正确"],
            "merge": ["确认无未解决的冲突", "确认合并结果正确"],
            "rebase": ["确认提交历史符合预期", "确认无冲突残留"],
            "reset": ["确认回退结果正确", "确认重要变更已备份"],
            "revert": ["确认还原提交生成正确"],
            "stash": ["确认暂存内容完整", "确认工作区状态正常"],
        }
        
        checklist = common_checks + action_checks.get(action, [])
        return checklist
    
    def analyze_repository_status(self, status_text: str) -> RepositoryStatus:
        """分析仓库状态文本，提取关键信息"""
        try:
            # 提取当前分支
            branch_match = re.search(r"On branch\s+(\S+)", status_text)
            branch = branch_match.group(1) if branch_match else ""
            
            # 检查是否有未提交的变更
            has_changes = bool(re.search(r"Changes not staged|Changes to be committed|Untracked files", status_text))
            
            # 检查是否有冲突
            conflict_files = re.findall(r"both modified:\s+(\S+)", status_text)
            
            # 检查领先/落后计数
            ahead_match = re.search(r"ahead of '.*?' by (\d+) commit", status_text)
            behind_match = re.search(r"behind '.*?' by (\d+) commit", status_text)
            ahead = int(ahead_match.group(1)) if ahead_match else 0
            behind = int(behind_match.group(1)) if behind_match else 0
            
            return RepositoryStatus(
                branch=branch,
                is_clean=not has_changes,
                ahead_count=ahead,
                behind_count=behind,
                conflicted_files=conflict_files,
            )
        except Exception as e:
            raise ValueError(f"仓库状态解析失败: {str(e)}")
    
    def generate_troubleshooting(self, error_text: str) -> List[Dict]:
        """根据错误文本生成排查建议"""
        suggestions = []
        
        # 权限错误
        if "permission denied" in error_text.lower() or "403" in error_text:
            suggestions.append({
                "error_type": "权限错误",
                "suggestion": "检查 SSH 密钥或访问令牌配置，确认有仓库访问权限",
                "commands": ["ssh -T git@github.com", "git config --list"],
            })
        
        # 认证错误
        if "authentication failed" in error_text.lower() or "401" in error_text:
            suggestions.append({
                "error_type": "认证失败",
                "suggestion": "确认凭据正确，可尝试更新凭据缓存",
                "commands": ["git credential-manager", "git config --global credential.helper"],
            })
        
        # 冲突错误
        if "conflict" in error_text.lower() or "merge failed" in error_text.lower():
            suggestions.append({
                "error_type": "合并冲突",
                "suggestion": "手动解决冲突文件，然后执行 git add 和 git commit",
                "commands": ["git status", "git diff", "git mergetool"],
            })
        
        # 找不到文件/路径
        if "does not have any commits" in error_text.lower():
            suggestions.append({
                "error_type": "空仓库",
                "suggestion": "仓库还没有提交，先创建初始提交",
                "commands": ["git add .", "git commit -m \"initial commit\""],
            })
        
        # 分支不存在
        if "no such branch" in error_text.lower() or "not a valid branch" in error_text.lower():
            suggestions.append({
                "error_type": "分支不存在",
                "suggestion": "检查分支名称拼写，确认分支是否已创建",
                "commands": ["git branch -a", "git fetch --all"],
            })
        
        # 通用建议
        if not suggestions:
            suggestions.append({
                "error_type": "未知错误",
                "suggestion": "请提供更详细的错误信息，或尝试以下通用排查步骤",
                "commands": ["git status", "git log --oneline -5"],
            })
        
        return suggestions
    
    def _build_error_response(self, code: str, message: str) -> Dict:
        """构建错误响应"""
        return {
            "success": False,
            "error_code": code,
            "error_message": message,
        }
    
    def validate_params(self, action: str, params: Dict[str, str]) -> Tuple[bool, str]:
        """验证参数格式"""
        # 验证分支名称格式
        if "branch_name" in params and params["branch_name"]:
            if not re.match(r"^[a-zA-Z0-9_\-\./]+$", params["branch_name"]):
                return False, "分支名称包含非法字符"
        
        # 验证提交哈希格式
        if "commit_hash" in params and params["commit_hash"]:
            if not re.match(r"^[a-f0-9]{7,40}$", params["commit_hash"].lower()):
                return False, "提交哈希格式不正确"
        
        # 验证远程名称
        if "remote" in params and params["remote"]:
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", params["remote"]):
                return False, "远程仓库名称包含非法字符"
        
        return True, ""


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> bool:
    """运行内置自检，验证核心逻辑"""
    print("=" * 60)
    print("run-git 技能自检开始")
    print("=" * 60)
    
    processor = GitSkillProcessor()
    all_passed = True
    
    # 测试1: 基本操作流程生成
    print("\n[测试1] 基本操作流程生成")
    try:
        request = GitOperationRequest("commit", {"message": "feat: 添加新功能"})
        response = processor.process_request(request)
        assert response["success"] is True, "提交操作应成功"
        assert len(response["steps"]) > 0, "应生成操作步骤"
        assert response["risk_level"] in ["low", "medium", "high"], "风险级别应合法"
        print(f"  ✅ 提交操作流程生成成功，步骤数: {len(response['steps'])}")
    except AssertionError as e:
        print(f"  ❌ 提交操作失败: {str(e)}")
        all_passed = False
    
    # 测试2: 缺少必填参数
    print("\n[测试2] 缺少必填参数检测")
    try:
        request = GitOperationRequest("commit", {})
        response = processor.process_request(request)
        assert response["success"] is False, "缺少参数应返回错误"
        assert response["error_code"] == "E002", "错误码应为 E002"
        print(f"  ✅ 缺失参数检测正确: {response['error_message']}")
    except AssertionError as e:
        print(f"  ❌ 缺失参数检测失败: {str(e)}")
        all_passed = False
    
    # 测试3: 不支持的操作类型
    print("\n[测试3] 不支持的操作类型")
    try:
        request = GitOperationRequest("unknown_op", {})
        response = processor.process_request(request)
        assert response["success"] is False, "未知操作应返回错误"
        assert response["error_code"] == "E001", "错误码应为 E001"
        print(f"  ✅ 未知操作检测正确: {response['error_message']}")
    except AssertionError as e:
        print(f"  ❌ 未知操作检测失败: {str(e)}")
        all_passed = False
    
    # 测试4: 仓库状态分析
    print("\n[测试4] 仓库状态文本分析")
    try:
        sample_status = """On branch main
Your branch is ahead of 'origin/main' by 2 commits.
  (use "git push" to publish your local commits)

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
\tmodified:   src/app.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
\ttests/test_new.py

no changes added to commit (use "git add" and/or "git commit -a")"""
        
        status = processor.analyze_repository_status(sample_status)
        assert status.branch == "main", "分支名应正确解析"
        assert status.is_clean is False, "应检测到未提交变更"
        assert status.ahead_count > 0, "应检测到领先提交数"
        print(f"  ✅ 仓库状态解析成功: 分支={status.branch}, 领先={status.ahead_count}, 干净={status.is_clean}")
    except AssertionError as e:
        print(f"  ❌ 仓库状态解析失败: {str(e)}")
        all_passed = False
    
    # 测试5: 冲突检测
    print("\n[测试5] 冲突检测")
    try:
        sample_conflict = """On branch feature
You have unmerged paths.
  (fix conflicts and run "git commit")
  (use "git merge --abort" to abort the merge)

Unmerged paths:
  (use "git add <file>..." to mark resolution)
\tboth modified:   src/config.py
\tboth modified:   src/utils.py"""
        
        status = processor.analyze_repository_status(sample_conflict)
        assert status.has_conflicts() is True, "应检测到冲突"
        assert len(status.conflicted_files) > 0, "应提取冲突文件列表"
        print(f"  ✅ 冲突检测成功: 冲突文件数={len(status.conflicted_files)}")
    except AssertionError as e:
        print(f"  ❌ 冲突检测失败: {str(e)}")
        all_passed = False
    
    # 测试6: 错误排查建议
    print("\n[测试6] 错误排查建议生成")
    try:
        error_text = "fatal: Authentication failed for 'https://github.com/user/repo.git'"
        suggestions = processor.generate_troubleshooting(error_text)
        assert len(suggestions) > 0, "应生成排查建议"
        assert any("认证" in s["error_type"] for s in suggestions), "应识别认证错误"
        print(f"  ✅ 错误排查建议生成成功: {len(suggestions)} 条建议")
    except AssertionError as e:
        print(f"  ❌ 错误排查建议生成失败: {str(e)}")
        all_passed = False
    
    # 测试7: 参数验证
    print("\n[测试7] 参数格式验证")
    try:
        valid, msg = processor.validate_params("branch", {"branch_name": "feature/test-1"})
        assert valid is True, "合法的分支名应通过验证"
        
        valid, msg = processor.validate_params("branch", {"branch_name": "bad branch!"})
        assert valid is False, "非法的分支名应被拒绝"
        print(f"  ✅ 参数验证功能正确")
    except AssertionError as e:
        print(f"  ❌ 参数验证失败: {str(e)}")
        all_passed = False
    
    # 测试8: 高风险操作标记
    print("\n[测试8] 高风险操作标记")
    try:
        request = GitOperationRequest("reset", {"commit_hash": "abc1234"})
        response = processor.process_request(request)
        assert response["success"] is True, "reset 操作应成功"
        assert response["risk_level"] == "high", "reset 应为高风险操作"
        print(f"  ✅ 高风险操作标记正确: {response['risk_label']}")
    except AssertionError as e:
        print(f"  ❌ 高风险操作标记失败: {str(e)}")
        all_passed = False
    
    # 测试9: 确认清单生成
    print("\n[测试9] 确认清单生成")
    try:
        request = GitOperationRequest("push", {"remote": "origin"})
        response = processor.process_request(request)
        assert len(response["confirmation"]) > 0, "应生成确认清单"
        print(f"  ✅ 确认清单生成成功: {len(response['confirmation'])} 项")
    except AssertionError as e:
        print(f"  ❌ 确认清单生成失败: {str(e)}")
        all_passed = False
    
    # 测试10: 完整操作流程（多步骤）
    print("\n[测试10] 完整操作流程")
    try:
        request = GitOperationRequest("merge", {
            "target_branch": "feature/new-feature",
            "current_branch": "main",
        })
        response = processor.process_request(request)
        assert response["success"] is True, "merge 操作应成功"
        assert len(response["steps"]) >= 2, "merge 应生成多个步骤"
        print(f"  ✅ 完整操作流程生成成功")
        for i, step in enumerate(response["steps"], 1):
            print(f"    步骤{i}: {step}")
    except AssertionError as e:
        print(f"  ❌ 完整操作流程失败: {str(e)}")
        all_passed = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有自检测试通过！")
    else:
        print("❌ 部分自检测试失败！")
    print("=" * 60)
    
    return all_passed


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="run-git 技能实现 - Git 操作流程生成与指导",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --action commit --message "feat: 添加新功能"
  python main.py --action merge --target-branch feature/xxx
  python main.py --selftest
        """,
    )
    
    parser.add_argument(
        "--action",
        choices=SUPPORTED_ACTIONS,
        help="Git 操作类型",
    )
    parser.add_argument(
        "--message",
        help="提交信息（用于 commit）",
    )
    parser.add_argument(
        "--branch-name",
        help="分支名称（用于 branch）",
    )
    parser.add_argument(
        "--target-branch",
        help="目标分支（用于 merge/rebase）",
    )
    parser.add_argument(
        "--current-branch",
        help="当前分支",
    )
    parser.add_argument(
        "--commit-hash",
        help="提交哈希（用于 reset/revert/cherry-pick）",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="远程仓库名称（默认: origin）",
    )
    parser.add_argument(
        "--tag-name",
        help="标签名称（用于 tag）",
    )
    parser.add_argument(
        "--files",
        help="文件列表（用于 commit）",
    )
    parser.add_argument(
        "--status-text",
        help="仓库状态文本（用于分析）",
    )
    parser.add_argument(
        "--error-text",
        help="错误文本（用于生成排查建议）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检",
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 创建处理器
    processor = GitSkillProcessor()
    
    # 状态文本分析模式
    if args.status_text:
        try:
            status = processor.analyze_repository_status(args.status_text)
            print(f"当前分支: {status.branch or '未知'}")
            print(f"工作区状态: {'干净' if status.is_clean else '有未提交变更'}")
            print(f"领先远程: {status.ahead_count} 个提交")
            print(f"落后远程: {status.behind_count} 个提交")
            if status.has_conflicts():
                print(f"冲突文件: {', '.join(status.conflicted_files)}")
            return
        except ValueError as e:
            print(f"错误: {str(e)}")
            sys.exit(1)
    
    # 错误排查模式
    if args.error_text:
        suggestions = processor.generate_troubleshooting(args.error_text)
        print("错误排查建议:")
        for i, s in enumerate(suggestions, 1):
            print(f"\n{i}. 错误类型: {s['error_type']}")
            print(f"   建议: {s['suggestion']}")
            print(f"   命令: {', '.join(s['commands'])}")
        return
    
    # 操作流程生成模式
    if not args.action:
        parser.print_help()
        sys.exit(0)
    
    # 构建参数
    params = {}
    if args.message:
        params["message"] = args.message
    if args.branch_name:
        params["branch_name"] = args.branch_name
    if args.target_branch:
        params["target_branch"] = args.target_branch
    if args.current_branch:
        params["current_branch"] = args.current_branch
    if args.commit_hash:
        params["commit_hash"] = args.commit_hash
    if args.remote:
        params["remote"] = args.remote
    if args.tag_name:
        params["tag_name"] = args.tag_name
    if args.files:
        params["files"] = args.files
    
    # 验证参数
    valid, msg = processor.validate_params(args.action, params)
    if not valid:
        print(f"错误 (E003): {msg}")
        sys.exit(1)
    
    # 处理请求
    request = GitOperationRequest(args.action, params)
    response = processor.process_request(request)
    
    # 输出结果
    if response["success"]:
        print(f"操作: {response['description']}")
        print(f"风险等级: {response['risk_label']}")
        print("\n执行步骤:")
        for i, step in enumerate(response["steps"], 1):
            print(f"  {i}. {step}")
        print(f"\n提示: {response['tips']}")
        print("\n确认清单:")
        for i, check in enumerate(response["confirmation"], 1):
            print(f"  ☐ {check}")
    else:
        print(f"错误 ({response['error_code']}): {response['error_message']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
