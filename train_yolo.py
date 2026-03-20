# -*- encoding:utf-8 -*-
"""
YOLO 一键训练脚本
- 支持数据增强（解决光影问题）
- 自动准备数据集
- 自动训练模型
"""
import os
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'
import shutil
import random
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from ultralytics import YOLO
import yaml
import argparse
from tqdm import tqdm
from loguru import logger

# ===================== 核心配置（已自动配置，无需修改） =====================
CONFIG = {
    # 原始图片路径（20多张图片放这里，支持jpg/png格式）
    "raw_images_path": "./raw_images",
    # 标注文件路径（YOLO格式的txt文件，和图片同名，如xxx.jpg对应xxx.txt）
    "raw_labels_path": "./raw_labels",
    # 训练输出目录
    "output_dir": "./yolo_training",
    # 类别名称（包含LabelImg默认类别 + 我们的类别）
    "class_names": [
        'dog', 'person', 'cat', 'tv', 'car', 'meatballs', 'marinara sauce',
        'tomato soup', 'chicken noodle soup', 'french onion soup', 'chicken breast',
        'ribs', 'pulled pork', 'hamburger', 'cavity',
        'baoxiang', 'bujitong', 'caofan', 'caofan1', 'danshui', 'haicao',
        'hanghaishi1', 'hanghaishi2', 'hanghaishi3', 'hanghaishi4', 'hanghaishi5',
        'hanghaishi6', 'hongbao', 'hongbao2', 'huozai1', 'huozai2', 'jiabanzangluan',
        'laji', 'pofan', 'shijieditu', 'shuyi', 'xiuzhenghangxian', 'yanhui', 'yuhuo'
    ],
    # 增强后总数据集大小（25张原始图→增强到300张）
    "augment_total": 300,
    # 训练参数
    "epochs": 100,  # 训练轮数
    "batch_size": 8,  # 批次大小（根据显卡显存调整）
    "img_size": 640,  # 输入图片尺寸
    "device": -1,  # 0=GPU，-1=CPU（当前使用CPU训练）
}

# ===================== 数据增强函数（解决光影/特效/透明度问题） =====================
def adjust_brightness(img, factor=None):
    """调整亮度"""
    if factor is None:
        factor = random.uniform(0.7, 1.3)
    return ImageEnhance.Brightness(img).enhance(factor)


def adjust_contrast(img, factor=None):
    """调整对比度"""
    if factor is None:
        factor = random.uniform(0.7, 1.3)
    return ImageEnhance.Contrast(img).enhance(factor)


def adjust_gamma(img, gamma=None):
    """伽马矫正"""
    if gamma is None:
        gamma = random.uniform(0.8, 1.2)
    img_np = np.array(img) / 255.0
    img_np = np.power(img_np, gamma) * 255.0
    return Image.fromarray(img_np.astype(np.uint8))


def apply_blur(img, radius=None):
    """轻微模糊"""
    if radius is None:
        radius = random.uniform(0, 1)
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def adjust_sharpness(img, factor=None):
    """调整锐度"""
    if factor is None:
        factor = random.uniform(0.5, 1.5)
    return ImageEnhance.Sharpness(img).enhance(factor)


