#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名imgsG文件夹中的中文文件为拼音
"""
import os
import shutil

# imgsG拼音映射
IMGSPINYIN_CHINESE_TO_PINYIN = {
    '世界地图': 'shijieditu',
    '买入': 'mairu',
    '全卖': 'quanmai',
    '前往': 'qianwang',
    '卖出': 'maichu',
    '成交': 'chengjiao',
    '我的货物': 'wodehuowu',
    '抬价': 'taijia',
    '拖航': 'tuohang',
    '招募水手': 'zhaomushuishou',
    '救助': 'jiuzhu',
    '继续航行': 'jixuhangxing',
    '航行中': 'hangxingzhong',
    '请客': 'qingke',
    '遇难回港': 'yunanhuigang'
}

imgsg_path = os.path.join(os.path.dirname(__file__), 'imgsG')

if os.path.isdir(imgsg_path):
    print('重命名 imgsG 文件...')
    
    items = os.listdir(imgsg_path)
    
    for item in items:
        if item.lower().endswith('.png'):
            name_without_ext = os.path.splitext(item)[0]
            
            if name_without_ext in IMGSPINYIN_CHINESE_TO_PINYIN:
                new_name = IMGSPINYIN_CHINESE_TO_PINYIN[name_without_ext] + '.png'
                old_path = os.path.join(imgsg_path, item)
                new_path = os.path.join(imgsg_path, new_name)
                
                if old_path != new_path:
                    print(f'{item} -> {new_name}')
                    shutil.move(old_path, new_path)
    
    print('完成！')
else:
    print('imgsG 文件夹不存在')
