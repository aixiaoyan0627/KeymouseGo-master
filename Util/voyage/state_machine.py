# -*- encoding:utf-8 -*-
"""
航行状态机：负责主循环、A策略、C策略的状态转换和逻辑控制

状态流程：
1. INIT (开启自检与状态判定) - 初始化并判定当前状态
2. STRATEGY_A (A策略) - 航行中，处理B类图片点击
3. STRATEGY_C (C策略) - 城市中，执行买卖操作
4. ERROR_CHECK (异常检测) - 死亡检测和偏航防护
5. STOPPED (停止)
"""
import os
import time
import random
import datetime
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple, Any
from dataclasses import dataclass

from loguru import logger

from .config import DetectionConfig
from .detector import ImageDetector, MatchResult, get_sea_name_from_path, get_all_c_images, get_sea_c_images
from .death_detector import DeathDetector
from .city_strategy import CityStrategyExecutor
from .action_executor import ActionExecutor
from .enhanced_script import EnhancedScriptExecutor
from .executor import ScriptExecutor


class VoyageState(Enum):
    """航行状态"""
    INIT = auto()              # 开启自检与状态判定
    STRATEGY_A = auto()        # A策略（航行中）
    STRATEGY_C = auto()        # C策略（城市中）
    ERROR_CHECK = auto()       # 异常检测（死亡/偏航）
    STOPPED = auto()           # 停止


@dataclass
class VoyageContext:
    """航行上下文，存储运行时状态"""
    state: VoyageState = VoyageState.INIT
    running: bool = True
    paused: bool = False
    current_city_config: Optional[Any] = None
    previous_city_config: Optional[Any] = None  # 上一个城市配置（用于死亡检测后的下一站选择）
    next_target_sea: Optional[str] = None
    c_city_not_matched: bool = False
    
    # 状态检测相关
    state_detection_start_time: float = 0.0  # 状态检测开始时间
    state_detection_fail_count: int = 0  # 状态检测失败次数
    state_detection_timeout: float = 60.0  # 1分钟超时开启死亡检测
    
    # A策略相关
    a_miss_count: int = 0  # A状态标识消失次数
    
    # 死亡检测相关
    death_check_count: int = 0  # 死亡检测次数
    max_death_check_count: int = 3  # 最大死亡检测次数（3次后停止航行）
    
    # C策略相关
    last_c_state_time: float = 0.0  # 最后一次进入C状态的时间


