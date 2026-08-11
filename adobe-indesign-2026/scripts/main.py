#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量文件处理脚本 - 支持批处理、工作流优化和自检功能"""

import os
import sys
import json
import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class BatchProcessor:
    """批处理处理器"""
    
    def __init__(self, input_files: List[str], output_dir: str = "output"):
        self.input_files = input_files
        self.output_dir = output_dir
        self.results = []
        
    def process(self) -> Dict[str, Any]:
        """处理所有输入文件"""
        if not self.input_files:
            raise ValueError("输入文件列表为空")
            
        os.makedirs(self.output_dir, exist_ok=True)
        
        for file_path in self.input_files:
            result = self._process_single_file(file_path)
            self.results.append(result)
            
        return {
            "status": "success",
            "processed": len(self.results),
            "results": self.results
        }
    
    def _process_single_file(self, file_path: str) -> Dict[str, Any]:
        """处理单个文件"""
        file_path = Path(file_path)
        if not file_path.exists():
            return {
                "file": str(file_path),
                "status": "error",
                "error": "文件不存在"
            }
            
        # 读取文件内容
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='gbk', errors='replace')
        except Exception as e:
            return {
                "file": str(file_path),
                "status": "error",
                "error": str(e)
            }
            
        # 计算文件哈希
        file_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 生成输出文件名
        output_name = f"{file_path.stem}_{file_hash[:8]}{file_path.suffix}"
        output_path = Path(self.output_dir) / output_name
        
        # 写入处理后的内容
        processed_content = self._process_content(content)
        output_path.write_text(processed_content, encoding='utf-8')
        
        return {
            "file": str(file_path),
            "status": "success",
            "output": str(output_path),
            "size": len(content)
        }
    
    def _process_content(self, content: str) -> str:
        """处理文件内容"""
        # 这里可以进行各种文本处理
        # 例如：去除多余空白、统一换行符等
        lines = content.splitlines()
        processed_lines = []
        for line in lines:
            # 去除行首尾空白
            line = line.strip()
            if line:  # 跳过空行
                processed_lines.append(line)
        return '\n'.join(processed_lines)


