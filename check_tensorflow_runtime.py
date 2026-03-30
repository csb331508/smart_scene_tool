import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="检查 TensorFlow 当前运行设备")
    parser.add_argument("--require-gpu", action="store_true", help="没有检测到 GPU 时返回非零退出码")
    args = parser.parse_args()

    try:
        import tensorflow as tf
    except ImportError:
        print("[ERROR] TensorFlow 未安装")
        return 1

    gpus = tf.config.list_physical_devices("GPU")
    cpus = tf.config.list_physical_devices("CPU")

    print(f"TensorFlow 版本: {tf.__version__}")
    print(f"CUDA 构建: {tf.test.is_built_with_cuda()}")
    print(f"GPU 数量: {len(gpus)}")
    print(f"CPU 数量: {len(cpus)}")

    for index, gpu in enumerate(gpus, 1):
        print(f"GPU {index}: {gpu}")

    if args.require_gpu and not gpus:
        print("[ERROR] 当前环境未检测到 TensorFlow GPU 设备")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
