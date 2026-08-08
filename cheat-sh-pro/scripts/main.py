#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""血缘关系分析工具 - 冒烟测试修复版"""

import json
import sys
import os
from datetime import datetime
from collections import defaultdict

class LineageAnalyzer:
    """血缘关系分析器"""
    
    def __init__(self):
        self.tables = {}  # 表名 -> 表信息
        self.columns = {}  # 表名.列名 -> 列信息
        self.lineage = []  # 血缘关系列表
        
    def add_table(self, name, database="default", schema="default"):
        """添加表"""
        self.tables[name] = {
            "name": name,
            "database": database,
            "schema": schema,
            "created_at": datetime.now().isoformat()
        }
        
    def add_column(self, table, column, data_type="string", comment=""):
        """添加列"""
        key = f"{table}.{column}"
        self.columns[key] = {
            "table": table,
            "column": column,
            "data_type": data_type,
            "comment": comment
        }
        
    def add_lineage(self, source_table, source_column, target_table, target_column, transform=""):
        """添加血缘关系"""
        relation = {
            "source": {
                "table": source_table,
                "column": source_column
            },
            "target": {
                "table": target_table,
                "column": target_column
            },
            "transform": transform,
            "created_at": datetime.now().isoformat()
        }
        self.lineage.append(relation)
        return relation
        
    def get_table_lineage(self, table_name):
        """获取表的血缘关系"""
        result = []
        for rel in self.lineage:
            if rel["source"]["table"] == table_name or rel["target"]["table"] == table_name:
                result.append(rel)
        return result
        
    def get_column_lineage(self, table_name, column_name):
        """获取列的血缘关系"""
        result = []
        for rel in self.lineage:
            if (rel["source"]["table"] == table_name and rel["source"]["column"] == column_name) or \
               (rel["target"]["table"] == table_name and rel["target"]["column"] == column_name):
                result.append(rel)
        return result
        
    def analyze_sql(self, sql):
        """分析SQL语句中的血缘关系"""
        # 简化版SQL解析
        sql_lower = sql.lower()
        
        # 提取INSERT INTO目标表
        insert_match = sql_lower.find("insert into")
        if insert_match >= 0:
            rest = sql[insert_match + 11:].strip()
            target_table = rest.split()[0].strip('`"\'')
            
            # 提取SELECT源表
            select_match = sql_lower.find("select")
            from_match = sql_lower.find("from")
            if select_match >= 0 and from_match > select_match:
                # 简单提取FROM后的表名
                from_part = sql[from_match + 4:].strip()
                # 分割可能的多个表
                source_tables = []
                for part in from_part.split(','):
                    table_name = part.strip().split()[0].strip('`"\'')
                    if table_name and table_name != 'where':
                        source_tables.append(table_name)
                
                # 添加血缘关系
                for source_table in source_tables:
                    if source_table != target_table:
                        self.add_lineage(
                            source_table, "*",
                            target_table, "*",
                            f"INSERT INTO {target_table} SELECT FROM {source_table}"
                        )
                return len(source_tables)
        return 0

def run_selftest():
    """运行自测"""
    print("[RUN] 开始自测...")
    
    # 创建分析器
    analyzer = LineageAnalyzer()
    
    # 添加测试表
    analyzer.add_table("ods_user")
    analyzer.add_table("dwd_user_info")
    analyzer.add_table("ads_user_stats")
    
    # 添加测试列
    analyzer.add_column("ods_user", "user_id", "bigint", "用户ID")
    analyzer.add_column("ods_user", "user_name", "string", "用户名")
    analyzer.add_column("dwd_user_info", "user_id", "bigint", "用户ID")
    analyzer.add_column("dwd_user_info", "user_name", "string", "用户名")
    analyzer.add_column("ads_user_stats", "total_users", "bigint", "总用户数")
    
    # 添加血缘关系
    analyzer.add_lineage("ods_user", "user_id", "dwd_user_info", "user_id", "直接映射")
    analyzer.add_lineage("ods_user", "user_name", "dwd_user_info", "user_name", "直接映射")
    analyzer.add_lineage("dwd_user_info", "*", "ads_user_stats", "*", "聚合计算")
    
    # 测试1: 血缘关系数量
    relations1 = analyzer.lineage
    assert len(relations1) > 0, "测试1失败: 未产生任何血缘关系"
    print(f"[PASS] 测试1: 血缘关系数量 = {len(relations1)}")
    
    # 测试2: 表血缘查询
    table_lineage = analyzer.get_table_lineage("dwd_user_info")
    assert len(table_lineage) > 0, "测试2失败: 未找到表血缘关系"
    print(f"[PASS] 测试2: 表血缘关系数量 = {len(table_lineage)}")
    
    # 测试3: 列血缘查询
    column_lineage = analyzer.get_column_lineage("ods_user", "user_id")
    assert len(column_lineage) > 0, "测试3失败: 未找到列血缘关系"
    print(f"[PASS] 测试3: 列血缘关系数量 = {len(column_lineage)}")
    
    # 测试4: SQL解析
    sql = "INSERT INTO dwd_user_info SELECT user_id, user_name FROM ods_user WHERE user_id > 100"
    sql_count = analyzer.analyze_sql(sql)
    assert sql_count > 0, "测试4失败: SQL解析未产生血缘关系"
    print(f"[PASS] 测试4: SQL解析产生血缘关系数量 = {sql_count}")
    
    # 测试5: 数据完整性
    assert len(analyzer.tables) >= 3, "测试5失败: 表数量不足"
    assert len(analyzer.columns) >= 5, "测试5失败: 列数量不足"
    print(f"[PASS] 测试5: 数据完整性验证通过")
    
    print("[PASS] 所有测试通过!")

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        run_selftest()
        return 0
    
    # 正常模式 - 分析示例SQL
    analyzer = LineageAnalyzer()
    
    # 添加示例表
    analyzer.add_table("ods_orders")
    analyzer.add_table("dwd_order_details")
    analyzer.add_table("ads_order_stats")
    
    # 示例SQL
    sql1 = "INSERT INTO dwd_order_details SELECT order_id, product_id, amount FROM ods_orders"
    sql2 = "INSERT INTO ads_order_stats SELECT product_id, COUNT(*) as cnt, SUM(amount) as total FROM dwd_order_details GROUP BY product_id"
    
    analyzer.analyze_sql(sql1)
    analyzer.analyze_sql(sql2)
    
    # 输出结果
    print("=" * 60)
    print("血缘关系分析结果")
    print("=" * 60)
    
    print("\n[表信息]")
    for table_name, table_info in analyzer.tables.items():
        print(f"  表: {table_name} (数据库: {table_info['database']})")
    
    print("\n[血缘关系]")
    for i, rel in enumerate(analyzer.lineage, 1):
        source = f"{rel['source']['table']}.{rel['source']['column']}"
        target = f"{rel['target']['table']}.{rel['target']['column']}"
        print(f"  {i}. {source} -> {target}")
        if rel['transform']:
            print(f"     转换: {rel['transform']}")
    
    print("\n[血缘查询示例]")
    print("  查询 dwd_order_details 的血缘关系:")
    for rel in analyzer.get_table_lineage("dwd_order_details"):
        print(f"    {rel['source']['table']}.{rel['source']['column']} -> "
              f"{rel['target']['table']}.{rel['target']['column']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
