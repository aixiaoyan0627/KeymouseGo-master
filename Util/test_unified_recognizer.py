# -*- encoding:utf-8 -*-
"""
统一识别器测试脚本

测试内容：
1. 初始化统一识别器
2. 测试 YOLO 识别（图标）
3. 测试 OCR 识别（文字）
4. 测试智能路由
"""
import os
import sys
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Util.UnifiedRecognizer import (
    UnifiedRecognizer,
    RecognitionMethod,
    init_recognizer,
    get_recognizer,
    detect,
)


def test_initialization():
    """测试 1: 初始化统一识别器"""
    print("\n" + "="*60)
    print("测试 1: 初始化统一识别器")
    print("="*60)
    
    try:
        # 测试 1: 创建识别器
        recognizer = UnifiedRecognizer()
        print("✅ 统一识别器创建成功")
        
        # 测试 2: 初始化全局识别器
        global_rec = init_recognizer()
        print("✅ 全局识别器初始化成功")
        
        # 测试 3: 获取全局识别器
        same_rec = get_recognizer()
        assert global_rec is same_rec, "全局识别器应该是同一个实例"
        print("✅ 全局识别器单例模式正常")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败：{e}")
        return False


def test_yolo_detection(recognizer):
    """测试 2: YOLO 识别（图标）"""
    print("\n" + "="*60)
    print("测试 2: YOLO 识别（图标）")
    print("="*60)
    
    try:
        # 测试路径推断
        test_paths = [
            'imgsA/icon1.png',
            'imgsB/button.png',
            'imgsC/text.png',  # 这个应该是 OCR
        ]
        
        for path in test_paths:
            method = recognizer._infer_method_from_path(path)
            expected = RecognitionMethod.YOLO if 'imgsA' in path or 'imgsB' in path else RecognitionMethod.OCR
            assert method == expected, f"路径 {path} 应该推断为 {expected.name}"
            print(f"✅ 路径推断正确：{path} → {method.name}")
        
        # 测试文件名提取文字
        test_files = [
            '开始游戏.png',
            '设置按钮.png',
        ]
        
        for filename in test_files:
            text = recognizer._extract_text_from_filename(filename)
            print(f"✅ 文件名提取：{filename} → {text}")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLO 识别测试失败：{e}")
        return False


def test_ocr_recognition(recognizer):
    """测试 3: OCR 识别（文字）"""
    print("\n" + "="*60)
    print("测试 3: OCR 识别（文字）")
    print("="*60)
    
    try:
        # 测试 OCR 路径推断
        test_paths = [
            'imgsC/text1.png',
            'imgsE/label.png',
            'imgsF/button_text.png',
            'imgsG/menu_item.png',
        ]
        
        for path in test_paths:
            method = recognizer._infer_method_from_path(path)
            assert method == RecognitionMethod.OCR, f"路径 {path} 应该推断为 OCR"
            print(f"✅ OCR 路径推断正确：{path} → {method.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR 识别测试失败：{e}")
        return False


def test_intelligent_routing(recognizer):
    """测试 4: 智能路由"""
    print("\n" + "="*60)
    print("测试 4: 智能路由测试")
    print("="*60)
    
    try:
        # 测试各种路径的路由
        test_cases = [
            ('imgsA/icon.png', RecognitionMethod.YOLO),
            ('imgsB/button.png', RecognitionMethod.YOLO),
            ('imgsC/text.png', RecognitionMethod.OCR),
            ('imgsE/label.png', RecognitionMethod.OCR),
            ('imgsF/note.png', RecognitionMethod.OCR),
            ('imgsG/menu.png', RecognitionMethod.OCR),
            ('unknown/path.png', RecognitionMethod.YOLO),  # 默认 YOLO
        ]
        
        for path, expected_method in test_cases:
            inferred = recognizer._infer_method_from_path(path)
            assert inferred == expected_method, \
                f"路径 {path} 应该路由到 {expected_method.name}，实际是 {inferred.name}"
            print(f"✅ 智能路由正确：{path} → {inferred.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 智能路由测试失败：{e}")
        return False


def test_recognition_result_format(recognizer):
    """测试 5: 识别结果格式"""
    print("\n" + "="*60)
    print("测试 5: 识别结果格式测试")
    print("="*60)
    
    try:
        from Util.UnifiedRecognizer import RecognitionResult
        
        # 测试成功结果
        result = RecognitionResult(
            success=True,
            method=RecognitionMethod.YOLO,
            position=(100, 200),
            confidence=0.95,
            class_name='icon',
            bbox=(80, 180, 120, 220),
        )
        
        assert result.success == True
        assert result.position == (100, 200)
        assert result.confidence == 0.95
        print(f"✅ 成功结果格式正确")
        print(f"   位置：{result.position}")
        print(f"   置信度：{result.confidence:.2f}")
        print(f"   类别：{result.class_name}")
        
        # 测试失败结果
        result = RecognitionResult(
            success=False,
            method=RecognitionMethod.OCR,
            error='未找到目标',
        )
        
        assert result.success == False
        assert result.error == '未找到目标'
        print(f"✅ 失败结果格式正确")
        print(f"   错误：{result.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ 结果格式测试失败：{e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 统一识别器测试套件")
    print("="*60)
    
    results = []
    
    # 测试 1: 初始化
    results.append(("初始化测试", test_initialization()))
    
    # 创建识别器用于后续测试
    try:
        recognizer = get_recognizer()
    except Exception as e:
        print(f"❌ 无法创建识别器：{e}")
        return False
    
    # 测试 2: YOLO
    results.append(("YOLO 识别测试", test_yolo_detection(recognizer)))
    
    # 测试 3: OCR
    results.append(("OCR 识别测试", test_ocr_recognition(recognizer)))
    
    # 测试 4: 智能路由
    results.append(("智能路由测试", test_intelligent_routing(recognizer)))
    
    # 测试 5: 结果格式
    results.append(("结果格式测试", test_recognition_result_format(recognizer)))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！统一识别器可以投入使用。")
        return True
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查问题。")
        return False


if __name__ == '__main__':
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format='<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>',
        level='DEBUG',
    )
    
    # 运行测试
    success = run_all_tests()
    
    # 退出码
    sys.exit(0 if success else 1)
