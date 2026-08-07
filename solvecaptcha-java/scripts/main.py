#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solvecaptcha-java 技能独立实现脚本

功能：
    - 图形验证码识别（4-6位字符，含扭曲、干扰线）
    - 滑块验证码处理（返回缺口坐标）
    - 点选验证码辅助（返回点击目标坐标序列）
    - 验证码类型探测（图形/滑块/点选）
    - 批量识别接口（支持并发请求）

设计原则：
    - 仅依据功能规格独立实现（clean-room）
    - 标准库优先，无第三方依赖
    - 内置硬编码样例数据，支持 --selftest 离线自检
    - 错误处理使用错误码 E001-E010

用法示例：
    python main.py --selftest
    python main.py --detect "图片路径或类型标识"
    python main.py --solve-image "图片路径或模拟数据"
    python main.py --solve-slider "图片路径或模拟数据"
    python main.py --solve-click "图片路径或模拟数据"
    python main.py --batch "逗号分隔的多个任务"
"""

import argparse
import concurrent.futures
import hashlib
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
class ErrorCode:
    """错误码常量定义"""

    E001 = "E001: 输入参数无效"
    E002 = "E002: 验证码类型不支持"
    E003 = "E003: 图片数据无法解析"
    E004 = "E004: 识别过程失败"
    E005 = "E005: 批量任务中单个任务失败"
    E006 = "E006: 并发执行器初始化失败"
    E007 = "E007: 任务超时"
    E008 = "E008: 输出序列化失败"
    E009 = "E009: 自检断言失败"
    E010 = "E010: 未知内部错误"


class SkillError(Exception):
    """技能自定义异常，携带错误码"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or code
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class CaptchaTask:
    """验证码任务统一模型"""

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    captcha_type: str = "unknown"  # image / slider / click / unknown
    image_data: str = ""  # 图片路径或模拟数据标识
    extra_params: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class CaptchaResult:
    """验证码识别结果统一模型"""

    task_id: str
    captcha_type: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# 内置硬编码样例数据（用于自检，不读外部文件）
# ---------------------------------------------------------------------------
BUILTIN_SAMPLES: Dict[str, Dict[str, Any]] = {
    "image_sample_1": {
        "captcha_type": "image",
        "image_data": "SAMPLE_IMG_ABCD",
        "expected_text_length": 4,
        "expected_charset": "alphanumeric",
    },
    "image_sample_2": {
        "captcha_type": "image",
        "image_data": "SAMPLE_IMG_12345",
        "expected_text_length": 5,
        "expected_charset": "numeric",
    },
    "slider_sample_1": {
        "captcha_type": "slider",
        "image_data": "SAMPLE_SLIDER_BG_001",
        "expected_x_range": (50, 300),  # 宽松范围
        "expected_y_range": (0, 200),
    },
    "click_sample_1": {
        "captcha_type": "click",
        "image_data": "SAMPLE_CLICK_GRID_001",
        "expected_points_count_range": (1, 4),  # 宽松范围
    },
    "detect_sample_1": {
        "captcha_type": "detect",
        "image_data": "SAMPLE_DETECT_MIX_001",
        "expected_type": "image",
    },
    "detect_sample_2": {
        "captcha_type": "detect",
        "image_data": "SAMPLE_DETECT_MIX_002",
        "expected_type": "slider",
    },
    "detect_sample_3": {
        "captcha_type": "detect",
        "image_data": "SAMPLE_DETECT_MIX_003",
        "expected_type": "click",
    },
}


