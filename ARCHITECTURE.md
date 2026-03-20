# KeymouseGo 软件架构梳理

## 📋 软件概述
**KeymouseGo** - 大航海时代 4 远洋脚本自动化工具
- **核心功能**: 鼠标/键盘录制回放 + 图像识别 + YOLO 目标检测 + OCR 文字识别
- **运行平台**: Windows
- **开发语言**: Python 3.12
- **GUI 框架**: PySide6

---

## 🏗️ 核心架构模块

### 1️⃣ 主程序入口
- **文件**: `KeymouseGo.py`
- **功能**:
  - 程序启动入口
  - 支持两种模式：GUI 模式 / 检测模式
  - DPI 适配和字体设置
  - 处理 pynput 与 PySide6 的兼容性

### 2️⃣ GUI 界面模块
- **文件**: 
  - `UIFunc.py` - 界面逻辑控制
  - `UIView.py` - 界面布局（.ui 文件）
  - `UIFileDialogFunc.py` / `UIFileDialogView.py` - 文件对话框

### 3️⃣ 事件系统 (`Event/`)
- **Event.py** - 脚本事件基类
- **UniversalEvents.py** - 跨平台事件
- **WindowsEvents.py** - Windows 专属事件
- **功能**:
  - 鼠标事件（点击、移动、拖拽）
  - 键盘事件（按键、组合键）
  - 事件录制和回放

### 4️⃣ 录制模块 (`Recorder/`)
- **UniversalRecorder.py** - 跨平台录制器
- **WindowsRecorder.py** - Windows 专属录制器
- **globals.py** - 录制全局变量
- **功能**:
  - 实时录制鼠标/键盘操作
  - 保存为脚本文件
  - 支持全局快捷键

### 5️⃣ 插件系统 (`Plugin/`)
- **Interface.py** - 插件接口定义
- **Manager.py** - 插件管理器
- **功能**:
  - 支持第三方插件扩展
  - 插件加载/卸载
  - 插件沙箱隔离

### 6️⃣ 图像识别模块 (`Util/`)
#### 6.1 基础识别
- **ImageRecognition.py** - 图像匹配识别
- **ImageHash.py** - 图像哈希比对
- **OCR 识别**: `ocr_recognizer.py`

#### 6.2 YOLO 目标检测
- **yolo_detector.py** - YOLO 检测器封装
- **DetectionLoop.py** - 检测循环
- **DetectionConfig** - 检测配置类

#### 6.3 统一识别器
- **unified_recognizer.py** - 整合多种识别方式

### 7️⃣ 游戏专用模块 (`Util/voyage/`)
#### 7.1 状态机系统
- **state_machine.py** - 基础状态机
- **state_machine_v2.py** - 增强版状态机

#### 7.2 策略系统
- **strategies.py** - 基础策略
- **strategy_v3.py** - 第三代策略
- **city_strategy.py** - 城市交易策略

#### 7.3 执行器
- **executor.py** - 脚本执行器
- **action_executor.py** - 动作执行器
- **GameInputExecutor.py** - 游戏输入执行

#### 7.4 检测器
- **detector.py** - 基础检测器
- **death_detector.py** - 死亡检测

#### 7.5 UI 界面
- **ui_ocean_v2.py** - 远洋 UI v2
- **ui_ocean_v3.py** - 远洋 UI v3

#### 7.6 工具类
- **pinyin_converter.py** - 拼音转换
- **pinyin_mapping.py** - 拼音映射
- **script_validator.py** - 脚本验证
- **config.py** - 配置管理
- **enhanced_script.py** - 增强脚本

### 8️⃣ 工具类 (`Util/`)
- **Global.py** - 全局变量和常量
- **Parser.py** - 脚本解析器
- **RunScriptClass.py** - 脚本运行类
- **ClickedLabel.py** - 可点击标签
- **CoordinateTool.py** - 坐标工具
- **plugin_sandbox.py** - 插件沙箱
- **enhanced_logger.py** - 增强日志

