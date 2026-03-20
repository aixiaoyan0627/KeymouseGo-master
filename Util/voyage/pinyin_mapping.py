# -*- encoding:utf-8 -*-
"""
拼音-中文双向映射模块
用于UI显示中文，底层使用拼音路径
"""
import os

# 海域拼音映射
SEA_PINYIN_TO_CHINESE = {
    'dongdizhonghai': '东地中海',
    'zhongnanmei': '中南美',
    'jialebi': '加勒比',
    'beidaxiyang': '北大西洋',
    'beihai': '北海',
    'honghai': '红海',
    'xidizhonghai': '西地中海',
    'feizhoudongan': '非洲东岸',
    'feizhouxian': '非洲西岸'
}

SEA_CHINESE_TO_PINYIN = {v: k for k, v in SEA_PINYIN_TO_CHINESE.items()}

# 城市拼音映射
CITY_PINYIN_TO_CHINESE = {
    'yalishanda': '亚历山大',
    'yisitanbuer': '伊斯坦布尔',
    'kechi': '刻赤',
    'kandia': '坎迪亚',
    'saiwasituobaoer': '塞瓦斯托波尔',
    'wenisi': '威尼斯',
    'ankena': '安科纳',
    'kailuo': '开罗',
    'zhadaer': '扎达尔',
    'lagusha': '拉古萨',
    'aodesa': '敖德萨',
    'famagusita': '法马古斯塔',
    'telabuzong': '特拉布宗',
    'banjiaxi': '班加西',
    'deliyatesite': '的里雅斯特',
    'saluonika': '萨洛尼卡',
    'beilute': '贝鲁特',
    'nabulesi': '那不勒斯',
    'xilakusa': '锡拉库萨',
    'yadian': '雅典',
    'yafa': '雅法',
    'bonanbuge': '伯南布哥',
    'kayang': '卡宴',
    'dakaiman': '大开曼',
    'weiliansitade': '威廉斯塔德',
    'lasijiasi': '拉斯加斯',
    'meilida': '梅里达',
    'boduobeiluo': '波多贝罗',
    'teluxilue': '特鲁希略',
    'weilakelusi': '韦拉克鲁斯',
    'malakaibo': '马拉开波',
    'hawanag': '哈瓦那',
    'shengdiyage': '圣地亚哥',
    'shengduomingge': '圣多明各',
    'shenghuan': '圣胡安',
    'nasao': '拿骚',
    'yamaijia': '牙买加',
    'huangjiagang': '皇家港',
    'yasuole': '亚速尔',
    'nant': '南特',
    'kasabulanka': '卡萨布兰卡',
    'xihong': '希洪',
    'lasipalmasi': '拉斯帕尔马斯',
    'falu': '法鲁',
    'boertu': '波尔图',
    'boderduo': '波尔多',
    'lisiben': '里斯本',
    'aerjin': '阿尔金',
    'madele': '马德拉',
    'bulaimei': '不来梅',
    'lundun': '伦敦',
    'danze': '但泽',
    'jalai': '加莱',
    'beiegen': '卑尔根',
    'lvbeike': '吕贝克',
    'gebenhagen': '哥本哈根',
    'duofu': '多佛',
    'aosilu': '奥斯陆',
    'anteweipu': '安特卫普',
    'sidegeermo': '斯德哥尔摩',
    'pulimaosi': '普利茅斯',
    'geluoninggen': '格罗宁根',
    'hanbao': '汉堡',
    'haierde': '海尔德',
    'aidingbao': '爱丁堡',
    'weisibi': '维斯比',
    'dubolin': '都柏林',
    'lijia': '里加',
    'amusitedan': '阿姆斯特丹',
    'yading': '亚丁',
    'zuofa': '佐法尔',
    'jida': '吉达',
    'bashila': '巴士拉',
    'zela': '泽拉',
    'suoketela': '索科特拉',
    'suyishi': '苏伊士',
    'huoermuzi': '霍尔木兹',
    'masikate': '马斯喀特',
    'masawa': '马萨瓦',
    'xiuda': '休达',
    'kaliyali': '卡利亚里',
    'kaerwei': '卡尔维',
    'saiweiliya': '塞维利亚',
    'basailuona': '巴塞罗那',
    'paerma': '帕尔马',
    'bisa': '比萨',
    'renaya': '热那亚',
    'walunxiya': '瓦伦西亚',
    'deliboli': '的黎波里',
    'tunisi': '突尼斯',
    'sasali': '萨萨里',
    'mengbiliai': '蒙彼利埃',
    'aerjier': '阿尔及尔',
    'malaga': '马拉加',
    'masai': '马赛',
    'jiewa': '基尔瓦',
    'tamatafu': '塔马塔夫',
    'mojiadisha': '摩加迪沙',
    'sanggeibaer': '桑给巴尔',
    'suofala': '索法拉',
    'nataer': '纳塔尔',
    'mosangbike': '莫桑比克',
    'mengbasa': '蒙巴萨',
    'malindi': '马林迪',
    'fudejiao': '佛得角',
    'kalibibu': '卡里比布',
    'luanda': '卢安达',
    'shengqiaozhi': '圣乔治',
    'shengduomei': '圣多美',
    'saililiang': '塞拉利昂',
    'kaipudun': '开普敦',
    'bengela': '本格拉',
    'duala': '杜阿拉',
    'beining': '贝宁',
    'abirang': '阿比让'
}

CITY_CHINESE_TO_PINYIN = {v: k for k, v in CITY_PINYIN_TO_CHINESE.items()}

