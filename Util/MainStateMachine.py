# -*- encoding:utf-8 -*-
"""
统一主状态机 - 分层架构的顶层协调器

负责：
1. 协调所有子状态机（录制、检测、远洋、插件）
2. 处理模块间的冲突
3. 全局事件分发
4. 提供统一的状态查询接口

架构：
MainStateMachine (统一协调)
├── RecordStateMachine (录制)
├── DetectionStateMachine (检测)
├── VoyageStateMachine (远洋 - 已有)
└── PluginStateMachine (插件)
"""
from enum import Enum, auto
from typing import Optional, Callable, Any
from dataclasses import dataclass
from loguru import logger


class MainState(Enum):
    """主状态机状态"""
    IDLE = auto()           # 空闲 - 可以启动任何模块
    RECORDING = auto()      # 录制中 - 不能启动检测/远洋
    DETECTING = auto()      # 检测中 - 不能启动录制/远洋
    VOYAGE = auto()         # 远洋自动化 - 不能启动录制/检测
    PLUGIN = auto()         # 插件运行中 - 不能启动其他模块
    STOPPED = auto()        # 停止 - 无法转换到其他状态


@dataclass
class ModuleStatus:
    """模块状态信息"""
    name: str
    running: bool = False
    paused: bool = False
    error: Optional[str] = None


