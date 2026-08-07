#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkillPack — 本地AI技能打包与团队部署工具

本脚本依据功能规格独立实现（clean-room），仅使用标准库。
支持技能打包、依赖清单生成、部署配置生成、版本校验、批量处理。
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 常量定义
# ---------------------------------------------------------------------------
MAX_PACK_SIZE = 500 * 1024 * 1024  # 500MB 上限
SUPPORTED_CONFIG_NAMES = ["skill.json", "skill.yaml", "skill.yml", "SKILL.md", "skill.md"]
DEFAULT_INDEX_NAME = "index.json"
DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_DEPLOY_CONFIG_NAME = "deploy_config.json"
ERROR_CODES = {
    "E001": "参数错误或缺少必要参数",
    "E002": "技能目录不存在或不可读",
    "E003": "技能包超过500MB大小限制",
    "E004": "技能包文件不存在或无法读取",
    "E005": "技能包格式无效（非zip）",
    "E006": "技能包内缺少必要配置文件",
    "E007": "版本校验失败或不兼容",
    "E008": "写入输出文件失败",
    "E009": "批量处理中部分任务失败",
    "E010": "内部逻辑错误",
}

# ---------------------------------------------------------------------------
# 异常与错误处理
# ---------------------------------------------------------------------------
class SkillPackError(Exception):
    """技能打包工具的自定义异常，携带错误码。"""
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


def _raise(code: str, **kwargs) -> None:
    """根据错误码抛出标准异常。"""
    template = ERROR_CODES.get(code, "未知错误")
    detail = "；".join(f"{k}={v}" for k, v in kwargs.items())
    msg = f"{template}。{detail}" if detail else template
    raise SkillPackError(code, msg)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _safe_filename(name: str) -> str:
    """将字符串转换为安全的文件名。"""
    return re.sub(r'[^A-Za-z0-9._-]', '_', name)


def _read_json(path: Path) -> Optional[Dict]:
    """读取 JSON 文件，失败时返回 None。"""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Dict) -> None:
    """写入 JSON 文件，失败时抛出 E008。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        _raise("E008", path=str(path), reason=str(exc))


def _compute_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希。"""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan_dependencies(skill_dir: Path) -> List[str]:
    """
    扫描技能目录，提取依赖清单。
    支持 requirements.txt 和配置文件中的依赖字段。
    """
    deps: List[str] = []
    req_file = skill_dir / "requirements.txt"
    if req_file.exists():
        for line in req_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                deps.append(line)

    # 扫描配置文件中的依赖字段
    for cfg_name in SUPPORTED_CONFIG_NAMES:
        cfg_path = skill_dir / cfg_name
        if not cfg_path.exists():
            continue
        if cfg_path.suffix == ".json":
            data = _read_json(cfg_path)
            if data and "dependencies" in data:
                deps.extend(data["dependencies"])
        elif cfg_path.suffix in (".yaml", ".yml"):
            # 简单 YAML 解析（仅提取 dependencies 字段，不引入第三方库）
            try:
                in_deps = False
                for line in cfg_path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("dependencies:"):
                        in_deps = True
                        continue
                    if in_deps:
                        if stripped.startswith("- "):
                            deps.append(stripped[2:].strip())
                        elif stripped and not stripped.startswith(("#", " ")):
                            in_deps = False
            except Exception:
                pass
        elif cfg_path.name.lower() == "skill.md":
            # 从 Markdown 中提取
