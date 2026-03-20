
# -*- encoding:utf-8 -*-
import os
import yaml

# 正确的类别列表
CORRECT_CLASSES = [
    'baoxiang',
    'bujitong',
    'caofan',
    'caofan1',
    'danshui',
    'haicao',
    'hanghaishi1',
    'hanghaishi2',
    'hanghaishi3',
    'hanghaishi4',
    'hanghaishi5',
    'hanghaishi6',
    'hongbao',
    'hongbao2',
    'huozai1',
    'huozai2',
    'jiabanzangluan',
    'laji',
    'pofan',
    'shijieditu',
    'shuyi',
    'xiuzhenghangxiang',
    'yanhui',
    'yuhuo'
]

# LabelImg 默认类别（我们需要把这些映射到正确的）
LABELIMG_DEFAULT_CLASSES = [
    'dog', 'person', 'cat', 'tv', 'car', 'meatballs', 'marinara sauce',
    'tomato soup', 'chicken noodle soup', 'french onion soup', 'chicken breast',
    'ribs', 'pulled pork', 'hamburger', 'cavity'
]

# 构建完整的类别映射
ALL_CLASSES = LABELIMG_DEFAULT_CLASSES + CORRECT_CLASSES

# 生成 old_id -&gt; new_id 的映射
class_to_id = {cls: idx for idx, cls in enumerate(CORRECT_CLASSES)}
old_to_new = {}
for old_idx, cls_name in enumerate(ALL_CLASSES):
    if cls_name in class_to_id:
        old_to_new[old_idx] = class_to_id[cls_name]
        print(f"映射: {cls_name} -&gt; new_id={class_to_id[cls_name]}")

# 更新 dataset.yaml
yaml_path = "./yolo_training/dataset.yaml"
if os.path.exists(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    data['nc'] = len(CORRECT_CLASSES)
    data['names'] = CORRECT_CLASSES
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    print(f"\n已更新: {yaml_path}")

# 修复标注文件
labels_dirs = [
    "./yolo_training/train/labels",
    "./yolo_training/val/labels"
]

fixed_total = 0
for labels_dir in labels_dirs:
    if not os.path.exists(labels_dir):
        continue
    fixed_count = 0
    for filename in os.listdir(labels_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(labels_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            changed = False
            for line in lines:
                parts = line.strip().split()
                if len(parts) &gt;= 5:
                    old_id = int(parts[0])
                    if old_id in old_to_new:
                        new_id = old_to_new[old_id]
                        parts[0] = str(new_id)
                        new_lines.append(' '.join(parts) + '\n')
                        changed = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            if changed:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                fixed_count += 1
    fixed_total += fixed_count
    print(f"修复完成: {labels_dir} - {fixed_count} 个文件")

print(f"\n总计修复: {fixed_total} 个标注文件")
print("\n✅ 数据集配置已修复完成！")
