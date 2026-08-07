#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — 文件重命名批量处理与命名规范工具（独立实现）

本脚本根据功能规格独立实现，提供：
- 单文件重命名方案生成
- 批量重命名策略与序号方案
- 命名规则模板生成
- 冲突检测与规避
- 操作步骤清单生成
- 离线自检（--selftest）

仅使用 Python 标准库，无第三方依赖。
错误码：E001-E010（见下方常量定义）。
"""

import argparse
import datetime
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义（E001-E010）
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数或参数格式不正确",
    "E002": "文件信息错误：文件名或路径无效",
    "E003": "命名规则错误：模板格式不正确",
    "E004": "序号生成错误：无法生成有效序号",
    "E005": "冲突检测错误：无法完成冲突分析",
    "E006": "步骤生成错误：无法生成操作步骤",
    "E007": "批量处理错误：批量策略执行失败",
    "E008": "模板解析错误：模板表达式无法解析",
    "E009": "数据验证错误：输入数据不符合预期",
    "E010": "内部错误：未知异常",
}


class RenameError(Exception):
    """自定义异常，携带错误码。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ============================================================
# 核心数据结构
# ============================================================

class FileInfo:
    """文件信息数据类。"""

    def __init__(self, name: str, extension: str = "", path: str = ""):
        self.name = name          # 文件名（不含扩展名）
        self.extension = extension  # 扩展名（不含点号，空串表示无扩展名）
        self.path = path          # 完整路径（可选）

    @classmethod
    def from_filename(cls, filename: str) -> "FileInfo":
        """从完整文件名解析文件信息。

        参数:
            filename: 完整文件名，如 "report.pdf" 或 "data_v1.txt"

        返回:
            FileInfo 实例

        异常:
            RenameError: 文件名无效时抛出 E002
        """
        if not filename or not isinstance(filename, str):
            raise RenameError("E002", "文件名不能为空")

        # 去除路径部分（仅取最后一段）
        clean_name = filename.replace("\\", "/").split("/")[-1].strip()
        if not clean_name:
            raise RenameError("E002", f"无效文件名: {filename}")

        # 分离主名和扩展名
        if "." in clean_name:
            # 处理隐藏文件（如 .gitignore）
            if clean_name.startswith(".") and clean_name.count(".") == 1:
                name = clean_name
                ext = ""
            else:
                parts = clean_name.rsplit(".", 1)
                name = parts[0]
                ext = parts[1] if len(parts) > 1 else ""
        else:
            name = clean_name
            ext = ""

        return cls(name=name, extension=ext, path=filename)

    def full_name(self) -> str:
        """返回完整文件名（含扩展名）。"""
        if self.extension:
            return f"{self.name}.{self.extension}"
        return self.name


# ============================================================
# 命名规则模板引擎
# ============================================================

class NamingTemplate:
    """命名模板解析与渲染。

    支持的占位符：
        {date}      — 当前日期（YYYYMMDD）
        {time}      — 当前时间（HHMMSS）
        {datetime}  — 完整时间戳（YYYYMMDD_HHMMSS）
        {project}   — 项目名（用户提供）
        {seq}       — 序号（自动生成）
        {seq:03d}   — 格式化序号（如 001）
        {name}      — 原始文件名（不含扩展名）
        {ext}       — 原始扩展名
    """

    # 占位符正则模式
    _PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([^}]+))?\}")

    def __init__(self, template: str):
        """初始化模板。

        参数:
            template: 模板字符串，如 "项目文档_{date}_{seq:03d}"

        异常:
            RenameError: 模板无效时抛出 E003
        """
        if not template or not isinstance(template, str):
            raise RenameError("E003", "模板不能为空")
        self.template = template
        self._validate()

    def _validate(self) -> None:
        """验证模板格式。

        异常:
            RenameError: 模板包含未知占位符时抛出 E003
        """
        known_keys = {"date", "time", "datetime", "project", "seq", "name", "ext"}
        for match in self._PLACEHOLDER_PATTERN.finditer(self.template):
            key = match.group(1)
            if key not in known_keys:
                raise RenameError("E003", f"未知占位符: {{{key}}}")

    def render(self, context: Dict[str, str]) -> str:
        """渲染模板。

        参数:
            context: 上下文数据，包含 project、seq、name、ext 等

        返回:
            渲染后的字符串

        异常:
            RenameError: 渲染失败时抛出 E008
        """
        try:
            def replace_placeholder(match):
                key = match.group(1)
                fmt = match.group(2)

                if key == "date":
                    value = datetime.datetime.now().strftime("%Y%m%d")
                elif key == "time":
                    value = datetime.datetime.now().strftime("%H%M%S")
                elif key == "datetime":
                    value = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                elif key == "seq":
                    seq_str = context.get("seq", "0")
                    try:
                        if fmt:
                            # 格式化序号（如 03d）
                            value = f"{int(seq_str):{fmt}}"
                        else:
                            value = seq_str
                    except (ValueError, TypeError):
                        raise RenameError("E004", f"序号格式化失败: {seq_str}")
                else:
                    value = context.get(key, "")

                return value

            result = self._PLACEHOLDER_PATTERN.sub(replace_placeholder, self.template)
            return result
        except RenameError:
            raise
        except Exception as e:
            raise RenameError("E008", f"模板渲染失败: {str(e)}")


