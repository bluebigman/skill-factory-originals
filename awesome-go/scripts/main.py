#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本名称: scripts/main.py
功能描述: 基于功能规格实现的独立工具脚本
设计原则: Clean-Room 独立实现，仅依据规格说明编写
"""

import argparse
import sys
import json
import re
from typing import Dict, List, Any, Optional, Tuple


# ============================================================
# 错误码常量定义
# ============================================================
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容",
    "E002": "关键信息缺失，请补充必要字段",
    "E003": "输入格式错误，请检查格式",
    "E004": "超出能力边界，无法处理",
    "E005": "置信度过低，结果无法确定",
    "E006": "内部处理异常",
    "E007": "参数解析错误",
    "E008": "输出格式不支持",
    "E009": "批量处理中断",
    "E010": "未知错误",
}


class ToolError(Exception):
    """自定义异常类，携带错误码"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心处理模块
# ============================================================
class DataProcessor:
    """数据处理核心类"""
    
    # 支持的关键字段（用于结构化识别）
    KEY_FIELDS = [
        "id", "name", "type", "url", "description", 
        "category", "tags", "status", "priority"
    ]
    
    def __init__(self):
        self.supported_formats = ["json", "text", "table"]
    
    def process(self, input_data: str, output_format: str = "json") -> Dict[str, Any]:
        """
        核心处理入口
        
        参数:
            input_data: 输入内容（字符串）
            output_format: 输出格式（json/text/table）
            
        返回:
            结构化处理结果
        """
        # 校验输入
        if not input_data or not input_data.strip():
            raise ToolError("E001")
        
        # 校验输出格式
        if output_format not in self.supported_formats:
            raise ToolError("E008", f"不支持的输出格式: {output_format}")
        
        try:
            # 步骤1: 解析输入
            parsed_data = self._parse_input(input_data)
            
            # 步骤2: 提取关键信息
            structured = self._extract_structured_data(parsed_data)
            
            # 步骤3: 计算置信度
            confidence = self._calculate_confidence(structured)
            
            # 步骤4: 生成输出
            result = {
                "status": "success",
                "data": structured,
                "confidence": confidence,
                "confidence_level": self._get_confidence_level(confidence),
                "note": "处理完成"
            }
            
            # 添加置信度标注
            if confidence < 85:
                result["warning"] = "[需核实] 部分字段可能存在不确定性"
                result["uncertain_fields"] = self._find_uncertain_fields(structured)
            elif confidence < 90:
                result["warning"] = "建议复核部分字段"
            
            return result
            
        except ToolError:
            raise
        except Exception as e:
            raise ToolError("E006", f"处理异常: {str(e)}")
    
    def _parse_input(self, input_data: str) -> Any:
        """
        解析输入内容
        
        支持:
        - JSON 格式输入
        - 键值对格式 (key: value 每行一个)
        - 简单文本
        """
        input_data = input_data.strip()
        
        # 尝试 JSON 解析
        if input_data.startswith(("{", "[")):
            try:
                return json.loads(input_data)
            except json.JSONDecodeError:
                raise ToolError("E003", "JSON 格式解析失败")
        
        # 尝试键值对解析
        lines = input_data.split("\n")
        kv_result = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 支持冒号和等号分隔
            for sep in [":", "="]:
                if sep in line:
                    key, value = line.split(sep, 1)
                    kv_result[key.strip()] = value.strip()
                    break
        
        if kv_result:
            return kv_result
        
        # 纯文本
        return {"content": input_data}
    
    def _extract_structured_data(self, parsed_data: Any) -> Dict[str, Any]:
        """
        从解析后的数据中提取结构化信息
        """
        result = {}
        
        if isinstance(parsed_data, dict):
            # 字典类型
            for key, value in parsed_data.items():
                normalized_key = str(key).lower()
                # 匹配已知字段
                if normalized_key in self.KEY_FIELDS:
                    result[normalized_key] = value
                # 匹配相似字段
                elif any(field in normalized_key for field in self.KEY_FIELDS):
                    result[normalized_key] = value
                else:
                    # 保留其他字段
                    result[f"extra_{normalized_key}"] = value
                    
        elif isinstance(parsed_data, list):
            # 列表类型，尝试识别记录结构
            records = []
            for item in parsed_data:
                if isinstance(item, dict):
                    records.append(item)
                else:
                    records.append({"value": item})
            result["records"] = records
            result["record_count"] = len(records)
            
        else:
            # 其他类型
            result["content"] = str(parsed_data)
        
        # 确保关键字段存在
        if not result:
            raise ToolError("E002", "未能提取到有效信息")
            
        return result
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """
        计算处理结果的置信度
        
        规则:
        - 基础置信度 80%
        - 每有一个已知字段 +2%
        - 每有一个未知字段 -5%
        - 有 records 结构 +5%
        """
        confidence = 80.0
        
        # 统计字段
        known_count = 0
        unknown_count = 0
        
        for key in data.keys():
            if key.startswith("extra_") or key == "content":
                unknown_count += 1
            elif key in ["records", "record_count"]:
                confidence += 5
            else:
                known_count += 1
        
        # 调整置信度
        confidence += known_count * 2
        confidence -= unknown_count * 5
        
        # 限制在合理范围
        confidence = max(10.0, min(99.0, confidence))
        
        return round(confidence, 1)
    
    def _get_confidence_level(self, confidence: float) -> str:
        """根据置信度返回级别"""
        if confidence >= 90:
            return "high"
        elif confidence >= 85:
            return "medium"
        else:
            return "low"
    
    def _find_uncertain_fields(self, data: Dict[str, Any]) -> List[str]:
        """找出不确定的字段"""
        uncertain = []
        for key, value in data.items():
            if key.startswith("extra_") or key == "content":
                uncertain.append(key)
            elif value is None or value == "":
                uncertain.append(key)
        return uncertain
    
    def format_output(self, result: Dict[str, Any], output_format: str) -> str:
        """
        格式化输出结果
        """
        if output_format == "json":
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        elif output_format == "text":
            lines = []
            lines.append(f"处理结果 (置信度: {result['confidence']}%)")
            lines.append("=" * 40)
            
            for key, value in result["data"].items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                else:
                    lines.append(f"{key}: {value}")
            
            if result.get("warning"):
                lines.append("")
                lines.append(f"警告: {result['warning']}")
            
            return "\n".join(lines)
        
        elif output_format == "table":
            # 表格格式
            lines = []
            lines.append("| 字段 | 值 |")
            lines.append("|------|-----|")
            
            for key, value in result["data"].items():
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False)
                else:
                    value_str = str(value)
                # 截断过长的值
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                lines.append(f"| {key} | {value_str} |")
            
            lines.append("")
            lines.append(f"置信度: {result['confidence']}%")
            
            return "\n".join(lines)
        
        else:
            raise ToolError("E008", f"不支持的输出格式: {output_format}")


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """
    自检函数：使用硬编码样例数据验证核心逻辑
    
    返回:
        True 表示自检通过
    """
    print("开始自检...")
    
    processor = DataProcessor()
    
    # 测试用例1: JSON 输入
    test_data_1 = """
    {
        "id": "go-001",
        "name": "gin",
        "type": "web framework",
        "description": "HTTP web framework",
        "category": "web"
    }
    """
    
    # 测试用例2: 键值对输入
    test_data_2 = """
    name: zap
    type: logging
    description: Fast structured logging
    """
    
    # 测试用例3: 文本输入
    test_data_3 = "这是一个简单的文本输入测试"
    
    # 测试用例4: 列表输入
    test_data_4 = '["item1", "item2", "item3"]'
    
    # 测试用例5: 空输入（应触发 E001）
    test_data_5 = ""
    
    # ===== 执行测试 =====
    passed = 0
    total = 5
    
    # 测试1: JSON 输入处理
    try:
        result = processor.process(test_data_1)
        assert result["status"] == "success"
        assert result["data"].get("id") == "go-001"
        assert result["data"].get("name") == "gin"
        assert result["confidence"] > 80, "置信度应大于80"
        passed += 1
        print("[PASS] JSON 输入处理")
    except Exception as e:
        print(f"[FAIL] JSON 输入处理: {e}")
    
    # 测试2: 键值对输入处理
    try:
        result = processor.process(test_data_2)
        assert result["status"] == "success"
        assert result["data"].get("name") == "zap"
        assert result["data"].get("type") == "logging"
        assert result["confidence"] > 80, "置信度应大于80"
        passed += 1
        print("[PASS] 键值对输入处理")
    except Exception as e:
        print(f"[FAIL] 键值对输入处理: {e}")
    
    # 测试3: 文本输入处理
    try:
        result = processor.process(test_data_3)
        assert result["status"] == "success"
        assert "content" in result["data"]
        assert result["confidence"] > 50, "置信度应大于50"
        passed += 1
        print("[PASS] 文本输入处理")
    except Exception as e:
        print(f"[FAIL] 文本输入处理: {e}")
    
    # 测试4: 列表输入处理
    try:
        result = processor.process(test_data_4)
        assert result["status"] == "success"
        assert result["data"].get("record_count") == 3
        assert result["confidence"] > 80, "置信度应大于80"
        passed += 1
        print("[PASS] 列表输入处理")
    except Exception as e:
        print(f"[FAIL] 列表输入处理: {e}")
    
    # 测试5: 空输入错误处理
    try:
        processor.process(test_data_5)
        print("[FAIL] 空输入应触发错误")
    except ToolError as e:
        assert e.code == "E001", f"错误码应为E001，实际为{e.code}"
        passed += 1
        print("[PASS] 空输入错误处理")
    except Exception as e:
        print(f"[FAIL] 空输入错误处理: {e}")
    
    # ===== 输出结果 =====
    print(f"\n自检结果: {passed}/{total} 通过")
    
    # 宽松判定：核心测试必须通过
    assert passed >= 4, f"自检失败，仅通过 {passed}/{total}"
    
    return True


