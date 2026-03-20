# -*- encoding:utf-8 -*-
"""
测试 ctypes 回调函数 - 使用全局变量
"""
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32

# 全局变量
g_count = 0
g_hwnds = []

print("=" * 80)
print("测试 ctypes 回调函数 (全局变量)")
print("=" * 80)

def callback(hwnd, _):
    global g_count, g_hwnds
    g_count += 1
    if g_count <= 5:
        print(f"  回调：句柄={hwnd}, 计数={g_count}")
    g_hwnds.append(hwnd)
    return True

# 保持回调函数的引用
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.py_object)
cb = WNDENUMPROC(callback)

print("\n开始枚举窗口...")
try:
    result = user32.EnumWindows(cb, None)
    print(f"EnumWindows 返回值：{result}")
    print(f"全局计数：{g_count}")
    print(f"收集到的句柄数：{len(g_hwnds)}")
    if g_hwnds:
        print(f"前 3 个句柄：{g_hwnds[:3]}")
except Exception as e:
    print(f"异常：{e}")
    print(f"全局计数：{g_count}")
    print(f"收集到的句柄数：{len(g_hwnds)}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