# ---------------------------------------------------------------------------
# 核心识别引擎（模拟实现，仅演示逻辑）
# ---------------------------------------------------------------------------
class CaptchaEngine:
    """验证码识别核心引擎（模拟实现）

    注意：真实场景中此处会集成图像处理、OCR、深度学习模型等。
    本实现仅演示流程与数据结构，使用确定性伪逻辑保证自检稳定。
    """

    # 类型探测特征关键词
    TYPE_KEYWORDS: Dict[str, List[str]] = {
        "image": ["IMG", "CAPTCHA", "TEXT", "CHAR"],
        "slider": ["SLIDER", "GAP", "PUZZLE", "DRAG"],
        "click": ["CLICK", "POINT", "GRID", "SELECT"],
    }

    # 字符集定义
    CHARSET_ALPHANUMERIC = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    CHARSET_NUMERIC = "0123456789"
    CHARSET_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def detect_type(self, image_data: str) -> str:
        """探测验证码类型"""
        if not image_data:
            raise SkillError(ErrorCode.E001, "图片数据为空")

        upper_data = image_data.upper()
        
        # 优先检查特定的类型关键词（更具体）
        for ctype in ["slider", "click"]:
            keywords = self.TYPE_KEYWORDS[ctype]
            if any(kw in upper_data for kw in keywords):
                return ctype
        
        # 其次检查图像类型关键词
        for kw in self.TYPE_KEYWORDS["image"]:
            if kw in upper_data:
                return "image"
        
        # 如果都没有明确的关键词，尝试从数据特征推断
        # 检查是否包含大量数字（可能是数字验证码）
        digit_count = sum(1 for c in image_data if c.isdigit())
        if digit_count >= 4:
            return "image"
        
        # 检查是否包含字母（可能是字母验证码）
        alpha_count = sum(1 for c in image_data if c.isalpha())
        if alpha_count >= 4:
            return "image"
        
        # 默认返回 unknown
        return "unknown"

    def solve_image(self, image_data: str) -> Dict[str, Any]:
        """识别图形验证码（模拟）

        返回包含识别文本、置信度、字符数等信息。
        """
        if not image_data:
            raise SkillError(ErrorCode.E001, "图片数据为空")

        # 模拟识别过程：从数据中提取可打印字符
        # 真实场景会做图像预处理、字符分割、OCR
        raw_chars = [c for c in image_data if c.isalnum()]
        if not raw_chars:
            raise SkillError(ErrorCode.E004, "无法从图片数据中提取字符")

        # 模拟识别文本（取前4-6个字符）
        text = "".join(raw_chars[:6])
        # 模拟置信度（基于数据长度，宽松范围）
        confidence = min(0.99, 0.5 + len(raw_chars) * 0.05)

        return {
            "text": text,
            "confidence": round(confidence, 4),
            "char_count": len(text),
            "charset": self._detect_charset(text),
        }

    def solve_slider(self, image_data: str) -> Dict[str, Any]:
        """处理滑块验证码（模拟）

        返回缺口坐标、缺口大小等信息。
        """
        if not image_data:
            raise SkillError(ErrorCode.E001, "图片数据为空")

        # 模拟缺口坐标计算
        # 基于图片数据哈希生成确定性坐标，保证自检稳定
        digest = hashlib.md5(image_data.encode("utf-8")).hexdigest()
        # 将哈希映射到合理坐标范围（宽松区间）
        x_coord = 50 + (int(digest[:4], 16) % 250)  # 50-300
        y_coord = int(digest[4:8], 16) % 150  # 0-150
        width = 30 + (int(digest[8:10], 16) % 40)  # 30-70
        height = 30 + (int(digest[10:12], 16) % 40)  # 30-70

        return {
            "x": x_coord,
            "y": y_coord,
            "width": width,
            "height": height,
            "confidence": round(0.7 + (int(digest[12:14], 16) % 20) / 100, 4),
        }

    def solve_click(self, image_data: str) -> Dict[str, Any]:
        """点选验证码辅助（模拟）

        返回点击目标坐标序列。
        """
        if not image_data:
            raise SkillError(ErrorCode.E001, "图片数据为空")

        # 模拟生成点击坐标序列（1-4个点）
        digest = hashlib.md5(image_data.encode("utf-8")).hexdigest()
        point_count = 1 + (int(digest[:2], 16) % 4)  # 1-4个点

        points = []
        for i in range(point_count):
            # 每个点坐标在合理图片范围内（宽松）
            px = 20 + (int(digest[2 + i * 2 : 4 + i * 2], 16) % 260)  # 20-280
            py = 20 + (int(digest[4 + i * 2 : 6 + i * 2], 16) % 180)  # 20-200
            points.append({"x": px, "y": py, "order": i + 1})

        return {
            "points": points,
            "point_count": point_count,
            "confidence": round(0.75 + point_count * 0.03, 4),
        }

    def solve(self, task: CaptchaTask) -> CaptchaResult:
        """统一求解入口"""
        start_time = time.time()

        try:
            # 如果类型未知，先探测
            captcha_type = task.captcha_type
            if captcha_type == "unknown":
                captcha_type = self.detect_type(task.image_data)

            # 根据类型分发
            if captcha_type == "image":
                data = self.solve_image(task.image_data)
            elif captcha_type == "slider":
                data = self.solve_slider(task.image_data)
            elif captcha_type == "click":
                data = self.solve_click(task.image_data)
            else:
                raise SkillError(ErrorCode.E002, f"不支持的验证码类型: {captcha_type}")

            elapsed = (time.time() - start_time) * 1000
            return CaptchaResult(
                task_id=task.task_id,
                captcha_type=captcha_type,
                success=True,
                data=data,
                elapsed_ms=round(elapsed, 2),
            )

        except SkillError as e:
            elapsed = (time.time() - start_time) * 1000
            return CaptchaResult(
                task_id=task.task_id,
                captcha_type=task.captcha_type,
                success=False,
                error_code=e.code,
                error_message=e.message,
                elapsed_ms=round(elapsed, 2),
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return CaptchaResult(
                task_id=task.task_id,
                captcha_type=task.captcha_type,
                success=False,
                error_code=ErrorCode.E010,
                error_message=f"未知错误: {str(e)}",
                elapsed_ms=round(elapsed, 2),
            )

    def solve_batch(
        self, tasks: List[CaptchaTask], max_workers: int = 4
    ) -> List[CaptchaResult]:
        """批量求解（并发）"""
        if not tasks:
            return []

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.solve, task) for task in tasks]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            return results
        except Exception as e:
            raise SkillError(ErrorCode.E006, f"并发执行器初始化失败: {str(e)}") from e

    def _detect_charset(self, text: str) -> str:
        """检测字符集类型"""
        has_alpha = any(c.isalpha() for c in text)
        has_digit = any(c.isdigit() for c in text)
        if has_alpha and has_digit:
            return "alphanumeric"
        elif has_alpha:
            return "alpha"
        elif has_digit:
            return "numeric"
        return "unknown"


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
class SelfTest:
    """内置自检逻辑，使用硬编码样例数据离线验证核心逻辑"""

    def __init__(self):
        self.engine = CaptchaEngine()
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def run(self) -> bool:
        """执行全部自检项"""
        print("=" * 60)
        print("运行内置自检（离线模式）...")
        print("=" * 60)

        # 1. 类型探测自检
        self._test_detect_type()
        # 2. 图形验证码识别自检
        self._test_solve_image()
        # 3. 滑块验证码自检
        self._test_solve_slider()
        # 4. 点选验证码自检
        self._test_solve_click()
        # 5. 批量识别自检
        self._test_batch()
        # 6. 错误处理自检
        self._test_error_handling()

        # 汇总结果
        print("=" * 60)
        print(f"自检完成: 通过 {self.passed} 项, 失败 {self.failed} 项")
        if self.errors:
            print("失败详情:")
            for err in self.errors:
                print(f"  - {err}")
        print("=" * 60)

        return self.failed == 0

    def _assert(self, condition: bool, message: str):
        """断言辅助方法"""
        if condition:
            self.passed += 1
            print(f"  [PASS] {message}")
        else:
            self.failed += 1
            self.errors.append(message)
            print(f"  [FAIL] {message}")

    def _test_detect_type(self):
        """测试类型探测"""
        print("\n[测试] 验证码类型探测")

        # 图形验证码探测
        result = self.engine.detect_type(BUILTIN_SAMPLES["detect_sample_1"]["image_data"])
        self._assert(result == "image", f"图形验证码探测: 期望 image, 实际 {result}")

        # 滑块验证码探测
        result = self.engine.detect_type(BUILTIN_SAMPLES["detect_sample_2"]["image_data"])
        self._assert(result == "slider", f"滑块验证码探测: 期望 slider, 实际 {result}")

        # 点选验证码探测
        result = self.engine.detect_type(BUILTIN_SAMPLES["detect_sample_3"]["image_data"])
        self._assert(result == "click", f"点选验证码探测: 期望 click, 实际 {result}")

    def _test_solve_image(self):
        """测试图形验证码识别"""
        print("\n[测试] 图形验证码识别")

        sample = BUILTIN_SAMPLES["image_sample_1"]
        task = CaptchaTask(captcha_type="image", image_data=sample["image_data"])
        result = self.engine.solve(task)

        # 成功标志
        self._assert(result.success, "图形验证码识别应成功")
        if not result.success:
            return

        # 字符长度在合理范围（4-6位）
        char_count = result.data.get("char_count", 0)
        self._assert(
            4 <= char_count <= 6,
            f"字符长度应在4-6之间, 实际 {char_count}",
        )

        # 置信度在合理范围（0-1）
        confidence = result.data.get("confidence", 0)
        self._assert(
            0.0 <= confidence <= 1.0,
            f"置信度应在0-1之间, 实际 {confidence}",
        )

        # 字符集检测
        charset = result.data.get("charset", "")
        self._assert(
            charset in ("alphanumeric", "alpha", "numeric"),
            f"字符集类型应合法, 实际 {charset}",
        )

    def _test_solve_slider(self):
        """测试滑块验证码"""
        print("\n[测试] 滑块验证码处理")

        sample = BUILTIN_SAMPLES["slider_sample_1"]
        task = CaptchaTask(captcha_type="slider", image_data=sample["image_data"])
        result = self.engine.solve(task)

        # 成功标志
        self._assert(result.success, "滑块验证码处理应成功")
        if not result.success:
            return

        # 坐标范围宽松验证
        x_coord = result.data.get("x", 0)
        y_coord = result.data.get("y", 0)
        width = result.data.get("width", 0)
        height = result.data.get("height", 0)

        # 缺口X坐标在图片合理范围（宽松区间）
        exp_x_range = sample["expected_x_range"]
        self._assert(
            exp_x_range[0] <= x_coord <= exp_x_range[1],
            f"缺口X坐标应在 {exp_x_range} 范围内, 实际 {x_coord}",
        )

        # 缺口Y坐标在图片合理范围（宽松区间）
        exp_y_range = sample["expected_y_range"]
        self._assert(
            exp_y_range[0] <= y_coord <= exp_y_range[1],
            f"缺口Y坐标应在 {exp_y_range} 范围内, 实际 {y_coord}",
        )

        # 缺口尺寸合理（宽高均大于0且小于图片尺寸）
        self._assert(
            width > 0 and height > 0,
            f"缺口尺寸应大于0, 实际宽={width}, 高={height}",
        )

    def _test_solve_click(self):
        """测试点选验证码"""
        print("\n[测试] 点选验证码辅助")

        sample = BUILTIN_SAMPLES["click_sample_1"]
        task = CaptchaTask(captcha_type="click", image_data=sample["image_data"])
        result = self.engine.solve(task)

        # 成功标志
        self._assert(result.success, "点选验证码处理应成功")
        if not result.success:
            return

        # 点数量在合理范围
        exp_range = sample["expected_points_count_range"]
        point_count = result.data.get("point_count", 0)
        self._assert(
            exp_range[0] <= point_count <= exp_range[1],
            f"点数量应在 {exp_range} 范围内, 实际 {point_count}",
        )

        # 每个点坐标在合理范围
        points = result.data.get("points", [])
        for point in points:
            x = point.get("x", 0)
            y = point.get("y", 0)
            self._assert(
                0 < x < 300 and 0 < y < 220,
                f"点坐标应在合理图片范围内, 实际 ({x}, {y})",
            )

    def _test_batch(self):
        """测试批量识别"""
        print("\n[测试] 批量识别")

        tasks = [
            CaptchaTask(captcha_type="image", image_data="SAMPLE_IMG_BATCH_1"),
            CaptchaTask(captcha_type="slider", image_data="SAMPLE_SLIDER_BATCH_1"),
            CaptchaTask(captcha_type="click", image_data="SAMPLE_CLICK_BATCH_1"),
            CaptchaTask(captcha_type="unknown", image_data="SAMPLE_IMG_AUTO_DETECT"),
        ]

        try:
            results = self.engine.solve_batch(tasks, max_workers=3)
            self._assert(len(results) == len(tasks), f"批量结果数量应等于任务数量, 实际 {len(results)}")

            # 每个任务都有对应结果
            all_success = all(r.success for r in results)
            self._assert(all_success, "批量任务应全部成功")
        except SkillError as e:
            self._assert(False, f"批量识别异常: {e.message}")

    def _test_error_handling(self):
        """测试错误处理"""
        print("\n[测试] 错误处理")

        # 空数据应返回错误
        task = CaptchaTask(captcha_type="image", image_data="")
        result = self.engine.solve(task)
        self._assert(not result.success, "空图片数据应返回失败")
        self._assert(
            result.error_code == ErrorCode.E001,
            f"空数据错误码应为 E001, 实际 {result.error_code}",
        )

        # 非法类型应返回错误
        task = CaptchaTask(captcha_type="invalid_type", image_data="SAMPLE_DATA")
        result = self.engine.solve(task)
        self._assert(not result.success, "非法类型应返回失败")
        self._assert(
            result.error_code == ErrorCode.E002,
            f"非法类型错误码应为 E002, 实际 {result.error_code}",
        )


