"""Veri seti denetimi (yol haritası Hafta 1, adım 5).

Sınıf dağılımı, kutu boyutları, bölmeler arası yakın kopyalar (veri sızıntısı) ve
gözle kontrol için kutuları çizilmiş 100 rastgele etiket.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\veri_denetimi.py
Çıktılar: docs/veri_denetimi.md, runs/denetim/
"""

import csv
import random
from collections import Counter
from pathlib import Path

import cv2
import imagehash
import numpy as np
import yaml
from PIL import Image

ML = Path(__file__).resolve().parents[1]
DATA = ML / "data" / "levha"
OUT = ML / "runs" / "denetim"
REPORT = ML.parent / "docs" / "veri_denetimi.md"
SPLITS = ("train", "valid", "test")
SIZE_BINS = (8, 16, 32, 64)  # kutunun kısa kenarı, model girişindeki piksel cinsinden
# Gözle kontrol: ≤10 hep aynı sahne, 12–14 karışık, ≥16 farklı sahne. Güvenli taraf: ≤12 sızıntı sayılır.
LEAK_MAX = 12

names = yaml.safe_load((DATA / "data.yaml").read_text(encoding="utf-8"))["names"]


def load_split(split):
    """Her görsel için (yol, genişlik, yükseklik, [(sınıf, x, y, w, h), ...]) döndürür."""
    items = []
    for img in sorted((DATA / split / "images").iterdir()):
        lbl = DATA / split / "labels" / f"{img.stem}.txt"
        boxes = []
        if lbl.exists():
            for line in lbl.read_text().split("\n"):
                if line.strip():
                    c, *xywh = line.split()
                    boxes.append((int(c), *map(float, xywh[:4])))
        with Image.open(img) as im:  # yalnızca başlığı okur, görüntüyü çözmez
            w, h = im.size
        items.append((img, w, h, boxes))
    return items


def short_side_px(w, h, bw, bh, imgsz):
    """Letterbox sonrası (uzun kenar = imgsz) kutunun kısa kenarı kaç piksel?"""
    s = imgsz / max(w, h)
    return min(bw * w, bh * h) * s


def phash_int(path):
    with Image.open(path) as im:
        im.draft("L", (256, 256))  # JPEG'i küçük çözerek hızlandır
        return int(str(imagehash.phash(im)), 16)


def hamming_to_all(h, arr):
    x = np.bitwise_xor(arr, np.uint64(h))
    return np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1)


