import re
import pyperclip
import win32api

from Event.Event import Event
from loguru import logger

import ctypes
import win32con
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
numofmonitors = user32.GetSystemMetrics(win32con.SM_CMONITORS)
# 主屏分辨率
SW, SH = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

# 导入获取游戏窗口位置的函数
try:
    from Util.ImageRecognition import get_window_rect_by_title
    HAS_WINDOW_RECT = True
except ImportError:
    HAS_WINDOW_RECT = False
    get_window_rect_by_title = None

# 游戏窗口标题（用于执行时换算坐标）
_game_window_title = '大航海时代：传说'
# 是否使用游戏窗口相对坐标模式
_use_relative_coords = True

def set_game_window_title(title):
    """设置游戏窗口标题"""
    global _game_window_title
    _game_window_title = title

def set_use_relative_coords(use_relative):
    """设置是否使用游戏窗口相对坐标模式"""
    global _use_relative_coords
    _use_relative_coords = use_relative


class WindowsEvent(Event):
    # 改变坐标
    # pos 为包含横纵坐标的元组
    # 值为int型:绝对坐标
    # 值为float型:相对坐标
    def changepos(self, pos: tuple):
        if self.event_type == 'EM':
            x, y = pos
            if isinstance(x, int):
                self.action[0] = int(x * 65535 / SW)
            else:
                self.action[0] = int(x * 65535)
            if isinstance(y, int):
                self.action[1] = int(y * 65535 / SH)
            else:
                self.action[1] = int(y * 65535)

    # 执行操作
    def execute(self, thd=None):
        self.sleep(thd)

        if self.event_type == 'EM':
            try:
                # 处理包含 'relative_to_window' 的情况
                is_relative_to_window = False
                rel_x, rel_y = 0, 0
                if len(self.action) == 3 and self.action[2] == 'relative_to_window':
                    x, y = self.action[0], self.action[1]
                    is_relative_to_window = True
                    rel_x, rel_y = x, y
                else:
                    x, y = self.action
            except (ValueError, TypeError) as e:
                logger.warning('Invalid action for EM event: {}, expected 2 values, got: {}', self.action_type, self.action)
                return
            
            # 约定 [-1, -1] 表示鼠标保持原位置不动
            if (len(self.action) == 2 and self.action == [-1, -1]) or \
               (len(self.action) == 3 and self.action[0] == -1 and self.action[1] == -1):
                pass
            else:
                if is_relative_to_window and _use_relative_coords and HAS_WINDOW_RECT and _game_window_title:
                    # 相对于游戏窗口的坐标，需要换算
                    try:
                        window_rect = get_window_rect_by_title(_game_window_title)
                        if window_rect:
                            win_left, win_top, win_width, win_height = window_rect
                            # 根据游戏窗口当前位置换算屏幕坐标
                            screen_x = win_left + int(rel_x * win_width)
                            screen_y = win_top + int(rel_y * win_height)
                            # 更好的兼容 win10 屏幕缩放问题
                            if numofmonitors > 1:
                                win32api.SetCursorPos([screen_x, screen_y])
                            else:
                                nx = int(screen_x * 65535 / SW)
                                ny = int(screen_y * 65535 / SH)
                                win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                        else:
                            # 找不到游戏窗口，使用屏幕比例坐标
                            # 兼容旧版的绝对坐标
                            if not isinstance(x, int) and not isinstance(y, int):
                                try:
                                    if isinstance(x, str):
                                        x = float(re.match('([0-1].[0-9]+)%', x).group(1))
                                    if isinstance(y, str):
                                        y = float(re.match('([0-1].[0-9]+)%', y).group(1))
                                except (AttributeError, ValueError) as e:
                                    logger.warning('Failed to parse relative coordinates: {}, {}', x, y)
                                    return
                            
                            # 更好的兼容 win10 屏幕缩放问题
                            if isinstance(x, int) and isinstance(y, int):
                                if numofmonitors > 1:
                                    win32api.SetCursorPos([x, y])
                                else:
                                    nx = int(x * 65535 / SW)
                                    ny = int(y * 65535 / SH)
                                    win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                            else:
                                nx = int(x * 65535)
                                ny = int(y * 65535)
                                win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                    except Exception as e:
                        logger.warning('Error converting relative window coordinates: {}', e)
                        # 换算失败，使用屏幕比例坐标
                        # 兼容旧版的绝对坐标
                        if not isinstance(x, int) and not isinstance(y, int):
                            try:
                                if isinstance(x, str):
                                    x = float(re.match('([0-1].[0-9]+)%', x).group(1))
                                if isinstance(y, str):
                                    y = float(re.match('([0-1].[0-9]+)%', y).group(1))
                            except (AttributeError, ValueError) as e:
                                logger.warning('Failed to parse relative coordinates: {}, {}', x, y)
                                return
                        
                        # 更好的兼容 win10 屏幕缩放问题
                        if isinstance(x, int) and isinstance(y, int):
                            if numofmonitors > 1:
                                win32api.SetCursorPos([x, y])
                            else:
                                nx = int(x * 65535 / SW)
                                ny = int(y * 65535 / SH)
                                win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                        else:
                            nx = int(x * 65535)
                            ny = int(y * 65535)
                            win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                else:
                    # 兼容旧版的绝对坐标
                    if not isinstance(x, int) and not isinstance(y, int):
                        try:
                            if isinstance(x, str):
                                x = float(re.match('([0-1].[0-9]+)%', x).group(1))
                            if isinstance(y, str):
                                y = float(re.match('([0-1].[0-9]+)%', y).group(1))
                        except (AttributeError, ValueError) as e:
                            logger.warning('Failed to parse relative coordinates: {}, {}', x, y)
                            return
                    
                    # 更好的兼容 win10 屏幕缩放问题
                    if isinstance(x, int) and isinstance(y, int):
                        if numofmonitors > 1:
                            win32api.SetCursorPos([x, y])
                        else:
                            nx = int(x * 65535 / SW)
                            ny = int(y * 65535 / SH)
                            win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)
                    else:
                        nx = int(x * 65535)
                        ny = int(y * 65535)
                        win32api.mouse_event(win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE, nx, ny, 0, 0)

            if self.action_type == 'mouse left down':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif self.action_type == 'mouse left up':
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif self.action_type == 'mouse right down':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            elif self.action_type == 'mouse right up':
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif self.action_type == 'mouse middle down':
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            elif self.action_type == 'mouse middle up':
                win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            elif self.action_type == 'mouse wheel up':
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, win32con.WHEEL_DELTA, 0)
            elif self.action_type == 'mouse wheel down':
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -win32con.WHEEL_DELTA, 0)
            elif self.action_type == 'mouse move':
                pass
            else:
                logger.warning('Unknown mouse event:%s' % self.action_type)

        elif self.event_type == 'EK':
            try:
                key_code, key_name, extended = self.action
            except (ValueError, TypeError) as e:
                logger.warning('Invalid action for EK event, expected 3 values, got: {}', self.action)
                return

            # shift ctrl alt
            # if key_code >= 160 and key_code <= 165:
            #     key_code = int(key_code/2) - 64

            # 不执行热键
            # if key_name in HOT_KEYS:
            #     return

            base = 0
            if extended:
                base = win32con.KEYEVENTF_EXTENDEDKEY

            if self.action_type == 'key down':
                win32api.keybd_event(key_code, 0, base, 0)
            elif self.action_type == 'key up':
                win32api.keybd_event(key_code, 0, base | win32con.KEYEVENTF_KEYUP, 0)
            else:
                logger.warning('Unknown keyboard event:', self.action_type)

        elif self.event_type == 'EX':

            if self.action_type == 'input':
                text = self.action
                pyperclip.copy(text)
                # Ctrl+V
                win32api.keybd_event(162, 0, 0, 0)  # ctrl
                win32api.keybd_event(86, 0, 0, 0)  # v
                win32api.keybd_event(86, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(162, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                logger.warning('Unknown extra event:%s' % self.action_type)
