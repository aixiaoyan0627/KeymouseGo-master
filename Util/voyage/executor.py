# -*- encoding:utf-8 -*-
"""
脚本执行器：负责航行脚本的执行和停止控制
"""
import os
from typing import Optional, Callable
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from loguru import logger

from Util.RunScriptClass import RunScriptCMDClass, StopFlag


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    script_path: str
    error_message: Optional[str] = None


class ScriptExecutor:
    """
    脚本执行器
    
    负责管理航行脚本的执行，包括：
    - 执行指定脚本
    - 停止正在执行的脚本
    - 执行状态回调
    """
    
    def __init__(
        self,
        on_start: Optional[Callable[[str], None]] = None,
        on_finish: Optional[Callable[[ExecutionResult], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self.on_start = on_start
        self.on_finish = on_finish
        self.on_log = on_log
        
        self._current_flag: Optional[StopFlag] = None
        self._current_thread: Optional[QThread] = None
        self._is_executing = False
    
    def is_executing(self) -> bool:
        """检查是否正在执行脚本"""
        return self._is_executing
    
    def execute(self, script_path: str, wait: bool = True) -> bool:
        """
        执行脚本
        
        :param script_path: 脚本路径
        :param wait: 是否等待执行完成
        :return: 是否成功启动
        """
        if not script_path or not os.path.isfile(script_path):
            logger.warning('Script path invalid or not found: {}', script_path)
            if self.on_log:
                self.on_log('脚本路径无效或不存在: {}'.format(script_path))
            return False
        
        if self._is_executing:
            logger.warning('Another script is already executing')
            if self.on_log:
                self.on_log('另一个脚本正在执行中')
            return False
        
        self._current_flag = StopFlag(False)
        self._current_thread = RunScriptCMDClass([script_path], 1, self._current_flag)
        
        if self.on_start:
            self.on_start(script_path)
        
        self._is_executing = True
        
        try:
            if wait:
                self._current_thread.finished.connect(self._on_finished)
            
            self._current_thread.start()
            
            if wait:
                self._current_thread.wait()
                # 手动重置执行状态，确保 _is_executing 被正确设置为 False
                self._is_executing = False
        except Exception as e:
            logger.error('Script execution failed: {}', e)
            if self.on_log:
                self.on_log('脚本执行异常: {}'.format(e))
            self._is_executing = False
        
        return True
    
    def stop(self):
        """停止当前执行的脚本"""
        if self._current_flag:
            self._current_flag.value = True
        
        # 调用线程的stop方法来唤醒可能正在等待的线程
        if self._current_thread and self._current_thread.isRunning():
            if hasattr(self._current_thread, 'stop'):
                self._current_thread.stop()
            self._current_thread.wait(2000)
        
        self._is_executing = False
    
    def _on_finished(self):
        """脚本执行完成回调"""
        self._is_executing = False
        if self.on_finish:
            result = ExecutionResult(
                success=True,
                script_path='',
            )
            self.on_finish(result)


class AsyncScriptExecutor(QThread):
    """
    异步脚本执行器
    
    在独立线程中执行脚本，支持暂停和恢复
    """
    
    started_signal = Signal(str)
    finished_signal = Signal(bool, str)
    log_signal = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._script_path: str = ''
        self._flag: Optional[StopFlag] = None
        self._thread: Optional[QThread] = None
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._paused = False
        self._running = True
    
    def execute(self, script_path: str):
        """设置要执行的脚本并启动"""
        self._script_path = script_path
        self._running = True
        self._paused = False
        self.start()
    
    def stop(self):
        """停止执行"""
        self._mutex.lock()
        self._running = False
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
        
        if self._flag:
            self._flag.value = True
        
        if self._thread and self._thread.isRunning():
            self._thread.wait(2000)
        
        if self.isRunning():
            self.wait(2000)
    
    def pause(self):
        """暂停执行"""
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()
    
    def resume(self):
        """恢复执行"""
        self._mutex.lock()
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
    
    def run(self):
        """执行脚本"""
        if not self._script_path or not os.path.isfile(self._script_path):
            self.log_signal.emit('脚本路径无效或不存在')
            self.finished_signal.emit(False, self._script_path)
            return
        
        self.started_signal.emit(self._script_path)
        
        self._flag = StopFlag(False)
        self._thread = RunScriptCMDClass([self._script_path], 1, self._flag)
        self._thread.finished.connect(self._on_script_finished)
        self._thread.start()
        
        while self._running and self._thread.isRunning():
            self._mutex.lock()
            while self._paused and self._running:
                self._condition.wait(self._mutex)
            self._mutex.unlock()
            
            if not self._running:
                self._flag.value = True
                break
            
            self.msleep(100)
        
        if self._thread.isRunning():
            self._thread.wait(2000)
        
        self.finished_signal.emit(True, self._script_path)
    
    def _on_script_finished(self):
        """脚本执行完成"""
        pass
