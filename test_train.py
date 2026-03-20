
# -*- encoding:utf-8 -*-
import os
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

print("=" * 60)
print("测试训练脚本")
print("=" * 60)

print("\n步骤 1: 导入 ultralytics...")
try:
    from ultralytics import YOLO
    print("   ✅ ultralytics 导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    import traceback
    print(traceback.format_exc())
    exit(1)

print("\n步骤 2: 检查数据集配置...")
yaml_path = "./yolo_training/dataset.yaml"
if os.path.exists(yaml_path):
    print(f"   ✅ 数据集配置存在: {yaml_path}")
    import yaml
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    print(f"   类别数: {data['nc']}")
    print(f"   类别: {data['names']}")
else:
    print(f"   ❌ 数据集配置不存在: {yaml_path}")
    exit(1)

print("\n步骤 3: 加载预训练模型...")
try:
    model = YOLO("yolov8s.pt")
    print("   ✅ 模型加载成功")
except Exception as e:
    print(f"   ❌ 模型加载失败: {e}")
    import traceback
    print(traceback.format_exc())
    exit(1)

print("\n" + "=" * 60)
print("所有检查通过！现在开始训练...")
print("=" * 60)
print("\n注意: 训练过程会显示进度条，请耐心等待...")
print("\n开始训练...\n")

try:
    results = model.train(
        data=yaml_path,
        epochs=10,  # 先用 10 轮测试
        batch=4,    # 小批次测试
        imgsz=640,
        device='cpu',
        patience=5,
        save=True,
        project="./yolo_training",
        name="test_train",
        exist_ok=True
    )
    print("\n✅ 训练成功！")
except Exception as e:
    print(f"\n❌ 训练失败: {e}")
    import traceback
    print(traceback.format_exc())
