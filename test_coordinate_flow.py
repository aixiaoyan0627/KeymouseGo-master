# -*- encoding:utf-8 -*-
"""
验证 A 策略坐标转换流程
"""
from Util.voyage.detector import ImageDetector, MatchResult
from Util.ImageRecognition import get_window_rect_by_title


print("=" * 80)
print("验证 A 策略坐标转换流程")
print("=" * 80)

window_title = "大航海时代：传说"

# 1. 模拟 detector 返回的坐标（窗口内绝对像素）
pixel_x, pixel_y = 515, 385
print(f"\n1. B 类图检测返回的坐标（窗口内绝对像素）: ({pixel_x}, {pixel_y})")

# 2. 获取窗口位置
window_rect = get_window_rect_by_title(window_title)
if not window_rect:
    print(f"❌ 找不到窗口：{window_title}")
    exit(1)

win_left, win_top, win_width, win_height = window_rect
print(f"2. 窗口位置：({win_left}, {win_top}, {win_width}, {win_height})")

# 3. 计算相对坐标
rel_x = pixel_x / win_width
rel_y = pixel_y / win_height
print(f"3. 转换为相对坐标：({rel_x:.6f}, {rel_y:.6f})")

# 4. 模拟 GameInputExecutor 重新获取窗口位置并计算屏幕坐标
# （这里假设窗口没有移动）
window_rect2 = get_window_rect_by_title(window_title)
win_left2, win_top2, win_width2, win_height2 = window_rect2

screen_x = win_left2 + int(rel_x * win_width2)
screen_y = win_top2 + int(rel_y * win_height2)
print(f"4. GameInputExecutor 重新获取窗口位置：({win_left2}, {win_top2}, {win_width2}, {win_height2})")
print(f"5. 计算屏幕坐标：({screen_x}, {screen_y})")

# 5. 验证坐标转换是否正确
expected_screen_x = win_left + pixel_x
expected_screen_y = win_top + pixel_y
print(f"\n验证:")
print(f"   直接计算屏幕坐标：({expected_screen_x}, {expected_screen_y})")
print(f"   相对坐标转换屏幕坐标：({screen_x}, {screen_y})")
print(f"   结果：{'✅ 一致' if (screen_x == expected_screen_x and screen_y == expected_screen_y) else '❌ 不一致'}")

# 6. 模拟窗口移动后的情况
print(f"\n模拟窗口移动后的情况:")
print(f"   假设窗口从 ({win_left}, {win_top}) 移动到 (100, 100)")
new_left, new_top = 100, 100
new_screen_x = new_left + int(rel_x * win_width)
new_screen_y = new_top + int(rel_y * win_height)
print(f"   新的屏幕坐标：({new_screen_x}, {new_screen_y})")
print(f"   如果使用旧坐标（错误）：({win_left + pixel_x}, {win_top + pixel_y})")
print(f"   差异：({new_screen_x - (win_left + pixel_x)}, {new_screen_y - (win_top + pixel_y)})")

print("\n" + "=" * 80)
print("结论:")
print("  - 使用相对坐标 + 实时获取窗口位置可以正确跟踪窗口移动")
print("  - 日志中显示的像素坐标只是中间表示，实际点击时会转换")
print("=" * 80)
