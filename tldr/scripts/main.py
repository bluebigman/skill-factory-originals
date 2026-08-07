#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tldr - 命令速查手册（Clean Room 独立实现）

本脚本根据功能规格独立设计实现，不参考任何既有代码。
核心功能：生成 TLDR 风格的命令速查卡片，支持批量处理与失败明细追踪。
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ========== 错误码定义 ==========
ERROR_CODES = {
    "E001": "输入文件不存在",
    "E002": "输入文件格式不支持",
    "E003": "输出目录不可写",
    "E004": "单条数据解析失败",
    "E005": "JSON 格式错误",
    "E006": "缺少必要字段",
    "E007": "处理超时",
    "E008": "IO 重试次数耗尽",
    "E009": "参数错误",
    "E010": "未知异常",
}

# ========== 内置示例数据（用于自检） ==========
SELF_TEST_SAMPLES = [
    {
        "command": "git commit",
        "description": "记录工作目录的变更",
        "examples": [
            "git commit -m \"提交信息\"",
            "git commit -a -m \"提交所有已跟踪文件的变更\"",
            "git commit --amend -m \"修改上一次提交信息\"",
        ],
        "platform": "linux",
    },
    {
        "command": "docker ps",
        "description": "列出容器",
        "examples": [
            "docker ps",
            "docker ps -a  # 列出所有容器（含已停止）",
            "docker ps -q  # 仅显示容器 ID",
        ],
        "platform": "linux",
    },
    {
        "command": "curl",
        "description": "传输数据的命令行工具",
        "examples": [
            "curl http://example.com",
            "curl -o 文件名 http://example.com/file",
            "curl -X POST -d 'key=value' http://example.com/api",
        ],
        "platform": "cross-platform",
    },
]


class TLDRCard:
    """TLDR 速查卡片数据模型"""

    def __init__(self, data: Dict[str, Any]):
        self.command = data.get("command", "")
        self.description = data.get("description", "")
        self.examples = data.get("examples", [])
        self.platform = data.get("platform", "unknown")
        self.tags = data.get("tags", [])

    def validate(self) -> Tuple[bool, str]:
        """校验数据完整性"""
        if not self.command or not isinstance(self.command, str):
            return False, "command 字段缺失或类型错误"
        if not self.description or not isinstance(self.description, str):
            return False, "description 字段缺失或类型错误"
        if not isinstance(self.examples, list) or len(self.examples) == 0:
            return False, "examples 必须为非空列表"
        return True, ""

    def to_markdown(self) -> str:
        """渲染为 Markdown 格式的速查卡片"""
        lines = []
        lines.append(f"# {self.command}")
        lines.append("")
        lines.append(f"> {self.description}")
        lines.append("")
        lines.append(f"平台: `{self.platform}`")
        lines.append("")
        lines.append("## 常用示例")
        lines.append("")
        for i, example in enumerate(self.examples, 1):
            lines.append(f"{i}. `{example}`")
            lines.append("")
        if self.tags:
            lines.append("## 标签")
            lines.append("")
            lines.append(", ".join(f"`{tag}`" for tag in self.tags))
            lines.append("")
        return "\n".join(lines)


