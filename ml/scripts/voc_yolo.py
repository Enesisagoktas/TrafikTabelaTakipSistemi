"""Pascal VOC (jpg + xml) setini ek_veri.py'nin okuduğu YOLO düzenine çevirir: <cikti>/{images,labels} + data.yaml.
EXIF yönü görsele uygulanır (TTSD'de 123 görsel yan; XML kutuları dönmüş hâle göre). Sınıf adları kaynaktaki gibi kalır.

  .venv\\Scripts\\python scripts\\voc_yolo.py data\\dis\\ttsd_navigatr\\repo\\test data\\dis\\ttsd_yolo
"""
import sys
import xml.etree.ElementTree as ET  # stdlib dış varlık çözmüyor, expat >= 2.4 "billion laughs"a karşı korumalı; defusedxml gerekmedi
from pathlib import Path

import yaml
from PIL import Image, ImageOps

src, out = Path(sys.argv[1]), Path(sys.argv[2])
(out / "images").mkdir(parents=True, exist_ok=True)
(out / "labels").mkdir(parents=True, exist_ok=True)
names, n_img = [], 0
for x in sorted(src.glob("*.xml")):
    img = x.with_suffix(".jpg")
    if not img.exists():
        continue
    im = ImageOps.exif_transpose(Image.open(img)).convert("RGB")
    W, H = im.size
    rows = []
    for o in ET.parse(x).getroot().iter("object"):
        n = o.find("name").text.strip()
        if n not in names:
            names.append(n)
        b = o.find("bndbox")
        x1, y1, x2, y2 = (float(b.find(k).text) for k in ("xmin", "ymin", "xmax", "ymax"))
        x1, x2, y1, y2 = max(0, x1), min(W, x2), max(0, y1), min(H, y2)
        if x2 > x1 and y2 > y1:
            rows.append(f"{names.index(n)} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}\n")
    im.save(out / "images" / img.name, quality=95)
    (out / "labels" / f"{img.stem}.txt").write_text("".join(rows))
    n_img += 1
(out / "data.yaml").write_text(yaml.safe_dump({"names": names}, allow_unicode=True), encoding="utf-8")
print(n_img, "görsel,", len(names), "sınıf:", names)
