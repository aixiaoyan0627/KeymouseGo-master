# -*- encoding:utf-8 -*-
import datetime
from typing import List

import json5
import os
import sys
import threading
import platform
import locale
try:
    import Recorder
except ImportError:
    Recorder = None  # 未安装 pyWinhook 时仅禁用录制与热键，界面与图片检测仍可用

from PySide6.QtGui import QTextCursor
from qt_material import list_themes, QtStyleTools
from PySide6.QtCore import *
from PySide6.QtWidgets import (QMainWindow, QApplication, QMessageBox,
    QGroupBox, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLabel, QComboBox, QCheckBox, QFormLayout, QDoubleSpinBox, QTabWidget, QWidget, QRadioButton)
from PySide6.QtMultimedia import QSoundEffect
from loguru import logger

from Event import ScriptEvent, flag_multiplemonitor
from Plugin.Manager import PluginManager
from UIView import Ui_UIView

from KeymouseGo import to_abs_path
from Util.RunScriptClass import RunScriptClass, RunScriptCMDClass, StopFlag
from Util.Global import State
from Util.ClickedLabel import Label
from Util.DetectionLoop import (
    DetectionLoop, DetectionConfig, load_config,
    list_sea_city_from_imgsc, get_c_image_path,
)


os.environ['QT_ENABLE_HIGHDPI_SCALING'] = "1"
# if platform.system() == 'Windows':
#     HOT_KEYS = ['F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
#                 'XButton1', 'XButton2', 'Middle']
# else:
#     HOT_KEYS = ['F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
#                 'Middle']

logger.remove()
if sys.stdout is not None:
    logger.add(sys.stdout, backtrace=True, diagnose=True,
               level='DEBUG')
logger.add(to_abs_path('logs', '{time}.log'), rotation='20MB', backtrace=True, diagnose=True,
           level='INFO')


def get_assets_path(*paths):
    # pyinstaller -F --add-data ./assets;assets KeymouseGo.py
    try:
        root = sys._MEIPASS
    except:
        root = os.getcwd()
    return os.path.join(root, 'assets', *paths)


scripts = []
scripts_map = {'current_index': 0, 'choice_language': '简体中文'}


def get_script_list_from_dir():
    global scripts

    if not os.path.exists(to_abs_path('scripts')):
        os.mkdir(to_abs_path('scripts'))
    scripts = os.listdir(to_abs_path('scripts'))[::-1]
    scripts = list(filter(lambda s: s.endswith('.txt') or s.endswith('.json5'), scripts))


def update_script_map():
    global scripts_map
    
    for (i, item) in enumerate(scripts):
        scripts_map[item] = i

