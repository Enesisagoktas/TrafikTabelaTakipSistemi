"""Arka plan (levhasız) örnekler: kendi train görsellerimizin levha içermeyen kısımlarından kırpıntılar.

Veri setinde hiç arka plan görseli yok; modelin yanlış alarmlarının çoğu "boş yerde levha görmek"
(scripts/uygulama_esigi.py). Ultralytics ~%10 arka plan görseli önerir. Yalnızca train'den kırpılır (test sızıntısı yok).
v2'nin >= 0,6 güvenle levha gördüğü kırpıntı atılır (etiketlenmemiş gerçek levha olabilir); daha düşük güvenle bir şey
gördüğü kırpıntı "zor negatif" olarak tutulur. Çıktı: data/levha640/ek/negatif/{images,labels(boş)} + birleşik liste.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\negatif.py [her_kacinci=10]
"""

import shutil
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

from ek_veri import DATA, rebuild_list

SKIP_CONF = 0.6


def free_regions(W, H, boxes):
    """Hiçbir kutuyla (pay bırakılarak) kesişmeyen dört kenar şeridi; yeterince büyük olanlar."""
    pad = 0.05 * max(W, H)
    x1 = min(b[0] for b in boxes) - pad
    y1 = min(b[1] for b in boxes) - pad
    x2 = max(b[2] for b in boxes) + pad
    y2 = max(b[3] for b in boxes) + pad
    cands = [(0, 0, int(x1), H), (int(x2), 0, W, H), (0, 0, W, int(y1)), (0, int(y2), W, H)]
    return sorted(
        [c for c in cands if c[2] - c[0] >= 0.35 * W and c[3] - c[1] >= 0.35 * H],
        key=lambda c: -(c[2] - c[0]) * (c[3] - c[1]),
    )


if __name__ == "__main__":
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    model = YOLO(Path(__file__).resolve().parents[1] / "runs/detect/v2/weights/best.pt")
    out = DATA / "ek" / "negatif"
    shutil.rmtree(out, ignore_errors=True)
    (out / "images").mkdir(parents=True)
    (out / "labels").mkdir(parents=True)
    kept = hard = skipped = 0
    for i, img in enumerate(sorted((DATA / "train" / "images").glob("*.jpg"))):
        if i % step:
            continue
        im = cv2.imread(str(img))
        H, W = im.shape[:2]
        boxes = []
        for row in (DATA / "train" / "labels" / f"{img.stem}.txt").read_text().splitlines():
            if row.strip():
                _, x, y, w, h = map(float, row.split())
                boxes.append(((x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H))
        regions = free_regions(W, H, boxes) if boxes else []
        if not regions:
            continue
        a, b, c, d = regions[0]
        crop = im[b:d, a:c]
        res = model(crop, conf=0.25, device="cpu", verbose=False)[0]
        top = float(res.boxes.conf.max()) if len(res.boxes) else 0.0
        if top >= SKIP_CONF:
            skipped += 1
            continue
        hard += top > 0
        name = f"negatif_{img.stem}"
        cv2.imwrite(str(out / "images" / f"{name}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        (out / "labels" / f"{name}.txt").write_text("")
        kept += 1
    print(f"arka plan kırpıntısı: {kept} (zor negatif {hard}) | v2 >= {SKIP_CONF} gördüğü için atılan {skipped}")
    print("train_birlesik.txt satır:", rebuild_list([*__import__('yaml').safe_load((DATA / 'data.yaml').read_text(encoding='utf-8'))['names']]))
