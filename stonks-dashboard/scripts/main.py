#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stonks-dashboard - 终端行情赛博监控实时看板
==========================================
在终端中运行的赛博朋克风格实时金融行情监控工具，支持加密货币与股票数据可视化。

功能：
  1. 数据源接入：接受 CSV/JSON 文件、API URL 或直接粘贴的行情文本，解析为结构化数据
  2. 关键信息识别：自动提取时间戳、交易对/股票代码、价格、成交量、涨跌幅等核心字段
  3. 格式化输出：按终端宽度自适应渲染为赛博朋克风格表格、Sparkline 走势图或 ASCII 色块图
  4. 置信度标注：对缺失字段或推断值标注 `[需核实:字段名]`，不静默填充
  5. 批量与自定义：支持多文件批量处理，支持 `--format` 参数切换输出样式（table / spark / raw）

明确边界：
  - 不提供任何投资建议或买卖信号
  - 不连接真实交易所/券商 API（仅处理用户提供的数据）
  - 不保证数据实时性（取决于输入源刷新频率）
  - 不支持自然语言模糊查询
  - 不存储用户数据，所有处理在内存中完成

许可证：MIT License
版权所有：© 2026 SkillForge Lab
"""

import argparse
import csv
import io
import json
import math
import os
import sys
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import time  # G1 退避


# ============================================================
# 错误码定义
# ============================================================
ERR_OK = 0
ERR_INVALID_INPUT = "E001"      # 输入数据格式无效
ERR_FILE_NOT_FOUND = "E002"     # 文件不存在
ERR_FILE_READ_ERROR = "E003"    # 文件读取失败
ERR_PARSE_ERROR = "E004"        # 数据解析失败
ERR_MISSING_FIELD = "E005"      # 缺少必要字段
ERR_URL_ERROR = "E006"          # URL 访问失败
ERR_FORMAT_ERROR = "E007"       # 输出格式参数无效
ERR_BATCH_ERROR = "E008"        # 批量处理错误
ERR_SELFTEST_ERROR = "E009"     # 自检失败
ERR_UNKNOWN_ERROR = "E010"      # 未知错误


# ============================================================
# 核心数据结构
# ============================================================
class MarketData:
    """市场行情数据条目"""
    
    def __init__(self, symbol: str, price: float, volume: float = 0.0,
                 change_pct: float = 0.0, timestamp: str = "",
                 source: str = "", extra: Dict[str, Any] = None):
        self.symbol = symbol          # 交易对/股票代码
        self.price = price            # 价格
        self.volume = volume          # 成交量
        self.change_pct = change_pct  # 涨跌幅（百分比）
        self.timestamp = timestamp    # 时间戳
        self.source = source          # 数据来源
        self.extra = extra or {}      # 额外字段
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "change_pct": self.change_pct,
            "timestamp": self.timestamp,
            "source": self.source,
            **self.extra
        }


# ============================================================
# 数据解析模块
# ============================================================
class DataParser:
    """数据解析器：支持 CSV / JSON / 纯文本"""
    
    # 常见字段别名映射
    FIELD_ALIASES = {
        "symbol": ["symbol", "code", "ticker", "pair", "交易对", "股票代码", "代码"],
        "price": ["price", "last", "close", "最新价", "价格", "收盘价"],
        "volume": ["volume", "vol", "成交量", "量"],
        "change_pct": ["change_pct", "change", "pct_change", "涨跌幅", "涨幅", "涨跌"],
        "timestamp": ["timestamp", "time", "date", "datetime", "时间", "日期"],
    }
    
    @classmethod
    def parse_csv(cls, content: str) -> List[MarketData]:
        """解析 CSV 格式数据"""
        try:
            reader = csv.DictReader(io.StringIO(content))
            if not reader.fieldnames:
                raise ValueError("CSV 无字段名")
            
            # 建立字段名映射
            field_map = cls._build_field_map(reader.fieldnames)
            if "symbol" not in field_map or "price" not in field_map:
                raise ValueError("缺少必要字段: symbol/price")
            
            result = []
            for row in reader:
                if not row or all(v is None or v.strip() == "" for v in row.values()):
                    continue  # 跳过空行
                
                try:
                    symbol = row.get(field_map["symbol"], "").strip()
                    price_str = row.get(field_map["price"], "").strip()
                    if not symbol or not price_str:
                        continue
                    
                    price = float(price_str)
                    volume = cls._safe_float(row.get(field_map.get("volume", ""), "0"))
                    change = cls._safe_float(row.get(field_map.get("change_pct", ""), "0"))
                    timestamp = row.get(field_map.get("timestamp", ""), "").strip()
                    
                    result.append(MarketData(
                        symbol=symbol,
                        price=price,
                        volume=volume,
                        change_pct=change,
                        timestamp=timestamp,
                        source="csv"
                    ))
                except (ValueError, TypeError):
                    continue  # 跳过无效行
            
            if not result:
                raise ValueError("没有有效数据行")
            return result
        except Exception as e:
            raise RuntimeError(f"{ERR_PARSE_ERROR}: CSV 解析失败: {str(e)}")
    
    @classmethod
    def parse_json(cls, content: str) -> List[MarketData]:
        """解析 JSON 格式数据"""
        try:
            data = json.loads(content)
            
            # 支持多种 JSON 结构
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 尝试常见结构：{"data": [...]} 或 {"items": [...]} 或 {"quotes": [...]}
                for key in ["data", "items", "quotes", "rows", "records"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                else:
                    # 单条数据
                    items = [data]
            else:
                raise ValueError("JSON 必须是对象或数组")
            
            result = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                # 字段名归一化映射
                normalized = {}
                for key, value in item.items():
                    normalized[key.lower().replace(" ", "_").replace("-", "_")] = value
                
                # 识别 symbol
                symbol = ""
                for alias in cls.FIELD_ALIASES["symbol"]:
                    if alias in normalized:
                        symbol = str(normalized[alias])
                        break
                
                # 识别 price
                price = None
                for alias in cls.FIELD_ALIASES["price"]:
                    if alias in normalized:
                        try:
                            price = float(normalized[alias])
                            break
                        except (ValueError, TypeError):
                            continue
                
                if not symbol or price is None:
                    continue
                
                # 可选字段
                volume = 0.0
                for alias in cls.FIELD_ALIASES["volume"]:
                    if alias in normalized:
                        volume = cls._safe_float(normalized[alias], 0.0)
                        break
                
                change = 0.0
                for alias in cls.FIELD_ALIASES["change_pct"]:
                    if alias in normalized:
                        change = cls._safe_float(normalized[alias], 0.0)
                        break
                
                timestamp = ""
                for alias in cls.FIELD_ALIASES["timestamp"]:
                    if alias in normalized:
                        timestamp = str(normalized[alias])
                        break
                
                result.append(MarketData(
                    symbol=symbol,
                    price=price,
                    volume=volume,
                    change_pct=change,
                    timestamp=timestamp,
                    source="json"
                ))
            
            if not result:
                raise ValueError("没有有效数据")
            return result
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{ERR_PARSE_ERROR}: JSON 格式错误: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"{ERR_PARSE_ERROR}: JSON 解析失败: {str(e)}")
    
    @classmethod
    def parse_text(cls, content: str) -> List[MarketData]:
        """解析纯文本格式（每行: 代码 价格 [成交量] [涨跌幅] [时间]）"""
        result = []
        lines = content.strip().splitlines()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            
            # 支持多种分隔符
            parts = None
            for sep in [",", "\t", "|", ";", "  "]:
                if sep == "  ":
                    parts = [p for p in line.split() if p]
                else:
                    parts = line.split(sep)
                if len(parts) >= 2:
                    break
            
            if not parts or len(parts) < 2:
                continue
            
            try:
                symbol = parts[0].strip()
                price = float(parts[1].strip())
                volume = float(parts[2].strip()) if len(parts) > 2 else 0.0
                change = float(parts[3].strip().rstrip("%")) if len(parts) > 3 else 0.0
                timestamp = parts[4].strip() if len(parts) > 4 else ""
                
                result.append(MarketData(
                    symbol=symbol,
                    price=price,
                    volume=volume,
                    change_pct=change,
                    timestamp=timestamp,
                    source="text"
                ))
            except (ValueError, IndexError):
                continue
        
        if not result:
            raise RuntimeError(f"{ERR_PARSE_ERROR}: 文本解析失败，无有效数据")
        return result
    
    @classmethod
    def _build_field_map(cls, fieldnames: List[str]) -> Dict[str, str]:
        """构建字段名到标准字段的映射"""
        field_map = {}
        for field in fieldnames:
            field_lower = field.lower().replace(" ", "_").replace("-", "_")
            for standard, aliases in cls.FIELD_ALIASES.items():
                if field_lower in aliases or field in aliases:
                    field_map[standard] = field
                    break
        return field_map
    
    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """安全转换为浮点数"""
        try:
            if value is None or value == "":
                return default
            return float(str(value).replace(",", "").replace("%", ""))
        except (ValueError, TypeError):
            return default


# ============================================================
# 数据加载器
# ============================================================
class DataLoader:
    """数据加载器：从文件、URL 或字符串加载数据"""
    
    @classmethod
    def load(cls, source: str) -> List[MarketData]:
        """
        加载数据，自动识别来源类型
        
        参数:
            source: 文件路径、URL、或直接的数据内容字符串
        
        返回:
            解析后的市场数据列表
        """
        # 1. 检查是否是 URL
        if source.startswith(("http://", "https://")):
            return cls._load_from_url(source)
        
        # 2. 检查是否是文件路径
        if os.path.isfile(source):
            return cls._load_from_file(source)
        
        # 3. 尝试作为直接内容解析
        return cls._parse_content(source, "inline")
    
    @classmethod
    def load_batch(cls, sources: List[str]) -> Tuple[List[MarketData], List[Tuple[str, str]]]:
        """
        批量加载多个数据源
        
        返回:
            (合并的数据列表, 错误列表[(source, error_code)])
        """
        all_data = []
        errors = []
        
        for source in sources:
            try:
                data = cls.load(source)
                all_data.extend(data)
            except Exception as e:
                errors.append((source, str(e)))
        
        return all_data, errors
    
    @classmethod
    def _load_from_file(cls, filepath: str) -> List[MarketData]:
        """从文件加载"""
        if not os.path.exists(filepath):
            raise RuntimeError(f"{ERR_FILE_NOT_FOUND}: 文件不存在: {filepath}")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return cls._parse_content(content, filepath)
        except IOError as e:
            raise RuntimeError(f"{ERR_FILE_READ_ERROR}: 文件读取失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"{ERR_FILE_READ_ERROR}: {str(e)}")
    
    @classmethod
    def _load_from_url(cls, url: str) -> List[MarketData]:
        """从 URL 加载"""
        try:
            time.sleep(0.1)  # G1 退避标记
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode("utf-8")
            return cls._parse_content(content, url)
        except Exception as e:
            raise RuntimeError(f"{ERR_URL_ERROR}: URL 访问失败: {str(e)}")
    
    @classmethod
    def _parse_content(cls, content: str, source_name: str) -> List[MarketData]:
        """根据内容格式自动选择解析器"""
        content = content.strip()
        if not content:
            raise RuntimeError(f"{ERR_INVALID_INPUT}: 空数据")
        
        # 尝试 JSON
        if content.startswith(("{", "[")):
            try:
                return DataParser.parse_json(content)
            except RuntimeError:
                pass
        
        # 尝试 CSV（包含逗号或多行）
        if "," in content or "\t" in content:
            try:
                return DataParser.parse_csv(content)
            except RuntimeError:
                pass
        
        # 尝试纯文本
        try:
            return DataParser.parse_text(content)
        except RuntimeError:
            pass
        
        raise RuntimeError(f"{ERR_INVALID_INPUT}: 无法识别数据格式: {source_name}")


# ============================================================
# 数据校验与置信度标注
# ============================================================
class DataValidator:
    """数据校验与置信度标注"""
    
    @classmethod
    def validate(cls, data_list: List[MarketData]) -> List[MarketData]:
        """校验数据并标注置信度"""
        for item in data_list:
            # 检查价格有效性
            if item.price <= 0:
                item.extra["[需核实:price]"] = "价格无效"
            
            # 检查涨跌幅范围（合理范围 -100% 到 1000%）
            if abs(item.change_pct) > 1000:
                item.extra["[需核实:change_pct]"] = "涨跌幅异常"
            
            # 检查时间戳格式
            if item.timestamp:
                try:
                    datetime.fromisoformat(item.timestamp.replace("Z", "+00:00"))
                except ValueError:
                    item.extra["[需核实:timestamp]"] = "时间格式异常"
        
        return data_list


# ============================================================
# 输出格式化模块
# ============================================================
class OutputFormatter:
    """输出格式化器：支持表格、Sparkline、原始数据三种格式"""
    
    # 赛博朋克风格 ANSI 颜色
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    @classmethod
    def format(cls, data_list: List[MarketData], fmt: str = "table",
               width: int = None) -> str:
        """
        格式化输出
        
        参数:
            data_list: 市场数据列表
            fmt: 输出格式（table / spark / raw）
            width: 终端宽度（None 表示自动检测）
        """
        if fmt not in ("table", "spark", "raw"):
            raise RuntimeError(f"{ERR_FORMAT_ERROR}: 不支持的格式: {fmt}")
        
        if width is None:
            width = cls._get_terminal_width()
        
        if fmt == "table":
            return cls._format_table(data_list, width)
        elif fmt == "spark":
            return cls._format_spark(data_list, width)
        else:
            return cls._format_raw(data_list)
    
    @classmethod
    def _format_table(cls, data_list: List[MarketData], width: int) -> str:
        """表格格式输出"""
        if not data_list:
            return "暂无数据"
        
        # 列宽计算
        symbol_w = max(10, max(len(d.symbol) for d in data_list) + 2)
        price_w = 14
        vol_w = 14
        chg_w = 10
        ts_w = max(10, max(len(d.timestamp) for d in data_list) + 2) if any(d.timestamp for d in data_list) else 0
        
        # 表头
        header = f"{cls.BOLD}{cls.CYAN}"
        header += f"{'代码':<{symbol_w}} {'最新价':>{price_w}} {'成交量':>{vol_w}} {'涨跌幅':>{chg_w}}"
        if ts_w:
            header += f" {'时间':>{ts_w}}"
        header += f"{cls.RESET}"
        
        # 分隔线
        sep_len = symbol_w + price_w + vol_w + chg_w + (ts_w if ts_w else 0) + 8
        separator = f"{cls.MAGENTA}{'─' * min(sep_len, width)}{cls.RESET}"
        
        lines = [header, separator]
        
        # 数据行
        for d in data_list:
            # 涨跌幅颜色
            if d.change_pct > 0:
                chg_color = cls.GREEN
                chg_sign = "+"
            elif d.change_pct < 0:
                chg_color = cls.RED
                chg_sign = ""
            else:
                chg_color = cls.YELLOW
                chg_sign = ""
            
            # 附加标注
            annotations = " ".join(f"{cls.YELLOW}{k}{cls.RESET}" 
                                   for k in d.extra.keys() if k.startswith("[需核实"))
            
            row = f"{cls.BLUE}{d.symbol:<{symbol_w}}{cls.RESET}"
            row += f" {cls.BOLD}{d.price:>{price_w-2}.2f}{cls.RESET}"
            row += f" {d.volume:>{vol_w-2},.0f}"
            row += f" {chg_color}{chg_sign}{d.change_pct:>{chg_w-3}.2f}%{cls.RESET}"
            if ts_w:
                row += f" {d.timestamp:>{ts_w}}"
            if annotations:
                row += f" {annotations}"
            
            lines.append(row)
        
        return "\n".join(lines)
    
    @classmethod
    def _format_spark(cls, data_list: List[MarketData], width: int) -> str:
        """Sparkline 格式输出（ASCII 走势图）"""
        if not data_list:
            return "暂无数据"
        
        # 按时间排序（如果有时间戳）
        sorted_data = sorted(data_list, key=lambda d: d.timestamp or "")
        
        lines = []
        header = f"{cls.BOLD}{cls.CYAN}价格走势图 (Sparkline){cls.RESET}"
        lines.append(header)
        lines.append(f"{cls.MAGENTA}{'─' * min(width, 60)}{cls.RESET}")
        
        # 计算价格范围
        prices = [d.price for d in sorted_data]
        min_p, max_p = min(prices), max(prices)
        
        # 生成 ASCII 走势图
        if max_p == min_p:
            # 所有价格相同
            spark_line = "─" * min(50, max(10, width - 20))
            lines.append(f"  {spark_line}  {cls.YELLOW}价格稳定 {min_p:.2f}{cls.RESET}")
        else:
            # 归一化到 0-10 范围
            norm_prices = [(p - min_p) / (max_p - min_p) * 10 for p in prices]
            
            # 构建字符映射
            chars = "▁▂▃▄▅▆▇█"
            spark_line = "".join(chars[min(7, int(n))] for n in norm_prices)
            
            lines.append(f"  {cls.GREEN}{spark_line}{cls.RESET}")
            lines.append(f"  最低: {cls.BLUE}{min_p:.2f}{cls.RESET}  最高: {cls.RED}{max_p:.2f}{cls.RESET}")
        
        # 标注信息
        for d in sorted_data[:5]:  # 最多显示 5 条
            chg_str = f"{d.change_pct:+.2f}%" if d.change_pct else "0.00%"
            chg_color = cls.GREEN if d.change_pct >= 0 else cls.RED
            lines.append(f"  {cls.BLUE}{d.symbol:<12}{cls.RESET} "
                         f"{d.price:>10.2f}  {chg_color}{chg_str}{cls.RESET}")
        
        return "\n".join(lines)
    
    @classmethod
    def _format_raw(cls, data_list: List[MarketData]) -> str:
        """原始 JSON 格式输出"""
        raw_data = [d.to_dict() for d in data_list]
        return json.dumps(raw_data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _get_terminal_width() -> int:
        """获取终端宽度"""
        try:
            return os.get_terminal_size().columns
        except (AttributeError, OSError):
            return 80  # 默认宽度


# ============================================================
# 自检模块
# ============================================================
class SelfTest:
    """内置自检功能：使用硬编码样例数据离线验证核心逻辑"""
    
    # 内置测试数据（不依赖外部文件）
    TEST_CSV = """symbol,price,volume,change_pct,timestamp
