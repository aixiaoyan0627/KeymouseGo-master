# -*- encoding:utf-8 -*-
"""
死亡检测器：负责沉船检测、偏航检测、卡死检测
"""
import os
import time
from typing import Optional, Callable
from dataclasses import dataclass

from loguru import logger


@dataclass
class DeathDetectorContext:
    """死亡检测器上下文"""
    # 沉船检测
    rescue_detected: bool = False
    # 偏航检测
    a_miss_start_time: Optional[float] = None
    # 卡死检测
    city_stuck_start_time: Optional[float] = None
    city_stuck_retry_count: int = 0


class DeathDetector:
    """
    死亡检测器
    
    职责：
    - 沉船检测（救助图标）
    - 偏航检测（A类图消失超时）
    - 卡死检测（C状态卡住超时）
    """
    
    def __init__(
        self,
        config,
        detector,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.detector = detector
        self.log = log_callback or print
        self.on_script_execute = script_callback
        
        self.ctx = DeathDetectorContext()
    
    def reset(self):
        """重置上下文"""
        self.ctx = DeathDetectorContext()
    
    def check_in_strategy_a(self, screenshot, capture_offset) -> bool:
        """
        在A策略下检查死亡检测
        
        :return: 是否检测到需要处理的情况（如果是则已处理）
        """
        # 沉船检测（最高优先级）
        if self._check_shipwreck(screenshot, capture_offset):
            return True
        
        # 偏航检测
        if self._check_off_course():
            return True
        
        return False
    
    def _check_shipwreck(self, screenshot, capture_offset) -> bool:
        """检查沉船"""
        if not self.config.death_config:
            return False
        
        if not self.config.death_config.rescue_image_paths:
            return False
        
        rescue_detected = self.detector.detect_class_a(
            self.config.death_config.rescue_image_paths, 
            screenshot, 
            capture_offset
        )
        
        if rescue_detected:
            self.log('[死亡检测] 检测到沉船（救助图标）')
            
            if (self.config.death_config.script_shipwreck_reset and 
                os.path.isfile(self.config.death_config.script_shipwreck_reset)):
                if self.on_script_execute:
                    self.on_script_execute(self.config.death_config.script_shipwreck_reset)
            
            self.reset()
            return True
        
        return False
    
    def _check_off_course(self) -> bool:
        """检查偏航"""
        if not self.config.death_config:
            return False
        
        if self.ctx.a_miss_start_time is None:
            self.ctx.a_miss_start_time = time.time()
            return False
        
        elapsed = time.time() - self.ctx.a_miss_start_time
        timeout = getattr(self.config.death_config, 'a_missing_timeout', 60.0)
        
        if elapsed >= timeout:
            self.log('[死亡检测] 偏航（A类图消失超过{}秒）'.format(int(timeout)))
            
            if (self.config.death_config.script_off_course_reset and 
                os.path.isfile(self.config.death_config.script_off_course_reset)):
                if self.on_script_execute:
                    self.on_script_execute(self.config.death_config.script_off_course_reset)
            
            self.reset()
            return True
        
        return False
    
    def reset_a_miss_timer(self):
        """重置A类图消失计时器"""
        self.ctx.a_miss_start_time = None
    
    def check_in_strategy_c(self, screenshot, capture_offset) -> bool:
        """
        在C策略下检查死亡检测
        
        :return: 是否检测到需要处理的情况（如果是则已处理）
        """
        # 沉船检测（最高优先级）
        if self._check_shipwreck(screenshot, capture_offset):
            return True
        
        # 卡死检测
        if self._check_city_stuck():
            return True
        
        return False
    
    def _check_city_stuck(self) -> bool:
        """检查城市卡死"""
        if not self.config.death_config:
            return False
        
        if self.ctx.city_stuck_start_time is None:
            self.ctx.city_stuck_start_time = time.time()
            return False
        
        elapsed = time.time() - self.ctx.city_stuck_start_time
        timeout = getattr(self.config.death_config, 'city_stuck_timeout', 60.0)
        
        if elapsed >= timeout:
            self.ctx.city_stuck_retry_count += 1
            max_retries = getattr(self.config.death_config, 'max_city_stuck_retries', 3)
            
            if self.ctx.city_stuck_retry_count >= max_retries:
                self.log('[死亡检测] 城市卡死，重试{}次后停止'.format(max_retries))
                return True  # 由调用者处理停止
            else:
                self.log('[死亡检测] 城市卡死，第{}次重试'.format(self.ctx.city_stuck_retry_count))
                self.ctx.city_stuck_start_time = time.time()
                return False
        
        return False
    
    def reset_city_stuck_timer(self):
        """重置城市卡死计时器"""
        self.ctx.city_stuck_start_time = None
        self.ctx.city_stuck_retry_count = 0
