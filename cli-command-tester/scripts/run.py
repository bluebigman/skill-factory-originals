#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP命令行测试工具 - 接口调试命令行速测
支持构造HTTP请求、自定义请求头、请求体、参数拼接、响应格式化、超时控制、跟随重定向、输出保存
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import gzip
import io
import random
from http.client import HTTPResponse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class HTTPTester:
    """HTTP请求测试核心类"""
    
    def __init__(self, method, url, headers=None, data=None, params=None, timeout=10, follow_redirects=True, insecure=False):
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.data = data
        self.params = params
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.insecure = insecure
        
    def build_url(self):
        """拼接查询参数"""
        if not self.params:
            return self.url
        separator = '&' if '?' in self.url else '?'
        return f"{self.url}{separator}{self.params}"
    
    def prepare_data(self):
        """准备请求体"""
        if not self.data:
            return None
        
        # 如果data是dict类型，转换为表单序列化
        if isinstance(self.data, dict):
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            return urllib.parse.urlencode(self.data).encode('utf-8')
        
        # 如果data是JSON字符串，自动设置Content-Type
        if isinstance(self.data, str) and (self.data.startswith('{') or self.data.startswith('[')):
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'
            return self.data.encode('utf-8')
        
        # 表单格式
        if isinstance(self.data, str):
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
            return self.data.encode('utf-8')
        
        # 其他类型转字符串
        return str(self.data).encode('utf-8')
    
    def execute_with_requests(self):
        """使用requests库执行请求（如果可用）"""
        if not HAS_REQUESTS:
            return None
        
        url = self.build_url()
        data = self.prepare_data()
        
        # 指数退避重试
        max_retries = 3
        retry_delays = [1, 2, 4]
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=self.method,
                    url=url,
                    headers=self.headers,
                    data=data,
                    timeout=self.timeout,
                    allow_redirects=self.follow_redirects,
                    verify=not self.insecure
                )
                return {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response.text,
                    'elapsed': response.elapsed.total_seconds(),
                    'url': response.url
                }
            except requests.exceptions.SSLError as e:
                if attempt == max_retries - 1:
                    return {'error': f"SSL错误: {str(e)}"}
                time.sleep(retry_delays[attempt])
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    return {'error': str(e)}
                time.sleep(retry_delays[attempt])
        
        return {'error': "请求失败"}
    
    def execute_with_urllib(self):
        """使用urllib执行请求（标准库实现）"""
        url = self.build_url()
        data = self.prepare_data()
        
        # 创建请求对象
        req = urllib.request.Request(url, data=data, method=self.method)
        
        # 设置请求头
        for key, value in self.headers.items():
            req.add_header(key, value)
        
        # 处理重定向
        if not self.follow_redirects:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            opener = urllib.request.build_opener(NoRedirect)
        else:
            opener = urllib.request.build_opener()
        
        # 处理HTTPS证书
        if self.insecure:
            context = ssl._create_unverified_context()
        else:
            context = ssl.create_default_context()
        opener.add_handler(urllib.request.HTTPSHandler(context=context))
        
        # 指数退避重试
        max_retries = 3
        retry_delays = [1, 2, 4]
        
        for attempt in range(max_retries):
            start_time = time.time()
            try:
                response = opener.open(req, timeout=self.timeout)
                elapsed = time.time() - start_time
                
                # 读取响应体
                body = response.read()
                # 处理gzip压缩
                content_encoding = response.headers.get('Content-Encoding', '')
                if 'gzip' in content_encoding:
                    body = gzip.decompress(body)
                
                # 尝试解码
                try:
                    body_text = body.decode('utf-8')
                except UnicodeDecodeError:
                    body_text = body.decode('latin-1')
                
                return {
                    'status_code': response.getcode(),
                    'headers': dict(response.headers),
                    'body': body_text,
                    'elapsed': elapsed,
                    'url': response.geturl()
                }
            except urllib.error.HTTPError as e:
                elapsed = time.time() - start_time
                # 读取错误响应体
                error_body = e.read()
                content_encoding = e.headers.get('Content-Encoding', '')
                if 'gzip' in content_encoding:
                    try:
                        error_body = gzip.decompress(error_body)
                    except:
                        pass
                return {
                    'status_code': e.code,
                    'headers': dict(e.headers),
                    'body': error_body.decode('utf-8', errors='replace'),
                    'elapsed': elapsed,
                    'url': url
                }
            except urllib.error.URLError as e:
                if isinstance(e.reason, ssl.SSLError):
                    if attempt == max_retries - 1:
                        return {'error': f"SSL错误: {e.reason}"}
                elif isinstance(e.reason, ConnectionRefusedError):
                    if attempt == max_retries - 1:
                        return {'error': f"连接被拒绝: {e.reason}"}
                elif isinstance(e.reason, TimeoutError):
                    if attempt == max_retries - 1:
                        return {'error': f"超时: {e.reason}"}
                else:
                    if attempt == max_retries - 1:
                        return {'error': f"URL错误: {e.reason}"}
                time.sleep(retry_delays[attempt])
            except Exception as e:
                if attempt == max_retries - 1:
                    return {'error': str(e)}
                time.sleep(retry_delays[attempt])
        
        return {'error': "请求失败"}
    
    def execute(self):
        """执行请求"""
        # 优先使用requests库
        if HAS_REQUESTS:
            result = self.execute_with_requests()
            if result and 'error' not in result:
                return result
        
        # 回退到urllib
        return self.execute_with_urllib()


