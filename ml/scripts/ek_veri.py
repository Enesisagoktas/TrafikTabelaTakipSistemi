"""Dış veri setini eğitime güvenli şekilde ekler: sınıf eşleme, 640 px küçültme, test/valid kopyalarını ayıklama.

Kaynak, YOLO düzeninde olmalı (Roboflow dışa aktarması gibi): <kaynak>/data.yaml (names) + .../images/*.jpg
ve yanında .../labels/*.txt. Çıktı: data/levha640/ek/<ad>/{images,labels}. Ardından birleşik liste yeniden yazılır:
data/levha640/train_birlesik.txt (bizim train + tüm ek/*) ve data_v5.yaml (val/test bizim temiz setlerimiz).

Kopya kuralı (docs/veri_denetimi.md ile aynı): bizim valid/test görsellerinden birine phash uzaklığı <= 12 olan
görsel atılır (test sızıntısı olmasın); bizim train'den birine <= 4 olan da atılır (zaten var).

Çalıştırma (ml/ klasöründe):
  .venv\\Scripts\\python scripts\\ek_veri.py <kaynak_klasor> <ad> <esleme.json> [--atla sinif1,sinif2] [--at sinif3] [--arka-plan] [--diger]
esleme.json: {"kaynak_sinif_adi": "bizim_sinif_adi", ...}; eşlenmeyen kutular atılır (--diger yoksa).
--atla: bu kaynak sınıflarından birini içeren görsel tamamen atlanır (bizimkine benzeyen ama farklı tasarım).
--at: bu kaynak sınıflarının kutuları atılır, görsel kalır (levha olmayan sınıflar: trafik ışığı, araç...).
--arka-plan: eşlenen kutusu kalmayan görseller etiketsiz (arka plan) olarak tutulur. Yalnızca kaynak bütün
  levhaları etiketliyorsa kullan; yoksa etiketsiz kalan gerçek levhalar modele "levha değil" diye öğretilir.
--diger: eşlenmeyen (ve --at'ta olmayan) her kutu 21. sınıf `diger_levha` olur: tanınan ama uyarısı olmayan levha.
  Birleşik liste için data_v6.yaml (21 sınıf) yazılır. Kaynak bütün levhaları etiketliyorsa anlamlı (v6, 29 Ekim).
"""

import argparse
import json
import shutil
from pathlib import Path

import cv2
import imagehash
import numpy as np
import yaml
from PIL import Image

SIZE = 640
DATA = Path(__file__).resolve().parents[1] / "data" / "levha640"
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".ppm"}


def phash(path):
    with Image.open(path) as im:
        im.draft("L", (256, 256))
        return int(str(imagehash.phash(im)), 16)


def min_dist(h, arr):
    x = np.bitwise_xor(arr, np.uint64(h))
    return int(np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1).min())


