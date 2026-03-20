# -*- encoding:utf-8 -*-
"""
调试窗口标题匹配问题
"""
import win32gui
import win32con


def list_all_windows():
    """列出所有可见窗口"""
    windows = []
    
    def enum_cb(hwnd, _):
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append((hwnd, title))
        except Exception as e:
            pass
        return True
    
    win32gui.EnumWindows(enum_cb, None)
    return windows


def find_game_windows(search_keywords=None):
    """查找可能包含游戏关键词的窗口"""
    if search_keywords is None:
        search_keywords = ['大航海', '航海', '传说', '游戏', 'Game']
    
    all_windows = list_all_windows()
    matched_windows = []
    
    print("=" * 80)
    print("所有可见窗口:")
    print("=" * 80)
    for i, (hwnd, title) in enumerate(all_windows[:50], 1):  # 只显示前 50 个
        print(f"{i:3d}. {title}")
    
    if len(all_windows) > 50:
        print(f"... 还有 {len(all_windows) - 50} 个窗口")
    
    print("\n" + "=" * 80)
    print("匹配的游戏窗口:")
    print("=" * 80)
    
    for hwnd, title in all_windows:
        for keyword in search_keywords:
            if keyword in title:
                matched_windows.append((hwnd, title))
                print(f"✓ 窗口句柄：{hwnd}")
                print(f"  窗口标题：{title}")
                
                # 获取窗口位置
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    print(f"  窗口位置：{rect}")
                    print(f"  窗口尺寸：{rect[2] - rect[0]} x {rect[3] - rect[1]}")
                except:
                    pass
                
                # 获取客户区域
                try:
                    client_rect = win32gui.GetClientRect(hwnd)
                    print(f"  客户区域：{client_rect}")
                except:
                    pass
                
                print()
                break
    
    if not matched_windows:
        print("⚠ 没有找到包含关键词的窗口")
        print(f"  搜索关键词：{search_keywords}")
        print("\n提示:")
        print("  1. 确保游戏已经打开")
        print("  2. 检查游戏窗口的实际标题")
        print("  3. 可能需要修改配置文件中的 capture_window_title 参数")
    
    return matched_windows


if __name__ == "__main__":
    print("调试窗口标题匹配问题\n")
    
    # 查找游戏窗口
    game_windows = find_game_windows()
    
    if game_windows:
        print("\n" + "=" * 80)
        print("建议:")
        print("=" * 80)
        
        hwnd, title = game_windows[0]
        print(f"1. 使用完整标题:")
        print(f"   capture_window_title = \"{title}\"")
        print()
        print(f"2. 或使用部分标题 (推荐):")
        # 提取最具体的部分
        if '大航海时代：传说' in title:
            print(f"   capture_window_title = \"大航海时代：传说\"")
        elif '大航海' in title:
            print(f"   capture_window_title = \"大航海\"")
        else:
            short_title = title.split(' - ')[0].split('(')[0].strip()
            print(f"   capture_window_title = \"{short_title}\"")
        
        print("\n3. 修改位置:")
        print("   Util/voyage/config.py 第 184 行")
        print("   或 voyage 配置文件中的 capture_window 字段")
    else:
        print("\n" + "=" * 80)
        print("操作建议:")
        print("=" * 80)
        print("1. 打开游戏")
        print("2. 重新运行此脚本")
        print("3. 根据输出修改配置文件")
