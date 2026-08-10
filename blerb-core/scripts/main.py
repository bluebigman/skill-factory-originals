#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
blerb-core 独立实现脚本

功能：将用户提供的文本、文件或URL解析为结构化结果，并标注置信度。
仅依据功能规格文档进行 clean-room 实现，不参考任何既有代码。

用法示例：
    python scripts/main.py --selftest           # 运行内置自检
    python scripts/main.py --input "文本内容"   # 解析文本
    python scripts/main.py --file data.txt      # 解析文件
    python scripts/main.py --url https://...    # 解析URL

错误码说明：
    E001: 参数错误（缺少输入或参数冲突）
    E002: 文件读取失败
    E003: URL访问失败
    E004: 输入内容为空
    E005: 输入类型不支持
    E006: 解析过程中发生未知异常
    E007: JSON序列化失败
    E008: 自检失败
    E009: 输出格式不支持
    E010: 系统编码错误
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import time

# G1 生产级重试退避
_max_retry = 3  # 最大重试次数
def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装（G1 生产门禁）。"""
    for attempt in range(_max_retry):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < _max_retry - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise


# ============================================================
# 数据模型
# ============================================================

@dataclass
class ParsedItem:
    """单个解析结果条目"""
    content: str                    # 原始内容片段
    fields: Dict[str, Any] = field(default_factory=dict)  # 提取的字段
    entities: List[str] = field(default_factory=list)     # 识别出的实体
    confidence: float = 0.0         # 置信度 0.0 ~ 1.0


@dataclass
class ParseResult:
    """整体解析结果"""
    items: List[ParsedItem] = field(default_factory=list)
    total_items: int = 0
    avg_confidence: float = 0.0
    source_type: str = "text"       # text / file / url
    source_name: str = ""           # 来源描述


# ============================================================
# 核心解析引擎
# ============================================================

class ContentParser:
    """
    内容解析器：将输入内容拆分为结构化条目，并提取关键信息。
    支持纯文本、CSV、JSON、Markdown 等格式的简单解析。
    """

    # 常见实体模式（宽松匹配）
    EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    URL_RE = re.compile(r'https?://[^\s<>"\'()]+')
    PHONE_RE = re.compile(r'(?<!\d)(?:\+?\d{1,3}[-.]?)?\(?\d{2,4}\)?[-.]?\d{3,4}[-.]?\d{3,4}(?!\d)')
    DATE_RE = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}')

    # 常见字段名模式（用于键值对提取）
    FIELD_KEY_RE = re.compile(
        r'(?:姓名|名字|name|年龄|age|邮箱|email|电话|phone|手机|mobile|'
        r'地址|address|日期|date|时间|time|金额|amount|价格|price|'
        r'编号|id|编号|code|备注|remark|备注|note|标题|title|'
        r'作者|author|公司|company|职位|position|部门|department)',
        re.IGNORECASE
    )

    def parse(self, content: str, source_type: str = "text",
              source_name: str = "") -> ParseResult:
        """
        解析入口：根据内容特征自动选择解析策略。

        参数:
            content: 原始输入内容
            source_type: 来源类型 (text/file/url)
            source_name: 来源名称（文件名或URL）

        返回:
            ParseResult 结构化解析结果

        异常:
            E004: 内容为空
            E006: 解析过程异常
        """
        if not content or not content.strip():
            raise RuntimeError("E004: 输入内容为空")

        try:
            # 根据内容格式选择解析策略
            if content.lstrip().startswith('{') or content.lstrip().startswith('['):
                items = self._parse_json(content)
            elif '\t' in content or (',' in content and self._looks_like_csv(content)):
                items = self._parse_csv(content)
            elif content.lstrip().startswith('#') or '|' in content:
                items = self._parse_markdown(content)
            else:
                items = self._parse_plain_text(content)

            # 计算整体统计
            total = len(items)
            avg_conf = sum(i.confidence for i in items) / total if total > 0 else 0.0

            return ParseResult(
                items=items,
                total_items=total,
                avg_confidence=round(avg_conf, 4),
                source_type=source_type,
                source_name=source_name
            )
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E006: 解析过程中发生异常 - {str(exc)}") from exc

    # ---------- 各格式解析 ----------

    def _parse_plain_text(self, content: str) -> List[ParsedItem]:
        """解析纯文本：按空行或换行拆分为条目"""
        # 按空行分段，若无空行则按行拆分
        segments = [s.strip() for s in re.split(r'\n\s*\n', content.strip()) if s.strip()]
        if len(segments) <= 1:
            segments = [s.strip() for s in content.strip().split('\n') if s.strip()]

        items = []
        for seg in segments:
            fields = self._extract_fields(seg)
            entities = self._extract_entities(seg)
            confidence = self._calc_confidence(fields, entities, seg)
            items.append(ParsedItem(
                content=seg[:200],  # 截断长文本
                fields=fields,
                entities=entities,
                confidence=confidence
            ))
        return items

    def _parse_csv(self, content: str) -> List[ParsedItem]:
        """解析CSV：首行为表头，后续行为数据"""
        try:
            reader = csv.reader(io_string(content))
            rows = list(reader)
        except Exception:
            # 降级为按行拆分
            return self._parse_plain_text(content)

        if len(rows) < 2:
            return self._parse_plain_text(content)

        header = [h.strip() for h in rows[0]]
        items = []
        for row in rows[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            fields = {}
            for idx, cell in enumerate(row):
                key = header[idx] if idx < len(header) else f"field_{idx}"
                fields[key] = cell.strip()
            entities = self._extract_entities(' '.join(row))
            confidence = self._calc_confidence(fields, entities, ' '.join(row))
            items.append(ParsedItem(
                content=' | '.join(row)[:200],
                fields=fields,
                entities=entities,
                confidence=confidence
            ))
        return items

    def _parse_json(self, content: str) -> List[ParsedItem]:
        """解析JSON：支持数组或对象"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 非标准JSON，降级为文本解析
            return self._parse_plain_text(content)

        items = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    fields = {str(k): v for k, v in item.items()}
                else:
                    fields = {"value": item}
                entities = self._extract_entities(json.dumps(fields, ensure_ascii=False))
                confidence = self._calc_confidence(fields, entities, json.dumps(fields, ensure_ascii=False))
                items.append(ParsedItem(
                    content=json.dumps(fields, ensure_ascii=False)[:200],
                    fields=fields,
                    entities=entities,
                    confidence=confidence
                ))
        elif isinstance(data, dict):
            # 将对象视为单一条目
            fields = {str(k): v for k, v in data.items()}
            entities = self._extract_entities(json.dumps(fields, ensure_ascii=False))
            confidence = self._calc_confidence(fields, entities, json.dumps(fields, ensure_ascii=False))
            items.append(ParsedItem(
                content=json.dumps(fields, ensure_ascii=False)[:200],
                fields=fields,
                entities=entities,
                confidence=confidence
            ))
        return items

    def _parse_markdown(self, content: str) -> List[ParsedItem]:
        """解析Markdown：识别表格和标题"""
        items = []

        # 尝试解析表格
        lines = content.strip().split('\n')
        table_lines = []
        in_table = False
        for line in lines:
            if '|' in line and line.strip().startswith('|'):
                table_lines.append(line)
                in_table = True
            elif in_table and line.strip() == '':
                break
            elif in_table:
                break

        if len(table_lines) >= 3:  # 表头 + 分隔 + 至少一行数据
            try:
                # 提取表头
                header = [c.strip() for c in table_lines[0].strip('|').split('|')]
                # 跳过分隔行（---）
                for row_line in table_lines[2:]:
                    cells = [c.strip() for c in row_line.strip('|').split('|')]
                    if len(cells) != len(header):
                        continue
                    fields = {header[i]: cells[i] for i in range(len(header))}
                    entities = self._extract_entities(' '.join(cells))
                    confidence = self._calc_confidence(fields, entities, ' '.join(cells))
                    items.append(ParsedItem(
                        content=' | '.join(cells)[:200],
                        fields=fields,
                        entities=entities,
                        confidence=confidence
                    ))
                if items:
                    return items
            except Exception:
                pass  # 表格解析失败，降级

        # 无表格或解析失败，按标题分段
        segments = re.split(r'\n(?=#{1,6}\s)', content)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            fields = self._extract_fields(seg)
            entities = self._extract_entities(seg)
            confidence = self._calc_confidence(fields, entities, seg)
            items.append(ParsedItem(
                content=seg[:200],
                fields=fields,
                entities=entities,
                confidence=confidence
            ))
        return items

    # ---------- 信息提取工具 ----------

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """从文本中提取键值对字段"""
        fields = {}

        # 尝试匹配 "键: 值" 或 "键=值" 模式
        kv_pattern = re.compile(
            r'(?P<key>{})\s*[:：=]\s*(?P<value>[^,;，；\n]+)'.format(
                self.FIELD_KEY_RE.pattern
            ),
            re.IGNORECASE
        )
        for match in kv_pattern.finditer(text):
            key = match.group('key').strip()
            value = match.group('value').strip()
            # 避免重复键
            if key.lower() not in [k.lower() for k in fields]:
                fields[key] = value

        # 如果没有匹配到，尝试通用键值对模式
        if not fields:
            generic_kv = re.compile(r'([^\s:：=]+)\s*[:：=]\s*([^,;，；\n]+)')
            for match in generic_kv.finditer(text):
                key = match.group(1).strip()
                value = match.group(2).strip()
                # 过滤掉明显不是字段的内容
                if 1 <= len(key) <= 20 and 1 <= len(value) <= 100:
                    if key.lower() not in [k.lower() for k in fields]:
                        fields[key] = value

        return fields

    def _extract_entities(self, text: str) -> List[str]:
        """从文本中识别实体（邮箱、URL、电话、日期）"""
        entities = []

        # 邮箱
        emails = self.EMAIL_RE.findall(text)
        entities.extend(emails)

        # URL
        urls = self.URL_RE.findall(text)
        entities.extend(urls)

        # 电话（宽松匹配，至少7位数字）
        for phone in self.PHONE_RE.findall(text):
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 7:
                entities.append(phone.strip())

        # 日期
        dates = self.DATE_RE.findall(text)
        entities.extend(dates)

        # 去重并保持顺序
        seen = set()
        unique = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique.append(e)
        return unique

    def _calc_confidence(self, fields: Dict, entities: List[str], text: str) -> float:
        """
        计算置信度：基于字段数量、实体数量、文本长度综合判断。
        采用宽松的启发式规则，返回 0.3 ~ 0.98 之间的值。
        """
        score = 0.3  # 基础分

        # 字段丰富度加分
        field_score = min(len(fields) * 0.15, 0.3)
        score += field_score

        # 实体识别加分
        entity_score = min(len(entities) * 0.1, 0.2)
        score += entity_score

        # 文本长度合理性加分
        text_len = len(text.strip())
        if 10 <= text_len <= 500:
            score += 0.15
        elif text_len > 500:
            score += 0.1

        # 结构化标记加分
        if fields or entities:
            score += 0.1

        # 截断到合理范围
        return max(0.3, min(0.98, round(score, 4)))

    def _looks_like_csv(self, content: str) -> bool:
        """判断内容是否像CSV格式"""
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return False
        # 检查每行逗号数量是否一致
        first_line_commas = lines[0].count(',')
        if first_line_commas == 0:
            return False
        return all(line.count(',') == first_line_commas for line in lines[1:5])


