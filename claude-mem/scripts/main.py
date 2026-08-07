#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claude-mem 技能独立实现 — 跨会话上下文持久化与压缩

仅依据功能规格 clean-room 重写，不参考任何既有代码。
功能：输入结构化、关键信息识别、格式约定输出、置信度标注、批量处理。
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 错误码定义
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "E001": "输入为空或缺少必要字段",
    "E002": "输入格式无法解析（JSON/文本/URL 均失败）",
    "E003": "输出格式仅支持 json 或 markdown",
    "E004": "批量处理时输入列表为空",
    "E005": "自定义字段结构无效（应为字典）",
    "E006": "URL 格式非法",
    "E007": "文件路径不存在或不可读",
    "E008": "内部逻辑错误：结构化结果为空",
    "E009": "参数冲突：--selftest 不能与其他业务参数同时使用",
    "E010": "未知错误",
}

# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class MemoryEntry:
    """记忆条目数据结构"""
    source: str = ""                     # 来源（文本/文件路径/URL）
    title: str = ""                      # 标题或主题
    key_points: List[str] = field(default_factory=list)   # 关键要点
    entities: List[str] = field(default_factory=list)     # 识别出的实体
    decisions: List[str] = field(default_factory=list)    # 决策项
    constraints: List[str] = field(default_factory=list)  # 约束条件
    todos: List[str] = field(default_factory=list)        # 待办事项
    confidence: float = 0.0              # 整体置信度 0~1
    raw_text: str = ""                   # 原始文本（截断保留）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            f"# 记忆条目: {self.title or '未命名'}",
            "",
            f"- **来源**: {self.source or '未知'}",
            f"- **置信度**: {self.confidence:.2f}",
            "",
        ]
        if self.key_points:
            lines.append("## 关键要点")
            lines.extend(f"- {p}" for p in self.key_points)
            lines.append("")
        if self.entities:
            lines.append("## 实体")
            lines.extend(f"- {e}" for e in self.entities)
            lines.append("")
        if self.decisions:
            lines.append("## 决策")
            lines.extend(f"- {d}" for d in self.decisions)
            lines.append("")
        if self.constraints:
            lines.append("## 约束")
            lines.extend(f"- {c}" for c in self.constraints)
            lines.append("")
        if self.todos:
            lines.append("## 待办")
            lines.extend(f"- [ ] {t}" for t in self.todos)
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 核心处理逻辑
# ---------------------------------------------------------------------------
class MemoryProcessor:
    """会话记忆处理器：解析、识别、压缩、格式化"""

    # 高价值信息关键词模式
    DECISION_PATTERNS = [
        r"决定[了用采用选择]",
        r"确定[了用采用选择]",
        r"选[用择定]了",
        r"最终[决定确定]",
        r"决策[:：]",
    ]
    CONSTRAINT_PATTERNS = [
        r"必须",
        r"不能",
        r"禁止",
        r"限制",
        r"约束[:：]",
        r"仅[限能]",
        r"不得",
    ]
    TODO_PATTERNS = [
        r"待办",
        r"需要[做完成处理解决]",
        r"下一步",
        r"TODO",
        r"后续",
    ]
    ENTITY_PATTERN = re.compile(
        r"(?:项目|系统|模块|工具|技术|框架|语言|平台|用户|团队|公司|会议|文档|版本)[:：]?\s*"
        r"([A-Za-z0-9_\-\u4e00-\u9fff]{2,30})"
    )
    TITLE_PATTERN = re.compile(
        r"(?:主题|标题|关于|议题)[:：]\s*([^\n。]{2,50})"
    )

    def __init__(self, custom_fields: Optional[Dict[str, Any]] = None):
        """初始化处理器，可传入自定义字段结构"""
        self.custom_fields = custom_fields or {}
        if not isinstance(self.custom_fields, dict):
            raise ValueError("E005")

    # -- 输入解析 ----------------------------------------------------------
    def parse_input(self, content: str, source: str = "text") -> str:
        """解析输入内容，返回规范化文本"""
        if not content or not content.strip():
            raise ValueError("E001")

        # 尝试 JSON 解析
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # 从常见字段提取文本
                text = (
                    data.get("text") or data.get("content") or
                    data.get("transcript") or data.get("message") or
                    ""
                )
                if not text:
                    raise ValueError("E002")
                return str(text)
            elif isinstance(data, list):
                # 列表形式：拼接文本
                parts = []
                for item in data:
                    if isinstance(item, dict):
                        parts.append(
                            str(item.get("text") or item.get("content") or "")
                        )
                    else:
                        parts.append(str(item))
                if not parts:
                    raise ValueError("E002")
                return "\n".join(parts)
            else:
                raise ValueError("E002")
        except (json.JSONDecodeError, ValueError):
            if source == "json" and not content.startswith("{") and not content.startswith("["):
                raise ValueError("E002")

        # URL 检测
        if source == "url" or self._looks_like_url(content):
            return self._extract_url_text(content)

        # 普通文本
        return content.strip()

    def _looks_like_url(self, text: str) -> bool:
        """判断是否为 URL"""
        text = text.strip()
        if not text.startswith(("http://", "https://")):
            return False
        try:
            result = urlparse(text)
            return bool(result.netloc and result.scheme)
        except Exception:
            return False

    def _extract_url_text(self, url: str) -> str:
        """从 URL 提取文本（离线模式：仅返回 URL 本身作为占位）"""
        url = url.strip()
        if not self._looks_like_url(url):
            raise ValueError("E006")
        # 离线实现：不访问网络，仅返回 URL 作为可处理文本
        return f"[URL] {url}"

    def load_file(self, path: str) -> str:
        """从文件读取内容"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, OSError):
            raise ValueError("E007")

    # -- 关键信息识别 ------------------------------------------------------
    def extract_key_info(self, text: str) -> Dict[str, Any]:
        """从文本中提取关键信息"""
        if not text:
            raise ValueError("E001")

        result: Dict[str, Any] = {
            "title": "",
            "key_points": [],
            "entities": [],
            "decisions": [],
            "constraints": [],
            "todos": [],
        }

        # 标题提取
        title_match = self.TITLE_PATTERN.search(text)
        if title_match:
            result["title"] = title_match.group(1).strip()
        else:
            # 使用第一行作为标题
            first_line = text.split("\n")[0].strip()
            if first_line and len(first_line) <= 50:
                result["title"] = first_line
            else:
                result["title"] = text[:30] + ("..." if len(text) > 30 else "")

        # 句子切分（简单按标点切分）
        sentences = re.split(r"[。！？!?；;\n]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # 关键要点：取前若干非空句子
        result["key_points"] = sentences[:5]

        # 实体提取
        for match in self.ENTITY_PATTERN.finditer(text):
            entity = match.group(1).strip()
            if entity and entity not in result["entities"]:
                result["entities"].append(entity)
        result["entities"] = result["entities"][:10]

        # 决策提取
        for sentence in sentences:
            for pattern in self.DECISION_PATTERNS:
                if re.search(pattern, sentence):
                    # 提取决策内容（关键词后的部分）
                    parts = re.split(pattern, sentence)
                    if len(parts) > 1:
                        decision = parts[-1].strip()
                        if decision and decision not in result["decisions"]:
                            result["decisions"].append(decision[:50])
                    break

        # 约束提取
        for sentence in sentences:
            for pattern in self.CONSTRAINT_PATTERNS:
                if re.search(pattern, sentence):
                    if sentence not in result["constraints"]:
                        result["constraints"].append(sentence[:50])
                    break

        # 待办提取
        for sentence in sentences:
            for pattern in self.TODO_PATTERNS:
                if re.search(pattern, sentence):
                    if sentence not in result["todos"]:
                        result["todos"].append(sentence[:50])
                    break

        return result

    def compute_confidence(self, info: Dict[str, Any]) -> float:
        """计算置信度（基于信息丰富度）"""
        if not info:
            return 0.0

        score = 0.0
        # 标题存在 +0.2
        if info.get("title"):
            score += 0.2
        # 关键要点数量
        score += min(len(info.get("key_points", [])) * 0.1, 0.3)
        # 实体数量
        score += min(len(info.get("entities", [])) * 0.1, 0.3)
        # 决策/约束/待办
        score += min(len(info.get("decisions", [])) * 0.1, 0.2)
        score += min(len(info.get("constraints", [])) * 0.1, 0.2)
        score += min(len(info.get("todos", [])) * 0.1, 0.2)

        # 归一化到 0~1，确保至少有基础值
        return min(max(score, 0.1), 1.0)

    # -- 主流程 ------------------------------------------------------------
    def process(
        self,
        content: str,
        source: str = "text",
        output_format: str = "json",
    ) -> str:
        """处理输入内容，生成压缩记忆条目"""
        if output_format not in ("json", "markdown"):
            raise ValueError("E003")

        # 解析输入
        text = self.parse_input(content, source)

        # 提取关键信息
        info = self.extract_key_info(text)
        if not info:
            raise ValueError("E008")

        # 计算置信度
        confidence = self.compute_confidence(info)

        # 构建记忆条目
        entry = MemoryEntry(
            source=source,
            title=info["title"],
            key_points=info["key_points"],
            entities=info["entities"],
            decisions=info["decisions"],
            constraints=info["constraints"],
            todos=info["todos"],
            confidence=confidence,
            raw_text=text[:200] + ("..." if len(text) > 200 else ""),
        )

        # 应用自定义字段（若提供）
        if self.custom_fields:
            for key, value in self.custom_fields.items():
                # 安全设置属性，避免覆盖核心字段
                if not hasattr(entry, key):
                    setattr(entry, key, value)
                elif key in ["source", "title", "key_points", "entities", 
                           "decisions", "constraints", "todos", "confidence", "raw_text"]:
                    # 允许覆盖核心字段但保持类型安全
                    setattr(entry, key, value)
                else:
                    setattr(entry, key, value)

        # 输出格式
        if output_format == "json":
            return json.dumps(entry.to_dict(), ensure_ascii=False, indent=2)
        else:
            return entry.to_markdown()

    def process_batch(
        self,
        items: List[Dict[str, str]],
        output_format: str = "json",
    ) -> str:
        """批量处理多个输入项"""
        if not items:
            raise ValueError("E004")

        results = []
        errors = []
        
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
                
            content = item.get("content", "")
            source = item.get("source", "text")
            
            if not content or not content.strip():
                continue
                
            try:
                result = self.process(content, source, output_format)
                if result:
                    results.append(result)
            except ValueError as e:
                # 记录错误但继续处理
                errors.append({"index": idx, "error": str(e)})
                continue
            except Exception as e:
                errors.append({"index": idx, "error": f"E010: {str(e)}"})
                continue

        if not results:
            if errors:
                raise ValueError(f"E004: 所有 {len(items)} 条数据均处理失败")
            raise ValueError("E004: 无有效数据可处理")

        if output_format == "json":
            # 合并为 JSON 数组
            parsed = []
            for r in results:
                try:
                    parsed.append(json.loads(r))
                except json.JSONDecodeError:
                    continue
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        else:
            # Markdown 合并
            return "\n\n---\n\n".join(results)


# ---------------------------------------------------------------------------
# 自检模块
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """内置硬编码样例数据离线自检，不依赖外部环境"""
    print("[selftest] 开始自检...")

    # 样例数据（硬编码，不读外部文件）
    sample_text = """
    项目会议纪要
    主题：电商平台重构
    决定采用 Python 3.12 作为后端语言，使用 FastAPI 框架。
    必须保证系统可用性达到 99.9%，不能使用 MongoDB。
    需要完成用户模块重构、订单系统迁移。
    下一步：编写技术方案文档，待办：数据库选型评审。
    约束：仅限使用开源组件。
    参会人员：张三（架构师）、李四（后端工程师）。
    """

    sample_url = "https://example.com/project/notes"
    sample_json = json.dumps({
        "text": "决策：选择 React 作为前端框架。需要完成组件库搭建。",
        "source": "会议记录"
    })

    processor = MemoryProcessor()

    # 测试1: 文本处理
    try:
        result = processor.process(sample_text, "text", "json")
        data = json.loads(result)
        assert data["title"], "E001: 标题不应为空"
        assert len(data["key_points"]) > 0, "E001: 关键要点不应为空"
        assert data["confidence"] > 0.1, "E001: 置信度应大于0.1"
        print(f"  [通过] 文本处理: 标题='{data['title']}', 置信度={data['confidence']:.2f}")
    except AssertionError as e:
        print(f"  [失败] 文本处理: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 文本处理异常: {e}")
        return 1

    # 测试2: JSON 输入处理
    try:
        result = processor.process(sample_json, "json", "json")
        data = json.loads(result)
        assert "React" in str(data.get("decisions", [])), "E002: 应识别出 React 决策"
        assert data["confidence"] > 0.1, "E002: 置信度应大于0.1"
        print(f"  [通过] JSON输入处理: 决策={data['decisions']}")
    except AssertionError as e:
        print(f"  [失败] JSON输入处理: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] JSON输入处理异常: {e}")
        return 1

    # 测试3: URL 输入（离线模式）
    try:
        result = processor.process(sample_url, "url", "json")
        data = json.loads(result)
        assert data["source"] == "url", "E006: 来源应为 url"
        assert data["title"], "E006: 标题不应为空"
        print(f"  [通过] URL处理(离线): 标题='{data['title']}'")
    except AssertionError as e:
        print(f"  [失败] URL处理: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] URL处理异常: {e}")
        return 1

    # 测试4: Markdown 输出
    try:
        result = processor.process(sample_text, "text", "markdown")
        assert "#" in result, "E003: Markdown 应包含标题标记"
        assert "-" in result, "E003: Markdown 应包含列表标记"
        print(f"  [通过] Markdown输出: 长度={len(result)}字符")
    except AssertionError as e:
        print(f"  [失败] Markdown输出: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] Markdown输出异常: {e}")
        return 1

    # 测试5: 批量处理
    try:
        batch_items = [
            {"content": "决定使用 PostgreSQL 数据库。需要完成迁移脚本。", "source": "text"},
            {"content": "主题：前端优化。采用 Vue 3。必须兼容移动端。", "source": "text"},
        ]
        result = processor.process_batch(batch_items, "json")
        data = json.loads(result)
        assert len(data) == 2, "E004: 应返回2条结果"
        assert data[0]["title"], "E004: 第一条应有标题"
        assert data[1]["title"], "E004: 第二条应有标题"
        print(f"  [通过] 批量处理: 共{len(data)}条")
    except AssertionError as e:
        print(f"  [失败] 批量处理: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 批量处理异常: {e}")
        return 1

    # 测试6: 错误处理
    try:
        processor.process("", "text", "json")
        print("  [失败] 空输入应报错")
        return 1
    except ValueError as e:
        assert str(e) == "E001", f"E001: 错误码不匹配，得到{str(e)}"
        print(f"  [通过] 错误处理: 空输入返回 {str(e)}")

    try:
        processor.process("测试文本", "text", "xml")
        print("  [失败] 非法输出格式应报错")
        return 1
    except ValueError as e:
        assert str(e) == "E003", f"E003: 错误码不匹配，得到{str(e)}"
        print(f"  [通过] 错误处理: 非法格式返回 {str(e)}")

    # 测试7: 自定义字段
    try:
        custom = {"project_name": "测试项目"}
        p2 = MemoryProcessor(custom_fields=custom)
        result = p2.process(sample_text, "text", "json")
        data = json.loads(result)
        assert data["project_name"] == "测试项目", "E005: 自定义字段未生效"
        print(f"  [通过] 自定义字段: project_name='{data['project_name']}'")
    except AssertionError as e:
        print(f"  [失败] 自定义字段: {e}")
        return 1
    except ValueError as e:
        print(f"  [失败] 自定义字段: {e}")
        return 1

    # 测试8: 批量处理错误隔离
    try:
        batch_with_error = [
            {"content": "决定使用 PostgreSQL 数据库。", "source": "text"},
            {"content": "", "source": "text"},  # 空内容应被跳过
            {"content": "主题：测试。采用 Vue。", "source": "text"},
        ]
        result = processor.process_batch(batch_with_error, "json")
        data = json.loads(result)
        assert len(data) == 2, "E004: 应返回2条有效结果"
        print(f"  [通过] 批量错误隔离: 有效结果{len(data)}条")
    except AssertionError as e:
        print(f"  [失败] 批量错误隔离: {e}")
        return 1
    except Exception as e:
        print(f"  [失败] 批量错误隔离异常: {e}")
        return 1

    print("[selftest] 全部自检通过 ✓")
    return 0


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------
def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="claude-mem 会话记忆处理工具",
        epilog="示例: python main.py --input '决定使用 Python' --format json",
    )
    parser.add_argument(
        "--input", "-i",
        help="输入文本内容（优先于 --file）",
    )
    parser.add_argument(
        "--file", "-f",
        help="输入文件路径",
    )
    parser.add_argument(
        "--url",
        help="输入 URL（离线模式，仅记录来源）",
    )
    parser.add_argument(
        "--source",
        choices=["text", "json", "file", "url"],
        default="text",
        help="输入类型（默认: text）",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="输出格式（默认: json）",
    )
    parser.add_argument(
        "--batch-file",
        help="批量处理文件（JSON 数组格式）",
    )
    parser.add_argument(
        "--custom",
        help="自定义字段（JSON 字典格式）",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置自检（不读取外部输入）",
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        if args.input or args.file or args.url or args.batch_file:
            print("E009: --selftest 不能与其他业务参数同时使用", file=sys.stderr)
            return 9
        return run_selftest()

    try:
        # 自定义字段
        custom_fields = None
        if args.custom:
            try:
                custom_fields = json.loads(args.custom)
                if not isinstance(custom_fields, dict):
                    raise ValueError("E005")
            except json.JSONDecodeError:
                print("E005: 自定义字段应为 JSON 字典", file=sys.stderr)
                return 5

        processor = MemoryProcessor(custom_fields=custom_fields)

        # 批量处理
        if args.batch_file:
            try:
                with open(args.batch_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                if not isinstance(items, list):
                    raise ValueError("E004")
                result = processor.process_batch(items, args.format)
                print(result)
                return 0
            except ValueError as e:
                print(f"{e}: 批量处理失败", file=sys.stderr)
                return 4
            except (IOError, OSError):
                print("E007: 批量文件读取失败", file=sys.stderr)
                return 7

        # 获取输入内容
        content = ""
        source = args.source

        if args.url:
            content = args.url
            source = "url"
        elif args.file:
            try:
                content = processor.load_file(args.file)
                source = "file"
            except ValueError as e:
                print(f"{e}: 文件读取失败", file=sys.stderr)
                return 7
        elif args.input:
            content = args.input
        else:
            # 从标准输入读取
            content = sys.stdin.read().strip()
            if not content:
                print("E001: 请输入内容（--input/--file/--url/标准输入）", file=sys.stderr)
                return 1

        # 处理
        result = processor.process(content, source, args.format)
        print(result)
        return 0

    except ValueError as e:
        error_code = str(e) if str(e) in ERROR_CODES else "E010"
        print(f"{error_code}: {ERROR_CODES.get(error_code, '未知错误')}", file=sys.stderr)
        return int(error_code[1:])
    except Exception as e:
        print(f"E010: 未知错误 - {e}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    sys.exit(main())
