#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
agent-memory-hub - 将文档/代码/对话保存为带时间戳的索引文件
支持四种记忆资产类型：对话(dialogue)、文档(document)、代码(code)、配置(config)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows 平台不支持 fcntl，使用备用方案


# ==================== 类型定义与常量 ====================

class MemoryType:
    """记忆类型枚举"""
    DIALOGUE = "dialogue"
    DOCUMENT = "document"
    CODE = "code"
    CONFIG = "config"

    ALL_TYPES = {DIALOGUE, DOCUMENT, CODE, CONFIG}

    # 类型对应的文件扩展名
    EXTENSIONS = {
        DIALOGUE: [".txt", ".chat", ".conversation"],
        DOCUMENT: [".md", ".rst", ".txt"],
        CODE: [".py", ".js", ".java", ".c", ".cpp", ".go", ".rs", ".ts", ".rb", ".php"],
        CONFIG: [".json", ".yaml", ".yml", ".toml", ".ini", ".conf"],
    }

    # 类型对应的默认文件扩展名
    DEFAULT_EXTENSION = {
        DIALOGUE: ".json",
        DOCUMENT: ".md",
        CODE: ".py",
        CONFIG: ".json",
    }

    @classmethod
    def validate(cls, file_type: str) -> str:
        """校验并规范化类型"""
        file_type = file_type.lower().strip()
        if file_type not in cls.ALL_TYPES:
            raise ValueError(
                f"不支持的记忆类型: '{file_type}'。支持的类型: {', '.join(sorted(cls.ALL_TYPES))}"
            )
        return file_type

    @classmethod
    def detect_from_extension(cls, file_path: str) -> str:
        """根据文件扩展名检测类型"""
        ext = os.path.splitext(file_path)[1].lower()
        for mem_type, extensions in cls.EXTENSIONS.items():
            if ext in extensions:
                return mem_type
        return cls.DIALOGUE  # 默认类型


# ==================== 文件锁实现 ====================

