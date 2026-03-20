# -*- encoding:utf-8 -*-
"""
航行策略模块：定义策略接口和具体策略实现

策略接口：
- IVoyageStrategy: 所有航行策略的接口

策略实现：
- OceanStrategy: 远洋策略
- PopularSingleStrategy: 流行-单线策略
- PopularCycleStrategy: 流行-搓搓策略
- DeathStrategy: 死亡处理策略
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Callable, List
from dataclasses import dataclass, field
import os
import time
import random

from loguru import logger

from .config import DetectionConfig, OceanV2Config, OceanRouteConfig, get_c_image_path
from .detector import ImageDetector, get_sea_name_from_path
from .action_executor import ActionExecutor


@dataclass
class StrategyContext:
    """策略上下文，共享给策略的状态信息"""
    consecutive_a_miss: int = 0
    last_double_click_time: float = 0.0
    main_script_index: int = 0


class IVoyageStrategy(ABC):
    """航行策略接口"""
    
    @abstractmethod
    def initialize(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        初始化策略
        
        :param config: 航行配置
        :param detector: 图像检测器
        :param action_executor: 动作执行器
        :param log_callback: 日志回调
        :param script_callback: 脚本执行回调
        :return: 是否初始化成功
        """
        pass
    
    @abstractmethod
    def on_enter_sailing(self) -> None:
        """进入航行状态（SAILING）时调用"""
        pass
    
    @abstractmethod
    def on_enter_in_city(self) -> None:
        """进入城市状态（IN_CITY）时调用"""
        pass
    
    @abstractmethod
    def run_sailing_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """
        航行状态（SAILING）单步执行
        
        :param screenshot: 屏幕截图
        :param capture_offset: 截图偏移
        :param ctx: 策略上下文
        :return: 是否继续在SAILING状态（False表示离开）
        """
        pass
    
    @abstractmethod
    def run_in_city_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """
        城市状态（IN_CITY）单步执行
        
        :param screenshot: 屏幕截图
        :param capture_offset: 截图偏移
        :param ctx: 策略上下文
        :return: 是否继续在IN_CITY状态（False表示离开）
        """
        pass