def write_clean_split(rows):
    """Sızıntısız valid/test listelerini ve onları kullanan data_temiz.yaml'ı yazar."""
    counts = {}
    for split, list_name in (("valid", "val_temiz.txt"), ("test", "test_temiz.txt")):
        keep = [f"./{split}/images/{name}" for s, name, _, d in rows if s == split and d > LEAK_MAX]
        (DATA / list_name).write_text("\n".join(keep) + "\n", encoding="utf-8")
        counts[split] = len(keep)
    cfg = {"path": "levha", "train": "train/images", "val": "val_temiz.txt", "test": "test_temiz.txt",
           "nc": len(names), "names": names}
    header = f"# veri_denetimi.py üretti: train'deki bir görsele çok benzeyen (phash ≤ {LEAK_MAX}) valid/test görselleri çıkarıldı.\n"
    (DATA / "data_temiz.yaml").write_text(header + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return counts


def draw_samples(items, n=100, per_sheet=25, cell=(384, 216)):
    random.seed(0)
    picks = random.sample([it for it in items if it[3]], n)
    (OUT / "etiketler").mkdir(parents=True, exist_ok=True)
    cells = []
    for img, w, h, boxes in picks:
        im = cv2.imread(str(img))
        t = max(2, round(max(w, h) / 300))
        for c, x, y, bw, bh in boxes:
            p1 = (int((x - bw / 2) * w), int((y - bh / 2) * h))
            p2 = (int((x + bw / 2) * w), int((y + bh / 2) * h))
            cv2.rectangle(im, p1, p2, (0, 0, 255), t)
            cv2.putText(im, names[c], (p1[0], max(p1[1] - 2 * t, 10 * t)), cv2.FONT_HERSHEY_SIMPLEX, t / 3, (0, 0, 255), t)
        cells.append(cv2.resize(im, cell))
    cols = 5
    for i in range(0, n, per_sheet):
        chunk = cells[i : i + per_sheet]
        rows = [np.hstack(chunk[r : r + cols]) for r in range(0, len(chunk), cols)]
        cv2.imwrite(str(OUT / "etiketler" / f"sayfa_{i // per_sheet + 1}.jpg"), np.vstack(rows))
    return [p[0].name for p in picks]


def main():
    data = {s: load_split(s) for s in SPLITS}
    lines = ["# Veri Seti Denetimi", "", f"Veri: `ml/data/levha` (Roboflow sürüm 17, augmentasyonsuz)", ""]

    # 1) Görsel / etiket sayıları
    lines += ["## 1. Bölmeler", "", "| Bölme | Görsel | Levha (kutu) | Etiketsiz görsel |", "|---|---|---|---|"]
    for s, items in data.items():
        n_box = sum(len(b) for *_, b in items)
        empty = sum(1 for *_, b in items if not b)
        lines.append(f"| {s} | {len(items)} | {n_box} | {empty} |")

    # 2) Sınıf dağılımı
    counts = {s: Counter(c for *_, b in items for c, *_ in b) for s, items in data.items()}
    lines += ["", "## 2. Sınıf dağılımı (kutu sayısı)", "", "| # | Sınıf | train | valid | test |", "|---|---|---|---|---|"]
    for i, n in sorted(enumerate(names), key=lambda t: -counts["train"][t[0]]):
        lines.append(f"| {i} | {n} | {counts['train'][i]} | {counts['valid'][i]} | {counts['test'][i]} |")

    # 3) Kutu boyutları (imgsz 640 ve 320 için)
    all_boxes = [(w, h, bw, bh) for items in data.values() for _, w, h, b in items for _, _, _, bw, bh in b]
    lines += ["", "## 3. Levhaların model girişindeki boyutu", "",
              "Kutunun kısa kenarı, görüntü model girişine küçültüldükten sonra kaç piksel kalıyor?", "",
              "| Kısa kenar | imgsz=640 | imgsz=320 |", "|---|---|---|"]
    edges = (0, *SIZE_BINS, 10**9)
    sizes = {z: np.array([short_side_px(*b, z) for b in all_boxes]) for z in (640, 320)}
    for lo, hi in zip(edges[:-1], edges[1:]):
        label = f"< {hi} px" if lo == 0 else (f"≥ {lo} px" if hi == 10**9 else f"{lo}–{hi} px")
        pct = {z: 100 * np.mean((v >= lo) & (v < hi)) for z, v in sizes.items()}
        lines.append(f"| {label} | %{pct[640]:.1f} | %{pct[320]:.1f} |")
    lines.append(f"\nMedyan kısa kenar: imgsz=640'ta {np.median(sizes[640]):.0f} px, imgsz=320'de {np.median(sizes[320]):.0f} px.")

    # 4) Bölmeler arası yakın kopyalar
    hashes = {s: np.array([phash_int(p) for p, *_ in items], dtype=np.uint64) for s, items in data.items()}
    rows = []
    for s in ("valid", "test"):
        for (img, *_), h in zip(data[s], hashes[s]):
            d = hamming_to_all(h, hashes["train"])
            j = int(d.argmin())
            rows.append((s, img.name, data["train"][j][0].name, int(d[j])))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "yakin_kopyalar.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([("bolme", "gorsel", "en_yakin_train", "hamming"), *sorted(rows, key=lambda r: r[3])])
    lines += ["", "## 4. Veri sızıntısı: valid/test görsellerinin train'deki en yakın eşi", "",
              "Algısal hash (64 bit) farkı: 0 = aynı görsel, ≤ 8 = neredeyse aynı kare, ≥ 20 = farklı görsel.", "",
              "| En yakın train eşine uzaklık | valid | test |", "|---|---|---|"]
    for lo, hi, label in ((0, 0, "0 (aynı)"), (1, 4, "1–4"), (5, 8, "5–8"), (9, 12, "9–12"), (13, 64, "≥ 13")):
        n = {s: sum(1 for r in rows if r[0] == s and lo <= r[3] <= hi) for s in ("valid", "test")}
        lines.append(f"| {label} | {n['valid']} | {n['test']} |")
    lines.append("\nTam liste: `ml/runs/denetim/yakin_kopyalar.csv`")
    clean = write_clean_split(rows)
    lines += ["", f"Uzaklığı ≤ {LEAK_MAX} olanlar sızıntı sayıldı ve dışarıda bırakıldı. "
              f"Temiz valid: {clean['valid']} görsel, temiz test: {clean['test']} görsel → `data/levha/data_temiz.yaml` "
              "(train aynı; orijinal veri setine dokunulmadı)."]

    # 5) Gözle kontrol örnekleri
    picked = draw_samples(data["train"])
    lines += ["", "## 5. Gözle kontrol", "",
              f"{len(picked)} rastgele train görselinin kutuları çizildi: `ml/runs/denetim/etiketler/sayfa_1..4.jpg`"]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
