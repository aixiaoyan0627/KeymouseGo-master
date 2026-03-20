# -*- encoding:utf-8 -*-
"""
GUI 状态机集成示例

展示如何在 UIFunc.py 中集成统一状态机架构
"""
from Util.MainStateMachine import MainStateMachine, MainState
from Util.RecordStateMachine import RecordStateMachine
from Util.DetectionStateMachine import DetectionStateMachine
from Util.PluginStateMachine import PluginStateMachine


class UIFuncWithStateMachine:
    """
    带状态机的 UIFunc 示例类
    
    这个类展示了如何修改现有的 UIFunc.py 以集成状态机
    """
    
    def __init__(self, app):
        # 原有的初始化代码...
        # self.ui = UIView()
        # ...
        
        # ========== 新增：状态机初始化 ==========
        self.main_sm = MainStateMachine()
        
        # 创建子状态机
        self.record_sm = RecordStateMachine()
        self.detection_sm = DetectionStateMachine()
        # voyage_sm 由远洋模块自己管理
        self.plugin_sm = PluginStateMachine()
        
        # 设置子状态机引用
        self.main_sm.set_sub_state_machines(
            record_sm=self.record_sm,
            detection_sm=self.detection_sm,
            plugin_sm=self.plugin_sm,
        )
        
        # 设置状态变化回调
        self.main_sm.on_state_change = self._on_main_state_change
        self.main_sm.on_error = self._on_main_error
        
        print("✅ 状态机初始化完成")
    
    def _on_main_state_change(self, old_state: MainState, new_state: MainState):
        """主状态机状态变化回调"""
        print(f'状态变化：{old_state.name} → {new_state.name}')
        
        # 更新 UI
        self._update_ui_state(new_state)
    
    def _on_main_error(self, message: str):
        """主状态机错误回调"""
        print(f'状态机错误：{message}')
        self._show_warning(message)
    
    def _update_ui_state(self, state: MainState):
        """根据状态更新 UI"""
        if state == MainState.IDLE:
            self._enable_all_buttons()
        elif state == MainState.RECORDING:
            self._disable_conflict_buttons('record')
        elif state == MainState.DETECTING:
            self._disable_conflict_buttons('detection')
        elif state == MainState.VOYAGE:
            self._disable_conflict_buttons('voyage')
        elif state == MainState.PLUGIN:
            self._disable_conflict_buttons('plugin')
        elif state == MainState.STOPPED:
            self._disable_all_buttons()
    
    def _enable_all_buttons(self):
        """启用所有按钮"""
        # 示例代码
        # self.ui.recordButton.setEnabled(True)
        # self.ui.detectionButton.setEnabled(True)
        # self.ui.voyageButton.setEnabled(True)
        pass
    
    def _disable_conflict_buttons(self, current_module: str):
        """禁用冲突的按钮"""
        # 示例代码
        if current_module == 'record':
            # self.ui.detectionButton.setEnabled(False)
            # self.ui.voyageButton.setEnabled(False)
            pass
        elif current_module == 'detection':
            # self.ui.recordButton.setEnabled(False)
            # self.ui.voyageButton.setEnabled(False)
            pass
        # ...
    
    def _disable_all_buttons(self):
        """禁用所有按钮"""
        # 示例代码
        pass
    
    def _show_warning(self, message: str):
        """显示警告对话框"""
        # from PySide6.QtWidgets import QMessageBox
        # QMessageBox.warning(self.ui, "警告", message)
        print(f"⚠️ 警告：{message}")
    
    # ========== 修改现有的启动函数 ==========
    
    def startRecordThread(self):
        """开始录制（修改版）"""
        # 新增：检查是否可以启动
        if not self.main_sm.can_start_module('record'):
            current = self.main_sm.get_current_module()
            self._show_warning(f"录制失败：{current} 模块正在运行")
            return
        
        # 启动状态机
        self.main_sm.start_module('record')
        
        # 原有的录制代码
        # ...
        
        print("✅ 开始录制")
    
    def startDetectionThread(self):
        """开始检测（修改版）"""
        # 新增：检查是否可以启动
        if not self.main_sm.can_start_module('detection'):
            current = self.main_sm.get_current_module()
            self._show_warning(f"检测失败：{current} 模块正在运行")
            return
        
        # 启动状态机
        self.main_sm.start_module('detection')
        
        # 原有的检测代码
        # ...
        
        print("✅ 开始检测")
    
    def startVoyageThread(self):
        """开始远洋（修改版）"""
        # 新增：检查是否可以启动
        if not self.main_sm.can_start_module('voyage'):
            current = self.main_sm.get_current_module()
            self._show_warning(f"远洋失败：{current} 模块正在运行")
            return
        
        # 启动状态机
        self.main_sm.start_module('voyage')
        
        # 原有的远洋代码
        # ...
        
        print("✅ 开始远洋")
    
    # ========== 修改现有的停止函数 ==========
    
    def stopThread(self):
        """停止当前模块（修改版）"""
        # 获取当前运行的模块
        current = self.main_sm.get_current_module()
        
        if current:
            # 停止状态机
            self.main_sm.stop_module(current)
            
            # 原有的停止代码
            # ...
            
            print(f"✅ 停止 {current} 模块")
        else:
            print("ℹ️ 没有模块在运行")
    
    def stopAllThread(self):
        """停止所有模块（修改版）"""
        # 停止所有状态机
        self.main_sm.stop_all()
        
        # 原有的停止代码
        # ...
        
        print("✅ 停止所有模块")
    
    # ========== 新增：状态查询函数 ==========
    
    def get_current_status(self):
        """获取当前状态"""
        return self.main_sm.get_status()
    
    def is_module_running(self, module_name: str):
        """检查模块是否正在运行"""
        return self.main_sm.is_module_running(module_name)
    
    # ========== 示例：完整的录制流程 ==========
    
    def record_example(self):
        """完整的录制流程示例"""
        # 1. 检查是否可以启动
        if not self.main_sm.can_start_module('record'):
            self._show_warning("无法启动录制")
            return
        
        # 2. 启动状态机
        self.main_sm.start_module('record')
        
        # 3. 启动录制状态机
        self.record_sm.start_recording()
        
        # 4. 开始实际录制
        # recorder.start()
        
        # 5. 录制中...
        # while self.record_sm.is_recording():
        #     event = get_event()
        #     self.record_sm.record_event(event)
        
        # 6. 停止录制
        # recorder.stop()
        self.record_sm.stop()
        
        # 7. 停止状态机
        self.main_sm.stop_module('record')
        
        # 8. 获取录制的事件
        # events = self.record_sm.get_recorded_events()
        
        print("✅ 录制完成")


# ========== 使用示例 ==========

if __name__ == '__main__':
    # 创建应用
    # app = QApplication(sys.argv)
    # ui = UIFuncWithStateMachine(app)
    
    # 模拟用户操作
    ui = UIFuncWithStateMachine(None)
    
    # 用户点击"开始录制"
    print("\n=== 用户点击'开始录制' ===")
    ui.startRecordThread()
    
    # 用户尝试点击"开始检测"（会失败）
    print("\n=== 用户尝试点击'开始检测' ===")
    ui.startDetectionThread()
    
    # 用户点击"停止"
    print("\n=== 用户点击'停止' ===")
    ui.stopThread()
    
    # 用户点击"开始检测"
    print("\n=== 用户点击'开始检测' ===")
    ui.startDetectionThread()
    
    # 查询状态
    print("\n=== 当前状态 ===")
    status = ui.get_current_status()
    print(status)
