# -*- encoding:utf-8 -*-
"""
测试检测区域绘制工具 - 在实际游戏画面上绘制
"""
import os
import cv2
import numpy as np

from Util.voyage.detector import ImageDetector
from Util.voyage.config import load_config


def test_draw_regions():
    """绘制检测区域并保存图片"""
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), 'configs', '赛维-圣地亚哥测试.json5')
    config = load_config(config_path)
    
    if not config:
        print('配置加载失败')
        return
    
    # 读取手动截取的游戏画面
    screenshot_path = os.path.join(os.path.dirname(__file__), 'game_screenshot.png')
    
    if not os.path.exists(screenshot_path):
        print(f'截图文件不存在: {screenshot_path}')
        return
    
    screenshot = cv2.imread(screenshot_path)
    if screenshot is None:
        print(f'无法读取截图文件: {screenshot_path}')
        return
    
    print(f'截图大小: {screenshot.shape[1]}x{screenshot.shape[0]}')
    
    # 创建检测器
    detector = ImageDetector(threshold=config.match_threshold)
    
    # 设置检测区域（使用基准窗口大小 1024x768）
    detector.set_window(
        window_title='',  # 不需要实际窗口
        region_a=config.region_a,
        region_b=config.region_b,
        region_b_delay=config.region_b_delay,
        region_c=config.region_c,
    )
    
    # 绘制检测区域
    result = detector.draw_detection_regions(screenshot)
    
    # 保存结果
    output_path = os.path.join(os.path.dirname(__file__), 'detection_regions_game.png')
    cv2.imwrite(output_path, result)
    
    print()
    print(f'检测区域图片已保存到: {output_path}')
    print()
    print('检测区域配置:')
    print(f'  A类区域: {config.region_a} -> 缩放后: {detector.scaled_region_a}')
    print(f'  B类区域: {config.region_b} -> 缩放后: {detector.scaled_region_b}')
    print(f'  B类delay区域: {config.region_b_delay} -> 缩放后: {detector.scaled_region_b_delay}')
    print(f'  C类区域: {config.region_c} -> 缩放后: {detector.scaled_region_c}')
    print()
    print('颜色说明:')
    print('  白色 - A类区域')
    print('  橙色 - B类区域')
    print('  黄色 - B类delay区域')
    print('  红色 - C类区域')


if __name__ == '__main__':
    test_draw_regions()
