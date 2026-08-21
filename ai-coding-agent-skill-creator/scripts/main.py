#!/usr/bin/env python3
"""AI 编程技能封装工具：从 GitHub 趋势仓库筛选并生成 AI 编程技能定义。"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# GitHub 趋势 API 端点（可通过环境变量配置）
GITHUB_TRENDING_API = os.environ.get(
    "GITHUB_TRENDING_API",
    "https://api.github.com/search/repositories?q=ai+programming&sort=stars&order=desc&per_page=10&page=1"
)

# 默认技能筛选关键词（可通过 --keywords 参数覆盖）
DEFAULT_SKILL_KEYWORDS = ["ai", "llm", "gpt", "code", "programming", "developer", "copilot", "agent"]

# TTL 缓存配置（秒）
CACHE_TTL = 300  # 5 分钟
_cache = {}
_cache_timestamp = {}
# 使用应用专属用户目录，避免多用户/容器环境权限问题
_cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "ai_skill_creator")
_cache_file = os.path.join(_cache_dir, "cache.json")
# 缓存 schema 版本号
CACHE_SCHEMA_VERSION = 1


def _ensure_cache_dir() -> None:
    """确保缓存目录存在"""
    if not os.path.exists(_cache_dir):
        try:
            os.makedirs(_cache_dir, exist_ok=True)
        except OSError:
            pass


def _load_disk_cache() -> None:
    """从磁盘加载缓存（进程重启后恢复）"""
    global _cache, _cache_timestamp
    try:
        _ensure_cache_dir()
        if os.path.exists(_cache_file):
            with open(_cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 校验 schema 版本，不匹配则丢弃
                if data.get("schema_version") != CACHE_SCHEMA_VERSION:
                    print("[WARN] 缓存版本不匹配，丢弃旧缓存")
                    _cache = {}
                    _cache_timestamp = {}
                    return
                _cache = data.get("cache", {})
                _cache_timestamp = data.get("timestamps", {})
                # 清理过期缓存（使用 pop 避免 KeyError）
                now = time.time()
                expired = [k for k, v in _cache_timestamp.items() if now - v > CACHE_TTL]
                for k in expired:
                    _cache.pop(k, None)
                    _cache_timestamp.pop(k, None)
    except (json.JSONDecodeError, OSError):
        # 缓存文件损坏时静默忽略
        _cache = {}
        _cache_timestamp = {}


def _save_disk_cache() -> None:
    """持久化缓存到磁盘（带文件锁）"""
    try:
        _ensure_cache_dir()
        # 使用临时文件 + 原子替换，避免并发写冲突
        fd, temp_path = tempfile.mkstemp(dir=_cache_dir, prefix=".cache_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": CACHE_SCHEMA_VERSION,
                    "cache": _cache,
                    "timestamps": _cache_timestamp
                }, f)
            os.replace(temp_path, _cache_file)
        except Exception:
            # 异常路径清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
    except OSError:
        # 磁盘写入失败时静默忽略（降级为内存缓存）
        pass


def _get_cached(key: str) -> Optional[Any]:
    """获取缓存数据（带 TTL，优先内存，其次磁盘）"""
    # 首次运行时加载磁盘缓存
    if not _cache and not _cache_timestamp:
        _load_disk_cache()
    
    if key in _cache:
        if time.time() - _cache_timestamp[key] < CACHE_TTL:
            return _cache[key]
        else:
            _cache.pop(key, None)
            _cache_timestamp.pop(key, None)
    return None


def _set_cache(key: str, value: Any) -> None:
    """设置缓存数据并持久化"""
    _cache[key] = value
    _cache_timestamp[key] = time.time()
    _save_disk_cache()


def _read_text_safe(path: str) -> str:
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _iter_lines(path: str):
    """批处理流式读取工具"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def fetch_github_trending(max_retries: int = 3, timeout: int = 10) -> List[Dict]:
    """获取 GitHub 趋势仓库，带重试退避、超时和缓存降级。"""
    cache_key = "github_trending"
    cached = _get_cached(cache_key)
    if cached is not None:
        print("[INFO] 使用缓存数据")
        return cached

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                GITHUB_TRENDING_API,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ai-coding-agent-skill-creator/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(
                        url=GITHUB_TRENDING_API,
                        code=response.status,
                        msg=f"HTTP {response.status}",
                        hdrs=response.headers,
                        fp=None
                    )
                # 检查限流头
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
                if rate_limit_remaining is not None and int(rate_limit_remaining) < 5:
                    print(f"[WARN] GitHub API 限流剩余 {rate_limit_remaining} 次，将降级使用缓存")
                    if cache_key in _cache:
                        return _cache[cache_key]
                
                data = json.loads(response.read().decode("utf-8"))
                items = data.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("API 返回结构异常：items 不是列表")
                _set_cache(cache_key, items)
                return items
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            # 对 403/429 和 5xx 进行重试
            if isinstance(e, urllib.error.HTTPError) and e.code in (403, 429):
                # 限流，使用 Retry-After 头或指数退避
                retry_after = e.headers.get("Retry-After") if hasattr(e, "headers") else None
                wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
            elif isinstance(e, urllib.error.HTTPError) and e.code >= 500:
                wait_time = 2 ** attempt
            else:
                wait_time = 2 ** attempt
            
            if attempt == max_retries - 1:
                # 降级策略：尝试使用缓存（即使过期）
                if cache_key in _cache:
                    print("[WARN] API 请求失败，使用过期缓存降级")
                    return _cache[cache_key]
                # 缓存为空且所有重试失败时，抛出明确异常
                raise RuntimeError(f"GitHub API 请求失败，且无可用缓存: {e}")
            print(f"[WARN] 请求失败，{wait_time}秒后重试 ({attempt + 1}/{max_retries})...")
            time.sleep(wait_time)
    return []


