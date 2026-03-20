
# -*- encoding:utf-8 -*-
import os
import sys

print("=" * 60)
print("修复版 YOLO 训练脚本")
print("=" * 60)

# 设置环境变量
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

try:
    from ultralytics import YOLO
    print("✅ ultralytics 导入成功")
except Exception as e:
    print(f"❌ ultralytics 导入失败: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

yaml_path = "./yolo_training/dataset.yaml"

if not os.path.exists(yaml_path):
    print(f"❌ 找不到数据集配置: {yaml_path}")
    sys.exit(1)

print(f"✅ 数据集配置: {yaml_path}")

print("\n开始加载模型...")
try:
    model = YOLO("yolov8s.pt")
    print("✅ 模型加载成功")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

print("\n开始训练...")
print("注意: 这次会显示进度条！")
print("=" * 60)

try:
    results = model.train(
        data=yaml_path,
        epochs=10,  # 先训练 10 轮测试
        batch=1,
        imgsz=320,
        device='cpu',
        patience=3,
        save=True,  # 关键：必须为 True 才会真正训练
        project="./yolo_training",
        name="fixed_train",
        exist_ok=True,
        workers=1,
        cache=False,
        amp=False,
        verbose=True
    )
    print("\n" + "=" * 60)
    print("✅ 训练成功完成！")
    print("=" * 60)
    
    # 检查最佳模型路径
    best_model_path = os.path.join("./yolo_training", "fixed_train", "weights", "best.pt")
    if os.path.exists(best_model_path):
        print(f"最佳模型已保存: {best_model_path}")
    
except Exception as e:
    print(f"\n❌ 训练失败: {e}")
    import traceback
    print("\n详细错误信息:")
    print(traceback.format_exc())
    sys.exit(1)
