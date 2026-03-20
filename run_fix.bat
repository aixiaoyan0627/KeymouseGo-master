
@echo off
chcp 65001 &gt;nul
echo ============================================================
echo 开始修复数据集
echo ============================================================

python -c "import os, yaml, shutil, random; CORRECT = ['baoxiang','bujitong','caofan','caofan1','danshui','haicao','hanghaishi1','hanghaishi2','hanghaishi3','hanghaishi4','hanghaishi5','hanghaishi6','hongbao','hongbao2','huozai1','huozai2','jiabanzangluan','laji','pofan','shijieditu','shuyi','xiuzhenghangxiang','yanhui','yuhuo']; ORIGINAL = ['dog','person','cat','tv','car','meatballs','marinara sauce','tomato soup','chicken noodle soup','french onion soup','chicken breast','ribs','pulled pork','hamburger','cavity','baoxiang','bujitong','caofan','caofan1','danshui','haicao','hanghaishi1','hanghaishi2','hanghaishi3','hanghaishi4','hanghaishi5','hanghaishi6','hongbao','hongbao2','huozai1','huozai2','jiabanzangluan','laji','pofan','shijieditu','shuyi','xiuzhenghangxian','yanhui','yuhuo']; old2new = {}; [old2new.update({ORIGINAL.index(c):i}) for i,c in enumerate(CORRECT) if c in ORIGINAL]; yolo_dir = './yolo_training'; os.path.exists(yolo_dir) and shutil.rmtree(yolo_dir); [os.makedirs(os.path.join(yolo_dir, s, d), exist_ok=True) for s in ['train','val'] for d in ['images','labels']]; img_dir = './raw_images'; lbl_dir = './raw_labels'; imgs = [f for f in os.listdir(img_dir) if f.endswith(('.png','.jpg'))]; random.seed(42); random.shuffle(imgs); val_n = max(1, int(len(imgs)*0.1)); train_imgs, val_imgs = imgs[val_n:], imgs[:val_n]; print(f'训练集: {len(train_imgs)}, 验证集: {len(val_imgs)}'); def proc(img_list, split): cnt=0; [ (shutil.copy(os.path.join(img_dir, f), os.path.join(yolo_dir, split, 'images', f)), (lambda lf: (os.path.exists(os.path.join(lbl_dir, lf)) and (lambda ll: (open(os.path.join(yolo_dir, split, 'labels', lf), 'w', encoding='utf-8').writelines([' '.join([str(old2new[int(p[0])])]+p[1:])+'\n' for l in ll if len((p=l.strip().split()))&gt;=5 and int(p[0]) in old2new])), open(os.path.join(lbl_dir, lf), 'r', encoding='utf-8').readlines()))) (os.path.splitext(f)[0]+'.txt'), cnt.__setitem__(0, cnt[0]+1) if os.path.exists(os.path.join(lbl_dir, os.path.splitext(f)[0]+'.txt')) else None) for f in img_list]; return cnt; print(f'训练处理: {proc(train_imgs, \"train\")}'); print(f'验证处理: {proc(val_imgs, \"val\")}'); yaml.dump({'path': os.path.abspath(yolo_dir), 'train': 'train/images', 'val': 'val/images', 'nc': len(CORRECT), 'names': CORRECT}, open(os.path.join(yolo_dir, 'dataset.yaml'), 'w', encoding='utf-8'), default_flow_style=False, allow_unicode=True); print('✅ 修复完成!')"

echo.
echo ============================================================
echo 开始训练
echo ============================================================

python simple_train.py

pause
