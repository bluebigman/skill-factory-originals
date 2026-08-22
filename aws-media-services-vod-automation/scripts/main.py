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
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed


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
# 网络请求辅助函数（带重试退避和超时）
# ---------------------------------------------------------------------------

def http_get_with_retry(url: str, max_retries: int = 3, timeout: int = 10) -> Optional[str]:
    """
    带重试退避和超时的 HTTP GET 请求。
    返回响应内容，失败返回 None。
    """
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    return response.read().decode("utf-8")
                else:
                    print(f"HTTP {response.status} for {url}")
        except urllib.error.URLError as e:
            print(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            print(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


# ---------------------------------------------------------------------------
# 批量处理（并发执行）
# ---------------------------------------------------------------------------

def process_batch_concurrent(
    sources: List[str],
    params_override: Optional[Dict[str, Any]] = None,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """
    并发处理多个输入源，使用 ThreadPoolExecutor。
    每个输入独立执行完整管线，返回结果列表。
    """
    if not sources:
        raise ValueError("E008: 批量处理输入为空")

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_map = {
            executor.submit(process_vod_pipeline, [source], params_override): source
            for source in sources
        }
        # 收集结果
        for future in as_completed(future_map):
            source = future_map[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"处理 {source} 失败: {e}")
                # 异常隔离：记录错误但不中断其他任务
                results.append({
                    "error": str(e),
                    "source": source
                })
    return results


# ---------------------------------------------------------------------------
# 模板验证辅助函数
# ---------------------------------------------------------------------------

def validate_template_structure(template: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 CloudFormation 模板结构完整性。
    检查资源引用、依赖关系、参数映射等。
    返回 (是否有效, 错误列表)。
    """
    errors: List[str] = []
    
    # 检查基本结构
    if "AWSTemplateFormatVersion" not in template:
        errors.append("缺少 AWSTemplateFormatVersion")
    if "Resources" not in template or not isinstance(template["Resources"], dict):
        errors.append("缺少 Resources 或格式错误")
        return False, errors
    
    resources = template["Resources"]
    
    # 检查资源引用完整性
    for resource_id, resource_def in resources.items():
        # 检查 Fn::GetAtt 引用
        if "Properties" in resource_def:
            props = resource_def["Properties"]
            # 递归检查所有引用
            def check_refs(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == "Fn::GetAtt" and isinstance(value, list) and len(value) == 2:
                            ref_resource = value[0]
                            if ref_resource not in resources:
                                errors.append(f"资源 {resource_id} 引用了不存在的资源: {ref_resource}")
                        else:
                            check_refs(value, f"{path}.{key}")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_refs(item, f"{path}[{i}]")
            
            check
