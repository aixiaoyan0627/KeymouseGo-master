# -*- encoding:utf-8 -*-
"""
动作执行器：负责鼠标、键盘等动作的执行

职责：
- 点击指定位置
- 双击指定位置
- 键盘按键
- 移动鼠标
"""
import time
import random
from typing import Optional, Tuple
from loguru import logger

from Util.ImageRecognition import click_at, double_click_at, get_window_rect_by_title

# 导入游戏输入执行器
try:
    from Util.GameInputExecutor import get_input_executor
    HAS_GAME_INPUT = True
except ImportError:
    HAS_GAME_INPUT = False
    get_input_executor = None


class ActionExecutor:
    """动作执行器"""
    
    def __init__(self, window_title: Optional[str] = None):
        self.window_title = window_title
        
        # 虚拟键码映射
        self._vk_map = {
            '0': 0x30,
            '1': 0x31,
            '2': 0x32,
            '3': 0x33,
            '4': 0x34,
            '5': 0x35,
            '6': 0x36,
            '7': 0x37,
            '8': 0x38,
            '9': 0x39,
            'a': 0x41,
            'b': 0x42,
            'c': 0x43,
            'd': 0x44,
            'e': 0x45,
            'f': 0x46,
            'g': 0x47,
            'h': 0x48,
            'i': 0x49,
            'j': 0x4A,
            'k': 0x4B,
            'l': 0x4C,
            'm': 0x4D,
            'n': 0x4E,
            'o': 0x4F,
            'p': 0x50,
            'q': 0x51,
            'r': 0x52,
            's': 0x53,
            't': 0x54,
            'u': 0x55,
            'v': 0x56,
            'w': 0x57,
            'x': 0x58,
            'y': 0x59,
            'z': 0x5A,
            'f1': 0x70,
            'f2': 0x71,
            'f3': 0x72,
            'f4': 0x73,
            'f5': 0x74,
            'f6': 0x75,
            'f7': 0x76,
            'f8': 0x77,
            'f9': 0x78,
            'f10': 0x79,
            'f11': 0x7A,
            'f12': 0x7B,
            'space': 0x20,
            'enter': 0x0D,
            'backspace': 0x08,
            'tab': 0x09,
            'escape': 0x1B,
            'shift': 0x10,
            'ctrl': 0x11,
            'control': 0x11,
            'alt': 0x12,
        }
    
    def _random_delay(self, min_delay: float = 0.3, max_delay: float = 1.0):
        """
        随机延时（0.3-1秒）
        
        :param min_delay: 最小延时（秒）
        :param max_delay: 最大延时（秒）
        """
        delay = random.uniform(min_delay, max_delay)
        logger.debug('Random delay: {:.3f}s', delay)
        time.sleep(delay)
    
    def _get_vk_code(self, key: str) -> Optional[int]:
        """获取按键的虚拟键码"""
        key_lower = key.lower()
        if key_lower in self._vk_map:
            return self._vk_map[key_lower]
        # 尝试直接转换为整数
        try:
            return int(key)
        except:
            return None
    
    def click_at(self, x, y, button: str = 'left', coordinate_type: str = 'relative_to_window') -> bool:
        """
        在指定位置点击
        
        :param x: X坐标（可以是像素值或相对坐标 0-1）
        :param y: Y坐标（可以是像素值或相对坐标 0-1）
        :param button: 鼠标按钮 ('left', 'right', 'middle')
        :param coordinate_type: 坐标类型
            - 'relative_to_window': 相对于窗口的相对坐标 (0-1)
            - 'absolute_to_window': 相对于窗口的绝对像素坐标
            - 'absolute_to_screen': 屏幕绝对坐标
        :return: 是否成功
        """
        try:
            # 移除自动随机延迟，使用脚本中定义的等待步骤
            # self._random_delay()
            
            if HAS_GAME_INPUT and self.window_title:
                executor = get_input_executor(self.window_title)
                
                # 判断是否是相对坐标（0-1 之间的小数）
                is_relative = coordinate_type == 'relative_to_window' or (isinstance(x, float) and 0 <= x <= 1 and isinstance(y, float) and 0 <= y <= 1)
                
                if is_relative:
                    # 相对坐标，直接传递
                    logger.debug('使用相对坐标点击：({}, {})', x, y)
                    executor.click(x, y, button=button, is_relative=True)
                else:
                    # 绝对像素坐标，需要转换为相对坐标
                    window_rect = get_window_rect_by_title(self.window_title)
                    if window_rect:
                        win_width, win_height = window_rect[2], window_rect[3]
                        rel_x = x / win_width
                        rel_y = y / win_height
                        logger.debug('坐标转换：像素 ({}, {}) → 相对 ({:.3f}, {:.3f})', x, y, rel_x, rel_y)
                        executor.click(rel_x, rel_y, button=button, is_relative=True)
                    else:
                        logger.warning('找不到窗口，使用像素坐标 ({}, {})', x, y)
                        executor.click(x, y, button=button, is_relative=False)
            else:
                # 回退到旧实现
                click_at(x, y, button, window_title=self.window_title)
            
            logger.debug('Clicked at ({}, {}) with {} button (coordinate_type: {})', x, y, button, coordinate_type)
            return True
        except Exception as e:
            logger.warning('Click failed at ({}, {}): {}', x, y, e)
            return False
    
    def double_click_at(self, x, y, button: str = 'left', coordinate_type: str = 'relative_to_window') -> bool:
        """
        在指定位置双击
        
        :param x: X坐标（可以是像素值或相对坐标 0-1）
        :param y: Y坐标（可以是像素值或相对坐标 0-1）
        :param button: 鼠标按钮 ('left', 'right', 'middle')
        :param coordinate_type: 坐标类型
            - 'relative_to_window': 相对于窗口的相对坐标 (0-1)
            - 'absolute_to_window': 相对于窗口的绝对像素坐标
            - 'absolute_to_screen': 屏幕绝对坐标
        :return: 是否成功
        """
        try:
            # 移除自动随机延迟，使用脚本中定义的等待步骤
            # self._random_delay()
            
            if HAS_GAME_INPUT and self.window_title:
                executor = get_input_executor(self.window_title)
                
                # 判断是否是相对坐标（0-1 之间的小数）
                is_relative = coordinate_type == 'relative_to_window' or (isinstance(x, float) and 0 <= x <= 1 and isinstance(y, float) and 0 <= y <= 1)
                
                if is_relative:
                    # 相对坐标，直接传递
                    logger.debug('使用相对坐标双击：({}, {})', x, y)
                    executor.click(x, y, button=button, is_relative=True)
                    time.sleep(0.15)
                    executor.click(x, y, button=button, is_relative=True)
                else:
                    # 绝对像素坐标，需要转换为相对坐标
                    window_rect = get_window_rect_by_title(self.window_title)
                    if window_rect:
                        win_width, win_height = window_rect[2], window_rect[3]
                        rel_x = x / win_width
                        rel_y = y / win_height
                        logger.debug('坐标转换：像素 ({}, {}) → 相对 ({:.3f}, {:.3f})', x, y, rel_x, rel_y)
                        executor.click(rel_x, rel_y, button=button, is_relative=True)
                        time.sleep(0.15)
                        executor.click(rel_x, rel_y, button=button, is_relative=True)
                    else:
                        logger.warning('找不到窗口，使用像素坐标 ({}, {})', x, y)
                        executor.click(x, y, button=button, is_relative=False)
                        time.sleep(0.15)
                        executor.click(x, y, button=button, is_relative=False)
            else:
                # 回退到旧实现
                double_click_at(x, y, button, window_title=self.window_title)
            
            logger.debug('Double clicked at ({}, {}) with {} button (coordinate_type: {})', x, y, button, coordinate_type)
            return True
        except Exception as e:
            logger.warning('Double click failed at ({}, {}): {}', x, y, e)
            return False
    
    def move_mouse_to(self, x, y, coordinate_type: str = 'relative_to_window') -> bool:
        """
        移动鼠标到指定位置
        
        :param x: X坐标（可以是像素值或相对坐标 0-1）
        :param y: Y坐标（可以是像素值或相对坐标 0-1）
        :param coordinate_type: 坐标类型
            - 'relative_to_window': 相对于窗口的相对坐标 (0-1)
            - 'absolute_to_window': 相对于窗口的绝对像素坐标
            - 'absolute_to_screen': 屏幕绝对坐标
        :return: 是否成功
        """
        try:
            # 鼠标移动不需要额外的随机延迟，脚本中已经有了延迟
            # self._random_delay()
            
            if HAS_GAME_INPUT and self.window_title:
                executor = get_input_executor(self.window_title)
                
                # 判断是否是相对坐标（0-1 之间的小数）
                is_relative = coordinate_type == 'relative_to_window' or (isinstance(x, float) and 0 <= x <= 1 and isinstance(y, float) and 0 <= y <= 1)
                
                executor.move_to(x, y, is_relative=is_relative)
                # 减少日志输出，避免过多干扰
                # logger.debug('Moved mouse to ({}, {}) [coordinate_type: {}]', x, y, coordinate_type)
                return True
            
            # 回退到旧的实现
            import win32api
            # 转换为屏幕绝对坐标
            screen_x, screen_y = x, y
            if self.window_title:
                from Util.ImageRecognition import get_window_rect_by_title
                window_rect = get_window_rect_by_title(self.window_title)
                if window_rect:
                    win_left, win_top, _, _ = window_rect
                    screen_x = win_left + x
                    screen_y = win_top + y
                    logger.debug('Converted window coords ({}, {}) to screen ({}, {})', x, y, screen_x, screen_y)
            win32api.SetCursorPos([screen_x, screen_y])
            logger.debug('Moved mouse to ({}, {})', x, y)
            return True
        except Exception as e:
            logger.warning('Mouse move failed to ({}, {}): {}', x, y, e)
            return False
    
    def drag(self, start_x, start_y, end_x, end_y, duration: float = 0.5, 
             button: str = 'left', steps: int = 20, 
             coordinate_type: str = 'relative_to_window') -> bool:
        """
        鼠标拖拽/滑动操作
        
        :param start_x: 起始X坐标
        :param start_y: 起始Y坐标
        :param end_x: 结束X坐标
        :param end_y: 结束Y坐标
        :param duration: 滑动持续时间（秒）
        :param button: 鼠标按钮 ('left', 'right', 'middle')
        :param steps: 滑动步数（步数越多轨迹越平滑）
        :param coordinate_type: 坐标类型
        :return: 是否成功
        """
        try:
            import win32api
            import win32con
            
            # 转换坐标
            def convert_coord(x, y):
                if coordinate_type == 'relative_to_window' and self.window_title:
                    window_rect = get_window_rect_by_title(self.window_title)
                    if window_rect:
                        win_left, win_top, win_width, win_height = window_rect
                        screen_x = win_left + int(x)
                        screen_y = win_top + int(y)
                        return screen_x, screen_y
                return int(x), int(y)
            
            # 转换起始和结束坐标
            start_screen_x, start_screen_y = convert_coord(start_x, start_y)
            end_screen_x, end_screen_y = convert_coord(end_x, end_y)
            
            logger.debug('拖拽: ({}, {}) -> ({}, {}), 持续{}秒, {}步', 
                        start_screen_x, start_screen_y, end_screen_x, end_screen_y, duration, steps)
            
            # 移动鼠标到起始位置
            win32api.SetCursorPos([start_screen_x, start_screen_y])
            time.sleep(0.1)
            
            # 按下鼠标按钮
            if button == 'left':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif button == 'right':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            elif button == 'middle':
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            
            time.sleep(0.05)
            
            # 平滑移动鼠标
            step_delay = duration / steps
            for i in range(1, steps + 1):
                t = i / steps
                # 线性插值
                current_x = int(start_screen_x + (end_screen_x - start_screen_x) * t)
                current_y = int(start_screen_y + (end_screen_y - start_screen_y) * t)
                win32api.SetCursorPos([current_x, current_y])
                time.sleep(step_delay)
            
            # 释放鼠标按钮
            if button == 'left':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif button == 'right':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif button == 'middle':
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            
            logger.debug('拖拽完成')
            return True
            
        except Exception as e:
            logger.warning('拖拽失败: {}', e)
            return False
    
    def scroll(self, x: int, y: int, scroll_amount: int = -3, scroll_times: int = 1,
               coordinate_type: str = 'relative_to_window') -> bool:
        """
        鼠标滚轮滚动操作
        
        :param x: 鼠标X坐标（滚动前移动到的位置）
        :param y: 鼠标Y坐标（滚动前移动到的位置）
        :param scroll_amount: 滚动量，正数向上滚动，负数向下滚动
        :param scroll_times: 滚动次数
        :param coordinate_type: 坐标类型
        :return: 是否成功
        """
        try:
            import win32api
            import win32con
            
            # 转换坐标
            if coordinate_type == 'relative_to_window' and self.window_title:
                window_rect = get_window_rect_by_title(self.window_title)
                if window_rect:
                    win_left, win_top, win_width, win_height = window_rect
                    screen_x = win_left + int(x)
                    screen_y = win_top + int(y)
                else:
                    screen_x, screen_y = int(x), int(y)
            else:
                screen_x, screen_y = int(x), int(y)
            
            logger.debug('滚轮滚动: 位置({}, {}), 滚动量{}, 次数{}', 
                        screen_x, screen_y, scroll_amount, scroll_times)
            
            # 移动鼠标到指定位置
            win32api.SetCursorPos([screen_x, screen_y])
            time.sleep(0.1)
            
            # 执行滚动
            for _ in range(scroll_times):
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, int(scroll_amount * 120), 0)
                time.sleep(0.1)
            
            logger.debug('滚轮滚动完成')
            return True
            
        except Exception as e:
            logger.warning('滚轮滚动失败: {}', e)
            return False
    
    def press_key(self, key: str) -> bool:
        """
        按下并释放键盘按键（完整的按键动作）
        
        :param key: 按键名称
        :return: 是否成功
        """
        try:
            self._random_delay()
            if HAS_GAME_INPUT:
                executor = get_input_executor(self.window_title)
                vk = self._get_vk_code(key)
                if vk is None:
                    logger.warning('Unknown key: {}', key)
                    return False
                executor.key_press(vk)
                logger.debug('Pressed and released key: {} (vk: {})', key, vk)
                return True
            
            # 回退到旧的实现
            import win32api
            import win32con
            vk = self._get_vk_code(key)
            if vk is None:
                logger.warning('Unknown key: {}', key)
                return False
            
            scan_code = win32api.MapVirtualKey(vk, 0)
            # 按下按键
            win32api.keybd_event(vk, scan_code, 0, 0)
            time.sleep(0.1)
            # 释放按键
            win32api.keybd_event(vk, scan_code, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)
            logger.debug('Pressed and released key: {} (vk: {})', key, vk)
            return True
        except Exception as e:
            logger.warning('Key press failed for {}: {}', key, e)
            return False
    
    def release_key(self, key: str) -> bool:
        """
        释放键盘按键（单独释放，不常用）
        
        :param key: 按键名称
        :return: 是否成功
        """
        try:
            if HAS_GAME_INPUT:
                executor = get_input_executor(self.window_title)
                vk = self._get_vk_code(key)
                if vk is None:
                    logger.warning('Unknown key: {}', key)
                    return False
                executor.key_up(vk)
                logger.debug('Released key: {} (vk: {})', key, vk)
                return True
            
            # 回退到旧的实现
            import win32api
            import win32con
            vk = self._get_vk_code(key)
            if vk is None:
                logger.warning('Unknown key: {}', key)
                return False
            
            scan_code = win32api.MapVirtualKey(vk, 0)
            win32api.keybd_event(vk, scan_code, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            logger.debug('Released key: {} (vk: {})', key, vk)
            return True
        except Exception as e:
            logger.warning('Key release failed for {}: {}', key, e)
            return False
