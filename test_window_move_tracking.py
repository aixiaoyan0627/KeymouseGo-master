# -*- encoding:utf-8 -*-
"""
测试窗口移动后的实时坐标跟踪功能

测试场景：
1. 在窗口位置 A 点击某个位置
2. 移动窗口到位置 B
3. 再次点击同一个相对坐标
4. 验证点击位置是否跟随窗口移动
"""
import time
from loguru import logger
from Util.GameInputExecutor import GameInputExecutor


def test_window_move_tracking():
    """测试窗口移动后的坐标跟踪"""
    
    print("=" * 60)
    print("窗口移动跟踪功能测试")
    print("=" * 60)
    
    # 创建执行器（替换为你的游戏窗口标题）
    window_title = "游戏窗口标题"  # TODO: 修改为实际窗口标题
    executor = GameInputExecutor(window_title=window_title, auto_activate_window=True)
    
    print(f"\n窗口标题：{window_title}")
    print("测试步骤：")
    print("1. 将游戏窗口移动到屏幕左侧")
    print("2. 按 Enter 键在窗口中心点击（相对坐标 0.5, 0.5）")
    print("3. 将游戏窗口移动到屏幕右侧")
    print("4. 再次按 Enter 键在窗口中心点击")
    print("5. 验证两次点击都准确命中窗口中心")
    print("\n按 Ctrl+C 退出测试")
    print("-" * 60)
    
    click_count = 0
    
    try:
        while True:
            click_count += 1
            print(f"\n第 {click_count} 次点击")
            
            # 获取当前窗口位置
            window_rect = executor._get_game_window_rect()
            if window_rect:
                left, top, width, height = window_rect
                print(f"窗口位置：({left}, {top}) 尺寸：{width}x{height}")
                
                # 在窗口中心点击（相对坐标 0.5, 0.5）
                print("点击窗口中心 (0.5, 0.5)")
                executor.click(0.5, 0.5, is_relative=True)
                
                print("点击完成！如果窗口移动了，下次点击会自动跟踪新位置")
            else:
                print(f"警告：找不到窗口 '{window_title}'")
                print("请确保窗口存在且标题正确")
            
            # 等待用户按下 Enter 键
            input("\n按 Enter 键进行下一次点击，或移动窗口后测试...")
            
    except KeyboardInterrupt:
        print(f"\n\n测试结束，共点击 {click_count} 次")
        print("如果每次点击都准确命中窗口中心，说明实时坐标跟踪功能正常！")


def test_absolute_vs_relative():
    """测试绝对坐标和相对坐标的区别"""
    
    print("\n" + "=" * 60)
    print("绝对坐标 vs 相对坐标测试")
    print("=" * 60)
    
    window_title = "游戏窗口标题"  # TODO: 修改为实际窗口标题
    executor = GameInputExecutor(window_title=window_title, auto_activate_window=True)
    
    print("\n测试说明：")
    print("1. 绝对坐标：屏幕固定位置，不随窗口移动")
    print("2. 相对坐标：窗口内相对位置，随窗口移动而更新")
    print("\n按 Enter 键测试...")
    
    try:
        while True:
            # 获取窗口位置
            window_rect = executor._get_game_window_rect()
            if window_rect:
                left, top, width, height = window_rect
                
                print(f"\n当前窗口位置：({left}, {top})")
                
                # 测试相对坐标（窗口中心）
                print("\n[相对坐标] 点击窗口中心 (0.5, 0.5)")
                executor.click(0.5, 0.5, is_relative=True)
                
                # 等待一下
                time.sleep(0.5)
                
                # 测试绝对坐标（屏幕固定位置）
                screen_x = left + width // 2
                screen_y = top + height // 2
                print(f"[绝对坐标] 点击屏幕位置 ({screen_x}, {screen_y})")
                executor.click(screen_x, screen_y)
                
                print("\n移动窗口后再次测试，观察相对坐标是否跟随窗口移动")
            else:
                print(f"找不到窗口：{window_title}")
            
            input("\n按 Enter 键继续...")
            
    except KeyboardInterrupt:
        print("\n测试结束")


if __name__ == "__main__":
    print("选择测试模式：")
    print("1. 窗口移动跟踪测试（推荐）")
    print("2. 绝对坐标 vs 相对坐标对比测试")
    
    choice = input("\n请输入测试模式 (1/2): ").strip()
    
    if choice == "1":
        test_window_move_tracking()
    elif choice == "2":
        test_absolute_vs_relative()
    else:
        print("无效的选择，使用默认模式 1")
        test_window_move_tracking()