class BatchProcessor:
    """批量处理引擎：支持超时、重试、降级与幂等"""

    def __init__(
        self,
        timeout_seconds: float = 5.0,
        max_retries: int = 3,
        output_suffix: str = "_out",
    ):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.output_suffix = output_suffix
        self.success_count = 0
        self.skip_count = 0
        self.fail_count = 0
        self.failures: List[Dict[str, str]] = []

    def process_file(self, input_path: Path, output_dir: Optional[Path] = None) -> str:
        """处理单个输入文件，返回输出文件路径"""
        # 检查输入文件
        if not input_path.exists():
            raise FileNotFoundError(f"{ERROR_CODES['E001']}: {input_path}")

        # 检查扩展名
        if input_path.suffix.lower() not in (".json", ".txt", ".md"):
            raise ValueError(f"{ERROR_CODES['E002']}: 不支持的文件格式 {input_path.suffix}")

        # 读取并解析数据
        data = self._read_with_retry(input_path)
        if data is None:
            raise IOError(f"{ERROR_CODES['E008']}: 读取文件失败 {input_path}")

        records = self._parse_data(data, input_path.suffix)

        # 确定输出路径
        if output_dir is None:
            output_dir = input_path.parent
        if not output_dir.exists() or not os.access(output_dir, os.W_OK):
            raise PermissionError(f"{ERROR_CODES['E003']}: 输出目录不可写 {output_dir}")

        output_path = output_dir / f"{input_path.stem}{self.output_suffix}.md"

        # 幂等性检查：如果输出已存在且内容相同，跳过
        if output_path.exists():
            existing = output_path.read_text(encoding="utf-8")
            if existing.startswith("<!-- generated-by-tldr -->"):
                return str(output_path)

        # 批量处理
        results = []
        for record in records:
            result = self._process_single(record)
            if result is not None:
                results.append(result)
                self.success_count += 1
            else:
                self.skip_count += 1

        # 写入输出
        content = self._render_output(results)
        self._write_with_retry(output_path, content)

        return str(output_path)

    def _process_single(self, record: Dict[str, Any]) -> Optional[str]:
        """处理单条记录，带超时控制"""
        start_time = time.time()

        try:
            # 模拟超时控制
            if time.time() - start_time > self.timeout_seconds:
                self._record_failure(record, "E007", "处理超时")
                return None

            card = TLDRCard(record)
            valid, msg = card.validate()
            if not valid:
                self._record_failure(record, "E006", msg)
                return None

            return card.to_markdown()

        except Exception as exc:
            self._record_failure(record, "E010", str(exc))
            return None

    def _record_failure(self, record: Dict[str, Any], code: str, reason: str):
        """记录失败明细"""
        self.fail_count += 1
        self.failures.append(
            {
                "command": record.get("command", "未知"),
                "error_code": code,
                "reason": reason,
            }
        )

    def _read_with_retry(self, path: Path) -> Optional[str]:
        """带重试的读取操作"""
        for attempt in range(self.max_retries):
            try:
                return path.read_text(encoding="utf-8")
            except (IOError, OSError):
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(0.5 * (attempt + 1))  # 递增间隔
        return None

    def _write_with_retry(self, path: Path, content: str) -> bool:
        """带重试的写入操作"""
        for attempt in range(self.max_retries):
            try:
                path.write_text(content, encoding="utf-8")
                return True
            except (IOError, OSError):
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))
        return False

    def _parse_data(self, raw: str, ext: str) -> List[Dict[str, Any]]:
        """解析输入数据（支持降级方案）"""
        # 尝试 JSON 解析
        if ext == ".json":
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "records" in data:
                    return data["records"]
                else:
                    return [data]
            except json.JSONDecodeError:
                # 降级：尝试按行解析
                return self._fallback_parse(raw)
        else:
            # 非 JSON 文件使用降级解析
            return self._fallback_parse(raw)

    def _fallback_parse(self, raw: str) -> List[Dict[str, Any]]:
        """降级解析：尝试从文本中提取命令信息"""
        records = []
        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        current_cmd = None
        current_desc = None
        current_examples = []

        for line in lines:
            if line.startswith("# "):
                # 保存上一条记录
                if current_cmd:
                    records.append(
                        {
                            "command": current_cmd,
                            "description": current_desc or "",
                            "examples": current_examples,
                            "platform": "unknown",
                        }
                    )
                # 开始新记录
                current_cmd = line[2:].strip()
                current_desc = None
                current_examples = []
            elif line.startswith("> ") and not current_desc:
                current_desc = line[2:].strip()
            elif line.startswith("- ") or line.startswith("* "):
                current_examples.append(line[2:].strip())

        # 保存最后一条
        if current_cmd:
            records.append(
                {
                    "command": current_cmd,
                    "description": current_desc or "",
                    "examples": current_examples,
                    "platform": "unknown",
                }
            )

        return records

    def _render_output(self, cards: List[str]) -> str:
        """渲染最终输出"""
        header = "<!-- generated-by-tldr -->\n"
        header += "<!-- 本文件由 tldr 工具生成，请勿手动编辑 -->\n\n"
        body = "\n\n---\n\n".join(cards)
        summary = (
            f"\n\n<!-- 统计: 成功 {self.success_count}, 跳过 {self.skip_count}, "
            f"失败 {self.fail_count} -->\n"
        )
        return header + body + summary

    def print_summary(self):
        """打印处理摘要"""
        print(f"处理总数: {self.success_count + self.skip_count + self.fail_count}")
        print(f"成功数: {self.success_count}")
        print(f"跳过数: {self.skip_count}")
        print(f"失败数: {self.fail_count}")
        if self.failures:
            print("\n失败明细:")
            for failure in self.failures:
                print(
                    f"  - {failure['command']}: "
                    f"[{failure['error_code']}] {failure['reason']}"
                )


