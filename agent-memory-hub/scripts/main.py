#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent-memory-hub 技能独立实现

将对话、文档、代码、决策整理为四类标准化记忆资产，并生成团队共享索引。
本脚本为 clean-room 实现，仅依据功能规格独立编写。

用法示例:
    python scripts/main.py --input ./docs --output ./memory_assets
    python scripts/main.py --selftest
"""

from __future__ import annotations
dry_run = False  # v3.274 模块级 dry-run 标志

import argparse
import json
import re
import sys
import tempfile
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入路径不存在或不可访问",
    "E002": "输出目录创建失败",
    "E003": "输入文件读取失败",
    "E004": "输入文件格式不支持",
    "E005": "资产条目生成失败",
    "E006": "索引文件写入失败",
    "E007": "参数解析失败",
    "E008": "内部逻辑错误（未知资产类型）",
    "E009": "批量处理超过上限（20 份）",
    "E010": "自检失败",
}


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def fail(code: str, context: str = "") -> None:
    """输出错误信息并退出。"""
    msg = ERROR_CODES.get(code, "未知错误")
    if context:
        msg = f"{msg} | {context}"
    print(f"[ERROR] {code}: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class MemoryAsset:
    """单一记忆资产条目。"""

    asset_id: str                # 唯一标识
    asset_type: str              # dialogue | document | code | decision
    title: str                   # 标题
    source: str                  # 来源路径或标识
    content_summary: str         # 内容摘要
    keywords: List[str]          # 关键词列表
    created_at: str              # 创建时间（ISO8601 UTC）
    metadata: Dict[str, str] = field(default_factory=dict)  # 附加元数据


@dataclass
class ProcessResult:
    """单份材料的处理结果。"""

    source: str
    asset: Optional[MemoryAsset]
    error: Optional[str] = None


@dataclass
class IndexRecord:
    """索引文件中的一条记录。"""

    asset_id: str
    asset_type: str
    title: str
    source: str
    created_at: str


# ---------------------------------------------------------------------------
# 核心工具函数
# ---------------------------------------------------------------------------
def _generate_asset_id(source: str, asset_type: str, seq: int) -> str:
    """根据来源、类型和序号生成稳定的资产 ID。"""
    import hashlib
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:8]
    type_map = {
        "dialogue": "dia",
        "document": "doc",
        "code": "cod",
        "decision": "dec",
    }
    prefix = type_map.get(asset_type, "doc")
    return f"{prefix}-{digest}-{seq:04d}"


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO8601 字符串。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_keywords(text: str, limit: int = 5) -> List[str]:
    """从文本中提取关键词。"""
    stopwords = {
        "the", "and", "for", "with", "that", "this", "are", "was",
        "were", "have", "has", "had", "not", "but", "you", "your",
        "from", "they", "will", "would", "can", "could", "should",
        "一个", "我们", "你们", "他们", "这个", "那个", "可以", "没有",
        "以及", "或者", "但是", "因为", "所以", "如果", "就是",
    }

    # 提取英文单词
    words_en = re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower())
    # 提取中文词组
    words_cn = re.findall(r"[\u4e00-\u9fff]{2,4}", text)

    all_words = words_en + words_cn
    filtered = [w for w in all_words if w not in stopwords and len(w) >= 2]

    # 按词频统计
    freq: Dict[str, int] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1

    # 按频率降序，取前 limit 个
    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words[:limit]]


def _guess_asset_type(filename: str, content: str = "") -> str:
    """根据文件名和内容猜测资产类型。"""
    name = filename.lower()

    # 代码文件
    code_exts = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php", ".sh"}
    if Path(name).suffix in code_exts:
        return "code"

    # 文档文件
    doc_exts = {".md", ".txt", ".rst", ".doc", ".docx", ".pdf"}
    if Path(name).suffix in doc_exts:
        # 检查是否为对话或决策类型
        if "对话" in name or "chat" in name or "conversation" in name:
            return "dialogue"
        if "决策" in name or "decision" in name or "adr" in name:
            return "decision"
        return "document"

    # 根据内容关键词猜测
    if content:
        if any(k in content for k in ["决策", "决定", "方案选型", "decision"]):
            return "decision"
        if any(k in content for k in ["对话", "用户说", "assistant:", "human:"]):
            return "dialogue"
        if any(k in content for k in ["def ", "class ", "function ", "import ", "from "]):
            return "code"

    # 默认按文档处理
    return "document"


def _read_text_file(path: Path) -> Tuple[str, Optional[str]]:
    """读取文本文件，返回 (内容, 错误码或 None)。"""
    try:
        # 尝试多种编码
        for encoding in ["utf-8", "gbk", "latin-1"]:
            try:
                return path.read_text(encoding=encoding), None
            except UnicodeDecodeError:
                continue
        return "", "E003"
    except Exception:
        return "", "E003"


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class MemoryHubProcessor:
    """记忆资产处理器。"""

    BATCH_LIMIT = 20

    def __init__(self, output_dir: str = "./memory_assets"):
        self.output_dir = Path(output_dir)

    def process_file(self, file_path: Path, seq: int) -> ProcessResult:
        """处理单个文件，生成记忆资产条目。"""
        source = str(file_path)

        try:
            # 读取文件内容
            content, err = _read_text_file(file_path)
            if err:
                return ProcessResult(source=source, asset=None, error=f"读取失败: {err}")

            if not content.strip():
                # 空文件不生成资产
                return ProcessResult(source=source, asset=None, error="空文件")

            # 猜测资产类型
            asset_type = _guess_asset_type(file_path.name, content)

            # 提取标题
            first_line = ""
            for line in content.splitlines():
                line = line.strip().strip("#").strip()
                if line:
                    first_line = line[:80]
                    break
            title = first_line if first_line else file_path.stem

            # 生成摘要
            summary = content.strip()[:200].replace("\n", " ").replace("\r", " ")

            # 提取关键词
            keywords = _extract_keywords(content)

            # 构建资产
            asset = MemoryAsset(
                asset_id=_generate_asset_id(source, asset_type, seq),
                asset_type=asset_type,
                title=title,
                source=source,
                content_summary=summary,
                keywords=keywords,
                created_at=_now_iso(),
                metadata={
                    "file_size": str(file_path.stat().st_size),
                    "file_name": file_path.name,
                },
            )
            return ProcessResult(source=source, asset=asset, error=None)
        except Exception as e:
            return ProcessResult(source=source, asset=None, error=f"处理异常: {str(e)}")

    def process_directory(self, input_dir: str) -> List[ProcessResult]:
        """处理目录下的所有支持文件。"""
        in_path = Path(input_dir)
        if not in_path.exists() or not in_path.is_dir():
            fail("E001", f"路径: {input_dir}")

        # 收集支持的文件
        supported_exts = {
            ".md", ".txt", ".rst", ".doc", ".docx", ".pdf",
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h",
            ".go", ".rs", ".rb", ".php", ".sh",
        }
        files = [p for p in in_path.rglob("*") if p.is_file() and p.suffix.lower() in supported_exts]

        # 批量上限检查
        if len(files) > self.BATCH_LIMIT:
            fail("E009", f"发现 {len(files)} 份材料，超过上限 {self.BATCH_LIMIT}")

        results: List[ProcessResult] = []
        for i, f in enumerate(sorted(files), start=1):
            results.append(self.process_file(f, i))
        return results

    def process_single_file(self, input_file: str) -> List[ProcessResult]:
        """处理单个文件。"""
        f = Path(input_file)
        if not f.exists() or not f.is_file():
            fail("E001", f"路径: {input_file}")
        if f.suffix.lower() not in {
            ".md", ".txt", ".rst", ".doc", ".docx", ".pdf",
            ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h",
            ".go", ".rs", ".rb", ".php", ".sh",
        }:
            fail("E004", f"不支持的文件格式: {f.suffix}")

        return [self.process_file(f, 1)]

    def write_assets(self, results: List[ProcessResult]) -> List[Path]:
        """将资产写入输出目录，返回写入的文件路径列表。"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            fail("E002", f"目录: {self.output_dir}, 错误: {str(e)}")

        written: List[Path] = []
        for r in results:
            if r.asset is None:
                continue

            # 按类型分目录存放
            type_dir = self.output_dir / r.asset.asset_type
            try:
                type_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                fail("E002", f"目录: {type_dir}, 错误: {str(e)}")

            # 文件名：资产ID.json
            file_path = type_dir / f"{r.asset.asset_id}.json"
            try:
                if not dry_run or getattr(args, "force", False):
                    file_path.write_text(
                    json.dumps(asdict(r.asset), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                written.append(file_path)
            except Exception as e:
                fail("E005", f"文件: {file_path}, 错误: {str(e)}")

        return written

    def write_index(self, results: List[ProcessResult]) -> Path:
        """生成团队共享索引文件。"""
        records: List[IndexRecord] = []
        for r in results:
            if r.asset is None:
                continue
            records.append(
                IndexRecord(
                    asset_id=r.asset.asset_id,
                    asset_type=r.asset.asset_type,
                    title=r.asset.title,
                    source=r.asset.source,
                    created_at=r.asset.created_at,
                )
            )

        index_data = {
            "schema_version": "1.0",
            "generated_at": _now_iso(),
            "total_assets": len(records),
            "assets": [asdict(rec) for rec in records],
        }

        index_path = self.output_dir / "INDEX.json"
        try:
            if not dry_run or getattr(args, "force", False):
                index_path.write_text(
                json.dumps(index_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            fail("E006", f"文件: {index_path}, 错误: {str(e)}")

        return index_path


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    """内置硬编码样例数据，离线自检核心逻辑。"""
    print("[SELFTEST] 开始自检...")
    
    tmp_dir = None
    try:
        # 创建临时目录
        tmp_dir = tempfile.mkdtemp(prefix="agent_memory_hub_selftest_")
        tmp = Path(tmp_dir)

        # 构造测试文件
        test_files = {
            "conversation.md": "# 客户对话记录\n用户: 我们需要一个知识库系统\n助手: 建议使用四类资产模型\n用户: 好的，请提供方案\n",
            "api_design.py": "# API 设计\nimport requests\n\ndef fetch_data(url):\n    resp = requests.get(url)\n    return resp.json()\n",
            "architecture_decision.md": "# ADR-001: 数据库选型\n## 决策\n选用 PostgreSQL 作为主数据库\n## 理由\n稳定可靠，支持 JSON 类型\n",
            "README.md": "# 项目说明\n这是一个示例项目，用于演示记忆资产整理功能\n",
        }

        for name, content in test_files.items():
            file_path = tmp / name
            if not dry_run or getattr(args, "force", False):
                file_path.write_text(content, encoding="utf-8")

        # 创建处理器
        out_dir = tmp / "out"
        processor = MemoryHubProcessor(output_dir=str(out_dir))

        # 处理目录
        results = processor.process_directory(str(tmp))
        print(f"[SELFTEST] 处理完成，共 {len(results)} 份材料")

        # 统计结果
        assets = [r.asset for r in results if r.asset is not None]
        errors = [r for r in results if r.asset is None]
        
        if errors:
            print(f"[SELFTEST] 警告: {len(errors)} 份材料处理失败")
            for e in errors:
                print(f"  - {e.source}: {e.error}")

        # 基本断言
        assert len(results) == 4, f"处理结果数量异常，期望 4，实际 {len(results)}"
        assert len(assets) >= 3, f"成功生成的资产数量过少: {len(assets)}"

        # 检查资产类型覆盖
        types = {a.asset_type for a in assets}
        print(f"[SELFTEST] 资产类型: {types}")
        assert len(types) >= 3, f"资产类型覆盖不足: {types}"

        # 检查资产 ID 格式
        for a in assets:
            pattern = r"^(dia|doc|cod|dec)-[0-9a-f]{8}-\d{4}$"
            assert re.match(pattern, a.asset_id), f"资产 ID 格式错误: {a.asset_id}"

        # 写入资产文件
        written = processor.write_assets(results)
        assert len(written) >= 3, f"写入资产文件数量过少: {len(written)}"
        print(f"[SELFTEST] 写入 {len(written)} 个资产文件")

        # 写入索引
        index_path = processor.write_index(results)
        assert index_path.exists(), "索引文件未生成"

        # 验证索引内容
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        assert index_data["total_assets"] >= 3, "索引中资产数量过少"
        assert len(index_data["assets"]) >= 3, "索引记录数量过少"
        print(f"[SELFTEST] 索引文件验证通过，共 {index_data['total_assets']} 条记录")

        # 验证资产文件内容
        for a in assets:
            asset_file = out_dir / a.asset_type / f"{a.asset_id}.json"
            if asset_file.exists():
                data = json.loads(asset_file.read_text(encoding="utf-8"))
                assert data["asset_id"] == a.asset_id, "资产文件内容不一致"

        # 测试错误处理
        try:
            processor.process_single_file(str(tmp / "nonexistent.txt"))
            assert False, "应抛出 E001 错误"
        except SystemExit as e:
            assert e.code != 0, "错误退出码应为非零"

        print(f"[SELFTEST] 全部断言通过（共处理 {len(results)} 份材料，生成 {len(assets)} 条资产）")
        return 0

    except AssertionError as e:
        print(f"[SELFTEST] 断言失败: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"[SELFTEST] 未预期异常: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        # 清理临时目录
        if tmp_dir:
            import shutil
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception as e:
                print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数。"""
    parser = argparse.ArgumentParser(
        description="agent-memory-hub: 将对话、文档、代码整理为四类记忆资产，生成团队共享索引",
        epilog="示例: python scripts/main.py --input ./docs --output ./memory_assets",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入文件或目录路径",
    )
    parser.add_argument(
        "--output", "-o",
        default="./memory_assets",
        help="输出目录（默认: ./memory_assets）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部文件）",
    )

    try:
        parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
        parser.add_argument("--force", action="store_true")  # R4 强制写盘

        parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
        args = parser.parse_args()
        global dry_run
        dry_run = getattr(args, "dry_run", False)  # v3.274 同步到全局
    except SystemExit as e:
        # 参数解析失败
        if e.code != 0:
            print(f"[ERROR] E007: {ERROR_CODES['E007']}", file=sys.stderr)
        return e.code if e.code else 0

    # 自检模式
    if args.selftest:
        result = _run_selftest()
        if result != 0:
            print(f"[ERROR] E010: {ERROR_CODES['E010']}", file=sys.stderr)
        return result

    # 常规处理模式
    if not args.input:
        print(f"[ERROR] E007: {ERROR_CODES['E007']} | 必须指定 --input 或使用 --selftest", file=sys.stderr)
        return 1

    try:
        processor = MemoryHubProcessor(output_dir=args.output)

        # 判断输入是文件还是目录
        input_path = Path(args.input)
        if input_path.is_dir():
            results = processor.process_directory(args.input)
        elif input_path.is_file():
            results = processor.process_single_file(args.input)
        else:
            fail("E001", f"路径: {args.input}")

        # 写入资产文件
        written_files = processor.write_assets(results)

        # 写入索引
        index_path = processor.write_index(results)

        # 输出汇总报告
        success_count = sum(1 for r in results if r.asset is not None)
        fail_count = sum(1 for r in results if r.asset is None)

        print(f"处理完成: 共 {len(results)} 份材料")
        print(f"  成功: {success_count} 条资产")
        print(f"  失败: {fail_count} 条")
        print(f"  输出目录: {processor.output_dir}")
        print(f"  资产文件: {len(written_files)} 个")
        print(f"  索引文件: {index_path}")

        # 输出失败明细
        for r in results:
            if r.asset is None and r.error:
                print(f"  [失败] {r.source}: {r.error}")

        # 输出下一步建议
        print("\n下一步建议:")
        print("  1. 检查生成的资产 JSON 文件，确认内容准确")
        print("  2. 将 INDEX.json 分享给团队成员")
        print("  3. 根据实际需求调整关键词或补充元数据")

        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] 未预期异常: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
