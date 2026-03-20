# -*- encoding:utf-8 -*-
"""
航行检测循环（重构版 - 薄封装层）

此文件现在是对 voyage 模块的封装，保持与现有代码的兼容性。
核心逻辑已拆分到：
- voyage/config.py: 配置管理
- voyage/detector.py: 图像检测
- voyage/state_machine.py: 状态机
- voyage/executor.py: 脚本执行
"""
import os
import time
from typing import List, Optional, Tuple, Dict, Any

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from loguru import logger

from Util.RunScriptClass import StopFlag
from Util.voyage.config import DetectionConfig, IconRule, load_config, list_sea_city_from_imgsc, get_c_image_path
from Util.voyage.detector import ImageDetector, get_sea_name_from_path, get_all_c_images
from Util.voyage.state_machine import VoyageStateMachine, VoyageState
from Util.voyage.executor import ScriptExecutor


class DetectionLoop(QThread):
    """
    航行检测线程（封装层）
    
    保持与现有代码的兼容性，内部使用 VoyageStateMachine 实现核心逻辑
    """
    trigger_found = Signal(str)
    log_message = Signal(str)

    def __init__(self, config: DetectionConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._running = True
        self._paused = False
        self._mutex = QMutex()
        self._condition = QWaitCondition()
        self._double_click_executed = False
        
        self._detector: Optional[ImageDetector] = None
        self._state_machine: Optional[VoyageStateMachine] = None
        self._script_executor: Optional[ScriptExecutor] = None
        
        self.capture_region = None
        self.title = ''
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.scaled_region_a = None
        self.scaled_region_b = None
        self.scaled_region_c = None

    def stop(self):
        """停止检测线程"""
        self._mutex.lock()
        self._running = False
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
        
        if self._state_machine:
            self._state_machine.stop()
        
        if self.isRunning():
            self.wait(5000)

    def resume(self):
        """恢复检测线程"""
        self._mutex.lock()
        self._paused = False
        self._condition.wakeAll()
        self._mutex.unlock()
        logger.debug('DetectionLoop resumed')

    def _run_script_and_wait(self, script_path: str):
        """执行脚本并等待完成"""
        if not script_path or not os.path.isfile(script_path):
            logger.warning('Script path invalid or not found: {}', script_path)
            return
        
        logger.debug('Calling _run_script_and_wait for script: {}', script_path)
        
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()
        
        self.trigger_found.emit(script_path)
        
        self._mutex.lock()
        while self._paused and self._running:
            self._condition.wait(self._mutex)
        self._mutex.unlock()

    def _take_screenshot(self):
        """统一的截图函数"""
        if self._detector:
            return self._detector.take_screenshot()
        
        from Util.ImageRecognition import take_screenshot
        try:
            if self.capture_region:
                return take_screenshot(region=self.capture_region)
            else:
                return take_screenshot()
        except Exception as e:
            logger.warning('Screenshot failed: {}', e)
            return None, None

    def run(self):
        """线程主入口"""
        try:
            logger.info('DetectionLoop started')
            
            self._detector = ImageDetector(
                threshold=self.config.match_threshold,
                base_window_size=(self.config.base_window_width, self.config.base_window_height),
                use_multi_scale=self.config.use_multi_scale,
            )
            
            self._state_machine = VoyageStateMachine(
                config=self.config,
                detector=self._detector,
                log_callback=lambda msg: self.log_message.emit(msg),
                script_callback=lambda path: self._run_script_and_wait(path),
                pause_check=lambda: self._paused,
                wait_for_resume=self._wait_for_resume,
            )
            
            if not self._state_machine.initialize():
                logger.info('State machine initialization failed')
                return
            
            while self._running and self._state_machine.is_running():
                if not self._state_machine.run_step():
                    break
            
            logger.info('DetectionLoop stopped')
        except Exception as e:
            logger.error('Critical error in DetectionLoop: {}', e)
            self._running = False
            try:
                self.log_message.emit('检测线程发生错误，已停止')
            except:
                pass

    def _wait_for_resume(self) -> bool:
        """等待恢复，返回是否继续运行"""
        self._mutex.lock()
        while self._paused and self._running:
            self._condition.wait(self._mutex)
        self._mutex.unlock()
        return self._running


# 导出兼容接口
__all__ = [
    'DetectionLoop',
    'DetectionConfig',
    'IconRule',
    'load_config',
    'list_sea_city_from_imgsc',
    'get_c_image_path',
]
