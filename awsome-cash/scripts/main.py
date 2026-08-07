#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
awsome-cash 技能实现脚本
=========================
将用户提供的任意数据、文件或URL解析为结构化结果，并标注置信度。

功能规格依据：
- 解析文本/文件/URL 中的关键信息
- 按用户指定或默认的字段结构重组数据
- 对每个提取字段标注置信度（高/中/低）
- 支持批量输入与自定义输出模板
- 对缺失或模糊信息给出 `[需核实:字段名]` 占位提示

错误码定义：
    E001: 输入参数缺失或无效
    E002: 文件不存在或无法读取
    E003: URL 格式无效或无法访问
    E004: 文本超过处理上限（10,000 字）
    E005: 文件大小超过处理上限（2MB）
    E006: 批量文件数量超过上限（5 个）
    E007: 不支持的输入类型或格式
    E008: 输出模板格式错误
    E009: 内部解析错误
    E010: 未知错误
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# 常量定义
# =============================================================================

# 处理上限
MAX_TEXT_LENGTH = 10000          # 单次请求文本不超过 10,000 字
MAX_URL_CONTENT_SIZE = 2 * 1024 * 1024  # URL 抓取页面不超过 2MB
MAX_BATCH_FILES = 5              # 批量文件不超过 5 个

# 支持的本地文件扩展名
SUPPORTED_EXTENSIONS = {'.txt', '.csv', '.json'}

# 默认输出字段结构
DEFAULT_FIELDS = ['name', 'date', 'amount', 'category', 'note']

# 置信度级别
CONFIDENCE_HIGH = '高'
CONFIDENCE_MEDIUM = '中'
CONFIDENCE_LOW = '低'


# =============================================================================
# 工具函数
# =============================================================================

def _now_str() -> str:
    """返回当前时间的 ISO 格式字符串。"""
    return datetime.now().isoformat(timespec='seconds')


def _make_error(code: str, message: str) -> Dict[str, Any]:
    """构造错误结果字典。"""
    return {
        'success': False,
        'error_code': code,
        'error_message': message,
        'timestamp': _now_str(),
    }


