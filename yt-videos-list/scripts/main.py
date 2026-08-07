#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-videos-list 独立实现脚本
基于功能规格 clean-room 重写，不依赖任何既有代码。
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# 错误码定义
ERROR_CODES = {
    "E001": "参数错误：缺少必要参数",
    "E002": "参数错误：无效的URL格式",
    "E003": "参数错误：无效的频道ID格式",
    "E004": "文件错误：无法创建输出文件",
    "E005": "文件错误：无法写入输出文件",
    "E006": "数据错误：无法解析视频数据",
    "E007": "数据错误：无法获取频道信息",
    "E008": "数据错误：视频列表为空",
    "E009": "运行错误：网络请求失败",
    "E010": "运行错误：未知异常",
}


@dataclass
class VideoInfo:
    """视频信息数据结构"""
    video_id: str
    title: str
    published_at: str
    duration: str
    view_count: int
    description: str
    channel_id: str = ""
    channel_title: str = ""


@dataclass
class ChannelInfo:
    """频道信息数据结构"""
    channel_id: str
    channel_title: str
    video_count: int = 0
    videos: List[VideoInfo] = field(default_factory=list)


class YouTubeChannelParser:
    """YouTube频道视频列表解析器（仅实现数据解析逻辑，不发起网络请求）"""

    def __init__(self):
        # 更灵活的视频ID匹配模式，支持多种格式
        self._video_pattern = re.compile(
            r'videoId["\']?\s*[:=]\s*["\']([A-Za-z0-9_-]{11})["\']'
        )
        # 备用模式：匹配JSON中的videoId
        self._video_json_pattern = re.compile(
            r'["\']videoId["\']\s*:\s*["\']([A-Za-z0-9_-]{11})["\']'
        )
        # 通用匹配：任何位置的11字符YouTube视频ID
        self._video_generic_pattern = re.compile(
            r'\b([A-Za-z0-9_-]{11})\b'
        )
        self._title_pattern = re.compile(
            r'title["\']?\s*[:=]\s*["\']([^"\']+)["\']'
        )
        self._duration_pattern = re.compile(
            r'lengthSeconds["\']?\s*[:=]\s*["\']?(\d+)["\']?'
        )

    def parse_channel_page(self, html_content: str) -> List[VideoInfo]:
        """
        从频道页面HTML中解析视频列表
        注意：此方法仅处理静态HTML内容，不发起网络请求
        """
        videos = []
        try:
            # 首先尝试标准模式
            video_ids = self._video_pattern.findall(html_content)
            
            # 如果标准模式没有找到，尝试JSON模式
            if not video_ids:
                video_ids = self._video_json_pattern.findall(html_content)
            
            # 如果还是没有找到，尝试更宽松的匹配
            if not video_ids:
                # 查找所有可能的视频ID（11字符的字母数字组合）
                all_matches = self._video_generic_pattern.findall(html_content)
                # 过滤掉明显的非视频ID（如单词片段）
                video_ids = [vid for vid in all_matches 
                           if not vid.isdigit() and 
                           any(c.isalpha() for c in vid) and
                           len(vid) == 11]
            
            if not video_ids:
                return []

            # 去重并保持顺序
            seen = set()
            unique_ids = []
            for vid in video_ids:
                if vid not in seen:
                    seen.add(vid)
                    unique_ids.append(vid)

            # 为每个视频ID创建基本信息
            for vid in unique_ids:
                video = VideoInfo(
                    video_id=vid,
                    title=f"视频 {vid}",  # 默认标题，后续可通过API获取
                    published_at="",
                    duration="",
                    view_count=0,
                    description="",
                )
                videos.append(video)

            # 尝试提取标题信息
            titles = self._title_pattern.findall(html_content)
            for i, video in enumerate(videos):
                if i < len(titles):
                    video.title = titles[i]

            # 尝试提取时长信息
            durations = self._duration_pattern.findall(html_content)
            for i, video in enumerate(videos):
                if i < len(durations):
                    video.duration = durations[i]

        except Exception as e:
            raise ValueError(f"E006: 无法解析视频数据: {str(e)}")

        return videos

    def format_duration(self, seconds: str) -> str:
        """将秒数格式化为 HH:MM:SS 格式"""
        try:
            total_seconds = int(seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes:02d}:{secs:02d}"
        except (ValueError, TypeError):
            return "00:00"


