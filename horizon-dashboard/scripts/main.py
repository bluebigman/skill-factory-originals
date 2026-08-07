#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
horizon-dashboard 技能独立实现（clean-room 重写）
仅供学习与参考用途，使用前请阅读相关文档。
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

# 错误码定义（与规格一致）
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理异常，请重试或检查输入",
    "E007": "输出序列化失败",
    "E008": "参数解析失败",
    "E009": "自检数据异常",
    "E010": "未知错误",
}

# 默认输出模板字段顺序（不含confidence，因为confidence是计算结果）
REQUIRED_FIELDS = ["id", "title", "category", "value", "status"]
# 可选字段（不参与置信度计算）
OPTIONAL_FIELDS = ["confidence"]

class HorizonDashboard:
    """horizon-dashboard 核心处理类"""
    
    def __init__(self):
        self.required_fields = REQUIRED_FIELDS
        self.optional_fields = OPTIONAL_FIELDS
    
    def _make_error(self, code: str, detail: str = "") -> Dict[str, Any]:
        """构造标准错误返回结构。"""
        if code not in ERROR_CODES:
            code = "E010"
        msg = ERROR_CODES[code]
        if detail:
            msg = f"{msg} {detail}"
        return {"ok": False, "error_code": code, "message": msg}
    
    def _make_success(self, data: Any, confidence: float = 1.0) -> Dict[str, Any]:
        """构造标准成功返回结构。"""
        return {"ok": True, "data": data, "confidence": confidence}
    
    def parse_input(self, raw_input: Any) -> Tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """
        解析输入内容，识别关键信息。
        支持：JSON 字符串、dict 对象、list 对象。
        返回 (解析后的记录列表, 错误信息)。
        """
        # E001: 输入为空
        if raw_input is None or (isinstance(raw_input, str) and not raw_input.strip()):
            return None, self._make_error("E001")
        
        # 如果已经是 dict 或 list，直接使用
        if isinstance(raw_input, (dict, list)):
            data_obj = raw_input
        elif isinstance(raw_input, str):
            try:
                data_obj = json.loads(raw_input)
            except json.JSONDecodeError:
                return None, self._make_error("E003", "需要 JSON 格式的输入")
        else:
            return None, self._make_error("E003", "不支持的输入类型")
        
        # 统一转为记录列表
        if isinstance(data_obj, dict):
            records = [data_obj]
        elif isinstance(data_obj, list):
            records = data_obj
        else:
            return None, self._make_error("E003", "输入应为对象或数组")
        
        # 检查每条记录是否为 dict
        for rec in records:
            if not isinstance(rec, dict):
                return None, self._make_error("E003", "每条记录应为对象")
        
        return records, None
    
    def extract_key_fields(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取关键字段并结构化。
        保留原有字段，并补充标准字段（若缺失）。
        对不确定项（缺失或空值）标注。
        """
        structured: List[Dict[str, Any]] = []
        for idx, rec in enumerate(records):
            new_rec: Dict[str, Any] = {}
            missing_fields = []
            
            # 处理必填字段
            for field in self.required_fields:
                if field in rec and rec[field] not in (None, ""):
                    new_rec[field] = rec[field]
                else:
                    # 缺失字段标记为待确认
                    new_rec[field] = None
                    missing_fields.append(field)
            
            # 处理可选字段（不影响置信度）
            for field in self.optional_fields:
                if field in rec and rec[field] is not None:
                    new_rec[field] = rec[field]
            
            # 保留原始额外字段
            for k, v in rec.items():
                if k not in new_rec:
                    new_rec[k] = v
            
            # 添加缺失字段信息
            new_rec["_missing_fields"] = missing_fields
            # 添加序号
            new_rec["_index"] = idx + 1
            
            structured.append(new_rec)
        return structured
    
    def compute_confidence(self, record: Dict[str, Any]) -> Tuple[float, str]:
        """
        计算置信度：
        - 无缺失必填字段：>=90% → 直接输出
        - 缺失 1-2 个必填字段：85%-90% → 建议复核
        - 缺失 >=3 个必填字段：<85% → 需核实
        返回 (置信度, 提示信息)
        """
        missing = record.get("_missing_fields", [])
        total = len(self.required_fields)
        missing_count = len(missing)
        filled_count = total - missing_count
        
        # 基础置信度 = 已填字段比例
        base_conf = filled_count / total
        
        # 根据缺失情况调整
        if missing_count == 0:
            # 完整记录，高置信度
            conf = 0.95
            note = ""
        elif missing_count == 1:
            # 缺失1个字段，中等偏高置信度
            conf = 0.88
            note = "建议复核"
        elif missing_count == 2:
            # 缺失2个字段，中等置信度
            conf = 0.85
            note = "建议复核"
        else:
            # 缺失3个及以上字段，低置信度
            conf = max(0.50, 0.80 - (missing_count - 2) * 0.10)
            note = "[需核实]"
        
        # 确保置信度在合理范围内
        conf = max(0.0, min(1.0, conf))
        
        return conf, note
    
    def format_output(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按模板组织输出，生成最终结果。
        """
        results: List[Dict[str, Any]] = []
        for rec in records:
            conf, note = self.compute_confidence(rec)
            
            # 构建输出数据（排除内部字段）
            output_data = {}
            for k, v in rec.items():
                if not k.startswith("_"):
                    output_data[k] = v
            
            item = {
                "index": rec.get("_index"),
                "data": output_data,
                "confidence": round(conf, 2),
                "note": note,
            }
            results.append(item)
        
        return {"records": results, "total": len(results)}
    
    def process_data(self, raw_input: Any) -> Dict[str, Any]:
        """
        核心处理流程：
        1. 解析输入
        2. 提取关键字段
        3. 计算置信度
        4. 组织输出
        """
        # Step 1: 解析输入
        records, err = self.parse_input(raw_input)
        if err:
            return err
        
        # Step 2: 提取关键字段
        structured = self.extract_key_fields(records)
        
        # Step 3&4: 计算置信度并组织输出
        output = self.format_output(structured)
        return self._make_success(output)
    
    def run_selftest(self) -> bool:
        """
        内置硬编码样例数据离线自检。
        不读外部文件、不依赖当前工作目录、不访问网络。
        使用宽松阈值断言，确保任何环境可直接通过。
        """
        # 样例 1：完整数据（应高置信度）
        sample1 = {
            "id": 1,
            "title": "月度销售报表",
            "category": "销售",
            "value": 1234.56,
            "status": "已完成"
        }
        result1 = self.process_data(sample1)
        assert result1["ok"] is True, "样例1应成功处理"
        assert result1["confidence"] >= 0.9, "样例1整体置信度应>=0.9"
        rec1 = result1["data"]["records"][0]
        assert rec1["confidence"] >= 0.9, "样例1记录置信度应>=0.9"
        assert rec1["data"]["title"] == "月度销售报表", "样例1标题应保留"
        assert rec1["note"] == "", "样例1不应有提示信息"
        
        # 样例 2：缺失字段数据（应低置信度）
        sample2 = {"id": 2, "title": "待完善记录"}
        result2 = self.process_data(sample2)
        assert result2["ok"] is True, "样例2应成功处理"
        rec2 = result2["data"]["records"][0]
        assert rec2["confidence"] < 0.9, "样例2置信度应<0.9"
        assert rec2["note"] != "", "样例2应有提示信息"
        
        # 样例 3：批量数据
        sample3 = [
            {"id": 3, "title": "A", "category": "X", "value": 10, "status": "ok"},
            {"id": 4, "title": "B"},
            {"id": 5, "title": "C", "category": "Y", "value": 20, "status": "pending"},
        ]
        result3 = self.process_data(sample3)
        assert result3["ok"] is True, "样例3应成功处理"
        assert result3["data"]["total"] == 3, "样例3应有3条记录"
        confs = [r["confidence"] for r in result3["data"]["records"]]
        assert max(confs) >= 0.9, "样例3至少一条高置信度"
        assert min(confs) < 0.9, "样例3至少一条低置信度"
        
        # 样例 4：空输入应报 E001
        result4 = self.process_data("")
        assert result4["ok"] is False, "空输入应失败"
        assert result4["error_code"] == "E001", "空输入应报E001"
        
        # 样例 5：非法 JSON 应报 E003
        result5 = self.process_data("not json at all")
        assert result5["ok"] is False, "非法JSON应失败"
        assert result5["error_code"] == "E003", "非法JSON应报E003"
        
        # 样例 6：JSON 字符串输入
        json_str = json.dumps({
            "id": 6, 
            "title": "JSON输入", 
            "category": "测试", 
            "value": 99, 
            "status": "ok"
        })
        result6 = self.process_data(json_str)
        assert result6["ok"] is True, "JSON字符串应成功"
        assert result6["data"]["records"][0]["data"]["title"] == "JSON输入", "JSON字符串应正确解析"
        
        # 样例 7：包含confidence字段的记录（应不影响置信度计算）
        sample7 = {
            "id": 7,
            "title": "带置信度的记录",
            "category": "测试",
            "value": 50,
            "status": "ok",
            "confidence": 0.98
        }
        result7 = self.process_data(sample7)
        assert result7["ok"] is True, "样例7应成功处理"
        rec7 = result7["data"]["records"][0]
        assert rec7["confidence"] >= 0.9, "样例7置信度应>=0.9"
        
        return True


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(description="horizon-dashboard 翻译润色技能实现")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--input", type=str, help="输入 JSON 字符串或文件路径（以@开头表示文件）")
    parser.add_argument("--pretty", action="store_true", help="美化输出 JSON")
    args = parser.parse_args()
    
    # 创建处理器实例
    processor = HorizonDashboard()
    
    # 自检模式
    if args.selftest:
        try:
            processor.run_selftest()
            print(json.dumps({"ok": True, "message": "自检通过"}, ensure_ascii=False))
            return 0
        except AssertionError as e:
            print(json.dumps(processor._make_error("E009", str(e)), ensure_ascii=False))
            return 1
        except Exception as e:
            print(json.dumps(processor._make_error("E006", str(e)), ensure_ascii=False))
            return 1
    
    # 处理输入
    if not args.input:
        print(json.dumps(processor._make_error("E001"), ensure_ascii=False))
        return 1
    
    raw_input: Any = args.input
    # 支持文件输入（@前缀）
    if args.input.startswith("@"):
        filepath = args.input[1:]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except Exception as e:
            print(json.dumps(processor._make_error("E006", f"读取文件失败: {e}"), ensure_ascii=False))
            return 1
    
    # 执行处理
    result = processor.process_data(raw_input)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
