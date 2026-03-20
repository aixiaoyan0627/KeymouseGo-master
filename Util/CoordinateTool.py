# -*- encoding:utf-8 -*-
"""
坐标获取工具：帮助用户获取游戏窗口内的坐标和区域
"""
import sys
import os
from typing import Optional, Tuple

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

try:
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def get_window_rect_by_title(title_substr: str) -> Optional[Tuple[int, int, int, int]]:
    """
    根据窗口标题（支持部分匹配）查找窗口，返回 (left, top, width, height)
    注意：返回的是客户区域（游戏内容显示区域）的坐标，不包括标题栏和边框
    """
    if not HAS_WIN32 or not title_substr:
        return None
    
    result = [None]
    
    def enum_cb(hwnd, _):
        try:
            # 检查窗口句柄是否有效
            if not win32gui.IsWindow(hwnd):
                return True
            
            # 检查窗口是否可见
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
            except Exception:
                # GetClientRect 失败，跳过此窗口
                return True
            
            # 将客户区域坐标转换为屏幕坐标
            try:
                left, top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
                right, bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
                result[0] = (left, top, right - left, bottom - top)
                return False
            except Exception:
                # ClientToScreen 失败，跳过此窗口
                return True
                
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
    
    try:
        win32gui.EnumWindows(enum_cb, None)
        return result[0]
    except Exception:
        # 忽略枚举过程中的错误
        pass
    return None


class CoordinateToolWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('坐标获取工具 - 1024x768')
        self.setGeometry(100, 100, 400, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        self.window_title = '大航海时代：传说'
        self.start_point: Optional[Tuple[int, int]] = None
        self.end_point: Optional[Tuple[int, int]] = None
        
        self.init_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_coordinates)
        self.update_timer.start(50)
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 窗口标题设置
        title_group = QGroupBox('游戏窗口')
        title_layout = QHBoxLayout()
        self.title_input = QLineEdit(self.window_title)
        self.title_input.setPlaceholderText('输入游戏窗口标题')
        self.refresh_btn = QPushButton('刷新')
        self.refresh_btn.clicked.connect(self.refresh_window)
        title_layout.addWidget(self.title_input)
        title_layout.addWidget(self.refresh_btn)
        title_group.setLayout(title_layout)
        layout.addWidget(title_group)
        
        # 窗口信息
        self.window_info_label = QLabel('窗口: 未找到')
        layout.addWidget(self.window_info_label)
        
        # 当前坐标
        coord_group = QGroupBox('当前坐标')
        coord_layout = QVBoxLayout()
        self.screen_coord_label = QLabel('屏幕坐标: (0, 0)')
        self.window_coord_label = QLabel('游戏内坐标: (0, 0)')
        coord_layout.addWidget(self.screen_coord_label)
        coord_layout.addWidget(self.window_coord_label)
        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)
        
        # 区域选择
        region_group = QGroupBox('区域选择')
        region_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton('记录起点 (F1)')
        self.start_btn.clicked.connect(self.record_start)
        self.end_btn = QPushButton('记录终点 (F2)')
        self.end_btn.clicked.connect(self.record_end)
        self.clear_btn = QPushButton('清除')
        self.clear_btn.clicked.connect(self.clear_region)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.end_btn)
        btn_layout.addWidget(self.clear_btn)
        region_layout.addLayout(btn_layout)
        
        self.start_label = QLabel('起点: 未设置')
        self.end_label = QLabel('终点: 未设置')
        self.region_label = QLabel('区域: (0, 0, 0, 0)')
        self.region_label.setStyleSheet('font-weight: bold; color: blue;')
        region_layout.addWidget(self.start_label)
        region_layout.addWidget(self.end_label)
        region_layout.addWidget(self.region_label)
        
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # 说明
        help_label = QLabel('使用说明：\n1. 确保游戏窗口为1024x768\n2. 将鼠标移到要检测的位置\n3. 点击记录起点和终点来选择区域\n4. 复制区域坐标到配置中')
        help_label.setStyleSheet('color: gray;')
        layout.addWidget(help_label)
        
        layout.addStretch()
    
    def refresh_window(self):
        self.window_title = self.title_input.text()
    
    def update_coordinates(self):
        cursor_pos = QCursor.pos()
        screen_x = cursor_pos.x()
        screen_y = cursor_pos.y()
        self.screen_coord_label.setText(f'屏幕坐标: ({screen_x}, {screen_y})')
        
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, win_width, win_height = window_rect
            self.window_info_label.setText(f'窗口: ({win_left}, {win_top}) {win_width}x{win_height}')
            
            rel_x = screen_x - win_left
            rel_y = screen_y - win_top
            if 0 <= rel_x < win_width and 0 <= rel_y < win_height:
                self.window_coord_label.setText(f'游戏内坐标: ({rel_x}, {rel_y})')
                self.window_coord_label.setStyleSheet('color: green;')
            else:
                self.window_coord_label.setText(f'游戏内坐标: 鼠标在窗口外')
                self.window_coord_label.setStyleSheet('color: red;')
        else:
            self.window_info_label.setText('窗口: 未找到')
            self.window_coord_label.setText('游戏内坐标: 窗口未找到')
            self.window_coord_label.setStyleSheet('color: gray;')
    
    def record_start(self):
        cursor_pos = QCursor.pos()
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            rel_x = cursor_pos.x() - win_left
            rel_y = cursor_pos.y() - win_top
            self.start_point = (rel_x, rel_y)
            self.start_label.setText(f'起点: ({rel_x}, {rel_y})')
            self.update_region()
    
    def record_end(self):
        cursor_pos = QCursor.pos()
        window_rect = get_window_rect_by_title(self.window_title)
        if window_rect:
            win_left, win_top, _, _ = window_rect
            rel_x = cursor_pos.x() - win_left
            rel_y = cursor_pos.y() - win_top
            self.end_point = (rel_x, rel_y)
            self.end_label.setText(f'终点: ({rel_x}, {rel_y})')
            self.update_region()
    
    def clear_region(self):
        self.start_point = None
        self.end_point = None
        self.start_label.setText('起点: 未设置')
        self.end_label.setText('终点: 未设置')
        self.region_label.setText('区域: (0, 0, 0, 0)')
    
    def update_region(self):
        if self.start_point and self.end_point:
            x1, y1 = self.start_point
            x2, y2 = self.end_point
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            self.region_label.setText(f'区域: ({left}, {top}, {width}, {height})')
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F1:
            self.record_start()
        elif event.key() == Qt.Key_F2:
            self.record_end()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CoordinateToolWindow()
    window.show()
    sys.exit(app.exec())
