
# -*- encoding:utf-8 -*-
import sys
print("=" * 60)
print("诊断脚本开始")
print("=" * 60)
print(f"Python 版本: {sys.version}")

print("\n1. 检查环境变量...")
import os
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'
print("   POLARS_SKIP_CPU_CHECK 已设置")

print("\n2. 尝试导入 torch...")
try:
    import torch
    print(f"   torch 版本: {torch.__version__}")
    print(f"   CUDA 可用: {torch.cuda.is_available()}")
except Exception as e:
    print(f"   torch 导入失败: {e}")
    import traceback
    print(traceback.format_exc())

print("\n3. 尝试导入 ultralytics...")
try:
    from ultralytics import YOLO
    print("   ultralytics 导入成功！")
except Exception as e:
    print(f"   ultralytics 导入失败: {e}")
    import traceback
    print(traceback.format_exc())

print("\n4. 检查数据集配置...")
yaml_path = "./yolo_training/dataset.yaml"
if os.path.exists(yaml_path):
    print(f"   数据集配置文件存在: {yaml_path}")
    try:
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        print(f"   类别数量: {data.get('nc', 'N/A')}")
        print(f"   类别名称: {data.get('names', 'N/A')}")
    except Exception as e:
        print(f"   读取配置失败: {e}")
else:
    print(f"   数据集配置文件不存在: {yaml_path}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
