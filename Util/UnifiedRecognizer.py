# -*- encoding:utf-8 -*-
"""
统一识别器基类

提供统一的识别接口，支持 YOLO 和 OCR 两种识别方式
智能路由：自动选择最佳识别方式

设计原则：
1. 统一接口：detect() → (x, y, confidence)
2. 智能路由：按目录自动选择 YOLO 或 OCR
3. 代码复用：共享截图、预处理、后处理逻辑
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from loguru import logger

# 导入截图工具
try:
    import cv2
    import mss
    HAS_CV = True
except ImportError:
    HAS_CV = False
    logger.warning('OpenCV 未安装，截图功能不可用')


class RecognitionMethod(Enum):
    """识别方法"""
    YOLO = auto()      # YOLO 目标检测
    OCR = auto()       # OCR 文字识别


@dataclass
class RecognitionResult:
    """识别结果"""
    success: bool
    method: RecognitionMethod
    position: Optional[Tuple[int, int]] = None  # 中心点坐标 (x, y)
    confidence: float = 0.0
    class_name: Optional[str] = None  # YOLO 类别
    text: Optional[str] = None  # OCR 文字
    bbox: Optional[Tuple[int, int, int, int]] = None  # 边界框 (x1, y1, x2, y2)
    error: Optional[str] = None  # 错误信息


# 目录到识别方法的映射配置
# imgsA/B → YOLO（图标）
# imgsC/E/F/G → OCR（文字）
DIRECTORY_METHOD_MAP = {
    'imgsA': RecognitionMethod.YOLO,
    'imgsB': RecognitionMethod.YOLO,
    'imgsC': RecognitionMethod.OCR,
    'imgsE': RecognitionMethod.OCR,
    'imgsF': RecognitionMethod.OCR,
    'imgsG': RecognitionMethod.OCR,
}


class BaseRecognizer(ABC):
    """
    识别器基类
    
    统一接口：
    ```python
    recognizer = ConcreteRecognizer()
    result = recognizer.detect(target)
    if result.success:
        x, y = result.position
        click(x, y)
    ```
    """
    
    def __init__(self, use_gpu: bool = True):
        """
        初始化识别器
        
        :param use_gpu: 是否使用 GPU
        """
        self.use_gpu = use_gpu
        self._initialized = False
    
    @abstractmethod
    def _init_engine(self):
        """初始化识别引擎（子类实现）"""
        pass
    
    @abstractmethod
    def _recognize(self, image: np.ndarray, target: Any) -> RecognitionResult:
        """
        执行识别（子类实现）
        
        :param image: 图像数组
        :param target: 识别目标
        :return: 识别结果
        """
        pass
    
    def _take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        截取屏幕截图
        
        :param region: 截取区域 (x1, y1, x2, y2)，None 表示全屏
        :return: OpenCV 图像数组（BGR 格式）
        """
        if not HAS_CV:
            raise ImportError('OpenCV 未安装')
        
        try:
            with mss.mss() as sct:
                if region:
                    monitor = {
                        'left': region[0],
                        'top': region[1],
                        'width': region[2] - region[0],
                        'height': region[3] - region[1],
                    }
                else:
                    monitor = sct.monitors[0]  # 全屏
                
                screenshot = sct.grab(monitor)
                
                # 转换为 OpenCV 格式（BGR）
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                return img
                
        except Exception as e:
            logger.error(f'截图失败：{e}')
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理
        
        :param image: 原始图像
        :return: 预处理后的图像
        """
        # 默认不需要特殊处理
        # 子类可以重写此方法添加自定义预处理
        return image
    
    def _postprocess_result(
        self,
        result: Any,
        method: RecognitionMethod,
    ) -> RecognitionResult:
        """
        后处理：统一转换为 RecognitionResult
        
        :param result: 原始识别结果
        :param method: 识别方法
        :return: 统一格式的识别结果
        """
        if result is None:
            return RecognitionResult(
                success=False,
                method=method,
            )
        
        # 提取坐标和置信度
        if isinstance(result, dict):
            # YOLO 格式
            bbox = result.get('bbox')
            confidence = result.get('confidence', 0.0)
            class_name = result.get('class_name')
            
            if bbox:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                return RecognitionResult(
                    success=True,
                    method=method,
                    position=(center_x, center_y),
                    confidence=confidence,
                    class_name=class_name,
                    bbox=bbox,
                )
        
        elif isinstance(result, tuple) and len(result) >= 2:
            # 简单坐标格式 (x, y)
            return RecognitionResult(
                success=True,
                method=method,
                position=(result[0], result[1]),
                confidence=1.0,
            )
        
        # 默认失败
        return RecognitionResult(
            success=False,
            method=method,
        )
    
    def detect(
        self,
        target: Any,
        screenshot: Optional[np.ndarray] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> RecognitionResult:
        """
        检测目标（统一接口）
        
        :param target: 识别目标（路径、类别名、文字等）
        :param screenshot: 屏幕截图（None 则自动截取）
        :param region: 检测区域
        :return: 识别结果
        """
        # 确保引擎已初始化
        if not self._initialized:
            self._init_engine()
            self._initialized = True
        
        # 截取或复用截图
        if screenshot is None:
            screenshot = self._take_screenshot(region)
        elif region:
            # 裁剪指定区域
            x1, y1, x2, y2 = region
            screenshot = screenshot[y1:y2, x1:x2]
        
        # 预处理
        image = self._preprocess_image(screenshot)
        
        # 执行识别
        try:
            result = self._recognize(image, target)
            return result
        except Exception as e:
            logger.error(f'识别失败：{e}')
            return RecognitionResult(
                success=False,
                method=self._get_method(),
                error=str(e),
            )
    
    @abstractmethod
    def _get_method(self) -> RecognitionMethod:
        """获取当前识别方法（子类实现）"""
        pass


class UnifiedRecognizer:
    """
    统一识别器（智能路由）
    
    根据目标路径自动选择最佳识别方式：
    - imgsA/B → YOLO（图标）
    - imgsC/E/F/G → OCR（文字）
    
    使用示例：
    ```python
    recognizer = UnifiedRecognizer()
    
    # 自动选择识别方式
    result = recognizer.detect('imgsA/icon1.png')
    if result.success:
        click(result.position)
    
    # 手动指定识别方式
    result = recognizer.detect('target', method=RecognitionMethod.YOLO)
    ```
    """
    
    def __init__(
        self,
        yolo_model_path: Optional[str] = None,
        use_gpu: bool = True,
    ):
        """
        初始化统一识别器
        
        :param yolo_model_path: YOLO 模型路径
        :param use_gpu: 是否使用 GPU
        """
        self.yolo_model_path = yolo_model_path
        self.use_gpu = use_gpu
        
        self._yolo_recognizer = None
        self._ocr_recognizer = None
        
        logger.info('统一识别器已初始化（YOLO+OCR 智能路由）')
    
    def _get_yolo_recognizer(self):
        """获取 YOLO 识别器（延迟加载，单例）"""
        if self._yolo_recognizer is None:
            from .yolo_recognizer import YOLORecognizer
            logger.info('正在初始化 YOLO 识别器...')
            self._yolo_recognizer = YOLORecognizer(
                model_path=self.yolo_model_path,
                use_gpu=self.use_gpu,
            )
            logger.info('YOLO 识别器已初始化')
        return self._yolo_recognizer
    
    def _get_ocr_recognizer(self):
        """获取 OCR 识别器（延迟加载）"""
        if self._ocr_recognizer is None:
            from .ocr_recognizer import OCRRecognizer
            self._ocr_recognizer = OCRRecognizer(use_gpu=self.use_gpu)
            logger.info('OCR 识别器已初始化')
        return self._ocr_recognizer
    
    def _infer_method_from_path(self, target: Union[str, List[str]]) -> RecognitionMethod:
        """
        根据路径推断识别方法
        
        :param target: 目标路径或列表
        :return: 识别方法
        """
        if not isinstance(target, str):
            # 非字符串目标，默认使用 YOLO
            return RecognitionMethod.YOLO
        
        target_lower = target.lower()
        
        # 遍历映射表，查找匹配的目录
        for dir_name, method in DIRECTORY_METHOD_MAP.items():
            if dir_name.lower() in target_lower:
                logger.debug(f'智能路由：{os.path.basename(target)} → {method.name}')
                return method
        
        # 默认使用 YOLO
        logger.debug(f'未匹配目录，使用默认方法：YOLO')
        return RecognitionMethod.YOLO
    
    def _extract_text_from_filename(self, filepath: str) -> str:
        """
        从文件名提取目标文字（用于 OCR）
        
        :param filepath: 文件路径
        :return: 提取的文字
        """
        filename = os.path.basename(filepath)
        name, _ = os.path.splitext(filename)
        
        # 尝试拼音转中文
        try:
            from .voyage.pinyin_converter import pinyin_to_chinese
            chinese_text = pinyin_to_chinese(name)
            if chinese_text != name:
                logger.debug(f'拼音转中文：{name} → {chinese_text}')
                return chinese_text
        except Exception:
            pass
        
        return name
    
    def detect(
        self,
        target: Union[str, List[str]],
        method: Optional[RecognitionMethod] = None,
        screenshot: Optional[np.ndarray] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> RecognitionResult:
        """
        检测目标（智能路由）
        
        :param target: 识别目标（路径、类别名、文字）
        :param method: 识别方法（None 则自动选择）
        :param screenshot: 屏幕截图（None 则自动截取）
        :param region: 检测区域
        :return: 识别结果
        """
        # 智能路由：自动选择识别方式
        if method is None:
            method = self._infer_method_from_path(target)
        
        logger.debug(f'使用识别方法：{method.name}')
        
        # 选择识别器
        if method == RecognitionMethod.YOLO:
            recognizer = self._get_yolo_recognizer()
        elif method == RecognitionMethod.OCR:
            recognizer = self._get_ocr_recognizer()
        else:
            return RecognitionResult(
                success=False,
                method=method,
                error=f'不支持的识别方法：{method}',
            )
        
        # 对于 OCR，需要从文件名提取文字
        if method == RecognitionMethod.OCR and isinstance(target, str) and os.path.exists(target):
            target = self._extract_text_from_filename(target)
            logger.debug(f'OCR 目标：{target}')
        
        # 执行识别
        return recognizer.detect(target, screenshot, region)
    
    def detect_multiple(
        self,
        targets: List[Union[str, List[str]]],
        screenshot: Optional[np.ndarray] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[RecognitionResult]:
        """
        批量检测多个目标
        
        :param targets: 目标列表
        :param screenshot: 屏幕截图（None 则自动截取）
        :param region: 检测区域
        :return: 识别结果列表
        """
        # 只截取一次屏幕
        if screenshot is None:
            screenshot = self._take_screenshot(region)
        
        results = []
        for target in targets:
            result = self.detect(target, screenshot=screenshot, region=None)
            results.append(result)
        
        return results
    
    def find_best_match(
        self,
        targets: List[str],
        screenshot: Optional[np.ndarray] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        min_confidence: float = 0.5,
    ) -> Optional[RecognitionResult]:
        """
        查找最佳匹配
        
        :param targets: 目标列表
        :param screenshot: 屏幕截图
        :param region: 检测区域
        :param min_confidence: 最低置信度
        :return: 最佳匹配结果或 None
        """
        results = self.detect_multiple(targets, screenshot, region)
        
        # 过滤成功结果
        successful = [r for r in results if r.success and r.confidence >= min_confidence]
        
        if not successful:
            return None
        
        # 返回置信度最高的
        best = max(successful, key=lambda x: x.confidence)
        logger.info(f'最佳匹配：{best.class_name or best.text} (confidence={best.confidence:.2f})')
        
        return best


# 便捷函数
_recognizer_instance: Optional[UnifiedRecognizer] = None


def init_recognizer(
    yolo_model_path: Optional[str] = None,
    use_gpu: bool = True,
) -> UnifiedRecognizer:
    """
    初始化全局识别器实例
    
    :param yolo_model_path: YOLO 模型路径
    :param use_gpu: 是否使用 GPU
    :return: UnifiedRecognizer 实例
    """
    global _recognizer_instance
    _recognizer_instance = UnifiedRecognizer(
        yolo_model_path=yolo_model_path,
        use_gpu=use_gpu,
    )
    return _recognizer_instance


def get_recognizer() -> UnifiedRecognizer:
    """
    获取全局识别器实例
    
    :return: UnifiedRecognizer 实例
    """
    global _recognizer_instance
    if _recognizer_instance is None:
        _recognizer_instance = UnifiedRecognizer()
    return _recognizer_instance


def detect(
    target: Union[str, List[str]],
    method: Optional[RecognitionMethod] = None,
    screenshot: Optional[np.ndarray] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
) -> RecognitionResult:
    """
    便捷函数：检测目标
    
    :param target: 识别目标
    :param method: 识别方法
    :param screenshot: 屏幕截图
    :param region: 检测区域
    :return: 识别结果
    """
    recognizer = get_recognizer()
    return recognizer.detect(target, method, screenshot, region)


# 导出
__all__ = [
    'RecognitionMethod',
    'RecognitionResult',
    'BaseRecognizer',
    'UnifiedRecognizer',
    'init_recognizer',
    'get_recognizer',
    'detect',
    'DIRECTORY_METHOD_MAP',
]
