#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图片哈希生成工具
为 imgsA/imgsB/imgsC/imgsD/imgsE/imgsF/imgsG 文件夹里的图片生成 dHash 并保存到配置文件
"""

import os
import json
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, List, Tuple


def calculate_dhash(image_path: str, hash_size: int = 16) -> str:
    """
    计算图片的 dHash（差异哈希）
    
    :param image_path: 图片路径
    :param hash_size: 哈希大小
    :return: 十六进制哈希字符串
    """
    try:
        # 使用 PIL 读取支持中文路径
        pil_img = Image.open(image_path).convert('L')  # 转为灰度
        if pil_img is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 调整大小为 (hash_size + 1, hash_size)
        resized = pil_img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        img = np.array(resized)
        
        # 计算相邻像素的差异
        diff = img[:, 1:] > img[:, :-1]
        
        # 转换为十六进制字符串
        hash_str = ''.join(['{:02x}'.format(int(''.join(['1' if pixel else '0' for pixel in row]), 2)) for row in diff])
        
        return hash_str
    except Exception as e:
        print(f"计算哈希失败 {image_path}: {e}")
        return ""


def scan_image_folders(base_dir: str) -> Dict[str, Dict[str, str]]:
    """
    扫描 imgsA-G 文件夹
    
    :param base_dir: 项目根目录
    :return: 哈希字典 {folder_name: {relative_path: hash_str}}
    """
    result = {}
    
    for folder_name in ['imgsA', 'imgsB', 'imgsC', 'imgsD', 'imgsE', 'imgsF', 'imgsG']:
        folder_path = os.path.join(base_dir, folder_name)
        
        if not os.path.isdir(folder_path):
            print(f"警告: 文件夹不存在 {folder_path}")
            continue
        
        print(f"正在扫描: {folder_name}")
        folder_hashes = {}
        
        # 递归遍历文件夹
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, base_dir)
                    
                    # 计算哈希
                    image_hash = calculate_dhash(full_path)
                    if image_hash:
                        folder_hashes[relative_path] = image_hash
                        print(f"  {relative_path}: {image_hash[:16]}...")
        
        result[folder_name] = folder_hashes
        print(f"  {folder_name} 完成，共 {len(folder_hashes)} 张图片\n")
    
    return result


def save_hashes_to_config(hashes: Dict[str, Dict[str, str]], output_path: str):
    """
    保存哈希到配置文件
    
    :param hashes: 哈希字典
    :param output_path: 输出路径
    """
    # 如果文件已存在，读取并更新
    existing_data = {}
    if os.path.isfile(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"读取现有配置失败: {e}")
    
    # 更新数据
    existing_data['image_hashes'] = hashes
    
    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    
    print(f"哈希已保存到: {output_path}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_config = os.path.join(base_dir, 'detection_config.json5')
    
    print("=" * 60)
    print("图片哈希生成工具")
    print("=" * 60)
    print()
    
    # 扫描并生成哈希
    hashes = scan_image_folders(base_dir)
    
    # 保存到配置
    if hashes:
        total_images = sum(len(v) for v in hashes.values())
        print(f"总处理图片数: {total_images}")
        print()
        
        save_hashes_to_config(hashes, output_config)
    else:
        print("没有找到任何图片！")


if __name__ == '__main__':
    main()
