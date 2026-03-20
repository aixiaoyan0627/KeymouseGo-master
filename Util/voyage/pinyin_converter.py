# -*- encoding:utf-8 -*-
"""
拼音-中文动态转换模块
使用 pypinyin 库进行动态转换，无需维护硬编码映射表

核心特点：
1. 支持拼音转中文（需要缓存机制）
2. 自动缓存常见映射
3. 向后兼容硬编码映射（作为后备）
"""
import os
from typing import Dict, Optional
from loguru import logger

try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    logger.warning('pypinyin 未安装，将使用硬编码映射作为后备')

# 导入原有的硬编码映射（作为后备）
try:
    from .pinyin_mapping import (
        SEA_PINYIN_TO_CHINESE,
        SEA_CHINESE_TO_PINYIN,
        CITY_PINYIN_TO_CHINESE,
        CITY_CHINESE_TO_PINYIN,
        IMGSPINYIN_TO_CHINESE,
        IMGSPINYIN_CHINESE_TO_PINYIN,
        IMGSBPINYIN_TO_CHINESE,
        IMGSBPINYIN_CHINESE_TO_PINYIN,
    )
    HAS_LEGACY_MAPPING = True
except ImportError:
    HAS_LEGACY_MAPPING = False

# 动态缓存
_pinyin_to_chinese_cache: Dict[str, str] = {}
_chinese_to_pinyin_cache: Dict[str, str] = {}


def _init_common_mappings():
    """初始化常见映射缓存"""
    if HAS_LEGACY_MAPPING:
        _pinyin_to_chinese_cache.update(SEA_PINYIN_TO_CHINESE)
        _pinyin_to_chinese_cache.update(CITY_PINYIN_TO_CHINESE)
        _pinyin_to_chinese_cache.update(IMGSPINYIN_TO_CHINESE)
        _pinyin_to_chinese_cache.update(IMGSBPINYIN_TO_CHINESE)
        
        _chinese_to_pinyin_cache.update(SEA_CHINESE_TO_PINYIN)
        _chinese_to_pinyin_cache.update(CITY_CHINESE_TO_PINYIN)
        _chinese_to_pinyin_cache.update(IMGSPINYIN_CHINESE_TO_PINYIN)
        _chinese_to_pinyin_cache.update(IMGSBPINYIN_CHINESE_TO_PINYIN)


# 初始化缓存
_init_common_mappings()


def chinese_to_pinyin(chinese: str, style: Style = Style.NORMAL) -> str:
    """
    中文转拼音（使用 pypinyin）
    
    参数:
        chinese: 中文字符串
        style: 拼音风格
    
    返回:
        拼音字符串
    """
    if not chinese:
        return chinese
    
    if chinese in _chinese_to_pinyin_cache:
        return _chinese_to_pinyin_cache[chinese]
    
    if HAS_PYPINYIN:
        try:
            pinyin_list = lazy_pinyin(chinese, style=style)
            pinyin_str = ''.join(pinyin_list)
            _chinese_to_pinyin_cache[chinese] = pinyin_str
            return pinyin_str
        except Exception as e:
            logger.warning(f'中文转拼音失败: {e}')
    
    if HAS_LEGACY_MAPPING:
        if chinese in SEA_CHINESE_TO_PINYIN:
            return SEA_CHINESE_TO_PINYIN[chinese]
        if chinese in CITY_CHINESE_TO_PINYIN:
            return CITY_CHINESE_TO_PINYIN[chinese]
        if chinese in IMGSPINYIN_CHINESE_TO_PINYIN:
            return IMGSPINYIN_CHINESE_TO_PINYIN[chinese]
        if chinese in IMGSBPINYIN_CHINESE_TO_PINYIN:
            return IMGSBPINYIN_CHINESE_TO_PINYIN[chinese]
    
    return chinese


