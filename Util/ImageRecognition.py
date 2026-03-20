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


def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    图像预处理：灰度化 + 边缘增强
    
    :param image: 输入图像 (BGR格式)
    :return: 处理后的图像
    """
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 高斯模糊去噪
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 边缘增强（使用Sobel算子）
    sobelx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    sobel = cv2.magnitude(sobelx, sobely)
    sobel = np.uint8(np.clip(sobel, 0, 255))
    
    return sobel


def _non_max_suppression(matches: List[Tuple[int, int, float, float]], 
                         template_width: int, 
                         template_height: int,
                         iou_threshold: float = 0.5) -> List[Tuple[int, int]]:
    """
    非极大值抑制，去除重叠的匹配
    
    :param matches: 匹配列表 [(cx, cy, score, scale), ...]
    :param template_width: 模板宽度
    :param template_height: 模板高度
    :param iou_threshold: IOU阈值
    :return: 去重后的位置列表 [(cx, cy), ...]
    """
    result = _non_max_suppression_with_scale(matches, template_width, template_height, iou_threshold)
    return [(cx, cy) for cx, cy, scale in result]


def _non_max_suppression_with_scale(matches: List[Tuple[int, int, float, float]], 
                                    template_width: int, 
                                    template_height: int,
                                    iou_threshold: float = 0.5) -> List[Tuple[int, int, float]]:
    """
    非极大值抑制，去除重叠的匹配（返回包含scale的结果）
    
    :param matches: 匹配列表 [(cx, cy, score, scale), ...]
    :param template_width: 模板宽度
    :param template_height: 模板高度
    :param iou_threshold: IOU阈值
    :return: 去重后的匹配列表 [(cx, cy, scale), ...]
    """
    if not matches:
        return []
    
    # 按匹配分数排序（从高到低）
    matches = sorted(matches, key=lambda x: x[2], reverse=True)
    
    keep = []
    suppressed = set()
    
    for i, (cx1, cy1, score1, scale1) in enumerate(matches):
        if i in suppressed:
            continue
        
        keep.append((cx1, cy1, scale1))
        
        # 计算当前框的边界
        w1 = template_width * scale1
        h1 = template_height * scale1
        x1_min, x1_max = cx1 - w1/2, cx1 + w1/2
        y1_min, y1_max = cy1 - h1/2, cy1 + h1/2
        
        # 检查后续匹配是否与当前框重叠
        for j in range(i + 1, len(matches)):
            if j in suppressed:
                continue
            
            cx2, cy2, score2, scale2 = matches[j]
            w2 = template_width * scale2
            h2 = template_height * scale2
            x2_min, x2_max = cx2 - w2/2, cx2 + w2/2
            y2_min, y2_max = cy2 - h2/2, cy2 + h2/2
            
            # 计算IOU
            inter_x_min = max(x1_min, x2_min)
            inter_x_max = min(x1_max, x2_max)
            inter_y_min = max(y1_min, y2_min)
            inter_y_max = min(y1_max, y2_max)
            
            if inter_x_max > inter_x_min and inter_y_max > inter_y_min:
                inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
                area1 = w1 * h1
                area2 = w2 * h2
                union_area = area1 + area2 - inter_area
                iou = inter_area / union_area if union_area > 0 else 0
                
                if iou > iou_threshold:
                    suppressed.add(j)
    
    return keep

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
import threading

# 线程局部存储的 mss 对象（避免频繁创建导致句柄泄漏，同时保证线程安全）
_thread_local = threading.local()
def _get_sct():
    if not hasattr(_thread_local, 'sct'):
        _thread_local.sct = mss.mss()
    return _thread_local.sct

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
) -> Tuple[bool, int]:
    """
    使用感知哈希进行二次验证
    
    :param template_path: 模板图片路径
    :param screenshot: 屏幕截图
    :param match_position: 匹配位置 (x, y) - 中心点
    :param template_size: 模板大小 (w, h)
    :param max_distance: 最大允许的汉明距离
    :return: (是否通过验证, 实际汉明距离)
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
            return True, 0
        
        # 计算匹配区域的哈希
        matched_hash = calculate_dhash(matched_region)
        if not matched_hash:
            return True, 0
        
        # 读取模板并计算哈希
        # 处理中文路径，用PIL读取
        try:
            pil_img = Image.open(template_path).convert('RGB')
            template_np = np.array(pil_img)
            template_np = cv2.cvtColor(template_np, cv2.COLOR_RGB2BGR)
        except:
            template_np = cv2.imread(template_path)
        
        if template_np is None:
            return True, 0
        
        template_hash = calculate_dhash(template_np)
        if not template_hash:
            return True, 0
        
        # 对比哈希
        distance = hamming_distance(matched_hash, template_hash)
        passed = distance <= max_distance
        
        if not passed:
            logger.debug(f'哈希验证失败: 距离={distance}, 阈值={max_distance}')
        
        return passed, distance
        
    except Exception as e:
        logger.warning(f'哈希验证异常: {e}')
        return True, 0


