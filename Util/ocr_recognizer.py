# -*- encoding:utf-8 -*-
"""
OCR 文字识别器

支持两种 OCR 引擎：
1. PaddleOCR（推荐，中文识别好）
2. EasyOCR（备选，多语言支持好）

继承自 BaseRecognizer，提供统一的识别接口
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum, auto

import numpy as np
from loguru import logger

from .UnifiedRecognizer import BaseRecognizer, RecognitionMethod, RecognitionResult


class OCREngine(Enum):
    """OCR 引擎类型"""
    PADDLE = auto()
    EASYOCR = auto()


@dataclass
class OCRData:
    """OCR 识别结果（内部格式）"""
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)


class OCRRecognizer(BaseRecognizer):
    """
    OCR 文字识别器
    
    使用示例：
    ```python
    ocr = OCRRecognizer()
    
    # 识别所有文字
    result = ocr.detect('开始游戏', screenshot)
    if result.success:
        x, y = result.position
        click(x, y)
    
    # 查找特定文字
    result = ocr.find_text(screenshot, '设置')
    ```
    """
    
    def __init__(
        self,
        engine: OCREngine = OCREngine.PADDLE,
        use_gpu: bool = True,
        languages: Optional[List[str]] = None,
    ):
        """
        初始化 OCR 识别器
        
        :param engine: OCR 引擎类型
        :param use_gpu: 是否使用 GPU
        :param languages: 语言列表
        """
        super().__init__(use_gpu)
        
        self.engine = engine
        self.use_gpu = use_gpu
        self.languages = languages or self._get_default_languages(engine)
        
        self._paddle_reader = None
        self._easyocr_reader = None
        
        # 立即初始化引擎
        self._init_engine()
        self._initialized = True  # 标记已初始化
        
        # 检查是否初始化成功
        if self._paddle_reader is None and self._easyocr_reader is None:
            logger.error('OCR 引擎初始化失败，所有引擎都不可用')
    
    def _get_default_languages(self, engine: OCREngine) -> List[str]:
        """获取默认语言列表"""
        if engine == OCREngine.PADDLE:
            return ['ch']  # PaddleOCR: ch=中英文
        else:
            return ['en']  # EasyOCR: en=英文 (中文支持有问题)
    
    def _init_engine(self):
        """初始化 OCR 引擎"""
        # 尝试 PaddleOCR
        self._init_paddleocr()
        
        # 如果 PaddleOCR 失败，尝试 EasyOCR
        if self._paddle_reader is None:
            logger.info('PaddleOCR 初始化失败，尝试 EasyOCR')
            self.engine = OCREngine.EASYOCR
            # EasyOCR 需要不同的语言参数
            self.languages = ['en']  # EasyOCR 只使用英文
            self._init_easyocr()
    
    def _init_paddleocr(self):
        """初始化 PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            
            logger.info('初始化 PaddleOCR...')
            
            # 尝试不同的参数组合，适配不同版本的 PaddleOCR
            try:
                # 新版 PaddleOCR (无 show_log 参数)
                self._paddle_reader = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.languages[0] if self.languages else 'ch',
                )
            except TypeError as e:
                if 'show_log' in str(e):
                    # 旧版 PaddleOCR (需要 show_log 参数)
                    try:
                        self._paddle_reader = PaddleOCR(
                            use_angle_cls=True,
                            lang=self.languages[0] if self.languages else 'ch',
                            use_gpu=self.use_gpu,
                            show_log=False,
                        )
                    except TypeError:
                        # 更旧的版本 (无 use_gpu 参数)
                        self._paddle_reader = PaddleOCR(
                            use_angle_cls=True,
                            lang=self.languages[0] if self.languages else 'ch',
                            show_log=False,
                        )
                else:
                    raise
            
            logger.info('PaddleOCR 初始化完成')
            
        except ImportError:
            logger.warning('PaddleOCR 未安装')
            self._paddle_reader = None
        except Exception as e:
            logger.error(f'PaddleOCR 初始化失败：{e}')
            self._paddle_reader = None
    
    def _init_easyocr(self):
        """初始化 EasyOCR"""
        try:
            import easyocr
            
            logger.info('初始化 EasyOCR...')
            
            self._easyocr_reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                verbose=False,
            )
            
            logger.info('EasyOCR 初始化完成')
            
        except ImportError:
            logger.error('EasyOCR 未安装，请运行：pip install easyocr paddleocr')
            self._easyocr_reader = None
        except Exception as e:
            logger.error(f'EasyOCR 初始化失败：{e}')
            self._easyocr_reader = None
    
    def _recognize(
        self,
        image: np.ndarray,
        target: Any,
    ) -> RecognitionResult:
        """
        执行 OCR 识别
        
        :param image: 图像数组
        :param target: 识别目标（文字或文字列表）
        :return: 识别结果
        """
        # 确保引擎已初始化
        if self.engine == OCREngine.PADDLE and self._paddle_reader is None:
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.OCR,
                error='PaddleOCR 未初始化',
            )
        elif self.engine == OCREngine.EASYOCR and self._easyocr_reader is None:
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.OCR,
                error='EasyOCR 未初始化',
            )
        
        # 处理目标
        target_texts = []
        if isinstance(target, str):
            target_texts.append(target)
        elif isinstance(target, list):
            target_texts = target
        else:
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.OCR,
                error=f'不支持的目标类型：{type(target)}',
            )
        
        # 执行 OCR 识别
        try:
            if self.engine == OCREngine.PADDLE:
                ocr_results = self._recognize_with_paddle(image)
            else:
                ocr_results = self._recognize_with_easyocr(image)
            
            if not ocr_results:
                return RecognitionResult(
                    success=False,
                    method=RecognitionMethod.OCR,
                )
            
            # 查找匹配的文字
            for ocr_result in ocr_results:
                text = ocr_result.text
                for target_text in target_texts:
                    if target_text in text:
                        logger.debug(f'OCR 匹配到文字：{target_text} in {text}')
                        
                        # 转换为统一格式
                        detection = {
                            'text': text,
                            'confidence': ocr_result.confidence,
                            'bbox': ocr_result.bbox,
                        }
                        
                        return self._postprocess_result(detection, RecognitionMethod.OCR)
            
            # 未找到匹配
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.OCR,
            )
            
        except Exception as e:
            logger.error(f'OCR 识别失败：{e}')
            return RecognitionResult(
                success=False,
                method=RecognitionMethod.OCR,
                error=str(e),
            )
    
    def _recognize_with_paddle(self, image: np.ndarray) -> List[OCRData]:
        """用 PaddleOCR 识别"""
        try:
            result = self._paddle_reader.ocr(image, cls=True)
            
            if not result or not result[0]:
                return []
            
            ocr_results = []
            
            for line in result[0]:
                if not line:
                    continue
                
                box = line[0]
                text_info = line[1]
                
                text = text_info[0]
                confidence = text_info[1]
                
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                
                x1 = int(min(x_coords))
                y1 = int(min(y_coords))
                x2 = int(max(x_coords))
                y2 = int(max(y_coords))
                
                ocr_results.append(OCRData(
                    text=text,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                ))
            
            return ocr_results
            
        except Exception as e:
            logger.error(f'PaddleOCR 识别失败：{e}')
            return []
    
    def _recognize_with_easyocr(self, image: np.ndarray) -> List[OCRData]:
        """用 EasyOCR 识别"""
        try:
            result = self._easyocr_reader.readtext(image)
            
            ocr_results = []
            
            for detection in result:
                box = detection[0]
                text = detection[1]
                confidence = detection[2]
                
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                
                x1 = int(min(x_coords))
                y1 = int(min(y_coords))
                x2 = int(max(x_coords))
                y2 = int(max(y_coords))
                
                ocr_results.append(OCRData(
                    text=text,
                    confidence=confidence,
                    bbox=(x1, y1, x2, y2),
                ))
            
            return ocr_results
            
        except Exception as e:
            logger.error(f'EasyOCR 识别失败：{e}')
            return []
    
    def _get_method(self) -> RecognitionMethod:
        """获取当前识别方法"""
        return RecognitionMethod.OCR
    
    def recognize_all(
        self,
        image: np.ndarray,
    ) -> List[OCRData]:
        """
        识别图像中的所有文字
        
        :param image: 图像数组
        :return: OCR 结果列表
        """
        if self.engine == OCREngine.PADDLE:
            return self._recognize_with_paddle(image)
        else:
            return self._recognize_with_easyocr(image)
    
    def find_text(
        self,
        image: np.ndarray,
        target_text: str,
        min_confidence: float = 0.5,
    ) -> Optional[RecognitionResult]:
        """
        查找特定文字
        
        :param image: 图像数组
        :param target_text: 目标文字
        :param min_confidence: 最低置信度
        :return: 识别结果或 None
        """
        ocr_results = self.recognize_all(image)
        
        for result in ocr_results:
            if result.confidence < min_confidence:
                continue
            
            if target_text in result.text:
                detection = {
                    'text': result.text,
                    'confidence': result.confidence,
                    'bbox': result.bbox,
                }
                return self._postprocess_result(detection, RecognitionMethod.OCR)
        
        return None


# 便捷函数
def create_ocr_recognizer(
    engine: str = "PADDLE",
    use_gpu: bool = True,
) -> OCRRecognizer:
    """
    创建 OCR 识别器
    
    :param engine: 引擎类型 (PADDLE/EASYOCR)
    :param use_gpu: 是否使用 GPU
    :return: OCRRecognizer 实例
    """
    engine_map = {
        "PADDLE": OCREngine.PADDLE,
        "EASYOCR": OCREngine.EASYOCR,
    }
    
    engine_type = engine_map.get(engine.upper(), OCREngine.PADDLE)
    
    return OCRRecognizer(
        engine=engine_type,
        use_gpu=use_gpu,
    )


# 导出
__all__ = [
    'OCREngine',
    'OCRData',
    'OCRRecognizer',
    'create_ocr_recognizer',
]
