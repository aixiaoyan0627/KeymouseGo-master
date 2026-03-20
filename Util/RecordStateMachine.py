# -*- encoding:utf-8 -*-
"""
录制状态机 - 管理录制和回放的状态

状态：
- IDLE: 空闲
- RECORDING: 录制中
- PLAYING: 回放中
- PAUSED: 暂停
- STOPPED: 停止

状态转换：
IDLE → RECORDING (开始录制)
IDLE → PLAYING (开始回放)
RECORDING → PAUSED (暂停录制)
RECORDING → IDLE (停止录制)
PLAYING → PAUSED (暂停回放)
PLAYING → IDLE (停止回放)
PAUSED → RECORDING (恢复录制)
PAUSED → PLAYING (恢复回放)
ANY → STOPPED (停止)
"""
from enum import Enum, auto
from typing import Optional, Callable, List, Any
from dataclasses import dataclass
import time
from loguru import logger

from Event import ScriptEvent


class RecordState(Enum):
    """录制状态"""
    IDLE = auto()
    RECORDING = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class RecordContext:
    """录制上下文"""
    state: RecordState = RecordState.IDLE
    running: bool = False
    paused: bool = False
    
    # 录制相关
    recorded_events: List[ScriptEvent] = None
    record_start_time: float = 0.0
    event_count: int = 0
    
    # 回放相关
    playing_events: List[ScriptEvent] = None
    play_start_time: float = 0.0
    current_event_index: int = 0
    
    # 配置
    use_relative_coords: bool = True
    game_window_title: str = '大航海时代：传说'


