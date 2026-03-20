# -*- encoding:utf-8 -*-
"""
测试坐标转换和点击功能
"""
from Util.ImageRecognition import click_at, get_window_rect_by_title


def test_coordinate_conversion():
    """测试坐标转换"""
    window_title = "大航海时代：传说"
    
    print("=" * 80)
    print("测试坐标转换和点击功能")
    print("=" * 80)
    
    # 获取窗口位置
    window_rect = get_window_rect_by_title(window_title)
    if not window_rect:
        print(f"❌ 找不到窗口：{window_title}")
        print("\n提示:")
        print("  1. 确保游戏已经打开")
        print("  2. 检查窗口标题是否正确")
        return
    
    left, top, width, height = window_rect
    print(f"✅ 找到窗口：{window_title}")
    print(f"   窗口位置：({left}, {top})")
    print(f"   窗口尺寸：{width} x {height}")
    
    # 测试坐标转换
    test_x, test_y = 515, 385  # 窗口内绝对像素坐标
    rel_x = test_x / width
    rel_y = test_y / height
    
    print(f"\n坐标转换测试:")
    print(f"   绝对像素坐标：({test_x}, {test_y})")
    print(f"   相对坐标：({rel_x:.3f}, {rel_y:.3f})")
    
    # 计算屏幕坐标
    screen_x = left + int(rel_x * width)
    screen_y = top + int(rel_y * height)
    print(f"   屏幕坐标：({screen_x}, {screen_y})")
    
    # 测试点击
    print(f"\n测试点击:")
    print(f"   准备点击位置：({test_x}, {test_y}) [窗口内绝对像素]")
    print(f"   实际点击位置：({screen_x}, {screen_y}) [屏幕绝对]")
    
    try:
        result = click_at(test_x, test_y, button='left', window_title=window_title)
        print(f"   点击结果：{'✅ 成功' if result else '❌ 失败'}")
    except Exception as e:
        print(f"   点击异常：{e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_coordinate_conversion()
