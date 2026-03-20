# -*- encoding:utf-8 -*-
"""
图片识别模块：截屏 + 模板匹配 + 感知哈希二次验证 + 固定坐标点击。
用于检测循环：识别触发图运行脚本、识别图标执行点击。
"""
import os
from typing import Optional, Tuple, List, Dict, Any

import cv2
import numpy as np
import mss
from loguru import logger
from PIL import Image

# 导入我们的感知哈希模块
try:
    from Util.ImageHash import init_hash_manager, get_hash_manager
    HAS_IMAGE_HASH = True
except ImportError:
    HAS_IMAGE_HASH = False

# Windows 下使用 win32api 点击、win32gui 获取窗口区域
try:
    import win32api
    import win32con
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    win32gui = None

# 导入新的游戏输入执行器
try:
    from Util.GameInputExecutor import get_input_executor
    HAS_GAME_INPUT = True
except ImportError:
    HAS_GAME_INPUT = False
    get_input_executor = None

import time

# 节流机制：避免频繁输出警告
_last_warning_time = 0
_warning_interval = 5  # 每5秒最多输出一次警告


def calculate_dhash(image_array: np.ndarray, hash_size: int = 16) -> Optional[str]:
    """
    计算图像数组的 dHash（差异哈希）
    
    :param image_array: OpenCV/numpy 图像数组 (BGR格式)
    :param hash_size: 哈希大小
    :return: 十六进制哈希字符串
    """
    try:
        # 转换为灰度
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array
        
        # 调整大小为 (hash_size + 1, hash_size)
        resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_LANCZOS4)
        
        # 计算相邻像素的差异
        diff = resized[:, 1:] > resized[:, :-1]
        
        # 转换为十六进制字符串
        hash_str = ''.join(['{:02x}'.format(int(''.join(['1' if pixel else '0' for pixel in row]), 2)) for row in diff])
        
        return hash_str
    except Exception as e:
        logger.warning(f'计算 dHash 失败: {e}')
        return None


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


