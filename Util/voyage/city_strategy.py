# -*- encoding:utf-8 -*-
"""
城市策略执行器：负责C策略的城市/海域判定和策略段执行
- 分为两个独立的类：
  - CityStrategyExecutorSingle: 流行单线模式
  - CityStrategyExecutorCycle: 流行搓搓模式
"""
import os
import time
from typing import Optional, Callable, Any, Tuple

from loguru import logger


class CityStrategyExecutorBase:
    """
    城市策略执行器基类
    """
    
    def __init__(
        self,
        config,
        log_callback: Optional[Callable[[str], None]] = None,
        enhanced_script_executor=None,
        script_executor=None,
        script_callback: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.log = log_callback or print
        self.enhanced_script_executor = enhanced_script_executor
        self.script_executor = script_executor
        self.on_script_execute = script_callback
        self._stopped = False
    
    def stop(self):
        """停止城市策略执行器"""
        self._stopped = True
        
        # 停止增强脚本执行器
        if self.enhanced_script_executor:
            self.enhanced_script_executor.stop()
        
        # 停止普通脚本执行器
        if self.script_executor:
            self.script_executor.stop()
    
    def _get_script_path(self, script_name: str) -> Optional[str]:
        """获取脚本路径"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 优先检查 scripts_enhanced 文件夹（.json5 格式）
        scripts_enhanced_dir = os.path.join(base_dir, 'scripts_enhanced')
        script_path_json5 = os.path.join(scripts_enhanced_dir, f'{script_name}.json5')
        if os.path.isfile(script_path_json5):
            return script_path_json5
        
        # 其次检查 scripts 文件夹（.json 格式）
        scripts_dir = os.path.join(base_dir, 'scripts')
        script_path_json = os.path.join(scripts_dir, f'{script_name}.json')
        return script_path_json if os.path.isfile(script_path_json) else None
    
    def _sleep_with_check(self, duration: float) -> bool:
        """可中断的睡眠
        
        :param duration: 睡眠时长（秒）
        :return: 如果正常完成返回True，如果被中断返回False
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._stopped:
                return False
            if self.enhanced_script_executor and getattr(self.enhanced_script_executor, '_stopped', False):
                return False
            time.sleep(0.1)
        return True

    def _execute_view_reset(self) -> bool:
        """
        执行画面复位操作
        
        :return: 是否执行成功
        """
        if self._stopped:
            self.log('[C策略] 已停止，跳过执行画面复位操作')
            return False
        
        self.log('[C策略] 执行画面复位操作')
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        fuwei_script_path = os.path.join(base_dir, 'system_scripts', 'fuwei.json5')
        
        if not os.path.isfile(fuwei_script_path):
            self.log(f'[C策略] 画面复位脚本不存在: {fuwei_script_path}')
            return False
        
        if self.script_executor:
            self.log(f'[C策略] 执行画面复位脚本: {os.path.basename(fuwei_script_path)}')
            self.script_executor.execute(fuwei_script_path, wait=True)
            return True
        
        self.log('[C策略] 普通脚本执行器未初始化!')
        return False
    
    def _execute_enhanced_script(self, script_name: str, context: Optional[dict] = None) -> bool:
        """
        执行增强脚本
        
        :param script_name: 脚本名称（不带扩展名）
        :param context: 上下文变量字典
        :return: 是否执行成功
        """
        if self._stopped:
            self.log(f'[C策略] 已停止，跳过执行脚本: {script_name}')
            return False
        
        self.log(f'[C策略] 准备执行脚本: {script_name}')
        script_path = self._get_script_path(script_name)
        self.log(f'[C策略] 脚本路径: {script_path}')
        if not script_path:
            self.log(f'[C策略] 脚本不存在: {script_name}')
            return False
        
        self.log(f'[C策略] 脚本存在，准备加载: {script_path}')
        if self.enhanced_script_executor:
            script = self.enhanced_script_executor.load_from_file(script_path)
            if not script:
                self.log(f'[C策略] 加载脚本失败: {script_name}')
                return False
            
            self.log(f'[C策略] 脚本加载成功，步骤数: {len(script.steps)}')
            if context:
                self.log(f'[C策略] 设置上下文: {context}')
                self.enhanced_script_executor.set_context(context)
            
            self.log(f'[C策略] 开始执行脚本...')
            result = self.enhanced_script_executor.execute(script)
            self.log(f'[C策略] 脚本执行结果: {result}')
            return result
        
        self.log(f'[C策略] 增强脚本执行器未初始化!')
        return False
    
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
    
    def _find_matching_sea_config(self, sea_name: str) -> Optional[Any]:
        """查找匹配的海域配置"""
        if self.config.ocean_v3_config:
            for city_cfg in self.config.ocean_v3_config.cities:
                if city_cfg.sea == sea_name:
                    return city_cfg
        elif self.config.ocean_v3_liuxing_config:
            for city_cfg in self.config.ocean_v3_liuxing_config.cities:
                if city_cfg.sea == sea_name:
                    return city_cfg
        return None
    
    def _get_previous_city_config(self, current_cfg: Any) -> Optional[Any]:
        """获取上一个城市配置"""
        cities = None
        if self.config.ocean_v3_config:
            cities = self.config.ocean_v3_config.cities
        elif self.config.ocean_v3_liuxing_config:
            cities = self.config.ocean_v3_liuxing_config.cities
        
        if not cities:
            return None
        
        current_idx = -1
        for i, city_cfg in enumerate(cities):
            if city_cfg.city_index == current_cfg.city_index:
                current_idx = i
                break
        
        if current_idx < 0:
            return None
        
        prev_idx = (current_idx - 1) % len(cities)
        return cities[prev_idx]


class CityStrategyExecutorSingle(CityStrategyExecutorBase):
    """
    城市策略执行器 - 流行单线模式
    
    跳转规则：1→2→3→4→5→6→7→8→1→2→3...
    
    执行步骤：
    1. 检测当前城市，匹配到城市N
    2. 执行买卖操作（script_trade）
    3. 等待15秒
    4. 直接跳回状态检测
    5. 循环执行
    """
    
    def _get_next_city_config(self, current_cfg: Any) -> Optional[Any]:
        """获取下一个城市配置（单线模式）"""
        cities = self.config.ocean_v3_liuxing_config.cities
        if not cities:
            self.log('[C策略] cities 列表为空')
            return None
        
        self.log('[C策略] 流行单线模式，当前城市配置: sea={}, city={}, city_index={}'.format(
            current_cfg.sea, current_cfg.city, current_cfg.city_index))
        self.log('[C策略] 所有城市配置: {}'.format([
            {'sea': c.sea, 'city': c.city, 'city_index': c.city_index} 
            for c in cities
        ]))
        
        current_idx = -1
        for i, city_cfg in enumerate(cities):
            if city_cfg.city_index == current_cfg.city_index:
                current_idx = i
                break
        
        if current_idx < 0:
            self.log('[C策略] 未找到当前城市在列表中的位置')
            return None
        
        # 查找下一个有效的城市配置（跳过空配置）
        for offset in range(1, len(cities) + 1):
            next_idx = (current_idx + offset) % len(cities)
            next_city = cities[next_idx]
            if next_city.sea and next_city.city:
                self.log('[C策略] 下一个城市配置: sea={}, city={}'.format(next_city.sea, next_city.city))
                return next_city
        
        self.log('[C策略] 未找到下一个有效城市配置')
        return None
    
    def _execute_city_segment(self, city_cfg: Any) -> bool:
        """执行城市策略段（单线模式）
        
        :return: 是否应该继续执行下一站等待（单线模式永远返回False，直接跳回状态检测）
        """
        if self._stopped:
            self.log('[C策略] 已停止，跳过执行城市策略段')
            return False
        
        self.log('[C策略] 执行指定买卖操作')
        if city_cfg.script_trade and os.path.isfile(city_cfg.script_trade):
            if self.script_executor:
                self.log(f'[C策略] 执行买卖脚本: {os.path.basename(city_cfg.script_trade)}')
                self.script_executor.execute(city_cfg.script_trade, wait=True)
        
        if self._stopped:
            return False
        
        # 流行单线模式：等待15秒后跳回状态检测
        self.log('[C策略] 流行单线模式：买卖操作完成，等待15秒后跳回状态检测')
        if not self._sleep_with_check(15):
            self.log('[C策略] 等待被中断')
            return False
        self.log('[C策略] 等待完成，跳回状态检测阶段')
        return False
    
    def handle_strategy_c_start(self, sea_name: str, city_name: str) -> Tuple[bool, Optional[str]]:
        """
        处理C策略开始（城市匹配的情况）
        
        :param sea_name: 海域名称
        :param city_name: 城市名称
        :return: (是否继续运行, 下一个目标海域)
        """
        self.log('[C策略] 当前处于「{}」海域「{}」'.format(sea_name, city_name))
        
        target_city_cfg = self._find_matching_city_config(sea_name, city_name)
        
        if target_city_cfg:
            self.log('[C策略] 检测到城市属于配置中的城市「{}」'.format(target_city_cfg.city))
            should_continue = self._execute_city_segment(target_city_cfg)
            return (should_continue, None)
        else:
            self.log('[C策略] 城市不属于配置中的任一城市')
            return (False, None)
    
    def handle_strategy_c_sea_matched(self, sea_name: str, sea_matched_cfg: Any) -> bool:
        """
        处理C策略海域匹配的情况（城市不匹配但海域匹配）
        
        :param sea_name: 海域名称
        :param sea_matched_cfg: 匹配的海域配置
        :return: 是否执行成功
        """
        self.log('[C策略] 海域「{}」匹配配置'.format(sea_name))
        
        # 流行单线模式：城市不匹配但海域匹配，直接停止运行
        self.log('[C策略] 流行单线模式：城市不匹配但海域匹配，停止航行')
        self._stopped = True
        return False


class CityStrategyExecutorCycle(CityStrategyExecutorBase):
    """
    城市策略执行器 - 流行搓搓模式
    
    跳转规则：1→2→1→3→1→4→1→5→1→6→1→7→1→8→1→2...
    
    执行步骤：
    1. 检测当前城市，匹配到城市N
    2. 执行买卖操作（script_trade）
    3. 等待3秒
    4. 执行下一站选择-指定城市
    5. 等待30秒（等待进入A状态或城市变更）
    6. 循环执行
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 记录上一个从城市1跳转到的目标城市索引
        self._last_target_city_index = 1
    
    def _get_next_city_config(self, current_cfg: Any) -> Optional[Any]:
        """获取下一个城市配置（搓搓模式）"""
        cities = self.config.ocean_v3_liuxing_config.cities
        if not cities:
            self.log('[C策略] cities 列表为空')
            return None
        
        self.log('[C策略] 流行搓搓模式，当前城市配置: sea={}, city={}, city_index={}'.format(
            current_cfg.sea, current_cfg.city, current_cfg.city_index))
        
        # 找到当前城市索引
        current_idx = -1
        for i, city_cfg in enumerate(cities):
            if city_cfg.city_index == current_cfg.city_index:
                current_idx = i
                break
        
        if current_idx < 0:
            self.log('[C策略] 未找到当前城市在列表中的位置')
            return None
        
        # 找到城市1
        city1 = None
        city1_idx = -1
        for i, cfg in enumerate(cities):
            if cfg.city_index == 1:
                city1 = cfg
                city1_idx = i
                break
        
        if city1 is None:
            self.log('[C策略] 未找到城市1配置')
            return None
        
        # 搓搓模式跳转规则
        if current_cfg.city_index == 1:
            # 当前是城市1，跳到下一个目标城市
            # 找到有效城市列表（只包含有配置的城市）
            valid_cities = [cfg for cfg in cities if cfg.sea and cfg.city]
            if not valid_cities:
                return None
            
            # 找到当前城市1在有效列表中的位置
            valid_city1_idx = -1
            for i, cfg in enumerate(valid_cities):
                if cfg.city_index == 1:
                    valid_city1_idx = i
                    break
            
            if valid_city1_idx < 0:
                return None
            
            # 找到下一个目标城市
            next_valid_idx = (valid_city1_idx + 1) % len(valid_cities)
            # 如果下一个还是城市1，继续往后找
            while valid_cities[next_valid_idx].city_index == 1:
                next_valid_idx = (next_valid_idx + 1) % len(valid_cities)
            
            next_city = valid_cities[next_valid_idx]
            self._last_target_city_index = next_city.city_index
            self.log('[C策略] 搓搓模式下一个城市配置(从1跳转): sea={}, city={}'.format(next_city.sea, next_city.city))
            return next_city
        else:
            # 当前不是城市1，跳回到城市1
            self.log('[C策略] 搓搓模式下一个城市配置(跳回1): sea={}, city={}'.format(city1.sea, city1.city))
            return city1
    
    def _execute_next_stop_script(self, city_cfg: Any):
        """执行下一站选择脚本"""
        self.log('[C策略] _execute_next_stop_script 被调用')
        
        # 获取下一个城市配置
        next_city_cfg = self._get_next_city_config(city_cfg)
        
        if next_city_cfg:
            context = {
                'next_stop_strategy': 'specified',
                'next_sea': next_city_cfg.sea,
                'next_city': next_city_cfg.city,
            }
            
            self.log('[C策略] 下一站策略：指定城市，目标海域: {}，目标城市: {}'.format(
                next_city_cfg.sea, next_city_cfg.city))
            self._execute_enhanced_script('下一站选择', context=context)
        else:
            self.log('[C策略] 未找到下一个城市配置')
    
    def _execute_city_segment(self, city_cfg: Any) -> bool:
        """执行城市策略段（搓搓模式）
        
        :return: 是否应该继续执行下一站等待（搓搓模式返回True，继续执行）
        """
        if self._stopped:
            self.log('[C策略] 已停止，跳过执行城市策略段')
            return False
        
        self.log('[C策略] 执行指定买卖操作')
        if city_cfg.script_trade and os.path.isfile(city_cfg.script_trade):
            if self.script_executor:
                self.log(f'[C策略] 执行买卖脚本: {os.path.basename(city_cfg.script_trade)}')
                self.script_executor.execute(city_cfg.script_trade, wait=True)
        
        if self._stopped:
            return False
        
        # 添加3秒等待时间，避免脚本衔接太快导致下一站选择失败
        self.log('[C策略] 等待3秒，准备执行下一站选择...')
        if not self._sleep_with_check(3):
            self.log('[C策略] 等待被中断')
            return False
        
        if self._stopped:
            return False
        
        # 流行搓搓模式：执行下一站选择-指定城市
        self.log('[C策略] 流行搓搓模式：执行下一站选择-指定城市')
        self.log('[C策略] 执行下一站选择')
        # 增强脚本：使用 enhanced_script_executor 执行（同步）
        self._execute_next_stop_script(city_cfg)
        
        if self._stopped:
            return False
        
        return True
    
    def handle_strategy_c_start(self, sea_name: str, city_name: str) -> Tuple[bool, Optional[str]]:
        """
        处理C策略开始（城市匹配的情况）
        
        :param sea_name: 海域名称
        :param city_name: 城市名称
        :return: (是否继续运行, 下一个目标海域)
        """
        self.log('[C策略] 当前处于「{}」海域「{}」'.format(sea_name, city_name))
        
        target_city_cfg = self._find_matching_city_config(sea_name, city_name)
        next_target_sea = None
        
        if target_city_cfg:
            self.log('[C策略] 检测到城市属于配置中的城市「{}」'.format(target_city_cfg.city))
            should_continue = self._execute_city_segment(target_city_cfg)
            
            if should_continue:
                # 获取下一个目标城市的海域
                next_city_cfg = self._get_next_city_config(target_city_cfg)
                if next_city_cfg:
                    next_target_sea = next_city_cfg.sea
                    self.log('[C策略] 下一个目标海域: 「{}」'.format(next_target_sea))
                
                return (True, next_target_sea)
            else:
                # 直接跳回状态检测
                return (False, None)
        else:
            self.log('[C策略] 城市不属于配置中的任一城市')
            return (False, None)
    
    def handle_strategy_c_sea_matched(self, sea_name: str, sea_matched_cfg: Any) -> bool:
        """
        处理C策略海域匹配的情况（城市不匹配但海域匹配）
        
        :param sea_name: 海域名称
        :param sea_matched_cfg: 匹配的海域配置
        :return: 是否执行成功
        """
        self.log('[C策略] 海域「{}」匹配配置'.format(sea_name))
        
        # 流行搓搓模式：城市不匹配但海域匹配，直接停止运行
        self.log('[C策略] 流行搓搓模式：城市不匹配但海域匹配，停止航行')
        self._stopped = True
        return False


class CityStrategyExecutor:
    """
    城市策略执行器（兼容层 - 根据模式选择使用Single或Cycle）
    """
    
    def __init__(
        self,
        config,
        log_callback: Optional[Callable[[str], None]] = None,
        enhanced_script_executor=None,
        script_executor=None,
        script_callback: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.log = log_callback or print
        
        # 根据模式选择使用哪个策略执行器
        is_liuxing_mode = config.ocean_v3_liuxing_config is not None
        if is_liuxing_mode and config.ocean_v3_liuxing_config.mode == 'cycle':
            # 流行搓搓模式
            self._executor = CityStrategyExecutorCycle(
                config, log_callback, enhanced_script_executor, 
                script_executor, script_callback
            )
            self.log('[C策略] 使用流行搓搓模式执行器')
        elif is_liuxing_mode and config.ocean_v3_liuxing_config.mode == 'single':
            # 流行单线模式
            self._executor = CityStrategyExecutorSingle(
                config, log_callback, enhanced_script_executor, 
                script_executor, script_callback
            )
            self.log('[C策略] 使用流行单线模式执行器')
        else:
            # 远洋V3模式，暂时保持原样（用Cycle类处理，但只执行单线逻辑）
            self._executor = CityStrategyExecutorSingle(
                config, log_callback, enhanced_script_executor, 
                script_executor, script_callback
            )
            self.log('[C策略] 使用远洋V3模式执行器')
    
    def stop(self):
        """停止城市策略执行器"""
        self._executor.stop()
    
    def handle_strategy_c_start(self, sea_name: str, city_name: str) -> Tuple[bool, Optional[str]]:
        """处理C策略开始（城市匹配的情况）"""
        return self._executor.handle_strategy_c_start(sea_name, city_name)
    
    def handle_strategy_c_sea_matched(self, sea_name: str, sea_matched_cfg: Any) -> bool:
        """处理C策略海域匹配的情况（城市不匹配但海域匹配）"""
        return self._executor.handle_strategy_c_sea_matched(sea_name, sea_matched_cfg)
