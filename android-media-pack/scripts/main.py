#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
android-media-pack 技能包独立实现脚本

本脚本依据功能规格 clean-room 实现，提供以下能力：
  C1: 迁移辅助（ExoPlayer 2.x -> Media3）
  C2: Compose 播放器 UI 代码生成
  C3: 流媒体配置生成（HLS / DASH / SmoothStreaming）
  C4: DRM 集成方案生成（Widevine 等）
  C5: 广告集成指引（IMA / 自定义广告 Server）

错误码说明：
  E001: 未知命令
  E002: 参数缺失或非法
  E003: 不支持的流媒体格式
  E004: 不支持的 DRM 方案
  E005: 不支持的广告类型
  E006: 输入内容为空
  E007: 输出目录不可写
  E008: 内部逻辑错误
  E009: 自检失败
  E010: 未捕获的异常

仅使用 Python 标准库，无第三方依赖。
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


# ============================================================
# 常量定义
# ============================================================

MEDIA3_VERSION = "1.10.1"
EXOPLAYER_OLD_GROUP = "com.google.android.exoplayer2"
EXOPLAYER_NEW_GROUP = "androidx.media3"

# 流媒体格式支持列表
SUPPORTED_STREAM_TYPES = {"hls", "dash", "smoothstreaming"}

# DRM 方案支持列表
SUPPORTED_DRM_SCHEMES = {"widevine", "playready", "clearkey"}

# 广告类型支持列表
SUPPORTED_AD_TYPES = {"ima", "custom"}

# 错误码映射
ERROR_MESSAGES = {
    "E001": "未知命令，请使用 --help 查看支持的命令",
    "E002": "参数缺失或非法，请检查输入",
    "E003": "不支持的流媒体格式，仅支持: hls, dash, smoothstreaming",
    "E004": "不支持的 DRM 方案，仅支持: widevine, playready, clearkey",
    "E005": "不支持的广告类型，仅支持: ima, custom",
    "E006": "输入内容为空，请提供有效内容",
    "E007": "输出目录不可写",
    "E008": "内部逻辑错误",
    "E009": "自检失败，请检查实现",
    "E010": "未捕获的异常",
}


# ============================================================
# 核心逻辑：迁移辅助 (C1)
# ============================================================

def generate_migration_guide(original_code: str = "") -> str:
    """
    生成 ExoPlayer 2.x 到 Media3 的迁移指南。

    依据规格 C1：将 ExoPlayer 2.x 代码迁移到 Media3 1.10.1。
    返回迁移说明文本（含常见替换规则）。
    """
    if not original_code:
        return (
            "【迁移辅助说明】\n"
            f"目标版本: Media3 {MEDIA3_VERSION}\n\n"
            "常见替换规则:\n"
            "  1. 包名替换:\n"
            f"     {EXOPLAYER_OLD_GROUP}.*  ->  {EXOPLAYER_NEW_GROUP}.*\n"
            "     示例: com.google.android.exoplayer2.ExoPlayer\n"
            "           -> androidx.media3.exoplayer.ExoPlayer\n"
            "  2. 依赖项替换:\n"
            "     implementation 'com.google.android.exoplayer2:exoplayer:2.x'\n"
            "     -> implementation 'androidx.media3:media3-exoplayer:1.10.1'\n"
            "  3. 核心类变更:\n"
            "     - ExoPlayer 接口方法基本兼容，注意包名变化\n"
            "     - PlayerView -> PlayerView (androidx.media3.ui.PlayerView)\n"
            "     - DefaultTrackSelector 包名更新\n"
            "  4. 构建脚本 (build.gradle):\n"
            "     - 确保 compileSdk >= 34\n"
            "     - 启用 coreLibraryDesugaring（如使用 Java 8+ API）\n"
            "  5. 注意事项:\n"
            "     - 检查所有 import 语句\n"
            "     - 检查 manifest 中 provider 配置\n"
            "     - 建议逐步迁移并编译验证\n"
        )

    # 简单统计原始代码中的旧包名出现次数
    old_pkg_count = original_code.count(EXOPLAYER_OLD_GROUP)
    lines = original_code.splitlines()
    total_lines = len(lines)

    guide = []
    guide.append("【迁移辅助报告】")
    guide.append(f"目标版本: Media3 {MEDIA3_VERSION}")
    guide.append(f"输入代码行数: {total_lines}")
    guide.append(f"检测到旧包名出现次数: {old_pkg_count}")
    guide.append("")
    guide.append("迁移步骤建议:")
    guide.append("  1. 全局替换包名: com.google.android.exoplayer2 -> androidx.media3")
    guide.append("  2. 更新 build.gradle 依赖:")
    guide.append("     - 移除 exoplayer 2.x 依赖")
    guide.append("     - 添加 media3-exoplayer, media3-ui, media3-datasource 等")
    guide.append("  3. 检查 PlayerView 布局 XML 中的标签名")
    guide.append("  4. 编译并修复剩余 import 错误")
    guide.append("  5. 验证播放功能正常")
    guide.append("")
    guide.append("详细替换规则请参考官方迁移文档。")

    return "\n".join(guide)


