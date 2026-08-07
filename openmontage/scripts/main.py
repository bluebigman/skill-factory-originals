#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
openmontage — 智能视频生产系统（独立实现）

本脚本依据功能规格独立编写（clean-room），仅使用 Python 标准库。
提供核心数据模型、管线编排、技能调度、结果校验等能力，
并支持 --selftest 离线自检。

错误码约定：
    E001: 输入参数错误
    E002: 输入数据格式错误
    E003: 管线不存在或不可用
    E004: 技能不存在或不可用
    E005: 数据转换失败
    E006: 关键信息提取失败
    E007: 管线执行失败
    E008: 结果校验失败
    E009: 输出格式错误
    E010: 内部未知错误

用法示例：
    python scripts/main.py --help
    python scripts/main.py --selftest
    python scripts/main.py --input sample.csv --pipeline rough_cut,color,subtitle
"""

import argparse
import csv
import io
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码与异常
# ---------------------------------------------------------------------------

class OpenMontageError(Exception):
    """openmontage 基础异常，携带错误码。"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


def err(code: str, message: str) -> OpenMontageError:
    """快速构造错误异常。"""
    return OpenMontageError(code, message)


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------

@dataclass
class MediaItem:
    """素材条目（对应 C1 多源输入转换后的结构化中间结果）。"""
    source: str                # 来源（路径/URL/标识符）
    media_type: str            # 类型：video / audio / image / subtitle
    duration: float = 0.0      # 时长（秒），未知为 0
    width: int = 0             # 宽（像素），未知为 0
    height: int = 0            # 高（像素），未知为 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SceneInfo:
    """场景信息（对应 C2 关键信息提取）。"""
    scene_id: str
    start_time: float
    end_time: float
    content: str = ""
    characters: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class PipelineResult:
    """管线执行结果（对应 C5 结果校验输出）。"""
    pipeline_name: str
    status: str                # success / failed
    output_path: str = ""
    confidence: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 内置技能库（C4：技能调度）
# ---------------------------------------------------------------------------

# 技能注册表：技能名 -> 可调用函数
# 每个技能函数接收参数 dict，返回 dict（结果）
SKILL_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}


