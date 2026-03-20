# 状态机接入情况分析

## 📋 总体评估

### ✅ 已接入状态机的模块

| 模块 | 状态机 | 接入程度 | 说明 |
|------|--------|----------|------|
| **远洋自动化** | ✅ `VoyageStateMachine` | **完全接入** | 完整的状态机管理 |
| **死亡检测** | ✅ `DeathDetector` | **完全接入** | 高优先级全局事件 |
| **城市策略** | ✅ `CityStrategyExecutor` | **完全接入** | 状态机调用 |
| **动作执行** | ✅ `ActionExecutor` | **完全接入** | 状态机控制 |
| **脚本执行** | ✅ `ScriptExecutor` | **完全接入** | 状态机调度 |

### ❌ 未接入状态机的模块

| 模块 | 当前状态 | 问题 | 建议 |
|------|----------|------|------|
| **基础录制回放** | ❌ 无状态机 | 独立运行 | 需要接入 |
| **图像触发检测** | ❌ 简单循环 | 无状态管理 | 需要接入 |
| **插件系统** | ❌ 独立运行 | 可能与主程序冲突 | 需要接入 |
| **GUI 界面** | ❌ Qt 事件循环 | 与状态机分离 | 需要协调 |

---

## 🏗️ 现有状态机架构分析

### 1. 远洋状态机（`VoyageStateMachine`）

**位置**: `Util/voyage/state_machine_v2.py`

**状态定义**:
```python
class VoyageState(Enum):
    IDLE = auto()       # 空闲
    SAILING = auto()    # 航行中（A 状态）
    IN_CITY = auto()    # 城市中（C 状态）
    DEAD = auto()       # 死亡状态
    STOPPED = auto()    # 停止
    WAITING = auto()    # 等待
```

**状态转换**:
```
IDLE → SAILING (开始航行)
SAILING → IN_CITY (连续 10 秒检测不到 A 类图标)
IN_CITY → SAILING (城市处理完毕)
SAILING → DEAD (检测到救助图标)
DEAD → SAILING (复位脚本执行完毕)
SAILING → SAILING (A 状态图标缺失超 1 分钟 → 偏航复位)
IN_CITY → WAITING (重试达 3 次)
ANY → STOPPED (停止信号)
```

**管理的模块**:
- ✅ `ImageDetector` - 图像检测器
- ✅ `DeathDetector` - 死亡检测器
- ✅ `ActionExecutor` - 动作执行器
- ✅ `CityStrategyExecutor` - 城市策略
- ✅ `ScriptExecutor` - 脚本执行器

**优点**:
1. 清晰的状态定义和转换
2. 高优先级全局事件（死亡检测）
3. 完整的超时和重试机制
4. 策略模式支持不同航行模式

---

### 2. 检测循环封装（`DetectionLoop`）

**位置**: `Util/DetectionLoop.py`

**功能**: 对 `VoyageStateMachine` 的封装，保持与 GUI 的兼容性

**问题**:
- 只是简单封装，没有额外的状态管理
- 依赖远洋状态机，自身无独立状态

---

## ⚠️ 未接入状态机的模块分析

### 1. 基础录制回放模块

**位置**: `Recorder/`, `Event/`

**当前架构**:
```
用户操作 → 录制器 → 保存脚本
加载脚本 → 回放器 → 执行事件
```

**问题**:
- ❌ 无状态管理，直接执行
- ❌ 可能与图像检测冲突
- ❌ 无法处理中断和恢复
- ❌ 没有错误恢复机制

**建议架构**:
```python
class RecordState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()

class RecordStateMachine:
    def __init__(self):
        self.state = RecordState.IDLE
        self.recorder = Recorder()
        self.player = Player()
    
    def handle_event(self, event):
        if self.state == RecordState.IDLE:
            self._handle_idle(event)
        elif self.state == RecordState.RECORDING:
            self._handle_recording(event)
        elif self.state == RecordState.PLAYING:
            self._handle_playing(event)
        # ...
```

---

### 2. 图像触发检测模块

**位置**: `Util/DetectionLoop.py` (基础检测模式)

**当前架构**:
```python
while True:
    screenshot = take_screenshot()
    if detect_trigger_image(screenshot):
        execute_script(script_path)
    if detect_icon(screenshot):
        click_at(position)
    sleep(interval)
```

