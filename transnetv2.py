import os
import subprocess
import sys

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'

import numpy as np
import tensorflow as tf


class TransNetV2:

    def __init__(self, model_dir=None, ffmpeg_path="ffmpeg", gpu_acceleration="auto"):
        if model_dir is None:
            # model_dir = os.path.join(os.path.dirname(__file__), "transnetv2-weights/")
            model_dir = "transnetv2-weights/"
            if not os.path.isdir(model_dir):
                raise FileNotFoundError(f"[TransNetV2] ERROR: {model_dir} is not a directory.")
            else:
                print(f"[TransNetV2] Using weights from {model_dir}.")

        self._input_size = (27, 48, 3)
        self.ffmpeg_path = ffmpeg_path
        self.gpu_acceleration = gpu_acceleration
        self.analysis_acceleration_status = "CPU"
        self.inference_device_status = "TensorFlow CPU"
        gpu_devices = tf.config.list_physical_devices("GPU")
        if gpu_devices:
            for gpu in gpu_devices:
                try:
                    tf.config.experimental.set_memory_growth(gpu, True)
                except Exception:
                    pass
            self.inference_device_status = f"TensorFlow GPU ({len(gpu_devices)} 张)"
        try:
            self._model = tf.saved_model.load(model_dir)
        except OSError as exc:
            raise IOError(f"[TransNetV2] It seems that files in {model_dir} are corrupted or missing. "
                          f"Re-download them manually and retry. For more info, see: "
                          f"https://github.com/soCzech/TransNetV2/issues/1#issuecomment-647357796") from exc

    def predict_raw(self, frames: np.ndarray):
        assert len(frames.shape) == 5 and frames.shape[2:] == self._input_size, \
            "[TransNetV2] Input shape must be [batch, frames, height, width, 3]."
        frames = tf.cast(frames, tf.float32)

        logits, dict_ = self._model(frames)
        single_frame_pred = tf.sigmoid(logits)
        all_frames_pred = tf.sigmoid(dict_["many_hot"])

        return single_frame_pred, all_frames_pred

    def predict_frames(self, frames: np.ndarray, progress_callback=None):
        assert len(frames.shape) == 4 and frames.shape[1:] == self._input_size, \
            "[TransNetV2] Input shape must be [frames, height, width, 3]."

        def input_iterator():
            # return windows of size 100 where the first/last 25 frames are from the previous/next batch
            # the first and last window must be padded by copies of the first and last frame of the video
            no_padded_frames_start = 25
            no_padded_frames_end = 25 + 50 - (len(frames) % 50 if len(frames) % 50 != 0 else 50)  # 25 - 74

            start_frame = np.expand_dims(frames[0], 0)
            end_frame = np.expand_dims(frames[-1], 0)
            padded_inputs = np.concatenate(
                [start_frame] * no_padded_frames_start + [frames] + [end_frame] * no_padded_frames_end, 0
            )

            ptr = 0
            while ptr + 100 <= len(padded_inputs):
                out = padded_inputs[ptr:ptr + 100]
                ptr += 50
                yield out[np.newaxis]

        predictions = []

        for inp in input_iterator():
            single_frame_pred, all_frames_pred = self.predict_raw(inp)
            predictions.append((single_frame_pred.numpy()[0, 25:75, 0],
                                all_frames_pred.numpy()[0, 25:75, 0]))

            processed_frames = min(len(predictions) * 50, len(frames))
            print("\r[TransNetV2] Processing video frames {}/{}".format(
                processed_frames, len(frames)
            ), end="")
            if progress_callback:
                progress_callback(f"正在模型推理... {processed_frames}/{len(frames)} 帧")

        print("\n")

        single_frame_pred = np.concatenate([single_ for single_, all_ in predictions])
        all_frames_pred = np.concatenate([all_ for single_, all_ in predictions])

        return single_frame_pred[:len(frames)], all_frames_pred[:len(frames)]  # remove extra padded frames

    def predict_video(self, video_fn: str):
        try:
            import ffmpeg
        except ModuleNotFoundError:
            raise ModuleNotFoundError("For `predict_video` function `ffmpeg` needs to be installed in order to extract "
                                      "individual frames from video file. Install `ffmpeg` command line tool and then "
                                      "install python wrapper by `pip install ffmpeg-python`.")

        print("[TransNetV2] Extracting frames from {}".format(video_fn))
        video_stream, err = ffmpeg.input(video_fn).output(
            "pipe:", format="rawvideo", pix_fmt="rgb24", s="48x27"
        ).run(capture_stdout=True, capture_stderr=True)

        video = np.frombuffer(video_stream, np.uint8).reshape([-1, 27, 48, 3])
        return (video, *self.predict_frames(video))

    def _get_hwaccel_candidates(self):
        """根据选择返回分析阶段的硬件解码候选"""
        if self.gpu_acceleration == "nvidia":
            return [("cuda", "NVIDIA CUDA"), (None, "CPU")]
        if self.gpu_acceleration == "amd":
            return [("d3d11va", "D3D11VA"), ("dxva2", "DXVA2"), (None, "CPU")]
        if self.gpu_acceleration == "cpu":
            return [(None, "CPU")]
        return [("cuda", "NVIDIA CUDA"), ("d3d11va", "D3D11VA"), ("dxva2", "DXVA2"), (None, "CPU")]

    def _run_ffmpeg_extract(self, cmd):
        """执行FFmpeg抽帧命令"""
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3600,
            creationflags=creationflags
        )

    def _decode_ffmpeg_error(self, raw_error):
        """提取FFmpeg错误摘要"""
        text = raw_error.decode("utf-8", errors="replace").strip()
        if not text:
            return "未知错误"

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            if line.lower() == "conversion failed!":
                continue
            return line
        return lines[-1]

    def _build_extract_frames_cmd(self, video_fn: str, hwaccel_method=None):
        """构建分析阶段抽帧命令"""
        cmd = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel", "error"
        ]

        if hwaccel_method:
            cmd.extend(["-hwaccel", hwaccel_method])

        cmd.extend([
            "-i", video_fn,
            "-an",
            "-sn",
            "-dn"
        ])

        cmd.extend([
            "-vf", "scale=48:27:flags=fast_bilinear,format=rgb24",
            "-pix_fmt", "rgb24",
            "-f", "rawvideo",
            "pipe:1"
        ])
        return cmd

    def _extract_frames_with_ffmpeg(self, video_fn: str, progress_callback=None):
        """使用FFmpeg批量抽取分析所需帧"""
        frame_size = int(np.prod(self._input_size))
        last_error = "未知错误"

        for hwaccel_method, label in self._get_hwaccel_candidates():
            if progress_callback:
                progress_callback("正在提取分析帧...")

            cmd = self._build_extract_frames_cmd(video_fn, hwaccel_method)
            result = self._run_ffmpeg_extract(cmd)

            if result.returncode != 0:
                last_error = self._decode_ffmpeg_error(result.stderr)
                print(f"[TransNetV2] Hardware decode fallback from {label}: {last_error}")
                continue

            raw_video = result.stdout
            if not raw_video:
                last_error = "FFmpeg未返回任何视频帧"
                print(f"[TransNetV2] Hardware decode fallback from {label}: {last_error}")
                continue

            if len(raw_video) % frame_size != 0:
                last_error = f"抽帧数据长度异常: {len(raw_video)}"
                print(f"[TransNetV2] Hardware decode fallback from {label}: {last_error}")
                continue

            video = np.frombuffer(raw_video, np.uint8).reshape([-1, 27, 48, 3])
            self.analysis_acceleration_status = label
            print(f"[TransNetV2] Successfully extracted {len(video)} frames with {label}")
            return video

        raise RuntimeError(f"[TransNetV2] Failed to extract frames: {last_error}")

    def predict_video_2(self, video_fn: str, progress_callback=None):
        print("[TransNetV2] Extracting frames from {}".format(video_fn))
        video = self._extract_frames_with_ffmpeg(video_fn, progress_callback)
        return video, *self.predict_frames(video, progress_callback=progress_callback)

    @staticmethod
    def predictions_to_scenes(predictions: np.ndarray, threshold: float = 0.15):
        """
        将预测结果转换为场景列表

        Args:
            predictions: 预测数组，每个元素是场景边界的概率
            threshold: 阈值（默认 0.15 以最大化场景检测数量）
                      值越低检测越敏感，检测到更多场景边界

        Returns:
            场景数组，形状为 [n_scenes, 2]，每行为 [start_frame, end_frame]
        """
        predictions = (predictions > threshold).astype(np.uint8)

        scenes = []
        t, t_prev, start = -1, 0, 0
        for i, t in enumerate(predictions):
            if t_prev == 1 and t == 0:
                start = i
            if t_prev == 0 and t == 1 and i != 0:
                scenes.append([start, i])
            t_prev = t
        if t == 0:
            scenes.append([start, i])

        # just fix if all predictions are 1
        if len(scenes) == 0:
            return np.array([[0, len(predictions) - 1]], dtype=np.int32)

        return np.array(scenes, dtype=np.int32)

    @staticmethod
    def visualize_predictions(frames: np.ndarray, predictions):
        from PIL import Image, ImageDraw

        if isinstance(predictions, np.ndarray):
            predictions = [predictions]

        ih, iw, ic = frames.shape[1:]
        width = 25

        # pad frames so that length of the video is divisible by width
        # pad frames also by len(predictions) pixels in width in order to show predictions
        pad_with = width - len(frames) % width if len(frames) % width != 0 else 0
        frames = np.pad(frames, [(0, pad_with), (0, 1), (0, len(predictions)), (0, 0)])

        predictions = [np.pad(x, (0, pad_with)) for x in predictions]
        height = len(frames) // width

        img = frames.reshape([height, width, ih + 1, iw + len(predictions), ic])
        img = np.concatenate(np.split(
            np.concatenate(np.split(img, height), axis=2)[0], width
        ), axis=2)[0, :-1]

        img = Image.fromarray(img)
        draw = ImageDraw.Draw(img)

        # iterate over all frames
        for i, pred in enumerate(zip(*predictions)):
            x, y = i % width, i // width
            x, y = x * (iw + len(predictions)) + iw, y * (ih + 1) + ih - 1

            # we can visualize multiple predictions per single frame
            for j, p in enumerate(pred):
                color = [0, 0, 0]
                color[(j + 1) % 3] = 255

                value = round(p * (ih - 1))
                if value != 0:
                    draw.line((x + j, y, x + j, y - value), fill=tuple(color), width=1)
        return img


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=str, nargs="+", help="path to video files to process")
    parser.add_argument("--weights", type=str, default=None,
                        help="path to TransNet V2 weights, tries to infer the location if not specified")
    parser.add_argument('--visualize', action="store_true",
                        help="save a png file with prediction visualization for each extracted video")
    args = parser.parse_args()

    model = TransNetV2(args.weights)
    for file in args.files:
        if os.path.exists(file + ".predictions.txt") or os.path.exists(file + ".scenes.txt"):
            print(f"[TransNetV2] {file}.predictions.txt or {file}.scenes.txt already exists. "
                  f"Skipping video {file}.", file=sys.stderr)
            continue

        video_frames, single_frame_predictions, all_frame_predictions = \
            model.predict_video(file)

        predictions = np.stack([single_frame_predictions, all_frame_predictions], 1)
        np.savetxt(file + ".predictions.txt", predictions, fmt="%.6f")

        scenes = model.predictions_to_scenes(single_frame_predictions)
        np.savetxt(file + ".scenes.txt", scenes, fmt="%d")

        if args.visualize:
            if os.path.exists(file + ".vis.png"):
                print(f"[TransNetV2] {file}.vis.png already exists. "
                      f"Skipping visualization of video {file}.", file=sys.stderr)
                continue

            pil_image = model.visualize_predictions(
                video_frames, predictions=(single_frame_predictions, all_frame_predictions))
            pil_image.save(file + ".vis.png")


if __name__ == "__main__":
    main()
