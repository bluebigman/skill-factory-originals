#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
capsize — EC2 部署与运维自动化 Skill 实现脚本
=============================================
功能：
  1. 部署配置解析：将用户提供的部署配置、服务器清单、环境变量等转换为结构化部署方案
  2. 关键信息提取：从部署脚本、SSH 配置、环境描述中识别主机、路径、角色、密钥等关键参数
  3. 命令生成：根据 Capistrano 约定生成可执行的部署命令序列
  4. 置信度标注：对推断出的配置项标注可信程度，不确定时明确提示
  5. 批量处理：支持多服务器、多环境（staging/production）的批量部署方案生成

仅生成方案与命令，不执行真实部署操作。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 错误码定义
# E001: 参数解析错误
# E002: 配置格式错误
# E003: 配置内容不完整
# E004: 环境名称无效
# E005: 服务器信息无效
# E006: 命令生成失败
# E007: 自检失败
# E008: 数据序列化失败
# E009: 输入为空
# E010: 未知错误
# ============================================================

# ------------------------------------------------------------
# 数据结构定义
# ------------------------------------------------------------

@dataclass
class ServerInfo:
    """服务器信息"""
    host: str
    user: str = "ubuntu"
    roles: List[str] = field(default_factory=list)
    port: int = 22
    ssh_key: Optional[str] = None
    deploy_to: Optional[str] = None
    confidence: float = 1.0  # 置信度 0.0-1.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class DeployConfig:
    """部署配置"""
    application: str
    environment: str
    servers: List[ServerInfo] = field(default_factory=list)
    repository: Optional[str] = None
    branch: str = "main"
    deploy_to: str = "/var/www/app"
    keep_releases: int = 5
    linked_files: List[str] = field(default_factory=list)
    linked_dirs: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    custom_tasks: List[str] = field(default_factory=list)
    confidence: float = 1.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ------------------------------------------------------------
# 核心逻辑模块
# ------------------------------------------------------------

