# -*- encoding:utf-8 -*-
"""
检测状态机 - 管理图像识别检测的状态

状态：
- IDLE: 空闲
- DETECTING: 检测中
- EXECUTING: 执行脚本中（检测到触发图）
- PAUSED: 暂停
- STOPPED: 停止

状态转换：
IDLE → DETECTING (开始检测)
DETECTING → EXECUTING (检测到触发图)
EXECUTING → DETECTING (脚本执行完毕)
DETECTING → PAUSED (暂停检测)
DETECTING → IDLE (停止检测)
PAUSED → DETECTING (恢复检测)
ANY → STOPPED (停止)
"""
from enum import Enum, auto
from typing import Optional, Callable, List, Tuple, Any
from dataclasses import dataclass
import time
from loguru import logger


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
    
    # 检测相关
    detection_count: int = 0
    trigger_count: int = 0
    last_trigger_time: float = 0.0
    
    # 当前触发信息
    current_trigger_image: Optional[str] = None
    current_script_path: Optional[str] = None
    
    # 配置
    check_interval: float = 0.5
    match_threshold: float = 0.7


class DetectionStateMachine:
    """
    检测状态机
    
    使用示例:
    ```python
    detection_sm = DetectionStateMachine()
    
    # 开始检测
    detection_sm.start_detection()
    
    # 每帧调用
    screenshot = take_screenshot()
    detection_sm.detect(screenshot)
    
    # 暂停检测
    detection_sm.pause()
    
    # 恢复检测
    detection_sm.resume()
    
    # 停止检测
    detection_sm.stop()
    ```
    """
    
    def __init__(self):
        self.ctx = DetectionContext()
        
        # 回调函数
        self.on_trigger_detected: Optional[Callable[[str, str], None]] = None
        self.on_icon_detected: Optional[Callable[[str, Tuple[int, int]], None]] = None
        self.on_state_change: Optional[Callable[[DetectionState, DetectionState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 检测器引用（由外部注入）
        self.detector: Optional[Any] = None
        
        # 触发配置
        self.trigger_images: List[str] = []
        self.trigger_script: str = ""
        self.icon_images: List[str] = []
        self.icon_positions: dict = {}
        
        logger.info('DetectionStateMachine initialized')
    
    def set_detector(self, detector):
        """设置图像检测器"""
        self.detector = detector
        logger.debug('Detector set')
    
    def set_trigger_config(self, trigger_images: List[str], trigger_script: str,
                           icon_images: List[str] = None, icon_positions: dict = None):
        """设置触发配置"""
        self.trigger_images = trigger_images
        self.trigger_script = trigger_script
        self.icon_images = icon_images or []
        self.icon_positions = icon_positions or {}
        logger.debug(f'Trigger config set: {len(trigger_images)} trigger images')
    
    def start_detection(self) -> bool:
        """开始检测"""
        if self.ctx.state != DetectionState.IDLE:
            self._log_error(f"当前状态 {self.ctx.state.name} 无法开始检测")
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = DetectionState.DETECTING
            self.ctx.running = True
            self.ctx.paused = False
            self.ctx.detection_count = 0
            self.ctx.trigger_count = 0
            self.ctx.last_trigger_time = 0.0
            
            logger.info(f'Started detection, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"开始检测失败：{e}")
            self.ctx.state = old_state
            return False
    
    def pause(self) -> bool:
        """暂停检测"""
        if not self.ctx.running or self.ctx.paused:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.paused = True
            
            logger.info(f'Detection paused, state: {old_state.name} → PAUSED')
            return True
            
        except Exception as e:
            self._log_error(f"暂停检测失败：{e}")
            return False
    
    def resume(self) -> bool:
        """恢复检测"""
        if not self.ctx.paused or self.ctx.state == DetectionState.STOPPED:
            return False
        
        try:
            self.ctx.paused = False
            
            logger.info('Detection resumed')
            return True
            
        except Exception as e:
            self._log_error(f"恢复检测失败：{e}")
            return False
    
    def stop(self) -> bool:
        """停止检测"""
        if self.ctx.state == DetectionState.IDLE or self.ctx.state == DetectionState.STOPPED:
            return False
        
        old_state = self.ctx.state
        
        try:
            # 重置状态
            self.ctx.state = DetectionState.IDLE
            self.ctx.running = False
            self.ctx.paused = False
            
            logger.info(f'Stopped detection, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"停止检测失败：{e}")
            return False
    
    def stop_all(self) -> bool:
        """强制停止所有检测"""
        old_state = self.ctx.state
        
        try:
            # 转换到停止状态
            self.ctx.state = DetectionState.STOPPED
            self.ctx.running = False
            self.ctx.paused = False
            
            logger.info(f'Stopped all detection, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"强制停止检测失败：{e}")
            return False
    
    def detect(self, screenshot, capture_offset: Tuple[int, int] = (0, 0)) -> bool:
        """
        执行一次检测
        
        :param screenshot: 屏幕截图
        :param capture_offset: 截图偏移
        :return: 是否检测到触发
        """
        if self.ctx.state != DetectionState.DETECTING or self.ctx.paused:
            return False
        
        if not self.detector:
            self._log_error("检测器未设置")
            return False
        
        try:
            self.ctx.detection_count += 1
            
            # 检测触发图
            for trigger_image in self.trigger_images:
                if self.detector.detect_single_image(trigger_image, screenshot, capture_offset):
                    logger.info(f'Trigger detected: {trigger_image}')
                    self._handle_trigger_detected(trigger_image)
                    return True
            
            # 检测图标
            for icon_image in self.icon_images:
                position = self.detector.detect_single_image_with_pos(icon_image, screenshot, capture_offset)
                if position:
                    logger.info(f'Icon detected: {icon_image} at {position}')
                    self._handle_icon_detected(icon_image, position)
            
            return False
            
        except Exception as e:
            self._log_error(f"检测失败：{e}")
            return False
    
    def script_execution_finished(self) -> bool:
        """通知脚本执行完毕"""
        if self.ctx.state != DetectionState.EXECUTING:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = DetectionState.DETECTING
            
            logger.info(f'Script execution finished, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"脚本执行完毕处理失败：{e}")
            return False
    
    def is_detecting(self) -> bool:
        """检查是否正在检测"""
        return self.ctx.state == DetectionState.DETECTING and not self.ctx.paused
    
    def is_executing(self) -> bool:
        """检查是否正在执行脚本"""
        return self.ctx.state == DetectionState.EXECUTING
    
    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            'state': self.ctx.state.name,
            'running': self.ctx.running,
            'paused': self.ctx.paused,
            'detection_count': self.ctx.detection_count,
            'trigger_count': self.ctx.trigger_count,
        }
    
    def _handle_trigger_detected(self, trigger_image: str):
        """处理触发图检测"""
        self.ctx.current_trigger_image = trigger_image
        self.ctx.current_script_path = self.trigger_script
        self.ctx.trigger_count += 1
        self.ctx.last_trigger_time = time.time()
        
        # 转换到执行状态
        old_state = self.ctx.state
        self.ctx.state = DetectionState.EXECUTING
        
        logger.info(f'Trigger detected: {trigger_image}, executing script: {self.trigger_script}')
        self._notify_state_change(old_state, self.ctx.state)
        
        # 触发回调
        if self.on_trigger_detected:
            self.on_trigger_detected(trigger_image, self.trigger_script)
    
    def _handle_icon_detected(self, icon_image: str, position: Tuple[int, int]):
        """处理图标检测"""
        # 获取点击位置
        click_position = self.icon_positions.get(icon_image, position)
        
        logger.info(f'Icon detected: {icon_image}, clicking at {click_position}')
        
        # 触发回调
        if self.on_icon_detected:
            self.on_icon_detected(icon_image, click_position)
    
    def _notify_state_change(self, old_state: DetectionState, new_state: DetectionState):
        """通知状态变化"""
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state)
            except Exception as e:
                self._log_error(f"状态变化回调失败：{e}")
    
    def _log_error(self, message: str):
        """记录错误"""
        logger.warning(message)
        if self.on_error:
            try:
                self.on_error(message)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")


# 导出
__all__ = [
    'DetectionState',
    'DetectionContext',
    'DetectionStateMachine',
]
