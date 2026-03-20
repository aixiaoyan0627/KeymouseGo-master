# -*- encoding:utf-8 -*-
"""
YOLO 目标检测器

基于 Ultralytics YOLOv8
官方文档: https://docs.ultralytics.com/
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import numpy as np
from loguru import logger

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning('ultralytics 未安装，YOLO 功能不可用')


class YOLODetector:
    """YOLO 目标检测器"""
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_gpu: bool = True,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ):
        """
        初始化 YOLO 检测器
        
        参数:
            model_path: 模型路径（None 则使用默认模型）
            use_gpu: 是否使用 GPU
            conf_threshold: 置信度阈值
            iou_threshold: IOU 阈值（非极大值抑制）
        """
        if not HAS_YOLO:
            raise ImportError('ultralytics 未安装，请运行: pip install ultralytics')
        
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        self._model = None
        self._device = None
        
        self._init_model()
    
    def _init_model(self):
        """初始化模型"""
        import torch
        
        if self.use_gpu and torch.cuda.is_available():
            self._device = 'cuda'
            logger.info('使用 GPU (CUDA) 进行推理')
        elif self.use_gpu and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self._device = 'mps'
            logger.info('使用 GPU (MPS) 进行推理')
        else:
            self._device = 'cpu'
            logger.info('使用 CPU 进行推理')
        
        if self.model_path and os.path.exists(self.model_path):
            logger.info(f'加载自定义模型: {self.model_path}')
            self._model = YOLO(self.model_path)
        else:
            logger.info('加载默认模型: yolov8n.pt (nano版本，速度快)')
            self._model = YOLO('yolov8n.pt')
        
        self._model.to(self._device)
        
        logger.info('YOLO 模型初始化完成')
    
    def detect(
        self,
        image: np.ndarray,
        class_names: Optional[List[str]] = None,
        class_ids: Optional[List[int]] = None,
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        检测图像中的目标
        
        参数:
            image: OpenCV 图像 (BGR 格式)
            class_names: 要检测的类别名称列表（None 则检测所有）
            class_ids: 要检测的类别 ID 列表（None 则检测所有）
            confidence_threshold: 置信度阈值（None 则使用默认）
        
        返回:
            检测结果列表，每个结果包含:
            {
                'class_id': int,
                'class_name': str,
                'confidence': float,
                'bbox': (x1, y1, x2, y2),
            }
        """
        if self._model is None:
            return []
        
        conf = confidence_threshold if confidence_threshold is not None else self.conf_threshold
        
        try:
            results = self._model.predict(
                source=image,
                conf=conf,
                iou=self.iou_threshold,
                device=self._device,
                verbose=False,
            )
            
            detections = []
            
            for result in results:
                if result.boxes is None:
                    continue
                
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id] if result.names else str(class_id)
                    confidence = float(box.conf[0])
                    
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    if class_names and class_name not in class_names:
                        continue
                    
                    if class_ids and class_id not in class_ids:
                        continue
                    
                    detections.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence,
                        'bbox': (x1, y1, x2, y2),
                    })
            
            if detections:
                logger.debug(f'YOLO 检测到 {len(detections)} 个目标')
            
            return detections
            
        except Exception as e:
            logger.error(f'YOLO 检测失败: {e}')
            return []
    
    def train(
        self,
        data_yaml: str,
        epochs: int = 100,
        imgsz: int = 640,
        batch: int = 16,
        project: str = 'runs/detect',
        name: str = 'train',
    ):
        """
        训练模型（高级功能）
        
        参数:
            data_yaml: 数据集配置文件路径
            epochs: 训练轮数
            imgsz: 图像大小
            batch: 批次大小
            project: 项目目录
            name: 实验名称
        """
        if self._model is None:
            logger.error('模型未初始化')
            return
        
        logger.info(f'开始训练模型，数据集: {data_yaml}')
        
        try:
            results = self._model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                project=project,
                name=name,
                device=self._device,
            )
            
            logger.info('训练完成')
            return results
            
        except Exception as e:
            logger.error(f'训练失败: {e}')
            return None
    
    def get_class_names(self) -> Dict[int, str]:
        """
        获取模型支持的类别名称
        
        返回:
            类别 ID 到名称的映射
        """
        if self._model is None:
            return {}
        
        return self._model.names


def create_yolo_detector(
    model_path: Optional[str] = None,
    use_gpu: bool = True,
) -> YOLODetector:
    """
    创建 YOLO 检测器的便捷函数
    
    参数:
        model_path: 模型路径
        use_gpu: 是否使用 GPU
    
    返回:
        YOLODetector
    """
    return YOLODetector(
        model_path=model_path,
        use_gpu=use_gpu,
    )
