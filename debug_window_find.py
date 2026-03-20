# -*- encoding:utf-8 -*-
"""
调试窗口查找问题
"""
import win32gui
import win32con


def debug_get_window_rect_by_title(title_substr: str):
    """调试版本的 get_window_rect_by_title"""
    print(f"\n正在查找包含 '{title_substr}' 的窗口...")
    
    result = [None]
    found_count = [0]
    error_count = [0]

    def enum_cb(hwnd, _):
        try:
            # 检查窗口句柄是否有效
            if not win32gui.IsWindow(hwnd):
                return True
            
            # 检查窗口是否可见
            if not win32gui.IsWindowVisible(hwnd):
                return True
            
            try:
                t = win32gui.GetWindowText(hwnd)
                if not t:
                    return True
            except Exception as e:
                print(f"  [跳过] GetWindowText 失败：{e}")
                return True
            
            # 检查标题是否匹配
            if title_substr.strip() not in t:
                return True
            
            # 匹配成功
            found_count[0] += 1
            print(f"  [匹配] 找到窗口：'{t}' (句柄：{hwnd})")
            
            # 获取客户区域矩形
            try:
                client_rect = win32gui.GetClientRect(hwnd)
                if not client_rect:
                    print(f"    [错误] GetClientRect 返回空")
                    return True
            except Exception as e:
                print(f"    [错误] GetClientRect 失败：{e}")
                return True
            
            # 将客户区域坐标转换为屏幕坐标
            try:
                left, top = win32gui.ClientToScreen(hwnd, (client_rect[0], client_rect[1]))
                right, bottom = win32gui.ClientToScreen(hwnd, (client_rect[2], client_rect[3]))
                result[0] = (left, top, right - left, bottom - top)
                print(f"    [成功] 窗口位置：{result[0]}")
                return False  # 停止枚举
            except Exception as e:
                print(f"    [错误] ClientToScreen 失败：{e}")
                return True
                
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
        win32gui.EnumWindows(enum_cb, None)
        print(f"枚举完成。找到 {found_count[0]} 个匹配的窗口，跳过 {error_count[0]} 个错误")
        
        if result[0]:
            print(f"\n✅ 成功找到窗口：{result[0]}")
        else:
            print(f"\n❌ 未找到匹配的窗口")
        
        return result[0]
    except Exception as e:
        print(f"\n❌ 枚举失败：{e}")
        return None


if __name__ == "__main__":
    print("=" * 80)
    print("调试窗口查找功能")
    print("=" * 80)
    
    window_title = "大航海时代：传说"
    rect = debug_get_window_rect_by_title(window_title)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