def register_skill(name: str):
    """装饰器：注册一个技能。"""
    def decorator(func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        SKILL_REGISTRY[name] = func
        return func
    return decorator


@register_skill("transition_effect")
def _skill_transition_effect(params: Dict[str, Any]) -> Dict[str, Any]:
    """转场特效技能（模拟）。"""
    effect_type = params.get("effect_type", "crossfade")
    duration = float(params.get("duration", 0.5))
    return {
        "applied": True,
        "effect": effect_type,
        "duration": duration,
        "note": "转场特效已应用（模拟）",
    }


@register_skill("audio_denoise")
def _skill_audio_denoise(params: Dict[str, Any]) -> Dict[str, Any]:
    """音频降噪技能（模拟）。"""
    strength = float(params.get("strength", 0.5))
    return {
        "applied": True,
        "strength": strength,
        "note": "音频降噪完成（模拟）",
    }


@register_skill("subtitle_generate")
def _skill_subtitle_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """字幕生成技能（模拟）。"""
    language = params.get("language", "zh")
    return {
        "applied": True,
        "language": language,
        "count": int(params.get("line_count", 0)),
        "note": "字幕生成完成（模拟）",
    }


# ---------------------------------------------------------------------------
# 内置生产管线（C3：管线编排执行）
# ---------------------------------------------------------------------------

# 管线注册表：管线名 -> 管线定义（技能序列 + 元信息）
PIPELINE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_pipeline(name: str, description: str, skills: List[str]):
    """注册一条生产管线。"""
    PIPELINE_REGISTRY[name] = {
        "name": name,
        "description": description,
        "skills": skills,
    }


# 注册 12 条标准管线
def _init_pipelines():
    register_pipeline("rough_cut", "粗剪：素材导入 + 基础剪辑", ["transition_effect"])
    register_pipeline("color", "调色：色彩校正与风格化", [])
    register_pipeline("subtitle", "字幕：自动生成与排版", ["subtitle_generate"])
    register_pipeline("audio", "音频：降噪与平衡", ["audio_denoise"])
    register_pipeline("export", "导出：格式转换与封装", [])
    register_pipeline("review", "审阅：生成预览与标注", [])
    register_pipeline("archive", "归档：素材与成片归档", [])
    register_pipeline("composite", "合成：多轨合成与特效", ["transition_effect"])
    register_pipeline("motion", "动效：动态图形与动画", [])
    register_pipeline("capture", "采集：多源素材采集", [])
    register_pipeline("transcode", "转码：分辨率与编码转换", [])
    register_pipeline("delivery", "交付：多平台分发准备", [])


_init_pipelines()


# ---------------------------------------------------------------------------
# 核心功能实现
# ---------------------------------------------------------------------------

class OpenMontageEngine:
    """openmontage 核心引擎。"""

    def __init__(self):
        self.media_items: List[MediaItem] = []
        self.scenes: List[SceneInfo] = []
        self.results: List[PipelineResult] = []
        self._temp_dir: Optional[str] = None

    # ---- C1: 多源输入转换 ----

    def load_from_csv(self, csv_text: str) -> List[MediaItem]:
        """
        从 CSV 文本加载素材清单，转换为结构化 MediaItem 列表。
        支持列：source, media_type, duration, width, height
        """
        if not csv_text or not csv_text.strip():
            raise err("E002", "CSV 输入为空")

        items: List[MediaItem] = []
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            required = {"source", "media_type"}
            for row_num, row in enumerate(reader, start=2):
                # 检查必需列
                if not required.issubset(row.keys()):
                    missing = required - set(row.keys())
                    raise err("E002", f"CSV 缺少必需列: {missing} (第 {row_num} 行)")

                source = row["source"].strip()
                media_type = row["media_type"].strip().lower()
                if not source or not media_type:
                    raise err("E002", f"第 {row_num} 行 source/media_type 不能为空")

                # 可选列，宽松解析
                try:
                    duration = float(row.get("duration", 0) or 0)
                except (ValueError, TypeError):
                    duration = 0.0
                try:
                    width = int(float(row.get("width", 0) or 0))
                except (ValueError, TypeError):
                    width = 0
                try:
                    height = int(float(row.get("height", 0) or 0))
                except (ValueError, TypeError):
                    height = 0

                item = MediaItem(
                    source=source,
                    media_type=media_type,
                    duration=max(0.0, duration),
                    width=max(0, width),
                    height=max(0, height),
                )
                items.append(item)
        except csv.Error as e:
            raise err("E002", f"CSV 解析失败: {e}")
        except OpenMontageError:
            raise
        except Exception as e:
            raise err("E005", f"数据转换失败: {e}")

        if not items:
            raise err("E002", "CSV 未包含任何有效素材行")

        self.media_items = items
        return items

    def load_from_json(self, json_text: str) -> List[MediaItem]:
        """从 JSON 文本加载素材清单。"""
        if not json_text or not json_text.strip():
            raise err("E002", "JSON 输入为空")
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise err("E002", f"JSON 解析失败: {e}")

        if not isinstance(data, list):
            raise err("E002", "JSON 顶层必须是数组")

        items: List[MediaItem] = []
        for idx, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise err("E002", f"第 {idx} 项不是对象")
            source = str(entry.get("source", "")).strip()
            media_type = str(entry.get("media_type", "")).strip().lower()
            if not source or not media_type:
                raise err("E002", f"第 {idx} 项缺少 source 或 media_type")
            items.append(MediaItem(
                source=source,
                media_type=media_type,
                duration=float(entry.get("duration", 0) or 0),
                width=int(entry.get("width", 0) or 0),
                height=int(entry.get("height", 0) or 0),
                metadata=entry.get("metadata", {}),
            ))

        if not items:
            raise err("E002", "JSON 未包含任何有效素材")
        self.media_items = items
        return items

    # ---- C2: 关键信息提取 ----

    def extract_scenes(self, script_text: str) -> List[SceneInfo]:
        """
        从剧本文本中提取场景信息（模拟实现）。
        识别模式：以 "场景" 或 "SCENE" 开头的行，后跟时间信息。
        """
        if not script_text or not script_text.strip():
            raise err("E002", "剧本输入为空")

        scenes: List[SceneInfo] = []
        lines = script_text.strip().splitlines()

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            # 宽松匹配：包含 "场景" 或 "SCENE" 关键词
            upper = line.upper()
            if "场景" not in line and "SCENE" not in upper:
                continue

            # 尝试提取时间（格式如: 00:10-00:25 或 10-25）
            import re
            time_match = re.search(r'(\d+)[:：]?(\d+)?\s*[-–—]\s*(\d+)[:：]?(\d+)?', line)
            if time_match:
                try:
                    start = float(time_match.group(1)) * 60 + float(time_match.group(2) or 0)
                    end = float(time_match.group(3)) * 60 + float(time_match.group(4) or 0)
                except ValueError:
                    start, end = 0.0, 0.0
            else:
                start, end = 0.0, 0.0

            # 从行中提取角色（模拟：匹配中括号或引号内内容）
            characters = []
            for m in re.finditer(r'[\[【]([^\]】]+)[\]】]', line):
                characters.append(m.group(1).strip())

            scene_id = f"SCENE_{line_num:03d}"
            scenes.append(SceneInfo(
                scene_id=scene_id,
                start_time=max(0.0, start),
                end_time=max(0.0, end),
                content=line,
                characters=characters,
                confidence=0.8,  # 模拟置信度
            ))

        if not scenes:
            raise err("E006", "未能从剧本中提取任何场景")

        self.scenes = scenes
        return scenes

    # ---- C3: 管线编排执行 ----

    def run_pipeline(self, pipeline_name: str, params: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """执行指定管线。"""
        if pipeline_name not in PIPELINE_REGISTRY:
            raise err("E003", f"管线不存在: {pipeline_name}")

        pipeline_def = PIPELINE_REGISTRY[pipeline_name]
        params = params or {}

        # 依次执行管线中的技能
        skill_results: Dict[str, Any] = {}
        for skill_name in pipeline_def["skills"]:
            if skill_name not in SKILL_REGISTRY:
                raise err("E004", f"技能不存在: {skill_name}")
            try:
                skill_result = SKILL_REGISTRY[skill_name](params.get(skill_name, {}))
                skill_results[skill_name] = skill_result
            except Exception as e:
                raise err("E007", f"技能 {skill_name} 执行失败: {e}")

        # 模拟输出路径
        output_path = f"output/{pipeline_name}_result"

        result = PipelineResult(
            pipeline_name=pipeline_name,
            status="success",
            output_path=output_path,
            confidence=0.95,
            details={
                "skills_executed": pipeline_def["skills"],
                "skill_results": skill_results,
                "params": params,
            },
        )
        self.results.append(result)
        return result

    def run_multi_pipeline(self, pipeline_names: List[str]) -> List[PipelineResult]:
        """按顺序执行多条管线。"""
        if not pipeline_names:
            raise err("E001", "管线列表为空")
        results = []
        for name in pipeline_names:
            results.append(self.run_pipeline(name))
        return results

    # ---- C4: 技能调度 ----

    def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """直接执行指定技能。"""
        if skill_name not in SKILL_REGISTRY:
            raise err("E004", f"技能不存在: {skill_name}")
        try:
            return SKILL_REGISTRY[skill_name](params)
        except Exception as e:
            raise err("E007", f"技能 {skill_name} 执行失败: {e}")

    # ---- C5: 结果校验输出 ----

    def validate_results(self, results: List[PipelineResult]) -> bool:
        """校验管线执行结果。"""
        if not results:
            raise err("E008", "没有可校验的结果")
        for r in results:
            if r.status != "success":
                raise err("E008", f"管线 {r.pipeline_name} 状态异常: {r.status}")
            if not (0.0 <= r.confidence <= 1.0):
                raise err("E008", f"管线 {r.pipeline_name} 置信度非法: {r.confidence}")
        return True

    def export_json(self, results: List[PipelineResult]) -> str:
        """导出结果为 JSON 字符串。"""
        try:
            data = [asdict(r) for r in results]
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            raise err("E009", f"JSON 导出失败: {e}")

    def export_csv(self, results: List[PipelineResult]) -> str:
        """导出结果为 CSV 字符串。"""
        try:
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["pipeline_name", "status", "output_path", "confidence"])
            for r in results:
                writer.writerow([r.pipeline_name, r.status, r.output_path, r.confidence])
            return buf.getvalue()
        except Exception as e:
            raise err("E009", f"CSV 导出失败: {e}")


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openmontage",
        description="开源智能视频生产系统 — 编排多管线与工具链，自动化完成视频制作流程。",
        epilog="示例: python scripts/main.py --input sample.csv --pipeline rough_cut,color,subtitle --export json",
    )
    parser.add_argument("--input", type=str, help="输入文件路径（CSV/JSON/文本）")
    parser.add_argument("--input-type", type=str, choices=["csv", "json", "script"], default="csv",
                        help="输入文件类型（默认 csv）")
    parser.add_argument("--pipeline", type=str, default="",
                        help="要执行的管线，逗号分隔（如 rough_cut,color,subtitle）")
    parser.add_argument("--skill", type=str, default="",
                        help="直接执行单个技能（如 audio_denoise）")
    parser.add_argument("--export", type=str, choices=["json", "csv"], default="json",
                        help="导出格式（默认 json）")
    parser.add_argument("--output", type=str, help="输出文件路径（默认打印到终端）")
    parser.add_argument("--selftest", action="store_true", help="运行内置离线自检")
    parser.add_argument("--list-pipelines", action="store_true", help="列出所有可用管线")
    parser.add_argument("--list-skills", action="store_true", help="列出所有可用技能")
    return parser


