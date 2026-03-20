
# -*- encoding:utf-8 -*-
import os
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'

from ultralytics import YOLO
from loguru import logger

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始训练 YOLO 模型")
    logger.info("=" * 60)
    
    yaml_path = "./yolo_training/dataset.yaml"
    
    logger.info(f"使用模型: yolov8s.pt")
    logger.info(f"训练轮数: 100")
    logger.info(f"批次大小: 2 (为适配CPU优化)")
    logger.info(f"图片尺寸: 640")
    logger.info(f"设备: CPU")
    
    try:
        model = YOLO("yolov8s.pt")
        
        results = model.train(
            data=yaml_path,
            epochs=100,
            batch=2,
            imgsz=640,
            device='cpu',
            patience=20,
            save=True,
            project="./yolo_training",
            name="yolov8_train",
            exist_ok=True,
            workers=2
        )
        
        logger.info("=" * 60)
        logger.info("训练完成！")
        logger.info("=" * 60)
        
        best_model_path = os.path.join("./yolo_training", "yolov8_train", "weights", "best.pt")
        if os.path.exists(best_model_path):
            logger.info(f"最佳模型已保存: {best_model_path}")
        
    except Exception as e:
        logger.error(f"训练失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
