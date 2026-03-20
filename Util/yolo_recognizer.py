# -*- encoding:utf-8 -*-
"""
YOLO 目标检测器

基于 Ultralytics YOLOv8
继承自 BaseRecognizer，提供统一的识别接口
"""
import os
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from loguru import logger

from .UnifiedRecognizer import BaseRecognizer, RecognitionMethod, RecognitionResult

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    logger.warning('ultralytics 未安装，YOLO 功能不可用')


class YOLORecognizer(BaseRecognizer):
    """
    YOLO 目标检测器
    
    使用示例：
    ```python
    yolo = YOLORecognizer(model_path='best.pt')
    
    # 检测单个目标
    result = yolo.detect('icon1', screenshot)
    if result.success:
        x, y = result.position
        click(x, y)
    
    # 检测多个目标
    result = yolo.detect(['icon1', 'icon2'], screenshot)
    ```
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        use_gpu: bool = True,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ):
        """
        初始化 YOLO 检测器
        
        :param model_path: 模型路径（None 则使用默认模型）
        :param use_gpu: 是否使用 GPU
        :param conf_threshold: 置信度阈值
        :param iou_threshold: IOU 阈值（非极大值抑制）
        """
        super().__init__(use_gpu)
        
        if not HAS_YOLO:
            raise ImportError('ultralytics 未安装，请运行：pip install ultralytics')
        
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        self._model = None
        self._device = None
        self._class_names = None
        
        # 立即初始化引擎
        self._init_engine()
        self._initialized = True  # 标记已初始化
    
    def _init_engine(self):
        """初始化 YOLO 模型"""
        import torch
        
        # 选择设备
        if self.use_gpu and torch.cuda.is_available():
            self._device = 'cuda'
            logger.info('使用 GPU (CUDA) 进行推理')
        elif self.use_gpu and hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            self._device = 'mps'
            logger.info('使用 GPU (MPS) 进行推理')
        else:
            self._device = 'cpu'
            logger.info('使用 CPU 进行推理')
        
        # 加载模型
        if self.model_path and os.path.exists(self.model_path):
            logger.info(f'加载自定义模型：{self.model_path}')
            self._model = YOLO(self.model_path)
        else:
            logger.info('加载默认模型：yolov8n.pt (nano 版本，速度快)')
            self._model = YOLO('yolov8n.pt')
        
        # 立即将模型移动到设备上并完成初始化
        self._model.to(self._device)
        
        # 预热：执行一次空检测，触发模型的真正加载
        try:
            logger.info('正在预热 YOLO 模型...')
            dummy_image = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(
                source=dummy_image,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self._device,
                verbose=False,
            )
            logger.info('YOLO 模型预热完成')
        except Exception as e:
            logger.warning(f'YOLO 模型预热失败：{e}')
        
        # 获取类别名称
        self._class_names = self._model.names
        
        logger.info('YOLO 模型初始化完成')
    
    def _recognize(
        self,
        image: np.ndarray,
        target: Any,
    ) -> RecognitionResult:
        """
        执行 YOLO 检测
        
        :param image: 图像数组
        :param target: 识别目标（类别名或列表）
        :return: 识别结果
        """
        if self._model is None:
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.YOLO,
                error='模型未初始化',
            )
        
        # 处理目标
        class_names = []
        if isinstance(target, str):
            class_names.append(target)
        elif isinstance(target, list):
            class_names = target
        else:
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.YOLO,
                error=f'不支持的目标类型：{type(target)}',
            )
        
        # 执行检测
        try:
            results = self._model.predict(
                source=image,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                verbose=False,
            )
            
            # 解析结果
            detections = []
            
            for result in results:
                if result.boxes is None:
                    continue
                
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id] if result.names else str(class_id)
                    confidence = float(box.conf[0])
                    
                    # 只保留匹配的目标
                    if class_name not in class_names:
                        continue
                    
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    detections.append({
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence,
                        'bbox': (x1, y1, x2, y2),
                    })
            
            if not detections:
                return RecognitionResult(
                    success=False,
                    method=RecognitionMethod.YOLO,
                )
            
            # 返回置信度最高的检测结果
            best_detection = max(detections, key=lambda x: x['confidence'])
            
            logger.debug(f'YOLO 检测到 {len(detections)} 个目标，最佳：{best_detection["class_name"]} ({best_detection["confidence"]:.2f})')
            
            return self._postprocess_result(best_detection, RecognitionMethod.YOLO)
            
        except Exception as e:
            logger.error(f'YOLO 检测失败：{e}')
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.YOLO,
                error=str(e),
            )
    
    def _get_method(self) -> RecognitionMethod:
        """获取当前识别方法"""
        return RecognitionMethod.YOLO
    
    def get_class_names(self) -> Dict[int, str]:
        """
        获取模型支持的类别名称
        
        :return: 类别 ID 到名称的映射
        """
        if self._model is None:
            return {}
        return self._model.names
    
    def set_conf_threshold(self, threshold: float):
        """
        设置置信度阈值
        
        :param threshold: 置信度阈值
        """
        self.conf_threshold = threshold
        logger.info(f'YOLO 置信度阈值已设置为：{threshold}')
    
    def detect_all(
        self,
        image: np.ndarray,
        class_names: Optional[List[str]] = None,
        confidence_threshold: Optional[float] = None,
    ) -> List[RecognitionResult]:
        """
        检测图像中的所有目标
        
        :param image: 图像数组
        :param class_names: 要检测的类别名称列表（None 则检测所有）
        :param confidence_threshold: 置信度阈值
        :return: 识别结果列表
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
            
            all_results = []
            
            for result in results:
                if result.boxes is None:
                    continue
                
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id] if result.names else str(class_id)
                    confidence = float(box.conf[0])
                    
                    # 过滤类别
                    if class_names and class_name not in class_names:
                        continue
                    
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    detection = {
                        'class_id': class_id,
                        'class_name': class_name,
                        'confidence': confidence,
                        'bbox': (x1, y1, x2, y2),
                    }
                    
                    result_obj = self._postprocess_result(detection, RecognitionMethod.YOLO)
                    all_results.append(result_obj)
            
            return all_results
            
        except Exception as e:
            logger.error(f'YOLO 检测失败：{e}')
            return []


# 便捷函数
def create_yolo_recognizer(
    model_path: Optional[str] = None,
    use_gpu: bool = True,
    conf_threshold: float = 0.25,
) -> YOLORecognizer:
    """
    创建 YOLO 识别器
    
    :param model_path: 模型路径
    :param use_gpu: 是否使用 GPU
    :param conf_threshold: 置信度阈值
    :return: YOLORecognizer 实例
    """
    return YOLORecognizer(
        model_path=model_path,
        use_gpu=use_gpu,
        conf_threshold=conf_threshold,
    )


# 导出
__all__ = [
    'YOLORecognizer',
    'create_yolo_recognizer',
]