**问题**:
- ❌ 简单无限循环，无状态管理
- ❌ 无法处理复杂场景（如多个触发条件）
- ❌ 没有超时和重试机制
- ❌ 可能与远洋状态机冲突

**建议架构**:
```python
class DetectionState(Enum):
    IDLE = auto()
    DETECTING = auto()
    EXECUTING = auto()
    WAITING = auto()
    STOPPED = auto()

class DetectionStateMachine:
    def __init__(self, config):
        self.state = DetectionState.IDLE
        self.config = config
        self.detector = ImageDetector()
        self.executor = ScriptExecutor()
    
    def run_step(self):
        if self.state == DetectionState.DETECTING:
            self._run_detecting()
        elif self.state == DetectionState.EXECUTING:
            self._run_executing()
        # ...
```

---

### 3. 插件系统

**位置**: `Plugin/`

**当前架构**:
```python
class PluginManager:
    def __init__(self):
        self.plugins = []
    
    def load_plugin(self, plugin):
        self.plugins.append(plugin)
    
    def run(self):
        for plugin in self.plugins:
            plugin.execute()
```

**问题**:
- ❌ 插件独立运行，无统一调度
- ❌ 可能与主程序状态冲突
- ❌ 无法处理插件间的依赖
- ❌ 没有生命周期管理

**建议架构**:
```python
class PluginState(Enum):
    UNLOADED = auto()
    LOADED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()

class PluginContext:
    def __init__(self):
        self.state = PluginState.UNLOADED
        self.priority = 0
        self.dependencies = []

class PluginManager:
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.plugins = {}
    
    def register_plugin(self, plugin, context):
        # 由状态机统一管理插件
        self.state_machine.register_plugin(plugin, context)
```

---

### 4. GUI 界面

**位置**: `UIFunc.py`, `UIView.py`

**当前架构**:
```
Qt 事件循环 ← → 用户操作
    ↓
调用功能模块
```

**问题**:
- ❌ Qt 事件循环与状态机分离
- ❌ 用户操作可能打断状态机
- ❌ 状态变化无法同步到界面

**建议架构**:
```python
class GUIStateMachine:
    def __init__(self):
        self.state = GUIState.MAIN
        self.ui = UIFunc()
        self.detection_thread = DetectionLoop()
    
    def handle_user_action(self, action):
        if self.state == GUIState.MAIN:
            self._handle_main_action(action)
        elif self.state == GUIState.DETECTING:
            self._handle_detecting_action(action)
        # ...
    
    def update_ui_from_state(self):
        # 根据状态机状态更新界面
        if self.state == GUIState.DETECTING:
            self.ui.show_detection_ui()
        elif self.state == GUIState.RECORDING:
            self.ui.show_recording_ui()
```

---

## 🎯 推荐的统一状态机架构

### 顶层状态机（MainStateMachine）

```python
class MainState(Enum):
    IDLE = auto()           # 空闲
    RECORDING = auto()      # 录制中
    PLAYING = auto()        # 回放中
    DETECTING = auto()      # 检测中
    VOYAGE = auto()         # 远洋自动化
    PLUGIN = auto()         # 插件运行中
    STOPPED = auto()        # 停止

class MainStateMachine:
    def __init__(self):
        self.state = MainState.IDLE
        
        # 子状态机
        self.record_sm = RecordStateMachine()
        self.detection_sm = DetectionStateMachine()
        self.voyage_sm = VoyageStateMachine()
        self.plugin_sm = PluginStateMachine()
        
        # 共享资源
        self.detector = ImageDetector()
        self.executor = ScriptExecutor()
    
    def start_recording(self):
        if self.state == MainState.IDLE:
            self.state = MainState.RECORDING
            self.record_sm.start()
    
    def start_detection(self):
        if self.state == MainState.IDLE:
            self.state = MainState.DETECTING
            self.detection_sm.start()
    
    def start_voyage(self):
        if self.state == MainState.IDLE:
            self.state = MainState.VOYAGE
            self.voyage_sm.start()
    
    def handle_global_event(self, event):
        # 全局事件处理（如停止、暂停）
        if event == Event.STOP:
            self._stop_all()
        elif event == Event.PAUSE:
            self._pause_all()
    
    def _stop_all(self):
        self.record_sm.stop()
        self.detection_sm.stop()
        self.voyage_sm.stop()
        self.plugin_sm.stop()
        self.state = MainState.STOPPED
```

