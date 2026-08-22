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
  6. Cstrano扩展：支持通过Cstrano插件进行部署扩展，提供接口和实现

仅生成方案与命令，不执行真实部署操作。
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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
# E011: Cstrano扩展错误
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
    cstrano_config: Optional[Dict[str, Any]] = None  # Cstrano扩展配置

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ------------------------------------------------------------
# Cstrano扩展模块
# ------------------------------------------------------------

class CstranoExtension:
    """
    Cstrano扩展支持类
    
    提供Cstrano插件的接口和实现，支持：
    - 插件加载
    - 任务注册
    - 配置扩展
    - 钩子执行
    """
    
    def __init__(self):
        """初始化Cstrano扩展"""
        self.plugins = {}
        self.tasks = {}
        self.hooks = {}
        self.config_extensions = {}
        self._loaded = False
        self._lock = threading.Lock()
        
    def load_plugin(self, plugin_name: str, plugin_config: Optional[Dict] = None) -> bool:
        """
        加载Cstrano插件
        
        参数:
            plugin_name: 插件名称
            plugin_config: 插件配置
            
        返回:
            bool: 是否加载成功
        """
        try:
            if not plugin_name or not isinstance(plugin_name, str):
                raise ValueError("E011: 插件名称无效")
                
            with self._lock:
                # 实际插件加载逻辑 - 尝试动态导入
                try:
                    # 尝试导入插件模块
                    module = __import__(f"cstrano_plugins.{plugin_name}", fromlist=["*"])
                    if hasattr(module, "setup"):
                        module.setup(self)
                    if hasattr(module, "register_tasks"):
                        module.register_tasks(self)
                    if hasattr(module, "add_hooks"):
                        module.add_hooks(self)
                except ImportError:
                    # 插件模块不存在时，使用内置默认行为
                    pass
                
                self.plugins[plugin_name] = {
                    "name": plugin_name,
                    "config": plugin_config or {},
                    "loaded_at": datetime.now(timezone.utc).isoformat(),
                    "status": "loaded"
                }
                
                # 注册默认任务
                self.tasks[f"{plugin_name}:setup"] = {
                    "description": f"Setup {plugin_name}",
                    "command": f"bundle exec cstrano {plugin_name}:setup"
                }
                self.tasks[f"{plugin_name}:deploy"] = {
                    "description": f"Deploy with {plugin_name}",
                    "command": f"bundle exec cstrano {plugin_name}:deploy"
                }
                
                self._loaded = True
                return True
        except Exception as e:
            print(f"Cstrano插件加载失败: {e}")
            return False
    
    def register_task(self, task_name: str, task_command: str, description: str = "") -> bool:
        """
        注册Cstrano任务
        
        参数:
            task_name: 任务名称
            task_command: 任务命令
            description: 任务描述
            
        返回:
            bool: 是否注册成功
        """
        try:
            if not task_name or not task_command:
                raise ValueError("E011: 任务名称或命令无效")
                
            with self._lock:
                self.tasks[task_name] = {
                    "description": description or f"Task {task_name}",
                    "command": task_command
                }
                return True
        except Exception as e:
            print(f"Cstrano任务注册失败: {e}")
            return False
    
    def add_hook(self, hook_name: str, hook_command: str) -> bool:
        """
        添加Cstrano钩子
        
        参数:
            hook_name: 钩子名称 (before_deploy, after_deploy等)
            hook_command: 钩子命令
            
        返回:
            bool: 是否添加成功
        """
        try:
            if not hook_name or not hook_command:
                raise ValueError("E011: 钩子名称或命令无效")
                
            with self._lock:
                if hook_name not in self.hooks:
                    self.hooks[hook_name] = []
                self.hooks[hook_name].append(hook_command)
                return True
        except Exception as e:
            print(f"Cstrano钩子添加失败: {e}")
            return False
    
    def extend_config(self, config_key: str, config_value: Any) -> bool:
        """
        扩展Cstrano配置
        
        参数:
            config_key: 配置键
            config_value: 配置值
            
        返回:
            bool: 是否扩展成功
        """
        try:
            if not config_key:
                raise ValueError("E011: 配置键无效")
                
            with self._lock:
                self.config_extensions[config_key] = config_value
                return True
        except Exception as e:
            print(f"Cstrano配置扩展失败: {e}")
            return False
    
    def generate_commands(self, config: DeployConfig) -> List[str]:
        """
        生成Cstrano相关命令
        
        参数:
            config: 部署配置
            
        返回:
            List[str]: Cstrano命令列表
        """
        commands = []
        
        # 生成插件加载命令
        for plugin_name in self.plugins:
            commands.append(f"# Cstrano插件: {plugin_name}")
            commands.append(f"bundle exec cstrano plugin install {plugin_name}")
            
        # 生成任务执行命令
        for task_name, task_info in self.tasks.items():
            commands.append(f"# Cstrano任务: {task_info['description']}")
            commands.append(task_info["command"])
            
        # 生成钩子执行命令
        for hook_name, hook_commands in self.hooks.items():
            commands.append(f"# Cstrano钩子: {hook_name}")
            for hook_cmd in hook_commands:
                commands.append(hook_cmd)
                
        # 生成配置扩展命令
        if self.config_extensions:
            commands.append("# Cstrano配置扩展")
            for key, value in self.config_extensions.items():
                commands.append(f"bundle exec cstrano config set {key} {value}")
                
        return commands
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "plugins": self.plugins,
            "tasks": self.tasks,
            "hooks": self.hooks,
            "config_extensions": self.config_extensions,
            "loaded": self._loaded
        }


