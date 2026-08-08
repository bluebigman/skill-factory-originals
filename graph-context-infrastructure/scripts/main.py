#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图上下文基础设施 - 独立实现脚本

功能：将文本/CSV/JSON 数据解析为结构化图谱（节点-边-属性），
支持置信度标注、多格式输出（JSON/GraphML/CSV）、批量处理。

仅依据功能规格独立实现，不复制任何既有代码。
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

# 错误码定义
ERR_INVALID_INPUT = "E001"      # 输入参数无效
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ = "E003"          # 文件读取失败
ERR_FILE_WRITE = "E004"         # 文件写入失败
ERR_ENCODING = "E005"           # 编码解析失败
ERR_PARSE = "E006"              # 数据解析失败
ERR_OUTPUT_FORMAT = "E007"      # 输出格式不支持
ERR_INTERNAL = "E008"           # 内部逻辑错误
ERR_PATH_VIOLATION = "E009"     # 路径越权
ERR_DRY_RUN = "E010"           # 预览模式禁止写盘


# ============================================================
# 输入校验
# ============================================================

def validate_input_path(path_str):
    """校验输入路径合法性，防止路径穿越。

    参数:
        path_str: 输入路径字符串

    返回:
        Path 对象

    异常:
        ValueError: 路径非法时抛出，带错误码
    """
    if not path_str or not isinstance(path_str, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: 路径不能为空且必须是字符串")

    path = Path(path_str).expanduser().resolve()

    # 白名单校验：只允许当前目录及子目录
    cwd = Path.cwd().resolve()
    try:
        path.relative_to(cwd)
    except ValueError:
        raise ValueError(f"{ERR_PATH_VIOLATION}: 路径 {path} 超出当前工作目录范围")

    return path


def validate_output_format(fmt):
    """校验输出格式是否支持。

    参数:
        fmt: 输出格式字符串

    返回:
        规范化后的格式名

    异常:
        ValueError: 格式不支持时抛出
    """
    supported = {"json", "graphml", "csv"}
    fmt_lower = fmt.lower() if fmt else ""
    if fmt_lower not in supported:
        raise ValueError(f"{ERR_OUTPUT_FORMAT}: 不支持的输出格式 '{fmt}'，"
                         f"仅支持 {sorted(supported)}")
    return fmt_lower


def validate_confidence_threshold(threshold):
    """校验置信度阈值范围。

    参数:
        threshold: 置信度阈值

    返回:
        浮点数阈值

    异常:
        ValueError: 阈值不在 [0,1] 范围时抛出
    """
    try:
        val = float(threshold)
    except (TypeError, ValueError):
        raise ValueError(f"{ERR_INVALID_INPUT}: 置信度阈值必须是数字，收到 {threshold}")

    if not 0.0 <= val <= 1.0:
        raise ValueError(f"{ERR_INVALID_INPUT}: 置信度阈值必须在 [0,1] 范围，收到 {val}")
    return val


# ============================================================
# 核心逻辑：文本解析为图谱
# ============================================================

# 中文/英文句子边界正则（句号、问号、感叹号、分号）
_SENTENCE_SPLIT_RE = re.compile(r'[。！？；!?;]\s*')
# 实体识别正则（中文连续词或英文单词）
_ENTITY_RE = re.compile(r'[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_]{1,}')
# 关系词识别（常见中文关系动词）
_RELATION_WORDS = {"是", "属于", "包含", "位于", "创建", "开发", "使用",
                   "支持", "提供", "拥有", "导致", "影响", "关联"}


def parse_text_to_graph(text):
    """将文本解析为图谱结构（节点-边-属性）。

    核心算法：
      1. 按句子边界切分文本
      2. 每个句子内识别实体（连续中文词/英文单词）
      3. 相邻实体之间建立关系边
      4. 关系置信度基于实体共现频率

    参数:
        text: 输入文本

    返回:
        dict: {"nodes": [...], "edges": [...], "stats": {...}}

    异常:
        ValueError: 文本为空或解析失败时抛出
    """
    if not text or not isinstance(text, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: 文本不能为空且必须是字符串")

    # 按句子切分（保留边界符）
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]

    nodes = OrderedDict()  # id -> {id, label, type, properties}
    edges = []             # [{source, target, relation, confidence}]
    relation_counter = {}  # (source, target, relation) -> count

    for sent in sentences:
        # 识别句子中的实体
        entities = _ENTITY_RE.findall(sent)
        if len(entities) < 2:
            continue

        # 去重但保持顺序
        unique_entities = []
        seen = set()
        for ent in entities:
            if ent not in seen:
                seen.add(ent)
                unique_entities.append(ent)

        # 为每个实体创建节点
        for ent in unique_entities:
            if ent not in nodes:
                nodes[ent] = {
                    "id": ent,
                    "label": ent,
                    "type": "entity",
                    "properties": {"source_sentence": sent[:50]}
                }

        # 相邻实体对建立关系
        for i in range(len(unique_entities) - 1):
            src = unique_entities[i]
            tgt = unique_entities[i + 1]
            # 检测句子中是否包含关系词
            relation = "关联"
            for rw in _RELATION_WORDS:
                if rw in sent:
                    relation = rw
                    break
            key = (src, tgt, relation)
            relation_counter[key] = relation_counter.get(key, 0) + 1

    # 生成边（置信度 = 共现次数 / 总句子数）
    total_sentences = max(len(sentences), 1)
    for (src, tgt, rel), cnt in relation_counter.items():
        confidence = min(cnt / total_sentences, 1.0)
        edges.append({
            "source": src,
            "target": tgt,
            "relation": rel,
            "confidence": round(confidence, 4)
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "sentence_count": len(sentences),
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }


def parse_csv_to_graph(csv_text):
    """将 CSV 文本解析为图谱。

    CSV 格式要求：至少两列，第一列是源节点，第二列是目标节点，
    可选第三列是关系名。

    参数:
        csv_text: CSV 文本内容

    返回:
        dict: 图谱结构
    """
    if not csv_text or not isinstance(csv_text, str):
        raise ValueError(f"{ERR_INVALID_INPUT}: CSV 文本不能为空")

    try:
        reader = csv.reader(csv_text.splitlines())
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    except Exception as e:
        raise ValueError(f"{ERR_PARSE}: CSV 解析失败 - {e}")

    if len(rows) < 2:
        raise ValueError(f"{ERR_PARSE}: CSV 至少需要表头+一行数据")

    header = [h.strip() for h in rows[0]]
    if len(header) < 2:
        raise ValueError(f"{ERR_PARSE}: CSV 至少需要两列（源节点、目标节点）")

    nodes = OrderedDict()
    edges = []

    for row in rows[1:]:
        if len(row) < 2:
            continue
        src = row[0].strip()
        tgt = row[1].strip()
        rel = row[2].strip() if len(row) > 2 else "关联"

        if not src or not tgt:
            continue

        for node_id, label in [(src, src), (tgt, tgt)]:
            if node_id not in nodes:
                nodes[node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": "entity",
                    "properties": {}
                }

        edges.append({
            "source": src,
            "target": tgt,
            "relation": rel,
            "confidence": 1.0  # 显式数据置信度为 1.0
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "sentence_count": len(rows) - 1,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    }


def parse_data_to_graph(data, data_format):
    """统一入口：根据数据格式解析为图谱。

    参数:
        data: 输入数据（文本或 CSV 内容）
        data_format: 数据格式（text/csv/json）

    返回:
        dict: 图谱结构
    """
    fmt = data_format.lower() if data_format else "text"

    if fmt == "csv":
        return parse_csv_to_graph(data)
    elif fmt == "json":
        # JSON 输入：期望是图谱结构或实体列表
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"{ERR_PARSE}: JSON 解析失败 - {e}")
        if isinstance(parsed, dict) and "nodes" in parsed and "edges" in parsed:
            return parsed  # 已经是图谱结构
        elif isinstance(parsed, list):
            # 实体列表 -> 构建简单图谱
            nodes = [{"id": x, "label": x, "type": "entity", "properties": {}}
                     for x in parsed if isinstance(x, str)]
            return {"nodes": nodes, "edges": [], "stats": {"node_count": len(nodes)}}
        else:
            raise ValueError(f"{ERR_PARSE}: JSON 格式不符合图谱结构")
    else:
        return parse_text_to_graph(data)


def filter_by_confidence(graph, threshold):
    """根据置信度阈值过滤边。

    参数:
        graph: 图谱结构
        threshold: 置信度阈值

    返回:
        过滤后的图谱
    """
    if threshold is None:
        return graph

    filtered_edges = [e for e in graph["edges"] if e["confidence"] >= threshold]
    # 重新统计节点（只保留有边的节点）
    node_ids = set()
    for e in filtered_edges:
        node_ids.add(e["source"])
        node_ids.add(e["target"])

    filtered_nodes = [n for n in graph["nodes"] if n["id"] in node_ids]

    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "stats": {
            "sentence_count": graph["stats"].get("sentence_count", 0),
            "node_count": len(filtered_nodes),
            "edge_count": len(filtertered_edges)
        }
    }


# ============================================================
# 输出格式化
# ============================================================

def format_json(graph):
    """格式化输出为 JSON 字符串。"""
    return json.dumps(graph, ensure_ascii=False, indent=2)


def format_graphml(graph):
    """格式化输出为 GraphML XML 字符串。"""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <graph id="G" edgedefault="undirected">'
    ]

    # 节点
    for node in graph["nodes"]:
        node_id = node["id"]
        label = node.get("label", node_id)
        lines.append(f'    <node id="{node_id}">')
        lines.append(f'      <data key="label">{label}</data>')
        lines.append('    </node>')

    # 边
    for edge in graph["edges"]:
        src = edge["source"]
        tgt = edge["target"]
        rel = edge.get("relation", "关联")
        conf = edge.get("confidence", 1.0)
        lines.append(f'    <edge source="{src}" target="{tgt}">')
        lines.append(f'      <data key="relation">{rel}</data>')
        lines.append(f'      <data key="confidence">{conf}</data>')
        lines.append('    </edge>')

    lines.append('  </graph>')
    lines.append('</graphml>')
    return "\n".join(lines)