class RecordStateMachine:
    """
    录制状态机
    
    使用示例:
    ```python
    record_sm = RecordStateMachine()
    
    # 开始录制
    record_sm.start_recording()
    
    # 暂停录制
    record_sm.pause()
    
    # 恢复录制
    record_sm.resume()
    
    # 停止录制
    record_sm.stop()
    
    # 开始回放
    record_sm.start_playing(events)
    ```
    """
    
    def __init__(self):
        self.ctx = RecordContext()
        
        # 回调函数
        self.on_event_recorded: Optional[Callable[[ScriptEvent], None]] = None
        self.on_playback_finished: Optional[Callable[[], None]] = None
        self.on_state_change: Optional[Callable[[RecordState, RecordState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 录制器引用（由外部注入）
        self.recorder: Optional[Any] = None
        self.player: Optional[Any] = None
        
        logger.info('RecordStateMachine initialized')
    
    def set_recorder_player(self, recorder=None, player=None):
        """设置录制器和回放器"""
        self.recorder = recorder
        self.player = player
        logger.debug('Recorder and player set')
    
    def start_recording(self) -> bool:
        """开始录制"""
        if self.ctx.state != RecordState.IDLE:
            self._log_error(f"当前状态 {self.ctx.state.name} 无法开始录制")
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = RecordState.RECORDING
            self.ctx.running = True
            self.ctx.paused = False
            self.ctx.recorded_events = []
            self.ctx.record_start_time = time.time()
            self.ctx.event_count = 0
            
            logger.info(f'Started recording, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"开始录制失败：{e}")
            self.ctx.state = old_state
            return False
    
    def start_playing(self, events: List[ScriptEvent]) -> bool:
        """开始回放"""
        if self.ctx.state != RecordState.IDLE:
            self._log_error(f"当前状态 {self.ctx.state.name} 无法开始回放")
            return False
        
        if not events:
            self._log_error("回放事件列表为空")
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.state = RecordState.PLAYING
            self.ctx.running = True
            self.ctx.paused = False
            self.ctx.playing_events = events
            self.ctx.play_start_time = time.time()
            self.ctx.current_event_index = 0
            
            logger.info(f'Started playing {len(events)} events, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"开始回放失败：{e}")
            self.ctx.state = old_state
            return False
    
    def pause(self) -> bool:
        """暂停（录制或回放）"""
        if not self.ctx.running or self.ctx.paused:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.paused = True
            
            if self.ctx.state == RecordState.RECORDING:
                logger.info('Recording paused')
            elif self.ctx.state == RecordState.PLAYING:
                logger.info('Playing paused')
            
            return True
            
        except Exception as e:
            self._log_error(f"暂停失败：{e}")
            return False
    
    def resume(self) -> bool:
        """恢复（录制或回放）"""
        if not self.ctx.paused:
            return False
        
        old_state = self.ctx.state
        
        try:
            self.ctx.paused = False
            
            if self.ctx.state == RecordState.RECORDING:
                logger.info('Recording resumed')
            elif self.ctx.state == RecordState.PLAYING:
                logger.info('Playing resumed')
            
            return True
            
        except Exception as e:
            self._log_error(f"恢复失败：{e}")
            return False
    
    def stop(self) -> bool:
        """停止（录制或回放）"""
        if self.ctx.state == RecordState.IDLE or self.ctx.state == RecordState.STOPPED:
            return False
        
        old_state = self.ctx.state
        
        try:
            # 停止录制器或回放器
            if self.ctx.state == RecordState.RECORDING and self.recorder:
                try:
                    self.recorder.stop()
                except Exception as e:
                    logger.warning(f"停止录制器失败：{e}")
            
            elif self.ctx.state == RecordState.PLAYING and self.player:
                try:
                    self.player.stop()
                except Exception as e:
                    logger.warning(f"停止回放器失败：{e}")
            
            # 重置状态
            self.ctx.state = RecordState.IDLE
            self.ctx.running = False
            self.ctx.paused = False
            
            logger.info(f'Stopped, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"停止失败：{e}")
            return False
    
    def stop_all(self) -> bool:
        """强制停止所有操作"""
        old_state = self.ctx.state
        
        try:
            # 强制停止
            if self.recorder:
                try:
                    self.recorder.stop()
                except:
                    pass
            
            if self.player:
                try:
                    self.player.stop()
                except:
                    pass
            
            # 转换到停止状态
            self.ctx.state = RecordState.STOPPED
            self.ctx.running = False
            self.ctx.paused = False
            
            logger.info(f'Stopped all, state: {old_state.name} → {self.ctx.state.name}')
            self._notify_state_change(old_state, self.ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"强制停止失败：{e}")
            return False
    
    def record_event(self, event: ScriptEvent) -> bool:
        """
        录制一个事件
        
        :param event: 要录制的事件
        :return: 是否录制成功
        """
        if self.ctx.state != RecordState.RECORDING or self.ctx.paused:
            return False
        
        try:
            self.ctx.recorded_events.append(event)
            self.ctx.event_count += 1
            
            if self.on_event_recorded:
                self.on_event_recorded(event)
            
            return True
            
        except Exception as e:
            self._log_error(f"录制事件失败：{e}")
            return False
    
    def get_next_event(self) -> Optional[ScriptEvent]:
        """
        获取下一个要回放的事件
        
        :return: 下一个事件，如果没有则返回 None
        """
        if self.ctx.state != RecordState.PLAYING or self.ctx.paused:
            return None
        
        if self.ctx.current_event_index >= len(self.ctx.playing_events):
            return None
        
        try:
            event = self.ctx.playing_events[self.ctx.current_event_index]
            self.ctx.current_event_index += 1
            return event
            
        except Exception as e:
            self._log_error(f"获取下一个事件失败：{e}")
            return None
    
    def is_recording(self) -> bool:
        """检查是否正在录制"""
        return self.ctx.state == RecordState.RECORDING and not self.ctx.paused
    
    def is_playing(self) -> bool:
        """检查是否正在回放"""
        return self.ctx.state == RecordState.PLAYING and not self.ctx.paused
    
    def is_paused(self) -> bool:
        """检查是否暂停"""
        return self.ctx.paused
    
    def get_recorded_events(self) -> List[ScriptEvent]:
        """获取已录制的事件列表"""
        return self.ctx.recorded_events or []
    
    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            'state': self.ctx.state.name,
            'running': self.ctx.running,
            'paused': self.ctx.paused,
            'event_count': self.ctx.event_count,
            'current_event_index': self.ctx.current_event_index,
        }
    
    def _notify_state_change(self, old_state: RecordState, new_state: RecordState):
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
    'RecordState',
    'RecordContext',
    'RecordStateMachine',
]
