# -*- encoding:utf-8 -*-
"""
测试实际的 get_window_rect_by_title 函数
"""
from Util.ImageRecognition import get_window_rect_by_title


print("=" * 80)
print("测试实际的 get_window_rect_by_title 函数")
print("=" * 80)

window_title = "大航海时代：传说"
print(f"\n查找窗口：'{window_title}'")

rect = get_window_rect_by_title(window_title)

if rect:
    print(f"\n✅ 成功找到窗口：{rect}")
    print(f"   位置：({rect[0]}, {rect[1]})")
    print(f"   尺寸：{rect[2]} x {rect[3]}")
else:
    print(f"\n❌ 未找到窗口")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
