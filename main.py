"""
场景分割工具 - 独立GUI应用程序
支持智能分割和普通分割两种模式
"""
import sys
import os
import json
import subprocess
import re
import random
import math
from pathlib import Path
from typing import List, Tuple, Optional, Callable


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    支持开发环境和PyInstaller打包后的环境
    
    Args:
        relative_path: 相对于程序根目录的路径
    
    Returns:
        资源文件的绝对路径
    """
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境中使用当前脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QLineEdit, QDoubleSpinBox, QComboBox,
    QMessageBox, QProgressDialog, QFileDialog, QGroupBox, QFormLayout, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon

try:
    import numpy as np
except ImportError:
    np = None


def setup_chinese_context_menu(widget):
    """为输入控件设置中文右键菜单"""
    widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def show_context_menu(pos):
        menu = QMenu(widget)

        # 撤销
        undo_action = QAction("撤销", widget)
        undo_action.triggered.connect(lambda: widget.undo() if hasattr(widget, 'undo') else None)
        undo_action.setEnabled(widget.isUndoAvailable() if hasattr(widget, 'isUndoAvailable') else False)
        menu.addAction(undo_action)

        # 重做
        redo_action = QAction("重做", widget)
        redo_action.triggered.connect(lambda: widget.redo() if hasattr(widget, 'redo') else None)
        redo_action.setEnabled(widget.isRedoAvailable() if hasattr(widget, 'isRedoAvailable') else False)
        menu.addAction(redo_action)

        menu.addSeparator()

        # 剪切
        cut_action = QAction("剪切", widget)
        cut_action.triggered.connect(lambda: widget.cut() if hasattr(widget, 'cut') else None)
        cut_action.setEnabled(widget.hasSelectedText() if hasattr(widget, 'hasSelectedText') else False)
        menu.addAction(cut_action)

        # 复制
        copy_action = QAction("复制", widget)
        copy_action.triggered.connect(lambda: widget.copy() if hasattr(widget, 'copy') else None)
        copy_action.setEnabled(widget.hasSelectedText() if hasattr(widget, 'hasSelectedText') else False)
        menu.addAction(copy_action)

        # 粘贴
        paste_action = QAction("粘贴", widget)
        paste_action.triggered.connect(lambda: widget.paste() if hasattr(widget, 'paste') else None)
        menu.addAction(paste_action)

        # 删除
        delete_action = QAction("删除", widget)
        delete_action.triggered.connect(lambda: widget.del_() if hasattr(widget, 'del_') else None)
        delete_action.setEnabled(widget.hasSelectedText() if hasattr(widget, 'hasSelectedText') else False)
        menu.addAction(delete_action)

        menu.addSeparator()

        # 全选
        select_all_action = QAction("全选", widget)
        select_all_action.triggered.connect(lambda: widget.selectAll() if hasattr(widget, 'selectAll') else None)
        menu.addAction(select_all_action)

        menu.exec(widget.mapToGlobal(pos))

    widget.customContextMenuRequested.connect(show_context_menu)


class VideoSplitter:
    """视频分割器 - 简化版本，只包含核心功能"""
    
    def __init__(self, ffmpeg_path=None):
        """初始化视频分割器"""
        # 查找FFmpeg
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        if not self.ffmpeg_path:
            raise FileNotFoundError(
                "未找到FFmpeg！请执行以下操作之一：\n"
                "1. 将 ffmpeg.exe 放在程序所在目录下\n"
                "2. 安装FFmpeg并添加到系统PATH环境变量"
            )
        
        print(f"[INFO] 使用FFmpeg: {self.ffmpeg_path}")
        
        # 检查TensorFlow可用性
        self.tensorflow_version = None
        self.tensorflow_gpu_available = False
        self.tensorflow_device_summary = "TensorFlow 未加载"
        self.tensorflow_available = self._check_tensorflow()
        
        # GPU加速设置
        self.gpu_acceleration = "auto"
        self.acceleration_status = "CPU (libx264)"
        self._encoder_probe_cache = {}
        self._resolved_encoder = None
        
    def _find_ffmpeg(self):
        """查找FFmpeg可执行文件 - 优先查找程序目录"""
        # 1. 首先检查程序所在目录
        try:
            # 获取可执行文件所在目录
            if getattr(sys, 'frozen', False):
                # 打包后的程序
                exe_dir = os.path.dirname(sys.executable)
            else:
                # 开发环境
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            ffmpeg_local = os.path.join(exe_dir, 'ffmpeg.exe')
            if os.path.exists(ffmpeg_local):
                print(f"[INFO] 找到本地FFmpeg: {ffmpeg_local}")
                return ffmpeg_local
        except Exception as e:
            print(f"[WARNING] 检查本地FFmpeg失败: {e}")
        
        # 2. 然后检查系统PATH
        try:
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                ffmpeg_path = result.stdout.strip().split('\n')[0]
                print(f"[INFO] 找到系统FFmpeg: {ffmpeg_path}")
                return ffmpeg_path
        except Exception as e:
            print(f"[WARNING] 检查系统FFmpeg失败: {e}")
        
        return None
    
    def _check_tensorflow(self):
        """检查TensorFlow是否可用"""
        try:
            import tensorflow as tf
            self.tensorflow_version = tf.__version__
            gpu_devices = tf.config.list_physical_devices('GPU')
            self.tensorflow_gpu_available = bool(gpu_devices)

            if gpu_devices:
                for gpu in gpu_devices:
                    try:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    except Exception:
                        pass

            if self.tensorflow_gpu_available:
                self.tensorflow_device_summary = f"TensorFlow GPU ({len(gpu_devices)} 张)"
            else:
                self.tensorflow_device_summary = "TensorFlow CPU"

            print(f"[OK] TensorFlow {tf.__version__} 可用")
            print(f"[INFO] TensorFlow 推理设备: {self.tensorflow_device_summary}")
            return True
        except ImportError:
            self.tensorflow_version = None
            self.tensorflow_gpu_available = False
            self.tensorflow_device_summary = "TensorFlow 未安装"
            print("[WARNING] TensorFlow不可用，智能分割功能将被禁用")
            return False
    
    def set_gpu_acceleration(self, gpu_type):
        """设置GPU加速类型"""
        self.gpu_acceleration = gpu_type
        self.acceleration_status = "CPU (libx264)"
        self._resolved_encoder = None

    def _run_ffmpeg_command(self, cmd, timeout):
        """统一执行FFmpeg命令，避免重复的子进程配置"""
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            creationflags=creationflags
        )

    def _build_encoder_config(self, backend):
        """根据后端类型构建视频编码配置"""
        configs = {
            'cpu': {
                'backend': 'cpu',
                'codec': 'libx264',
                'label': 'CPU (libx264)',
                'args': ['-preset', 'fast', '-crf', '23']
            },
            'nvidia': {
                'backend': 'nvidia',
                'codec': 'h264_nvenc',
                'label': 'NVIDIA NVENC',
                'args': ['-preset', 'fast', '-rc', 'constqp', '-qp', '23']
            },
            'amd': {
                'backend': 'amd',
                'codec': 'h264_amf',
                'label': 'AMD AMF',
                'args': ['-quality', 'speed', '-rc', 'cqp', '-qp_i', '23', '-qp_p', '23']
            }
        }
        return configs[backend]

    def _get_acceleration_priority(self):
        """根据用户选择返回编码后端优先级"""
        if self.gpu_acceleration == 'nvidia':
            return ['nvidia', 'cpu']
        if self.gpu_acceleration == 'amd':
            return ['amd', 'cpu']
        if self.gpu_acceleration == 'cpu':
            return ['cpu']
        return ['nvidia', 'amd', 'cpu']

    def _probe_encoder(self, encoder_config):
        """轻量探测编码器是否能在当前机器上正常初始化"""
        backend = encoder_config['backend']
        if backend == 'cpu':
            return True

        if backend in self._encoder_probe_cache:
            return self._encoder_probe_cache[backend]

        cmd = [
            self.ffmpeg_path,
            '-hide_banner',
            '-loglevel', 'error',
            '-f', 'lavfi',
            '-i', 'color=c=black:s=640x360:d=0.2:r=24',
            '-frames:v', '1',
            '-an',
            '-c:v', encoder_config['codec']
        ]
        cmd.extend(encoder_config['args'])
        cmd.extend(['-f', 'null', '-'])

        try:
            result = self._run_ffmpeg_command(cmd, timeout=15)
            available = result.returncode == 0
            self._encoder_probe_cache[backend] = available

            if available:
                print(f"[INFO] 硬件编码器可用: {encoder_config['label']}")
            else:
                error_msg = self._extract_ffmpeg_error(result)
                print(f"[WARNING] 硬件编码器不可用: {encoder_config['label']} - {error_msg}")

            return available
        except Exception as e:
            self._encoder_probe_cache[backend] = False
            print(f"[WARNING] 探测硬件编码器失败: {encoder_config['label']} - {e}")
            return False

    def _extract_ffmpeg_error(self, result):
        """提取FFmpeg错误信息中的有效摘要"""
        raw_output = (result.stderr or result.stdout or '').strip()
        if not raw_output:
            return "未知错误"

        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        ignore_tokens = ('ffmpeg version', 'configuration:', 'libav', 'Input #', 'Output #', 'Stream #')

        for line in reversed(lines):
            if any(token in line for token in ignore_tokens):
                continue
            if line.lower() == 'conversion failed!':
                continue
            return line

        return lines[-1]

    def _resolve_video_encoder(self):
        """根据用户选择解析实际使用的视频编码器"""
        if self._resolved_encoder is not None:
            return self._resolved_encoder

        for backend in self._get_acceleration_priority():
            encoder_config = self._build_encoder_config(backend)
            if self._probe_encoder(encoder_config):
                self._resolved_encoder = encoder_config
                self.acceleration_status = encoder_config['label']
                print(f"[INFO] 当前视频编码器: {encoder_config['label']}")
                return encoder_config

        self._resolved_encoder = self._build_encoder_config('cpu')
        self.acceleration_status = self._resolved_encoder['label']
        print(f"[INFO] 当前视频编码器: {self._resolved_encoder['label']}")
        return self._resolved_encoder

    def _build_extract_command(self, video_path, output_path, start_time, end_time, encoder_config):
        """构建提取片段命令，保留原有切片时序逻辑，仅替换视频编码器"""
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c:v', encoder_config['codec'],
            '-c:a', 'aac'
        ]
        cmd.extend(encoder_config['args'])
        cmd.extend([
            '-y',
            output_path
        ])
        return cmd
    
    def _get_video_metadata(self, video_path):
        """获取视频元数据（时长和帧率）"""
        try:
            cmd = [self.ffmpeg_path, '-i', video_path]
            result = self._run_ffmpeg_command(cmd, timeout=10)
            
            # 解析时长
            duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
            if duration_match:
                hours, minutes, seconds = duration_match.groups()
                duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            else:
                return None, None
            
            # 解析帧率
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', result.stderr)
            fps = float(fps_match.group(1)) if fps_match else 30.0
            
            return duration, fps
        except Exception as e:
            print(f"[ERROR] 获取视频元数据失败: {e}")
            return None, None
    
    def _extract_segment(self, video_path, output_path, start_time, end_time):
        """使用FFmpeg提取视频片段"""
        try:
            duration = end_time - start_time
            if duration < 0.01:
                return False

            encoder_config = self._resolve_video_encoder()
            cmd = self._build_extract_command(
                video_path, output_path, start_time, end_time, encoder_config
            )
            result = self._run_ffmpeg_command(cmd, timeout=3600)

            if result.returncode == 0 and os.path.exists(output_path):
                return True

            if encoder_config['backend'] != 'cpu':
                error_msg = self._extract_ffmpeg_error(result)
                print(f"[WARNING] {encoder_config['label']} 编码失败，自动回退CPU: {error_msg}")

                cpu_config = self._build_encoder_config('cpu')
                self._encoder_probe_cache[encoder_config['backend']] = False
                self._resolved_encoder = cpu_config
                self.acceleration_status = f"{encoder_config['label']} 初始化失败，已回退到 CPU (libx264)"

                retry_cmd = self._build_extract_command(
                    video_path, output_path, start_time, end_time, cpu_config
                )
                retry_result = self._run_ffmpeg_command(retry_cmd, timeout=3600)
                return retry_result.returncode == 0 and os.path.exists(output_path)

            return False
        except Exception as e:
            print(f"[ERROR] 提取片段失败: {e}")
            return False
    
    def smart_split(self, video_path, output_folder, min_duration, max_duration,
                   progress_callback=None, short_segment_strategy='keep'):
        """智能分割模式 - 使用TransNetV2检测场景"""
        if not self.tensorflow_available:
            return False, "TensorFlow不可用，无法使用智能分割", []
        
        try:
            from transnetv2 import TransNetV2
            
            # 创建输出文件夹
            os.makedirs(output_folder, exist_ok=True)
            
            # 加载模型
            if progress_callback:
                progress_callback("正在加载模型...")
            model = TransNetV2(
                ffmpeg_path=self.ffmpeg_path,
                gpu_acceleration=self.gpu_acceleration
            )
            
            # 分析视频
            if progress_callback:
                progress_callback("正在分析视频场景...")
            video_frames, single_frame_pred, _ = model.predict_video_2(
                video_path,
                progress_callback=progress_callback
            )
            
            # 检测场景边界
            scenes = model.predictions_to_scenes(single_frame_pred, threshold=0.15)
            
            # 获取视频FPS
            duration, fps = self._get_video_metadata(video_path)
            if not fps:
                fps = 30.0
            
            # 转换场景帧为时间
            raw_scenes = []
            for start_frame, end_frame in scenes:
                start_time = start_frame / fps
                end_time = end_frame / fps
                raw_scenes.append((start_time, end_time))
            
            # 合并短片段逻辑
            # 要求：从前往后合并，直到满足最小间隔；只有最后一个片段如果不满足，才向前合并
            merged_scenes = []
            if raw_scenes:
                # 初始化当前buffer为第一个场景
                current_start, current_end = raw_scenes[0]
                
                for i in range(1, len(raw_scenes)):
                    next_start, next_end = raw_scenes[i]
                    
                    # 检查当前累积时长
                    current_duration = current_end - current_start
                    
                    if short_segment_strategy == 'merge' and current_duration < min_duration:
                         # 不满足最小时长，且策略为合并：与下一个场景合并
                         # 扩展当前buffer的结束时间
                         current_end = next_end
                    else:
                        # 满足时长 或者 策略不是合并：保存当前buffer
                        merged_scenes.append((current_start, current_end))
                        # 开启新的buffer
                        current_start, current_end = next_start, next_end
                
                # 处理最后一个buffer
                current_duration = current_end - current_start
                if short_segment_strategy == 'merge' and current_duration < min_duration and merged_scenes:
                    # 如果最后一个片段太短，且前面有已保存的片段：合并到前一个片段 (特殊情况：最后一个片段向前合并)
                    last_saved_start, last_saved_end = merged_scenes.pop()
                    merged_scenes.append((last_saved_start, current_end))
                else:
                    # 否则（满足时长，或只有一个片段，或策略不合并），直接保存
                    merged_scenes.append((current_start, current_end))
            
            # 最终筛选和处理超长片段
            final_scenes = []
            for start, end in merged_scenes:
                duration = end - start
                
                # 再次检查时长（处理'delete'策略或单个长片段的情况）
                if duration < min_duration:
                    if short_segment_strategy == 'delete':
                        continue
                    # keep or merge(但只有一个片段无法合并) -> keep
                
                if duration > max_duration:
                    # 分割超长场景
                    current = start
                    while current < end:
                        segment_end = min(current + max_duration, end)
                        final_scenes.append((current, segment_end))
                        current = segment_end
                else:
                    final_scenes.append((start, end))
            
            # 提取视频片段
            output_files = []
            total_scenes = len(final_scenes)
            self._resolve_video_encoder()
            
            for i, (start, end) in enumerate(final_scenes, 1):
                if progress_callback:
                    progress_callback(f"正在提取片段 {i}/{total_scenes}...")
                
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_file = os.path.join(output_folder, f"{video_name}_片段_{i:03d}.mp4")
                
                if self._extract_segment(video_path, output_file, start, end):
                    output_files.append(output_file)
            
            return True, f"成功分割为 {len(output_files)} 个场景", output_files
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"智能分割失败: {str(e)}", []
    
    def regular_split(self, video_path, output_folder, min_duration, max_duration,
                     progress_callback=None, short_segment_strategy='keep'):
        """普通分割模式 - 按固定/随机时间间隔分割"""
        try:
            # 创建输出文件夹
            os.makedirs(output_folder, exist_ok=True)
            
            # 获取视频时长
            duration, fps = self._get_video_metadata(video_path)
            if not duration:
                return False, "无法获取视频时长", []
            
            # 生成分割时间点
            segments = []
            current_time = 0.0
            
            while current_time < duration:
                # 随机选择片段时长（在min和max之间）
                if min_duration == max_duration:
                    segment_duration = min_duration
                else:
                    segment_duration = random.uniform(min_duration, max_duration)
                
                end_time = min(current_time + segment_duration, duration)
                segments.append((current_time, end_time))
                current_time = end_time
            
            # 处理最后一个片段（可能小于最小时长）
            if segments and short_segment_strategy == 'delete':
                last_duration = segments[-1][1] - segments[-1][0]
                if last_duration < min_duration and len(segments) > 1:
                    segments.pop()  # 删除最后一个短片段
            elif segments and short_segment_strategy == 'merge' and len(segments) > 1:
                last_duration = segments[-1][1] - segments[-1][0]
                if last_duration < min_duration:
                    # 合并到前一个片段
                    segments[-2] = (segments[-2][0], segments[-1][1])
                    segments.pop()
            
            # 提取视频片段
            output_files = []
            total_segments = len(segments)
            self._resolve_video_encoder()
            
            for i, (start, end) in enumerate(segments, 1):
                if progress_callback:
                    progress_callback(f"正在提取片段 {i}/{total_segments}...")
                
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_file = os.path.join(output_folder, f"{video_name}_片段_{i:03d}.mp4")
                
                if self._extract_segment(video_path, output_file, start, end):
                    output_files.append(output_file)
            
            return True, f"成功分割为 {len(output_files)} 个片段", output_files
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"普通分割失败: {str(e)}", []


class SplittingWorker(QThread):
    """后台分割视频的工作线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, list)

    def __init__(self, splitter, mode, video_path, output_folder, min_dur, max_dur,
                 short_segment_strategy="keep", gpu_acceleration="auto"):
        super().__init__()
        self.splitter = splitter
        self.mode = mode
        self.video_path = video_path
        self.output_folder = output_folder
        self.min_duration = min_dur
        self.max_duration = max_dur
        self.short_segment_strategy = short_segment_strategy
        self.gpu_acceleration = gpu_acceleration

    def run(self):
        """执行分割任务"""
        try:
            self.splitter.set_gpu_acceleration(self.gpu_acceleration)
            
            if self.mode == "smart":
                success, msg, files = self.splitter.smart_split(
                    self.video_path, self.output_folder,
                    self.min_duration, self.max_duration,
                    self.progress.emit, self.short_segment_strategy
                )
            else:
                success, msg, files = self.splitter.regular_split(
                    self.video_path, self.output_folder,
                    self.min_duration, self.max_duration,
                    self.progress.emit, self.short_segment_strategy
                )
            
            self.finished.emit(success, msg, files)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, f"处理失败: {str(e)}", [])


