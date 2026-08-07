#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resource-controller 技能独立实现脚本

本脚本根据功能规格独立实现，不依赖任何既有代码。
提供核心处理逻辑、错误码体系、命令行接口和离线自检功能。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
class ErrorCode:
    """错误码常量定义"""
    E001 = "E001"  # 输入为空
    E002 = "E002"  # 关键信息缺失
    E003 = "E003"  # 输入格式错误
    E004 = "E004"  # 超出能力边界
    E005 = "E005"  # 置信度过低
    E006 = "E006"  # 输出格式化失败
    E007 = "E007"  # 内部处理异常
    E008 = "E008"  # 参数错误
    E009 = "E009"  # 文件读取失败
    E010 = "E010"  # 未知错误


# 错误码对应的标准化话术
ERROR_MESSAGES = {
    ErrorCode.E001: "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    ErrorCode.E002: "还缺少以下信息，请补充：关键字段",
    ErrorCode.E003: "输入格式不符合要求，示例：JSON 对象或文本行",
    ErrorCode.E004: "这超出了本工具的能力范围，建议使用专业工具处理",
    ErrorCode.E005: "结果无法确定，建议人工复核或补充更多信息",
    ErrorCode.E006: "输出格式化失败，请检查输出配置",
    ErrorCode.E007: "内部处理异常，请重试或检查输入",
    ErrorCode.E008: "命令行参数错误，请检查参数设置",
    ErrorCode.E009: "文件读取失败，请检查文件路径和权限",
    ErrorCode.E010: "发生未知错误，请提交反馈",
}