def get_window_rect_by_title(title_substr: str, expected_width: Optional[int] = None, expected_height: Optional[int] = None) -> Optional[Tuple[int, int, int, int]]:
    """
    根据窗口标题（支持部分匹配）查找窗口，返回 (left, top, width, height)。
    返回的是客户区域（游戏内容显示区域）的坐标，不包括标题栏和边框。
    未找到返回 None。需要 win32gui。
    
    :param title_substr: 窗口标题子串
    :param expected_width: 期望的窗口宽度（如 1024），用于过滤不匹配的窗口
    :param expected_height: 期望的窗口高度（如 768），用于过滤不匹配的窗口
    """
    global _last_warning_time
    
    if not HAS_WIN32 or win32gui is None or not title_substr or not title_substr.strip():
        return None
    
    result = [None]
    found_windows = []

    def enum_cb(hwnd, _):
        try:
            # 检查窗口句柄是否有效
            if not win32gui.IsWindow(hwnd):
                return True
            
            # 检查窗口是否可见且有标题
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            try:
                t = win32gui.GetWindowText(hwnd)
                if not t:
                    return True
            except Exception:
                # GetWindowText 失败，跳过此窗口
                return True
            
            # 检查标题是否匹配
            if title_substr.strip() not in t:
                return True
            
            # 获取客户区域矩形
            try:
                client_rect = win32gui.GetClientRect(hwnd)
                if not client_rect:
                    return True
            except Exception as e:
                logger.debug(f'GetClientRect 失败 (hwnd={hwnd}, title={t}): {e}')
                return True
            
            width = client_rect[2] - client_rect[0]
            height = client_rect[3] - client_rect[1]
            
            # 记录找到的窗口（包括尺寸信息）
            found_windows.append((hwnd, t, width, height))
            
            # 如果指定了期望尺寸，检查是否匹配
            if expected_width is not None or expected_height is not None:
                width_match = expected_width is None or abs(width - expected_width) < 50  # 允许 50 像素误差
                height_match = expected_height is None or abs(height - expected_height) < 50
                if not (width_match and height_match):
                    logger.trace(f'窗口尺寸不匹配 (hwnd={hwnd}, title={t}): {width}x{height} != {expected_width}x{expected_height}')
                    return True
            
            # 将客户区域坐标转换为屏幕坐标
            try:
                left, top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
                right, bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
                result[0] = (left, top, right - left, bottom - top)
                logger.trace(f'找到窗口：hwnd={hwnd}, title={t}, size={width}x{height}, rect={result[0]}')
                return False  # 停止枚举
            except Exception as e:
                logger.debug(f'ClientToScreen 失败 (hwnd={hwnd}, title={t}): {e}')
                return True
                
        except ValueError as e:
            # PyObject is NULL 或其他窗口句柄无效错误
            if "NULL" in str(e) or "hwnd" in str(e).lower():
                # 窗口句柄无效，跳过
                logger.debug(f'窗口句柄无效：hwnd={hwnd}')
                return True
            # 其他 ValueError，重新抛出
            raise
        except Exception as e:
            # 忽略其他异常，继续枚举
            logger.debug(f'枚举窗口未知错误 (hwnd={hwnd}): {e}')
            pass
        
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
        
        if result[0] is None:
            # 未找到窗口，记录所有可见窗口
            if found_windows:
                logger.debug(f'未找到匹配 "{title_substr}" 的窗口，找到以下窗口：{[(hwnd, t, f"{w}x{h}") for hwnd, t, w, h in found_windows]}')
        
        return result[0]
    except Exception as e:
        current_time = time.time()
        # 将 EnumWindows 相关的异常完全忽略，只记录到最细粒度
        if "EnumWindows" in str(e) or "无效的窗口句柄" in str(e):
            logger.trace('get_window_rect_by_title (EnumWindows): {}', e)
        else:
            if current_time - _last_warning_time > _warning_interval:
                logger.debug('get_window_rect_by_title failed: {}', e)
                _last_warning_time = current_time
        return None


