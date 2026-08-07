#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sequel-model 数据建模与结构转换工具

独立实现脚本，仅依据功能规格设计。
支持将输入数据转换为结构化 JSON 输出，包含字段映射、批量处理与置信度标注。
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入数据格式无效",
    "E002": "输入数据为空",
    "E003": "字段映射失败",
    "E004": "批量处理超出限制",
    "E005": "JSON 解析失败",
    "E006": "输出序列化失败",
    "E007": "URL 格式无效",
    "E008": "文件路径无效",
    "E009": "内部处理错误",
    "E010": "参数错误",
}


class SequelModelError(Exception):
    """自定义异常类，携带错误码"""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        self.message = message or ERROR_CODES.get(error_code, "未知错误")
        super().__init__(f"[{error_code}] {self.message}")


# ============================================================
# 核心功能类
# ============================================================
class SequelModel:
    """数据建模与结构转换核心类"""

    # 默认字段映射模板（键为通用字段名，值为可能的输入字段别名）
    DEFAULT_FIELD_MAP = {
        "id": ["id", "ID", "编号", "标识"],
        "name": ["name", "名称", "姓名", "title"],
        "email": ["email", "邮箱", "邮件"],
        "phone": ["phone", "电话", "手机", "联系电话"],
        "address": ["address", "地址", "位置"],
        "date": ["date", "日期", "时间", "created_at", "create_time"],
        "amount": ["amount", "金额", "价格", "数量", "count"],
        "status": ["status", "状态", "类型", "type"],
        "description": ["description", "描述", "备注", "说明", "details"],
    }

    def __init__(self, field_map: Optional[Dict[str, List[str]]] = None):
        """
        初始化 SequelModel 实例

        Args:
            field_map: 自定义字段映射表，格式为 {标准字段名: [别名列表]}
        """
        self.field_map = field_map or self.DEFAULT_FIELD_MAP.copy()

    def process(self, data: Any) -> Dict[str, Any]:
        """
        处理输入数据，转换为结构化结果

        Args:
            data: 输入数据，支持 dict、list[dict] 或 JSON 字符串

        Returns:
            结构化结果字典，包含处理后的数据与元信息
        """
        try:
            # 解析输入
            parsed_data = self._parse_input(data)

            if not parsed_data:
                raise SequelModelError("E002")

            # 判断是单条还是批量
            if isinstance(parsed_data, list):
                # 批量处理
                if len(parsed_data) > 1000:
                    raise SequelModelError("E004", "批量处理超过 1000 条记录上限")
                records = [self._process_record(item) for item in parsed_data]
                result = {
                    "data": records,
                    "meta": {
                        "count": len(records),
                        "batch": True,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            else:
                # 单条处理
                record = self._process_record(parsed_data)
                result = {
                    "data": record,
                    "meta": {
                        "count": 1,
                        "batch": False,
                        "timestamp": datetime.now().isoformat(),
                    },
                }

            return result

        except SequelModelError:
            raise
        except json.JSONDecodeError as exc:
            raise SequelModelError("E005", f"JSON 解析失败: {str(exc)}") from exc
        except Exception as exc:
            raise SequelModelError("E009", f"内部处理错误: {str(exc)}") from exc

    def _parse_input(self, data: Any) -> Union[Dict, List[Dict], None]:
        """
        解析输入数据

        Args:
            data: 原始输入

        Returns:
            解析后的字典或字典列表
        """
        if data is None:
            return None

        # 如果是字符串，尝试解析为 JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                # 尝试去除可能的空白后再次解析
                stripped = data.strip()
                if stripped:
                    try:
                        data = json.loads(stripped)
                    except json.JSONDecodeError:
                        raise SequelModelError("E001")
                else:
                    return None

        # 验证数据类型
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            # 验证列表中的元素都是字典
            valid_items = [item for item in data if isinstance(item, dict)]
            if len(valid_items) != len(data):
                raise SequelModelError("E001", "列表中包含非字典元素")
            return valid_items
        else:
            raise SequelModelError("E001")

    def _process_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单条记录，进行字段映射和转换

        Args:
            record: 原始记录字典

        Returns:
            处理后的结构化记录
        """
        if not record:
            raise SequelModelError("E002")

        result: Dict[str, Any] = {}
        missing_fields: List[str] = []
        mapped_count = 0

        # 遍历标准字段映射
        for standard_field, aliases in self.field_map.items():
            value = None
            found = False

            # 尝试匹配别名
            for alias in aliases:
                if alias in record:
                    value = record[alias]
                    found = True
                    break

            if found:
                # 字段值清洗
                cleaned_value = self._clean_value(value)
                result[standard_field] = cleaned_value
                mapped_count += 1
            else:
                # 字段缺失，标记
                missing_fields.append(standard_field)
                result[standard_field] = None

        # 保留未映射的原始字段
        mapped_aliases = set()
        for aliases in self.field_map.values():
            mapped_aliases.update(aliases)
        for key, value in record.items():
            if key not in mapped_aliases:
                result[f"raw_{key}"] = value

        # 计算置信度
        total_fields = len(self.field_map)
        confidence = mapped_count / total_fields if total_fields > 0 else 0.0

        # 添加元数据
        result["_meta"] = {
            "confidence": round(confidence, 2),
            "missing_fields": missing_fields,
            "mapped_count": mapped_count,
            "total_fields": total_fields,
        }

        return result

    def _clean_value(self, value: Any) -> Any:
        """
        清洗字段值

        Args:
            value: 原始值

        Returns:
            清洗后的值
        """
        if value is None:
            return None

        # 字符串清洗
        if isinstance(value, str):
            cleaned = value.strip()
            # 空字符串转为 None
            if not cleaned:
                return None
            return cleaned

        # 数字类型直接返回
        if isinstance(value, (int, float, bool)):
            return value

        # 列表或字典深度清洗
        if isinstance(value, (list, dict)):
            return value

        # 其他类型转为字符串
        return str(value)

    def to_json(self, data: Any, pretty: bool = True) -> str:
        """
        将处理结果转换为 JSON 字符串

        Args:
            data: 输入数据
            pretty: 是否格式化输出

        Returns:
            JSON 字符串
        """
        try:
            result = self.process(data)
            if pretty:
                return json.dumps(result, ensure_ascii=False, indent=2)
            return json.dumps(result, ensure_ascii=False)
        except SequelModelError:
            raise
        except Exception as exc:
            raise SequelModelError("E006", f"输出序列化失败: {str(exc)}") from exc


# ============================================================
# 命令行接口
# ============================================================
def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="sequel-model 数据建模与结构转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理 JSON 字符串
  python main.py --input '{"name": "张三", "email": "zhang@example.com"}'

  # 处理 JSON 文件
  python main.py --file input.json

  # 批量处理
  python main.py --input '[{"name": "张三"}, {"name": "李四"}]'

  # 运行自检
  python main.py --selftest
        """,
    )
    parser.add_argument(
        "--input", "-i", type=str, help="输入数据（JSON 字符串）"
    )
    parser.add_argument(
        "--file", "-f", type=str, help="输入文件路径（包含 JSON 数据）"
    )
    parser.add_argument(
        "--output", "-o", type=str, help="输出文件路径（默认输出到 stdout）"
    )
    parser.add_argument(
        "--compact", "-c", action="store_true", help="紧凑输出（不格式化）"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检程序"
    )
    return parser


def read_input_file(file_path: str) -> Any:
    """读取输入文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise SequelModelError("E008", f"文件不存在: {file_path}")
    except PermissionError:
        raise SequelModelError("E008", f"文件无读取权限: {file_path}")
    except Exception as exc:
        raise SequelModelError("E008", f"读取文件失败: {str(exc)}")


def write_output_file(file_path: str, content: str) -> None:
    """写入输出文件"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as exc:
        raise SequelModelError("E006", f"写入文件失败: {str(exc)}")


# ============================================================
# 自检程序
# ============================================================
def run_selftest() -> int:
    """
    运行内置自检程序

    使用硬编码样例数据离线验证核心逻辑，不依赖外部文件或网络。

    Returns:
        0 表示通过，非 0 表示失败
    """
    print("=" * 60)
    print("sequel-model 自检程序")
    print("=" * 60)

    try:
        # 创建实例
        model = SequelModel()

        # --- 测试 1: 单条记录处理 ---
        print("\n[测试 1] 单条记录处理")
        sample1 = {
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "13800138000",
            "address": "北京市海淀区",
            "date": "2026-01-15",
        }
        result1 = model.process(sample1)
        data1 = result1["data"]

        # 断言：关键字段已映射
        assert data1.get("name") == "张三", "名称字段映射失败"
        assert data1.get("email") == "zhangsan@example.com", "邮箱字段映射失败"
        assert data1.get("phone") == "13800138000", "电话字段映射失败"
        assert data1.get("address") == "北京市海淀区", "地址字段映射失败"
        assert data1.get("date") == "2026-01-15", "日期字段映射失败"

        # 断言：置信度在合理范围
        meta1 = data1.get("_meta", {})
        confidence1 = meta1.get("confidence", 0)
        assert 0 <= confidence1 <= 1, "置信度超出范围"
        assert confidence1 > 0.5, "置信度应大于 0.5（大部分字段已映射）"

        # 断言：缺失字段数量合理
        missing1 = meta1.get("missing_fields", [])
        assert len(missing1) <= 3, "缺失字段过多"

        print(f"  通过 - 置信度: {confidence1:.2f}, 映射字段: {meta1.get('mapped_count')}/{meta1.get('total_fields')}")

        # --- 测试 2: 批量记录处理 ---
        print("\n[测试 2] 批量记录处理")
        sample2 = [
            {"name": "李四", "email": "lisi@example.com"},
            {"name": "王五", "phone": "13900139000"},
            {"name": "赵六", "address": "上海市浦东新区"},
        ]
        result2 = model.process(sample2)
        data2 = result2["data"]

        # 断言：批量处理数量正确
        assert isinstance(data2, list), "批量处理结果应为列表"
        assert len(data2) == 3, "批量处理数量错误"

        # 断言：每条记录都有元数据
        for record in data2:
            assert "_meta" in record, "记录缺少元数据"
            meta = record["_meta"]
            assert 0 <= meta["confidence"] <= 1, "置信度超出范围"

        # 断言：批量标记正确
        assert result2["meta"]["batch"] is True, "批量标记错误"
        assert result2["meta"]["count"] == 3, "计数错误"

        print(f"  通过 - 处理 {len(data2)} 条记录")

        # --- 测试 3: JSON 字符串输入 ---
        print("\n[测试 3] JSON 字符串输入")
        json_str = '{"name": "测试", "amount": 100, "status": "active"}'
        result3 = model.process(json_str)
        data3 = result3["data"]

        # 断言：字段映射成功
        assert data3.get("name") == "测试", "JSON 输入名称映射失败"
        assert data3.get("amount") == 100, "JSON 输入金额映射失败"
        assert data3.get("status") == "active", "JSON 输入状态映射失败"

        print("  通过 - JSON 字符串解析成功")

        # --- 测试 4: 字段别名匹配 ---
        print("\n[测试 4] 字段别名匹配")
        sample4 = {
            "编号": "A001",
            "标题": "测试文档",
            "创建时间": "2026-02-01",
        }
        result4 = model.process(sample4)
        data4 = result4["data"]

        # 断言：中文别名映射成功
        assert data4.get("id") == "A001", "编号字段映射失败"
        assert data4.get("name") == "测试文档", "标题字段映射失败"
        assert data4.get("date") == "2026-02-01", "创建时间字段映射失败"

        print("  通过 - 中文别名映射成功")

        # --- 测试 5: 空值处理 ---
        print("\n[测试 5] 空值处理")
        sample5 = {"name": "   ", "email": None, "phone": ""}
        result5 = model.process(sample5)
        data5 = result5["data"]

        # 断言：空字符串和 None 转为 None
        assert data5.get("name") is None, "空白字符串应转为 None"
        assert data5.get("email") is None, "None 值应保持为 None"
        assert data5.get("phone") is None, "空字符串应转为 None"

        print("  通过 - 空值处理正确")

        # --- 测试 6: 错误处理 ---
        print("\n[测试 6] 错误处理")

        # 空输入
        try:
            model.process(None)
            assert False, "空输入应抛出异常"
        except SequelModelError as exc:
            assert exc.error_code == "E002", f"错误码应为 E002，实际为 {exc.error_code}"
            print(f"  通过 - 空输入错误码: {exc.error_code}")

        # 无效输入
        try:
            model.process(12345)
            assert False, "无效输入应抛出异常"
        except SequelModelError as exc:
            assert exc.error_code == "E001", f"错误码应为 E001，实际为 {exc.error_code}"
            print(f"  通过 - 无效输入错误码: {exc.error_code}")

        # 无效 JSON
        try:
            model.process("{invalid json")
            assert False, "无效 JSON 应抛出异常"
        except SequelModelError as exc:
            assert exc.error_code in ("E001", "E005"), f"错误码应为 E001 或 E005，实际为 {exc.error_code}"
            print(f"  通过 - 无效 JSON 错误码: {exc.error_code}")

        # --- 测试 7: 自定义字段映射 ---
        print("\n[测试 7] 自定义字段映射")
        custom_map = {
            "custom_id": ["cid", "自定义ID"],
            "custom_name": ["cname", "自定义名称"],
        }
        custom_model = SequelModel(field_map=custom_map)
        sample7 = {"cid": "C001", "cname": "自定义"}
        result7 = custom_model.process(sample7)
        data7 = result7["data"]

        # 断言：自定义映射生效
        assert data7.get("custom_id") == "C001", "自定义字段映射失败"
        assert data7.get("custom_name") == "自定义", "自定义字段映射失败"

        print("  通过 - 自定义字段映射成功")

        # --- 测试 8: 批量限制 ---
        print("\n[测试 8] 批量限制检查")
        # 构造 1001 条记录
        large_batch = [{"name": f"测试{i}"} for i in range(1001)]
        try:
            model.process(large_batch)
            assert False, "超过限制应抛出异常"
        except SequelModelError as exc:
            assert exc.error_code == "E004", f"错误码应为 E004，实际为 {exc.error_code}"
            print(f"  通过 - 批量限制错误码: {exc.error_code}")

        # --- 测试 9: JSON 输出 ---
        print("\n[测试 9] JSON 输出")
        json_output = model.to_json({"name": "输出测试"})
        parsed_output = json.loads(json_output)
        assert "data" in parsed_output, "输出缺少 data 字段"
        assert "meta" in parsed_output, "输出缺少 meta 字段"
        print("  通过 - JSON 输出格式正确")

        # --- 测试 10: 原始字段保留 ---
        print("\n[测试 10] 原始字段保留")
        sample10 = {"name": "测试", "custom_field": "自定义值"}
        result10 = model.process(sample10)
        data10 = result10["data"]
        assert data10.get("raw_custom_field") == "自定义值", "原始字段未保留"
        print("  通过 - 原始字段保留成功")

        print("\n" + "=" * 60)
        print("所有自检测试通过！")
        print("=" * 60)
        return 0

    except AssertionError as exc:
        print(f"\n自检失败: {exc}")
        return 1
    except Exception as exc:
        print(f"\n自检异常: {exc}")
        return 1


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 运行自检
    if args.selftest:
        return run_selftest()

    # 获取输入数据
    input_data = None
    try:
        if args.file:
            # 从文件读取
            file_content = read_input_file(args.file)
            input_data = file_content
        elif args.input:
            # 从命令行参数读取
            input_data = args.input
        else:
            # 从 stdin 读取
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                input_data = stdin_data
            else:
                parser.print_help()
                return 1

        # 处理数据
        model = SequelModel()
        output = model.to_json(input_data, pretty=not args.compact)

        # 输出结果
        if args.output:
            write_output_file(args.output, output)
            print(f"结果已写入: {args.output}")
        else:
            print(output)

        return 0

    except SequelModelError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"未预期错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
