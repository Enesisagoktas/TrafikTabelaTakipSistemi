"""Zayıf sınıflar için hata analizi (orijinal test, CPU): kaçırılan/karışan levhalar ne oldu, ne kadar küçüktü,
yanlış pozitifler nereden geliyor; kaçırılanların kırpılmış ızgarası docs/img/kacirilanlar_<model>.jpg.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\hata_analizi.py runs/detect/v2/weights/best.pt
"""
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "docs" / "img"
WEAK = ["pedestrian_info", "speed70", "speed30", "giveway"]


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


if __name__ == "__main__":
    mpath = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/detect/v2/weights/best.pt")
    model = YOLO(ROOT / mpath)
    names = model.names
    fp, fn = {w: Counter() for w in WEAK}, {w: Counter() for w in WEAK}
    size_ok, size_miss = {w: [] for w in WEAK}, {w: [] for w in WEAK}
    crops = {w: [] for w in WEAK}
    for img in sorted((ROOT / "data/levha640/test/images").glob("*.jpg")):
        im = cv2.imread(str(img))
        h, w = im.shape[:2]
        gt = []
        for r in (ROOT / "data/levha640/test/labels" / f"{img.stem}.txt").read_text().splitlines():
            if r.strip():
                c, x, y, bw, bh = map(float, r.split())
                gt.append((names[int(c)], [(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h]))
        res = model(im, imgsz=640, conf=0.4, device="cpu", verbose=False)[0]
        pr = [(names[int(c)], b.tolist(), float(p)) for c, b, p in zip(res.boxes.cls, res.boxes.xyxy, res.boxes.conf)]
        for gname, gb in gt:  # kaçırma / karışma
            if gname not in WEAK:
                continue
            best = max(pr, key=lambda p: iou(p[1], gb), default=None)
            side = min(gb[2] - gb[0], gb[3] - gb[1])
            if best and iou(best[1], gb) >= 0.5 and best[0] == gname:
                size_ok[gname].append(side)
                continue
            got = best[0] if best and iou(best[1], gb) >= 0.5 else "hiçbir şey"
            fn[gname][got] += 1
            size_miss[gname].append(side)
            if len(crops[gname]) < 12:
                x1, y1, x2, y2 = map(int, gb)
                pad = max(10, int(side))
                c = im[max(0, y1 - pad):y2 + pad, max(0, x1 - pad):x2 + pad]
                c = cv2.resize(c, (160, 160))
                cv2.putText(c, f"-> {got[:12]}", (2, 152), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
                crops[gname].append(c)
        for pname, pb, _ in pr:  # yanlış pozitif
            if pname not in WEAK:
                continue
            best = max(gt, key=lambda g: iou(g[1], pb), default=None)
            if best and iou(best[1], pb) >= 0.5 and best[0] == pname:
                continue
            fp[pname][best[0] if best and iou(best[1], pb) >= 0.5 else "arka plan"] += 1
    for wk in WEAK:
        print(f"\n{wk}: doğru {len(size_ok[wk])}, kaçırılan/karışan {sum(fn[wk].values())} -> {dict(fn[wk])}")
        print(f"   yanlış pozitif {sum(fp[wk].values())} -> {dict(fp[wk])}")
        if size_ok[wk] and size_miss[wk]:
            print(f"   kısa kenar medyanı (px, 640): doğru {np.median(size_ok[wk]):.0f} | kaçırılan {np.median(size_miss[wk]):.0f}")
    rows = [np.hstack(crops[wk][:6] + [np.zeros((160, 160, 3), np.uint8)] * (6 - len(crops[wk][:6]))) for wk in WEAK if crops[wk]]
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / f"kacirilanlar_{mpath.parts[-3]}.jpg"), np.vstack(rows))
    print("\nızgara satırları:", [wk for wk in WEAK if crops[wk]])