### 9️⃣ 资源配置
- **assets/** - 国际化文件、音效
- **imgsA-G/** - 游戏图像资源
- **configs/** - 配置文件示例

---

## 🔄 执行流程

### 模式 1: GUI 录制回放
```
用户启动 → 加载界面 → 录制脚本 → 保存脚本 → 加载脚本 → 回放脚本
```

### 模式 2: 检测模式（长期运行）
```
启动检测模式 → 加载配置 → 实时截图 → 图像识别/YOLO 检测
    ↓
识别到触发图 → 暂停检测 → 执行脚本 → 恢复检测
    ↓
识别到图标 → 固定坐标点击
```

### 模式 3: 远洋脚本自动化
```
加载远洋脚本 → 初始化状态机 → 循环执行
    ↓
城市导航 → 交易操作 → 航行 → 随机事件处理
    ↓
死亡检测 → 异常处理 → 继续航行
```

---

## 📦 依赖库

### 核心依赖
- **PySide6** - GUI 框架
- **pynput** - 鼠标/键盘控制
- **ultralytics** - YOLOv8 目标检测
- **torch** - 深度学习框架
- **opencv-python** - 图像处理
- **Pillow** - 图像加载
- **numpy** - 数值计算
- **polars-lts-cpu** - 数据处理（兼容旧 CPU）

### 辅助依赖
- **loguru** - 日志记录
- **pyyaml** - YAML 配置解析
- **json5** - JSON5 配置解析
- **psutil** - 系统监控

---

## 🎯 关键特性

### 1. 图像识别
- **模板匹配**: 基于 OpenCV 的模板匹配
- **图像哈希**: 感知哈希快速比对
- **多尺度识别**: 支持不同分辨率
- **阈值控制**: 可调整识别灵敏度

### 2. YOLO 目标检测
- **实时检测**: 长期后台运行
- **触发机制**: 识别到目标执行脚本
- **批量处理**: 支持 24 种目标类别
- **CPU 优化**: 适配老款 CPU（需 polars-lts-cpu）

### 3. OCR 文字识别
- **游戏文字提取**: 识别游戏内文字信息
- **港口名称识别**: 自动识别当前港口
- **商品价格读取**: 读取交易价格

### 4. 脚本系统
- **录制回放**: 录制用户操作并回放
- **脚本编辑**: 支持手动编辑脚本
- **插件扩展**: 第三方插件支持
- **配置保存**: 保存/加载配置

### 5. 远洋自动化
- **状态机驱动**: 清晰的状态转换
- **策略模式**: 灵活的交易策略
- **死亡检测**: 自动处理战斗失败
- **航线规划**: 自动导航到目标港口

---

## 🛠️ 配置文件

### 1. detection_config.json5
```json5
{
  "trigger_image_paths": ["触发图片路径"],
  "trigger_script_path": "触发脚本路径",
  "icon_image_paths": ["图标图片路径"],
  "icon_click_positions": {"图标名": [x, y]},
  "detection_interval": 0.5,
  "confidence_threshold": 0.7
}
```

### 2. 远洋脚本配置（JSON5）
```json5
{
  "route": ["港口 1", "港口 2", "港口 3"],
  "trade_goods": ["商品 1", "商品 2"],
  "buy_threshold": 100,
  "sell_threshold": 150,
  "enable_death_detection": true
}
```

### 3. YOLO 数据集配置（YAML）
```yaml
path: D:\KeymouseGo-master\yolo_training
train: train/images
val: val/images
nc: 24
names:
  - baoxiang
  - bujitong
  - ...
```

---

## 📊 目录结构

```
KeymouseGo-master/
├── KeymouseGo.py          # 主程序入口
├── UIFunc.py              # 界面逻辑
├── UIView.py              # 界面布局
├── Event/                 # 事件系统
├── Recorder/              # 录制模块
├── Plugin/                # 插件系统
├── Util/                  # 工具模块
│   ├── voyage/            # 游戏专用模块
│   ├── yolo_detector.py   # YOLO 检测
│   ├── DetectionLoop.py   # 检测循环
│   └── ...
├── yolo_training/         # YOLO 训练数据
│   ├── dataset.yaml       # 数据集配置
│   ├── train/             # 训练集
│   └── val/               # 验证集
├── configs/               # 配置文件
├── imgsA-G/               # 图像资源
├── assets/                # 资源文件
└── logs/                  # 日志文件
```

---

## 🚀 使用场景

### 1. 脚本录制回放
- 录制游戏操作
- 批量重复操作
- 自动化任务

### 2. 图像触发脚本
- 识别到特定画面执行脚本
- 长时间挂机检测
- 自动响应游戏事件

### 3. 远洋自动化
- 自动航行贸易
- 自动处理随机事件
- 自动应对海盗战斗

### 4. YOLO 目标检测
- 识别游戏图标
- 检测光影变化
- 复杂场景识别

---

## ⚠️ 已知问题和解决方案

### 1. CPU 兼容性问题
**问题**: 老款 CPU 缺少 AVX2 等指令集导致崩溃  
**解决**: 安装 `polars-lts-cpu`
```cmd
pip uninstall polars -y
pip install polars-lts-cpu
```

### 2. Python 3.12 兼容性
**问题**: 部分库在 Python 3.12 上有兼容性问题  
**建议**: 使用 Python 3.10 或 3.11

### 3. pynput 与 PySide6 冲突
**解决**: 在主程序入口前禁用 shiboken feature 检查

---

## 🎓 开发指南

### 添加新识别目标
1. 收集训练图片（建议 20+ 张）
2. 使用 LabelImg 标注
3. 更新 `dataset.yaml`
4. 重新训练模型
5. 更新检测配置

### 添加新功能模块
1. 在 `Util/` 创建新模块
2. 实现统一接口
3. 在主程序中注册
4. 添加配置项

### 开发插件
1. 继承 `Plugin.Interface`
2. 实现必要的方法
3. 放入 `Plugin/` 目录
4. 通过管理器加载

---

## 📝 维护建议

1. **定期清理日志**: `logs/` 目录会快速增长
2. **备份配置文件**: 重要配置定期备份
3. **更新依赖库**: 定期检查更新
4. **测试兼容性**: 更新前在测试环境验证

---

## 🔮 未来扩展方向

1. **AI 增强**: 集成更多 AI 模型（如 GPT 辅助决策）
2. **云端同步**: 配置和脚本云端同步
3. **多游戏支持**: 扩展到其他游戏
4. **可视化编辑器**: 脚本可视化编辑
5. **性能优化**: 进一步提升识别速度

---

## 📞 支持和贡献

- **问题反馈**: GitHub Issues
- **功能建议**: GitHub Discussions
- **代码贡献**: Pull Request
- **文档完善**: 欢迎补充文档

---

**最后更新**: 2026-03-10  
**版本**: KeymouseGo v1.0 (优化版)
