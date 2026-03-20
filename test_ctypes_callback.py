# -*- encoding:utf-8 -*-
"""
测试 ctypes 回调函数
"""
import ctypes
import ctypes.wintypes

user32 = ctypes.windll.user32


def test_callback(hwnd, _):
    """简单回调"""
    print(f"回调被调用！句柄：{hwnd}")
    return True


print("=" * 80)
print("测试 ctypes 回调函数")
print("=" * 80)

# 方法 1: 直接传递 Python 函数
print("\n方法 1: 直接传递 Python 函数")
try:
    count = [0]
    
    def callback1(hwnd, _):
        count[0] += 1
        if count[0] <= 3:
            print(f"  回调 1: 句柄={hwnd}, 计数={count[0]}")
        return True
    
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.py_object)(callback1), None)
    print(f"  总共枚举 {count[0]} 个窗口")
except Exception as e:
    print(f"  失败：{e}")

# 方法 2: 保持回调引用
print("\n方法 2: 保持回调引用")
try:
    count = [0]
    
    def callback2(hwnd, _):
        count[0] += 1
        if count[0] <= 3:
            print(f"  回调 2: 句柄={hwnd}, 计数={count[0]}")
        return True
    
    # 保持回调函数的引用
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.py_object)
    cb = WNDENUMPROC(callback2)
    user32.EnumWindows(cb, None)
    print(f"  总共枚举 {count[0]} 个窗口")
except Exception as e:
    print(f"  失败：{e}")

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