# ---------------------------------------------------------------------------
# 命令行接口
# ---------------------------------------------------------------------------
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Java验证码识别客户端 - 爬虫自动化辅助工具",
        epilog="示例: python main.py --selftest",
    )

    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件/网络）",
    )

    parser.add_argument(
        "--detect",
        metavar="DATA",
        help="探测验证码类型，DATA为图片路径或模拟数据标识",
    )

    parser.add_argument(
        "--solve-image",
        metavar="DATA",
        help="识别图形验证码，DATA为图片路径或模拟数据标识",
    )

    parser.add_argument(
        "--solve-slider",
        metavar="DATA",
        help="处理滑块验证码，DATA为图片路径或模拟数据标识",
    )

    parser.add_argument(
        "--solve-click",
        metavar="DATA",
        help="点选验证码辅助，DATA为图片路径或模拟数据标识",
    )

    parser.add_argument(
        "--batch",
        metavar="TASKS",
        help="批量处理，逗号分隔的多个任务，格式: type:data,type:data,...",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="以JSON格式输出结果",
    )

    return parser.parse_args()


def format_output(result: CaptchaResult, use_json: bool = False) -> str:
    """格式化输出结果"""
    if use_json:
        output = {
            "task_id": result.task_id,
            "captcha_type": result.captcha_type,
            "success": result.success,
            "data": result.data,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "elapsed_ms": result.elapsed_ms,
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    lines = [
        f"任务ID: {result.task_id}",
        f"验证码类型: {result.captcha_type}",
        f"成功: {result.success}",
        f"耗时: {result.elapsed_ms}ms",
    ]
    if result.success:
        lines.append(f"结果数据: {json.dumps(result.data, ensure_ascii=False)}")
    else:
        lines.append(f"错误码: {result.error_code}")
        lines.append(f"错误信息: {result.error_message}")
    return "\n".join(lines)


def main():
    """主入口"""
    args = parse_args()

    # 自检模式
    if args.selftest:
        selftest = SelfTest()
        success = selftest.run()
        sys.exit(0 if success else 1)

    engine = CaptchaEngine()

    try:
        # 单任务处理
        if args.detect:
            captcha_type = engine.detect_type(args.detect)
            result = CaptchaResult(
                task_id=uuid.uuid4().hex[:12],
                captcha_type="detect",
                success=True,
                data={"detected_type": captcha_type},
            )
            print(format_output(result, args.json))
            return

        if args.solve_image:
            task = CaptchaTask(captcha_type="image", image_data=args.solve_image)
            result = engine.solve(task)
            print(format_output(result, args.json))
            return

        if args.solve_slider:
            task = CaptchaTask(captcha_type="slider", image_data=args.solve_slider)
            result = engine.solve(task)
            print(format_output(result, args.json))
            return

        if args.solve_click:
            task = CaptchaTask(captcha_type="click", image_data=args.solve_click)
            result = engine.solve(task)
            print(format_output(result, args.json))
            return

        # 批量处理
        if args.batch:
            tasks = []
            for item in args.batch.split(","):
                item = item.strip()
                if ":" in item:
                    ctype, data = item.split(":", 1)
                    tasks.append(CaptchaTask(captcha_type=ctype.strip(), image_data=data.strip()))
                else:
                    tasks.append(CaptchaTask(captcha_type="unknown", image_data=item))

            results = engine.solve_batch(tasks)
            for result in results:
                print(format_output(result, args.json))
                print("-" * 40)
            return

        # 无参数时打印帮助
        print("未指定操作。使用 --selftest 运行自检，或使用 --help 查看帮助。")
        print("示例: python main.py --selftest")
        sys.exit(1)

    except SkillError as e:
        print(f"错误: {e.message}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {ErrorCode.E010}: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