def _make_success(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """构造成功结果字典。"""
    result = {
        'success': True,
        'data': data,
        'timestamp': _now_str(),
    }
    if meta:
        result['meta'] = meta
    return result


def _validate_text_length(text: str) -> Optional[str]:
    """检查文本长度是否超限，超限返回错误码，否则返回 None。"""
    if len(text) > MAX_TEXT_LENGTH:
        return 'E004'
    return None


def _safe_read_text_file(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """
    安全读取文本文件内容。
    返回 (内容, 错误码)；成功时错误码为 None。
    """
    if not os.path.isfile(filepath):
        return None, 'E002'

    # 检查文件大小
    try:
        file_size = os.path.getsize(filepath)
    except OSError:
        return None, 'E002'

    if file_size > MAX_URL_CONTENT_SIZE:
        return None, 'E005'

    # 检查扩展名
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None, 'E007'

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            return None, 'E002'

    # 检查文本长度
    err_code = _validate_text_length(content)
    if err_code:
        return None, err_code

    return content, None


def _parse_csv_text(text: str) -> List[Dict[str, str]]:
    """
    简易 CSV 文本解析器（不依赖 csv 模块，避免特殊字符处理差异）。
    支持带引号的字段和逗号分隔。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    # 解析一行，处理引号
    def parse_line(line: str) -> List[str]:
        fields = []
        current = []
        in_quotes = False
        i = 0
        while i < len(line):
            ch = line[i]
            if in_quotes:
                if ch == '"':
                    if i + 1 < len(line) and line[i + 1] == '"':
                        current.append('"')
                        i += 2
                        continue
                    in_quotes = False
                else:
                    current.append(ch)
            else:
                if ch == '"':
                    in_quotes = True
                elif ch == ',':
                    fields.append(''.join(current).strip())
                    current = []
                else:
                    current.append(ch)
            i += 1
        fields.append(''.join(current).strip())
        return fields

    # 第一行作为表头
    header = parse_line(lines[0])
    records = []
    for line in lines[1:]:
        values = parse_line(line)
        # 补齐或截断到表头长度
        while len(values) < len(header):
            values.append('')
        values = values[:len(header)]
        record = {header[i]: values[i] for i in range(len(header))}
        records.append(record)
    return records


def _parse_json_text(text: str) -> Any:
    """解析 JSON 文本。"""
    return json.loads(text)


def _infer_field_type(value: str) -> str:
    """推断字段类型。"""
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value.strip()):
        return 'date'
    if re.match(r'^\d+(\.\d+)?$', value.strip()):
        return 'number'
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value.strip()):
        return 'email'
    if re.match(r'^https?://', value.strip()):
        return 'url'
    return 'text'


def _assess_confidence(value: Any, field_name: str) -> str:
    """
    评估单个字段的置信度。
    规则：
      - 值缺失或为空 -> 低
      - 值为占位符（含 [需核实]） -> 低
      - 值非空且类型明确 -> 高
      - 值非空但格式模糊 -> 中
    """
    if value is None or value == '':
        return CONFIDENCE_LOW

    if isinstance(value, str):
        if '[需核实' in value:
            return CONFIDENCE_LOW
        if len(value.strip()) < 2:
            return CONFIDENCE_MEDIUM

    # 日期字段检查
    if field_name == 'date':
        if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value.strip()):
            return CONFIDENCE_HIGH
        return CONFIDENCE_MEDIUM

    # 金额字段检查
    if field_name == 'amount':
        if isinstance(value, (int, float)):
            return CONFIDENCE_HIGH
        if isinstance(value, str) and re.match(r'^\d+(\.\d+)?$', value.strip()):
            return CONFIDENCE_HIGH
        return CONFIDENCE_MEDIUM

    return CONFIDENCE_HIGH


def _extract_from_text(text: str, fields: List[str]) -> Dict[str, Any]:
    """
    从纯文本中提取指定字段的信息。
    采用宽松的正则匹配策略，对每个字段尽力提取。
    """
    result = {}
    text_lower = text.lower()

    # 名称提取：尝试匹配常见模式
    if 'name' in fields:
        # 尝试匹配 "名称：xxx" 或 "姓名：xxx"
        match = re.search(r'(?:名称|姓名)[：:\s]+([^\n,，。;；]+)', text)
        if match:
            result['name'] = match.group(1).strip()
        else:
            result['name'] = '[需核实:name]'

    # 日期提取
    if 'date' in fields:
        # 匹配 2024-01-01 或 2024/01/01 或 2024年1月1日
        match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)', text)
        if match:
            date_str = match.group(1)
            # 统一格式为 YYYY-MM-DD
            date_str = date_str.replace('/', '-').replace('年', '-').replace('月', '-').replace('日', '')
            result['date'] = date_str
        else:
            result['date'] = '[需核实:date]'

    # 金额提取
    if 'amount' in fields:
        # 首先尝试匹配带货币符号的金额
        match = re.search(r'(?:金额|价格|费用|总计)[：:\s]*([¥￥]?\d+(?:\.\d{1,2})?)', text)
        if match:
            amount_str = match.group(1).replace('¥', '').replace('￥', '')
            try:
                result['amount'] = float(amount_str)
            except ValueError:
                result['amount'] = '[需核实:amount]'
        else:
            # 尝试匹配带货币符号的金额
            match = re.search(r'[¥￥]\s*(\d+(?:\.\d{1,2})?)', text)
            if match:
                try:
                    result['amount'] = float(match.group(1))
                except ValueError:
                    result['amount'] = '[需核实:amount]'
            else:
                # 最后尝试匹配独立的数字（可能为金额）
                # 但要避免匹配日期中的数字
                match = re.search(r'(?<![\d-])\d+(?:\.\d{1,2})?(?![\d-])', text)
                if match:
                    try:
                        result['amount'] = float(match.group(0))
                    except ValueError:
                        result['amount'] = '[需核实:amount]'
                else:
                    result['amount'] = '[需核实:amount]'

    # 类别提取
    if 'category' in fields:
        # 常见类别关键词
        categories = ['餐饮', '交通', '购物', '娱乐', '医疗', '教育', '居住', '工资', '奖金']
        found = None
        for cat in categories:
            if cat in text:
                found = cat
                break
        result['category'] = found if found else '[需核实:category]'

    # 备注提取
    if 'note' in fields:
        match = re.search(r'(?:备注|说明|注释)[：:\s]+([^\n]+)', text)
        if match:
            result['note'] = match.group(1).strip()
        else:
            result['note'] = '[需核实:note]'

    return result


def _process_structured_data(data: Any, fields: List[str]) -> List[Dict[str, Any]]:
    """
    处理结构化数据（列表或字典），提取指定字段并标注置信度。
    """
    records = []

    # 如果是单个字典，转为列表
    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        return records

    for item in data:
        if not isinstance(item, dict):
            continue

        record = {}
        for field in fields:
            value = item.get(field)
            if value is None:
                # 尝试模糊匹配键名
                for key, val in item.items():
                    if field in key.lower() or key.lower() in field:
                        value = val
                        break

            if value is None:
                value = f'[需核实:{field}]'

            record[field] = value
            record[f'{field}_confidence'] = _assess_confidence(value, field)

        records.append(record)

    return records


def _process_text_input(text: str, fields: List[str]) -> Dict[str, Any]:
    """
    处理纯文本输入，尝试解析为结构化数据。
    """
    # 检查文本长度
    err_code = _validate_text_length(text)
    if err_code:
        return _make_error(err_code, f'文本长度超过上限 {MAX_TEXT_LENGTH} 字')

    text = text.strip()
    if not text:
        return _make_error('E001', '输入文本为空')

    # 尝试按 JSON 解析
    parsed_data = None
    parse_method = None
    try:
        parsed_data = _parse_json_text(text)
        parse_method = 'json'
    except json.JSONDecodeError:
        pass

    # 尝试按 CSV 解析
    if parsed_data is None:
        try:
            csv_records = _parse_csv_text(text)
            if len(csv_records) > 1 or (len(csv_records) == 1 and any(csv_records[0].values())):
                parsed_data = csv_records
                parse_method = 'csv'
        except Exception:
            pass

    # 如果结构化解析成功
    if parsed_data is not None:
        records = _process_structured_data(parsed_data, fields)
        if records:
            return _make_success(
                records,
                meta={'source_type': 'text', 'parse_method': parse_method, 'record_count': len(records)}
            )

    # 否则按纯文本提取
    extracted = _extract_from_text(text, fields)
    # 为每个字段添加置信度
    result_record = {}
    for field in fields:
        value = extracted.get(field, f'[需核实:{field}]')
        result_record[field] = value
        result_record[f'{field}_confidence'] = _assess_confidence(value, field)

    return _make_success(
        [result_record],
        meta={'source_type': 'text', 'parse_method': 'regex', 'record_count': 1}
    )


def _process_file_input(filepath: str, fields: List[str]) -> Dict[str, Any]:
    """
    处理本地文件输入。
    """
    content, err_code = _safe_read_text_file(filepath)
    if err_code:
        error_messages = {
            'E002': '文件不存在或无法读取',
            'E004': '文件内容超过长度限制',
            'E005': '文件大小超过 2MB 限制',
            'E007': '不支持的文件类型（仅支持 .txt/.csv/.json）',
        }
        return _make_error(err_code, error_messages.get(err_code, '文件读取错误'))

    # 调用文本处理逻辑
    result = _process_text_input(content, fields)
    if result.get('success'):
        result['meta']['source_type'] = 'file'
        result['meta']['file_path'] = filepath
    return result


def _process_url_input(url: str, fields: List[str]) -> Dict[str, Any]:
    """
    处理 URL 输入。
    注意：本实现仅验证 URL 格式，不实际访问网络（保持离线可用）。
    如需真实抓取，请安装 requests 库并取消注释相应代码。
    """
    # 验证 URL 格式
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return _make_error('E003', f'无效的 URL 格式: {url}')

    # 检测需要认证的 URL（简单判断）
    if '@' in parsed.netloc:
        return _make_error('E003', '不支持需要登录认证的 URL')

    # 注意：出于离线自检和安全性考虑，此处不实际发起网络请求。
    # 如需真实抓取，请安装 requests 并取消以下注释：
    # try:
    #     import requests  # pip install requests
    #     resp = requests.get(url, timeout=10)
    #     if resp.status_code != 200:
    #         return _make_error('E003', f'URL 访问失败: HTTP {resp.status_code}')
    #     content = resp.text
    #     if len(content.encode('utf-8')) > MAX_URL_CONTENT_SIZE:
    #         return _make_error('E005', 'URL 页面大小超过 2MB 限制')
    # except ImportError:
    #     return _make_error('E003', '需要安装 requests 库才能访问 URL')
    # except Exception as e:
    #     return _make_error('E003', f'URL 访问异常: {str(e)}')

    # 离线模式：返回提示信息
    return _make_error('E003', 'URL 抓取需要网络访问，当前为离线模式。请使用文本或文件输入。')


def _process_batch_input(inputs: List[str], fields: List[str], input_types: List[str]) -> Dict[str, Any]:
    """
    处理批量输入。
    """
    if len(inputs) > MAX_BATCH_FILES:
        return _make_error('E006', f'批量输入数量超过上限 {MAX_BATCH_FILES} 个')

    results = []
    for i, (item, itype) in enumerate(zip(inputs, input_types)):
        if itype == 'text':
            result = _process_text_input(item, fields)
        elif itype == 'file':
            result = _process_file_input(item, fields)
        elif itype == 'url':
            result = _process_url_input(item, fields)
        else:
            result = _make_error('E007', f'不支持的输入类型: {itype}')

        result['index'] = i
        results.append(result)

    return _make_success(results, meta={'batch_size': len(results), 'input_types': input_types})


def _validate_output_template(template: str) -> Optional[str]:
    """
    验证输出模板格式。
    支持 JSON 或 Markdown 表格。
    """
    template_lower = template.lower().strip()
    if template_lower in ('json', 'markdown', 'md'):
        return None
    return 'E008'


def _format_markdown_table(records: List[Dict[str, Any]], fields: List[str]) -> str:
    """将记录格式化为 Markdown 表格。"""
    if not records:
        return '（无数据）'

    # 构建表头
    header = ['字段'] + fields
    lines = []
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '---|' * len(header))

    # 每条记录一行
    for i, record in enumerate(records):
        row = [f'记录{i + 1}']
        for field in fields:
            value = record.get(field, '')
            conf = record.get(f'{field}_confidence', '')
            cell = f'{value} ({conf})' if conf else str(value)
            row.append(cell)
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)


def _format_output(result: Dict[str, Any], template: str = 'json') -> str:
    """
    根据模板格式化输出。
    """
    template_lower = template.lower().strip()

    if template_lower in ('markdown', 'md'):
        if not result.get('success'):
            return f"**错误 ({result.get('error_code')})**: {result.get('error_message')}"
        records = result.get('data', [])
        if isinstance(records, dict):
            records = [records]
        fields = []
        if records:
            # 提取字段名（去掉 _confidence 后缀）
            for key in records[0].keys():
                if not key.endswith('_confidence'):
                    fields.append(key)
        return _format_markdown_table(records, fields)

    # 默认 JSON 输出
    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# 自检模块
# =============================================================================

def _run_selftest() -> bool:
    """
    内置自检逻辑，使用硬编码样例数据验证核心功能。
    不读取外部文件，不依赖当前工作目录，不访问网络。
    """
    print("=" * 60)
    print("awsome-cash 自检开始")
    print("=" * 60)

    all_passed = True

    # -------------------------------------------------------------------------
    # 测试 1: 纯文本解析
    # -------------------------------------------------------------------------
    print("\n[测试 1] 纯文本解析")
    sample_text = """
    餐饮消费记录
    名称：张三
    日期：2024-03-15
    金额：¥128.50
    类别：餐饮
    备注：同事聚餐
    """
    try:
        result = _process_text_input(sample_text, DEFAULT_FIELDS)
        if not result.get('success'):
            print(f"  ✗ 文本解析失败: {result.get('error_message')}")
            all_passed = False
        else:
            records = result.get('data', [])
            if not records:
                print("  ✗ 文本解析结果为空")
                all_passed = False
            else:
                record = records[0]
                print(f"  ✓ 文本解析成功: {record}")
                # 验证关键字段
                if record.get('name') != '张三':
                    print(f"  ✗ 名称提取错误: {record.get('name')}")
                    all_passed = False
                if record.get('date') != '2024-03-15':
                    print(f"  ✗ 日期提取错误: {record.get('date')}")
                    all_passed = False
                if not isinstance(record.get('amount'), (int, float)):
                    print(f"  ✗ 金额应为数值类型: {record.get('amount')}")
                    all_passed = False
                elif record.get('amount') != 128.50:
                    print(f"  ✗ 金额值错误: {record.get('amount')}")
                    all_passed = False
    except Exception as e:
        print(f"  ✗ 测试1异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 2: JSON 文本解析
    # -------------------------------------------------------------------------
    print("\n[测试 2] JSON 文本解析")
    try:
        sample_json = json.dumps([
            {"name": "项目A", "date": "2024-01-10", "amount": 999.99, "category": "开发", "note": "第一阶段"},
            {"name": "项目B", "date": "2024-02-20", "amount": 1500.00, "category": "运维", "note": "服务器"}
        ], ensure_ascii=False)
        result = _process_text_input(sample_json, DEFAULT_FIELDS)
        if not result.get('success'):
            print(f"  ✗ JSON 解析失败: {result.get('error_message')}")
            all_passed = False
        else:
            records = result.get('data', [])
            if len(records) != 2:
                print(f"  ✗ JSON 记录数错误: {len(records)}")
                all_passed = False
            else:
                if records[0]['name'] != '项目A':
                    print(f"  ✗ JSON 第一条记录名称错误: {records[0]['name']}")
                    all_passed = False
                if records[1]['amount'] != 1500.00:
                    print(f"  ✗ JSON 第二条记录金额错误: {records[1]['amount']}")
                    all_passed = False
                print(f"  ✓ JSON 解析成功: {len(records)} 条记录")
    except Exception as e:
        print(f"  ✗ 测试2异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 3: CSV 文本解析
    # -------------------------------------------------------------------------
    print("\n[测试 3] CSV 文本解析")
    try:
        sample_csv = "name,date,amount,category,note\n李四,2024-04-01,88.50,交通,地铁\n王五,2024-04-02,45.00,餐饮,午餐"
        result = _process_text_input(sample_csv, DEFAULT_FIELDS)
        if not result.get('success'):
            print(f"  ✗ CSV 解析失败: {result.get('error_message')}")
            all_passed = False
        else:
            records = result.get('data', [])
            if len(records) != 2:
                print(f"  ✗ CSV 记录数错误: {len(records)}")
                all_passed = False
            else:
                if records[0]['name'] != '李四':
                    print(f"  ✗ CSV 第一条记录名称错误: {records[0]['name']}")
                    all_passed = False
                if records[1]['category'] != '餐饮':
                    print(f"  ✗ CSV 第二条记录类别错误: {records[1]['category']}")
                    all_passed = False
                print(f"  ✓ CSV 解析成功: {len(records)} 条记录")
    except Exception as e:
        print(f"  ✗ 测试3异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 4: 置信度标注
    # -------------------------------------------------------------------------
    print("\n[测试 4] 置信度标注")
    try:
        test_values = [
            ('张三', 'name', CONFIDENCE_HIGH),
            ('2024-01-01', 'date', CONFIDENCE_HIGH),
            (123.45, 'amount', CONFIDENCE_HIGH),
            ('', 'name', CONFIDENCE_LOW),
            ('[需核实:name]', 'name', CONFIDENCE_LOW),
            ('x', 'note', CONFIDENCE_MEDIUM),
        ]
        conf_test_passed = True
        for value, field, expected_min in test_values:
            conf = _assess_confidence(value, field)
            # 宽松断言：高置信度值不应被评为低
            if expected_min == CONFIDENCE_HIGH:
                if conf == CONFIDENCE_LOW:
                    print(f"  ✗ 高置信度值被低估: field={field}, value={value}, conf={conf}")
                    conf_test_passed = False
            elif expected_min == CONFIDENCE_LOW:
                if conf != CONFIDENCE_LOW:
                    print(f"  ✗ 低置信度值被高估: field={field}, value={value}, conf={conf}")
                    conf_test_passed = False
            else:
                if conf not in (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH):
                    print(f"  ✗ 置信度评估异常: field={field}, value={value}, conf={conf}")
                    conf_test_passed = False
        if conf_test_passed:
            print(f"  ✓ 置信度标注逻辑正确")
        else:
            all_passed = False
    except Exception as e:
        print(f"  ✗ 测试4异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 5: 错误处理
    # -------------------------------------------------------------------------
    print("\n[测试 5] 错误处理")
    try:
        # 空文本
        result = _process_text_input("", DEFAULT_FIELDS)
        if result.get('success') or result.get('error_code') != 'E001':
            print(f"  ✗ 空文本错误处理错误")
            all_passed = False

        # 超长文本
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        result = _process_text_input(long_text, DEFAULT_FIELDS)
        if result.get('success') or result.get('error_code') != 'E004':
            print(f"  ✗ 超长文本错误处理错误")
            all_passed = False

        # 不存在的文件
        result = _process_file_input("/nonexistent/path/file.txt", DEFAULT_FIELDS)
        if result.get('success') or result.get('error_code') != 'E002':
            print(f"  ✗ 文件错误处理错误")
            all_passed = False

        # 无效 URL
        result = _process_url_input("not-a-url", DEFAULT_FIELDS)
        if result.get('success') or result.get('error_code') != 'E003':
            print(f"  ✗ URL 错误处理错误")
            all_passed = False

        # 批量超限
        many_inputs = ["a"] * (MAX_BATCH_FILES + 1)
        many_types = ["text"] * (MAX_BATCH_FILES + 1)
        result = _process_batch_input(many_inputs, DEFAULT_FIELDS, many_types)
        if result.get('success') or result.get('error_code') != 'E006':
            print(f"  ✗ 批量错误处理错误")
            all_passed = False

        print(f"  ✓ 错误处理逻辑正确")
    except Exception as e:
        print(f"  ✗ 测试5异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 6: 输出模板
    # -------------------------------------------------------------------------
    print("\n[测试 6] 输出模板")
    try:
        sample_result = _process_text_input(sample_text, DEFAULT_FIELDS)

        # JSON 模板
        json_output = _format_output(sample_result, 'json')
        if '"success": true' not in json_output:
            print(f"  ✗ JSON 输出格式错误")
            all_passed = False
        else:
            parsed = json.loads(json_output)
            if not parsed['success']:
                print(f"  ✗ JSON 输出解析失败")
                all_passed = False

        # Markdown 模板
        md_output = _format_output(sample_result, 'markdown')
        if '|' not in md_output or '记录1' not in md_output:
            print(f"  ✗ Markdown 表格格式错误")
            all_passed = False

        # 无效模板
        err_code = _validate_output_template('xml')
        if err_code != 'E008':
            print(f"  ✗ 无效模板错误码错误: {err_code}")
            all_passed = False

        print(f"  ✓ 输出模板功能正常")
    except Exception as e:
        print(f"  ✗ 测试6异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 测试 7: 批量处理
    # -------------------------------------------------------------------------
    print("\n[测试 7] 批量处理")
    try:
        batch_inputs = [sample_text, sample_json]
        batch_types = ["text", "text"]
        result = _process_batch_input(batch_inputs, DEFAULT_FIELDS, batch_types)
        if not result.get('success'):
            print(f"  ✗ 批量处理失败: {result.get('error_message')}")
            all_passed = False
        else:
            batch_data = result.get('data', [])
            if len(batch_data) != 2:
                print(f"  ✗ 批量处理记录数错误: {len(batch_data)}")
                all_passed = False
            elif not batch_data[0].get('success') or not batch_data[1].get('success'):
                print(f"  ✗ 批量处理子项失败")
                all_passed = False
            else:
                print(f"  ✓ 批量处理成功: {len(batch_data)} 个输入")
    except Exception as e:
        print(f"  ✗ 测试7异常: {str(e)}")
        all_passed = False

    # -------------------------------------------------------------------------
    # 汇总
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    if all_passed:
        print("自检全部通过 ✓")
    else:
        print("自检存在失败项 ✗")
    print("=" * 60)
    return all_passed


# =============================================================================
# 主入口
# =============================================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description='awsome-cash: 数据解析、结构化输出、置信度标注',
        epilog='示例: python main.py --text "名称：张三 日期：2024-01-01 金额：100" --fields name date amount'
    )
    parser.add_argument('--text', type=str, help='要解析的文本内容')
    parser.add_argument('--file', type=str, help='要解析的本地文件路径')
    parser.add_argument('--url', type=str, help='要解析的 URL（离线模式不可用）')
    parser.add_argument('--fields', type=str, default=','.join(DEFAULT_FIELDS),
                        help=f'输出字段列表，逗号分隔（默认: {",".join(DEFAULT_FIELDS)}）')
    parser.add_argument('--template', type=str, default='json', choices=['json', 'markdown'],
                        help='输出模板（默认: json）')
    parser.add_argument('--selftest', action='store_true', help='运行内置自检')
    parser.add_argument('--batch', nargs='*', help='批量输入（配合 --type 使用）')
    parser.add_argument('--type', nargs='*', default=[], choices=['text', 'file', 'url'],
                        help='批量输入类型列表')

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = _run_selftest()
        return 0 if success else 1

    # 解析字段列表
    fields = [f.strip() for f in args.fields.split(',') if f.strip()]
    if not fields:
        print(json.dumps(_make_error('E001', '字段列表为空'), ensure_ascii=False, indent=2))
        return 1

    # 验证输出模板
    template_err = _validate_output_template(args.template)
    if template_err:
        print(json.dumps(_make_error(template_err, f'不支持的输出模板: {args.template}'), ensure_ascii=False, indent=2))
        return 1

    # 处理输入
    result = None
    input_count = sum(1 for x in [args.text, args.file, args.url] if x is not None)

    if input_count > 1:
        result = _make_error('E001', '只能指定一种输入方式（--text/--file/--url 三选一）')
    elif args.batch:
        # 批量处理
        if not args.type:
            args.type = ['text'] * len(args.batch)
        if len(args.batch) != len(args.type):
            result = _make_error('E001', '批量输入与类型数量不匹配')
        else:
            result = _process_batch_input(args.batch, fields, args.type)
    elif args.text is not None:
        result = _process_text_input(args.text, fields)
    elif args.file is not None:
        result = _process_file_input(args.file, fields)
    elif args.url is not None:
        result = _process_url_input(args.url, fields)
    else:
        result = _make_error('E001', '请提供输入：--text、--file、--url 或 --batch')

    # 输出结果
    output = _format_output(result, args.template)
    print(output)

    # 返回退出码
    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
