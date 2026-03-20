#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重命名imgsC, imgsE, imgsF文件夹中的中文文件夹和文件为拼音
"""
import os
import shutil

# 海域拼音映射
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

# 城市拼音映射
CITY_PINYIN = {
    '亚历山大': 'yalishanda',
    '伊斯坦布尔': 'yisitanbuer',
    '刻赤': 'kechi',
    '坎迪亚': 'kandia',
    '塞瓦斯托波尔': 'saiwasituobaoer',
    '威尼斯': 'wenisi',
    '安科纳': 'ankena',
    '开罗': 'kailuo',
    '扎达尔': 'zhadaer',
    '拉古萨': 'lagusha',
    '敖德萨': 'aodesa',
    '法马古斯塔': 'famagusita',
    '特拉布宗': 'telabuzong',
    '班加西': 'banjiaxi',
    '的里雅斯特': 'deliyatesite',
    '萨洛尼卡': 'saluonika',
    '贝鲁特': 'beilute',
    '那不勒斯': 'nabulesi',
    '锡拉库萨': 'xilakusa',
    '雅典': 'yadian',
    '雅法': 'yafa',
    '伯南布哥': 'bonanbuge',
    '卡宴': 'kayang',
    '大开曼': 'dakaiman',
    '威廉斯塔德': 'weiliansitade',
    '拉斯加斯': 'lasijiasi',
    '梅里达': 'meilida',
    '波多贝罗': 'boduobeiluo',
    '特鲁希略': 'teluxilue',
    '韦拉克鲁斯': 'weilakelusi',
    '马拉开波': 'malakaibo',
    '哈瓦那': 'hawanag',
    '圣地亚哥': 'shengdiyage',
    '圣多明各': 'shengduomingge',
    '圣胡安': 'shenghuan',
    '拿骚': 'nasao',
    '牙买加': 'yamaijia',
    '皇家港': 'huangjiagang',
    '亚速尔': 'yasuole',
    '南特': 'nant',
    '卡萨布兰卡': 'kasabulanka',
    '希洪': 'xihong',
    '拉斯帕尔马斯': 'lasipalmasi',
    '法鲁': 'falu',
    '波尔图': 'boertu',
    '波尔多': 'boderduo',
    '里斯本': 'lisiben',
    '阿尔金': 'aerjin',
    '马德拉': 'madele',
    '不来梅': 'bulaimei',
    '伦敦': 'lundun',
    '但泽': 'danze',
    '加莱': 'jalai',
    '卑尔根': 'beiegen',
    '吕贝克': 'lvbeike',
    '哥本哈根': 'gebenhagen',
    '多佛': 'duofu',
    '奥斯陆': 'aosilu',
    '安特卫普': 'anteweipu',
    '斯德哥摩': 'sidegemo',
    '斯德哥尔摩': 'sidegeermo',
    '普利茅斯': 'pulimaosi',
    '格罗宁根': 'geluoninggen',
    '汉堡': 'hanbao',
    '海尔德': 'haierde',
    '爱丁堡': 'aidingbao',
    '维斯比': 'weisibi',
    '都柏林': 'dubolin',
    '里加': 'lijia',
    '阿姆斯特丹': 'amusitedan',
    '亚丁': 'yading',
    '佐法尔': 'zuofa',
    '吉达': 'jida',
    '巴士拉': 'bashila',
    '泽拉': 'zela',
    '索科特拉': 'suoketela',
    '苏伊士': 'suyishi',
    '霍尔木兹': 'huoermuzi',
    '马斯喀特': 'masikate',
    '马萨瓦': 'masawa',
    '休达': 'xiuda',
    '卡利亚里': 'kaliyali',
    '卡尔维': 'kaerwei',
    '塞维利亚': 'saiweiliya',
    '巴塞罗那': 'basailuona',
    '帕尔马': 'paerma',
    '比萨': 'bisa',
    '热那亚': 'renaya',
    '瓦伦西亚': 'walunxiya',
    '的黎波里': 'deliboli',
    '突尼斯': 'tunisi',
    '萨萨里': 'sasali',
    '蒙彼利埃': 'mengbiliai',
    '阿尔及尔': 'aerjier',
    '马拉加': 'malaga',
    '马赛': 'masai',
    '基尔瓦': 'jiewa',
    '塔马塔夫': 'tamatafu',
    '摩加迪沙': 'mojiadisha',
    '桑给巴尔': 'sanggeibaer',
    '索法拉': 'suofala',
    '纳塔尔': 'nataer',
    '莫桑比克': 'mosangbike',
    '蒙巴萨': 'mengbasa',
    '马林迪': 'malindi',
    '佛得角': 'fudejiao',
    '卡里比布': 'kalibibu',
    '卢安达': 'luanda',
    '圣乔治': 'shengqiaozhi',
    '圣多美': 'shengduomei',
    '塞拉利昂': 'saililiang',
    '开普敦': 'kaipudun',
    '本格拉': 'bengela',
    '杜阿拉': 'duala',
    '贝宁': 'beining',
    '阿比让': 'abirang'
}


def rename_folder_and_files(folder_path, is_imgsC=False):
    """重命名文件夹和文件"""
    if not os.path.isdir(folder_path):
        return
    
    print(f'开始处理: {folder_path}')
    
    if is_imgsC:
        # imgsC文件夹 - 先重命名海域文件夹
        sea_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
        
        for sea_name in sea_dirs:
            if sea_name in SEA_PINYIN:
                old_path = os.path.join(folder_path, sea_name)
                new_name = SEA_PINYIN[sea_name]
                new_path = os.path.join(folder_path, new_name)
                
                if old_path != new_path:
                    print(f'重命名海域: {sea_name} -> {new_name}')
                    shutil.move(old_path, new_path)
        
        # 再重命名城市文件
        sea_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
        
        for sea_name in sea_dirs:
            sea_path = os.path.join(folder_path, sea_name)
            
            if not os.path.isdir(sea_path):
                continue
                
            files = [f for f in os.listdir(sea_path) if f.lower().endswith('.png')]
            
            for filename in files:
                city_name = os.path.splitext(filename)[0]
                
                if city_name in CITY_PINYIN:
                    old_path = os.path.join(sea_path, filename)
                    new_name = CITY_PINYIN[city_name] + '.png'
                    new_path = os.path.join(sea_path, new_name)
                    
                    if old_path != new_path:
                        print(f'重命名文件: {filename} -> {new_name}')
                        shutil.move(old_path, new_path)
    else:
        # imgsE和imgsF文件夹
        items = os.listdir(folder_path)
        
        for item in items:
            item_path = os.path.join(folder_path, item)
            
            if os.path.isdir(item_path):
                # 处理子文件夹
                rename_folder_and_files(item_path, is_imgsC=False)
            elif item.lower().endswith('.png'):
                # 处理文件
                name_without_ext = os.path.splitext(item)[0]
                
                # 尝试使用海域或城市拼音
                new_name = None
                if name_without_ext in SEA_PINYIN:
                    new_name = SEA_PINYIN[name_without_ext] + '.png'
                elif name_without_ext in CITY_PINYIN:
                    new_name = CITY_PINYIN[name_without_ext] + '.png'
                
                if new_name:
                    new_path = os.path.join(folder_path, new_name)
                    if item_path != new_path:
                        print(f'重命名文件: {item} -> {new_name}')
                        shutil.move(item_path, new_path)


if __name__ == '__main__':
    base_dir = os.path.dirname(__file__)
    
    # 处理 imgsC
    imgsc_path = os.path.join(base_dir, 'imgsC')
    if os.path.isdir(imgsc_path):
        rename_folder_and_files(imgsc_path, is_imgsC=True)
    
    # 处理 imgsE
    imgse_path = os.path.join(base_dir, 'imgsE')
    if os.path.isdir(imgse_path):
        rename_folder_and_files(imgse_path, is_imgsC=False)
    
    # 处理 imgsF
    imgsf_path = os.path.join(base_dir, 'imgsF')
    if os.path.isdir(imgsf_path):
        rename_folder_and_files(imgsf_path, is_imgsC=False)
    
    print('重命名完成！')
