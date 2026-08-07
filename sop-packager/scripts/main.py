#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sop-packager — 流程封装与标准作业程序生成

将重复性操作整理为标准作业程序（SOP），供 AI 自动执行。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例:
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --input "打开浏览器，输入网址，点击登录" --output sop.md
"""

import argparse
import json
import os
import re
import sys
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 错误码定义（E001-E010）
ERR_SUCCESS = 0
ERR_INVALID_INPUT = "E001"      # 输入为空或格式错误
ERR_FILE_NOT_FOUND = "E002"     # 输入文件不存在
ERR_OUTPUT_DIR = "E003"         # 输出目录不可写
ERR_PARSE_FAILED = "E004"       # 内容解析失败
ERR_TEMPLATE_MISSING = "E005"   # 模板缺失
ERR_BATCH_EMPTY = "E006"        # 批量处理列表为空
ERR_URL_INVALID = "E007"        # URL 格式不合法
ERR_CONFIDENCE_LOW = "E008"     # 置信度过低，无法生成
ERR_INTERNAL = "E009"           # 内部未知错误
ERR_SELFTEST_FAIL = "E010"      # 自检失败


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class SOPStep:
    """SOP 单个步骤"""
    order: int                    # 步骤序号
    action: str                   # 动作描述
    condition: str = ""           # 触发条件（可选）
    owner: str = ""               # 责任人（可选）
    time_limit: str = ""          # 时限要求（可选）
    confidence: float = 0.0       # 置信度 0.0 ~ 1.0
    notes: str = ""               # 备注（可选）


@dataclass
class SOPDocument:
    """SOP 文档对象"""
    title: str
    steps: List[SOPStep] = field(default_factory=list)
    created_at: str = ""
    source: str = ""              # 来源描述（文件/URL/文本）
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式 SOP 文档"""
        lines = [
            f"# {self.title}",
            "",
            f"> 生成时间: {self.created_at}",
            f"> 来源: {self.source}",
            "",
            "## 步骤清单",
            "",
        ]
        for step in self.steps:
            lines.append(f"### 步骤 {step.order}")
            lines.append(f"- **动作**: {step.action}")
            if step.condition:
                lines.append(f"- **条件**: {step.condition}")
            if step.owner:
                lines.append(f"- **责任人**: {step.owner}")
            if step.time_limit:
                lines.append(f"- **时限**: {step.time_limit}")
            lines.append(f"- **置信度**: {step.confidence:.0%}")
            if step.notes:
                lines.append(f"- **备注**: {step.notes}")
            lines.append("")
        return "\n".join(lines)


# ============================================================
# 核心解析引擎
# ============================================================

