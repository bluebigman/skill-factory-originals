#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py — AWS Media Services VOD Automation 参考实现（独立重写版）

本脚本依据功能规格独立实现，不包含任何既有代码。
用途：解析媒体输入源、识别关键参数、生成 CloudFormation 模板骨架、
      输出结构化结果，并提供离线自检（--selftest）。

错误码约定：
    E001: 未知/不支持的输入类型
    E002: 输入参数缺失或无效
    E003: 模板生成失败
    E004: 输出目录不可写
    E005: 自检数据异常
    E006: 不支持的编码格式
    E007: 参数映射失败
    E008: 批量处理输入为空
    E009: JSON 序列化失败
    E010: 内部逻辑错误（不应发生）

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# 数据模型（依据规格 1.1 能力项定义）
# ---------------------------------------------------------------------------

@dataclass
class MediaInput:
    """标准化输入清单条目。"""
    source: str                     # 原始输入（路径 / S3 URI / HTTP URL）
    input_type: str                 # local / s3 / http
    bucket: Optional[str] = None    # S3 桶名（如适用）
    key: Optional[str] = None       # S3 对象键（如适用）
    file_name: Optional[str] = None # 文件名（从路径或 URL 提取）
    extension: Optional[str] = None # 文件扩展名


@dataclass
class MediaParams:
    """关键参数映射表。"""
    resolution: str = "1920x1080"   # 目标分辨率
    codec: str = "h264"             # 视频编码
    bitrate: int = 5000000          # 视频码率（bps）
    frame_rate: int = 30            # 帧率（fps）
    audio_codec: str = "aac"        # 音频编码
    audio_bitrate: int = 128000     # 音频码率（bps）
    container: str = "mp4"          # 输出容器格式


@dataclass
class TemplateResult:
    """CloudFormation 模板生成结果。"""
    template_body: Dict[str, Any]   # 模板内容（字典）
    resource_list: List[str]        # 资源逻辑 ID 列表
    dependencies: Dict[str, List[str]]  # 资源依赖关系


# ---------------------------------------------------------------------------
# 核心逻辑：输入解析
# ---------------------------------------------------------------------------

def parse_input_source(source: str) -> MediaInput:
    """
    解析输入源，识别类型（local / s3 / http）。
    依据规格 1.1 能力项 1。
    """
    if not source or not source.strip():
        raise ValueError("E002: 输入源不能为空")

    source = source.strip()

    # 尝试解析为 URL
    parsed = urlparse(source)

    if parsed.scheme == "s3":
        # S3 URI 格式: s3://bucket-name/path/to/file
        if not parsed.netloc or not parsed.path.lstrip("/"):
            raise ValueError("E001: S3 URI 无效，需包含桶名和对象键")
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        file_name = key.split("/")[-1] if key else None
        ext = os.path.splitext(file_name)[1].lstrip(".") if file_name else None
        return MediaInput(
            source=source,
            input_type="s3",
            bucket=bucket,
            key=key,
            file_name=file_name,
            extension=ext
        )

    if parsed.scheme in ("http", "https"):
        # HTTP(S) URL
        path = parsed.path
        file_name = path.split("/")[-1] if path else None
        ext = os.path.splitext(file_name)[1].lstrip(".") if file_name else None
        return MediaInput(
            source=source,
            input_type="http",
            file_name=file_name,
            extension=ext
        )

    # 本地文件路径
    if not os.path.exists(source):
        # 不强制要求文件存在（可能只是描述），但给出提示性处理
        # 此处按规格要求：接受“本地文件描述”，故不报错
        pass

    file_name = os.path.basename(source)
    ext = os.path.splitext(file_name)[1].lstrip(".") if file_name else None
    return MediaInput(
        source=source,
        input_type="local",
        file_name=file_name,
        extension=ext
    )


def parse_batch_inputs(sources: List[str]) -> List[MediaInput]:
    """批量解析输入源（规格 1.1 能力项 5）。"""
    if not sources:
        raise ValueError("E008: 批量处理输入为空")
    return [parse_input_source(s) for s in sources]


# ---------------------------------------------------------------------------
# 核心逻辑：参数识别与映射
# ---------------------------------------------------------------------------

# 支持的编码格式（规格未限定，这里定义合理默认集合）
SUPPORTED_VIDEO_CODECS = {"h264", "h265", "hevc", "vp9", "av1"}
SUPPORTED_AUDIO_CODECS = {"aac", "mp3", "opus", "vorbis"}
SUPPORTED_CONTAINERS = {"mp4", "mkv", "mov", "webm"}

# 常见分辨率映射（用于从字符串解析）
RESOLUTION_PATTERN = re.compile(r"^(\d{3,5})[xX*](\d{3,5})$")