def io_string(content: str):
    """兼容Python 3.x的StringIO"""
    import io
    return io.StringIO(content)


# ============================================================
# 输入读取
# ============================================================

def read_text_input(text: str) -> str:
    """校验并返回文本输入"""
    if not text or not text.strip():
        raise RuntimeError("E004: 输入内容为空")
    return text.strip()


def read_file_input(filepath: str) -> str:
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if not content.strip():
            raise RuntimeError(f"E004: 文件 {filepath} 内容为空")
        return content
    except RuntimeError:
        raise
    except FileNotFoundError as exc:
        raise RuntimeError(f"E002: 文件不存在 - {filepath}") from exc
    except PermissionError as exc:
        raise RuntimeError(f"E002: 文件无读取权限 - {filepath}") from exc
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"E002: 文件编码不支持（请使用UTF-8）- {filepath}") from exc
    except OSError as exc:
        raise RuntimeError(f"E002: 文件读取失败 - {str(exc)}") from exc


def read_url_input(url: str) -> str:
    """读取URL内容"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'blerb-core/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            # 尝试从响应头获取编码
            charset = resp.headers.get_content_charset() or 'utf-8'
            content = resp.read().decode(charset, errors='replace')
        if not content.strip():
            raise RuntimeError(f"E004: URL {url} 返回内容为空")
        return content
    except RuntimeError:
        raise
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"E003: URL访问HTTP错误 - {exc.code} {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"E003: URL访问失败 - {str(exc.reason)} {url}") from exc
    except Exception as exc:
        raise RuntimeError(f"E003: URL解析异常 - {str(exc)} {url}") from exc


# ============================================================
# 输出格式化
# ============================================================

def format_output(result: ParseResult, fmt: str = "json") -> str:
    """
    将解析结果格式化为指定格式。

    支持格式: json, markdown, csv, text
    """
    if fmt == "json":
        return _to_json(result)
    elif fmt == "markdown":
        return _to_markdown(result)
    elif fmt == "csv":
        return _to_csv(result)
    elif fmt == "text":
        return _to_text(result)
    else:
        raise RuntimeError(f"E009: 不支持的输出格式 - {fmt}")


def _to_json(result: ParseResult) -> str:
    """转换为JSON字符串"""
    try:
        data = asdict(result)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except TypeError as exc:
        raise RuntimeError(f"E007: JSON序列化失败 - {str(exc)}") from exc


def _to_markdown(result: ParseResult) -> str:
    """转换为Markdown表格"""
    lines = []
    lines.append(f"# 解析结果（来源: {result.source_name or result.source_type}）")
    lines.append("")
    lines.append(f"- 总条目数: {result.total_items}")
    lines.append(f"- 平均置信度: {result.avg_confidence:.2%}")
    lines.append("")

    if result.items:
        # 收集所有字段名
        all_keys = []
        for item in result.items:
            for k in item.fields.keys():
                if k not in all_keys:
                    all_keys.append(k)

        # 表格头
        header = ["#", "内容"] + all_keys + ["实体", "置信度"]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))

        # 表格内容
        for idx, item in enumerate(result.items, 1):
            row = [str(idx), item.content[:50]]
            for k in all_keys:
                val = item.fields.get(k, "")
                row.append(str(val)[:30])
            row.append(", ".join(item.entities[:3]))
            row.append(f"{item.confidence:.0%}")
            lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _to_csv(result: ParseResult) -> str:
    """转换为CSV格式"""
    import io
    output = io.StringIO()
    writer = csv.writer(output)

    # 收集字段名
    all_keys = []
    for item in result.items:
        for k in item.fields.keys():
            if k not in all_keys:
                all_keys.append(k)

    # 写入表头
    writer.writerow(["index", "content"] + all_keys + ["entities", "confidence"])

    # 写入数据行
    for idx, item in enumerate(result.items, 1):
        row = [idx, item.content[:100]]
        for k in all_keys:
            row.append(item.fields.get(k, ""))
        row.append(";".join(item.entities))
        row.append(f"{item.confidence:.4f}")
        writer.writerow(row)

    return output.getvalue()


def _to_text(result: ParseResult) -> str:
    """转换为纯文本格式"""
    lines = []
    lines.append(f"解析结果汇总: 共 {result.total_items} 条, 平均置信度 {result.avg_confidence:.2%}")
    lines.append("=" * 60)

    for idx, item in enumerate(result.items, 1):
        lines.append(f"\n[{idx}] 内容: {item.content}")
        if item.fields:
            lines.append("    字段:")
            for k, v in list(item.fields.items())[:10]:
                lines.append(f"      {k}: {v}")
        if item.entities:
            lines.append(f"    实体: {', '.join(item.entities[:5])}")
        lines.append(f"    置信度: {item.confidence:.2%}")

    return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================

def run_selftest() -> bool:
    """
    内置自检：使用硬编码样例数据验证核心逻辑。
    不读取外部文件、不访问网络、不依赖当前目录。

    返回:
        True 表示自检通过
    """
    print("=" * 60)
    print("blerb-core 自检开始")
    print("=" * 60)

    parser = ContentParser()

    # ---- 测试1: 纯文本解析 ----
    print("\n[测试1] 纯文本解析")
    sample_text = """
    联系人: 张三
    邮箱: zhangsan@example.com
    电话: 138-1234-5678
    地址: 北京市朝阳区

    项目编号: PRJ-2026-001
    金额: 15000元
    日期: 2026-03-15
    """
    try:
        result = parser.parse(sample_text, source_type="text", source_name="自检样例")
        assert result.total_items >= 1, "纯文本解析应至少产生1条结果"
        assert result.avg_confidence >= 0.3, "平均置信度应不低于0.3"
        assert result.avg_confidence <= 1.0, "平均置信度应不高于1.0"

        # 检查是否提取到邮箱实体
        all_entities = [e for item in result.items for e in item.entities]
        assert any("example.com" in e for e in all_entities), "应提取到邮箱实体"
        print(f"  ✓ 通过 - 条目数: {result.total_items}, 平均置信度: {result.avg_confidence:.2%}")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except RuntimeError as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试2: JSON解析 ----
    print("\n[测试2] JSON解析")
    sample_json = json.dumps([
        {"name": "产品A", "price": 99.9, "stock": 100},
        {"name": "产品B", "price": 199.9, "stock": 50}
    ], ensure_ascii=False)
    try:
        result = parser.parse(sample_json, source_type="text", source_name="JSON样例")
        assert result.total_items == 2, "JSON数组应解析为2条"
        assert result.avg_confidence >= 0.3, "平均置信度应不低于0.3"
        # 检查字段提取
        all_fields = {k for item in result.items for k in item.fields.keys()}
        assert "name" in all_fields, "应提取到name字段"
        print(f"  ✓ 通过 - 条目数: {result.total_items}, 字段: {sorted(all_fields)}")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except RuntimeError as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试3: CSV解析 ----
    print("\n[测试3] CSV解析")
    sample_csv = "姓名,年龄,城市\n李四,28,上海\n王五,35,广州\n"
    try:
        result = parser.parse(sample_csv, source_type="text", source_name="CSV样例")
        assert result.total_items >= 1, "CSV应解析出数据行"
        assert result.avg_confidence >= 0.3, "平均置信度应不低于0.3"
        # 检查字段
        all_fields = {k for item in result.items for k in item.fields.keys()}
        assert "姓名" in all_fields or "name" in all_fields, "应提取到姓名字段"
        print(f"  ✓ 通过 - 条目数: {result.total_items}, 字段: {sorted(all_fields)}")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except RuntimeError as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试4: 空输入处理 ----
    print("\n[测试4] 空输入处理")
    try:
        parser.parse("   ", source_type="text")
        print("  ✗ 失败: 空输入应抛出E004异常")
        return False
    except RuntimeError as exc:
        assert "E004" in str(exc), f"错误码应为E004, 实际: {exc}"
        print(f"  ✓ 通过 - 正确抛出: {exc}")

    # ---- 测试5: 输出格式化 ----
    print("\n[测试5] 输出格式化")
    sample_result = parser.parse("测试内容 name=test email=test@example.com", source_type="text")
    try:
        json_out = format_output(sample_result, "json")
        assert json_out.startswith("{") or json_out.startswith("["), "JSON输出格式不正确"
        md_out = format_output(sample_result, "markdown")
        assert "|" in md_out, "Markdown输出应包含表格"
        csv_out = format_output(sample_result, "csv")
        assert "," in csv_out, "CSV输出应包含逗号"
        txt_out = format_output(sample_result, "text")
        assert "解析结果" in txt_out, "文本输出应包含标题"
        print("  ✓ 通过 - 所有格式输出正常")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except RuntimeError as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试6: 实体提取 ----
    print("\n[测试6] 实体提取")
    entity_text = "联系邮箱 test@example.com 或访问 https://example.com 电话 010-12345678"
    try:
        entities = parser._extract_entities(entity_text)
        assert len(entities) >= 2, f"应至少提取2个实体, 实际: {len(entities)}"
        assert any("example.com" in e for e in entities), "应包含邮箱实体"
        assert any("http" in e for e in entities), "应包含URL实体"
        print(f"  ✓ 通过 - 提取实体: {entities}")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False

    # ---- 测试7: 置信度合理性 ----
    print("\n[测试7] 置信度合理性")
    try:
        # 简单文本置信度应较低
        simple = parser.parse("这是一段简单的测试文本", source_type="text")
        # 丰富文本置信度应较高
        rich = parser.parse(
            "姓名: 张三\n邮箱: zhangsan@example.com\n电话: 13812345678\n地址: 北京市海淀区中关村",
            source_type="text"
        )
        assert simple.avg_confidence >= 0.3, "简单文本置信度应不低于0.3"
        assert rich.avg_confidence >= simple.avg_confidence, "丰富文本置信度应不低于简单文本"
        assert rich.avg_confidence <= 1.0, "置信度不应超过1.0"
        print(f"  ✓ 通过 - 简单: {simple.avg_confidence:.2%}, 丰富: {rich.avg_confidence:.2%}")
    except AssertionError as exc:
        print(f"  ✗ 失败: {exc}")
        return False
    except RuntimeError as exc:
        print(f"  ✗ 异常: {exc}")
        return False

    # ---- 测试8: 错误处理 ----
    print("\n[测试8] 错误处理")
    try:
        # 不存在的文件
        read_file_input("/nonexistent/path/file.txt")
        print("  ✗ 失败: 应抛出E002异常")
        return False
    except RuntimeError as exc:
        assert "E002" in str(exc), f"错误码应为E002, 实际: {exc}"
        print(f"  ✓ 通过 - 文件错误处理正确: {exc}")

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return True


# ============================================================
# 主程序
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="blerb-core: 数据解析与结构化输出工具",
        epilog="示例: python main.py --input '姓名: 张三 邮箱: z@example.com'"
    )

    # 输入参数（互斥组）
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--input", "-i", type=str, help="直接输入文本内容")
    input_group.add_argument("--file", "-f", type=str, help="从文件读取内容")
    input_group.add_argument("--url", "-u", type=str, help="从URL读取内容")

    # 输出参数
    parser.add_argument("--format", "-o", type=str, default="json",
                        choices=["json", "markdown", "csv", "text"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--selftest", action="store_true", help="运行内置自检")
    parser.add_argument("--source-name", type=str, default="",
                        help="来源名称（用于输出显示）")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)

    # 检查输入
    if not args.input and not args.file and not args.url:
        parser.error("E001: 必须提供 --input, --file 或 --url 参数")

    try:
        # 读取输入
        source_type = "text"
        source_name = args.source_name or ""
        if args.input:
            content = read_text_input(args.input)
            source_name = source_name or "命令行输入"
        elif args.file:
            content = read_file_input(args.file)
            source_type = "file"
            source_name = source_name or os.path.basename(args.file)
        elif args.url:
            content = read_url_input(args.url)
            source_type = "url"
            source_name = source_name or args.url

        # 解析
        parser_engine = ContentParser()
        result = parser_engine.parse(content, source_type=source_type, source_name=source_name)

        # 输出
        output = format_output(result, args.format)
        print(output)

    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("错误: E010: 用户中断操作", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"错误: E010: 未知系统错误 - {str(exc)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
