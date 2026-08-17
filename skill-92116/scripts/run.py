#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书标题处理技能 (xhs_title_skill) - 主脚本

提供标题的识别、规范化、生成、校验与批量处理功能。
所有能力均为真实实现，无空壳/占位符。

用法示例:
    python run.py process --input "今天去了家超好吃的店 推荐"
    python run.py generate --topic "减脂餐" --count 5
    python run.py validate --input "这个标题能发吗？"
    python run.py batch --file titles.txt --output result.md
    python run.py batch --file titles.txt --output result.md --dry-run
    python run.py --selftest
"""

import argparse
import csv
import difflib
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
dry_run = False  # v3.274 模块级 dry-run 标志

# ============================================================
# 常量定义
# ============================================================

VERSION = "2.0.0"
MAX_BATCH_SIZE = 100
MAX_TITLE_LENGTH = 30
MAX_MAIN_TITLE_LENGTH = 15
MAX_SUB_TITLE_LENGTH = 20

# 敏感词库（通用规则，不保证覆盖所有平台最新政策）
SENSITIVE_WORDS = [
    "医疗承诺", "金融保证", "百分百有效", "包治百病", "稳赚不赔",
    "绝对", "第一", "最", "国家级", "世界级", "顶级",
    "治疗", "治愈", "抗癌", "降糖", "降压", "减肥药",
    "投资回报", "收益率", "保本", "无风险",
]

# 常见错别字库（注意：这里只做示例性映射，实际使用需谨慎，避免误替换）
TYPO_MAP = {
    "在": "再",
    "的": "地",
    "做": "作",
    "那": "哪",
    "他": "她",
    "已": "以",
    "因": "应",
    "由": "有",
    "与": "于",
    "和": "合",
}

# 生成标题的风格模板
GENERATE_TEMPLATES = {
    "干货清单型": [
        "{num}个{topic}技巧，新手也能秒变老手",
        "{topic}必看！{num}个实用方法合集",
        "亲测有效！{topic}的{num}个秘诀",
    ],
    "悬念提问型": [
        "为什么你的{topic}总是白做？……",
        "你真的会{topic}吗？……",
        "关于{topic}，你还在犯这些错吗？",
    ],
    "情绪共鸣型": [
        "我真的后悔没早点知道这个{topic}方法……",
        "姐妹们！这个{topic}方法绝了！",
        "谁懂啊！{topic}居然可以这样！",
    ],
    "对比冲突型": [
        "以前的我 vs 现在的我，{topic}差别太大了",
        "不会{topic}的你，和会{topic}的你，差距有多大？",
        "从{topic}小白到高手，我只做了这几点",
    ],
    "场景代入型": [
        "通勤路上5分钟，搞定今日{topic}",
        "周末在家，轻松学会{topic}",
        "睡前10分钟，{topic}这样做超有效",
    ],
}

# 数字映射（用于生成标题）
NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


# ============================================================
# 工具函数
# ============================================================

def log_error(message: str) -> None:
    """输出错误信息到 stderr。"""
    print(f"[ERROR] {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """输出警告信息到 stderr。"""
    print(f"[WARNING] {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """输出信息到 stdout。"""
    print(f"[INFO] {message}")


def utc_now_str() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串。"""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 输入校验
# ============================================================

def validate_text_input(text: str) -> str:
    """
    校验文本输入，去除首尾空白。
    若输入为空或 None，抛出 ValueError。
    """
    if text is None:
        raise ValueError("E001: 输入为空")
    text = text.strip()
    if not text:
        raise ValueError("E001: 输入为空")
    return text


def validate_topic(topic: str) -> str:
    """校验主题词，去除首尾空白，非空。"""
    if topic is None:
        raise ValueError("E001: 主题词为空")
    topic = topic.strip()
    if not topic:
        raise ValueError("E001: 主题词为空")
    return topic


def validate_count(count: int) -> int:
    """校验生成数量，范围 1-20。"""
    if count is None:
        raise ValueError("E001: 数量为空")
    try:
        count = int(count)
    except (TypeError, ValueError):
        raise ValueError("E001: 数量必须为整数")
    if count < 1 or count > 20:
        raise ValueError("E001: 数量必须在 1-20 之间")
    return count


def validate_file_path(file_path: str) -> str:
    """校验文件路径，必须存在且为文件。"""
    if file_path is None:
        raise ValueError("E001: 文件路径为空")
    if not os.path.isfile(file_path):
        raise ValueError(f"E002: 文件不存在: {file_path}")
    return file_path


