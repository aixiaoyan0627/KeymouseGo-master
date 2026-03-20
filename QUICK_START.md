# 智能识别模块快速使用指南

## 🚀 三步上手

### 1. 安装依赖
```bash
pip install ultralytics paddleocr
```

### 2. 初始化识别器（程序启动时调用一次）
```python
from Util.unified_recognizer import init_recognizer

# 初始化（默认智能路由模式）
init_recognizer(
    default_method="SMART",
    use_gpu=True,  # 有 GPU 就设为 True，没有就 False
)
```

### 3. 使用（完全兼容现有代码）
```python
from Util.unified_recognizer import find_image_on_screen

# 就是这么简单！自动选择：
# - imgsC/E/F/G → OCR
# - imgsA/B → YOLO
position = find_image_on_screen("imgsG/qingke.png")
```

---

## 🎯 智能路由规则

| 文件夹 | 内容类型 | 识别方法 | 说明 |
|--------|-----------|----------|------|
| **imgsC** | 文字 | **OCR** | 精准识别文字 |
| **imgsE** | 文字 | **OCR** | 精准识别文字 |
| **imgsF** | 文字 | **OCR** | 精准识别文字 |
| **imgsG** | 文字 | **OCR** | 精准识别文字 |
| **imgsA** | 图形 | **YOLO** | 测试模块 |
| **imgsB** | 图形 | **YOLO** | 测试模块 |
| 其他 | 未知 | 模板匹配 | 向后兼容 |

---

## 💡 使用示例

### 示例 1：完全自动化（推荐）
```python
from Util.unified_recognizer import init_recognizer, find_image_on_screen

# 初始化
init_recognizer()

# 自动选择 OCR（因为在 imgsG）
position = find_image_on_screen("imgsG/qingke.png")
if position:
    print(f"找到请客按钮（OCR）: {position}")

# 自动选择 YOLO（因为在 imgsA）
position = find_image_on_screen("imgsA/some_icon.png")
if position:
    print(f"找到图标（YOLO）: {position}")
```

### 示例 2：强制使用某种方法
```python
from Util.unified_recognizer import find_image_on_screen

# 强制用 OCR
position = find_image_on_screen("imgsG/qingke.png", method="OCR")

# 强制用模板匹配
position = find_image_on_screen("imgsG/qingke.png", method="TEMPLATE")
```

### 示例 3：高级用法 - 直接使用识别器
```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化
init_recognizer()
recognizer = get_recognizer()

# 使用检测接口
result = recognizer.detect("imgsG/qingke.png")

if result.success:
    print(f"成功！方法: {result.method.name}")
    print(f"位置: {result.position}")
    if result.text:
        print(f"识别到的文字: {result.text}")
    if result.confidence:
        print(f"置信度: {result.confidence:.2f}")
```

---

## ⚙️ 配置说明

### 初始化参数
```python
init_recognizer(
    default_method="SMART",  # 默认识别方法
    yolo_model_path=None,    # YOLO 模型路径（训练后设置）
    use_gpu=True,            # 是否使用 GPU
)
```

### 识别方法选项
| 方法 | 说明 |
|------|------|
| `SMART` | 智能路由（推荐，默认） |
| `TEMPLATE` | 模板匹配（原有方案） |
| `YOLO` | YOLO 目标检测 |
| `OCR` | OCR 文字识别 |
| `HYBRID` | 混合模式 |

---

## 📝 关于 YOLO 测试模块

### 现阶段（测试阶段）
- **imgsA/B 会自动使用 YOLO**
- 但**注意**：预训练的 YOLO 模型不认识您的游戏图标！
- 所以现阶段可能识别失败，这是**正常的**

### 如何让 YOLO 真正工作？
1. 收集截图（不同光影下）
2. 标注数据
3. 训练模型
4. 设置 `yolo_model_path` 参数

详细步骤请查看 `YOLO_OCR_GUIDE.md`

---

## ❓ 常见问题

### Q1: 没有 GPU 能用吗？
**A**: 可以！
```python
init_recognizer(use_gpu=False)
```

### Q2: OCR 速度慢怎么办？
**A**: OCR 确实比模板匹配慢一些，但：
- 准确度大幅提升（因为是直接读文字）
- 对光影变化鲁棒
- 建议先用着，后续可以优化

### Q3: 拼音文件名怎么办？
**A**: 自动处理！比如：
- `imgsG/qingke.png` → 自动识别文字「请客」

### Q4: YOLO 现在识别失败？
**A**: 正常！因为：
- 预训练模型不认识您的游戏图标
- 这只是测试模块
- 等您准备好数据训练后就可以用了

---

## 🎯 推荐流程

### 现在（立即可以用）
1. 安装依赖
2. 初始化 `init_recognizer()`
3. 继续用，**imgsC/E/F/G 会自动用 OCR**
4. imgsA/B 暂时用 YOLO 测试（可能失败，没关系）

### 后续（看效果决定）
- 如果 OCR 效果很好，继续用
- 如果想让 YOLO 也工作，收集数据训练模型

---

## 📚 更多文档

- 详细指南：`YOLO_OCR_GUIDE.md`
- API 文档：查看代码注释