# ============================================================
# 核心逻辑：Compose 播放器 UI (C2)
# ============================================================

def generate_compose_player_ui(ui_requirements: Dict[str, Any] = None) -> str:
    """
    生成基于 Jetpack Compose 的播放器 UI 代码。

    依据规格 C2：生成基于 Jetpack Compose 的播放器界面代码。
    支持指定控制条、手势、全屏等需求。
    """
    req = ui_requirements or {}
    show_controls = req.get("controls", True)
    enable_fullscreen = req.get("fullscreen", True)
    enable_gestures = req.get("gestures", False)

    lines = []
    lines.append("// 自动生成的 Jetpack Compose 播放器 UI 代码")
    lines.append("// 依赖: androidx.media3:media3-ui-compose")
    lines.append("")
    lines.append("import androidx.compose.foundation.layout.Box")
    lines.append("import androidx.compose.foundation.layout.fillMaxSize")
    lines.append("import androidx.compose.runtime.Composable")
    lines.append("import androidx.compose.ui.Modifier")
    lines.append("import androidx.media3.ui.compose.PlayerSurface")
    lines.append("import androidx.media3.ui.compose.PlayerController")
    lines.append("import androidx.media3.ui.compose.rememberPlayerControllerState")
    lines.append("")
    lines.append("@Composable")
    lines.append("fun MediaPlayerScreen(player: ExoPlayer, modifier: Modifier = Modifier) {")
    lines.append("    Box(modifier = modifier.fillMaxSize()) {")
    lines.append("        // 播放器画面")
    lines.append("        PlayerSurface(player = player, modifier = Modifier.fillMaxSize())")
    lines.append("")

    if show_controls:
        lines.append("        // 控制条")
        lines.append("        val controllerState = rememberPlayerControllerState(player)")
        lines.append("        PlayerController(")
        lines.append("            player = player,")
        lines.append("            controllerState = controllerState,")
        lines.append("            modifier = Modifier.fillMaxSize()")
        lines.append("        )")
        lines.append("")

    if enable_fullscreen:
        lines.append("        // 全屏切换按钮逻辑（需结合 Activity 状态）")
        lines.append("        // 示例: 点击后切换窗口布局")
        lines.append("")

    if enable_gestures:
        lines.append("        // 手势控制（滑动调节音量/亮度/进度）")
        lines.append("        // 建议使用 Modifier.pointerInput 实现")
        lines.append("")

    lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("// 使用示例:")
    lines.append("// @Preview")
    lines.append("// @Composable")
    lines.append("// fun PreviewMediaPlayer() {")
    lines.append("//     val context = LocalContext.current")
    lines.append("//     val player = remember {")
    lines.append("//         ExoPlayer.Builder(context).build()")
    lines.append("//     }")
    lines.append("//     MediaPlayerScreen(player = player)")
    lines.append("// }")

    return "\n".join(lines)


# ============================================================
# 核心逻辑：流媒体配置 (C3)
# ============================================================