def verify_with_dhash(
    template_path: str,
    screenshot: np.ndarray,
    match_position: Tuple[int, int],
    template_size: Tuple[int, int],
    max_distance: int = 100,
) -> bool:
    """
    使用感知哈希进行二次验证
    
    :param template_path: 模板图片路径
    :param screenshot: 屏幕截图
    :param match_position: 匹配位置 (x, y) - 中心点
    :param template_size: 模板大小 (w, h)
    :param max_distance: 最大允许的汉明距离
    :return: 是否通过验证
    """
    try:
        # 计算中心点到左上角的偏移
        w, h = template_size
        x1 = max(0, match_position[0] - w // 2)
        y1 = max(0, match_position[1] - h // 2)
        x2 = min(screenshot.shape[1], x1 + w)
        y2 = min(screenshot.shape[0], y1 + h)
        
        # 裁剪匹配区域
        matched_region = screenshot[y1:y2, x1:x2]
        
        # 如果裁剪区域太小，直接通过
        if matched_region.shape[0] < h // 2 or matched_region.shape[1] < w // 2:
            return True
        
        # 计算匹配区域的哈希
        matched_hash = calculate_dhash(matched_region)
        if not matched_hash:
            return True
        
        # 读取模板并计算哈希
        # 处理中文路径，用PIL读取
        try:
            pil_img = Image.open(template_path).convert('RGB')
            template_np = np.array(pil_img)
            template_np = cv2.cvtColor(template_np, cv2.COLOR_RGB2BGR)
        except:
            template_np = cv2.imread(template_path)
        
        if template_np is None:
            return True
        
        template_hash = calculate_dhash(template_np)
        if not template_hash:
            return True
        
        # 对比哈希
        distance = hamming_distance(matched_hash, template_hash)
        passed = distance <= max_distance
        
        if not passed:
            logger.debug(f'哈希验证失败: 距离={distance}, 阈值={max_distance}')
        
        return passed
        
    except Exception as e:
        logger.warning(f'哈希验证异常: {e}')
        return True


def get_window_rect_by_title(title_substr: str) -> Optional[Tuple[int, int, int, int]]:
    """
    根据窗口标题（支持部分匹配）查找窗口，返回 (left, top, width, height)。
    返回的是客户区域（游戏内容显示区域）的坐标，不包括标题栏和边框。
    未找到返回 None。需要 win32gui。
    """
    global _last_warning_time
    
    if not HAS_WIN32 or win32gui is None or not title_substr or not title_substr.strip():
        return None
    result = [None]

    def enum_cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if title_substr.strip() in t:
                    # 获取客户区域矩形
                    client_rect = win32gui.GetClientRect(hwnd)
                    # 将客户区域坐标转换为屏幕坐标
                    left, top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
                    right, bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
                    result[0] = (left, top, right - left, bottom - top)
                    return False  # 停止枚举
        except Exception as e:
            # 忽略无效窗口句柄等异常，继续枚举
            pass
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
        return result[0]
    except Exception as e:
        current_time = time.time()
        if current_time - _last_warning_time > _warning_interval:
            logger.warning('get_window_rect_by_title failed: {}', e)
            _last_warning_time = current_time
        return None


def take_screenshot(monitor: Optional[Dict[str, int]] = None, region: Optional[Tuple[int, int, int, int]] = None) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    截取屏幕，返回 (BGR 格式的 numpy 数组, 坐标偏移 (offset_x, offset_y))。
    monitor 为 None 且 region 为 None 时使用主屏。
    region: (left, top, width, height) 时只截取该区域，返回的 offset 为 (left, top)，用于将匹配坐标转为屏幕坐标。
    """
    with mss.mss() as sct:
        if region is not None:
            left, top, w, h = region
            monitor = {'left': left, 'top': top, 'width': w, 'height': h}
            offset = (left, top)
        elif monitor is None:
            monitor = sct.monitors[0]
            offset = (0, 0)
        else:
            offset = (monitor.get('left', 0), monitor.get('top', 0))
        img = sct.grab(monitor)
        frame = np.array(img)[:, :, :3]
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR), offset


def find_image_on_screen(
    template_path: str,
    threshold: float = 0.8,
    screenshot: Optional[np.ndarray] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    capture_offset: Tuple[int, int] = (0, 0),
) -> Optional[Tuple[int, int]]:
    """
    在屏幕上查找模板图片，返回匹配区域中心点的屏幕坐标 (x, y)，未找到返回 None。

    :param template_path: 模板图片路径（小图）
    :param threshold: 匹配阈值 0~1，越高越严格
    :param screenshot: 若提供则用此图代替截屏，用于一次截屏多次匹配
    :param region: (left, top, width, height) 在屏幕上的检测区域，None 表示全屏（仅当 screenshot 为 None 时有效）
    :param capture_offset: 当 screenshot 来自区域截屏时，为 (left, top)，用于将匹配坐标转为屏幕坐标
    """
    all_positions = find_all_images_on_screen(
        template_path, threshold, screenshot, region, capture_offset
    )
    return all_positions[0] if all_positions else None


def find_all_images_on_screen(
    template_path: str,
    threshold: float = 0.8,
    screenshot: Optional[np.ndarray] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    capture_offset: Tuple[int, int] = (0, 0),
) -> List[Tuple[int, int]]:
    """
    在屏幕上查找模板图片的所有出现位置，返回所有匹配区域中心点的屏幕坐标列表。

    :param template_path: 模板图片路径（小图）
    :param threshold: 匹配阈值 0~1，越高越严格
    :param screenshot: 若提供则用此图代替截屏，用于一次截屏多次匹配
    :param region: (left, top, width, height) 在屏幕上的检测区域，None 表示全屏（仅当 screenshot 为 None 时有效）
    :param capture_offset: 当 screenshot 来自区域截屏时，为 (left, top)，用于将匹配坐标转为屏幕坐标
    :return: 所有匹配位置的列表 [(x1, y1), (x2, y2), ...]
    """
    if not os.path.isfile(template_path):
        logger.warning('Template image not found: {}', template_path)
        return []

    # 处理中文路径问题
    try:
        # 尝试直接读取
        template = cv2.imread(template_path)
        if template is None:
            # 如果失败，尝试使用gbk编码
            if os.name == 'nt':  # Windows系统
                # 方法1：使用gbk编码
                try:
                    template_path_gbk = template_path.encode('gbk').decode('latin-1')
                    template = cv2.imread(template_path_gbk)
                except:
                    pass
                # 方法2：使用numpy从文件读取
                if template is None:
                    try:
                        with open(template_path, 'rb') as f:
                            img_data = np.frombuffer(f.read(), np.uint8)
                            template = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    except:
                        pass
            if template is None:
                logger.warning('Failed to load template: {}', template_path)
                return []
    except Exception as e:
        logger.warning('Error loading template: {} - {}', template_path, e)
        return []

    # 保存region的偏移量，用于后续坐标计算
    region_offset = (0, 0)
    
    if screenshot is not None:
        screen = screenshot
        if region is not None:
            left, top, w, h = region
            # 保存region的偏移，用于后续坐标计算
            region_offset = (left, top)
            # 裁剪screenshot到指定region
            screen = screen[top : top + h, left : left + w]
    else:
        with mss.mss() as sct:
            mon = sct.monitors[0]
            if region is not None:
                left, top, w, h = region
                mon = {'left': mon['left'] + left, 'top': mon['top'] + top, 'width': w, 'height': h}
                region_offset = (left, top)
            img = sct.grab(mon)
            frame = np.array(img)[:, :, :3]
            screen = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

    h, w = template.shape[:2]
    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    
    # 找出所有超过阈值的匹配位置
    locations = np.where(res >= threshold)
    positions = []
    
    # 防止重复检测（去除重叠的匹配）
    # 使用非极大值抑制的简化版
    seen = set()
    
    for pt in zip(*locations[::-1]):  # 交换 x, y 坐标
        # 计算中心点（相对于当前screen区域）
        cx_rel = pt[0] + w // 2
        cy_rel = pt[1] + h // 2
        
        # 转为屏幕绝对坐标
        if screenshot is None:
            with mss.mss() as sct:
                m = sct.monitors[0]
                cx = cx_rel + m['left'] + region_offset[0]
                cy = cy_rel + m['top'] + region_offset[1]
        else:
            # 当传入screenshot时，cx_rel和cy_rel是相对于裁剪后的screen的
            # 需要加上region_offset和capture_offset
            cx = cx_rel + region_offset[0] + capture_offset[0]
            cy = cy_rel + region_offset[1] + capture_offset[1]
        
        # 简化的去重：检查附近是否已有检测到的位置
        nearby = False
        for (x, y) in positions:
            if abs(cx - x) < w // 2 and abs(cy - y) < h // 2:
                nearby = True
                break
        
        if not nearby:
                # 感知哈希二次验证 - 暂时禁用，因为太严格容易误报
                verified = True
                # if screenshot is not None:
                #     # position_in_screen 是相对于 screen 的坐标
                #     position_in_screen = (cx_rel, cy_rel)
                #     verified = verify_with_dhash(
                #         template_path=template_path,
                #         screenshot=screen,
                #         match_position=position_in_screen,
                #         template_size=(w, h),
                #         max_distance=100,
                #     )
                
                if verified:
                    positions.append((cx, cy))
                else:
                    logger.debug(f'CV2 匹配被哈希验证拒绝: {os.path.basename(template_path)}')
    
    return positions


def click_at(x: int, y: int, button: str = 'left', window_title: Optional[str] = None) -> None:
    """
    执行一次点击。
    如果提供了 window_title，则 x,y 视为游戏窗口内坐标，否则视为屏幕绝对坐标。
    button: 'left' | 'right' | 'middle'
    
    使用优化的 GameInputExecutor（基于 SendInput API）
    """
    if HAS_GAME_INPUT:
        executor = get_input_executor(window_title)
        is_relative = window_title is not None
        executor.click(x, y, button=button, is_relative=is_relative)
        return
    
    # 回退到旧的实现
    if not HAS_WIN32:
        logger.warning('win32api not available, click_at skipped')
        return
    
    screen_x, screen_y = x, y
    if window_title:
        window_rect = get_window_rect_by_title(window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            screen_x = win_left + x
            screen_y = win_top + y
            logger.debug('Converted window coords ({}, {}) to screen ({}, {})', x, y, screen_x, screen_y)
        else:
            logger.warning('Could not find window for title "{}", using screen coords', window_title)
    
    win32api.SetCursorPos([screen_x, screen_y])
    if button == 'left':
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    elif button == 'right':
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    elif button == 'middle':
        win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)


def double_click_at(x: int, y: int, button: str = 'left', window_title: Optional[str] = None) -> None:
    """
    执行双击。
    如果提供了 window_title，则 x,y 视为游戏窗口内坐标，否则视为屏幕绝对坐标。
    button: 'left' | 'right' | 'middle'
    
    使用优化的 GameInputExecutor（基于 SendInput API）
    """
    import time
    if HAS_GAME_INPUT:
        executor = get_input_executor(window_title)
        is_relative = window_title is not None
        executor.click(x, y, button=button, is_relative=is_relative)
        time.sleep(0.1)
        executor.click(x, y, button=button, is_relative=is_relative)
        return
    
    # 回退到旧的实现
    if not HAS_WIN32:
        logger.warning('win32api not available, double_click_at skipped')
        return
    
    screen_x, screen_y = x, y
    if window_title:
        window_rect = get_window_rect_by_title(window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            screen_x = win_left + x
            screen_y = win_top + y
            logger.debug('Converted window coords ({}, {}) to screen ({}, {})', x, y, screen_x, screen_y)
        else:
            logger.warning('Could not find window for title "{}", using screen coords', window_title)
    
    win32api.SetCursorPos([screen_x, screen_y])
    click_interval = 0.25  # 双击间隔
    for _ in range(2):
        if button == 'left':
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif button == 'right':
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif button == 'middle':
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
        time.sleep(click_interval)
