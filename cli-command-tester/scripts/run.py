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
import os
import tempfile
import threading
import http.server
import socketserver
from datetime import datetime, timezone
from http.client import HTTPResponse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class HTTPTester:
    """HTTP请求测试核心类"""

    def __init__(self, method, url, headers=None, data=None, params=None, timeout=10, follow_redirects=True, insecure=False, max_retries=3):
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.data = data
        self.params = params
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.insecure = insecure
        self.max_retries = max_retries

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

        return None

    def _create_request(self):
        """创建urllib请求对象"""
        url = self.build_url()
        data = self.prepare_data()
        headers = dict(self.headers)

        # 设置User-Agent
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'CLI-Command-Tester/2.0.0'

        # 设置Accept-Encoding
        if 'Accept-Encoding' not in headers:
            headers['Accept-Encoding'] = 'gzip'

        req = urllib.request.Request(url, data=data, headers=headers, method=self.method)
        return req

    def _create_ssl_context(self):
        """创建SSL上下文"""
        if self.insecure:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context
        return ssl.create_default_context()

    def _decode_response(self, response):
        """解码响应体，处理gzip压缩"""
        raw_data = response.read()

        # 检查Content-Encoding
        content_encoding = response.headers.get('Content-Encoding', '')
        if 'gzip' in content_encoding:
            try:
                raw_data = gzip.decompress(raw_data)
            except gzip.BadGzipFile:
                pass  # 不是有效的gzip数据，保持原样

        # 尝试解码
        try:
            return raw_data.decode('utf-8')
        except UnicodeDecodeError:
            try:
                return raw_data.decode('latin-1')
            except UnicodeDecodeError:
                return raw_data.decode('utf-8', errors='replace')

    def execute(self):
        """执行HTTP请求，带指数退避重试"""
        req = self._create_request()
        ssl_context = self._create_ssl_context()

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                if self.follow_redirects:
                    # 使用默认的HTTPRedirectHandler
                    opener = urllib.request.build_opener(
                        urllib.request.HTTPRedirectHandler(),
                        urllib.request.HTTPSHandler(context=ssl_context)
                    )
                else:
                    # 自定义不跟随重定向的handler
                    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
                        def redirect_request(self, req, fp, code, msg, headers, newurl):
                            return None
                    opener = urllib.request.build_opener(
                        NoRedirectHandler(),
                        urllib.request.HTTPSHandler(context=ssl_context)
                    )

                start_time = time.time()
                response = opener.open(req, timeout=self.timeout)
                elapsed = time.time() - start_time

                body = self._decode_response(response)
                status = response.getcode()
                response_headers = dict(response.headers)

                return {
                    'status': status,
                    'headers': response_headers,
                    'body': body,
                    'elapsed': elapsed,
                    'url': response.geturl(),
                    'retries': attempt
                }

            except urllib.error.HTTPError as e:
                # HTTP错误（4xx, 5xx）不重试
                body = e.read().decode('utf-8', errors='replace')
                return {
                    'status': e.code,
                    'headers': dict(e.headers),
                    'body': body,
                    'elapsed': 0,
                    'url': self.url,
                    'retries': attempt,
                    'error': str(e)
                }

            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last_error = e
                if attempt < self.max_retries:
                    # 指数退避：1s, 2s, 4s
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    break

        # 所有重试都失败
        return {
            'status': 0,
            'headers': {},
            'body': '',
            'elapsed': 0,
            'url': self.url,
            'retries': self.max_retries,
            'error': f"网络错误: {last_error}"
        }


def format_response(result, verbose=False):
    """格式化响应输出"""
    lines = []

    # 状态行
    if result['status'] == 0:
        lines.append(f"❌ 请求失败: {result.get('error', '未知错误')}")
    else:
        lines.append(f"HTTP/1.1 {result['status']}")

    # 响应头
    if verbose:
        lines.append("")
        lines.append("--- 响应头 ---")
        for key, value in result['headers'].items():
            lines.append(f"{key}: {value}")

    # 响应体
    if result['body']:
        lines.append("")
        lines.append("--- 响应体 ---")
        try:
            # 尝试解析JSON并格式化
            parsed = json.loads(result['body'])
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            lines.append(formatted)
        except (json.JSONDecodeError, ValueError):
            # 不是JSON，原样输出
            lines.append(result['body'])

    # 统计信息
    lines.append("")
    lines.append(f"⏱️ 耗时: {result['elapsed']:.3f}s | 重试次数: {result['retries']}")

    return "\n".join(lines)


def atomic_write_file(filepath, content):
    """原子化写入文件"""
    directory = os.path.dirname(os.path.abspath(filepath))
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # 创建临时文件
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix='.tmp_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # 原子替换
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise e


