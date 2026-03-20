# 统一状态机架构使用指南

## 📋 架构概述

```
MainStateMachine (统一主状态机)
├── RecordStateMachine (录制状态机)
├── DetectionStateMachine (检测状态机)
├── VoyageStateMachine (远洋状态机 - 已有)
└── PluginStateMachine (插件状态机)
```

---

## 🎯 核心优势

### 1. 避免模块冲突
- ✅ 录制时无法启动检测
- ✅ 检测时无法启动远洋
- ✅ 插件运行时无法启动其他模块

### 2. 统一状态管理
- ✅ 所有模块状态集中管理
- ✅ 清晰的状态转换逻辑
- ✅ 统一的状态查询接口

### 3. 错误处理
- ✅ 统一错误日志
- ✅ 状态回滚机制
- ✅ 异常安全

---

## 🚀 快速开始

### 步骤 1: 导入状态机

```python
from Util.MainStateMachine import MainStateMachine, MainState
from Util.RecordStateMachine import RecordStateMachine
from Util.DetectionStateMachine import DetectionStateMachine
from Util.PluginStateMachine import PluginStateMachine
from Util.voyage.state_machine_v2 import VoyageStateMachine
```

### 步骤 2: 创建并配置状态机

```python
# 创建主状态机
main_sm = MainStateMachine()

# 创建子状态机
record_sm = RecordStateMachine()
detection_sm = DetectionStateMachine()
voyage_sm = VoyageStateMachine(config, detector, action_executor, strategy)
plugin_sm = PluginStateMachine()

# 设置子状态机引用
main_sm.set_sub_state_machines(
    record_sm=record_sm,
    detection_sm=detection_sm,
    voyage_sm=voyage_sm,
    plugin_sm=plugin_sm
)
```

### 步骤 3: 使用状态机

```python
# 启动录制
if main_sm.can_start_module('record'):
    main_sm.start_module('record')
    record_sm.start_recording()
    
    # 开始实际录制
    recorder.start()

# 尝试启动检测（会失败，因为录制中）
if not main_sm.can_start_module('detection'):
    print("❌ 录制中，无法启动检测")

# 停止录制
main_sm.stop_module('record')
recorder.stop()

# 现在可以启动检测了
if main_sm.can_start_module('detection'):
    main_sm.start_module('detection')
    detection_sm.start_detection()
```

---

## 📖 详细使用示例

### 示例 1: 录制模块

```python
from Util.RecordStateMachine import RecordStateMachine, RecordState

# 创建状态机
record_sm = RecordStateMachine()

# 设置回调
record_sm.on_state_change = lambda old, new: print(f'状态：{old.name} → {new.name}')
record_sm.on_error = lambda msg: print(f'错误：{msg}')

# 开始录制
if record_sm.start_recording():
    print("✅ 开始录制")
    
    # 录制事件
    while record_sm.is_recording():
        event = get_next_event()
        if event:
            record_sm.record_event(event)
    
    # 停止录制
    record_sm.stop()
    recorded_events = record_sm.get_recorded_events()
    
    # 保存事件
    save_events(recorded_events)

# 开始回放
events = load_events('script.txt')
if record_sm.start_playing(events):
    print("✅ 开始回放")
    
    while record_sm.is_playing():
        event = record_sm.get_next_event()
        if event:
            execute_event(event)
        else:
            break
    
    # 回放完成
    if record_sm.on_playback_finished:
        record_sm.on_playback_finished()
```

---

### 示例 2: 检测模块