class VideoListGenerator:
    """视频清单生成器"""

    def __init__(self):
        self.parser = YouTubeChannelParser()

    def extract_channel_id(self, url_or_id: str) -> Tuple[Optional[str], Optional[str]]:
        """
        从URL或ID中提取频道ID
        返回 (channel_id, error_message)
        """
        if not url_or_id:
            return None, "E001: 缺少频道URL或ID"

        # 如果看起来像纯ID
        if re.match(r'^[A-Za-z0-9_-]{24}$', url_or_id):
            return url_or_id, None

        # 尝试解析URL
        try:
            parsed = urlparse(url_or_id)
            if not parsed.scheme or not parsed.netloc:
                return None, "E002: 无效的URL格式"

            # 处理不同形式的YouTube URL
            path_parts = parsed.path.strip('/').split('/')
            
            # 处理 youtube.com/channel/UCxxx 格式
            if 'channel' in path_parts:
                idx = path_parts.index('channel')
                if idx + 1 < len(path_parts):
                    channel_id = path_parts[idx + 1]
                    if re.match(r'^[A-Za-z0-9_-]{24}$', channel_id):
                        return channel_id, None
                    return None, "E003: 无效的频道ID格式"

            # 处理 youtube.com/c/xxx 或 youtube.com/user/xxx 格式
            if any(prefix in path_parts for prefix in ['c', 'user', 'custom']):
                # 这些格式需要额外处理，这里返回None表示需要进一步解析
                return None, "E002: 无法从该URL格式提取频道ID"

            # 处理 youtube.com/@handle 格式
            if path_parts and path_parts[0].startswith('@'):
                # handle格式，需要API解析
                return None, "E002: 需要API解析handle格式"

        except Exception:
            return None, "E002: 无效的URL格式"

        return None, "E002: 无法从URL中提取频道ID"

    def generate_list(self, channel_info: ChannelInfo, format_type: str) -> Tuple[Optional[str], Optional[str]]:
        """
        生成视频清单文本
        返回 (content, error_message)
        """
        if not channel_info.videos:
            return None, "E008: 视频列表为空"

        try:
            if format_type == 'txt':
                return self._format_txt(channel_info), None
            elif format_type == 'csv':
                return self._format_csv(channel_info), None
            elif format_type == 'md':
                return self._format_md(channel_info), None
            else:
                return None, f"E001: 不支持的格式: {format_type}"
        except Exception as e:
            return None, f"E010: 生成清单失败: {str(e)}"

    def _format_txt(self, channel_info: ChannelInfo) -> str:
        """生成TXT格式清单"""
        lines = []
        lines.append(f"频道: {channel_info.channel_title}")
        lines.append(f"频道ID: {channel_info.channel_id}")
        lines.append(f"视频数量: {len(channel_info.videos)}")
        lines.append("=" * 50)
        
        for i, video in enumerate(channel_info.videos, 1):
            lines.append(f"{i}. {video.title}")
            lines.append(f"   ID: {video.video_id}")
            if video.published_at:
                lines.append(f"   发布时间: {video.published_at}")
            if video.duration:
                lines.append(f"   时长: {video.duration}")
            if video.view_count > 0:
                lines.append(f"   观看次数: {video.view_count:,}")
            if video.description:
                desc = video.description[:100] + "..." if len(video.description) > 100 else video.description
                lines.append(f"   简介: {desc}")
            lines.append("-" * 30)
        
        return "\n".join(lines)

    def _format_csv(self, channel_info: ChannelInfo) -> str:
        """生成CSV格式清单"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['序号', '视频ID', '标题', '发布时间', '时长', '观看次数', '简介'])
        
        # 写入数据
        for i, video in enumerate(channel_info.videos, 1):
            writer.writerow([
                i,
                video.video_id,
                video.title,
                video.published_at,
                video.duration,
                video.view_count,
                video.description[:200]  # 限制简介长度
            ])
        
        return output.getvalue()

    def _format_md(self, channel_info: ChannelInfo) -> str:
        """生成Markdown格式清单"""
        lines = []
        lines.append(f"# {channel_info.channel_title}")
        lines.append("")
        lines.append(f"- **频道ID**: `{channel_info.channel_id}`")
        lines.append(f"- **视频数量**: {len(channel_info.videos)}")
        lines.append("")
        lines.append("| 序号 | 视频ID | 标题 | 发布时间 | 时长 | 观看次数 |")
        lines.append("|------|--------|------|----------|------|----------|")
        
        for i, video in enumerate(channel_info.videos, 1):
            # 格式化观看次数
            views = f"{video.view_count:,}" if video.view_count > 0 else "-"
            lines.append(f"| {i} | `{video.video_id}` | {video.title} | {video.published_at or '-'} | {video.duration or '-'} | {views} |")
        
        return "\n".join(lines)

    def save_to_file(self, content: str, filepath: str) -> Optional[str]:
        """保存内容到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return None
        except IOError as e:
            return f"E004: 无法写入文件 {filepath}: {str(e)}"