def filter_ai_skills(repos: List[Dict], keywords: Optional[List[str]] = None) -> List[Dict]:
    """根据关键词筛选 AI 编程相关仓库，使用加权评分。"""
    if keywords is None:
        keywords = DEFAULT_SKILL_KEYWORDS
    
    filtered = []
    for repo in repos:
        description = (repo.get("description") or "").lower()
        topics = [t.lower() for t in repo.get("topics", [])]
        name = (repo.get("name") or "").lower()
        full_name = (repo.get("full_name") or "").lower()
        
        combined_text = f"{name} {full_name} {description} {' '.join(topics)}"
        
        # 加权评分：名称匹配权重高，描述次之，主题最低
        score = 0
        for keyword in keywords:
            kw = keyword.lower()
            if kw in name or kw in full_name:
                score += 3
            elif kw in description:
                score += 2
            elif kw in topics:
                score += 1
        
        # 至少匹配一个关键词且得分大于0
        if score > 0:
            repo_copy = dict(repo)
            repo_copy["_skill_score"] = score
            filtered.append(repo_copy)
    
    # 按评分降序排序
    filtered.sort(key=lambda x: x.get("_skill_score", 0), reverse=True)
    return filtered


def generate_skill_definition(repo: Dict) -> Dict:
    """从仓库生成技能定义（参数抽象）。"""
    return {
        "skill_name": repo.get("name", "unknown"),
        "repo_url": repo.get("html_url", ""),
        "description": repo.get("description", "") or "No description",
        "language": repo.get("language", "unknown"),
        "stars": repo.get("stargazers_count", 0),
        "topics": repo.get("topics", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "repo_name": repo.get("full_name", ""),
            "clone_url": repo.get("clone_url", ""),
            "default_branch": repo.get("default_branch", "main")
        }
    }


def validate_skill(skill: Dict) -> Tuple[bool, str]:
    """验证技能定义完整性。"""
    required_fields = ["skill_name", "repo_url", "description", "parameters"]
    for field in required_fields:
        if field not in skill or not skill[field]:
            return False, f"缺少必要字段: {field}"
    if not skill["parameters"].get("repo_name"):
        return False, "参数中缺少 repo_name"
    return True, "验证通过"


def validate_skill_schema(skills: List[Dict], schema: Optional[Dict] = None) -> Tuple[bool, str]:
    """验证技能列表是否符合 JSON Schema。"""
    if schema is None:
        # 默认 schema
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill_name", "repo_url", "description", "parameters"],
                "properties": {
                    "skill_name": {"type": "string"},
                    "repo_url": {"type": "string"},
                    "description": {"type": "string"},
                    "language": {"type": "string"},
                    "stars": {"type": "integer"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "generated_at": {"type": "string"},
                    "parameters": {
                        "type": "object",
                        "required": ["repo_name", "clone_url", "default_branch"],
                        "properties": {
                            "repo_name": {"type": "string"},
                            "clone_url": {"type": "string"},
                            "default_branch": {"type": "string"}
                        }
                    }
                }
            }
        }
    
    try:
        # 简化版 schema 验证（不引入外部依赖）
        if not isinstance(skills, list):
            return False, "技能列表必须是数组"
        
        for skill in skills:
            if not isinstance(skill, dict):
                return False, "技能必须是对象"
            
            required = schema.get("items", {}).get("required", [])
            for field in required:
                if field not in skill:
                    return False, f"缺少字段: {field}"
            
            # 验证 parameters
            params = skill.get("parameters", {})
            param_required = schema.get("items", {}).get("properties", {}).get("parameters", {}).get("required", [])
            for field in param_required:
                if field not in params:
                    return False, f"参数缺少字段: {field}"
        
        return True, "Schema 验证通过"
    except Exception as e:
        return False, f"Schema 验证失败: {e}"