```python
from Util.DetectionStateMachine import DetectionStateMachine, DetectionState

# 创建状态机
detection_sm = DetectionStateMachine()

# 配置触发
detection_sm.set_trigger_config(
    trigger_images=['trigger1.png', 'trigger2.png'],
    trigger_script='trigger_script.txt',
    icon_images=['icon1.png', 'icon2.png'],
    icon_positions={'icon1.png': (100, 200)}
)

# 设置回调
detection_sm.on_trigger_detected = lambda img, script: (
    print(f'检测到触发图：{img}'),
    execute_script(script)
)

detection_sm.on_icon_detected = lambda img, pos: (
    print(f'检测到图标：{img}'),
    click_at(pos)
)

# 开始检测
if detection_sm.start_detection():
    print("✅ 开始检测")
    
    # 检测循环
    while detection_sm.is_detecting():
        screenshot = take_screenshot()
        detection_sm.detect(screenshot)
        
        # 如果检测到触发图，等待脚本执行完毕
        if detection_sm.is_executing():
            wait_for_script_finish()
            detection_sm.script_execution_finished()
        
        sleep(0.5)
```

---

### 示例 3: 插件模块

```python
from Util.PluginStateMachine import PluginStateMachine, PluginState

# 创建状态机
plugin_sm = PluginStateMachine()

# 加载插件
plugin1 = MyPlugin1()
plugin2 = MyPlugin2()

plugin_sm.load_plugin(plugin1, priority=10)
plugin_sm.load_plugin(plugin2, priority=5)

# 启动所有插件
plugin_sm.start_all()

# 查询状态
status = plugin_sm.get_status()
print(status)
# {'MyPlugin1': {'state': 'RUNNING', 'priority': 10, 'error': None}, ...}

# 暂停特定插件
plugin_sm.pause_plugin('MyPlugin1')

# 恢复插件
plugin_sm.resume_plugin('MyPlugin1')

# 停止所有插件
plugin_sm.stop_all()

# 卸载所有插件
plugin_sm.unload_all()
```

---

### 示例 4: 远洋模块（已有）

```python
from Util.voyage.state_machine_v2 import VoyageStateMachine, VoyageState

# 远洋状态机已经存在，直接使用
voyage_sm = VoyageStateMachine(
    config=config,
    detector=detector,
    action_executor=action_executor,
    strategy=strategy,
    death_detector=death_detector,
)

# 初始化
if voyage_sm.initialize():
    print("✅ 远洋状态机初始化成功")
    
    # 运行
    while voyage_sm.is_running():
        voyage_sm.run_step()
        sleep(0.5)
```

---

## 🔄 主状态机协调示例

### 完整流程示例

```python
from Util.MainStateMachine import MainStateMachine

# 创建主状态机
main_sm = MainStateMachine()

# 设置状态变化回调
def on_state_change(old_state, new_state):
    print(f'主状态：{old_state.name} → {new_state.name}')
    update_ui_state(new_state)

main_sm.on_state_change = on_state_change

# 用户点击"开始录制"按钮
def on_start_record_clicked():
    if main_sm.can_start_module('record'):
        main_sm.start_module('record')
        record_sm.start_recording()
        recorder.start()
        update_ui("录制中...")
    else:
        show_error("无法启动录制：当前有其他模块在运行")

# 用户点击"开始检测"按钮
def on_start_detection_clicked():
    if main_sm.can_start_module('detection'):
        main_sm.start_module('detection')
        detection_sm.start_detection()
        start_detection_thread()
        update_ui("检测中...")
    else:
        current = main_sm.get_current_module()
        show_error(f"无法启动检测：{current} 模块正在运行")

# 用户点击"开始远洋"按钮
def on_start_voyage_clicked():
    if main_sm.can_start_module('voyage'):
        main_sm.start_module('voyage')
        if voyage_sm.initialize():
            start_voyage_thread()
            update_ui("远洋自动化中...")
        else:
            main_sm.stop_module('voyage')
            show_error("远洋初始化失败")
    else:
        current = main_sm.get_current_module()
        show_error(f"无法启动远洋：{current} 模块正在运行")

# 用户点击"停止"按钮
def on_stop_clicked():
    current_module = main_sm.get_current_module()
    if current_module:
        main_sm.stop_module(current_module)
        update_ui("已停止")
    else:
        # 停止所有
        main_sm.stop_all()
        update_ui("所有模块已停止")
```

---

## ⚠️ 冲突处理示例

### 场景 1: 录制时尝试启动检测

