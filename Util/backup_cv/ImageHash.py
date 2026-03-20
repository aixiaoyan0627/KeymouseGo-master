# -*- encoding:utf-8 -*-
"""
图片哈希模块：dHash 计算、加载、匹配
"""
import os
import json
from typing import Optional, Dict, Tuple, List
from PIL import Image
import numpy as np
from loguru import logger


class ImageHashManager:
    """
    图片哈希管理器
    
    职责：
    - 加载哈希配置
    - 计算 dHash
    - 匹配图片（汉明距离）
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.hash_db: Dict[str, str] = {}  # {relative_path: dhash_str}
        
        if config_path and os.path.isfile(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        从配置文件加载哈希
        
        :param config_path: 配置文件路径
        :return: 是否成功加载
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'image_hashes' in data:
                # 合并所有文件夹的哈希
                self.hash_db = {}
                for folder, hashes in data['image_hashes'].items():
                    self.hash_db.update(hashes)
                
                logger.info(f'已加载 {len(self.hash_db)} 个图片哈希')
                return True
            return False
        except Exception as e:
            logger.error(f'加载哈希配置失败: {e}')
            return False
    
    @staticmethod
    def calculate_dhash(image_path: str, hash_size: int = 16) -> Optional[str]:
        """
        计算图片的 dHash（差异哈希）
        
        :param image_path: 图片路径
        :param hash_size: 哈希大小
        :return: 十六进制哈希字符串
        """
        try:
            pil_img = Image.open(image_path).convert('L')  # 转为灰度
            if pil_img is None:
                return None
            
            # 调整大小为 (hash_size + 1, hash_size)
            resized = pil_img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            img = np.array(resized)
            
            # 计算相邻像素的差异
            diff = img[:, 1:] > img[:, :-1]
            
            # 转换为十六进制字符串
            hash_str = ''.join(['{:02x}'.format(int(''.join(['1' if pixel else '0' for pixel in row]), 2)) for row in diff])
            
            return hash_str
        except Exception as e:
            logger.warning(f'计算哈希失败 {image_path}: {e}')
            return None
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """
        计算两个哈希值之间的汉明距离
        
        :param hash1: 哈希值1
        :param hash2: 哈希值2
        :return: 汉明距离（越小越相似）
        """
        if len(hash1) != len(hash2):
            return float('inf')
        
        distance = 0
        for c1, c2 in zip(hash1, hash2):
            if c1 != c2:
                distance += 1
        
        return distance
    
    @staticmethod
    def hash_to_bin(hash_str: str) -> str:
        """
        将十六进制哈希字符串转换为二进制字符串
        
        :param hash_str: 十六进制哈希字符串
        :return: 二进制字符串
        """
        return ''.join([format(int(c, 16), '04b') for c in hash_str])
    
    def match_image(
        self,
        image_path: str,
        max_distance: int = 10,
        candidates: Optional[List[str]] = None,
    ) -> Optional[Tuple[str, int]]:
        """
        在哈希库中匹配图片
        
        :param image_path: 待匹配图片路径
        :param max_distance: 最大汉明距离（阈值）
        :param candidates: 候选路径列表（可选，仅在这些路径中匹配）
        :return: (匹配路径, 汉明距离) 或 None
        """
        target_hash = self.calculate_dhash(image_path)
        if target_hash is None:
            return None
        
        best_match = None
        best_distance = float('inf')
        
        # 确定要搜索的范围
        search_paths = candidates if candidates else list(self.hash_db.keys())
        
        for path, stored_hash in self.hash_db.items():
            if path not in search_paths:
                continue
            
            distance = self.hamming_distance(target_hash, stored_hash)
            
            if distance < best_distance and distance <= max_distance:
                best_distance = distance
                best_match = path
                
                # 如果找到完美匹配，直接返回
                if distance == 0:
                    break
        
        if best_match:
            return (best_match, best_distance)
        
        return None


# 全局哈希管理器实例
_hash_manager: Optional[ImageHashManager] = None


def init_hash_manager(config_path: Optional[str] = None) -> ImageHashManager:
    """
    初始化全局哈希管理器
    
    :param config_path: 配置文件路径
    :return: 哈希管理器实例
    """
    global _hash_manager
    
    if _hash_manager is None:
        _hash_manager = ImageHashManager(config_path)
    
    return _hash_manager


def get_hash_manager() -> Optional[ImageHashManager]:
    """
    获取全局哈希管理器实例
    
    :return: 哈希管理器实例或 None
    """
    return _hash_manager
