#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/main.py - Kameleo 反检测浏览器指纹伪装技能核心逻辑

本脚本依据功能规格独立实现，提供：
  1. 浏览器指纹伪装参数生成与校验
  2. 多配置文件隔离管理（内存模拟）
  3. 自动化脚本注入辅助（WebDriver 连接串生成）
  4. 批量创建配置文件的 API 模拟
  5. 自托管部署环境检查
  6. 离线自检（--selftest）

仅使用 Python 标准库，无第三方依赖。
错误码约定：
  E001 - 参数缺失或类型错误
  E002 - 配置不存在
  E003 - 配置已存在
  E004 - 指纹参数非法
  E005 - 引擎不支持
  E006 - 自动化协议不支持
  E007 - 批量创建数量非法
  E008 - 自检断言失败
  E009 - 未知命令
  E010 - 内部状态异常
"""

import argparse
import hashlib
import json
import os
import platform
import random
import re
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ------------------------------------------------------------
# 常量定义
# ------------------------------------------------------------
SUPPORTED_ENGINES = ("chromium", "firefox")
SUPPORTED_AUTOMATION_PROTOCOLS = ("selenium", "playwright", "puppeteer")
DEFAULT_FINGERPRINT_KEYS = (
    "canvas", "webgl", "timezone", "fonts", "user_agent", "resolution", "language"
)
ERROR_CODES = {
    "E001": "参数缺失或类型错误",
    "E002": "配置不存在",
    "E003": "配置已存在",
    "E004": "指纹参数非法",
    "E005": "引擎不支持",
    "E006": "自动化协议不支持",
    "E007": "批量创建数量非法",
    "E008": "自检断言失败",
    "E009": "未知命令",
    "E010": "内部状态异常",
}


# ------------------------------------------------------------
# 数据模型
# ------------------------------------------------------------
@dataclass
class FingerprintProfile:
    """浏览器指纹配置文件"""
    profile_id: str
    name: str
    engine: str
    fingerprint: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    automation_port: Optional[int] = None
    is_running: bool = False


@dataclass
class AutomationConnection:
    """自动化连接信息"""
    protocol: str
    host: str
    port: int
    connection_string: str
    profile_id: str


# ------------------------------------------------------------
# 核心逻辑类
# ------------------------------------------------------------
class KameleoManager:
    """Kameleo 反检测浏览器管理器（内存实现）"""

    def __init__(self) -> None:
        """初始化管理器，创建空配置存储"""
        self._profiles: Dict[str, FingerprintProfile] = {}
        self._profile_name_index: Dict[str, str] = {}  # name -> profile_id

    # ---------- 指纹生成 ----------
    @staticmethod
    def _generate_fingerprint(engine: str, seed: Optional[str] = None) -> Dict[str, Any]:
        """
        生成浏览器指纹参数集合。

        参数:
            engine: 浏览器引擎（chromium/firefox）
            seed: 随机种子，用于确定性生成（测试用）

        返回:
            包含各类指纹参数的字典

        异常:
            E005: 不支持的引擎
        """
        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"E005: 不支持的引擎 '{engine}'，仅支持 {SUPPORTED_ENGINES}")

        rng = random.Random(seed)

        # 根据引擎选择 User-Agent 模板
        if engine == "chromium":
            chrome_versions = [120, 121, 122, 123, 124, 125, 126]
            ua = (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{rng.choice(chrome_versions)}.0.0.0 Safari/537.36"
            )
        else:  # firefox
            firefox_versions = [115, 120, 121, 122, 123, 124, 125]
            ua = (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{rng.choice(firefox_versions)}.0) "
                f"Gecko/20100101 Firefox/{rng.choice(firefox_versions)}.0"
            )

        # 常见时区列表
        timezones = [
            "Asia/Shanghai", "Asia/Tokyo", "America/New_York",
            "Europe/London", "Europe/Paris", "Australia/Sydney",
            "America/Los_Angeles", "Asia/Singapore", "Europe/Berlin"
        ]

        # 常见字体列表
        fonts_pool = [
            ["Arial", "Helvetica", "sans-serif"],
            ["Times New Roman", "Georgia", "serif"],
            ["Courier New", "monospace"],
            ["Verdana", "Geneva", "sans-serif"],
            ["Tahoma", "Lucida Grande", "sans-serif"],
            ["Trebuchet MS", "Helvetica", "sans-serif"]
        ]

        # 常见分辨率
        resolutions = [
            (1920, 1080), (1366, 768), (1440, 900),
            (1536, 864), (1280, 720), (2560, 1440)
        ]

        # Canvas 指纹（模拟噪声参数）
        canvas_noise = rng.uniform(0.0001, 0.01)

        # WebGL 渲染器
        webgl_renderers = [
            "ANGLE (NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0)"
        ]

        fingerprint = {
            "canvas": {
                "noise": round(canvas_noise, 6),
                "hash": hashlib.md5(f"{engine}-{canvas_noise}-{rng.random()}".encode()).hexdigest()[:16]
            },
            "webgl": {
                "renderer": rng.choice(webgl_renderers),
                "vendor": "Google Inc. (NVIDIA)" if "NVIDIA" in rng.choice(webgl_renderers) else "Google Inc. (Intel)",
                "version": "WebGL 2.0"
            },
            "timezone": rng.choice(timezones),
            "fonts": rng.choice(fonts_pool),
            "user_agent": ua,
            "resolution": rng.choice(resolutions),
            "language": rng.choice(["en-US", "zh-CN", "zh-TW", "ja-JP", "ko-KR"]),
            "hardware_concurrency": rng.choice([4, 8, 12, 16]),
            "device_memory": rng.choice([4, 8, 16, 32]),
            "platform": "Win32",
            "do_not_track": rng.choice(["1", "0", "unspecified"]),
            "color_depth": 24,
            "pixel_ratio": rng.choice([1.0, 1.25, 1.5, 2.0])
        }
        return fingerprint

    @staticmethod
    def _validate_fingerprint(fingerprint: Dict[str, Any]) -> None:
        """
        校验指纹参数是否合法。

        参数:
            fingerprint: 待校验的指纹字典

        异常:
            E004: 指纹参数非法
        """
        if not isinstance(fingerprint, dict):
            raise ValueError("E004: 指纹必须是字典类型")

        for key in DEFAULT_FINGERPRINT_KEYS:
            if key not in fingerprint:
                raise ValueError(f"E004: 缺少必要指纹参数 '{key}'")

        # 校验 user_agent 格式
        ua = fingerprint.get("user_agent", "")
        if not isinstance(ua, str) or "Mozilla" not in ua:
            raise ValueError("E004: user_agent 格式非法")

        # 校验 timezone
        tz = fingerprint.get("timezone", "")
        if not isinstance(tz, str) or "/" not in tz:
            raise ValueError("E004: timezone 格式非法")

        # 校验 resolution
        res = fingerprint.get("resolution")
        if not isinstance(res, (tuple, list)) or len(res) != 2:
            raise ValueError("E004: resolution 必须是 (width, height) 二元组")
        w, h = res
        if not (320 <= w <= 7680 and 200 <= h <= 4320):
            raise ValueError("E004: resolution 超出合理范围")

    # ---------- 配置文件管理 ----------
    def create_profile(
        self,
        name: str,
        engine: str = "chromium",
        fingerprint: Optional[Dict[str, Any]] = None
    ) -> FingerprintProfile:
        """
        创建新的浏览器配置文件。

        参数:
            name: 配置名称（唯一）
            engine: 浏览器引擎
            fingerprint: 自定义指纹（可选，默认自动生成）

        返回:
            创建的配置文件对象

        异常:
            E001: 参数缺失
            E003: 配置名已存在
            E005: 引擎不支持
            E004: 指纹非法
        """
        if not name or not isinstance(name, str):
            raise ValueError("E001: 配置名称不能为空且必须为字符串")

        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"E005: 不支持的引擎 '{engine}'")

        if name in self._profile_name_index:
            raise ValueError(f"E003: 配置名称 '{name}' 已存在")

        # 生成或使用自定义指纹
        if fingerprint is None:
            fingerprint = self._generate_fingerprint(engine, seed=name)
        else:
            self._validate_fingerprint(fingerprint)

        # 创建配置
        profile_id = str(uuid.uuid4())
        profile = FingerprintProfile(
            profile_id=profile_id,
            name=name,
            engine=engine,
            fingerprint=fingerprint
        )

        self._profiles[profile_id] = profile
        self._profile_name_index[name] = profile_id
        return profile

    def get_profile(self, profile_id: str) -> FingerprintProfile:
        """
        获取指定配置。

        参数:
            profile_id: 配置 ID

        返回:
            配置文件对象

        异常:
            E002: 配置不存在
        """
        if profile_id not in self._profiles:
            raise ValueError(f"E002: 配置 '{profile_id}' 不存在")
        return self._profiles[profile_id]

    def get_profile_by_name(self, name: str) -> FingerprintProfile:
        """
        根据名称获取配置。

        参数:
            name: 配置名称

        返回:
            配置文件对象

        异常:
            E002: 配置不存在
        """
        if name not in self._profile_name_index:
            raise ValueError(f"E002: 配置 '{name}' 不存在")
        profile_id = self._profile_name_index[name]
        return self._profiles[profile_id]

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        列出所有配置概要信息。

        返回:
            配置概要列表
        """
        result = []
        for profile in self._profiles.values():
            result.append({
                "profile_id": profile.profile_id,
                "name": profile.name,
                "engine": profile.engine,
                "is_running": profile.is_running,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            })
        return result

    def delete_profile(self, profile_id: str) -> bool:
        """
        删除指定配置。

        参数:
            profile_id: 配置 ID

        返回:
            是否删除成功

        异常:
            E002: 配置不存在
        """
        if profile_id not in self._profiles:
            raise ValueError(f"E002: 配置 '{profile_id}' 不存在")

        profile = self._profiles.pop(profile_id)
        self._profile_name_index.pop(profile.name, None)
        return True

    def update_profile_fingerprint(
        self,
        profile_id: str,
        fingerprint: Dict[str, Any]
    ) -> FingerprintProfile:
        """
        更新配置的指纹参数。

        参数:
            profile_id: 配置 ID
            fingerprint: 新的指纹参数

        返回:
            更新后的配置文件对象

        异常:
            E002: 配置不存在
            E004: 指纹非法
        """
        profile = self.get_profile(profile_id)
        self._validate_fingerprint(fingerprint)
        profile.fingerprint = fingerprint
        profile.updated_at = time.time()
        return profile

    # ---------- 批量操作 ----------
    def batch_create_profiles(
        self,
        names: List[str],
        engine: str = "chromium"
    ) -> List[FingerprintProfile]:
        """
        批量创建配置文件。

        参数:
            names: 配置名称列表
            engine: 浏览器引擎

        返回:
            创建的配置文件列表

        异常:
            E001: 参数缺失
            E007: 批量数量非法
            E005: 引擎不支持
        """
        if not names or not isinstance(names, list):
            raise ValueError("E001: 名称列表不能为空")

        if len(names) > 100:
            raise ValueError(f"E007: 批量创建数量 {len(names)} 超过上限 100")

        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"E005: 不支持的引擎 '{engine}'")

        created = []
        for name in names:
            profile = self.create_profile(name, engine=engine)
            created.append(profile)
        return created

    # ---------- 自动化连接 ----------
    def start_automation(
        self,
        profile_id: str,
        protocol: str = "selenium",
        host: str = "127.0.0.1",
        port: Optional[int] = None
    ) -> AutomationConnection:
        """
        启动自动化连接（模拟）。

        参数:
            profile_id: 配置 ID
            protocol: 自动化协议
            host: 主机地址
            port: 端口（默认随机 9000-9999）

        返回:
            自动化连接信息

        异常:
            E002: 配置不存在
            E006: 协议不支持
        """
        profile = self.get_profile(profile_id)

        if protocol not in SUPPORTED_AUTOMATION_PROTOCOLS:
            raise ValueError(f"E006: 不支持的自动化协议 '{protocol}'")

        if port is None:
            port = random.randint(9000, 9999)

        # 生成连接字符串
        if protocol == "selenium":
            conn_str = f"http://{host}:{port}/wd/hub"
        elif protocol == "playwright":
            conn_str = f"ws://{host}:{port}/playwright"
        else:  # puppeteer
            conn_str = f"http://{host}:{port}/puppeteer"

        profile.automation_port = port
        profile.is_running = True
        profile.updated_at = time.time()

        return AutomationConnection(
            protocol=protocol,
            host=host,
            port=port,
            connection_string=conn_str,
            profile_id=profile_id
        )

    def stop_automation(self, profile_id: str) -> bool:
        """
        停止自动化连接。

        参数:
            profile_id: 配置 ID

        返回:
            是否停止成功

        异常:
            E002: 配置不存在
        """
        profile = self.get_profile(profile_id)
        profile.automation_port = None
        profile.is_running = False
        profile.updated_at = time.time()
        return True

    # ---------- 部署与环境 ----------
    @staticmethod
    def check_deployment_environment() -> Dict[str, Any]:
        """
        检查自托管部署环境。

        返回:
            环境信息字典
        """
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "temp_dir": tempfile.gettempdir(),
            "cwd": os.getcwd(),
            "is_64bit": sys.maxsize > 2**32,
            "timestamp": time.time()
        }
        return info

    # ---------- 序列化 ----------
    def to_json(self, profile_id: str) -> str:
        """
        将配置序列化为 JSON 字符串。

        参数:
            profile_id: 配置 ID

        返回:
            JSON 字符串

        异常:
            E002: 配置不存在
        """
        profile = self.get_profile(profile_id)
        return json.dumps(asdict(profile), ensure_ascii=False, indent=2)

    def export_all_profiles(self) -> str:
        """
        导出所有配置为 JSON 字符串。

        返回:
            所有配置的 JSON 字符串
        """
        profiles_data = []
        for profile in self._profiles.values():
            profiles_data.append(asdict(profile))
        return json.dumps(profiles_data, ensure_ascii=False, indent=2)


