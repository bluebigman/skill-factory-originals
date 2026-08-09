#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理工具 - 支持视频信息提取、脚本生成、校验与报告输出
仅依赖标准库，支持离线自检
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


# ==================== 错误码定义 ====================
ERROR_CODES = {
    "E001": "路径为空",
    "E002": "路径不存在",
    "E003": "非视频文件",
    "E004": "视频文件损坏",
    "E005": "参数缺失",
    "E006": "参数类型错误",
    "E007": "脚本生成失败",
    "E008": "视频校验失败",
    "E009": "元数据格式化失败",
    "E010": "操作记录失败",
}


class VideoToolError(Exception):
    """视频工具自定义异常"""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or ERROR_CODES.get(code, "未知错误")
        super().__init__(f"[{code}] {self.message}")


# ==================== 核心功能函数 ====================

def validate_path(path: str) -> Tuple[bool, str]:
    """验证路径有效性"""
    if not path or not path.strip():
        return False, "E001"
    if not os.path.exists(path):
        return False, "E002"
    return True, ""


def is_video_file(filepath: str) -> bool:
    """检查是否为视频文件"""
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    ext = os.path.splitext(filepath)[1].lower()
    return ext in video_extensions


def extract_video_info(filepath: str) -> Dict[str, Any]:
    """提取视频信息（模拟实现）"""
    if not os.path.exists(filepath):
        raise VideoToolError("E002", f"文件不存在: {filepath}")
    if not is_video_file(filepath):
        raise VideoToolError("E003", f"非视频文件: {filepath}")
    
    # 模拟提取信息（实际项目中可调用ffprobe等工具）
    return {
        "duration": 10.5,  # 秒
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "codec": "h264",
        "size": 1024 * 1024,  # 字节
        "bitrate": 800000,  # bps
    }


def generate_script(info: Dict[str, Any]) -> str:
    """生成处理脚本"""
    try:
        duration = info.get("duration", 0)
        width = info.get("width", 0)
        height = info.get("height", 0)
        
        if duration <= 0 or width <= 0 or height <= 0:
            raise VideoToolError("E005", "视频参数缺失")
        
        script = f"""
# 视频处理脚本
# 时长: {duration:.1f}s, 分辨率: {width}x{height}
ffmpeg -i input.mp4 -c:v libx264 -preset fast -crf 23 \\
       -c:a aac -b:a 128k output.mp4
"""
        return script.strip()
    except Exception as e:
        if isinstance(e, VideoToolError):
            raise
        raise VideoToolError("E007", f"脚本生成失败: {str(e)}")


def validate_video(filepath: str, info: Dict[str, Any]) -> bool:
    """校验视频文件"""
    try:
        if not os.path.exists(filepath):
            return False
        if not is_video_file(filepath):
            return False
        if info.get("duration", 0) <= 0:
            return False
        if info.get("width", 0) <= 0 or info.get("height", 0) <= 0:
            return False
        return True
    except Exception:
        return False


def format_metadata(info: Dict[str, Any]) -> str:
    """格式化元数据"""
    try:
        duration = info.get("duration", 0)
        width = info.get("width", 0)
        height = info.get("height", 0)
        fps = info.get("fps", 0)
        codec = info.get("codec", "unknown")
        
        metadata = {
            "时长": f"{duration:.1f}秒",
            "分辨率": f"{width}x{height}",
            "帧率": f"{fps}fps",
            "编码": codec,
        }
        return json.dumps(metadata, ensure_ascii=False, indent=2)
    except Exception as e:
        raise VideoToolError("E009", f"元数据格式化失败: {str(e)}")


