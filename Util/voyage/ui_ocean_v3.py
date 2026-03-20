# -*- encoding:utf-8 -*-
"""
远洋V3 UI组件（调整版）：
- 城市1-8横向布局
- 每个城市：海域/城市/买卖脚本/下一站策略
- 不需要公共脚本配置区
- UI显示中文，底层使用拼音
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

from .pinyin_mapping import (
    sea_pinyin_to_chinese, sea_chinese_to_pinyin,
    city_pinyin_to_chinese, city_chinese_to_pinyin,
    convert_sea_cities_to_chinese
)


class OceanV3CityRow(QFrame):
    """单个城市配置行（调整版）"""
    
    changed = pyqtSignal(int)  # city_index
    
    def __init__(self, city_index: int, parent=None):
        super().__init__(parent)
        self.city_index = city_index
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet('OceanV3CityRow { background-color: #f5f5f5; padding: 4px; border-radius: 4px; }')
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # 城市标签
        lbl_city = QLabel(f'城市{self.city_index}')
        lbl_city.setStyleSheet('font-weight: bold; min-width: 60px;')
        layout.addWidget(lbl_city)
        
        # 选项1：海域
        self.cb_sea = QComboBox()
        self.cb_sea.setPlaceholderText('海域')
        self.cb_sea.setMaximumWidth(120)
        self.cb_sea.currentTextChanged.connect(self._on_sea_changed)
        self.cb_sea.currentTextChanged.connect(self._on_changed)
        layout.addWidget(self.cb_sea)
        
        # 选项2：城市
        self.cb_city = QComboBox()
        self.cb_city.setPlaceholderText('城市')
        self.cb_city.setMaximumWidth(120)
        self.cb_city.currentTextChanged.connect(self._on_changed)
        layout.addWidget(self.cb_city)
        
        # 选项3：指定买卖操作脚本
        self.cb_trade_script = QComboBox()
        self.cb_trade_script.setPlaceholderText('买卖脚本')
        self.cb_trade_script.setMaximumWidth(180)
        self.cb_trade_script.currentTextChanged.connect(self._on_changed)
        layout.addWidget(self.cb_trade_script)
        
        # 选项4：下一站策略
        self.cb_next_strategy = QComboBox()
        self.cb_next_strategy.addItems(['指定城市', '自动选择最高价'])
        self.cb_next_strategy.setMaximumWidth(140)
        self.cb_next_strategy.currentTextChanged.connect(self._on_changed)
        layout.addWidget(self.cb_next_strategy)
        
        layout.addStretch()
    
    def set_sea_cities(self, sea_cities: Dict[str, List[str]]):
        """设置海域-城市数据（sea_cities为拼音格式，UI显示中文）"""
        # 先转换为中文用于显示
        self.sea_cities_pinyin = sea_cities
        self.sea_cities_chinese = convert_sea_cities_to_chinese(sea_cities)
        
        current_sea_pinyin = self._get_current_sea_pinyin()
        current_city_pinyin = self._get_current_city_pinyin()
        
        self.cb_sea.blockSignals(True)
        self.cb_city.blockSignals(True)
        
        self.cb_sea.clear()
        self.cb_sea.addItem('')
        for sea_chinese in sorted(self.sea_cities_chinese.keys()):
            sea_pinyin = sea_chinese_to_pinyin(sea_chinese)
            self.cb_sea.addItem(sea_chinese, sea_pinyin)
        
        if current_sea_pinyin:
            idx = self.cb_sea.findData(current_sea_pinyin)
            if idx >= 0:
                self.cb_sea.setCurrentIndex(idx)
        
        self._update_cities()
        
        if current_city_pinyin:
            idx = self.cb_city.findData(current_city_pinyin)
            if idx >= 0:
                self.cb_city.setCurrentIndex(idx)
        
        self.cb_sea.blockSignals(False)
        self.cb_city.blockSignals(False)
    
    def set_script_list(self, scripts: List[str]):
        """设置脚本列表"""
        current_text = self.cb_trade_script.currentText()
        self.cb_trade_script.blockSignals(True)
        self.cb_trade_script.clear()
        self.cb_trade_script.addItem('')
        for s in scripts:
            self.cb_trade_script.addItem(os.path.basename(s) if os.path.isabs(s) else s, s)
        self.cb_trade_script.blockSignals(False)
        
        if current_text:
            idx = self.cb_trade_script.findText(current_text)
            if idx >= 0:
                self.cb_trade_script.setCurrentIndex(idx)
    
    def _update_cities(self):
        """根据当前海域更新城市列表"""
        sea_pinyin = self.cb_sea.currentData()
        self.cb_city.blockSignals(True)
        self.cb_city.clear()
        
        if sea_pinyin and sea_pinyin in self.sea_cities_pinyin:
            for city_pinyin in self.sea_cities_pinyin[sea_pinyin]:
                city_chinese = city_pinyin_to_chinese(city_pinyin)
                self.cb_city.addItem(city_chinese, city_pinyin)
        
        self.cb_city.blockSignals(False)
    
    def _get_current_sea_pinyin(self) -> str:
        """获取当前选择的海域拼音"""
        return self.cb_sea.currentData() or ''
    
    def _get_current_city_pinyin(self) -> str:
        """获取当前选择的城市拼音"""
        return self.cb_city.currentData() or ''
    
    def _on_sea_changed(self):
        self._update_cities()
    
    def _on_changed(self):
        self.changed.emit(self.city_index)
    
    def get_config(self) -> dict:
        """获取配置（返回拼音格式）"""
        strategy_text = self.cb_next_strategy.currentText()
        return {
            'city_index': self.city_index,
            'sea': self._get_current_sea_pinyin(),
            'city': self._get_current_city_pinyin(),
            'script_trade': self.cb_trade_script.currentData(),
            'next_stop_strategy': 'auto' if strategy_text == '自动选择最高价' else 'specified',
        }
    
    def set_config(self, cfg: dict):
        """设置配置（cfg为拼音格式，UI显示中文）"""
        sea_pinyin = cfg.get('sea', '')
        city_pinyin = cfg.get('city', '')
        script_trade = cfg.get('script_trade', '')
        strategy = cfg.get('next_stop_strategy', 'specified')
        
        # 先保存当前城市选择，因为更新海域会清空城市列表
        
        # 设置海域
        if sea_pinyin:
            idx = self.cb_sea.findData(sea_pinyin)
            if idx >= 0:
                self.cb_sea.setCurrentIndex(idx)
        
        # 更新城市列表
        self._update_cities()
        
        # 设置城市
        if city_pinyin:
            idx = self.cb_city.findData(city_pinyin)
            if idx >= 0:
                self.cb_city.setCurrentIndex(idx)
        
        # 设置脚本
        if script_trade:
            idx = self.cb_trade_script.findData(script_trade)
            if idx >= 0:
                self.cb_trade_script.setCurrentIndex(idx)
        
        # 设置策略
        self.cb_next_strategy.setCurrentIndex(1 if strategy == 'auto' else 0)


class OceanV3Panel(QWidget):
    """远洋V3主面板（调整版）"""
    
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.city_rows: List[OceanV3CityRow] = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 说明
        lbl_tip = QLabel('说明：每个城市的下一站策略使用下一行城市的海域/城市配置，城市8使用城市1的配置')
        lbl_tip.setStyleSheet('color: #666; font-size: 12px; margin-bottom: 5px;')
        layout.addWidget(lbl_tip)
        
        # 城市配置区
        lbl_cities = QLabel('城市配置 (城市1-8):')
        lbl_cities.setStyleSheet('font-weight: bold; font-size: 14px;')
        layout.addWidget(lbl_cities)
        
        # 可滚动的城市列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setSpacing(8)
        
        # 创建8个城市行
        for i in range(1, 9):
            row = OceanV3CityRow(i)
            row.changed.connect(self._on_city_changed)
            self.city_rows.append(row)
            self.scroll_layout.addWidget(row)
        
        self.scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def set_sea_cities(self, sea_cities: Dict[str, List[str]]):
        """设置海域-城市数据"""
        for row in self.city_rows:
            row.set_sea_cities(sea_cities)
    
    def set_script_list(self, scripts: List[str]):
        """设置脚本列表"""
        for row in self.city_rows:
            row.set_script_list(scripts)
    
    def _on_city_changed(self, city_index: int):
        self.config_changed.emit()
    
    def get_config(self) -> dict:
        """获取完整配置"""
        cities = []
        for row in self.city_rows:
            cities.append(row.get_config())
        
        return {
            'cities': cities,
        }
    
    def set_config(self, cfg: dict):
        """设置配置"""
        cities_cfg = cfg.get('cities', [])
        for i, row_cfg in enumerate(cities_cfg):
            if i < len(self.city_rows):
                self.city_rows[i].set_config(row_cfg)
