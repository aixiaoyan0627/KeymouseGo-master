#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新配置文件中的中文海域和城市名为拼音
"""
import os
import json5

# 拼音映射表（与rename_to_pinyin.py保持一致）
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


def update_config_file(config_path):
    """更新配置文件"""
    print(f'处理配置文件: {config_path}')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json5.load(f)
    
    # 更新 ocean_v3 配置
    if 'ocean_v3' in data and 'cities' in data['ocean_v3']:
        for city_cfg in data['ocean_v3']['cities']:
            # 更新海域
            sea = city_cfg.get('sea', '')
            if sea in SEA_PINYIN:
                old_sea = sea
                city_cfg['sea'] = SEA_PINYIN[sea]
                print(f'  更新海域: {old_sea} -> {city_cfg["sea"]}')
            
            # 更新城市
            city = city_cfg.get('city', '')
            if city in CITY_PINYIN:
                old_city = city
                city_cfg['city'] = CITY_PINYIN[city]
                print(f'  更新城市: {old_city} -> {city_cfg["city"]}')
    
    # 更新 ocean 配置（旧版）
    if 'start_sea' in data:
        sea = data['start_sea']
        if sea in SEA_PINYIN:
            data['start_sea'] = SEA_PINYIN[sea]
    
    if 'start_city' in data:
        city = data['start_city']
        if city in CITY_PINYIN:
            data['start_city'] = CITY_PINYIN[city]
    
    if 'transit_sea' in data:
        sea = data['transit_sea']
        if sea in SEA_PINYIN:
            data['transit_sea'] = SEA_PINYIN[sea]
    
    if 'transit_city' in data:
        city = data['transit_city']
        if city in CITY_PINYIN:
            data['transit_city'] = CITY_PINYIN[city]
    
    if 'back_sea' in data:
        sea = data['back_sea']
        if sea in SEA_PINYIN:
            data['back_sea'] = SEA_PINYIN[sea]
    
    if 'back_city' in data:
        city = data['back_city']
        if city in CITY_PINYIN:
            data['back_city'] = CITY_PINYIN[city]
    
    # 保存更新后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json5.dump(data, f, indent=2, ensure_ascii=False)
    
    print('配置文件更新完成！')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # 默认处理当前目录下的所有配置文件
        config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        if os.path.isdir(config_dir):
            for filename in os.listdir(config_dir):
                if filename.lower().endswith(('.json', '.json5')):
                    config_path = os.path.join(config_dir, filename)
                    update_config_file(config_path)
                    print()
        else:
            print('请提供配置文件路径')
            sys.exit(1)
        
        sys.exit(0)
    
    update_config_file(config_path)
