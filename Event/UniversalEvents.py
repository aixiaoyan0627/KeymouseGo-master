import re

# import pyperclip
import pyautogui
from Event.Event import Event
from loguru import logger

SW, SH = pyautogui.size()

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


class UniversalEvent(Event):
    # 改变坐标
    # pos 为包含横纵坐标的元组
    # 值为int型:绝对坐标
    # 值为float型:相对坐标
    def changepos(self, pos: tuple):
        if self.event_type == 'EM':
            x, y = pos
            if isinstance(x, int):
                self.action[0] = x
            else:
                self.action[0] = int(x * SW)
            if isinstance(y, int):
                self.action[1] = y
            else:
                self.action[1] = int(y * SH)

    def execute(self, thd=None):
        self.sleep(thd)

        if self.event_type == 'EM':
            x, y = self.action
            
            # 检查是否是相对于游戏窗口的坐标
            is_relative_to_window = False
            rel_x, rel_y = 0, 0
            if len(self.action) >= 3 and self.action[2] == 'relative_to_window':
                is_relative_to_window = True
                rel_x, rel_y = x, y
            
            if self.action == [-1, -1]:
                # 约定 [-1, -1] 表示鼠标保持原位置不动
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
                            pyautogui.moveTo(screen_x, screen_y)
                        else:
                            # 找不到游戏窗口，使用屏幕比例坐标
                            if not isinstance(x, int):
                                x = int(x * SW)
                            if not isinstance(y, int):
                                y = int(y * SH)
                            pyautogui.moveTo(x, y)
                    except Exception:
                        # 换算失败，使用屏幕比例坐标
                        if not isinstance(x, int):
                            x = int(x * SW)
                        if not isinstance(y, int):
                            y = int(y * SH)
                        pyautogui.moveTo(x, y)
                else:
                    # 兼容旧版的绝对坐标
                    if not isinstance(x, int) and not isinstance(y, int):
                        x = float(re.match('([0-1].[0-9]+)%', x).group(1))
                        y = float(re.match('([0-1].[0-9]+)%', y).group(1))

                    if not isinstance(x, int):
                        x = int(x * SW)
                    if not isinstance(y, int):
                        y = int(y * SH)
                    pyautogui.moveTo(x, y)

            if self.action_type == 'mouse left down':
                pyautogui.mouseDown(button='left')
            elif self.action_type == 'mouse left up':
                pyautogui.mouseUp(button='left')
            elif self.action_type == 'mouse right down':
                pyautogui.mouseDown(button='right')
            elif self.action_type == 'mouse right up':
                pyautogui.mouseUp(button='right')
            elif self.action_type == 'mouse middle down':
                pyautogui.mouseDown(button='middle')
            elif self.action_type == 'mouse middle up':
                pyautogui.mouseUp(button='middle')
            elif self.action_type == 'mouse wheel up':
                pyautogui.scroll(1)
            elif self.action_type == 'mouse wheel down':
                pyautogui.scroll(-1)
            elif self.action_type == 'mouse move':
                pass
            else:
                logger.warning('Unknown mouse event:%s' % self.action_type)

        elif self.event_type == 'EK':
            key_code, key_name, extended = self.action

            if self.action_type == 'key down':
                pyautogui.keyDown(key_name)
            elif self.action_type == 'key up':
                pyautogui.keyUp(key_name)
            else:
                logger.warning('Unknown keyboard event:', self.action_type)

        elif self.event_type == 'EX':
            if self.action_type == 'input':
                text = self.action
                # pyperclip.copy(text)

                pyautogui.write(text)
                # Ctrl+V
                # keyboardctl.press('ctrl')
                # keyboardctl.press('v')
                # keyboardctl.release('v')
                # keyboardctl.release('ctrl')
            else:
                logger.warning('Unknown extra event:%s' % self.action_type)
