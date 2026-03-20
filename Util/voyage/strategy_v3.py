# -*- encoding:utf-8 -*-
"""
远洋V3策略模块（调整版）：城市1-8闭环执行

策略说明：
- 每个城市配置：海域/城市/买卖脚本/下一站策略
- 下一站使用下一行城市的配置（城市8使用城市1的）
"""
import os
from typing import List, Optional, Callable, Tuple
from dataclasses import dataclass
from loguru import logger

from .config import OceanV3Config, OceanCityV3Config
from .strategies import IVoyageStrategy, StrategyContext
from .detector import ImageDetector
from .action_executor import ActionExecutor


@dataclass
class OceanV3StrategyContext:
    """V3策略上下文"""
    current_city_index: int = 1  # 当前正在处理的城市索引
    in_auto_selected_city: bool = False  # 是否处于自动选择的城市中


class OceanV3Strategy(IVoyageStrategy):
    """远洋V3策略：城市1-8闭环执行（调整版）
    
    执行流程：
    1. 检测当前所在城市，匹配到城市N
    2. 从城市N开始执行闭环
    3. 执行到港固定 → 买卖操作 → 下一站选择
    4. 等待到达下一个城市，继续执行
    
    配置关联规则：
    - 城市N的下一站使用城市N+1的配置
    - 城市8使用城市1的配置
    """
    
    def __init__(
        self,
        ocean_config: OceanV3Config,
        detector: ImageDetector,
        action_executor: ActionExecutor,
        city_image_paths: List[str],
        imgsc_root: str,
        script_dock_fixed: str = '',
        script_next_stop_specified: str = '',
        script_next_stop_auto: str = '',
        script_auto_trade: str = '',
        on_script_execute: Optional[Callable[[str], None]] = None,
        on_set_context_var: Optional[Callable[[str, str], None]] = None,
    ):
        self.ocean_config = ocean_config
        self.detector = detector
        self.action_executor = action_executor
        self.city_image_paths = city_image_paths
        self.imgsc_root = imgsc_root
        self.script_dock_fixed = script_dock_fixed
        self.script_next_stop_specified = script_next_stop_specified
        self.script_next_stop_auto = script_next_stop_auto
        self.script_auto_trade = script_auto_trade
        self.on_script_execute = on_script_execute
        self.on_set_context_var = on_set_context_var
        self.v3_ctx = OceanV3StrategyContext()
        self._city_path_to_index: dict = {}
        self._build_city_index_map()
    
    def _build_city_index_map(self):
        """建立城市图片路径到索引的映射"""
        for city_cfg in self.ocean_config.cities:
            if city_cfg.sea and city_cfg.city:
                img_path = os.path.join(self.imgsc_root, city_cfg.sea, f'{city_cfg.city}.png')
                if os.path.exists(img_path):
                    self._city_path_to_index[os.path.normpath(img_path)] = city_cfg.city_index
    
    def _get_next_city_cfg(self, current_index: int) -> Optional[OceanCityV3Config]:
        """获取下一个城市配置"""
        if not self.ocean_config.cities:
            return None
        
        current_in_list = -1
        for i, cfg in enumerate(self.ocean_config.cities):
            if cfg.city_index == current_index:
                current_in_list = i
                break
        
        if current_in_list < 0:
            return None
        
        next_in_list = (current_in_list + 1) % len(self.ocean_config.cities)
        return self.ocean_config.cities[next_in_list]
    
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
    
    def _execute_city_segment(self, city_cfg: OceanCityV3Config):
        """执行城市段闭环"""
        logger.info(f'开始执行城市{city_cfg.city_index}段')
        
        # 1. 执行到港固定操作
        if self.script_dock_fixed and self.on_script_execute:
            self.on_script_execute(self.script_dock_fixed)
        
        # 2. 执行买卖操作
        if city_cfg.script_trade and self.on_script_execute:
            self.on_script_execute(city_cfg.script_trade)
        
        # 3. 执行下一站选择
        self._execute_next_stop(city_cfg)
    
    def _execute_next_stop(self, city_cfg: OceanCityV3Config):
        """执行下一站选择"""
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
            # 下一站城市（仅当策略为指定城市时）
            if city_cfg.next_stop_strategy == 'specified' and next_city_cfg.city:
                self.on_set_context_var('next_city', next_city_cfg.city)
        
        # 选择并执行脚本
        script_path = None
        if city_cfg.next_stop_strategy == 'auto':
            script_path = self.script_next_stop_auto
        else:
            script_path = self.script_next_stop_specified
        
        if script_path and self.on_script_execute:
            logger.info(f'执行下一站选择: {"自动选择最高价" if city_cfg.next_stop_strategy == "auto" else "指定城市"}')
            self.on_script_execute(script_path)
    
    def run_in_city_step(self, screenshot, capture_offset, ctx: StrategyContext):
        """在城市状态下执行一步
        
        Returns:
            bool: 是否继续保持城市状态
        """
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
        # 航行中不需要特殊处理，只需要等待进入城市
        return True
    
    def reset(self):
        """重置策略状态"""
        self.v3_ctx = OceanV3StrategyContext()
        logger.info('V3策略已重置')
