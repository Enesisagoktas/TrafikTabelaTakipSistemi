"""Sözde etiket: modelin kendi eğitim görsellerimizde bulduğu `diger_levha` kutularını etikete ekler.

Bizim (Hootbu) train görselleri yalnızca 20 sınıfı etiketliyor; öteki levhalar etiketsiz, yani modele "arka plan"
diye gösteriliyor. 21. sınıf (diger_levha) başka bir setten gelince bu bir çelişki olur. v6, güveni >= EŞİK olan ve
var olan hiçbir kutuyla çakışmayan diger_levha tespitlerini bulur; bunlar etiket olarak eklenir (sınıf 20).
İlk çalıştırmada orijinal etiketler <klasör>/labels_orig altına yedeklenir; tekrar çalıştırınca yedekten başlar.
Denetim için rastgele 60 sözde kutunun paftası yazılır (pafta.jpg).

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\sozde_etiket.py runs/detect/v6_devam/weights/best.pt [esik=0.5]
"""

import random
import shutil
import sys
from pathlib import Path

from PIL import Image
from ultralytics import YOLO

DATA = Path(__file__).resolve().parents[1] / "data" / "levha640"
FOLDERS = [DATA / "train", DATA / "ek" / "negatif"]
OTHER = 20  # diger_levha indeksi (data_v6.yaml)


def iou(a, b):
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    w, h = max(0, min(ax2, bx2) - max(ax1, bx1)), max(0, min(ay2, by2) - max(ay1, by1))
    return w * h / (a[2] * a[3] + b[2] * b[3] - w * h + 1e-9)


def main(weights, thr=0.5):
    model = YOLO(weights)
    added, images, sample = 0, 0, []
    for folder in FOLDERS:
        lbl, orig = folder / "labels", folder / "labels_orig"
        if not orig.exists():
            shutil.copytree(lbl, orig)
        for p in sorted((folder / "images").glob("*.jpg")):
            src = orig / f"{p.stem}.txt"
            rows = [r.split() for r in src.read_text().splitlines() if r.strip()] if src.exists() else []
            boxes = [tuple(map(float, r[1:])) for r in rows]
            r = model.predict(p, imgsz=640, conf=thr, verbose=False, device=0)[0]
            new = [tuple(map(float, b)) for c, b in zip(r.boxes.cls.tolist(), r.boxes.xywhn.tolist())
                   if int(c) == OTHER and all(iou(tuple(map(float, b)), o) < 0.3 for o in boxes)]
            if new:
                images += 1
                added += len(new)
                sample += [(p, b) for b in new]
            (lbl / f"{p.stem}.txt").write_text("".join(" ".join(r) + "\n" for r in rows) + "".join(f"{OTHER} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n" for x, y, w, h in new))
    random.seed(0)
    random.shuffle(sample)
    S, cols = 96, 12
    sheet = Image.new("RGB", (cols * S, max(1, -(-min(60, len(sample)) // cols)) * S), "white")
    for i, (p, (x, y, w, h)) in enumerate(sample[:60]):
        im = Image.open(p)
        W, H = im.size
        crop = im.crop((int((x - w * 0.65) * W), int((y - h * 0.65) * H), int((x + w * 0.65) * W), int((y + h * 0.65) * H)))
        crop.thumbnail((S - 4, S - 4))
        sheet.paste(crop, ((i % cols) * S + 2, (i // cols) * S + 2))
    out = Path(weights).parent.parent / "sozde_pafta.jpg"
    sheet.save(out, quality=85)
    print(f"{images} görsele {added} diger_levha kutusu eklendi (eşik {thr}); pafta: {out}")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.5)
