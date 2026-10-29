"""Modeli UYGULAMANIN çalışma ayarlarıyla ölçer (tek kare): yanlış alarm ("halüsinasyon"), kaçırma, yakalama.

Uygulamadaki kurallar (mobile/lib/alerts.dart + main.dart): güven >= 0,6; speed30/50/70 >= 0,65, pedestrian_info
>= 0,70; kutu yüksekliği >= görüntünün %5'i. (5 karede 3 oylaması tek kareyle ölçülemez; gerçek uygulama daha temkinli.)
Eşleşme: aynı sınıf ve IoU >= 0,5 -> doğru. Eşleşmeyen tahmin -> yanlış alarm (başka bir levhanın üstündeyse
"yanlış sınıf", değilse "boş yerde"). Eşleşmeyen gerçek levha -> kaçırma.

Çalıştırma (ml/ klasöründe):
  .venv\\Scripts\\python scripts\\uygulama_esigi.py runs/detect/v2/weights/best.pt [data/levha640/data_temiz.yaml]
"""

import sys
from collections import Counter
from pathlib import Path

import yaml
from ultralytics import YOLO

ML = Path(__file__).resolve().parents[1]
MIN_CONF, MIN_H = 0.6, 0.05
FLOOR = {"speed30": 0.65, "speed50": 0.65, "speed70": 0.65, "pedestrian_info": 0.7}


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def test_images(data_yaml):
    cfg = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    root = ML / "data" / cfg["path"]
    t = root / cfg["test"]
    if t.suffix == ".txt":
        return [root / ln[2:] for ln in t.read_text(encoding="utf-8").split() if ln.startswith("./")], cfg["names"]
    return sorted(t.glob("*.jpg")), cfg["names"]


if __name__ == "__main__":
    model_path = ML / sys.argv[1]
    data_yaml = ML / (sys.argv[2] if len(sys.argv) > 2 else "data/levha640/data_temiz.yaml")
    imgs, names = test_images(data_yaml)
    model = YOLO(model_path, task="detect")
    tp = fn = fn_big = gt_big = 0
    fp = Counter()
    fp_cls = Counter()
    for img in imgs:
        lbl = Path(str(img).replace("\\images\\", "\\labels\\").replace("/images/", "/labels/")).with_suffix(".txt")
        gt = []
        for row in lbl.read_text().splitlines():
            if row.strip():
                c, x, y, w, h = map(float, row.split())
                gt.append((names[int(c)], (x - w / 2, y - h / 2, x + w / 2, y + h / 2), h))
        r = model(str(img), imgsz=640, conf=0.25, agnostic_nms=True, device="cpu", verbose=False)[0]  # telefondaki eklenti gibi
        preds = [
            (r.names[int(k)], b.tolist(), float(p))
            for k, b, p in zip(r.boxes.cls, r.boxes.xyxyn, r.boxes.conf)
            if float(p) >= max(MIN_CONF, FLOOR.get(r.names[int(k)], 0)) and float(b[3] - b[1]) >= MIN_H
        ]
        used = set()
        for name, box, _ in sorted(preds, key=lambda p: -p[2]):
            j = max(range(len(gt)), key=lambda i: iou(gt[i][1], box) if i not in used else -1, default=None)
            if j is not None and j not in used and iou(gt[j][1], box) >= 0.5 and gt[j][0] == name:
                used.add(j)
                tp += 1
            else:
                kind = "yanlış sınıf" if j is not None and iou(gt[j][1], box) >= 0.5 else "boş yerde"
                fp[kind] += 1
                fp_cls[name] += 1
        for i, (_, _, h) in enumerate(gt):
            big = h >= MIN_H
            gt_big += big
            if i not in used:
                fn += 1
                fn_big += big
    n_gt = tp + fn
    print(f"model: {sys.argv[1]} | test: {data_yaml.name} ({len(imgs)} görsel, {n_gt} levha)")
    print(f"doğru {tp} | yanlış alarm {sum(fp.values())} {dict(fp)} | kaçırma {fn}")
    print(f"kesinlik {tp / max(tp + sum(fp.values()), 1):.3f} | yakalama (tüm) {tp / max(n_gt, 1):.3f} | "
          f"yakalama (yükseklik >= %{MIN_H * 100:g}: {gt_big} levha) {(gt_big - fn_big) / max(gt_big, 1):.3f} | "
          f"100 görselde yanlış alarm {100 * sum(fp.values()) / len(imgs):.1f}")
    print("yanlış alarm sınıfları:", dict(fp_cls.most_common()))