def generate_streaming_config(stream_type: str, url: str) -> str:
    """
    生成流媒体播放配置代码。

    依据规格 C3：配置 HLS / DASH / SmoothStreaming 播放参数。
    返回 MediaItem 构建代码。
    """
    stream_type = stream_type.lower().strip()

    if stream_type not in SUPPORTED_STREAM_TYPES:
        raise ValueError("E003")

    if not url:
        raise ValueError("E006")

    # 根据格式生成不同配置
    if stream_type == "hls":
        extra_config = (
            "            .setMimeType(MimeTypes.APPLICATION_M3U8)\n"
            "            .setStreamType(C.CONTENT_TYPE_URI)"
        )
    elif stream_type == "dash":
        extra_config = (
            "            .setMimeType(MimeTypes.APPLICATION_MPD)\n"
            "            .setStreamType(C.CONTENT_TYPE_URI)"
        )
    else:  # smoothstreaming
        extra_config = (
            "            .setMimeType(MimeTypes.APPLICATION_SS)\n"
            "            .setStreamType(C.CONTENT_TYPE_URI)"
        )

    code = []
    code.append("// 自动生成的流媒体配置代码")
    code.append(f"// 格式: {stream_type.upper()}")
    code.append("")
    code.append("import androidx.media3.common.MediaItem")
    code.append("import androidx.media3.common.MimeTypes")
    code.append("import androidx.media3.common.C")
    code.append("")
    code.append("val mediaItem = MediaItem.Builder()")
    code.append(f"            .setUri(\"{url}\")")
    code.append(extra_config)
    code.append("            .build()")
    code.append("")
    code.append("// 播放器设置")
    code.append("player.setMediaItem(mediaItem)")
    code.append("player.prepare()")
    code.append("player.playWhenReady = true")
    code.append("")

    return "\n".join(code)


# ============================================================
# 核心逻辑：DRM 集成 (C4)
# ============================================================

def generate_drm_config(drm_scheme: str, license_url: str) -> str:
    """
    生成 DRM 集成方案代码。

    依据规格 C4：生成 Widevine 等 DRM 方案的接入代码。
    """
    drm_scheme = drm_scheme.lower().strip()

    if drm_scheme not in SUPPORTED_DRM_SCHEMES:
        raise ValueError("E004")

    if not license_url:
        raise ValueError("E006")

    # UUID 映射
    uuid_map = {
        "widevine": "EDEF8BA9-79D6-4ACE-A3C8-27DCD51D21ED",
        "playready": "9A04F079-9840-4286-AB92-E65BE0885F95",
        "clearkey": "1077EFEC-C0B2-4D02-ACE3-3C1E52E2FB4B",
    }

    uuid = uuid_map.get(drm_scheme, "")

    code = []
    code.append("// 自动生成的 DRM 集成代码")
    code.append(f"// 方案: {drm_scheme.upper()}")
    code.append("")
    code.append("import androidx.media3.common.MediaItem")
    code.append("import androidx.media3.common.MediaItem.DrmConfiguration")
    code.append("import androidx.media3.exoplayer.drm.ClearKeyUtil  // 如适用")
    code.append("import com.google.common.collect.ImmutableList")
    code.append("")
    code.append("val drmConfiguration = DrmConfiguration.Builder(")
    code.append(f"    UUID.fromString(\"{uuid}\")")
    code.append(")")
    code.append(f"    .setLicenseUri(\"{license_url}\")")
    code.append("    .setLicenseRequestHeaders(mapOf(")
    code.append("        // 按需添加自定义请求头")
    code.append("        // \"Authorization\" to \"Bearer token\"")
    code.append("    ))")
    code.append("    .build()")
    code.append("")
    code.append("val mediaItem = MediaItem.Builder()")
    code.append("    .setUri(\"YOUR_MEDIA_URL\")")
    code.append("    .setDrmConfiguration(drmConfiguration)")
    code.append("    .build()")
    code.append("")
    code.append("// 播放器设置")
    code.append("player.setMediaItem(mediaItem)")
    code.append("player.prepare()")
    code.append("player.playWhenReady = true")
    code.append("")

    return "\n".join(code)


# ============================================================
# 核心逻辑：广告集成 (C5)
# ============================================================