class VoyageStateMachine:
    """
    航行状态机
    
    状态转换流程：
    INIT → STRATEGY_A 或 STRATEGY_C
    STRATEGY_A → STRATEGY_C (A状态标识消失超过10秒)
    STRATEGY_C → STRATEGY_A (策略段执行完成) 或 INIT (城市不匹配)
    STRATEGY_A/C → ERROR_CHECK (状态异常)
    ERROR_CHECK → STRATEGY_A (死亡复位/偏航防护完成) 或 STOPPED
    """
    
    def __init__(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
        pause_check: Optional[Callable[[], bool]] = None,
        wait_for_resume: Optional[Callable[[], bool]] = None,
    ):
        self.config = config
        self.detector = detector
        self.log = log_callback or print
        self.on_script_execute = script_callback
        self.pause_check = pause_check
        self.wait_for_resume = wait_for_resume
        
        self.ctx = VoyageContext()
        
        self.a_paths: List[str] = []
        self.a1_paths: List[str] = []  # imgsA1
        self.a2_paths: List[str] = []  # imgsA2
        self.a3_paths: List[str] = []  # imgsA3
        self.b_instant_paths: List[str] = []
        self.b_delay_paths: List[str] = []
        self.c_all_paths: List[str] = []
        self.c_priority_seas: List[str] = []  # 配置中设置的优先海域列表
        
        self.min_interval = 0.5
        self.max_interval = 1.0
        
        self.death_detector = DeathDetector(
            config=self.config,
            detector=self.detector,
            log_callback=self.log,
            script_callback=self.on_script_execute,
        )
        
        self.action_executor = ActionExecutor(window_title=self.config.capture_window_title)
        
        self.script_executor = ScriptExecutor(on_log=self.log)
        
        self.enhanced_script_executor = EnhancedScriptExecutor(
            detector=self.detector,
            action_executor=self.action_executor,
            script_executor=self.script_executor,
            log_callback=self.log,
        )
        
        self.city_strategy = CityStrategyExecutor(
            config=self.config,
            log_callback=self.log,
            enhanced_script_executor=self.enhanced_script_executor,
            script_executor=self.script_executor,
            script_callback=self.on_script_execute,
        )
    
    def initialize(self) -> bool:
        """
        初始化状态机
        
        :return: 是否初始化成功
        """
        self.log('[状态机] 开始初始化...')
        
        # 设置默认区域值
        if self.config.region_a_list is None:
            # region_a1: [175, 689, 74, 67], region_a2: [878, 510, 118, 178], region_a3: [84, 13, 187, 23]
            self.config.region_a_list = [
                (175, 689, 74, 67),
                (878, 510, 118, 178),
                (84, 13, 187, 23),
            ]
        if self.config.region_a1 is None:
            self.config.region_a1 = (175, 689, 74, 67)
        if self.config.region_a2 is None:
            self.config.region_a2 = (878, 510, 118, 178)
        if self.config.region_a3 is None:
            self.config.region_a3 = (84, 13, 187, 23)
        if self.config.region_b is None:
            self.config.region_b = (587, 432, 155, 150)
        if self.config.region_b_delay is None:
            self.config.region_b_delay = (587, 432, 155, 150)
        if self.config.region_c is None:
            self.config.region_c = (865, 10, 122, 29)
        if self.config.region_e is None:
            self.config.region_e = (814, 374, 107, 297)
        if self.config.region_f is None:
            self.config.region_f = (757, 140, 92, 494)
        
        if not self.detector.set_window(
            self.config.capture_window_title,
            self.config.region_a,
            self.config.region_a_list,
            self.config.region_a1,
            self.config.region_a2,
            self.config.region_a3,
            self.config.region_b,
            self.config.region_b_delay,
            self.config.region_c,
            self.config.region_e,
            self.config.region_f,
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
        
        self._init_paths()
        
        self.log('[状态机] 图片路径初始化完成')
        self.log('[状态机] A类图片: {} 张'.format(len(self.a_paths)))
        self.log('[状态机] A1类图片: {} 张'.format(len(self.a1_paths)))
        self.log('[状态机] A2类图片: {} 张'.format(len(self.a2_paths)))
        self.log('[状态机] A3类图片: {} 张'.format(len(self.a3_paths)))
        self.log('[状态机] B类instant图片: {} 张'.format(len(self.b_instant_paths)))
        self.log('[状态机] B类delay图片: {} 张'.format(len(self.b_delay_paths)))
        self.log('[状态机] C类图片: {} 张'.format(len(self.c_all_paths)))
        
        # 打印检测区域配置
        self.log('[状态机] 检测区域配置:')
        self.log('[状态机]   region_a: {}'.format(self.config.region_a))
        self.log('[状态机]   region_a1: {}'.format(self.config.region_a1))
        self.log('[状态机]   region_a2: {}'.format(self.config.region_a2))
        self.log('[状态机]   region_a3: {}'.format(self.config.region_a3))
        self.log('[状态机]   region_b: {}'.format(self.config.region_b))
        self.log('[状态机]   region_b_delay: {}'.format(self.config.region_b_delay))
        self.log('[状态机]   region_c: {}'.format(self.config.region_c))
        self.log('[状态机]   region_e: {}'.format(self.config.region_e))
        self.log('[状态机]   region_f: {}'.format(self.config.region_f))
        
        # 预加载所有C类图片模板到缓存
        self.log('[状态机] 开始预加载C类图片模板...')
        start_time = time.time()
        loaded_count = 0
        for path in self.c_all_paths:
            template = self.detector._load_template(path)
            if template is not None:
                loaded_count += 1
        elapsed = time.time() - start_time
        self.log('[状态机] C类图片模板预加载完成: {}/{} 张, 耗时 {:.2f}秒'.format(
            loaded_count, len(self.c_all_paths), elapsed))
        
        if self.config.ocean_v3_config and len(self.config.ocean_v3_config.cities) > 0:
            first_city = self.config.ocean_v3_config.cities[0]
            self.ctx.next_target_sea = first_city.sea
            self.log('[状态机] 初始目标海域: 「{}」'.format(first_city.sea))
        elif self.config.ocean_v3_liuxing_config and len(self.config.ocean_v3_liuxing_config.cities) > 0:
            first_city = self.config.ocean_v3_liuxing_config.cities[0]
            self.ctx.next_target_sea = first_city.sea
            self.log('[状态机] 初始目标海域(流行板块): 「{}」'.format(first_city.sea))
        
        self.ctx.state = VoyageState.INIT
        self.log('[状态机] 初始化完成，进入「开启自检与状态判定」')
        
        return True
    
    def _init_paths(self):
        """初始化图片路径"""
        self.a_paths = [p for p in self.config.image_a_paths if p and os.path.isfile(p)]
        self.a1_paths = [p for p in self.config.image_a1_paths if p and os.path.isfile(p)]
        self.a2_paths = [p for p in self.config.image_a2_paths if p and os.path.isfile(p)]
        self.a3_paths = [p for p in self.config.image_a3_paths if p and os.path.isfile(p)]
        
        self.b_instant_paths = []
        self.b_delay_paths = []
        for p in self.config.image_b_paths:
            if p and os.path.isfile(p):
                if 'instant' in p.lower() or 'Instant' in p:
                    self.b_instant_paths.append(p)
                else:
                    self.b_delay_paths.append(p)
        
        self.c_all_paths = get_all_c_images(self.config.imgsc_root_path)
        
        # 从配置中提取优先海域列表（去重）
        self.c_priority_seas = []
        if self.config.ocean_v3_config and self.config.ocean_v3_config.cities:
            for city_cfg in self.config.ocean_v3_config.cities:
                if city_cfg.sea and city_cfg.sea not in self.c_priority_seas:
                    self.c_priority_seas.append(city_cfg.sea)
        elif self.config.ocean_v3_liuxing_config and self.config.ocean_v3_liuxing_config.cities:
            for city_cfg in self.config.ocean_v3_liuxing_config.cities:
                if city_cfg.sea and city_cfg.sea not in self.c_priority_seas:
                    self.c_priority_seas.append(city_cfg.sea)
        
        self.log('[状态机] 优先检测海域列表: {}'.format(self.c_priority_seas))
    
    def stop(self):
        """停止状态机"""
        self.ctx.running = False
        self.ctx.paused = False
        self.ctx.state = VoyageState.STOPPED
        
        # 停止城市策略执行器（它会停止自己的增强脚本和普通脚本执行器）
        if self.city_strategy and hasattr(self.city_strategy, 'stop'):
            self.city_strategy.stop()
        
        # 停止增强脚本执行器
        if self.enhanced_script_executor:
            self.enhanced_script_executor.stop()
        
        # 停止普通脚本执行器
        if self.script_executor:
            self.script_executor.stop()
        
        self.log('[状态机] 已停止')
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.ctx.running
    
    def run_step(self) -> bool:
        """
        执行一步状态机循环
        
        :return: 是否继续运行
        """
        try:
            if not self.ctx.running:
                return False
            
            if self.pause_check and self.pause_check():
                if self.wait_for_resume:
                    if not self.wait_for_resume():
                        return False
                # 再次检查停止标志，因为在 wait_for_resume 期间可能被停止
                if not self.ctx.running:
                    return False
                return True
            
            if self.ctx.state == VoyageState.INIT:
                return self._run_init()
            elif self.ctx.state == VoyageState.STRATEGY_A:
                return self._run_strategy_a()
            elif self.ctx.state == VoyageState.STRATEGY_C:
                return self._run_strategy_c()
            elif self.ctx.state == VoyageState.ERROR_CHECK:
                return self._run_error_check()
            elif self.ctx.state == VoyageState.STOPPED:
                return False
            
            return True
        except Exception as e:
            self.log('[状态机] 执行主循环时发生错误: {}'.format(str(e)))
            logger.exception('[状态机] 主循环异常')
            return True
    
    def _run_init(self) -> bool:
        """
        状态检测
        
        流程：
        1. 同时检测A、C状态
        2. 如检测到A状态，进入A策略
        3. 如检测到C状态，进入C策略
        4. 连续1分钟无法触发A或C策略，开启死亡检测
        5. 连续3轮状态检测及死亡检测后仍无法触发，停止航行
        """
        try:
            # 首先检查是否已停止
            if not self.ctx.running:
                return False
            
            current_time = time.time()
            
            # 初始化状态检测开始时间
            if self.ctx.state_detection_start_time == 0.0:
                self.ctx.state_detection_start_time = current_time
                self.log('[状态检测] 开始检测玩家当前状态...')
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                self.log('[状态检测] 截图失败，等待重试')
                # 可中断的等待
                for _ in range(10):
                    time.sleep(0.1)
                    if not self.ctx.running:
                        return False
                return True
            
            # 再次检查是否已停止
            if not self.ctx.running:
                return False
            
            # 检测所有A类状态（A1、A2、A3）
            a_detected = False
            if self.a_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a_paths, screenshot, capture_offset, 'default')
            if not a_detected and self.a1_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a1_paths, screenshot, capture_offset, 'a1')
            if not a_detected and self.a2_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a2_paths, screenshot, capture_offset, 'a2')
            if not a_detected and self.a3_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a3_paths, screenshot, capture_offset, 'a3')
            
            # 再次检查是否已停止
            if not self.ctx.running:
                return False
            
            c_detected = self.detector.detect_class_c(
                self.c_all_paths, 
                screenshot, 
                capture_offset,
                priority_seas=self.c_priority_seas,
                imgsc_root_path=self.config.imgsc_root_path
            )
            
            if a_detected:
                self.log('[状态检测] 检测到A状态标识，进入A策略')
                self.ctx.state = VoyageState.STRATEGY_A
                self.ctx.state_detection_fail_count = 0
                self.ctx.death_check_count = 0
                return True
            
            if c_detected:
                self.log('[状态检测] 检测到C状态标识，进入C策略')
                self.ctx.state = VoyageState.STRATEGY_C
                self.ctx.last_c_state_time = current_time
                self.ctx.state_detection_fail_count = 0
                self.ctx.death_check_count = 0
                self._handle_strategy_c_start(c_detected)
                return True
            
            # 未检测到任何状态
            elapsed = current_time - self.ctx.state_detection_start_time
            
            # 检查是否已停止
            if not self.ctx.running:
                return False
            
            # 检查是否是V3-liuxing模式
            is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
            
            if elapsed >= self.ctx.state_detection_timeout:
                if is_liuxing_mode:
                    # V3-liuxing模式：不执行死亡检测，继续状态检测
                    self.log('[状态检测] V3-liuxing模式：连续1分钟无法触发A或C策略，继续状态检测（不执行死亡检测）')
                    # 重置状态检测开始时间，避免频繁进入死亡检测
                    self.ctx.state_detection_start_time = current_time
                else:
                    # 超过1分钟，开启死亡检测
                    self.log('[状态检测] 连续1分钟无法触发A或C策略，开启死亡检测')
                    self.ctx.state = VoyageState.ERROR_CHECK
                    self.ctx.state_detection_fail_count += 1
                return True
            
            # 等待后继续检测
            self.log('[状态检测] 未检测到A或C状态，继续检测... (已等待{:.0f}秒)'.format(elapsed))
            # 可中断的等待
            for _ in range(10):
                time.sleep(0.1)
                if not self.ctx.running:
                    return False
            return True
        except Exception as e:
            self.log('[状态检测] 执行状态检测时发生错误: {}'.format(str(e)))
            logger.exception('[状态检测] 状态检测异常')
            return True
    
    def _wait_for_a_state(self, timeout: float = 30.0) -> bool:
        """
        等待A状态标识出现
        
        :param timeout: 超时时间（秒）
        :return: 是否在超时前检测到A状态
        """
        start_time = time.time()
        last_log_time = 0.0
        while time.time() - start_time < timeout:
            # 检查是否已停止（优先检查，确保快速响应）
            if not self.ctx.running:
                self.log('[状态机] 等待A状态标识时检测到停止信号')
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(0.1)
                # 再次检查停止标志
                if not self.ctx.running:
                    self.log('[状态机] 等待A状态标识时检测到停止信号')
                    return False
                continue
            
            # 检测所有A类状态（A1、A2、A3）
            a_detected = False
            if self.a_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a_paths, screenshot, capture_offset, 'default')
            if not a_detected and self.a1_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a1_paths, screenshot, capture_offset, 'a1')
            if not a_detected and self.a2_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a2_paths, screenshot, capture_offset, 'a2')
            if not a_detected and self.a3_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a3_paths, screenshot, capture_offset, 'a3')
            
            if a_detected:
                return True
            
            elapsed = time.time() - start_time
            # 每3秒打印一次日志
            if elapsed - last_log_time >= 3.0:
                self.log('[状态机] 等待A状态标识... ({:.0f}/{:.0f}秒)'.format(elapsed, timeout))
                last_log_time = elapsed
            
            # 更短的等待时间，更快响应停止信号
            for _ in range(5):
                time.sleep(0.1)
                if not self.ctx.running:
                    self.log('[状态机] 等待A状态标识时检测到停止信号')
                    return False
        
        return False
    
    def _wait_for_a_state_or_city_change(self, timeout: float = 30.0, current_sea: Optional[str] = None, current_city: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        等待A状态标识出现或城市变更为配置中的另一个城市
        
        :param timeout: 超时时间（秒）
        :param current_sea: 当前所在海域（用于判断是否真的变更了城市）
        :param current_city: 当前所在城市（用于判断是否真的变更了城市）
        :return: (是否在超时前检测到A状态或城市变更, 检测到的城市名, 检测到的海域名)
        """
        start_time = time.time()
        last_log_time = 0.0
        while time.time() - start_time < timeout:
            # 检查是否已停止（优先检查，确保快速响应）
            if not self.ctx.running:
                self.log('[状态机] 等待A状态标识或城市变更时检测到停止信号')
                return False, None, None
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                time.sleep(0.1)
                # 再次检查停止标志
                if not self.ctx.running:
                    self.log('[状态机] 等待A状态标识或城市变更时检测到停止信号')
                    return False, None, None
                continue
            
            # 1. 检测A状态
            a_detected = False
            if self.a_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a_paths, screenshot, capture_offset, 'default')
            if not a_detected and self.a1_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a1_paths, screenshot, capture_offset, 'a1')
            if not a_detected and self.a2_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a2_paths, screenshot, capture_offset, 'a2')
            if not a_detected and self.a3_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a3_paths, screenshot, capture_offset, 'a3')
            
            if a_detected:
                return True, None, None
            
            # 2. 检测城市是否变更为配置中的另一个城市
            c_detected = self.detector.detect_class_c(
                self.c_all_paths, 
                screenshot, 
                capture_offset,
                priority_seas=self.c_priority_seas,
                imgsc_root_path=self.config.imgsc_root_path
            )
            
            if c_detected:
                sea_name = get_sea_name_from_path(c_detected, self.config.imgsc_root_path)
                city_name = os.path.splitext(os.path.basename(c_detected))[0]
                
                # 检查是否是配置中的城市
                target_city_cfg = self._find_matching_city_config(sea_name, city_name)
                if target_city_cfg:
                    # 只有当检测到的城市与当前城市不同时，才认为是变更
                    if current_sea is not None and current_city is not None:
                        if sea_name == current_sea and city_name == current_city:
                            # 同一个城市，继续等待
                            pass
                        else:
                            # 不同的城市，认为是变更
                            return True, city_name, sea_name
                    else:
                        # 没有当前城市信息，直接认为是变更
                        return True, city_name, sea_name
            
            elapsed = time.time() - start_time
            # 每3秒打印一次日志
            if elapsed - last_log_time >= 3.0:
                self.log('[状态机] 等待A状态标识或城市变更... ({:.0f}/{:.0f}秒)'.format(elapsed, timeout))
                last_log_time = elapsed
            
            # 更短的等待时间，更快响应停止信号
            for _ in range(5):
                time.sleep(0.1)
                if not self.ctx.running:
                    self.log('[状态机] 等待A状态标识或城市变更时检测到停止信号')
                    return False, None, None
        
        return False, None, None
    
    def _run_strategy_a(self) -> bool:
        """
        A策略（航行中）
        
        流程：
        1. 检测A状态标识物（imgsA/imgsA1/imgsA2/imgsA3文件夹内任一图片存在即为A状态）
        2. 如A状态标识存在，持续监测点击imgsB类图标
        3. 连续3次未检测到A状态标识，跳回状态检测
        """
        try:
            # 检查是否已停止
            if not self.ctx.running:
                return False
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                # 可中断的等待
                wait_time = random.uniform(self.min_interval, self.max_interval)
                start_wait = time.time()
                while time.time() - start_wait < wait_time:
                    time.sleep(0.1)
                    if not self.ctx.running:
                        return False
                return True
            
            # 检测所有A类状态（A1、A2、A3）
            a_detected = False
            if self.a_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a_paths, screenshot, capture_offset, 'default')
            if not a_detected and self.a1_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a1_paths, screenshot, capture_offset, 'a1')
            if not a_detected and self.a2_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a2_paths, screenshot, capture_offset, 'a2')
            if not a_detected and self.a3_paths:
                a_detected = a_detected or self.detector.detect_class_a(self.a3_paths, screenshot, capture_offset, 'a3')
            
            if a_detected:
                # A状态标识存在，重置计数器，监测点击B类图片
                self.ctx.a_miss_count = 0
                self._handle_b_class_detection(screenshot, capture_offset)
            else:
                # A状态标识消失，计数+1
                self.ctx.a_miss_count += 1
                self.log('[A策略] A状态标识消失，计数: {}/3'.format(self.ctx.a_miss_count))
                
                if self.ctx.a_miss_count >= 3:
                    # 连续3次未检测到A状态标识，跳回状态检测
                    self.log('[A策略] 连续3次未检测到A状态标识，跳回状态检测')
                    self.ctx.state = VoyageState.INIT
                    self.ctx.state_detection_start_time = 0.0
                    self.ctx.a_miss_count = 0
                    return True
            
            # 可中断的等待
            wait_time = random.uniform(self.min_interval, self.max_interval)
            start_wait = time.time()
            while time.time() - start_wait < wait_time:
                time.sleep(0.1)
                if not self.ctx.running:
                    return False
            return True
        except Exception as e:
            self.log('[A策略] 执行A策略时发生错误: {}'.format(str(e)))
            logger.exception('[A策略] 执行异常')
            return True
    
    def _handle_b_class_detection(self, screenshot, capture_offset):
        """处理B类图片检测"""
        # 只检测delay类图片
        if self.b_delay_paths:
            results_delay = self.detector.detect_class_b(
                self.b_delay_paths, 
                screenshot, 
                capture_offset
            )
            if results_delay:
                self.log('[A策略] 检测到B类delay图片: {} 个'.format(len(results_delay)))
                for result in results_delay:
                    name = os.path.basename(result.path)
                    base = os.path.splitext(name)[0]
                    self._handle_delay_image(result, base)
    
    def _handle_delay_image(self, result, base: str):
        """处理delay类图片：在检测区域内点击"""
        try:
            detected_x, detected_y = result.position
            
            # 获取检测区域边界，确保点击在区域内
            region = self.config.region_b_delay
            if region:
                left, top, width, height = region
                right = left + width
                bottom = top + height
                
                self.log('[A策略] delay类"{}": 检测位置({}, {}), 区域边界[{}, {}, {}, {}]'.format(
                    base, detected_x, detected_y, left, top, right, bottom))
                
                # 检查检测位置是否在区域内
                if not (left <= detected_x <= right and top <= detected_y <= bottom):
                    self.log('[A策略] 警告：检测位置超出区域边界！')
                
                # 确保点击位置在检测区域内
                click_x = max(left, min(detected_x, right))
                click_y = max(top, min(detected_y, bottom))
            else:
                click_x, click_y = detected_x, detected_y
                self.log('[A策略] delay类"{}": 检测位置({}, {}), 无区域限制'.format(
                    base, detected_x, detected_y))
            
            click_delay = random.uniform(0.2, 0.6)
            time.sleep(click_delay)
            clicked = self.detector.click_at(click_x, click_y)
            self.log('[A策略] 点击位置({}, {}), 结果: {}'.format(click_x, click_y, clicked))
        except Exception as e:
            self.log('[A策略] 处理delay图片时发生错误: {}'.format(str(e)))
            logger.exception('[A策略] 处理delay图片异常')
    
    def _handle_strategy_c_start(self, matched_c_path: str):
        """处理C策略开始"""
        sea_name = get_sea_name_from_path(matched_c_path, self.config.imgsc_root_path)
        city_name = os.path.splitext(os.path.basename(matched_c_path))[0]
        
        self.log('[C策略] 检测到城市: 「{}」海域「{}」'.format(sea_name, city_name))
        
        self.ctx.c_city_not_matched = False
    
    def _run_strategy_c(self) -> bool:
        """
        C策略（城市中）
        
        流程：
        1. 检测玩家当前所处城市
        2. 如城市与配置匹配，执行对应策略段
        3. 如城市不匹配但海域匹配，执行固定操作流程
        4. 如城市和海域都不匹配，自动停止航行
        """
        try:
            # 检查是否已停止
            if not self.ctx.running:
                return False
            
            if self.ctx.c_city_not_matched:
                self.log('[C策略] 城市不匹配，进入状态判定')
                self.ctx.state = VoyageState.INIT
                return True
            
            screenshot, capture_offset = self.detector.take_screenshot()
            if screenshot is None:
                # 可中断的等待
                for _ in range(10):
                    time.sleep(0.1)
                    if not self.ctx.running:
                        return False
                return True
            
            c_detected = self.detector.detect_class_c(
                self.c_all_paths, 
                screenshot, 
                capture_offset,
                priority_seas=self.c_priority_seas,
                imgsc_root_path=self.config.imgsc_root_path
            )
            
            if not c_detected:
                self.log('[C策略] 未检测到城市标识，进入状态判定')
                self.ctx.state = VoyageState.INIT
                return True
            
            sea_name = get_sea_name_from_path(c_detected, self.config.imgsc_root_path)
            city_name = os.path.splitext(os.path.basename(c_detected))[0]
            
            self.log('[C策略] 检测到城市: 「{}」，海域: 「{}」'.format(city_name, sea_name))
            
            # 打印配置中的城市列表
            if self.config.ocean_v3_config:
                self.log('[C策略] 配置中的城市列表:')
                for city_cfg in self.config.ocean_v3_config.cities:
                    self.log('[C策略]   - sea={}, city={}'.format(city_cfg.sea, city_cfg.city))
            
            # 1. 检查城市是否匹配配置
            target_city_cfg = self._find_matching_city_config(sea_name, city_name)
            self.log('[C策略] 城市匹配结果: {}'.format(target_city_cfg))
            
            if target_city_cfg:
                # 保存当前城市配置为上一个城市配置（用于死亡检测后的下一站选择）
                self.ctx.previous_city_config = target_city_cfg
                self.log('[C策略] 城市匹配成功: 「{}」'.format(city_name))
                result, next_sea = self.city_strategy.handle_strategy_c_start(sea_name, city_name)
                
                if result:
                    if next_sea:
                        self.ctx.next_target_sea = next_sea
                        self.log('[状态机] 设置下一个目标海域: 「{}」'.format(next_sea))
                    
                    # 检查是否是V3-liuxing模式
                    is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
                    
                    if is_liuxing_mode:
                        self.log('[状态机] 从C策略跳转，等待A状态标识出现或城市变更（最长30秒）...')
                        wait_result, detected_city, detected_sea = self._wait_for_a_state_or_city_change(30, sea_name, city_name)
                        if not self.ctx.running:
                            return False
                        if wait_result:
                            if detected_city and detected_sea:
                                self.log('[状态机] 检测到城市变更为: 「{}」海域「{}」，直接进入C策略'.format(detected_sea, detected_city))
                                # 保存当前城市配置为上一个城市配置（用于死亡检测后的下一站选择）
                                new_target_city_cfg = self._find_matching_city_config(detected_sea, detected_city)
                                if new_target_city_cfg:
                                    self.ctx.previous_city_config = new_target_city_cfg
                                self.ctx.state = VoyageState.STRATEGY_C
                                self.ctx.last_c_state_time = time.time()
                            else:
                                self.ctx.state = VoyageState.STRATEGY_A
                                self.ctx.last_c_state_time = time.time()
                                self.log('[状态机] 检测到A状态，进入A策略')
                        else:
                            self.log('[状态机] 等待超时，进入状态检测')
                            self.ctx.state = VoyageState.INIT
                            self.ctx.state_detection_start_time = 0.0
                    else:
                        # 远洋V3模式使用原来的逻辑
                        self.log('[状态机] 从C策略跳转至A策略，等待A状态标识出现（最长30秒）...')
                        wait_result = self._wait_for_a_state(30)
                        if not self.ctx.running:
                            return False
                        if wait_result:
                            self.ctx.state = VoyageState.STRATEGY_A
                            self.ctx.last_c_state_time = time.time()
                            self.log('[状态机] 检测到A状态，进入A策略')
                        else:
                            self.log('[状态机] 等待超时，进入状态检测')
                            self.ctx.state = VoyageState.INIT
                            self.ctx.state_detection_start_time = 0.0
                    return True
                else:
                    self.log('[C策略] 策略段执行失败，进入状态判定')
                    self.ctx.state = VoyageState.INIT
                    return True
            
            # 2. 检查海域是否匹配配置（城市不匹配）
            sea_matched_cfg = self._find_matching_sea_config(sea_name)
            
            if sea_matched_cfg:
                # 保存海域匹配的配置为上一个城市配置（用于死亡检测后的下一站选择）
                self.ctx.previous_city_config = sea_matched_cfg
                self.log('[C策略] 城市不匹配但海域匹配: 「{}」，执行固定操作流程'.format(sea_name))
                result = self.city_strategy.handle_strategy_c_sea_matched(sea_name, sea_matched_cfg)
                
                if result:
                    # 检查是否是V3-liuxing模式
                    is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
                    
                    if is_liuxing_mode:
                        self.log('[状态机] 从C策略跳转，等待A状态标识出现或城市变更（最长30秒）...')
                        wait_result, detected_city, detected_sea = self._wait_for_a_state_or_city_change(30)
                        if not self.ctx.running:
                            return False
                        if wait_result:
                            if detected_city and detected_sea:
                                self.log('[状态机] 检测到城市变更为: 「{}」海域「{}」，直接进入C策略'.format(detected_sea, detected_city))
                                # 保存当前城市配置为上一个城市配置（用于死亡检测后的下一站选择）
                                new_target_city_cfg = self._find_matching_city_config(detected_sea, detected_city)
                                if new_target_city_cfg:
                                    self.ctx.previous_city_config = new_target_city_cfg
                                self.ctx.state = VoyageState.STRATEGY_C
                                self.ctx.last_c_state_time = time.time()
                            else:
                                self.ctx.state = VoyageState.STRATEGY_A
                                self.ctx.last_c_state_time = time.time()
                                self.log('[状态机] 检测到A状态，进入A策略')
                        else:
                            self.log('[状态机] 等待超时，进入状态检测')
                            self.ctx.state = VoyageState.INIT
                            self.ctx.state_detection_start_time = 0.0
                    else:
                        # 远洋V3模式使用原来的逻辑
                        self.log('[状态机] 从C策略跳转至A策略，等待A状态标识出现（最长30秒）...')
                        wait_result = self._wait_for_a_state(30)
                        if not self.ctx.running:
                            return False
                        if wait_result:
                            self.ctx.state = VoyageState.STRATEGY_A
                            self.ctx.last_c_state_time = time.time()
                            self.log('[状态机] 检测到A状态，进入A策略')
                        else:
                            self.log('[状态机] 等待超时，进入状态检测')
                            self.ctx.state = VoyageState.INIT
                            self.ctx.state_detection_start_time = 0.0
                    return True
                else:
                    self.log('[C策略] 固定操作流程执行失败，进入状态判定')
                    self.ctx.state = VoyageState.INIT
                    return True
            
            # 3. 城市和海域都不匹配，自动停止航行
            self.log('[C策略] 城市和海域都不匹配配置，自动停止航行')
            self.log('[C策略] 当前位置: 海域「{}」，城市「{}」'.format(sea_name, city_name))
            self.ctx.state = VoyageState.STOPPED
            self.ctx.running = False
            return False
        except Exception as e:
            self.log('[C策略] 执行C策略时发生错误: {}'.format(str(e)))
            logger.exception('[C策略] 执行异常')
            return True
    
    def _find_matching_sea_config(self, sea_name: str) -> Optional[Any]:
        """查找匹配的海域配置（返回该海域的第一个配置）"""
        if self.config.ocean_v3_config:
            for city_cfg in self.config.ocean_v3_config.cities:
                if city_cfg.sea == sea_name:
                    return city_cfg
        elif self.config.ocean_v3_liuxing_config:
            for city_cfg in self.config.ocean_v3_liuxing_config.cities:
                if city_cfg.sea == sea_name:
                    return city_cfg
        return None
    
    def _find_matching_city_config(self, sea_name: str, city_name: str) -> Optional[Any]:
        """查找匹配的城市配置"""
        if self.config.ocean_v3_config:
            for city_cfg in self.config.ocean_v3_config.cities:
                if city_cfg.sea == sea_name and city_cfg.city == city_name:
                    return city_cfg
        elif self.config.ocean_v3_liuxing_config:
            for city_cfg in self.config.ocean_v3_liuxing_config.cities:
                if city_cfg.sea == sea_name and city_cfg.city == city_name:
                    return city_cfg
        return None
    
    def _run_error_check(self) -> bool:
        """
        死亡检测
        
        V3-liuxing模式：直接跳回状态检测，不执行死亡检测
        远洋V3模式：执行死亡检测流程
        流程：
        1. 等待1秒
        2. 执行一轮"画面复位操作"
        3. 等待1秒
        4. 检测死亡标识物是否存在（imgsG/jiuzhu.png）
        5. 存在则点击并执行"死亡复位脚本"，脚本执行完毕后跳转状态检测
        6. 不存在则直接跳转状态检测
        7. 连续3轮状态检测及死亡检测后仍无法触发，停止航行
        """
        # 检查是否是V3-liuxing模式
        is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
        
        if is_liuxing_mode:
            # V3-liuxing模式：直接跳回状态检测，不执行死亡检测
            self.log('[死亡检测] V3-liuxing模式：不执行死亡检测，跳转状态检测')
            self.ctx.state = VoyageState.INIT
            self.ctx.state_detection_start_time = 0.0
            self.ctx.death_check_count = 0
            return True
        
        # 远洋V3模式：继续执行原来的死亡检测流程
        self.log('[死亡检测] 开始执行死亡检测流程 (第{}次)'.format(self.ctx.death_check_count + 1))
        
        # 检查是否已停止
        if not self.ctx.running:
            return False
        
        # 1. 等待1秒（可中断）
        for _ in range(10):
            time.sleep(0.1)
            if not self.ctx.running:
                return False
        
        # 检查是否已停止
        if not self.ctx.running:
            return False
        
        # 2. 执行画面复位操作
        self.log('[死亡检测] 执行画面复位操作')
        self._execute_view_reset()
        
        # 检查是否已停止
        if not self.ctx.running:
            return False
        
        # 3. 等待1秒（可中断）
        for _ in range(10):
            time.sleep(0.1)
            if not self.ctx.running:
                return False
        
        # 4. 检测死亡标识物
        screenshot, capture_offset = self.detector.take_screenshot()
        if screenshot is None:
            self.log('[死亡检测] 截图失败，跳转状态检测')
            self.ctx.state = VoyageState.INIT
            self.ctx.state_detection_start_time = 0.0
            return True
        
        death_detected = self._check_death(screenshot, capture_offset)
        
        if death_detected:
            self.log('[死亡检测] 检测到死亡标识，执行死亡复位')
            # 点击死亡标识
            self._click_death_icon(screenshot, capture_offset)
            # 执行死亡复位脚本（已包含下一站选择功能）
            self._execute_death_reset()
            
            self.ctx.death_check_count = 0
            self.ctx.state_detection_fail_count = 0
        else:
            self.log('[死亡检测] 未检测到死亡标识')
        
        # 检查是否达到最大检测次数
        self.ctx.death_check_count += 1
        if self.ctx.death_check_count >= self.ctx.max_death_check_count:
            self.log('[死亡检测] 连续{}轮检测失败，停止航行'.format(self.ctx.max_death_check_count))
            self.ctx.state = VoyageState.STOPPED
            self.ctx.running = False
            return False
        
        # 跳转状态检测
        self.log('[死亡检测] 跳转状态检测')
        self.ctx.state = VoyageState.INIT
        self.ctx.state_detection_start_time = 0.0
        return True
    
    def _execute_view_reset(self):
        """执行画面复位操作"""
        reset_script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'system_scripts', 'fuwei.json5'
        )
        
        if os.path.isfile(reset_script_path):
            try:
                self.log('[死亡检测] 执行画面复位脚本')
                self.script_executor.execute(reset_script_path, wait=True)
                self.log('[死亡检测] 画面复位完成')
            except Exception as e:
                self.log('[死亡检测] 画面复位异常: {}'.format(e))
        else:
            self.log('[死亡检测] 画面复位脚本不存在')
    
    def _check_death(self, screenshot, capture_offset) -> bool:
        """检测是否死亡"""
        death_trigger_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'imgsG', 'jiuzhu.png'
        )
        
        if not os.path.isfile(death_trigger_path):
            self.log('[死亡检测] 死亡触发图不存在: {}'.format(death_trigger_path))
            return False
        
        result = self.detector.detect_single(death_trigger_path, screenshot, capture_offset)
        return result is not None
    
    def _click_death_icon(self, screenshot, capture_offset):
        """点击死亡图标"""
        death_trigger_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'imgsG', 'jiuzhu.png'
        )
        
        result = self.detector.detect_single(death_trigger_path, screenshot, capture_offset)
        if result:
            x, y = result
            self.log('[死亡检测] 点击死亡图标: ({}, {})'.format(x, y))
            self.detector.click_at(x, y)
            time.sleep(1.0)
    
    def _execute_death_reset(self):
        """执行死亡复位脚本"""
        # 首先尝试执行增强脚本版本的死亡复位脚本
        death_reset_script_name = '死亡复位脚本'
        death_reset_path = self._get_enhanced_script_path(death_reset_script_name)
        
        if death_reset_path and os.path.isfile(death_reset_path):
            self.log('[死亡检测] 执行死亡复位脚本: {}'.format(death_reset_path))
            
            # 获取上一个城市配置的下一个城市信息
            if self.ctx.previous_city_config and self.config.ocean_v3_config:
                cities = self.config.ocean_v3_config.cities
                if cities:
                    current_idx = -1
                    for i, cfg in enumerate(cities):
                        if cfg.city_index == self.ctx.previous_city_config.city_index:
                            current_idx = i
                            break
                    
                    next_city_cfg = None
                    if current_idx >= 0:
                        for offset in range(1, len(cities) + 1):
                            next_idx = (current_idx + offset) % len(cities)
                            next_city = cities[next_idx]
                            if next_city.sea and next_city.city:
                                next_city_cfg = next_city
                                break
                    
                    if next_city_cfg:
                        # 设置上下文变量，默认使用"指定城市"模式
                        context = {
                            'next_stop_strategy': 'specified',
                            'next_sea': next_city_cfg.sea,
                            'next_city': next_city_cfg.city,
                        }
                        self.log('[死亡检测] 设置上下文: {}'.format(context))
                        self.enhanced_script_executor.set_context(context)
            
            # 执行脚本
            script = self.enhanced_script_executor.load_from_file(death_reset_path)
            if script:
                result = self.enhanced_script_executor.execute(script)
                self.log('[死亡检测] 死亡复位脚本执行结果: {}'.format(result))
            else:
                self.log('[死亡检测] 加载死亡复位脚本失败')
        else:
            # 回退到旧的 system_scripts 目录
            death_reset_path_old = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'system_scripts', 'death_reset.json5'
            )
            
            if os.path.isfile(death_reset_path_old):
                self.log('[死亡检测] 执行死亡复位脚本(旧版): {}'.format(death_reset_path_old))
                self.script_executor.execute(death_reset_path_old, wait=True)
                self.log('[死亡检测] 死亡复位脚本执行完成')
            else:
                self.log('[死亡检测] 死亡复位脚本不存在，跳过')
    
    def _execute_next_stop_after_death(self, city_cfg: Any):
        """
        死亡检测后执行下一站选择（只执行下一站选择，不包括入港固定操作和买卖操作）
        
        :param city_cfg: 城市配置
        """
        # 检查是否已停止
        if not self.ctx.running:
            return
        
        if not city_cfg:
            self.log('[死亡检测] 城市配置为空，跳过下一站选择')
            return
        
        # 获取下一个城市配置
        next_city_cfg = None
        if self.config.ocean_v3_config:
            cities = self.config.ocean_v3_config.cities
            if cities:
                current_idx = -1
                for i, cfg in enumerate(cities):
                    if cfg.city_index == city_cfg.city_index:
                        current_idx = i
                        break
                
                if current_idx >= 0:
                    # 查找下一个有效的城市配置（跳过空配置）
                    for offset in range(1, len(cities) + 1):
                        next_idx = (current_idx + offset) % len(cities)
                        next_city = cities[next_idx]
                        if next_city.sea and next_city.city:
                            next_city_cfg = next_city
                            break
        
        # 检查是否已停止
        if not self.ctx.running:
            return
        
        if next_city_cfg:
            context = {
                'next_stop_strategy': city_cfg.next_stop_strategy,
                'next_sea': next_city_cfg.sea,
                'next_city': next_city_cfg.city,
            }
            
            self.log('[死亡检测] 下一站策略：{}，目标海域: {}，目标城市: {}'.format(
                city_cfg.next_stop_strategy, next_city_cfg.sea, next_city_cfg.city))
            
            # 执行增强脚本：下一站选择
            script_name = '下一站选择'
            script_path = self._get_enhanced_script_path(script_name)
            
            if script_path and os.path.isfile(script_path):
                self.log('[死亡检测] 准备执行脚本: {}'.format(script_name))
                if self.enhanced_script_executor:
                    script = self.enhanced_script_executor.load_from_file(script_path)
                    if script:
                        self.log('[死亡检测] 脚本加载成功，步骤数: {}'.format(len(script.steps)))
                        if context:
                            self.log('[死亡检测] 设置上下文: {}'.format(context))
                            self.enhanced_script_executor.set_context(context)
                        
                        # 检查是否已停止
                        if not self.ctx.running:
                            return
                        
                        self.log('[死亡检测] 开始执行脚本...')
                        result = self.enhanced_script_executor.execute(script)
                        self.log('[死亡检测] 脚本执行结果: {}'.format(result))
                    else:
                        self.log('[死亡检测] 加载脚本失败: {}'.format(script_name))
                else:
                    self.log('[死亡检测] 增强脚本执行器未初始化!')
            else:
                self.log('[死亡检测] 脚本不存在: {}'.format(script_name))
        else:
            self.log('[死亡检测] 未找到下一个城市配置')
    
    def _get_enhanced_script_path(self, script_name: str):
        """获取增强脚本路径"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        scripts_enhanced_dir = os.path.join(base_dir, 'scripts_enhanced')
        script_path_json5 = os.path.join(scripts_enhanced_dir, f'{script_name}.json5')
        if os.path.isfile(script_path_json5):
            return script_path_json5
        
        # 其次检查 scripts 文件夹（.json 格式）
        scripts_dir = os.path.join(base_dir, 'scripts')
        script_path_json = os.path.join(scripts_dir, f'{script_name}.json')
        return script_path_json if os.path.isfile(script_path_json) else None