class LocalTestHandler(http.server.BaseHTTPRequestHandler):
    """本地测试服务器处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path.startswith('/get'):
            # 返回JSON响应
            response_data = {
                'method': 'GET',
                'path': self.path,
                'headers': dict(self.headers),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('X-Test-Header', 'test-value')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        elif self.path.startswith('/error'):
            # 返回错误状态
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not Found'}).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Hello World')
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        response_data = {
            'method': 'POST',
            'path': self.path,
            'body': body.decode('utf-8', errors='replace'),
            'headers': dict(self.headers),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """抑制日志输出"""
        pass


def start_local_server():
    """启动本地测试服务器"""
    handler = LocalTestHandler
    httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def run_selftest():
    """自检测试 - 真实调用核心功能"""
    print("🔍 运行自检测试...")
    tests_passed = 0
    tests_failed = 0

    # 启动本地测试服务器
    print("\n[准备] 启动本地测试服务器...")
    httpd, port = start_local_server()
    base_url = f"http://127.0.0.1:{port}"
    print(f"  ✅ 本地服务器已启动: {base_url}")

    try:
        # 测试1: 构建URL
        print("\n[测试1] URL参数拼接")
        tester = HTTPTester('GET', f'{base_url}/get', params='page=1&size=20')
        url = tester.build_url()
        assert url == f'{base_url}/get?page=1&size=20', f"URL拼接错误: {url}"
        print(f"  ✅ URL拼接正确: {url}")
        tests_passed += 1

        # 测试2: JSON请求体准备
        print("\n[测试2] JSON请求体准备")
        tester = HTTPTester('POST', f'{base_url}/post', data='{"name":"test"}')
        data = tester.prepare_data()
        assert data == b'{"name":"test"}', f"JSON请求体错误: {data}"
        assert tester.headers.get('Content-Type') == 'application/json', f"Content-Type错误: {tester.headers}"
        print(f"  ✅ JSON请求体正确: {data}")
        tests_passed += 1

        # 测试3: 表单请求体准备
        print("\n[测试3] 表单请求体准备")
        tester = HTTPTester('POST', f'{base_url}/post', data={'name': 'test'})
        data = tester.prepare_data()
        assert data == b'name=test', f"表单请求体错误: {data}"
        assert tester.headers.get('Content-Type') == 'application/x-www-form-urlencoded', f"Content-Type错误: {tester.headers}"
        print(f"  ✅ 表单请求体正确: {data}")
        tests_passed += 1

        # 测试4: 真实HTTP GET请求
        print("\n[测试4] 真实HTTP GET请求")
        tester = HTTPTester('GET', f'{base_url}/get', params='test=1', timeout=5)
        result = tester.execute()
        assert result['status'] == 200, f"HTTP状态码错误: {result['status']}"
        assert 'test' in result['body'], "响应体缺少参数"
        assert 'timestamp' in result['body'], "响应体缺少时间戳"
        print(f"  ✅ GET请求成功 (状态码: {result['status']})")
        tests_passed += 1

        # 测试5: 真实HTTP POST请求
        print("\n[测试5] 真实HTTP POST请求")
        tester = HTTPTester('POST', f'{base_url}/post', data='{"name":"test"}', timeout=5)
        result = tester.execute()
        assert result['status'] == 200, f"HTTP状态码错误: {result['status']}"
        assert 'name' in result['body'], "响应体缺少POST数据"
        print(f"  ✅ POST请求成功 (状态码: {result['status']})")
        tests_passed += 1

        # 测试6: 响应格式化（JSON）
        print("\n[测试6] JSON响应格式化")
        result = {
            'status': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"name":"test","age":30}',
            'elapsed': 0.123,
            'retries': 0
        }
        formatted = format_response(result, verbose=True)
        assert 'HTTP/1.1 200' in formatted, "状态行缺失"
        assert '"name": "test"' in formatted, "JSON格式化失败"
        assert 'Content-Type' in formatted, "响应头缺失"
        print(f"  ✅ JSON格式化正确")
        tests_passed += 1

        # 测试7: 响应格式化（非JSON）
        print("\n[测试7] 非JSON响应格式化")
        result = {
            'status': 200,
            'headers': {},
            'body': 'Hello World',
            'elapsed': 0.1,
            'retries': 0
        }
        formatted = format_response(result, verbose=False)
        assert 'Hello World' in formatted, "非JSON响应错误"
        print(f"  ✅ 非JSON格式化正确")
        tests_passed += 1

        # 测试8: 原子写入
        print("\n[测试8] 原子文件写入")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_file = f.name
        try:
            success = atomic_write_file(test_file, "测试内容")
            assert success, "原子写入失败"
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == "测试内容", f"文件内容错误: {content}"
            print(f"  ✅ 原子写入正确: {test_file}")
            tests_passed += 1
        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

        # 测试9: 错误处理（无效URL）
        print("\n[测试9] 无效URL错误处理")
        tester = HTTPTester('GET', 'https://nonexistent-domain-12345.com/', timeout=3, max_retries=1)
        result = tester.execute()
        assert result['status'] == 0, f"应该返回错误状态"
        assert 'error' in result, "缺少错误信息"
        print(f"  ✅ 错误处理正确: {result['error'][:50]}...")
        tests_passed += 1

        # 测试10: 重试机制验证
        print("\n[测试10] 重试机制验证")
        start_time = time.time()
        tester = HTTPTester('GET', 'https://nonexistent-domain-12345.com/', timeout=1, max_retries=2)
        result = tester.execute()
        elapsed = time.time() - start_time
        assert result['status'] == 0, "应该返回错误状态"
        assert result['retries'] == 2, f"重试次数错误: {result['retries']}"
        assert elapsed >= 3, f"重试等待时间不足: {elapsed:.2f}s"
        print(f"  ✅ 重试机制正确 (重试次数: {result['retries']}, 耗时: {elapsed:.2f}s)")
        tests_passed += 1

        # 测试11: HTTP错误处理
        print("\n[测试11] HTTP错误处理")
        tester = HTTPTester('GET', f'{base_url}/error', timeout=5)
        result = tester.execute()
        assert result['status'] == 404, f"HTTP状态码错误: {result['status']}"
        assert 'error' in result['body'], "响应体缺少错误信息"
        print(f"  ✅ HTTP错误处理正确 (状态码: {result['status']})")
        tests_passed += 1

    finally:
        # 关闭服务器
        httpd.shutdown()
        httpd.server_close()
        print("\n[清理] 本地测试服务器已关闭")

    # 汇总
    print(f"\n{'='*50}")