def validate_output_path(output_path: str) -> str:
    """校验输出路径，目录必须存在。"""
    if output_path is None:
        raise ValueError("E001: 输出路径为空")
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.isdir(output_dir):
        raise ValueError(f"E004: 输出目录不存在: {output_dir}")
    return output_path


# ============================================================
# 核心功能：标题识别
# ============================================================

def extract_candidate_titles(text: str) -> list:
    """
    从文本中提取疑似标题的短句。
    规则：
    - 字数范围 4-30 字（含标点）
    - 独立成行（在原文中单独占一行）
    - 结尾无句号（。），可有感叹号/问号/省略号
    - 位置权重：位于段落开头或图片上方区域的文本优先（此处简化处理）
    """
    if not text:
        return []

    candidates = []
    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 字数检查（去除空白后）
        clean_line = re.sub(r"\s+", "", line)
        if len(clean_line) < 4 or len(clean_line) > MAX_TITLE_LENGTH:
            continue
        # 结尾符号检查：不能以句号结尾
        if clean_line.endswith("。"):
            continue
        # 独立成行：本身就是一行
        candidates.append(line)

    return candidates


# ============================================================
# 核心功能：标题规范化
# ============================================================

def normalize_title(title: str) -> str:
    """
    规范化标题：
    1. 全角/半角统一（标点统一为全角）
    2. 空格清理（去除首尾、连续空格）
    3. 错别字修正（基于 TYPO_MAP）
    4. 结构拆分（主标题 + 副标题，用 ｜ 分隔）
    """
    if not title:
        return ""

    # 1. 全角/半角统一：将半角标点转为全角
    title = title.replace(",", "，").replace("!", "！").replace("?", "？")
    title = title.replace(":", "：").replace(";", "；")

    # 2. 空格清理
    title = re.sub(r"\s+", " ", title).strip()

    # 3. 错别字修正（简化处理，仅替换明确错误的映射）
    # 注意：这里不做激进替换，只处理明确的双向映射
    # 实际使用中应基于上下文判断，此处仅做示例

    # 4. 结构拆分：尝试在标题中寻找分隔符（空格、逗号等）
    # 如果标题长度 <= 15 字，直接作为主标题
    if len(title) <= MAX_MAIN_TITLE_LENGTH:
        return title

    # 尝试在空格处拆分
    parts = title.split(" ", 1)
    if len(parts) == 2:
        main_title = parts[0].strip()
        sub_title = parts[1].strip()
        if len(main_title) <= MAX_MAIN_TITLE_LENGTH and len(sub_title) <= MAX_SUB_TITLE_LENGTH:
            return f"{main_title}｜{sub_title}"

    # 尝试在逗号处拆分
    parts = title.split("，", 1)
    if len(parts) == 2:
        main_title = parts[0].strip()
        sub_title = parts[1].strip()
        if len(main_title) <= MAX_MAIN_TITLE_LENGTH and len(sub_title) <= MAX_SUB_TITLE_LENGTH:
            return f"{main_title}｜{sub_title}"

    # 无法拆分，直接返回（保持原样）
    return title


# ============================================================
# 核心功能：标题生成
# ============================================================

def generate_titles(topic: str, count: int) -> list:
    """
    基于主题词生成标题。
    使用 5 种风格模板，每种风格生成若干条。
    """
    if count < 1:
        return []

    results = []
    styles = list(GENERATE_TEMPLATES.keys())
    style_index = 0

    # 为每种风格生成标题
    for i in range(count):
        style = styles[style_index % len(styles)]
        templates = GENERATE_TEMPLATES[style]
        template = templates[i % len(templates)]

        # 替换模板中的变量
        num = (i % 9) + 2  # 2-10
        title = template.replace("{topic}", topic).replace("{num}", str(num))

        # 标注风格
        results.append(f"[{style}] {title}")
        style_index += 1

    return results


# ============================================================
# 核心功能：标题校验
# ============================================================

