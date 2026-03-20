# -*- encoding:utf-8 -*-
"""
检测状态机 - 管理图像检测的生命周期

状态：
- IDLE: 空闲
- DETECTING: 检测中
- EXECUTING: 执行脚本中
- PAUSED: 暂停
- STOPPED: 停止

使用统一识别器（YOLO+OCR 智能路由）替代传统 CV 模板匹配
"""
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger

from Util.UnifiedRecognizer import UnifiedRecognizer, RecognitionResult, RecognitionMethod


class DetectionState(Enum):
    """检测状态"""
    IDLE = auto()
    DETECTING = auto()
    EXECUTING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class DetectionContext:
    """检测上下文"""
    state: DetectionState = DetectionState.IDLE
    running: bool = False
    paused: bool = False
    trigger_images: List[str] = field(default_factory=list)
    trigger_script: str = ""
    icon_images: List[str] = field(default_factory=list)
    icon_positions: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    detection_count: int = 0
    execution_count: int = 0
    error_message: Optional[str] = None


class DetectionStateMachine:
    """
    检测状态机
    
    使用统一识别器（YOLO+OCR 智能路由），不再依赖传统 CV 模板匹配
    支持智能路由：imgsA/B → YOLO，imgsC/E/F/G → OCR
    
    使用示例:
    ```python
    detection_sm = DetectionStateMachine()
    
    # 配置检测目标
    detection_sm.set_trigger_config(
        trigger_images=['imgsA/trigger1.png', 'imgsC/trigger2.png'],
        trigger_script='script.txt',
        icon_images=['imgsA/icon1.png', 'imgsC/text1.png'],
        icon_positions={'imgsA/icon1.png': (100, 200)}
    )
    
    # 开始检测
    detection_sm.start_detection()
    
    # 检测循环
    while detection_sm.is_detecting():
        screenshot = take_screenshot()
        detection_sm.detect(screenshot)
    
    # 停止检测
    detection_sm.stop()
    ```
    """
    
    def __init__(self):
        self.ctx = DetectionContext()
        
        # 统一识别器（YOLO+OCR 智能路由）
        self.recognizer: Optional[UnifiedRecognizer] = None
        
        # 检测配置
        self.trigger_images: List[str] = []
        self.trigger_script: str = ""
        self.icon_images: List[str] = []
        self.icon_positions: Dict[str, Tuple[int, int]] = {}
        
        # 回调函数
        self.on_trigger_detected: Optional[Callable[[str, str], None]] = None  # (trigger_image, script_path)
        self.on_icon_detected: Optional[Callable[[str, Tuple[int, int]], None]] = None  # (icon_image, position)
        self.on_state_change: Optional[Callable[[DetectionState, DetectionState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_script_execution_finished: Optional[Callable[[], None]] = None
        
        logger.info('DetectionStateMachine initialized (using Unified Recognizer: YOLO+OCR)')
    
    def _init_recognizer(self):
        """初始化统一识别器"""
        if self.recognizer is None:
            self.recognizer = UnifiedRecognizer()
            logger.info('Unified Recognizer (YOLO+OCR) initialized')
    
    def set_trigger_config(
        self,
        trigger_images: List[str],
        trigger_script: str,
        icon_images: Optional[List[str]] = None,
        icon_positions: Optional[Dict[str, Tuple[int, int]]] = None,
    ):
        """
        设置检测配置
        
        :param trigger_images: 触发图列表
        :param trigger_script: 触发脚本路径
        :param icon_images: 图标列表
        :param icon_positions: 图标固定位置
        """
        self.trigger_images = trigger_images
        self.trigger_script = trigger_script
        self.icon_images = icon_images or []
        self.icon_positions = icon_positions or {}
        
        logger.info(f'Detection config set: {len(trigger_images)} triggers, {len(icon_images)} icons')
    
    def start_detection(self) -> bool:
        """开始检测"""
        if self.ctx.state != DetectionState.IDLE:
            self._log_error(f"当前状态 {self.ctx.state.name} 无法开始检测")
            return False
        
        old_state = self.ctx.state
        
        try:
            # 初始化识别器
            self._init_recognizer()
            
            # 更新上下文
            self.ctx.state = DetectionState.DETECTING
            self.ctx.running = True
            self.ctx.paused = False
            self.ctx.detection_count = 0
            self.ctx.execution_count = 0
            self.ctx.error_message = None
            
            logger.info(f'Started detection, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
        except Exception as e:
            self._log_error(f"开始检测失败：{e}")
            self.ctx.state = old_state
            return False
    
    def pause(self) -> bool:
        """暂停检测"""
        if self.ctx.state != DetectionState.DETECTING:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = DetectionState.PAUSED
            self.ctx.paused = True
            
            logger.info(f'Detection paused, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
        except Exception as e:
            self._log_error(f"暂停检测失败：{e}")
            return False
    
    def resume(self) -> bool:
        """恢复检测"""
        if self.ctx.state != DetectionState.PAUSED:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = DetectionState.DETECTING
            self.ctx.paused = False
            
            logger.info(f'Detection resumed, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
        except Exception as e:
            self._log_error(f"恢复检测失败：{e}")
            return False
    
    def stop(self) -> bool:
        """停止检测"""
        if self.ctx.state == DetectionState.STOPPED:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = DetectionState.STOPPED
            self.ctx.running = False
            self.ctx.paused = True
            
            logger.info(f'Detection stopped, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
        except Exception as e:
            self._log_error(f"停止检测失败：{e}")
            return False
    
    def detect(self, screenshot, capture_offset: Tuple[int, int] = (0, 0)) -> bool:
        """
        执行检测
        
        :param screenshot: 截图
        :param capture_offset: 截图偏移量 (x, y)
        :return: 是否检测到触发图
        """
        if self.ctx.state != DetectionState.DETECTING or self.ctx.paused:
            return False
        
        if not self.recognizer:
            self._log_error("统一识别器未初始化")
            return False
        
        try:
            self.ctx.detection_count += 1
            
            # 检测触发图
            for trigger_image in self.trigger_images:
                result = self.recognizer.detect(trigger_image, screenshot=screenshot)
                if result.success:
                    logger.info(f'Trigger detected: {trigger_image}')
                    self._handle_trigger_detected(trigger_image)
                    return True
            
            # 检测图标
            for icon_image in self.icon_images:
                result = self.recognizer.detect(icon_image, screenshot=screenshot)
                if result.success and result.position:
                    # 应用偏移量
                    x, y = result.position
                    adjusted_x = x + capture_offset[0]
                    adjusted_y = y + capture_offset[1]
                    adjusted_position = (adjusted_x, adjusted_y)
                    
                    logger.info(f'Icon detected: {icon_image} at {adjusted_position}')
                    self._handle_icon_detected(icon_image, adjusted_position)
            
            return False
        except Exception as e:
            self._log_error(f"检测失败：{e}")
            return False
    
    def script_execution_finished(self):
        """脚本执行完成回调"""
        if self.ctx.state == DetectionState.EXECUTING:
            old_state = self.ctx.state
            self.ctx.state = DetectionState.DETECTING
            
            logger.info(f'Script execution finished, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            if self.on_script_execution_finished:
                try:
                    self.on_script_execution_finished()
                except Exception as e:
                    self._log_error(f"脚本执行完成回调失败：{e}")
    
    def _handle_trigger_detected(self, trigger_image: str):
        """处理触发图检测"""
        if self.ctx.state != DetectionState.DETECTING:
            return
        
        old_state = self.ctx.state
        self.ctx.state = DetectionState.EXECUTING
        self.ctx.execution_count += 1
        
        logger.info(f'Trigger processing, state: {old_state.name} → {self.ctx.state.name}')
        self._notify_state_change(old_state, self.ctx.state)
        
        if self.on_trigger_detected:
            try:
                self.on_trigger_detected(trigger_image, self.trigger_script)
            except Exception as e:
                self._log_error(f"触发图检测回调失败：{e}")
    
    def _handle_icon_detected(self, icon_image: str, position: Tuple[int, int]):
        """处理图标检测"""
        if self.ctx.state != DetectionState.DETECTING:
            return
        
        if self.on_icon_detected:
            try:
                self.on_icon_detected(icon_image, position)
            except Exception as e:
                self._log_error(f"图标检测回调失败：{e}")
    
    def is_detecting(self) -> bool:
        """是否正在检测"""
        return self.ctx.state == DetectionState.DETECTING and self.ctx.running and not self.ctx.paused
    
    def is_executing(self) -> bool:
        """是否正在执行脚本"""
        return self.ctx.state == DetectionState.EXECUTING
    
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self.ctx.state == DetectionState.PAUSED
    
    def is_stopped(self) -> bool:
        """是否已停止"""
        return self.ctx.state == DetectionState.STOPPED
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            'state': self.ctx.state.name,
            'running': self.ctx.running,
            'paused': self.ctx.paused,
            'detection_count': self.ctx.detection_count,
            'execution_count': self.ctx.execution_count,
            'error': self.ctx.error_message,
        }
    
    def _notify_state_change(self, old_state: DetectionState, new_state: DetectionState):
        """通知状态变化"""
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                self._log_error(f"状态变化回调失败：{e}")
    
    def _log_error(self, message: str):
        """记录错误"""
        logger.warning(f'[Detection] {message}')
        self.ctx.error_message = message
        if self.on_error:
            try:
                self.on_error(message)
            except Exception as e:
                logger.error(f"错误回调失败：{e}")


# 导出
__all__ = [
    'DetectionState',
    'DetectionContext',
    'DetectionStateMachine',
]
