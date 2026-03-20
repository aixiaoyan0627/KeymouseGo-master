# -*- encoding:utf-8 -*-
"""
游戏输入执行器：使用Windows原生SendInput API，更稳定的游戏兼容性
支持：
- 坐标转换（屏幕 → 游戏窗口相对坐标）
- DPI缩放适配
- 游戏窗口绑定
- 窗口激活检测（输入前自动激活窗口）
- SendInput API（比mouse_event/keybd_event更稳定）
"""
import ctypes
import ctypes.wintypes
import time
from typing import Optional, Tuple
from loguru import logger

# Windows API 常量
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

SM_CXSCREEN = 0
SM_CYSCREEN = 1

SW_RESTORE = 9
SW_SHOW = 5
SW_SHOWNORMAL = 1


# Windows API 结构定义
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD)
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _anonymous_ = ("ui",)
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("ui", INPUT_UNION)
    ]

# 加载Windows API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 设置进程DPI感知
try:
    user32.SetProcessDPIAware()
except:
    pass

# 获取屏幕分辨率
screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
screen_height = user32.GetSystemMetrics(SM_CYSCREEN)

# 延迟导入 get_window_rect_by_title（避免循环导入）
HAS_WINDOW_RECT = True  # 假设可以导入，在 _get_game_window_rect 中实际导入


def _get_window_handle_by_title(window_title: str) -> Optional[int]:
    """通过窗口标题获取窗口句柄"""
    def callback(hwnd):
        try:
            # 检查窗口句柄是否有效
            if not ctypes.wintypes.HWND(hwnd):
                return True
            
            try:
                title_length = user32.GetWindowTextLengthW(hwnd)
                if title_length <= 0:
                    return True
            except Exception:
                # GetWindowTextLengthW 失败，跳过此窗口
                return True
            
            try:
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                title = title_buffer.value
                if not title:
                    return True
            except Exception:
                # GetWindowTextW 失败，跳过此窗口
                return True
            
            # 检查标题是否匹配
            if window_title not in title:
                return True
            
            # 匹配成功
            _window_handles.append(hwnd)
            
        except ValueError as e:
            # PyObject is NULL 或其他窗口句柄无效错误
            if "NULL" in str(e) or "hwnd" in str(e).lower():
                # 窗口句柄无效，跳过
                return True
            # 其他 ValueError，重新抛出
            raise
        except Exception:
            # 忽略其他异常，继续枚举
            pass
        
        return True
    
    _window_handles = []
    try:
        # 正确的回调类型：只接受一个 HWND 参数
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND)
        user32.EnumWindows(WNDENUMPROC(callback), None)
    except Exception as e:
        logger.warning(f'枚举窗口失败：{e}')
    
    return _window_handles[0] if _window_handles else None


def _is_window_foreground(hwnd: int) -> bool:
    """检查窗口是否在前台"""
    foreground_hwnd = user32.GetForegroundWindow()
    return hwnd == foreground_hwnd


def _activate_window(hwnd: int, wait_ms: int = 100, retry_count: int = 3) -> bool:
    """
    激活窗口
    
    参数:
        hwnd: 窗口句柄
        wait_ms: 每次尝试后等待的毫秒数
        retry_count: 重试次数
    
    返回:
        是否成功激活
    """
    for i in range(retry_count):
        try:
            # 先还原窗口（如果是最小化的）
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            
            # 激活窗口
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            
            # 等待一下并检查是否真的在前台
            time.sleep(wait_ms / 1000.0)
            if _is_window_foreground(hwnd):
                if i > 0:
                    logger.debug(f'窗口激活成功（尝试 {i + 1} 次）')
                return True
            else:
                logger.warning(f'窗口激活尝试 {i + 1} 次后仍未在前台')
        except Exception as e:
            logger.warning(f'窗口激活失败（尝试 {i + 1} 次）: {e}')
    
    return False



