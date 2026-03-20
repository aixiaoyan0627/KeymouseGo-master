# -*- encoding:utf-8 -*-
"""
新架构独立测试程序 (简化版)
用于测试 OceanV2Panel UI和OceanMultiRouteStrategy
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
    QSplitter
)
from PySide6.QtCore import Qt
from loguru import logger
logger.remove()
logger.add(sys.stderr, level="INFO")

from KeymouseGo import to_abs_path
from Util.DetectionLoop import list_sea_city_from_imgsc
from Util.voyage import (
    OceanMultiRouteStrategy,
    OceanV2Config,
    OceanRouteConfig,
    OceanCityConfig,
)
from Util.voyage.ui_ocean_v2 import OceanV2Panel


class MainWindow(QMainWindow):
    """测试主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("新架构测试 - 独立测试程序")
        self.resize(900, 700)
        
        # 先初始化属性
        self.log_text = None
        self.ocean_panel = None
        self.scripts: list = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：OceanV2Panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        lbl_title = QLabel("远洋配置面板 (新架构 V2)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        left_layout.addWidget(lbl_title)
        
        self.ocean_panel = OceanV2Panel()
        left_layout.addWidget(self.ocean_panel)
        
        splitter.addWidget(left_widget)
        
        # 右侧：日志和控制面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        lbl_log = QLabel("日志输出")
        lbl_log.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        right_layout.addWidget(lbl_log)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        right_layout.addWidget(self.log_text)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_get_config = QPushButton("获取配置")
        self.btn_get_config.clicked.connect(self._on_get_config)
        btn_layout.addWidget(self.btn_get_config)
        
        self.btn_test_strategy = QPushButton("测试策略")
        self.btn_test_strategy.clicked.connect(self._on_test_strategy)
        btn_layout.addWidget(self.btn_test_strategy)
        
        self.btn_clear_log = QPushButton("清除日志")
        self.btn_clear_log.clicked.connect(self._on_clear_log)
        btn_layout.addWidget(self.btn_clear_log)
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_widget)
        
        splitter.setSizes([500, 400])
        main_layout.addWidget(splitter)
        
        # 加载海域-城市数据和脚本
        self._load_sea_cities()
        self._load_scripts()
    
    def _load_scripts(self):
        """加载 scripts 文件夹下的脚本"""
        scripts_dir = to_abs_path('scripts')
        self.scripts = []
        if os.path.isdir(scripts_dir):
            for f in os.listdir(scripts_dir):
                if f.lower().endswith('.json') or f.lower().endswith('.json5'):
                    self.scripts.append(f)
            self.scripts.sort()
            self.ocean_panel.set_scripts(self.scripts)
            self._log(f"加载了 {len(self.scripts)} 个脚本")
        else:
            self._log("scripts 目录不存在")
    
    def _load_sea_cities(self):
        """加载海域-城市数据"""
        imgs_c = to_abs_path('imgsC')
        if os.path.isdir(imgs_c):
            sea_city_map = list_sea_city_from_imgsc(imgs_c)
            self.ocean_panel.set_sea_cities(sea_city_map)
            self._log(f"加载了 {len(sea_city_map)} 个海域的数据")
        else:
            self._log("imgsC 目录不存在")
    
    def _log(self, msg):
        """输出日志"""
        if self.log_text:
            self.log_text.append(msg)
        logger.info(msg)
    
    def _on_get_config(self):
        """获取当前配置"""
        routes_data = self.ocean_panel.get_routes_config()
        
        self._log("=" * 60)
        self._log("获取航线配置:")
        self._log("=" * 60)
        
        for i, route_data in enumerate(routes_data):
            self._log(f"航线 {i + 1}:")
            self._log(f"  买入: {route_data['buy']}")
            self._log(f"  卖出: {route_data['sell']}")
            self._log(f"  脚本-到港固定: {route_data.get('script_dock_fixed', '')} [默认端口]")
            self._log(f"  脚本-买卖操作: {route_data.get('script_trade', '')}")
            self._log(f"  脚本-下一站(指定): {route_data.get('script_next_stop_specified', '')} [端口]")
            self._log(f"  脚本-下一站(自动): {route_data.get('script_next_stop_auto', '')} [端口]")
            self._log("-" * 40)
        
        self._log("=" * 60)
        
        # 转换为 OceanV2Config
        ocean_config = OceanV2Config()
        for route_data in routes_data:
            buy = OceanCityConfig(
                sea=route_data['buy']['sea'],
                city=route_data['buy']['city'],
                use_auto_select=route_data['buy']['use_auto_select'],
            )
            sell = OceanCityConfig(
                sea=route_data['sell']['sea'],
                city=route_data['sell']['city'],
                use_auto_select=route_data['sell']['use_auto_select'],
            )
            route_config = OceanRouteConfig(
                route_id=route_data['route_id'],
                buy=buy,
                sell=sell,
                script_dock_fixed=route_data.get('script_dock_fixed', ''),
                script_trade=route_data.get('script_trade', ''),
                script_next_stop_specified=route_data.get('script_next_stop_specified', ''),
                script_next_stop_auto=route_data.get('script_next_stop_auto', ''),
            )
            ocean_config.routes.append(route_config)
        
        self._log(f"转换为 OceanV2Config 成功，共 {len(ocean_config.routes)} 条航线")
        
        QMessageBox.information(self, "成功", f"成功获取配置！\n共 {len(routes_data)} 条航线", QMessageBox.Ok)
    
    def _on_test_strategy(self):
        """测试策略模块"""
        routes_data = self.ocean_panel.get_routes_config()
        
        if not routes_data:
            QMessageBox.warning(self, "提示", "请先添加至少一条航线", QMessageBox.Ok)
            return
        
        ocean_config = OceanV2Config()
        for route_data in routes_data:
            buy = OceanCityConfig(
                sea=route_data['buy']['sea'],
                city=route_data['buy']['city'],
                use_auto_select=route_data['buy']['use_auto_select'],
            )
            sell = OceanCityConfig(
                sea=route_data['sell']['sea'],
                city=route_data['sell']['city'],
                use_auto_select=route_data['sell']['use_auto_select'],
            )
            route_config = OceanRouteConfig(
                route_id=route_data['route_id'],
                buy=buy,
                sell=sell,
                script_dock_fixed=route_data.get('script_dock_fixed', ''),
                script_trade=route_data.get('script_trade', ''),
                script_next_stop_specified=route_data.get('script_next_stop_specified', ''),
                script_next_stop_auto=route_data.get('script_next_stop_auto', ''),
            )
            ocean_config.routes.append(route_config)
        
        self._log("=" * 60)
        self._log("测试策略模块")
        self._log("=" * 60)
        
        # 创建策略
        strategy = OceanMultiRouteStrategy(ocean_config)
        self._log("✓ OceanMultiRouteStrategy 创建成功")
        self._log(f"✓ 航线数量: {len(strategy.ocean_config.routes)}")
        
        # 设置日志回调
        def log_callback(msg):
            self._log(f"[策略] {msg}")
        
        strategy.set_log_callback(log_callback)
        
        self._log("=" * 60)
        self._log("策略模块测试通过！")
        self._log("=" * 60)
        
        QMessageBox.information(self, "成功", "策略模块测试通过！", QMessageBox.Ok)
    
    def _on_clear_log(self):
        """清除日志"""
        if self.log_text:
            self.log_text.clear()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