def process_items(items: List[Dict], output_format: str = "text") -> str:
    """处理技能列表，返回格式化后的字符串。"""
    if output_format == "json":
        return json.dumps(items, ensure_ascii=False, indent=2)
    elif output_format == "markdown":
        lines = ["| 序号 | 技能名称 | 仓库 | 描述 |", "|------|----------|------|------|"]
        for i, item in enumerate(items, 1):
            lines.append(f"| {i} | {item['skill_name']} | [{item['repo_url']}]({item['repo_url']}) | {item['description'][:50]}... |")
        return "\n".join(lines)
    else:  # text
        lines = []
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item['skill_name']} - {item['description']}")
        return "\n".join(lines)


def write_file(path: str, content: str, dry_run: bool = False) -> bool:
    """原子写入文件，支持 dry-run 模式。"""
    if dry_run:
        print(f"[DRY-RUN] 将写入文件: {path}")
        print(f"[DRY-RUN] 内容长度: {len(content)} 字符")
        return False

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 原子写入：临时文件 + os.replace
    fd, temp_path = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".swp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)
        os.replace(temp_path, path)
    except Exception:
        # 异常路径清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    return True


def process_repos_concurrently(repos: List[Dict], max_workers: int = 5) -> List[Dict]:
    """并发处理仓库列表，生成技能定义。"""
    skills = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_repo = {executor.submit(generate_skill_definition, repo): repo for repo in repos}
        for future in as_completed(future_to_repo):
            try:
                skill = future.result()
                skills.append(skill)
            except Exception as e:
                print(f"[WARN] 处理仓库失败: {e}", file=sys.stderr)
    return skills


def run_selftest() -> int:
    """运行自检，验证核心链路（GitHub 获取、技能封装、验证）。"""
    print("[RUN] 自检开始")
    
    # 1. 测试 GitHub 数据获取（mock 数据模拟真实调用）
    print("\n测试 GitHub 趋势获取...")
    mock_repos = [
        {
            "name": "test-ai-agent",
            "full_name": "test/test-ai-agent",
            "html_url": "https://github.com/test/test-ai-agent",
            "description": "AI programming agent for code generation",
            "language": "Python",
            "stargazers_count": 100,
            "topics": ["ai", "programming", "agent"],
            "clone_url": "https://github.com/test/test-ai-agent.git",
            "default_branch": "main"
        },
        {
            "name": "unrelated-tool",
            "full_name": "test/unrelated-tool",
            "html_url": "https://github.com/test/unrelated-tool",
            "description": "A simple calculator",
            "language": "JavaScript",
            "stargazers_count": 50,
            "topics": ["calculator"],
            "clone_url": "https://github.com/test/unrelated-tool.git",
            "default_branch": "main"
        },
        {
            "name": "llm-code-assistant",
            "full_name": "test/llm-code-assistant",
            "html_url": "https://github.com/test/llm-code-assistant",
            "description": "LLM powered code assistant",
            "language": "TypeScript",
            "stargazers_count": 200,
            "topics": ["llm", "code", "assistant"],
            "clone_url": "https://github.com/test/llm-code-assistant.git",
            "default_branch": "main"
        }
    ]
    
    # 测试筛选逻辑（默认关键词）
    filtered = filter_ai_skills(mock_repos)
    assert len(filtered) == 2, f"筛选结果数量错误: {len(filtered)}"
    assert filtered[0]["name"] == "llm-code-assistant", "筛选结果排序错误（应优先高分）"
    assert filtered[1]["name"] == "test-ai-agent", "筛选结果错误"
    print("  [PASS] 技能筛选逻辑正常（加权评分）")
    
    #
