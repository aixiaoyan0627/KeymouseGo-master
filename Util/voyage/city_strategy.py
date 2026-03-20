# -*- encoding:utf-8 -*-
"""
城市策略执行器：负责C策略的城市/海域判定和策略段执行
"""
import os
import time
from typing import Optional, Callable, Any, Tuple

from loguru import logger


class CityStrategyExecutor:
    """
    城市策略执行器
    
    职责：
    - 城市归属判定
    - 海域归属判定
    - 策略段执行
    - 下一站选择
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
    
    def _get_next_city_config(self, current_cfg: Any) -> Optional[Any]:
        """获取下一个城市配置"""
        # 检查是否是流行搓搓模式
        if self.config.ocean_v3_liuxing_config and self.config.ocean_v3_liuxing_config.mode == 'cycle':
            # 流行搓搓模式：1→2→1→3→1→4...
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
            
            # 搓搓模式跳转规则
            if current_idx == 0:
                # 当前是城市1，跳到下一个城市
                next_idx = current_idx + 1
                while next_idx < len(cities):
                    next_city = cities[next_idx]
                    if next_city.sea and next_city.city:
                        self.log('[C策略] 搓搓模式下一个城市配置(从1跳转): sea={}, city={}'.format(next_city.sea, next_city.city))
                        return next_city
                    next_idx += 1
                # 如果没有更多城市，跳回城市1
                self.log('[C策略] 搓搓模式没有更多城市，跳回城市1')
                return cities[0]
            else:
                # 当前不是城市1，跳回城市1
                next_city = cities[0]
                self.log('[C策略] 搓搓模式下一个城市配置(跳回1): sea={}, city={}'.format(next_city.sea, next_city.city))
                return next_city
        
        # 普通模式（流行单线或远洋）
        cities = None
        if self.config.ocean_v3_config:
            cities = self.config.ocean_v3_config.cities
        elif self.config.ocean_v3_liuxing_config:
            cities = self.config.ocean_v3_liuxing_config.cities
        
        if not cities:
            self.log('[C策略] ocean_v3_config或ocean_v3_liuxing_config 为空')
            return None
        
        if not cities:
            self.log('[C策略] cities 列表为空')
            return None
        
        self.log('[C策略] 当前城市配置: sea={}, city={}, city_index={}'.format(
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
    
    def _execute_city_segment(self, city_cfg: Any):
        """执行城市策略段"""
        if self._stopped:
            self.log('[C策略] 已停止，跳过执行城市策略段')
            return
        
        # 检查是否是流行板块（流行板块不执行到港固定操作）
        is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
        
        if not is_liuxing_mode:
            self.log('[C策略] 执行到港固定操作')
            # 增强脚本：使用 enhanced_script_executor 执行（同步）
            if not self._execute_enhanced_script('到港固定操作'):
                self.log('[C策略] 到港固定操作被中断')
                return
            
            if self._stopped:
                return
            
            # 添加3秒间隔（可中断）
            if not self._sleep_with_check(3):
                self.log('[C策略] 等待被中断')
                return
            
            if self._stopped:
                return
        
        self.log('[C策略] 执行指定买卖操作')
        if city_cfg.script_trade and os.path.isfile(city_cfg.script_trade):
            if self.script_executor:
                self.log(f'[C策略] 执行买卖脚本: {os.path.basename(city_cfg.script_trade)}')
                self.script_executor.execute(city_cfg.script_trade, wait=True)
        
        if self._stopped:
            return
        
        # 流行板块：执行买卖操作完成后，等待15秒，然后直接跳回状态检测阶段
        if is_liuxing_mode:
            self.log('[C策略] 流行板块：买卖操作完成，等待15秒后跳回状态检测')
            if not self._sleep_with_check(15):
                self.log('[C策略] 等待被中断')
                return
            self.log('[C策略] 等待完成，跳回状态检测阶段')
            return
        
        # 非流行板块（远洋V3）：继续执行原来的流程
        # 添加3秒间隔（可中断）
        if not self._sleep_with_check(3):
            self.log('[C策略] 等待被中断')
            return
        
        if self._stopped:
            return
        
        self.log('[C策略] 执行下一站选择')
        # 增强脚本：使用 enhanced_script_executor 执行（同步）
        self._execute_next_stop_script(city_cfg)
    
    def _execute_next_stop_script(self, city_cfg: Any):
        """执行下一站选择脚本"""
        self.log('[C策略] _execute_next_stop_script 被调用')
        
        # 获取下一个城市配置
        next_city_cfg = self._get_next_city_config(city_cfg)
        
        if next_city_cfg:
            context = {
                'next_stop_strategy': city_cfg.next_stop_strategy,
                'next_sea': next_city_cfg.sea,
                'next_city': next_city_cfg.city,
            }
            
            self.log('[C策略] 下一站策略：{}，目标海域: {}，目标城市: {}'.format(
                city_cfg.next_stop_strategy, next_city_cfg.sea, next_city_cfg.city))
            self._execute_enhanced_script('下一站选择', context=context)
        else:
            self.log('[C策略] 未找到下一个城市配置')
    
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
            self._execute_city_segment(target_city_cfg)
            
            # 获取下一个目标城市的海域
            next_city_cfg = self._get_next_city_config(target_city_cfg)
            if next_city_cfg:
                next_target_sea = next_city_cfg.sea
                self.log('[C策略] 下一个目标海域: 「{}」'.format(next_target_sea))
            
            return (True, next_target_sea)
        else:
            self.log('[C策略] 城市不属于配置中的任一城市')
            return (False, None)
    
    def handle_strategy_c_sea_matched(self, sea_name: str, sea_matched_cfg: Any) -> bool:
        """
        处理C策略海域匹配的情况（城市不匹配但海域匹配）
        
        执行固定操作流程：入港固定操作 → 买卖操作固定版 → 下一站选择-指定城市
        流行板块不执行到港固定操作
        
        :param sea_name: 海域名称
        :param sea_matched_cfg: 匹配的海域配置
        :return: 是否执行成功
        """
        self.log('[C策略] 海域「{}」匹配配置，执行固定操作流程'.format(sea_name))
        
        # 检查是否是流行板块（流行板块不执行到港固定操作）
        is_liuxing_mode = self.config.ocean_v3_liuxing_config is not None
        
        # 获取上一个策略段配置
        prev_city_cfg = self._get_previous_city_config(sea_matched_cfg)
        
        if not prev_city_cfg:
            self.log('[C策略] 未找到上一个策略段配置')
            return False
        
        self.log('[C策略] 使用上一个策略段配置: sea={}, city={}'.format(prev_city_cfg.sea, prev_city_cfg.city))
        
        if not is_liuxing_mode:
            # 1. 执行入港固定操作
            self.log('[C策略] 执行入港固定操作')
            if not self._execute_enhanced_script('到港固定操作'):
                self.log('[C策略] 入港固定操作执行失败')
                return False
        
        # 2. 执行买卖操作固定版
        self.log('[C策略] 执行买卖操作固定版')
        if not self._execute_enhanced_script('买卖操作固定版'):
            self.log('[C策略] 买卖操作固定版执行失败')
            return False
        
        # 3. 执行下一站选择-强制使用指定城市模式
        self.log('[C策略] 执行下一站选择-指定城市（海域匹配但城市不匹配时，强制使用指定城市模式）')
        # 创建一个临时配置，强制 next_stop_strategy 为 'specified'
        temp_cfg = type(prev_city_cfg)(**prev_city_cfg.__dict__)
        temp_cfg.next_stop_strategy = 'specified'
        self._execute_next_stop_script(temp_cfg)
        
        return True