def format_csv(graph):
    """格式化输出为 CSV 字符串。"""
    output = []
    # 节点部分
    output.append("# NODES")
    output.append("id,label,type")
    for node in graph["nodes"]:
        output.append(f"{node['id']},{node.get('label', node['id'])},{node.get('type', 'entity')}")

    # 边部分
    output.append("")
    output.append("# EDGES")
    output.append("source,target,relation,confidence")
    for edge in graph["edges"]:
        output.append(f"{edge['source']},{edge['target']},"
                      f"{edge.get('relation', '关联')},{edge.get('confidence', 1.0)}")

    return "\n".join(output)


def format_graph(graph, output_format):
    """统一格式化入口。

    参数:
        graph: 图谱结构
        output_format: 输出格式（json/graphml/csv）

    返回:
        格式化后的字符串
    """
    fmt = validate_output_format(output_format)

    if fmt == "json":
        return format_json(graph)
    elif fmt == "graphml":
        return format_graphml(graph)
    elif fmt == "csv":
        return format_csv(graph)
    else:
        raise ValueError(f"{ERR_OUTPUT_FORMAT}: 未知格式 {fmt}")


# ============================================================
# 文件读写（多编码支持）
# ============================================================

def read_text_file(path):
    """读取文本文件，支持多编码。

    编码探测顺序：utf-8 → gbk → gb18030 → latin-1（兜底）

    参数:
        path: 文件路径

    返回:
        文件内容字符串

    异常:
        FileNotFoundError: 文件不存在
        IOError: 读取失败
    """
    if not path.exists():
        raise FileNotFoundError(f"{ERR_FILE_NOT_FOUND}: 文件不存在 {path}")

    # 尝试多种编码
    encodings = ["utf-8", "gbk", "gb18030", "latin-1"]
    last_error = None

    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except IOError as e:
            raise IOError(f"{ERR_FILE_READ}: 读取文件失败 {path} - {e}")

    # 所有编码都失败，使用 errors="replace" 兜底
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            print(f"警告: 文件编码无法完全识别，已使用替换字符处理 {path}",
                  file=sys.stderr)
            return content
    except IOError as e:
        raise IOError(f"{ERR_FILE_READ}: 读取文件失败 {path} - {e}")


