# -*- encoding:utf-8 -*-
"""
插件沙箱系统

核心特点：
1. 使用子进程运行插件，崩溃不影响主程序
2. 插件生命周期管理
3. 超时控制
4. 进程间通信
"""
import os
import sys
import time
import json
import subprocess
import multiprocessing
from typing import Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from loguru import logger

try:
    from Plugin.Interface import PluginInterface
    HAS_PLUGIN_INTERFACE = True
except ImportError:
    HAS_PLUGIN_INTERFACE = False
    PluginInterface = object


class PluginStatus(Enum):
    """插件状态"""
    IDLE = auto()
    LOADING = auto()
    RUNNING = auto()
    STOPPED = auto()
    CRASHED = auto()
    TIMEOUT = auto()


@dataclass
class PluginProcessInfo:
    """插件进程信息"""
    plugin_id: str
    process: Optional[multiprocessing.Process] = None
    status: PluginStatus = PluginStatus.IDLE
    start_time: float = 0.0
    last_heartbeat: float = 0.0
    crash_count: int = 0
    max_crashes: int = 3


class PluginSandbox:
    """
    插件沙箱
    
    使用子进程运行插件，插件崩溃不影响主程序
    """
    
    def __init__(
        self,
        plugin_dir: str = "plugins",
        timeout: float = 30.0,
        heartbeat_interval: float = 5.0,
        max_crashes: int = 3,
    ):
        """
        初始化插件沙箱
        
        参数:
            plugin_dir: 插件目录
            timeout: 插件调用超时时间（秒）
            heartbeat_interval: 心跳检测间隔（秒）
            max_crashes: 最大崩溃次数
        """
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(exist_ok=True)
        
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self.max_crashes = max_crashes
        
        self.plugins: Dict[str, PluginProcessInfo] = {}
        self._running = False
        self._monitor_thread = None
        
        logger.info(f'插件沙箱已初始化，插件目录: {self.plugin_dir}')
    
    def load_plugin(self, plugin_id: str, plugin_path: str) -> bool:
        """
        加载插件（在沙箱中）
        
        参数:
            plugin_id: 插件ID
            plugin_path: 插件路径
        
        返回:
            是否加载成功
        """
        if plugin_id in self.plugins:
            logger.warning(f'插件已加载: {plugin_id}')
            return True
        
        logger.info(f'加载插件: {plugin_id}')
        
        plugin_info = PluginProcessInfo(
            plugin_id=plugin_id,
            status=PluginStatus.LOADING,
            max_crashes=self.max_crashes,
        )
        
        self.plugins[plugin_id] = plugin_info
        
        try:
            parent_conn, child_conn = multiprocessing.Pipe()
            
            process = multiprocessing.Process(
                target=self._plugin_worker,
                args=(child_conn, plugin_path, plugin_id),
                daemon=True,
            )
            
            process.start()
            
            plugin_info.process = process
            plugin_info.status = PluginStatus.IDLE
            plugin_info.start_time = time.time()
            
            logger.info(f'插件加载成功: {plugin_id}')
            return True
            
        except Exception as e:
            logger.error(f'加载插件失败: {plugin_id}, 错误: {e}')
            plugin_info.status = PluginStatus.CRASHED
            return False
    
    @staticmethod
    def _plugin_worker(conn, plugin_path: str, plugin_id: str):
        """
        插件工作进程
        
        参数:
            conn: 管道连接
            plugin_path: 插件路径
            plugin_id: 插件ID
        """
        try:
            import sys
            import os
            import importlib.util
            
            sys.path.insert(0, os.path.dirname(plugin_path))
            
            spec = importlib.util.spec_from_file_location(
                f'plugin_{plugin_id}',
                plugin_path,
            )
            
            if spec and spec.loader:
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                
                if hasattr(plugin_module, 'Plugin'):
                    plugin_class = plugin_module.Plugin
                    plugin_instance = plugin_class()
                    
                    while True:
                        if conn.poll(1.0):
                            message = conn.recv()
                            
                            if message.get('type') == 'stop':
                                break
                            
                            if message.get('type') == 'call':
                                func_name = message.get('func_name')
                                args = message.get('args', [])
                                kwargs = message.get('kwargs', {})
                                
                                try:
                                    if hasattr(plugin_instance, func_name):
                                        func = getattr(plugin_instance, func_name)
                                        result = func(*args, **kwargs)
                                        conn.send({
                                            'type': 'result',
                                            'result': result,
                                        })
                                    else:
                                        conn.send({
                                            'type': 'error',
                                            'error': f'函数不存在: {func_name}',
                                        })
                                except Exception as e:
                                    conn.send({
                                        'type': 'error',
                                        'error': str(e),
                                    })
                            
                            if message.get('type') == 'heartbeat':
                                conn.send({
                                    'type': 'heartbeat',
                                    'time': time.time(),
                                })
        except Exception as e:
            try:
                conn.send({
                    'type': 'crash',
                    'error': str(e),
                })
            except:
                pass
    
    def call_plugin(
        self,
        plugin_id: str,
        func_name: str,
        *args,
        **kwargs,
    ) -> Tuple[bool, Any]:
        """
        调用插件函数
        
        参数:
            plugin_id: 插件ID
            func_name: 函数名
            *args: 位置参数
            **kwargs: 关键字参数
        
        返回:
            (是否成功, 结果/错误信息)
        """
        if plugin_id not in self.plugins:
            return False, f'插件未加载: {plugin_id}'
        
        plugin_info = self.plugins[plugin_id]
        
        if plugin_info.status in [PluginStatus.CRASHED, PluginStatus.STOPPED]:
            return False, f'插件不可用: {plugin_id}, 状态: {plugin_info.status}'
        
        if plugin_info.crash_count >= plugin_info.max_crashes:
            plugin_info.status = PluginStatus.CRASHED
            return False, f'插件崩溃次数已达上限: {plugin_id}'
        
        try:
            parent_conn, child_conn = multiprocessing.Pipe()
            
            message = {
                'type': 'call',
                'func_name': func_name,
                'args': args,
                'kwargs': kwargs,
            }
            
            parent_conn.send(message)
            
            if parent_conn.poll(self.timeout):
                response = parent_conn.recv()
                
                if response.get('type') == 'result':
                    plugin_info.last_heartbeat = time.time()
                    return True, response.get('result')
                elif response.get('type') == 'error':
                    return False, response.get('error')
                elif response.get('type') == 'crash':
                    plugin_info.crash_count += 1
                    plugin_info.status = PluginStatus.CRASHED
                    return False, f'插件崩溃: {response.get("error")}'
            else:
                plugin_info.status = PluginStatus.TIMEOUT
                return False, f'插件调用超时: {plugin_id}'
                
        except Exception as e:
            plugin_info.crash_count += 1
            if plugin_info.crash_count >= plugin_info.max_crashes:
                plugin_info.status = PluginStatus.CRASHED
            return False, f'调用插件异常: {e}'
    
    def stop_plugin(self, plugin_id: str):
        """
        停止插件
        
        参数:
            plugin_id: 插件ID
        """
        if plugin_id not in self.plugins:
            return
        
        plugin_info = self.plugins[plugin_id]
        
        if plugin_info.process and plugin_info.process.is_alive():
            try:
                plugin_info.process.terminate()
                plugin_info.process.join(timeout=5.0)
                
                if plugin_info.process.is_alive():
                    plugin_info.process.kill()
                    plugin_info.process.join()
            except Exception as e:
                logger.warning(f'停止插件异常: {plugin_id}, 错误: {e}')
        
        plugin_info.status = PluginStatus.STOPPED
        logger.info(f'插件已停止: {plugin_id}')
    
    def restart_plugin(self, plugin_id: str, plugin_path: str) -> bool:
        """
        重启插件
        
        参数:
            plugin_id: 插件ID
            plugin_path: 插件路径
        
        返回:
            是否重启成功
        """
        self.stop_plugin(plugin_id)
        
        if plugin_id in self.plugins:
            self.plugins[plugin_id].crash_count = 0
            self.plugins[plugin_id].status = PluginStatus.IDLE
        
        return self.load_plugin(plugin_id, plugin_path)
    
    def stop_all(self):
        """停止所有插件"""
        for plugin_id in list(self.plugins.keys()):
            self.stop_plugin(plugin_id)
        
        self._running = False
    
    def get_plugin_status(self, plugin_id: str) -> Optional[PluginStatus]:
        """
        获取插件状态
        
        参数:
            plugin_id: 插件ID
        
        返回:
            插件状态
        """
        if plugin_id in self.plugins:
            return self.plugins[plugin_id].status
        return None
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有插件状态
        
        返回:
            插件状态字典
        """
        result = {}
        for plugin_id, info in self.plugins.items():
            result[plugin_id] = {
                'status': info.status.name,
                'crash_count': info.crash_count,
                'max_crashes': info.max_crashes,
                'uptime': time.time() - info.start_time if info.start_time > 0 else 0,
            }
        return result


# 全局插件沙箱实例
_sandbox: Optional[PluginSandbox] = None


def init_plugin_sandbox(
    plugin_dir: str = "plugins",
    timeout: float = 30.0,
    max_crashes: int = 3,
) -> PluginSandbox:
    """
    初始化全局插件沙箱
    
    参数:
        plugin_dir: 插件目录
        timeout: 插件调用超时时间
        max_crashes: 最大崩溃次数
    
    返回:
        插件沙箱实例
    """
    global _sandbox
    _sandbox = PluginSandbox(
        plugin_dir=plugin_dir,
        timeout=timeout,
        max_crashes=max_crashes,
    )
    return _sandbox


def get_plugin_sandbox() -> Optional[PluginSandbox]:
    """
    获取全局插件沙箱实例
    
    返回:
        插件沙箱实例
    """
    return _sandbox