def pinyin_to_chinese(pinyin: str) -> str:
    """
    拼音转中文（使用缓存映射）
    
    参数:
        pinyin: 拼音字符串
    
    返回:
        中文字符串
    """
    if not pinyin:
        return pinyin
    
    if pinyin in _pinyin_to_chinese_cache:
        return _pinyin_to_chinese_cache[pinyin]
    
    if HAS_LEGACY_MAPPING:
        if pinyin in SEA_PINYIN_TO_CHINESE:
            return SEA_PINYIN_TO_CHINESE[pinyin]
        if pinyin in CITY_PINYIN_TO_CHINESE:
            return CITY_PINYIN_TO_CHINESE[pinyin]
        if pinyin in IMGSPINYIN_TO_CHINESE:
            return IMGSPINYIN_TO_CHINESE[pinyin]
        if pinyin in IMGSBPINYIN_TO_CHINESE:
            return IMGSBPINYIN_TO_CHINESE[pinyin]
    
    return pinyin


def add_mapping(pinyin: str, chinese: str):
    """
    添加自定义映射
    
    参数:
        pinyin: 拼音
        chinese: 中文
    """
    _pinyin_to_chinese_cache[pinyin] = chinese
    _chinese_to_pinyin_cache[chinese] = pinyin


# ==================== 兼容原有接口 ====================


def sea_pinyin_to_chinese(pinyin: str) -> str:
    """海域拼音转中文（兼容接口）"""
    return pinyin_to_chinese(pinyin)


def sea_chinese_to_pinyin(chinese: str) -> str:
    """海域中文转拼音（兼容接口）"""
    return chinese_to_pinyin(chinese)


def city_pinyin_to_chinese(pinyin: str) -> str:
    """城市拼音转中文（兼容接口）"""
    return pinyin_to_chinese(pinyin)


def city_chinese_to_pinyin(chinese: str) -> str:
    """城市中文转拼音（兼容接口）"""
    return chinese_to_pinyin(chinese)


def image_pinyin_to_chinese(filename: str) -> str:
    """图片文件名拼音转中文（兼容接口）"""
    name_without_ext = os.path.splitext(filename)[0]
    chinese_name = pinyin_to_chinese(name_without_ext)
    if chinese_name != name_without_ext:
        return chinese_name + os.path.splitext(filename)[1]
    return filename


def image_chinese_to_pinyin(filename: str) -> str:
    """图片文件名中文转拼音（兼容接口）"""
    name_without_ext = os.path.splitext(filename)[0]
    pinyin_name = chinese_to_pinyin(name_without_ext)
    if pinyin_name != name_without_ext:
        return pinyin_name + os.path.splitext(filename)[1]
    return filename


def convert_sea_cities_to_chinese(sea_cities: dict) -> dict:
    """将海域-城市字典中的拼音转换为中文（兼容接口）"""
    result = {}
    for sea_pinyin, cities_pinyin in sea_cities.items():
        sea_chinese = sea_pinyin_to_chinese(sea_pinyin)
        cities_chinese = [city_pinyin_to_chinese(c) for c in cities_pinyin]
        result[sea_chinese] = cities_chinese
    return result


def convert_config_to_pinyin(config: dict) -> dict:
    """将配置中的中文海域和城市转换为拼音（兼容接口）"""
    if 'cities' in config:
        for city_cfg in config['cities']:
            if 'sea' in city_cfg:
                city_cfg['sea'] = sea_chinese_to_pinyin(city_cfg['sea'])
            if 'city' in city_cfg:
                city_cfg['city'] = city_chinese_to_pinyin(city_cfg['city'])
    return config


def convert_config_to_chinese(config: dict) -> dict:
    """将配置中的拼音海域和城市转换为中文（兼容接口）"""
    if 'cities' in config:
        for city_cfg in config['cities']:
            if 'sea' in city_cfg:
                city_cfg['sea'] = sea_pinyin_to_chinese(city_cfg['sea'])
            if 'city' in city_cfg:
                city_cfg['city'] = city_pinyin_to_chinese(city_cfg['city'])
    return config
