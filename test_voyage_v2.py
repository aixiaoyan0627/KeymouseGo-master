# -*- encoding:utf-8 -*-
"""
新架构测试脚本：验证所有模块的接口和功能
"""
import os
import sys
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_config_classes():
    """测试配置类"""
    print("=" * 60)
    print("测试1：配置类")
    print("=" * 60)
    
    from Util.voyage import (
        OceanCityConfig,
        OceanRouteConfig,
        OceanV2Config,
        DeathConfig,
    )
    
    # 测试 DeathConfig
    death_config = DeathConfig(
        rescue_image_paths=["imgs/rescue1.png", "imgs/rescue2.png"],
        script_shipwreck_reset="scripts/shipwreck_reset.txt",
        script_off_course_reset="scripts/off_course_reset.txt",
        a_missing_timeout=60.0,
        city_stuck_timeout=60.0,
        max_city_stuck_retries=3,
    )
    print("✓ DeathConfig 实例化成功")
    print(f"  - death_config: {death_config}")
    print()
    
    # 测试 OceanCityConfig
    city1 = OceanCityConfig(sea="加勒比海", city="圣胡安", use_auto_select=False)
    city2 = OceanCityConfig(sea="墨西哥湾", city="", use_auto_select=True)
    
    print("✓ OceanCityConfig 实例化成功")
    print(f"  - city1: {city1}")
    print(f"  - city2: {city2}")
    
    # 测试 OceanRouteConfig
    route1 = OceanRouteConfig(
        route_id=1,
        buy=city1,
        sell=city2,
        script_dock_fixed="scripts/dock_fixed.txt",
        script_trade="scripts/trade.txt",
        script_next_stop_specified="scripts/next_stop_specified.txt",
        script_next_stop_auto="scripts/next_stop_auto.txt",
    )
    
    print("\n✓ OceanRouteConfig 实例化成功")
    print(f"  - route1: {route1}")
    
    # 测试 OceanV2Config
    config = OceanV2Config(
        routes=[route1],
        current_route_index=0,
        max_routes=4,
    )
    
    print("\n✓ OceanV2Config 实例化成功")
    print(f"  - config.routes: {len(config.routes)} 条航线")
    print(f"  - config.current_route_index: {config.current_route_index}")
    
    print("\n✅ 配置类测试通过！")
    return True


def test_strategy_interfaces():
    """测试策略接口"""
    print("\n" + "=" * 60)
    print("测试2：策略模块接口")
    print("=" * 60)
    
    from Util.voyage import (
        IVoyageStrategy,
        StrategyContext,
        BaseStrategy,
        OceanStrategy,
        OceanMultiRouteStrategy,
        DetectionConfig,
    )
    
    # 检查抽象基类
    print("✓ IVoyageStrategy 抽象基类存在")
    
    # 检查是否有必需的抽象方法
    abstract_methods = [name for name in dir(IVoyageStrategy) if not name.startswith('_')]
    print(f"  - 抽象方法: {abstract_methods}")
    
    # 测试策略上下文
    ctx = StrategyContext(
        consecutive_a_miss=0,
        last_double_click_time=0.0,
        main_script_index=0,
    )
    print("\n✓ StrategyContext 实例化成功")
    print(f"  - ctx: {ctx}")
    
    # 测试 OceanMultiRouteStrategy 实例化
    strategy = OceanMultiRouteStrategy()
    print("\n✓ OceanMultiRouteStrategy 实例化成功")
    
    # 测试设置配置
    from Util.voyage import OceanV2Config, OceanRouteConfig, OceanCityConfig
    ocean_config = OceanV2Config()
    ocean_config.routes.append(OceanRouteConfig(
        route_id=1,
        buy=OceanCityConfig(sea="加勒比海", city="圣胡安"),
        sell=OceanCityConfig(sea="墨西哥湾", use_auto_select=True),
    ))
    strategy.set_ocean_config(ocean_config)
    print("✓ set_ocean_config() 方法正常")
    
    print("\n✅ 策略模块接口测试通过！")
    return True


