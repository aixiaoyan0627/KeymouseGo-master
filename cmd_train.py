
# -*- encoding:utf-8 -*-
import os
import subprocess
import sys

print("=" * 60)
print("使用命令行方式调用 YOLO 训练")
print("=" * 60)

# 设置环境变量
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

# 使用 subprocess 调用 yolo 命令
cmd = [
    "yolo",
    "task=detect",
    "mode=train",
    "model=yolov8s.pt",
    "data=./yolo_training/dataset.yaml",
    "epochs=5",
    "batch=1",
    "imgsz=64",
    "device=cpu",
    "workers=0",
    "cache=False",
    "verbose=True",
    "project=./yolo_training",
    "name=cmd_train"
]

print(f"\n执行命令: {' '.join(cmd)}")
print("=" * 60)

try:
    result = subprocess.run(cmd, check=True)
    print("\n✅ 训练成功完成！")
except subprocess.CalledProcessError as e:
    print(f"\n❌ 训练失败，退出码：{e.returncode}")
except Exception as e:
    print(f"\n❌ 发生错误: {e}")

print("\n" + "=" * 60)
print("训练结束")
print("=" * 60)