# ------------------------------------------------------------
# 自检模块（离线内置样例）
# ------------------------------------------------------------
def _run_selftest() -> int:
    """
    运行内置自检程序，验证核心逻辑。

    使用硬编码样例数据，不依赖外部文件、网络或当前工作目录。

    返回:
        0 - 全部通过
        1 - 存在失败项（打印错误详情）

    异常:
        E008: 自检断言失败
    """
    print("=" * 60)
    print("Kameleo 核心逻辑自检 (--selftest)")
    print("=" * 60)

    failures: List[str] = []

    # 辅助断言函数（宽松阈值）
    def assert_true(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)
            print(f"  [FAIL] {message}")
        else:
            print(f"  [PASS] {message}")

    # --------------------------------------------------------
    # 测试 1: 创建配置文件（默认指纹）
    # --------------------------------------------------------
    print("\n[1] 创建配置文件测试")
    manager = KameleoManager()

    try:
        profile1 = manager.create_profile(name="test_profile_a", engine="chromium")
        assert_true(profile1.profile_id is not None, "创建配置后应生成 profile_id")
        assert_true(len(profile1.profile_id) > 10, "profile_id 长度应大于 10")
        assert_true(profile1.engine == "chromium", "引擎应为 chromium")
        assert_true(profile1.name == "test_profile_a", "配置名应正确保存")
        assert_true("user_agent" in profile1.fingerprint, "指纹应包含 user_agent")
        assert_true("Mozilla" in profile1.fingerprint["user_agent"], "User-Agent 应包含 Mozilla")
        assert_true("canvas" in profile1.fingerprint, "指纹应包含 canvas")
        assert_true("webgl" in profile1.fingerprint, "指纹应包含 webgl")
        assert_true("timezone" in profile1.fingerprint, "指纹应包含 timezone")
        assert_true("fonts" in profile1.fingerprint, "指纹应包含 fonts")
    except ValueError as e:
        assert_true(False, f"创建配置异常: {e}")

    # --------------------------------------------------------
    # 测试 2: 指纹参数合理性（宽松区间）
    # --------------------------------------------------------
    print("\n[2] 指纹参数合理性测试")
    try:
        fp = profile1.fingerprint
        res = fp.get("resolution", (0, 0))
        assert_true(isinstance(res, (tuple, list)), "分辨率应为元组或列表")
        assert_true(len(res) == 2, "分辨率应包含两个值")
        w, h = res
        assert_true(320 <= w <= 7680, f"宽度应在合理范围 (320-7680)，实际: {w}")
        assert_true(200 <= h <= 4320, f"高度应在合理范围 (200-4320)，实际: {h}")

        hc = fp.get("hardware_concurrency", 0)
        assert_true(1 <= hc <= 64, f"硬件并发数应在 1-64 范围，实际: {hc}")

        dm = fp.get("device_memory", 0)
        assert_true(dm in (2, 4, 8, 16, 32, 64), f"设备内存应为 2 的幂，实际: {dm}")

        canvas_noise = fp.get("canvas", {}).get("noise", 0)
        assert_true(0 < canvas_noise < 0.1, f"Canvas 噪声应在 (0, 0.1) 区间，实际: {canvas_noise}")

        tz = fp.get("timezone", "")
        assert_true("/" in tz, f"时区应包含区域/城市格式，实际: {tz}")
    except Exception as e:
        assert_true(False, f"指纹校验异常: {e}")

    # --------------------------------------------------------
    # 测试 3: Firefox 引擎指纹差异
    # --------------------------------------------------------
    print("\n[3] Firefox 引擎测试")
    try:
        profile_ff = manager.create_profile(name="test_profile_ff", engine="firefox")
        assert_true(profile_ff.engine == "firefox", "引擎应为 firefox")
        ua_ff = profile_ff.fingerprint.get("user_agent", "")
        assert_true("Firefox" in ua_ff, f"Firefox 的 UA 应包含 Firefox，实际: {ua_ff[:50]}...")
        assert_true("Chrome" not in ua_ff, "Firefox 的 UA 不应包含 Chrome")
    except ValueError as e:
        assert_true(False, f"Firefox 配置异常: {e}")

    # --------------------------------------------------------
    # 测试 4: 配置隔离性
    # --------------------------------------------------------
    print("\n[4] 配置隔离性测试")
    try:
        profile_a = manager.get_profile_by_name("test_profile_a")
        profile_b = manager.get_profile_by_name("test_profile_ff")
        assert_true(profile_a.profile_id != profile_b.profile_id, "两个配置的 ID 应不同")
        assert_true(
            profile_a.fingerprint.get("user_agent") != profile_b.fingerprint.get("user_agent"),
            "两个配置的 User-Agent 应不同"
        )
        # 修改 A 的指纹不影响 B
        old_b_ua = profile_b.fingerprint["user_agent"]
        new_fp = dict(profile_a.fingerprint)
        new_fp["user_agent"] = "Mozilla/5.0 (Custom Test UA)"
        manager.update_profile_fingerprint(profile_a.profile_id, new_fp)
        profile_b_after = manager.get_profile_by_name("test_profile_ff")
        assert_true(
            profile_b_after.fingerprint["user_agent"] == old_b_ua,
            "修改配置 A 不应影响配置 B"
        )
    except ValueError as e:
        assert_true(False, f"隔离性测试异常: {e}")

    # --------------------------------------------------------
    # 测试 5: 批量创建
    # --------------------------------------------------------
    print("\n[5] 批量创建测试")
    try:
        batch_names = [f"batch_profile_{i}" for i in range(5)]
        batch_profiles = manager.batch_create_profiles(batch_names, engine="chromium")
        assert_true(len(batch_profiles) == 5, f"应创建 5 个配置，实际: {len(batch_profiles)}")
        all_names = [p.name for p in batch_profiles]
        assert_true(all(n in all_names for n in batch_names), "批量创建的配置名应正确")
        # 配置 ID 唯一性
        all_ids = [p.profile_id for p in batch_profiles]
        assert_true(len(set(all_ids)) == 5, "批量创建的配置 ID 应唯一")
    except ValueError as e:
        assert_true(False, f"批量创建异常: {e}")

    # --------------------------------------------------------
    # 测试 6: 自动化连接
    # --------------------------------------------------------
    print("\n[6] 自动化连接测试")
    try:
        conn = manager.start_automation(profile1.profile_id, protocol="selenium")
        assert_true(conn.protocol == "selenium", "协议应为 selenium")
        assert_true(conn.port > 0, f"端口应大于 0，实际: {conn.port}")
        assert_true("wd/hub" in conn.connection_string, "Selenium 连接串应包含 wd/hub")
        assert_true("127.0.0.1" in conn.connection_string, "连接串应包含主机地址")

        # Playwright
        conn_pw = manager.start_automation(profile1.profile_id, protocol="playwright", port=9222)
        assert_true(conn_pw.port == 9222, "指定端口应生效")
        assert_true("playwright" in conn_pw.connection_string, "Playwright 连接串应包含协议名")

        # 停止自动化
        stopped = manager.stop_automation(profile1.profile_id)
        assert_true(stopped, "停止自动化应返回 True")
        profile_after_stop = manager.get_profile(profile1.profile_id)
        assert_true(not profile_after_stop.is_running, "停止后 is_running 应为 False")
    except ValueError as e:
        assert_true(False, f"自动化连接异常: {e}")

    # --------------------------------------------------------
    # 测试 7: 错误处理
    # --------------------------------------------------------
    print("\n[7] 错误处理测试")
    try:
        # E002 - 不存在的配置
        try:
            manager.get_profile("nonexistent_id_12345")
            assert_true(False, "访问不存在的配置应抛出异常")
        except ValueError as e:
            assert_true("E002" in str(e), f"应抛出 E002 错误，实际: {e}")

        # E003 - 重复名称
        try:
            manager.create_profile(name="test_profile_a", engine="chromium")
            assert_true(False, "重复创建同名配置应抛出异常")
        except ValueError as e:
            assert_true("E003" in str(e), f"应抛出 E003 错误，实际: {e}")

        # E005 - 不支持的引擎
        try:
            manager.create_profile(name="invalid_engine_profile", engine="safari")
            assert_true(False, "不支持的引擎应抛出异常")
        except ValueError as e:
            assert_true("E005" in str(e), f"应抛出 E005 错误，实际: {e}")

        # E006 - 不支持的自动化协议
        try:
            manager.start_automation(profile1.profile_id, protocol="cypress")
            assert_true(False, "不支持的协议应抛出异常")
        except ValueError as e:
            assert_true("E006" in str(e), f"应抛出 E006 错误，实际: {e}")

        # E007 - 批量数量超限
        try:
            too_many = [f"overflow_{i}" for i in range(101)]
            manager.batch_create_profiles(too_many)
            assert_true(False, "超过 100 个的批量创建应抛出异常")
        except ValueError as e:
            assert_true("E007" in str(e), f"应抛出 E007 错误，实际: {e}")
    except Exception as e:
        assert_true(False, f"错误处理测试异常: {e}")

    # --------------------------------------------------------
    # 测试 8: 自定义指纹
    # --------------------------------------------------------
    print("\n[8] 自定义指纹测试")
    try:
        custom_fp = {
            "canvas": {"noise": 0.005, "hash": "abc123def456"},
            "webgl": {"renderer": "Custom Renderer", "vendor": "Custom Vendor", "version": "WebGL 2.0"},
            "timezone": "Asia/Shanghai",
            "fonts": ["Arial", "Helvetica", "sans-serif"],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomUA/1.0",
            "resolution": (1920, 1080),
            "language": "zh-CN",
            "hardware_concurrency": 8,
            "device_memory": 16,
            "platform": "Win32",
            "do_not_track": "1",
            "color_depth": 24,
            "pixel_ratio": 1.5
        }
        profile_custom = manager.create_profile(
            name="custom_fp_profile",
            engine="chromium",
            fingerprint=custom_fp
        )
        assert_true(
            profile_custom.fingerprint["user_agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CustomUA/1.0",
            "自定义 UA 应被正确保存"
        )
        assert_true(
            profile_custom.fingerprint["timezone"] == "Asia/Shanghai",
            "自定义时区应被正确保存"
        )
        assert_true(
            profile_custom.fingerprint["resolution"] == (1920, 1080),
            "自定义分辨率应被正确保存"
        )
    except ValueError as e:
        assert_true(False, f"自定义指纹测试异常: {e}")

    # --------------------------------------------------------
    # 测试 9: 序列化
    # --------------------------------------------------------
    print("\n[9] 序列化测试")
    try:
        json_str = manager.to_json(profile1.profile_id)
        data = json.loads(json_str)
        assert_true(data["name"] == "test_profile_a", "JSON 应包含配置名称")
        assert_true("fingerprint" in data, "JSON 应包含指纹数据")
        assert_true("profile_id" in data, "JSON 应包含 profile_id")
    except (ValueError, json.JSONDecodeError) as e:
        assert_true(False, f"序列化测试异常: {e}")

    # --------------------------------------------------------
    # 测试 10: 部署环境检查
    # --------------------------------------------------------
    print("\n[10] 部署环境检查测试")
    try:
        env_info = manager.check_deployment_environment()
        assert_true("os" in env_info, "环境信息应包含操作系统")
        assert_true("python_version" in env_info, "环境信息应包含 Python 版本")
        assert_true("timestamp" in env_info, "环境信息应包含时间戳")
        assert_true(env_info["timestamp"] > 0, "时间戳应大于 0")
    except Exception as e:
        assert_true(False, f"环境检查异常: {e}")

    # --------------------------------------------------------
    # 汇总结果
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    if failures:
        print(f"自检完成: {len(failures)} 项失败")
        for i, f in enumerate(failures, 1):
            print(f"  {i}. {f}")
        print("=" * 60)
        return 1
    else:
        print("自检完成: 全部通过 ✓")
        print("=" * 60)
        return 0


# ------------------------------------------------------------
# 命令行入口
# ------------------------------------------------------------
def main() -> int:
    """
    命令行主入口。

    返回:
        进程退出码
    """
    parser = argparse.ArgumentParser(
        description="Kameleo 反检测浏览器指纹伪装工具（核心逻辑实现）",
        epilog="示例: python main.py --selftest"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行内置离线自检（不依赖外部文件/网络）"
    )
    parser.add_argument(
        "--create",
        type=str,
        metavar="NAME",
        help="创建新配置（自动生成指纹）"
    )
    parser.add_argument(
        "--engine",
        type=str,
        default="chromium",
        choices=SUPPORTED_ENGINES,
        help=f"浏览器引擎（默认: chromium，可选: {', '.join(SUPPORTED_ENGINES)}）"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有配置"
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="检查部署环境"
    )

    args = parser.parse_args()

    # 自检模式
    if args.selftest:
        return _run_selftest()

    # 环境检查模式
    if args.env:
        manager = KameleoManager()
        env_info = manager.check_deployment_environment()
        print(json.dumps(env_info, ensure_ascii=False, indent=2))
        return 0

    # 创建配置模式
    if args.create:
        manager = KameleoManager()
        try:
            profile = manager.create_profile(name=args.create, engine=args.engine)
            print(f"创建成功:")
            print(f"  profile_id: {profile.profile_id}")
            print(f"  name: {profile.name}")
            print(f"  engine: {profile.engine}")
            print(f"  user_agent: {profile.fingerprint['user_agent']}")
            print(f"  timezone: {profile.fingerprint['timezone']}")
            print(f"  resolution: {profile.fingerprint['resolution']}")
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 1

    # 列表模式
    if args.list:
        manager = KameleoManager()
        # 创建一些示例配置以便展示
        try:
            manager.create_profile("demo_chromium", engine="chromium")
            manager.create_profile("demo_firefox", engine="firefox")
        except ValueError:
            pass  # 已存在则忽略
        profiles = manager.list_profiles()
        if not profiles:
            print("暂无配置")
        else:
            print(f"共 {len(profiles)} 个配置:")
            for p in profiles:
                status = "运行中" if p["is_running"] else "已停止"
                print(f"  [{p['engine']}] {p['name']} ({p['profile_id'][:8]}...) - {status}")
        return 0

    # 无参数时显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