def take_screenshot(monitor: Optional[Dict[str, int]] = None, region: Optional[Tuple[int, int, int, int]] = None) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    截取屏幕，返回 (BGR 格式的 numpy 数组, 坐标偏移 (offset_x, offset_y))。
    monitor 为 None 且 region 为 None 时使用主屏。
    region: (left, top, width, height) 时只截取该区域，返回的 offset 为 (left, top)，用于将匹配坐标转为屏幕坐标。
    """
    sct = _get_sct()
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
    template: Optional[np.ndarray] = None,
    use_hash_verify: bool = True,
    use_multi_scale: bool = False,  # 是否使用多尺度检测
) -> Optional[Tuple[int, int, float]]:
    """
    在屏幕上查找模板图片，返回匹配区域中心点的屏幕坐标 (x, y, confidence)，未找到返回 None。

    :param template_path: 模板图片路径（小图）
    :param threshold: 匹配阈值 0~1，越高越严格
    :param screenshot: 若提供则用此图代替截屏，用于一次截屏多次匹配
    :param region: (left, top, width, height) 在屏幕上的检测区域，None 表示全屏（仅当 screenshot 为 None 时有效）
    :param capture_offset: 当 screenshot 来自区域截屏时，为 (left, top)，用于将匹配坐标转为屏幕坐标
    :param template: 可选，预加载的模板图片，避免重复读取文件
    :param use_hash_verify: 是否使用感知哈希二次验证，默认True
    :param use_multi_scale: 是否使用多尺度检测，默认False（仅使用原始尺寸）
    """
    all_positions = find_all_images_on_screen(
        template_path, threshold, screenshot, region, capture_offset, template, use_hash_verify, use_multi_scale
    )
    return all_positions[0] if all_positions else None


def find_all_images_on_screen(
    template_path: str,
    threshold: float = 0.8,
    screenshot: Optional[np.ndarray] = None,
    region: Optional[Tuple[int, int, int, int]] = None,
    capture_offset: Tuple[int, int] = (0, 0),
    template: Optional[np.ndarray] = None,
    use_hash_verify: bool = True,
    use_multi_scale: bool = False,  # 是否使用多尺度检测
) -> List[Tuple[int, int, float]]:
    """
    在屏幕上查找模板图片的所有出现位置，返回所有匹配区域中心点的屏幕坐标列表。

    :param template_path: 模板图片路径（小图）
    :param threshold: 匹配阈值 0~1，越高越严格
    :param screenshot: 若提供则用此图代替截屏，用于一次截屏多次匹配
    :param region: (left, top, width, height) 在屏幕上的检测区域，None 表示全屏（仅当 screenshot 为 None 时有效）
    :param capture_offset: 当 screenshot 来自区域截屏时，为 (left, top)，用于将匹配坐标转为屏幕坐标
    :param template: 可选，预加载的模板图片，避免重复读取文件
    :param use_hash_verify: 是否使用感知哈希二次验证，默认True
    :param use_multi_scale: 是否使用多尺度检测，默认False（仅使用原始尺寸）
    :return: 所有匹配位置的列表 [(x1, y1, confidence1), (x2, y2, confidence2), ...]
    """
    # 如果没有传入预加载的模板，则从文件读取
    if template is None:
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

    # 保存原始screen用于哈希验证
    screen_original = screen.copy()
    
    # 图像预处理：灰度化 + 边缘增强（可选，通过环境变量控制）
    use_preprocessing = os.environ.get('CV_PREPROCESS', '0') == '1'
    if use_preprocessing:
        screen_processed = _preprocess_image(screen)
        template_processed = _preprocess_image(template)
    else:
        # 转换为灰度图进行匹配（保持原有行为）
        if len(screen.shape) == 3:
            screen_processed = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        else:
            screen_processed = screen
        if len(template.shape) == 3:
            template_processed = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_processed = template
    
    # 多尺度检测
    if use_multi_scale:
        scales = [0.95, 1.0, 1.05]  # 使用多尺度
    else:
        scales = [1.0]  # 只使用原始尺寸
    
    all_matches = []
    
    # 检查检测区域是否有效（至少1x1）
    screen_h, screen_w = screen_processed.shape[:2]
    if screen_h <= 0 or screen_w <= 0:
        logger.info('检测区域为空或无效 ({}x{})，跳过匹配'.format(screen_w, screen_h))
        return []
    
    # 检查模板是否比检测区域大，如果是则跳过
    template_h, template_w = template_processed.shape[:2]
    if template_h > screen_h or template_w > screen_w:
        logger.info('模板 {} ({}x{}) 比检测区域 ({}x{}) 大，跳过匹配'.format(
            os.path.basename(template_path), template_w, template_h, screen_w, screen_h))
        return []
    
    for scale in scales:
        if scale == 1.0:
            scaled_template = template_processed
        else:
            h, w = template_processed.shape[:2]
            new_w, new_h = int(w * scale), int(h * scale)
            # 确保缩放后的模板至少有1x1像素
            if new_w <= 0 or new_h <= 0:
                logger.info('缩放后的模板尺寸无效 ({}x{}, scale={})，跳过'.format(new_w, new_h, scale))
                continue
            scaled_template = cv2.resize(template_processed, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # 再次检查缩放后的模板是否比检测区域大
        scaled_h, scaled_w = scaled_template.shape[:2]
        screen_h, screen_w = screen_processed.shape[:2]
        
        if scaled_h > screen_h or scaled_w > screen_w:
            logger.info('缩放后的模板 ({}x{}, scale={}) 比检测区域 ({}x{}) 大'.format(
                scaled_w, scaled_h, scale, screen_w, screen_h))
            # 如果是放大的比例，尝试使用原始尺寸
            if scale > 1.0:
                logger.info('尝试使用原始尺寸 (scale=1.0) 替代')
                scaled_template = template_processed
                scaled_h, scaled_w = template_h, template_w
                # 再次检查原始尺寸是否适合
                if scaled_h > screen_h or scaled_w > screen_w:
                    logger.info('原始尺寸也不适合，跳过此缩放比例')
                    continue
            else:
                # 对于缩小比例，如果还是太大，就跳过
                continue
        
        try:
            # 模板匹配
            res = cv2.matchTemplate(screen_processed, scaled_template, cv2.TM_CCOEFF_NORMED)
            
            # 找出所有超过阈值的匹配位置
            locations = np.where(res >= threshold)
            
            for pt in zip(*locations[::-1]):
                th, tw = scaled_template.shape[:2]
                # 计算中心点（相对于当前screen区域）
                cx_rel = pt[0] + tw // 2
                cy_rel = pt[1] + th // 2
                match_score = res[pt[1], pt[0]]
                all_matches.append((cx_rel, cy_rel, match_score, scale))
        except Exception as e:
            logger.info('模板匹配出错 (scale={}): {}'.format(scale, e))
            continue
    
    # 非极大值抑制，去除重叠的匹配
    # 返回的是 (cx, cy, scale) 列表
    filtered_matches = _non_max_suppression_with_scale(all_matches, template.shape[1], template.shape[0])
    
    # 转换为屏幕绝对坐标并验证
    final_positions = []
    for cx_rel, cy_rel, scale in filtered_matches:
        # 转为屏幕绝对坐标
        if screenshot is None:
            with mss.mss() as sct:
                m = sct.monitors[0]
                cx = cx_rel + m['left'] + region_offset[0]
                cy = cy_rel + m['top'] + region_offset[1]
        else:
            cx = cx_rel + region_offset[0] + capture_offset[0]
            cy = cy_rel + region_offset[1] + capture_offset[1]
        
        # 感知哈希二次验证
        # 注意：对于 imgsC 文件夹（城市标识），哈希验证效果不佳，已禁用
        # is_imgsC = 'imgsC' in template_path.replace('\\', '/').split('/')
        # should_hash_verify = use_hash_verify and is_imgsC
        should_hash_verify = False  # 暂时禁用哈希验证
        
        verified = True
        actual_distance = 0
        if should_hash_verify and screenshot is not None:
            actual_w = int(template.shape[1] * scale)
            actual_h = int(template.shape[0] * scale)
            
            # 智能调节阈值：从20开始，逐步放宽到25、30、35、40
            # 阈值说明：≤20严格，≤30中等，≤40宽松，≥50基本无效
            max_distance_levels = [20, 25, 30, 35, 40]
            for max_dist in max_distance_levels:
                verified, actual_distance = verify_with_dhash(
                    template_path=template_path,
                    screenshot=screen_original,
                    match_position=(cx_rel, cy_rel),
                    template_size=(actual_w, actual_h),
                    max_distance=max_dist,
                )
                if verified:
                    if max_dist > 30:
                        logger.debug(f'哈希验证通过（放宽阈值）: {os.path.basename(template_path)}, 距离={actual_distance}, 阈值={max_dist}')
                    break
            
            if not verified:
                logger.debug(f'CV2 匹配被哈希验证拒绝: {os.path.basename(template_path)}, 距离={actual_distance}')
        
        if verified:
            final_positions.append((cx, cy, match_score))
    
    return final_positions


def click_at(x: int, y: int, button: str = 'left', window_title: Optional[str] = None) -> bool:
    """
    执行一次点击。
    如果提供了 window_title，则 x,y 视为游戏窗口内坐标，否则视为屏幕绝对坐标。
    button: 'left' | 'right' | 'middle'
    
    使用优化的 GameInputExecutor（基于 SendInput API）
    
    注意：
    - x, y 是窗口内绝对像素坐标（相对于窗口左上角）
    - 会自动转换为相对坐标（0-1）传给 GameInputExecutor
    - GameInputExecutor 会重新获取窗口位置并计算屏幕坐标
    
    返回：
        bool: 是否点击成功
    """
    try:
        if HAS_GAME_INPUT:
            executor = get_input_executor(window_title)
            
            # 将绝对像素坐标转换为相对坐标（0-1）
            if window_title:
                window_rect = get_window_rect_by_title(window_title)
                if window_rect:
                    win_width, win_height = window_rect[2], window_rect[3]
                    # 转换为相对坐标
                    rel_x = x / win_width
                    rel_y = y / win_height
                    logger.debug(f'坐标转换：像素 ({x}, {y}) → 相对 ({rel_x:.3f}, {rel_y:.3f}) [窗口：{win_width}x{win_height}]')
                    executor.click(rel_x, rel_y, button=button, is_relative=True)
                    return True
                else:
                    logger.warning(f'找不到窗口 "{window_title}"，使用像素坐标 ({x}, {y})')
            
            # 没有窗口标题或找不到窗口，直接使用像素坐标
            executor.click(x, y, button=button, is_relative=False)
            return True
        
        # 回退到旧的实现
        if not HAS_WIN32:
            logger.warning('win32api not available, click_at skipped')
            return False
        
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
        
        return True
        
    except Exception as e:
        logger.error(f'click_at failed: {e}')
        return False


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