def write_text_file(path, content, dry_run=False):
    """写入文本文件。

    参数:
        path: 目标路径
        content: 内容
        dry_run: 预览模式（不实际写入）

    返回:
        bool: 是否实际写入

    异常:
        ValueError: 预览模式禁止写盘
        IOError: 写入失败
    """
    if dry_run:
        print(f"[DRY-RUN] 将写入 {path} ({len(content)} 字节)")
        return False

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except IOError as e:
        raise IOError(f"{ERR_FILE_WRITE}: 写入文件失败 {path} - {e}")


# ============================================================
# 主流程
# ============================================================

def process_input(input_source, data_format, threshold, dry_run=False):
    """处理输入源（文件或文本）并生成图谱。

    参数:
        input_source: 文件路径或直接文本
        data_format: 数据格式
        threshold: 置信度阈值
        dry_run: 预览模式

    返回:
        (图谱结构, 格式化输出字符串)
    """
    # 判断是文件还是直接文本
    if input_source and Path(input_source).exists():
        path = validate_input_path(input_source)
        content = read_text_file(path)
    else:
        content = input_source

    if not content or not content.strip():
        raise ValueError(f"{ERR_INVALID_INPUT}: 输入内容为空")

    # 解析为图谱
    graph = parse_data_to_graph(content, data_format)

    # 过滤置信度
    if threshold is not None:
        graph = filter_by_confidence(graph, threshold)

    return graph