class ConfigParser:
    """部署配置解析器"""

    # 常见角色关键词映射
    ROLE_KEYWORDS = {
        "app": ["app", "application", "web", "前端"],
        "db": ["db", "database", "数据库"],
        "web": ["web", "nginx", "apache", "http"],
        "worker": ["worker", "queue", "job", "异步"],
        "cache": ["cache", "redis", "memcached"],
    }

    # 常见路径关键词
    PATH_KEYWORDS = {
        "deploy_to": ["deploy_to", "deploy path", "部署路径", "发布目录"],
        "repo": ["repo", "repository", "仓库", "代码库"],
    }

    # 服务器信息正则
    SERVER_PATTERN = re.compile(
        r"(?:ec2-[\w-]+\.compute\.amazonaws\.com|[\w.-]+\.\w{2,})"
    )

    # SSH 配置样式识别
    SSH_KEY_PATTERN = re.compile(r"(?:ssh|key|密钥)[-_ ]?(?:path|file|位置|路径)?[:：]\s*([\/\w.\-]+\.pem|\/[\w\/.\-]+)")
    USER_PATTERN = re.compile(r"(?:user|用户)[:：]\s*(\w+)")
    PORT_PATTERN = re.compile(r"(?:port|端口)[:：]\s*(\d+)")
    DEPLOY_PATH_PATTERN = re.compile(r"(?:deploy_to|deploy path|部署路径)[:：]\s*([\/\w.\-]+)")
    BRANCH_PATTERN = re.compile(r"(?:branch|分支)[:：]\s*([\w.\-\/]+)")
    REPO_PATTERN = re.compile(r"(?:repo|repository|仓库)[:：]\s*([\w:\/\.@\-]+\.git|[\w:\/\.@\-]+)")

    # 链接文件和目录的正则模式
    LINKED_FILES_PATTERN = re.compile(r'linked_files\s*[:=]\s*\[([^\]]*)\]', re.IGNORECASE)
    LINKED_DIRS_PATTERN = re.compile(r'linked_dirs\s*[:=]\s*\[([^\]]*)\]', re.IGNORECASE)
    PATH_IN_LIST_PATTERN = re.compile(r'["\']([\/\w.\-]+)["\']')

    def parse(self, raw_config: str, app_name: str, environment: str = "production") -> DeployConfig:
        """
        解析部署配置文本，返回结构化配置对象

        参数:
            raw_config: 原始配置文本
            app_name: 应用名称
            environment: 环境名称 (staging/production)

        返回:
            DeployConfig: 结构化部署配置

        异常:
            E002: 配置格式错误
            E003: 配置内容不完整
            E009: 输入为空
        """
        if not raw_config or not raw_config.strip():
            raise ValueError("E009: 输入配置为空")

        if not app_name or not app_name.strip():
            raise ValueError("E003: 应用名称不能为空")

        if environment not in ["staging", "production", "test", "dev"]:
            raise ValueError(f"E004: 无效环境名称: {environment}")

        config = DeployConfig(
            application=app_name.strip(),
            environment=environment,
        )

        lines = raw_config.strip().splitlines()

        # 解析服务器信息
        servers = self._parse_servers(lines)
        if servers:
            config.servers = servers
        else:
            # 尝试从文本中提取服务器地址
            server_hosts = self.SERVER_PATTERN.findall(raw_config)
            if server_hosts:
                for host in server_hosts:
                    server = ServerInfo(host=host)
                    config.servers.append(server)
            else:
                raise ValueError("E003: 未找到服务器信息")

        # 解析仓库
        repo_match = self.REPO_PATTERN.search(raw_config)
        if repo_match:
            config.repository = repo_match.group(1).strip()

        # 解析分支
        branch_match = self.BRANCH_PATTERN.search(raw_config)
        if branch_match:
            config.branch = branch_match.group(1).strip()

        # 解析部署路径
        deploy_path_match = self.DEPLOY_PATH_PATTERN.search(raw_config)
        if deploy_path_match:
            config.deploy_to = deploy_path_match.group(1).strip()

        # 解析环境变量
        env_vars = self._parse_env_vars(lines)
        config.env_vars = env_vars

        # 解析链接文件/目录
        linked_files, linked_dirs = self._parse_linked_paths(lines)
        config.linked_files = linked_files
        config.linked_dirs = linked_dirs

        # 解析自定义任务
        config.custom_tasks = self._parse_custom_tasks(lines)

        # 置信度评估
        config.confidence, config.notes = self._evaluate_confidence(config, raw_config)

        return config

    def _parse_servers(self, lines: List[str]) -> List[ServerInfo]:
        """从配置行中解析服务器信息"""
        servers = []
        current_server = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 新服务器行
            if "server" in line.lower() and (":" in line or "=" in line):
                # 尝试提取主机
                hosts = self.SERVER_PATTERN.findall(line)
                if hosts:
                    if current_server:
                        servers.append(current_server)
                    current_server = ServerInfo(host=hosts[0])

                    # 提取用户
                    user_match = self.USER_PATTERN.search(line)
                    if user_match:
                        current_server.user = user_match.group(1)

                    # 提取端口
                    port_match = self.PORT_PATTERN.search(line)
                    if port_match:
                        current_server.port = int(port_match.group(1))

                    # 提取SSH密钥
                    key_match = self.SSH_KEY_PATTERN.search(line)
                    if key_match:
                        current_server.ssh_key = key_match.group(1)

                    # 提取角色
                    roles = self._extract_roles(line)
                    if roles:
                        current_server.roles = roles

                    # 提取部署路径
                    path_match = self.DEPLOY_PATH_PATTERN.search(line)
                    if path_match:
                        current_server.deploy_to = path_match.group(1)

        if current_server:
            servers.append(current_server)

        return servers

    def _extract_roles(self, text: str) -> List[str]:
        """从文本中提取角色"""
        roles = []
        text_lower = text.lower()
        for role, keywords in self.ROLE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    if role not in roles:
                        roles.append(role)
                    break
        return roles

    def _parse_env_vars(self, lines: List[str]) -> Dict[str, str]:
        """解析环境变量"""
        env_vars = {}
        in_env_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "env" in line.lower() and ("{" in line or ":" in line):
                in_env_section = True
                # 尝试从同一行解析
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    value = parts[1].strip().strip('"\'')
                    env_vars[key] = value
                continue

            if in_env_section:
                if "}" in line:
                    in_env_section = False
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    value = parts[1].strip().strip('"\'')
                    env_vars[key] = value

        return env_vars

    def _parse_linked_paths(self, lines: List[str]) -> tuple:
        """解析链接文件和目录"""
        linked_files = []
        linked_dirs = []
        in_files_section = False
        in_dirs_section = False
        current_file_line = ""
        current_dir_line = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测 linked_files 声明
            if "linked_files" in line.lower():
                # 如果同一行包含列表，直接解析
                match = self.LINKED_FILES_PATTERN.search(line)
                if match:
                    paths = self.PATH_IN_LIST_PATTERN.findall(match.group(1))
                    linked_files.extend(paths)
                else:
                    # 检查是否有内联的数组
                    if "[" in line:
                        in_files_section = True
                        current_file_line = line[line.index("["):]
                        continue
                    else:
                        in_files_section = True
                        current_file_line = ""
                continue

            # 检测 linked_dirs 声明
            if "linked_dirs" in line.lower():
                # 如果同一行包含列表，直接解析
                match = self.LINKED_DIRS_PATTERN.search(line)
                if match:
                    paths = self.PATH_IN_LIST_PATTERN.findall(match.group(1))
                    linked_dirs.extend(paths)
                else:
                    # 检查是否有内联的数组
                    if "[" in line:
                        in_dirs_section = True
                        current_dir_line = line[line.index("["):]
                        continue
                    else:
                        in_dirs_section = True
                        current_dir_line = ""
                continue

            # 处理文件列表内容
            if in_files_section:
                current_file_line += line
                # 检查是否包含完整的列表
                if "]" in current_file_line:
                    # 提取所有路径
                    paths = self.PATH_IN_LIST_PATTERN.findall(current_file_line)
                    linked_files.extend(paths)
                    in_files_section = False
                    current_file_line = ""
                continue

            # 处理目录列表内容
            if in_dirs_section:
                current_dir_line += line
                # 检查是否包含完整的列表
                if "]" in current_dir_line:
                    # 提取所有路径
                    paths = self.PATH_IN_LIST_PATTERN.findall(current_dir_line)
                    linked_dirs.extend(paths)
                    in_dirs_section = False
                    current_dir_line = ""
                continue

        return linked_files, linked_dirs

    def _parse_custom_tasks(self, lines: List[str]) -> List[str]:
        """解析自定义任务"""
        tasks = []
        for line in lines:
            line = line.strip()
            if line.startswith("task ") or line.startswith("before ") or line.startswith("after "):
                tasks.append(line)
        return tasks

    def _evaluate_confidence(self, config: DeployConfig, raw_config: str) -> tuple:
        """评估配置置信度"""
        notes = []
        confidence = 1.0

        # 检查关键信息是否完整
        if not config.repository:
            confidence -= 0.2
            notes.append("[需核实:repository]")

        if not config.servers:
            confidence -= 0.3
            notes.append("[需核实:servers]")

        for server in config.servers:
            if not server.roles:
                confidence -= 0.1
                notes.append(f"[需核实:server_roles:{server.host}]")

        if config.environment == "production" and not config.repository:
            confidence -= 0.1
            notes.append("[需核实:production_repository]")

        # 确保置信度在合理范围
        confidence = max(0.1, min(1.0, confidence))

        return confidence, notes