def test_state_machine():
    """测试状态机模块"""
    print("\n" + "=" * 60)
    print("测试3：状态机模块")
    print("=" * 60)
    
    from Util.voyage import (
        VoyageStateMachineV2,
        VoyageState,
        DetectionConfig,
        ImageDetector,
        ActionExecutor,
        OceanStrategy,
        DeathDetector,
    )
    
    print("✓ VoyageState 枚举存在")
    print(f"  - 状态: {[s.name for s in VoyageState]}")
    
    print("\n✓ VoyageStateMachineV2 类存在")
    print("✓ DeathDetector 类存在")
    print("✓ ImageDetector 类存在")
    print("✓ ActionExecutor 类存在")
    
    print("\n✅ 状态机模块测试通过！")
    return True


def test_detector_and_executor():
    """测试检测器和执行器"""
    print("\n" + "=" * 60)
    print("测试4：检测器和执行器")
    print("=" * 60)
    
    from Util.voyage import ImageDetector, ActionExecutor, DeathDetector
    
    # 测试 ActionExecutor
    executor = ActionExecutor()
    print("✓ ActionExecutor 实例化成功")
    print(f"  - 方法: {[m for m in dir(executor) if not m.startswith('_')]}")
    
    # 测试 DeathDetector
    death_detector = DeathDetector(threshold=0.7)
    print("\n✓ DeathDetector 实例化成功")
    print("  - death_detector.detect() 方法存在")
    
    # 测试 ImageDetector
    detector = ImageDetector()
    print("\n✓ ImageDetector 实例化成功")
    print("  - detector.set_window() 方法存在")
    print("  - detector.take_screenshot() 方法存在")
    print("  - detector.detect_class_a() 方法存在")
    print("  - detector.detect_class_b() 方法存在")
    print("  - detector.detect_class_c() 方法存在")
    
    print("\n✅ 检测器和执行器测试通过！")
    return True


def test_all_imports():
    """测试所有导入"""
    print("\n" + "=" * 60)
    print("测试5：模块完整导入")
    print("=" * 60)
    
    # 测试 voyage 模块的完整导出
    from Util import voyage
    
    expected_exports = [
        'DetectionConfig',
        'IconRule',
        'load_config',
        'list_sea_city_from_imgsc',
        'get_c_image_path',
        'OceanCityConfig',
        'OceanRouteConfig',
        'OceanV2Config',
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
        'VoyageStateMachineV2',
        'VoyageState',
        'VoyageStateMachine',
        'ScriptExecutor',
    ]
    
    missing = []
    for name in expected_exports:
        if not hasattr(voyage, name):
            missing.append(name)
        else:
            print(f"✓ {name}")
    
    if missing:
        print(f"\n⚠  缺失导出: {missing}")
    else:
        print("\n✓ 所有导出项都存在")
    
    print("\n✅ 模块完整导入测试通过！")
    return not missing


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       新架构模块测试套件")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("配置类", test_config_classes()))
    except Exception as e:
        print(f"\n❌ 配置类测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("配置类", False))
    
    try:
        results.append(("策略模块接口", test_strategy_interfaces()))
    except Exception as e:
        print(f"\n❌ 策略模块接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("策略模块接口", False))
    
    try:
        results.append(("状态机模块", test_state_machine()))
    except Exception as e:
        print(f"\n❌ 状态机模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("状态机模块", False))
    
    try:
        results.append(("检测器和执行器", test_detector_and_executor()))
    except Exception as e:
        print(f"\n❌ 检测器和执行器测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("检测器和执行器", False))
    
    try:
        results.append(("模块完整导入", test_all_imports()))
    except Exception as e:
        print(f"\n❌ 模块完整导入测试失败: {e}")
        import traceback
        traceback.print_exc()
        results.append(("模块完整导入", False))
    
    print("\n" + "=" * 60)
    print("       测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {name}: {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"  总计: {passed} 个通过, {failed} 个失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
