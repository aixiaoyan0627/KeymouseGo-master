# YOLO+OCR 图像识别模块使用指南

## 📋 目录
- [快速开始](#快速开始)
- [安装依赖](#安装依赖)
- [模块架构](#模块架构)
- [使用示例](#使用示例)
- [训练自己的 YOLO 模型](#训练自己的-yolo-模型)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 YOLO (Ultralytics)
pip install ultralytics

# 安装 OCR (二选一，推荐 PaddleOCR)
pip install paddleocr
# 或者
pip install easyocr
```

### 2. 基本使用

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化（程序启动时调用一次）
init_recognizer(
    default_method="TEMPLATE",  # 可以是 TEMPLATE/YOLO/OCR/HYBRID
    use_gpu=True,
)

# 获取识别器
recognizer = get_recognizer()

# 使用模板匹配（兼容现有代码）
from Util.unified_recognizer import find_image_on_screen

position = find_image_on_screen(
    template_path="imgsG/qingke.png",
    threshold=0.8,
)

# 或者使用 YOLO
result = recognizer.detect(
    target=["button", "icon"],
    method="YOLO",
)

# 或者使用 OCR
result = recognizer.detect(
    target="请客",
    method="OCR",
)

if result.success:
    print(f"找到目标: {result.position}")
```

---

## 📦 安装依赖

### 完整依赖安装

```bash
# 基础依赖（已有的）
pip install opencv-python numpy mss loguru

# YOLO 依赖
pip install ultralytics torch torchvision

# OCR 依赖（推荐 PaddleOCR）
pip install paddleocr paddlepaddle

# 如果 GPU 可用，安装 GPU 版本的 PyTorch
# 访问 https://pytorch.org/get-started/locally/ 获取对应命令
```

### 检查 GPU 是否可用

```python
import torch
print("CUDA 可用:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU 数量:", torch.cuda.device_count())
    print("GPU 名称:", torch.cuda.get_device_name(0))
```

---

## 🏗️ 模块架构

```
Util/
├── unified_recognizer.py    # 统一识别接口（推荐使用）
├── yolo_detector.py         # YOLO 检测器
├── ocr_recognizer.py        # OCR 识别器
└── ImageRecognition.py      # 原有模板匹配（保留）
```

### 识别方法对比

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **TEMPLATE** | 速度快、无需训练、CPU 即可 | 对光影变化敏感 | imgsE/F（稳定图标） |
| **YOLO** | 泛化能力强、抗光影变化 | 需要训练、需要 GPU | imgsA/G/B/C（变化大的图标） |
| **OCR** | 可以识别文字 | 速度较慢、只适用于文字 | 需要识别文字的场景 |
| **HYBRID** | 结合两者优点 | 稍复杂 | 想要最高准确率 |

---

## 💡 使用示例

### 示例 1：兼容现有代码（模板匹配）

```python
# 完全兼容现有代码，无需修改
from Util.unified_recognizer import find_image_on_screen

position = find_image_on_screen("imgsG/qingke.png")
if position:
    print(f"找到请客按钮: {position}")
```

### 示例 2：使用 YOLO 检测

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化
init_recognizer(default_method="YOLO")
recognizer = get_recognizer()

# 检测特定类别
result = recognizer.detect(
    target=["qingke_button", "exit_button"],
    method="YOLO",
    confidence_threshold=0.6,
)

if result.success:
    print(f"找到: {result.class_name}, 置信度: {result.confidence:.2f}")
    print(f"位置: {result.position}")
```

### 示例 3：使用 OCR 识别文字

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化
init_recognizer(default_method="OCR")
recognizer = get_recognizer()

# 识别特定文字
result = recognizer.detect(
    target="请客",
    method="OCR",
)

if result.success:
    print(f"找到文字: {result.text}")
    print(f"位置: {result.position}")
```

### 示例 4：混合模式（推荐）

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化
init_recognizer(default_method="HYBRID")
recognizer = get_recognizer()

# 先用 YOLO 检测，失败后用模板匹配
result = recognizer.detect(
    target="imgsG/qingke.png",
    method="HYBRID",
)

if result.success:
    print(f"识别成功，使用方法: {result.method.name}")
```

### 示例 5：直接使用 YOLO 检测器

```python
from Util.yolo_detector import YOLODetector

# 创建检测器
detector = YOLODetector(
    model_path="path/to/your/model.pt",  # 可选，用自己训练的模型
    use_gpu=True,
)

# 检测
import cv2
image = cv2.imread("screenshot.png")

results = detector.detect(
    image=image,
    class_names=["button", "icon"],
    confidence_threshold=0.5,
)

for result in results:
    print(f"检测到: {result['class_name']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"边界框: {result['bbox']}")
```

### 示例 6：直接使用 OCR 识别器

```python
from Util.ocr_recognizer import OCRRecognizer, OCREngine

# 创建识别器
recognizer = OCRRecognizer(
    engine=OCREngine.PADDLE,  # 或者 OCREngine.EASYOCR
    use_gpu=True,
)

# 识别
import cv2
image = cv2.imread("screenshot.png")

results = recognizer.recognize(image)

for result in results:
    print(f"文字: {result.text}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"位置: {result.bbox}")

# 查找特定文字
target_result = recognizer.find_text(
    image=image,
    target_text="请客",
    min_confidence=0.6,
)

if target_result:
    print(f"找到目标文字: {target_result.text}")
```

---

## 🎓 训练自己的 YOLO 模型

### 为什么需要训练？

YOLOv8 的预训练模型是用 COCO 数据集训练的，识别的是通用物体（人、车、狗等），**不认识游戏里的图标**。

您需要：
1. 收集游戏截图
2. 标注图标位置
3. 训练模型
4. 使用自己的模型

### 步骤 1：准备数据集

#### 1.1 收集截图
在不同光影下截图，建议每个图标准备 50-200 张截图。

#### 1.2 标注数据
使用标注工具标注图标位置：
- **LabelImg**: https://github.com/HumanSignal/labelImg
- **LabelStudio**: https://labelstud.io/
- **CVAT**: https://github.com/opencv/cvat

标注格式建议使用 YOLO 格式。

### 步骤 2：数据集结构

```
dataset/
├── images/
│   ├── train/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   └── val/
│       ├── img001.jpg
│       └── ...
└── labels/
    ├── train/
    │   ├── img001.txt
    │   ├── img002.txt
    │   └── ...
    └── val/
        ├── img001.txt
        └── ...
```

### 步骤 3：创建配置文件

创建 `dataset.yaml`：

```yaml
path: /path/to/dataset  # 数据集根目录
train: images/train      # 训练集图片（相对 path）
val: images/val          # 验证集图片（相对 path）

names:
  0: qingke_button       # 请客按钮
  1: exit_button         # 退出按钮
  2: map_button          # 地图按钮
  # ... 更多类别
```

### 步骤 4：训练模型

```python
from Util.yolo_detector import YOLODetector

detector = YOLODetector(use_gpu=True)

# 开始训练
results = detector.train(
    data_yaml="dataset.yaml",
    epochs=100,      # 训练轮数，建议 50-200
    imgsz=640,       # 图像大小
    batch=16,        # 批次大小，根据显存调整
    project="runs",
    name="keymousego",
)

# 训练完成后，模型在 runs/keymousego/weights/best.pt
```

### 步骤 5：使用训练好的模型

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 使用自己的模型
init_recognizer(
    default_method="YOLO",
    yolo_model_path="runs/keymousego/weights/best.pt",
    use_gpu=True,
)

recognizer = get_recognizer()

# 检测
result = recognizer.detect(
    target=["qingke_button", "exit_button"],
    method="YOLO",
)
```

---

## ❓ 常见问题

### Q1: 没有 GPU 能用吗？

**A**: 可以！但速度会比较慢。

```python
init_recognizer(use_gpu=False)
```

建议：
- 没有 GPU 的话，先用**增强版模板匹配**
- 或者在有 GPU 的机器上训练好模型，在 CPU 上推理（速度稍慢但能用）

### Q2: 不想训练模型怎么办？

**A**: 先用混合模式，或者先用增强版模板匹配。

```python
# 混合模式：先 YOLO（如果可用），再模板匹配
init_recognizer(default_method="HYBRID")
```

### Q3: 如何选择识别方法？

| 图片类别 | 错误率 | 推荐方法 |
|---------|--------|---------|
| imgsE/F | 低 | TEMPLATE |
| imgsA/G | ~10% | HYBRID 或 训练 YOLO |
| imgsB/C | ~15%+ | 训练 YOLO |

### Q4: 安装依赖失败怎么办？

**A**: 按顺序安装：

```bash
# 1. 先安装 PyTorch（根据官网选择适合你系统的版本）
# 访问 https://pytorch.org/get-started/locally/

# 2. 安装 YOLO
pip install ultralytics

# 3. 安装 OCR（二选一）
pip install paddleocr
# 或
pip install easyocr
```

### Q5: 训练模型需要多少张图片？

**A**: 建议每个类别 50-200 张，越多越好。

- 最少 30 张（能跑，但效果一般）
- 50-100 张（效果不错）
- 200+ 张（效果很好）

---

## 📚 参考资源

- **YOLOv8 官方文档**: https://docs.ultralytics.com/
- **PaddleOCR 文档**: https://github.com/PaddlePaddle/PaddleOCR
- **EasyOCR 文档**: https://github.com/JaidedAI/EasyOCR
- **LabelImg 标注工具**: https://github.com/HumanSignal/labelImg

---

## 💡 我的建议

### 阶段 1（现在）：
- 继续使用模板匹配
- 同时收集截图，为训练做准备

### 阶段 2（有数据后）：
- 标注 50-100 张 imgsA/G 的图片
- 训练一个小型 YOLO 模型
- 在 imgsA/G 上试用，看看效果

### 阶段 3（效果好的话）：
- 继续收集更多数据
- 训练完整的模型
- 逐步替换

---

需要我帮您实现其他部分吗？
