# -*- encoding:utf-8 -*-
"""
简易坐标获取工具：使用 tkinter 实现，无需额外依赖
功能：
- 显示鼠标当前屏幕坐标
- 当鼠标在游戏窗口内时显示相对坐标
- 支持记录起点和终点，计算区域
- 支持窗口标题设置
"""
import tkinter as tk
import time
from typing import Optional, Tuple


try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def get_window_rect_by_title(title_substr: str) -> Optional[Tuple[int, int, int, int]]:
    """
    根据窗口标题（支持部分匹配）查找窗口，返回 (left, top, width, height)
    """
    if not HAS_WIN32 or not title_substr:
        return None
    
    result = [None]
    
    def enum_cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t and title_substr.strip() in t:
                    # 获取客户区域矩形
                    client_rect = win32gui.GetClientRect(hwnd)
                    # 将客户区域坐标转换为屏幕坐标
                    left, top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
                    right, bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
                    result[0] = (left, top, right - left, bottom - top)
                    return False
        except Exception:
            pass
        return True
    
    try:
        win32gui.EnumWindows(enum_cb, None)
        return result[0]
    except Exception:
        pass
    return None


class CoordinateTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("坐标获取工具 (简易版)")
        self.root.geometry("400x350")
        self.root.wm_attributes("-topmost", 1)  # 窗口置顶
        
        self.window_title = "大航海时代：传说"
        self.start_point = None
        self.end_point = None
        
        self.setup_ui()
        self.update_coordinates()
    
    def setup_ui(self):
        # 窗口标题设置
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(title_frame, text="游戏窗口标题：").pack(side=tk.LEFT, padx=5)
        self.title_var = tk.StringVar(value=self.window_title)
        title_entry = tk.Entry(title_frame, textvariable=self.title_var, width=30)
        title_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(title_frame, text="刷新", command=self.refresh_window).pack(side=tk.LEFT, padx=5)
        
        # 窗口信息
        self.window_info = tk.Label(self.root, text="窗口: 未找到", font=("Arial", 10))
        self.window_info.pack(pady=5, padx=10)
        
        # 当前坐标
        coord_frame = tk.Frame(self.root)
        coord_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(coord_frame, text="屏幕坐标: ", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.screen_coord = tk.Label(coord_frame, text="(0, 0)", font=("Arial", 10, "bold"))
        self.screen_coord.pack(side=tk.LEFT, padx=5)
        
        coord_frame2 = tk.Frame(self.root)
        coord_frame2.pack(pady=5, padx=10, fill=tk.X)
        
        tk.Label(coord_frame2, text="游戏内坐标: ", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.window_coord = tk.Label(coord_frame2, text="(0, 0)", font=("Arial", 10, "bold"), fg="green")
        self.window_coord.pack(side=tk.LEFT, padx=5)
        
        # 区域选择
        region_frame = tk.Frame(self.root)
        region_frame.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Button(region_frame, text="记录起点 (F1)", command=self.record_start, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(region_frame, text="记录终点 (F2)", command=self.record_end, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(region_frame, text="清除", command=self.clear_region, width=10).pack(side=tk.LEFT, padx=5)
        
        # 区域信息
        self.start_label = tk.Label(self.root, text="起点: 未设置", font=("Arial", 10))
        self.start_label.pack(pady=2, padx=10)
        
        self.end_label = tk.Label(self.root, text="终点: 未设置", font=("Arial", 10))
        self.end_label.pack(pady=2, padx=10)
        
        self.region_label = tk.Label(self.root, text="区域: (0, 0, 0, 0)", font=("Arial", 10, "bold"), fg="blue")
        self.region_label.pack(pady=5, padx=10)
        
        # 说明
        help_text = """使用说明：
1. 确保游戏窗口为1024x768
2. 将鼠标移到要检测的位置
3. 点击记录起点和终点来选择区域
4. 复制区域坐标到配置中
5. 按 F1 记录起点，F2 记录终点
6. 确保工具窗口有焦点"""
        help_label = tk.Label(self.root, text=help_text, font=("Arial", 9), justify=tk.LEFT, fg="gray")
        help_label.pack(pady=10, padx=10, fill=tk.X)
        
        # 绑定热键（只绑定一次）
        self.root.bind('<F1>', lambda e: self.record_start())
        self.root.bind('<F2>', lambda e: self.record_end())
        
        # 确保窗口获得焦点
        self.root.focus_set()
    
    def refresh_window(self):
        self.window_title = self.title_var.get()
    
    def record_start(self):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            rel_x = x - win_left
            rel_y = y - win_top
            self.start_point = (rel_x, rel_y)
            self.start_label.config(text=f"起点: ({rel_x}, {rel_y})")
            self.update_region()
    
    def record_end(self):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            rel_x = x - win_left
            rel_y = y - win_top
            self.end_point = (rel_x, rel_y)
            self.end_label.config(text=f"终点: ({rel_x}, {rel_y})")
            self.update_region()
    
    def clear_region(self):
        self.start_point = None
        self.end_point = None
        self.start_label.config(text="起点: 未设置")
        self.end_label.config(text="终点: 未设置")
        self.region_label.config(text="区域: (0, 0, 0, 0)")
    
    def update_region(self):
        if self.start_point and self.end_point:
            x1, y1 = self.start_point
            x2, y2 = self.end_point
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            self.region_label.config(text=f"区域: ({left}, {top}, {width}, {height})")
    
    def update_coordinates(self):
        # 获取鼠标当前位置
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        self.screen_coord.config(text=f"({x}, {y})")
        
        # 计算游戏内坐标
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, win_width, win_height = window_rect
            self.window_info.config(text=f"窗口: ({win_left}, {win_top}) {win_width}x{win_height}")
            
            rel_x = x - win_left
            rel_y = y - win_top
            if 0 <= rel_x < win_width and 0 <= rel_y < win_height:
                self.window_coord.config(text=f"({rel_x}, {rel_y})", fg="green")
            else:
                self.window_coord.config(text="鼠标在窗口外", fg="red")
        else:
            self.window_info.config(text="窗口: 未找到")
            self.window_coord.config(text="窗口未找到", fg="gray")
        
        # 每秒更新一次
        self.root.after(100, self.update_coordinates)
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    tool = CoordinateTool()
    tool.run()