
import sys
print("Python 版本:", sys.version)
print("开始导入...")

try:
    import os
    print("os 导入成功")
    
    os.environ['POLARS_SKIP_CPU_CHECK'] = '1'
    print("环境变量设置成功")
    
    print("尝试导入 ultralytics...")
    from ultralytics import YOLO
    print("ultralytics 导入成功！")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    print(traceback.format_exc())
