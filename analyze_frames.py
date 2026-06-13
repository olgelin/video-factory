#!/usr/bin/env python3
"""分析每帧的视觉密度 + 颜色分布"""
from PIL import Image
import numpy as np
import os

frames_dir = r'E:\Hermes-Agent\workspace\xiaoshan\video-factory\frames_v38'
files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])

sample = [files[i] for i in [0, 3, 7, 11, 15, 20, 25, 29] if i < len(files)]

print("=== 每帧详细视觉分析 ===")
for f in sample:
    img = np.array(Image.open(os.path.join(frames_dir, f)))
    h, w = img.shape[:2]
    edges = np.abs(np.diff(img.astype(int), axis=0)).sum() + np.abs(np.diff(img.astype(int), axis=1)).sum()
    edge = edges / (h*w*3*255)
    uniq = len(np.unique(img.reshape(-1, img.shape[-1] if img.ndim==3 else 1), axis=0))
    bri = img.mean()
    # 找最常见的3个颜色
    flat = img.reshape(-1, 3)
    unique, counts = np.unique(flat, axis=0, return_counts=True)
    sorted_idx = np.argsort(-counts)
    top3 = [(tuple(unique[i]), counts[i]) for i in sorted_idx[:3]]
    top_str = " | ".join([f"rgb{c}={n//1000}k" for c, n in top3])
    print(f"{f:<10} edge={edge:.2f} uniq={uniq:<6} bri={bri:.1f} | {top_str}")
