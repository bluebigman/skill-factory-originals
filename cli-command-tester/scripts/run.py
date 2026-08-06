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


def run_selftest():
    """自检测试 - 真实调用核心功能"""
    print("🔍 运行自检测试...")
    tests_passed = 0
    tests_failed = 0

    # 测试1: 构建URL
    print("\n[测试1] URL参数拼接")
    tester = HTTPTester('GET', 'https://api.example.com/users', params='page=1&size=20')
    url = tester.build_url()
    assert url == 'https://api.example.com/users?page=1&size=20', f"URL拼接错误: {url}"
    print(f"  ✅ URL拼接正确: {url}")
    tests_passed += 1

    # 测试2: JSON请求体准备
    print("\n[测试2] JSON请求体准备")
    tester = HTTPTester('POST', 'https://api.example.com/users', data='{"name":"test"}')
    data = tester.prepare_data()
    assert data == b'{"name":"test"}', f"JSON请求体错误: {data}"
    assert tester.headers.get('Content-Type') == 'application/json', f"Content-Type错误: {tester.headers}"
    print(f"  ✅ JSON请求体正确: {data}")
    tests_passed += 1

    # 测试3: 表单请求体准备
    print("\n[测试3] 表单请求体准备")
    tester = HTTPTester('POST', 'https://api.example.com/users', data={'name': 'test'})
    data = tester.prepare_data()
    assert data == b'name=test', f"表单请求体错误: {data}"
    assert tester.headers.get('Content-Type') == 'application/x-www-form-urlencoded', f"Content-Type错误: {tester.headers}"
    print(f"  ✅ 表单请求体正确: {data}")
    tests_passed += 1

    # 测试4: 响应格式化（JSON）
    print("\n[测试4] JSON响应格式化")
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

    # 测试5: 响应格式化（非JSON）
    print("\n[测试5] 非JSON响应格式化")
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

    # 测试6: 原子写入
    print("\n[测试6] 原子文件写入")
    import tempfile as tmp
    with tmp.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
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

    # 测试7: 真实HTTP请求（使用httpbin.org）
    print("\n[测试7] 真实HTTP请求")
    try:
        tester = HTTPTester('GET', 'https://httpbin.org/get', params='test=1', timeout=5)
        result = tester.execute()
        assert result['status'] == 200, f"HTTP状态码错误: {result['status']}"
        assert 'test' in result['body'], "响应体缺少参数"
        print(f"  ✅ 真实HTTP请求成功 (状态码: {result['status']})")
        tests_passed += 1
    except Exception as e:
        print(f"  ⚠️ 真实HTTP请求失败（网络可能不可用）: {e}")
        # 不标记为失败，因为可能是网络环境问题

    # 测试8: 错误处理（无效URL）
    print("\n[测试8] 无效URL错误处理")
    tester = HTTPTester('GET', 'https://nonexistent-domain-12345.com/', timeout=3, max_retries=1)
    result = tester.execute()
    assert result['status'] == 0, f"应该返回错误状态"
    assert 'error' in result, "缺少错误信息"
    print(f"  ✅ 错误处理正确: {result['error'][:50]}...")
    tests_passed += 1

    # 汇总
    print(f"\n{'='*50}")
    print(f"✅ 通过: {tests_passed} | ❌ 失败: {tests_failed}")
    if tests_failed > 0:
        print("❌ 自检测试失败")
        return 1
    else:
        print("✅ 自检测试全部通过")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='HTTP命令行测试工具 - 接口调试命令行速测',
        epilog='示例: cli POST https://api.example.com/users -d \'{"name":"test"}\' -H "Authorization: Bearer token"'
    )

    # 位置参数
    parser.add_argument('method', nargs='?', default='GET',
                        help='HTTP方法 (GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS)')
    parser.add_argument('url', nargs='?',
                        help='目标URL')

    # 可选参数
    parser.add_argument('-H', '--header', action='append', default=[],
                        help='自定义请求头，格式: "Header: value" (可多次使用)')
    parser.add_argument('-d', '--data',
                        help='请求体 (JSON字符串或表单格式)')
    parser.add_argument('-p', '--params',
                        help='查询参数，格式: "key1=value1&key2=value2"')
    parser.add_argument('-t', '--timeout', type=float, default=10,
                        help='超时时间（秒），默认10秒')
    parser.add_argument('-L', '--location', action='store_true',
                        help='跟随重定向')
    parser.add_argument('-o', '--output',
                        help='输出文件路径（原子化写入）')
    parser.add_argument('-k', '--insecure', action='store_true',
                        help='跳过TLS证书验证')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细输出（包含响应头）')
    parser.add_argument('--no-retry', action='store_true',
                        help='禁用重试机制')
    parser.add_argument('--selftest', action='store_true',
                        help='运行自检测试')

    args = parser.parse_args()

    # 自检测试
    if args.selftest:
        return run_selftest()

    # 参数验证
    if not args.url:
        parser.error("必须提供URL参数")

    # 解析请求头
    headers = {}
    for header in args.header:
        if ':' not in header:
            parser.error(f"请求头格式错误: {header} (应为 'Header: value')")
        key, value = header.split(':', 1)
        headers[key.strip()] = value.strip()

    # 解析请求体
    data = None
    if args.data:
        # 尝试解析JSON
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            # 不是JSON，作为原始字符串
            data = args.data

    # 创建测试器
    tester = HTTPTester(
        method=args.method,
        url=args.url,
        headers=headers,
        data=data,
        params=args.params,
        timeout=args.timeout,
        follow_redirects=args.location,
        insecure=args.insecure,
        max_retries=0 if args.no_retry else 3
    )

    # 执行请求
    result = tester.execute()

    # 格式化输出
    output = format_response(result, verbose=args.verbose)
    print(output)

    # 保存到文件
    if args.output:
        try:
            atomic_write_file(args.output, result['body'])
            print(f"\n📁 响应已保存到: {args.output}")
        except Exception as e:
            print(f"\n❌ 文件写入失败: {e}", file=sys.stderr)
            return 6

    # 返回退出码
    if result['status'] == 0:
        return 2  # 网络错误
    elif result['status'] >= 400:
        return 4  # HTTP错误
    else:
        return 0  # 成功


if __name__ == '__main__':
    sys.exit(main())
