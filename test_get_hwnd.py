# -*- encoding:utf-8 -*-
"""
测试 _get_window_handle_by_title 函数
"""
import sys
sys.path.insert(0, 'Util')
from GameInputExecutor import _get_window_handle_by_title


print("=" * 80)
print("测试 _get_window_handle_by_title 函数")
print("=" * 80)

window_title = "大航海时代：传说"
print(f"\n查找窗口：'{window_title}'")

hwnd = _get_window_handle_by_title(window_title)

if hwnd:
    print(f"\n✅ 成功找到窗口句柄：{hwnd}")
else:
    print(f"\n❌ 未找到窗口句柄")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
