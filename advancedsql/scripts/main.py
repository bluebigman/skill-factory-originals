#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQL 方言转换工具：支持 MySQL/PostgreSQL/Oracle 方言互转"""

import argparse
import sys
from pathlib import Path


def read_text_safe(path):
    """带编码兜底的文本读取器（R3 编码兜底）"""
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


def load_rows(path):
    """读取 SQL 文件，按行解析（R2 异常降级 + R5 流式读取）"""
    try:
        rows = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("--"):
                    rows.append(line)
        return rows
    except Exception as e:
        print(f"[WARN] 解析 {path} 失败，降级为空集: {e}", file=sys.stderr)
        return []


def convert_sql(sql_text, source_dialect, target_dialect):
    """核心转换逻辑：返回 (转换后文本, 变更列表)"""
    changed_items = []
    lines = sql_text.splitlines()
    converted_lines = []
    skipped = 0

    for idx, line in enumerate(lines, 1):
        original = line
        converted = line

        # 方言差异转换规则
        if source_dialect == "mysql" and target_dialect == "postgresql":
            # MySQL 反引号 -> PostgreSQL 双引号
            if "`" in converted:
                converted = converted.replace("`", '"')
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # MySQL AUTO_INCREMENT -> PostgreSQL SERIAL
            if "AUTO_INCREMENT" in converted.upper():
                converted = converted.replace("AUTO_INCREMENT", "SERIAL")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # MySQL TINYINT(1) -> PostgreSQL BOOLEAN
            if "TINYINT(1)" in converted.upper():
                converted = converted.replace("TINYINT(1)", "BOOLEAN")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        elif source_dialect == "postgresql" and target_dialect == "mysql":
            # PostgreSQL 双引号 -> MySQL 反引号
            if '"' in converted and not converted.startswith('"'):
                converted = converted.replace('"', '`')
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # PostgreSQL SERIAL -> MySQL AUTO_INCREMENT
            if "SERIAL" in converted.upper():
                converted = converted.replace("SERIAL", "AUTO_INCREMENT")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # PostgreSQL BOOLEAN -> MySQL TINYINT(1)
            if "BOOLEAN" in converted.upper():
                converted = converted.replace("BOOLEAN", "TINYINT(1)")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        elif source_dialect == "oracle" and target_dialect == "postgresql":
            # Oracle VARCHAR2 -> PostgreSQL VARCHAR
            if "VARCHAR2" in converted.upper():
                converted = converted.replace("VARCHAR2", "VARCHAR")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # Oracle NUMBER -> PostgreSQL NUMERIC
            if "NUMBER" in converted.upper():
                converted = converted.replace("NUMBER", "NUMERIC")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        elif source_dialect == "postgresql" and target_dialect == "oracle":
            # PostgreSQL VARCHAR -> Oracle VARCHAR2
            if "VARCHAR" in converted.upper() and "VARCHAR2" not in converted.upper():
                converted = converted.replace("VARCHAR", "VARCHAR2")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # PostgreSQL NUMERIC -> Oracle NUMBER
            if "NUMERIC" in converted.upper():
                converted = converted.replace("NUMERIC", "NUMBER")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        elif source_dialect == "mysql" and target_dialect == "oracle":
            # MySQL 反引号 -> Oracle 无引号
            if "`" in converted:
                converted = converted.replace("`", "")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # MySQL AUTO_INCREMENT -> Oracle SEQUENCE 提示
            if "AUTO_INCREMENT" in converted.upper():
                converted = converted.replace("AUTO_INCREMENT", "GENERATED BY DEFAULT AS IDENTITY")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        elif source_dialect == "oracle" and target_dialect == "mysql":
            # Oracle 无引号 -> MySQL 反引号
            if "GENERATED BY DEFAULT AS IDENTITY" in converted.upper():
                converted = converted.replace("GENERATED BY DEFAULT AS IDENTITY", "AUTO_INCREMENT")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
            # Oracle VARCHAR2 -> MySQL VARCHAR
            if "VARCHAR2" in converted.upper():
                converted = converted.replace("VARCHAR2", "VARCHAR")
                changed_items.append({
                    "name": f"line_{idx}",
                    "before": original,
                    "after": converted
                })
        else:
            skipped += 1

        converted_lines.append(converted)

    return "\n".join(converted_lines), changed_items, skipped