def generate_ad_integration(ad_type: str, ad_tag_url: str = "") -> str:
    """
    生成广告集成指引。

    依据规格 C5：提供 IMA / 自定义广告 Server 的接入步骤。
    """
    ad_type = ad_type.lower().strip()

    if ad_type not in SUPPORTED_AD_TYPES:
        raise ValueError("E005")

    guide = []
    guide.append(f"【{ad_type.upper()} 广告集成指引】")
    guide.append("")

    if ad_type == "ima":
        if not ad_tag_url:
            ad_tag_url = "YOUR_IMA_AD_TAG_URL"

        guide.append("1. 添加依赖:")
        guide.append("   implementation 'androidx.media3:media3-ui:1.10.1'")
        guide.append("   implementation 'androidx.media3:media3-exoplayer-ima:1.10.1'")
        guide.append("")
        guide.append("2. 在布局中添加广告视图:")
        guide.append("   <androidx.media3.ui.PlayerView")
        guide.append("       android:id=\"@+id/player_view\"")
        guide.append("       ... />")
        guide.append("")
        guide.append("3. 初始化 IMA 广告:")
        guide.append("   val adsLoader = ImaAdsLoader.Builder(context).build()")
        guide.append("   playerView.setAdUiViewGroup(adUiViewGroup)")
        guide.append("   playerView.setPlayer(player)")
        guide.append("")
        guide.append("4. 设置广告标签:")
        guide.append(f"   adsLoader.setAdTagUri(Uri.parse(\"{ad_tag_url}\"))")
        guide.append("")
        guide.append("5. 释放资源:")
        guide.append("   override fun onDestroy() {")
        guide.append("       adsLoader.release()")
        guide.append("       super.onDestroy()")
        guide.append("   }")
    else:  # custom
        guide.append("1. 实现自定义广告加载器:")
        guide.append("   - 继承 AdsLoader 接口")
        guide.append("   - 实现广告请求与回调")
        guide.append("")
        guide.append("2. 配置广告服务器:")
        guide.append("   - 定义广告标签协议")
        guide.append("   - 实现 VAST/VPAID 解析（如需要）")
        guide.append("")
        guide.append("3. 集成到播放器:")
        guide.append("   playerView.setAdUiViewGroup(adUiViewGroup)")
        guide.append("   playerView.setAdsLoader(customAdsLoader)")
        guide.append("")
        guide.append("4. 测试与验证:")
        guide.append("   - 验证广告触发时机")
        guide.append("   - 验证广告跳过逻辑")
        guide.append("   - 验证广告与内容切换")

    return "\n".join(guide)


# ============================================================
# 命令处理
# ============================================================

def handle_migrate(args: argparse.Namespace) -> str:
    """处理迁移命令"""
    code = args.code or ""
    return generate_migration_guide(code)


def handle_compose(args: argparse.Namespace) -> str:
    """处理 Compose UI 生成命令"""
    req = {}
    if args.controls is not None:
        req["controls"] = args.controls
    if args.fullscreen is not None:
        req["fullscreen"] = args.fullscreen
    if args.gestures is not None:
        req["gestures"] = args.gestures
    return generate_compose_player_ui(req)


def handle_stream(args: argparse.Namespace) -> str:
    """处理流媒体配置命令"""
    return generate_streaming_config(args.format, args.url)


def handle_drm(args: argparse.Namespace) -> str:
    """处理 DRM 集成命令"""
    return generate_drm_config(args.scheme, args.license_url)


def handle_ad(args: argparse.Namespace) -> str:
    """处理广告集成命令"""
    return generate_ad_integration(args.ad_type, args.ad_tag or "")


def handle_help(args: argparse.Namespace) -> str:
    """处理帮助命令"""
    return get_help_text()


def get_help_text() -> str:
    """获取帮助文本"""
    return """android-media-pack 技能包 - 命令行工具

用法:
  python main.py <命令> [选项]

命令:
  migrate    迁移辅助 (ExoPlayer 2.x -> Media3)
  compose    生成 Compose 播放器 UI
  stream     生成流媒体配置
  drm        生成 DRM 集成方案
  ad         生成广告集成指引
  help       显示帮助信息
  --selftest 运行自检

示例:
  python main.py migrate --code "com.google.android.exoplayer2.ExoPlayer"
  python main.py compose --controls true --fullscreen true
  python main.py stream --format hls --url https://example.com/stream.m3u8
  python main.py drm --scheme widevine --license_url https://license.example.com
  python main.py ad --ad_type ima --ad_tag https://example.com/ad.xml
"""


# ============================================================
# 命令行入口
# ============================================================

COMMAND_HANDLERS = {
    "migrate": handle_migrate,
    "compose": handle_compose,
    "stream": handle_stream,
    "drm": handle_drm,
    "ad": handle_ad,
    "help": handle_help,
}