class SOPParser:
    """
    将非结构化文本解析为结构化 SOP 步骤。
    采用规则 + 关键词匹配方式，不依赖外部 NLP 库。
    """

    # 常见动作关键词（中英文）
    ACTION_KEYWORDS = [
        "打开", "关闭", "点击", "输入", "选择", "提交", "保存", "删除",
        "复制", "粘贴", "上传", "下载", "启动", "停止", "重启", "等待",
        "检查", "确认", "验证", "设置", "配置", "创建", "修改", "更新",
        "发送", "接收", "打印", "扫描", "连接", "断开", "登录", "退出",
        "完成", "执行", "处理", "记录", "填写", "获取", "读取", "写入",
        "open", "close", "click", "input", "select", "submit", "save",
        "delete", "copy", "paste", "upload", "download", "start", "stop",
        "restart", "wait", "check", "confirm", "verify", "set", "create",
        "modify", "update", "send", "receive", "print", "scan", "connect",
        "disconnect", "login", "logout", "complete", "execute", "process"
    ]

    # 条件关键词
    CONDITION_KEYWORDS = ["如果", "若", "当", "如", "if", "when", "case"]

    # 责任人关键词
    OWNER_KEYWORDS = ["负责人", "责任人", "由", "owner", "assignee"]

    # 时限关键词
    TIME_KEYWORDS = ["秒", "分钟", "小时", "天", "周", "月", "秒内", "分钟内",
                     "小时内", "天内", "周内", "月内", "立即", "及时",
                     "second", "minute", "hour", "day", "week", "month",
                     "immediately", "asap"]

    # 时间量词模式
    TIME_PATTERN = re.compile(
        r'(\d+\s*(?:秒|分钟|小时|天|周|月)|立即|及时|'
        r'\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?))'
    )

    # 责任人模式
    OWNER_PATTERN = re.compile(
        r'(?:负责人|责任人)[：:]\s*([^\s，。；,;]+)|'
        r'由\s*([^\s，。；,;]+)'
    )

    def __init__(self) -> None:
        self._step_patterns = self._compile_patterns()

    def _compile_patterns(self) -> List[re.Pattern]:
        """编译步骤分割正则"""
        # 按常见分隔符分割步骤：换行、句号、分号、数字序号等
        patterns = [
            re.compile(r"[\n\r;；]+"),                       # 换行/分号
            re.compile(r"(?<=[。！？!?])\s*"),                # 中文句号后
            re.compile(r"\d+[\.\)、）]\s*"),                  # 数字序号
        ]
        return patterns

    def parse(self, text: str, source: str = "文本输入") -> SOPDocument:
        """
        解析文本为 SOP 文档

        参数:
            text: 非结构化流程描述文本
            source: 来源描述

        返回:
            SOPDocument 对象

        异常:
            ValueError: 当输入为空或无法解析时
        """
        if not text or not text.strip():
            raise ValueError(f"{ERR_INVALID_INPUT}: 输入文本为空")

        # 1. 分割原始步骤
        raw_steps = self._split_steps(text.strip())
        if not raw_steps:
            raise ValueError(f"{ERR_PARSE_FAILED}: 无法从文本中提取步骤")

        # 2. 逐条解析为 SOPStep
        steps: List[SOPStep] = []
        for idx, raw in enumerate(raw_steps, start=1):
            step = self._parse_single_step(raw, idx)
            if step is not None:
                steps.append(step)

        if not steps:
            raise ValueError(f"{ERR_PARSE_FAILED}: 未能识别有效的操作步骤")

        # 3. 生成文档
        doc = SOPDocument(
            title=self._generate_title(text),
            steps=steps,
            created_at=datetime.now().isoformat(timespec="seconds"),
            source=source,
            metadata={
                "total_steps": len(steps),
                "avg_confidence": round(
                    sum(s.confidence for s in steps) / len(steps), 2
                ),
                "parser_version": "1.1.0",
            },
        )
        return doc

    def _split_steps(self, text: str) -> List[str]:
        """将文本分割为候选步骤列表"""
        # 先按换行分割
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # 如果行数足够多，直接以行为单位
        if len(lines) >= 2:
            return lines

        # 否则尝试按标点/序号分割
        candidates: List[str] = []
        for pattern in self._step_patterns:
            parts = pattern.split(text)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                candidates = parts
                break

        return candidates if candidates else [text]

    def _parse_single_step(self, text: str, order: int) -> Optional[SOPStep]:
        """解析单个步骤文本"""
        # 清理序号前缀（如 "1."、"1、" 等）
        clean = re.sub(r"^\s*\d+[\.\)、）]\s*", "", text).strip()
        if not clean:
            return None

        # 提取条件（从文本开头找）
        condition = ""
        remaining_text = clean
        for kw in self.CONDITION_KEYWORDS:
            pos = remaining_text.find(kw)
            if pos >= 0:
                # 条件是从关键词到第一个动作关键词之前
                # 找到条件结束位置（通常是第一个动作关键词）
                condition_end = len(remaining_text)
                for action_kw in self.ACTION_KEYWORDS:
                    action_pos = remaining_text.find(action_kw, pos + len(kw))
                    if action_pos > 0 and action_pos < condition_end:
                        condition_end = action_pos
                condition = remaining_text[pos:condition_end].strip()
                remaining_text = remaining_text[:pos] + remaining_text[condition_end:]
                break

        # 提取责任人
        owner = ""
        owner_match = self.OWNER_PATTERN.search(remaining_text)
        if owner_match:
            owner = owner_match.group(1) or owner_match.group(2) or ""
            # 移除责任人部分
            remaining_text = remaining_text[:owner_match.start()] + \
                           remaining_text[owner_match.end():]

        # 提取时限
        time_limit = ""
        time_match = self.TIME_PATTERN.search(remaining_text)
        if time_match:
            time_limit = time_match.group(0)
            # 移除时限部分
            remaining_text = remaining_text[:time_match.start()] + \
                           remaining_text[time_match.end():]

        # 提取动作（取第一个动作关键词所在位置）
        action_start = -1
        action_keyword = ""
        lower_remaining = remaining_text.lower()

        for kw in self.ACTION_KEYWORDS:
            pos = lower_remaining.find(kw.lower())
            if pos >= 0 and (action_start < 0 or pos < action_start):
                action_start = pos
                action_keyword = kw

        if action_start < 0:
            # 没有识别到动作关键词，但文本存在，仍然生成步骤（低置信度）
            step = SOPStep(
                order=order,
                action=remaining_text.strip() or clean,
                condition=condition,
                owner=owner,
                time_limit=time_limit,
                confidence=0.3,
                notes="未识别到明确动作关键词，请人工确认",
            )
            return step

        # 动作描述
        action_text = remaining_text[action_start:].strip(" ，,;；。")
        if not action_text:
            action_text = action_keyword

        # 计算置信度
        confidence = self._calc_confidence(
            clean, bool(condition), bool(owner), bool(time_limit)
        )

        step = SOPStep(
            order=order,
            action=action_text,
            condition=condition,
            owner=owner,
            time_limit=time_limit,
            confidence=confidence,
        )
        return step

    def _calc_confidence(self, text: str, has_cond: bool, has_owner: bool, has_time: bool) -> float:
        """计算步骤置信度"""
        base = 0.6
        if len(text) >= 5:
            base += 0.1
        if has_cond:
            base += 0.1
        if has_owner:
            base += 0.05
        if has_time:
            base += 0.05
        # 动作关键词命中数越多越可靠
        hits = sum(1 for kw in self.ACTION_KEYWORDS if kw.lower() in text.lower())
        if hits >= 2:
            base += 0.1
        return min(base, 0.98)

    def _generate_title(self, text: str) -> str:
        """从文本生成标题"""
        # 取第一行或前20个字符
        first_line = text.strip().splitlines()[0] if text.strip().splitlines() else text
        title = first_line[:30].strip()
        if len(title) < 3:
            title = "标准作业程序"
        return title