def save(path, data, dry_run=False):
    """写盘函数（R4 预览撤回）"""
    if not dry_run:
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(path)
        print(f"[写入] {path}")
        return True
    print(f"[dry-run] 将写入 {path}（{len(data)} 字节），未落盘")
    return False


def _selftest():
    """自测契约（R1 契约先于代码）"""
    print("[selftest] 开始自测...")

    # 测试用例 1：MySQL -> PostgreSQL
    mysql_sql = "CREATE TABLE `users` (id INT AUTO_INCREMENT PRIMARY KEY, active TINYINT(1));"
    converted, changed, skipped = convert_sql(mysql_sql, "mysql", "postgresql")
    assert '"users"' in converted, "MySQL 反引号未转换为 PostgreSQL 双引号"
    assert "SERIAL" in converted, "AUTO_INCREMENT 未转换为 SERIAL"
    assert "BOOLEAN" in converted, "TINYINT(1) 未转换为 BOOLEAN"
    assert len(changed) == 3, f"MySQL->PG 应有 3 处变更，实际 {len(changed)}"
    assert skipped == 0, f"MySQL->PG 不应有跳过，实际 {skipped}"

    # 测试用例 2：PostgreSQL -> MySQL
    pg_sql = 'CREATE TABLE "users" (id SERIAL PRIMARY KEY, active BOOLEAN);'
    converted, changed, skipped = convert_sql(pg_sql, "postgresql", "mysql")
    assert "`users`" in converted, "PostgreSQL 双引号未转换为 MySQL 反引号"
    assert "AUTO_INCREMENT" in converted, "SERIAL 未转换为 AUTO_INCREMENT"
    assert "TINYINT(1)" in converted, "BOOLEAN 未转换为 TINYINT(1)"
    assert len(changed) == 3, f"PG->MySQL 应有 3 处变更，实际 {len(changed)}"
    assert skipped == 0, f"PG->MySQL 不应有跳过，实际 {skipped}"

    # 测试用例 3：Oracle -> PostgreSQL
    oracle_sql = "CREATE TABLE users (id NUMBER PRIMARY KEY, name VARCHAR2(100));"
    converted, changed, skipped = convert_sql(oracle_sql, "oracle", "postgresql")
    assert "NUMERIC" in converted, "NUMBER 未转换为 NUMERIC"
    assert "VARCHAR" in converted and "VARCHAR2" not in converted, "VARCHAR2 未转换为 VARCHAR"
    assert len(changed) == 2, f"Oracle->PG 应有 2 处变更，实际 {len(changed)}"
    assert skipped == 0, f"Oracle->PG 不应有跳过，实际 {skipped}"

    # 测试用例 4：PostgreSQL -> Oracle
    pg_sql2 = "CREATE TABLE users (id NUMERIC PRIMARY KEY, name VARCHAR(100));"
    converted, changed, skipped = convert_sql(pg_sql2, "postgresql", "oracle")
    assert "NUMBER" in converted, "NUMERIC 未转换为 NUMBER"
    assert "VARCHAR2" in converted, "VARCHAR 未转换为 VARCHAR2"
    assert len(changed) == 2, f"PG->Oracle 应有 2 处变更，实际 {len(changed)}"
    assert skipped == 0, f"PG->Oracle 不应有跳过，实际 {skipped}"

    # 测试用例 5：MySQL -> Oracle
    mysql_sql2 = "CREATE TABLE `users` (id INT AUTO_INCREMENT PRIMARY KEY);"
    converted, changed, skipped = convert_sql(mysql_sql2, "mysql", "oracle")
    assert "users" in converted and "`" not in converted, "MySQL 反引号未去除"
    assert "GENERATED BY DEFAULT AS IDENTITY" in converted, "AUTO_INCREMENT 未转换"
    assert len(changed) == 2, f"MySQL->Oracle 应有 2 处变更，实际 {len(changed)}"
    assert skipped == 0, f"MySQL->Oracle 不应有跳过，实际 {skipped}"

    # 测试用例 6：Oracle -> MySQL
    oracle_sql2 = "CREATE TABLE users (id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, name VARCHAR2(100));"
    converted, changed, skipped = convert_sql(oracle_sql2, "oracle", "mysql")
    assert "AUTO_INCREMENT" in converted, "Oracle 标识列未转换为 AUTO_INCREMENT"
    assert "VARCHAR" in converted and "VARCHAR2" not in converted, "VARCHAR2 未转换为 VARCHAR"
    assert len(changed) == 2, f"Oracle->MySQL 应有 2 处变更，实际 {len(changed)}"
    assert skipped == 0, f"Oracle->MySQL 不应有跳过，实际 {skipped}"

    # 测试用例 7：相同方言不转换
    same_sql = "CREATE TABLE users (id INT PRIMARY KEY);"
    converted, changed, skipped = convert_sql(same_sql, "mysql", "mysql")
    assert converted == same_sql, "相同方言不应转换"
    assert len(changed) == 0, f"相同方言不应有变更，实际 {len(changed)}"
    assert skipped == 1, f"相同方言应跳过 1 行，实际 {skipped}"

    # 测试用例 8：save 函数 dry-run 模式
    test_path = Path("_selftest_output.sql")
    result = save(str(test_path), "test content", dry_run=True)
    assert result is False, "dry-run 应返回 False"
    assert not test_path.exists(), "dry-run 不应创建文件"

    # 测试用例 9：save 函数实际写入
    result = save(str(test_path), "test content", dry_run=False)
    assert result is True, "实际写入应返回 True"
    assert test_path.exists(), "实际写入应创建文件"
    content = read_text_safe(str(test_path))
    assert content == "test content", "写入内容不一致"
    test_path.unlink()  # 清理

    # 测试用例 10：read_text_safe 编码兜底
    test_enc_path = Path("_selftest_enc.sql")
    test_enc_path.write_bytes("中文测试".encode("gbk"))
    content = read_text_safe(str(test_enc_path))
    assert "中文测试" in content, "GBK 编码读取失败"
    test_enc_path.unlink()

    print("[selftest] 全部 10 项测试通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description="SQL 方言转换工具")
    ap.add_argument("--input", help="输入 SQL 文件路径")
    ap.add_argument("--output", help="输出 SQL 文件路径（默认 stdout）")
    ap.add_argument("--source", choices=["mysql", "postgresql", "oracle"], default="mysql", help="源方言")
    ap.add_argument("--target", choices=["mysql", "postgresql", "oracle"], default="postgresql", help="目标方言")
    ap.add_argument("--selftest", action="store_true", help="运行自测")
    ap.add_argument("--dry-run", action="store_true", help="预览模式，不实际写盘")
    ap.add_argument("--verbose", action="store_true", help="显示详细转换明细")
    args = ap.parse_args()

    # selftest 必须在所有必填校验之前
    if args.selftest:
        return _selftest()

    # 业务参数校验
    if args.input is None:
        ap.error("--input 为必填参数")

    # 读取输入
    sql_text = read_text_safe(args.input)
    if not sql_text:
        print(f"[WARN] 输入文件 {args.input} 为空或读取失败", file=sys.stderr)
        return 1

    # 执行转换
    converted, changed_items, skipped = convert_sql(sql_text, args.source, args.target)

    # 输出明细（R6 可解释输出）
    if args.verbose:
        for idx, item in enumerate(changed_items, 1):
            print(f"[明细] {idx}. {item['name']}: {item['before']} -> {item['after']}")
    print(f"[汇总] changed={len(changed_items)} 项，skipped={skipped} 项")

    # 输出结果
    if args.output:
        save(args.output, converted, dry_run=args.dry_run)
    else:
        print(converted)

    return 0


if __name__ == "__main__":
    sys.exit(main())
