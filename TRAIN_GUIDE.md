# YOLO 训练脚本使用说明

## 📋 目录
- [修复的问题](#修复的问题)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [配置说明](#配置说明)
- [数据标注](#数据标注)
- [运行训练](#运行训练)
- [使用训练好的模型](#使用训练好的模型)

---

## 🔧 修复的问题（相比原脚本）

### 1. ✅ 修复了 `putalpha` 返回值错误
- **原问题**: `img.putalpha()` 是原地操作，返回 `None`
- **修复**: 移除了有问题的透明度调整（因为游戏截图通常不是 RGBA）

### 2. ✅ 统一了增强策略返回类型
- **原问题**: 有些返回 PIL Image，有些返回 numpy 数组
- **修复**: 所有增强函数都返回 PIL Image

### 3. ✅ 增强了错误处理和进度显示
- 添加了 `tqdm` 进度条
- 添加了 `loguru` 日志记录
- 更完善的异常处理

### 4. ✅ 添加了命令行参数
- `--prepare-only`: 仅准备数据集
- `--train-only`: 仅训练模型

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install ultralytics opencv-python pillow pyyaml tqdm loguru albumentations
```

### 2. 准备目录和数据
```
KeymouseGo-master/
├── raw_images/        # 放原始图片（20+张）
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
├── raw_labels/        # 放标注文件（YOLO格式）
│   ├── img001.txt
│   ├── img002.txt
│   └── ...
└── train_yolo.py      # 训练脚本
```

### 3. 修改配置
打开 `train_yolo.py`，修改 `CONFIG` 部分：
```python
CONFIG = {
    "class_names": ["qingke_button", "exit_button", ...],  # 你的类别名称
    "augment_total": 300,      # 增强后总图片数
    "epochs": 100,              # 训练轮数
    "batch_size": 8,            # 根据显存调整
    "device": 0,                # 0=GPU, -1=CPU
}
```

### 4. 运行训练
```bash
python train_yolo.py
```

---

## 📁 目录结构

### 运行前需要准备：
```
KeymouseGo-master/
├── raw_images/        # 您的原始图片
│   ├── image1.jpg
│   ├── image2.png
│   └── ...
├── raw_labels/        # 对应的标注文件
│   ├── image1.txt
│   ├── image2.txt
│   └── ...
└── train_yolo.py
```

### 运行后自动生成：
```
KeymouseGo-master/
├── yolo_training/
│   ├── dataset.yaml          # 数据集配置
│   ├── train/
│   │   ├── images/           # 训练图片（原始+增强）
│   │   └── labels/           # 训练标注
│   ├── val/
│   │   ├── images/           # 验证图片
│   │   └── labels/           # 验证标注
│   └── yolov8_train/
│       └── weights/
│           ├── best.pt        # ⭐ 最佳模型（用这个！）
│           └── last.pt        # 最后一轮模型
└── training.log               # 训练日志
```

---

## ⚙️ 配置说明

| 参数 | 说明 | 推荐值 |
|------|------|---------|
| `raw_images_path` | 原始图片目录 | `"./raw_images"` |
| `raw_labels_path` | 原始标注目录 | `"./raw_labels"` |
| `output_dir` | 训练输出目录 | `"./yolo_training"` |
| `class_names` | 类别名称列表 | 根据实际情况 |
| `augment_total` | 增强后总图片数 | `200-500` |
| `epochs` | 训练轮数 | `50-200` |
| `batch_size` | 批次大小 | `8-16`（根据显存） |
| `img_size` | 输入图片尺寸 | `640` |
| `device` | 设备 | `0`（GPU）或 `-1`（CPU） |

---

## 🏷️ 数据标注

### 标注工具推荐
- **LabelImg**: https://github.com/HumanSignal/labelImg
- **LabelStudio**: https://labelstud.io/
- **CVAT**: https://github.com/opencv/cvat

### YOLO 标注格式
每个 `.txt` 文件对应一张图片，格式如下：
```
<class_id> <x_center> <y_center> <width> <height>
```

例如：
```
0 0.5 0.5 0.2 0.3
1 0.3 0.7 0.15 0.2
```

**注意**: 坐标都是**归一化**的（0-1 之间）

### 标注建议
1. 每个图标都要标注完整
2. 尽量贴合图标边缘
3. 同一类别的标注要一致
4. 在不同光影下都要有标注

---

## 🏃 运行训练

### 完整运行（准备数据+训练）
```bash
python train_yolo.py
```

### 仅准备数据集
```bash
python train_yolo.py --prepare-only
```

### 仅训练（数据已准备好）
```bash
python train_yolo.py --train-only
```

### 训练过程中会看到
- 数据增强进度条
- 训练日志（保存到 `training.log`）
- 验证集指标
- 自动保存最佳模型

---

## 🎯 使用训练好的模型

训练完成后，最佳模型在：
```
yolo_training/yolov8_train/weights/best.pt
```

### 在您的代码中使用

```python
from Util.unified_recognizer import init_recognizer, get_recognizer

# 初始化时指定您的模型
init_recognizer(
    default_method="SMART",
    yolo_model_path=r"d:\KeymouseGo-master\yolo_training\yolov8_train\weights\best.pt",
    use_gpu=True,
)

# 正常使用即可！
from Util.unified_recognizer import find_image_on_screen

# 会自动使用您的模型识别 imgsA/B
position = find_image_on_screen("imgsA/your_icon.png")
```

---

## 💡 小技巧

### 1. 显存不足怎么办？
- 减小 `batch_size`（如从 16 改为 8）
- 减小 `img_size`（如从 640 改为 416）
- 使用 CPU 训练（`device: -1`，但会慢很多）

### 2. 训练效果不好怎么办？
- 增加原始图片数量（20张→50张）
- 增加标注质量
- 增加训练轮数（`epochs: 150`）
- 尝试更大的模型（`yolov8m.pt` 或 `yolov8l.pt`）

### 3. 如何查看训练效果？
- 查看 `training.log`
- 查看 `yolo_training/yolov8_train/` 下的图表
- 用验证集图片测试模型

---

## ❓ 常见问题

### Q1: 没有 GPU 能训练吗？
**A**: 能，但会很慢！建议：
- 先用少量数据测试
- 或者找有 GPU 的机器训练
- 训练好的模型可以在 CPU 上推理

### Q2: 需要多少张图片？
**A**: 建议每个类别：
- 最少: 20-30 张
- 推荐: 50-100 张
- 理想: 200+ 张

### Q3: 标注太麻烦怎么办？
**A**: 没办法，标注是必须的！但：
- 可以先标 20 张试试效果
- 效果好再继续标
- 或者用半自动标注工具

---

需要我解释其他部分吗？