```python
# 当前状态：RECORDING
main_sm.start_module('record')
record_sm.start_recording()

# 用户尝试启动检测
if main_sm.can_start_module('detection'):
    # ❌ 这个条件不会满足
    main_sm.start_module('detection')
else:
    # ✅ 显示错误提示
    show_warning("录制中，无法启动检测")
```

### 场景 2: 强制停止所有模块

```python
# 用户点击"紧急停止"按钮
def on_emergency_stop():
    # 停止所有模块
    main_sm.stop_all()
    
    # 停止所有后台线程
    stop_all_threads()
    
    update_ui("已紧急停止")
```

---

## 📊 状态查询

### 查询主状态

```python
status = main_sm.get_status()
print(status)
# {
#     'main_state': 'RECORDING',
#     'modules': {
#         'record': {'running': True, 'paused': False, 'error': None},
#         'detection': {'running': False, 'paused': False, 'error': None},
#         'voyage': {'running': False, 'paused': False, 'error': None},
#         'plugin': {'running': False, 'paused': False, 'error': None}
#     }
# }
```

### 查询模块状态

```python
# 查询主状态机
print(main_sm.state)  # MainState.RECORDING

# 查询录制状态机
print(record_sm.ctx.state)  # RecordState.RECORDING

# 查询检测状态机
print(detection_sm.ctx.state)  # DetectionState.DETECTING

# 查询远洋状态机
print(voyage_sm.ctx.state)  # VoyageState.SAILING

# 查询插件状态机
print(plugin_sm.get_status())  # {'Plugin1': {...}, ...}
```

---

## 🎯 最佳实践

### 1. 始终检查状态

```python
# ❌ 错误：直接启动
record_sm.start_recording()

# ✅ 正确：先检查状态
if main_sm.can_start_module('record'):
    main_sm.start_module('record')
    record_sm.start_recording()
```

### 2. 处理状态转换失败

```python
if not main_sm.start_module('voyage'):
    current = main_sm.get_current_module()
    show_error(f"启动失败：{current} 模块正在运行")
    return
```

### 3. 使用回调更新 UI

```python
main_sm.on_state_change = lambda old, new: (
    update_ui_state(new),
    log_state_change(old, new)
)
```

### 4. 优雅地停止

```python
# ❌ 错误：直接退出
sys.exit()

# ✅ 正确：先停止所有模块
main_sm.stop_all()
cleanup_resources()
sys.exit()
```

---

## 🔧 集成到现有代码

### 最小改动方案

```python
# 在 KeymouseGo.py 或 UIFunc.py 中

# 1. 创建主状态机
main_sm = MainStateMachine()

# 2. 在所有启动函数前添加检查
def startRecordThread():
    if not main_sm.can_start_module('record'):
        QMessageBox.warning(self, "警告", "有其他模块在运行，无法录制")
        return
    
    main_sm.start_module('record')
    # 原有的录制代码...

def startDetectionThread():
    if not main_sm.can_start_module('detection'):
        QMessageBox.warning(self, "警告", "有其他模块在运行，无法检测")
        return
    
    main_sm.start_module('detection')
    # 原有的检测代码...

# 3. 在停止函数后更新状态
def stopThread():
    current = main_sm.get_current_module()
    if current:
        main_sm.stop_module(current)
    # 原有的停止代码...
```

---

## 📝 总结

### 核心要点

1. **统一协调**: 主状态机协调所有子状态机
2. **互斥检查**: 使用 `can_start_module()` 避免冲突
3. **状态查询**: 使用 `get_status()` 获取所有状态
4. **错误处理**: 统一错误日志和状态回滚

### 迁移路径

1. **阶段 1**: 在 GUI 层面添加互斥检查（快速解决）
2. **阶段 2**: 逐步集成各个状态机
3. **阶段 3**: 完全切换到新架构

### 预期效果

- ✅ 不再有模块冲突
- ✅ 清晰的状态管理
- ✅ 更好的错误处理
- ✅ 易于扩展和维护

---

**创建时间**: 2026-03-10  
**版本**: 1.0  
**作者**: AI Assistant
