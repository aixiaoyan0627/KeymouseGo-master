# 增强版日志系统使用指南

## 目录
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [API 参考](#api-参考)
- [使用示例](#使用示例)

---

## 快速开始

### 1. 初始化日志系统

在程序启动时初始化增强日志系统：

```python
from Util.enhanced_logger import init_enhanced_logger

# 初始化（只需调用一次）
logger = init_enhanced_logger(
    log_dir="logs",              # 日志目录
    log_level="INFO",            # 日志级别：DEBUG/INFO/WARNING/ERROR
    save_failure_screenshots=True  # 是否保存失败截图
)
```

### 2. 获取日志器实例

在其他模块中使用：

```python
from Util.enhanced_logger import get_enhanced_logger

logger = get_enhanced_logger()
```

---

## 核心功能

### 1. 分级日志

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息

### 2. 按天分割日志文件

- `keymousego_YYYY-MM-DD.log`: 完整日志（DEBUG 及以上）
- `error_YYYY-MM-DD.log`: 错误日志（ERROR 级别）
- 自动保留 30 天

### 3. 失败截图自动保存

- 识别失败时自动保存截图
- 脚本执行失败时自动保存截图
- 截图保存到 `logs/screenshots/` 目录
- 自动清理 7 天前的旧截图

---

## API 参考

### `log_recognition()` - 记录识别结果

```python
context = logger.log_recognition(
    template_name="qingke.png",    # 模板名称
    success=True,                   # 是否识别成功
    position=(500, 300),           # 识别到的坐标
    confidence=0.95,                # 置信度
    region=(0, 0, 1920, 1080),     # 检测区域
    frame=screenshot                # 图像帧（用于保存截图）
)
```

**返回**: `RecognitionContext` 对象，包含所有识别信息

---

### `log_script_step()` - 记录脚本执行步骤

```python
context = logger.log_script_step(
    step_index=1,                   # 步骤索引
    step_type="FIND_AND_CLICK",     # 步骤类型
    params={"image": "qingke.png"}, # 步骤参数
    success=True,                    # 是否成功
    error_message=None,              # 错误信息（失败时）
    execution_time=0.5,              # 执行时间（秒）
    frame=screenshot                 # 图像帧（用于保存截图）
)
```

**返回**: `ScriptStepContext` 对象，包含所有步骤信息

---

### `log_state_transition()` - 记录状态机转换

```python
logger.log_state_transition(
    from_state="FIND_PORT",          # 源状态
    to_state="ENTER_PORT",           # 目标状态
    event="PORT_FOUND",              # 触发事件
    context_data={"port_name": "Qingdao"}  # 上下文数据
)
```

---

### `log_input_action()` - 记录输入操作

```python
logger.log_input_action(
    action_type="click",             # 操作类型：click/move/keypress
    position=(500, 300),             # 坐标
    key=None,                         # 按键（keypress 时用）
    success=True,                     # 是否成功
    error_message=None                # 错误信息
)
```

---

## 使用示例

### 示例 1: 图像识别模块集成

```python
from Util.enhanced_logger import get_enhanced_logger

class ImageRecognizer:
    def __init__(self):
        self.logger = get_enhanced_logger()
    
    def find_image(self, template_path, screenshot):
        # ... 识别逻辑 ...
        
        if found:
            self.logger.log_recognition(
                template_name=os.path.basename(template_path),
                success=True,
                position=(x, y),
                confidence=confidence,
                frame=screenshot
            )
            return (x, y)
        else:
            self.logger.log_recognition(
                template_name=os.path.basename(template_path),
                success=False,
                confidence=confidence,
                frame=screenshot
            )
            return None
```

---

### 示例 2: 脚本执行器集成

```python
from Util.enhanced_logger import get_enhanced_logger
import time

class ScriptExecutor:
    def __init__(self):
        self.logger = get_enhanced_logger()
    
    def execute_step(self, step, index, screenshot=None):
        start_time = time.time()
        
        try:
            # ... 执行步骤 ...
            
            execution_time = time.time() - start_time
            
            self.logger.log_script_step(
                step_index=index,
                step_type=step["type"],
                params=step.get("params", {}),
                success=True,
                execution_time=execution_time,
                frame=screenshot
            )
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.logger.log_script_step(
                step_index=index,
                step_type=step["type"],
                params=step.get("params", {}),
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                frame=screenshot
            )
            return False
```

---

### 示例 3: 状态机集成

```python
from Util.enhanced_logger import get_enhanced_logger

class StateMachine:
    def __init__(self):
        self.logger = get_enhanced_logger()
        self.current_state = "IDLE"
    
    def transition(self, event, context_data=None):
        old_state = self.current_state
        
        # ... 状态转换逻辑 ...
        
        self.logger.log_state_transition(
            from_state=old_state,
            to_state=self.current_state,
            event=event,
            context_data=context_data
        )
```

---

### 示例 4: 输入执行器集成

```python
from Util.enhanced_logger import get_enhanced_logger

class InputExecutor:
    def __init__(self):
        self.logger = get_enhanced_logger()
    
    def click(self, x, y):
        try:
            # ... 点击逻辑 ...
            
            self.logger.log_input_action(
                action_type="click",
                position=(x, y),
                success=True
            )
            return True
        except Exception as e:
            self.logger.log_input_action(
                action_type="click",
                position=(x, y),
                success=False,
                error_message=str(e)
            )
            return False
    
    def press_key(self, key):
        try:
            # ... 按键逻辑 ...
            
            self.logger.log_input_action(
                action_type="keypress",
                key=key,
                success=True
            )
            return True
        except Exception as e:
            self.logger.log_input_action(
                action_type="keypress",
                key=key,
                success=False,
                error_message=str(e)
            )
            return False
```

---

## 日志文件结构

```
logs/
├── keymousego_2026-03-07.log    # 当日完整日志
├── keymousego_2026-03-06.log    # 昨日日志
├── error_2026-03-07.log          # 当日错误日志
└── screenshots/
    ├── fail_20260307_143022_123456.png  # 识别失败截图
    └── script_fail_20260307_143500_654321.png  # 脚本失败截图
```

---

## 日志格式

```
2026-03-07 14:30:22.123 | INFO     | Util.ImageRecognition:find_image:150 - 识别成功 | 模板: qingke.png | 坐标: (500, 300) | 置信度: 0.95
2026-03-07 14:30:23.456 | ERROR    | Util.ImageRecognition:find_image:160 - 识别失败 | 模板: exit.png | 置信度: 0.30
2026-03-07 14:30:23.457 | ERROR    | Util.ImageRecognition:find_image:162 - 失败截图已保存: logs/screenshots/fail_20260307_143023_456789.png
```

---

## 最佳实践

1. **在程序启动时初始化日志系统**
2. **识别失败时一定要传入 frame 参数保存截图**
3. **脚本执行失败时传入 frame 和错误信息**
4. **使用正确的日志级别**：调试用 DEBUG，正常用 INFO，问题用 WARNING/ERROR
5. **定期检查 logs/ 目录大小，避免占用过多磁盘空间**