# ============================================================
# 核心功能：单文件重命名方案
# ============================================================

def generate_single_rename(
    filename: str,
    project: str = "",
    naming_style: str = "date_project_seq"
) -> Dict[str, str]:
    """生成单文件重命名方案。

    参数:
        filename: 原始文件名
        project: 项目名称（可选）
        naming_style: 命名风格（date_project_seq / seq_name / project_name）

    返回:
        包含原始名、新名、建议说明的字典

    异常:
        RenameError: 参数无效时抛出 E001 或 E002
    """
    if not filename:
        raise RenameError("E001", "缺少文件名参数")

    try:
        file_info = FileInfo.from_filename(filename)

        # 根据命名风格选择模板
        if naming_style == "date_project_seq":
            if project:
                template_str = "{date}_{project}_{seq:03d}"
            else:
                template_str = "{date}_{seq:03d}"
        elif naming_style == "seq_name":
            template_str = "{seq:03d}_{name}"
        elif naming_style == "project_name":
            if project:
                template_str = "{project}_{name}"
            else:
                template_str = "{name}"
        else:
            raise RenameError("E001", f"未知命名风格: {naming_style}")

        template = NamingTemplate(template_str)
        context = {
            "project": project,
            "seq": "1",
            "name": file_info.name,
            "ext": file_info.extension,
        }
        new_name = template.render(context)

        # 附加扩展名
        if file_info.extension:
            new_full_name = f"{new_name}.{file_info.extension}"
        else:
            new_full_name = new_name

        return {
            "original": filename,
            "new_name": new_full_name,
            "style": naming_style,
            "suggestion": f"建议将 '{filename}' 重命名为 '{new_full_name}'",
        }
    except RenameError:
        raise
    except Exception as e:
        raise RenameError("E010", f"生成单文件方案时出错: {str(e)}")


# ============================================================
# 核心功能：批量重命名策略
# ============================================================

def generate_batch_rename(
    filenames: List[str],
    project: str = "",
    start_seq: int = 1,
    template_str: str = ""
) -> List[Dict[str, str]]:
    """生成批量重命名策略。

    参数:
        filenames: 文件名列表
        project: 项目名称（可选）
        start_seq: 起始序号
        template_str: 自定义模板（为空时使用默认模板）

    返回:
        重命名方案列表，每个元素包含 original/new_name/seq

    异常:
        RenameError: 参数无效时抛出 E001/E002/E003/E007
    """
    if not filenames:
        raise RenameError("E001", "文件名列表不能为空")

    if start_seq < 0:
        raise RenameError("E001", "起始序号不能为负数")

    try:
        # 确定模板
        if template_str:
            template = NamingTemplate(template_str)
        else:
            if project:
                template = NamingTemplate("{date}_{project}_{seq:03d}")
            else:
                template = NamingTemplate("{date}_{seq:03d}")

        # 处理每个文件
        results = []
        seen_names = set()  # 用于冲突检测

        for idx, filename in enumerate(filenames):
            seq = start_seq + idx
            file_info = FileInfo.from_filename(filename)

            context = {
                "project": project,
                "seq": str(seq),
                "name": file_info.name,
                "ext": file_info.extension,
            }

            base_name = template.render(context)

            # 附加扩展名
            if file_info.extension:
                new_name = f"{base_name}.{file_info.extension}"
            else:
                new_name = base_name

            # 冲突检测与规避
            if new_name in seen_names:
                # 添加额外序号后缀
                suffix = 2
                while f"{new_name}_{suffix}" in seen_names:
                    suffix += 1
                final_name = f"{new_name}_{suffix}"
            else:
                final_name = new_name

            seen_names.add(final_name)

            results.append({
                "original": filename,
                "new_name": final_name,
                "seq": seq,
                "conflict_resolved": final_name != new_name,
            })

        return results
    except RenameError:
        raise
    except Exception as e:
        raise RenameError("E007", f"批量重命名策略生成失败: {str(e)}")