class CommandGenerator:
    """部署命令生成器"""

    def generate(self, config: DeployConfig) -> List[str]:
        """
        根据配置生成部署命令序列

        参数:
            config: 部署配置

        返回:
            List[str]: 命令列表

        异常:
            E006: 命令生成失败
        """
        if not config or not config.application:
            raise ValueError("E006: 配置无效，无法生成命令")

        commands = []

        # 基础检查
        commands.append(f"# 应用: {config.application}")
        commands.append(f"# 环境: {config.environment}")
        commands.append("")

        # 服务器检查命令
        for server in config.servers:
            ssh_base = f"ssh {server.user}@{server.host}"
            if server.port != 22:
                ssh_base += f" -p {server.port}"
            if server.ssh_key:
                ssh_base += f" -i {server.ssh_key}"

            commands.append(f"# 检查服务器: {server.host}")
            commands.append(f"{ssh_base} 'uname -a'")
            commands.append("")

        # 部署命令
        commands.append("# Capistrano 部署命令")
        commands.append(f"bundle exec cap {config.environment} deploy")

        # 自定义任务
        if config.custom_tasks:
            commands.append("")
            commands.append("# 自定义任务")
            for task in config.custom_tasks:
                commands.append(f"bundle exec cap {config.environment} {task}")

        # 回滚命令
        commands.append("")
        commands.append("# 回滚命令（如需回滚到上一版本）")
        commands.append(f"bundle exec cap {config.environment} deploy:rollback")

        return commands