class MainStateMachine:
    """
    统一主状态机
    
    使用示例:
    ```python
    main_sm = MainStateMachine()
    
    # 启动录制
    if main_sm.can_start_module('record'):
        main_sm.start_module('record')
        record_sm.start()
    
    # 尝试启动检测（会失败，因为录制中）
    if not main_sm.can_start_module('detection'):
        print("录制中，无法启动检测")
    
    # 停止录制
    main_sm.stop_module('record')
    record_sm.stop()
    ```
    """
    
    def __init__(self):
        self.state = MainState.IDLE
        self.previous_state = MainState.IDLE
        
        # 子状态机（初始化为 None，由外部注入）
        self.record_sm: Optional[Any] = None
        self.detection_sm: Optional[Any] = None
        self.voyage_sm: Optional[Any] = None  # ✅ 已有的远洋状态机
        self.plugin_sm: Optional[Any] = None
        
        # 模块状态
        self.modules = {
            'record': ModuleStatus(name='record'),
            'detection': ModuleStatus(name='detection'),
            'voyage': ModuleStatus(name='voyage'),
            'plugin': ModuleStatus(name='plugin'),
        }
        
        # 回调函数
        self.on_state_change: Optional[Callable[[MainState, MainState], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        logger.info('MainStateMachine initialized')
    
    def set_sub_state_machines(self, record_sm=None, detection_sm=None, 
                                voyage_sm=None, plugin_sm=None):
        """设置子状态机引用"""
        self.record_sm = record_sm
        self.detection_sm = detection_sm
        self.voyage_sm = voyage_sm
        self.plugin_sm = plugin_sm
        logger.debug('Sub-state machines set')
    
    def can_start_module(self, module_name: str) -> bool:
        """
        检查是否可以启动指定模块
        
        :param module_name: 模块名称 ('record', 'detection', 'voyage', 'plugin')
        :return: 是否可以启动
        """
        if self.state == MainState.STOPPED:
            self._log_error(f"系统已停止，无法启动 {module_name}")
            return False
        
        if self.state == MainState.IDLE:
            return True
        
        # 检查当前运行的模块
        if self.state == MainState.RECORDING and module_name != 'record':
            self._log_error(f"录制中，无法启动 {module_name}")
            return False
        elif self.state == MainState.DETECTING and module_name != 'detection':
            self._log_error(f"检测中，无法启动 {module_name}")
            return False
        elif self.state == MainState.VOYAGE and module_name not in ['voyage', 'plugin']:
            self._log_error(f"远洋自动化中，无法启动 {module_name}")
            return False
        elif self.state == MainState.PLUGIN and module_name != 'plugin':
            self._log_error(f"插件运行中，无法启动 {module_name}")
            return False
        
        return True
    
    def start_module(self, module_name: str) -> bool:
        """
        启动指定模块
        
        :param module_name: 模块名称
        :return: 是否启动成功
        """
        if not self.can_start_module(module_name):
            return False
        
        old_state = self.state
        
        try:
            # 转换状态
            if module_name == 'record':
                self.state = MainState.RECORDING
            elif module_name == 'detection':
                self.state = MainState.DETECTING
            elif module_name == 'voyage':
                self.state = MainState.VOYAGE
            elif module_name == 'plugin':
                self.state = MainState.PLUGIN
            else:
                self._log_error(f"未知模块：{module_name}")
                return False
            
            # 更新模块状态
            self.modules[module_name].running = True
            
            logger.info(f'Module {module_name} started, state: {old_state.name} → {self.state.name}')
            self._notify_state_change(old_state, self.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"启动模块 {module_name} 失败：{e}")
            self.state = old_state
            return False
    
    def stop_module(self, module_name: str) -> bool:
        """
        停止指定模块
        
        :param module_name: 模块名称
        :return: 是否停止成功
        """
        if self.state == MainState.STOPPED:
            return False
        
        # 检查是否是当前运行的模块
        current_module = self._get_current_module()
        if current_module != module_name:
            self._log_error(f"模块 {module_name} 未运行")
            return False
        
        old_state = self.state
        
        try:
            # 停止子状态机
            if module_name == 'record' and self.record_sm:
                self.record_sm.stop()
            elif module_name == 'detection' and self.detection_sm:
                self.detection_sm.stop()
            elif module_name == 'voyage' and self.voyage_sm:
                self.voyage_sm.stop()
            elif module_name == 'plugin' and self.plugin_sm:
                self.plugin_sm.stop()
            
            # 更新状态
            self.state = MainState.IDLE
            self.modules[module_name].running = False
            
            logger.info(f'Module {module_name} stopped, state: {old_state.name} → {self.state.name}')
            self._notify_state_change(old_state, self.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"停止模块 {module_name} 失败：{e}")
            return False
    
    def stop_all(self) -> bool:
        """
        停止所有模块
        
        :return: 是否停止成功
        """
        if self.state == MainState.STOPPED:
            return False
        
        old_state = self.state
        
        try:
            # 停止所有子状态机
            if self.record_sm:
                self.record_sm.stop()
            if self.detection_sm:
                self.detection_sm.stop()
            if self.voyage_sm:
                self.voyage_sm.stop()
            if self.plugin_sm:
                self.plugin_sm.stop()
            
            # 更新所有模块状态
            for module in self.modules.values():
                module.running = False
                module.paused = False
            
            # 转换到停止状态
            self.state = MainState.STOPPED
            
            logger.info(f'All modules stopped, state: {old_state.name} → {self.state.name}')
            self._notify_state_change(old_state, self.state)
            
            return True
            
        except Exception as e:
            self._log_error(f"停止所有模块失败：{e}")
            return False
    
    def pause_module(self, module_name: str) -> bool:
        """暂停指定模块"""
        if not self.modules[module_name].running:
            return False
        
        try:
            if module_name == 'record' and self.record_sm and hasattr(self.record_sm, 'pause'):
                self.record_sm.pause()
                self.modules[module_name].paused = True
                logger.info(f'Module {module_name} paused')
                return True
            elif module_name == 'detection' and self.detection_sm and hasattr(self.detection_sm, 'pause'):
                self.detection_sm.pause()
                self.modules[module_name].paused = True
                logger.info(f'Module {module_name} paused')
                return True
            # ... 其他模块
            
            return False
        except Exception as e:
            self._log_error(f"暂停模块 {module_name} 失败：{e}")
            return False
    
    def resume_module(self, module_name: str) -> bool:
        """恢复指定模块"""
        if not self.modules[module_name].paused:
            return False
        
        try:
            if module_name == 'record' and self.record_sm and hasattr(self.record_sm, 'resume'):
                self.record_sm.resume()
                self.modules[module_name].paused = False
                logger.info(f'Module {module_name} resumed')
                return True
            elif module_name == 'detection' and self.detection_sm and hasattr(self.detection_sm, 'resume'):
                self.detection_sm.resume()
                self.modules[module_name].paused = False
                logger.info(f'Module {module_name} resumed')
                return True
            # ... 其他模块
            
            return False
        except Exception as e:
            self._log_error(f"恢复模块 {module_name} 失败：{e}")
            return False
    
    def get_current_module(self) -> Optional[str]:
        """获取当前运行的模块名称"""
        return self._get_current_module()
    
    def get_status(self) -> dict:
        """获取所有模块的状态"""
        return {
            'main_state': self.state.name,
            'modules': {
                name: {
                    'running': status.running,
                    'paused': status.paused,
                    'error': status.error,
                }
                for name, status in self.modules.items()
            }
        }
    
    def is_module_running(self, module_name: str) -> bool:
        """检查指定模块是否正在运行"""
        return self.modules[module_name].running
    
    def _get_current_module(self) -> Optional[str]:
        """获取当前运行的模块名称"""
        if self.state == MainState.RECORDING:
            return 'record'
        elif self.state == MainState.DETECTING:
            return 'detection'
        elif self.state == MainState.VOYAGE:
            return 'voyage'
        elif self.state == MainState.PLUGIN:
            return 'plugin'
        return None
    
    def _notify_state_change(self, old_state: MainState, new_state: MainState):
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
    'MainState',
    'ModuleStatus',
    'MainStateMachine',
]