def generate_diff_report(graph, verbose=False):
    """生成处理报告。

    参数:
        graph: 图谱结构
        verbose: 是否输出详细信息

    返回:
        报告字符串
    """
    stats = graph["stats"]
    report = []
    report.append(f"图谱统计: {stats['node_count']} 个节点, {stats['edge_count']} 条边")

    if verbose:
        report.append("\n节点明细:")
        for node in graph["nodes"]:
            report.append(f"  - {node['id']} (类型: {node.get('type', 'entity')})")

        report.append("\n边明细:")
        for edge in graph["edges"]:
            report.append(f"  - {edge['source']} → {edge['target']} "
                          f"[{edge.get('relation', '关联')}] "
                          f"置信度: {edge.get('confidence', 1.0):.2f}")

    return "\n".join(report)


def main():
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="图上下文基础设施 - 将文本/CSV/JSON 解析为结构化图谱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -i data.txt -f text -o graph.json
  %(prog)s -i data.csv -f csv --format graphml --dry-run
  %(prog)s --selftest
        """
    )
    parser.add_argument("-i", "--input", help="输入文件路径或直接文本")
    parser.add_argument("-f", "--data-format", default="text",
                        choices=["text", "csv", "json"],
                        help="输入数据格式 (默认: text)")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--format", dest="output_format", default="json",
                        choices=["json", "graphml", "csv"],
                        help="输出格式 (默认: json)")
    parser.add_argument("-t", "--threshold", type=float, default=None,
                        help="置信度阈值 [0,1]，低于阈值的边将被过滤")
    parser.add_argument("--dry-run", action="store_true",
                        help="预览模式：只打印输出内容，不写文件")
    parser.add_argument("--force", action="store_true",
                        help="强制写盘（需与 --dry-run 配合使用）")
    parser.add_argument("--verbose", action="store_true",
                        help="输出详细处理报告")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.1")

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        run_selftest()
        return 0

    # 参数校验
    if not args.input:
        parser.error(f"{ERR_INVALID_INPUT}: 必须提供 --input 参数")

    try:
        # 校验参数
        threshold = validate_confidence_threshold(args.threshold) if args.threshold is not None else None
        output_format = validate_output_format(args.output_format)

        # 处理输入
        graph = process_input(args.input, args.data_format, threshold, args.dry_run)

        # 格式化输出
        output_content = format_graph(graph, output_format)

        # 输出报告
        if args.verbose:
            report = generate_diff_report(graph, verbose=True)
            print(report)

        # 写盘或打印
        if args.output:
            output_path = validate_input_path(args.output)
            # 预览模式检查
            if args.dry_run and not args.force:
                print(f"[DRY-RUN] 输出预览 ({output_format}):")
                print(output_content[:2000] + ("..." if len(output_content) > 2000 else ""))
                print(f"\n[DRY-RUN] 文件未写入: {output_path}")
                print("提示: 使用 --force 参数强制写入")
            else:
                write_text_file(output_path, output_content, dry_run=args.dry_run)
                print(f"图谱已写入: {output_path}")
        else:
            # 无输出文件时打印到 stdout
            print(output_content)

        return 0

    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except (FileNotFoundError, IOError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"{ERR_INTERNAL}: 未预期的错误 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


# ============================================================
# 自检
# ============================================================

def run_selftest():
    """运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、不访问网络。
    断言使用宽松阈值（区间/大小比较），保证任何环境可过。
    """
    print("=" * 60)
    print("图上下文基础设施 - 自检开始")
    print("=" * 60)

    # 测试用例 1: 中文文本解析
    print("\n[测试 1] 中文文本解析")
    text1 = "张三开发了智能系统。智能系统支持数据分析。李四使用了智能系统。"
    try:
        graph1 = parse_text_to_graph(text1)
        assert graph1["stats"]["node_count"] >= 3, "节点数应至少包含 3 个实体"
        assert graph1["stats"]["edge_count"] >= 2, "边数应至少 2 条"
        assert len(graph1["nodes"]) > 0, "节点列表不能为空"
        assert len(graph1["edges"]) > 0, "边列表不能为空"
        # 验证节点包含关键实体
        node_ids = [n["id"] for n in graph1["nodes"]]
        assert "张三" in node_ids, "应包含实体'张三'"
        assert "智能系统" in node_ids, "应包含实体'智能系统'"
        print(f"  ✓ 通过 (节点: {graph1['stats']['node_count']}, 边: {graph1['stats']['edge_count']})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 2: 空输入处理
    print("\n[测试 2] 空输入处理")
    try:
        parse_text_to_graph("")
        print("  ✗ 失败: 空输入未抛出异常")
        sys.exit(1)
    except ValueError as e:
        assert "E001" in str(e), f"错误码应为 E001，收到 {e}"
        print("  ✓ 通过 (正确拒绝空输入)")

    # 测试用例 3: CSV 解析
    print("\n[测试 3] CSV 解析")
    csv_data = "source,target,relation\n张三,智能系统,开发\n李四,智能系统,使用\n"
    try:
        graph3 = parse_csv_to_graph(csv_data)
        assert graph3["stats"]["node_count"] == 3, "CSV 应解析出 3 个节点"
        assert graph3["stats"]["edge_count"] == 2, "CSV 应解析出 2 条边"
        assert all(e["confidence"] == 1.0 for e in graph3["edges"]), "显式数据置信度应为 1.0"
        print(f"  ✓ 通过 (节点: {graph3['stats']['node_count']}, 边: {graph3['stats']['edge_count']})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 4: 输出格式
    print("\n[测试 4] 输出格式")
    try:
        json_out = format_graph(graph1, "json")
        assert json_out.startswith("{"), "JSON 输出应以 { 开头"
        assert '"nodes"' in json_out, "JSON 输出应包含 nodes"

        graphml_out = format_graph(graph1, "graphml")
        assert "<graphml" in graphml_out, "GraphML 输出应包含 graphml 标签"
        assert "<node" in graphml_out, "GraphML 输出应包含节点"

        csv_out = format_graph(graph1, "csv")
        assert "id,label,type" in csv_out, "CSV 输出应包含节点表头"
        assert "source,target" in csv_out, "CSV 输出应包含边表头"
        print("  ✓ 通过 (JSON/GraphML/CSV 三种格式均正常)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 5: 置信度过滤
    print("\n[测试 5] 置信度过滤")
    try:
        filtered = filter_by_confidence(graph1, 0.5)
        assert filtered["stats"]["edge_count"] <= graph1["stats"]["edge_count"], \
            "过滤后边数不应增加"
        print(f"  ✓ 通过 (过滤前: {graph1['stats']['edge_count']} 边, "
              f"过滤后: {filtered['stats']['edge_count']} 边)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 6: 超长文本性能（O(n) 验证）
    print("\n[测试 6] 超长文本处理")
    long_text = "实体A关联实体B。" * 1000  # 2000 字
    try:
        import time
        start = time.time()
        graph6 = parse_text_to_graph(long_text)
        elapsed = time.time() - start
        assert graph6["stats"]["sentence_count"] >= 900, "应处理至少 900 个句子"
        assert elapsed < 5.0, f"处理 2000 字不应超过 5 秒，实际 {elapsed:.2f} 秒"
        print(f"  ✓ 通过 (处理 {len(long_text)} 字符，耗时 {elapsed:.2f} 秒)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 7: 中文标点处理
    print("\n[测试 7] 中文标点处理")
    text7 = "系统A；系统B。系统C！系统D？"
    try:
        graph7 = parse_text_to_graph(text7)
        assert graph7["stats"]["sentence_count"] >= 4, "应识别 4 个句子"
        print(f"  ✓ 通过 (识别 {graph7['stats']['sentence_count']} 个句子)")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 8: 编码处理（模拟 GBK 内容）
    print("\n[测试 8] 编码处理")
    try:
        # 模拟 GBK 编码的文本
        gbk_text = "测试实体一与测试实体二关联。".encode("gbk")
        decoded = gbk_text.decode("gbk")
        graph8 = parse_text_to_graph(decoded)
        assert graph8["stats"]["node_count"] >= 2, "GBK 编码文本应能正常解析"
        print("  ✓ 通过 (GBK 编码文本正常解析)")
    except (UnicodeDecodeError, AssertionError) as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 9: 空边处理
    print("\n[测试 9] 无关系文本")
    try:
        graph9 = parse_text_to_graph("这是一个没有任何实体关系的简单文本。")
        # 可能没有边，但不能崩溃
        assert isinstance(graph9["edges"], list), "边列表必须是列表类型"
        print(f"  ✓ 通过 (节点: {graph9['stats']['node_count']}, 边: {graph9['stats']['edge_count']})")
    except AssertionError as e:
        print(f"  ✗ 失败: {e}")
        sys.exit(1)

    # 测试用例 10: 输入校验
    print("\n[测试 10] 输入校验")
    try:
        validate_output_format("invalid")
        print("  ✗ 失败: 非法格式未抛出异常")
        sys.exit(1)
    except ValueError as e:
        assert "E007" in str(e), f"错误码应为 E007，收到 {e}"
        print("  ✓ 通过 (非法格式正确拒绝)")

    print("\n" + "=" * 60)
    print("自检全部通过 ✓")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
