# -*- encoding:utf-8 -*-
"""
航行状态机（新架构）：

核心特点：
1. SAILING（A状态）和 IN_CITY（C状态）完全分离
2. 高优先级全局事件检测（死亡检测）
3. 策略模式：不同运行模式使用不同策略
4. 清晰的状态转换
5. 完整的超时和重试机制

状态：
- IDLE: 空闲
- SAILING: 航行中（A状态）
- IN_CITY: 城市中（C状态）
- DEAD: 死亡状态
- STOPPED: 停止状态
- WAITING: 等待状态（城市重试达到上限）
"""
import os
import time
from enum import Enum, auto
from typing import Optional, Callable, Tuple
from dataclasses import dataclass, field

from loguru import logger

from .config import DetectionConfig, DeathConfig
from .detector import ImageDetector
from .action_executor import ActionExecutor
from .death_detector import DeathDetector
from .strategies import IVoyageStrategy, StrategyContext, OceanStrategy


class VoyageState(Enum):
    """航行状态"""
    IDLE = auto()
    SAILING = auto()
    IN_CITY = auto()
    DEAD = auto()
    STOPPED = auto()
    WAITING = auto()


@dataclass
class VoyageContext:
    """航行上下文"""
    state: VoyageState = VoyageState.IDLE
    running: bool = True
    paused: bool = False
    strategy_ctx: StrategyContext = field(default_factory=StrategyContext)
    
    # A状态相关计时
    last_a_detected_time: float = 0.0
    a_missing_start_time: float = 0.0
    
    # C状态相关计时和重试
    city_script_finished_time: float = 0.0
    city_stuck_retry_count: int = 0
    is_in_city_script_execution: bool = False
    
    # 记录上一次下一站选择的参数（用于复位）
    last_sell_sea: str = ""
    last_sell_city: str = ""
    last_city_selection_mode: str = ""


