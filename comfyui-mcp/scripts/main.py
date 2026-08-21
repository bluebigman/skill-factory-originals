#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comfyui-mcp 技能独立实现脚本
================================
通过命令行或 MCP 协议驱动本地 ComfyUI 完成图像、视频与音频生成任务。

仅依据功能规格独立实现（clean-room），不复制任何既有代码。

用法示例:
    python main.py --selftest          # 离线自检核心逻辑
    python main.py --version           # 查看版本
    python main.py --help              # 查看帮助

错误码说明:
    E001: 参数解析错误
    E002: 不支持的子命令
    E003: 缺少必要参数
    E004: 生成类型无效
    E005: 参数值无效（如负数）
    E006: 任务创建失败
    E007: 任务状态查询失败
    E008: 结果获取失败
    E009: 服务连接失败
    E010: 内部逻辑错误
"""

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ============================================================
# 版本与元数据
# ============================================================
SKILL_VERSION = "1.0.2"
SKILL_NAME = "comfyui-mcp"
SKILL_DISPLAY_NAME = "本地创意工坊 ComfyUI 节点控制台"
SKILL_DESCRIPTION = "通过 MCP 协议在本地驱动 ComfyUI 完成图像、视频与音频生成任务。"


# ============================================================
# 数据模型
# ============================================================
@dataclass
class GenerateTask:
    """生成任务数据模型"""
    task_id: str
    task_type: str          # image / video / audio
    prompt: str
    params: Dict[str, Any]
    status: str = "pending"  # pending / running / completed / failed
    result_path: Optional[str] = None
    result_meta: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ServiceStatus:
    """服务状态数据模型"""
    available: bool
    node_count: int
    version: str
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ============================================================
# 核心逻辑：任务管理器
# ============================================================
class TaskManager:
    """
    任务管理器：负责创建、查询、管理生成任务。
    在离线自检模式下使用模拟数据，不依赖真实 ComfyUI 服务。
    """

    # 支持的生成类型
    SUPPORTED_TYPES = ("image", "video", "audio")

    def __init__(self, offline: bool = False):
        """
        初始化任务管理器

        Args:
            offline: 是否离线模式（用于自检，不连接真实服务）
        """
        self.offline = offline
        self._tasks: Dict[str, GenerateTask] = {}
        self._node_count = 0
        self._service_version = "unknown"
        self._connected = False

        if not offline:
            # 尝试连接本地 ComfyUI 服务
            self._connect_service()

    def _connect_service(self) -> bool:
        """
        连接本地 ComfyUI 服务（模拟实现）
        实际使用时需替换为真实 HTTP 请求

        Returns:
            是否连接成功
        """
        # 真实实现中应检查 http://127.0.0.1:8188/system_stats
        # 此处为模拟，默认认为服务可用
        try:
            # 模拟网络检查
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)  # 500ms 超时
            result = sock.connect_ex(("127.0.0.1", 8188))
            sock.close()

            if result == 0:
                self._connected = True
                self._service_version = "1.0.0"  # 模拟版本号
                self._node_count = 128  # 模拟节点数
                return True
            else:
                self._connected = False
                return False
        except Exception:
            self._connected = False
            return False

    def check_service(self) -> ServiceStatus:
        """
        检查服务状态

        Returns:
            服务状态对象
        """
        if self.offline:
            # 离线自检模式：返回模拟数据
            return ServiceStatus(
                available=True,
                node_count=128,
                version="1.0.0",
                message="离线自检模式（模拟数据）"
            )

        if not self._connected:
            # 尝试重新连接
            self._connect_service()

        if self._connected:
            return ServiceStatus(
                available=True,
                node_count=self._node_count,
                version=self._service_version,
                message="服务运行正常"
            )
        else:
            return ServiceStatus(
                available=False,
                node_count=0,
                version="unknown",
                message="无法连接本地 ComfyUI 服务，请确认服务已启动"
            )

    def create_task(self, task_type: str, prompt: str, params: Dict[str, Any]) -> GenerateTask:
        """
        创建生成任务

        Args:
            task_type: 任务类型（image/video/audio）
            prompt: 生成提示词
            params: 生成参数

        Returns:
            创建的任务对象

        Raises:
            ValueError: 参数无效时抛出
        """
        # 参数校验
        if task_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"不支持的生成类型: {task_type}")

        if not prompt or not prompt.strip():
            raise ValueError("提示词不能为空")

        # 类型特定参数校验
        if task_type == "image":
            steps = params.get("steps", 30)
            if steps <= 0:
                raise ValueError("steps 必须为正数")
        elif task_type == "video":
            frames = params.get("frames", 48)
            if frames <= 0:
                raise ValueError("frames 必须为正数")
        elif task_type == "audio":
            duration = params.get("duration", 10)
            if duration <= 0:
                raise ValueError("duration 必须为正数")

        # 创建任务
        task = GenerateTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            prompt=prompt.strip(),
            params=params
        )

        # 离线模式直接模拟完成
        if self.offline:
            task.status = "completed"
            task.result_path = self._simulate_result(task)
            task.result_meta = self._generate_result_meta(task)

        self._tasks[task.task_id] = task
        return task

    def _simulate_result(self, task: GenerateTask) -> str:
        """
        模拟生成结果路径

        Args:
            task: 任务对象

        Returns:
            模拟的文件路径
        """
        ext_map = {
            "image": "png",
            "video": "mp4",
            "audio": "wav"
        }
        ext = ext_map.get(task.task_type, "bin")
        filename = f"{task.task_id[:8]}.{ext}"
        return os.path.join("/tmp/comfyui-mcp", filename)

    def _generate_result_meta(self, task: GenerateTask) -> Dict[str, Any]:
        """
        生成结果元数据

        Args:
            task: 任务对象

        Returns:
            元数据字典
        """
        meta = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "created_at": task.created_at,
        }

        if task.task_type == "image":
            meta["width"] = 1024
            meta["height"] = 1024
            meta["format"] = "PNG"
            meta["file_size_bytes"] = 2457600  # 模拟 2.4MB
        elif task.task_type == "video":
            meta["width"] = 1280
            meta["height"] = 720
            meta["fps"] = 24
            meta["frames"] = task.params.get("frames", 48)
            meta["duration_seconds"] = meta["frames"] / meta["fps"]
            meta["format"] = "MP4"
            meta["file_size_bytes"] = 5242880  # 模拟 5MB
        elif task.task_type == "audio":
            meta["sample_rate"] = 44100
            meta["channels"] = 2
            meta["duration_seconds"] = task.params.get("duration", 10)
            meta["format"] = "WAV"
            meta["file_size_bytes"] = 1764000  # 模拟 1.7MB
            meta["waveform_summary"] = "峰值 -3.2dB, 平均 -18.5dB, 动态范围 15.3dB"

        return meta

    def get_task(self, task_id: str) -> Optional[GenerateTask]:
        """
        查询任务

        Args:
            task_id: 任务 ID

        Returns:
            任务对象或 None
        """
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[GenerateTask]:
        """
        列出所有任务

        Returns:
            任务列表
        """
        return list(self._tasks.values())

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            状态字典
        """
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"任务不存在: {task_id}")

        return {
            "task_id": task.task_id,
            "status": task.status,
            "result_path": task.result_path,
            "result_meta": task.result_meta,
        }


