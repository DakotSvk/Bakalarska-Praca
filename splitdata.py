import os
import random
import shutil

base_path = r"C:\Bakalarka\dataset"
train_img_path = os.path.join(base_path, "train", "images")
train_lab_path = os.path.join(base_path, "train", "labels")

dirs = {
    "valid": 0.15,
    "test": 0.10
}

if not os.path.exists(train_img_path):
    print(f"Error: Could not find directory {train_img_path}. Check if photos are in the 'images' subdirectory.")
else:
    images = [f for f in os.listdir(train_img_path) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    random.shuffle(images)

    for mode, percentage in dirs.items():
        count = int(len(images) * percentage)
        to_move = images[:count]
        images = images[count:]

        dest_img = os.path.join(base_path, mode, "images")
        dest_lab = os.path.join(base_path, mode, "labels")
        
        os.makedirs(dest_img, exist_ok=True)
        os.makedirs(dest_lab, exist_ok=True)

        for img_name in to_move:
            shutil.move(os.path.join(train_img_path, img_name), os.path.join(dest_img, img_name))
            
            label_name = os.path.splitext(img_name)[0] + ".txt"
            label_src = os.path.join(train_lab_path, label_name)
            if os.path.exists(label_src):
                shutil.move(label_src, os.path.join(dest_lab, label_name))

    print(f"Done! Data has been split into {list(dirs.keys())}.")