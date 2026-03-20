
# -*- encoding:utf-8 -*-
import os
import sys
import traceback
import psutil

print("=" * 60)
print("深度调试脚本 - 检查内存和资源问题")
print("=" * 60)

# 检查系统资源
print("\n步骤 1: 检查系统资源")
print(f"CPU 核心数: {psutil.cpu_count()}")
print(f"内存总量: {psutil.virtual_memory().total / (1024**3):.1f} GB")
print(f"可用内存: {psutil.virtual_memory().available / (1024**3):.1f} GB")

# 设置环境变量
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

print("\n步骤 2: 检查数据集")
yaml_path = "./yolo_training/dataset.yaml"
print(f"数据集配置: {yaml_path}")

# 检查数据集大小
train_images_dir = "./yolo_training/train/images"
if os.path.exists(train_images_dir):
    total_size = 0
    for root, dirs, files in os.walk(train_images_dir):
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    print(f"训练集总大小: {total_size / (1024**2):.1f} MB")

print("\n步骤 3: 导入 ultralytics")
try:
    from ultralytics import YOLO
    print("✅ ultralytics 导入成功")
except Exception as e:
    print(f"❌ ultralytics 导入失败: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("\n步骤 4: 测试数据加载（不训练）")
try:
    model = YOLO("yolov8s.pt")
    print("✅ 模型加载成功")
    
    # 只创建数据集，不训练
    print("\n尝试创建数据集...")
    dataset = model._setup_dataset(yaml_path)
    print("✅ 数据集创建成功")
    
    print(f"训练集大小: {len(dataset.train_loader.dataset)}")
    print(f"验证集大小: {len(dataset.val_loader.dataset)}")
    
    # 测试加载一个批次
    print("\n测试加载一个批次...")
    for batch in dataset.train_loader:
        print("✅ 批次加载成功")
        print(f"批次形状: {batch['img'].shape}")
        break
        
except Exception as e:
    print(f"❌ 数据加载失败: {e}")
    print("详细错误:")
    print(traceback.format_exc())
    
    # 尝试更简单的测试
    print("\n尝试更简单的测试...")
    try:
        # 使用最小的配置
        results = model.train(
            data=yaml_path,
            epochs=1,
            batch=1,
            imgsz=64,  # 非常小的尺寸
            device='cpu',
            save=False,
            verbose=True,
            workers=0,  # 不使用多线程
            cache=False
        )
        print("✅ 最小配置训练成功")
    except Exception as e2:
        print(f"❌ 最小配置也失败: {e2}")
        print("可能的问题:")
        print("1. 内存不足")
        print("2. 数据集路径问题")
        print("3. 标注文件格式错误")

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
