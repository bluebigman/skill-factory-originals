#!/usr/bin/env python3
"""
数据管道核心模块 - 用于数据清洗、转换和验证
支持离线自测模式，无需外部依赖
"""

import json
import hashlib
import argparse
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class DataPipeline:
    """数据管道核心类，负责数据的清洗、转换和验证"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化数据管道
        
        Args:
            config: 配置字典，包含清洗规则等
        """
        self.config = config or {}
        self.stats = {
            "processed": 0,
            "cleaned": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None
        }
    
    def clean_data(self, data: List[Dict]) -> List[Dict]:
        """
        清洗数据：去除空值、修正类型、去重
        
        Args:
            data: 原始数据列表
            
        Returns:
            清洗后的数据列表
        """
        self.stats["start_time"] = datetime.now().isoformat()
        cleaned_data = []
        seen = set()
        
        for record in data:
            try:
                # 跳过空记录
                if not record:
                    continue
                
                # 生成记录指纹用于去重
                record_str = json.dumps(record, sort_keys=True, default=str)
                fingerprint = hashlib.md5(record_str.encode()).hexdigest()
                
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                
                # 清洗每条记录
                cleaned_record = self._clean_record(record)
                if cleaned_record:
                    cleaned_data.append(cleaned_record)
                    self.stats["cleaned"] += 1
                
                self.stats["processed"] += 1
                
            except Exception as e:
                self.stats["errors"] += 1
                print(f"处理记录时出错: {e}", file=sys.stderr)
        
        self.stats["end_time"] = datetime.now().isoformat()
        return cleaned_data
    
    def _clean_record(self, record: Dict) -> Optional[Dict]:
        """
        清洗单条记录
        
        Args:
            record: 原始记录
            
        Returns:
            清洗后的记录，如果无效则返回 None
        """
        cleaned = {}
        
        for key, value in record.items():
            # 处理空值
            if value is None:
                continue
            
            # 字符串清理
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue
            
            # 数字转换
            if isinstance(value, str) and re.match(r'^-?\d+\.?\d*$', value):
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass
            
            cleaned[key] = value
        
        return cleaned if cleaned else None
    
    def transform_data(self, data: List[Dict], transformations: List[Dict]) -> List[Dict]:
        """
        应用数据转换规则
        
        Args:
            data: 输入数据
            transformations: 转换规则列表
            
        Returns:
            转换后的数据
        """
        result = data.copy()
        
        for transform in transformations:
            field = transform.get("field")
            operation = transform.get("operation")
            
            if not field or not operation:
                continue
            
            for record in result:
                if field in record:
                    try:
                        record[field] = self._apply_transform(
                            record[field], operation, transform.get("params", {})
                        )
                    except Exception as e:
                        print(f"转换字段 {field} 时出错: {e}", file=sys.stderr)
        
        return result
    
    def _apply_transform(self, value: Any, operation: str, params: Dict) -> Any:
        """
        应用单个转换操作
        
        Args:
            value: 输入值
            operation: 操作类型
            params: 操作参数
            
        Returns:
            转换后的值
        """
        if operation == "uppercase" and isinstance(value, str):
            return value.upper()
        elif operation == "lowercase" and isinstance(value, str):
            return value.lower()
        elif operation == "trim" and isinstance(value, str):
            return value.strip()
        elif operation == "multiply" and isinstance(value, (int, float)):
            factor = params.get("factor", 1)
            return value * factor
        elif operation == "add" and isinstance(value, (int, float)):
            amount = params.get("amount", 0)
            return value + amount
        elif operation == "format_date":
            # 简单日期格式化
            if isinstance(value, str):
                try:
                    date_obj = datetime.fromisoformat(value)
                    format_str = params.get("format", "%Y-%m-%d")
                    return date_obj.strftime(format_str)
                except ValueError:
                    return value
        return value
    
    def validate_data(self, data: List[Dict], rules: List[Dict]) -> Dict:
        """
        数据验证
        
        Args:
            data: 待验证数据
            rules: 验证规则列表
            
        Returns:
            验证结果字典
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "total_records": len(data),
            "valid_records": 0,
            "invalid_records": 0
        }
        
        for record in data:
            record_valid = True
            
            for rule in rules:
                field = rule.get("field")
                rule_type = rule.get("type")
                
                if field not in record:
                    if rule.get("required"):
                        validation_result["errors"].append(
                            f"记录缺少必填字段: {field}"
                        )
                        record_valid = False
                    continue
                
                value = record[field]
                
                # 类型验证
                if rule_type == "string" and not isinstance(value, str):
                    validation_result["errors"].append(
                        f"字段 {field} 应为字符串，实际为 {type(value).__name__}"
                    )
                    record_valid = False
                elif rule_type == "number" and not isinstance(value, (int, float)):
                    validation_result["errors"].append(
                        f"字段 {field} 应为数字，实际为 {type(value).__name__}"
                    )
                    record_valid = False
                elif rule_type == "min_length" and isinstance(value, str):
                    min_len = rule.get("value", 0)
                    if len(value) < min_len:
                        validation_result["errors"].append(
                            f"字段 {field} 长度小于最小值 {min_len}"
                        )
                        record_valid = False
                elif rule_type == "max_length" and isinstance(value, str):
                    max_len = rule.get("value", 100)
                    if len(value) > max_len:
                        validation_result["errors"].append(
                            f"字段 {field} 长度大于最大值 {max_len}"
                        )
                        record_valid = False
                elif rule_type == "range" and isinstance(value, (int, float)):
                    min_val = rule.get("min", float('-inf'))
                    max_val = rule.get("max", float('inf'))
                    if value < min_val or value > max_val:
                        validation_result["errors"].append(
                            f"字段 {field} 超出范围 [{min_val}, {max_val}]"
                        )
                        record_valid = False
            
            if record_valid:
                validation_result["valid_records"] += 1
            else:
                validation_result["invalid_records"] += 1
                validation_result["valid"] = False
        
        return validation_result
    
    def get_stats(self) -> Dict:
        """获取处理统计信息"""
        return self.stats


def run_selftest() -> bool:
    """
    运行自测，验证核心功能
    
    Returns:
        测试是否通过
    """
    print("开始运行自测...")
    
    # 1. 测试数据清洗
    print("\n测试1: 数据清洗")
    pipeline = DataPipeline()
    test_data = [
        {"name": "  Alice  ", "age": "25", "email": "alice@example.com"},
        {"name": "Bob", "age": "30", "email": ""},
        {"name": "  Alice  ", "age": "25", "email": "alice@example.com"},  # 重复
        {"name": None, "age": "40", "email": "carol@example.com"},  # 空值
        {"name": "Dave", "age": "not_a_number", "email": "dave@example.com"},
        {},  # 空记录
    ]
    
    cleaned = pipeline.clean_data(test_data)
    print(f"输入 {len(test_data)} 条记录，清洗后剩 {len(cleaned)} 条")
    
    assert len(cleaned) == 3, f"清洗后应剩 3 条记录，实际 {len(cleaned)}"
    assert all("email" in r for r in cleaned), "清洗后所有记录应包含 email"
    assert all(r["name"] != "" for r in cleaned), "清洗后不应有空名称"
    
    # 验证去重和空值处理
    names = [r["name"] for r in cleaned]
    assert "Alice" in names, "Alice 应存在"
    assert "Bob" in names, "Bob 应存在"
    assert "Dave" in names, "Dave 应存在"
    
    print("✓ 数据清洗测试通过")
    
    # 2. 测试数据转换
    print("\n测试2: 数据转换")
    test_transforms = [
        {"field": "name", "operation": "uppercase"},
        {"field": "age", "operation": "multiply", "params": {"factor": 2}},
    ]
    
    transformed = pipeline.transform_data(cleaned, test_transforms)
    print(f"转换后数据: {transformed}")
    
    assert transformed[0]["name"] == "ALICE", "名称应转为大写"
    assert transformed[0]["age"] == 50, "年龄应乘以2"
    
    print("✓ 数据转换测试通过")
    
    # 3. 测试数据验证
    print("\n测试3: 数据验证")
    validation_rules = [
        {"field": "name", "type": "string", "required": True},
        {"field": "age", "type": "number"},
        {"field": "email", "type": "string", "required": True},
    ]
    
    validation_result = pipeline.validate_data(cleaned, validation_rules)
    print(f"验证结果: {validation_result}")
    
    assert validation_result["valid"] == True, "所有记录应通过验证"
    assert validation_result["valid_records"] == 3, "3 条记录应全部有效"
    
    print("✓ 数据验证测试通过")
    
    # 4. 测试边缘情况
    print("\n测试4: 边缘情况")
    
    # 空数据
    empty_result = pipeline.clean_data([])
    assert len(empty_result) == 0, "空数据应返回空列表"
    
    # 单条记录
    single_data = [{"test": "value"}]
    single_result = pipeline.clean_data(single_data)
    assert len(single_result) == 1, "单条记录应正常处理"
    
    # 复杂嵌套数据
    nested_data = [
        {"id": 1, "data": {"nested": [1, 2, 3]}},
        {"id": 2, "data": {"nested": [4, 5, 6]}},
    ]
    nested_result = pipeline.clean_data(nested_data)
    assert len(nested_result) == 2, "嵌套数据应正常处理"
    
    print("✓ 边缘情况测试通过")
    
    # 5. 测试统计信息
    print("\n测试5: 统计信息")
    stats = pipeline.get_stats()
    print(f"统计信息: {stats}")
    
    assert stats["processed"] > 0, "应有已处理记录数"
    assert stats["cleaned"] > 0, "应有已清洗记录数"
    assert stats["start_time"] is not None, "应有开始时间"
    assert stats["end_time"] is not None, "应有结束时间"
    
    print("✓ 统计信息测试通过")
    
    print("\n=== 所有自测通过 ===")
    return True


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="数据管道核心模块",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --selftest          # 运行自测
  %(prog)s --input data.json   # 处理数据文件
  %(prog)s --help              # 显示帮助
        """
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测并退出"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入 JSON 数据文件路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出 JSON 文件路径"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 运行自测模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 处理数据文件模式
    if args.input:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            pipeline = DataPipeline()
            cleaned_data = pipeline.clean_data(data)
            
            if args.verbose:
                print(f"处理完成: {len(cleaned_data)} 条有效记录")
                print(f"统计: {pipeline.get_stats()}")
            
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
                print(f"结果已保存到: {args.output}")
            else:
                print(json.dumps(cleaned_data, ensure_ascii=False, indent=2))
            
        except FileNotFoundError:
            print(f"错误: 找不到文件 {args.input}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"错误: JSON 解析失败 - {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 无参数时显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()
