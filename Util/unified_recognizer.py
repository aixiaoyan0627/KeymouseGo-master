# -*- encoding:utf-8 -*-
"""
YOLO+OCR 图像识别模块

核心特点：
1. 支持多种识别方式：模板匹配、YOLO、OCR
2. 统一接口，易于切换
3. 按目录自动智能路由（imgsC/E/F/G→OCR, imgsA/B→YOLO）
4. 向后兼容现有代码
"""
import os
from typing import Optional, Tuple, List, Dict, Any, Union
from enum import Enum, auto
from dataclasses import dataclass

from loguru import logger

# 导入现有的模板匹配
try:
    from .ImageRecognition import (
        find_image_on_screen as find_with_template,
        find_all_images_on_screen as find_all_with_template,
        take_screenshot,
    )
    HAS_TEMPLATE_MATCHER = True
except ImportError:
    HAS_TEMPLATE_MATCHER = False

# 导入拼音转换器
try:
    from .voyage.pinyin_converter import pinyin_to_chinese
    HAS_PINYIN_CONVERTER = True
except ImportError:
    HAS_PINYIN_CONVERTER = False


class RecognitionMethod(Enum):
    """识别方法"""
    TEMPLATE = auto()  # 模板匹配（现有方案）
    YOLO = auto()      # YOLO 目标检测
    OCR = auto()       # OCR 文字识别
    HYBRID = auto()    # 混合方案（先 YOLO，再验证）
    SMART = auto()     # 智能路由（按目录自动选择）


# 目录到识别方法的映射
DIRECTORY_METHOD_MAP = {
    'imgsC': RecognitionMethod.OCR,
    'imgsE': RecognitionMethod.OCR,
    'imgsF': RecognitionMethod.OCR,
    'imgsG': RecognitionMethod.OCR,
    'imgsA': RecognitionMethod.YOLO,
    'imgsB': RecognitionMethod.YOLO,
}


@dataclass
class DetectionResult:
    """检测结果"""
    method: RecognitionMethod
    success: bool
    position: Optional[Tuple[int, int]] = None  # 中心点坐标
    confidence: float = 0.0
    class_name: Optional[str] = None  # YOLO 类别
    text: Optional[str] = None  # OCR 文字
    bbox: Optional[Tuple[int, int, int, int]] = None  # 边界框 (x1, y1, x2, y2)
    extra: Dict[str, Any] = None  # 额外信息


# 全局识别器实例
_recognizer = None