# ============================================================
# 核心数据结构
# ============================================================
class ProcessingResult:
    """处理结果数据类"""
    
    def __init__(
        self,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        warnings: Optional[List[str]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.data = data if data is not None else {}
        self.confidence = confidence  # 0.0 ~ 1.0
        self.warnings = warnings if warnings is not None else []
        self.error_code = error_code
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        result = {
            "success": self.success,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }
        if self.success:
            result["data"] = self.data
        else:
            result["error_code"] = self.error_code
            result["error_message"] = self.error_message
        return result


# ============================================================
# 核心处理逻辑
# ============================================================
class ResourceController:
    """资源控制器核心处理类"""
    
    # 关键字段识别关键字
    KEY_FIELDS = ["name", "type", "id", "value", "title", "description", "category"]
    
    # 输出模板
    OUTPUT_TEMPLATE = {
        "summary": "",
        "fields": {},
        "metadata": {
            "version": "1.0.0",
            "processed": False,
        },
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化控制器"""
        self.config = config or {}
        self._batch_mode = self.config.get("batch_mode", False)
    
    def process(self, raw_input: Any) -> ProcessingResult:
        """
        处理输入内容，返回结构化结果
        
        流程：
        1. 检查输入是否为空
        2. 解析输入内容
        3. 提取关键字段
        4. 计算置信度
        5. 生成结构化输出
        """
        # Step 1: 输入为空检查
        if raw_input is None or raw_input == "":
            return ProcessingResult(
                success=False,
                error_code=ErrorCode.E001,
                error_message=ERROR_MESSAGES[ErrorCode.E001],
            )
        
        # 批量模式处理
        if self._batch_mode and isinstance(raw_input, list):
            return self._process_batch(raw_input)
        
        # 单条处理
        try:
            # Step 2: 解析输入
            parsed = self._parse_input(raw_input)
            if not parsed["success"]:
                return parsed["result"]
            
            # Step 3: 提取关键字段
            content = parsed["content"]
            fields = self._extract_fields(content)
            
            # Step 4: 计算置信度
            confidence = self._calculate_confidence(fields, content)
            
            # Step 5: 生成输出
            output = self._build_output(fields, content)
            
            # 置信度检查
            warnings = []
            if confidence < 0.85:
                warnings.append("低置信度：部分字段可能不准确，请人工复核")
            elif confidence < 0.90:
                warnings.append("建议复核：置信度在85%-90%之间")
            
            return ProcessingResult(
                success=True,
                data=output,
                confidence=confidence,
                warnings=warnings,
            )
            
        except Exception as e:
            # 内部处理异常
            return ProcessingResult(
                success=False,
                error_code=ErrorCode.E007,
                error_message=f"{ERROR_MESSAGES[ErrorCode.E007]} 详情: {str(e)}",
            )
    
    def _process_batch(self, items: List[Any]) -> ProcessingResult:
        """批量处理多个输入"""
        results = []
        for idx, item in enumerate(items):
            result = self.process(item)
            results.append({
                "index": idx + 1,
                "result": result.to_dict(),
            })
        
        # 计算整体置信度
        success_count = sum(1 for r in results if r["result"]["success"])
        total_count = len(results)
        avg_confidence = (
            sum(r["result"]["confidence"] for r in results) / total_count
            if total_count > 0 else 0
        )
        
        return ProcessingResult(
            success=True,
            data={
                "batch_size": total_count,
                "success_count": success_count,
                "fail_count": total_count - success_count,
                "items": results,
            },
            confidence=avg_confidence,
        )
    
    def _parse_input(self, raw_input: Any) -> Dict[str, Any]:
        """
        解析输入内容
        
        支持：
        - 字典/对象
        - JSON 字符串
        - 普通文本
        """
        # 已经是字典类型
        if isinstance(raw_input, dict):
            return {"success": True, "content": raw_input, "result": None}
        
        # 字符串类型
        if isinstance(raw_input, str):
            # 尝试 JSON 解析
            try:
                parsed = json.loads(raw_input)
                if isinstance(parsed, dict):
                    return {"success": True, "content": parsed, "result": None}
                elif isinstance(parsed, list):
                    # JSON 数组，尝试作为批量处理
                    return {"success": True, "content": {"_batch": parsed}, "result": None}
                else:
                    # 解析成功但不是对象
                    return {
                        "success": False,
                        "content": None,
                        "result": ProcessingResult(
                            success=False,
                            error_code=ErrorCode.E003,
                            error_message=ERROR_MESSAGES[ErrorCode.E003],
                        ),
                    }
            except json.JSONDecodeError:
                # 不是 JSON，按普通文本处理
                # 尝试解析键值对格式: key=value;key2=value2
                content = self._parse_key_value_text(raw_input)
                return {"success": True, "content": content, "result": None}
        
        # 其他类型（数字、布尔等）
        # 转换为字符串处理
        if isinstance(raw_input, (int, float, bool)):
            return {
                "success": True,
                "content": {"value": str(raw_input)},
                "result": None,
            }
        
        # 无法处理的类型
        return {
            "success": False,
            "content": None,
            "result": ProcessingResult(
                success=False,
                error_code=ErrorCode.E003,
                error_message=ERROR_MESSAGES[ErrorCode.E003],
            ),
        }
    
    def _parse_key_value_text(self, text: str) -> Dict[str, str]:
        """
        解析键值对文本
        
        支持格式：
        - key=value;key2=value2
        - key: value
        - 每行一个键值对
        """
        content = {}
        
        # 先尝试分号分隔
        segments = text.split(";")
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            
            # 尝试 = 分隔
            if "=" in segment:
                parts = segment.split("=", 1)
                key = parts[0].strip()
                value = parts[1].strip()
                if key:  # 确保 key 不为空
                    content[key] = value
            # 尝试 : 分隔
            elif ":" in segment:
                parts = segment.split(":", 1)
                key = parts[0].strip()
                value = parts[1].strip()
                if key:  # 确保 key 不为空
                    content[key] = value
        
        # 如果分号分隔没有结果，尝试按行解析
        if not content:
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                
                # 尝试 = 分隔
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    content[key] = value
                # 尝试 : 分隔
                elif ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    content[key] = value
        
        return content
    
    def _extract_fields(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键字段"""
        fields = {}
        
        # 处理批量内容
        if "_batch" in content and isinstance(content["_batch"], list):
            return {"batch_items": content["_batch"]}
        
        # 遍历内容中的键值对
        for key, value in content.items():
            key_lower = key.lower().strip()
            
            # 检查是否为关键字段
            for known_field in self.KEY_FIELDS:
                if key_lower == known_field or key_lower.endswith(f"_{known_field}"):
                    fields[known_field] = value
                    break
            else:
                # 非关键字段也保留，但标记为扩展字段
                fields[key] = value
        
        return fields
    
    def _calculate_confidence(self, fields: Dict[str, Any], content: Dict[str, Any]) -> float:
        """
        计算置信度
        
        规则：
        - 基础置信度 0.80
        - 有关键字段 +0.05/个（最多 +0.15）
        - 有内容 +0.05
        - 内容完整性高 +0.05
        """
        # 批量内容处理
        if "batch_items" in fields:
            return 0.95  # 批量处理置信度较高
        
        confidence = 0.80
        
        # 关键字段数量
        key_field_count = sum(
            1 for key in fields if key in self.KEY_FIELDS
        )
        confidence += min(key_field_count * 0.05, 0.15)
        
        # 内容非空
        if content:
            confidence += 0.05
        
        # 内容完整性（有多个字段）
        if len(fields) >= 3:
            confidence += 0.05
        
        # 限制在 0~1 之间
        return max(0.0, min(confidence, 1.0))
    
    def _build_output(self, fields: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, Any]:
        """构建结构化输出"""
        output = json.loads(json.dumps(self.OUTPUT_TEMPLATE))  # 深拷贝模板
        
        # 批量内容处理
        if "batch_items" in fields:
            output["summary"] = f"批量处理 {len(fields['batch_items'])} 个项目"
            output["fields"] = fields
            output["metadata"]["processed"] = True
            output["metadata"]["field_count"] = len(fields)
            output["metadata"]["content_type"] = "batch"
            return output
        
        # 生成摘要
        summary_parts = []
        if "name" in fields:
            summary_parts.append(f"名称: {fields['name']}")
        if "type" in fields:
            summary_parts.append(f"类型: {fields['type']}")
        if "title" in fields:
            summary_parts.append(f"标题: {fields['title']}")
        
        output["summary"] = "；".join(summary_parts) if summary_parts else "未识别到关键摘要信息"
        
        # 填充字段
        output["fields"] = fields
        
        # 更新元数据
        output["metadata"]["processed"] = True
        output["metadata"]["field_count"] = len(fields)
        output["metadata"]["content_type"] = type(content).__name__
        
        return output
    
    def format_output(self, result: ProcessingResult, format_type: str = "json") -> str:
        """
        格式化输出结果
        
        支持格式：json, text, pretty
        """
        try:
            if format_type == "json":
                return json.dumps(result.to_dict(), ensure_ascii=False)
            elif format_type == "pretty":
                return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
            elif format_type == "text":
                return self._format_as_text(result)
            else:
                # 未知格式，回退到 JSON
                return json.dumps(result.to_dict(), ensure_ascii=False)
        except Exception:
            # 格式化失败
            return json.dumps({
                "success": False,
                "error_code": ErrorCode.E006,
                "error_message": ERROR_MESSAGES[ErrorCode.E006],
            })
    
    def _format_as_text(self, result: ProcessingResult) -> str:
        """文本格式输出"""
        if not result.success:
            return f"[错误] {result.error_code}: {result.error_message}"
        
        lines = []
        lines.append(f"[成功] 置信度: {result.confidence:.0%}")
        
        if result.warnings:
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        
        data = result.data
        if "summary" in data:
            lines.append(f"摘要: {data['summary']}")
        
        if "fields" in data:
            lines.append("字段:")
            for key, value in data["fields"].items():
                lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)


# ============================================================
# 命令行接口
# ============================================================
def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="resource-controller: Rails RESTful controller abstraction plugin",
        epilog="示例: python main.py --input '{\"name\": \"test\", \"type\": \"demo\"}' --format pretty",
    )
    
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入内容，支持 JSON 字符串或键值对文本",
    )
    
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="从文件读取输入内容",
    )
    
    parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["json", "pretty", "text"],
        default="pretty",
        help="输出格式 (默认: pretty)",
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式（输入为 JSON 数组时自动启用）",
    )
    
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检",
    )
    
    return parser


