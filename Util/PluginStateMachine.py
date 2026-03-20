# -*- encoding:utf-8 -*-
"""
插件状态机 - 管理插件的生命周期

状态：
- UNLOADED: 未加载
- LOADED: 已加载
- RUNNING: 运行中
- PAUSED: 暂停
- STOPPED: 停止

状态转换：
UNLOADED → LOADED (加载插件)
LOADED → RUNNING (启动插件)
RUNNING → PAUSED (暂停插件)
PAUSED → RUNNING (恢复插件)
RUNNING → STOPPED (停止插件)
STOPPED → UNLOADED (卸载插件)
"""
from enum import Enum, auto
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

from Plugin.Interface import PluginInterface


class PluginState(Enum):
    """插件状态"""
    UNLOADED = auto()
    LOADED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()


@dataclass
class PluginContext:
    """插件上下文"""
    state: PluginState = PluginState.UNLOADED
    plugin_instance: Optional[PluginInterface] = None
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class PluginStateMachine:
    """
    插件状态机
    
    使用示例:
    ```python
    plugin_sm = PluginStateMachine()
    
    # 加载插件
    plugin_sm.load_plugin(plugin_instance)
    
    # 启动所有插件
    plugin_sm.start_all()
    
    # 暂停特定插件
    plugin_sm.pause_plugin('plugin_name')
    
    # 恢复插件
    plugin_sm.resume_plugin('plugin_name')
    
    # 停止所有插件
    plugin_sm.stop_all()
    ```
    """
    
    def __init__(self):
        self.plugins: Dict[str, PluginContext] = {}
        
        # 回调函数
        self.on_plugin_loaded: Optional[Callable[[str], None]] = None
        self.on_plugin_started: Optional[Callable[[str], None]] = None
        self.on_plugin_stopped: Optional[Callable[[str], None]] = None
        self.on_state_change: Optional[Callable[[str, PluginState, PluginState], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        logger.info('PluginStateMachine initialized')
    
    def load_plugin(self, plugin_instance: PluginInterface, priority: int = 0,
                    dependencies: List[str] = None) -> bool:
        """
        加载插件
        
        :param plugin_instance: 插件实例
        :param priority: 优先级（数字越大优先级越高）
        :param dependencies: 依赖的插件列表
        :return: 是否加载成功
        """
        plugin_name = plugin_instance.meta.name if hasattr(plugin_instance, 'meta') else str(plugin_instance)
        
        if plugin_name in self.plugins:
            self._log_error(plugin_name, "插件已加载")
            return False
        
        # 检查依赖
        if dependencies:
            for dep in dependencies:
                if dep not in self.plugins:
                    self._log_error(plugin_name, f"依赖的插件 {dep} 未加载")
                    return False
        
        old_state = PluginState.UNLOADED
        
        try:
            ctx = PluginContext(
                state=PluginState.LOADED,
                plugin_instance=plugin_instance,
                priority=priority,
                dependencies=dependencies or [],
            )
            self.plugins[plugin_name] = ctx
            
            logger.info(f'Plugin loaded: {plugin_name}, state: {old_state.name} → {ctx.state.name}')
            self._notify_state_change(plugin_name, old_state, ctx.state)
            
            if self.on_plugin_loaded:
                self.on_plugin_loaded(plugin_name)
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"加载失败：{e}")
            return False
    
    def start_plugin(self, plugin_name: str) -> bool:
        """启动插件"""
        if plugin_name not in self.plugins:
            self._log_error(plugin_name, "插件未加载")
            return False
        
        ctx = self.plugins[plugin_name]
        
        if ctx.state not in [PluginState.LOADED, PluginState.PAUSED, PluginState.STOPPED]:
            self._log_error(plugin_name, f"当前状态 {ctx.state.name} 无法启动")
            return False
        
        old_state = ctx.state
        
        try:
            # 调用插件的启动方法
            if hasattr(ctx.plugin_instance, 'start'):
                ctx.plugin_instance.start()
            
            ctx.state = PluginState.RUNNING
            ctx.error_message = None
            
            logger.info(f'Plugin started: {plugin_name}, state: {old_state.name} → {ctx.state.name}')
            self._notify_state_change(plugin_name, old_state, ctx.state)
            
            if self.on_plugin_started:
                self.on_plugin_started(plugin_name)
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"启动失败：{e}")
            ctx.error_message = str(e)
            return False
    
    def start_all(self) -> bool:
        """启动所有已加载的插件（按优先级）"""
        # 按优先级排序
        sorted_plugins = sorted(
            self.plugins.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        
        success_count = 0
        for plugin_name, ctx in sorted_plugins:
            if ctx.state in [PluginState.LOADED, PluginState.PAUSED, PluginState.STOPPED]:
                if self.start_plugin(plugin_name):
                    success_count += 1
        
        logger.info(f'Started {success_count}/{len(self.plugins)} plugins')
        return success_count > 0
    
    def pause_plugin(self, plugin_name: str) -> bool:
        """暂停插件"""
        if plugin_name not in self.plugins:
            return False
        
        ctx = self.plugins[plugin_name]
        
        if ctx.state != PluginState.RUNNING:
            return False
        
        old_state = ctx.state
        
        try:
            # 调用插件的暂停方法
            if hasattr(ctx.plugin_instance, 'pause'):
                ctx.plugin_instance.pause()
            
            ctx.state = PluginState.PAUSED
            
            logger.info(f'Plugin paused: {plugin_name}, state: {old_state.name} → {ctx.state.name}')
            self._notify_state_change(plugin_name, old_state, ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"暂停失败：{e}")
            return False
    
    def resume_plugin(self, plugin_name: str) -> bool:
        """恢复插件"""
        if plugin_name not in self.plugins:
            return False
        
        ctx = self.plugins[plugin_name]
        
        if ctx.state != PluginState.PAUSED:
            return False
        
        old_state = ctx.state
        
        try:
            # 调用插件的恢复方法
            if hasattr(ctx.plugin_instance, 'resume'):
                ctx.plugin_instance.resume()
            
            ctx.state = PluginState.RUNNING
            
            logger.info(f'Plugin resumed: {plugin_name}, state: {old_state.name} → {ctx.state.name}')
            self._notify_state_change(plugin_name, old_state, ctx.state)
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"恢复失败：{e}")
            return False
    
    def stop_plugin(self, plugin_name: str) -> bool:
        """停止插件"""
        if plugin_name not in self.plugins:
            return False
        
        ctx = self.plugins[plugin_name]
        
        if ctx.state == PluginState.STOPPED:
            return False
        
        old_state = ctx.state
        
        try:
            # 调用插件的停止方法
            if hasattr(ctx.plugin_instance, 'stop'):
                ctx.plugin_instance.stop()
            
            ctx.state = PluginState.STOPPED
            
            logger.info(f'Plugin stopped: {plugin_name}, state: {old_state.name} → {ctx.state.name}')
            self._notify_state_change(plugin_name, old_state, ctx.state)
            
            if self.on_plugin_stopped:
                self.on_plugin_stopped(plugin_name)
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"停止失败：{e}")
            return False
    
    def stop_all(self) -> bool:
        """停止所有插件"""
        success_count = 0
        for plugin_name in list(self.plugins.keys()):
            if self.stop_plugin(plugin_name):
                success_count += 1
        
        logger.info(f'Stopped {success_count}/{len(self.plugins)} plugins')
        return success_count > 0
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name not in self.plugins:
            return False
        
        ctx = self.plugins[plugin_name]
        
        if ctx.state != PluginState.STOPPED:
            self._log_error(plugin_name, "插件未停止，无法卸载")
            return False
        
        old_state = ctx.state
        
        try:
            # 调用插件的卸载方法
            if hasattr(ctx.plugin_instance, 'unload'):
                ctx.plugin_instance.unload()
            
            # 从列表中移除
            del self.plugins[plugin_name]
            
            logger.info(f'Plugin unloaded: {plugin_name}, state: {old_state.name} → UNLOADED')
            
            return True
            
        except Exception as e:
            self._log_error(plugin_name, f"卸载失败：{e}")
            return False
    
    def unload_all(self) -> bool:
        """卸载所有插件"""
        # 先停止所有插件
        self.stop_all()
        
        # 然后卸载
        for plugin_name in list(self.plugins.keys()):
            self.unload_plugin(plugin_name)
        
        logger.info('All plugins unloaded')
        return True
    
    def get_plugin_state(self, plugin_name: str) -> Optional[PluginState]:
        """获取插件状态"""
        if plugin_name not in self.plugins:
            return None
        return self.plugins[plugin_name].state
    
    def get_status(self) -> dict:
        """获取所有插件的状态"""
        return {
            name: {
                'state': ctx.state.name,
                'priority': ctx.priority,
                'error': ctx.error_message,
            }
            for name, ctx in self.plugins.items()
        }
    
    def is_plugin_running(self, plugin_name: str) -> bool:
        """检查插件是否正在运行"""
        if plugin_name not in self.plugins:
            return False
        return self.plugins[plugin_name].state == PluginState.RUNNING
    
    def _notify_state_change(self, plugin_name: str, old_state: PluginState, new_state: PluginState):
        """通知状态变化"""
        if self.on_state_change:
            try:
                self.on_state_change(plugin_name, old_state, new_state)
            except Exception as e:
                self._log_error(plugin_name, f"状态变化回调失败：{e}")
    
    def _log_error(self, plugin_name: str, message: str):
        """记录错误"""
        logger.warning(f'[{plugin_name}] {message}')
        if self.on_error:
            try:
                self.on_error(plugin_name, message)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")


# 导出
__all__ = [
    'PluginState',
    'PluginContext',
    'PluginStateMachine',
]
