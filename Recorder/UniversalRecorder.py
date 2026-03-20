import re

# 修复 pynput 与 shiboken/six 的冲突 - 在导入任何模块之前执行
try:
    # 禁用 shiboken 的 feature 检查
    import shibokensupport
    if hasattr(shibokensupport, 'feature'):
        original_feature_imported = shibokensupport.feature.feature_imported
        shibokensupport.feature.feature_imported = lambda *args, **kwargs: None
except ImportError:
    pass

try:
    # 确保 six 正确加载
    import six
except ImportError:
    pass

from pynput import mouse, keyboard
from Event import ScreenWidth as SW, ScreenHeight as SH
import Recorder.globals as globalv

# 导入获取游戏窗口位置的函数
try:
    from Util.ImageRecognition import get_window_rect_by_title
    HAS_WINDOW_RECT = True
except ImportError:
    HAS_WINDOW_RECT = False
    get_window_rect_by_title = None

record_signals = globalv.RecordSignal()

buttondic = {mouse.Button.left: 'left',
             mouse.Button.right: 'right',
             mouse.Button.middle: 'middle'
             }

# some keyname recorded by pynput is not supported in pyautogui
renamedic = {'cmd': 'win', 'shift_r': 'shiftright', 'alt_r': 'altright', 'ctrl_r': 'ctrlright',
             'caps_lock': 'capslock', 'num_lock': 'numlock',
             'page_up': 'pageup', 'page_down': 'pagedown', 'print_screen': 'printscreen'}

# 游戏窗口标题（用于录制相对坐标）
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


def get_delay(action_type):
    delay = globalv.current_ts() - globalv.latest_time

    # 录制鼠标轨迹的精度，数值越小越精准，但同时可能产生大量的冗余
    mouse_move_interval_ms = globalv.mouse_interval_ms or 999999

    if action_type == 'mouse move' and delay < mouse_move_interval_ms:
        return -1

    if globalv.latest_time < 0:
        delay = 0
    globalv.latest_time = globalv.current_ts()
    return delay


def get_mouse_event(x, y, action_type):
    # 检查是否使用相对坐标模式
    if _use_relative_coords and HAS_WINDOW_RECT and _game_window_title:
        try:
            window_rect = get_window_rect_by_title(_game_window_title)
            if window_rect:
                win_left, win_top, win_width, win_height = window_rect
                # 计算相对于游戏窗口的坐标比例
                rel_x = (x - win_left) / win_width
                rel_y = (y - win_top) / win_height
                # 确保坐标在游戏窗口范围内
                if 0 <= rel_x <= 1 and 0 <= rel_y <= 1:
                    # 保存为相对于游戏窗口的比例坐标
                    tpos = (rel_x, rel_y, 'relative_to_window')
                else:
                    # 鼠标在窗口外，使用屏幕比例坐标
                    tpos = (x / SW, y / SH)
            else:
                # 找不到游戏窗口，使用屏幕比例坐标
                tpos = (x / SW, y / SH)
        except Exception as e:
            # 获取窗口失败，使用屏幕比例坐标
            tpos = (x / SW, y / SH)
    else:
        # 不使用相对坐标模式，使用原有的屏幕比例坐标
        tpos = (x / SW, y / SH)
    
    delay = get_delay(action_type)
    if delay < 0:
        return None
    else:
        return globalv.ScriptEvent({
            'delay': delay,
            'event_type': 'EM',
            'action_type': action_type,
            'action': tpos
        })


def on_move(x, y):
    event = get_mouse_event(x, y, 'mouse move')
    if event:
        try:
            record_signals.event_signal.emit(event)
            record_signals.cursor_pos_change.emit((x, y))
        except RuntimeError:
            pass


def on_click(x, y, button, pressed):
    action_type = 'mouse {0} {1}'.format(buttondic[button],
                                     'down' if pressed else 'up')
    event = get_mouse_event(x, y, action_type)
    if event:
        try:
            record_signals.event_signal.emit(event)
        except RuntimeError:
            pass


def on_scroll(x, y, dx, dy):
    action_type = 'mouse wheel {0}'.format('down' if dy < 0 else 'up')
    event = get_mouse_event(x, y, action_type)
    if event:
        try:
            record_signals.event_signal.emit(event)
        except RuntimeError:
            pass


def get_keyboard_event(key, action_type):
    #TODO: maybe can helo https://blog.csdn.net/haiyangdaozhang/article/details/109158793
    delay = get_delay(action_type)
    if delay < 0:
        return None
    else:
        try:
            keycode = key.value.vk
            keyname = renamedic.get(key.name, key.name)
        except AttributeError:
            keycode = key.vk
            keyname = key.char
        if keyname is None:
            return None
        if re.match('^([0-9])$', keyname) and keycode is None:
            keyname = 'num{}'.format(keyname)
        event = globalv.ScriptEvent({
            'delay': delay,
            'event_type': 'EK',
            'action_type': action_type,
            'action': (keycode, keyname, 0)
        })
        return event


def on_press(key):
    event = get_keyboard_event(key, 'key down')
    if event:
        try:
            record_signals.event_signal.emit(event)
        except RuntimeError:
            pass


def on_release(key):
    event = get_keyboard_event(key, 'key up')
    if event:
        try:
            record_signals.event_signal.emit(event)
        except RuntimeError:
            pass


def setuphook(commandline=False):
    if not commandline:
        mouselistener = mouse.Listener(
            on_move=on_move,
            on_scroll=on_scroll,
            on_click=on_click
        )
        mouselistener.start()
    keyboardlistener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )
    keyboardlistener.start()