class FileLock:
    """跨平台文件锁，用于保护索引文件的原子操作"""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self._lock_file = None

    def __enter__(self):
        """获取文件锁"""
        # 确保锁文件所在目录存在
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)
        self._lock_file = open(self.lock_path, "w")
        
        if fcntl:
            # Unix/Linux/Mac 使用 fcntl.flock
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX)
        else:
            # Windows 使用 msvcrt 或简单的时间戳锁
            try:
                import msvcrt
                msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_LOCK, 1)
            except (ImportError, OSError):
                # 最后备选：使用文件存在性作为锁（不推荐，但保证跨平台）
                lock_path = self.lock_path + ".lock"
                while os.path.exists(lock_path):
                    time.sleep(0.1)
                with open(lock_path, "w") as f:
                    f.write(str(os.getpid()))
                self._lock_file = open(lock_path, "r")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放文件锁"""
        if self._lock_file:
            if fcntl:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
            else:
                try:
                    import msvcrt
                    msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                except (ImportError, OSError):
                    # 删除锁文件
                    lock_path = self.lock_path + ".lock"
                    if os.path.exists(lock_path):
                        os.remove(lock_path)
            self._lock_file.close()
            self._lock_file = None
        return False


# ==================== 核心功能 ====================

def load_spec(spec_path: str) -> dict:
    """加载 spec 文件（此处为简化实现，实际可从 JSON/YAML 读取）"""
    spec = {
        "name": "agent-memory-hub",
        "version": "1.0.0",
        "description": "将文档/代码/对话保存为带时间戳的索引文件",
        "trigger": ["memory", "remember", "save_memory", "store"],
        "output_dir": "memory_hub",
        "index_file": "index.json",
    }
    if spec_path and os.path.exists(spec_path):
        # 简单解析，实际可扩展
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 尝试提取 output_dir
        m = re.search(r'output_dir\s*[:=]\s*["\']([^"\']+)["\']', content)
        if m:
            spec["output_dir"] = m.group(1)
        m = re.search(r'index_file\s*[:=]\s*["\']([^"\']+)["\']', content)
        if m:
            spec["index_file"] = m.group(1)
    return spec


def match_trigger(text: str, spec: dict) -> bool:
    """判断文本是否触发记忆保存"""
    triggers = spec.get("trigger", [])
    for t in triggers:
        if t.lower() in text.lower():
            return True
    return False


def generate_id(content: str, full_hash: bool = False) -> str:
    """
    生成基于内容哈希的 ID
    使用 SHA-256，取前 16 位十六进制（64 位），碰撞概率极低
    如果 full_hash=True，返回完整 SHA-256 哈希
    """
    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if full_hash:
        return sha256
    return sha256[:16]


def save_memory(
    content: str,
    file_type: str,
    output_dir: str,
    index_file: str,
    metadata: Optional[Dict] = None
) -> str:
    """
    保存记忆内容到文件，并更新索引
    返回生成的记忆 ID
    
    参数:
        content: 记忆内容
        file_type: 记忆类型 (dialogue/document/code/config)
        output_dir: 输出目录
        index_file: 索引文件名
        metadata: 附加元数据
    """
    # 校验类型
    file_type = MemoryType.validate(file_type)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成时间戳和 ID
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
    content_hash = generate_id(content, full_hash=True)
    short_hash = content_hash[:16]
    
    # 生成唯一 ID（使用 UUID4 避免碰撞）
    memory_id = f"{file_type}_{short_hash}_{uuid.uuid4().hex[:8]}"
    
    # 根据类型选择文件扩展名
    ext = MemoryType.DEFAULT_EXTENSION[file_type]
    filename = f"{memory_id}{ext}"
    filepath = os.path.join(output_dir, filename)
    
    # 根据类型格式化内容
    if file_type == MemoryType.DIALOGUE:
        # 对话保存为 JSON 格式
        dialogue_data = {
            "type": "dialogue",
            "timestamp": timestamp,
            "content": content,
            "metadata": metadata or {}
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    elif file_type == MemoryType.CODE:
        # 代码保存为原始文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    elif file_type == MemoryType.CONFIG:
        # 配置保存为 JSON 格式
        try:
            # 尝试解析为 JSON
            config_data = json.loads(content)
        except json.JSONDecodeError:
            # 如果不是 JSON，保存原始内容
            config_data = {"content": content}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    else:  # DOCUMENT
        # 文档保存为 Markdown
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    
    # 更新索引文件（使用文件锁保证原子性）
    index_path = os.path.join(output_dir, index_file)
    lock_path = index_path + ".lock"
    
    with FileLock(lock_path):
        # 读取现有索引
        index_data = []
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                # 索引文件损坏时，备份并重新开始
                backup_path = index_path + f".bak_{timestamp}"
                try:
                    os.rename(index_path, backup_path)
                except OSError:
                    pass
                index_data = []
        
        # 添加新条目
        entry = {
            "id": memory_id,
            "type": file_type,
            "timestamp": timestamp,
            "file": filename,
            "path": filepath,
            "content_hash": content_hash,  # 保存完整哈希用于去重校验
            "metadata": metadata or {},
        }
        index_data.append(entry)
        
        # 写入索引
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    return memory_id


def process_file(file_path: str, output_dir: str, index_file: str) -> str:
    """处理单个文件，返回生成的记忆 ID"""
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 根据扩展名判断类型
    file_type = MemoryType.detect_from_extension(file_path)
    
    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 附加文件元数据
    metadata = {
        "source_file": file_path,
        "file_size": os.path.getsize(file_path),
    }
    
    return save_memory(content, file_type, output_dir, index_file, metadata)


def selftest() -> int:
    """自检函数：验证核心功能"""
    print("=" * 60)
    print("agent-memory-hub 自检开始")
    print("=" * 60)
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 测试文件创建
            print("\n[1/5] 创建测试文件...")
            test_doc = os.path.join(tmpdir, "test_doc.md")
            with open(test_doc, "w", encoding="utf-8") as f:
                f.write("# 测试文档\n这是用于自检的文档内容。")
            
            test_code = os.path.join(tmpdir, "test_code.py")
            with open(test_code, "w", encoding="utf-8") as f:
                f.write("def hello():\n    print('hello')\n")
            
            test_dialogue = os.path.join(tmpdir, "test_dialogue.txt")
            with open(test_dialogue, "w", encoding="utf-8") as f:
                f.write("用户: 你好\n助手: 你好，有什么可以帮助？")
            
            test_config = os.path.join(tmpdir, "test_config.json")
            with open(test_config, "w", encoding="utf-8") as f:
                f.write('{"key": "value", "number": 42}')
            
            print("  测试文件创建完成")
            
            # 2. 测试类型检测
            print("\n[2/5] 测试类型检测...")
            assert MemoryType.detect_from_extension(test_doc) == MemoryType.DOCUMENT, "文档类型检测失败"
            assert MemoryType.detect_from_extension(test_code) == MemoryType.CODE, "代码类型检测失败"
            assert MemoryType.detect_from_extension(test_dialogue) == MemoryType.DIALOGUE, "对话类型检测失败"
            assert MemoryType.detect_from_extension(test_config) == MemoryType.CONFIG, "配置类型检测失败"
            print("  类型检测通过")
            
            # 3. 测试类型校验
            print("\n[3/5] 测试类型校验...")
            try:
                MemoryType.validate("invalid_type")
                print("  错误：应该拒绝未知类型")
                return 1
            except ValueError as e:
                print(f"  正确拒绝未知类型: {e}")
            
            # 4. 测试核心保存功能
            print("\n[4/5] 测试核心保存功能...")
            output_dir = os.path.join(tmpdir, "memory_hub")
            index_file = "index.json"
            
            # 处理所有文件
            test_files = [test_doc, test_code, test_dialogue, test_config]
            memory_ids = []
            for f in test_files:
                print(f"  处理: {os.path.basename(f)}")
                memory_id = process_file(f, output_dir, index_file)
                memory_ids.append(memory_id)
                print(f"    生成 ID: {memory_id}")
            
            # 验证索引文件
            index_path = os.path.join(output_dir, index_file)
            assert os.path.exists(index_path), "索引文件未生成"
            
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            assert len(index_data) == 4, f"索引条目数应为 4，实际 {len(index_data)}"
            
            # 验证每个条目
            for entry in index_data:
                required_fields = ["id", "type", "timestamp", "file", "path", "content_hash"]
                for field in required_fields:
                    assert field in entry, f"索引条目缺少字段: {field}"
                
                # 验证文件存在
                assert os.path.exists(entry["path"]), f"索引指向的文件不存在: {entry['path']}"
                
                # 验证类型
                assert entry["type"] in MemoryType.ALL_TYPES, f"无效的类型: {entry['type']}"
                
                # 验证文件扩展名
                ext = os.path.splitext(entry["file"])[1]
                expected_ext = MemoryType.DEFAULT_EXTENSION[entry["type"]]
                assert ext == expected_ext, f"文件扩展名不匹配: {ext} != {expected_ext}"
            
            print("  核心保存功能测试通过")
            
            # 5. 测试并发安全
            print("\n[5/5] 测试并发安全...")
            import threading
            
            def concurrent_save(idx):
                content = f"并发测试内容 {idx}"
                try:
                    save_memory(content, MemoryType.DOCUMENT, output_dir, index_file)
                except Exception as e:
                    print(f"  并发保存失败: {e}")
                    raise
            
            threads = []
            for i in range(10):
                t = threading.Thread(target=concurrent_save, args=(i,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # 验证并发后的索引完整性
            with open(index_path, "r", encoding="utf-8") as f:
                final_index = json.load(f)
            
            assert len(final_index) == 14, f"并发后索引条目数应为 14，实际 {len(final_index)}"
            
            # 验证没有重复 ID
            ids = [entry["id"] for entry in final_index]
            assert len(ids) == len(set(ids)), "存在重复的 ID"
            
            print("  并发安全测试通过")
            
            # 所有测试通过
            print("\n" + "=" * 60)
            print("自检通过！所有测试均成功。")
            print("=" * 60)
            return 0
            
    except Exception as e:
        print(f"\n自检失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(description="agent-memory-hub - 记忆保存工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--spec", type=str, default="", help="spec 文件路径")
    parser.add_argument("--input", type=str, nargs="+", help="输入文件路径")
    parser.add_argument("--output-dir", type=str, default="memory_hub", help="输出目录")
    parser.add_argument("--index-file", type=str, default="index.json", help="索引文件名")
    parser.add_argument("--type", type=str, choices=list(MemoryType.ALL_TYPES), 
                       help="记忆类型（用于直接输入内容时）")
    parser.add_argument("--content", type=str, help="直接输入内容（与 --type 配合使用）")

    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    # 加载 spec
    spec = load_spec(args.spec)
    output_dir = args.output_dir or spec.get("output_dir", "memory_hub")
    index_file = args.index_file or spec.get("index_file", "index.json")

    # 处理直接
