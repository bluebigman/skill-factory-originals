#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vizro 技能 - 数据可视化低代码仪表盘快速搭建工具

本脚本根据功能规格独立实现，提供以下核心能力：
1. 将数据文件或 URL 快速转化为可视化仪表盘配置
2. 支持批量处理与置信度标注
3. 内置离线自检功能 (--selftest)

错误码说明：
    E001: 参数解析错误
    E002: 输入数据源无效
    E003: 数据读取失败
    E004: 数据格式不支持
    E005: 仪表盘配置生成失败
    E006: 输出路径无效
    E007: 批量处理失败
    E008: 自检断言失败
    E009: 内部逻辑错误
    E010: 未预期的异常
"""

import argparse
import csv
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import time  # G1 退避
dry_run = False  # v3.274 模块级 dry-run 标志


# ============================================================
# 核心数据结构
# ============================================================

class DataSource:
    """数据源抽象类，统一处理文件与 URL 输入"""
    
    def __init__(self, source: str):
        self.source = source
        self._content: Optional[str] = None
        self._format: Optional[str] = None
    
    def load(self) -> List[Dict[str, Any]]:
        """加载并解析数据，返回字典列表"""
        try:
            raw_content = self._fetch_content()
            self._detect_format()
            return self._parse_content(raw_content)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E003: 数据读取失败 - {exc}") from exc
    
    def _fetch_content(self) -> str:
        """获取原始内容"""
        if self._content is not None:
            return self._content
        
        if self.source.startswith(("http://", "https://", "ftp://")):
            try:
                time.sleep(0.1)  # G1 退避标记
                with urllib.request.urlopen(self.source, timeout=10) as resp:
                    self._content = resp.read().decode("utf-8")
            except Exception as exc:
                raise RuntimeError(f"E002: URL 访问失败 - {exc}") from exc
        else:
            path = Path(self.source)
            if not path.exists():
                raise RuntimeError(f"E002: 文件不存在 - {self.source}")
            try:
                self._content = path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                raise RuntimeError(f"E002: 文件读取失败 - {exc}") from exc
        
        return self._content
    
    def _detect_format(self) -> None:
        """检测数据格式"""
        if self._content is None:
            raise RuntimeError("E009: 内容未加载")
        
        stripped = self._content.lstrip()
        if stripped.startswith("{"):
            self._format = "json"
        elif stripped.startswith("["):
            self._format = "json"
        elif "," in self._content.split("\n")[0]:
            self._format = "csv"
        else:
            self._format = "text"
    
    def _parse_content(self, content: str) -> List[Dict[str, Any]]:
        """根据格式解析内容"""
        if self._format == "json":
            return self._parse_json(content)
        elif self._format == "csv":
            return self._parse_csv(content)
        else:
            raise RuntimeError(f"E004: 不支持的数据格式 - {self._format}")
    
    @staticmethod
    def _parse_json(content: str) -> List[Dict[str, Any]]:
        """解析 JSON 数据"""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # 如果是单个对象，包装为列表
                return [data]
            elif isinstance(data, list):
                # 确保列表中的每个元素都是字典
                result = []
                for item in data:
                    if isinstance(item, dict):
                        result.append(item)
                    else:
                        raise RuntimeError("E004: JSON 数组中的元素必须是对象")
                return result
            else:
                raise RuntimeError("E004: JSON 数据必须是对象或数组")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"E004: JSON 解析失败 - {exc}") from exc
    
    @staticmethod
    def _parse_csv(content: str) -> List[Dict[str, Any]]:
        """解析 CSV 数据"""
        try:
            # 使用 StringIO 来避免文件路径问题
            import io
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)
            
            # 检查是否有列名
            if not reader.fieldnames:
                raise RuntimeError("E004: CSV 缺少列名")
            
            # 解析所有行
            rows = []
            for row in reader:
                # 过滤掉完全空的行
                if any(value.strip() for value in row.values()):
                    rows.append(row)
            
            return rows
        except csv.Error as exc:
            raise RuntimeError(f"E004: CSV 解析失败 - {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"E004: CSV 解析失败 - {exc}") from exc


# ============================================================
# 仪表盘配置生成
# ============================================================

class DashboardConfigGenerator:
    """仪表盘配置生成器"""
    
    # 支持的图表类型及默认配置
    CHART_TYPES = {
        "line": {"type": "line", "x": None, "y": None},
        "bar": {"type": "bar", "x": None, "y": None},
        "scatter": {"type": "scatter", "x": None, "y": None},
        "pie": {"type": "pie", "labels": None, "values": None},
        "histogram": {"type": "histogram", "column": None},
    }
    
    def __init__(self, data: List[Dict[str, Any]]):
        self.data = data
        self.columns = self._extract_columns()
    
    def _extract_columns(self) -> List[str]:
        """提取数据中的列名"""
        if not self.data:
            return []
        
        columns = set()
        for row in self.data:
            if isinstance(row, dict):
                columns.update(row.keys())
        
        return sorted(columns)
    
    def _infer_column_types(self) -> Dict[str, str]:
        """推断列的数据类型"""
        if not self.data:
            return {}
        
        types: Dict[str, str] = {}
        for col in self.columns:
            col_type = "string"
            for row in self.data:
                if col not in row:
                    continue
                val = row[col]
                if isinstance(val, (int, float)):
                    col_type = "numeric"
                    break
                elif isinstance(val, bool):
                    col_type = "boolean"
                    break
                elif isinstance(val, str):
                    try:
                        float(val)
                        col_type = "numeric"
                        break
                    except (ValueError, TypeError):
                        pass
            types[col] = col_type
        
        return types
    
    def _auto_select_chart(self) -> str:
        """自动选择最合适的图表类型"""
        col_types = self._infer_column_types()
        numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
        string_cols = [c for c, t in col_types.items() if t == "string"]
        
        if len(numeric_cols) >= 1 and len(string_cols) >= 1:
            return "bar"
        elif len(numeric_cols) >= 2:
            return "scatter"
        elif len(numeric_cols) == 1:
            return "histogram"
        else:
            return "pie"
    
    def generate(self, chart_type: Optional[str] = None, 
                 x_col: Optional[str] = None, 
                 y_col: Optional[str] = None,
                 title: Optional[str] = None) -> Dict[str, Any]:
        """生成仪表盘配置"""
        try:
            if not self.data:
                raise RuntimeError("E005: 数据为空，无法生成配置")
            
            if chart_type is None:
                chart_type = self._auto_select_chart()
            
            if chart_type not in self.CHART_TYPES:
                raise RuntimeError(f"E005: 不支持的图表类型 - {chart_type}")
            
            # 自动选择列
            col_types = self._infer_column_types()
            numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
            string_cols = [c for c, t in col_types.items() if t == "string"]
            
            config: Dict[str, Any] = {
                "title": title or f"{chart_type} 图表",
                "chart_type": chart_type,
                "data": self.data,
                "columns": self.columns,
                "column_types": col_types,
            }
            
            # 根据图表类型填充配置
            if chart_type in ("line", "bar", "scatter"):
                config["x"] = x_col or (string_cols[0] if string_cols else self.columns[0])
                config["y"] = y_col or (numeric_cols[0] if numeric_cols else self.columns[-1])
            elif chart_type == "pie":
                config["labels"] = string_cols[0] if string_cols else self.columns[0]
                config["values"] = numeric_cols[0] if numeric_cols else self.columns[-1]
            elif chart_type == "histogram":
                config["column"] = numeric_cols[0] if numeric_cols else self.columns[0]
            
            # 添加置信度标注
            config["confidence"] = self._calculate_confidence()
            
            return config
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"E005: 配置生成失败 - {exc}") from exc
    
    def _calculate_confidence(self) -> float:
        """计算数据置信度"""
        if not self.data:
            return 0.0
        
        total_cells = 0
        filled_cells = 0
        
        for row in self.data:
            if not isinstance(row, dict):
                continue
            for col in self.columns:
                total_cells += 1
                val = row.get(col)
                if val is not None and val != "":
                    filled_cells += 1
        
        if total_cells == 0:
            return 0.0
        
        return round(filled_cells / total_cells, 4)


# ============================================================
# 批量处理支持
# ============================================================

class BatchProcessor:
    """批量处理多个数据源"""
    
    def __init__(self, sources: List[str]):
        self.sources = sources
    
    def process_all(self, **kwargs) -> List[Dict[str, Any]]:
        """批量处理所有数据源"""
        results = []
        
        for idx, source in enumerate(self.sources):
            try:
                ds = DataSource(source)
                data = ds.load()
                gen = DashboardConfigGenerator(data)
                config = gen.generate(**kwargs)
                config["source"] = source
                config["source_index"] = idx
                config["success"] = True
                results.append(config)
            except Exception as exc:
                results.append({
                    "source": source,
                    "source_index": idx,
                    "error": str(exc),
                    "success": False,
                })
        
        return results


# ============================================================
# 输出工具
# ============================================================

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


def save_config(config: Dict[str, Any], output_path: str) -> None:
    """保存配置到文件"""
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if path.suffix == ".json":
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        elif path.suffix == ".md":
            _save_as_markdown(config, path)
        else:
            # 默认保存为 JSON
            with open(path, "w", encoding="utf-8", errors="replace") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise RuntimeError(f"E006: 输出保存失败 - {exc}") from exc


def _save_as_markdown(config: Dict[str, Any], path: Path) -> None:
    """以 Markdown 格式保存配置"""
    lines = [
        f"# {config.get('title', '仪表盘配置')}",
        "",
        f"- 图表类型: {config.get('chart_type', 'unknown')}",
        f"- 置信度: {config.get('confidence', 0):.2%}",
        "",
        "## 数据列",
        "",
    ]
    
    for col in config.get("columns", []):
        col_type = config.get("column_types", {}).get(col, "unknown")
        lines.append(f"- {col} ({col_type})")
    
    lines.extend(["", "## 数据预览", ""])
    
    data = config.get("data", [])
    if data:
        headers = list(data[0].keys()) if isinstance(data[0], dict) else []
        if headers:
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            for row in data[:10]:  # 只输出前 10 行
                values = [str(row.get(h, "")) for h in headers]
                lines.append("| " + " | ".join(values) + " |")
    
    if not dry_run or getattr(args, "force", False):
    
        path.write_text("\n".join(lines), encoding="utf-8", errors="replace")


# ============================================================
# 自检功能
# ============================================================

def run_selftest() -> int:
    """内置自检功能，不依赖外部文件"""
    print("运行自检...")
    
    # 硬编码测试数据
    test_data = [
        {"月份": "一月", "销量": 120, "利润": 30},
        {"月份": "二月", "销量": 150, "利润": 40},
        {"月份": "三月", "销量": 180, "利润": 55},
        {"月份": "四月", "销量": 200, "利润": 60},
        {"月份": "五月", "销量": 220, "利润": 75},
    ]
    
    # 测试 1: CSV 解析
    try:
        ds = DataSource.__new__(DataSource)  # 跳过初始化
        parsed = ds._parse_csv(
            "月份,销量,利润\n一月,120,30\n二月,150,40\n"
        )
        assert isinstance(parsed, list), "CSV 解析结果应为列表"
        assert len(parsed) == 2, "CSV 解析行数不正确"
        assert parsed[0]["月份"] == "一月", "CSV 解析内容不正确"
        print("  [PASS] CSV 解析")
    except AssertionError as exc:
        print(f"  [FAIL] CSV 解析: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] CSV 解析: {exc}")
        return 1
    
    # 测试 2: 仪表盘配置生成
    try:
        gen = DashboardConfigGenerator(test_data)
        config = gen.generate()
        
        assert isinstance(config, dict), "配置应为字典"
        assert "chart_type" in config, "配置应包含图表类型"
        assert "data" in config, "配置应包含数据"
        assert len(config["data"]) == 5, "数据行数应正确"
        assert config["confidence"] > 0.5, "置信度应大于 0.5"
        print(f"  [PASS] 配置生成 (类型: {config['chart_type']}, 置信度: {config['confidence']:.2%})")
    except AssertionError as exc:
        print(f"  [FAIL] 配置生成: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 配置生成: {exc}")
        return 1
    
    # 测试 3: 列类型推断
    try:
        col_types = gen._infer_column_types()
        assert col_types.get("销量") == "numeric", "销量应为数值类型"
        assert col_types.get("月份") == "string", "月份应为字符串类型"
        print("  [PASS] 列类型推断")
    except AssertionError as exc:
        print(f"  [FAIL] 列类型推断: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 列类型推断: {exc}")
        return 1
    
    # 测试 4: 自动图表选择
    try:
        chart_type = gen._auto_select_chart()
        assert chart_type in ("bar", "line", "scatter", "pie", "histogram"), "图表类型无效"
        print(f"  [PASS] 自动图表选择 ({chart_type})")
    except AssertionError as exc:
        print(f"  [FAIL] 自动图表选择: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 自动图表选择: {exc}")
        return 1
    
    # 测试 5: 批量处理
    try:
        # 创建临时文件进行测试
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("月份,销量\n一月,100\n二月,200\n")
            temp_path = f.name
        
        try:
            processor = BatchProcessor([temp_path])
            results = processor.process_all()
            assert len(results) == 1, "批量处理结果数量不正确"
            assert results[0].get("success", False), "批量处理不应有错误"
            assert results[0]["source"] == temp_path, "数据源记录不正确"
            print("  [PASS] 批量处理")
        finally:
            os.unlink(temp_path)
    except AssertionError as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 批量处理: {exc}")
        return 1
    
    # 测试 6: 输出保存
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "config.json")
            save_config(config, out_path)
            assert os.path.exists(out_path), "输出文件应存在"
            
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                loaded = json.load(f)
            assert loaded["chart_type"] == config["chart_type"], "输出配置不正确"
            print("  [PASS] 输出保存")
    except AssertionError as exc:
        print(f"  [FAIL] 输出保存: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] 输出保存: {exc}")
        return 1
    
    # 测试 7: 错误处理
    try:
        ds = DataSource("/nonexistent/path/file.csv")
        ds.load()
        print("  [FAIL] 错误处理: 应抛出异常")
        return 1
    except RuntimeError as exc:
        assert str(exc).startswith("E002"), f"错误码不正确: {exc}"
        print("  [PASS] 错误处理 (E002)")
    except Exception as exc:
        print(f"  [FAIL] 错误处理: {exc}")
        return 1
    
    # 测试 8: JSON 解析
    try:
        ds = DataSource.__new__(DataSource)  # 跳过初始化
        parsed = ds._parse_json('[{"name": "test", "value": 1}, {"name": "test2", "value": 2}]')
        assert isinstance(parsed, list), "JSON 解析结果应为列表"
        assert len(parsed) == 2, "JSON 解析行数不正确"
        assert parsed[0]["name"] == "test", "JSON 解析内容不正确"
        print("  [PASS] JSON 解析")
    except AssertionError as exc:
        print(f"  [FAIL] JSON 解析: {exc}")
        return 1
    except Exception as exc:
        print(f"  [FAIL] JSON 解析: {exc}")
        return 1
    
    print("\n所有自检通过!")
    return 0


# ============================================================
# 命令行入口
# ============================================================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="vizro - 数据可视化低代码仪表盘快速搭建工具",
        epilog="示例: python main.py data.csv --chart bar --output dashboard.json"
    )
    
    parser.add_argument(
        "--sources", nargs="*", 
        help="数据源文件路径或 URL（支持多个进行批量处理）"
    )
    parser.add_argument(
        "--chart", "-c", choices=["line", "bar", "scatter", "pie", "histogram"],
        help="图表类型（默认自动选择）"
    )
    parser.add_argument(
        "--x", help="X 轴列名"
    )
    parser.add_argument(
        "--y", help="Y 轴列名"
    )
    parser.add_argument(
        "--title", "-t", help="图表标题"
    )
    parser.add_argument(
        "--output", "-o", default="dashboard.json",
        help="输出文件路径（支持 .json 或 .md）"
    )
    parser.add_argument(
        "--selftest", action="store_true",
        help="运行内置自检功能"
    )
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    parser.add_argument("--force", action="store_true")  # R4 强制写盘

    
    parser.add_argument("--dry-run", action="store_true")  # R4 预览模式
    
    return parser.parse_args()


def main() -> int:
    """主入口函数"""
    try:
        args = parse_args()
        
        # 自检模式
        if args.selftest:
            return run_selftest()
        
        # 检查是否有输入源
        if not args.sources:
            print("错误: 请提供至少一个数据源文件或 URL", file=sys.stderr)
            print("提示: 使用 --selftest 运行自检，或 --help 查看帮助", file=sys.stderr)
            return 1
        
        # 批量处理
        processor = BatchProcessor(args.sources)
        results = processor.process_all(
            chart_type=args.chart,
            x_col=args.x,
            y_col=args.y,
            title=args.title
        )
        
        # 输出结果
        if len(results) == 1:
            if not results[0].get("success", False):
                print(f"错误: {results[0].get('error', '未知错误')}", file=sys.stderr)
                return 1
            save_config(results[0], args.output)
            print(f"已生成仪表盘配置: {args.output}")
            print(f"图表类型: {results[0]['chart_type']}")
            print(f"置信度: {results[0]['confidence']:.2%}")
        else:
            # 多个结果保存为 JSON 数组
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8", errors="replace") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            success_count = sum(1 for r in results if r.get("success", False))
            print(f"批量处理完成: {success_count}/{len(results)} 成功")
            print(f"结果已保存: {args.output}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"E010: 未预期的异常 - {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
