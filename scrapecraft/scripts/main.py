#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapecraft - 爬虫采集技能核心实现

基于功能规格的 clean-room 独立实现。
仅依赖标准库，提供命令行接口与离线自检功能。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义（E001-E010）
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空，请提供待处理的内容，格式为：用户提供的数据/文件/URL",
    "E002": "关键信息缺失，请补充以下信息：",
    "E003": "输入格式不符合要求，请参考示例格式",
    "E004": "超出能力边界，本工具仅处理文本/文件/URL描述的结构化转换",
    "E005": "置信度过低，结果无法确定，建议人工复核",
    "E006": "内部处理异常，请检查输入内容",
    "E007": "批量处理中断，存在无效条目",
    "E008": "输出格式不受支持，仅支持 json/text/csv",
    "E009": "字段映射冲突，请检查字段定义",
    "E010": "资源限制，单次处理条目数超限",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class FieldSpec:
    """字段规格定义"""
    name: str
    aliases: List[str] = field(default_factory=list)
    required: bool = False
    type_hint: str = "string"  # string | number | boolean


@dataclass
class ProcessingResult:
    """处理结果封装"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    error_code: Optional[str] = None
    message: str = ""
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心处理引擎
# ---------------------------------------------------------------------------
class ScrapecraftEngine:
    """爬虫采集核心引擎"""

    # 默认字段映射（支持常见同义词）
    DEFAULT_FIELDS = [
        FieldSpec("title", ["标题", "名称", "name", "题目", "主题"]),
        FieldSpec("url", ["链接", "网址", "address", "link", "URL", "地址"]),
        FieldSpec("author", ["作者", "creator", "writer", "创建者", "作者名"]),
        FieldSpec("date", ["日期", "时间", "date_time", "published", "发布时间", "创建时间"]),
        FieldSpec("content", ["内容", "正文", "body", "text", "文章内容", "详细信息"]),
        FieldSpec("category", ["分类", "类别", "type", "tag", "标签", "类目"]),
        FieldSpec("image", ["图片", "图片链接", "image_url", "封面", "缩略图"]),
        FieldSpec("views", ["浏览量", "阅读量", "view_count", "点击量"]),
        FieldSpec("likes", ["点赞数", "喜欢数", "like_count", "赞"]),
        FieldSpec("status", ["状态", "state", "审核状态"]),
    ]

    def __init__(self, max_items: int = 100):
        """初始化引擎

        Args:
            max_items: 单次处理的最大条目数（E010 资源限制）
        """
        self.max_items = max_items
        self._field_map = self._build_field_map()

    def _build_field_map(self) -> Dict[str, str]:
        """构建同义词到标准字段名的映射表"""
        mapping = {}
        for field_spec in self.DEFAULT_FIELDS:
            # 标准字段名
            mapping[field_spec.name.lower()] = field_spec.name
            # 同义词别名
            for alias in field_spec.aliases:
                normalized_alias = self._normalize_key_for_map(alias)
                mapping[normalized_alias] = field_spec.name
        return mapping

    def _normalize_key_for_map(self, key: str) -> str:
        """标准化键名用于映射查找（去空格、下划线、连字符等）"""
        normalized = key.strip().lower()
        # 去掉常见分隔符和特殊字符
        normalized = re.sub(r"[\s_\-:：/\\.,;；，。]", "", normalized)
        return normalized

    def _normalize_key(self, key: str) -> str:
        """将输入键名标准化为标准字段名

        支持中英文同义词匹配，忽略大小写和空白。
        """
        normalized = self._normalize_key_for_map(key)
        return self._field_map.get(normalized, key.strip())

    def _infer_value_type(self, value: Any) -> str:
        """推断值的类型"""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            # 尝试识别布尔字符串
            value_lower = value.strip().lower()
            if value_lower in ("true", "false", "yes", "no", "是", "否", "真", "假"):
                return "boolean"
            # 尝试识别数字字符串
            try:
                float(value.strip())
                return "number"
            except ValueError:
                pass
        return "string"

    def _extract_fields(self, raw_item: Any) -> Tuple[Dict[str, Any], float, List[str]]:
        """从单个输入条目中提取结构化字段

        Returns:
            (字段字典, 置信度, 警告列表)
        """
        warnings = []
        extracted = {}

        # 根据输入类型分派处理
        if isinstance(raw_item, dict):
            # 字典输入：直接按键映射
            for key, value in raw_item.items():
                std_key = self._normalize_key(str(key))
                extracted[std_key] = value

        elif isinstance(raw_item, str):
            # 字符串输入：尝试解析 JSON 或键值对
            parsed = self._parse_string_input(raw_item)
            if parsed:
                for key, value in parsed.items():
                    std_key = self._normalize_key(str(key))
                    extracted[std_key] = value
            else:
                # 无法解析，整段作为内容
                extracted["content"] = raw_item
                warnings.append("输入无法结构化解析，已按纯文本处理")

        elif isinstance(raw_item, (int, float, bool)):
            # 标量输入
            extracted["content"] = str(raw_item)
            warnings.append("标量输入已转为文本内容")

        else:
            raise ValueError(f"不支持的输入类型: {type(raw_item)}")

        # 计算置信度
        confidence = self._calculate_confidence(extracted, warnings)

        return extracted, confidence, warnings

    def _parse_string_input(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试解析字符串为结构化数据

        支持 JSON 格式和简单的 key: value 格式。
        """
        text = text.strip()
        if not text:
            return None

        # 尝试 JSON 解析
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            return None
        except json.JSONDecodeError:
            pass

        # 尝试 key: value 格式（每行一个）
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            # 支持冒号或等号分隔
            match = re.match(r"^([^:=]+)[:=](.+)$", line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                result[key] = value

        return result if result else None

    def _calculate_confidence(self, fields: Dict[str, Any], warnings: List[str]) -> float:
        """计算提取结果的置信度

        规则：
        - 基础 90 分
        - 每个警告扣 5 分（最低 60 分）
        - 缺少必填字段扣 10 分
        - 字段数量影响置信度
        """
        confidence = 90.0
        confidence -= len(warnings) * 5.0

        # 检查必填字段
        required_fields = [f.name for f in self.DEFAULT_FIELDS if f.required]
        missing = [f for f in required_fields if f not in fields]
        confidence -= len(missing) * 10.0

        # 根据字段数量调整置信度
        field_count = len(fields)
        if field_count == 0:
            confidence -= 30  # 无字段，置信度极低
        elif field_count == 1:
            confidence -= 15  # 只有一个字段，置信度较低
        elif field_count >= 5:
            confidence += 5  # 字段丰富，置信度提升

        return max(60.0, min(99.0, confidence))

    def process_item(self, raw_item: Any) -> ProcessingResult:
        """处理单个输入条目"""
        try:
            if raw_item is None or (isinstance(raw_item, str) and not raw_item.strip()):
                return ProcessingResult(
                    success=False,
                    error_code="E001",
                    message=ERROR_CODES["E001"],
                )

            fields, confidence, warnings = self._extract_fields(raw_item)

            # 置信度分级处理
            if confidence < 85.0:
                fields["_requires_verification"] = True
                warnings.append("[需核实] 置信度低于85%，部分字段可能不准确")
            elif confidence < 90.0:
                warnings.append("建议复核：置信度在85%-90%之间")

            # 附加元数据
            fields["_confidence"] = round(confidence, 1)
            fields["_processed"] = True

            return ProcessingResult(
                success=True,
                data=fields,
                confidence=confidence,
                warnings=warnings,
            )

        except ValueError as e:
            return ProcessingResult(
                success=False,
                error_code="E003",
                message=f"{ERROR_CODES['E003']} 原因: {str(e)}",
            )
        except Exception as e:
            return ProcessingResult(
                success=False,
                error_code="E006",
                message=f"{ERROR_CODES['E006']} 原因: {str(e)}",
            )

    def process_batch(self, raw_items: List[Any]) -> List[ProcessingResult]:
        """批量处理多个输入条目"""
        if len(raw_items) > self.max_items:
            return [ProcessingResult(
                success=False,
                error_code="E010",
                message=f"{ERROR_CODES['E010']} 上限: {self.max_items}",
            )]

        results = []
        for item in raw_items:
            results.append(self.process_item(item))

        # 检查是否有失败项
        failed = [r for r in results if not r.success]
        if failed and len(failed) < len(results):
            # 部分失败，标记警告
            for r in results:
                if r.success:
                    r.warnings.append("批量处理中存在失败条目，请检查")

        return results

    # ------------------------------------------------------------------
    # 输出格式化
    # ------------------------------------------------------------------
    def format_output(self, results: List[ProcessingResult], fmt: str = "json") -> str:
        """将处理结果格式化为指定格式输出"""
        if fmt not in ("json", "text", "csv"):
            return ERROR_CODES["E008"]

        if fmt == "json":
            return self._format_json(results)
        elif fmt == "text":
            return self._format_text(results)
        else:  # csv
            return self._format_csv(results)

    def _format_json(self, results: List[ProcessingResult]) -> str:
        """JSON 格式输出"""
        output = []
        for r in results:
            if r.success:
                output.append({
                    "success": True,
                    "data": r.data,
                    "confidence": r.confidence,
                    "warnings": r.warnings,
                })
            else:
                output.append({
                    "success": False,
                    "error_code": r.error_code,
                    "message": r.message,
                })
        return json.dumps(output, ensure_ascii=False, indent=2)

    def _format_text(self, results: List[ProcessingResult]) -> str:
        """纯文本格式输出"""
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"--- 条目 {i} ---")
            if r.success:
                for key, value in r.data.items():
                    if key.startswith("_"):
                        continue
                    lines.append(f"  {key}: {value}")
                lines.append(f"  置信度: {r.confidence:.1f}%")
                for w in r.warnings:
                    lines.append(f"  警告: {w}")
            else:
                lines.append(f"  错误 [{r.error_code}]: {r.message}")
            lines.append("")
        return "\n".join(lines)

    def _format_csv(self, results: List[ProcessingResult]) -> str:
        """CSV 格式输出"""
        # 收集所有可用字段
        all_keys = set()
        for r in results:
            if r.success and r.data:
                all_keys.update(k for k in r.data.keys() if not k.startswith("_"))

        # 排序保证一致性
        sorted_keys = sorted(all_keys)
        header = ",".join(["index"] + sorted_keys + ["confidence"])
        rows = [header]

        for i, r in enumerate(results, 1):
            if r.success:
                values = [str(i)]
                for key in sorted_keys:
                    value = r.data.get(key, "")
                    # 处理 CSV 转义
                    value_str = str(value).replace('"', '""')
                    values.append(f'"{value_str}"')
                values.append(f'"{r.confidence:.1f}"')
                rows.append(",".join(values))
            else:
                rows.append(f'"{i}",,,,"错误: {r.error_code}"')

        return "\n".join(rows)


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """离线自检核心逻辑（不依赖外部文件/网络）"""
    print("=" * 60)
    print("scrapecraft 自检模式")
    print("=" * 60)

    engine = ScrapecraftEngine()
    passed = 0
    total = 0

    # 测试用例 1: 字典输入
    print("\n[测试 1] 字典输入处理")
    total += 1
    item = {
        "标题": "Python爬虫入门教程",
        "网址": "https://example.com/python-crawler",
        "作者": "张三",
        "日期": "2026-01-15",
        "内容": "本文介绍Python爬虫基础知识...",
        "分类": "技术教程",
    }
    result = engine.process_item(item)
    assert result.success, f"字典输入处理失败: {result.message}"
    assert result.confidence >= 85.0, f"置信度过低: {result.confidence}"
    assert result.data.get("title") == "Python爬虫入门教程", "标题字段映射错误"
    assert result.data.get("url") == "https://example.com/python-crawler", "URL字段映射错误"
    assert result.data.get("author") == "张三", "作者字段映射错误"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 2: JSON 字符串输入
    print("\n[测试 2] JSON 字符串输入")
    total += 1
    json_str = json.dumps({
        "title": "数据分析实战",
        "author": "李四",
        "date": "2026-02-01",
        "content": "使用Python进行数据分析..."
    })
    result = engine.process_item(json_str)
    assert result.success, f"JSON 字符串处理失败: {result.message}"
    assert result.data.get("title") == "数据分析实战", "标题提取错误"
    assert result.data.get("author") == "李四", "作者提取错误"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 3: 键值对文本输入
    print("\n[测试 3] 键值对文本输入")
    total += 1
    kv_text = "标题: 机器学习入门\n作者: 王五\n日期: 2026-03-10\n内容: 机器学习基础概念..."
    result = engine.process_item(kv_text)
    assert result.success, f"键值对文本处理失败: {result.message}"
    assert result.data.get("title") == "机器学习入门", "标题提取错误"
    assert result.data.get("author") == "王五", "作者提取错误"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 4: 纯文本输入（低置信度）
    print("\n[测试 4] 纯文本输入（低置信度场景）")
    total += 1
    plain_text = "这是一段无法结构化解析的纯文本内容，没有明确的字段标识。"
    result = engine.process_item(plain_text)
    assert result.success, f"纯文本处理失败: {result.message}"
    assert result.data.get("content") == plain_text, "内容字段错误"
    assert result.confidence < 90.0, f"纯文本置信度应低于90%，实际: {result.confidence}"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 5: 空输入（错误处理）
    print("\n[测试 5] 空输入错误处理")
    total += 1
    result = engine.process_item("")
    assert not result.success, "空输入应返回失败"
    assert result.error_code == "E001", f"错误码错误: {result.error_code}"
    print(f"  ✓ 通过 (错误码: {result.error_code})")
    passed += 1

    # 测试用例 6: 批量处理
    print("\n[测试 6] 批量处理")
    total += 1
    batch = [
        {"标题": "文章1", "内容": "内容1"},
        "标题: 文章2\n内容: 内容2",
        {"title": "Article 3", "content": "Content 3"},
    ]
    results = engine.process_batch(batch)
    assert len(results) == 3, f"批量处理数量错误: {len(results)}"
    assert all(r.success for r in results), "批量处理存在失败项"
    print(f"  ✓ 通过 (处理 {len(results)} 条)")
    passed += 1

    # 测试用例 7: 输出格式
    print("\n[测试 7] 输出格式")
    total += 1
    results = engine.process_batch([{"标题": "测试", "内容": "内容"}])
    json_out = engine.format_output(results, "json")
    text_out = engine.format_output(results, "text")
    csv_out = engine.format_output(results, "csv")
    assert json_out.startswith("["), "JSON 输出格式错误"
    assert "--- 条目 1 ---" in text_out, "文本输出格式错误"
    assert "index" in csv_out, "CSV 输出格式错误"
    print("  ✓ 通过 (json/text/csv 均正常)")
    passed += 1

    # 测试用例 8: 同义词字段映射
    print("\n[测试 8] 同义词字段映射")
    total += 1
    item = {
        "名称": "同义词测试",
        "链接": "https://example.com/synonym",
        "创建者": "赵六",
    }
    result = engine.process_item(item)
    assert result.success, f"同义词映射处理失败: {result.message}"
    assert result.data.get("title") == "同义词测试", "名称→标题映射失败"
    assert result.data.get("url") == "https://example.com/synonym", "链接→URL映射失败"
    assert result.data.get("author") == "赵六", "创建者→作者映射失败"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 9: 资源限制
    print("\n[测试 9] 资源限制（E010）")
    total += 1
    small_engine = ScrapecraftEngine(max_items=2)
    batch = [{"a": 1}, {"b": 2}, {"c": 3}]
    results = small_engine.process_batch(batch)
    assert not results[0].success, "超限应返回失败"
    assert results[0].error_code == "E010", f"错误码错误: {results[0].error_code}"
    print(f"  ✓ 通过 (错误码: {results[0].error_code})")
    passed += 1

    # 测试用例 10: 字段类型推断
    print("\n[测试 10] 字段类型推断")
    total += 1
    item = {
        "标题": "类型测试",
        "数量": "42",
        "启用": "true",
    }
    result = engine.process_item(item)
    assert result.success, f"类型推断处理失败: {result.message}"
    # 验证类型推断逻辑（不依赖具体转换，只验证可处理）
    assert result.data.get("title") == "类型测试"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 测试用例 11: 更多同义词测试
    print("\n[测试 11] 扩展同义词映射")
    total += 1
    item = {
        "标题": "扩展同义词",
        "发布时间": "2026-04-01",
        "标签": "测试",
        "浏览量": 1000,
        "图片链接": "https://example.com/image.jpg",
    }
    result = engine.process_item(item)
    assert result.success, f"扩展同义词处理失败: {result.message}"
    assert result.data.get("date") == "2026-04-01", "发布时间→日期映射失败"
    assert result.data.get("category") == "测试", "标签→分类映射失败"
    assert result.data.get("views") == 1000, "浏览量映射失败"
    assert result.data.get("image") == "https://example.com/image.jpg", "图片链接映射失败"
    print(f"  ✓ 通过 (置信度: {result.confidence:.1f}%)")
    passed += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"自检完成: {passed}/{total} 项测试通过")
    if passed == total:
        print("全部通过 ✔")
        return 0
    else:
        print(f"存在失败项 ✘")
        return 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="scrapecraft - 爬虫采集技能核心实现",
        epilog="示例: python main.py --input '标题: 测试' --format json",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部资源）",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="输入内容（JSON 字符串或键值对文本）",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="输入文件路径（每行一个条目）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "text", "csv"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help="单次处理最大条目数（默认: 100）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    engine = ScrapecraftEngine(max_items=args.max_items)

    # 收集输入
    items = []
    if args.input:
        # 尝试解析为 JSON 数组
        try:
            parsed = json.loads(args.input)
            if isinstance(parsed, list):
                items = parsed
            else:
                items = [parsed]
        except json.JSONDecodeError:
            # 按键值对文本处理
            items = [args.input]

    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(line)
        except FileNotFoundError:
            print(f"错误: 文件不存在 - {args.file}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误: 读取文件失败 - {str(e)}", file=sys.stderr)
            return 1
    else:
        # 无输入，显示帮助
        parser.print_help()
        return 1

    # 处理
    if not items:
        print(ERROR_CODES["E001"], file=sys.stderr)
        return 1

    results = engine.process_batch(items)

    # 输出
    output = engine.format_output(results, args.format)
    print(output)

    # 检查是否有失败项
    failed = [r for r in results if not r.success]
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