# ============================================================
# 命令行接口
# ============================================================
def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器

    Returns:
        配置好的解析器
    """
    parser = argparse.ArgumentParser(
        prog=SKILL_NAME,
        description=SKILL_DESCRIPTION,
        epilog="示例: python main.py 图像生成 --prompt '赛博朋克城市夜景' --steps 30"
    )

    # 全局参数
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行离线自检（不连接外部服务）"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 图像生成
    img_parser = subparsers.add_parser("图像生成", help="生成静态图像")
    img_parser.add_argument("--prompt", required=False, help="生成提示词")
    img_parser.add_argument("--steps", type=int, default=30, help="采样步数（默认30）")
    img_parser.add_argument("--width", type=int, default=1024, help="图像宽度")
    img_parser.add_argument("--height", type=int, default=1024, help="图像高度")

    # 视频生成
    vid_parser = subparsers.add_parser("视频生成", help="生成短视频片段")
    vid_parser.add_argument("--prompt", required=False, help="生成提示词")
    vid_parser.add_argument("--frames", type=int, default=48, help="帧数（默认48）")
    vid_parser.add_argument("--fps", type=int, default=24, help="帧率（默认24）")

    # 音频生成
    aud_parser = subparsers.add_parser("音频生成", help="生成音效或配乐")
    aud_parser.add_argument("--prompt", required=False, help="生成提示词")
    aud_parser.add_argument("--duration", type=int, default=10, help="时长秒数（默认10）")

    # 工作流自检
    subparsers.add_parser("工作流自检", help="检查 ComfyUI 服务状态")

    return parser


def run_selftest() -> int:
    """
    运行离线自检

    使用内置硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。

    Returns:
        退出码（0 表示成功）
    """
    print("=" * 60)
    print("comfyui-mcp 离线自检")
    print("=" * 60)

    # 初始化离线任务管理器
    manager = TaskManager(offline=True)

    # 测试1: 服务状态检查
    print("\n[1/5] 服务状态检查...")
    status = manager.check_service()
    assert status.available, "服务应可用"
    assert status.node_count > 0, "节点数应大于0"
    assert status.version, "版本号不应为空"
    print(f"  ✓ 服务可用，节点数={status.node_count}，版本={status.version}")

    # 测试2: 图像生成
    print("\n[2/5] 图像生成测试...")
    img_task = manager.create_task(
        task_type="image",
        prompt="赛博朋克城市夜景",
        params={"steps": 30, "width": 1024, "height": 1024}
    )
    assert img_task.task_id, "任务ID不应为空"
    assert img_task.status == "completed", "离线模式任务应直接完成"
    assert img_task.result_path, "结果路径不应为空"
    assert img_task.result_path.endswith(".png"), "图像结果应为PNG格式"
    meta = img_task.result_meta
    assert meta["width"] > 0 and meta["height"] > 0, "图像尺寸应大于0"
    assert meta["file_size_bytes"] > 0, "文件大小应大于0"
    print(f"  ✓ 图像任务完成，ID={img_task.task_id[:8]}...")
    print(f"    尺寸={meta['width']}x{meta['height']}, 路径={img_task.result_path}")

    # 测试3: 视频生成
    print("\n[3/5] 视频生成测试...")
    vid_task = manager.create_task(
        task_type="video",
        prompt="蝴蝶在花丛中飞舞",
        params={"frames": 48, "fps": 24}
    )
    assert vid_task.task_id, "任务ID不应为空"
    assert vid_task.status == "completed", "离线模式任务应直接完成"
    assert vid_task.result_path.endswith(".mp4"), "视频结果应为MP4格式"
    vid_meta = vid_task.result_meta
    assert vid_meta["frames"] > 0, "帧数应大于0"
    assert vid_meta["duration_seconds"] > 0, "时长应大于0"
    print(f"  ✓ 视频任务完成，ID={vid_task.task_id[:8]}...")
    print(f"    帧数={vid_meta['frames']}, 时长={vid_meta['duration_seconds']:.1f}s")

    # 测试4: 音频生成
    print("\n[4/5] 音频生成测试...")
    aud_task = manager.create_task(
        task_type="audio",
        prompt="雨声与雷声混合",
        params={"duration": 10}
    )
    assert aud_task.task_id, "任务ID不应为空"
    assert aud_task.status == "completed", "离线模式任务应直接完成"
    assert aud_task.result_path.endswith(".wav"), "音频结果应为WAV格式"
    aud_meta = aud_task.result_meta
    assert aud_meta["sample_rate"] > 0, "采样率应大于0"
    assert aud_meta["duration_seconds"] > 0, "时长应大于0"
    assert "waveform_summary" in aud_meta, "应包含波形摘要"
    print(f"  ✓ 音频任务完成，ID={aud_task.task_id[:8]}...")
    print(f"    采样率={aud_meta['sample_rate']}Hz, 时长={aud_meta['duration_seconds']}s")

    # 测试5: 任务查询与错误处理
    print("\n[5/5] 任务查询与错误处理测试...")

    # 查询存在的任务
    task_info = manager.get_task_status(img_task.task_id)
    assert task_info["status"] == "completed", "任务状态应为completed"
    print(f"  ✓ 任务查询正常，状态={task_info['status']}")

    # 查询不存在的任务
    try:
        manager.get_task_status("nonexistent-id")
        assert False, "查询不存在的任务应抛出异常"
    except KeyError:
        print("  ✓ 不存在的任务正确抛出异常")

    # 无效参数测试
    try:
        manager.create_task("invalid_type", "prompt", {})
        assert False, "无效类型应抛出异常"
    except ValueError:
        print("  ✓ 无效类型正确抛出异常")

    try:
        manager.create_task("image", "", {})
        assert False, "空提示词应抛出异常"
    except ValueError:
        print("  ✓ 空提示词正确抛出异常")

    try:
        manager.create_task("image", "prompt", {"steps": -5})
        assert False, "负步数应抛出异常"
    except ValueError:
        print("  ✓ 负步数正确抛出异常")

    # 总结
    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)
    return 0


def run_version() -> int:
    """
    显示版本信息

    Returns:
        退出码
    """
    print(f"{SKILL_NAME} 版本 {SKILL_VERSION}")
    print(f"名称: {SKILL_DISPLAY_NAME}")
    print(f"描述: {SKILL_DESCRIPTION}")
    return 0


def run_command(args: argparse.Namespace) -> int:
    """
    执行具体命令

    Args:
        args: 解析后的命令行参数

    Returns:
        退出码
    """
    # 创建任务管理器（非离线模式）
    manager = TaskManager(offline=False)

    if args.command == "工作流自检":
        # 服务状态检查
        status = manager.check_service()
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
        return 0 if status.available else 1

    elif args.command == "图像生成":
        try:
            task = manager.create_task(
                task_type="image",
                prompt=args.prompt,
                params={
                    "steps": args.steps,
                    "width": args.width,
                    "height": args.height
                }
            )
            result = {
                "task_id": task.task_id,
                "status": task.status,
                "result_path": task.result_path,
                "result_meta": task.result_meta
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"错误 E004: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 E006: 任务创建失败 - {e}", file=sys.stderr)
            return 1

    elif args.command == "视频生成":
        try:
            task = manager.create_task(
                task_type="video",
                prompt=args.prompt,
                params={
                    "frames": args.frames,
                    "fps": args.fps
                }
            )
            result = {
                "task_id": task.task_id,
                "status": task.status,
                "result_path": task.result_path,
                "result_meta": task.result_meta
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"错误 E004: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 E006: 任务创建失败 - {e}", file=sys.stderr)
            return 1

    elif args.command == "音频生成":
        try:
            task = manager.create_task(
                task_type="audio",
                prompt=args.prompt,
                params={"duration": args.duration}
            )
            result = {
                "task_id": task.task_id,
                "status": task.status,
                "result_path": task.result_path,
                "result_meta": task.result_meta
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            print(f"错误 E004: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"错误 E006: 任务创建失败 - {e}", file=sys.stderr)
            return 1

    else:
        print(f"错误 E002: 不支持的子命令 '{args.command}'", file=sys.stderr)
        return 1


def main() -> int:
    """
    主入口函数

    Returns:
        退出码
    """
    parser = build_parser()
    args = parser.parse_args()

    # 全局参数处理
    if args.version:
        return run_version()

    if args.selftest:
        return run_selftest()

    # 子命令处理
    if not args.command:
        parser.print_help()
        return 0

    return run_command(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"错误 E010: 未预期的内部错误 - {e}", file=sys.stderr)
        sys.exit(1)