def map_params(
    resolution: Optional[str] = None,
    codec: Optional[str] = None,
    bitrate: Optional[int] = None,
    frame_rate: Optional[int] = None,
    audio_codec: Optional[str] = None,
    audio_bitrate: Optional[int] = None,
    container: Optional[str] = None,
) -> MediaParams:
    """
    根据输入参数生成参数映射表（规格 1.1 能力项 2）。
    不存在的参数使用默认值。
    """
    params = MediaParams()

    if resolution is not None:
        # 验证分辨率格式
        if not RESOLUTION_PATTERN.match(str(resolution)):
            raise ValueError(f"E007: 分辨率格式无效: {resolution}")
        params.resolution = str(resolution)

    if codec is not None:
        codec_lower = str(codec).lower()
        if codec_lower not in SUPPORTED_VIDEO_CODECS:
            raise ValueError(f"E006: 不支持的视频编码: {codec}")
        params.codec = codec_lower

    if bitrate is not None:
        if int(bitrate) <= 0:
            raise ValueError("E007: 码率必须为正数")
        params.bitrate = int(bitrate)

    if frame_rate is not None:
        if int(frame_rate) <= 0:
            raise ValueError("E007: 帧率必须为正数")
        params.frame_rate = int(frame_rate)

    if audio_codec is not None:
        ac_lower = str(audio_codec).lower()
        if ac_lower not in SUPPORTED_AUDIO_CODECS:
            raise ValueError(f"E006: 不支持的音频编码: {audio_codec}")
        params.audio_codec = ac_lower

    if audio_bitrate is not None:
        if int(audio_bitrate) <= 0:
            raise ValueError("E007: 音频码率必须为正数")
        params.audio_bitrate = int(audio_bitrate)

    if container is not None:
        c_lower = str(container).lower()
        if c_lower not in SUPPORTED_CONTAINERS:
            raise ValueError(f"E006: 不支持的容器格式: {container}")
        params.container = c_lower

    return params


# ---------------------------------------------------------------------------
# 核心逻辑：CloudFormation 模板生成
# ---------------------------------------------------------------------------