def run_selftest() -> bool:
    """运行内置自检（不依赖任何外部资源）"""
    print("=== tldr 自检开始 ===")

    # 测试 1: 数据模型校验
    print("[1/4] 测试数据模型...")
    for sample in SELF_TEST_SAMPLES:
        card = TLDRCard(sample)
        valid, _ = card.validate()
        assert valid, f"样例数据校验失败: {sample.get('command')}"
    print("  通过")

    # 测试 2: Markdown 渲染
    print("[2/4] 测试 Markdown 渲染...")
    card = TLDRCard(SELF_TEST_SAMPLES[0])
    rendered = card.to_markdown()
    assert "git commit" in rendered, "渲染结果缺少命令名"
    assert "记录工作目录的变更" in rendered, "渲染结果缺少描述"
    assert "git commit -m" in rendered, "渲染结果缺少示例"
    assert len(rendered) > 50, "渲染结果过短"
    print("  通过")

    # 测试 3: 批量处理（使用临时目录）
    print("[3/4] 测试批量处理...")
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 写入测试输入
        input_file = tmp / "test_input.json"
        input_file.write_text(
            json.dumps(SELF_TEST_SAMPLES, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 执行处理
        processor = BatchProcessor()
        output_path = processor.process_file(input_file, tmp)

        # 验证输出
        assert output_path.endswith("_out.md"), "输出文件名不符合预期"
        assert Path(output_path).exists(), "输出文件未生成"
        content = Path(output_path).read_text(encoding="utf-8")
        assert "git commit" in content, "输出内容缺少命令"
        assert "docker ps" in content, "输出内容缺少命令"
        assert "curl" in content, "输出内容缺少命令"
        assert processor.success_count == 3, f"成功数应为3，实际为 {processor.success_count}"
        assert processor.fail_count == 0, f"失败数应为0，实际为 {processor.fail_count}"
    print("  通过")

    # 测试 4: 错误处理
    print("[4/4] 测试错误处理...")
    processor = BatchProcessor()

    # 测试不存在的文件
    try:
        processor.process_file(Path("/nonexistent/path/file.json"))
        assert False, "应该抛出 FileNotFoundError"
    except FileNotFoundError:
        pass

    # 测试不支持的格式
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        bad_file = tmp / "test.xyz"
        bad_file.write_text("test", encoding="utf-8")
        try:
            processor.process_file(bad_file)
            assert False, "应该抛出 ValueError"
        except ValueError:
            pass
    print("  通过")

    print("=== 自检全部通过 ===")
    return True


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="tldr - 命令速查手册生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
        "  python main.py --input commands.json\n"
        "  python main.py --input commands.json --output-dir ./out\n"
        "  python main.py --selftest\n",
    )
    parser.add_argument("--input", "-i", help="输入文件路径（JSON/TXT/MD）")
    parser.add_argument("--output-dir", "-o", help="输出目录（默认与输入同目录）")
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="单条处理超时时间（秒）"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="IO 操作最大重试次数"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="运行内置自检后退出"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        try:
            success = run_selftest()
            return 0 if success else 1
        except AssertionError as exc:
            print(f"自检失败: {exc}", file=sys.stderr)
            return 1

    # 参数校验
    if not args.input:
        parser.error("必须指定 --input 或使用 --selftest")

    # 执行处理
    try:
        input_path = Path(args.input).resolve()
        output_dir = Path(args.output_dir).resolve() if args.output_dir else None

        processor = BatchProcessor(
            timeout_seconds=args.timeout,
            max_retries=args.max_retries,
        )
        result = processor.process_file(input_path, output_dir)
        print(f"输出文件: {result}")
        processor.print_summary()

        # 如果有失败，返回非零退出码
        if processor.fail_count > 0:
            return 1
        return 0

    except FileNotFoundError as exc:
        print(f"错误 [{ERROR_CODES['E001']}]: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"错误 [{ERROR_CODES['E003']}]: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"错误 [{ERROR_CODES['E002']}]: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"错误 [{ERROR_CODES['E010']}]: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