class UnifiedRecognizer:
    """统一识别器"""
    
    def __init__(
        self,
        default_method: RecognitionMethod = RecognitionMethod.SMART,
        yolo_model_path: Optional[str] = None,
        use_gpu: bool = True,
    ):
        """
        初始化统一识别器
        
        参数:
            default_method: 默认识别方法（默认 SMART=智能路由）
            yolo_model_path: YOLO 模型路径
            use_gpu: 是否使用 GPU
        """
        self.default_method = default_method
        self.yolo_model_path = yolo_model_path
        self.use_gpu = use_gpu
        
        self._yolo_detector = None
        self._ocr_recognizer = None
        
        logger.info(f'统一识别器已初始化，默认方法: {default_method.name}')
    
    def _infer_method_from_path(self, target: Union[str, List[str]]) -> RecognitionMethod:
        """
        根据路径推断识别方法
        
        参数:
            target: 目标路径或列表
        
        返回:
            RecognitionMethod
        """
        if not isinstance(target, str):
            return RecognitionMethod.TEMPLATE
        
        target_lower = target.lower()
        
        for dir_name, method in DIRECTORY_METHOD_MAP.items():
            if dir_name.lower() in target_lower:
                logger.debug(f'智能路由: {os.path.basename(target)} → {method.name}')
                return method
        
        return RecognitionMethod.TEMPLATE
    
    def _extract_text_from_filename(self, filepath: str) -> Optional[str]:
        """
        从文件名提取目标文字（用于 OCR）
        
        参数:
            filepath: 模板文件路径
        
        返回:
            提取的文字或 None
        """
        filename = os.path.basename(filepath)
        name, _ = os.path.splitext(filename)
        
        if not name:
            return None
        
        if HAS_PINYIN_CONVERTER:
            try:
                chinese_text = pinyin_to_chinese(name)
                if chinese_text != name:
                    logger.debug(f'拼音转中文: {name} → {chinese_text}')
                    return chinese_text
            except Exception as e:
                logger.debug(f'拼音转中文失败: {e}')
        
        return name
    
    def _init_yolo(self):
        """初始化 YOLO 检测器（延迟加载）"""
        if self._yolo_detector is None:
            try:
                from .yolo_detector import YOLODetector
                self._yolo_detector = YOLODetector(
                    model_path=self.yolo_model_path,
                    use_gpu=self.use_gpu,
                )
                logger.info('YOLO 检测器已初始化')
            except Exception as e:
                logger.warning(f'YOLO 检测器初始化失败: {e}')
                self._yolo_detector = None
    
    def _init_ocr(self):
        """初始化 OCR 识别器（延迟加载）"""
        if self._ocr_recognizer is None:
            try:
                from .ocr_recognizer import OCRRecognizer
                self._ocr_recognizer = OCRRecognizer(use_gpu=self.use_gpu)
                logger.info('OCR 识别器已初始化')
            except Exception as e:
                logger.warning(f'OCR 识别器初始化失败: {e}')
                self._ocr_recognizer = None
    
    def detect(
        self,
        target: Union[str, List[str]],
        method: Optional[RecognitionMethod] = None,
        screenshot: Optional[Any] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        **kwargs,
    ) -> DetectionResult:
        """
        检测目标
        
        参数:
            target: 目标（模板路径 / 类别名 / 文字）
            method: 识别方法（None 则使用默认）
            screenshot: 屏幕截图（None 则自动截取）
            region: 检测区域
            **kwargs: 其他参数
        
        返回:
            DetectionResult
        """
        if method is None:
            method = self.default_method
        
        if method == RecognitionMethod.SMART:
            inferred_method = self._infer_method_from_path(target)
            return self.detect(target, inferred_method, screenshot, region, **kwargs)
        elif method == RecognitionMethod.TEMPLATE:
            return self._detect_with_template(target, screenshot, region, **kwargs)
        elif method == RecognitionMethod.YOLO:
            return self._detect_with_yolo(target, screenshot, region, **kwargs)
        elif method == RecognitionMethod.OCR:
            return self._detect_with_ocr(target, screenshot, region, **kwargs)
        elif method == RecognitionMethod.HYBRID:
            return self._detect_with_hybrid(target, screenshot, region, **kwargs)
        else:
            return DetectionResult(
                method=method,
                success=False,
                extra={'error': f'未知方法: {method}'},
            )
    
    def _detect_with_template(
        self,
        template_path: str,
        screenshot: Optional[Any] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        threshold: float = 0.8,
        **kwargs,
    ) -> DetectionResult:
        """用模板匹配检测"""
        if not HAS_TEMPLATE_MATCHER:
            return DetectionResult(
                method=RecognitionMethod.TEMPLATE,
                success=False,
                extra={'error': '模板匹配不可用'},
            )
        
        position = find_with_template(
            template_path=template_path,
            threshold=threshold,
            screenshot=screenshot,
            region=region,
        )
        
        return DetectionResult(
            method=RecognitionMethod.TEMPLATE,
            success=position is not None,
            position=position,
            confidence=threshold if position else 0.0,
        )
    
    def _detect_with_yolo(
        self,
        target: Union[str, List[str]],
        screenshot: Optional[Any] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        confidence_threshold: float = 0.5,
        **kwargs,
    ) -> DetectionResult:
        """用 YOLO 检测"""
        self._init_yolo()
        
        if self._yolo_detector is None:
            return DetectionResult(
                method=RecognitionMethod.YOLO,
                success=False,
                extra={'error': 'YOLO 检测器不可用'},
            )
        
        if screenshot is None:
            screenshot, _ = take_screenshot(region=region)
        
        class_names = []
        if isinstance(target, str):
            if os.path.exists(target):
                class_name = self._extract_text_from_filename(target)
                if class_name:
                    class_names.append(class_name)
                    logger.debug(f'从文件名提取类别名: {class_name}')
            else:
                class_names.append(target)
        else:
            class_names = target
        
        if not class_names:
            return DetectionResult(
                method=RecognitionMethod.YOLO,
                success=False,
                extra={'error': '未找到目标类别'},
            )
        
        results = self._yolo_detector.detect(
            image=screenshot,
            class_names=class_names,
            confidence_threshold=confidence_threshold,
        )
        
        if results:
            best_result = max(results, key=lambda x: x['confidence'])
            x1, y1, x2, y2 = best_result['bbox']
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            
            return DetectionResult(
                method=RecognitionMethod.YOLO,
                success=True,
                position=(center_x, center_y),
                confidence=best_result['confidence'],
                class_name=best_result['class_name'],
                bbox=(x1, y1, x2, y2),
            )
        
        return DetectionResult(
            method=RecognitionMethod.YOLO,
            success=False,
        )
    
    def _detect_with_ocr(
        self,
        target: Union[str, List[str]],
        screenshot: Optional[Any] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        **kwargs,
    ) -> DetectionResult:
        """用 OCR 检测"""
        self._init_ocr()
        
        if self._ocr_recognizer is None:
            return DetectionResult(
                method=RecognitionMethod.OCR,
                success=False,
                extra={'error': 'OCR 识别器不可用'},
            )
        
        if screenshot is None:
            screenshot, _ = take_screenshot(region=region)
        
        target_texts = []
        if isinstance(target, str):
            if os.path.exists(target):
                text = self._extract_text_from_filename(target)
                if text:
                    target_texts.append(text)
                    logger.debug(f'从文件名提取目标文字: {text}')
            else:
                target_texts.append(target)
        else:
            target_texts = target
        
        if not target_texts:
            return DetectionResult(
                method=RecognitionMethod.OCR,
                success=False,
                extra={'error': '未找到目标文字'},
            )
        
        ocr_results = self._ocr_recognizer.recognize(image=screenshot)
        
        for result in ocr_results:
            text = result.text
            for target_text in target_texts:
                if target_text in text:
                    x1, y1, x2, y2 = result.bbox
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    return DetectionResult(
                        method=RecognitionMethod.OCR,
                        success=True,
                        position=(center_x, center_y),
                        text=text,
                        bbox=(x1, y1, x2, y2),
                    )
        
        return DetectionResult(
            method=RecognitionMethod.OCR,
            success=False,
        )
    
    def _detect_with_hybrid(
        self,
        target: Union[str, List[str]],
        screenshot: Optional[Any] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        **kwargs,
    ) -> DetectionResult:
        """混合检测（先用 YOLO，再用模板匹配验证）"""
        yolo_result = self._detect_with_yolo(target, screenshot, region, **kwargs)
        
        if yolo_result.success:
            return yolo_result
        
        if isinstance(target, str) and os.path.exists(target):
            return self._detect_with_template(target, screenshot, region, **kwargs)
        
        return yolo_result


