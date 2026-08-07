#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glooit - 未命名工具
仅供学习与参考用途。使用前请阅读相关文档。
"""

import argparse
import json
import sys
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "还缺少以下信息，请补充：...",
    "E003": "输入格式不符合要求，示例：...",
    "E004": "这超出了本工具的能力范围，建议...",
    "E005": "结果无法确定，建议：...",
    "E006": "内部处理错误，请重试",
    "E007": "参数解析错误，请检查命令行参数",
    "E008": "输出序列化失败",
    "E009": "批量处理中断，请检查输入批次",
    "E010": "未知错误，请联系维护者",
}


class GlooitError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E010"])
        super().__init__(f"[{self.code}] {self.message}")


# ============================================================
# 核心处理类
# ============================================================
class GlooitProcessor:
    """glooit 核心处理器：解析输入、结构化输出、置信度评估"""

    # 关键字段识别规则（按优先级排列）
    FIELD_PATTERNS = [
        ("name", r"(?:名称|姓名|名字|name)[:：]?\s*([^\s,，、;；]+)"),
        ("email", r"(?:邮箱|邮件|email)[:：]?\s*([\w.+-]+@[\w-]+\.[\w.]+)"),
        ("phone", r"(?:电话|手机|phone|tel)[:：]?\s*(\+?\d[\d\s-]{6,})"),
        ("url", r"(?:网址|链接|url)[:：]?\s*(https?://[^\s,，、;；]+)"),
        ("date", r"(?:日期|时间|date)[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"),
        ("amount", r"(?:金额|价格|amount|price)[:：]?\s*([\d,]+\.?\d*\s*[元美元€￥]?)"),
    ]

    # 停止词/噪音词（用于判断信息是否有效）
    NOISE_WORDS = {"无", "暂无", "未知", "不详", "n/a", "na", "none", "null", "待定", "未提供"}

    def __init__(self, input_data: Any, options: Optional[Dict] = None):
        """
        初始化处理器
        :param input_data: 用户提供的原始输入（字符串、字典、列表等）
        :param options: 处理选项（如输出格式、完整度等）
        """
        self.raw_input = input_data
        self.options = options or {}
        self.structured_data: Dict[str, Any] = {}
        self.confidence: float = 0.0
        self.warnings: List[str] = []
        self._validated = False

    # ---------- 对外主流程 ----------
    def process(self) -> Dict[str, Any]:
        """执行完整处理流程，返回标准结果结构"""
        try:
            # Step 1: 输入校验
            self._validate_input()

            # Step 2: 解析并结构化
            self._parse_input()

            # Step 3: 置信度评估
            self._evaluate_confidence()

            # Step 4: 组装输出
            return self._build_output()

        except GlooitError:
            raise
        except Exception as exc:  # 兜底异常
            raise GlooitError("E010", f"内部错误: {exc}") from exc

    # ---------- 内部步骤 ----------
    def _validate_input(self) -> None:
        """校验输入合法性"""
        if self.raw_input is None or (isinstance(self.raw_input, str) and not self.raw_input.strip()):
            raise GlooitError("E001")

        # 检查必需字段（当选项要求时）
        required = self.options.get("required_fields", [])
        missing = [f for f in required if not self._extract_field(f)]
        if missing:
            raise GlooitError("E002", f"还缺少以下信息，请补充：{', '.join(missing)}")

        # 格式校验（支持 json 字符串）
        if isinstance(self.raw_input, str):
            stripped = self.raw_input.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    self.raw_input = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise GlooitError("E003", f"JSON 格式错误: {exc}") from exc

        self._validated = True

    def _parse_input(self) -> None:
        """解析输入，提取关键信息"""
        if isinstance(self.raw_input, dict):
            # 直接使用字典键值
            self.structured_data = self._parse_dict(self.raw_input)
        elif isinstance(self.raw_input, list):
            # 列表：逐项解析（简单模式，取第一项有效）
            self.structured_data = self._parse_list(self.raw_input)
        elif isinstance(self.raw_input, str):
            # 文本：正则提取
            self.structured_data = self._parse_text(self.raw_input)
        else:
            raise GlooitError("E003", f"不支持的输入类型: {type(self.raw_input).__name__}")

        # 若解析结果为空，尝试从原始文本兜底提取
        if not self.structured_data and isinstance(self.raw_input, str):
            self.structured_data = self._regex_extract(self.raw_input)

    def _parse_dict(self, data: Dict) -> Dict[str, Any]:
        """解析字典输入"""
        result: Dict[str, Any] = {}
        for key, value in data.items():
            # 清理键名
            clean_key = str(key).strip().lower()
            if not clean_key or clean_key in self.NOISE_WORDS:
                continue
            # 清理值
            if isinstance(value, str):
                clean_value = value.strip()
                if clean_value.lower() in self.NOISE_WORDS:
                    continue
                result[clean_key] = clean_value
            elif isinstance(value, (int, float, bool)):
                result[clean_key] = value
            elif isinstance(value, (dict, list)):
                # 嵌套结构保留但标记
                result[clean_key] = {"_nested": value, "_type": type(value).__name__}
            else:
                # 其他类型转字符串
                result[clean_key] = str(value)
        return result

    def _parse_list(self, data: List) -> Dict[str, Any]:
        """解析列表输入（取第一个非空字典）"""
        for item in data:
            if isinstance(item, dict):
                parsed = self._parse_dict(item)
                if parsed:
                    return parsed
            elif isinstance(item, str) and item.strip():
                parsed = self._parse_text(item)
                if parsed:
                    return parsed
        # 全部无效
        raise GlooitError("E001")

    def _parse_text(self, text: str) -> Dict[str, Any]:
        """解析文本输入（先尝试 JSON，再正则）"""
        # 尝试 JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return self._parse_dict(data)
            elif isinstance(data, list):
                return self._parse_list(data)
        except json.JSONDecodeError:
            pass
        # 正则提取
        return self._regex_extract(text)

    def _regex_extract(self, text: str) -> Dict[str, Any]:
        """使用正则规则提取关键字段"""
        result: Dict[str, Any] = {}
        for field, pattern in self.FIELD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value and value.lower() not in self.NOISE_WORDS:
                    result[field] = value
        return result

    def _extract_field(self, field: str) -> Optional[Any]:
        """从已解析数据中提取指定字段（供校验使用）"""
        if not self.structured_data:
            # 尝试直接解析
            try:
                self._parse_input()
            except GlooitError:
                return None
        # 支持多级键（用点分隔）
        keys = field.split(".")
        current = self.structured_data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current if current is not None else None

    def _evaluate_confidence(self) -> None:
        """评估结果置信度（0-100）"""
        if not self.structured_data:
            self.confidence = 0.0
            self.warnings.append("未提取到任何有效字段")
            return

        # 基础分：字段数量
        field_count = len(self.structured_data)
        if field_count >= 5:
            base = 95.0
        elif field_count >= 3:
            base = 90.0
        elif field_count >= 1:
            base = 80.0
        else:
            base = 0.0

        # 扣分项：嵌套结构（不完整）
        nested_count = sum(1 for v in self.structured_data.values() if isinstance(v, dict) and "_nested" in v)
        if nested_count:
            base -= nested_count * 5

        # 扣分项：警告
        base -= len(self.warnings) * 2

        # 边界修正
        self.confidence = max(0.0, min(100.0, base))

        # 根据置信度添加标注
        if self.confidence >= 90:
            pass  # 直接输出
        elif self.confidence >= 85:
            self.warnings.append("建议复核")
        elif self.confidence < 85:
            self.warnings.append("[需核实] 结果不确定，请人工确认")

    def _build_output(self) -> Dict[str, Any]:
        """组装标准输出结构"""
        # 根据置信度决定标注
        if self.confidence >= 90:
            confidence_label = "高"
        elif self.confidence >= 85:
            confidence_label = "中（建议复核）"
        elif self.confidence >= 60:
            confidence_label = "低（[需核实]）"
        else:
            confidence_label = "极低（[需核实]）"

        output = {
            "status": "success" if self.confidence >= 60 else "partial",
            "data": self.structured_data,
            "confidence": {
                "score": round(self.confidence, 1),
                "label": confidence_label,
                "warnings": self.warnings,
            },
            "meta": {
                "source_type": type(self.raw_input).__name__,
                "field_count": len(self.structured_data),
                "disclaimer": "本结果仅供学习与参考用途，不构成任何专业建议。请咨询持证专业人士。",
            },
        }
        return output

    # ---------- 批量处理 ----------
    @classmethod
    def batch_process(cls, inputs: List[Any], options: Optional[Dict] = None) -> List[Dict]:
        """批量处理多个输入"""
        if not inputs:
            raise GlooitError("E001")
        results = []
        for idx, item in enumerate(inputs):
            try:
                processor = cls(item, options)
                results.append(processor.process())
            except GlooitError as exc:
                results.append({
                    "status": "error",
                    "error_code": exc.code,
                    "error_message": exc.message,
                    "input_index": idx,
                })
            except Exception as exc:  # 兜底
                results.append({
                    "status": "error",
                    "error_code": "E010",
                    "error_message": str(exc),
                    "input_index": idx,
                })
        return results


# ============================================================
# CLI 入口
# ============================================================
def run_cli(args: argparse.Namespace) -> int:
    """命令行主入口"""
    try:
        # 读取输入
        if args.input:
            input_data = args.input
        elif args.file:
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    input_data = f.read()
            except OSError as exc:
                print(f"[E007] 无法读取文件: {exc}", file=sys.stderr)
                return 7
        elif args.json:
            try:
                input_data = json.loads(args.json)
            except json.JSONDecodeError as exc:
                print(f"[E003] JSON 解析失败: {exc}", file=sys.stderr)
                return 3
        else:
            # 交互模式
            print("请输入待处理内容（输入空行结束）：")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if not line.strip():
                    break
                lines.append(line)
            if not lines:
                raise GlooitError("E001")
            input_data = "\n".join(lines)

        # 选项
        options = {}
        if args.required:
            options["required_fields"] = args.required.split(",")

        # 执行处理
        if args.batch:
            # 批量模式：按行拆分（JSON 数组或每行一个）
            if isinstance(input_data, list):
                batch_inputs = input_data
            elif isinstance(input_data, str):
                batch_inputs = [line.strip() for line in input_data.splitlines() if line.strip()]
            else:
                batch_inputs = [input_data]
            results = GlooitProcessor.batch_process(batch_inputs, options)
        else:
            processor = GlooitProcessor(input_data, options)
            results = [processor.process()]

        # 输出
        output_text = json.dumps(results, ensure_ascii=False, indent=2)
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_text)
                print(f"结果已写入: {args.output}")
            except OSError as exc:
                print(f"[E008] 写入失败: {exc}", file=sys.stderr)
                return 8
        else:
            print(output_text)
        return 0

    except GlooitError as exc:
        print(f"{exc}", file=sys.stderr)
        # 返回错误码数字部分
        return int(exc.code[1:]) if exc.code[1:].isdigit() else 10
    except Exception as exc:  # 兜底
        print(f"[E010] 未知错误: {exc}", file=sys.stderr)
        return 10


# ============================================================
# 自检模块（离线、内置数据）
# ============================================================
def run_selftest() -> int:
    """
    离线自检核心逻辑。
    使用硬编码样例数据，不读文件、不联网、不依赖工作目录。
    断言采用宽松阈值（大小/区间比较），确保稳健。
    """
    print("=== glooit 自检开始 ===")
    failures = 0

    # ---------- 测试1：文本输入 ----------
    print("\n[测试1] 文本输入解析")
    sample_text = "姓名：张三，邮箱：zhangsan@example.com，电话：13800138000，日期：2026-05-20"
    try:
        proc = GlooitProcessor(sample_text)
        result = proc.process()
        data = result["data"]
        # 宽松断言：关键字段存在且非空
        assert "name" in data and data["name"], "姓名缺失"
        assert "email" in data and data["email"], "邮箱缺失"
        assert "phone" in data and data["phone"], "电话缺失"
        # 置信度应为较高（>=80）
        assert result["confidence"]["score"] >= 80, f"置信度过低: {result['confidence']['score']}"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1

    # ---------- 测试2：JSON 输入 ----------
    print("\n[测试2] JSON 输入解析")
    sample_json = '{"name": "李四", "age": 30, "city": "北京", "active": true}'
    try:
        proc = GlooitProcessor(sample_json)
        result = proc.process()
        data = result["data"]
        # 宽松断言：字段数量大于等于3
        assert len(data) >= 3, f"字段数不足: {len(data)}"
        # 值类型保持
        assert isinstance(data.get("age"), int), "age 应为整数"
        assert isinstance(data.get("active"), bool), "active 应为布尔"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1

    # ---------- 测试3：空输入 ----------
    print("\n[测试3] 空输入错误处理")
    try:
        GlooitProcessor("").process()
        print("  ✗ 失败: 未抛出 E001")
        failures += 1
    except GlooitError as exc:
        assert exc.code == "E001", f"错误码应为 E001，实际 {exc.code}"
        print("  ✓ 通过")
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1

    # ---------- 测试4：批量处理 ----------
    print("\n[测试4] 批量处理")
    batch_inputs = [
        "姓名：王五，电话：13900139000",
        "这是一条无结构纯文本，没有关键信息",
        {"name": "赵六", "score": 95.5},
    ]
    try:
        results = GlooitProcessor.batch_process(batch_inputs)
        # 宽松断言：结果数量一致，状态合理
        assert len(results) == 3, f"结果数量应为3，实际 {len(results)}"
        # 第一条应成功
        assert results[0]["status"] == "success", f"第一条应成功: {results[0]}"
        # 第二条可能成功或部分成功（不应为 error）
        assert results[1]["status"] != "error", f"第二条不应为 error: {results[1]}"
        # 第三条应成功
        assert results[2]["status"] == "success", f"第三条应成功: {results[2]}"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1

    # ---------- 测试5：置信度区间 ----------
    print("\n[测试5] 置信度区间")
    try:
        # 完整数据 → 高置信度
        full_data = {"name": "测试", "email": "a@b.com", "phone": "12345678901", "url": "http://example.com", "date": "2026-01-01"}
        proc = GlooitProcessor(full_data)
        result = proc.process()
        assert result["confidence"]["score"] >= 90, f"完整数据置信度应>=90: {result['confidence']['score']}"

        # 少量数据 → 中置信度
        partial_data = {"name": "测试"}
        proc = GlooitProcessor(partial_data)
        result = proc.process()
        assert 60 <= result["confidence"]["score"] <= 90, f"少量数据置信度应在60-90: {result['confidence']['score']}"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1
    except Exception as exc:
        print(f"  ✗ 异常: {exc}")
        failures += 1

    # ---------- 测试6：错误码完整性 ----------
    print("\n[测试6] 错误码定义")
    try:
        expected_codes = [f"E{str(i).zfill(3)}" for i in range(1, 11)]
        for code in expected_codes:
            assert code in ERROR_CODES, f"缺少错误码 {code}"
        print("  ✓ 通过")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        failures += 1

    # ---------- 汇总 ----------
    print(f"\n=== 自检结束: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="glooit - 未命名工具（仅供学习与参考用途）",
        epilog="示例: python main.py --input '姓名：张三' | python main.py --selftest",
    )
    # 输入方式（互斥）
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", "-i", help="直接输入文本内容")
    group.add_argument("--file", "-f", help="从文件读取输入")
    group.add_argument("--json", "-j", help="输入 JSON 字符串")

    # 选项
    parser.add_argument("--output", "-o", help="输出到文件（默认 stdout）")
    parser.add_argument("--required", "-r", help="必需字段（逗号分隔），缺失时返回 E002")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理模式（多行/数组输入）")
    parser.add_argument("--selftest", action="store_true", help="运行离线自检后退出")

    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