---

## 📊 模块冲突风险分析

### 当前风险

| 冲突场景 | 风险等级 | 描述 |
|----------|----------|------|
| **录制时启动检测** | 🔴 高 | 两个模块同时使用截图功能 |
| **检测时启动远洋** | 🔴 高 | 两个状态机同时运行 |
| **插件与主程序** | 🟡 中 | 插件可能修改全局状态 |
| **GUI 与后台** | 🟡 中 | 用户操作可能打断后台任务 |

### 典型冲突示例

```python
# 场景：用户同时启动录制和检测
# 线程 1: 录制模块
while recording:
    screenshot = take_screenshot()  # ← 冲突点 1
    save_event()

# 线程 2: 检测模块
while detecting:
    screenshot = take_screenshot()  # ← 冲突点 1
    if detect(screenshot):          # ← 资源竞争
        execute_script()
```

**问题**:
1. 同时截图导致性能下降
2. 截图内容不一致
3. 鼠标键盘事件混乱

---

## ✅ 解决方案

### 方案 1: 统一状态机（推荐）

**架构**:
```
MainStateMachine
├── RecordStateMachine
├── DetectionStateMachine
├── VoyageStateMachine (已存在)
└── PluginStateMachine
```

**优点**:
- ✅ 统一调度，避免冲突
- ✅ 清晰的状态转换
- ✅ 易于扩展和维护

**实现步骤**:
1. 创建 `MainStateMachine` 类
2. 将现有模块改造为子状态机
3. 实现状态转换逻辑
4. 更新 GUI 调用方式

---

### 方案 2: 互斥锁机制（临时方案）

**架构**:
```python
class ResourceManager:
    _instance = None
    
    def __init__(self):
        self.screenshot_lock = Lock()
        self.input_lock = Lock()
        self.current_owner = None
    
    def acquire_screenshot(self, owner):
        if self.screenshot_lock.acquire(timeout=5):
            self.current_owner = owner
            return True
        return False
```

**优点**:
- ✅ 实现简单
- ✅ 快速解决冲突

**缺点**:
- ❌ 治标不治本
- ❌ 可能导致死锁
- ❌ 难以维护

---

## 🎯 优先级建议

### P0 - 必须解决

1. **远洋状态机与检测循环的整合**
   - 现状：`DetectionLoop` 封装了 `VoyageStateMachine`
   - 问题：基础检测模式无状态机
   - 解决：统一使用状态机架构

2. **录制与检测的互斥**
   - 现状：可能同时运行
   - 问题：资源冲突
   - 解决：在 GUI 层面禁止同时启动

### P1 - 强烈建议

3. **插件系统状态管理**
   - 现状：独立运行
   - 问题：可能与主程序冲突
   - 解决：实现插件生命周期管理

4. **GUI 与状态机同步**
   - 现状：分离
   - 问题：状态不一致
   - 解决：实现状态同步机制

### P2 - 可选优化

5. **统一日志和错误处理**
   - 现状：各模块独立
   - 解决：由状态机统一管理

6. **性能监控**
   - 现状：无
   - 解决：状态机集成性能监控

---

## 📝 总结

### 现状

✅ **远洋自动化模块** - 已有完整的状态机实现，架构优秀

❌ **其他模块** - 大部分未接入状态机，存在冲突风险

### 建议

1. **短期**: 在 GUI 层面添加互斥检查，禁止冲突操作
2. **中期**: 为各模块实现子状态机
3. **长期**: 实现统一的 `MainStateMachine`

### 代码量估算

| 任务 | 预估代码量 | 时间 |
|------|------------|------|
| 录制状态机 | ~300 行 | 2 小时 |
| 检测状态机 | ~400 行 | 3 小时 |
| 插件状态机 | ~250 行 | 2 小时 |
| 主状态机 | ~200 行 | 1 小时 |
| GUI 整合 | ~300 行 | 2 小时 |
| **总计** | **~1450 行** | **10 小时** |

---

**最后更新**: 2026-03-10  
**作者**: AI Assistant
