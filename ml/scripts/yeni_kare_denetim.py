"""Yeni sürüş videolarından çıkarılan kareleri modelle tarar, levha içerenleri sözde etiketler, sınıf başına denetim paftası yazar.

Amaç (30 Ekim, v10): farklı şehir/hava Türk kareleri. Model önerir, insan (ya da Claude, paftaya bakarak) ayıklar.
1) Tarama:  .venv\\Scripts\\python scripts\\yeni_kare_denetim.py tara <model.pt> <kare_klasoru> <ad> [esik=0.35]
   -> data/dis/<ad>_sozde/{images,labels,data.yaml}: yalnızca en az bir tespiti olan kareler (YOLO düzeni, names = modelin adları)
   -> data/dis/<ad>_sozde/pafta_<sinif>_<n>.jpg: o sınıfın kutuları numaralı (sınıf:no), 12 sütun x 10 satır.
2) Denetim: reddedilecek kutuları data/dis/<ad>_sozde/ret.txt'ye yaz, satır başına "sinif:no" (ör. keskin_viraj:17), ya da
   bütün sınıfı atmak için "sinif:*". Bir kutunun sınıfını değiştirmek için "sinif:no=yeni_sinif".
3) Uygulama: .venv\\Scripts\\python scripts\\yeni_kare_denetim.py uygula <ad>
   -> ret.txt uygulanır; kutusu kalmayan kare silinir. Sonra ek_veri.py ile eğitime eklenir (eşleme: kimlik, --diger).
"""

import json
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw
from ultralytics import YOLO

DIS = Path(__file__).resolve().parents[1] / "data" / "dis"
S, COLS, ROWS = 96, 12, 10


def tara(weights, frames, ad, thr=0.35):
    model = YOLO(weights)
    names = [model.names[i] for i in range(len(model.names))]
    out = DIS / f"{ad}_sozde"
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(exist_ok=True)
    (out / "data.yaml").write_text(yaml.safe_dump({"names": names}), encoding="utf-8")
    boxes = {}  # sınıf -> [(no, görsel, (x,y,w,h))]
    kept = 0
    for p in sorted(Path(frames).glob("*.jpg")):
        r = model.predict(p, imgsz=640, conf=thr, verbose=False, device=0)[0]
        if not len(r.boxes):
            continue
        kept += 1
        lines = []
        for c, b, cf in zip(r.boxes.cls.tolist(), r.boxes.xywhn.tolist(), r.boxes.conf.tolist()):
            n = names[int(c)]
            lst = boxes.setdefault(n, [])
            lst.append((len(lst) + 1, p.name, tuple(b), cf))
            lines.append(f"{int(c)} " + " ".join(f"{v:.6f}" for v in b))
        (out / "labels" / f"{p.stem}.txt").write_text("\n".join(lines) + "\n")
        Image.open(p).save(out / "images" / p.name, quality=93)
    for n, lst in boxes.items():
        for si in range(0, len(lst), COLS * ROWS):
            chunk = lst[si:si + COLS * ROWS]
            sheet = Image.new("RGB", (COLS * S, -(-len(chunk) // COLS) * S), "white")
            d = ImageDraw.Draw(sheet)
            for i, (no, img, (x, y, w, h), cf) in enumerate(chunk):
                im = Image.open(Path(frames) / img)
                W, H = im.size
                crop = im.crop((int((x - w * 0.7) * W), int((y - h * 0.7) * H), int((x + w * 0.7) * W), int((y + h * 0.7) * H)))
                crop.thumbnail((S - 4, S - 4))
                px, py = (i % COLS) * S + 2, (i // COLS) * S + 2
                sheet.paste(crop, (px, py))
                d.rectangle((px, py, px + 30, py + 11), fill="black")
                d.text((px + 2, py), f"{no}", fill="yellow")
                d.text((px + 2, py + S - 14), f"{cf:.2f}", fill="red")
            sheet.save(out / f"pafta_{n}_{si // (COLS * ROWS) + 1}.jpg", quality=85)
    json.dump({n: [(no, img, b, round(cf, 3)) for no, img, b, cf in lst] for n, lst in boxes.items()},
              open(out / "kutular.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{kept} karede tespit var; sınıf başına kutu:", {n: len(l) for n, l in sorted(boxes.items())})


def uygula(ad):
    out = DIS / f"{ad}_sozde"
    names = yaml.safe_load((out / "data.yaml").read_text(encoding="utf-8"))["names"]
    boxes = json.load(open(out / "kutular.json", encoding="utf-8"))
    ret, degis = set(), {}
    for line in (out / "ret.txt").read_text(encoding="utf-8").splitlines() if (out / "ret.txt").exists() else []:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, new = line.partition("=")
        n, no = key.split(":")
        if new:
            degis[(n, int(no))] = new.strip()
        elif no == "*":
            ret.add((n, "*"))
        else:
            ret.add((n, int(no)))
    drop = {}  # görsel -> {(sınıf_idx, kutu) atılacak}; değişenler -> yeni sınıf
    for n, lst in boxes.items():
        for no, img, b, _ in lst:
            key = (names.index(n), tuple(round(v, 6) for v in b))
            if (n, no) in degis:  # "sinif:*" + "sinif:no=sinif" = yalnızca o kutuyu tut
                drop.setdefault(img, {})[key] = names.index(degis[(n, no)])
            elif (n, no) in ret or (n, "*") in ret:
                drop.setdefault(img, {})[key] = None
    removed = changed = deleted = 0
    for lbl in sorted((out / "labels").glob("*.txt")):
        img = lbl.stem + ".jpg"
        rows = []
        for row in lbl.read_text().splitlines():
            c, *b = row.split()
            key = (int(c), tuple(round(float(v), 6) for v in b))
            act = drop.get(img, {}).get(key, "keep")
            if act is None:
                removed += 1
                continue
            if act != "keep":
                changed += 1
                c = act
            rows.append(f"{c} " + " ".join(b))
        if rows:
            lbl.write_text("\n".join(rows) + "\n")
        else:
            lbl.unlink()
            (out / "images" / img).unlink(missing_ok=True)
            deleted += 1
    print(f"{removed} kutu atıldı, {changed} kutunun sınıfı değişti, {deleted} kare silindi; kalan kare {len(list((out / 'labels').glob('*.txt')))}")


if __name__ == "__main__":
    if sys.argv[1] == "tara":
        tara(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else 0.35)
    else:
        uygula(sys.argv[2])
