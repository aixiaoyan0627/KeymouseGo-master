# KeymouseGo 打包发布指南

## 目录
- [快速开始](#快速开始)
- [打包配置说明](#打包配置说明)
- [体积优化技巧](#体积优化技巧)
- [兼容性问题解决](#兼容性问题解决)
- [常见问题](#常见问题)

---

## 快速开始

### 方式一：使用自动化脚本（推荐）

1. **双击运行** `build_optimized.bat`
2. **选择打包方式**：
   - `1` - 优化版（推荐，体积小）
   - `2` - 标准版（兼容性最好）
   - `3` - 调试版（显示控制台）

### 方式二：手动打包

```bash
# 优化版（推荐）
pyinstaller --clean KeymouseGo_optimized.spec

# 标准版
pyinstaller --clean KeymouseGo_release.spec

# 调试版
pyinstaller --clean KeymouseGo.spec
```

打包完成后，可执行文件位于 `dist/KeymouseGo.exe`

---

## 打包配置说明

### KeymouseGo_optimized.spec（优化版）

**特点**：
- ✅ 剔除无用模块，体积减少约 50%
- ✅ 使用 UPX 压缩
- ✅ 显式导入所有必要依赖
- ✅ 包含所有资源文件

**适用场景**：正式发布、需要小体积

### KeymouseGo_release.spec（标准版）

**特点**：
- ✅ 包含所有模块
- ✅ 兼容性最好
- ✅ 体积较大

**适用场景**：遇到兼容性问题时使用

### KeymouseGo.spec（调试版）

**特点**：
- ✅ 显示控制台窗口
- ✅ 便于调试错误
- ✅ 不压缩

**适用场景**：开发调试、排查问题

---

## 体积优化技巧

### 1. 剔除无用模块

在 `KeymouseGo_optimized.spec` 中，我们剔除了以下模块：

```python
EXCLUDES = [
    'tkinter',           # 我们用 PySide6，不需要 tkinter
    'matplotlib',        # 如果不用绘图
    'scipy',             # 如果不用科学计算
    'IPython',           # 不需要交互式环境
    'unittest',          # 不需要测试框架
    'email',             # 不需要邮件功能
    # ... 更多
]
```

**效果**：体积减少约 30-40%

### 2. 使用 UPX 压缩

UPX 是一个开源的可执行文件压缩工具。

**步骤**：
1. 下载 UPX：https://github.com/upx/upx/releases
2. 解压到项目根目录的 `upx/` 文件夹
3. 确保 spec 文件中设置了 `upx=True`

**效果**：体积再减少约 20-30%

### 3. 剥离符号表

在 spec 文件中设置：
```python
strip=True  # 剥离符号表
```

**效果**：体积减少约 5-10%

### 4. 只打包必要的资源

确保只打包实际使用的资源文件：
```python
DATAS = [
    ('./assets', 'assets'),
    ('./imgsA', 'imgsA'),
    ('./imgsB', 'imgsB'),
    # ... 只包含需要的
]
```

---

## 兼容性问题解决

### 1. VC++ 运行库缺失

**问题**：在某些 Windows 系统上运行时提示缺失 `msvcp140.dll` 等文件

**解决方案**：

#### 方案 A：打包时包含 VC++ 运行库（推荐）

1. 下载 VC++ Redistributable：
   - https://aka.ms/vs/17/release/vc_redist.x64.exe

2. 将其放在安装包中，在首次运行时自动安装

#### 方案 B：让用户手动安装

在发布说明中提示用户安装：
> 运行前请先安装 [VC++ 2015-2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### 2. OpenCV DLL 缺失

**问题**：运行时提示找不到 OpenCV 的 DLL 文件

**解决方案**：
在 spec 文件的 `hiddenimports` 中显式添加：
```python
hiddenimports=[
    'cv2',
    'numpy',
    'numpy.core._multiarray_umath',
]
```

### 3. PySide6 模块缺失

**解决方案**：
```python
hiddenimports=[
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]
```

---

## 常见问题

### Q: 打包后运行报错 "ModuleNotFoundError"

**A**: 在 spec 文件的 `hiddenimports` 中添加缺失的模块

### Q: 打包后的文件太大怎么办？

**A**:
1. 使用 `KeymouseGo_optimized.spec`
2. 下载并使用 UPX 压缩
3. 检查是否打包了不必要的资源文件

### Q: 在 Win10 上能运行，Win11 上不行？

**A**: 确保用户安装了最新的 VC++ 运行库，或使用标准版打包配置

### Q: 如何调试打包后的程序？

**A**: 使用调试版打包配置（`KeymouseGo.spec`），它会显示控制台窗口

### Q: UPX 压缩后程序启动变慢？

**A**: UPX 压缩会在启动时解压，会有轻微延迟。如果在意启动速度，可以禁用 UPX（`upx=False`）

---

## 推荐发布流程

1. **测试**：在开发环境测试所有功能
2. **打包**：使用优化版配置打包
3. **测试**：在干净的 Windows 虚拟机上测试
4. **发布**：如果有问题，尝试标准版配置
5. **文档**：附上运行环境要求说明

---

## 参考链接

- PyInstaller 文档：https://pyinstaller.org/
- UPX 下载：https://github.com/upx/upx/releases
- VC++ Redistributable：https://aka.ms/vs/17/release/vc_redist.x64.exe
