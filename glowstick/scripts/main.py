#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
glowstick - 实时绘图数据可视化工具（独立实现）

本脚本依据功能规格独立编写，不复制任何既有代码。
功能：将本地文件或远程URL的数据快速转为实时OpenGL图表。
支持 CSV/JSON/TXT 格式，自动推断图表类型。

用法示例：
    python main.py data.csv
    python main.py https://example.com/data.json
    python main.py --selftest
"""

import argparse
import csv
import io
import json
import math
import os
import sys
import tempfile
import urllib.request
import urllib.error
import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import time
from datetime import datetime, timezone

# ============================================================
# 错误码定义
# ============================================================
ERROR_CODES = {
    "E001": "参数错误：未提供输入文件或URL",
    "E002": "文件不存在或无法访问",
    "E003": "URL访问失败或网络错误",
    "E004": "数据格式无法识别（仅支持CSV/JSON/TXT）",
    "E005": "数据解析失败：内容格式不正确",
    "E006": "数据为空或缺少有效数值列",
    "E007": "图表类型推断失败",
    "E008": "内存不足或文件过大（超过500MB限制）",
    "E009": "OpenGL渲染初始化失败",
    "E010": "内部错误：未预期的异常",
}


def error_exit(code: str, message: str = "") -> None:
    """输出错误信息并退出程序"""
    err_msg = ERROR_CODES.get(code, "未知错误")
    if message:
        print(f"[错误 {code}] {err_msg}: {message}", file=sys.stderr)
    else:
        print(f"[错误 {code}] {err_msg}", file=sys.stderr)
    sys.exit(1)


# ============================================================
# 数据模型
# ============================================================
@dataclass
class DataSeries:
    """数据序列，包含x/y/z坐标数据"""
    x: List[float]
    y: List[float]
    z: Optional[List[float]] = None
    labels: Optional[List[str]] = None
    series_name: str = "data"


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: str  # "line", "scatter2d", "scatter3d", "bar"
    title: str = "glowstick 实时图表"
    x_label: str = "X"
    y_label: str = "Y"
    z_label: str = "Z"


# ============================================================
# 数据加载与解析
# ============================================================
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB限制
MAX_TOTAL_TIME = 30  # 最大总耗时限制（秒）
REQUEST_TIMEOUT = 10  # 单次请求超时（秒）
MAX_RETRY = 3  # 最大重试次数


def _retry_request(fn, *args, **kwargs):
    """带重试退避的请求封装，区分可重试与不可重试错误，有总超时控制"""
    start_time = time.time()
    last_exception = None

    for attempt in range(MAX_RETRY):
        # 检查总耗时
        if time.time() - start_time > MAX_TOTAL_TIME:
            raise TimeoutError(f"请求总耗时超过{MAX_TOTAL_TIME}秒限制")

        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as e:
            # HTTP错误状态码处理
            status_code = e.code
            if 400 <= status_code < 500:
                # 4xx错误不可重试，直接抛出
                raise
            elif status_code >= 500:
                # 5xx错误可重试
                last_exception = e
                if attempt < MAX_RETRY - 1:
                    wait_time = 2 ** attempt
                    print(f"HTTP {status_code}错误，{wait_time}秒后重试 ({attempt + 1}/{MAX_RETRY})", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    raise
            else:
                # 其他状态码（如3xx重定向）视为不可重试
                raise
        except socket.timeout as e:
            last_exception = e
            if attempt < MAX_RETRY - 1:
                wait_time = 2 ** attempt
                print(f"请求超时，{wait_time}秒后重试 ({attempt + 1}/{MAX_RETRY})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise
        except urllib.error.URLError as e:
            last_exception = e
            if isinstance(e.reason, socket.timeout):
                if attempt < MAX_RETRY - 1:
                    wait_time = 2 ** attempt
                    print(f"请求超时，{wait_time}秒后重试 ({attempt + 1}/{MAX_RETRY})", file=sys.stderr)
                    time.sleep(wait_time)
                else:
                    raise
            elif attempt < MAX_RETRY - 1:
                wait_time = 2 ** attempt
                print(f"连接错误，{wait_time}秒后重试 ({attempt + 1}/{MAX_RETRY})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise
        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRY - 1:
                wait_time = 2 ** attempt
                print(f"请求异常，{wait_time}秒后重试 ({attempt + 1}/{MAX_RETRY})", file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise

    raise last_exception if last_exception else RuntimeError("请求失败")


def load_data_from_file(filepath: str) -> str:
    """从本地文件读取数据内容"""
    if not os.path.exists(filepath):
        error_exit("E002", f"文件不存在: {filepath}")

    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE:
        error_exit("E008", f"文件大小 {file_size} 超过500MB限制")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        error_exit("E005", f"读取文件失败: {e}")


def load_data_from_url(url: str) -> str:
    """从远程URL获取数据内容，带重试退避和超时控制"""
    def _fetch():
        req = urllib.request.Request(url, headers={"User-Agent": "glowstick/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            # 检查重定向
            if resp.geturl() != url:
                print(f"注意: 请求被重定向到 {resp.geturl()}", file=sys.stderr)
            content = resp.read()
            if len(content) > MAX_FILE_SIZE:
                error_exit("E008", f"URL数据超过500MB限制")
            return content.decode("utf-8")

    try:
        return _retry_request(_fetch)
    except urllib.error.HTTPError as e:
        error_exit("E003", f"URL访问失败: HTTP {e.code} {e.reason}")
    except socket.timeout:
        error_exit("E003", f"URL访问超时: {url}")
    except urllib.error.URLError as e:
        error_exit("E003", f"URL访问失败: {e}")
    except Exception as e:
        error_exit("E003", f"URL访问失败: {e}")


def detect_format(content: str) -> str:
    """自动检测数据格式"""
    stripped = content.strip()
    if not stripped:
        error_exit("E006", "数据内容为空")

    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    elif "," in stripped.split("\n")[0] or "\t" in stripped.split("\n")[0]:
        return "csv"
    else:
        return "txt"


def parse_csv_data(content: str) -> DataSeries:
    """解析CSV格式数据"""
    try:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            error_exit("E006", "CSV数据为空")

        # 尝试识别表头
        header = rows[0]
        data_rows = rows[1:]
        try:
            # 验证第一行是否为数值
            [float(v) for v in header if v.strip()]
            # 如果是数值，则第一行也是数据
            data_rows = rows
            header = None
        except ValueError:
            pass  # 第一行是表头

        if not data_rows:
            error_exit("E006", "没有数据行")

        # 解析数值列
        x_vals, y_vals, z_vals = [], [], []
        labels = []

        for row in data_rows:
            if len(row) < 2:
                continue
            try:
                x_vals.append(float(row[0].strip()))
                y_vals.append(float(row[1].strip()))
                if len(row) >= 3:
                    z_vals.append(float(row[2].strip()))
                if len(row) >= 4:
                    labels.append(row[3].strip())
            except (ValueError, IndexError):
                continue

        if not x_vals or not y_vals:
            error_exit("E005", "CSV数据缺少有效数值列")

        return DataSeries(
            x=x_vals,
            y=y_vals,
            z=z_vals if z_vals else None,
            labels=labels if labels else None,
            series_name="CSV数据"
        )
    except Exception as e:
        error_exit("E005", f"CSV解析失败: {e}")


def parse_json_data(content: str) -> DataSeries:
    """解析JSON格式数据"""
    try:
        data = json.loads(content)

        # 支持多种JSON结构
        if isinstance(data, list):
            # 列表形式: [{x:1, y:2}, ...] 或 [[1,2], [3,4]]
            x_vals, y_vals, z_vals = [], [], []
            for item in data:
                if isinstance(item, dict):
                    if "x" in item and "y" in item:
                        x_vals.append(float(item["x"]))
                        y_vals.append(float(item["y"]))
                        if "z" in item:
                            z_vals.append(float(item["z"]))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    x_vals.append(float(item[0]))
                    y_vals.append(float(item[1]))
                    if len(item) >= 3:
                        z_vals.append(float(item[2]))

        elif isinstance(data, dict):
            # 字典形式: {"x": [1,2,3], "y": [4,5,6]}
            if "x" in data and "y" in data:
                x_vals = [float(v) for v in data["x"]]
                y_vals = [float(v) for v in data["y"]]
                z_vals = [float(v) for v in data["z"]] if "z" in data else []
            else:
                error_exit("E005", "JSON缺少x/y键")
        else:
            error_exit("E005", "JSON格式不支持")

        if not x_vals or not y_vals:
            error_exit("E006", "JSON数据为空或缺少数值")

        return DataSeries(
            x=x_vals,
            y=y_vals,
            z=z_vals if z_vals else None,
            series_name="JSON数据"
        )
    except json.JSONDecodeError as e:
        error_exit("E005", f"JSON解析失败: {e}")
    except Exception as e:
        error_exit("E005", f"JSON数据处理失败: {e}")


def parse_txt_data(content: str) -> DataSeries:
    """解析TXT格式数据（每行两个或三个数值，空格/逗号/制表符分隔）"""
    try:
        x_vals, y_vals, z_vals = [], [], []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # 支持空格、逗号、制表符分隔
            parts = line.replace(",", " ").split()
            if len(parts) >= 2:
                try:
                    x_vals.append(float(parts[0]))
                    y_vals.append(float(parts[1]))
                    if len(parts) >= 3:
                        z_vals.append(float(parts[2]))
                except ValueError:
                    continue

        if not x_vals or not y_vals:
            error_exit("E006", "TXT数据缺少有效数值")

        return DataSeries(
            x=x_vals,
            y=y_vals,
            z=z_vals if z_vals else None,
            series_name="TXT数据"
        )
    except Exception as e:
        error_exit("E005", f"TXT解析失败: {e}")


def parse_data(content: str, fmt: str) -> DataSeries:
    """根据格式解析数据"""
    if fmt == "csv":
        return parse_csv_data(content)
    elif fmt == "json":
        return parse_json_data(content)
    elif fmt == "txt":
        return parse_txt_data(content)
    else:
        error_exit("E004", f"不支持的数据格式: {fmt}")


# ============================================================
# 图表类型推断
# ============================================================
def infer_chart_type(series: DataSeries) -> str:
    """根据数据结构推断图表类型"""
    if series.z and len(series.z) > 0:
        return "scatter3d"
    elif len(series.x) >= 2 and len(series.y) >= 2:
        # 判断是否为折线图（数据点有序）或散点图
        x_sorted = sorted(series.x)
        if x_sorted == series.x or x_sorted == list(reversed(series.x)):
            return "line"
        else:
            return "scatter2d"
    else:
        return "bar"


# ============================================================
# OpenGL渲染模块
# ============================================================
class OpenGLRenderer:
    """OpenGL渲染器，支持2D/3D图表渲染"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self._initialized = False
        self._window = None
        
    def initialize(self) -> bool:
        """初始化OpenGL环境"""
        try:
            import OpenGL.GL as gl
            import OpenGL.GLUT as glut
            
            glut.glutInit()
            glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB | glut.GLUT_DEPTH)
            glut.glutInitWindowSize(self.width, self.height)
            self._window = glut.glutCreateWindow(b"glowstick")
            
            gl.glClearColor(0.1, 0.1, 0.15, 1.0)
            gl.glEnable(gl.GL_DEPTH_TEST)
            
            self._initialized = True
            return True
        except ImportError:
            print("警告: 未安装PyOpenGL，使用软件渲染模式", file=sys.stderr)
            self._initialized = False
            return False
        except Exception as e:
            error_exit("E009", f"OpenGL初始化失败: {e}")
            
    def render(self, series: DataSeries, config: ChartConfig) -> bool:
        """渲染图表"""
        if not self._initialized:
            # 软件渲染模式（模拟）
            return self._software_render(series, config)
            
        try:
            import OpenGL.GL as gl
            import OpenGL.GLUT as glut
            
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            
            if config.chart_type == "scatter3d":
                self._render_3d_scatter(series, config)
            elif config.chart_type == "line":
                self._render_line(series, config)
            elif config.chart_type == "scatter2d":
                self._render_2d_scatter(series, config)
            elif config.chart_type == "bar":
                self._render_bar(series, config)
                
            glut.glutSwapBuffers()
            return True
        except Exception as e:
            error_exit("E009", f"渲染失败: {e}")
            
    def _render_3d_scatter(self, series: DataSeries, config: ChartConfig):
        """渲染3D散点图"""
        import OpenGL.GL as gl
        gl.glPointSize(5.0)
        gl.glBegin(gl.GL_POINTS)
        for i in range(len(series.x)):
            gl.glColor3f(0.2, 0.6, 1.0)
            gl.glVertex3f(series.x[i], series.y[i], series.z[i] if series.z else 0)
        gl.glEnd()
        
    def _render_line(self, series: DataSeries, config: ChartConfig):
        """渲染折线图"""
        import OpenGL.GL as gl
        gl.glLineWidth(2.0)
        gl.glBegin(gl.GL_LINE_STRIP)
        for i in range(len(series.x)):
            gl.glColor3f(0.2, 0.8, 0.4)
            gl.glVertex2f(series.x[i], series.y[i])
        gl.glEnd()
        
    def _render_2d_scatter(self, series: DataSeries, config: ChartConfig):
        """渲染2D散点图"""
        import OpenGL.GL as gl
        gl.glPointSize(4.0)
        gl.glBegin(gl.GL_POINTS)
        for i in range(len(series.x)):
            gl.glColor3f(0.8, 0.3, 0.2)
            gl.gl