class BatchProcessor:
    """批量处理器"""

    def process(self, configs: List[DeployConfig]) -> Dict[str, Any]:
        """
        批量处理多个部署配置

        参数:
            configs: 部署配置列表

        返回:
            Dict[str, Any]: 批量处理结果
        """
        result = {
            "total": len(configs),
            "environments": {},
            "configs": []
        }

        for config in configs:
            env = config.environment
            if env not in result["environments"]:
                result["environments"][env] = {
                    "count": 0,
                    "applications": []
                }
            result["environments"][env]["count"] += 1
            result["environments"][env]["applications"].append(config.application)

            config_dict = config.to_dict()
            config_dict["deploy_commands"] = CommandGenerator().generate(config)
            result["configs"].append(config_dict)

        return result


# ------------------------------------------------------------
# 自检模块
# ------------------------------------------------------------

def run_selftest() -> bool:
    """
    运行自检，验证核心逻辑

    返回:
        bool: 自检是否通过
    """
    print("=" * 60)
    print("capsize 自检开始")
    print("=" * 60)

    try:
        # 测试1: 配置解析
        print("\n[测试1] 配置解析...")
        sample_config = """
        server: ec2-54-123-45-67.compute.amazonaws.com, user: ubuntu, roles: app, db
        server: ec2-54-123-45-68.compute.amazonaws.com, user: ubuntu, roles: web, port: 2222
        repo: git@github.com:example/myapp.git
        branch: main
        deploy_to: /var/www/myapp
        env:
          RAILS_ENV=production
          SECRET_KEY_BASE=abc123
        linked_files: ["config/database.yml", "config/secrets.yml"]
        linked_dirs: ["log", "tmp/pids"]
        """

        parser = ConfigParser()
        config = parser.parse(sample_config, "myapp", "production")

        assert config.application == "myapp", "应用名称解析错误"
        assert config.environment == "production", "环境名称解析错误"
        assert len(config.servers) >= 2, "服务器数量不足"
        assert config.repository is not None, "仓库地址未解析"
        assert config.branch == "main", "分支解析错误"
        assert config.deploy_to == "/var/www/myapp", "部署路径解析错误"
        assert len(config.env_vars) >= 2, "环境变量解析不足"
        assert len(config.linked_files) >= 2, "链接文件解析不足"
        assert len(config.linked_dirs) >= 2, "链接目录解析不足"
        print("  ✓ 配置解析测试通过")

        # 测试2: 服务器信息
        print("\n[测试2] 服务器信息...")
        first_server = config.servers[0]
        assert first_server.host.startswith("ec2-"), "服务器地址格式错误"
        assert first_server.user == "ubuntu", "默认用户错误"
        assert len(first_server.roles) >= 1, "服务器角色缺失"
        assert 0.0 <= first_server.confidence <= 1.0, "置信度范围错误"
        print("  ✓ 服务器信息测试通过")

        # 测试3: 命令生成
        print("\n[测试3] 命令生成...")
        generator = CommandGenerator()
        commands = generator.generate(config)
        assert len(commands) > 10, "命令数量不足"
        assert any("cap production deploy" in cmd for cmd in commands), "缺少部署命令"
        assert any("ssh" in cmd for cmd in commands), "缺少SSH命令"
        assert any("rollback" in cmd for cmd in commands), "缺少回滚命令"
        print("  ✓ 命令生成测试通过")

        # 测试4: 批量处理
        print("\n[测试4] 批量处理...")
        batch_processor = BatchProcessor()
        config2 = DeployConfig(
            application="myapp-staging",
            environment="staging",
            servers=[ServerInfo(host="ec2-54-123-45-69.compute.amazonaws.com")]
        )
        batch_result = batch_processor.process([config, config2])
        assert batch_result["total"] == 2, "批量处理数量错误"
        assert "production" in batch_result["environments"], "缺少production环境"
        assert "staging" in batch_result["environments"], "缺少staging环境"
        assert batch_result["environments"]["production"]["count"] >= 1, "production环境数量错误"
        print("  ✓ 批量处理测试通过")

        # 测试5: 错误处理
        print("\n[测试5] 错误处理...")
        try:
            parser.parse("", "app", "production")
            assert False, "空配置未抛出异常"
        except ValueError as e:
            assert "E009" in str(e), f"错误码错误: {e}"

        try:
            parser.parse(sample_config, "app", "invalid_env")
            assert False, "无效环境未抛出异常"
        except ValueError as e:
            assert "E004" in str(e), f"错误码错误: {e}"

        try:
            parser.parse("no server here", "app", "production")
            assert False, "无服务器信息未抛出异常"
        except ValueError as e:
            assert "E003" in str(e), f"错误码错误: {e}"
        print("  ✓ 错误处理测试通过")

        # 测试6: 置信度评估
        print("\n[测试6] 置信度评估...")
        incomplete_config = """
        server: ec2-54-123-45-70.compute.amazonaws.com
        """
        incomplete = parser.parse(incomplete_config, "app2", "production")
        assert incomplete.confidence < 1.0, "不完整配置置信度应为小于1"
        assert len(incomplete.notes) > 0, "应该有置信度提示"
        print("  ✓ 置信度评估测试通过")

        print("\n" + "=" * 60)
        print("✅ 所有自检测试通过!")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        print("错误码: E007")
        return False
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        print("错误码: E010")
        return False