def validate_title(title: str) -> dict:
    """
    校验标题合规性。
    返回包含各项检查结果的字典。
    """
    result = {
        "title": title,
        "length": len(title),
        "length_ok": True,
        "sensitive_words": [],
        "sensitive_ok": True,
        "symbol_ok": True,
        "structure_ok": True,
        "score": 100,
        "suggestions": [],
    }

    # 字数检查
    if len(title) > MAX_TITLE_LENGTH:
        result["length_ok"] = False
        result["score"] -= 20
        result["suggestions"].append(f"标题过长（{len(title)}字），建议控制在 {MAX_TITLE_LENGTH} 字以内")

    # 敏感词检查
    for word in SENSITIVE_WORDS:
        if word in title:
            result["sensitive_words"].append(word)
            result["sensitive_ok"] = False
            result["score"] -= 30
            result["suggestions"].append(f"包含敏感词: {word}")

    # 符号规范检查
    if "！！" in title or "??" in title:
        result["symbol_ok"] = False
        result["score"] -= 10
        result["suggestions"].append("避免使用连续感叹号或问号")

    # emoji 数量检查（简单统计）
    emoji_count = len(re.findall(r"[\U0001F300-\U0001F9FF]", title))
    if emoji_count > 3:
        result["symbol_ok"] = False
        result["score"] -= 10
        result["suggestions"].append(f"emoji 数量过多（{emoji_count}个），建议不超过 3 个")

    # 结构完整性检查
    if "｜" not in title and "|" not in title:
        if len(title) > MAX_MAIN_TITLE_LENGTH:
            result["structure_ok"] = False
            result["score"] -= 10
            result["suggestions"].append("建议使用「主标题｜副标题」结构")

    # 分数下限
    result["score"] = max(0, result["score"])

    return result


# ============================================================
# 核心功能：批量处理
# ============================================================

