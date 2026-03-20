from platform import system
from PySide6.QtCore import Slot
import Recorder.globals

if system() == 'Windows':
    import Recorder.UniversalRecorder as _Recorder
    _Recorder.globalv.key_combination_trigger = ['win', 'shiftright', 'shift', 'ctrlright', 'ctrl', 'altright', 'alt']
elif system() in ['Linux', 'Darwin']:
    import Recorder.UniversalRecorder as _Recorder
    _Recorder.globalv.key_combination_trigger = ['win', 'shiftright', 'shift', 'ctrlright', 'ctrl', 'altright', 'alt']
else:
    raise OSError("Unsupported platform '{}'".format(system()))

setuphook = _Recorder.setuphook
set_game_window_title = _Recorder.set_game_window_title
set_use_relative_coords = _Recorder.set_use_relative_coords

# 捕获到事件后调用函数
def set_callback(callback):
    _Recorder.record_signals.event_signal.connect(callback)

def set_cursor_pose_change(callback):
    _Recorder.record_signals.cursor_pos_change.connect(callback)

def dispose():
    _Recorder.record_signals.event_signal.disconnect()


# 槽函数:改变鼠标精度
@Slot(int)
def set_interval(value):
    globals.mouse_interval_ms = value