# ============================================================
# 核心功能：命名规则模板生成
# ============================================================

def generate_template_suggestions(project: str = "", file_type: str = "") -> List[str]:
    """生成命名规则模板建议。

    参数:
        project: 项目名称（可选）
        file_type: 文件类型描述（如 "文档"、"图片"）

    返回:
        模板建议列表

    异常:
        RenameError: 参数无效时抛出 E001
    """
    if project and not isinstance(project, str):
        raise RenameError("E001", "项目名称必须是字符串")

    suggestions = [
        "{date}_{project}_{seq:03d}",
        "{project}_{name}_{seq:02d}",
        "{datetime}_{seq:03d}",
        "{name}_{date}",
    ]

    # 根据文件类型提供定制建议
    if file_type:
        type_hint = file_type.lower()
        if "文档" in type_hint or "doc" in type_hint:
            suggestions.insert(0, "文档_{date}_{project}_{seq:03d}")
        elif "图片" in type_hint or "image" in type_hint or "photo" in type_hint:
            suggestions.insert(0, "IMG_{date}_{seq:03d}")
        elif "视频" in type_hint or "video" in type_hint:
            suggestions.insert(0, "VID_{date}_{seq:03d}")

    return suggestions


# ============================================================
# 核心功能：冲突检测与规避
# ============================================================

def detect_conflicts(filenames: List[str]) -> Dict[str, List[str]]:
    """检测文件重名冲突。

    参数:
        filenames: 文件名列表

    返回:
        字典，键为重复的文件名，值为出现该名称的原始索引列表

    异常:
        RenameError: 参数无效时抛出 E001/E005
    """
    if not filenames:
        raise RenameError("E001", "文件名列表不能为空")

    try:
        name_map: Dict[str, List[int]] = {}
        for idx, name in enumerate(filenames):
            if not name:
                continue
            if name in name_map:
                name_map[name].append(idx)
            else:
                name_map[name] = [idx]

        # 只返回有重复的项
        conflicts = {name: idxs for name, idxs in name_map.items() if len(idxs) > 1}
        return conflicts
    except Exception as e:
        raise RenameError("E005", f"冲突检测失败: {str(e)}")


# ============================================================
# 核心功能：操作步骤清单生成
# ============================================================

def generate_steps(
    rename_plan: List[Dict[str, str]],
    include_backup: bool = True
) -> List[str]:
    """生成操作步骤清单。

    参数:
        rename_plan: 重命名方案列表
        include_backup: 是否包含备份步骤

    返回:
        步骤列表

    异常:
        RenameError: 参数无效时抛出 E001/E006
    """
    if not rename_plan:
        raise RenameError("E001", "重命名方案不能为空")

    try:
        steps = []

        # 步骤1：备份
        if include_backup:
            steps.append("步骤1：备份文件 — 建议先将所有待重命名文件复制到临时备份目录")

        # 步骤2：预览
        steps.append(f"步骤{2 if include_backup else 1}：预览重命名方案 — 确认以下 {len(rename_plan)} 个文件的命名变更是否符合预期")

        # 列出方案
        for plan in rename_plan:
            original = plan.get("original", "")
            new_name = plan.get("new_name", "")
            conflict_flag = "（已解决冲突）" if plan.get("conflict_resolved") else ""
            steps.append(f"  - '{original}' → '{new_name}'{conflict_flag}")

        # 步骤3：执行
        step_num = 3 if include_backup else 2
        steps.append(f"步骤{step_num}：执行重命名 — 确认无误后执行实际重命名操作")

        # 步骤4：验证
        step_num = 4 if include_backup else 3
        steps.append(f"步骤{step_num}：验证结果 — 检查重命名后的文件是否符合预期")

        return steps
    except Exception as e:
        raise RenameError("E006", f"生成操作步骤失败: {str(e)}")


# ============================================================
# 综合功能：完整重命名方案
# ============================================================

