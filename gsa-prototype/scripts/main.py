#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GSA Prototype - 政府网站分析原型系统"""

import json
import re
import sys
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from collections import Counter, defaultdict

class GSAAnalyzer:
    """GSA分析器主类"""
    
    def __init__(self):
        self.data = []
        self.load_sample_data()
    
    def load_sample_data(self):
        """加载样例数据"""
        self.data = [
            {
                "url": "https://www.example.gov/index.html",
                "title": "政府首页",
                "content": "欢迎访问政府网站，这里提供各类公共服务信息。",
                "publish_date": "2024-01-15",
                "access_count": 1500,
                "category": "首页"
            },
            {
                "url": "https://www.example.gov/news/2024/01/20.html",
                "title": "新闻动态",
                "content": "政府发布最新政策法规，推动经济社会发展。",
                "publish_date": "2024-01-20",
                "access_count": 800,
                "category": "新闻"
            },
            {
                "url": "https://www.example.gov/service/education.html",
                "title": "教育服务",
                "content": "提供教育资源、考试信息、学校查询等服务。",
                "publish_date": "2024-01-10",
                "access_count": 2000,
                "category": "服务"
            },
            {
                "url": "https://www.example.gov/service/health.html",
                "title": "医疗服务",
                "content": "提供医疗资源、健康咨询、医院预约等服务。",
                "publish_date": "2024-01-18",
                "access_count": 1200,
                "category": "服务"
            }
        ]
    
    def search(self, query, page=1, page_size=10):
        """搜索功能"""
        # 参数验证
        if not isinstance(page, int) or page < 1:
            raise ValueError("page 字段必须是整数且大于0")
        if not isinstance(page_size, int) or page_size < 1:
            raise ValueError("page_size 字段必须是整数且大于0")
        
        # 搜索过滤
        results = []
        query_lower = query.lower() if query else ""
        
        for item in self.data:
            # 在标题和内容中搜索
            search_text = f"{item['title']} {item['content']}".lower()
            if query_lower in search_text:
                results.append(item)
        
        # 分页
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        page_results = results[start:end]
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": page_results,
            "query": query
        }
    
    def get_stats(self):
        """获取统计信息"""
        total_pages = len(self.data)
        total_access = sum(item["access_count"] for item in self.data)
        
        # 分类统计
        categories = Counter(item["category"] for item in self.data)
        
        # 平均访问量
        avg_access = total_access / total_pages if total_pages > 0 else 0
        
        # 最近更新
        dates = [datetime.strptime(item["publish_date"], "%Y-%m-%d") for item in self.data]
        latest = max(dates) if dates else datetime.now()
        
        return {
            "total_pages": total_pages,
            "total_access": total_access,
            "avg_access": round(avg_access, 2),
            "categories": dict(categories),
            "latest_update": latest.strftime("%Y-%m-%d")
        }
    
    def analyze_url(self, url):
        """分析URL结构"""
        parsed = urlparse(url)
        return {
            "scheme": parsed.scheme,
            "domain": parsed.netloc,
            "path": parsed.path,
            "query": parsed.query,
            "is_secure": parsed.scheme == "https"
        }
    
    def get_hot_pages(self, limit=5):
        """获取热门页面"""
        sorted_data = sorted(self.data, key=lambda x: x["access_count"], reverse=True)
        return sorted_data[:limit]
    
    def get_category_summary(self):
        """获取分类摘要"""
        summary = defaultdict(lambda: {"count": 0, "total_access": 0})
        for item in self.data:
            cat = item["category"]
            summary[cat]["count"] += 1
            summary[cat]["total_access"] += item["access_count"]
        return dict(summary)

def run_selftest():
    """运行自检程序"""
    print("[RUN] === GSA Prototype 自检开始 ===")
    
    analyzer = GSAAnalyzer()
    
    # 测试1: 标准查询
    try:
        result = analyzer.search("政府")
        assert result["total"] >= 1, "标准查询应返回至少1条结果"
        assert result["page"] == 1, "默认页码应为1"
        assert len(result["results"]) >= 1, "应返回至少1条结果"
        print("  [PASS] 标准查询")
    except Exception as e:
        print(f"  [FAIL] 标准查询: {e}")
        return False
    
    # 测试2: 中文编码
    try:
        result = analyzer.search("教育")
        assert result["total"] >= 1, "中文查询应返回至少1条结果"
        assert len(result["results"]) >= 1, "中文查询应返回结果"
        print("  [PASS] 中文编码")
    except Exception as e:
        print(f"  [FAIL] 中文编码: {e}")
        return False
    
    # 测试3: 分页功能
    try:
        result = analyzer.search("服务", page=1, page_size=2)
        assert result["total"] >= 1, "分页查询应返回结果"
        assert len(result["results"]) <= 2, "分页大小应正确"
        print("  [PASS] 分页功能")
    except Exception as e:
        print(f"  [FAIL] 分页功能: {e}")
        return False
    
    # 测试4: 统计功能
    try:
        stats = analyzer.get_stats()
        assert stats["total_pages"] >= 1, "统计应包含页面数"
        assert stats["total_access"] > 0, "统计应包含访问量"
        assert len(stats["categories"]) >= 1, "统计应包含分类"
        print("  [PASS] 统计功能")
    except Exception as e:
        print(f"  [FAIL] 统计功能: {e}")
        return False
    
    # 测试5: URL分析
    try:
        url_info = analyzer.analyze_url("https://www.example.gov/path?query=1")
        assert url_info["scheme"] == "https", "URL协议应正确"
        assert url_info["domain"] == "www.example.gov", "URL域名应正确"
        assert url_info["is_secure"] == True, "应识别HTTPS"
        print("  [PASS] URL分析")
    except Exception as e:
        print(f"  [FAIL] URL分析: {e}")
        return False
    
    # 测试6: 热门页面
    try:
        hot_pages = analyzer.get_hot_pages(3)
        assert len(hot_pages) <= 3, "热门页面数量应正确"
        assert len(hot_pages) >= 1, "应返回热门页面"
        print("  [PASS] 热门页面")
    except Exception as e:
        print(f"  [FAIL] 热门页面: {e}")
        return False
    
    # 测试7: 参数验证
    try:
        try:
            analyzer.search("测试", page=0)
            print("  [FAIL] 参数验证: 应拒绝无效页码")
            return False
        except ValueError:
            print("  [PASS] 参数验证")
    except Exception as e:
        print(f"  [FAIL] 参数验证: {e}")
        return False
    
    print("[PASS] === GSA Prototype 自检通过 ===")
    return True

def main():
    """主函数"""
    # 检查是否有自检参数
    if "--selftest" in sys.argv:
        success = run_selftest()
        sys.exit(0 if success else 1)
    
    # 正常模式
    analyzer = GSAAnalyzer()
    
    # 示例：执行搜索
    print("GSA Prototype 已启动")
    print("可用命令: --selftest 运行自检")
    
    # 示例查询
    result = analyzer.search("服务")
    print(f"\n搜索'服务'结果: 共{result['total']}条")
    for item in result["results"][:3]:
        print(f"  - {item['title']} (访问量: {item['access_count']})")
    
    # 显示统计
    stats = analyzer.get_stats()
    print(f"\n统计信息:")
    print(f"  总页面数: {stats['total_pages']}")
    print(f"  总访问量: {stats['total_access']}")
    print(f"  平均访问量: {stats['avg_access']}")

if __name__ == "__main__":
    main()
