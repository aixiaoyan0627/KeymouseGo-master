# -*- encoding:utf-8 -*-
"""
流行V3-liuxing策略模块：城市1-8闭环执行
- 支持流行单线和流行搓搓两种模式
- 不执行到港固定操作
- 强制指定城市策略
"""
import os
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
from loguru import logger

from .config import OceanV3LiuxingConfig, OceanCityV3LiuxingConfig
from .strategies import IVoyageStrategy, StrategyContext
from .detector import ImageDetector
from .action_executor import ActionExecutor


@dataclass
class OceanV3LiuxingStrategyContext:
    """V3-liuxing策略上下文"""
    current_city_index: int = 1  # 当前正在处理的城市索引
    in_auto_selected_city: bool = False  # 是否处于自动选择的城市中
    cycle_next_to_city1: bool = False  # 搓搓模式下，下一个是否跳转到城市1
    start_time: float = 0.0  # 开始航行时间
    duration_minutes: int = 0  # 时长设置（分钟）


class OceanV3LiuxingStrategy(IVoyageStrategy):
    """流行V3-liuxing策略：城市1-8闭环执行
    
    执行流程：
    1. 检测当前所在城市，匹配到城市N
    2. 从城市N开始执行闭环
    3. 执行买卖操作 → 下一站选择-指定城市
    4. 等待到达下一个城市，继续执行
    
    流行单线模式（single）：
    - 跳转规则与远洋相同（1→2→3→...→8→1）
    
    流行搓搓模式（cycle）：
    - 跳转规则为 1→2→1→3→1→4→...→1→8→1→2...
    
    配置关联规则：
    - 城市N的下一站使用城市N+1的配置
    - 城市8使用城市1的配置
    """
    
    def __init__(
        self,
        ocean_config: OceanV3LiuxingConfig,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        city_image_paths: List[str],
        imgsc_root: str,
        script_next_stop_specified: str = '',
        on_script_execute: Optional[Callable[[str], None]] = None,
        on_set_context_var: Optional[Callable[[str, str], None]] = None,
    ):
        self.ocean_config = ocean_config
        self.detector = detector
        self.action_executor = action_executor
        self.city_image_paths = city_image_paths
        self.imgsc_root = imgsc_root
        self.script_next_stop_specified = script_next_stop_specified
        self.on_script_execute = on_script_execute
        self.on_set_context_var = on_set_context_var
        self.v3_ctx = OceanV3LiuxingStrategyContext()
        self.v3_ctx.duration_minutes = ocean_config.duration_minutes
        self._city_path_to_index: dict = {}
        self._build_city_index_map()
    
    def _build_city_index_map(self):
        """建立城市图片路径到索引的映射"""
        for city_cfg in self.ocean_config.cities:
            if city_cfg.sea and city_cfg.city:
                img_path = os.path.join(self.imgsc_root, city_cfg.sea, f'{city_cfg.city}.png')
                if os.path.exists(img_path):
                    self._city_path_to_index[os.path.normpath(img_path)] = city_cfg.city_index
    
    def _get_next_city_cfg(self, current_index: int) -> Optional[OceanCityV3LiuxingConfig]:
        """获取下一个城市配置（根据模式返回不同的下一个城市）"""
        if not self.ocean_config.cities:
            return None
        
        mode = self.ocean_config.mode
        
        if mode == 'single':
            # 流行单线模式：与远洋相同
            current_in_list = -1
            for i, cfg in enumerate(self.ocean_config.cities):
                if cfg.city_index == current_index:
                    current_in_list = i
                    break
            
            if current_in_list < 0:
                return None
            
            next_in_list = (current_in_list + 1) % len(self.ocean_config.cities)
            return self.ocean_config.cities[next_in_list]
        
        else:  # mode == 'cycle'
            # 流行搓搓模式：1→2→1→3→1→4→...
            
            # 先找到有效城市列表（只包含有配置的城市）
            valid_cities = [cfg for cfg in self.ocean_config.cities if cfg.sea and cfg.city]
            if not valid_cities:
                return None
            
            # 找到城市1
            city1 = None
            for cfg in valid_cities:
                if cfg.city_index == 1:
                    city1 = cfg
                    break
            
            if current_index == 1:
                # 当前是城市1，跳转到下一个城市（2, 3, 4...）
                self.v3_ctx.cycle_next_to_city1 = True
                # 找到当前城市1的下一个目标城市
                # 需要知道上一个跳转的城市是哪个
                # 简化版：找到城市1之后的下一个城市
                current_idx = -1
                for i, cfg in enumerate(valid_cities):
                    if cfg.city_index == 1:
                        current_idx = i
                        break
                
                if current_idx >= 0:
                    next_idx = (current_idx + 1) % len(valid_cities)
                    # 如果下一个还是城市1，继续往后找
                    if valid_cities[next_idx].city_index == 1:
                        next_idx = (next_idx + 1) % len(valid_cities)
                    return valid_cities[next_idx]
                return valid_cities[1] if len(valid_cities) > 1 else city1
            else:
                # 当前不是城市1，跳回到城市1
                self.v3_ctx.cycle_next_to_city1 = False
                return city1
    
    def _handle_matched_city(self, matched_path: str):
        """处理匹配到的城市"""
        norm_path = os.path.normpath(matched_path)
        city_index = self._city_path_to_index.get(norm_path)
        if city_index is None:
            logger.warning(f'匹配到未知城市图片: {matched_path}')
            return
        
        self.v3_ctx.current_city_index = city_index
        logger.info(f'匹配到城市{city_index}')
        
        # 找到对应的配置
        city_cfg = None
        for cfg in self.ocean_config.cities:
            if cfg.city_index == city_index:
                city_cfg = cfg
                break
        
        if city_cfg:
            self._execute_city_segment(city_cfg)
    
    def _execute_city_segment(self, city_cfg: OceanCityV3LiuxingConfig):
        """执行城市段闭环（不执行到港固定操作）"""
        logger.info(f'开始执行城市{city_cfg.city_index}段')
        
        # 1. 执行买卖操作（直接执行，不执行到港固定）
        if city_cfg.script_trade and self.on_script_execute:
            self.on_script_execute(city_cfg.script_trade)
        
        # 2. 执行下一站选择-指定城市（强制）
        self._execute_next_stop(city_cfg)
    
    def _execute_next_stop(self, city_cfg: OceanCityV3LiuxingConfig):
        """执行下一站选择（强制指定城市）"""
        # 获取下一个城市配置（用于提供海域/城市信息）
        next_city_cfg = self._get_next_city_cfg(city_cfg.city_index)
        
        if not next_city_cfg:
            logger.warning('找不到下一个城市配置')
            return
        
        # 设置上下文变量
        if self.on_set_context_var:
            # 下一站海域
            if next_city_cfg.sea:
                self.on_set_context_var('next_sea', next_city_cfg.sea)
            # 下一站城市（强制指定城市）
            if next_city_cfg.city:
                self.on_set_context_var('next_city', next_city_cfg.city)
        
        # 执行指定城市的下一站选择脚本
        if self.script_next_stop_specified and self.on_script_execute:
            logger.info(f'执行下一站选择: 指定城市')
            self.on_script_execute(self.script_next_stop_specified)
    
    def _check_duration_timeout(self, current_time: float) -> bool:
        """检查是否时长超时"""
        if self.v3_ctx.duration_minutes <= 0:
            return False
        
        elapsed_seconds = current_time - self.v3_ctx.start_time
        elapsed_minutes = elapsed_seconds / 60.0
        
        if elapsed_minutes >= self.v3_ctx.duration_minutes:
            logger.info(f'时长超时: {elapsed_minutes:.1f}分钟 >= {self.v3_ctx.duration_minutes}分钟')
            return True
        
        return False
    
    def run_in_city_step(self, screenshot, capture_offset, ctx: StrategyContext):
        """在城市状态下执行一步
        
        Returns:
            bool: 是否继续保持城市状态
        """
        # 检查时长超时
        import time
        current_time = time.time()
        if self._check_duration_timeout(current_time):
            # 超时了，停止航行
            ctx.should_stop = True
            return False
        
        matched_path = self.detector.detect_class_c(self.city_image_paths, screenshot, capture_offset)
        if matched_path:
            self._handle_matched_city(matched_path)
            return False
        return True
    
    def run_in_sailing_step(self, screenshot, capture_offset, ctx: StrategyContext):
        """在航行状态下执行一步
        
        Returns:
            bool: 是否继续保持航行状态
        """
        # 检查时长超时
        import time
        current_time = time.time()
        if self._check_duration_timeout(current_time):
            # 超时了，停止航行
            ctx.should_stop = True
            return False
        
        # 航行中不需要特殊处理，只需要等待进入城市
        return True
    
    def reset(self):
        """重置策略状态"""
        import time
        self.v3_ctx = OceanV3LiuxingStrategyContext()
        self.v3_ctx.duration_minutes = self.ocean_config.duration_minutes
        self.v3_ctx.start_time = time.time()
        logger.info('V3-liuxing策略已重置')