def read_boxes(lbl):
    """YOLO satırları; çokgen (segmentasyon) satırları kutuya çevrilir."""
    boxes = []
    for row in lbl.read_text().splitlines() if lbl.exists() else []:
        p = row.split()
        if len(p) == 5:
            boxes.append((int(p[0]), *map(float, p[1:])))
        elif len(p) > 5 and len(p) % 2 == 1:
            xs, ys = list(map(float, p[1::2])), list(map(float, p[2::2]))
            x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
            boxes.append((int(p[0]), (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1))
    return boxes


def names_of(src):
    n = yaml.safe_load((src / "data.yaml").read_text(encoding="utf-8"))["names"]
    return n if isinstance(n, list) else [n[k] for k in sorted(n)]


def rebuild_list(ours):
    lines = [f"./train/images/{p.name}" for p in sorted((DATA / "train" / "images").glob("*.jpg"))]
    lines += [f"./{p.relative_to(DATA).as_posix()}" for p in sorted(DATA.glob("ek/*/images/*.jpg"))]
    (DATA / "train_birlesik.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    cfg = {"path": "levha640", "train": "train_birlesik.txt", "val": "val_temiz.txt", "test": "test_temiz.txt",
           "nc": len(ours), "names": ours}
    out = DATA / ("data_v6.yaml" if "diger_levha" in ours else "data_v5.yaml")  # v6: 21 sınıf
    out.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kaynak", type=Path)
    ap.add_argument("ad")
    ap.add_argument("esleme", type=Path)
    ap.add_argument("--atla", default="")
    ap.add_argument("--at", default="")
    ap.add_argument("--arka-plan", action="store_true")
    ap.add_argument("--diger", action="store_true")
    a = ap.parse_args()

    ours = yaml.safe_load((DATA / "data.yaml").read_text(encoding="utf-8"))["names"]
    if a.diger:
        ours = ours + ["diger_levha"]
    src_names = names_of(a.kaynak)
    mapping = json.loads(a.esleme.read_text(encoding="utf-8-sig"))  # Windows'ta yazılan dosyada BOM olabilir
    bad = [k for k, v in mapping.items() if k not in src_names or v not in ours]
    if bad:
        raise SystemExit(f"eşlemede bilinmeyen sınıf: {bad}")
    to_ours = {src_names.index(k): ours.index(v) for k, v in mapping.items()}
    skip = {src_names.index(s) for s in a.atla.split(",") if s}
    drop = {src_names.index(s) for s in a.at.split(",") if s}
    if a.diger:
        to_ours.update({i: ours.index("diger_levha") for i in range(len(src_names)) if i not in to_ours and i not in skip and i not in drop})

    hv = np.array([phash(p) for s in ("valid", "test") for p in (DATA / s / "images").glob("*.jpg")], dtype=np.uint64)
    ht = np.array([phash(p) for p in (DATA / "train" / "images").glob("*.jpg")], dtype=np.uint64)

    out = DATA / "ek" / a.ad
    shutil.rmtree(out, ignore_errors=True)
    (out / "images").mkdir(parents=True)
    (out / "labels").mkdir(parents=True)
    stats = dict(gorsel=0, eklendi=0, sizinti=0, train_kopyasi=0, atlandi=0, bos=0, kutu=0)
    per_class = {}
    for img in sorted(p for p in a.kaynak.rglob("*") if p.suffix.lower() in EXTS and p.parent.name == "images"):
        stats["gorsel"] += 1
        boxes = read_boxes(img.parent.parent / "labels" / f"{img.stem}.txt")
        if any(c in skip for c, *_ in boxes):
            stats["atlandi"] += 1
            continue
        kept = [(to_ours[c], *b) for c, *b in boxes if c in to_ours]
        if not kept and not a.arka_plan:
            stats["bos"] += 1
            continue
        h = phash(img)
        if min_dist(h, hv) <= 12:
            stats["sizinti"] += 1
            continue
        if min_dist(h, ht) <= 4:
            stats["train_kopyasi"] += 1
            continue
        im = cv2.imread(str(img))
        r = SIZE / max(im.shape[:2])
        if r < 1:
            im = cv2.resize(im, (round(im.shape[1] * r), round(im.shape[0] * r)), interpolation=cv2.INTER_AREA)
        name = f"{a.ad}_{img.stem}"
        cv2.imwrite(str(out / "images" / f"{name}.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 95])
        (out / "labels" / f"{name}.txt").write_text("".join(f"{c} {x:.6f} {y:.6f} {w:.6f} {hh:.6f}\n" for c, x, y, w, hh in kept))
        stats["eklendi"] += 1
        stats["kutu"] += len(kept)
        for c, *_ in kept:
            per_class[ours[c]] = per_class.get(ours[c], 0) + 1
    print(json.dumps({"ad": a.ad, **stats, "sinif_kutu": dict(sorted(per_class.items()))}, ensure_ascii=False))
    print("train_birlesik.txt satır:", rebuild_list(ours))


if __name__ == "__main__":
    main()