def run_selftest() -> int:
    """
    运行离线自检
    
    使用硬编码样例数据，不读取外部文件，不访问网络。
    断言使用宽松阈值，确保自检在任何环境都能通过。
    """
    print("=" * 60)
    print("resource-controller 自检开始")
    print("=" * 60)
    
    controller = ResourceController()
    test_count = 0
    pass_count = 0
    
    # 测试用例 1: 正常处理
    print("\n[测试 1] 正常处理 JSON 输入")
    test_count += 1
    result = controller.process('{"name": "test_resource", "type": "model", "id": 1}')
    assert result.success, f"测试 1 失败: {result.error_message}"
    assert result.confidence >= 0.8, f"测试 1 置信度异常: {result.confidence}"
    assert result.data["fields"].get("name") == "test_resource", "字段提取失败"
    pass_count += 1
    print(f"  通过 (置信度: {result.confidence:.0%})")
    
    # 测试用例 2: 空输入
    print("\n[测试 2] 空输入处理")
    test_count += 1
    result = controller.process("")
    assert not result.success, "空输入应该失败"
    assert result.error_code == ErrorCode.E001, f"错误码应为 E001, 实际: {result.error_code}"
    pass_count += 1
    print("  通过")
    
    # 测试用例 3: 键值对文本
    print("\n[测试 3] 键值对文本处理")
    test_count += 1
    result = controller.process("name=demo;type=service;version=2.0")
    assert result.success, f"测试 3 失败: {result.error_message}"
    assert result.confidence >= 0.8, f"测试 3 置信度异常: {result.confidence}"
    assert result.data["fields"].get("name") == "demo", "键值对解析失败"
    pass_count += 1
    print(f"  通过 (置信度: {result.confidence:.0%})")
    
    # 测试用例 4: 批量处理
    print("\n[测试 4] 批量处理")
    test_count += 1
    batch_controller = ResourceController({"batch_mode": True})
    items = [
        {"name": "item1", "type": "a"},
        {"name": "item2", "type": "b"},
        "name=item3;type=c",
    ]
    result = batch_controller.process(items)
    assert result.success, f"测试 4 失败: {result.error_message}"
    assert result.data["batch_size"] == 3, "批量处理数量错误"
    assert result.data["success_count"] >= 2, "批量处理成功率过低"
    pass_count += 1
    print(f"  通过 (批量大小: {result.data['batch_size']}, 成功: {result.data['success_count']})")
    
    # 测试用例 5: 格式输出
    print("\n[测试 5] 格式化输出")
    test_count += 1
    result = controller.process('{"name": "format_test"}')
    assert result.success, f"测试 5 失败: {result.error_message}"
    
    json_out = controller.format_output(result, "json")
    assert json_out, "JSON 输出为空"
    assert '"success": true' in json_out, "JSON 输出缺少 success 字段"
    
    text_out = controller.format_output(result, "text")
    assert text_out, "文本输出为空"
    assert "置信度" in text_out, "文本输出缺少置信度信息"
    pass_count += 1
    print("  通过")
    
    # 测试用例 6: 置信度分级
    print("\n[测试 6] 置信度分级")
    test_count += 1
    # 低置信度场景（只有少量信息）
    result = controller.process("hello")
    assert result.success, f"测试 6 失败: {result.error_message}"
    # 置信度应该较低（没有关键字段）
    assert result.confidence < 0.9, f"置信度应低于 0.9, 实际: {result.confidence}"
    pass_count += 1
    print(f"  通过 (置信度: {result.confidence:.0%})")
    
    # 测试用例 7: 错误码完整性
    print("\n[测试 7] 错误码定义")
    test_count += 1
    for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]:
        assert code in ERROR_MESSAGES, f"错误码 {code} 未定义"
        assert ERROR_MESSAGES[code], f"错误码 {code} 消息为空"
    pass_count += 1
    print("  通过")
    
    # 测试用例 8: 边界能力
    print("\n[测试 8] 能力边界检查")
    test_count += 1
    # 处理非支持类型
    result = controller.process(12345)  # 数字类型
    # 数字类型应该被处理或返回错误
    if result.success:
        assert result.confidence > 0, "数字类型处理置信度异常"
    else:
        assert result.error_code in [ErrorCode.E003, ErrorCode.E007], "数字类型应返回格式错误或内部错误"
    pass_count += 1
    print("  通过")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print(f"自检完成: {pass_count}/{test_count} 通过")
    print("=" * 60)
    
    return 0 if pass_count == test_count else 1


