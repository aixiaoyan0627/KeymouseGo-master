#!/usr/bin/env python3
# -*- encoding:utf-8 -*-
"""
图像识别系统测试脚本
"""
import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from Util.ImageRecognition import (
    take_screenshot,
    find_image_on_screen,
    find_all_images_on_screen,
    get_window_rect_by_title,
)
from Util.voyage.detector import ImageDetector, get_all_c_images

def test_window_detection():
    """测试窗口检测"""
    logger.info("="*50)
    logger.info("测试1: 窗口检测")
    logger.info("="*50)
    
    window_title = "大航海时代：传说"
    logger.info(f"尝试查找窗口: {window_title}")
    
    rect = get_window_rect_by_title(window_title)
    if rect:
        logger.info(f"✓ 找到窗口: {rect}")
        return rect
    else:
        logger.warning("✗ 未找到窗口")
        return None

def test_screenshot(window_rect=None):
    """测试截图功能"""
    logger.info("\n" + "="*50)
    logger.info("测试2: 截图功能")
    logger.info("="*50)
    
    try:
        if window_rect:
            screenshot, offset = take_screenshot(region=window_rect)
            logger.info(f"✓ 区域截图成功: 大小={screenshot.shape}, 偏移={offset}")
        else:
            screenshot, offset = take_screenshot()
            logger.info(f"✓ 全屏截图成功: 大小={screenshot.shape}")
        return screenshot, offset
    except Exception as e:
        logger.error(f"✗ 截图失败: {e}")
        return None, (0, 0)

def test_image_detection(screenshot, offset, window_title=""):
    """测试图像检测"""
    logger.info("\n" + "="*50)
    logger.info("测试3: 图像检测")
    logger.info("="*50)
    
    # 测试imgsC文件夹下的图片
    imgsc_root = os.path.join(os.path.dirname(__file__), "imgsC")
    if not os.path.exists(imgsc_root):
        logger.warning(f"imgsC文件夹不存在: {imgsc_root}")
        return
    
    all_c_paths = get_all_c_images(imgsc_root)
    logger.info(f"找到 {len(all_c_paths)} 张C类图片")
    
    # 创建ImageDetector
    detector = ImageDetector(threshold=0.6)
    
    if window_title:
        success = detector.set_window(window_title)
        logger.info(f"设置窗口: {'成功' if success else '失败'}")
    
    # 测试前10张图片
    test_count = min(10, len(all_c_paths))
    logger.info(f"测试前 {test_count} 张图片...")
    
    found_count = 0
    for i, path in enumerate(all_c_paths[:test_count]):
        logger.info(f"  [{i+1}/{test_count}] 检测: {os.path.basename(path)}")
        
        pos = detector.detect_single(path, screenshot, offset)
        if pos:
            logger.info(f"    ✓ 找到位置: {pos}")
            found_count += 1
        else:
            logger.debug(f"    ✗ 未找到")
    
    logger.info(f"检测完成: 找到 {found_count}/{test_count} 张图片")

def main():
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    logger.info("开始图像识别系统测试")
    logger.info(f"当前目录: {os.getcwd()}")
    
    # 1. 测试窗口检测
    window_rect = test_window_detection()
    window_title = "大航海时代：传说" if window_rect else ""
    
    # 2. 测试截图
    screenshot, offset = test_screenshot(window_rect)
    if screenshot is None:
        logger.error("无法获取截图，测试终止")
        return
    
    # 3. 测试图像检测
    test_image_detection(screenshot, offset, window_title)
    
    logger.info("\n" + "="*50)
    logger.info("测试完成")
    logger.info("="*50)

if __name__ == "__main__":
    main()
