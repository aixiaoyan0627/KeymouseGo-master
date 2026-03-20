# -*- encoding:utf-8 -*-
"""
图像检测器：负责截图和图像匹配
使用 OpenCV 模板匹配
"""
import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

import numpy as np
import cv2
from loguru import logger

from Util.ImageRecognition import (
    take_screenshot,
    find_image_on_screen,
    find_all_images_on_screen,
    click_at,
    double_click_at,
    get_window_rect_by_title,
)


# 常量定义
HAS_UNIFIED_RECOGNIZER = False


@dataclass
class MatchResult:
    """匹配结果"""
    path: str
    position: Tuple[int, int]
    folder_name: str = ''
    confidence: float = 0.0
    text: str = ''


class ImageDetector:
    """图像检测器"""
    
    def __init__(
        self,
        threshold: float = 0.8,
        base_window_size: Tuple[int, int] = (1024, 768),
        use_multi_scale: bool = False,
    ):
        self.threshold = threshold
        self.base_window_width, self.base_window_height = base_window_size
        self.use_multi_scale = use_multi_scale
        self.window_title = ''
        self.capture_region = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        
        # 保存原始region值
        self.region_a = None
        self.region_a_list = None  # 多个A类检测区域
        self.region_a1 = None  # A1类检测区域
        self.region_a2 = None  # A2类检测区域
        self.region_a3 = None  # A3类检测区域
        self.region_b = None
        self.region_b_delay = None
        self.region_c = None
        self.region_e = None
        self.region_f = None
        
        # 缩放后的region值
        self.scaled_region_a = None
        self.scaled_region_a_list = None  # 多个缩放后的A类区域
        self.scaled_region_a1 = None  # 缩放后的A1类区域
        self.scaled_region_a2 = None  # 缩放后的A2类区域
        self.scaled_region_a3 = None  # 缩放后的A3类区域
        self.scaled_region_b = None
        self.scaled_region_b_delay = None  # B类delay图片检测区域
        self.scaled_region_c = None
        self.scaled_region_e = None
        self.scaled_region_f = None
        
        # 模板图片缓存
        self._template_cache: Dict[str, np.ndarray] = {}
        
        self._last_window_check_time = 0.0
        
        logger.info('图像检测器：使用 OpenCV 模板匹配')
    
    
    def set_window(
        self,
        window_title: str,
        region_a: Optional[Tuple[int, int, int, int]] = None,
        region_a_list: Optional[List[Tuple[int, int, int, int]]] = None,
        region_a1: Optional[Tuple[int, int, int, int]] = None,
        region_a2: Optional[Tuple[int, int, int, int]] = None,
        region_a3: Optional[Tuple[int, int, int, int]] = None,
        region_b: Optional[Tuple[int, int, int, int]] = None,
        region_b_delay: Optional[Tuple[int, int, int, int]] = None,
        region_c: Optional[Tuple[int, int, int, int]] = None,
        region_e: Optional[Tuple[int, int, int, int]] = None,
        region_f: Optional[Tuple[int, int, int, int]] = None,
    ) -> bool:
        """
        设置游戏窗口
        
        :param window_title: 窗口标题
        :param region_a: A类检测区域
        :param region_a_list: A类检测区域列表
        :param region_a1: A1类检测区域
        :param region_a2: A2类检测区域
        :param region_a3: A3类检测区域
        :param region_b: B类检测区域
        :param region_b_delay: B类delay图片检测区域
        :param region_c: C类检测区域
        :param region_e: E类检测区域
        :param region_f: F类检测区域
        :return: 是否成功锁定窗口
        """
        self.window_title = window_title
        self.capture_region = None
        
        # 保存原始region值
        self.region_a = region_a
        self.region_a_list = region_a_list
        self.region_a1 = region_a1
        self.region_a2 = region_a2
        self.region_a3 = region_a3
        self.region_b = region_b
        self.region_b_delay = region_b_delay
        self.region_c = region_c
        self.region_e = region_e
        self.region_f = region_f
        
        if window_title:
            self.capture_region = get_window_rect_by_title(window_title, expected_width=1024, expected_height=768)
            if self.capture_region:
                window_width, window_height = self.capture_region[2], self.capture_region[3]
                self._calculate_scale_and_regions(
                    window_width, window_height, region_a, region_a_list, region_a1, region_a2, region_a3, region_b, region_b_delay, region_c, region_e, region_f
                )
                return True
            else:
                return False
        
        self._calculate_scale_and_regions(
            self.base_window_width, self.base_window_height,
            region_a, region_a_list, region_a1, region_a2, region_a3, region_b, region_b_delay, region_c, region_e, region_f
        )
        return True
    
    def _calculate_scale_and_regions(
        self,
        actual_width: int,
        actual_height: int,
        region_a: Optional[Tuple[int, int, int, int]] = None,
        region_a_list: Optional[List[Tuple[int, int, int, int]]] = None,
        region_a1: Optional[Tuple[int, int, int, int]] = None,
        region_a2: Optional[Tuple[int, int, int, int]] = None,
        region_a3: Optional[Tuple[int, int, int, int]] = None,
        region_b: Optional[Tuple[int, int, int, int]] = None,
        region_b_delay: Optional[Tuple[int, int, int, int]] = None,
        region_c: Optional[Tuple[int, int, int, int]] = None,
        region_e: Optional[Tuple[int, int, int, int]] = None,
        region_f: Optional[Tuple[int, int, int, int]] = None,
    ):
        """根据实际窗口大小计算缩放因子和缩放后的区域坐标"""
        if actual_width <= 0 or actual_height <= 0:
            self.scale_x = 1.0
            self.scale_y = 1.0
            self.scaled_region_a = region_a
            self.scaled_region_a_list = region_a_list
            self.scaled_region_a1 = region_a1
            self.scaled_region_a2 = region_a2
            self.scaled_region_a3 = region_a3
            self.scaled_region_b = region_b
            self.scaled_region_b_delay = region_b_delay
            self.scaled_region_c = region_c
            self.scaled_region_e = region_e
            self.scaled_region_f = region_f
            return
        
        self.scale_x = actual_width / self.base_window_width
        self.scale_y = actual_height / self.base_window_height
        
        def scale_region(region):
            if region is None:
                return None
            left, top, width, height = region
            return (
                int(left * self.scale_x),
                int(top * self.scale_y),
                int(width * self.scale_x),
                int(height * self.scale_y)
            )
        
        def scale_region_list(region_list):
            if region_list is None:
                return None
            return [scale_region(r) for r in region_list]
        
        self.scaled_region_a = scale_region(region_a)
        self.scaled_region_a_list = scale_region_list(region_a_list)
        self.scaled_region_a1 = scale_region(region_a1)
        self.scaled_region_a2 = scale_region(region_a2)
        self.scaled_region_a3 = scale_region(region_a3)
        self.scaled_region_b = scale_region(region_b)
        self.scaled_region_b_delay = scale_region(region_b_delay)
        self.scaled_region_c = scale_region(region_c)
        self.scaled_region_e = scale_region(region_e)
        self.scaled_region_f = scale_region(region_f)
    
    def take_screenshot(self) -> Tuple[Optional[np.ndarray], Tuple[int, int]]:
        """截取屏幕"""
        try:
            if self.capture_region and self.window_title:
                # 每隔更长时间重新获取窗口位置，避免频繁检查导致问题
                current_time = time.time()
                if current_time - self._last_window_check_time > 60.0:  # 每60秒最多检查一次窗口位置
                    self._last_window_check_time = current_time
                    if self.window_title:
                        try:
                            new_capture_region = get_window_rect_by_title(self.window_title, expected_width=1024, expected_height=768)
                            if new_capture_region:
                                if self.capture_region != new_capture_region:
                                    logger.debug('窗口位置已更新: {} -> {}'.format(self.capture_region, new_capture_region))
                                    self.capture_region = new_capture_region
                                    # 窗口位置更新后，重新计算缩放后的区域
                                    window_width, window_height = new_capture_region[2], new_capture_region[3]
                                    self._calculate_scale_and_regions(
                                        window_width, window_height,
                                        self.region_a, self.region_a_list, self.region_a1, self.region_a2, self.region_a3, self.region_b, self.region_b_delay, self.region_c,
                                        self.region_e, self.region_f
                                    )
                        except Exception as e:
                            logger.debug('更新窗口位置失败，继续使用旧位置: {}', e)
                return take_screenshot(region=self.capture_region)
            elif self.capture_region:
                return take_screenshot(region=self.capture_region)
            else:
                return take_screenshot()
        except Exception as e:
            logger.warning('Screenshot failed: {}', e)
            return None, (0, 0)
    
    def _load_template(self, template_path: str) -> Optional[np.ndarray]:
        """加载模板图片（带缓存）"""
        if template_path in self._template_cache:
            return self._template_cache[template_path]
        
        if not template_path or not os.path.isfile(template_path):
            return None
        
        # 处理中文路径问题
        template = None
        try:
            template = cv2.imread(template_path)
            if template is None and os.name == 'nt':
                try:
                    template_path_gbk = template_path.encode('gbk').decode('latin-1')
                    template = cv2.imread(template_path_gbk)
                except:
                    pass
                if template is None:
                    try:
                        with open(template_path, 'rb') as f:
                            img_data = np.frombuffer(f.read(), np.uint8)
                            template = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    except:
                        pass
        except Exception as e:
            logger.warning('Error loading template: {} - {}', template_path, e)
            return None
        
        if template is not None:
            self._template_cache[template_path] = template
        
        return template

    def detect_single(
        self,
        template_path: str,
        screenshot: np.ndarray,
        capture_offset: Tuple[int, int] = (0, 0),
        region: Optional[Tuple[int, int, int, int]] = None,
        use_hash_verify: bool = True,
    ) -> Optional[Tuple[int, int, float]]:
        """
        检测单个图片
        
        :param template_path: 模板图片路径
        :param screenshot: 截屏图像
        :param capture_offset: 截屏偏移
        :param region: 检测区域
        :param use_hash_verify: 是否使用感知哈希二次验证
        :return: 匹配位置和置信度或None（游戏窗口内坐标）: (x, y, confidence)
        """
        if not template_path or not os.path.isfile(template_path):
            return None
        
        # 使用缓存的模板
        template = self._load_template(template_path)
        if template is None:
            return None
        
        try:
            screen_pos = find_image_on_screen(
                template_path,
                threshold=self.threshold,
                screenshot=screenshot,
                capture_offset=capture_offset,
                region=region,
                template=template,
                use_hash_verify=use_hash_verify,
                use_multi_scale=self.use_multi_scale,
            )
            
            if screen_pos is None:
                return None
            
            # 将屏幕绝对坐标转换为游戏窗口内坐标
            window_rect = get_window_rect_by_title(self.window_title, expected_width=1024, expected_height=768) if self.window_title else None
            if window_rect:
                win_left, win_top, _, _ = window_rect
                return (screen_pos[0] - win_left, screen_pos[1] - win_top, screen_pos[2])
            
            return screen_pos
        except Exception as e:
            logger.warning('Error detecting image {}: {}', template_path, e)
            return None
    
    def detect_first_match(
        self,
        paths: List[str],
        screenshot: np.ndarray,
        capture_offset: Tuple[int, int] = (0, 0),
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
        """
        在路径列表中匹配所有图片，按置信度排序，返回置信度最高的匹配结果
        
        :param paths: 模板图片路径列表
        :param screenshot: 截屏图像
        :param capture_offset: 截屏偏移
        :param region: 检测区域
        :return: (路径, 屏幕坐标) 或 (None, None)
        """
        all_matches = []
        
        for p in paths:
            if not p or not os.path.isfile(p):
                continue
            result = self.detect_single(p, screenshot, capture_offset, region)
            if result is not None:
                x, y, confidence = result
                all_matches.append((p, (x, y), confidence))
        
        if not all_matches:
            return (None, None)
        
        # 按置信度从高到低排序
        all_matches.sort(key=lambda x: x[2], reverse=True)
        
        best_match = all_matches[0]
        logger.debug(f'按置信度排序结果: {[(os.path.basename(p), c) for p, _, c in all_matches]}')
        
        return (best_match[0], best_match[1])
    
    def detect_class_a(
        self,
        a_paths: List[str],
        screenshot: np.ndarray,
        capture_offset: Tuple[int, int] = (0, 0),
        region_type: str = 'default',
    ) -> bool:
        """
        检测A类图片是否存在
        
        :param a_paths: A类图片路径列表
        :param screenshot: 截图
        :param capture_offset: 截图偏移
        :param region_type: 区域类型 'default', 'a1', 'a2', 'a3'
        """
        # 根据region_type选择对应的区域
        region = None
        if region_type == 'a1':
            region = self.scaled_region_a1
        elif region_type == 'a2':
            region = self.scaled_region_a2
        elif region_type == 'a3':
            region = self.scaled_region_a3
        elif self.scaled_region_a_list:
            region = self.scaled_region_a_list
        else:
            region = self.scaled_region_a
        
        # 如果是列表，遍历所有区域
        if isinstance(region, list):
            regions_to_check = region
        elif region:
            regions_to_check = [region]
        else:
            # 如果没有设置任何区域，则不检测
            return False
        
        for path in a_paths:
            for r in regions_to_check:
                pos = self.detect_single(
                    path, screenshot, capture_offset, r
                )
                if pos is not None:
                    return True
        return False
    
    def detect_class_b(self, b_paths: List[str], screenshot, capture_offset: Tuple[int, int] = (0, 0)) -> List[MatchResult]:
        """
        检测B类图片，返回所有匹配结果（包括多个相同图片的多个位置）
        
        :return: 匹配结果列表
        """
        results = []
        for path in b_paths:
            # 根据路径判断是 delay 还是 instant，使用不同的检测区域
            path_lower = path.lower()
            if 'delay' in path_lower:
                region = self.scaled_region_b_delay if self.scaled_region_b_delay else self.scaled_region_b
            else:
                region = self.scaled_region_b
            
            positions = self.detect_all(
                path, screenshot, capture_offset, region
            )
            if positions:
                folder_name = os.path.basename(os.path.dirname(path))
                for pos in positions:
                    results.append(MatchResult(
                        path=path,
                        position=pos,
                        folder_name=folder_name,
                    ))
        return results
    
    def detect_all(
        self,
        template_path: str,
        screenshot: np.ndarray,
        capture_offset: Tuple[int, int] = (0, 0),
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> List[Tuple[int, int]]:
        """
        检测单个图片的所有出现位置
        
        :param template_path: 模板图片路径
        :param screenshot: 截屏图像
        :param capture_offset: 截屏偏移
        :param region: 检测区域
        :return: 所有匹配位置的列表 [(x1, y1), (x2, y2), ...]（游戏窗口内坐标）
        """
        if not template_path or not os.path.isfile(template_path):
            return []
        
        try:
            screen_positions = find_all_images_on_screen(
                template_path,
                threshold=self.threshold,
                screenshot=screenshot,
                capture_offset=capture_offset,
                region=region,
            )
            
            # 将屏幕绝对坐标转换为游戏窗口内坐标（只提取位置，忽略置信度）
            window_rect = get_window_rect_by_title(self.window_title, expected_width=1024, expected_height=768) if self.window_title else None
            if window_rect:
                win_left, win_top, _, _ = window_rect
                converted_positions = [(x - win_left, y - win_top) for x, y, _ in screen_positions]
                return converted_positions
            
            return [(x, y) for x, y, _ in screen_positions]
        except Exception as e:
            logger.warning('Error detecting all images {}: {}', template_path, e)
            return []
    
    def detect_class_c(
        self,
        c_paths: List[str],
        screenshot: np.ndarray,
        capture_offset: Tuple[int, int] = (0, 0),
        priority_seas: Optional[List[str]] = None,
        imgsc_root_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        检测C类图片，返回匹配到的图片路径
        
        :param c_paths: 所有C类图片路径列表
        :param screenshot: 截屏图像
        :param capture_offset: 截屏偏移
        :param priority_seas: 优先检测的海域列表
        :param imgsc_root_path: imgsC根目录，用于提取海域路径
        :return: 匹配到的图片路径或None
        """
        # 如果有优先海域列表，先尝试检测优先海域
        if priority_seas and imgsc_root_path:
            for sea_name in priority_seas:
                # 获取该海域的所有图片
                sea_paths = get_sea_c_images(imgsc_root_path, sea_name)
                if sea_paths:
                    logger.debug(f'优先检测海域: {sea_name}, 共 {len(sea_paths)} 张图片')
                    matched_path, _ = self.detect_first_match(
                        sea_paths, screenshot, capture_offset, self.scaled_region_c
                    )
                    if matched_path:
                        logger.debug(f'在优先海域 {sea_name} 中检测到: {os.path.basename(matched_path)}')
                        return matched_path
            
            # 优先海域都检测不到，输出日志
            logger.debug(f'优先海域 {priority_seas} 未检测到匹配，扩大检测范围')
        
        # 优先海域检测不到或没有优先海域，检测所有C类图片
        matched_path, _ = self.detect_first_match(
            c_paths, screenshot, capture_offset, self.scaled_region_c
        )
        return matched_path
    
    def click_at(self, x: int, y: int, button: str = 'left') -> bool:
        """点击指定位置（使用游戏窗口内坐标）"""
        try:
            click_at(x, y, button, self.window_title)
            return True
        except Exception as e:
            logger.warning('Click failed: {}', e)
            return False
    
    def double_click_at(self, x: int, y: int, button: str = 'left') -> bool:
        """双击指定位置（使用游戏窗口内坐标）"""
        try:
            double_click_at(x, y, button, self.window_title)
            return True
        except Exception as e:
            logger.warning('Double click failed: {}', e)
            return False
    
    def draw_detection_regions(
        self,
        screenshot: np.ndarray,
        save_path: Optional[str] = None
    ) -> np.ndarray:
        """在截图上画出检测区域的边框"""
        img = screenshot.copy()
        
        colors = {
            'A': (255, 255, 255),      # 白色
            'B': (0, 165, 255),        # 橙色
            'B_delay': (0, 255, 255),  # 黄色
            'C': (0, 0, 255)           # 红色
        }
        
        if self.scaled_region_a:
            left, top, width, height = self.scaled_region_a
            cv2.rectangle(img, (left, top), (left + width, top + height), colors['A'], 2)
            cv2.putText(img, 'A', (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['A'], 2)
        
        if self.scaled_region_b:
            left, top, width, height = self.scaled_region_b
            cv2.rectangle(img, (left, top), (left + width, top + height), colors['B'], 2)
            cv2.putText(img, 'B', (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['B'], 2)
        
        if self.scaled_region_b_delay:
            left, top, width, height = self.scaled_region_b_delay
            cv2.rectangle(img, (left, top), (left + width, top + height), colors['B_delay'], 2)
            cv2.putText(img, 'B_delay', (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['B_delay'], 2)
        
        if self.scaled_region_c:
            left, top, width, height = self.scaled_region_c
            cv2.rectangle(img, (left, top), (left + width, top + height), colors['C'], 2)
            cv2.putText(img, 'C', (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors['C'], 2)
        
        if save_path:
            try:
                save_dir = os.path.dirname(save_path)
                if save_dir and not os.path.exists(save_dir):
                    os.makedirs(save_dir, exist_ok=True)
                cv2.imwrite(save_path, img)
                logger.debug('Detection regions image saved: {}', save_path)
            except Exception as e:
                logger.warning('Failed to save detection regions image: {}', e)
        
        return img
    
    def get_window_size(self) -> Tuple[int, int]:
        """获取当前窗口大小"""
        if self.capture_region:
            return (self.capture_region[2], self.capture_region[3])
        return (self.base_window_width, self.base_window_height)
    
    def get_scale_factors(self) -> Tuple[float, float]:
        """获取缩放因子"""
        return (self.scale_x, self.scale_y)


def get_sea_name_from_path(image_path: str, imgsc_root: str) -> str:
    """从图片路径中提取海域名称"""
    try:
        rel_path = os.path.relpath(image_path, imgsc_root)
        parts = rel_path.split(os.sep)
        if len(parts) >= 1:
            return parts[0]
    except:
        pass
    return ''


def get_all_c_images(imgsc_root: str) -> List[str]:
    """获取imgsC文件夹下所有的C类图片"""
    all_c_paths = []
    if not imgsc_root or not os.path.isdir(imgsc_root):
        return all_c_paths
    
    for sea in os.listdir(imgsc_root):
        sea_dir = os.path.join(imgsc_root, sea)
        if os.path.isdir(sea_dir):
            for f in os.listdir(sea_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    all_c_paths.append(os.path.join(sea_dir, f))
    return all_c_paths


def get_sea_c_images(imgsc_root: str, sea_name: str) -> List[str]:
    """
    获取imgsC文件夹下特定海域的C类图片
    
    :param imgsc_root: imgsC根目录
    :param sea_name: 海域名称
    :return: 该海域下的图片路径列表
    """
    sea_c_paths = []
    if not imgsc_root or not os.path.isdir(imgsc_root) or not sea_name:
        return sea_c_paths
    
    sea_dir = os.path.join(imgsc_root, sea_name)
    if os.path.isdir(sea_dir):
        for f in os.listdir(sea_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                sea_c_paths.append(os.path.join(sea_dir, f))
    
    return sea_c_paths
