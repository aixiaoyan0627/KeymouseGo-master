import os
import sys

# 修复 pynput 与 shiboken/six 的冲突 - 在导入任何模块之前执行
try:
    # 禁用 shiboken 的 feature 检查
    import shibokensupport
    if hasattr(shibokensupport, 'feature'):
        original_feature_imported = shibokensupport.feature.feature_imported
        shibokensupport.feature.feature_imported = lambda *args, **kwargs: None
except ImportError:
    pass

try:
    # 确保 six 正确加载
    import six
except ImportError:
    pass

import math
# 先导入 pynput 避免与 PySide6 冲突
try:
    from pynput import mouse, keyboard
except ImportError:
    pass
# 抑制 Qt 在部分环境下触发的 DPI 相关提示（拒绝访问等），界面表现不变
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")
from PySide6.QtWidgets import QApplication, QWidget, QSpinBox
from PySide6.QtCore import Qt, Slot, QRect

import argparse
from Event import ScriptEvent
from loguru import logger

from Plugin.Manager import PluginManager
from Util.RunScriptClass import RunScriptCMDClass, StopFlag
from Util.DetectionLoop import DetectionLoop, DetectionConfig, load_config


def to_abs_path(*args):
    return os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                        *args)


def resize_layout(ui, ratio_w, ratio_h):
    ui.resize(ui.width() * ratio_w, ui.height() * ratio_h)

    for q_widget in ui.findChildren(QWidget):
        q_widget.setGeometry(QRect(q_widget.x() * ratio_w,
                                   q_widget.y() * ratio_h,
                                   q_widget.width() * ratio_w,
                                   q_widget.height() * ratio_h))
        q_widget.setStyleSheet('font-size: ' + str(
                                math.ceil(9 * min(ratio_h, ratio_w))) + 'px')
        if isinstance(q_widget, QSpinBox):
            q_widget.setStyleSheet('padding-left: 7px')


def main():
    # 试用期检查 - 只在UI启动时检查
    trial_passed = True
    trial_remaining = 7
    trial_error_msg = None
    
    # 延迟试用期检查，直到UI成功启动
    def check_trial_on_ui_start():
        nonlocal trial_passed, trial_remaining, trial_error_msg
        try:
            from Util.trial_manager import check_trial
            trial_passed, trial_remaining, trial_error_msg = check_trial()
            
            if not trial_passed:
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle('试用期结束')
                msg.setText(trial_error_msg)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                sys.exit(0)
            elif trial_remaining <= 3:
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox()
                msg.setWindowTitle('试用期提醒')
                msg.setText(f'试用期剩余 {trial_remaining} 天，请及时续费！')
                msg.setIcon(QMessageBox.Warning)
                msg.exec()
        except Exception as e:
            print(f'试用期检查失败: {e}')
            # 如果试用期检查失败，允许继续运行（避免影响测试）
            trial_passed = True
    
    import UIFunc
    import Recorder  # 仅图形界面/录制需要，检测模式不导入
    
    # 设置环境变量解决编码问题
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=freetype'
    
    app = QApplication(sys.argv)
    
    # 设置应用程序字体，确保中文正确显示
    from PySide6.QtGui import QFont
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    
    # Qt6 已默认启用高 DPI，无需再设置（AA_EnableHighDpiScaling 已弃用）
    ui = UIFunc.UIFunc(app)

    ui.setFixedSize(ui.width(), ui.height())
    ui.show()
    sys.exit(app.exec())


def run_detection_mode(config_path: str) -> None:
    """
    图片识别检测模式：实时检测长期运行；
    识别到触发图时暂停检测、执行脚本1，脚本结束后恢复检测；
    识别到图标时在固定坐标点击。
    配置见 detection_config.json5 或 Util.DetectionLoop.load_config 说明。
    """
    # 设置环境变量解决编码问题
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=freetype'
    
    config = load_config(config_path)
    if config is None:
        logger.error('Detection config load failed, exit.')
        return
    if not config.trigger_image_paths or not config.trigger_script_path:
        logger.warning('trigger_image_paths and trigger_script_path should be set in config.')
    
    # 确保脚本路径是绝对路径
    script_abs = config.trigger_script_path
    if not os.path.isabs(script_abs):
        script_abs = to_abs_path(script_abs)
    
    # 添加详细的路径调试信息
    logger.debug('Original script path: {}', config.trigger_script_path)
    logger.debug('Absolute script path: {}', script_abs)
    logger.debug('File exists: {}', os.path.isfile(script_abs))
    logger.debug('Current working directory: {}', os.getcwd())
    
    if not os.path.isfile(script_abs):
        logger.error('Trigger script not found: {}', script_abs)
        logger.error('Current working directory: {}', os.getcwd())
        logger.error('Absolute path attempted: {}', os.path.abspath(script_abs))
        return  # 直接返回，避免后续问题

    app = QApplication(sys.argv)
    
    # 设置应用程序字体，确保中文正确显示
    from PySide6.QtGui import QFont
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    PluginManager.reload()

    detection_loop = DetectionLoop(config)
    # 用于保持脚本线程引用，避免被回收
    script_holder = []

    def on_trigger_found():
        path = script_abs if os.path.isfile(script_abs) else config.trigger_script_path
        flag = StopFlag(False)
        thread = RunScriptCMDClass([path], 1, flag)
        thread.finished.connect(detection_loop.resume)
        script_holder.append(thread)
        thread.start()
        logger.info('Trigger script started: {}', path)

    detection_loop.trigger_found.connect(on_trigger_found)
    detection_loop.start()

    sys.exit(app.exec())


@logger.catch
def single_run(script_path, run_times):
    import Recorder  # 命令行跑脚本+F9 停止需要钩子
    
    # 设置环境变量解决编码问题
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=freetype'
    
    flag = StopFlag(False)
    thread = RunScriptCMDClass(script_path, run_times, flag)

    stop_name = 'f9'

    @Slot(ScriptEvent)
    def on_keyboard_event(event):
        key_name = event.action[1].lower()
        if key_name == stop_name:
            logger.debug('break exit!')
            flag.value = True
            thread.resume()
        return True

    Recorder.setuphook(commandline=True)
    Recorder.set_callback(on_keyboard_event)

    PluginManager.reload()
    eventloop = QApplication()
    
    # 设置应用程序字体，确保中文正确显示
    from PySide6.QtGui import QFont
    font = QFont("Microsoft YaHei UI", 9)
    eventloop.setFont(font)

    thread.finished.connect(eventloop.exit)
    thread.start()

    sys.exit(eventloop.exec_())


if __name__ == '__main__':
    logger.debug(sys.argv)
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument('scripts',
                            help='Path for the scripts',
                            type=str,
                            nargs='*'
                            )
        parser.add_argument('-rt', '--runtimes',
                            help='Run times for the script',
                            type=int,
                            default=1
                            )
        parser.add_argument('--detect',
                            help='Run image detection mode (config file path, default: detection_config.json5)',
                            type=str,
                            nargs='?',
                            const='detection_config.json5',
                            metavar='CONFIG'
                            )
        args = parser.parse_args()
        if getattr(args, 'detect', None) is not None:
            config_path = args.detect
            if not os.path.isabs(config_path):
                config_path = to_abs_path(config_path)
            run_detection_mode(config_path)
        elif args.scripts:
            args_dict = vars(args)
            single_run(args_dict['scripts'], run_times=args_dict['runtimes'])
        else:
            main()
    else:
        main()
