#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题工坊 Pro - 场景化标题生成与校验工具

一站式标题生成、整理与校验工具，支持批量处理、多风格生成、敏感词检测与可读性分析。

用法示例:
    python run.py generate --topic "AI医疗" --count 5
    python run.py validate --title "2024年AI医疗的5个关键突破"
    python run.py organize --input titles.txt --dry-run
    python run.py --selftest
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

VERSION = "2.0.0"
DEFAULT_COUNT = 5
MAX_COUNT = 50
MIN_TITLE_LEN = 8
MAX_TITLE_LEN = 30
SIMILARITY_THRESHOLD = 0.8
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # 指数退避基数（秒）

# 敏感词列表（绝对化用语）
SENSITIVE_WORDS = [
    "最", "第一", "100%", "百分之百", "绝对", "唯一", "顶级",
    "国家级", "世界级", "全球级", "史无前例", "空前绝后",
    "极致", "完美", "万能", "无敌", "永久", "终身",
]

# 风格模板
STYLE_TEMPLATES = {
    "悬念型": [
        "揭秘{topic}背后的真相",
        "{topic}竟然还能这样？",
        "没想到{topic}还有这一面",
        "{topic}的秘密，今天终于揭晓",
        "关于{topic}，你可能不知道的5件事",
    ],
    "数据型": [
        "2024年{topic}的5个关键数据",
        "{topic}市场规模突破千亿，你了解多少？",
        "90%的人不知道：{topic}的真相",
        "{topic}增长300%背后的逻辑",
        "3组数据看懂{topic}趋势",
    ],
    "对比型": [
        "{topic} vs 传统方案：谁更胜一筹？",
        "对比了10家{topic}服务商，我推荐这家",
        "{topic}新旧模式大比拼",
        "左看右看，{topic}还是这个好",
        "{topic}的A面与B面",
    ],
    "提问型": [
        "你真的了解{topic}吗？",
        "{topic}的未来在哪里？",
        "为什么{topic}如此重要？",
        "如何正确看待{topic}？",
        "{topic}，是机遇还是挑战？",
    ],
    "清单型": [
        "{topic}全景盘点：从入门到精通",
        "{topic}必备清单：这10样不能少",
        "{topic}完整指南：一篇就够了",
        "收藏！{topic}最全整理",
        "{topic}资源合集：建议保存",
    ],
}

# 风格关键词映射（用于识别用户输入中的风格意图）
STYLE_KEYWORDS = {
    "悬念型": ["悬念", "揭秘", "竟然", "没想到", "秘密"],
    "数据型": ["数据", "数字", "百分比", "增长", "规模"],
    "对比型": ["对比", "vs", "比较", "比拼", "哪个"],
    "提问型": ["提问", "问", "为什么", "如何", "吗"],
    "清单型": ["清单", "盘点", "合集", "指南", "大全"],
}


# ============================================================
# 工具函数
# ============================================================

