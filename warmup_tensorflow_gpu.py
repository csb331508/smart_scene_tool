import os
import time

import tensorflow as tf


def main():
    print(f"TensorFlow 版本: {tf.__version__}")
    print(f"CUDA 构建: {tf.test.is_built_with_cuda()}")
    gpus = tf.config.list_physical_devices("GPU")
    print(f"GPU 数量: {len(gpus)}")
    if not gpus:
        print("未检测到 TensorFlow GPU 设备")
        return 1

    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except Exception:
            pass

    start = time.time()
    with tf.device("/GPU:0"):
        a = tf.random.normal([2048, 2048])
        b = tf.random.normal([2048, 2048])
        c = tf.matmul(a, b)
        _ = c.numpy()
    elapsed = time.time() - start

    cache_path = os.environ.get("CUDA_CACHE_PATH", "")
    print(f"预热完成，用时: {elapsed:.2f} 秒")
    if cache_path:
        print(f"CUDA 缓存目录: {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
