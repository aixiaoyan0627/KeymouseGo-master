
# -*- encoding:utf-8 -*-
import os
import sys

print("=" * 60)
print("最简单的 YOLO 测试")
print("=" * 60)

# 设置环境变量
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

try:
    from ultralytics import YOLO
    print("✅ ultralytics 导入成功")
except Exception as e:
    print(f"❌ ultralytics 导入失败: {e}")
    sys.exit(1)

print("\n尝试最简单的训练...")
print("使用最小配置：1个epoch，batch=1，imgsz=64")
print("=" * 60)

try:
    model = YOLO("yolov8s.pt")
    
    # 最简配置
    results = model.train(
        data="./yolo_training/dataset.yaml",
        epochs=1,
        batch=1,
        imgsz=64,  # 非常小的尺寸
        device='cpu',
        save=True,
        verbose=True,
        workers=0,  # 不使用多线程
        cache=False
    )
    
    print("\n✅ 训练成功！")
    
except Exception as e:
    print(f"\n❌ 训练失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 检查是否是内存问题
    if "memory" in str(e).lower() or "cuda" in str(e).lower():
        print("\n⚠️ 可能是内存不足，尝试更小的配置...")
        try:
            # 更小的配置
            results = model.train(
                data="./yolo_training/dataset.yaml",
                epochs=1,
                batch=1,
                imgsz=32,  # 更小的尺寸
                device='cpu',
                save=True,
                verbose=True,
                workers=0,
                cache=False
            )
            print("✅ 小尺寸训练成功！")
        except Exception as e2:
            print(f"❌ 小尺寸也失败: {e2}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
