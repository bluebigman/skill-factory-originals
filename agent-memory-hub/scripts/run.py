#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-memory-hub - 记忆资产团队索引工具

将对话、文档、代码整理为四类记忆资产，生成团队共享索引。
支持批量处理，输出结构化资产文件和汇总索引。

用法示例:
    python run.py --input ./docs --output ./memory_assets
    python run.py --input ./conversation.txt --output ./memory_assets --type dialogue
    python run.py --selftest
"""

import os
import sys
import json
import hashlib
import argparse
import datetime
import tempfile
import logging
from datetime import timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from logging.handlers import RotatingFileHandler

# 配置日志 - 默认使用临时目录，可通过 --log-file 覆盖
DEFAULT_LOG_DIR = tempfile.gettempdir()
DEFAULT_LOG_FILE = os.path.join(DEFAULT_LOG_DIR, 'agent_memory_hub.log')

def setup_logging(log_file: str = DEFAULT_LOG_FILE) -> logging.Logger:
    """配置日志系统，支持文件轮转"""
    logger = logging.getLogger('agent_memory_hub')
    logger.setLevel(logging.INFO)
    
    # 清除已有handlers
    logger.handlers.clear()
    
    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件handler（带轮转）
    try:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"无法创建日志文件 {log_file}: {e}")
    
    return logger

logger = setup_logging()

# 尝试导入可选依赖
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# 资产类型定义
ASSET_TYPES = {
    "dialogue": "对话记忆",
    "document": "文档记忆",
    "code": "代码记忆",
    "decision": "决策记忆"
}

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".java", ".cpp", ".c", ".h",
    ".json", ".yaml", ".yml", ".csv", ".log"
}

# 角色标记配置（可外部覆盖）
ROLE_MARKERS = {
    "用户": "user", "User": "user", "用户:": "user",
    "AI": "assistant", "Assistant": "assistant", "AI:": "assistant",
    "助手": "assistant", "系统": "system",
    "Human": "user", "human": "user", "Bot": "assistant", "bot": "assistant"
}

# 决策标记配置
DECISION_MARKERS = ["决策:", "决定:", "结论:", "方案:", "Decision:", "Conclusion:"]

# 断点续处理状态文件
STATE_FILE = ".processing_state.json"


def load_role_markers(config_path: Optional[Path] = None) -> Dict[str, str]:
    """从外部配置加载角色标记，支持正则表达式"""
    markers = dict(ROLE_MARKERS)
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'role_markers' in config:
                    markers.update(config['role_markers'])
                logger.info(f"已从 {config_path} 加载角色标记配置")
        except Exception as e:
            logger.warning(f"加载配置失败: {e}，使用默认配置")
    return markers


def atomic_write(filepath: Path, content: str, encoding: str = 'utf-8') -> bool:
    """原子写入文件：使用唯一临时文件，确保并发安全"""
    # 创建临时文件（带随机后缀）
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f'.{filepath.stem}_',
        suffix='.tmp'
    )
    try:
        with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # 原子替换
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        logger.error(f"原子写入失败 {filepath}: {e}")
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False


def load_state(output_dir: Path) -> Dict:
    """加载断点续处理状态"""
    state_file = output_dir / STATE_FILE
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载状态文件失败: {e}")
    return {"processed": [], "failed": []}


def save_state(output_dir: Path, state: Dict) -> bool:
    """保存断点续处理状态"""
    state_file = output_dir / STATE_FILE
    return atomic_write(state_file, json.dumps(state, ensure_ascii=False, indent=2))


def classify_file(filepath: Path, role_markers: Dict[str, str]) -> str:
    """根据文件扩展名和内容分类资产类型"""
    ext = filepath.suffix.lower()
    if ext in {".py", ".js", ".java", ".cpp", ".c", ".h"}:
        return "code"
    elif ext in {".txt", ".log"}:
        # 检查是否为对话记录（包含对话标记）
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")[:2000]
            if any(marker in content for marker in role_markers.keys()):
                return "dialogue"
        except Exception:
            pass
        return "document"
    elif ext in {".md", ".json", ".yaml", ".yml", ".csv"}:
        return "document"
    else:
        return "document"


def extract_dialogue(content: str, role_markers: Dict[str, str]) -> dict:
    """从对话文本中提取结构化信息"""
    lines = content.split("\n")
    messages = []
    current_role = None
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别角色标记（支持正则）
        matched = False
        for marker, role in role_markers.items():
            if line.startswith(marker) and ":" in line[:30]:
                # 保存之前的消息
                if current_role and current_text:
                    messages.append({
                        "role": current_role,
                        "content": "\n".join(current_text).strip()
                    })
                current_role = role
                current_text = [line.split(":", 1)[1].strip()]
                matched = True
                break

        if not matched:
            if current_role:
                current_text.append(line)

    # 保存最后一条消息
    if current_role and current_text:
        messages.append({
            "role": current_role,
            "content": "\n".join(current_text).strip()
        })

    # 提取主题（取前50个字符）
    topic = ""
    for msg in messages[:3]:
        if msg["role"] in {"user", "assistant"}:
            topic = msg["content"][:50]
            break

    return {
        "type": "dialogue",
        "topic": topic,
        "message_count": len(messages),
        "participants": list(set(m["role"] for m in messages)),
        "messages": messages[:10]  # 最多保存10条
    }


def extract_document(content: str, filepath: Path) -> dict:
    """从文档中提取关键信息"""
    lines = content.split("\n")
    title = filepath.stem
    keywords = []

    # 提取标题
    for line in lines[:20]:
        line = line.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            break

    # 提取关键词（简单实现：高频词）
    word_count = {}
    for line in lines:
        for word in line.split():
            word = word.strip(".,;:!?()[]{}'\"")
            if len(word) > 2 and not word.isdigit():
                word_count[word] = word_count.get(word, 0) + 1

    keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
    keywords = [w for w, _ in keywords]

    return {
        "type": "document",
        "title": title,
        "keywords": keywords,
        "line_count": len(lines),
        "char_count": len(content),
        "file_type": filepath.suffix
    }


def extract_code(content: str, filepath: Path) -> dict:
    """从代码文件中提取结构信息"""
    lines = content.split("\n")
    functions = []
    classes = []
    imports = []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # 提取导入
        if line_stripped.startswith(("import ", "from ")):
            imports.append(line_stripped)

        # 提取函数定义
        if line_stripped.startswith(("def ", "async def ")):
            func_name = line_stripped.split("(")[0].replace("def ", "").replace("async ", "").strip()
            functions.append({
                "name": func_name,
                "line": i + 1
            })

        # 提取类定义
        if line_stripped.startswith("class "):
            class_name = line_stripped.split("(")[0].replace("class ", "").strip()
            classes.append({
                "name": class_name,
                "line": i + 1
            })

    return {
        "type": "code",
        "language": filepath.suffix.lstrip("."),
        "functions": functions[:20],
        "classes": classes[:10],
        "imports": imports[:20],
        "total_lines": len(lines)
    }


def extract_decision(content: str) -> dict:
    """从内容中提取决策信息"""
    lines = content.split("\n")
    decisions = []
    current_decision = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 识别决策标记
        if any(marker in line for marker in DECISION_MARKERS):
            if current_decision:
                decisions.append(current_decision)
            current_decision = {
                "title": line.split(":", 1)[1].strip() if ":" in line else line,
                "details": []
            }
        elif current_decision and line.startswith("-"):
            current_decision["details"].append(line.lstrip("-").strip())

    if current_decision:
        decisions.append(current_decision)

    if not decisions:
        # 如果没有明确决策标记，提取关键段落
        decisions = [{
            "title": "未标记决策",
            "details": [line for line in lines if len(line) > 20][:5]
        }]

    return {
        "type": "decision",
        "decisions": decisions[:10]
    }


def process_file(filepath: Path, output_dir: Path, role_markers: Dict[str, str]) -> dict:
    """处理单个文件，生成资产条目"""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"读取文件失败 {filepath}: {e}")
        return {"error": f"读取文件失败: {e}", "source_file": str(filepath)}

    # 分类并提取
    asset_type = classify_file(filepath, role_markers)
    try:
        if asset_type == "dialogue":
            data = extract_dialogue(content, role_markers)
        elif asset_type == "code":
            data = extract_code(content, filepath)
        elif asset_type == "decision":
            data = extract_decision(content)
        else:
            data = extract_document(content, filepath)
    except Exception as e:
        logger.error(f"提取失败 {filepath}: {e}")
        return {"error": f"提取失败: {e}", "source_file": str(filepath)}

    # 生成唯一ID
    file_hash = hashlib.md5(str(filepath).encode()).hexdigest()[:8]
    timestamp = datetime.datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 构建资产条目
    asset = {
        "id": f"{asset_type}_{file_hash}_{timestamp}",
        "source_file": str(filepath),
        "processed_at": datetime.datetime.now(timezone.utc).isoformat(),
        "asset_type": asset_type,
        "asset_type_cn": ASSET_TYPES[asset_type],
        "data": data
    }

    # 保存资产文件（原子写入）
    asset_file = output_dir / f"{asset['id']}.json"
    if not atomic_write(asset_file, json.dumps(asset, ensure_ascii=False, indent=2)):
        return {"error": f"写入资产文件失败: {asset_file}", "source_file": str(filepath)}

    return asset


def generate_index(assets: List[dict], output_dir: Path) -> Tuple[Path, Path]:
    """生成团队共享索引文件（JSON和Markdown）"""
    index_data = {
        "generated_at": datetime.datetime.now(timezone.utc).isoformat(),
        "total_assets": len(assets),
        "asset_summary": {},
        "assets": []
    }

    # 统计各类资产数量
    for asset in assets:
        asset_type = asset["asset_type"]
        index_data["asset_summary"][asset_type] = index_data["asset_summary"].get(asset_type, 0) + 1
        index_data["assets"].append({
            "id": asset["id"],
            "type": asset["asset_type"],
            "type_cn": asset["asset_type_cn"],
            "source": asset["source_file"],
            "processed_at": asset["processed_at"]
        })

    # 生成索引文件（原子写入）
    index_file = output_dir / "index.json"
    if not atomic_write(index_file, json.dumps(index_data, ensure_ascii=False, indent=2)):
        logger.error(f"写入索引文件失败: {index_file}")

    # 同时生成Markdown格式索引
    md_lines = [
        "# 团队记忆资产索引",
        "",
        f"生成时间: {index_data['generated_at']}",
        f"资产总数: {index_data['total_assets']}",
        "",
        "## 资产统计",
        ""
    ]

    for asset_type, count in index_data["asset_summary"].items():
        md_lines.append(f"- {ASSET_TYPES.get(asset_type, asset_type)}: {count}")

    md_lines.extend(["", "## 资产列表", ""])

    for asset in index_data["assets"]:
        md_lines.append(f"- [{asset['type_cn']}] {asset['source']} (ID: {asset['id']})")

    md_file = output_dir / "index.md"
    if not atomic_write(md_file, "\n".join(md_lines)):
        logger.error(f"写入Markdown索引失败: {md_file}")

    return index_file, md_file


def process_input(input_path: Path, output_dir: Path, asset_type: str = None,
                  role_markers: Dict[str, str] = None) -> List[dict]:
    """处理输入路径（文件或目录），支持断点续处理"""
    if role_markers is None:
        role_markers = ROLE_MARKERS

    assets = []

    # 检查输入路径
    if not input_path.exists():
        raise FileNotFoundError(f"输入路径不存在: {input_path}")

    # 收集待处理文件
    files = []
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(input_path)
        else:
            raise ValueError(f"不支持的文件类型: {input_path.suffix}")
    elif input_path.is_dir():
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(input_path.glob(f"*{ext}"))
        # 限制数量
        if len(files) > 20:
            logger.warning(f"检测到 {len(files)} 个文件，仅处理前20个")
            files = files[:20]

    if not files:
        raise ValueError(f"在 {input_path} 中未找到支持的文件")

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载断点状态
    state = load_state(output_dir)
    processed_files = set(state.get("processed", []))
    failed_files = set(state.get("failed", []))

    # 处理每个文件
    for filepath in files:
        file_str = str(filepath)
        if file_str in processed_files:
            logger.info(f"跳过已处理文件: {filepath}")
            continue

        logger.info(f"处理: {filepath}")
        try:
            asset = process_file(filepath, output_dir, role_markers)
            if "error" in asset:
                logger.error(f"  错误: {asset['error']}")
                failed_files.add(file_str)
            else:
                assets.append(asset)
                processed_files.add(file_str)
                logger.info(f"  已生成: {asset['id']}")
        except Exception as e:
            logger.error(f"  处理失败: {e}")
            failed_files.add(file_str)

        # 定期保存状态（每处理一个文件就保存）
        state = {"processed": list(processed_files), "failed": list(failed_files)}
        save_state(output_dir, state)

    return assets