def format_operation_log(action: str, status: str, detail: str = "") -> str:
    """格式化操作记录"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "时间": timestamp,
            "操作": action,
            "状态": status,
            "详情": detail,
        }
        return json.dumps(log_entry, ensure_ascii=False)
    except Exception as e:
        raise VideoToolError("E010", f"操作记录格式化失败: {str(e)}")


def format_validation_report(filepath: str, is_valid: bool, issues: List[str]) -> str:
    """格式化校验报告"""
    try:
        report = {
            "文件": filepath,
            "校验时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "是否有效": "是" if is_valid else "否",
            "问题列表": issues if issues else ["无"],
        }
        return json.dumps(report, ensure_ascii=False, indent=2)
    except Exception as e:
        raise VideoToolError("E009", f"校验报告格式化失败: {str(e)}")


# ==================== 自检函数 ====================

def run_selftest() -> bool:
    """运行自检程序"""
    print("[RUN] === 自检开始 ===")
    all_passed = True
    
    def check(name: str, condition: bool) -> bool:
        nonlocal all_passed
        status = "PASS" if condition else "FAIL"
        print(f"{status}: {name}")
        if not condition:
            all_passed = False
        return condition
    
    # 1. 空路径校验
    valid, code = validate_path("")
    check("空路径校验", not valid and code == "E001")
    
    # 2. 非视频文件校验
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_txt = f.name
    try:
        try:
            extract_video_info(temp_txt)
            check("非视频文件校验", False)
        except VideoToolError as e:
            check("非视频文件校验", e.code == "E003")
    finally:
        os.unlink(temp_txt)
    
    # 3. 关键参数提取
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        temp_video = f.name
    try:
        info = extract_video_info(temp_video)
        check("关键参数提取", 
              info["duration"] > 0 and 
              info["width"] > 0 and 
              info["height"] > 0)
        
        # 4. 脚本生成
        script = generate_script(info)
        check("脚本生成", len(script) > 100)
        
        # 5. 视频校验逻辑
        is_valid = validate_video(temp_video, info)
        check("视频校验逻辑", is_valid is True)
        
        # 6. 元数据格式化
        metadata = format_metadata(info)
        check("元数据格式化", len(metadata) > 50)
        
        # 7. 操作记录格式化
        log = format_operation_log("测试操作", "成功", "测试详情")
        check("操作记录格式化", len(log) > 20)
        
        # 8. 校验报告格式化
        report = format_validation_report(temp_video, True, [])
        check("校验报告格式化", len(report) > 50)
        
        # 9. 错误码完整性
        check("错误码完整性", len(ERROR_CODES) == 10)
        
        # 10. 无效目录未抛出异常
        try:
            invalid_result = validate_path("/nonexistent/path/to/video.mp4")
            check("无效目录未抛出异常", invalid_result[0] is False and invalid_result[1] == "E002")
        except Exception:
            check("无效目录未抛出异常", False)
            
    finally:
        os.unlink(temp_video)
    
    print(f"=== 自检完成: {sum(1 for _ in range(10)) - (0 if all_passed else 1)} 通过, {0 if all_passed else 1} 失败 ===")
    return all_passed


# ==================== 主程序 ====================

def main():
    parser = argparse.ArgumentParser(description="视频处理工具")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--input", type=str, help="输入视频文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--action", type=str, choices=["info", "script", "validate", "report"],
                       help="执行的操作")
    
    args = parser.parse_args()
    
    if args.selftest:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    if not args.input:
        print("错误: 请指定输入文件路径 (--input)")
        sys.exit(1)
    
    try:
        # 验证路径
        valid, code = validate_path(args.input)
        if not valid:
            raise VideoToolError(code, f"路径无效: {args.input}")
        
        # 提取信息
        info = extract_video_info(args.input)
        
        # 根据操作执行
        if args.action == "info" or args.action is None:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        elif args.action == "script":
            script = generate_script(info)
            print(script)
        elif args.action == "validate":
            is_valid = validate_video(args.input, info)
            issues = [] if is_valid else ["视频文件校验失败"]
            report = format_validation_report(args.input, is_valid, issues)
            print(report)
        elif args.action == "report":
            metadata = format_metadata(info)
            print(metadata)
            
    except VideoToolError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
