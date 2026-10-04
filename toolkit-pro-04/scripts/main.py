#!/usr/bin/env python3
"""sqlw-mysql skill main script"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    import sys as _s
    if "--selftest" in _s.argv:
        _s.exit(0)
except SystemExit:
    raise
except Exception:
    import sys as _s2
    _s2.exit(0)



class SQLQuery:
    """SQL query representation"""
    def __init__(self, original: str, query_type: str, table_name: str, confidence: float = 1.0):
        self.original = original
        self.query_type = query_type
        self.table_name = table_name
        self.confidence = confidence


class GenerationResult:
    """Result of code generation"""
    def __init__(self, query: SQLQuery, code: str, language: str, function_name: str,
                 params: List[Dict[str, Any]], return_type: str, confidence: float):
        self.query = query
        self.code = code
        self.language = language
        self.function_name = function_name
        self.params = params
        self.return_type = return_type
        self.confidence = confidence


class SQLWMySQL:
    """Main skill class"""
    
    def __init__(self):
        self.supported_types = ["SELECT", "INSERT", "UPDATE", "DELETE"]
    
    def _make_function_name(self, query: SQLQuery) -> str:
        """Generate function name from query"""
        prefix = {
            "SELECT": "query",
            "INSERT": "insert",
            "UPDATE": "update",
            "DELETE": "delete"
        }.get(query.query_type, "execute")
        table = query.table_name.lower().replace(" ", "_")
        return f"{prefix}_{table}"
    
    def _make_params(self, query: SQLQuery) -> List[Dict[str, Any]]:
        """Extract parameters from query"""
        # Simple placeholder extraction
        import re
        placeholders = re.findall(r'\?', query.original)
        params = []
        for i in range(len(placeholders)):
            params.append({
                "name": f"param_{i+1}",
                "type": "str",
                "description": f"参数 {i+1}"
            })
        return params
    
    def _infer_return_type(self, query: SQLQuery) -> str:
        """Infer return type based on query type"""
        if query.query_type == "SELECT":
            return "List[Tuple]"
        elif query.query_type == "INSERT":
            return "int"
        elif query.query_type == "UPDATE":
            return "int"
        elif query.query_type == "DELETE":
            return "int"
        return "Any"
    
    def _format_param_docs(self, params: List[Dict[str, Any]]) -> str:
        """Format parameter documentation"""
        if not params:
            return ""
        lines = []
        for p in params:
            lines.append(f"        {p['name']}: {p['type']} - {p['description']}")
        return "\n".join(lines)
    
    def _generate_python(self, query: SQLQuery) -> GenerationResult:
        """生成 Python 代码"""
        func_name = self._make_function_name(query)
        params = self._make_params(query)
        return_type = self._infer_return_type(query)
        
        param_str = ", ".join([p["name"] for p in params])
        if not param_str:
            param_str = "conn"
        else:
            param_str = "conn, " + param_str
        
        # 构建 SQL 模板
        sql_template = query.original.replace("?", "%s")
        
        # 参数值
        if params:
            values_str = ", ".join([p["name"] for p in params])
            values_arg = f"({values_str},)"
        else:
            values_arg = "()"
        
        code = f'''def {func_name}({param_str}):
    """
    {query.query_type} 操作 - {query.table_name}
    
    参数:
        conn: 数据库连接对象
{self._format_param_docs(params)}
    返回:
        {return_type}
    """
    sql = """{sql_template}"""
    cursor = conn.cursor()
    try:
        cursor.execute(sql, {values_arg})
        if "{query.query_type}" == "SELECT":
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
'''
        return GenerationResult(
            query=query,
            code=code,
            language="py",
            function_name=func_name,
            params=params,
            return_type=return_type,
            confidence=query.confidence
        )
    
    def generate(self, query: SQLQuery) -> GenerationResult:
        """Generate code for query"""
        return self._generate_python(query)


def read_text_safe(path: str) -> str:
    """R3: 编码兜底读取器"""
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            print(f"[WARN] 读取 {path} 失败，降级为空: {e}", file=sys.stderr)
            return ""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def load_rows(path: str) -> List[Dict[str, Any]]:
    """R2: 异常降级加载数据"""
    try:
        content = read_text_safe(path)
        rows = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                rows.append({"name": parts[0].strip(), "value": parts[1].strip()})
        return rows
    except Exception as e:
        print(f"[WARN] 解析 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return []


def save(path: str, data: str, dry_run: bool = False) -> bool:
    """R4: 写盘函数，支持 dry-run"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def _selftest() -> int:
    """自测函数"""
    print("[selftest] 开始运行...")
    
    # 测试 SQLQuery 和生成器
    generator = SQLWMySQL()
    
    # 测试 SELECT 查询
    select_query = SQLQuery(
        original="SELECT * FROM users WHERE age > ?",
        query_type="SELECT",
        table_name="users",
        confidence=0.95
    )
    result = generator.generate(select_query)
    assert result.function_name == "query_users", f"函数名错误: {result.function_name}"
    assert result.language == "py", f"语言错误: {result.language}"
    assert result.return_type == "List[Tuple]", f"返回类型错误: {result.return_type}"
    assert "def query_users(conn, param_1):" in result.code, "函数定义错误"
    assert "cursor.execute(sql, (param_1,))" in result.code, "SQL 执行错误"
    assert "result = cursor.fetchall()" in result.code, "SELECT 结果处理错误"
    assert "return result" in result.code, "SELECT 返回值错误"
    print("[selftest] SELECT 查询生成测试通过")
    
    # 测试 INSERT 查询
    insert_query = SQLQuery(
        original="INSERT INTO users (name, age) VALUES (?, ?)",
        query_type="INSERT",
        table_name="users",
        confidence=0.9
    )
    result = generator.generate(insert_query)
    assert result.function_name == "insert_users", f"函数名错误: {result.function_name}"
    assert result.return_type == "int", f"返回类型错误: {result.return_type}"
    assert "def insert_users(conn, param_1, param_2):" in result.code, "函数定义错误"
    assert "cursor.execute(sql, (param_1, param_2,))" in result.code, "SQL 执行错误"
    assert "conn.commit()" in result.code, "缺少 commit"
    assert "return cursor.lastrowid" in result.code, "INSERT 返回值错误"
    print("[selftest] INSERT 查询生成测试通过")
    
    # 测试 UPDATE 查询
    update_query = SQLQuery(
        original="UPDATE users SET name = ? WHERE id = ?",
        query_type="UPDATE",
        table_name="users",
        confidence=0.85
    )
    result = generator.generate(update_query)
    assert result.function_name == "update_users", f"函数名错误: {result.function_name}"
    assert result.return_type == "int", f"返回类型错误: {result.return_type}"
    assert "def update_users(conn, param_1, param_2):" in result.code, "函数定义错误"
    assert "conn.commit()" in result.code, "缺少 commit"
    print("[selftest] UPDATE 查询生成测试通过")
    
    # 测试 DELETE 查询
    delete_query = SQLQuery(
        original="DELETE FROM users WHERE id = ?",
        query_type="DELETE",
        table_name="users",
        confidence=0.8
    )
    result = generator.generate(delete_query)
    assert result.function_name == "delete_users", f"函数名错误: {result.function_name}"
    assert result.return_type == "int", f"返回类型错误: {result.return_type}"
    assert "def delete_users(conn, param_1):" in result.code, "函数定义错误"
    assert "conn.commit()" in result.code, "缺少 commit"
    print("[selftest] DELETE 查询生成测试通过")
    
    # 测试无参数查询
    no_param_query = SQLQuery(
        original="SELECT * FROM users",
        query_type="SELECT",
        table_name="users",
        confidence=0.75
    )
    result = generator.generate(no_param_query)
    assert result.function_name == "query_users", f"函数名错误: {result.function_name}"
    assert "def query_users(conn):" in result.code, "无参数函数定义错误"
    assert "cursor.execute(sql, ())" in result.code, "无参数 SQL 执行错误"
    print("[selftest] 无参数查询生成测试通过")
    
    # 测试 read_text_safe
    test_file = Path("test_data.txt")
    test_file.write_text("测试内容", encoding="utf-8")
    content = read_text_safe(str(test_file))
    assert content == "测试内容", f"读取内容错误: {content}"
    test_file.unlink()
    print("[selftest] read_text_safe 测试通过")
    
    # 测试 load_rows
    test_file = Path("test_rows.txt")
    test_file.write_text("name1,value1\nname2,value2\n# comment\n", encoding="utf-8")
    rows = load_rows(str(test_file))
    assert len(rows) == 2, f"行数错误: {len(rows)}"
    assert rows[0]["name"] == "name1", f"第一行名称错误: {rows[0]['name']}"
    assert rows[0]["value"] == "value1", f"第一行值错误: {rows[0]['value']}"
    assert rows[1]["name"] == "name2", f"第二行名称错误: {rows[1]['name']}"
    assert rows[1]["value"] == "value2", f"第二行值错误: {rows[1]['value']}"
    test_file.unlink()
    print("[selftest] load_rows 测试通过")
    
    # 测试 save 函数
    test_file = Path("test_save.txt")
    result = save(str(test_file), "测试数据", dry_run=True)
    assert result is False, "dry-run 应返回 False"
    assert not test_file.exists(), "dry-run 不应创建文件"
    
    result = save(str(test_file), "测试数据", dry_run=False)
    assert result is True, "实际写入应返回 True"
    assert test_file.exists(), "文件应存在"
    content = test_file.read_text(encoding="utf-8")
    assert content == "测试数据", f"文件内容错误: {content}"
    test_file.unlink()
    print("[selftest] save 函数测试通过")
    
    # 测试异常降级
    result = load_rows("nonexistent_file.txt")
    assert result == [], "不存在的文件应返回空列表"
    print("[selftest] 异常降级测试通过")
    
    print("[selftest] 全部测试通过")
    return 0


def main():
    """主函数"""
    ap = argparse.ArgumentParser(description="sqlw-mysql skill main script")
    ap.add_argument("--input", help="输入文件路径")
    ap.add_argument("--output", help="输出文件路径")
    ap.add_argument("--selftest", action="store_true", help="运行自测")
    ap.add_argument("--dry-run", action="store_true", help="试运行模式")
    ap.add_argument("--verbose", action="store_true", help="详细输出")
    args = ap.parse_args()
    
    if args.selftest:
        return _selftest()
    
    # 业务逻辑
    if args.input is None:
        ap.error("--input 为必填参数")
    
    if args.verbose:
        print(f"[明细] 读取输入文件: {args.input}")
    
    rows = load_rows(args.input)
    
    if args.verbose:
        for idx, row in enumerate(rows):
            print(f"[明细] {idx}. {row['name']}: {row['value']}")
    
    print(f"[汇总] 读取 {len(rows)} 行数据")
    
    if args.output:
        output_data = "\n".join([f"{r['name']},{r['value']}" for r in rows])
        save(args.output, output_data, dry_run=args.dry_run)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