class SceneSplittingApp(QMainWindow):
    """场景分割应用程序主窗口"""
    
    CONFIG_FILE = "config.json"
    
    def __init__(self):
        super().__init__()
        self.splitter = None
        self.worker = None
        self.batch_videos = []
        self.batch_current_index = 0
        self.batch_results = {'total': 0, 'success': 0, 'failed': 0, 'details': []}
        
        # 初始化分割器
        try:
            self.splitter = VideoSplitter()
        except Exception as e:
            QMessageBox.critical(self, "初始化失败", f"无法初始化视频分割器:\n{str(e)}")
            sys.exit(1)
        
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("双星科技场景智能分割工具 v1.2")
        self.setMinimumSize(600, 700)
        
        # 中央 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("✂️ 双星科技场景智能分割工具 （QV:39909）")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 分割模式选择
        mode_group = QGroupBox("分割模式")
        mode_layout = QHBoxLayout()
        mode_label = QLabel("选择模式:")
        self.mode_combo = QComboBox()
        
        if self.splitter.tensorflow_available:
            self.mode_combo.addItems(["🤖 智能场景分割", "⏱️ 普通场景分割"])
        else:
            self.mode_combo.addItems(["⏱️ 普通场景分割"])
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 时间范围配置
        time_group = QGroupBox("⏱️ 时间范围配置")
        time_layout = QFormLayout()
        
        self.min_duration = QDoubleSpinBox()
        self.min_duration.setMinimum(0.1)
        self.min_duration.setMaximum(3600)
        self.min_duration.setValue(5.0)
        self.min_duration.setSuffix(" 秒")
        time_layout.addRow("最短时间区间:", self.min_duration)
        
        self.max_duration = QDoubleSpinBox()
        self.max_duration.setMinimum(0.1)
        self.max_duration.setMaximum(3600)
        self.max_duration.setValue(30.0)
        self.max_duration.setSuffix(" 秒")
        time_layout.addRow("最长时间区间:", self.max_duration)
        
        self.short_segment_combo = QComboBox()
        self.short_segment_combo.addItems([
            "保留所有短片段",
            "删除小于最短时长的片段",
            "合并短片段"
        ])
        time_layout.addRow("短片段处理:", self.short_segment_combo)
        
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems([
            "自动选择最佳加速方式",
            "使用 NVIDIA GPU 加速",
            "使用 AMD GPU 加速",
            "仅使用 CPU 处理"
        ])
        time_layout.addRow("硬件加速:", self.gpu_combo)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # 输入输出配置
        io_group = QGroupBox("📂 输入/输出配置")
        io_layout = QFormLayout()
        
        self.input_folder = QLineEdit()
        self.input_folder.setPlaceholderText("选择输入文件夹...")
        input_btn = QPushButton("📂 浏览...")
        input_btn.clicked.connect(self._select_input_folder)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_folder)
        input_layout.addWidget(input_btn)
        io_layout.addRow("输入文件夹:", input_layout)
        
        self.output_folder = QLineEdit()
        self.output_folder.setPlaceholderText("选择输出文件夹...")
        output_btn = QPushButton("📂 浏览...")
        output_btn.clicked.connect(self._select_output_folder)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_folder)
        output_layout.addWidget(output_btn)
        io_layout.addRow("输出文件夹:", output_layout)
        
        io_group.setLayout(io_layout)
        layout.addWidget(io_group)
        
        # 设置右键菜单
        for widget in [self.mode_combo, self.min_duration, self.max_duration,
                      self.short_segment_combo, self.gpu_combo, self.input_folder, self.output_folder]:
            setup_chinese_context_menu(widget)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        start_btn = QPushButton("🚀 开始分割")
        start_btn.setMinimumHeight(40)
        start_btn.setMinimumWidth(120)
        start_btn.clicked.connect(self._start_splitting)
        button_layout.addWidget(start_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # 应用样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
    
    def _select_input_folder(self):
        """选择输入文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择输入文件夹")
        if folder:
            self.input_folder.setText(folder)
    
    def _select_output_folder(self):
        """选择输出文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if folder:
            self.output_folder.setText(folder)
    
    def _load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                if 'mode' in config:
                    mode_index = 0 if config['mode'] == 'smart' else 1
                    self.mode_combo.setCurrentIndex(mode_index)
                if 'min_duration' in config:
                    self.min_duration.setValue(config['min_duration'])
                if 'max_duration' in config:
                    self.max_duration.setValue(config['max_duration'])
                if 'short_segment_strategy' in config:
                    strategy_index = {'keep': 0, 'delete': 1, 'merge': 2}.get(
                        config['short_segment_strategy'], 0)
                    self.short_segment_combo.setCurrentIndex(strategy_index)
                if 'gpu_acceleration' in config:
                    gpu_index = {'auto': 0, 'nvidia': 1, 'amd': 2, 'cpu': 3}.get(
                        config['gpu_acceleration'], 0)
                    self.gpu_combo.setCurrentIndex(gpu_index)
                if 'input_folder' in config:
                    self.input_folder.setText(config['input_folder'])
                if 'output_folder' in config:
                    self.output_folder.setText(config['output_folder'])
        except Exception as e:
            print(f"[WARNING] 加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            strategy_map = {0: 'keep', 1: 'delete', 2: 'merge'}
            gpu_map = {0: 'auto', 1: 'nvidia', 2: 'amd', 3: 'cpu'}
            config = {
                'mode': 'smart' if self.mode_combo.currentIndex() == 0 else 'regular',
                'min_duration': self.min_duration.value(),
                'max_duration': self.max_duration.value(),
                'short_segment_strategy': strategy_map.get(self.short_segment_combo.currentIndex(), 'keep'),
                'gpu_acceleration': gpu_map.get(self.gpu_combo.currentIndex(), 'auto'),
                'input_folder': self.input_folder.text(),
                'output_folder': self.output_folder.text()
            }
            
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARNING] 保存配置失败: {e}")
    
    def _start_splitting(self):
        """开始分割"""
        # 验证输入
        if not self.input_folder.text():
            QMessageBox.warning(self, "错误", "请选择输入文件夹")
            return
        
        if not self.output_folder.text():
            QMessageBox.warning(self, "错误", "请选择输出文件夹")
            return
        
        min_dur = self.min_duration.value()
        max_dur = self.max_duration.value()
        
        if min_dur > max_dur:
            QMessageBox.warning(self, "错误", "最少时间不能大于最多时间")
            return
        
        # 保存配置
        self._save_config()
        
        # 获取视频文件
        input_path = Path(self.input_folder.text())
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}
        video_files = [f for f in input_path.glob('*') if f.suffix.lower() in video_extensions]
        
        if not video_files:
            QMessageBox.warning(self, "错误", "输入文件夹中没有找到视频文件")
            return
        
        # 初始化批处理
        self.batch_videos = sorted(video_files)
        self.batch_current_index = 0
        self.batch_results = {
            'total': len(self.batch_videos),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        # 获取参数
        mode_index = self.mode_combo.currentIndex()
        mode = "smart" if (self.splitter.tensorflow_available and mode_index == 0) else "regular"
        
        strategy_map = {0: 'keep', 1: 'delete', 2: 'merge'}
        gpu_map = {0: 'auto', 1: 'nvidia', 2: 'amd', 3: 'cpu'}
        short_segment_strategy = strategy_map.get(self.short_segment_combo.currentIndex(), 'keep')
        gpu_acceleration = gpu_map.get(self.gpu_combo.currentIndex(), 'auto')
        
        # 处理第一个视频
        self._process_next_video(mode, min_dur, max_dur, short_segment_strategy, gpu_acceleration)
    
    def _process_next_video(self, mode, min_dur, max_dur, short_segment_strategy, gpu_acceleration):
        """处理下一个视频"""
        if self.batch_current_index >= len(self.batch_videos):
            self._show_batch_summary()
            return
        
        video_file = self.batch_videos[self.batch_current_index]
        video_name = video_file.stem
        output_subfolder = os.path.join(self.output_folder.text(), video_name)
        
        current_num = self.batch_current_index + 1
        total_num = len(self.batch_videos)
        
        # 创建进度对话框
        progress = QProgressDialog(f"正在处理视频 {current_num}/{total_num}...", "取消", 0, 0, self)
        progress.setWindowTitle(f"分割 {video_name}")
        progress.setMinimumWidth(400)
        progress.show()
        
        # 创建工作线程
        self.worker = SplittingWorker(
            self.splitter, mode, str(video_file), output_subfolder,
            min_dur, max_dur, short_segment_strategy, gpu_acceleration
        )
        self.worker.progress.connect(lambda msg: progress.setLabelText(msg))
        self.worker.finished.connect(lambda success, msg, files:
            self._on_splitting_finished(success, msg, files, video_name, progress,
                                       mode, min_dur, max_dur, short_segment_strategy, gpu_acceleration))
        self.worker.start()
    
    def _on_splitting_finished(self, success, message, files, video_name, progress,
                              mode, min_dur, max_dur, short_segment_strategy, gpu_acceleration):
        """分割完成回调"""
        progress.close()
        
        # 记录结果
        if success:
            self.batch_results['success'] += 1
            self.batch_results['details'].append({
                'video': video_name,
                'status': '成功',
                'message': message,
                'files': len(files)
            })
        else:
            self.batch_results['failed'] += 1
            self.batch_results['details'].append({
                'video': video_name,
                'status': '失败',
                'message': message,
                'files': 0
            })
        
        # 处理下一个视频
        self.batch_current_index += 1
        
        if self.batch_current_index < len(self.batch_videos):
            self._process_next_video(mode, min_dur, max_dur, short_segment_strategy, gpu_acceleration)
        else:
            self._show_batch_summary()
    
    def _show_batch_summary(self):
        """显示批处理总结"""
        total = self.batch_results['total']
        success = self.batch_results['success']
        failed = self.batch_results['failed']
        
        details_text = ""
        for detail in self.batch_results['details']:
            status_icon = "✅" if detail['status'] == '成功' else "❌"
            details_text += f"{status_icon} {detail['video']}: {detail['status']}\n"
            if detail['files'] > 0:
                details_text += f"   输出文件: {detail['files']} 个\n"
        
        summary_message = f"""批处理完成！

总计: {total} 个视频
成功: {success} 个
失败: {failed} 个

详情:
{details_text}"""
        
        QMessageBox.information(self, "批处理完成", summary_message)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion样式获得更好的外观
    
    window = SceneSplittingApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