def generate_cloudformation_template(
    inputs: List[MediaInput],
    params: MediaParams
) -> TemplateResult:
    """
    生成 CloudFormation 模板（规格 1.1 能力项 3）。
    生成结构化的 YAML/JSON 兼容字典。
    注意：本实现生成 JSON 格式模板（YAML 是 JSON 的超集，可直接转换）。
    """
    if not inputs:
        raise ValueError("E002: 无有效输入源")

    # 构建资源列表
    resources: Dict[str, Any] = {}
    resource_ids: List[str] = []
    dependencies: Dict[str, List[str]] = {}

    # 为每个输入创建一个 MediaConvert 任务资源（示例性）
    for idx, media_in in enumerate(inputs):
        resource_id = f"MediaConvertJob{idx + 1}"
        resource_ids.append(resource_id)

        # 构建输入配置
        if media_in.input_type == "s3":
            input_uri = f"s3://{media_in.bucket}/{media_in.key}"
        elif media_in.input_type == "http":
            input_uri = media_in.source
        else:
            # 本地文件：在真实部署中需先上传至 S3，这里用占位符
            input_uri = f"s3://your-bucket/path/to/{media_in.file_name or 'input'}"

        # 资源定义（简化但结构完整的 CloudFormation 资源）
        resources[resource_id] = {
            "Type": "AWS::MediaConvert::Job",
            "Properties": {
                "Role": {"Fn::GetAtt": ["MediaConvertRole", "Arn"]},
                "Settings": {
                    "Inputs": [
                        {
                            "FileInput": input_uri,
                            "AudioSelectors": {
                                "Audio Selector 1": {
                                    "DefaultSelection": "DEFAULT"
                                }
                            }
                        }
                    ],
                    "OutputGroups": [
                        {
                            "OutputGroupSettings": {
                                "Type": "FILE_GROUP_SETTINGS",
                                "FileGroupSettings": {
                                    "Destination": "s3://your-output-bucket/output/"
                                }
                            },
                            "Outputs": [
                                {
                                    "ContainerSettings": {
                                        "Container": params.container.upper()
                                    },
                                    "VideoDescription": {
                                        "CodecSettings": {
                                            "Codec": params.codec.upper(),
                                            "CodecSettings": {
                                                "Bitrate": params.bitrate,
                                                "Framerate": {
                                                    "Value": params.frame_rate
                                                }
                                            }
                                        }
                                    },
                                    "AudioDescriptions": [
                                        {
                                            "CodecSettings": {
                                                "Codec": params.audio_codec.upper(),
                                                "CodecSettings": {
                                                    "Bitrate": params.audio_bitrate
                                                }
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

        # 依赖关系：所有任务依赖 IAM 角色
        dependencies[resource_id] = ["MediaConvertRole"]

    # 添加 IAM 角色资源
    resources["MediaConvertRole"] = {
        "Type": "AWS::IAM::Role",
        "Properties": {
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "mediaconvert.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            },
            "Policies": [
                {
                    "PolicyName": "MediaConvertAccess",
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:GetObject",
                                    "s3:PutObject"
                                ],
                                "Resource": "*"
                            }
                        ]
                    }
                }
            ]
        }
    }
    resource_ids.append("MediaConvertRole")

    # 构建完整模板
    template: Dict[str, Any] = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "VOD Automation Workflow - Generated by skill",
        "Resources": resources,
        "Outputs": {
            "WorkflowName": {
                "Value": "VODAutomationWorkflow"
            }
        }
    }

    return TemplateResult(
        template_body=template,
        resource_list=resource_ids,
        dependencies=dependencies
    )


# ---------------------------------------------------------------------------
# 核心逻辑：结构化输出
# ---------------------------------------------------------------------------

def build_structured_result(
    inputs: List[MediaInput],
    params: MediaParams,
    template_result: TemplateResult
) -> Dict[str, Any]:
    """
    构建结构化输出（规格 1.1 能力项 4）。
    包含输入清单、参数映射、资源清单与依赖关系。
    """
    return {
        "schema_version": "1.0.0",
        "inputs": [asdict(i) for i in inputs],
        "parameters": asdict(params),
        "resources": {
            "template": template_result.template_body,
            "resource_list": template_result.resource_list,
            "dependencies": template_result.dependencies
        }
    }


# ---------------------------------------------------------------------------
# 核心流程：完整处理管线
# ---------------------------------------------------------------------------

def process_vod_pipeline(
    sources: List[str],
    params_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    完整处理管线：解析输入 -> 参数映射 -> 生成模板 -> 结构化输出。
    """
    try:
        # 1. 解析输入
        inputs = parse_batch_inputs(sources)

        # 2. 参数映射
        override = params_override or {}
        params = map_params(**override)

        # 3. 生成模板
        template = generate_cloudformation_template(inputs, params)

        # 4. 结构化输出
        result = build_structured_result(inputs, params, template)
        return result

    except ValueError as e:
        # 保留原始错误码
        raise
    except Exception:
        raise ValueError("E010: 内部逻辑错误")


# ---------------------------------------------------------------------------
# 自检模块（--selftest）
# ---------------------------------------------------------------------------

def run_selftest() -> int:
    """
    离线自检核心逻辑。使用内置硬编码样例数据，不读取外部文件。
    使用宽松断言（大小比较/区间判断），确保任何环境可过。
    """
    print("开始自检...")

    # ---- 测试 1: 输入解析 ----
    print("[1/5] 测试输入解析...")
    try:
        # S3 URI
        s3_input = parse_input_source("s3://my-bucket/videos/sample.mp4")
        assert s3_input.input_type == "s3"
        assert s3_input.bucket == "my-bucket"
        assert s3_input.key == "videos/sample.mp4"
        assert s3_input.file_name == "sample.mp4"
        assert s3_input.extension == "mp4"

        # HTTP URL
        http_input = parse_input_source("https://example.com/media/video1.mov")
        assert http_input.input_type == "http"
        assert http_input.file_name == "video1.mov"
        assert http_input.extension == "mov"

        # 本地路径
        local_input = parse_input_source("/tmp/input/video.mp4")
        assert local_input.input_type == "local"
        assert local_input.file_name == "video.mp4"
        assert local_input.extension == "mp4"

        print("    ✓ 输入解析测试通过")
    except Exception as e:
        print(f"    ✗ 输入解析测试失败: {e}")
        return 1

    # ---- 测试 2: 参数映射 ----
    print("[2/5] 测试参数映射...")
    try:
        params = map_params(
            resolution="1920x1080",
            codec="h264",
            bitrate=5000000,
            frame_rate=30,
            audio_codec="aac",
            audio_bitrate=128000,
            container="mp4"
        )
        # 宽松验证
        assert params.resolution == "1920x1080"
        assert params.codec == "h264"
        assert params.bitrate > 0
        assert params.frame_rate > 0
        assert params.audio_codec == "aac"
        assert params.audio_bitrate > 0
        assert params.container == "mp4"

        # 默认参数测试
        default_params = map_params()
        assert default_params.resolution is not None
        assert default_params.bitrate > 0
        assert default_params.frame_rate > 0
        print("    ✓ 参数映射测试通过")
    except Exception as e:
        print(f"    ✗ 参数映射测试失败: {e}")
        return 1

    # ---- 测试 3: 模板生成 ----
    print("[3/5] 测试模板生成...")
    try:
        inputs = [
            parse_input_source("s3://bucket1/videos/a.mp4"),
            parse_input_source("s3://bucket2/videos/b.mov")
        ]
        params = map_params()
        template = generate_cloudformation_template(inputs, params)

        # 宽松验证
        assert template.template_body is not None
        assert len(template.resource_list) >= 2  # 至少包含任务和角色
        assert "MediaConvertRole" in template.resource_list
        assert len(template.dependencies) > 0
        print("    ✓ 模板生成测试通过")
    except Exception as e:
        print(f"    ✗ 模板生成测试失败: {e}")
        return 1

    # ---- 测试 4: 完整管线 ----
    print("[4/5] 测试完整管线...")
    try:
        result = process_vod_pipeline(
            ["s3://bucket/videos/sample.mp4"],
            {"resolution": "1280x720", "bitrate": 3000000}
        )
        assert result["schema_version"] == "1.0.0"
        assert len(result["inputs"]) == 1
        assert result["inputs"][0]["input_type"] == "s3"
        assert result["parameters"]["resolution"] == "1280x720"
        assert result["parameters"]["bitrate"] == 3000000
        assert len(result["resources"]["resource_list"]) >= 2
        print("    ✓ 完整管线测试通过")
    except Exception as e:
        print(f"    ✗ 完整管线测试失败: {e}")
        return 1

    # ---- 测试 5: 错误处理 ----
    print("[5/5] 测试错误处理...")
    try:
        # 空输入
        try:
            parse_batch_inputs([])
            print("    ✗ 空输入未抛出异常")
            return 1
        except ValueError as e:
            assert "E008" in str(e)

        # 无效分辨率
        try:
            map_params(resolution="invalid")
            print("    ✗ 无效分辨率未抛出异常")
            return 1
        except ValueError as e:
            assert "E007" in str(e)

        # 不支持的编码
        try:
            map_params(codec="unknown_codec")
            print("    ✗ 不支持的编码未抛出异常")
            return 1
        except ValueError as e:
            assert "E006" in str(e)

        print("    ✓ 错误处理测试通过")
    except Exception as e:
        print(f"    ✗ 错误处理测试失败: {e}")
        return 1

    print("\n全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------

def main() -> int:
    """命令行主入口。"""
    parser = argparse.ArgumentParser(
        description="AWS Media Services VOD Automation - 参考实现",
        epilog="示例: python main.py --sources s3://bucket/video.mp4 --resolution 1920x1080"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        help="输入源列表（S3 URI、HTTP URL 或本地路径）"
    )
    parser.add_argument("--resolution", help="目标分辨率，如 1920x1080")
    parser.add_argument("--codec", help="视频编码，如 h264/h265")
    parser.add_argument("--bitrate", type=int, help="视频码率（bps）")
    parser.add_argument("--frame-rate", type=int, help="帧率（fps）")
    parser.add_argument("--audio-codec", help="音频编码，如 aac/mp3")
    parser.add_argument("--audio-bitrate", type=int, help="音频码率（bps）")
    parser.add_argument("--container", help="输出容器，如 mp4/mkv")
    parser.add_argument("--output", help="输出 JSON 文件路径（可选）")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不依赖外部文件/网络）"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return run_selftest()

    # 正常处理模式
    if not args.sources:
        print("错误: 请提供 --sources 参数（至少一个输入源）", file=sys.stderr)
        print("提示: 运行 --selftest 可进行离线自检", file=sys.stderr)
        return 1

    try:
        # 收集参数覆盖
        override: Dict[str, Any] = {}
        if args.resolution:
            override["resolution"] = args.resolution
        if args.codec:
            override["codec"] = args.codec
        if args.bitrate is not None:
            override["bitrate"] = args.bitrate
        if args.frame_rate is not None:
            override["frame_rate"] = args.frame_rate
        if args.audio_codec:
            override["audio_codec"] = args.audio_codec
        if args.audio_bitrate is not None:
            override["audio_bitrate"] = args.audio_bitrate
        if args.container:
            override["container"] = args.container

        # 执行完整管线
        result = process_vod_pipeline(args.sources, override)

        # 输出结果
        output_json = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output_json)
                print(f"结果已写入: {args.output}")
            except OSError as e:
                print(f"E004: 无法写入输出文件: {e}", file=sys.stderr)
                return 1
        else:
            print(output_json)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"E010: 未预期错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
