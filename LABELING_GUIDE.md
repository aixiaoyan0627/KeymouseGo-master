# 数据标注指南

## 📋 概述
您需要标注 `raw_images/` 目录下的 **25 张图片**，标注文件放到 `raw_labels/` 目录。

---

## 🚀 快速开始

### 步骤 1：下载标注工具
推荐使用 **LabelImg**：
- 下载地址：https://github.com/HumanSignal/labelImg/releases
- 找最新版本的 `.exe` 文件下载（Windows）

### 步骤 2：设置 LabelImg
1. 打开 LabelImg
2. 点击菜单 `View` → 勾选 `Auto Save mode`（自动保存）
3. 点击菜单 `Change Output Dir` → 选择 `d:\KeymouseGo-master\raw_labels`
4. 点击菜单 `Open Dir` → 选择 `d:\KeymouseGo-master\raw_images`
5. **重要**：点击菜单 `PascalVOC` → 切换为 `YOLO` 格式！

### 步骤 3：开始标注
1. 用鼠标在图片上框选目标
2. 输入类别名称（从下面的列表选择）
3. 按 `D` 键下一张，按 `A` 键上一张
4. 标注完所有图片即可！

---

## 🏷️ 类别列表（按顺序！）

| ID | 类别名称 | 说明 |
|----|-----------|------|
| 0 | baoxiang | 宝箱 |
| 1 | bujitong | 不吉通 |
| 2 | caofan | 操帆 |
| 3 | caofan1 | 操帆1 |
| 4 | danshui | 淡水 |
| 5 | haicao | 海草 |
| 6 | hanghaishi1 | 航海士1 |
| 7 | hanghaishi2 | 航海士2 |
| 8 | hanghaishi3 | 航海士3 |
| 9 | hanghaishi4 | 航海士4 |
| 10 | hanghaishi5 | 航海士5 |
| 11 | hanghaishi6 | 航海士6 |
| 12 | hongbao | 红包 |
| 13 | hongbao2 | 红包2 |
| 14 | huozai1 | 火灾1 |
| 15 | huozai2 | 火灾2 |
| 16 | jiabanzangluan | 夹板脏乱 |
| 17 | laji | 垃圾 |
| 18 | pofan | 破帆 |
| 19 | shijieditu | 世界地图 |
| 20 | shuyi | 鼠疫 |
| 21 | xiuzhenghangxiang | 修正航向 |
| 22 | yanhui | 宴会 |
| 23 | yuhuo | 余火 |

**注意**：类别顺序很重要！必须按上面的顺序！

---

## 📝 标注技巧

### 1. 如何框选
- 尽量紧贴图标边缘
- 不要框太大，也不要太小
- 每个图标单独一个框

### 2. 快速操作
- `W` - 开始画框
- `D` - 下一张图片
- `A` - 上一张图片
- `Ctrl+S` - 保存
- `Del` - 删除选中的框

### 3. 注意事项
- ✅ 每张图片只标注对应的图标（看文件名）
- ✅ 标注完成后检查一下 `raw_labels/` 目录，确保每个图片都有对应的 `.txt` 文件
- ✅ 如果标错了，删除对应的 `.txt` 文件重新标

---

## ✅ 检查清单

标注完成后，请确认：

- [ ] `raw_labels/` 目录下有 **25 个 .txt 文件**
- [ ] 每个文件名和 `raw_images/` 里的图片一一对应
- [ ] 没有标错类别

---

## 🎯 标注完成后

标注完成后，运行训练脚本：

```bash
python train_yolo.py
```

就这么简单！训练会自动开始，预计需要 30 分钟到 2 小时（取决于您的 GPU）。

---

## ❓ 常见问题

### Q1: 标注太麻烦，可以不标吗？
**A**: 不行！标注是训练的必要步骤，没有标注数据无法训练。

### Q2: 可以用半自动标注吗？
**A**: 第一次必须手动标。等训练出第一个模型后，可以用它来辅助标注。

### Q3: 标错了怎么办？
**A**: 删除对应的 `.txt` 文件，重新标就可以了。

### Q4: 标注需要多长时间？
**A**: 25 张图片，熟练的话 15-30 分钟就能完成。

---

需要帮助吗？有问题随时问！