def init_recognizer(
    default_method: str = "SMART",
    yolo_model_path: Optional[str] = None,
    use_gpu: bool = True,
) -> UnifiedRecognizer:
    """
    初始化全局识别器
    
    参数:
        default_method: 默认方法 (SMART/TEMPLATE/YOLO/OCR/HYBRID)
        yolo_model_path: YOLO 模型路径
        use_gpu: 是否使用 GPU
    
    返回:
        UnifiedRecognizer
    """
    global _recognizer
    
    method_map = {
        "TEMPLATE": RecognitionMethod.TEMPLATE,
        "YOLO": RecognitionMethod.YOLO,
        "OCR": RecognitionMethod.OCR,
        "HYBRID": RecognitionMethod.HYBRID,
        "SMART": RecognitionMethod.SMART,
    }
    
    method = method_map.get(default_method.upper(), RecognitionMethod.SMART)
    
    _recognizer = UnifiedRecognizer(
        default_method=method,
        yolo_model_path=yolo_model_path,
        use_gpu=use_gpu,
    )
    
    return _recognizer


def get_recognizer() -> UnifiedRecognizer:
    """
    获取全局识别器实例
    
    返回:
        UnifiedRecognizer
    """
    global _recognizer
    
    if _recognizer is None:
        _recognizer = UnifiedRecognizer()
    
    return _recognizer


# ==================== 兼容现有接口 ====================


def find_image_on_screen(
    template_path: str,
    threshold: float = 0.8,
    screenshot: Optional[Any] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    method: str = "TEMPLATE",
    **kwargs,
) -> Optional[Tuple[int, int]]:
    """
    兼容现有接口的查找函数
    
    参数:
        template_path: 模板路径
        threshold: 阈值
        screenshot: 截图
        region: 区域
        method: 识别方法 (TEMPLATE/YOLO/OCR/HYBRID)
    
    返回:
        坐标或 None
    """
    recognizer = get_recognizer()
    
    method_map = {
        "TEMPLATE": RecognitionMethod.TEMPLATE,
        "YOLO": RecognitionMethod.YOLO,
        "OCR": RecognitionMethod.OCR,
        "HYBRID": RecognitionMethod.HYBRID,
    }
    
    result = recognizer.detect(
        target=template_path,
        method=method_map.get(method.upper(), RecognitionMethod.TEMPLATE),
        screenshot=screenshot,
        region=region,
        threshold=threshold,
        **kwargs,
    )
    
    return result.position if result.success else None


def find_all_images_on_screen(
    template_path: str,
    threshold: float = 0.8,
    screenshot: Optional[Any] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    method: str = "TEMPLATE",
    **kwargs,
) -> List[Tuple[int, int]]:
    """
    兼容现有接口的查找所有函数
    
    注意：YOLO/OCR 模式下此函数可能只返回一个结果
    """
    if method.upper() == "TEMPLATE" and HAS_TEMPLATE_MATCHER:
        return find_all_with_template(
            template_path=template_path,
            threshold=threshold,
            screenshot=screenshot,
            region=region,
        )
    
    position = find_image_on_screen(
        template_path=template_path,
        threshold=threshold,
        screenshot=screenshot,
        region=region,
        method=method,
        **kwargs,
    )
    
    return [position] if position else []
