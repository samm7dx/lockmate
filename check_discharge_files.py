import os
import hashlib

# Find discharge summary files and compute their SHA256
input_dir = 'C:/Users/samri/Secret-Wards-ToolKit/dev/input'
for root, dirs, files in os.walk(input_dir):
    for f in files:
        if 'discharge' in f.lower():
            filepath = os.path.join(root, f)
            with open(filepath, 'rb') as fp:
                sha256 = hashlib.sha256(fp.read()).hexdigest()
            print(f'{f}: {sha256[:16]}')