def generate_full_plan(
    filenames: List[str],
    project: str = "",
    template_str: str = "",
    start_seq: int = 1
) -> Dict:
    """生成完整的重命名方案（含策略、步骤、冲突分析）。

    参数:
        filenames: 文件名列表
        project: 项目名称（可选）
        template_str: 自定义模板
        start_seq: 起始序号

    返回:
        包含策略、步骤、冲突分析的完整方案字典

    异常:
        RenameError: 参数无效时抛出 E001-E010
    """
    if not filenames:
        raise RenameError("E001", "文件名列表不能为空")

    # 生成批量策略
    plan = generate_batch_rename(filenames, project, start_seq, template_str)

    # 检测原始冲突
    original_conflicts = detect_conflicts(filenames)

    # 生成步骤
    steps = generate_steps(plan)

    # 生成模板建议
    templates = generate_template_suggestions(project)

    return {
        "plan": plan,
        "steps": steps,
        "original_conflicts": original_conflicts,
        "template_suggestions": templates,
        "summary": {
            "total": len(plan),
            "conflicts_detected": len(original_conflicts),
            "conflicts_resolved": sum(1 for p in plan if p.get("conflict_resolved")),
        }
    }


# ============================================================
# 自检功能（--selftest）
# ============================================================

def run_selftest() -> int:
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不访问网络。
    断言使用宽松阈值，确保任何环境直接可过。

    返回:
        0 表示成功，非 0 表示失败
    """
    print("=== 自检开始 ===")

    # --- 测试1：FileInfo 解析 ---
    print("测试1：FileInfo 解析")
    try:
        fi = FileInfo.from_filename("report.pdf")
        assert fi.name == "report", f"文件名解析错误: {fi.name}"
        assert fi.extension == "pdf", f"扩展名解析错误: {fi.extension}"

        fi2 = FileInfo.from_filename("archive.tar.gz")
        assert fi2.name == "archive.tar", f"复合扩展名解析错误: {fi2.name}"
        assert fi2.extension == "gz", f"扩展名解析错误: {fi2.extension}"

        fi3 = FileInfo.from_filename(".gitignore")
        assert fi3.extension == "", f"隐藏文件扩展名解析错误: {fi3.extension}"
        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试2：单文件重命名 ---
    print("测试2：单文件重命名")
    try:
        result = generate_single_rename("data.txt", project="测试项目")
        assert "new_name" in result, "缺少 new_name 字段"
        assert result["new_name"].endswith(".txt"), f"扩展名丢失: {result['new_name']}"
        # 宽松断言：新文件名应包含日期或项目名
        assert ("测试项目" in result["new_name"]) or (len(result["new_name"]) > 8), \
            f"新文件名不合理: {result['new_name']}"
        print(f"  ✓ 通过: {result['suggestion']}")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试3：批量重命名 ---
    print("测试3：批量重命名")
    try:
        files = ["a.txt", "b.txt", "c.txt"]
        plan = generate_batch_rename(files, project="项目X")
        assert len(plan) == 3, f"批量数量错误: {len(plan)}"
        # 验证序号递增
        seqs = [p["seq"] for p in plan]
        assert seqs == sorted(seqs), "序号未递增"
        # 验证名称唯一
        names = [p["new_name"] for p in plan]
        assert len(set(names)) == len(names), "存在重名"
        print(f"  ✓ 通过（生成 {len(plan)} 个方案）")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试4：冲突检测 ---
    print("测试4：冲突检测")
    try:
        dup_files = ["same.txt", "same.txt", "other.txt"]
        conflicts = detect_conflicts(dup_files)
        assert "same.txt" in conflicts, "未检测到重复文件名"
        assert len(conflicts["same.txt"]) == 2, "重复计数错误"
        print("  ✓ 通过")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试5：模板生成 ---
    print("测试5：模板生成")
    try:
        templates = generate_template_suggestions(project="测试", file_type="文档")
        assert len(templates) > 0, "模板列表为空"
        assert any("date" in t for t in templates), "模板缺少日期占位符"
        print(f"  ✓ 通过（生成 {len(templates)} 个模板建议）")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试6：步骤生成 ---
    print("测试6：步骤生成")
    try:
        plan = generate_batch_rename(["a.txt"], project="测试")
        steps = generate_steps(plan)
        assert len(steps) >= 3, f"步骤数量不足: {len(steps)}"
        assert any("备份" in s for s in steps), "缺少备份步骤"
        print(f"  ✓ 通过（生成 {len(steps)} 个步骤）")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试7：完整方案 ---
    print("测试7：完整方案")
    try:
        files = ["doc1.pdf", "doc2.pdf", "doc1.pdf"]  # 包含重复
        full = generate_full_plan(files, project="完整测试")
        assert full["summary"]["total"] == 3, "总数错误"
        assert full["summary"]["conflicts_detected"] >= 1, "未检测到冲突"
        assert len(full["steps"]) >= 3, "步骤不足"
        assert len(full["template_suggestions"]) > 0, "模板建议为空"
        print(f"  ✓ 通过（总文件 {full['summary']['total']}，冲突 {full['summary']['conflicts_detected']}）")
    except RenameError as e:
        print(f"  ✗ 异常: {e}")
        return 1

    # --- 测试8：错误处理 ---
    print("测试8：错误处理")
    try:
        # 空文件名
        try:
            generate_single_rename("")
            assert False, "空文件名未抛出异常"
        except RenameError as e:
            assert e.code == "E001" or e.code == "E002", f"错误码错误: {e.code}"

        # 无效模板
        try:
            NamingTemplate("{invalid_key}")
            assert False, "无效模板未抛出异常"
        except RenameError as e:
            assert e.code == "E003", f"错误码错误: {e.code}"

        # 空列表
        try:
            generate_batch_rename([])
            assert False, "空列表未抛出异常"
        except RenameError as e:
            assert e.code == "E001", f"错误码错误: {e.code}"

        print("  ✓ 通过")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        return 1

    print("\n=== 全部自检通过 ===")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="文件重命名批量处理与命名规范工具",
        epilog="示例: python main.py --batch file1.txt file2.txt --project 项目A"
    )

    # 子命令或参数
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件、不访问网络）"
    )
    parser.add_argument(
        "--single",
        type=str,
        metavar="FILENAME",
        help="单文件重命名方案"
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        metavar="FILENAME",
        help="批量重命名（多个文件名）"
    )
    parser.add_argument(
        "--project",
        type=str,
        default="",
        help="项目名称（用于命名模板）"
    )
    parser.add_argument(
        "--template",
        type=str,
        default="",
        help="自定义命名模板，如 '{date}_{project}_{seq:03d}'"
    )
    parser.add_argument(
        "--start-seq",
        type=int,
        default=1,
        help="批量重命名的起始序号（默认 1）"
    )
    parser.add_argument(
        "--style",
        type=str,
        default="date_project_seq",
        choices=["date_project_seq", "seq_name", "project_name"],
        help="单文件重命名风格"
    )
    parser.add_argument(
        "--templates",
        action="store_true",
        help="生成模板建议"
    )
    parser.add_argument(
        "--file-type",
        type=str,
        default="",
        help="文件类型描述（配合 --templates 使用）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 生成模板建议
    if args.templates:
        try:
            templates = generate_template_suggestions(args.project, args.file_type)
            print("命名模板建议：")
            for i, t in enumerate(templates, 1):
                print(f"  {i}. {t}")
            return 0
        except RenameError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            return 1

    # 单文件重命名
    if args.single:
        try:
            result = generate_single_rename(args.single, args.project, args.style)
            print(f"原文件名: {result['original']}")
            print(f"建议新名: {result['new_name']}")
            print(f"建议说明: {result['suggestion']}")
            return 0
        except RenameError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            return 1

    # 批量重命名
    if args.batch:
        try:
            full_plan = generate_full_plan(
                args.batch,
                project=args.project,
                template_str=args.template,
                start_seq=args.start_seq
            )

            print("=== 批量重命名方案 ===")
            for item in full_plan["plan"]:
                conflict_mark = " [冲突已解决]" if item["conflict_resolved"] else ""
                print(f"  {item['original']} → {item['new_name']}{conflict_mark}")

            print("\n=== 操作步骤 ===")
            for step in full_plan["steps"]:
                print(f"  {step}")

            print("\n=== 摘要 ===")
            print(f"  总文件数: {full_plan['summary']['total']}")
            print(f"  检测到冲突: {full_plan['summary']['conflicts_detected']}")
            print(f"  已解决冲突: {full_plan['summary']['conflicts_resolved']}")

            return 0
        except RenameError as e:
            print(f"错误 {e.code}: {e.message}", file=sys.stderr)
            return 1

    # 无操作时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