class BaseStrategy(IVoyageStrategy):
    """策略基类，提供通用功能"""
    
    def __init__(self):
        self.config: Optional[DetectionConfig] = None
        self.detector: Optional[ImageDetector] = None
        self.action_executor: Optional[ActionExecutor] = None
        self.log: Callable[[str], None] = print
        self.on_script_execute: Optional[Callable[[str], None]] = None
        
        self.a_paths: List[str] = []
        self.b_paths: List[str] = []
        self.c_all_paths: List[str] = []
    
    def initialize(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        self.config = config
        self.detector = detector
        self.action_executor = action_executor
        self.log = log_callback or print
        self.on_script_execute = script_callback
        
        self._init_paths()
        return True
    
    def _init_paths(self):
        """初始化图片路径"""
        self.a_paths = [p for p in self.config.image_a_paths if p and os.path.isfile(p)]
        self.b_paths = [p for p in self.config.image_b_paths if p and os.path.isfile(p)]
        
        from .detector import get_all_c_images
        self.c_all_paths = get_all_c_images(self.config.imgsc_root_path)
        
        logger.debug('A类图片路径: {}', self.a_paths)
        logger.debug('B类图片路径: {}', self.b_paths)
        logger.debug('C类所有图片数量: {}', len(self.c_all_paths))
    
    def on_enter_sailing(self) -> None:
        pass
    
    def on_enter_in_city(self) -> None:
        pass


class OceanStrategy(BaseStrategy):
    """远洋策略"""
    
    def __init__(self):
        super().__init__()
        self.c_start_sea_paths: List[str] = []
        self.c_transit_sea_paths: List[str] = []
        self.c_back_sea_paths: List[str] = []
        self.c_specified_paths: List[str] = []
        self.c_start_path: str = ''
        self.c_transit_path: str = ''
        self.c_back_path: str = ''
        
        self.double_click_position: Optional[Tuple[int, int]] = None
    
    def initialize(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if not super().initialize(config, detector, action_executor, log_callback, script_callback):
            return False
        
        self._init_ocean_paths()
        return True
    
    def _init_ocean_paths(self):
        """初始化远洋模式特有的路径"""
        self.c_start_sea_paths = [p for p in self.config.c_start_sea_paths if p and os.path.isfile(p)]
        self.c_transit_sea_paths = [p for p in self.config.c_transit_sea_paths if p and os.path.isfile(p)]
        self.c_back_sea_paths = [p for p in self.config.c_back_sea_paths if p and os.path.isfile(p)]
        
        self.c_start_path = os.path.normpath(self.config.c_start_path) if self.config.c_start_path and os.path.isfile(self.config.c_start_path) else ''
        self.c_transit_path = os.path.normpath(self.config.c_transit_path) if self.config.c_transit_path and os.path.isfile(self.config.c_transit_path) else ''
        self.c_back_path = os.path.normpath(self.config.c_back_path) if self.config.c_back_path and os.path.isfile(self.config.c_back_path) else ''
        
        self.c_specified_paths = []
        self.c_specified_paths.extend(self.c_start_sea_paths)
        self.c_specified_paths.extend(self.c_transit_sea_paths)
        self.c_specified_paths.extend(self.c_back_sea_paths)
    
    def on_enter_sailing(self) -> None:
        self.log('[远洋] 进入航行状态')
    
    def on_enter_in_city(self) -> None:
        self.log('[远洋] 进入城市状态')
    
    def run_sailing_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """航行状态（A状态）单步执行"""
        
        a_detected = self.detector.detect_class_a(self.a_paths, screenshot, capture_offset)
        
        if not a_detected:
            ctx.consecutive_a_miss += 1
            
            if ctx.consecutive_a_miss >= 20:
                self.log('[远洋] 10秒未检测到航行状态，离开A状态')
                return False
            
            self.log('[远洋] 未检测到航行状态（{}/20）'.format(ctx.consecutive_a_miss))
            return True
        
        ctx.consecutive_a_miss = 0
        self.log('[远洋] 正在航行中')
        
        self._handle_b_class_detection(screenshot, capture_offset)
        
        current_time = time.time()
        if current_time - ctx.last_double_click_time >= 5:
            if self.double_click_position:
                self.log('[远洋] 执行双击（{}, {}）'.format(self.double_click_position[0], self.double_click_position[1]))
                self.action_executor.double_click_at(self.double_click_position[0], self.double_click_position[1])
            ctx.last_double_click_time = current_time
        
        return True
    
    def _handle_b_class_detection(self, screenshot, capture_offset):
        """处理B类图片检测"""
        results = self.detector.detect_class_b(self.b_paths, screenshot, capture_offset)
        
        for result in results:
            name = os.path.basename(result.path)
            base = os.path.splitext(name)[0]
            
            if result.folder_name.lower() == 'instant':
                self.log('[远洋] 点击"{}"（立即）'.format(base))
                self.action_executor.click_at(result.position[0], result.position[1])
            else:
                random_delay = random.uniform(0.5, 1.5)
                self.log('[远洋] 点击"{}"（延迟{:.2f}秒）'.format(base, random_delay))
                time.sleep(random_delay)
                self.action_executor.click_at(result.position[0], result.position[1])
    
    def run_in_city_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """城市状态（C状态）单步执行"""
        
        matched_c = self.detector.detect_class_c(self.c_specified_paths, screenshot, capture_offset)
        
        if matched_c:
            self._handle_city_detected(matched_c)
            return False
        
        return True
    
    def _handle_city_detected(self, matched_c_path: str):
        """处理检测到城市的情况"""
        from .detector import get_sea_name_from_path
        
        sea_name = get_sea_name_from_path(matched_c_path, self.config.imgsc_root_path)
        self.log('[远洋] 当前处于「{}」海域'.format(sea_name))
        
        city_name = os.path.splitext(os.path.basename(matched_c_path))[0]
        
        script_path = self._determine_script(matched_c_path, city_name)
        
        if script_path:
            self.log('[远洋] 执行脚本: {}'.format(os.path.basename(script_path)))
            if self.on_script_execute:
                self.on_script_execute(script_path)
    
    def _determine_script(self, matched_c_path: str, city_name: str) -> Optional[str]:
        """确定要执行的脚本"""
        norm_matched = os.path.normpath(matched_c_path)
        
        if norm_matched == self.c_start_path:
            self.log('[远洋] 当前所在城市为「{}」，是处于「始发地」'.format(city_name))
            return self.config.script_start_arrived
        elif norm_matched == self.c_transit_path:
            self.log('[远洋] 当前所在城市为「{}」，是处于「中转地」'.format(city_name))
            return self.config.script_transit_arrived
        elif norm_matched == self.c_back_path:
            self.log('[远洋] 当前所在城市为「{}」，是处于「回程地」'.format(city_name))
            return self.config.script_back_arrived
        
        if matched_c_path in self.c_start_sea_paths or norm_matched in [os.path.normpath(p) for p in self.c_start_sea_paths]:
            self.log('[远洋] 当前所在城市为「{}」，否处于「始发地」'.format(city_name))
            return self.config.script_start_not_arrived
        elif matched_c_path in self.c_transit_sea_paths or norm_matched in [os.path.normpath(p) for p in self.c_transit_sea_paths]:
            self.log('[远洋] 当前所在城市为「{}」，否处于「中转地」'.format(city_name))
            return self.config.script_transit_not_arrived
        elif matched_c_path in self.c_back_sea_paths or norm_matched in [os.path.normpath(p) for p in self.c_back_sea_paths]:
            self.log('[远洋] 当前所在城市为「{}」，否处于「回程地」'.format(city_name))
            return self.config.script_back_not_arrived
        
        return None


@dataclass
class RouteSegment:
    """单个航线分段状态"""
    route_id: int
    buy_city_path: str = ''
    buy_auto_sea_paths: List[str] = field(default_factory=list)
    sell_city_path: str = ''
    sell_auto_sea_paths: List[str] = field(default_factory=list)
    script_dock_fixed: str = ''
    script_trade: str = ''
    script_next_stop_specified: str = ''
    script_next_stop_auto: str = ''


class OceanMultiRouteStrategy(BaseStrategy):
    """新架构多航线策略：分段式执行策略
    
    特点：
    - 支持多条航线，分段执行
    - 执行完航线1 → 航线2 → 航线3 → 航线4 → 循环
    - 支持自动选择最高价（卖出时只要是指定海域的任一城市即匹配）
    - 可以从任意匹配的航线开始执行
    """
    
    def __init__(self, ocean_config: Optional[OceanV2Config] = None):
        super().__init__()
        self.ocean_config = ocean_config or OceanV2Config()
        self.current_route_index = 0
        self.route_segments = []
        self.in_buy_phase = True
        self.c_all_paths = []
    
    def set_ocean_config(self, ocean_config: OceanV2Config):
        """设置新架构远洋配置"""
        self.ocean_config = ocean_config
    
    def initialize(
        self,
        config: DetectionConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        log_callback: Optional[Callable[[str], None]] = None,
        script_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        if not super().initialize(config, detector, action_executor, log_callback, script_callback):
            return False
        
        self._init_routes()
        self._init_paths()
        return True
    
    def _init_routes(self):
        """从OceanV2Config初始化航线分段"""
        self.route_segments = []
        
        for route in self.ocean_config.routes:
            segment = RouteSegment(
                route_id=route.route_id,
                script_dock_fixed=route.script_dock_fixed,
                script_trade=route.script_trade,
                script_next_stop_specified=route.script_next_stop_specified,
                script_next_stop_auto=route.script_next_stop_auto,
            )
            
            if route.buy.sea and route.buy.city:
                segment.buy_city_path = get_c_image_path(
                    self.config.imgsc_root_path,
                    route.buy.sea,
                    route.buy.city
                )
                segment.buy_auto_sea_paths = self._get_sea_all_paths(route.buy.sea)
            
            if route.sell.sea:
                if route.sell.use_auto_select:
                    segment.sell_auto_sea_paths = self._get_sea_all_paths(route.sell.sea)
                else:
                    segment.sell_city_path = get_c_image_path(
                        self.config.imgsc_root_path,
                        route.sell.sea,
                        route.sell.city
                    )
            
            self.route_segments.append(segment)
        
        self.current_route_index = 0
        self.in_buy_phase = True
        
        logger.info('Initialized {} route segments', len(self.route_segments))
    
    def _get_sea_all_paths(self, sea: str) -> List[str]:
        """获取指定海域的所有城市图片路径"""
        result = []
        if not sea or not self.config.imgsc_root_path:
            return result
        
        sea_dir = os.path.join(self.config.imgsc_root_path, sea)
        if os.path.isdir(sea_dir):
            for f in os.listdir(sea_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    result.append(os.path.join(sea_dir, f))
        return result
    
    def _init_paths(self):
        """初始化A/B/C类图片路径"""
        from .detector import get_all_c_images
        self.c_all_paths = get_all_c_images(self.config.imgsc_root_path)
        self.a_paths = [p for p in self.config.image_a_paths if p and os.path.isfile(p)]
        self.b_paths = [p for p in self.config.image_b_paths if p and os.path.isfile(p)]
        
        self.log('[多航线] A类图片数量: {}', len(self.a_paths))
        self.log('[多航线] B类图片数量: {}', len(self.b_paths))
        self.log('[多航线] C类图片数量: {}', len(self.c_all_paths))
    
    def on_enter_sailing(self) -> None:
        current_segment = self._get_current_segment()
        phase = '买入' if self.in_buy_phase else '卖出'
        self.log('[多航线] 进入航行状态，航线{} - {}阶段'.format(
            current_segment.route_id if current_segment else '?', phase))
    
    def on_enter_in_city(self) -> None:
        current_segment = self._get_current_segment()
        phase = '买入' if self.in_buy_phase else '卖出'
        self.log('[多航线] 进入城市状态，航线{} - {}阶段'.format(
            current_segment.route_id if current_segment else '?', phase))
    
    def _get_current_segment(self) -> Optional[RouteSegment]:
        if not self.route_segments:
            return None
        if self.current_route_index < len(self.route_segments):
            return self.route_segments[self.current_route_index]
        return None
    
    def _advance_to_next_segment(self):
        if not self.route_segments:
            return
        
        if self.in_buy_phase:
            self.in_buy_phase = False
            self.log('[多航线] 买入完成，进入卖出阶段')
        else:
            self.current_route_index = (self.current_route_index + 1) % len(self.route_segments)
            self.in_buy_phase = True
            self.log('[多航线] 航线{}完成，进入航线{} - 买入阶段'.format(
                self.current_route_index + 1, self.current_route_index + 1
            ))
    
    def run_sailing_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """航行状态（A状态）单步执行"""
        
        a_detected = self.detector.detect_class_a(self.a_paths, screenshot, capture_offset)
        
        if not a_detected:
            ctx.consecutive_a_miss += 1
            
            if ctx.consecutive_a_miss >= 20:
                self.log('[多航线] 10秒未检测到航行状态，离开A状态')
                return False
            
            self.log('[多航线] 未检测到航行状态（{}/20）'.format(ctx.consecutive_a_miss))
            return True
        
        ctx.consecutive_a_miss = 0
        self.log('[多航线] 正在航行中')
        
        self._handle_b_class_detection(screenshot, capture_offset)
        
        current_time = time.time()
        if current_time - ctx.last_double_click_time >= 5:
            if self.double_click_position:
                self.log('[多航线] 执行双击（{}, {}）'.format(self.double_click_position[0], self.double_click_position[1]))
                self.action_executor.double_click_at(self.double_click_position[0], self.double_click_position[1])
            ctx.last_double_click_time = current_time
        
        return True
    
    def _handle_b_class_detection(self, screenshot, capture_offset):
        """处理B类图片检测"""
        results = self.detector.detect_class_b(self.b_paths, screenshot, capture_offset)
        
        for result in results:
            name = os.path.basename(result.path)
            base = os.path.splitext(name)[0]
            
            if result.folder_name.lower() == 'instant':
                self.log('[多航线] 点击"{}"（立即）'.format(base))
                self.action_executor.click_at(result.position[0], result.position[1])
            else:
                random_delay = random.uniform(0.5, 1.5)
                self.log('[多航线] 点击"{}"（延迟{:.2f}秒）'.format(base, random_delay))
                time.sleep(random_delay)
                self.action_executor.click_at(result.position[0], result.position[1])
    
    def run_in_city_step(
        self,
        screenshot,
        capture_offset: Tuple[int, int],
        ctx: StrategyContext,
    ) -> bool:
        """城市状态（C状态）单步执行"""
        
        matched_c = self._detect_city(screenshot, capture_offset)
        
        if matched_c:
            self._handle_city_detected(matched_c)
            return False
        
        return True
    
    def _detect_city(self, screenshot, capture_offset) -> Optional[str]:
        """检测当前城市是否匹配当前分段"""
        current_segment = self._get_current_segment()
        if not current_segment:
            return None
        
        check_paths = []
        if self.in_buy_phase:
            if current_segment.buy_city_path:
                check_paths.append(current_segment.buy_city_path)
            check_paths.extend(current_segment.buy_auto_sea_paths)
        else:
            if current_segment.sell_city_path:
                check_paths.append(current_segment.sell_city_path)
            check_paths.extend(current_segment.sell_auto_sea_paths)
        
        if not check_paths:
            return None
        
        matched = self.detector.detect_class_c(check_paths, screenshot, capture_offset)
        return matched
    
    def _handle_city_detected(self, matched_c_path: str):
        """处理检测到城市的情况"""
        sea_name = get_sea_name_from_path(matched_c_path, self.config.imgsc_root_path)
        city_name = os.path.splitext(os.path.basename(matched_c_path))[0]
        
        current_segment = self._get_current_segment()
        phase = '买入' if self.in_buy_phase else '卖出'
        
        self.log('[多航线] 检测到匹配城市「{}」{}，航线{} - {}阶段'.format(
            city_name, sea_name, current_segment.route_id if current_segment else '?', phase
        ))
        
        script_path = self._determine_script(matched_c_path, current_segment, self.in_buy_phase)
        
        if script_path:
            self.log('[多航线] 执行脚本: {}'.format(os.path.basename(script_path)))
            if self.on_script_execute:
                self.on_script_execute(script_path)
        
        self._advance_to_next_segment()
    
    def _determine_script(self, matched_c_path: str, segment: RouteSegment, is_buy_phase: bool) -> Optional[str]:
        """确定要执行的脚本"""
        if is_buy_phase:
            norm_matched = os.path.normpath(matched_c_path)
            norm_target = os.path.normpath(segment.buy_city_path) if segment.buy_city_path else ''
            
            if segment.buy_city_path and norm_matched == norm_target:
                return segment.buy_script_arrived
            else:
                return segment.buy_script_not_arrived
        else:
            return segment.sell_script_auto if segment.sell_auto_sea_paths else segment.sell_script_arrived

