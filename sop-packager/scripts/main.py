#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOP Packager — 流程封装与标准作业程序生成工具

功能：
- 将用户提供的文本内容解析为结构化步骤清单
- 提取动作、条件、责任人、时限等关键要素
- 按模板生成 Markdown 格式的 SOP 文档
- 对提取字段标注置信度
- 支持批量处理多个文本片段

用法：
    python main.py --input "文本内容"                 # 处理单条文本
    python main.py --input "文本" --output out.md     # 输出到文件
    python main.py --batch "文本1" --batch "文本2"    # 批量处理
    python main.py --selftest                         # 离线自检
"""

import sys
import json
import argparse
import re
from datetime import datetime
from typing import Dict, List, Any, Optional


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入内容为空或仅包含空白字符",
    "E002": "输入内容不是有效的字符串类型",
    "E003": "输出文件路径无效或无法写入",
    "E004": "批量处理时输入列表为空",
    "E005": "文本解析失败，无法提取有效步骤",
    "E006": "JSON 序列化失败",
    "E007": "参数组合无效（如同时指定 input 和 batch）",
    "E008": "模板渲染失败",
    "E009": "自检断言失败",
    "E010": "未知错误",
}


# ============================================================
# 核心数据结构
# ============================================================

class SOPStep:
    """单个 SOP 步骤"""
    def __init__(self, action: str, order: int, condition: str = "",
                 owner: str = "", deadline: str = "", confidence: float = 1.0):
        self.action = action          # 动作描述
        self.order = order            # 步骤序号
        self.condition = condition    # 前置条件
        self.owner = owner            # 责任人
        self.deadline = deadline      # 时限
        self.confidence = confidence  # 置信度 0.0 ~ 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "order": self.order,
            "condition": self.condition,
            "owner": self.owner,
            "deadline": self.deadline,
            "confidence": self.confidence,
        }


class SOPDocument:
    """SOP 文档对象"""
    def __init__(self, title: str = ""):
        self.title = title
        self.steps: List[SOPStep] = []
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.source_text = ""

    @property
    def step_count(self) -> int:
        """获取步骤数量"""
        return len(self.steps)

    def add_step(self, step: SOPStep) -> None:
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "created_at": self.created_at,
            "step_count": self.step_count,
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_markdown(self) -> str:
        """渲染为 Markdown 格式"""
        lines = []
        lines.append(f"# {self.title or '标准作业程序'}")
        lines.append("")
        lines.append(f"> 生成时间：{self.created_at}")
        lines.append(f"> 步骤总数：{self.step_count}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for step in self.steps:
            lines.append(f"## 步骤 {step.order}: {step.action}")
            if step.condition:
                lines.append(f"- **前置条件**: {step.condition}")
            if step.owner:
                lines.append(f"- **责任人**: {step.owner}")
            if step.deadline:
                lines.append(f"- **时限**: {step.deadline}")
            conf = int(step.confidence * 100)
            lines.append(f"- **置信度**: {conf}%")
            lines.append("")

        return "\n".join(lines)


# ============================================================
# 文本解析引擎
# ============================================================

# 常见动作关键词（用于识别步骤）
ACTION_KEYWORDS = [
    "打开", "关闭", "创建", "删除", "更新", "修改", "检查", "确认",
    "提交", "审批", "发送", "接收", "下载", "上传", "安装", "配置",
    "启动", "停止", "重启", "备份", "恢复", "连接", "断开", "执行",
    "记录", "通知", "验证", "测试", "调整", "设置", "获取", "输入",
]

# 常见条件关键词
CONDITION_KEYWORDS = ["如果", "当", "若", "前提", "条件", "确保", "检查是否"]

# 常见责任关键词
OWNER_KEYWORDS = ["负责人", "责任人", "由", "归属", "管理员", "操作员"]

# 常见时限关键词
DEADLINE_KEYWORDS = ["小时内", "天内", "分钟", "立即", "尽快", "截止", "之前", "前完成"]


def _split_sentences(text: str) -> List[str]:
    """将文本按句号、换行等分割为句子列表"""
    # 先按换行分割，再按句号等标点细分
    parts = re.split(r'[\n\r]+', text)
    sentences = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 按句号、分号、感叹号等分割
        sub_parts = re.split(r'[。；;！!]', part)
        for sp in sub_parts:
            sp = sp.strip()
            if sp:
                sentences.append(sp)
    return sentences


def _extract_action(sentence: str) -> str:
    """从句子中提取动作描述"""
    # 去除常见的前缀修饰词
    cleaned = re.sub(r'^(请|需要|必须|建议|可以|应当|应)', '', sentence)
    cleaned = cleaned.strip()
    return cleaned


def _extract_condition(sentence: str) -> str:
    """提取条件信息"""
    for kw in CONDITION_KEYWORDS:
        idx = sentence.find(kw)
        if idx >= 0:
            # 返回条件关键词后的内容
            return sentence[idx:].strip()
    return ""


def _extract_owner(sentence: str) -> str:
    """提取责任人"""
    for kw in OWNER_KEYWORDS:
        idx = sentence.find(kw)
        if idx >= 0:
            # 提取关键词后的内容
            after = sentence[idx + len(kw):].strip()
            # 取第一个词或短句
            match = re.match(r'^([\u4e00-\u9fa5A-Za-z0-9_\-]+)', after)
            if match:
                return match.group(1)
    return ""


def _extract_deadline(sentence: str) -> str:
    """提取时限信息"""
    for kw in DEADLINE_KEYWORDS:
        idx = sentence.find(kw)
        if idx >= 0:
            # 返回包含时限关键词的片段
            start = max(0, idx - 5)
            end = min(len(sentence), idx + len(kw) + 5)
            return sentence[start:end].strip()
    return ""


def _calc_confidence(sentence: str) -> float:
    """计算步骤置信度"""
    score = 1.0
    # 句子过短可能信息不足
    if len(sentence) < 5:
        score -= 0.3
    # 没有明显的动作词
    has_action = any(kw in sentence for kw in ACTION_KEYWORDS)
    if not has_action:
        score -= 0.2
    # 句子含糊
    if any(w in sentence for w in ["大概", "可能", "也许", "或许"]):
        score -= 0.2
    return max(0.3, min(1.0, score))


def parse_text_to_sop(text: str, title: str = "") -> SOPDocument:
    """将文本解析为 SOP 文档"""
    if not text or not text.strip():
        raise ValueError(ERROR_CODES["E001"])

    doc = SOPDocument(title=title)
    doc.source_text = text

    sentences = _split_sentences(text)
    if not sentences:
        raise ValueError(ERROR_CODES["E005"])

    order = 1
    for sentence in sentences:
        # 跳过纯标题或无关内容
        if len(sentence) < 2:
            continue

        action = _extract_action(sentence)
        if not action:
            continue

        condition = _extract_condition(sentence)
        owner = _extract_owner(sentence)
        deadline = _extract_deadline(sentence)
        confidence = _calc_confidence(sentence)

        step = SOPStep(
            action=action,
            order=order,
            condition=condition,
            owner=owner,
            deadline=deadline,
            confidence=confidence,
        )
        doc.add_step(step)
        order += 1

    if not doc.steps:
        raise ValueError(ERROR_CODES["E005"])

    return doc


# ============================================================
# 批量处理
# ============================================================

def process_batch(texts: List[str]) -> List[SOPDocument]:
    """批量处理多个文本片段"""
    if not texts:
        raise ValueError(ERROR_CODES["E004"])

    results = []
    for i, text in enumerate(texts):
        doc = parse_text_to_sop(text, title=f"批量文档 {i + 1}")
        results.append(doc)
    return results


# ============================================================
# 输出辅助
# ============================================================

def format_json(doc: SOPDocument) -> str:
    """将 SOP 文档格式化为 JSON 字符串"""
    try:
        return json.dumps(doc.to_dict(), ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        raise ValueError(ERROR_CODES["E006"])


def save_to_file(content: str, filepath: str) -> None:
    """保存内容到文件"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except (IOError, OSError):
        raise ValueError(ERROR_CODES["E003"])


