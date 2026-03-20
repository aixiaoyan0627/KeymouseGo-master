# -*- encoding:utf-8 -*-
"""
航行配置数据类和加载函数
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any, Dict

import json5
from loguru import logger

from .pinyin_mapping import (
    sea_chinese_to_pinyin, city_chinese_to_pinyin,
    convert_config_to_pinyin
)


@dataclass
class OceanCityV3Config:
    """单个城市配置（V3架构 - 调整版）
    
    每个城市有4个选项：
    1. 海域/城市
    2. 指定买卖操作脚本
    3. 下一站策略
    """
    city_index: int = 1
    # 海域/城市
    sea: str = ''
    city: str = ''
    # 指定买卖操作脚本
    script_trade: str = ''
    # 下一站策略
    next_stop_strategy: str = 'specified'  # 'specified'=指定城市, 'auto'=自动选择最高价


@dataclass
class OceanV3Config:
    """远洋V3架构配置（城市1-8 - 调整版）
    
    特点：
    - 最多支持8个城市
    - 每个城市：海域/城市/买卖脚本/下一站策略
    - 下一站使用下一行城市的配置（城市8使用城市1的）
    """
    cities: List[OceanCityV3Config] = field(default_factory=list)
    max_cities: int = 8


@dataclass
class OceanCityV3LiuxingConfig:
    """单个城市配置（V3-liuxing架构 - 流行板块）
    
    每个城市有3个选项：
    1. 海域/城市
    2. 指定买卖操作脚本
    3. 下一站策略（固定为指定城市）
    """
    city_index: int = 1
    # 海域/城市
    sea: str = ''
    city: str = ''
    # 指定买卖操作脚本
    script_trade: str = ''
    # 下一站策略（固定为指定城市）
    next_stop_strategy: str = 'specified'


@dataclass
class OceanV3LiuxingConfig:
    """流行V3-liuxing架构配置（城市1-8）
    
    特点：
    - 最多支持8个城市
    - 每个城市：海域/城市/买卖脚本
    - 下一站固定为指定城市
    - 支持两种模式：流行单线、流行搓搓
    """
    cities: List[OceanCityV3LiuxingConfig] = field(default_factory=list)
    max_cities: int = 8
    # 运行模式：'single'=流行单线, 'cycle'=流行搓搓
    mode: str = 'single'
    # 时长设置（分钟），0表示不限制
    duration_minutes: int = 0


@dataclass
class IconRule:
    """图标规则：识别到 image_path 时，在 (click_x, click_y) 点击。"""
    image_path: str
    click_x: int
    click_y: int
    threshold: float = 0.8
    button: str = 'left'


@dataclass
class DeathConfig:
    """死亡检测配置"""
    rescue_image_paths: List[str] = field(default_factory=list)
    script_shipwreck_reset: str = ''
    script_off_course_reset: str = ''
    a_missing_timeout: float = 60.0
    city_stuck_timeout: float = 60.0
    max_city_stuck_retries: int = 3


@dataclass
class DetectionConfig:
    """航行检测配置"""
    image_a_paths: List[str] = field(default_factory=list)
    image_a1_paths: List[str] = field(default_factory=list)  # imgsA1
    image_a2_paths: List[str] = field(default_factory=list)  # imgsA2
    image_a3_paths: List[str] = field(default_factory=list)  # imgsA3
    c_start_sea_paths: List[str] = field(default_factory=list)
    c_transit_sea_paths: List[str] = field(default_factory=list)
    c_back_sea_paths: List[str] = field(default_factory=list)
    c_start_path: str = ''
    c_transit_path: str = ''
    c_back_path: str = ''
    script_start_arrived: str = ''
    script_start_not_arrived: str = ''
    script_transit_arrived: str = ''
    script_transit_not_arrived: str = ''
    script_back_arrived: str = ''
    script_back_not_arrived: str = ''
    imgsc_root_path: str = ''
    trigger_image_paths: List[str] = field(default_factory=list)
    trigger_script_path: str = ''
    icon_rules: List[IconRule] = field(default_factory=list)
    image_a_path: str = ''
    image_b_paths: List[str] = field(default_factory=list)
    script_a_path: str = ''
    script_b_path: str = ''
    use_two_layer: bool = False
    check_interval: float = 0.5
    match_threshold: float = 0.7
    capture_window_title: str = ''
    city_scripts: List[str] = field(default_factory=list)
    popular_mode: str = 'single'
    main_city_scripts: List[str] = field(default_factory=list)
    main_city_script_index: int = 0
    region_a: Optional[Tuple[int, int, int, int]] = None  # A类检测区域（单个）
    region_a_list: Optional[List[Tuple[int, int, int, int]]] = None  # A类检测区域列表（多个）
    region_a1: Optional[Tuple[int, int, int, int]] = None  # A1类检测区域
    region_a2: Optional[Tuple[int, int, int, int]] = None  # A2类检测区域
    region_a3: Optional[Tuple[int, int, int, int]] = None  # A3类检测区域
    region_b: Optional[Tuple[int, int, int, int]] = None
    region_b_delay: Optional[Tuple[int, int, int, int]] = None  # B类delay图片检测区域
    region_c: Optional[Tuple[int, int, int, int]] = None
    region_e: Optional[Tuple[int, int, int, int]] = None  # E类图片检测区域
    region_f: Optional[Tuple[int, int, int, int]] = None  # F类图片检测区域
    base_window_width: int = 1024
    base_window_height: int = 768
    use_multi_scale: bool = False  # 是否使用多尺度检测（默认不使用）
    death_config: DeathConfig = field(default_factory=DeathConfig)
    # V3架构配置
    ocean_v3_config: Optional[OceanV3Config] = None
    # V3-liuxing架构配置（流行板块）
    ocean_v3_liuxing_config: Optional[OceanV3LiuxingConfig] = None


def _resolve_path(path: str, base_dir: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(base_dir, path))


def _get_all_images_in_folder(folder_path: str, extensions: Tuple[str, ...] = ('.png', '.jpg', '.jpeg')) -> List[str]:
    """获取文件夹下所有指定扩展名的图片路径"""
    if not folder_path or not os.path.isdir(folder_path):
        return []
    
    result = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(extensions):
                result.append(os.path.join(root, f))
    return result


def load_config(config_path: str, base_dir: Optional[str] = None) -> Optional[DetectionConfig]:
    """从 JSON5 加载配置。"""
    if not os.path.isfile(config_path):
        logger.warning('Config file not found: {}', config_path)
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
    except Exception as e:
        logger.error('Failed to load config: {}', e)
        return None

    if base_dir is None:
        base_dir = os.path.dirname(config_path)

    def get_path(key: str, default: str = '') -> str:
        v = data.get(key, default)
        if not v:
            return default
        return _resolve_path(v, base_dir)

    def get_path_list(key: str) -> List[str]:
        v = data.get(key, [])
        if isinstance(v, str):
            return [_resolve_path(v, base_dir)] if v else []
        return [_resolve_path(p, base_dir) for p in v if p]

    def get_float(key: str, default: float) -> float:
        v = data.get(key, default)
        try:
            return float(v)
        except (ValueError, TypeError):
            return default

    def get_str(key: str, default: str = '') -> str:
        return data.get(key, default) or default

    def get_str_list(key: str) -> List[str]:
        v = data.get(key, [])
        if isinstance(v, str):
            return [v] if v else []
        return [p for p in v if p]

    def get_optional_region(key: str) -> Optional[Tuple[int, int, int, int]]:
        v = data.get(key)
        if v and isinstance(v, (list, tuple)) and len(v) == 4:
            return tuple(int(x) for x in v)
        return None
    
    def get_optional_region_list(key: str) -> Optional[List[Tuple[int, int, int, int]]]:
        v = data.get(key)
        if v and isinstance(v, list):
            result = []
            for item in v:
                if item and isinstance(item, (list, tuple)) and len(item) == 4:
                    result.append(tuple(int(x) for x in item))
            return result if result else None
        return None

    tab_type = get_str('tab_type', 'ocean')
    
    config = DetectionConfig(
        capture_window_title=get_str('capture_window', '大航海时代：传说'),
        match_threshold=get_float('match_threshold', 0.7),
        check_interval=get_float('check_interval', 0.5),
        popular_mode=get_str('popular_mode', 'single'),
        main_city_scripts=get_str_list('main_city_scripts'),
        region_a=get_optional_region('region_a'),
        region_a_list=get_optional_region_list('region_a_list'),
        region_a1=get_optional_region('region_a1'),
        region_a2=get_optional_region('region_a2'),
        region_a3=get_optional_region('region_a3'),
        region_b=get_optional_region('region_b'),
        region_b_delay=get_optional_region('region_b_delay'),
        region_c=get_optional_region('region_c'),
        region_e=get_optional_region('region_e'),
        region_f=get_optional_region('region_f'),
    )

    # 获取项目根目录（配置文件的上级目录）
    project_root = os.path.dirname(base_dir) if base_dir else '.'

    if tab_type == 'ocean':
        config.imgsc_root_path = get_path('imgsc_root', os.path.join(project_root, 'imgsC'))
        
        start_sea = get_str('start_sea')
        transit_sea = get_str('transit_sea')
        back_sea = get_str('back_sea')
        
        if start_sea:
            sea_dir = os.path.join(config.imgsc_root_path, start_sea)
            config.c_start_sea_paths = _get_all_images_in_folder(sea_dir)
        if transit_sea:
            sea_dir = os.path.join(config.imgsc_root_path, transit_sea)
            config.c_transit_sea_paths = _get_all_images_in_folder(sea_dir)
        if back_sea:
            sea_dir = os.path.join(config.imgsc_root_path, back_sea)
            config.c_back_sea_paths = _get_all_images_in_folder(sea_dir)
        
        start_city = get_str('start_city')
        transit_city = get_str('transit_city')
        back_city = get_str('back_city')
        
        if start_sea and start_city:
            config.c_start_path = os.path.join(config.imgsc_root_path, start_sea, f'{start_city}.png')
        if transit_sea and transit_city:
            config.c_transit_path = os.path.join(config.imgsc_root_path, transit_sea, f'{transit_city}.png')
        if back_sea and back_city:
            config.c_back_path = os.path.join(config.imgsc_root_path, back_sea, f'{back_city}.png')
        
        config.script_start_arrived = get_path('script_start_arrived')
        config.script_start_not_arrived = get_path('script_start_not_arrived')
        config.script_transit_arrived = get_path('script_transit_arrived')
        config.script_transit_not_arrived = get_path('script_transit_not_arrived')
        config.script_back_arrived = get_path('script_back_arrived')
        config.script_back_not_arrived = get_path('script_back_not_arrived')
        
        config.city_scripts = get_str_list('city_scripts')
        
        popular_configs = data.get('popular_configs', [])
        if popular_configs and isinstance(popular_configs, list):
            for pc in popular_configs:
                if pc.get('script'):
                    config.city_scripts.append(_resolve_path(pc['script'], base_dir))
    elif tab_type == 'ocean_v3':
        config.imgsc_root_path = get_path('imgsc_root', os.path.join(project_root, 'imgsC'))
        
        # 加载V3配置
        ocean_v3_data = data
        ocean_v3_config = OceanV3Config()
        
        # 加载城市配置
        cities_data = ocean_v3_data.get('cities', [])
        for city_data in cities_data:
            city_cfg = OceanCityV3Config()
            city_cfg.city_index = int(city_data.get('city_index', 1))
            # 自动将中文海域和城市转换为拼音
            sea = city_data.get('sea', '')
            city = city_data.get('city', '')
            city_cfg.sea = sea_chinese_to_pinyin(sea)
            city_cfg.city = city_chinese_to_pinyin(city)
            
            script_trade = city_data.get('script_trade', '')
            if script_trade:
                script_trade = _resolve_path(script_trade, base_dir)
            city_cfg.script_trade = script_trade
            
            city_cfg.next_stop_strategy = city_data.get('next_stop_strategy', 'specified')
            ocean_v3_config.cities.append(city_cfg)
        
        config.ocean_v3_config = ocean_v3_config
    else:
        config.trigger_image_paths = get_path_list('trigger_image_paths')
        config.trigger_script_path = get_path('trigger_script_path')
        
        icon_rules_data = data.get('icon_rules', [])
        for rule in icon_rules_data:
            if isinstance(rule, dict) and rule.get('image_path'):
                config.icon_rules.append(IconRule(
                    image_path=_resolve_path(rule['image_path'], base_dir),
                    click_x=int(rule.get('click_x', 0)),
                    click_y=int(rule.get('click_y', 0)),
                    threshold=float(rule.get('threshold', 0.8)),
                    button=rule.get('button', 'left'),
                ))
        
        config.image_a_path = get_path('image_a_path')
        config.image_b_paths = get_path_list('image_b_paths')
        config.script_a_path = get_path('script_a_path')
        config.script_b_path = get_path('script_b_path')
        config.use_two_layer = data.get('use_two_layer', False)

    imgs_a_path = os.path.join(project_root, 'imgsA')
    if os.path.isdir(imgs_a_path):
        config.image_a_paths = _get_all_images_in_folder(imgs_a_path)
    
    # imgsA1, imgsA2, imgsA3 文件夹（在imgsA目录下）
    imgs_a1_path = os.path.join(project_root, 'imgsA', 'imgsA1')
    if os.path.isdir(imgs_a1_path):
        config.image_a1_paths = _get_all_images_in_folder(imgs_a1_path)
    
    imgs_a2_path = os.path.join(project_root, 'imgsA', 'imgsA2')
    if os.path.isdir(imgs_a2_path):
        config.image_a2_paths = _get_all_images_in_folder(imgs_a2_path)
    
    imgs_a3_path = os.path.join(project_root, 'imgsA', 'imgsA3')
    if os.path.isdir(imgs_a3_path):
        config.image_a3_paths = _get_all_images_in_folder(imgs_a3_path)
    
    imgs_b_path = os.path.join(project_root, 'imgsB')
    if os.path.isdir(imgs_b_path):
        config.image_b_paths = _get_all_images_in_folder(imgs_b_path)
    
    # 加载死亡检测配置
    death_config_data = data.get('death_config', {})
    
    # 解析救助图标路径
    rescue_image_paths = []
    rescue_paths_raw = death_config_data.get('rescue_image_paths', [])
    if isinstance(rescue_paths_raw, str):
        rescue_paths_raw = [rescue_paths_raw]
    for p in rescue_paths_raw:
        if p:
            rescue_image_paths.append(_resolve_path(p, base_dir))
    
    # 解析脚本路径
    script_shipwreck_reset = death_config_data.get('script_shipwreck_reset', '')
    if script_shipwreck_reset:
        script_shipwreck_reset = _resolve_path(script_shipwreck_reset, base_dir)
    
    script_off_course_reset = death_config_data.get('script_off_course_reset', '')
    if script_off_course_reset:
        script_off_course_reset = _resolve_path(script_off_course_reset, base_dir)
    
    config.death_config = DeathConfig(
        rescue_image_paths=rescue_image_paths,
        script_shipwreck_reset=script_shipwreck_reset,
        script_off_course_reset=script_off_course_reset,
        a_missing_timeout=float(death_config_data.get('a_missing_timeout', 60.0)),
        city_stuck_timeout=float(death_config_data.get('city_stuck_timeout', 60.0)),
        max_city_stuck_retries=int(death_config_data.get('max_city_stuck_retries', 3)),
    )

    return config


def list_sea_city_from_imgsc(imgsc_root: str) -> Dict[str, List[str]]:
    """列出 imgsC 下所有海域及其城市"""
    result: Dict[str, List[str]] = {}
    if not imgsc_root or not os.path.isdir(imgsc_root):
        return result
    
    for sea in os.listdir(imgsc_root):
        sea_dir = os.path.join(imgsc_root, sea)
        if os.path.isdir(sea_dir):
            cities = []
            for f in os.listdir(sea_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    city_name = os.path.splitext(f)[0]
                    cities.append(city_name)
            result[sea] = sorted(cities)
    
    return result


def get_c_image_path(imgsc_root: str, sea: str, city: str) -> str:
    """获取指定海域城市的图片路径"""
    return os.path.join(imgsc_root, sea, f'{city}.png')


# ========================================
# 兼容性定义（保留旧类名别名，避免导入错误）
# ========================================

@dataclass
class OceanCityConfig:
    """兼容性：旧版城市配置"""
    sea: str = ''
    city: str = ''
    use_auto_select: bool = False


@dataclass
class OceanRouteConfig:
    """兼容性：旧版航线配置"""
    route_id: int = 1
    buy: OceanCityConfig = field(default_factory=OceanCityConfig)
    sell: OceanCityConfig = field(default_factory=OceanCityConfig)
    script_dock_fixed: str = ''
    script_trade: str = ''
    script_next_stop_specified: str = ''
    script_next_stop_auto: str = ''


@dataclass
class OceanV2Config:
    """兼容性：旧版远洋配置"""
    routes: List[OceanRouteConfig] = field(default_factory=list)
    current_route_index: int = 0
    max_routes: int = 4
