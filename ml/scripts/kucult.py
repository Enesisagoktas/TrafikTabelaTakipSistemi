"""Veri setinin 640 px'e küçültülmüş kopyasını üretir: data/levha -> data/levha640.

Neden: Windows'ta cache=ram önbelleği her DataLoader işçisine kopyalanıyor (3,2 GB x işçi sayısı).
Ultralytics görüntüyü zaten uzun kenarı imgsz olacak şekilde INTER_AREA ile küçültüyor; burada aynısı
bir kez yapılır, eğitim önbelleksiz ve çok işçiyle hızlı okur. Etiketler normalize olduğu için aynen kopyalanır.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\kucult.py
"""

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

SIZE = 640
ML = Path(__file__).resolve().parents[1]
SRC, DST = ML / "data" / "levha", ML / "data" / f"levha{SIZE}"


def shrink(img: Path):
    out = DST / img.relative_to(SRC)
    im = cv2.imread(str(img))
    h, w = im.shape[:2]
    r = SIZE / max(h, w)
    if r < 1:
        im = cv2.resize(im, (round(w * r), round(h * r)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(out), im, [cv2.IMWRITE_JPEG_QUALITY, 95])


def main():
    for split in ("train", "valid", "test"):
        (DST / split / "images").mkdir(parents=True, exist_ok=True)
        shutil.copytree(SRC / split / "labels", DST / split / "labels", dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.cache"))
    images = sorted(SRC.glob("*/images/*.jpg"))
    with ThreadPoolExecutor(8) as pool:  # cv2 GIL'i bırakır
        list(pool.map(shrink, images))
    for name in ("val_temiz.txt", "test_temiz.txt"):
        shutil.copy(SRC / name, DST / name)
    for name in ("data.yaml", "data_temiz.yaml"):
        text = (SRC / name).read_text(encoding="utf-8").replace("path: levha\n", f"path: levha{SIZE}\n")
        (DST / name).write_text(text, encoding="utf-8")
    print(len(images), "görsel ->", DST)


if __name__ == "__main__":
    main()