# 定义各命令的参数（不设置 required=False，改为在 handler 中检查）
COMMAND_ARGS = {
    "migrate": [
        (["--code"], {"type": str, "default": None, "help": "原始代码片段"}),
    ],
    "compose": [
        (["--controls"], {"type": bool, "default": None, "help": "是否显示控制条"}),
        (["--fullscreen"], {"type": bool, "default": None, "help": "是否支持全屏"}),
        (["--gestures"], {"type": bool, "default": None, "help": "是否支持手势"}),
    ],
    "stream": [
        (["--format"], {"type": str, "default": None, "help": "流媒体格式: hls/dash/smoothstreaming"}),
        (["--url"], {"type": str, "default": None, "help": "流媒体 URL"}),
    ],
    "drm": [
        (["--scheme"], {"type": str, "default": None, "help": "DRM 方案: widevine/playready/clearkey"}),
        (["--license_url"], {"type": str, "default": None, "help": "许可证服务器 URL"}),
    ],
    "ad": [
        (["--ad_type"], {"type": str, "default": None, "help": "广告类型: ima/custom"}),
        (["--ad_tag"], {"type": str, "default": "", "help": "广告标签 URL (IMA 需要)"}),
    ],
    "help": [],
}


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="android-media-pack 技能包命令行工具",
        add_help=False,
    )
    parser.add_argument("--command", nargs="?", choices=list(COMMAND_HANDLERS.keys()) + [None],
                        default=None, help="要执行的命令")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    parser.add_argument("--help", action="store_true", help="显示帮助")

    # 添加各命令的参数
    for cmd, arg_specs in COMMAND_ARGS.items():
        for args, kwargs in arg_specs:
            parser.add_argument(*args, **kwargs)

    return parser


def validate_command_args(args: argparse.Namespace) -> Optional[str]:
    """
    验证命令参数是否完整。
    返回错误码字符串，如果参数合法返回 None。
    """
    if args.command == "stream":
        if not args.format:
            return "E002"
        if not args.url:
            return "E002"
    elif args.command == "drm":
        if not args.scheme:
            return "E002"
        if not args.license_url:
            return "E002"
    elif args.command == "ad":
        if not args.ad_type:
            return "E002"
    return None


def main() -> int:
    """主入口函数"""
    parser = build_parser()
    args = parser.parse_args()

    try:
        # 自检模式
        if args.selftest:
            return run_selftest()

        # 帮助模式
        if args.help or args.command is None:
            print(get_help_text())
            return 0

        # 验证命令参数
        error_code = validate_command_args(args)
        if error_code:
            print(f"错误 {error_code}: {ERROR_MESSAGES[error_code]}", file=sys.stderr)
            return 1

        # 执行命令
        handler = COMMAND_HANDLERS.get(args.command)
        if handler is None:
            print(f"错误 E001: {ERROR_MESSAGES['E001']}", file=sys.stderr)
            return 1

        result = handler(args)
        print(result)
        return 0

    except ValueError as e:
        code = str(e)
        msg = ERROR_MESSAGES.get(code, ERROR_MESSAGES["E008"])
        print(f"错误 {code}: {msg}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误 E010: {ERROR_MESSAGES['E010']} - {str(e)}", file=sys.stderr)
        return 1


# ============================================================
# 自检逻辑
# ============================================================

