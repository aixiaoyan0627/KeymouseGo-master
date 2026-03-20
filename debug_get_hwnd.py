# -*- encoding:utf-8 -*-
"""
调试 _get_window_handle_by_title 函数
"""
import ctypes
import ctypes.wintypes
from typing import Optional, List

user32 = ctypes.windll.user32


def debug_get_window_handle_by_title(window_title: str) -> Optional[int]:
    """调试版本"""
    print(f"\n正在查找包含 '{window_title}' 的窗口...")
    
    _window_handles: List[int] = []
    found_count = [0]
    error_count = [0]
    total_count = [0]
    
    def callback(hwnd, _):
        total_count[0] += 1
        
        try:
            # 检查窗口句柄是否有效
            if not ctypes.wintypes.HWND(hwnd):
                return True
            
            try:
                title_length = user32.GetWindowTextLengthW(hwnd)
                if title_length <= 0:
                    return True
            except Exception as e:
                print(f"  [跳过] GetWindowTextLengthW 失败 (句柄：{hwnd}): {e}")
                return True
            
            try:
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                title = title_buffer.value
                if not title:
                    return True
            except Exception as e:
                print(f"  [跳过] GetWindowTextW 失败 (句柄：{hwnd}): {e}")
                return True
            
            # 检查标题是否匹配
            if window_title not in title:
                return True
            
            # 匹配成功
            found_count[0] += 1
            print(f"  [匹配] 找到窗口：'{title}' (句柄：{hwnd})")
            _window_handles.append(hwnd)
            
        except ValueError as e:
            error_count[0] += 1
            if "NULL" in str(e):
                print(f"  [跳过] PyObject is NULL (句柄：{hwnd})")
                return True
            print(f"  [错误] ValueError: {e}")
            raise
        except Exception as e:
            print(f"  [跳过] 其他异常：{e}")
            pass
        
        return True
    
    try:
        print("开始枚举窗口...")
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.py_object)
        user32.EnumWindows(WNDENUMPROC(callback), None)
        print(f"枚举完成。总共检查 {total_count[0]} 个窗口，找到 {found_count[0]} 个匹配，跳过 {error_count[0]} 个错误")
        
        if _window_handles:
            print(f"\n✅ 成功找到窗口句柄：{_window_handles[0]}")
            return _window_handles[0]
        else:
            print(f"\n❌ 未找到匹配的窗口")
            return None
            
    except Exception as e:
        print(f"\n❌ 枚举失败：{e}")
        return None


if __name__ == "__main__":
    print("=" * 80)
    print("调试 _get_window_handle_by_title 函数")
    print("=" * 80)
    
    window_title = "大航海时代：传说"
    hwnd = debug_get_window_handle_by_title(window_title)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