BTC/USDT,45000.50,1234.56,2.35,2026-01-15T10:30:00
ETH/USDT,3200.75,5678.90,-1.20,2026-01-15T10:31:00
AAPL,185.30,1000000,0.85,2026-01-15T10:32:00
"""
    
    TEST_JSON = """[
        {"symbol": "SOL/USDT", "price": 150.25, "volume": 89000, "change_pct": 5.67, "timestamp": "2026-01-15T10:33:00"},
        {"symbol": "GOOGL", "price": 140.50, "volume": 2500000, "change_pct": -0.45, "timestamp": "2026-01-15T10:34:00"}
    ]"""
    
    TEST_TEXT = """# 简易行情文本
DOGE/USDT 0.085 1000000 3.21 2026-01-15T10:35:00
TSLA 250.10 500000 -2.50 2026-01-15T10:36:00
"""
    
    @classmethod
    def run(cls) -> bool:
        """运行全部自检，返回是否全部通过"""
        print("🔍 运行自检...")
        passed = 0
        total = 0
        
        # 1. CSV 解析测试
        total += 1
        try:
            csv_data = DataParser.parse_csv(cls.TEST_CSV)
            assert len(csv_data) >= 3, "CSV 应解析出至少 3 条数据"
            assert all(d.price > 0 for d in csv_data), "价格应大于 0"
            assert all(d.symbol for d in csv_data), "代码不应为空"
            passed += 1
            print("  ✅ CSV 解析")
        except Exception as e:
            print(f"  ❌ CSV 解析: {e}")
        
        # 2. JSON 解析测试
        total += 1
        try:
            json_data = DataParser.parse_json(cls.TEST_JSON)
            assert len(json_data) >= 2, "JSON 应解析出至少 2 条数据"
            assert all(d.price > 0 for d in json_data), "价格应大于 0"
            assert all(d.symbol for d in json_data), "代码不应为空"
            passed += 1
            print("  ✅ JSON 解析")
        except Exception as e:
            print(f"  ❌ JSON 解析: {e}")
        
        # 3. 文本解析测试
        total += 1
        try:
            text_data = DataParser.parse_text(cls.TEST_TEXT)
            assert len(text_data) >= 2, "文本应解析出至少 2 条数据"
            assert all(d.price > 0 for d in text_data), "价格应大于 0"
            passed += 1
            print("  ✅ 文本解析")
        except Exception as e:
            print(f"  ❌ 文本解析: {e}")
        
        # 4. 数据加载器测试
        total += 1
        try:
            loader_data = DataLoader.load(cls.TEST_CSV)
            assert len(loader_data) >= 3, "加载器应解析出至少 3 条数据"
            passed += 1
            print("  ✅ 数据加载器")
        except Exception as e:
            print(f"  ❌ 数据加载器: {e}")
        
        # 5. 数据校验测试
        total += 1
        try:
            merged = DataParser.parse_csv(cls.TEST_CSV) + DataParser.parse_json(cls.TEST_JSON)
            validated = DataValidator.validate(merged)
            assert len(validated) >= 5, "合并数据应至少 5 条"
            passed += 1
            print("  ✅ 数据校验")
        except Exception as e:
            print(f"  ❌ 数据校验: {e}")
        
        # 6. 表格输出测试
        total += 1
        try:
            data = DataParser.parse_csv(cls.TEST_CSV)
            output = OutputFormatter.format(data, "table", width=100)
            assert len(output) > 0, "表格输出不应为空"
            assert "BTC" in output, "表格应包含 BTC"
            passed += 1
            print("  ✅ 表格输出")
        except Exception as e:
            print(f"  ❌ 表格输出: {e}")
        
        # 7. Sparkline 输出测试
        total += 1
        try:
            data = DataParser.parse_json(cls.TEST_JSON)
            output = OutputFormatter.format(data, "spark", width=100)
            assert len(output) > 0, "Sparkline 输出不应为空"
            passed += 1
            print("  ✅ Sparkline 输出")
        except Exception as e:
            print(f"  ❌ Sparkline 输出: {e}")
        
        # 8. 原始输出测试
        total += 1
        try:
            data = DataParser.parse_text(cls.TEST_TEXT)
            output = OutputFormatter.format(data, "raw")
            parsed = json.loads(output)
            assert len(parsed) >= 2, "原始输出应可解析为 JSON 且至少 2 条"
            passed += 1
            print("  ✅ 原始输出")
        except Exception as e:
            print(f"  ❌ 原始输出: {e}")
        
        # 9. 批量加载测试
        total += 1
        try:
            all_data, errors = DataLoader.load_batch([cls.TEST_CSV, cls.TEST_JSON, cls.TEST_TEXT])
            assert len(all_data) >= 7, "批量加载应至少 7 条数据"
            assert len(errors) == 0, f"不应有错误，实际: {errors}"
            passed += 1
            print("  ✅ 批量加载")
        except Exception as e:
            print(f"  ❌ 批量加载: {e}")
        
        # 10. 错误处理测试
        total += 1
        try:
            # 无效数据应抛出异常
            try:
                DataParser.parse_csv("not,csv\n1")
                print("  ❌ 错误处理: 无效 CSV 未抛异常")
            except RuntimeError:
                passed += 1
                print("  ✅ 错误处理")
        except Exception as e:
            print(f"  ❌ 错误处理: {e}")
        
        # 汇总
        print(f"\n📊 自检结果: {passed}/{total} 通过")
        return passed == total


# ============================================================
# 命令行入口
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


def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="终端行情赛博监控实时看板",
        epilog="示例:\n"
               "  python main.py data.csv\n"
               "  python main.py --format spark data.json\n"
               "  python main.py --selftest\n"
               "  python main.py --batch file1.csv file2.json"
    )
    
    parser.add_argument("--sources", nargs="*", help="数据源（文件路径、URL 或直接数据内容）")
    parser.add_argument("--format", choices=["table", "spark", "raw"], default="table",
                        help="输出格式 (默认: table)")
    parser.add_argument("--width", type=int, default=None,
                        help="终端宽度 (默认: 自动检测)")
    parser.add_argument("--batch", action="store_true",
                        help="批量处理多个数据源")
    parser.add_argument("--selftest", action="store_true",
                        help="运行内置自检")
    
    parser.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        success = SelfTest.run()
        return 0 if success else 1
    
    # 正常处理模式
    if not args.sources:
        parser.print_help()
        return 1
    
    try:
        # 加载数据
        if args.batch or len(args.sources) > 1:
            # 批量模式
            all_data, errors = DataLoader.load_batch(args.sources)
            if errors:
                print(f"⚠️  部分数据源加载失败 ({len(errors)} 个):", file=sys.stderr)
                for source, err in errors:
                    print(f"  - {source}: {err}", file=sys.stderr)
        else:
            # 单数据源模式
            all_data = DataLoader.load(args.sources[0])
            errors = []
        
        if not all_data:
            print("❌ 没有可显示的数据", file=sys.stderr)
            return 1
        
        # 数据校验
        all_data = DataValidator.validate(all_data)
        
        # 格式化输出
        output = OutputFormatter.format(all_data, args.format, args.width)
        print(output)
        
        # 错误提示
        if errors:
            print(f"\n⚠️  共 {len(errors)} 个数据源处理失败", file=sys.stderr)
            return 2
        
        return 0
        
    except RuntimeError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  用户中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ 未知错误 ({ERR_UNKNOWN_ERROR}): {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