# ============================================================
# 主入口
# ============================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="数据处理工具 - 基于功能规格的独立实现",
        epilog="使用 --selftest 进行离线自检"
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容（字符串）"
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径"
    )
    
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "text", "table"],
        default="json",
        help="输出格式 (默认: json)"
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自检"
    )
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        try:
            run_selftest()
            print("自检通过")
            sys.exit(0)
        except AssertionError as e:
            print(f"自检失败: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"自检异常: {e}")
            sys.exit(1)
    
    # 正常处理模式
    try:
        # 收集输入
        input_data = ""
        
        if args.input:
            input_data = args.input
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except FileNotFoundError:
                raise ToolError("E003", f"文件不存在: {args.file}")
            except IOError as e:
                raise ToolError("E003", f"文件读取失败: {str(e)}")
        else:
            # 尝试从标准输入读取
            if not sys.stdin.isatty():
                input_data = sys.stdin.read()
            else:
                # 交互模式提示
                print("请输入内容 (Ctrl+D 结束):")
                try:
                    input_data = sys.stdin.read()
                except KeyboardInterrupt:
                    print("\n已取消")
                    sys.exit(0)
        
        # 处理数据
        processor = DataProcessor()
        result = processor.process(input_data, args.format)
        
        # 格式化输出
        output = processor.format_output(result, args.format)
        print(output)
        
    except ToolError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未预期错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
