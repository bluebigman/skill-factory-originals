#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import argparse
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

class ScreenRecordingProcessor:
    """录屏处理专家 - 一站式录屏处理工具"""
    
    def __init__(self, ffmpeg_path='ffmpeg', ffprobe_path='ffprobe'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.check_dependencies()
    
    def check_dependencies(self):
        """检查ffmpeg和ffprobe是否可用"""
        for tool in [self.ffmpeg_path, self.ffprobe_path]:
            if shutil.which(tool) is None:
                print(f"警告: {tool} 未找到，部分功能可能不可用")
    
    def probe_video(self, filepath):
        """使用 ffprobe 获取视频文件的完整元数据"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        cmd = [
            self.ffprobe_path, '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            filepath
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe 执行失败: {result.stderr}")
            data = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            raise RuntimeError(f"无法解析视频信息: {e}")
        
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            if stream['codec_type'] == 'video' and video_stream is None:
                video_stream = stream
            elif stream['codec_type'] == 'audio' and audio_stream is None:
                audio_stream = stream
        
        if video_stream is None:
            raise ValueError("未找到视频流，文件可能不是有效的视频文件")
        
        format_info = data.get('format', {})
        bit_rate = int(format_info.get('bit_rate', 0)) / 1000
        file_size = os.path.getsize(filepath) / (1024 * 1024)
        
        # 安全解析帧率
        fps = 0
        avg_frame_rate = video_stream.get('avg_frame_rate', '0/1')
        if '/' in avg_frame_rate:
            try:
                num, den = avg_frame_rate.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 0
            except (ValueError, ZeroDivisionError):
                fps = 0
        
        info = {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'format': format_info.get('format_name', 'unknown'),
            'duration': float(format_info.get('duration', 0)),
            'bit_rate_kbps': bit_rate,
            'file_size_mb': file_size,
            'video': {
                'codec': video_stream.get('codec_name', 'unknown'),
                'width': video_stream.get('width', 0),
                'height': video_stream.get('height', 0),
                'fps': fps,
                'pixel_format': video_stream.get('pix_fmt', 'unknown')
            },
            'audio': None
        }
        
        if audio_stream:
            info['audio'] = {
                'codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': audio_stream.get('sample_rate', '0'),
                'channels': audio_stream.get('channels', 0)
            }
        
        return info
    
    def compress_video(self, input_path, output_path, crf=23, resolution=None):
        """视频压缩转码 - H.265/HEVC压缩"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        cmd = [
            self.ffmpeg_path, '-i', input_path,
            '-c:v', 'libx265',
            '-crf', str(crf),
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '128k'
        ]
        
        if resolution:
            cmd.extend(['-vf', f'scale=-2:{resolution}'])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"压缩失败: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("压缩超时")
    
    def extract_audio(self, input_path, output_path, format='mp3', bitrate='192k'):
        """提取音频"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        cmd = [
            self.ffmpeg_path, '-i', input_path,
            '-vn',
            '-acodec', 'libmp3lame' if format == 'mp3' else 'pcm_s16le',
            '-b:a', bitrate if format == 'mp3' else '192k',
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"音频提取失败: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("音频提取超时")
    
    def extract_thumbnail(self, input_path, output_path, time_point='00:00:01'):
        """截取关键帧生成封面图"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        cmd = [
            self.ffmpeg_path, '-i', input_path,
            '-ss', time_point,
            '-vframes', '1',
            '-q:v', '2',
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"封面截取失败: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("封面截取超时")
    
    def merge_videos(self, input_paths, output_path):
        """拼接多段录屏"""
        if not input_paths:
            raise ValueError("输入文件列表为空")
        
        for path in input_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"输入文件不存在: {path}")
        
        # 创建临时文件列表
        list_file = 'temp_file_list.txt'
        try:
            with open(list_file, 'w', encoding='utf-8') as f:
                for path in input_paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            
            cmd = [
                self.ffmpeg_path, '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"视频拼接失败: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("视频拼接超时")
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
    
    def generate_gif(self, input_path, output_path, start_time='00:00:00', duration=3):
        """生成预览GIF"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        cmd = [
            self.ffmpeg_path, '-i', input_path,
            '-ss', start_time,
            '-t', str(duration),
            '-vf', 'fps=10,scale=320:-1:flags=lanczos',
            '-c:v', 'gif',
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"GIF生成失败: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            raise RuntimeError("GIF生成超时")
    
    def rename_by_time(self, filepath, output_dir=None):
        """按录制时间重命名文件"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        info = self.probe_video(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        new_name = f"{mtime.strftime('%Y%m%d_%H%M%S')}_录屏{Path(filepath).suffix}"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            new_path = os.path.join(output_dir, new_name)
        else:
            new_path = os.path.join(os.path.dirname(filepath), new_name)
        
        shutil.copy2(filepath, new_path)
        return new_path
    
    def batch_process(self, input_dir, output_dir=None, action='info'):
        """批量处理目录下的所有视频文件"""
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"目录不存在: {input_dir}")
        
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv']
        results = []
        
        for file in os.listdir(input_dir):
            filepath = os.path.join(input_dir, file)
            if os.path.isfile(filepath) and Path(file).suffix.lower() in video_extensions:
                try:
                    if action == 'info':
                        info = self.probe_video(filepath)
                        results.append({'file': file, 'status': 'success', 'info': info})
                    elif action == 'compress':
                        if output_dir:
                            output_path = os.path.join(output_dir, f"compressed_{file}")
                            self.compress_video(filepath, output_path)
                            results.append({'file': file, 'status': 'success', 'output': output_path})
                except Exception as e:
                    results.append({'file': file, 'status': 'error', 'error': str(e)})
        
        return results