# ------------------------------------------------------------
# 网络请求工具类
# ------------------------------------------------------------

class NetworkUtils:
    """网络请求工具类，提供重试、超时、退避机制"""
    
    @staticmethod
    def request_with_retry(url: str, timeout: int = 5, max_retries: int = 3, 
                          backoff_factor: float = 1.5) -> Optional[Dict]:
        """
        带重试和退避的HTTP请求
        
        参数:
            url: 请求URL
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            backoff_factor: 退避因子
            
        返回:
            Optional[Dict]: 响应JSON数据，失败返回None
        """
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "capsize-skill"})
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    if response.status == 200:
                        return json.loads(response.read().decode("utf-8"))
                    else:
                        print(f"HTTP {response.status} 错误: {url}")
            except urllib.error.URLError as e:
                print(f"URL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            except urllib.error.HTTPError as e:
                print(f"HTTP错误 (尝试 {attempt + 1}/{max_retries}): {e.code} - {e.reason}")
            except Exception as e:
                print(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = backoff_factor ** attempt
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        return None
    
    @staticmethod
    def batch_request(urls: List[str], timeout: int = 5, max_retries: int = 3,
                     max_workers: int = 5) -> Dict[str, Optional[Dict]]:
        """
        并发批量请求
        
        参数:
            urls: URL列表
            timeout: 超时时间
            max_retries: 最大重试次数
            max_workers: 最大并发数
            
        返回:
            Dict[str, Optional[Dict]]: URL到响应数据的映射
        """
        results = {}
        
        def fetch_url(url):
            return url, NetworkUtils.request_with_retry(url, timeout, max_retries)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(fetch_url, url): url for url in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    _, result = future.result()
                    results[url] = result
                except Exception as e:
                    print(f"请求 {url} 失败: {e}")
                    results[url] = None
        
        return results


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

    # Cstrano配置正则
    CSTRANO_PLUGIN_PATTERN = re.compile(r'cstrano_plugin\s*[:=]\s*["\']([\w-]+)["\']', re.IGNORECASE)
    CSTRANO_TASK_PATTERN = re.compile(r'cstrano_task\s*[:=]\s*["\']([\w:]+)["\']', re.IGNORECASE)
    CSTRANO_HOOK_PATTERN = re.compile(r'cstrano_hook\s*[:=]\s*["\']([\w_]+)["\']', re.IGNORECASE)

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

        # 解析Cstrano配置
        config.cstrano_config = self._parse_cstrano_config(raw_config)

        # 置信度评估
        config.confidence, config.notes = self._evaluate_confidence(config, raw_config)

        return config