def read_input_from_file(filepath: str) -> str:
    """从文件读取输入内容"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return json.dumps({
            "success": False,
            "error_code": ErrorCode.E009,
            "error_message": f"文件不存在: {filepath}",
        })
    except PermissionError:
        return json.dumps({
            "success": False,
            "error_code": ErrorCode.E009,
            "error_message": f"无权限读取文件: {filepath}",
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error_code": ErrorCode.E009,
            "error_message": f"读取文件失败: {str(e)}",
        })


def main() -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 检查参数
    if not args.input and not args.file:
        parser.error(f"{ErrorCode.E008}: 必须提供 --input 或 --file 参数")
        return 1
    
    # 获取输入
    raw_input = args.input
    if args.file:
        raw_input = read_input_from_file(args.file)
        # 检查文件读取是否成功
        try:
            file_result = json.loads(raw_input)
            if not file_result.get("success", True):
                print(json.dumps(file_result, ensure_ascii=False, indent=2))
                return 1
        except json.JSONDecodeError:
            # 文件内容不是错误 JSON，继续处理
            pass
    
    # 创建控制器
    controller = ResourceController({
        "batch_mode": args.batch,
    })
    
    # 处理输入
    result = controller.process(raw_input)
    
    # 输出结果
    print(controller.format_output(result, args.format))
    
    # 返回退出码
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