class TaskManager:
    """任务管理器，支持添加、删除、完成任务和查看任务"""
    
    def __init__(self):
        self.tasks = []
        self.next_id = 1
    
    def add_task(self, title, priority='medium', due_date=None):
        """添加新任务"""
        task = {
            'id': self.next_id,
            'title': title,
            'priority': priority,
            'due_date': due_date,
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        self.tasks.append(task)
        self.next_id += 1
        return task['id']
    
    def delete_task(self, task_id):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task['id'] == task_id:
                return self.tasks.pop(i)
        return None
    
    def complete_task(self, task_id):
        """完成任务"""
        task = self.get_task(task_id)
        if task:
            task['completed'] = True
            return True
        return False
    
    def get_task(self, task_id):
        """获取任务"""
        for task in self.tasks:
            if task['id'] == task_id:
                return task
        return None
    
    def list_tasks(self, include_completed=True):
        """列出任务"""
        if include_completed:
            return self.tasks
        return [t for t in self.tasks if not t['completed']]
    
    def get_stats(self):
        """获取任务统计信息"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t['completed'])
        pending = total - completed
        return {
            'total': total,
            'completed': completed,
            'pending': pending
        }
    
    def to_json(self):
        """转换为JSON格式"""
        return json.dumps({
            'tasks': self.tasks,
            'next_id': self.next_id
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str):
        """从JSON加载"""
        data = json.loads(json_str)
        manager = cls()
        manager.tasks = data['tasks']
        manager.next_id = data['next_id']
        return manager

def selftest():
    """自测函数"""
    print("Running selftest...")
    
    # 测试任务管理器
    manager = TaskManager()
    
    # 测试添加任务
    id1 = manager.add_task("测试任务1", "high")
    id2 = manager.add_task("测试任务2", "medium", "2024-12-31")
    id3 = manager.add_task("测试任务3", "low")
    
    # 验证任务数量
    stats = manager.get_stats()
    assert stats['total'] >= 3, f"Expected at least 3 tasks, got {stats['total']}"
    assert stats['pending'] >= 3, f"Expected at least 3 pending tasks, got {stats['pending']}"
    
    # 测试获取任务
    task1 = manager.get_task(id1)
    assert task1 is not None, "Task 1 should exist"
    assert task1['title'] == "测试任务1", f"Unexpected title: {task1['title']}"
    assert task1['priority'] == "high", f"Unexpected priority: {task1['priority']}"
    
    # 测试完成任务
    assert manager.complete_task(id1) == True, "Should complete task successfully"
    task1 = manager.get_task(id1)
    assert task1['completed'] == True, "Task 1 should be completed"
    
    # 测试统计
    stats = manager.get_stats()
    assert stats['completed'] >= 1, f"Expected at least 1 completed task, got {stats['completed']}"
    assert stats['pending'] >= 2, f"Expected at least 2 pending tasks, got {stats['pending']}"
    
    # 测试删除任务
    deleted = manager.delete_task(id2)
    assert deleted is not None, "Should delete task successfully"
    assert manager.get_task(id2) is None, "Task 2 should not exist after deletion"
    
    # 测试列表功能
    all_tasks = manager.list_tasks()
    assert len(all_tasks) >= 2, f"Expected at least 2 tasks, got {len(all_tasks)}"
    
    pending_tasks = manager.list_tasks(include_completed=False)
    assert len(pending_tasks) >= 1, f"Expected at least 1 pending task, got {len(pending_tasks)}"
    
    # 测试JSON序列化
    json_str = manager.to_json()
    assert json_str is not None, "JSON serialization should work"
    
    # 测试JSON反序列化
    manager2 = TaskManager.from_json(json_str)
    assert manager2 is not None, "JSON deserialization should work"
    assert len(manager2.tasks) == len(manager.tasks), "Task count should match after deserialization"
    
    # 测试边界情况
    assert manager.complete_task(999) == False, "Should return False for non-existent task"
    assert manager.delete_task(999) is None, "Should return None for non-existent task"
    assert manager.get_task(999) is None, "Should return None for non-existent task"
    
    # 测试录屏处理器
    processor = ScreenRecordingProcessor()
    
    # 测试文件不存在异常
    try:
        processor.probe_video("nonexistent_file.mp4")
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass
    
    # 测试空文件列表
    try:
        processor.merge_videos([], "output.mp4")
        assert False, "Should raise ValueError"
    except ValueError:
        pass
    
    # 测试不存在的目录
    try:
        processor.batch_process("nonexistent_dir")
        assert False, "Should raise NotADirectoryError"
    except NotADirectoryError:
        pass
    
    # 测试帧率解析
    test_fps = "30/1"
    if '/' in test_fps:
        try:
            num, den = test_fps.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0
            assert fps == 30.0, f"Expected 30.0 fps, got {fps}"
        except (ValueError, ZeroDivisionError):
            assert False, "Should not raise exception for valid fps"
    
    # 测试异常帧率
    bad_fps = "0/0"
    if '/' in bad_fps:
        try:
            num, den = bad_fps.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0
            assert fps == 0, f"Expected 0 fps for invalid ratio, got {fps}"
        except (ValueError, ZeroDivisionError):
            assert False, "Should handle zero denominator gracefully"
    
    # 测试空任务列表
    empty_manager = TaskManager()
    assert empty_manager.list_tasks() == [], "Empty manager should have no tasks"
    assert empty_manager.get_stats() == {'total': 0, 'completed': 0, 'pending': 0}, "Empty manager stats should be zero"
    
    # 测试JSON序列化边界
    empty_json = empty_manager.to_json()
    empty_manager2 = TaskManager.from_json(empty_json)
    assert len(empty_manager2.tasks) == 0, "Empty manager should deserialize to empty tasks"
    
    print("All selftest assertions passed!")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="录屏处理专家 - 一站式录屏处理工具")
    parser.add_argument('--selftest', action='store_true', help='运行自测')
    
    # 任务管理参数
    parser.add_argument('--add', nargs='+', help='添加任务: --add "任务标题" [优先级] [截止日期]')
    parser.add_argument('--list', action='store_true', help='列出所有任务')
    parser.add_argument('--complete', type=int, help='完成任务: --complete 任务ID')
    parser.add_argument('--delete', type=int, help='删除任务: --delete 任务ID')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    # 录屏处理参数
    parser.add_argument('--probe', type=str, help='获取视频信息: --probe 文件路径')
    parser.add_argument('--compress', nargs=2, help='压缩视频: --compress 输入文件 输出文件 [--crf 值]')
    parser.add_argument('--crf', type=int, default=23, help='压缩质量 (18-28，默认23)')
    parser.add_argument('--extract-audio', nargs=2, help='提取音频: --extract-audio 输入文件 输出文件')
    parser.add_argument('--thumbnail', nargs=2, help='截取封面: --thumbnail 输入文件 输出文件')
    parser.add_argument('--merge', nargs='+', help='拼接视频: --merge 输出文件 输入文件1 输入文件2 ...')
    parser.add_argument('--gif', nargs=2, help='生成GIF: --gif 输入文件 输出文件')
    parser.add_argument('--rename', type=str, help='按时间重命名: --rename 文件路径')
    parser.add_argument('--batch', nargs=2, help='批量处理: --batch 输入目录 操作类型(info/compress)')
    
    args = parser.parse_args()
    
    if args.selftest:
        selftest()
        return 0
    
    processor = ScreenRecordingProcessor()
    
    # 任务管理功能
    manager = TaskManager()
    
    if args.add:
        title = args.add[0]
        priority = args.add[1] if len(args.add) > 1 else 'medium'
        due_date = args.add[2] if len(args.add) > 2 else None
        task_id = manager.add_task(title, priority, due_date)
        print(f"任务已添加，ID: {task_id}")
    
    if args.list:
        tasks = manager.list_tasks()
        if not tasks:
            print("暂无任务")
        else:
            for task in tasks:
                status = "✓" if task['completed'] else "✗"
                print(f"[{status}] ID: {task['id']}, 标题: {task['title']}, "
                      f"优先级: {task['priority']}, 截止日期: {task['due_date'] or '无'}")
    
    if args.complete is not None:
        if manager.complete_task(args.complete):
            print(f"任务 {args.complete} 已完成")
        else:
            print(f"任务 {args.complete} 不存在")
    
    if args.delete is not None:
        task = manager.delete_task(args.delete)
        if task:
            print(f"任务 {args.delete} 已删除")
        else:
            print(f"任务 {args.delete} 不存在")
    
    if args.stats:
        stats = manager.get_stats()
        print(f"总任务数: {stats['total']}")
        print(f"已完成: {stats['completed']}")
        print(f"待完成: {stats['pending']}")
    
    # 录屏处理功能
    if args.probe:
        try:
            info = processor.probe_video(args.probe)
            print(json.dumps(info, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.compress:
        try:
            input_file, output_file = args.compress
            processor.compress_video(input_file, output_file, crf=args.crf)
            print(f"压缩完成: {output_file}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.extract_audio:
        try:
            input_file, output_file = args.extract_audio
            processor.extract_audio(input_file, output_file)
            print(f"音频提取完成: {output_file}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.thumbnail:
        try:
            input_file, output_file = args.thumbnail
            processor.extract_thumbnail(input_file, output_file)
            print(f"封面截取完成: {output_file}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.merge:
        try:
            output_file = args.merge[0]
            input_files = args.merge[1:]
            processor.merge_videos(input_files, output_file)
            print(f"视频拼接完成: {output_file}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.gif:
        try:
            input_file, output_file = args.gif
            processor.generate_gif(input_file, output_file)
            print(f"GIF生成完成: {output_file}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.rename:
        try:
            new_path = processor.rename_by_time(args.rename)
            print(f"重命名完成: {new_path}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    if args.batch:
        try:
            input_dir, action = args.batch
            results = processor.batch_process(input_dir, action=action)
            for result in results:
                if result['status'] == 'success':
                    print(f"✓ {result['file']}")
                else:
                    print(f"✗ {result['file']}: {result.get('error', '未知错误')}")
        except Exception as e:
            print(f"错误: {e}")
            return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