class UIFunc(QMainWindow, Ui_UIView, QtStyleTools):
    updateStateSignal: Signal = Signal(State)

    def __init__(self, app):
        global scripts

        super(UIFunc, self).__init__()

        logger.info('assets root:{0}'.format(get_assets_path()))

        self.setupUi(self)
        # 扩大窗口以容纳两层检测 UI
        self.resize(920, 640)

        self.app = app

        self.state = State(State.IDLE)

        self.config = self.loadconfig()

        self.setFocusPolicy(Qt.NoFocus)

        self.trans = QTranslator(self)
        self.choice_language.addItems(['简体中文', 'English', '繁體中文'])
        self.choice_language.currentTextChanged.connect(self.onchangelang)

        # 获取默认的地区设置
        language = '简体中文' if locale.getdefaultlocale()[0] == 'zh_CN' else 'English'
        self.choice_language.setCurrentText(language)
        self.onchangelang()

        get_script_list_from_dir()
        update_script_map()
        self.scripts = scripts
        self.choice_script.addItems(self.scripts)
        if self.scripts:
            self.choice_script.setCurrentIndex(0)

        PluginManager.reload()

        # Config
        self.choice_theme.addItems(['Default'])
        self.choice_theme.addItems(list_themes())
        # self.choice_theme.addItems(PluginManager.resources_paths)
        self.stimes.setValue(int(self.config.value("Config/LoopTimes")))
        self.mouse_move_interval_ms.setValue(int(self.config.value("Config/Precision")))
        self.choice_theme.setCurrentText(self.config.value("Config/Theme"))
        if self.config.value('Config/Script') is not None and self.config.value('Config/Script') in self.scripts:
            self.choice_script.setCurrentText(self.config.value('Config/Script'))
        self.stimes.valueChanged.connect(self.onconfigchange)
        self.mouse_move_interval_ms.valueChanged.connect(self.onconfigchange)
        if Recorder is not None:
            self.mouse_move_interval_ms.valueChanged.connect(Recorder.set_interval)
        self.choice_theme.currentTextChanged.connect(self.onchangetheme)
        self.choice_script.currentTextChanged.connect(self.onconfigchange)
        self.hotkey_stop.setText(self.config.value("Config/StopHotKey"))
        self.hotkey_start.setText(self.config.value("Config/StartHotKey"))
        self.hotkey_record.setText(self.config.value("Config/RecordHotKey"))

        # 在运行日志窗口下方添加游戏窗口标题和匹配阈值设置
        self.window_config_widget = QWidget(self.centralwidget)
        self.window_config_widget.setGeometry(QRect(10, 440, 631, 60))
        window_config_layout = QHBoxLayout(self.window_config_widget)
        window_config_layout.setContentsMargins(0, 0, 0, 0)
        
        # 远洋模式
        self.label_capture_window = QLabel("游戏窗口标题")
        self.le_capture_window = QLineEdit()
        self.le_capture_window.setPlaceholderText("留空则默认锁定《大航海时代：传说》窗口")
        self.le_capture_window.setMaximumWidth(200)
        # 默认锁定《大航海时代：传说》窗口
        self.le_capture_window.setText("大航海时代：传说")
        
        # 匹配阈值
        self.label_match_threshold = QLabel("匹配阈值")
        self.spin_match_threshold = QDoubleSpinBox()
        self.spin_match_threshold.setRange(0.5, 0.95)
        self.spin_match_threshold.setSingleStep(0.05)
        self.spin_match_threshold.setValue(0.7)
        self.spin_match_threshold.setMaximumWidth(80)
        
        # 将控件添加到布局中
        window_config_layout.addWidget(self.label_capture_window)
        window_config_layout.addWidget(self.le_capture_window)
        window_config_layout.addSpacing(20)
        window_config_layout.addWidget(self.label_match_threshold)
        window_config_layout.addWidget(self.spin_match_threshold)
        window_config_layout.addStretch(1)


        self.onchangetheme()

        self.textlog.textChanged.connect(lambda: self.textlog.moveCursor(QTextCursor.End))

        # For tune playing
        self.player = QSoundEffect()
        self.volumeSlider.setValue(50)
        self.volumeSlider.valueChanged.connect(
            lambda: self.player.setVolume(
                self.volumeSlider.value()/100.0))

        self.record = []

        self.actioncount = 0

        # For better thread control
        self.runthread = None

        self.btrun.clicked.connect(self.OnBtrunButton)
        self.btrecord.clicked.connect(self.OnBtrecordButton)
        self.btpauserecord.clicked.connect(self.OnPauseRecordButton)
        self.bt_open_script_files.clicked.connect(self.OnBtOpenScriptFilesButton)
        self.choice_language.installEventFilter(self)
        self.choice_script.installEventFilter(self)
        self.btrun.installEventFilter(self)
        self.btrecord.installEventFilter(self)
        self.btpauserecord.installEventFilter(self)
        self.bt_open_script_files.installEventFilter(self)

        # 航行检测（默认两层逻辑，无单独开关；配置路径需改时在代码中改）
        self.detection_loop = None
        self.detection_script_holder = []
        self._current_voyage_script_flag = None  # 当前航行脚本的 StopFlag，停止航行时置 True 以中断脚本

        # 跑商：始发地（海域-城市）、到达/未到达脚本；回程地同上；底部 开始航行/停止航行
        self.groupBox_layer2 = QGroupBox(self.centralwidget)
        self.groupBox_layer2.setTitle("跑商")
        # 放在窗口右侧新增区域，避免与左侧热键(370,10,271,151)重叠
        self.groupBox_layer2.setGeometry(650, 10, 270, 620)
        
        # 添加QTabWidget，创建"远洋"和"流行"两个选项卡
        self.tabWidget = QTabWidget(self.groupBox_layer2)
        self.tabWidget.setGeometry(QRect(10, 15, 250, 550))
        
        # 远洋选项卡
        self.tab_ocean = QWidget()
        self.tabWidget.addTab(self.tab_ocean, "远洋")
        flay_ocean = QFormLayout(self.tab_ocean)
        flay_ocean.setContentsMargins(10, 15, 10, 10)
        flay_ocean.setVerticalSpacing(8)
        self.label_start_sea = QLabel("始发地-海域")
        self.cb_start_sea = QComboBox()
        self.cb_start_sea.setMaximumWidth(140)
        self.label_start_city = QLabel("始发地-城市")
        self.cb_start_city = QComboBox()
        self.cb_start_city.setMaximumWidth(140)
        self.label_start_arrived = QLabel("处于始发地")
        self.cb_script_start_arrived = QComboBox()
        self.cb_script_start_arrived.setMaximumWidth(140)
        self.label_start_not_arrived = QLabel("未处于始发地")
        self.cb_script_start_not_arrived = QComboBox()
        self.cb_script_start_not_arrived.setMaximumWidth(140)
        
        # 中转地
        self.label_transit_sea = QLabel("中转地-海域")
        self.cb_transit_sea = QComboBox()
        self.cb_transit_sea.setMaximumWidth(140)
        self.label_transit_city = QLabel("中转地-城市")
        self.cb_transit_city = QComboBox()
        self.cb_transit_city.setMaximumWidth(140)
        self.label_transit_arrived = QLabel("处于中转地")
        self.cb_script_transit_arrived = QComboBox()
        self.cb_script_transit_arrived.setMaximumWidth(140)
        self.label_transit_not_arrived = QLabel("未处于中转地")
        self.cb_script_transit_not_arrived = QComboBox()
        self.cb_script_transit_not_arrived.setMaximumWidth(140)
        
        self.label_back_sea = QLabel("回程地-海域")
        self.cb_back_sea = QComboBox()
        self.cb_back_sea.setMaximumWidth(140)
        self.label_back_city = QLabel("回程地-城市")
        self.cb_back_city = QComboBox()
        self.cb_back_city.setMaximumWidth(140)
        self.label_back_arrived = QLabel("处于回程地")
        self.cb_script_back_arrived = QComboBox()
        self.cb_script_back_arrived.setMaximumWidth(140)
        self.label_back_not_arrived = QLabel("未处于回程地")
        self.cb_script_back_not_arrived = QComboBox()
        self.cb_script_back_not_arrived.setMaximumWidth(140)
        
        flay_ocean.addRow(self.label_start_sea, self.cb_start_sea)
        flay_ocean.addRow(self.label_start_city, self.cb_start_city)
        flay_ocean.addRow(self.label_start_arrived, self.cb_script_start_arrived)
        flay_ocean.addRow(self.label_start_not_arrived, self.cb_script_start_not_arrived)
        
        # 增加板块空隙
        spacer = QWidget()
        spacer.setFixedHeight(3)
        flay_ocean.addRow(spacer)
        
        flay_ocean.addRow(self.label_transit_sea, self.cb_transit_sea)
        flay_ocean.addRow(self.label_transit_city, self.cb_transit_city)
        flay_ocean.addRow(self.label_transit_arrived, self.cb_script_transit_arrived)
        flay_ocean.addRow(self.label_transit_not_arrived, self.cb_script_transit_not_arrived)
        
        # 增加板块空隙
        spacer2 = QWidget()
        spacer2.setFixedHeight(5)
        flay_ocean.addRow(spacer2)
        
        flay_ocean.addRow(self.label_back_sea, self.cb_back_sea)
        flay_ocean.addRow(self.label_back_city, self.cb_back_city)
        flay_ocean.addRow(self.label_back_arrived, self.cb_script_back_arrived)
        flay_ocean.addRow(self.label_back_not_arrived, self.cb_script_back_not_arrived)
        
        # 增加板块空隙
        spacer3 = QWidget()
        spacer3.setFixedHeight(5)
        flay_ocean.addRow(spacer3)
        self._sea_city_map = {}
        self._fill_sea_city()
        self.cb_start_sea.currentTextChanged.connect(lambda: self._on_sea_changed(True))
        self.cb_transit_sea.currentTextChanged.connect(lambda: self._on_sea_changed('transit'))
        self.cb_back_sea.currentTextChanged.connect(lambda: self._on_sea_changed(False))
        for cb in (self.cb_script_start_arrived, self.cb_script_start_not_arrived,
                   self.cb_script_transit_arrived, self.cb_script_transit_not_arrived,
                   self.cb_script_back_arrived, self.cb_script_back_not_arrived):
            cb.addItem("")  # 添加空选项
            cb.addItems(self.scripts)
            cb.setCurrentIndex(0)  # 选中空选项
        
        # 流行选项卡
        self.tab_popular = QWidget()
        self.tabWidget.addTab(self.tab_popular, "流行")
        flay_popular = QFormLayout(self.tab_popular)
        flay_popular.setContentsMargins(10, 15, 10, 10)
        flay_popular.setVerticalSpacing(8)
        
        # 流行模式：运行模式选择
        self.label_popular_mode = QLabel("运行模式")
        self.popular_mode_group = QWidget()
        popular_mode_layout = QHBoxLayout(self.popular_mode_group)
        popular_mode_layout.setContentsMargins(0, 0, 0, 0)
        
        self.rb_single_mode = QRadioButton("单线跑商")
        self.rb_cycle_mode = QRadioButton("搓搓跑商")
        self.rb_single_mode.setChecked(True)
        
        # 连接信号
        self.rb_single_mode.toggled.connect(self._on_popular_mode_changed)
        self.rb_cycle_mode.toggled.connect(self._on_popular_mode_changed)
        
        popular_mode_layout.addWidget(self.rb_single_mode)
        popular_mode_layout.addWidget(self.rb_cycle_mode)
        flay_popular.addRow(self.label_popular_mode, self.popular_mode_group)
        
        # 流行模式：城市1-4，每个城市可选海域、城市、脚本
        self.popular_city_sea_combos = []
        self.popular_city_city_combos = []
        self.popular_city_script_combos = []
        # 搓搓跑商：城市1的多个脚本
        self.popular_main_city_script_combos = []
        
        # 获取所有海域列表和城市数据
        imgs_c = to_abs_path('imgsC')
        sea_list = []
        city_data_by_sea = {}
        
        if os.path.isdir(imgs_c):
            for sea in os.listdir(imgs_c):
                sea_dir = os.path.join(imgs_c, sea)
                if os.path.isdir(sea_dir):
                    sea_list.append(sea)
                    city_data_by_sea[sea] = []
                    for f in os.listdir(sea_dir):
                        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                            city_name = os.path.splitext(f)[0]
                            city_data_by_sea[sea].append(city_name)
        
        # 城市1（主城市）
        i = 1
        # 海域选择
        sea_label = QLabel(f"城市{i}海域")
        sea_combo = QComboBox()
        sea_combo.setMaximumWidth(140)
        sea_combo.addItem("")
        sea_combo.addItems(sea_list)
        flay_popular.addRow(sea_label, sea_combo)
        self.popular_city_sea_combos.append(sea_combo)
        
        # 城市选择
        city_label = QLabel(f"城市{i}城市")
        city_combo = QComboBox()
        city_combo.setMaximumWidth(140)
        city_combo.addItem("")
        flay_popular.addRow(city_label, city_combo)
        self.popular_city_city_combos.append(city_combo)
        
        # 单线跑商模式：城市1单个脚本
        script_label = QLabel(f"城市{i}脚本（单线）")
        script_combo = QComboBox()
        script_combo.setMaximumWidth(140)
        script_combo.addItem("")  # 添加空选项
        script_combo.addItems(self.scripts)
        script_combo.setCurrentIndex(0)  # 选中空选项
        flay_popular.addRow(script_label, script_combo)
        self.popular_city_script_combos.append(script_combo)
        
        # 增加板块空隙
        spacer = QWidget()
        spacer.setFixedHeight(3)
        flay_popular.addRow(spacer)
        
        # 搓搓跑商模式：城市1多个脚本（3个脚本，对应A-B, A-C, A-D）
        for j in range(1, 4):
            main_script_label = QLabel(f"城市{i}脚本{j}（搓搓）")
            main_script_combo = QComboBox()
            main_script_combo.setMaximumWidth(140)
            main_script_combo.addItem("")  # 添加空选项
            main_script_combo.addItems(self.scripts)
            main_script_combo.setCurrentIndex(0)  # 选中空选项
            flay_popular.addRow(main_script_label, main_script_combo)
            self.popular_main_city_script_combos.append(main_script_combo)
        
        # 海域选择改变时更新城市列表
        def on_sea_changed(combo_sea, combo_city):
            selected_sea = combo_sea.currentText()
            combo_city.clear()
            combo_city.addItem("")
            if selected_sea and selected_sea in city_data_by_sea:
                combo_city.addItems(city_data_by_sea[selected_sea])
        
        sea_combo.currentTextChanged.connect(lambda text, sc=sea_combo, cc=city_combo: on_sea_changed(sc, cc))
        
        # 城市2-4（副城市）
        for i in range(2, 5):
            # 增加板块空隙
            spacer = QWidget()
            spacer.setFixedHeight(2)
            flay_popular.addRow(spacer)
            # 海域选择
            sea_label = QLabel(f"城市{i}海域")
            sea_combo = QComboBox()
            sea_combo.setMaximumWidth(140)
            sea_combo.addItem("")
            sea_combo.addItems(sea_list)
            flay_popular.addRow(sea_label, sea_combo)
            self.popular_city_sea_combos.append(sea_combo)
            
            # 城市选择
            city_label = QLabel(f"城市{i}城市")
            city_combo = QComboBox()
            city_combo.setMaximumWidth(140)
            city_combo.addItem("")
            flay_popular.addRow(city_label, city_combo)
            self.popular_city_city_combos.append(city_combo)
            
            # 脚本选择
            script_label = QLabel(f"城市{i}脚本")
            script_combo = QComboBox()
            script_combo.setMaximumWidth(140)
            script_combo.addItem("")  # 添加空选项
            script_combo.addItems(self.scripts)
            script_combo.setCurrentIndex(0)  # 选中空选项
            flay_popular.addRow(script_label, script_combo)
            self.popular_city_script_combos.append(script_combo)
            
            # 海域选择改变时更新城市列表
            sea_combo.currentTextChanged.connect(lambda text, sc=sea_combo, cc=city_combo: on_sea_changed(sc, cc))
        

        
        # 海事选项卡
        self.tab_maritime = QWidget()
        self.tabWidget.addTab(self.tab_maritime, "海事")
        flay_maritime = QFormLayout(self.tab_maritime)
        flay_maritime.setContentsMargins(10, 15, 10, 10)
        flay_maritime.setVerticalSpacing(8)
        
        # 城市选择
        self.label_maritime_city = QLabel("城市")
        self.cb_maritime_city = QComboBox()
        self.cb_maritime_city.setMaximumWidth(140)
        self.cb_maritime_city.addItem("")
        # 这里可以添加城市列表，暂时使用一些示例城市
        self.cb_maritime_city.addItems(["里斯本", "伦敦", "阿姆斯特丹", "威尼斯", "亚历山大"])
        flay_maritime.addRow(self.label_maritime_city, self.cb_maritime_city)
        
        # 任务列表容器
        self.maritime_tasks_widget = QWidget()
        self.maritime_tasks_layout = QVBoxLayout(self.maritime_tasks_widget)
        self.maritime_tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.maritime_tasks_layout.setSpacing(5)
        
        # 初始隐藏任务列表
        self.maritime_tasks_widget.setVisible(False)
        flay_maritime.addRow(self.maritime_tasks_widget)
        
        # 连接城市选择信号
        self.cb_maritime_city.currentTextChanged.connect(self._on_maritime_city_changed)
        
        # 添加保存和加载配置按钮
        self.bt_save_config = QPushButton("保存配置")
        self.bt_load_config = QPushButton("加载配置")
        
        # 添加体力监测和高效监测按钮
        self.bt_stamina_monitor = QPushButton("体力监测")
        self.bt_efficiency_monitor = QPushButton("高效监测")
        
        # 添加开始航行和停止航行按钮
        self.bt_voyage_start = QPushButton("开始航行")
        self.bt_voyage_stop = QPushButton("停止航行")
        self.bt_voyage_stop.setEnabled(False)
        
        # 设置按钮大小
        self.bt_save_config.setMinimumWidth(100)
        self.bt_load_config.setMinimumWidth(100)
        self.bt_stamina_monitor.setMinimumWidth(100)
        self.bt_efficiency_monitor.setMinimumWidth(100)
        self.bt_voyage_start.setMinimumWidth(100)
        self.bt_voyage_stop.setMinimumWidth(100)
        
        # 创建按钮容器并设置布局
        button_widget = QWidget(self.groupBox_layer2)
        button_widget.setGeometry(QRect(10, 550, 250, 60))
        button_layout = QVBoxLayout(button_widget)
        
        # 顶部按钮容器（用于切换保存/加载或体力/高效监测）
        self.top_buttons_container = QWidget()
        self.top_buttons_layout = QHBoxLayout(self.top_buttons_container)
        self.top_buttons_layout.setContentsMargins(0, 0, 0, 5)
        self.top_buttons_layout.setSpacing(8)
        
        # 添加保存/加载按钮
        self.top_buttons_layout.addWidget(self.bt_save_config)
        self.top_buttons_layout.addWidget(self.bt_load_config)
        
        # 添加体力监测和高效监测按钮（初始隐藏）
        self.bt_stamina_monitor.hide()
        self.bt_efficiency_monitor.hide()
        
        button_layout.addWidget(self.top_buttons_container)
        
        # 开始/停止按钮行
        start_stop_layout = QHBoxLayout()
        start_stop_layout.addWidget(self.bt_voyage_start)
        start_stop_layout.addWidget(self.bt_voyage_stop)
        start_stop_layout.setContentsMargins(0, 0, 0, 5)
        start_stop_layout.setSpacing(8)
        button_layout.addLayout(start_stop_layout)
        
        button_layout.setContentsMargins(0, 5, 0, 0)
        button_layout.setSpacing(5)
        
        # 连接选项卡切换信号
        self.tabWidget.currentChanged.connect(self._on_tab_changed)
        
        self.bt_voyage_start.clicked.connect(self.on_voyage_start)
        self.bt_voyage_stop.clicked.connect(self.on_voyage_stop)
        self.bt_save_config.clicked.connect(self.on_save_config)
        self.bt_load_config.clicked.connect(self.on_load_config)

        if Recorder is None:
            self.keys_pool = []
            self.hotkey_set_btn = None
            self.btrecord.setEnabled(False)
            self.btpauserecord.setEnabled(False)
            self.hotkey_start.setEnabled(False)
            self.hotkey_record.setEnabled(False)
            self.hotkey_stop.setEnabled(False)
            tip = "需要安装 pyWinhook 才能使用录制与热键"
            self.btrecord.setToolTip(tip)
            self.hotkey_start.setToolTip(tip)
            self.hotkey_record.setToolTip(tip)
            self.hotkey_stop.setToolTip(tip)
        else:
            # 组合键缓冲池，[ctrl,shift,alt,cmd/start/win]可用作组合键，但不能单独用作启动热键
            self.keys_pool: List[str] = []
            self.hotkey_set_btn = None
            self.hotkey_stop.clicked.connect(lambda: self.OnHotkeyButton(self.hotkey_stop))
            self.hotkey_start.clicked.connect(lambda: self.OnHotkeyButton(self.hotkey_start))
            self.hotkey_record.clicked.connect(lambda: self.OnHotkeyButton(self.hotkey_record))

            # 热键引发状态转移
            def check_hotkeys(key_name):
                if key_name in Recorder.globals.key_combination_trigger:
                    if self.state == State.SETTING_HOT_KEYS:
                        self.hotkey_set_btn.setText('+'.join(self.keys_pool))
                    return False
                key_name = '+'.join([*self.keys_pool, key_name])

                if self.state == State.SETTING_HOT_KEYS:
                    for btn in [self.hotkey_start, self.hotkey_record, self.hotkey_stop]:
                        if btn is not self.hotkey_set_btn and btn.text() != '' and btn.text() == key_name:
                            self.keys_pool.clear()
                            self.hotkey_set_btn.setText('')
                            self.update_state(State.IDLE)
                            return False
                    self.hotkey_set_btn.setText(key_name)
                    self.update_state(State.IDLE)
                    self.onconfigchange()
                    return False

                start_name = self.hotkey_start.text()
                stop_name = self.hotkey_stop.text()
                record_name = self.hotkey_record.text()

                if key_name == start_name:
                    if self.state == State.IDLE:
                        logger.debug('{0} host start'.format(key_name))
                        self.OnBtrunButton()
                    elif self.state == State.RUNNING:
                        logger.info('Script pause')
                        logger.debug('{0} host pause'.format(key_name))
                        self.runthread.set_pause()
                        self.update_state(State.PAUSE_RUNNING)
                    elif self.state == State.PAUSE_RUNNING:
                        logger.info('Script resume')
                        self.runthread.resume()
                        logger.debug('{0} host resume'.format(key_name))
                        self.update_state(State.RUNNING)
                elif key_name == stop_name:
                    if self.state == State.RUNNING or self.state == State.PAUSE_RUNNING:
                        logger.info('Script stop')
                        self.tnumrd.setText('broken')
                        self.runthread.resume()
                        logger.debug('{0} host stop'.format(key_name))
                        self.update_state(State.IDLE)
                    elif self.state == State.RECORDING or self.state == State.PAUSE_RECORDING:
                        self.recordMethod()
                        logger.info('Record stop')
                        logger.debug('{0} host stop record'.format(key_name))
                elif key_name == record_name:
                    if self.state == State.RECORDING:
                        self.pauseRecordMethod()
                        logger.debug('{0} host pause record'.format(key_name))
                    elif self.state == State.PAUSE_RECORDING:
                        self.pauseRecordMethod()
                        logger.debug('{0} host resume record'.format(key_name))
                    elif self.state == State.IDLE:
                        self.recordMethod()
                        logger.debug('{0} host start record'.format(key_name))
                # 添加F11和F12作为开始和停止航行的快捷键
                elif key_name == 'f11':
                    # F11: 开始航行
                    if self.state == State.IDLE:
                        self.on_voyage_start()
                elif key_name == 'f12':
                    # F12: 停止航行
                    if self.detection_loop is not None:
                        self.on_voyage_stop()
                return key_name in [start_name, stop_name, record_name, 'f11', 'f12']

            @Slot(ScriptEvent)
            def on_record_event(event: ScriptEvent):
                # 判断mouse热键
                if event.event_type == "EM":
                    name = event.action_type
                    if 'mouse x1 down' == name and check_hotkeys('xbutton1'):
                        return
                    elif 'mouse x2 down' == name and check_hotkeys('xbutton2'):
                        return
                    elif 'mouse middle down' == name and check_hotkeys('middle'):
                        return
                else:
                    key_name = event.action[1].lower()
                    if event.action_type == 'key down':
                        if key_name in Recorder.globals.key_combination_trigger and len(self.keys_pool) < 3 and key_name not in self.keys_pool:
                            self.keys_pool.append(key_name)
                        check_hotkeys(key_name)
                    elif event.action_type == 'key up':
                        if key_name in Recorder.globals.key_combination_trigger and key_name in self.keys_pool:
                            self.keys_pool.remove(key_name)
                            check_hotkeys(key_name)
                    for btn in [self.hotkey_start, self.hotkey_record, self.hotkey_stop]:
                        if key_name == btn.text():
                            return
                if self.state == State.RECORDING:
                    if event.event_type == 'EM' and not flag_multiplemonitor:
                        # 检查是否是相对于游戏窗口的坐标
                        if len(event.action) >= 3 and event.action[2] == 'relative_to_window':
                            # 保留相对坐标格式
                            pass
                        else:
                            tx, ty = event.action
                            event.action = ['{0}%'.format(tx), '{0}%'.format(ty)]
                    event_dict = event.__dict__
                    event_dict['type'] = 'event'
                    self.record.append(event_dict)
                    self.actioncount = self.actioncount + 1
                    text = '%d actions recorded' % self.actioncount
                    # 只记录非鼠标移动事件，减少日志输出
                    if not (event.event_type == 'EM' and event.action_type == 'mouse move'):
                        logger.debug('Recorded %s' % event)
                        self.textlog.append(str(event))
                    else:
                        # 鼠标移动事件只更新计数器，不记录日志
                        self.tnumrd.setText(text)
            logger.debug('Initialize at thread ' + str(QThread.currentThread()))
            Recorder.setuphook()
            Recorder.set_callback(on_record_event)
            Recorder.set_cursor_pose_change(self.cursor_pos_change)
            Recorder.set_interval(self.mouse_move_interval_ms.value())

    def eventFilter(self, watched, event: QEvent):
        et: QEvent.Type = event.type()
        # print(event, et)
        if et == QEvent.KeyPress or et == QEvent.KeyRelease:
            return True
        return super(UIFunc, self).eventFilter(watched, event)

    def onconfigchange(self):
        self.config.setValue("Config/LoopTimes", self.stimes.value())
        self.config.setValue("Config/Precision", self.mouse_move_interval_ms.value())
        self.config.setValue("Config/Theme", self.choice_theme.currentText())
        self.config.setValue("Config/Script", self.choice_script.currentText())
        self.config.setValue("Config/StartHotKey", self.hotkey_start.text())
        self.config.setValue("Config/StopHotKey", self.hotkey_stop.text())
        self.config.setValue("Config/RecordHotKey", self.hotkey_record.text())

    def onchangelang(self):
        global scripts_map

        if self.choice_language.currentText() == '简体中文':
            self.trans.load(get_assets_path('i18n', 'zh-cn'))
            _app = QApplication.instance()
            _app.installTranslator(self.trans)
            self.retranslateUi(self)
        elif self.choice_language.currentText() == 'English':
            self.trans.load(get_assets_path('i18n', 'en'))
            _app = QApplication.instance()
            _app.installTranslator(self.trans)
            self.retranslateUi(self)
        elif self.choice_language.currentText() == '繁體中文':
            self.trans.load(get_assets_path('i18n', 'zh-tw'))
            _app = QApplication.instance()
            _app.installTranslator(self.trans)
            self.retranslateUi(self)
        self.retranslateUi(self)
        self.hotkey_stop.setText(self.config.value("Config/StopHotKey"))
        self.hotkey_start.setText(self.config.value("Config/StartHotKey"))
        self.hotkey_record.setText(self.config.value("Config/RecordHotKey"))

    def onchangetheme(self):
        theme = self.choice_theme.currentText()
        if theme == 'Default':
            self.apply_stylesheet(self.app, theme='default')
        else:
            self.apply_stylesheet(self.app, theme=theme)
        self.config.setValue("Config/Theme", self.choice_theme.currentText())

    @Slot(str)
    def playtune(self, filename: str):
        self.player.setSource(QUrl.fromLocalFile(get_assets_path('sounds', filename)))
        self.player.play()

    def closeEvent(self, event):
        self.config.sync()
        if self.detection_loop:
            self.detection_loop.stop()
        if Recorder is not None:
            Recorder.dispose()
        if self.state == State.PAUSE_RUNNING:
            self.update_state(State.RUNNING)
        elif self.state == State.PAUSE_RECORDING:
            self.update_state(State.RECORDING)
        if self.runthread:
            self.runthread.resume()
        event.accept()

    def loadconfig(self):
        if not os.path.exists(to_abs_path('config.ini')):
            with open(to_abs_path('config.ini'), 'w', encoding='utf-8') as f:
                f.write('[Config]\n'
                        'StartHotKey=f6\n'
                        'StopHotKey=f9\n'
                        'RecordHotKey=f10\n'
                        'LoopTimes=1\n'
                        'Precision=200\n'
                        'Language=zh-cn\n'
                        'Theme=Default\n')
        return QSettings(to_abs_path('config.ini'), QSettings.IniFormat)

    def get_script_path(self):
        i = self.choice_script.currentIndex()
        if i < 0:
            return ''
        script = self.scripts[i]
        path = os.path.join(to_abs_path('scripts'), script)
        logger.info('Script path: {0}'.format(path))
        return path

    def new_script_path(self):
        now = datetime.datetime.now()
        script = '%s.json5' % now.strftime('%m%d_%H%M')
        if script in self.scripts:
            script = '%s.json5' % now.strftime('%m%d_%H%M%S')
        self.scripts.insert(0, script)
        update_script_map()
        self.choice_script.clear()
        self.choice_script.addItems(self.scripts)
        self.choice_script.setCurrentIndex(0)
        return self.get_script_path()

    def pauseRecordMethod(self):
        if self.state == State.PAUSE_RECORDING:
            logger.info('Record resume')
            self.btpauserecord.setText(QCoreApplication.translate("UIView", 'Pause', None))
            self.update_state(State.RECORDING)
        elif self.state == State.RECORDING:
            logger.info('Record pause')
            self.btpauserecord.setText(QCoreApplication.translate("UIView", 'Continue', None))
            self.tnumrd.setText('record paused')
            self.update_state(State.PAUSE_RECORDING)

    def OnPauseRecordButton(self):
        self.pauseRecordMethod()

    def OnBtOpenScriptFilesButton(self):
        global scripts_map

        import UIFileDialogFunc

        scripts_map['current_index'] = self.choice_script.currentIndex()
        file_dialog = UIFileDialogFunc.FileDialog()
        self.bt_open_script_files.setDisabled(True)
        self.btrecord.setDisabled(True)
        self.btrun.setDisabled(True)
        self.hotkey_start.setDisabled(True)
        self.hotkey_stop.setDisabled(True)
        self.hotkey_record.setDisabled(True)
        file_dialog.show()
        self.bt_open_script_files.setDisabled(False)
        self.btrecord.setDisabled(False)
        self.btrun.setDisabled(False)
        self.hotkey_start.setEnabled(True)
        self.hotkey_stop.setEnabled(True)
        self.hotkey_record.setEnabled(True)
        # 重新设置的为点击按钮时, 所处的位置
        self.choice_script.clear()
        self.choice_script.addItems(scripts)
        self.choice_script.setCurrentIndex(scripts_map['current_index'])

    def recordMethod(self):
        if self.state == State.RECORDING or self.state == State.PAUSE_RECORDING:
            logger.info('Record stop')
            
            # 秒表方式：结束录制时间 - 开始录制时间 + 4秒预留
            import time
            end_time_ms = int(time.time() * 1000)
            total_duration_ms = end_time_ms - self.record_start_time_ms + 4000
            
            script_path = self.new_script_path()
            with open(script_path, 'w', encoding='utf-8') as f:
                json5.dump({"scripts": self.record, "total_duration_ms": total_duration_ms}, indent=2, ensure_ascii=False, fp=f)
            
            self.btrecord.setText(QCoreApplication.translate("UIView", 'Record', None))
            self.tnumrd.setText('finished')
            self.record = []
            self.actioncount = 0
            self.choice_script.setCurrentIndex(0)
            self.btpauserecord.setText(QCoreApplication.translate("UIView", 'Pause Record', None))
            self.update_state(State.IDLE)
            self._refresh_voyage_script_list()
        elif self.state == State.IDLE:
            logger.info('Record start')
            self.textlog.clear()
            status = self.tnumrd.text()
            if 'running' in status or 'recorded' in status:
                return
            self.btrecord.setText(QCoreApplication.translate("UIView", 'Finish', None))
            self.tnumrd.setText('0 actions recorded')
            self.record = []
            
            # 设置游戏窗口标题，用于录制相对坐标
            try:
                import Recorder
                if hasattr(Recorder, 'set_game_window_title'):
                    window_title = self.le_capture_window.text().strip() or "大航海时代：传说"
                    Recorder.set_game_window_title(window_title)
                if hasattr(Recorder, 'set_use_relative_coords'):
                    Recorder.set_use_relative_coords(True)
            except Exception as e:
                logger.warning('Failed to set game window title for recording: {}', e)
            
            # 秒表方式：记录开始录制时间
            import time
            self.record_start_time_ms = int(time.time() * 1000)
            
            self.update_state(State.RECORDING)

    def OnBtrecordButton(self):
        if self.state == State.RECORDING or self.state == State.PAUSE_RECORDING:
            self.record = self.record[:-2]
        self.recordMethod()

    def OnBtrunButton(self):
        logger.info('Script start')
        self.textlog.clear()
        self.update_state(State.RUNNING)
        
        # 设置游戏窗口标题，用于执行时换算坐标
        try:
            import Event
            if hasattr(Event, 'set_game_window_title'):
                window_title = self.le_capture_window.text().strip() or "大航海时代：传说"
                Event.set_game_window_title(window_title)
            if hasattr(Event, 'set_use_relative_coords'):
                Event.set_use_relative_coords(True)
        except Exception as e:
            logger.warning('Failed to set game window title for execution: {}', e)
        
        if self.runthread:
            self.updateStateSignal.disconnect()
        self.runthread = RunScriptClass(self)
        self.runthread.start()

    def update_state(self, state):
        self.state = state
        if state != State.SETTING_HOT_KEYS or state != State.RECORDING or state != State.PAUSE_RECORDING:
            self.updateStateSignal.emit(self.state)
        if state == State.IDLE:
            self.hotkey_start.setEnabled(True)
            self.hotkey_stop.setEnabled(True)
            self.hotkey_record.setEnabled(True)
            self.btrun.setEnabled(True)
            self.btrecord.setEnabled(True)
            self.btpauserecord.setEnabled(False)
            # 启用跑商界面的按钮
            if hasattr(self, 'bt_voyage_start'):
                self.bt_voyage_start.setEnabled(True)
            if hasattr(self, 'bt_voyage_stop'):
                self.bt_voyage_stop.setEnabled(False)
        elif state == State.RUNNING or state == State.PAUSE_RUNNING or state == State.SETTING_HOT_KEYS:
            self.hotkey_start.setEnabled(False)
            self.hotkey_stop.setEnabled(False)
            self.hotkey_record.setEnabled(False)
            self.btrun.setEnabled(False)
            self.btrecord.setEnabled(False)
            self.btpauserecord.setEnabled(False)
            # 禁用跑商界面的按钮
            if hasattr(self, 'bt_voyage_start'):
                self.bt_voyage_start.setEnabled(False)
        elif state == State.RECORDING or state == State.PAUSE_RECORDING:
            self.hotkey_start.setEnabled(False)
            self.hotkey_stop.setEnabled(False)
            self.hotkey_record.setEnabled(False)
            self.btrun.setEnabled(False)
            self.btrecord.setEnabled(True)
            self.btpauserecord.setEnabled(True)
            # 禁用跑商界面的按钮
            if hasattr(self, 'bt_voyage_start'):
                self.bt_voyage_start.setEnabled(False)

    def OnHotkeyButton(self, btn_obj: QObject):
        self.hotkey_set_btn = btn_obj
        self.update_state(State.SETTING_HOT_KEYS)

    @Slot(bool)
    def handle_runscript_status(self, succeed):
        self.update_state(State.IDLE)

    @Slot(tuple)
    def cursor_pos_change(self, pos):
        self.label_cursor_pos.setText(f'Cursor pos: {pos}')

    def _fill_sea_city(self):
        imgsc = to_abs_path('imgsC')
        self._sea_city_map = list_sea_city_from_imgsc(imgsc)
        seas = [''] + sorted(self._sea_city_map.keys())
        self.cb_start_sea.clear()
        self.cb_start_sea.addItems(seas)
        self.cb_transit_sea.clear()
        self.cb_transit_sea.addItems(seas)
        self.cb_back_sea.clear()
        self.cb_back_sea.addItems(seas)
        self._on_sea_changed(True)
        self._on_sea_changed('transit')
        self._on_sea_changed(False)

    def _on_sea_changed(self, is_start: bool):
        if is_start == 'transit':
            sea = self.cb_transit_sea.currentText()
            cities = [''] + self._sea_city_map.get(sea, [])
            cb = self.cb_transit_city
            cb.clear()
            cb.addItems(cities)
        else:
            sea = self.cb_start_sea.currentText() if is_start else self.cb_back_sea.currentText()
            cities = [''] + self._sea_city_map.get(sea, [])
            cb = self.cb_start_city if is_start else self.cb_back_city
            cb.clear()
            cb.addItems(cities)
        
        # 检查始发地、中转地和回程地是否选择了同一海域
        if hasattr(self, 'cb_start_sea') and hasattr(self, 'cb_back_sea') and hasattr(self, 'cb_transit_sea'):
            start_sea = self.cb_start_sea.currentText()
            transit_sea = self.cb_transit_sea.currentText()
            back_sea = self.cb_back_sea.currentText()
            
            # 检查始发地和回程地
            if start_sea and back_sea and start_sea == back_sea:
                QMessageBox.warning(self, "海域选择错误", "始发地与回程地不可选择同一海域")
                # 重置当前选择的海域
                if is_start is True:
                    self.cb_start_sea.setCurrentIndex(0)
                elif is_start is False:
                    self.cb_back_sea.setCurrentIndex(0)
            
            # 检查始发地和中转地
            if start_sea and transit_sea and start_sea == transit_sea:
                QMessageBox.warning(self, "海域选择错误", "始发地与中转地不可选择同一海域")
                if is_start == 'transit':
                    self.cb_transit_sea.setCurrentIndex(0)
                elif is_start is True:
                    self.cb_start_sea.setCurrentIndex(0)
            
            # 检查中转地和回程地
            if transit_sea and back_sea and transit_sea == back_sea:
                QMessageBox.warning(self, "海域选择错误", "中转地与回程地不可选择同一海域")
                if is_start == 'transit':
                    self.cb_transit_sea.setCurrentIndex(0)
                elif is_start is False:
                    self.cb_back_sea.setCurrentIndex(0)
    
    def _on_popular_mode_changed(self):
        """处理流行模式的运行模式切换"""
        is_single_mode = self.rb_single_mode.isChecked()
        
        # 单线跑时城市1脚本（单线）正常显示，搓搓选项栏变为灰色不可用
        # 搓搓跑时城市1脚本（单线）隐藏，搓搓选项栏正常显示
        
        # 显示/隐藏城市1脚本（单线）
        if hasattr(self, 'popular_city_script_combos') and self.popular_city_script_combos:
            # 城市1脚本（单线）是第一个组合框
            script_combo = self.popular_city_script_combos[0]
            # 找到对应的标签
            layout = script_combo.parent().layout()
            if layout:
                for i in range(layout.rowCount()):
                    item = layout.itemAt(i)
                    if item and item.widget() == script_combo:
                        # 找到标签
                        label_item = layout.itemAtPosition(i, QFormLayout.LabelRole)
                        if label_item:
                            label = label_item.widget()
                            if label:
                                label.setVisible(is_single_mode)
                        script_combo.setVisible(is_single_mode)
        
        # 启用/禁用搓搓跑的脚本选项栏
        if hasattr(self, 'popular_main_city_script_combos'):
            for combo in self.popular_main_city_script_combos:
                # 找到对应的标签
                layout = combo.parent().layout()
                if layout:
                    for i in range(layout.rowCount()):
                        item = layout.itemAt(i)
                        if item and item.widget() == combo:
                            # 找到标签
                            label_item = layout.itemAtPosition(i, QFormLayout.LabelRole)
                            if label_item:
                                label = label_item.widget()
                                if label:
                                    label.setEnabled(not is_single_mode)
                            combo.setEnabled(not is_single_mode)
    
    def _on_maritime_city_changed(self):
        """处理海事模式城市选择变化"""
        selected_city = self.cb_maritime_city.currentText()
        
        # 清空任务列表
        while self.maritime_tasks_layout.count() > 0:
            item = self.maritime_tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if selected_city:
            # 显示任务列表
            self.maritime_tasks_widget.setVisible(True)
            
            # 根据选择的城市添加任务（这里使用示例任务）
            tasks = []
            if selected_city == "里斯本":
                tasks = ["护航任务", "贸易任务", "探索任务", "讨伐任务"]
            elif selected_city == "伦敦":
                tasks = ["护航任务", "贸易任务", "渔业任务", "讨伐任务"]
            elif selected_city == "阿姆斯特丹":
                tasks = ["护航任务", "贸易任务", "造船任务", "讨伐任务"]
            elif selected_city == "威尼斯":
                tasks = ["护航任务", "贸易任务", "艺术任务", "讨伐任务"]
            elif selected_city == "亚历山大":
                tasks = ["护航任务", "贸易任务", "考古任务", "讨伐任务"]
            
            # 添加任务复选框
            for task in tasks:
                checkbox = QCheckBox(task)
                self.maritime_tasks_layout.addWidget(checkbox)
        else:
            # 隐藏任务列表
            self.maritime_tasks_widget.setVisible(False)
    
    def _on_tab_changed(self, index):
        """处理选项卡切换"""
        # 清空顶部按钮布局
        while self.top_buttons_layout.count() > 0:
            item = self.top_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        if index == 2:  # 海事选项卡（索引为2）
            # 显示体力监测和高效监测按钮
            self.top_buttons_layout.addWidget(self.bt_stamina_monitor)
            self.top_buttons_layout.addWidget(self.bt_efficiency_monitor)
            self.bt_stamina_monitor.show()
            self.bt_efficiency_monitor.show()
        else:  # 远洋或流行选项卡
            # 显示保存配置和加载配置按钮
            self.top_buttons_layout.addWidget(self.bt_save_config)
            self.top_buttons_layout.addWidget(self.bt_load_config)
            self.bt_save_config.show()
            self.bt_load_config.show()

    def on_voyage_start(self):
        """开始航行：A 类仅点击；C 类检测始发地海域文件夹内全部城市图、回程地海域文件夹内全部城市图，按匹配结果执行处于/未处于脚本。"""
        # 检查是否有脚本正在执行
        if self.state == State.RUNNING:
            QMessageBox.warning(self, "开始航行", "有脚本正在执行，请先停止脚本后再开始航行。")
            return
        
        # 检查是否正在录制
        if self.state == State.RECORDING or self.state == State.PAUSE_RECORDING:
            QMessageBox.warning(self, "开始航行", "正在录制脚本，请先完成录制后再开始航行。")
            return
        
        # 检查始发地和回程地是否选择了同一海域
        current_tab = self.tabWidget.currentIndex()
        if current_tab == 0:  # 远洋选项卡
            start_sea = self.cb_start_sea.currentText()
            back_sea = self.cb_back_sea.currentText()
            if start_sea and back_sea and start_sea == back_sea:
                QMessageBox.warning(self, "海域选择错误", "始发地与回程地不可选择同一海域")
                return
        
        imgs_a = to_abs_path('imgsA')
        imgs_c = to_abs_path('imgsC')
        imgs_b = to_abs_path('imgsB')
        # A 类仅使用 caofan.png、caofan1.png
        image_a_paths = []
        if os.path.isdir(imgs_a):
            for base in ('caofan', 'caofan1'):
                for ext in ('.png', '.jpg', '.jpeg'):
                    p = os.path.join(imgs_a, base + ext)
                    if os.path.isfile(p):
                        image_a_paths.append(p)
                        break
        # B 类：imgsB 下全部图片，用于「随机出现的按钮」点击
        image_b_paths = []
        if os.path.isdir(imgs_b):
            for f in os.listdir(imgs_b):
                if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_b_paths.append(os.path.join(imgs_b, f))
        
        # 检查当前选中的选项卡
        current_tab = self.tabWidget.currentIndex()
        
        if current_tab == 0:  # 远洋选项卡
            config = self._create_ocean_config(image_a_paths, image_b_paths, imgs_c)
            if config is None:
                return
        elif current_tab == 1:  # 流行选项卡
            config = self._create_popular_config(image_a_paths, image_b_paths, imgs_c)
            if config is None:
                return
        elif current_tab == 2:  # 海事选项卡
            QMessageBox.information(self, "海事功能", "海事功能开发中，敬请期待！")
            return
        else:
            QMessageBox.warning(self, "错误", "未知的选项卡！")
            return
        
        self.detection_loop = DetectionLoop(config)

        def on_trigger_found(script_path: str):
            path = (script_path or '').strip()
            if not path or not os.path.isfile(path):
                self.detection_loop.resume()
                return
            
            # 读取脚本的总时长（如果有）
            total_duration_ms = None
            try:
                with open(path, 'r', encoding='utf8') as f:
                    content = json5.load(f)
                    if 'total_duration_ms' in content:
                        total_duration_ms = content['total_duration_ms']
            except Exception as e:
                logger.warning('Failed to read script duration: {}', e)
            
            self.textlog.append("[航行] 执行脚本: {}".format(os.path.basename(path)))
            self.textlog.append("[航行] 脚本执行中...")
            
            flag = StopFlag(False)
            self._current_voyage_script_flag = flag
            thread = RunScriptCMDClass([path], 1, flag)
            
            def on_script_finished():
                self.textlog.append("[航行] 脚本执行完毕")
                if self.detection_loop is not None:
                    self.detection_loop.resume()
            
            thread.finished.connect(on_script_finished)
            self.detection_script_holder.append(thread)
            thread.start()
            logger.info("Voyage script started: %s", path)
            
            # 如果有总时长信息，记录一下方便调试
            if total_duration_ms is not None:
                logger.info("Script estimated duration: {} ms", total_duration_ms)

        self.detection_loop.trigger_found.connect(on_trigger_found)
        self.detection_loop.log_message.connect(self.textlog.append)
        self.detection_loop.start()
        
        # 禁用左边的录制脚本功能
        self.hotkey_start.setEnabled(False)
        self.hotkey_stop.setEnabled(False)
        self.hotkey_record.setEnabled(False)
        self.btrun.setEnabled(False)
        self.btrecord.setEnabled(False)
        self.btpauserecord.setEnabled(False)
        
        # 启用/禁用跑商界面的按钮
        self.bt_voyage_start.setEnabled(False)
        self.bt_voyage_stop.setEnabled(True)
        self.tnumrd.setText("航行中...")

    def on_voyage_stop(self):
        if not self.detection_loop:
            return
        # 先中断正在执行的航行脚本
        if self._current_voyage_script_flag:
            self._current_voyage_script_flag.value = True
            self._current_voyage_script_flag = None
        loop = self.detection_loop
        self.detection_loop = None
        self.bt_voyage_stop.setEnabled(False)
        self.bt_voyage_start.setEnabled(True)
        self.tnumrd.setText("Ready...")
        loop.stop()
        loop.wait(1000)
        
        # 重新启用左边的录制脚本功能
        self.hotkey_start.setEnabled(True)
        self.hotkey_stop.setEnabled(True)
        self.hotkey_record.setEnabled(True)
        self.btrun.setEnabled(True)
        self.btrecord.setEnabled(True)
        self.btpauserecord.setEnabled(False)
        
        logger.info("Voyage stopped.")

    def _refresh_voyage_script_list(self):
        """录制完成后刷新脚本列表，使新脚本可被航行下拉框选中。"""
        global scripts
        get_script_list_from_dir()
        self.scripts = scripts
        
        # 刷新远洋模式的脚本下拉框
        for cb in (self.cb_script_start_arrived, self.cb_script_start_not_arrived,
                   self.cb_script_transit_arrived, self.cb_script_transit_not_arrived,
                   self.cb_script_back_arrived, self.cb_script_back_not_arrived):
            cur = cb.currentText()
            cb.clear()
            cb.addItem("")  # 添加空选项
            cb.addItems(self.scripts)
            idx = cb.findText(cur)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
        
        # 刷新流行模式的脚本下拉框
        for combo in self.popular_city_script_combos:
            cur = combo.currentText()
            combo.clear()
            combo.addItem("")  # 添加空选项
            combo.addItems(self.scripts)
            idx = combo.findText(cur)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
        
        # 刷新搓搓跑商主城市的多个脚本下拉框
        for combo in self.popular_main_city_script_combos:
            cur = combo.currentText()
            combo.clear()
            combo.addItem("")  # 添加空选项
            combo.addItems(self.scripts)
            idx = combo.findText(cur)
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def on_save_config(self):
        """保存配置到文件"""
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        
        name, ok = QInputDialog.getText(None, "保存配置", "请输入配置名称：")
        if not ok or not name.strip():
            return
        
        config_name = name.strip()
        
        try:
            # 确保configs目录存在
            configs_dir = to_abs_path('configs')
            if not os.path.exists(configs_dir):
                os.makedirs(configs_dir)
            
            config_path = os.path.join(configs_dir, f'{config_name}.json5')
            
            # 收集配置数据
            config_data = {}
            
            # 远洋模式配置
            config_data['tab_type'] = 'ocean'
            config_data['start_sea'] = self.cb_start_sea.currentText()
            config_data['start_city'] = self.cb_start_city.currentText()
            config_data['script_start_arrived'] = self.cb_script_start_arrived.currentText()
            config_data['script_start_not_arrived'] = self.cb_script_start_not_arrived.currentText()
            # 中转地配置
            config_data['transit_sea'] = self.cb_transit_sea.currentText()
            config_data['transit_city'] = self.cb_transit_city.currentText()
            config_data['script_transit_arrived'] = self.cb_script_transit_arrived.currentText()
            config_data['script_transit_not_arrived'] = self.cb_script_transit_not_arrived.currentText()
            config_data['back_sea'] = self.cb_back_sea.currentText()
            config_data['back_city'] = self.cb_back_city.currentText()
            config_data['script_back_arrived'] = self.cb_script_back_arrived.currentText()
            config_data['script_back_not_arrived'] = self.cb_script_back_not_arrived.currentText()
            config_data['capture_window'] = self.le_capture_window.text()
            config_data['match_threshold'] = self.spin_match_threshold.value()
            
            # 流行模式配置
            config_data['popular_mode'] = 'single' if self.rb_single_mode.isChecked() else 'cycle'
            popular_configs = []
            for i in range(4):
                city_config = {}
                city_config['sea'] = self.popular_city_sea_combos[i].currentText()
                city_config['city'] = self.popular_city_city_combos[i].currentText()
                city_config['script'] = self.popular_city_script_combos[i].currentText()
                popular_configs.append(city_config)
            config_data['popular_configs'] = popular_configs
            # 搓搓跑商主城市脚本
            main_city_scripts = []
            for combo in self.popular_main_city_script_combos:
                main_city_scripts.append(combo.currentText())
            config_data['main_city_scripts'] = main_city_scripts
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json5.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.textlog.append(f'[配置] 已保存配置：{config_name}')
            QMessageBox.information(None, '保存成功', f'配置「{config_name}」保存成功！')
            
        except Exception as e:
            logger.error('Save config failed: {}', e)
            QMessageBox.critical(None, '保存失败', f'保存配置时出错：{str(e)}')

    def on_load_config(self):
        """从文件加载配置"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        
        configs_dir = to_abs_path('configs')
        if not os.path.exists(configs_dir):
            os.makedirs(configs_dir)
        
        file_path, _ = QFileDialog.getOpenFileName(
            None, 
            '加载配置', 
            configs_dir, 
            'Config Files (*.json5);;All Files (*)'
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json5.load(f)
            
            # 恢复远洋模式配置
            if 'start_sea' in config_data and config_data['start_sea']:
                idx = self.cb_start_sea.findText(config_data['start_sea'])
                if idx >= 0:
                    self.cb_start_sea.setCurrentIndex(idx)
            
            if 'start_city' in config_data and config_data['start_city']:
                idx = self.cb_start_city.findText(config_data['start_city'])
                if idx >= 0:
                    self.cb_start_city.setCurrentIndex(idx)
            
            if 'script_start_arrived' in config_data and config_data['script_start_arrived']:
                idx = self.cb_script_start_arrived.findText(config_data['script_start_arrived'])
                if idx >= 0:
                    self.cb_script_start_arrived.setCurrentIndex(idx)
            
            if 'script_start_not_arrived' in config_data and config_data['script_start_not_arrived']:
                idx = self.cb_script_start_not_arrived.findText(config_data['script_start_not_arrived'])
                if idx >= 0:
                    self.cb_script_start_not_arrived.setCurrentIndex(idx)
            
            # 恢复中转地配置
            if 'transit_sea' in config_data and config_data['transit_sea']:
                idx = self.cb_transit_sea.findText(config_data['transit_sea'])
                if idx >= 0:
                    self.cb_transit_sea.setCurrentIndex(idx)
            
            if 'transit_city' in config_data and config_data['transit_city']:
                idx = self.cb_transit_city.findText(config_data['transit_city'])
                if idx >= 0:
                    self.cb_transit_city.setCurrentIndex(idx)
            
            if 'script_transit_arrived' in config_data and config_data['script_transit_arrived']:
                idx = self.cb_script_transit_arrived.findText(config_data['script_transit_arrived'])
                if idx >= 0:
                    self.cb_script_transit_arrived.setCurrentIndex(idx)
            
            if 'script_transit_not_arrived' in config_data and config_data['script_transit_not_arrived']:
                idx = self.cb_script_transit_not_arrived.findText(config_data['script_transit_not_arrived'])
                if idx >= 0:
                    self.cb_script_transit_not_arrived.setCurrentIndex(idx)
            
            if 'back_sea' in config_data and config_data['back_sea']:
                idx = self.cb_back_sea.findText(config_data['back_sea'])
                if idx >= 0:
                    self.cb_back_sea.setCurrentIndex(idx)
            
            if 'back_city' in config_data and config_data['back_city']:
                idx = self.cb_back_city.findText(config_data['back_city'])
                if idx >= 0:
                    self.cb_back_city.setCurrentIndex(idx)
            
            if 'script_back_arrived' in config_data and config_data['script_back_arrived']:
                idx = self.cb_script_back_arrived.findText(config_data['script_back_arrived'])
                if idx >= 0:
                    self.cb_script_back_arrived.setCurrentIndex(idx)
            
            if 'script_back_not_arrived' in config_data and config_data['script_back_not_arrived']:
                idx = self.cb_script_back_not_arrived.findText(config_data['script_back_not_arrived'])
                if idx >= 0:
                    self.cb_script_back_not_arrived.setCurrentIndex(idx)
            
            if 'capture_window' in config_data:
                self.le_capture_window.setText(config_data['capture_window'])
            
            if 'match_threshold' in config_data:
                self.spin_match_threshold.setValue(config_data['match_threshold'])
            
            # 恢复流行模式配置
            if 'popular_mode' in config_data:
                if config_data['popular_mode'] == 'single':
                    self.rb_single_mode.setChecked(True)
                else:
                    self.rb_cycle_mode.setChecked(True)
            
            if 'popular_configs' in config_data:
                for i in range(min(4, len(config_data['popular_configs']))):
                    city_config = config_data['popular_configs'][i]
                    if 'sea' in city_config:
                        idx = self.popular_city_sea_combos[i].findText(city_config['sea'])
                        if idx >= 0:
                            self.popular_city_sea_combos[i].setCurrentIndex(idx)
                    if 'city' in city_config:
                        idx = self.popular_city_city_combos[i].findText(city_config['city'])
                        if idx >= 0:
                            self.popular_city_city_combos[i].setCurrentIndex(idx)
                    if 'script' in city_config:
                        idx = self.popular_city_script_combos[i].findText(city_config['script'])
                        if idx >= 0:
                            self.popular_city_script_combos[i].setCurrentIndex(idx)
            
            # 恢复搓搓跑商主城市脚本
            if 'main_city_scripts' in config_data:
                for i in range(min(3, len(config_data['main_city_scripts']))):
                    script_name = config_data['main_city_scripts'][i]
                    idx = self.popular_main_city_script_combos[i].findText(script_name)
                    if idx >= 0:
                        self.popular_main_city_script_combos[i].setCurrentIndex(idx)
            
            config_name = os.path.splitext(os.path.basename(file_path))[0]
            self.textlog.append(f'[配置] 已加载配置：{config_name}')
            QMessageBox.information(None, '加载成功', f'配置「{config_name}」加载成功！')
            
        except Exception as e:
            logger.error('Load config failed: {}', e)
            QMessageBox.critical(None, '加载失败', f'加载配置时出错：{str(e)}')

    def _create_ocean_config(self, image_a_paths, image_b_paths, imgs_c):
        """创建远洋模式配置"""
        sea_s = self.cb_start_sea.currentText()
        city_s = self.cb_start_city.currentText()
        sea_t = self.cb_transit_sea.currentText()
        city_t = self.cb_transit_city.currentText()
        sea_b = self.cb_back_sea.currentText()
        city_b = self.cb_back_city.currentText()
        
        # 始发地海域下全部城市图路径
        c_start_sea_paths = []
        if sea_s:
            sea_dir = os.path.join(imgs_c, sea_s)
            if os.path.isdir(sea_dir):
                for f in os.listdir(sea_dir):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        c_start_sea_paths.append(os.path.join(sea_dir, f))
        
        # 中转地海域下全部城市图路径
        c_transit_sea_paths = []
        if sea_t:
            sea_dir = os.path.join(imgs_c, sea_t)
            if os.path.isdir(sea_dir):
                for f in os.listdir(sea_dir):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        c_transit_sea_paths.append(os.path.join(sea_dir, f))
        
        # 回程地海域下全部城市图路径
        c_back_sea_paths = []
        if sea_b:
            sea_dir = os.path.join(imgs_c, sea_b)
            if os.path.isdir(sea_dir):
                for f in os.listdir(sea_dir):
                    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                        c_back_sea_paths.append(os.path.join(sea_dir, f))
        
        c_start = get_c_image_path(imgs_c, sea_s, city_s)
        c_transit = get_c_image_path(imgs_c, sea_t, city_t)
        c_back = get_c_image_path(imgs_c, sea_b, city_b)
        
        # 检查是否至少有一个配置
        has_config = (
            image_a_paths or 
            (c_start_sea_paths and c_start) or 
            (c_transit_sea_paths and c_transit) or
            (c_back_sea_paths and c_back)
        )
        if not has_config:
            QMessageBox.warning(self, "开始航行", "请至少：在 imgsA 放入 A 类图，或选择始发地/中转地/回程地的海域与城市（imgsC 下需有对应海域文件夹及城市图）。")
            return None
        
        scripts_dir = to_abs_path('scripts')
        
        def path_for(name):
            return os.path.join(scripts_dir, name) if name else ''
        
        s_arr = path_for(self.cb_script_start_arrived.currentText())
        s_not = path_for(self.cb_script_start_not_arrived.currentText())
        t_arr = path_for(self.cb_script_transit_arrived.currentText())
        t_not = path_for(self.cb_script_transit_not_arrived.currentText())
        b_arr = path_for(self.cb_script_back_arrived.currentText())
        b_not = path_for(self.cb_script_back_not_arrived.currentText())
        
        if c_start and (not os.path.isfile(s_arr) or not os.path.isfile(s_not)):
            QMessageBox.warning(self, "开始航行", "始发地需选择有效的「处于始发地」「未处于始发地」脚本。")
            return None
        
        if c_transit and (not os.path.isfile(t_arr) or not os.path.isfile(t_not)):
            QMessageBox.warning(self, "开始航行", "中转地需选择有效的「处于中转地」「未处于中转地」脚本。")
            return None
        
        if c_back and (not os.path.isfile(b_arr) or not os.path.isfile(b_not)):
            QMessageBox.warning(self, "开始航行", "回程地需选择有效的「处于回程地」「未处于回程地」脚本。")
            return None
        
        # 默认锁定《大航海时代：传说》窗口；若用户填了其它标题则优先生效
        window_title = self.le_capture_window.text().strip() or "大航海时代：传说"
        
        # 合并所有指定海域的C类图片
        c_specified_paths = []
        c_specified_paths.extend(c_start_sea_paths)
        c_specified_paths.extend(c_transit_sea_paths)
        c_specified_paths.extend(c_back_sea_paths)
        
        return DetectionConfig(
            image_a_paths=image_a_paths,
            image_b_paths=image_b_paths,
            c_start_sea_paths=c_specified_paths,
            c_transit_sea_paths=c_transit_sea_paths,
            c_back_sea_paths=c_back_sea_paths,
            c_start_path=c_start,
            c_transit_path=c_transit,
            c_back_path=c_back,
            script_start_arrived=s_arr,
            script_start_not_arrived=s_not,
            script_transit_arrived=t_arr,
            script_transit_not_arrived=t_not,
            script_back_arrived=b_arr,
            script_back_not_arrived=b_not,
            imgsc_root_path=imgs_c,
            check_interval=3.0,
            match_threshold=float(self.spin_match_threshold.value()),
            capture_window_title=window_title,
        )

    def _create_popular_config(self, image_a_paths, image_b_paths, imgs_c):
        """创建流行模式配置"""
        # 流行模式：只检测用户指定的城市图片
        c_city_paths = []
        c_city_scripts = []
        scripts_dir = to_abs_path('scripts')
        
        # 获取每个城市对应的脚本和图片
        for i in range(4):
            sea = self.popular_city_sea_combos[i].currentText()
            city = self.popular_city_city_combos[i].currentText()
            script_name = self.popular_city_script_combos[i].currentText()
            
            # 只有当同时指定了海域、城市和脚本时才添加
            if sea and city and script_name:
                # 添加脚本路径
                script_path = os.path.join(scripts_dir, script_name)
                if os.path.isfile(script_path):
                    c_city_scripts.append(script_path)
                else:
                    c_city_scripts.append('')
                
                # 查找城市图片路径（支持多种常见图片格式）
                city_image_full_path = None
                for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
                    test_path = os.path.join(imgs_c, sea, f"{city}{ext}")
                    if os.path.isfile(test_path):
                        city_image_full_path = test_path
                        break
                
                if city_image_full_path:
                    c_city_paths.append(city_image_full_path)
                else:
                    c_city_paths.append('')
            else:
                # 如果未指定完整配置，添加空值
                c_city_scripts.append('')
                c_city_paths.append('')
        
        # 默认锁定《大航海时代：传说》窗口；若用户填了其它标题则优先生效
        window_title = self.le_capture_window.text().strip() or "大航海时代：传说"
        
        # 确定运行模式
        popular_mode = 'single' if self.rb_single_mode.isChecked() else 'cycle'
        
        # 收集搓搓跑商主城市脚本
        main_city_scripts = []
        scripts_dir = to_abs_path('scripts')
        for combo in self.popular_main_city_script_combos:
            script_name = combo.currentText()
            if script_name:
                script_path = os.path.join(scripts_dir, script_name)
                if os.path.isfile(script_path):
                    main_city_scripts.append(script_path)
                else:
                    main_city_scripts.append('')
            else:
                main_city_scripts.append('')
        
        # 创建配置对象，使用流行模式的参数
        return DetectionConfig(
            image_a_paths=image_a_paths,
            image_b_paths=image_b_paths,
            c_start_sea_paths=c_city_paths,  # 用于流行模式的城市检测
            c_back_sea_paths=[],  # 流行模式不需要回程地
            c_start_path='',  # 流行模式不需要特定的始发地
            c_back_path='',  # 流行模式不需要特定的回程地
            script_start_arrived='',  # 流行模式使用c_city_scripts
            script_start_not_arrived='',  # 流行模式使用c_city_scripts
            script_back_arrived='',  # 流行模式不需要
            script_back_not_arrived='',  # 流行模式不需要
            imgsc_root_path=imgs_c,
            check_interval=3.0,
            match_threshold=float(self.spin_match_threshold.value()),
            capture_window_title=window_title,
            # 添加流行模式的城市脚本
            city_scripts=c_city_scripts,
            # 添加搓搓跑商相关配置
            popular_mode=popular_mode,
            main_city_scripts=main_city_scripts,
            main_city_script_index=0
        )