class GameInputExecutor:
    """
    游戏输入执行器
    
    特点：
    - 使用SendInput API（更稳定，不易被游戏拦截）
    - 自动坐标转换（支持屏幕→游戏窗口相对坐标）
    - DPI缩放适配
    - 游戏窗口绑定
    - 窗口激活检测（输入前自动激活窗口）
    """
    
    def __init__(self, window_title: Optional[str] = None, auto_activate_window: bool = True):
        """
        初始化游戏输入执行器
        
        参数:
            window_title: 游戏窗口标题，如果提供则启用相对坐标模式
            auto_activate_window: 是否自动激活游戏窗口（默认True）
        """
        self.window_title = window_title
        self.auto_activate_window = auto_activate_window
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._dpi_scale = self._get_dpi_scale()
        
        logger.debug(f'GameInputExecutor 初始化: 窗口标题={window_title}, 自动激活窗口={auto_activate_window}, DPI缩放={self._dpi_scale}')
    
    def _ensure_window_active(self) -> bool:
        """
        确保游戏窗口在前台
        
        返回:
            是否成功激活窗口（如果没有绑定窗口则返回True）
        """
        if not self.window_title or not self.auto_activate_window:
            return True
        
        hwnd = _get_window_handle_by_title(self.window_title)
        if not hwnd:
            logger.warning(f'找不到窗口: {self.window_title}')
            return False
        
        if _is_window_foreground(hwnd):
            return True
        
        logger.debug(f'窗口不在前台，正在激活: {self.window_title}')
        return _activate_window(hwnd)
    
    def _get_dpi_scale(self) -> float:
        """获取系统DPI缩放比例"""
        try:
            hdc = user32.GetDC(0)
            if hdc:
                dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                user32.ReleaseDC(0, hdc)
                return dpi_x / 96.0
        except Exception as e:
            logger.warning(f'获取DPI缩放失败: {e}')
        return 1.0
    
    def _get_game_window_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """获取游戏窗口位置"""
        if not self.window_title or not HAS_WINDOW_RECT:
            logger.debug(f'_get_game_window_rect: window_title={self.window_title}, HAS_WINDOW_RECT={HAS_WINDOW_RECT}')
            return None
        
        # 延迟导入（避免循环导入）
        try:
            from Util.ImageRecognition import get_window_rect_by_title
            rect = get_window_rect_by_title(self.window_title)
            logger.debug(f'_get_game_window_rect: 窗口="{self.window_title}", 返回值={rect}')
            return rect
        except ImportError as e:
            logger.warning(f'导入 get_window_rect_by_title 失败：{e}')
            return None
        except Exception as e:
            logger.warning(f'获取游戏窗口位置失败：{e}')
            return None
    
    def screen_to_game(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        屏幕坐标 → 游戏窗口内坐标
        
        参数:
            screen_x, screen_y: 屏幕绝对坐标
        
        返回:
            (game_x, game_y): 游戏窗口内坐标
        """
        window_rect = self._get_game_window_rect()
        if window_rect:
            win_left, win_top, _, _ = window_rect
            game_x = int((screen_x - win_left) / self._dpi_scale)
            game_y = int((screen_y - win_top) / self._dpi_scale)
            return game_x, game_y
        return screen_x, screen_y
    
    def game_to_screen(self, game_x: int, game_y: int) -> Tuple[int, int]:
        """
        游戏窗口内坐标 → 屏幕坐标
        
        参数:
            game_x, game_y: 游戏窗口内坐标（绝对像素或相对坐标 0-1）
        
        返回:
            (screen_x, screen_y): 屏幕绝对坐标
        
        注意:
            - 如果坐标在 0-1 之间，视为相对坐标（窗口比例）
            - 如果坐标>1，视为绝对像素坐标
            - 如果找不到窗口且使用相对坐标，会抛出异常
        """
        window_rect = self._get_game_window_rect()
        if window_rect:
            win_left, win_top, win_width, win_height = window_rect
            
            # 检查是否是相对坐标（0-1 之间）
            if 0 <= game_x <= 1 and 0 <= game_y <= 1:
                # 相对坐标：按窗口比例计算
                screen_x = win_left + int(game_x * win_width)
                screen_y = win_top + int(game_y * win_height)
            else:
                # 绝对像素坐标：直接加上窗口偏移
                screen_x = win_left + int(game_x)
                screen_y = win_top + int(game_y)
            
            return screen_x, screen_y
        
        # 如果没有窗口，根据坐标类型处理
        if 0 <= game_x <= 1 and 0 <= game_y <= 1:
            # 相对坐标但没有窗口，这是错误情况
            logger.error(f'无法转换相对坐标 ({game_x}, {game_y})：找不到窗口 "{self.window_title}"')
            raise ValueError(f'找不到窗口 "{self.window_title}"，无法转换相对坐标')
        
        # 绝对像素坐标，直接返回（假设已经是屏幕坐标）
        logger.warning(f'找不到窗口 "{self.window_title}"，使用绝对坐标 ({game_x}, {game_y})')
        return game_x, game_y
    
    def _send_mouse_input(self, dx: int, dy: int, flags: int, mouse_data: int = 0):
        """
        发送鼠标输入（使用SendInput）
        
        参数:
            dx, dy: 坐标
            flags: 鼠标事件标志
            mouse_data: 额外数据（如滚轮）
        """
        extra = ctypes.pointer(ctypes.wintypes.ULONG(0))
        
        inputs = (INPUT * 1)()
        inputs[0].type = INPUT_MOUSE
        inputs[0].mi.dx = dx
        inputs[0].mi.dy = dy
        inputs[0].mi.mouseData = mouse_data
        inputs[0].mi.dwFlags = flags
        inputs[0].mi.time = 0
        inputs[0].mi.dwExtraInfo = extra
        
        user32.SendInput(1, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    
    def _send_keyboard_input(self, vk: int, flags: int, scan: int = 0):
        """
        发送键盘输入（使用SendInput）
        
        参数:
            vk: 虚拟键码
            flags: 键盘事件标志
            scan: 扫描码
        """
        extra = ctypes.pointer(ctypes.wintypes.ULONG(0))
        
        inputs = (INPUT * 1)()
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = vk
        inputs[0].ki.wScan = scan
        inputs[0].ki.dwFlags = flags
        inputs[0].ki.time = 0
        inputs[0].ki.dwExtraInfo = extra
        
        user32.SendInput(1, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    
    def move_to(self, x: int, y: int, is_relative: bool = False):
        """
        移动鼠标到指定位置
        
        特点：
        - 每次调用都重新获取游戏窗口位置（实时坐标）
        - 支持窗口移动后自动跟踪
        - 自动坐标转换（屏幕 ↔ 游戏窗口）
        
        参数:
            x, y: 坐标
            is_relative: 是否是相对于游戏窗口的坐标
        
        性能影响:
        - 每次调用增加约 0.1-0.5ms（获取窗口位置）
        - CPU 占用增加 < 0.1%
        """
        # 确保窗口激活（但不影响坐标计算）
        self._ensure_window_active()
        
        # 每次都重新获取窗口位置（实时跟踪窗口移动）
        if is_relative:
            # 如果是相对坐标，需要转换为屏幕坐标
            screen_x, screen_y = self.game_to_screen(x, y)
        else:
            # 如果是绝对坐标，直接使用
            screen_x, screen_y = x, y
        
        # 转换为 Windows SendInput 需要的绝对坐标（0-65535）
        abs_x = int(screen_x * 65535 / self._screen_width)
        abs_y = int(screen_y * 65535 / self._screen_height)
        
        self._send_mouse_input(abs_x, abs_y, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)
        logger.debug(f'鼠标移动到：屏幕 ({screen_x}, {screen_y}) [相对={is_relative}]')
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = 'left', is_relative: bool = False):
        """
        鼠标点击
        
        特点：
        - 如果提供坐标，会在点击前重新获取窗口位置（实时坐标）
        - 支持窗口移动后自动跟踪
        - 自动坐标转换
        
        参数:
            x, y: 点击位置（可选，不提供则在当前位置点击）
            button: 'left', 'right', 'middle'
            is_relative: 是否是相对于游戏窗口的坐标
        
        示例:
            # 在窗口内相对坐标 (0.5, 0.5) 点击（窗口中心）
            executor.click(0.5, 0.5, is_relative=True)
            
            # 在屏幕绝对坐标 (100, 200) 点击
            executor.click(100, 200)
        """
        self._ensure_window_active()
        
        if x is not None and y is not None:
            self.move_to(x, y, is_relative)
        
        if button == 'left':
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
        elif button == 'right':
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        elif button == 'middle':
            down_flag = MOUSEEVENTF_MIDDLEDOWN
            up_flag = MOUSEEVENTF_MIDDLEUP
        else:
            logger.warning(f'未知的鼠标按钮: {button}')
            return
        
        self._send_mouse_input(0, 0, down_flag)
        self._send_mouse_input(0, 0, up_flag)
        logger.debug(f'鼠标点击: {button}')
    
    def mouse_down(self, x: Optional[int] = None, y: Optional[int] = None, 
                   button: str = 'left', is_relative: bool = False):
        """按下鼠标键"""
        self._ensure_window_active()
        
        if x is not None and y is not None:
            self.move_to(x, y, is_relative)
        
        if button == 'left':
            flag = MOUSEEVENTF_LEFTDOWN
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTDOWN
        elif button == 'middle':
            flag = MOUSEEVENTF_MIDDLEDOWN
        else:
            logger.warning(f'未知的鼠标按钮: {button}')
            return
        
        self._send_mouse_input(0, 0, flag)
    
    def mouse_up(self, button: str = 'left'):
        """释放鼠标键"""
        self._ensure_window_active()
        
        if button == 'left':
            flag = MOUSEEVENTF_LEFTUP
        elif button == 'right':
            flag = MOUSEEVENTF_RIGHTUP
        elif button == 'middle':
            flag = MOUSEEVENTF_MIDDLEUP
        else:
            logger.warning(f'未知的鼠标按钮: {button}')
            return
        
        self._send_mouse_input(0, 0, flag)
    
    def scroll(self, delta: int):
        """
        鼠标滚轮
        
        参数:
            delta: 滚动量（正数向上，负数向下）
        """
        self._ensure_window_active()
        self._send_mouse_input(0, 0, MOUSEEVENTF_WHEEL, delta * WHEEL_DELTA)
    
    def key_press(self, vk: int, extended: bool = False):
        """
        按下并释放键盘键
        
        参数:
            vk: 虚拟键码
            extended: 是否是扩展键
        """
        self._ensure_window_active()
        
        flags = KEYEVENTF_EXTENDEDKEY if extended else 0
        self._send_keyboard_input(vk, flags)
        self._send_keyboard_input(vk, flags | KEYEVENTF_KEYUP)
        logger.debug(f'按键: {vk}')
    
    def key_down(self, vk: int, extended: bool = False):
        """按下键盘键"""
        self._ensure_window_active()
        
        flags = KEYEVENTF_EXTENDEDKEY if extended else 0
        self._send_keyboard_input(vk, flags)
    
    def key_up(self, vk: int, extended: bool = False):
        """释放键盘键"""
        self._ensure_window_active()
        
        flags = KEYEVENTF_EXTENDEDKEY if extended else 0
        self._send_keyboard_input(vk, flags | KEYEVENTF_KEYUP)


# 全局单例
_input_executor: Optional[GameInputExecutor] = None

def get_input_executor(window_title: Optional[str] = None, auto_activate_window: bool = True) -> GameInputExecutor:
    """
    获取输入执行器单例
    
    参数:
        window_title: 游戏窗口标题
        auto_activate_window: 是否自动激活游戏窗口（默认True）
    
    返回:
        GameInputExecutor 实例
    """
    global _input_executor
    if (_input_executor is None or 
        _input_executor.window_title != window_title or
        _input_executor.auto_activate_window != auto_activate_window):
        _input_executor = GameInputExecutor(window_title, auto_activate_window)
    return _input_executor

def set_game_window_title(title: str):
    """设置游戏窗口标题"""
    global _input_executor
    if _input_executor:
        _input_executor.window_title = title
    else:
        _input_executor = GameInputExecutor(title)

def set_auto_activate_window(enabled: bool):
    """设置是否自动激活窗口"""
    global _input_executor
    if _input_executor:
        _input_executor.auto_activate_window = enabled
    else:
        _input_executor = GameInputExecutor(None, enabled)
