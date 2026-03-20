
# -*- encoding:utf-8 -*-
import os

OUR_CLASSES = [
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

LABELIMG_CLASSES = [
    'dog', 'person', 'cat', 'tv', 'car', 'meatballs', 'marinara sauce', 
    'tomato soup', 'chicken noodle soup', 'french onion soup', 'chicken breast', 
    'ribs', 'pulled pork', 'hamburger', 'cavity',
    'baoxiang', 'bujitong', 'caofan', 'caofan1', 'danshui', 'haicao',
    'hanghaishi1', 'hanghaishi2', 'hanghaishi3', 'hanghaishi4', 'hanghaishi5',
    'hanghaishi6', 'hongbao', 'hongbao2', 'huozai1', 'huozai2', 'jiabanzangluan',
    'laji', 'pofan', 'shijieditu', 'shuyi', 'xiuzhenghangxian', 'yanhui', 'yuhuo'
]

old_to_new = {}
for i, class_name in enumerate(OUR_CLASSES):
    if class_name in LABELIMG_CLASSES:
        old_id = LABELIMG_CLASSES.index(class_name)
        old_to_new[old_id] = i
        print(f"Map: {class_name} -&gt; old={old_id}, new={i}")

labels_dir = "raw_labels"
fixed_count = 0

for filename in os.listdir(labels_dir):
    if filename.endswith(".txt") and filename != "classes.txt":
        filepath = os.path.join(labels_dir, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                old_class_id = int(parts[0])
                if old_class_id in old_to_new:
                    new_class_id = old_to_new[old_class_id]
                    parts[0] = str(new_class_id)
                    new_lines.append(' '.join(parts) + '\n')
                    changed = True
                else:
                    print(f"Warning: Unknown ID {old_class_id} in {filename}")
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            fixed_count += 1
            print(f"Fixed: {filename}")

print(f"\nFixed {fixed_count} label files!")

with open(os.path.join(labels_dir, "classes.txt"), 'w', encoding='utf-8') as f:
    for class_name in OUR_CLASSES:
        f.write(class_name + '\n')

print(f"Updated: raw_labels/classes.txt")