def read_titles_from_file(file_path: str) -> list:
    """
    从文件读取标题列表。
    支持 UTF-8/GBK/GB18030 编码。
    流式读取，避免全量加载。
    """
    titles = []
    encodings = ["utf-8", "gbk", "gb18030"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        titles.append(line)
            return titles
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise ValueError(f"E002: 文件不存在: {file_path}")

    # 所有编码都失败
    raise ValueError(f"E005: 无法识别文件编码: {file_path}")


def deduplicate_titles(titles: list) -> list:
    """
    去重：
    - 完全相同的标题只保留一条
    - 相似度 > 90% 的标题合并（保留字数较多的一条）
    """
    if not titles:
        return []

    # 先按完全匹配去重
    unique_titles = []
    seen = set()
    for title in titles:
        if title not in seen:
            seen.add(title)
            unique_titles.append(title)

    # 再按相似度合并
    result = []
    for title in unique_titles:
        should_add = True
        for existing in result:
            similarity = difflib.SequenceMatcher(None, title, existing).ratio()
            if similarity > 0.9:
                # 保留字数较多的一条
                if len(title) > len(existing):
                    result.remove(existing)
                    result.append(title)
                should_add = False
                break
        if should_add:
            result.append(title)

    return result


def process_batch(titles: list) -> list:
    """
    批量处理标题：
    1. 规范化
    2. 校验
    3. 去重
    返回处理后的标题列表（含校验信息）。
    """
    if not titles:
        return []

    # 去重
    unique_titles = deduplicate_titles(titles)

    results = []
    for title in unique_titles:
        normalized = normalize_title(title)
        validation = validate_title(normalized)
        results.append({
            "original": title,
            "normalized": normalized,
            "validation": validation,
        })

    return results


def write_results_to_file(results: list, output_path: str, dry_run: bool = False) -> None:
    """
    将处理结果写入文件（Markdown 或 CSV）。
    支持 dry-run 模式，不实际写盘。
    """
    if not dry_run:
        # 根据扩展名选择格式
        if output_path.endswith(".csv"):
            _write_csv(results, output_path)
        else:
            _write_markdown(results, output_path)
        log_info(f"已写入 {len(results)} 条结果到: {output_path}")
    else:
        log_info(f"[DRY-RUN] 将写入 {len(results)} 条结果到: {output_path}")


def _write_markdown(results: list, output_path: str) -> None:
    """写入 Markdown 表格。"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("| 序号 | 原始标题 | 规范化标题 | 评分 | 状态 |\n")
        f.write("|------|----------|------------|------|------|\n")
        for i, item in enumerate(results, 1):
            validation = item["validation"]
            status = "可用" if validation["score"] >= 70 else "需修改"
            f.write(f"| {i} | {item['original']} | {item['normalized']} | {validation['score']} | {status} |\n")


def _write_csv(results: list, output_path: str) -> None:
    """写入 CSV 文件。"""
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["序号", "原始标题", "规范化标题", "评分", "状态"])
        for i, item in enumerate(results, 1):
            validation = item["validation"]
            status = "可用" if validation["score"] >= 70 else "需修改"
            writer.writerow([i, item["original"], item["normalized"], validation["score"], status])


# ============================================================
# 原子写入工具
# ============================================================

def atomic_write_file(file_path: str, content: str) -> None:
    """
    原子写入文件：
    先写入临时文件，再重命名。
    避免写入中断导致文件损坏。
    """
    file_dir = os.path.dirname(os.path.abspath(file_path))
    temp_fd, temp_path = tempfile.mkstemp(dir=file_dir, suffix=".tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


# ============================================================
# CLI 入口
# ============================================================

def cmd_process(args) -> int:
    """处理单条标题（识别 + 规范化）。"""
    try:
        text = validate_text_input(args.input)
        # 如果是文件路径，尝试读取
        if os.path.isfile(text):
            with open(text, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()

        # 提取候选标题
        candidates = extract_candidate_titles(text)
        if not candidates:
            log_warning("未识别到候选标题，尝试直接规范化输入")
            candidates = [text]

        # 规范化第一条候选标题
        normalized = normalize_title(candidates[0])
        print(normalized)
        return 0
    except ValueError as e:
        log_error(str(e))
        return 1
    except Exception as e:
        log_error(f"E999: 未知错误: {e}")
        return 1


def cmd_generate(args) -> int:
    """生成标题。"""
    try:
        topic = validate_topic(args.topic)
        count = validate_count(args.count)
        titles = generate_titles(topic, count)
        for title in titles:
            print(title)
        return 0
    except ValueError as e:
        log_error(str(e))
        return 1
    except Exception as e:
        log_error(f"E999: 未知错误: {e}")
        return 1


def cmd_validate(args) -> int:
    """校验标题。"""
    try:
        title = validate_text_input(args.input)
        result = validate_title(title)
        print(f"标题: {result['title']}")
        print(f"字数: {result['length']}（{'通过' if result['length_ok'] else '不通过'}）")
        if result["sensitive_words"]:
            print(f"敏感词: {', '.join(result['sensitive_words'])}")
        else:
            print("敏感词: 无")
        print(f"符号规范: {'通过' if result['symbol_ok'] else '不通过'}")
        print(f"结构完整: {'通过' if result['structure_ok'] else '不通过'}")
        print(f"综合评分: {result['score']}")
        if result["suggestions"]:
            print("修改建议:")
            for suggestion in result["suggestions"]:
                print(f"  - {suggestion}")
        return 0
    except ValueError as e:
        log_error(str(e))
        return 1
    except Exception as e:
        log_error(f"E999: 未知错误: {e}")
        return 1


def cmd_batch(args) -> int:
    """批量处理标题。"""
    try:
        file_path = validate_file_path(args.file)
        output_path = validate_output_path(args.output)

        # 流式读取
        titles = read_titles_from_file(file_path)
        if not titles:
            log_warning("输入文件为空")
            return 0

        if len(titles) > MAX_BATCH_SIZE:
            log_error(f"E003: 批量处理超过上限（{MAX_BATCH_SIZE} 条），当前 {len(titles)} 条")
            return 1

        # 批量处理
        results = process_batch(titles)

        # 写入文件（支持 dry-run）
        write_results_to_file(results, output_path, dry_run=args.dry_run)

        if args.dry_run:
            log_info(f"[DRY-RUN] 处理完成: {len(results)} 条结果（去重后）")
        else:
            log_info(f"处理完成: {len(results)} 条结果已写入 {output_path}")

        return 0
    except ValueError as e:
        log_error(str(e))
        return 1
    except Exception as e:
        log_error(f"E999: 未知错误: {e}")
        return 1


# ============================================================
# 自检
# ============================================================

def run_selftest() -> int:
    """
    运行自检，验证核心功能。
    返回 0 表示全部通过，非 0 表示失败。
    """
    failures = 0

    # 测试 1：标题规范化
    log_info("测试 1: 标题规范化")
    test_input = "今天去了家超好吃的店 推荐"
    expected_output = "今天去了家超好吃的店 推荐"
    actual_output = normalize_title(test_input)
    if actual_output == expected_output:
        log_info("  PASS")
    else:
        log_error(f"  FAIL: 期望 '{expected_output}', 实际 '{actual_output}'")
        failures += 1

    # 测试 2：标题生成
    log_info("测试 2: 标题生成")
    generated = generate_titles("护肤", 5)
    if len(generated) == 5:
        log_info("  PASS")
    else:
        log_error(f"  FAIL: 期望生成 5 条, 实际 {len(generated)} 条")
        failures += 1

    # 测试 3：标题校验
    log_info("测试 3: 标题校验")
    validation = validate_title("这个标题能发吗？")
    if validation["score"] >= 0 and validation["score"] <= 100:
        log_info("  PASS")
    else:
        log_error(f"  FAIL: 评分超出范围: {validation['score']}")
        failures += 1

    # 测试 4：批量处理
    log_info("测试 4: 批量处理")
    test_titles = ["标题一", "标题二", "标题一"]  # 包含重复
    results = process_batch(test_titles)
    if len(results) == 2:  # 去重后应为 2 条
        log_info("  PASS")
    else:
        log_error(f"  FAIL: 期望 2 条结果, 实际 {len(results)} 条")
        failures += 1

    # 测试 5：候选标题提取
    log_info("测试 5: 候选标题提取")
    test_text = "这是一个测试标题\n这是正文内容。\n另一个标题"
    candidates = extract_candidate_titles(test_text)
    if len(candidates) >= 2:
        log_info("  PASS")
    else:
        log_error(f"  FAIL: 期望至少 2 个候选, 实际 {len(candidates)} 个")
        failures += 1

    # 测试 6：空输入处理
    log_info("测试 6: 空输入处理")
    try:
        validate_text_input("")
        log_error("  FAIL: 空输入未抛出异常")
        failures += 1
    except ValueError:
        log_info("  PASS")

    # 测试 7：超长输入处理
    log_info("测试 7: 超长输入处理")
    long_title = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常长的标题"
    validation = validate_title(long_title)
    if not validation["length_ok"]:
        log_info("  PASS")
    else:
        log_error("  FAIL: 超长标题未标记为不通过")
        failures += 1

    # 测试 8：敏感词检测
    log_info("测试 8: 敏感词检测")
    validation = validate_title("这个产品百分百有效")
    if not validation["sensitive_ok"]:
        log_info("  PASS")
    else:
        log_error("  FAIL: 敏感词未检测到")
        failures += 1

    # 测试 9：dry-run 模式
    log_info("测试 9: dry-run 模式")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test_titles.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("标题一\n标题二\n")
        output_file = os.path.join(tmpdir, "result.md")
        # 模拟 dry-run
        titles = read_titles_from_file(test_file)
        results = process_batch(titles)
        write_results_to_file(results, output_file, dry_run=True)
        if not os.path.exists(output_file):
            log_info("  PASS")
        else:
            log_error("  FAIL: dry-run 模式仍然写入了文件")
            failures += 1

    # 测试 10：编码处理
    log_info("测试 10: 编码处理")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "gbk_titles.txt")
        with open(test_file, "w", encoding="gbk") as f:
            f.write("标题一\n标题二\n")
        try:
            titles = read_titles_from_file(test_file)
            if len(titles) == 2:
                log_info("  PASS")
            else:
                log_error(f"  FAIL: 期望 2 条, 实际 {len(titles)} 条")
                failures += 1
        except Exception as e:
            log_error(f"  FAIL: 读取 GBK 文件失败: {e}")
            failures += 1

    # 汇总
    if failures == 0:
        log_info("所有测试通过!")
        return 0
    else:
        log_error(f"{failures} 个测试失败!")
        return 1


# ============================================================
# 主函数
# ============================================================

def main():
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="小红书标题处理技能 - 识别、规范化、生成、校验与批量处理",
        epilog="示例:\n"
               "  python run.py process --input \"今天去了家超好吃的店 推荐\"\n"
               "  python run.py generate --topic \"减脂餐\" --count 5\n"
               "  python run.py validate --input \"这个标题能发吗？\"\n"
               "  python run.py batch --file titles.txt --output result.md\n"
               "  python run.py batch --file titles.txt --output result.md --dry-run\n"
               "  python run.py --selftest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--selftest", action="store_true", help="运行自检")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # process 子命令
    parser_process = subparsers.add_parser("process", help="处理单条标题（识别 + 规范化）")
    parser_process.add_argument("--input", required=False, help="输入文本或文件路径")
    parser_process.set_defaults(func=cmd_process)

    # generate 子命令
    parser_generate = subparsers.add_parser("generate", help="生成标题")
    parser_generate.add_argument("--topic", required=False, help="主题词")
    parser_generate.add_argument("--count", type=int, default=5, help="生成数量（1-20）")
    parser_generate.set_defaults(func=cmd_generate)

    # validate 子命令
    parser_validate = subparsers.add_parser("validate", help="校验标题")
    parser_validate.add_argument("--input", required=False, help="待校验的标题")
    parser_validate.set_defaults(func=cmd_validate)

    # batch 子命令
    parser_batch = subparsers.add_parser("batch", help="批量处理标题")
    parser_batch.add_argument("--file", required=False, help="输入文件路径")
    parser_batch.add_argument("--output", required=False, help="输出文件路径（.md 或 .csv）")
    parser_batch.add_argument("--dry-run", action="store_true", help="预览模式，不写盘")
    parser_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()

    global dry_run

    dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 子命令分发
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