# ------------------------------------------------------------
# 主程序
# ------------------------------------------------------------

def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="capsize - EC2部署运维自动化工具",
        epilog="示例: python main.py --config config.txt --app myapp --env production --output plan.json"
    )

    parser.add_argument("--config", "-c", help="部署配置文件路径")
    parser.add_argument("--app", "-a", help="应用名称")
    parser.add_argument("--env", "-e", default="production", help="环境名称 (staging/production/test/dev)")
    parser.add_argument("--output", "-o", help="输出文件路径 (JSON格式)")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    parser.add_argument("--force", action="store_true")  # R4 强制写盘


    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    if not args.config:
        print("错误: 缺少配置文件路径 (使用 --config 指定)")
        print("提示: 使用 --selftest 运行自检")
        sys.exit(1)

    if not args.app:
        print("错误: 缺少应用名称 (使用 --app 指定)")
        sys.exit(1)

    try:
        # 读取配置
        with open(args.config, "r", encoding="utf-8") as f:
            raw_config = f.read()

        # 解析配置
        parser = ConfigParser()
        config = parser.parse(raw_config, args.app, args.env)

        # 生成命令
        generator = CommandGenerator()
        commands = generator.generate(config)

        # 输出结果
        result = {
            "config": config.to_dict(),
            "commands": commands,
            "summary": {
                "application": config.application,
                "environment": config.environment,
                "servers": len(config.servers),
                "confidence": config.confidence,
                "notes": config.notes
            }
        }

        # 输出到文件或控制台
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"部署方案已保存到: {args.output}")
            except Exception as e:
                print(f"错误: 无法写入输出文件 (错误码: E008) - {e}")
                sys.exit(1)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 显示置信度提示
        if config.notes:
            print("\n⚠️ 置信度提示:")
            for note in config.notes:
                print(f"  {note}")

    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"错误: 配置文件不存在: {args.config} (错误码: E002)")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e} (错误码: E010)")
        sys.exit(1)


if __name__ == "__main__":
    main()
