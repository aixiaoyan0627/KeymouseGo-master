# -*- encoding:utf-8 -*-
"""
测试 GameInputExecutor 的 _get_game_window_rect 方法
"""
from Util.GameInputExecutor import GameInputExecutor


print("=" * 80)
print("测试 GameInputExecutor 的 _get_game_window_rect 方法")
print("=" * 80)

window_title = "大航海时代：传说"
executor = GameInputExecutor(window_title)

print(f"\n窗口标题：{window_title}")
print(f"窗口标题属性：{executor.window_title}")

# 测试 _get_game_window_rect
rect = executor._get_game_window_rect()
print(f"\n_get_game_window_rect 返回值：{rect}")

# 测试 get_window_rect_by_title
from Util.ImageRecognition import get_window_rect_by_title
rect2 = get_window_rect_by_title(window_title)
print(f"get_window_rect_by_title 返回值：{rect2}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