def get_utc_now() -> str:
    """获取 UTC 当前时间字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def safe_print(message: str, verbose: bool = False) -> None:
    """安全打印，处理编码问题"""
    try:
        print(message)
    except UnicodeEncodeError:
        # 降级输出：替换无法编码的字符
        print(message.encode("ascii", "replace").decode("ascii"))


def print_error(message: str) -> None:
    """打印错误信息到 stderr"""
    try:
        print(f"[ERROR] {message}", file=sys.stderr)
    except UnicodeEncodeError:
        print(f"[ERROR] {message.encode('ascii', 'replace').decode('ascii')}", file=sys.stderr)


def print_warning(message: str) -> None:
    """打印警告信息到 stderr"""
    try:
        print(f"[WARNING] {message}", file=sys.stderr)
    except UnicodeEncodeError:
        print(f"[WARNING] {message.encode('ascii', 'replace').decode('ascii')}", file=sys.stderr)


def read_file_with_encoding(filepath: str) -> List[str]:
    """
    读取文件，自动检测编码（UTF-8 → GBK → GB18030 三级 fallback）
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件内容列表（每行一个元素）
        
    Raises:
        FileNotFoundError: 文件不存在
        UnicodeDecodeError: 所有编码都无法解码
    """
    file_path = Path(filepath)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    encodings = ["utf-8", "gbk", "gb18030"]
    last_error = None
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, errors="strict") as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError as e:
            last_error = e
            continue
    
    # 所有编码都失败，使用 errors="replace" 降级
    print_warning(f"文件编码无法识别，使用 replace 模式读取: {filepath}")
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return [line.strip() for line in f if line.strip()]


def atomic_write(filepath: str, content: str) -> None:
    """
    原子化写入文件（先写临时文件，再重命名）
    
    Args:
        filepath: 目标文件路径
        content: 要写入的内容
    """
    file_path = Path(filepath)
    temp_fd, temp_path = tempfile.mkstemp(dir=str(file_path.parent) if file_path.parent.exists() else ".")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, filepath)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度（基于字符集合的 Jaccard 相似度）
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        相似度分数（0.0 - 1.0）
    """
    if not text1 or not text2:
        return 0.0
    
    set1 = set(text1)
    set2 = set(text2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def detect_style_from_text(text: str) -> Optional[str]:
    """
    从文本中检测风格意图
    
    Args:
        text: 用户输入文本
        
    Returns:
        检测到的风格名，未检测到返回 None
    """
    text_lower = text.lower()
    for style, keywords in STYLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return style
    return None


# ============================================================
# 标题生成模块
# ============================================================

def generate_titles(topic: str, count: int = DEFAULT_COUNT, style: Optional[str] = None,
                    audience: Optional[str] = None) -> List[Dict[str, str]]:
    """
    生成标题
    
    Args:
        topic: 主题描述
        count: 生成数量（1-50）
        style: 风格（悬念型/数据型/对比型/提问型/清单型），None 表示混合
        audience: 目标受众
        
    Returns:
        标题列表，每个元素为 {"title": str, "style": str}
        
    Raises:
        ValueError: 参数无效
    """
    # 输入校验
    if not topic or not topic.strip():
        raise ValueError("主题不能为空")
    
    if count < 1 or count > MAX_COUNT:
        raise ValueError(f"生成数量必须在 1-{MAX_COUNT} 之间")
    
    valid_styles = list(STYLE_TEMPLATES.keys())
    if style and style not in valid_styles:
        raise ValueError(f"无效的风格: {style}，可选: {', '.join(valid_styles)}")
    
    # 确定使用的风格列表
    if style:
        styles_to_use = [style]
    else:
        styles_to_use = valid_styles
    
    # 生成标题
    titles = []
    topic_clean = topic.strip()
    
    # 受众修饰
    audience_prefix = ""
    if audience and audience.strip():
        audience_prefix = f"【{audience.strip()}】"
    
    for i in range(count):
        style_idx = i % len(styles_to_use)
        current_style = styles_to_use[style_idx]
        templates = STYLE_TEMPLATES[current_style]
        template = templates[i % len(templates)]
        
        title = template.format(topic=topic_clean)
        
        # 添加受众前缀（仅第一条）
        if i == 0 and audience_prefix:
            title = f"{audience_prefix}{title}"
        
        titles.append({"title": title, "style": current_style})
    
    return titles


# ============================================================
# 标题校验模块
# ============================================================

def validate_title(title: str, existing_titles: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """
    校验单个标题
    
    Args:
        title: 要校验的标题
        existing_titles: 已有标题列表（用于重复率检查）
        
    Returns:
        校验结果字典
    """
    results = {}
    
    # 1. 长度检查
    title_len = len(title)
    if title_len < MIN_TITLE_LEN:
        results["length"] = {
            "status": "❌",
            "message": f"标题长度 {title_len} 字，建议控制在 {MIN_TITLE_LEN}-{MAX_TITLE_LEN} 字",
        }
    elif title_len > MAX_TITLE_LEN:
        results["length"] = {
            "status": "⚠️",
            "message": f"标题长度 {title_len} 字，超过建议上限 {MAX_TITLE_LEN} 字",
        }
    else:
        results["length"] = {
            "status": "✅",
            "message": f"长度：{title_len}字（符合 {MIN_TITLE_LEN}-{MAX_TITLE_LEN} 字标准）",
        }
    
    # 2. 敏感词检查
    sensitive_found = []
    for word in SENSITIVE_WORDS:
        if word in title:
            sensitive_found.append(word)
    
    if sensitive_found:
        results["sensitive"] = {
            "status": "❌",
            "message": f"标题含敏感词: {', '.join(sensitive_found)}，建议替换",
        }
    else:
        results["sensitive"] = {
            "status": "✅",
            "message": "敏感词：未检出",
        }
    
    # 3. 可读性检查（检测英文缩写）
    abbreviations = re.findall(r'\b[A-Z]{2,}\b', title)
    if abbreviations:
        results["readability"] = {
            "status": "⚠️",
            "message": f"含缩写: {', '.join(abbreviations)}，建议首次出现时写全称",
        }
    else:
        results["readability"] = {
            "status": "✅",
            "message": "可读性：未发现缩写问题",
        }
    
    # 4. 重复率检查
    if existing_titles:
        max_similarity = 0.0
        most_similar = ""
        for existing in existing_titles:
            if existing == title:
                continue
            sim = calculate_similarity(title, existing)
            if sim > max_similarity:
                max_similarity = sim
                most_similar = existing
        
        if max_similarity >= SIMILARITY_THRESHOLD:
            results["duplicate"] = {
                "status": "❌",
                "message": f"与已有标题'{most_similar}'相似度 {max_similarity:.0%}，建议调整",
            }
        else:
            results["duplicate"] = {
                "status": "✅",
                "message": f"重复率：与已有标题相似度 {max_similarity:.0%}",
            }
    else:
        results["duplicate"] = {
            "status": "✅",
            "message": "重复率：未提供已有标题，跳过检查",
        }
    
    return results


def validate_titles_batch(titles: List[str], existing_titles: Optional[List[str]] = None) -> List[Dict]:
    """
    批量校验标题
    
    Args:
        titles: 标题列表
        existing_titles: 已有标题列表
        
    Returns:
        校验结果列表
    """
    results = []
    for title in titles:
        result = validate_title(title, existing_titles)
        results.append({"title": title, "checks": result})
    return results


# ============================================================
# 标题整理模块
# ============================================================

def organize_titles(titles: List[str]) -> Dict[str, List[Dict[str, str]]]:
    """
    整理标题列表（去重、分类、排序）
    
    Args:
        titles: 原始标题列表
        
    Returns:
        整理后的标题分类字典
    """
    # 1. 去重（保持顺序）
    seen = set()
    unique_titles = []
    duplicates = []
    
    for title in titles:
        title_clean = title.strip()
        if not title_clean:
            continue
        if title_clean in seen:
            duplicates.append(title_clean)
        else:
            seen.add(title_clean)
            unique_titles.append(title_clean)
    
    # 2. 分类和排序
    recommended = []
    needs_optimization = []
    
    for title in unique_titles:
        # 检查长度
        title_len = len(title)
        # 检查敏感词
        has_sensitive = any(word in title for word in SENSITIVE_WORDS)
        
        if MIN_TITLE_LEN <= title_len <= MAX_TITLE_LEN and not has_sensitive:
            recommended.append({
                "title": title,
                "length": title_len,
                "note": "无敏感词",
            })
        else:
            issues = []
            if title_len < MIN_TITLE_LEN or title_len > MAX_TITLE_LEN:
                issues.append(f"长度{title_len}字")
            if has_sensitive:
                issues.append("含敏感词")
            needs_optimization.append({
                "title": title,
                "length": title_len,
                "note": "、".join(issues),
            })
    
    # 按长度排序（推荐优先）
    recommended.sort(key=lambda x: x["length"])
    needs_optimization.sort(key=lambda x: x["length"])
    
    return {
        "recommended": recommended,
        "needs_optimization": needs_optimization,
        "duplicates": duplicates,
    }


# ============================================================
# 输出格式化模块
# ============================================================

def format_generate_output(titles: List[Dict[str, str]], topic: str, count: int,
                           style: Optional[str], audience: Optional[str]) -> str:
    """格式化生成结果输出"""
    lines = []
    style_desc = style if style else "混合风格"
    audience_desc = audience if audience else "通用大众"
    
    lines.append(f"已生成 {count} 条标题（主题：{topic}，风格：{style_desc}，受众：{audience_desc}）")
    lines.append("")
    
    for i, item in enumerate(titles, 1):
        lines.append(f"{i}. {item['title']}（{item['style']}）")
    
    lines.append("")
    lines.append("需要调整风格或数量吗？回复\"换风格\"\"加数量\"或直接使用。")
    
    return "\n".join(lines)


def format_validate_output(results: Dict[str, Dict[str, str]], title: str) -> str:
    """格式化校验结果输出"""
    lines = []
    lines.append("校验结果：")
    
    for check_name, check_result in results.items():
        lines.append(f"{check_result['status']} {check_result['message']}")
    
    # 判断结论
    has_error = any(r["status"] == "❌" for r in results.values())
    has_warning = any(r["status"] == "⚠️" for r in results.values())
    
    lines.append("")
    if has_error:
        lines.append("结论：标题存在必须修改的问题，请调整后重新校验。")
    elif has_warning:
        lines.append("结论：标题基本合格，建议根据提示优化后使用。")
    else:
        lines.append("结论：标题完全合格，可以直接使用。")
    
    return "\n".join(lines)


def format_organize_output(organized: Dict[str, List[Dict[str, str]]], total: int,
                           dry_run: bool = False, output_path: Optional[str] = None) -> str:
    """格式化整理结果输出"""
    lines = []
    
    if dry_run and output_path:
        lines.append(f"[DRY-RUN] 将写入：{output_path}")
    
    dup_count = len(organized["duplicates"])
    lines.append(f"已整理 {total} 条标题，去重 {dup_count} 条，分类如下：")
    lines.append("")
    
    lines.append(f"【推荐优先】（{len(organized['recommended'])}条）")
    for item in organized["recommended"]:
        lines.append(f"- {item['title']}（长度{item['length']}字，{item['note']}）")
    
    lines.append("")
    lines.append(f"【需优化】（{len(organized['needs_optimization'])}条）")
    for item in organized["needs_optimization"]:
        lines.append(f"- {item['title']}（{item['note']}）")
    
    if organized["duplicates"]:
        lines.append("")
        lines.append(f"【已去重】（{dup_count}条）")
        for title in organized["duplicates"]:
            lines.append(f"- {title}（重复）")
    
    return "\n".join(lines)


# ============================================================
# 网络请求模块（带超时和重试）
# ============================================================

def http_request_with_retry(url: str, timeout: int = 5, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """
    带超时和指数退避重试的 HTTP 请求
    
    Args:
        url: 请求 URL
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        
    Returns:
        响应内容，失败返回 None
    """
    import urllib.request
    import urllib.error
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TitleForgePro/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            print_warning(f"网络请求失败（第{attempt + 1}次）: {e}")
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = RETRY_BACKOFF ** attempt
                print_warning(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print_error(f"网络请求连续失败 {max_retries} 次，已放弃")
                return None
        except Exception as e:
            print_error(f"网络请求异常: {e}")
            return None
    
    return None


# ============================================================
# 主程序
# ============================================================

def run_selftest() -> int:
    """
    自检函数：验证核心功能是否正常
    
    Returns:
        0 表示全部通过，非 0 表示有失败
    """
    print("=" * 60)
    print("标题工坊 Pro 自检程序")
    print(f"版本: {VERSION}")
    print(f"时间: {get_utc_now()}")
    print("=" * 60)
    
    failures = 0
    
    # 测试 1: 标题生成
    print("\n[测试 1] 标题生成...")
    try:
        titles = generate_titles("AI医疗", count=5)
        assert len(titles) == 5, f"期望生成 5 条，实际 {len(titles)} 条"
        assert all(t["title"] for t in titles), "存在空标题"
        assert all(t["style"] in STYLE_TEMPLATES for t in titles), "存在无效风格"
        print(f"  ✅ 生成 {len(titles)} 条标题，风格: {[t['style'] for t in titles]}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 2: 指定风格生成
    print("\n[测试 2] 指定风格生成...")
    try:
        titles = generate_titles("远程办公", count=3, style="数据型")
        assert len(titles) == 3, f"期望生成 3 条，实际 {len(titles)} 条"
        assert all(t["style"] == "数据型" for t in titles), "风格不匹配"
        print(f"  ✅ 生成 {len(titles)} 条数据型标题")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 3: 标题校验 - 正常标题
    print("\n[测试 3] 标题校验（正常标题）...")
    try:
        result = validate_title("2024年AI医疗的5个关键突破")
        assert result["length"]["status"] == "✅", f"长度检查失败: {result['length']['message']}"
        assert result["sensitive"]["status"] == "✅", f"敏感词检查失败: {result['sensitive']['message']}"
        print(f"  ✅ 校验通过: {result['length']['message']}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 4: 标题校验 - 含敏感词
    print("\n[测试 4] 标题校验（含敏感词）...")
    try:
        result = validate_title("这是最好的标题")
        assert result["sensitive"]["status"] == "❌", "敏感词检查应该失败"
        print(f"  ✅ 正确检出敏感词: {result['sensitive']['message']}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 5: 标题整理
    print("\n[测试 5] 标题整理...")
    try:
        test_titles = [
            "AI医疗革命",
            "AI医疗革命",  # 重复
            "2024年AI医疗的5个关键突破",
            "这个标题太长了，超过了三十个字的限制需要精简一下内容",
            "最好的AI医疗方案",
        ]
        organized = organize_titles(test_titles)
        assert len(organized["duplicates"]) == 1, f"期望去重 1 条，实际 {len(organized['duplicates'])} 条"
        assert len(organized["recommended"]) >= 1, "推荐列表不应为空"
        assert len(organized["needs_optimization"]) >= 1, "需优化列表不应为空"
        print(f"  ✅ 整理完成: 推荐 {len(organized['recommended'])} 条，需优化 {len(organized['needs_optimization'])} 条，去重 {len(organized['duplicates'])} 条")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 6: 相似度计算
    print("\n[测试 6] 相似度计算...")
    try:
        sim1 = calculate_similarity("AI医疗革命", "AI医疗革命")
        sim2 = calculate_similarity("AI医疗革命", "完全不同的标题")
        assert sim1 == 1.0, f"相同文本相似度应为 1.0，实际 {sim1}"
        assert sim2 < 0.5, f"不同文本相似度应小于 0.5，实际 {sim2}"
        print(f"  ✅ 相似度计算正常: 相同={sim1:.2f}, 不同={sim2:.2f}")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 7: 批量校验
    print("\n[测试 7] 批量校验...")
    try:
        titles = ["AI医疗革命", "2024年AI医疗的5个关键突破"]
        results = validate_titles_batch(titles)
        assert len(results) == 2, f"期望 2 条结果，实际 {len(results)} 条"
        assert all("checks" in r for r in results), "结果缺少 checks 字段"
        print(f"  ✅ 批量校验完成: {len(results)} 条")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 8: 文件读取（编码处理）
    print("\n[测试 8] 文件编码处理...")
    try:
        # 创建临时测试文件
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write("标题一\n标题二\n")
            temp_path = f.name
        
        try:
            lines = read_file_with_encoding(temp_path)
            assert len(lines) == 2, f"期望 2 行，实际 {len(lines)} 行"
            print(f"  ✅ 文件读取正常: {len(lines)} 行")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 9: 原子写入
    print("\n[测试 9] 原子写入...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name
        
        try:
            atomic_write(temp_path, "测试内容")
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            assert content == "测试内容", "写入内容不匹配"
            print(f"  ✅ 原子写入正常")
        finally:
            os.unlink(temp_path)
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 测试 10: 输入校验
    print("\n[测试 10] 输入校验...")
    try:
        try:
            generate_titles("", count=5)
            failures += 1
            print("  ❌ 空主题应该抛出异常")
        except ValueError:
            print("  ✅ 空主题正确抛出异常")
        
        try:
            generate_titles("测试", count=100)
            failures += 1
            print("  ❌ 超量应该抛出异常")
        except ValueError:
            print("  ✅ 超量正确抛出异常")
    except Exception as e:
        failures += 1
        print(f"  ❌ 失败: {e}")
    
    # 汇总
    print("\n" + "=" * 60)
    if failures == 0:
        print("✅ 全部测试通过！")
        return 0
    else:
        print(f"❌ {failures} 项测试失败！")
        return 1


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="标题工坊 Pro - 场景化标题生成与校验工具",
        epilog="示例:\n"
               "  python run.py generate --topic \"AI医疗\" --count 5\n"
               "  python run.py validate --title \"2024年AI医疗的5个关键突破\"\n"
               "  python run.py organize --input titles.txt --dry-run\n"
               "  python run.py --selftest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--selftest", action="store_true", help="运行自检程序")
    parser.add_argument("--verbose", action="store_true", help="输出详细调试信息")
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # generate 子命令
    gen_parser = subparsers.add_parser("generate", help="生成标题")
    gen_parser.add_argument("--topic", required=False, help="主题描述（必填）")
    gen_parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"生成数量（默认 {DEFAULT_COUNT}，最大 {MAX_COUNT}）")
    gen_parser.add_argument("--style", choices=list(STYLE_TEMPLATES.keys()), help="风格（悬念型/数据型/对比型/提问型/清单型）")
    gen_parser.add_argument("--audience", help="目标受众")
    
    # validate 子命令
    val_parser = subparsers.add_parser("validate", help="校验标题")
    val_parser.add_argument("--title", help="要校验的标题")
    val_parser.add_argument("--input", help="包含多个标题的文件路径")
    val_parser.add_argument("--existing", help="已有标题列表文件（用于重复率检查）")
    
    # organize 子命令
    org_parser = subparsers.add_parser("organize", help="整理标题")
    org_parser.add_argument("--input", required=False, help="输入文件路径（每行一个标题）")
    org_parser.add_argument("--output", help="输出文件路径（默认: cleaned_<输入文件名>）")
    org_parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    org_parser.add_argument("--force", action="store_true", help="强制执行（与 --dry-run 配合使用）")
    
    args = parser.parse_args()
    
    global dry_run
    
    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    
    # 自检模式
    if args.selftest:
        return run_selftest()
    
    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0
    
    # ========================================
    # generate 命令
    # ========================================
    if args.command == "generate":
        try:
            # 检测风格意图（从 topic 中）
            detected_style = detect_style_from_text(args.topic)
            if detected_style and not args.style:
                if args.verbose:
                    print_warning(f"从主题中检测到风格意图: {detected_style}")
                args.style = detected_style
            
            titles = generate_titles(
                topic=args.topic,
                count=args.count,
                style=args.style,
                audience=args.audience,
            )
            
            output = format_generate_output(
                titles=titles,
                topic=args.topic,
                count=len(titles),
                style=args.style,
                audience=args.audience,
            )
            safe_print(output)
            return 0
            
        except ValueError as e:
            print_error(f"参数错误: {e}")
            return 2
        except Exception as e:
            print_error(f"生成失败: {e}")
            return 1
    
    # ========================================
    # validate 命令
    # ========================================
    if args.command == "validate":
        try:
            # 读取已有标题（用于重复率检查）
            existing_titles = None
            if args.existing:
                try:
                    existing_titles = read_file_with_encoding(args.existing)
                    if args.verbose:
                        print_warning(f"已加载 {len(existing_titles)} 条已有标题用于重复率检查")
                except Exception as e:
                    print_warning(f"无法读取已有标题文件: {e}，跳过重复率检查")
            
            # 单标题校验
            if args.title:
                results = validate_title(args.title, existing_titles)
                output = format_validate_output(results, args.title)
                safe_print(output)
                return 0
            
            # 批量校验
            if args.input:
                try:
                    titles = read_file_with_encoding(args.input)
                except Exception as e:
                    print_error(f"读取文件失败: {e}")
                    return 1
                
                if not titles:
                    print_warning("文件中没有标题")
                    return 0
                
                results = validate_titles_batch(titles, existing_titles)
                
                # 输出结果
                lines = [f"批量校验 {len(results)} 条标题：", ""]
                pass_count = 0
                warn_count = 0
                fail_count = 0
                
                for item in results:
                    title = item["title"]
                    checks = item["checks"]
                    has_error = any(c["status"] == "❌" for c in checks.values())
                    has_warning = any(c["status"] == "⚠️" for c in checks.values())
                    
                    if has_error:
                        status = "❌"
                        fail_count += 1
                    elif has_warning:
                        status = "⚠️"
                        warn_count += 1
                    else:
                        status = "✅"
                        pass_count += 1
                    
                    lines.append(f"{status} {title}")
                    if args.verbose:
                        for check_name, check in checks.items():
                            lines.append(f"   {check['status']} {check['message']}")
                
                lines.append("")
                lines.append(f"统计: ✅ {pass_count} 通过, ⚠️ {warn_count} 需优化, ❌ {fail_count} 不通过")
                safe_print("\n".join(lines))
                return 0
            
            print_error("请提供 --title 或 --input 参数")
            return 2
            
        except Exception as e:
            print_error(f"校验失败: {e}")
            return 1
    
    # ========================================
    # organize 命令
    # ========================================
    if args.command == "organize":
        try:
            # 读取输入文件
            try:
                titles = read_file_with_encoding(args.input)
            except Exception as e:
                print_error(f"读取文件失败: {e}")
                return 1
            
            if not titles:
                print_warning("文件中没有标题")
                return 0
            
            # 整理标题
            organized = organize_titles(titles)
            
            # 确定输出路径
            output_path = args.output
            if not output_path:
                input_path = Path(args.input)
                output_path = str(input_path.parent / f"cleaned_{input_path.name}")
            
            # 生成输出内容
            output_content = format_organize_output(
                organized=organized,
                total=len(titles),
                dry_run=args.dry_run,
                output_path=output_path,
            )
            
            # 预览模式：只打印不写入
            if not args.dry_run:
                # 实际写入
                if args.force:
                    # 构建写入内容
                    write_lines = []
                    write_lines.append(f"# 标题整理结果 - {get_utc_now()}")
                    write_lines.append(f"# 输入: {args.input}")
                    write_lines.append("")
                    
                    write_lines.append("## 推荐优先")
                    for item in organized["recommended"]:
                        write_lines.append(item["title"])
                    
                    write_lines.append("")
                    write_lines.append("## 需优化")
                    for item in organized["needs_optimization"]:
                        write_lines.append(item["title"])
                    
                    write_lines.append("")
                    write_lines.append("## 已去重")
                    for title in organized["duplicates"]:
                        write_lines.append(title)
                    
                    try:
                        atomic_write(output_path, "\n".join(write_lines))
                        safe_print(output_content)
                        safe_print("")
                        safe_print(f"✅ 已写入: {output_path}")
                        return 0
                    except Exception as e:
                        print_error(f"写入文件失败: {e}")
                        return 1
                else:
                    # 未指定 --force，提示用户
                    safe_print(output_content)
                    safe_print("")
                    safe_print("提示: 使用 --force 参数实际写入文件。")
                    return 0
            else:
                safe_print(output_content)
                safe_print("")
                safe_print("[DRY-RUN] 未写入任何文件。使用 --force 实际写入。")
                return 0
            
        except Exception as e:
            print_error(f"整理失败: {e}")
            return 1
    
    # 未知命令
    print_error(f"未知命令: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
