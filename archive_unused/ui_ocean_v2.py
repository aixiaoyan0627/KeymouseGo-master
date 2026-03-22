# -*- encoding:utf-8 -*-
"""
新架构远洋UI组件：
- 可滚动面板
- 动态添加航线（最多4条）
- 双层下拉选择（海域→城市）
- 支持"自动选择最高价"选项
"""
import os
from typing import Dict, List, Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QScrollArea, QFrame,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal as pyqtSignal
from loguru import logger


class DoubleLayerCitySelector(QWidget):
    """双层城市选择器：海域→城市，支持'自动选择最高价'"""
    
    city_changed = pyqtSignal(str, str, bool)
    
    AUTO_SELECT_TEXT = '自动选择最高价'
    
    def __init__(self, label_text: str, enable_auto_select: bool = False, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.enable_auto_select = enable_auto_select
        self.sea_cities: Dict[str, List[str]] = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        lbl = QLabel(self.label_text)
        layout.addWidget(lbl)
        
        grid = QGridLayout()
        grid.setSpacing(4)
        
        grid.addWidget(QLabel('海域:'), 0, 0)
        self.cb_sea = QComboBox()
        self.cb_sea.currentTextChanged.connect(self._on_sea_changed)
        grid.addWidget(self.cb_sea, 0, 1)
        
        grid.addWidget(QLabel('城市:'), 1, 0)
        self.cb_city = QComboBox()
        self.cb_city.currentTextChanged.connect(self._on_city_changed)
        grid.addWidget(self.cb_city, 1, 1)
        
        layout.addLayout(grid)
    
    def set_sea_cities(self, sea_cities: Dict[str, List[str]]):
        """设置海域-城市数据"""
        self.sea_cities = sea_cities
        
        current_sea = self.cb_sea.currentText()
        current_city = self.cb_city.currentText()
        
        self.cb_sea.blockSignals(True)
        self.cb_city.blockSignals(True)
        
        self.cb_sea.clear()
        self.cb_sea.addItem('')
        for sea in sorted(sea_cities.keys()):
            self.cb_sea.addItem(sea)
        
        if current_sea in sea_cities:
            idx = self.cb_sea.findText(current_sea)
            if idx >= 0:
                self.cb_sea.setCurrentIndex(idx)
        
        self._update_cities()
        
        if current_city:
            idx = self.cb_city.findText(current_city)
            if idx >= 0:
                self.cb_city.setCurrentIndex(idx)
        
        self.cb_sea.blockSignals(False)
        self.cb_city.blockSignals(False)
    
    def _update_cities(self):
        """根据当前海域更新城市列表"""
        self.cb_city.clear()
        
        sea = self.cb_sea.currentText()
        if not sea:
            return
        
        if self.enable_auto_select:
            self.cb_city.addItem(self.AUTO_SELECT_TEXT)
        
        if sea in self.sea_cities:
            for city in self.sea_cities[sea]:
                self.cb_city.addItem(city)
    
    def _on_sea_changed(self, text: str):
        self._update_cities()
        self._emit_change()
    
    def _on_city_changed(self, text: str):
        self._emit_change()
    
    def _emit_change(self):
        sea = self.cb_sea.currentText()
        city = self.cb_city.currentText()
        use_auto = (city == self.AUTO_SELECT_TEXT)
        self.city_changed.emit(sea, city, use_auto)
    
    def get_selection(self) -> tuple:
        """获取选择结果: (sea, city, use_auto_select)"""
        sea = self.cb_sea.currentText()
        city = self.cb_city.currentText()
        use_auto = (city == self.AUTO_SELECT_TEXT)
        return sea, city, use_auto
    
    def set_selection(self, sea: str, city: str, use_auto: bool = False):
        """设置选择"""
        sea_idx = self.cb_sea.findText(sea)
        if sea_idx >= 0:
            self.cb_sea.setCurrentIndex(sea_idx)
        
        if use_auto:
            city_idx = self.cb_city.findText(self.AUTO_SELECT_TEXT)
            if city_idx >= 0:
                self.cb_city.setCurrentIndex(city_idx)
        else:
            city_idx = self.cb_city.findText(city)
            if city_idx >= 0:
                self.cb_city.setCurrentIndex(city_idx)


class RouteCard(QFrame):
    """单个航线配置卡片"""
    
    removed = pyqtSignal(int)
    
    def __init__(self, route_id: int, parent=None):
        super().__init__(parent)
        self.route_id = route_id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet('RouteCard { background-color: #f5f5f5; padding: 8px; border-radius: 4px; }')
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        lbl_title = QLabel(f'航线 {self.route_id}')
        lbl_title.setStyleSheet('font-weight: bold; font-size: 14px;')
        header_layout.addWidget(lbl_title)
        
        header_layout.addStretch()
        
        btn_remove = QPushButton('×')
        btn_remove.setFixedSize(28, 28)
        btn_remove.setStyleSheet('''
            QPushButton { 
                background-color: #ff6b6b; 
                color: white; 
                border: none; 
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ee5a5a; }
        ''')
        btn_remove.clicked.connect(lambda: self.removed.emit(self.route_id))
        header_layout.addWidget(btn_remove)
        
        layout.addLayout(header_layout)
        
        self.buy_selector = DoubleLayerCitySelector('买入城市', enable_auto_select=False)
        layout.addWidget(self.buy_selector)
        
        self.sell_selector = DoubleLayerCitySelector('卖出城市', enable_auto_select=True)
        layout.addWidget(self.sell_selector)
        
        lbl_scripts_title = QLabel('脚本配置:')
        lbl_scripts_title.setStyleSheet('font-weight: bold; font-size: 12px; margin-top: 5px;')
        layout.addWidget(lbl_scripts_title)
        
        grid_scripts = QGridLayout()
        grid_scripts.setSpacing(4)
        
        # 买卖操作 - 只显示这个给用户
        grid_scripts.addWidget(QLabel('买卖操作:'), 0, 0)
        self.cb_script_trade = QComboBox()
        self.cb_script_trade.setMaximumWidth(140)
        grid_scripts.addWidget(self.cb_script_trade, 0, 1)
        
        layout.addLayout(grid_scripts)
    
    def set_sea_cities(self, sea_cities: Dict[str, List[str]]):
        self.buy_selector.set_sea_cities(sea_cities)
        self.sell_selector.set_sea_cities(sea_cities)
    
    def set_scripts(self, scripts: List[str]):
        """设置可用脚本列表"""
        self.cb_script_trade.clear()
        self.cb_script_trade.addItem("")
        self.cb_script_trade.addItems(scripts)
        self.cb_script_trade.setCurrentIndex(0)
    
    def get_config(self) -> dict:
        buy_sea, buy_city, buy_auto = self.buy_selector.get_selection()
        sell_sea, sell_city, sell_auto = self.sell_selector.get_selection()
        
        return {
            'route_id': self.route_id,
            'buy': {
                'sea': buy_sea,
                'city': buy_city,
                'use_auto_select': buy_auto,
            },
            'sell': {
                'sea': sell_sea,
                'city': sell_city,
                'use_auto_select': sell_auto,
            },
            'script_dock_fixed': '',  # 端口保留，用户后期填充
            'script_trade': self.cb_script_trade.currentText(),
            'script_next_stop_specified': '',  # 端口：指定城市对应的下一站脚本
            'script_next_stop_auto': '',  # 端口：自动选择最高价对应的下一站脚本
        }


class OceanV2Panel(QWidget):
    """新架构远洋配置面板"""
    
    MAX_ROUTES = 4
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.route_cards: Dict[int, RouteCard] = {}
        self.scripts: List[str] = []
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet('''
            QScrollArea { border: none; }
            QScrollBar:vertical { width: 12px; }
        ''')
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        btn_add = QPushButton('+ 添加航线')
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QPushButton:disabled { background-color: #cccccc; }
        ''')
        btn_add.clicked.connect(self._add_route)
        self.btn_add = btn_add
        main_layout.addWidget(btn_add)
    
    def set_sea_cities(self, sea_cities: Dict[str, List[str]]):
        """设置海域-城市数据"""
        self.sea_cities = sea_cities
        for card in self.route_cards.values():
            card.set_sea_cities(sea_cities)
    
    def set_scripts(self, scripts: List[str]):
        """设置可用脚本列表"""
        self.scripts = scripts
        for card in self.route_cards.values():
            card.set_scripts(scripts)
    
    def _get_next_route_id(self) -> int:
        used_ids = set(self.route_cards.keys())
        for i in range(1, self.MAX_ROUTES + 1):
            if i not in used_ids:
                return i
        return -1
    
    def _add_route(self):
        route_id = self._get_next_route_id()
        if route_id < 0:
            return
        
        card = RouteCard(route_id)
        if hasattr(self, 'sea_cities'):
            card.set_sea_cities(self.sea_cities)
        if self.scripts:
            card.set_scripts(self.scripts)
        card.removed.connect(self._remove_route)
        
        self.route_cards[route_id] = card
        self.scroll_layout.addWidget(card)
        
        self._update_add_button()
    
    def _remove_route(self, route_id: int):
        if route_id not in self.route_cards:
            return
        
        card = self.route_cards.pop(route_id)
        self.scroll_layout.removeWidget(card)
        card.deleteLater()
        
        self._update_add_button()
    
    def _update_add_button(self):
        count = len(self.route_cards)
        self.btn_add.setEnabled(count < self.MAX_ROUTES)
        self.btn_add.setText(f'+ 添加航线 ({count}/{self.MAX_ROUTES})')
    
    def get_routes_config(self) -> List[dict]:
        """获取所有航线配置"""
        result = []
        sorted_ids = sorted(self.route_cards.keys())
        for route_id in sorted_ids:
            result.append(self.route_cards[route_id].get_config())
        return result