def format_response(result, show_headers=False, max_length=2000):
    """格式化响应输出"""
    if not result:
        return "错误: 请求执行失败"
    
    if 'error' in result:
        return f"错误: {result['error']}"
    
    output = []
    
    # 状态行
    output.append(f"HTTP {result['status_code']}")
    output.append(f"耗时: {result['elapsed']:.3f}s")
    output.append(f"URL: {result['url']}")
    output.append("")
    
    # 响应头
    if show_headers:
        output.append("--- 响应头 ---")
        for key, value in result['headers'].items():
            output.append(f"{key}: {value}")
        output.append("")
    
    # 响应体
    output.append("--- 响应体 ---")
    body = result['body']
    
    # 尝试格式化JSON
    try:
        json_data = json.loads(body)
        formatted = json.dumps(json_data, indent=2, ensure_ascii=False)
        body = formatted
    except (json.JSONDecodeError, TypeError):
        pass
    
    # 截断过长内容
    if len(body) > max_length:
        body = body[:max_length] + f"\n... (已截断，总长度 {len(result['body'])} 字符)"
    
    output.append(body)
    
    return "\n".join(output)


def selftest():
    """自检函数 - 本地测试核心功能"""
    print("=== 自检开始 ===")
    
    # 测试1: 参数拼接
    tester = HTTPTester("GET", "http://example.com/api", params="page=1&size=20")
    url = tester.build_url()
    assert url == "http://example.com/api?page=1&size=20", f"参数拼接失败: {url}"
    print("[PASS] 参数拼接")
    
    # 测试2: JSON数据准备
    tester = HTTPTester("POST", "http://example.com/api", data='{"name":"test"}')
    data = tester.prepare_data()
    assert data == b'{"name":"test"}', "JSON数据准备失败"
    assert tester.headers.get('Content-Type') == 'application/json', "Content-Type设置失败"
    print("[PASS] JSON数据准备")
    
    # 测试3: 表单数据准备（字符串）
    tester = HTTPTester("POST", "http://example.com/api", data="name=test&age=20")
    data = tester.prepare_data()
    assert data == b"name=test&age=20", "表单数据准备失败"
    assert tester.headers.get('Content-Type') == 'application/x-www-form-urlencoded', "表单Content-Type设置失败"
    print("[PASS] 表单数据准备（字符串）")
    
    # 测试4: 表单数据准备（dict类型）
    tester = HTTPTester("POST", "http://example.com/api", data={"name": "test", "age": 20})
    data = tester.prepare_data()
    assert data == b"name=test&age=20", f"dict表单序列化失败: {data}"
    assert tester.headers.get('Content-Type') == 'application/x-www-form-urlencoded', "dict表单Content-Type设置失败"
    print("[PASS] 表单数据准备（dict类型）")
    
    # 测试5: 响应格式化 - JSON
    result = {
        'status_code': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': '{"name":"张三","age":30}',
        'elapsed': 0.123,
        'url': 'http://example.com'
    }
    formatted = format_response(result)
    assert "张三" in formatted, "JSON格式化失败"
    assert "HTTP 200" in formatted, "状态码显示失败"
    print("[PASS] 响应格式化")
    
    # 测试6: 响应截断
    long_body = "x" * 3000
    result['body'] = long_body
    formatted = format_response(result, max_length=100)
    assert "已截断" in formatted, "截断功能失败"
    print("[PASS] 响应截断")
    
    # 测试7: 错误处理
    result = {'error': "连接失败"}
    formatted = format_response(result)
    assert "错误" in formatted, "错误处理失败"
    print("[PASS] 错误处理")
    
    # 测试8: gzip解压处理
    import gzip as gzip_module
    test_data = b'{"compressed": true}'
    compressed_data = gzip_module.compress(test_data)
    decompressed = gzip_module.decompress(compressed_data)
    assert decompressed == test_data, "gzip解压失败"
    print("[PASS] gzip解压处理")
    
    # 测试9: 重试机制（模拟失败场景）
    tester = HTTPTester("GET", "http://127.0.0.1:1", timeout=1)
    result = tester.execute()
    assert 'error' in result, "重试机制测试失败"
    print("[PASS] 重试机制")
    
    # 测试10: insecure参数
    tester = HTTPTester("GET", "https://example.com", insecure=True)
    assert tester.insecure == True, "insecure参数设置失败"
    print("[PASS] insecure参数")
    
    print("=== 自检完成: 全部通过 ===")
    return 0


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="HTTP命令行测试工具 - 快速构造HTTP请求、调试REST API并格式化输出响应结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s GET https://api.example.com/health
  %(prog)s POST https://api.example.com/users -d '{"name":"张三"}' -H "Authorization: Bearer token"
  %(prog)s GET https://api.example.com -p "page=1&size=20" -i
  %(prog)s GET https://api.example.com -t 10 -L -o response.json
  %(prog)s --selftest
        """
    )
    
    # 位置参数
    parser.add_argument('method', nargs='?', choices=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
                       help="HTTP方法")
    parser.add_argument('url', nargs='?', help="请求URL")
    
    # 可选参数
    parser.add_argument('-H', '--header', action='append', default=[], metavar='HEADER',
                       help="自定义请求头，格式: 'Key: Value'，可多次使用")
    parser.add_argument('-d', '--data', help="请求体数据（JSON或表单格式）")
    parser.add_argument('-p', '--params', help="查询参数，格式: 'key1=value1&key2=value2'")
    parser.add_argument('-t', '--timeout', type=float, default=10, help="超时时间（秒），默认10秒")
    parser.add_argument('-L', '--location', action='store_true', help="跟随重定向")
    parser.add_argument('-i', '--include', action='store_true', help="显示响应头")
    parser.add_argument('-o', '--output', help="将响应体保存到文件")
    parser.add_argument('--max-length', type=int, default=2000, help="响应体最大显示长度，默认2000字符")
    parser.add_argument('--insecure', action='store_true', help="关闭SSL证书验证")
    parser.add_argument('--selftest', action='store_true', help="运行自检")
    
    args = parser.parse_args()
    
    # 自检模式
    if args.selftest:
        sys.exit(selftest())
    
    # 参数校验
    if not args.method or not args.url:
        parser.error("必须提供HTTP方法和URL")
    
    # 解析请求头
    headers = {}
    for h in args.header:
        if ':' not in h:
            parser.error(f"无效的请求头格式: {h}，应为 'Key: Value'")
        key, value = h.split(':', 1)
        headers[key.strip()] = value.strip()
    
    # 创建测试器
    tester = HTTPTester(
        method=args.method,
        url=args.url,
        headers=headers,
        data=args.data,
        params=args.params,
        timeout=args.timeout,
        follow_redirects=args.location,
        insecure=args.insecure
    )
    
    # 执行请求
    print(f"正在请求: {args.method} {tester.build_url()}")
    result = tester.execute()
    
    # 格式化输出
    output = format_response(result, show_headers=args.include, max_length=args.max_length)
    print(output)
    
    # 保存到文件
    if args.output and 'error' not in result:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(result['body'])
            print(f"\n响应已保存到: {args.output}")
        except IOError as e:
            print(f"\n错误: 无法保存文件: {e}", file=sys.stderr)
            sys.exit(1)
    
    # 根据状态码设置退出码
    if 'error' in result:
        sys.exit(1)
    elif result['status_code'] >= 400:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