def flip_horizontal(img):
    """水平翻转"""
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def augment_image(image_path, label_path, save_dir, aug_index):
    """
    对单张图片进行增强，生成多种光影/透明度/特效变体
    """
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"无法读取图片: {image_path}")
        return False
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img)
    img_name = os.path.basename(image_path).split(".")[0]
    ext = os.path.basename(image_path).split(".")[-1]

    # 定义增强策略（覆盖光影、特效）
    aug_strategies = [
        adjust_brightness,
        adjust_contrast,
        adjust_gamma,
        apply_blur,
        adjust_sharpness,
        flip_horizontal,
    ]

    # 随机选择1-3种增强策略组合
    selected_augs = random.sample(aug_strategies, k=random.randint(1, 3))
    aug_img = img_pil
    
    for aug_func in selected_augs:
        try:
            result = aug_func(aug_img)
            if result is not None:
                aug_img = result
        except Exception as e:
            logger.debug(f"增强策略 {aug_func.__name__} 失败: {e}")
            continue

    # 保存增强后的图片
    aug_img_path = os.path.join(save_dir, f"{img_name}_aug{aug_index}.{ext}")
    aug_img.save(aug_img_path)

    # 复制标注文件（增强不改变标注位置）
    label_save_dir = save_dir.replace("images", "labels")
    os.makedirs(label_save_dir, exist_ok=True)
    aug_label_path = os.path.join(label_save_dir, f"{img_name}_aug{aug_index}.txt")
    shutil.copy(label_path, aug_label_path)
    
    return True

