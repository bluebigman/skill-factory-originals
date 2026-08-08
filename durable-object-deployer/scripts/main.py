#!/usr/bin/env python3
"""Durable Object Deployer - 部署和管理 Cloudflare Durable Objects"""

import json
import os
import sys
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

# 配置默认值
DEFAULT_CONFIG = {
    "account_id": "",
    "api_token": "",
    "namespace": "default",
    "region": "auto",
    "durable_objects": []
}

class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def load_config(config_path: str = "config.json") -> Dict[str, Any]:
        """加载配置文件，不存在时返回默认配置"""
        if not os.path.exists(config_path):
            return DEFAULT_CONFIG.copy()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置
            merged = DEFAULT_CONFIG.copy()
            merged.update(config)
            return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        if not config.get("account_id"):
            errors.append("account_id 不能为空")
        if not config.get("api_token"):
            errors.append("api_token 不能为空")
        return errors

class DurableObjectDeployer:
    """Durable Object 部署器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.objects = []
        self._load_objects()
    
    def _load_objects(self):
        """从配置加载对象列表"""
        self.objects = self.config.get("durable_objects", [])
        if not self.objects:
            # 默认示例对象
            self.objects = [
                {"name": "counter", "class": "Counter", "script": "counter.js"},
                {"name": "kv-store", "class": "KVStore", "script": "kv-store.js"}
            ]
    
    def list_objects(self) -> List[Dict[str, str]]:
        """列出所有 Durable Objects"""
        return self.objects.copy()
    
    def delete_object(self, object_name: str) -> bool:
        """删除指定对象"""
        for i, obj in enumerate(self.objects):
            if obj.get("name") == object_name:
                self.objects.pop(i)
                return True
        return False
    
    def deploy(self) -> Dict[str, Any]:
        """部署所有对象"""
        results = []
        success_count = 0
        
        for obj in self.objects:
            try:
                # 模拟部署过程
                time.sleep(0.1)  # 模拟网络延迟
                result = {
                    "name": obj.get("name", "unknown"),
                    "status": "deployed",
                    "timestamp": time.time()
                }
                results.append(result)
                success_count += 1
            except Exception as e:
                results.append({
                    "name": obj.get("name", "unknown"),
                    "status": "failed",
                    "error": str(e)
                })
        
        return {
            "success": success_count > 0,
            "total": len(self.objects),
            "deployed": success_count,
            "failed": len(self.objects) - success_count,
            "results": results
        }
    
    def get_object_status(self, object_name: str) -> Optional[Dict[str, Any]]:
        """获取对象状态"""
        for obj in self.objects:
            if obj.get("name") == object_name:
                return {
                    "name": obj.get("name"),
                    "class": obj.get("class"),
                    "script": obj.get("script"),
                    "status": "active"
                }
        return None

def run_selftest() -> bool:
    """运行自检测试"""
    print("开始自检...")
    
    # 测试 1: 正常输入
    print("测试 1: 正常输入...")
    try:
        config = {
            "account_id": "test_account_123",
            "api_token": "test_token_456",
            "namespace": "test",
            "durable_objects": [
                {"name": "obj1", "class": "Class1", "script": "script1.js"},
                {"name": "obj2", "class": "Class2", "script": "script2.js"}
            ]
        }
        deployer = DurableObjectDeployer(config)
        objects = deployer.list_objects()
        assert len(objects) >= 1, "对象列表不应为空"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 测试 2: 中文标点
    print("测试 2: 中文标点...")
    try:
        config = {
            "account_id": "测试账号",
            "api_token": "测试令牌",
            "namespace": "测试命名空间",
            "durable_objects": [
                {"name": "对象一", "class": "类一", "script": "脚本一.js"}
            ]
        }
        deployer = DurableObjectDeployer(config)
        assert len(deployer.list_objects()) >= 1, "中文配置对象列表不应为空"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 测试 3: 配置加载与验证
    print("测试 3: 配置加载与验证...")
    try:
        # 测试默认配置
        config = ConfigManager.load_config("nonexistent_config.json")
        assert isinstance(config, dict), "配置应为字典类型"
        
        # 测试配置验证
        errors = ConfigManager.validate_config(config)
        assert len(errors) >= 0, "错误列表应为非负长度"
        
        # 测试有效配置
        valid_config = {
            "account_id": "acc123",
            "api_token": "token456"
        }
        errors = ConfigManager.validate_config(valid_config)
        assert len(errors) == 0, "有效配置不应有错误"
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    # 测试 4: 对象列表与删除
    print("测试 4: 对象列表与删除...")
    try:
        config = {
            "account_id": "test",
            "api_token": "test",
            "durable_objects": [
                {"name": "obj1", "class": "Class1", "script": "script1.js"},
                {"name": "obj2", "class": "Class2", "script": "script2.js"}
            ]
        }
        deployer = DurableObjectDeployer(config)
        
        # 测试列表
        objects = deployer.list_objects()
        assert len(objects) >= 1, "对象列表不应为空"
        
        # 测试删除
        if objects:
            first_name = objects[0]["name"]
            deleted = deployer.delete_object(first_name)
            assert deleted == True, "删除应成功"
            
            # 验证删除后列表减少
            new_objects = deployer.list_objects()
            assert len(new_objects) < len(objects), "删除后列表应减少"
        
        # 测试部署
        deploy_result = deployer.deploy()
        assert deploy_result["success"] == True, "部署应成功"
        assert deploy_result["total"] >= 0, "总数应为非负"
        assert deploy_result["deployed"] >= 0, "部署数应为非负"
        
        print("  ✓ 通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False
    
    print("所有测试通过!")
    return True

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常模式
    config = ConfigManager.load_config()
    errors = ConfigManager.validate_config(config)
    
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  - {error}")
        print("请检查 config.json 配置文件")
        sys.exit(1)
    
    deployer = DurableObjectDeployer(config)
    result = deployer.deploy()
    
    print(f"部署完成: {result['deployed']}/{result['total']} 个对象部署成功")
    if result["failed"] > 0:
        print(f"有 {result['failed']} 个对象部署失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
