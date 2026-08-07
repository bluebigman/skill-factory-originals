#!/usr/bin/env python3
"""
主程序入口脚本
包含自测试功能，可离线运行
"""

import argparse
import sys
import json
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class DataProcessor:
    """数据处理核心类"""
    
    def __init__(self):
        self.data_store = {}
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入数据"""
        try:
            # 基本验证
            if not isinstance(data, dict):
                raise ValueError("输入必须是字典类型")
            
            # 处理数据
            result = {
                "timestamp": datetime.now().isoformat(),
                "processed": True,
                "data": data
            }
            
            # 计算数据指纹
            data_str = json.dumps(data, sort_keys=True)
            result["fingerprint"] = hashlib.sha256(data_str.encode()).hexdigest()[:16]
            
            # 存储数据
            self.data_store[result["fingerprint"]] = data
            
            return result
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "processed": False,
                "error": str(e)
            }
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证数据格式"""
        required_fields = ["name", "value"]
        return all(field in data for field in required_fields)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        return {
            "total_records": len(self.data_store),
            "unique_keys": len(set(self.data_store.keys())),
            "last_updated": datetime.now().isoformat()
        }


class ConfigManager:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "debug": False,
        "max_retries": 3,
        "timeout": 30
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
            except (json.JSONDecodeError, OSError) as e:
                print(f"警告: 配置文件加载失败: {e}", file=sys.stderr)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        self.config[key] = value
    
    def save(self) -> bool:
        """保存配置到文件"""
        if not self.config_path:
            return False
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False


class Logger:
    """日志记录类"""
    
    def __init__(self, level: str = "INFO"):
        self.level = level
        self.logs: List[Dict[str, str]] = []
    
    def log(self, message: str, level: str = "INFO") -> None:
        """记录日志"""
        if self._should_log(level):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            }
            self.logs.append(log_entry)
            print(f"[{level}] {message}")
    
    def _should_log(self, level: str) -> bool:
        """判断是否应该记录该级别日志"""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        current_idx = levels.index(self.level) if self.level in levels else 1
        target_idx = levels.index(level) if level in levels else 1
        return target_idx >= current_idx
    
    def get_logs(self) -> List[Dict[str, str]]:
        """获取所有日志"""
        return self.logs
    
    def export_logs(self, filepath: str) -> bool:
        """导出日志到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False


def run_selftest() -> bool:
    """运行自测试"""
    print("=" * 50)
    print("开始运行自测试...")
    print("=" * 50)
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 数据处理器
    print("\n1. 测试 DataProcessor")
    try:
        processor = DataProcessor()
        test_data = {"name": "test", "value": 123}
        result = processor.process(test_data)
        
        assert result["processed"] == True, "数据处理失败"
        assert result["fingerprint"], "指纹为空"
        assert len(result["fingerprint"]) == 16, "指纹长度错误"
        
        # 测试验证功能
        assert processor.validate(test_data) == True, "数据验证失败"
        assert processor.validate({"name": "test"}) == False, "数据验证应失败"
        
        # 测试统计
        stats = processor.get_statistics()
        assert stats["total_records"] == 1, "统计记录数错误"
        
        print("   ✓ DataProcessor 测试通过")
        tests_passed += 1
    except Exception as e:
        print(f"   ✗ DataProcessor 测试失败: {e}")
        tests_failed += 1
    
    # 测试2: 配置管理器
    print("\n2. 测试 ConfigManager")
    try:
        config_mgr = ConfigManager()
        assert config_mgr.get("version") == "1.0.0", "默认版本错误"
        assert config_mgr.get("debug") == False, "默认调试模式错误"
        
        # 测试设置和获取
        config_mgr.set("test_key", "test_value")
        assert config_mgr.get("test_key") == "test_value", "配置设置失败"
        
        print("   ✓ ConfigManager 测试通过")
        tests_passed += 1
    except Exception as e:
        print(f"   ✗ ConfigManager 测试失败: {e}")
        tests_failed += 1
    
    # 测试3: 日志记录器
    print("\n3. 测试 Logger")
    try:
        logger = Logger("DEBUG")
        logger.log("测试日志", "INFO")
        logger.log("调试日志", "DEBUG")
        logger.log("错误日志", "ERROR")
        
        logs = logger.get_logs()
        assert len(logs) == 3, "日志数量错误"
        assert logs[0]["level"] == "INFO", "日志级别错误"
        
        print("   ✓ Logger 测试通过")
        tests_passed += 1
    except Exception as e:
        print(f"   ✗ Logger 测试失败: {e}")
        tests_failed += 1
    
    # 测试4: 错误处理
    print("\n4. 测试错误处理")
    try:
        processor = DataProcessor()
        result = processor.process("invalid_data")  # 传入非字典
        assert result["processed"] == False, "错误处理失败"
        assert "error" in result, "错误信息缺失"
        
        print("   ✓ 错误处理测试通过")
        tests_passed += 1
    except Exception as e:
        print(f"   ✗ 错误处理测试失败: {e}")
        tests_failed += 1
    
    # 测试5: 数据完整性
    print("\n5. 测试数据完整性")
    try:
        processor = DataProcessor()
        data1 = {"name": "item1", "value": 100}
        data2 = {"name": "item2", "value": 200}
        
        result1 = processor.process(data1)
        result2 = processor.process(data2)
        
        # 确保指纹不同
        assert result1["fingerprint"] != result2["fingerprint"], "指纹应不同"
        
        # 确保存储正确
        stats = processor.get_statistics()
        assert stats["total_records"] == 2, "记录数应为2"
        
        print("   ✓ 数据完整性测试通过")
        tests_passed += 1
    except Exception as e:
        print(f"   ✗ 数据完整性测试失败: {e}")
        tests_failed += 1
    
    # 测试总结
    print("\n" + "=" * 50)
    print(f"测试完成: {tests_passed} 通过, {tests_failed} 失败")
    print("=" * 50)
    
    return tests_failed == 0


def main() -> int:
    """主程序入口"""
    parser = argparse.ArgumentParser(description="主程序脚本")
    parser.add_argument("--selftest", action="store_true", help="运行自测试")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--input", type=str, help="输入文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--verbose", action="store_true", help="详细输出模式")
    
    args = parser.parse_args()
    
    # 运行自测试
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1
    
    # 正常模式运行
    print("主程序运行中...")
    
    # 初始化组件
    config_mgr = ConfigManager(args.config)
    logger = Logger("DEBUG" if args.verbose else "INFO")
    processor = DataProcessor()
    
    logger.log(f"配置版本: {config_mgr.get('version')}")
    
    # 处理输入数据
    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.log(f"读取到输入数据: {len(data)} 条")
            
            # 处理数据
            results = []
            for item in data:
                result = processor.process(item)
                results.append(result)
            
            # 输出结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                logger.log(f"结果已保存到: {args.output}")
            else:
                print(json.dumps(results, indent=2, ensure_ascii=False))
                
        except Exception as e:
            logger.log(f"处理数据时出错: {e}", "ERROR")
            return 1
    else:
        # 演示模式
        demo_data = [
            {"name": "示例1", "value": 100},
            {"name": "示例2", "value": 200},
            {"name": "示例3", "value": 300}
        ]
        
        logger.log("运行演示模式...")
        for item in demo_data:
            result = processor.process(item)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        logger.log(f"处理完成，共 {len(demo_data)} 条记录")
    
    # 显示统计信息
    stats = processor.get_statistics()
    print(f"\n统计数据: 共 {stats['total_records']} 条记录")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
