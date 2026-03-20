# -*- encoding:utf-8 -*-
"""
航行模块：负责游戏航行自动化检测与脚本执行

模块结构：
- config.py: 航行配置数据类
- detector.py: 图像检测器
- action_executor.py: 动作执行器（点击、双击等）
- death_detector.py: 死亡检测器
- strategies.py: 策略接口和具体策略实现
- state_machine_v2.py: 新架构状态机（推荐使用）
- state_machine.py: 旧版状态机（保留兼容）
- executor.py: 脚本执行器
"""

from .config import (
    DetectionConfig,
    DeathConfig,
    IconRule,
    load_config,
    list_sea_city_from_imgsc,
    get_c_image_path,
    OceanCityConfig,
    OceanRouteConfig,
    OceanV2Config,
    OceanCityV3Config,
    OceanV3Config,
    OceanCityV3LiuxingConfig,
    OceanV3LiuxingConfig,
)
from .enhanced_script import (
    EnhancedScript,
    EnhancedStep,
    StepType,
    EnhancedScriptExecutor,
)
from .detector import ImageDetector, get_sea_name_from_path, get_all_c_images
from .action_executor import ActionExecutor
from .death_detector import DeathDetector
from .strategies import (
    IVoyageStrategy,
    StrategyContext,
    BaseStrategy,
    OceanStrategy,
    OceanMultiRouteStrategy,
)
from .strategy_v3 import (
    OceanV3Strategy,
    OceanV3StrategyContext,
)
from .strategy_v3_liuxing import (
    OceanV3LiuxingStrategy,
    OceanV3LiuxingStrategyContext,
)
try:
    from .ui_ocean_v2 import OceanV2Panel
except ImportError:
    OceanV2Panel = None
try:
    from .ui_ocean_v3 import OceanV3Panel
except ImportError:
    OceanV3Panel = None
try:
    from .ui_ocean_v3_liuxing import OceanV3LiuxingPanel
except ImportError:
    OceanV3LiuxingPanel = None
from .state_machine_v2 import VoyageStateMachine as VoyageStateMachineV2, VoyageState
from .state_machine import VoyageStateMachine
from .executor import ScriptExecutor

__all__ = [
    'DetectionConfig',
    'DeathConfig',
    'IconRule',
    'load_config',
    'list_sea_city_from_imgsc',
    'get_c_image_path',
    'OceanCityConfig',
    'OceanRouteConfig',
    'OceanV2Config',
    'OceanCityV3Config',
    'OceanV3Config',
    'OceanCityV3LiuxingConfig',
    'OceanV3LiuxingConfig',
    'EnhancedScript',
    'EnhancedStep',
    'StepType',
    'EnhancedScriptExecutor',
    'ImageDetector',
    'get_sea_name_from_path',
    'get_all_c_images',
    'ActionExecutor',
    'DeathDetector',
    'IVoyageStrategy',
    'StrategyContext',
    'BaseStrategy',
    'OceanStrategy',
    'OceanMultiRouteStrategy',
    'OceanV3Strategy',
    'OceanV3StrategyContext',
    'OceanV3LiuxingStrategy',
    'OceanV3LiuxingStrategyContext',
    'VoyageStateMachineV2',
    'VoyageState',
    'VoyageStateMachine',
    'ScriptExecutor',
]

if OceanV2Panel is not None:
    __all__.append('OceanV2Panel')
if OceanV3Panel is not None:
    __all__.append('OceanV3Panel')
if OceanV3LiuxingPanel is not None:
    __all__.append('OceanV3LiuxingPanel')