class WorkflowOptimizer:
    """工作流优化器"""
    
    def __init__(self, tasks: List[Dict[str, Any]]):
        self.tasks = tasks
        self.optimized_order = []
        
    def optimize(self) -> List[Dict[str, Any]]:
        """优化任务执行顺序"""
        if not self.tasks:
            return []
            
        # 按优先级排序
        sorted_tasks = sorted(self.tasks, key=lambda x: x.get('priority', 0), reverse=True)
        
        # 按依赖关系调整
        self.optimized_order = self._resolve_dependencies(sorted_tasks)
        return self.optimized_order
    
    def _resolve_dependencies(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析任务依赖关系"""
        result = []
        visited = set()
        
        def visit(task):
            task_id = task.get('id')
            if task_id in visited:
                return
            visited.add(task_id)
            
            # 先处理依赖
            dependencies = task.get('dependencies', [])
            for dep_id in dependencies:
                for t in tasks:
                    if t.get('id') == dep_id:
                        visit(t)
                        break
            
            result.append(task)
        
        for task in tasks:
            visit(task)
            
        return result


def generate_script(template: str, params: Dict[str, Any]) -> str:
    """生成脚本内容"""
    script = template
    for key, value in params.items():
        placeholder = "{{" + key + "}}"
        script = script.replace(placeholder, str(value))
    return script


def run_batch_processing(input_files: List[str], output_dir: str = "output") -> Dict[str, Any]:
    """运行批处理"""
    try:
        processor = BatchProcessor(input_files, output_dir)
        return processor.process()
    except ValueError as e:
        return {
            "status": "error",
            "error": f"E004: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"E006: 批处理流程生成失败: {str(e)}"
        }


def run_workflow_optimization(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """运行工作流优化"""
    try:
        optimizer = WorkflowOptimizer(tasks)
        optimized = optimizer.optimize()
        return {
            "status": "success",
            "optimized_order": [t.get('id') for t in optimized]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def run_selftest() -> bool:
    """运行自检测试"""
    print("[RUN] 开始自检...")
    all_passed = True
    
    # 测试1: 脚本生成测试
    try:
        template = "print('Hello, {{name}}!')"
        params = {"name": "World"}
        script = generate_script(template, params)
        assert "Hello, World!" in script, "脚本生成失败"
        print("[PASS] 脚本生成测试")
    except Exception as e:
        print(f"[FAIL] 脚本生成测试: {e}")
        all_passed = False
    
    # 测试2: 批处理测试
    try:
        # 创建临时测试文件
        test_dir = Path("test_temp")
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "test.txt"
        test_file.write_text("  Hello World  \n\n  Test Content  \n", encoding='utf-8')
        
        result = run_batch_processing([str(test_file)], "test_output")
        assert result["status"] == "success", f"批处理失败: {result.get('error')}"
        assert result["processed"] >= 1, "处理文件数不正确"
        print("[PASS] 批处理测试")
        
        # 清理
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)
        shutil.rmtree("test_output", ignore_errors=True)
    except Exception as e:
        print(f"[FAIL] 批处理测试: {e}")
        all_passed = False
    
    # 测试3: 工作流优化测试
    try:
        tasks = [
            {"id": "task1", "priority": 1, "dependencies": []},
            {"id": "task2", "priority": 2, "dependencies": ["task1"]},
            {"id": "task3", "priority": 3, "dependencies": ["task2"]}
        ]
        result = run_workflow_optimization(tasks)
        assert result["status"] == "success", "工作流优化失败"
        assert len(result["optimized_order"]) >= 3, "优化结果不完整"
        print("[PASS] 工作流优化测试")
    except Exception as e:
        print(f"[FAIL] 工作流优化测试: {e}")
        all_passed = False
    
    # 测试4: 空输入处理测试
    try:
        result = run_batch_processing([])
        # 空输入应该返回错误状态，而不是抛出异常
        assert result["status"] == "error", "空输入应该返回错误状态"
        assert "E004" in result.get("error", ""), "错误码不正确"
        print("[PASS] 空输入处理测试")
    except Exception as e:
        print(f"[FAIL] 空输入处理测试: {e}")
        all_passed = False
    
    # 测试5: 中文标点处理测试
    try:
        content = "你好，世界！这是一个测试。"
        processor = BatchProcessor(["dummy.txt"])
        processed = processor._process_content(content)
        assert len(processed) > 0, "中文内容处理失败"
        print("[PASS] 中文标点处理测试")
    except Exception as e:
        print(f"[FAIL] 中文标点处理测试: {e}")
        all_passed = False
    
    # 测试6: 超长输入处理测试
    try:
        long_content = "x" * 10000
        processor = BatchProcessor(["dummy.txt"])
        processed = processor._process_content(long_content)
        assert len(processed) >= 10000, "超长内容处理失败"
        print("[PASS] 超长输入处理测试")
    except Exception as e:
        print(f"[FAIL] 超长输入处理测试: {e}")
        all_passed = False
    
    print(f"\n自检完成: {'全部通过' if all_passed else '存在失败'}")
    return all_passed


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="批量文件处理工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--batch", nargs="+", help="批处理文件列表")
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument("--optimize", help="工作流优化JSON文件")
    parser.add_argument("--generate", help="生成脚本模板")
    parser.add_argument("--params", help="模板参数JSON")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if args.batch:
        result = run_batch_processing(args.batch, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if args.optimize:
        try:
            with open(args.optimize, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            result = run_workflow_optimization(tasks)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"错误: {e}")
    
    if args.generate:
        try:
            template = args.generate
            params = json.loads(args.params) if args.params else {}
            script = generate_script(template, params)
            print(script)
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