# ============================================================
# 批量处理与输出
# ============================================================

class SOPPackager:
    """SOP 打包器：支持单文本、文件、批量处理"""

    def __init__(self, parser: Optional[SOPParser] = None) -> None:
        self.parser = parser or SOPParser()

    def process_text(self, text: str, source: str = "文本输入") -> SOPDocument:
        """处理单段文本"""
        return self.parser.parse(text, source)

    def process_file(self, file_path: str) -> SOPDocument:
        """处理文件"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在 {file_path}")
        if not path.is_file():
            raise ValueError(f"{ERR_INVALID_INPUT}: 路径不是文件 {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 尝试其他编码
            content = path.read_text(encoding="gbk", errors="replace")

        return self.parser.parse(content, source=str(path))

    def process_batch(self, file_paths: List[str]) -> List[SOPDocument]:
        """批量处理多个文件"""
        if not file_paths:
            raise ValueError(f"{ERR_BATCH_EMPTY}: 批量处理列表为空")

        results = []
        errors = []
        for fp in file_paths:
            try:
                results.append(self.process_file(fp))
            except Exception as e:
                errors.append({"file": fp, "error": str(e)})

        if not results:
            raise RuntimeError(f"{ERR_BATCH_EMPTY}: 所有文件处理失败，错误: {errors}")

        return results

    def export_doc(self, doc: SOPDocument, output_path: str, fmt: str = "md") -> str:
        """导出文档到文件"""
        path = Path(output_path)
        # 确保父目录存在
        if path.parent and not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise PermissionError(f"{ERR_OUTPUT_DIR}: 无法创建目录 {path.parent}: {e}")

        # 检查目录可写
        if path.parent and not os.access(path.parent, os.W_OK):
            raise PermissionError(f"{ERR_OUTPUT_DIR}: 目录不可写 {path.parent}")

        # 根据格式输出
        if fmt == "json":
            content = doc.to_json()
        elif fmt == "md":
            content = doc.to_markdown()
        else:
            # 默认输出 markdown
            content = doc.to_markdown()

        try:
            path.write_text(content, encoding="utf-8")
        except OSError as e:
            raise PermissionError(f"{ERR_OUTPUT_DIR}: 写入失败 {path}: {e}")

        return str(path)


# ============================================================
# 自检模块（--selftest）
# ============================================================

def run_selftest() -> int:
    """
    内置硬编码样例数据，离线自检核心逻辑。
    不读取外部文件，不依赖当前工作目录，不访问网络。

    返回:
        0 表示成功，非 0 表示失败
    """
    print("=" * 60)
    print("SOP Packager 自检开始")
    print("=" * 60)

    # 硬编码测试数据（不依赖外部资源）
    test_text = """
    1. 打开浏览器，输入公司内部系统网址
    2. 使用员工账号登录系统，如果忘记密码请联系管理员
    3. 在首页点击"新建申请"按钮
    4. 填写申请表单，负责人：张三
    5. 上传附件材料，需要在 30 分钟内完成
    6. 点击提交按钮，等待系统确认
    7. 将申请编号记录到台账中
    """

    try:
        # 测试 1: 基本解析
        print("\n[测试 1] 文本解析")
        parser = SOPParser()
        doc = parser.parse(test_text, source="自检样例")

        # 宽松断言：步骤数在合理范围
        assert len(doc.steps) >= 3, f"步骤数过少: {len(doc.steps)}"
        assert len(doc.steps) <= 10, f"步骤数过多: {len(doc.steps)}"
        print(f"  ✓ 步骤数 {len(doc.steps)} 在合理范围 [3, 10]")

        # 宽松断言：置信度在合理范围
        for step in doc.steps:
            assert 0.0 <= step.confidence <= 1.0, f"置信度越界: {step.confidence}"
        avg_conf = sum(s.confidence for s in doc.steps) / len(doc.steps)
        assert avg_conf > 0.3, f"平均置信度过低: {avg_conf}"
        print(f"  ✓ 平均置信度 {avg_conf:.2f} > 0.3")

        # 测试 2: 标题生成
        print("\n[测试 2] 标题生成")
        assert doc.title and len(doc.title) >= 2, f"标题异常: {doc.title}"
        print(f"  ✓ 标题: {doc.title}")

        # 测试 3: JSON 序列化
        print("\n[测试 3] JSON 序列化")
        json_str = doc.to_json()
        assert json_str and len(json_str) > 50, "JSON 输出过短"
        # 验证 JSON 可反序列化
        json_data = json.loads(json_str)
        assert "steps" in json_data, "JSON 缺少 steps 字段"
        assert len(json_data["steps"]) == len(doc.steps), "JSON steps 数量不一致"
        print(f"  ✓ JSON 序列化成功，长度 {len(json_str)} 字符")

        # 测试 4: Markdown 输出
        print("\n[测试 4] Markdown 输出")
        md_str = doc.to_markdown()
        assert md_str.startswith("# "), "Markdown 缺少标题"
        assert "## 步骤清单" in md_str, "Markdown 缺少步骤清单"
        assert "步骤 1" in md_str, "Markdown 缺少步骤 1"
        print(f"  ✓ Markdown 生成成功，长度 {len(md_str)} 字符")

        # 测试 5: 特殊输入处理
        print("\n[测试 5] 空输入处理")
        try:
            parser.parse("   ")
            raise AssertionError("空输入未抛出异常")
        except ValueError as e:
            assert str(e).startswith("E001"), f"错误码不正确: {e}"
            print("  ✓ 空输入正确抛出 E001")

        # 测试 6: 批量处理
        print("\n[测试 6] 批量处理空列表")
        packager = SOPPackager()
        try:
            packager.process_batch([])
            raise AssertionError("空批量列表未抛出异常")
        except ValueError as e:
            assert str(e).startswith("E006"), f"错误码不正确: {e}"
            print("  ✓ 空批量列表正确抛出 E006")

        # 测试 7: 动作关键词识别
        print("\n[测试 7] 动作关键词识别")
        simple_text = "打开应用，输入账号密码，点击登录"
        simple_doc = parser.parse(simple_text, source="自检")
        assert len(simple_doc.steps) >= 1, "未能识别任何步骤"
        # 至少有一个步骤包含动作
        actions = [s.action for s in simple_doc.steps]
        assert any("打开" in a or "输入" in a or "点击" in a for a in actions), \
            f"未识别到动作关键词: {actions}"
        print(f"  ✓ 识别到动作: {actions[:3]}")

        # 测试 8: 错误文件处理
        print("\n[测试 8] 不存在的文件")
        try:
            packager.process_file("/nonexistent/path/file.txt")
            raise AssertionError("不存在的文件未抛出异常")
        except FileNotFoundError as e:
            assert str(e).startswith("E002"), f"错误码不正确: {e}"
            print("  ✓ 不存在文件正确抛出 E002")

        # 测试 9: 导出功能（使用临时目录）
        print("\n[测试 9] 导出功能")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test_sop.md"
            result = packager.export_doc(doc, str(out_path), fmt="md")
            assert Path(result).exists(), "导出文件不存在"
            content = Path(result).read_text(encoding="utf-8")
            assert "步骤" in content, "导出内容缺少步骤"
            print(f"  ✓ 导出成功: {result}")

        # 测试 10: 条件/责任人/时限提取
        print("\n[测试 10] 要素提取")
        rich_text = "如果网络正常，由张三在30分钟内完成数据备份"
        rich_doc = parser.parse(rich_text, source="自检")
        # 至少有一个步骤
        assert len(rich_doc.steps) >= 1, "未能解析富文本"
        step = rich_doc.steps[0]
        # 宽松断言：条件、责任人、时限至少有一个被提取
        has_element = bool(step.condition) or bool(step.owner) or bool(step.time_limit)
        assert has_element, "未能提取任何条件/责任人/时限"
        print(f"  ✓ 条件='{step.condition}' 责任人='{step.owner}' 时限='{step.time_limit}'")
        
        # 额外验证：确保三个要素都被提取
        assert step.condition, f"条件未提取: {rich_text}"
        assert step.owner, f"责任人未提取: {rich_text}"
        assert step.time_limit, f"时限未提取: {rich_text}"
        print(f"  ✓ 条件、责任人、时限均已提取")

        print("\n" + "=" * 60)
        print("全部自检通过 ✅")
        print("=" * 60)
        return ERR_SUCCESS

    except AssertionError as e:
        print(f"\n❌ 自检失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 自检异常: {e}")
        return 1


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SOP Packager — 流程封装与标准作业程序生成",
        epilog="示例: python scripts/main.py --input '打开浏览器，登录系统' --output sop.md",
    )

    # 输入参数
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本（直接传入流程描述）",
    )
    input_group.add_argument(
        "--file", "-f",
        type=str,
        help="输入文件路径（读取文件内容）",
    )
    input_group.add_argument(
        "--batch", "-b",
        type=str,
        nargs="+",
        help="批量处理多个文件路径",
    )

    # 输出参数
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="sop_output.md",
        help="输出文件路径（默认: sop_output.md）",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["md", "json"],
        default="md",
        help="输出格式（默认: md）",
    )

    # 自检参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件，不访问网络）",
    )

    # 版本
    parser.add_argument(
        "--version",
        action="version",
        version="sop-packager 1.1.0",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    try:
        packager = SOPPackager()

        # 根据输入类型处理
        if args.batch:
            docs = packager.process_batch(args.batch)
            # 批量处理时，输出到各自目录
            results = []
            for idx, doc in enumerate(docs):
                if len(docs) == 1:
                    out = args.output
                else:
                    suffix = Path(args.output).suffix
                    stem = Path(args.output).stem
                    out = f"{stem}_{idx + 1}{suffix}"
                result = packager.export_doc(doc, out, fmt=args.format)
                results.append(result)
            print(f"批量处理完成，共 {len(results)} 个文件:")
            for r in results:
                print(f"  - {r}")

        elif args.file:
            doc = packager.process_file(args.file)
            result = packager.export_doc(doc, args.output, fmt=args.format)
            print(f"文件处理完成: {result}")
            print(f"共 {len(doc.steps)} 个步骤，平均置信度 {doc.metadata['avg_confidence']:.2f}")

        elif args.input:
            doc = packager.process_text(args.input, source="命令行输入")
            result = packager.export_doc(doc, args.output, fmt=args.format)
            print(f"文本处理完成: {result}")
            print(f"共 {len(doc.steps)} 个步骤，平均置信度 {doc.metadata['avg_confidence']:.2f}")

        else:
            parser.print_help()
            return ERR_INVALID_INPUT

        return ERR_SUCCESS

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误 ({ERR_INTERNAL}): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