def handle_selftest() -> int:
    """内置自检：使用硬编码样例数据，不读外部文件、不依赖工作目录。"""
    engine = OpenMontageEngine()

    # ---- 1. C1: CSV 输入转换 ----
    sample_csv = (
        "source,media_type,duration,width,height\n"
        "clip1.mp4,video,12.5,1920,1080\n"
        "audio1.wav,audio,8.0,0,0\n"
        "title.png,image,0,1280,720\n"
        "sub1.srt,subtitle,10.0,0,0\n"
    )
    items = engine.load_from_csv(sample_csv)
    assert len(items) >= 3, "CSV 转换应至少得到 3 个素材"
    assert all(i.source for i in items), "素材 source 不能为空"
    assert all(i.media_type for i in items), "素材 media_type 不能为空"
    # 宽松验证：时长非负
    assert all(i.duration >= 0 for i in items), "时长不能为负"

    # ---- 2. C2: 场景提取 ----
    sample_script = (
        "场景1 [主角] 00:00-00:10 主角登场\n"
        "SCENE 2 [配角] 00:15-00:30 对话\n"
        "普通行不提取\n"
        "场景3 00:40-01:00 高潮\n"
    )
    scenes = engine.extract_scenes(sample_script)
    assert len(scenes) >= 2, "应至少提取 2 个场景"
    # 宽松验证：场景 ID 非空，时间非负
    assert all(s.scene_id for s in scenes), "场景 ID 不能为空"
    assert all(s.start_time >= 0 for s in scenes), "场景开始时间不能为负"
    assert all(s.end_time >= s.start_time for s in scenes), "场景结束时间应晚于开始时间"

    # ---- 3. C3: 管线执行 ----
    results = engine.run_multi_pipeline(["rough_cut", "subtitle", "audio"])
    assert len(results) >= 2, "应至少执行 2 条管线"
    assert all(r.status == "success" for r in results), "管线应全部成功"
    assert all(r.confidence > 0.5 for r in results), "置信度应大于 0.5"

    # ---- 4. C4: 技能调度 ----
    skill_result = engine.execute_skill("audio_denoise", {"strength": 0.7})
    assert skill_result.get("applied") is True, "技能应成功应用"
    assert "strength" in skill_result, "技能结果应包含参数"

    # 技能不存在时应抛出 E004
    try:
        engine.execute_skill("nonexistent_skill", {})
        raise AssertionError("不应执行不存在的技能")
    except OpenMontageError as e:
        assert e.code == "E004", f"错误码应为 E004，实际 {e.code}"

    # ---- 5. C5: 校验与导出 ----
    assert engine.validate_results(results) is True, "结果校验应通过"

    json_out = engine.export_json(results)
    assert json_out and json_out.startswith("["), "JSON 导出应为数组"

    csv_out = engine.export_csv(results)
    assert "pipeline_name" in csv_out, "CSV 导出应包含表头"

    # ---- 6. 管线/技能注册表 ----
    assert len(PIPELINE_REGISTRY) >= 10, "应注册至少 10 条管线"
    assert len(SKILL_REGISTRY) >= 3, "应注册至少 3 个技能"

    # 错误处理验证
    try:
        engine.load_from_csv("")
        raise AssertionError("空 CSV 应报错")
    except OpenMontageError as e:
        assert e.code in ("E002", "E005"), f"错误码应为 E002/E005，实际 {e.code}"

    # 全部通过
    print("[SELFTEST] 全部自检通过 ✓")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return handle_selftest()

    # 列出管线
    if args.list_pipelines:
        print("可用管线：")
        for name, info in PIPELINE_REGISTRY.items():
            print(f"  {name}: {info['description']}")
        return 0

    # 列出技能
    if args.list_skills:
        print("可用技能：")
        for name in SKILL_REGISTRY:
            print(f"  {name}")
        return 0

    engine = OpenMontageEngine()

    # 执行单技能（无需输入文件）
    if args.skill:
        if not args.skill:
            print("错误: --skill 需要技能名称", file=sys.stderr)
            return 1
        try:
            result = engine.execute_skill(args.skill, {})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except OpenMontageError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 需要输入文件
    if not args.input:
        print("错误: 需要 --input 或 --selftest", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    if not os.path.isfile(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        return 1

    try:
        # 加载输入
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()

        if args.input_type == "csv":
            engine.load_from_csv(content)
        elif args.input_type == "json":
            engine.load_from_json(content)
        elif args.input_type == "script":
            engine.extract_scenes(content)
        else:
            raise err("E001", f"不支持的输入类型: {args.input_type}")

        # 执行管线
        results: List[PipelineResult] = []
        if args.pipeline:
            pipeline_names = [p.strip() for p in args.pipeline.split(",") if p.strip()]
            results = engine.run_multi_pipeline(pipeline_names)
        else:
            # 无管线时，仅输出输入解析结果
            print(f"输入解析完成: {len(engine.media_items) or len(engine.scenes)} 条记录")
            return 0

        # 校验
        engine.validate_results(results)

        # 导出
        if args.export == "json":
            output_text = engine.export_json(results)
        else:
            output_text = engine.export_csv(results)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_text)
            print(f"结果已写入: {args.output}")
        else:
            print(output_text)

        return 0

    except OpenMontageError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: [E010] 未知异常: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
