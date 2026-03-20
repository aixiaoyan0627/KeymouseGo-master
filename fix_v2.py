
# -*- encoding:utf-8 -*-
import os
import yaml
import shutil
import random

print("=" * 60)
print("数据集修复 v2")
print("=" * 60)

# 正确类别
CORRECT_CLASSES = [
    'baoxiang', 'bujitong', 'caofan', 'caofan1', 'danshui',
    'haicao', 'hanghaishi1', 'hanghaishi2', 'hanghaishi3',
    'hanghaishi4', 'hanghaishi5', 'hanghaishi6', 'hongbao',
    'hongbao2', 'huozai1', 'huozai2', 'jiabanzangluan', 'laji',
    'pofan', 'shijieditu', 'shuyi', 'xiuzhenghangxiang', 'yanhui', 'yuhuo'
]

# 原始类别
ORIGINAL_CLASSES = [
    'dog', 'person', 'cat', 'tv', 'car', 'meatballs', 'marinara sauce',
    'tomato soup', 'chicken noodle soup', 'french onion soup', 'chicken breast',
    'ribs', 'pulled pork', 'hamburger', 'cavity',
    'baoxiang', 'bujitong', 'caofan', 'caofan1', 'danshui', 'haicao',
    'hanghaishi1', 'hanghaishi2', 'hanghaishi3', 'hanghaishi4', 'hanghaishi5',
    'hanghaishi6', 'hongbao', 'hongbao2', 'huozai1', 'huozai2', 'jiabanzangluan',
    'laji', 'pofan', 'shijieditu', 'shuyi', 'xiuzhenghangxian', 'yanhui', 'yuhuo'
]

# 建立映射
old_to_new = {}
for new_id, cls_name in enumerate(CORRECT_CLASSES):
    if cls_name in ORIGINAL_CLASSES:
        old_id = ORIGINAL_CLASSES.index(cls_name)
        old_to_new[old_id] = new_id
        print(f"映射: {cls_name} (old={old_id}) -&gt; new={new_id}")

print(f"\n共 {len(old_to_new)} 个类别")

# 清理旧目录
yolo_dir = "./yolo_training"
if os.path.exists(yolo_dir):
    shutil.rmtree(yolo_dir)

# 创建新目录
os.makedirs(yolo_dir)
os.makedirs(os.path.join(yolo_dir, "train", "images"))
os.makedirs(os.path.join(yolo_dir, "train", "labels"))
os.makedirs(os.path.join(yolo_dir, "val", "images"))
os.makedirs(os.path.join(yolo_dir, "val", "labels"))

# 获取图片
img_dir = "./raw_images"
label_dir = "./raw_labels"
images = [f for f in os.listdir(img_dir) if f.endswith(('.png', '.jpg'))]
random.seed(42)
random.shuffle(images)

val_num = max(1, int(len(images) * 0.1))
train_imgs = images[val_num:]
val_imgs = images[:val_num]

print(f"\n训练集: {len(train_imgs)} 张")
print(f"验证集: {len(val_imgs)} 张")

# 处理文件
def process_files(img_list, target_split):
    count = 0
    for img_file in img_list:
        # 复制图片
        src_img = os.path.join(img_dir, img_file)
        dst_img = os.path.join(yolo_dir, target_split, "images", img_file)
        shutil.copy(src_img, dst_img)
        
        # 处理标注
        label_file = os.path.splitext(img_file)[0] + ".txt"
        src_label = os.path.join(label_dir, label_file)
        dst_label = os.path.join(yolo_dir, target_split, "labels", label_file)
        
        if os.path.exists(src_label):
            with open(src_label, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) &gt;= 5:
                    old_id = int(parts[0])
                    if old_id in old_to_new:
                        new_id = old_to_new[old_id]
                        parts[0] = str(new_id)
                        new_line = ' '.join(parts) + '\n'
                        new_lines.append(new_line)
            
            with open(dst_label, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            count += 1
    return count

train_count = process_files(train_imgs, "train")
val_count = process_files(val_imgs, "val")

print(f"\n处理完成: 训练集 {train_count}, 验证集 {val_count}")

# 生成 yaml
yaml_data = {
    "path": os.path.abspath(yolo_dir),
    "train": "train/images",
    "val": "val/images",
    "nc": len(CORRECT_CLASSES),
    "names": CORRECT_CLASSES
}

yaml_path = os.path.join(yolo_dir, "dataset.yaml")
with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)

print(f"\n已生成: {yaml_path}")
print(f"类别数: {len(CORRECT_CLASSES)}")
print("\n" + "=" * 60)
print("✅ 修复完成！")
