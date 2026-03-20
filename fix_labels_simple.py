
# -*- encoding:utf-8 -*-
import os

print("=" * 60)
print("修复标注文件类别 ID")
print("=" * 60)

# 正确的类别列表
CORRECT_CLASSES = [
    'baoxiang', 'bujitong', 'caofan', 'caofan1', 'danshui',
    'haicao', 'hanghaishi1', 'hanghaishi2', 'hanghaishi3',
    'hanghaishi4', 'hanghaishi5', 'hanghaishi6', 'hongbao',
    'hongbao2', 'huozai1', 'huozai2', 'jiabanzangluan', 'laji',
    'pofan', 'shijieditu', 'shuyi', 'xiuzhenghangxiang', 'yanhui', 'yuhuo'
]

# LabelImg 默认类别（前面 15 个）
LABELIMG_DEFAULT = [
    'dog', 'person', 'cat', 'tv', 'car', 'meatballs', 'marinara sauce',
    'tomato soup', 'chicken noodle soup', 'french onion soup', 'chicken breast',
    'ribs', 'pulled pork', 'hamburger', 'cavity'
]

# 原始完整类别列表（LabelImg 默认 + 我们的）
ORIGINAL_FULL = LABELIMG_DEFAULT + CORRECT_CLASSES

# 建立映射：old_id -&gt; new_id
old_to_new = {}
for new_id, cls_name in enumerate(CORRECT_CLASSES):
    old_id = ORIGINAL_FULL.index(cls_name)
    old_to_new[old_id] = new_id
    print(f"映射: {cls_name} (old={old_id}) -&gt; new={new_id}")

print(f"\n共 {len(old_to_new)} 个类别需要映射")

# 删除旧的缓存
cache_files = [
    "./yolo_training/train/labels.cache",
    "./yolo_training/val/labels.cache"
]
for cache_file in cache_files:
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"\n已删除缓存: {cache_file}")

# 修复训练集标注
print("\n修复训练集标注...")
train_labels_dir = "./yolo_training/train/labels"
train_count = 0
for filename in os.listdir(train_labels_dir):
    if filename.endswith(".txt"):
        filepath = os.path.join(train_labels_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
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
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        train_count += 1

print(f"训练集: {train_count} 个文件已修复")

# 修复验证集标注
print("\n修复验证集标注...")
val_labels_dir = "./yolo_training/val/labels"
val_count = 0
for filename in os.listdir(val_labels_dir):
    if filename.endswith(".txt"):
        filepath = os.path.join(val_labels_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
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
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        val_count += 1

print(f"验证集: {val_count} 个文件已修复")

print("\n" + "=" * 60)
print("✅ 标注文件修复完成！")
print("=" * 60)