class VoyageStateMachine:
    """
    航行状态机（新架构）
    
    状态转换：
    IDLE → SAILING (开始航行，先进入航行状态)
    SAILING → IN_CITY (连续10秒检测不到A类)
    IN_CITY → SAILING (城市处理完毕，重新检测)
    SAILING → DEAD (检测到救助图标 → 执行沉船复位)
    SAILING → SAILING (A状态图标缺失超1分钟 → 执行偏航复位)
    IN_CITY → WAITING (重试达3次仍未回到海上)
    ANY → STOPPED (停止信号)
    """
    
    def __init__(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        strategy: IVoyageStrategy,
        death_detector: Optional[DeathDetector] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        wait_for_resume: Optional[Callable[[], bool]] = None,
    ):
        self.config = config
        self.death_config = config.death_config or DeathConfig()
        self.detector = detector
        self.action_executor = action_executor
        self.strategy = strategy
        self.death_detector = death_detector or DeathDetector()
        
        self.log = log_callback or print
        self.on_script_execute = script_callback
        self.pause_check = pause_check
        self.wait_for_resume = wait_for_resume
        
        self.ctx = VoyageContext()
        self.interval = max(self.config.check_interval, 0.3)
    
    def initialize(self) -> bool:
        """
        初始化状态机
        
        :return: 是否初始化成功
        """
        if not self.detector.set_window(
            self.config.capture_window_title,
            self.config.region_a,
            self.config.region_b,
            self.config.region_c,
        ):
            self.log('[状态机] 未找到游戏窗口「{}」，航行已停止'.format(self.config.capture_window_title))
            return False
        
        window_size = self.detector.get_window_size()
        scale_x, scale_y = self.detector.get_scale_factors()
        self.log('[状态机] 已锁定游戏窗口「{}」，窗口大小: {}x{}, 缩放因子: {:.2f}x{:.2f}'.format(
            self.config.capture_window_title,
            window_size[0], window_size[1],
            scale_x, scale_y
        ))
        
        if not self.strategy.initialize(
            self.config,
            self.detector,
            self.action_executor,
            self.log,
            self.on_script_execute,
        ):
            self.log('[状态机] 策略初始化失败')
            return False
        
        import datetime
        screenshot, capture_offset = self.detector.take_screenshot()
        if screenshot is not None:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join('logs', f'detection_regions_{timestamp}.png')
            self.detector.draw_detection_regions(screenshot, save_path)
            self.log('[状态机] 检测区域可视化图片已保存到: {}'.format(save_path))
        
        # 初始化计时
        self.ctx.last_a_detected_time = time.time()
        self.ctx.a_missing_start_time = 0.0
        
        self.ctx.state = VoyageState.SAILING
        self.strategy.on_enter_sailing()
        return True
    
    def stop(self):
        """停止状态机"""
        self.ctx.running = False
        self.ctx.paused = False
        self.ctx.state = VoyageState.STOPPED
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.ctx.running
    
    def _check_global_events(self, screenshot, capture_offset) -> bool:
        """
        检查全局事件（高优先级）
        
        :return: True 表示已处理全局事件，当前状态步应该跳过
        """
        if self.death_detector.detect_rescue(screenshot, capture_offset):
            self._handle_shipwreck()
            return True
        return False
    
    def _handle_shipwreck(self):
        """处理沉船事件（A状态救助图标）"""
        self.log('[状态机] 检测到救助图标（沉船），执行沉船复位脚本')
        self.ctx.state = VoyageState.DEAD
        
        if self.death_config.script_shipwreck_reset and self.on_script_execute:
            self.log('[状态机] 执行沉船复位脚本: {}'.format(self.death_config.script_shipwreck_reset))
            self.on_script_execute(self.death_config.script_shipwreck_reset)
        else:
            self.log('[状态机] 警告：未配置沉船复位脚本')
        
        # 执行完脚本后回到A状态
        self.log('[状态机] 沉船复位脚本执行完毕，回到航行状态')
        self.ctx.state = VoyageState.SAILING
        self.ctx.last_a_detected_time = time.time()
        self.ctx.a_missing_start_time = 0.0
        self.strategy.on_enter_sailing()
    
    def _handle_a_missing_timeout(self):
        """处理A状态图标缺失超时（偏航）"""
        self.log('[状态机] 航行中图标缺失超过{}秒，执行偏航复位脚本'.format(self.death_config.a_missing_timeout))
        self.ctx.state = VoyageState.DEAD
        
        if self.death_config.script_off_course_reset and self.on_script_execute:
            self.log('[状态机] 执行偏航复位脚本: {}'.format(self.death_config.script_off_course_reset))
            self.on_script_execute(self.death_config.script_off_course_reset)
        else:
            self.log('[状态机] 警告：未配置偏航复位脚本')
        
        # 执行完脚本后回到A状态
        self.log('[状态机] 偏航复位脚本执行完毕，回到航行状态')
        self.ctx.state = VoyageState.SAILING
        self.ctx.last_a_detected_time = time.time()
        self.ctx.a_missing_start_time = 0.0
        self.strategy.on_enter_sailing()
    
    def _handle_city_stuck(self):
        """处理C状态卡住（超过1分钟未回到A状态）"""
        self.ctx.city_stuck_retry_count += 1
        
        self.log('[状态机] 城市状态卡住，第{}次重试（最多{}次）'.format(
            self.ctx.city_stuck_retry_count, self.death_config.max_city_stuck_retries
        ))
        
        if self.ctx.city_stuck_retry_count >= self.death_config.max_city_stuck_retries:
            self.log('[状态机] 重试次数已达上限，进入等待状态')
            self.ctx.state = VoyageState.WAITING
            self.ctx.running = False
            return
        
        # 再次执行策略的城市处理逻辑
        self.log('[状态机] 重新执行城市脚本流程')
        self.ctx.city_script_finished_time = 0.0
        self.ctx.is_in_city_script_execution = True
        
        # 让策略重新开始处理城市
        self.strategy.on_enter_in_city()
    
    def run_step(self) -> bool:
        """
        执行一步状态机循环
        
        :return: 是否继续运行
        """
        if not self.ctx.running:
            return False
        
        if self.pause_check and self.pause_check():
            if self.wait_for_resume:
                if not self.wait_for_resume():
                    return False
            return True
        
        screenshot, capture_offset = self.detector.take_screenshot()
        if screenshot is None:
            time.sleep(self.interval)
            return True
        
        if self._check_global_events(screenshot, capture_offset):
            time.sleep(self.interval)
            return True
        
        if self.ctx.state == VoyageState.SAILING:
            self._run_sailing_state(screenshot, capture_offset)
        elif self.ctx.state == VoyageState.IN_CITY:
            self._run_in_city_state(screenshot, capture_offset)
        elif self.ctx.state == VoyageState.DEAD:
            self._run_dead_state(screenshot, capture_offset)
        elif self.ctx.state == VoyageState.WAITING:
            self._run_waiting_state(screenshot, capture_offset)
        elif self.ctx.state == VoyageState.STOPPED:
            return False
        
        time.sleep(self.interval)
        return True
    
    def _run_sailing_state(self, screenshot, capture_offset):
        """航行状态（A状态）"""
        current_time = time.time()
        
        # 检测是否存在A类图标
        a_detected = self.detector.detect_image_a(screenshot, capture_offset)
        
        if a_detected:
            # 检测到A类图标
            self.ctx.last_a_detected_time = current_time
            self.ctx.a_missing_start_time = 0.0
            
            # 执行策略的航行步骤
            stay_in_sailing = self.strategy.run_sailing_step(
                screenshot,
                capture_offset,
                self.ctx.strategy_ctx,
            )
            
            if not stay_in_sailing:
                self._transition_to_in_city()
        else:
            # 未检测到A类图标
            if self.ctx.a_missing_start_time == 0.0:
                self.ctx.a_missing_start_time = current_time
            
            # 检查A类图标缺失是否超过偏航复位超时（1分钟）
            a_missing_duration = current_time - self.ctx.a_missing_start_time
            if a_missing_duration >= self.death_config.a_missing_timeout:
                self._handle_a_missing_timeout()
                return
            
            # 检查是否超过进入城市状态的阈值（10秒）
            if a_missing_duration >= 10.0:
                self._transition_to_in_city()
    
    def _transition_to_in_city(self):
        """转换到城市状态"""
        self.log('[状态机] 转换到 IN_CITY 状态')
        self.ctx.state = VoyageState.IN_CITY
        self.ctx.strategy_ctx.consecutive_a_miss = 0
        self.ctx.city_script_finished_time = 0.0
        self.ctx.city_stuck_retry_count = 0
        self.ctx.is_in_city_script_execution = True
        self.strategy.on_enter_in_city()
    
    def _run_in_city_state(self, screenshot, capture_offset):
        """城市状态（C状态）"""
        current_time = time.time()
        
        # 先检查是否已经回到A状态（为了保险）
        a_detected = self.detector.detect_image_a(screenshot, capture_offset)
        if a_detected:
            self.log('[状态机] 检测到航行中图标，回到航行状态')
            self._transition_to_sailing()
            return
        
        # 执行策略的城市步骤
        stay_in_city = self.strategy.run_in_city_step(
            screenshot,
            capture_offset,
            self.ctx.strategy_ctx,
        )
        
        if not stay_in_city:
            # 策略表示城市处理完毕
            if self.ctx.city_script_finished_time == 0.0:
                self.ctx.city_script_finished_time = current_time
                self.ctx.is_in_city_script_execution = False
                self.log('[状态机] 城市脚本执行完毕，等待回到海上')
            
            # 检查是否超时
            stuck_duration = current_time - self.ctx.city_script_finished_time
            if stuck_duration >= self.death_config.city_stuck_timeout:
                self._handle_city_stuck()
        else:
            # 仍在城市处理中
            self.ctx.city_script_finished_time = 0.0
    
    def _transition_to_sailing(self):
        """转换到航行状态"""
        self.log('[状态机] 转换到 SAILING 状态')
        self.ctx.state = VoyageState.SAILING
        self.ctx.last_a_detected_time = time.time()
        self.ctx.a_missing_start_time = 0.0
        self.strategy.on_enter_sailing()
    
    def _run_dead_state(self, screenshot, capture_offset):
        """死亡状态（临时状态，事件处理完后应该已跳转）"""
        self.log('[状态机] 死亡状态 - 等待事件处理完成')
        time.sleep(0.5)
    
    def _run_waiting_state(self, screenshot, capture_offset):
        """等待状态（停止所有游戏相关模块）"""
        self.log('[状态机] 等待状态 - 已停止游戏相关操作')
        time.sleep(1)
    
    def run(self):
        """运行状态机主循环"""
        time.sleep(5.0)
        
        if not self.initialize():
            self.ctx.state = VoyageState.STOPPED
            return
        
        while self.ctx.running:
            if not self.run_step():
                break
        
        self.ctx.state = VoyageState.STOPPED
        logger.info('VoyageStateMachine stopped')
