# -*- encoding:utf-8 -*-
"""
准备 YOLO 训练数据
- 复制图片
- 生成类别列表
"""
import os
import shutil
from pathlib import Path
from loguru import logger

# 源目录
SOURCE_DIRS = [
    "imgsA",
    "imgsB/Delay",
    "imgsB/Instant",
]

# 额外添加的图片
EXTRA_IMAGES = [
    "imgsG/shijieditu.png",
]

# 目标目录
TARGET_IMAGES_DIR = "raw_images"
TARGET_LABELS_DIR = "raw_labels"


def main():
    logger.info("=" * 60)
    logger.info("开始准备训练数据")
    logger.info("=" * 60)
    
    # 创建目标目录
    os.makedirs(TARGET_IMAGES_DIR, exist_ok=True)
    os.makedirs(TARGET_LABELS_DIR, exist_ok=True)
    
    class_names = set()
    copied_count = 0
    
    # 复制各个目录的图片
    for source_dir in SOURCE_DIRS:
        if not os.path.exists(source_dir):
            logger.warning(f"目录不存在，跳过: {source_dir}")
            continue
        
        logger.info(f"处理目录: {source_dir}")
        
        for filename in os.listdir(source_dir):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                src_path = os.path.join(source_dir, filename)
                
                # 提取类别名（不带后缀）
                class_name = os.path.splitext(filename)[0]
                class_names.add(class_name)
                
                # 复制图片
                dst_path = os.path.join(TARGET_IMAGES_DIR, filename)
                shutil.copy2(src_path, dst_path)
                copied_count += 1
                logger.debug(f"复制: {filename}")
    
    # 复制额外的图片
    logger.info(f"处理额外图片")
    for img_path in EXTRA_IMAGES:
        if os.path.exists(img_path):
            filename = os.path.basename(img_path)
            
            # 提取类别名
            class_name = os.path.splitext(filename)[0]
            class_names.add(class_name)
            
            # 复制图片
            dst_path = os.path.join(TARGET_IMAGES_DIR, filename)
            shutil.copy2(img_path, dst_path)
            copied_count += 1
            logger.debug(f"复制额外图片: {filename}")
        else:
            logger.warning(f"额外图片不存在，跳过: {img_path}")
    
    # 生成类别列表（排序）
    sorted_classes = sorted(list(class_names))
    
    logger.info("=" * 60)
    logger.info(f"准备完成！")
    logger.info(f"复制图片数量: {copied_count}")
    logger.info(f"类别数量: {len(sorted_classes)}")
    logger.info(f"类别列表: {sorted_classes}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("下一步:")
    logger.info("1. 使用标注工具标注这些图片")
    logger.info("2. 将标注文件 (*.txt) 放到 raw_labels/ 目录")
    logger.info("3. 运行 train_yolo.py 开始训练")
    logger.info("")
    logger.info("类别顺序（用于训练配置）:")
    logger.info(f'class_names = {sorted_classes}')


if __name__ == "__main__":
    main()