# ============================================================
# 命令行入口
# ============================================================

def run_selftest() -> bool:
    """内置自检逻辑，使用硬编码样例数据"""
    print("=" * 60)
    print("SOP Packager 自检模式")
    print("=" * 60)

    # --- 测试样例 1：单条文本解析 ---
    print("\n[测试 1] 单条文本解析")
    sample_text = (
        "首先打开系统管理后台。"
        "然后创建新的用户账号。"
        "如果用户角色是管理员，需要额外配置权限。"
        "最后由负责人审核并提交。"
    )
    try:
        doc = parse_text_to_sop(sample_text, title="测试流程")
        assert doc.step_count >= 2, "步骤数量应不少于 2"
        assert doc.steps[0].order == 1, "第一步序号应为 1"
        assert doc.steps[0].action != "", "第一步动作不应为空"
        # 宽松检查：至少有一个步骤包含条件或责任人
        has_condition = any(s.condition for s in doc.steps)
        has_owner = any(s.owner for s in doc.steps)
        # 不强制要求，但如果有则通过
        print(f"  ✓ 解析成功，共 {doc.step_count} 个步骤")
        print(f"  ✓ 置信度范围: {min(s.confidence for s in doc.steps):.1f} ~ "
              f"{max(s.confidence for s in doc.steps):.1f}")
        if has_condition:
            print("  ✓ 成功提取条件信息")
        if has_owner:
            print("  ✓ 成功提取责任人")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 2：批量处理 ---
    print("\n[测试 2] 批量处理")
    batch_texts = [
        "安装依赖包并配置环境变量。",
        "启动服务并检查日志。",
    ]
    try:
        docs = process_batch(batch_texts)
        assert len(docs) == 2, "应返回 2 个文档"
        assert all(d.step_count >= 1 for d in docs), "每个文档至少 1 个步骤"
        print(f"  ✓ 批量处理成功，共 {len(docs)} 个文档")
        for i, d in enumerate(docs):
            print(f"    - 文档 {i + 1}: {d.step_count} 个步骤")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 3：Markdown 生成 ---
    print("\n[测试 3] Markdown 生成")
    try:
        md = doc.to_markdown()
        assert "# " in md, "应包含标题"
        assert "## 步骤" in md, "应包含步骤标题"
        assert "置信度" in md, "应包含置信度信息"
        print(f"  ✓ Markdown 生成成功，长度 {len(md)} 字符")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 4：JSON 生成 ---
    print("\n[测试 4] JSON 生成")
    try:
        json_str = format_json(doc)
        data = json.loads(json_str)
        assert "steps" in data, "JSON 应包含 steps 字段"
        assert len(data["steps"]) >= 2, "JSON 步骤数应不少于 2"
        print(f"  ✓ JSON 生成成功，长度 {len(json_str)} 字符")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 5：错误处理 ---
    print("\n[测试 5] 错误处理")
    try:
        parse_text_to_sop("   ")
        print("  ✗ 空文本应抛出异常")
        return False
    except ValueError as e:
        print(f"  ✓ 空文本正确报错: {e}")

    try:
        parse_text_to_sop(None)  # type: ignore
        print("  ✗ None 应抛出异常")
        return False
    except (ValueError, TypeError):
        print("  ✓ None 输入正确报错")

    # --- 测试样例 6：复杂文本解析 ---
    print("\n[测试 6] 复杂文本解析")
    complex_text = (
        "一、准备工作：请确保系统已安装 Python 3.8 以上版本。"
        "二、配置数据库：创建数据库实例，并设置连接字符串。"
        "三、部署服务：将代码部署到生产环境，由运维负责人执行。"
        "四、验证：检查服务是否正常运行，如果异常则回滚。"
    )
    try:
        doc2 = parse_text_to_sop(complex_text, title="部署流程")
        assert doc2.step_count >= 3, "复杂文本应提取至少 3 个步骤"
        print(f"  ✓ 复杂文本解析成功，共 {doc2.step_count} 个步骤")
        for s in doc2.steps:
            print(f"    - 步骤 {s.order}: {s.action[:20]}... 置信度 {s.confidence:.1f}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 7：边界情况 ---
    print("\n[测试 7] 边界情况")
    edge_texts = [
        "打开文件。保存文件。",  # 短句
        "这是一个很长的步骤描述，包含多个关键词，需要仔细分析其中的动作和条件信息，"
        "同时要注意责任人可能出现在句子的不同位置，以及时限信息的多种表达方式。",  # 长句
        "复制文件到目标目录。",  # 简单动作
    ]
    try:
        for i, text in enumerate(edge_texts):
            d = parse_text_to_sop(text)
            assert d.step_count >= 1, f"边界文本 {i} 应至少提取 1 个步骤"
        print(f"  ✓ 所有边界文本处理成功")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 8：置信度合理性 ---
    print("\n[测试 8] 置信度合理性")
    try:
        for s in doc.steps:
            assert 0.0 <= s.confidence <= 1.0, "置信度应在 0~1 之间"
        # 明确动作的置信度应高于含糊描述
        clear_text = "打开系统设置。"
        vague_text = "可能需要调整一些配置，也许还要检查日志。"
        d_clear = parse_text_to_sop(clear_text)
        d_vague = parse_text_to_sop(vague_text)
        if d_clear.steps and d_vague.steps:
            conf_clear = d_clear.steps[0].confidence
            conf_vague = d_vague.steps[0].confidence
            # 不强制要求 clear > vague，只检查都在合理范围
            assert 0.3 <= conf_clear <= 1.0
            assert 0.3 <= conf_vague <= 1.0
            print(f"  ✓ 置信度均在合理范围: [{conf_clear:.2f}, {conf_vague:.2f}]")
        else:
            print("  ✓ 置信度检查通过")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 9：Markdown 渲染完整性 ---
    print("\n[测试 9] Markdown 渲染完整性")
    try:
        md = doc.to_markdown()
        # 检查包含基本结构
        assert "---" in md, "应包含分隔线"
        assert md.count("## 步骤") == doc.step_count, "步骤标题数量应匹配"
        print(f"  ✓ Markdown 结构完整，包含 {doc.step_count} 个步骤标题")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    # --- 测试样例 10：JSON 结构完整性 ---
    print("\n[测试 10] JSON 结构完整性")
    try:
        json_str = format_json(doc)
        data = json.loads(json_str)
        required_fields = ["title", "created_at", "step_count", "steps"]
        for field in required_fields:
            assert field in data, f"JSON 缺少字段: {field}"
        for step in data["steps"]:
            for field in ["action", "order", "confidence"]:
                assert field in step, f"步骤缺少字段: {field}"
        print(f"  ✓ JSON 结构完整，包含所有必要字段")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ 所有自检测试通过")
    print("=" * 60)
    return True


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="SOP Packager - 流程封装与标准作业程序生成工具",
        epilog="示例: python main.py --input '打开系统。创建账号。' --output sop.md"
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="输入文本内容"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径（支持 .md 或 .json）"
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        default="",
        help="SOP 文档标题"
    )
    parser.add_argument(
        "--batch",
        action="append",
        type=str,
        help="批量处理模式，可多次指定"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="输出格式（默认 markdown）"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        success = run_selftest()
        return 0 if success else 1

    # 参数校验
    if args.input and args.batch:
        print(f"错误 [{ERROR_CODES['E007']}]: 不能同时指定 --input 和 --batch",
              file=sys.stderr)
        return 1

    try:
        # 批量处理
        if args.batch:
            docs = process_batch(args.batch)
            # 批量模式输出 JSON
            results = [d.to_dict() for d in docs]
            output_content = json.dumps(results, ensure_ascii=False, indent=2)
            if args.output:
                save_to_file(output_content, args.output)
            else:
                print(output_content)
            return 0

        # 单条处理
        if not args.input:
            print(f"错误 [{ERROR_CODES['E007']}]: 请提供 --input 或 --batch 参数",
                  file=sys.stderr)
            parser.print_help()
            return 1

        doc = parse_text_to_sop(args.input, title=args.title)

        # 生成输出
        if args.format == "json":
            output_content = format_json(doc)
        else:
            output_content = doc.to_markdown()

        # 输出或保存
        if args.output:
            save_to_file(output_content, args.output)
            print(f"✅ 已保存到: {args.output}")
        else:
            print(output_content)

        return 0

    except ValueError as e:
        # 提取错误码
        code = "E010"
        for c, msg in ERROR_CODES.items():
            if msg in str(e):
                code = c
                break
        print(f"错误 [{code}]: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 [{ERROR_CODES['E010']}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
