from platform import system


if system() == 'Windows':
    import Event.WindowsEvents as _Event
    event_cls = _Event.WindowsEvent
    flag_multiplemonitor = _Event.numofmonitors > 1
elif system() in ['Linux', 'Darwin']:
    import Event.UniversalEvents as _Event
    event_cls = _Event.UniversalEvent
    flag_multiplemonitor = False
else:
    raise OSError("Unsupported platform '{}'".format(system()))

ScriptEvent = event_cls
ScreenWidth = _Event.SW
ScreenHeight = _Event.SH

# 导出游戏窗口相对坐标相关的函数
if hasattr(_Event, 'set_game_window_title'):
    set_game_window_title = _Event.set_game_window_title
if hasattr(_Event, 'set_use_relative_coords'):
    set_use_relative_coords = _Event.set_use_relative_coords