class SelfTest:
    """内置自检模块"""

    @staticmethod
    def run_all() -> bool:
        """运行所有自检"""
        print("开始自检...")
        tests = [
            SelfTest.test_channel_id_extraction,
            SelfTest.test_html_parsing,
            SelfTest.test_format_generation,
            SelfTest.test_error_handling,
        ]
        
        all_passed = True
        for test in tests:
            try:
                test()
                print(f"  ✓ {test.__name__}")
            except AssertionError as e:
                print(f"  ✗ {test.__name__}: {str(e)}")
                all_passed = False
            except Exception as e:
                print(f"  ✗ {test.__name__}: 未预期异常: {str(e)}")
                all_passed = False
        
        print(f"自检{'通过' if all_passed else '失败'}")
        return all_passed

    @staticmethod
    def test_channel_id_extraction():
        """测试频道ID提取"""
        generator = VideoListGenerator()
        
        # 测试频道URL
        channel_id, err = generator.extract_channel_id("https://www.youtube.com/channel/UC1234567890123456789012")
        assert err is None, f"应成功提取频道ID，但失败: {err}"
        assert channel_id == "UC1234567890123456789012", f"频道ID不匹配: {channel_id}"
        
        # 测试纯ID
        channel_id, err = generator.extract_channel_id("UC1234567890123456789012")
        assert err is None, f"应成功提取纯ID，但失败: {err}"
        assert channel_id == "UC1234567890123456789012", f"纯ID不匹配: {channel_id}"
        
        # 测试无效URL
        _, err = generator.extract_channel_id("not_a_valid_url")
        assert err is not None, "无效URL应返回错误"
        
        # 测试空输入
        _, err = generator.extract_channel_id("")
        assert err is not None, "空输入应返回错误"

    @staticmethod
    def test_html_parsing():
        """测试HTML解析"""
        parser = YouTubeChannelParser()
        
        # 测试包含视频ID的HTML - 多种格式
        test_html = """
        <script>
        var ytInitialData = {
            "contents": {
                "videoRenderer": [
                    {"videoId": "ABC123XYZ789", "title": {"runs": [{"text": "测试视频1"}]}},
                    {"videoId": "DEF456UVW123", "title": {"runs": [{"text": "测试视频2"}]}}
                ]
            }
        };
        </script>
        """
        videos = parser.parse_channel_page(test_html)
        assert len(videos) >= 2, f"应至少解析出2个视频，实际: {len(videos)}"
        assert any(v.video_id == "ABC123XYZ789" for v in videos), "应包含特定视频ID"
        assert any(v.video_id == "DEF456UVW123" for v in videos), "应包含另一个特定视频ID"
        
        # 测试更简单的格式
        test_html_simple = """
        <div class="video">
            <span>videoId: "XYZ789ABC123"</span>
            <span>videoId: "UVW123DEF456"</span>
        </div>
        """
        videos = parser.parse_channel_page(test_html_simple)
        assert len(videos) >= 2, f"简单格式应至少解析出2个视频，实际: {len(videos)}"
        
        # 测试空HTML
        videos = parser.parse_channel_page("")
        assert len(videos) == 0, "空HTML应返回空列表"
        
        # 测试时长格式化
        formatted = parser.format_duration("3661")
        assert formatted == "01:01:01", f"时长格式化不正确: {formatted}"
        
        # 测试无效时长
        formatted = parser.format_duration("invalid")
        assert formatted == "00:00", f"无效时长应返回00:00: {formatted}"

    @staticmethod
    def test_format_generation():
        """测试清单生成"""
        generator = VideoListGenerator()
        
        # 创建测试数据
        video1 = VideoInfo(
            video_id="ABC123XYZ789",
            title="测试视频1",
            published_at="2024-01-01",
            duration="10:30",
            view_count=100,
            description="这是一个测试视频"
        )
        video2 = VideoInfo(
            video_id="DEF456UVW123",
            title="测试视频2",
            published_at="2024-02-01",
            duration="05:15",
            view_count=50,
            description="另一个测试视频"
        )
        
        channel = ChannelInfo(
            channel_id="UC1234567890123456789012",
            channel_title="测试频道",
            videos=[video1, video2]
        )
        
        # 测试TXT格式
        content, err = generator.generate_list(channel, 'txt')
        assert err is None, f"TXT生成失败: {err}"
        assert "测试频道" in content, "TXT应包含频道名"
        assert "测试视频1" in content, "TXT应包含视频标题"
        assert "ABC123XYZ789" in content, "TXT应包含视频ID"
        
        # 测试CSV格式
        content, err = generator.generate_list(channel, 'csv')
        assert err is None, f"CSV生成失败: {err}"
        assert "视频ID" in content, "CSV应包含表头"
        assert "ABC123XYZ789" in content, "CSV应包含视频ID"
        
        # 测试MD格式
        content, err = generator.generate_list(channel, 'md')
        assert err is None, f"MD生成失败: {err}"
        assert "| 序号 |" in content, "MD应包含表格头部"
        assert "测试视频1" in content, "MD应包含视频标题"
        assert "ABC123XYZ789" in content, "MD应包含视频ID"
        
        # 测试不支持的格式
        _, err = generator.generate_list(channel, 'xml')
        assert err is not None, "不支持的格式应返回错误"

    @staticmethod
    def test_error_handling():
        """测试错误处理"""
        generator = VideoListGenerator()
        
        # 测试空视频列表
        channel = ChannelInfo(
            channel_id="UC1234567890123456789012",
            channel_title="空频道",
            videos=[]
        )
        _, err = generator.generate_list(channel, 'txt')
        assert err is not None, "空列表应返回错误"
        assert "E008" in err, "应返回E008错误码"
        
        # 测试文件写入
        # 尝试写入不存在的目录
        err = generator.save_to_file("test", "/nonexistent/path/test.txt")
        assert err is not None, "写入不存在目录应失败"


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="YouTube频道视频清单生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --url https://www.youtube.com/channel/UCxxx --format txt
  python main.py --channel-id UCxxx --format csv --output list.csv
  python main.py --selftest
        """
    )
    
    parser.add_argument("--url", help="YouTube频道URL")
    parser.add_argument("--channel-id", help="YouTube频道ID")
    parser.add_argument("--format", choices=['txt', 'csv', 'md'], default='txt', help="输出格式")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--selftest", action="store_true", help="运行自检")
    
    args = parser.parse_args()
    
    # 运行自检
    if args.selftest:
        success = SelfTest.run_all()
        sys.exit(0 if success else 1)
    
    # 检查必要参数
    if not args.url and not args.channel_id:
        print("错误: E001 - 需要提供 --url 或 --channel-id 参数", file=sys.stderr)
        print("提示: 使用 --selftest 运行自检", file=sys.stderr)
        sys.exit(1)
    
    # 提取频道ID
    generator = VideoListGenerator()
    source = args.url or args.channel_id
    channel_id, err = generator.extract_channel_id(source)
    
    if err:
        print(f"错误: {err}", file=sys.stderr)
        sys.exit(1)
    
    # 注意：实际网络请求需要网络库，这里仅演示本地处理
    # 在实际使用中，需要实现网络请求获取频道数据
    print(f"频道ID: {channel_id}")
    print("提示: 当前为演示模式，实际网络请求需要额外实现")
    print("建议: 使用 --selftest 验证核心逻辑")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
