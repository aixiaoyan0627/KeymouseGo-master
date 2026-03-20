#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名imgsF文件夹中的中文子文件夹
"""
import os
import shutil

SEA_PINYIN = {
    '东地中海': 'dongdizhonghai',
    '中南美': 'zhongnanmei',
    '加勒比': 'jialebi',
    '北大西洋': 'beidaxiyang',
    '北海': 'beihai',
    '红海': 'honghai',
    '西地中海': 'xidizhonghai',
    '非洲东岸': 'feizhoudongan',
    '非洲西岸': 'feizhouxian'
}

imgsf_path = os.path.join(os.path.dirname(__file__), 'imgsF')

if os.path.isdir(imgsf_path):
    print('重命名 imgsF 子文件夹...')
    
    items = os.listdir(imgsf_path)
    
    for item in items:
        item_path = os.path.join(imgsf_path, item)
        
        if os.path.isdir(item_path) and item in SEA_PINYIN:
            new_name = SEA_PINYIN[item]
            new_path = os.path.join(imgsf_path, new_name)
            
            if item_path != new_path:
                print(f'{item} -> {new_name}')
                shutil.move(item_path, new_path)
    
    print('完成！')
else:
    print('imgsF 文件夹不存在')