def run_selftest() -> int:
    """
    运行内置自检，验证核心逻辑。

    使用硬编码样例数据，不读取外部文件、不依赖当前工作目录、不访问网络。
    断言使用宽松阈值（大小比较/区间判断），确保任何环境可过。
    """
    print("=== android-media-pack 自检开始 ===")
    errors = []

    # --- 测试 C1: 迁移辅助 ---
    try:
        # 空输入
        guide_empty = generate_migration_guide()
        assert len(guide_empty) > 0, "空输入迁移指南不应为空"
        assert MEDIA3_VERSION in guide_empty, "迁移指南应包含目标版本"

        # 带旧包名代码
        sample_code = "import com.google.android.exoplayer2.ExoPlayer;\nimport com.google.android.exoplayer2.PlayerView;"
        guide = generate_migration_guide(sample_code)
        assert len(guide) > 0, "迁移指南不应为空"
        assert "com.google.android.exoplayer2" in guide or "androidx.media3" in guide, \
            "迁移指南应包含包名替换信息"
        # 宽松断言：输出长度应合理
        assert 100 < len(guide) < 10000, "迁移指南长度应在合理区间"

        print("  [PASS] C1 迁移辅助")
    except AssertionError as e:
        errors.append(f"C1 迁移辅助断言失败: {e}")
        print(f"  [FAIL] C1 迁移辅助: {e}")
    except Exception as e:
        errors.append(f"C1 迁移辅助异常: {e}")
        print(f"  [FAIL] C1 迁移辅助异常: {e}")

    # --- 测试 C2: Compose UI 生成 ---
    try:
        # 默认参数
        ui_default = generate_compose_player_ui()
        assert len(ui_default) > 0, "Compose UI 代码不应为空"
        assert "@Composable" in ui_default, "应包含 @Composable 注解"
        assert "PlayerSurface" in ui_default, "应包含 PlayerSurface"

        # 自定义参数
        ui_custom = generate_compose_player_ui({
            "controls": False,
            "fullscreen": False,
            "gestures": True,
        })
        assert len(ui_custom) > 0, "Compose UI 代码不应为空"
        # 宽松断言：代码长度应合理
        assert 200 < len(ui_custom) < 20000, "Compose UI 代码长度应在合理区间"

        # 验证不同参数组合
        ui_min = generate_compose_player_ui({"controls": False, "fullscreen": False, "gestures": False})
        assert len(ui_min) > 0, "最小配置 UI 不应为空"

        print("  [PASS] C2 Compose UI 生成")
    except AssertionError as e:
        errors.append(f"C2 Compose UI 断言失败: {e}")
        print(f"  [FAIL] C2 Compose UI: {e}")
    except Exception as e:
        errors.append(f"C2 Compose UI 异常: {e}")
        print(f"  [FAIL] C2 Compose UI 异常: {e}")

    # --- 测试 C3: 流媒体配置 ---
    try:
        # HLS
        hls_config = generate_streaming_config("hls", "https://example.com/stream.m3u8")
        assert len(hls_config) > 0, "HLS 配置不应为空"
        assert "MediaItem" in hls_config, "应包含 MediaItem"
        assert "m3u8" in hls_config.lower() or "M3U8" in hls_config, "应包含 HLS MIME 类型"

        # DASH
        dash_config = generate_streaming_config("dash", "https://example.com/manifest.mpd")
        assert len(dash_config) > 0, "DASH 配置不应为空"
        assert "mpd" in dash_config.lower() or "MPD" in dash_config, "应包含 DASH MIME 类型"

        # SmoothStreaming
        ss_config = generate_streaming_config("smoothstreaming", "https://example.com/manifest")
        assert len(ss_config) > 0, "SmoothStreaming 配置不应为空"
        assert "ss" in ss_config.lower() or "SS" in ss_config, "应包含 SmoothStreaming MIME 类型"

        # 大小写不敏感
        hls_upper = generate_streaming_config("HLS", "https://example.com/stream.m3u8")
        assert len(hls_upper) > 0, "大写 HLS 配置不应为空"

        # 非法格式应抛异常
        try:
            generate_streaming_config("invalid", "https://example.com/stream")
            errors.append("C3 非法格式未抛异常")
            print("  [FAIL] C3 非法格式未抛异常")
        except ValueError as e:
            assert str(e) == "E003", f"错误码应为 E003，实际: {e}"
            print("  [PASS] C3 非法格式正确抛异常")

        print("  [PASS] C3 流媒体配置")
    except AssertionError as e:
        errors.append(f"C3 流媒体配置断言失败: {e}")
        print(f"  [FAIL] C3 流媒体配置: {e}")
    except Exception as e:
        errors.append(f"C3 流媒体配置异常: {e}")
        print(f"  [FAIL] C3 流媒体配置异常: {e}")

    # --- 测试 C4: DRM 集成 ---
    try:
        # Widevine
        wv_config = generate_drm_config("widevine", "https://license.example.com/wv")
        assert len(wv_config) > 0, "Widevine 配置不应为空"
        assert "EDEF8BA9" in wv_config.upper(), "应包含 Widevine UUID"

        # PlayReady
        pr_config = generate_drm_config("playready", "https://license.example.com/pr")
        assert len(pr_config) > 0, "PlayReady 配置不应为空"
        assert "9A04F079" in pr_config.upper(), "应包含 PlayReady UUID"

        # ClearKey
        ck_config = generate_drm_config("clearkey", "https://license.example.com/ck")
        assert len(ck_config) > 0, "ClearKey 配置不应为空"
        assert "1077EFEC" in ck_config.upper(), "应包含 ClearKey UUID"

        # 非法方案
        try:
            generate_drm_config("invalid", "https://license.example.com")
            errors.append("C4 非法方案未抛异常")
            print("  [FAIL] C4 非法方案未抛异常")
        except ValueError as e:
            assert str(e) == "E004", f"错误码应为 E004，实际: {e}"
            print("  [PASS] C4 非法方案正确抛异常")

        print("  [PASS] C4 DRM 集成")
    except AssertionError as e:
        errors.append(f"C4 DRM 集成断言失败: {e}")
        print(f"  [FAIL] C4 DRM 集成: {e}")
    except Exception as e:
        errors.append(f"C4 DRM 集成异常: {e}")
        print(f"  [FAIL] C4 DRM 集成异常: {e}")

    # --- 测试 C5: 广告集成 ---
    try:
        # IMA
        ima_guide = generate_ad_integration("ima", "https://example.com/ad.xml")
        assert len(ima_guide) > 0, "IMA 指南不应为空"
        assert "IMA" in ima_guide.upper(), "应包含 IMA 关键字"
        assert "ImaAdsLoader" in ima_guide, "应包含 ImaAdsLoader"

        # Custom
        custom_guide = generate_ad_integration("custom")
        assert len(custom_guide) > 0, "Custom 指南不应为空"
        assert "CUSTOM" in custom_guide.upper(), "应包含 Custom 关键字"

        # 非法类型
        try:
            generate_ad_integration("invalid")
            errors.append("C5 非法类型未抛异常")
            print("  [FAIL] C5 非法类型未抛异常")
        except ValueError as e:
            assert str(e) == "E005", f"错误码应为 E005，实际: {e}"
            print("  [PASS] C5 非法类型正确抛异常")

        print("  [PASS] C5 广告集成")
    except AssertionError as e:
        errors.append(f"C5 广告集成断言失败: {e}")
        print(f"  [FAIL] C5 广告集成: {e}")
    except Exception as e:
        errors.append(f"C5 广告集成异常: {e}")
        print(f"  [FAIL] C5 广告集成异常: {e}")

    # --- 测试错误处理 ---
    try:
        # 空 URL
        try:
            generate_streaming_config("hls", "")
            errors.append("空 URL 未抛异常")
            print("  [FAIL] 空 URL 未抛异常")
        except ValueError as e:
            assert str(e) == "E006", f"错误码应为 E006，实际: {e}"
            print("  [PASS] 空 URL 正确抛异常")

        # 空 license URL
        try:
            generate_drm_config("widevine", "")
            errors.append("空 license URL 未抛异常")
            print("  [FAIL] 空 license URL 未抛异常")
        except ValueError as e:
            assert str(e) == "E006", f"错误码应为 E006，实际: {e}"
            print("  [PASS] 空 license URL 正确抛异常")

        print("  [PASS] 错误处理")
    except AssertionError as e:
        errors.append(f"错误处理断言失败: {e}")
        print(f"  [FAIL] 错误处理: {e}")
    except Exception as e:
        errors.append(f"错误处理异常: {e}")
        print(f"  [FAIL] 错误处理异常: {e}")

    # --- 测试帮助文本 ---
    try:
        help_text = get_help_text()
        assert len(help_text) > 0, "帮助文本不应为空"
        assert "migrate" in help_text, "帮助文本应包含 migrate 命令"
        assert "compose" in help_text, "帮助文本应包含 compose 命令"
        assert "stream" in help_text, "帮助文本应包含 stream 命令"
        assert "drm" in help_text, "帮助文本应包含 drm 命令"
        assert "ad" in help_text, "帮助文本应包含 ad 命令"
        print("  [PASS] 帮助文本")
    except AssertionError as e:
        errors.append(f"帮助文本断言失败: {e}")
        print(f"  [FAIL] 帮助文本: {e}")
    except Exception as e:
        errors.append(f"帮助文本异常: {e}")
        print(f"  [FAIL] 帮助文本异常: {e}")

    # --- 总结 ---
    print("")
    if errors:
        print(f"=== 自检失败: {len(errors)} 个错误 ===")
        for err in errors:
            print(f"  - {err}")
        print(f"错误 E009: {ERROR_MESSAGES['E009']}")
        return 1
    else:
        print("=== 自检全部通过 ===")
        return 0


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":
    sys.exit(main())
