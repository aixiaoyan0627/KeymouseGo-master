
# -*- encoding:utf-8 -*-
import os
import sys
import traceback

print("=" * 60)
print("YOLO 训练调试脚本")
print("=" * 60)

# 设置环境变量
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

print("\n步骤 1: 检查 Python 环境")
print(f"Python 版本: {sys.version}")

print("\n步骤 2: 检查数据集配置")
yaml_path = "./yolo_training/dataset.yaml"
print(f"数据集配置路径: {yaml_path}")

if not os.path.exists(yaml_path):
    print("❌ 数据集配置文件不存在")
    sys.exit(1)

print("✅ 数据集配置文件存在")

# 检查数据集目录
train_dir = "./yolo_training/train"
val_dir = "./yolo_training/val"

print(f"\n检查训练目录: {train_dir}")
if os.path.exists(train_dir):
    train_images = os.path.join(train_dir, "images")
    train_labels = os.path.join(train_dir, "labels")
    
    if os.path.exists(train_images):
        images = [f for f in os.listdir(train_images) if f.endswith(('.png', '.jpg'))]
        print(f"  训练图片数量: {len(images)}")
    else:
        print("❌ 训练图片目录不存在")
        
    if os.path.exists(train_labels):
        labels = [f for f in os.listdir(train_labels) if f.endswith('.txt')]
        print(f"  训练标注数量: {len(labels)}")
    else:
        print("❌ 训练标注目录不存在")
else:
    print("❌ 训练目录不存在")

print(f"\n检查验证目录: {val_dir}")
if os.path.exists(val_dir):
    val_images = os.path.join(val_dir, "images")
    val_labels = os.path.join(val_dir, "labels")
    
    if os.path.exists(val_images):
        images = [f for f in os.listdir(val_images) if f.endswith(('.png', '.jpg'))]
        print(f"  验证图片数量: {len(images)}")
    else:
        print("❌ 验证图片目录不存在")
        
    if os.path.exists(val_labels):
        labels = [f for f in os.listdir(val_labels) if f.endswith('.txt')]
        print(f"  验证标注数量: {len(labels)}")
    else:
        print("❌ 验证标注目录不存在")
else:
    print("❌ 验证目录不存在")

print("\n步骤 3: 导入 ultralytics")
try:
    from ultralytics import YOLO
    print("✅ ultralytics 导入成功")
except Exception as e:
    print(f"❌ ultralytics 导入失败: {e}")
    print("详细错误信息:")
    print(traceback.format_exc())
    sys.exit(1)

print("\n步骤 4: 加载预训练模型")
try:
    model = YOLO("yolov8s.pt")
    print("✅ 模型加载成功")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    print("详细错误信息:")
    print(traceback.format_exc())
    sys.exit(1)

print("\n步骤 5: 开始训练（简化版测试）")
print("注意: 使用最小配置进行测试")
print("=" * 60)

try:
    print("开始训练...")
    results = model.train(
        data=yaml_path,
        epochs=2,  # 只训练 2 轮测试
        batch=1,   # 最小批次
        imgsz=320, # 小尺寸
        device='cpu',
        patience=1,
        save=False, # 不保存，只测试
        verbose=True
    )
    print("\n✅ 训练成功完成！")
    
except Exception as e:
    print(f"\n❌ 训练失败: {e}")
    print("\n详细错误信息:")
    print(traceback.format_exc())
    
    # 检查是否是特定错误
    if "CUDA" in str(e):
        print("\n⚠️ 检测到 CUDA 相关错误，尝试强制使用 CPU")
        try:
            results = model.train(
                data=yaml_path,
                epochs=2,
                batch=1,
                imgsz=320,
                device='cpu',
                patience=1,
                save=False,
                verbose=True
            )
            print("✅ 使用 CPU 训练成功！")
        except Exception as e2:
            print(f"❌ CPU 训练也失败: {e2}")

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