# imgsG 拼音映射
IMGSPINYIN_TO_CHINESE = {
    'shijieditu': '世界地图',
    'mairu': '买入',
    'quanmai': '全卖',
    'qianwang': '前往',
    'maichu': '卖出',
    'chengjiao': '成交',
    'wodehuowu': '我的货物',
    'taijia': '抬价',
    'tuohang': '拖航',
    'zhaomushuishou': '招募水手',
    'jiuzhu': '救助',
    'jixuhangxing': '继续航行',
    'hangxingzhong': '航行中',
    'qingke': '请客',
    'yunanhuigang': '遇难回港'
}

IMGSPINYIN_CHINESE_TO_PINYIN = {v: k for k, v in IMGSPINYIN_TO_CHINESE.items()}

# imgsB 拼音映射
IMGSBPINYIN_TO_CHINESE = {
    'caofan': '操帆',
    'xiuzhenghangxiang': '修正航向',
    'laji': '垃圾',
    'yanhui': '宴会',
    'haicao': '海草',
    'danshui': '淡水',
    'huozai1': '火灾1',
    'huozai2': '火灾2',
    'jiabanzangluan': '甲板脏乱',
    'pofan': '破帆',
    'hongbao': '红包',
    'hongbao2': '红包2',
    'hanghaishi1': '航海士1',
    'hanghaishi2': '航海士2',
    'hanghaishi3': '航海士3',
    'hanghaishi4': '航海士4',
    'hanghaishi5': '航海士5',
    'hanghaishi6': '航海士6',
    'shuyi': '鼠疫',
    'baoxiang': '宝箱',
    'bujitong': '补给桶',
    'yuhuo': '鱼获'
}

IMGSBPINYIN_CHINESE_TO_PINYIN = {v: k for k, v in IMGSBPINYIN_TO_CHINESE.items()}


def sea_pinyin_to_chinese(pinyin: str) -> str:
    """海域拼音转中文"""
    return SEA_PINYIN_TO_CHINESE.get(pinyin, pinyin)


def sea_chinese_to_pinyin(chinese: str) -> str:
    """海域中文转拼音"""
    return SEA_CHINESE_TO_PINYIN.get(chinese, chinese)


def city_pinyin_to_chinese(pinyin: str) -> str:
    """城市拼音转中文"""
    return CITY_PINYIN_TO_CHINESE.get(pinyin, pinyin)


def city_chinese_to_pinyin(chinese: str) -> str:
    """城市中文转拼音"""
    return CITY_CHINESE_TO_PINYIN.get(chinese, chinese)


def convert_sea_cities_to_chinese(sea_cities: dict) -> dict:
    """将海域-城市字典中的拼音转换为中文"""
    result = {}
    for sea_pinyin, cities_pinyin in sea_cities.items():
        sea_chinese = sea_pinyin_to_chinese(sea_pinyin)
        cities_chinese = [city_pinyin_to_chinese(c) for c in cities_pinyin]
        result[sea_chinese] = cities_chinese
    return result


def convert_config_to_pinyin(config: dict) -> dict:
    """将配置中的中文海域和城市转换为拼音"""
    if 'cities' in config:
        for city_cfg in config['cities']:
            if 'sea' in city_cfg:
                city_cfg['sea'] = sea_chinese_to_pinyin(city_cfg['sea'])
            if 'city' in city_cfg:
                city_cfg['city'] = city_chinese_to_pinyin(city_cfg['city'])
    return config


def convert_config_to_chinese(config: dict) -> dict:
    """将配置中的拼音海域和城市转换为中文"""
    if 'cities' in config:
        for city_cfg in config['cities']:
            if 'sea' in city_cfg:
                city_cfg['sea'] = sea_pinyin_to_chinese(city_cfg['sea'])
            if 'city' in city_cfg:
                city_cfg['city'] = city_pinyin_to_chinese(city_cfg['city'])
    return config


def image_pinyin_to_chinese(filename: str) -> str:
    """
    将图片文件名从拼音转换为中文显示
    
    参数:
        filename: 图片文件名（包含扩展名或不包含都可以）
    
    返回:
        转换后的中文文件名
    """
    name_without_ext = os.path.splitext(filename)[0]
    
    # 先检查imgsB的映射
    if name_without_ext in IMGSBPINYIN_TO_CHINESE:
        return IMGSBPINYIN_TO_CHINESE[name_without_ext] + os.path.splitext(filename)[1]
    
    # 再检查imgsG的映射
    if name_without_ext in IMGSPINYIN_TO_CHINESE:
        return IMGSPINYIN_TO_CHINESE[name_without_ext] + os.path.splitext(filename)[1]
    
    return filename


def image_chinese_to_pinyin(filename: str) -> str:
    """
    将图片文件名从中文转换为拼音
    
    参数:
        filename: 图片文件名（包含扩展名或不包含都可以）
    
    返回:
        转换后的拼音文件名
    """
    name_without_ext = os.path.splitext(filename)[0]
    
    # 先检查imgsB的映射
    if name_without_ext in IMGSBPINYIN_CHINESE_TO_PINYIN:
        return IMGSBPINYIN_CHINESE_TO_PINYIN[name_without_ext] + os.path.splitext(filename)[1]
    
    # 再检查imgsG的映射
    if name_without_ext in IMGSPINYIN_CHINESE_TO_PINYIN:
        return IMGSPINYIN_CHINESE_TO_PINYIN[name_without_ext] + os.path.splitext(filename)[1]
    
    return filename