# ===================== 数据整理与增强主函数 =====================
def prepare_dataset():
    logger.info("=" * 60)
    logger.info("开始准备数据集")
    logger.info("=" * 60)
    
    # 1. 创建目录结构
    dirs = [
        CONFIG["output_dir"],
        os.path.join(CONFIG["output_dir"], "train/images"),
        os.path.join(CONFIG["output_dir"], "train/labels"),
        os.path.join(CONFIG["output_dir"], "val/images"),
        os.path.join(CONFIG["output_dir"], "val/labels"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # 2. 获取原始数据列表
    raw_images = [f for f in os.listdir(CONFIG["raw_images_path"]) if f.endswith(("jpg", "png", "jpeg", "bmp"))]
    if len(raw_images) == 0:
        raise ValueError(f"原始图片目录为空，请检查: {CONFIG['raw_images_path']}")
    
    logger.info(f"找到 {len(raw_images)} 张原始图片")

    # 3. 检查标注文件
    valid_images = []
    for img_file in raw_images:
        label_file = os.path.splitext(img_file)[0] + ".txt"
        label_path = os.path.join(CONFIG["raw_labels_path"], label_file)
        if os.path.exists(label_path):
            valid_images.append(img_file)
        else:
            logger.warning(f"跳过: {img_file} (缺少标注文件)")
    
    if len(valid_images) == 0:
        raise ValueError("没有找到有效的图片+标注对！")
    
    logger.info(f"有效图片: {len(valid_images)} 张")

    # 4. 数据增强（生成足够的训练样本）
    logger.info(f"开始数据增强，目标: {CONFIG['augment_total']} 张")
    aug_count = 0
    failed_count = 0
    
    with tqdm(total=CONFIG['augment_total'], desc="数据增强进度") as pbar:
        while aug_count < CONFIG["augment_total"]:
            for img_file in valid_images:
                if aug_count >= CONFIG["augment_total"]:
                    break
                
                img_path = os.path.join(CONFIG["raw_images_path"], img_file)
                label_file = os.path.splitext(img_file)[0] + ".txt"
                label_path = os.path.join(CONFIG["raw_labels_path"], label_file)
                
                # 生成增强图片
                success = augment_image(
                    img_path, 
                    label_path, 
                    os.path.join(CONFIG["output_dir"], "train/images"), 
                    aug_count
                )
                
                if success:
                    aug_count += 1
                    pbar.update(1)
                else:
                    failed_count += 1

    logger.info(f"数据增强完成: 成功 {aug_count} 张, 失败 {failed_count} 张")

    # 5. 复制原始图片到训练集，并划分验证集（10%）
    logger.info("划分训练/验证集")
    val_count = max(1, int(len(valid_images) * 0.1))
    val_samples = random.sample(valid_images, k=val_count)
    
    for img_file in valid_images:
        img_path = os.path.join(CONFIG["raw_images_path"], img_file)
        label_file = os.path.splitext(img_file)[0] + ".txt"
        label_path = os.path.join(CONFIG["raw_labels_path"], label_file)
        
        # 划分训练/验证集
        if img_file in val_samples:
            target_img_dir = os.path.join(CONFIG["output_dir"], "val/images")
            target_label_dir = os.path.join(CONFIG["output_dir"], "val/labels")
        else:
            target_img_dir = os.path.join(CONFIG["output_dir"], "train/images")
            target_label_dir = os.path.join(CONFIG["output_dir"], "train/labels")
        
        shutil.copy(img_path, target_img_dir)
        shutil.copy(label_path, target_label_dir)

    # 6. 生成YOLO配置文件（yaml）
    yaml_data = {
        "path": os.path.abspath(CONFIG["output_dir"]),
        "train": "train/images",
        "val": "val/images",
        "nc": len(CONFIG["class_names"]),
        "names": CONFIG["class_names"]
    }
    yaml_path = os.path.join(CONFIG["output_dir"], "dataset.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
    
    logger.info(f"数据集配置文件已生成: {yaml_path}")
    logger.info("=" * 60)
    logger.info("数据集准备完成！")
    logger.info("=" * 60)
    
    return yaml_path

# ===================== 模型训练函数 =====================
def train_yolo(yaml_path):
    logger.info("=" * 60)
    logger.info("开始训练 YOLO 模型")
    logger.info("=" * 60)
    
    # 加载预训练YOLOv8模型
    model = YOLO("yolov8s.pt")  # s=小模型，m=中模型，l=大模型（根据需求选）
    
    logger.info(f"使用模型: yolov8s.pt")
    logger.info(f"训练轮数: {CONFIG['epochs']}")
    logger.info(f"批次大小: {CONFIG['batch_size']}")
    logger.info(f"图片尺寸: {CONFIG['img_size']}")
    logger.info(f"设备: {'GPU' if CONFIG['device'] == 0 else 'CPU'}")
    
    # 开始训练
    try:
        results = model.train(
            data=yaml_path,
            epochs=CONFIG["epochs"],
            batch=CONFIG["batch_size"],
            imgsz=CONFIG["img_size"],
            device='cpu',  # 强制使用 CPU
            patience=20,  # 早停（20轮无提升则停止）
            save=True,    # 保存最佳模型
            project=CONFIG["output_dir"],
            name="yolov8_train",
            exist_ok=True
        )
        
        logger.info("=" * 60)
        logger.info("训练完成！")
        logger.info("=" * 60)
        
        # 查找最佳模型
        best_model_path = os.path.join(CONFIG["output_dir"], "yolov8_train", "weights", "best.pt")
        if os.path.exists(best_model_path):
            logger.info(f"最佳模型已保存: {best_model_path}")
            logger.info("")
            logger.info("使用方法:")
            logger.info(f'init_recognizer(yolo_model_path=r"{best_model_path}")')
        
        return results
        
    except Exception as e:
        logger.error(f"训练失败: {e}")
        raise

# ===================== 主函数 =====================
def main():
    parser = argparse.ArgumentParser(description="YOLO 一键训练脚本")
    parser.add_argument("--prepare-only", action="store_true", help="仅准备数据集，不训练")
    parser.add_argument("--train-only", action="store_true", help="仅训练（数据集已准备好）")
    args = parser.parse_args()
    
    # 设置日志
    logger.add("training.log", rotation="10 MB", encoding="utf-8")
    
    try:
        yaml_path = None
        
        if not args.train_only:
            yaml_path = prepare_dataset()
        
        if not args.prepare_only:
            if yaml_path is None:
                yaml_path = os.path.join(CONFIG["output_dir"], "dataset.yaml")
                if not os.path.exists(yaml_path):
                    raise FileNotFoundError(f"找不到数据集配置文件: {yaml_path}")
            
            train_yolo(yaml_path)
        
        logger.info("所有任务完成！")
        
    except Exception as e:
        logger.error(f"程序出错: {e}")
        raise


if __name__ == "__main__":
    main()
